"""Validate destination content before it is rendered into the product frame."""
from __future__ import annotations
import argparse
import json
import re
import unicodedata
from pathlib import Path
from _media_policy import official_brand_allowed
from _content_integrity import content_failures
from _outfit_advice import outfit_errors

def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip()) and (value.strip() != 'REPLACE_ME')

def require_fields(record: dict, fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if record.get(field) in (None, '', [], {})]

def cover_title_too_wide(value: str) -> bool:
    text = str(value).strip()
    cjk = sum((1 for char in text if unicodedata.east_asian_width(char) in {'W', 'F'}))
    return cjk > 9 if cjk >= max(3, len(text) // 2) else len(text) > 28

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', type=Path)
    parser.add_argument('--allow-test-fixture', action='store_true', help='Tests only; production compilation never sets this flag')
    args = parser.parse_args()
    failures: list[str] = []
    try:
        data = json.loads(args.profile.read_text(encoding='utf-8'))
    except Exception as exc:
        print(f'FAIL invalid destination data: {exc}')
        return 2
    is_test_fixture = bool(data.get('test_fixture'))
    if is_test_fixture and (not args.allow_test_fixture):
        failures.append('test_fixture profiles are forbidden in production; do not strip the marker or reuse regression data')
    serialized_profile = json.dumps(data, ensure_ascii=False).lower()
    fixture_markers = ('generated-fixture', 'local-regression-fixture', 'smoke_test', 'example.com')
    if not args.allow_test_fixture and any((marker in serialized_profile for marker in fixture_markers)):
        failures.append('production profile contains test/regression/example fixture provenance')
    for key in ('destination', 'display_name', 'country'):
        if not nonempty(data.get(key)):
            failures.append(f'missing {key}')
    trip = data.get('trip', {})
    days = trip.get('days', 0) if isinstance(trip, dict) else 0
    quality_mode = str('standard' if isinstance(trip, dict) else 'standard').strip().lower()
    if not isinstance(days, int) or days < 1:
        failures.append('trip.days must be a positive integer')
        days = 0
    cover = data.get('cover', {})
    for key in ('kicker', 'title', 'summary', 'image'):
        if not nonempty(cover.get(key) if isinstance(cover, dict) else None):
            failures.append(f'cover.{key} is missing')
    if isinstance(cover, dict) and nonempty(cover.get('title')) and cover_title_too_wide(cover['title']):
        failures.append('cover.title is too wide for the locked canonical display size; shorten it before rendering (CJK max 9 full-width characters, Latin max 28 characters)')
    if isinstance(cover, dict) and nonempty(cover.get('title')):
        title_text_raw = str(cover['title']).strip()
        destination_names = {str(data.get('destination', '')).strip(), str(data.get('display_name', '')).strip()}
        if not args.allow_test_fixture and any((name and name.casefold() in title_text_raw.casefold() for name in destination_names)):
            failures.append('cover.title must be an editorial phrase without repeating the destination name')
        if not args.allow_test_fixture and re.search('\\d+\\s*(?:天|日)\\s*\\d*\\s*(?:晚|夜)?|\\d+\\s*(?:人|位)', title_text_raw):
            failures.append('cover.title must not repeat duration or traveler count; use the dedicated cover metadata')
        display_lines = cover.get('title_lines') if isinstance(cover.get('title_lines'), list) else [cover.get('title'), cover.get('subtitle', 'ITINERARY')]
        if len(display_lines) > 2 or any((not nonempty(str(line)) or cover_title_too_wide(str(line)) for line in display_lines[:2])):
            failures.append('cover display requires one or two short title lines that fit the canonical safe zone')
        display_text = ' '.join((str(line) for line in display_lines))
        if not args.allow_test_fixture and re.search('\\d+\\s*(?:天|日)\\s*\\d*\\s*(?:晚|夜)?|\\d+\\s*(?:人|位)', display_text):
            failures.append('cover display lines must not repeat duration or traveler count')
    if isinstance(cover, dict) and nonempty(cover.get('title')) and nonempty(cover.get('subtitle')):
        title_text = str(cover['title']).strip().casefold()
        subtitle_text = str(cover['subtitle']).strip().casefold()
        if subtitle_text and subtitle_text in title_text:
            failures.append('cover.title must not repeat cover.subtitle; the canonical cover renders the subtitle as its own display line')
    transport = data.get('transport', {})
    status = transport.get('status') if isinstance(transport, dict) else None
    legs = transport.get('legs', []) if isinstance(transport, dict) else []
    if status not in {'pending', 'confirmed'}:
        failures.append('transport.status must be pending or confirmed')
    if status == 'pending' and legs:
        failures.append('pending transport must have an empty legs array')
    if status == 'confirmed' and (not isinstance(legs, list) or not legs):
        failures.append('confirmed transport needs one record per actual leg')
    if status == 'confirmed' and isinstance(legs, list):
        for index, leg in enumerate(legs, 1):
            transport_fields = ('direction', 'date', 'service_number', 'origin', 'destination', 'departure_time', 'arrival_time')
            if not args.allow_test_fixture:
                transport_fields += ('verification_status', 'source_url', 'checked_at')
            missing = require_fields(leg, transport_fields) if isinstance(leg, dict) else ['record']
            if missing:
                failures.append(f"transport leg {index} missing: {', '.join(missing)}")
            elif not args.allow_test_fixture and leg.get('verification_status') != 'verified':
                failures.append(f'transport leg {index} cannot be confirmed without a verified future schedule')
        if isinstance(transport.get('decision_summary'), dict):
            missing = require_fields(transport['decision_summary'], ('selection_id', 'effective_price_cny', 'baggage', 'baggage_status', 'snapshot_at', 'source_url'))
            if missing:
                failures.append('selected transport decision missing: ' + ', '.join(missing))
    stays = data.get('stays', [])
    if not isinstance(stays, list) or not stays:
        failures.append('stays requires at least one pending or confirmed record')
    else:
        for index, stay in enumerate(stays, 1):
            state = stay.get('status') if isinstance(stay, dict) else None
            if state not in {'pending', 'confirmed'}:
                failures.append(f'stay {index} status must be pending or confirmed')
            if state == 'confirmed':
                missing = require_fields(stay, ('place_id', 'check_in', 'check_out'))
                if missing:
                    failures.append(f"confirmed stay {index} missing: {', '.join(missing)}")
    itinerary = data.get('itinerary', [])
    if not isinstance(itinerary, list) or len(itinerary) != days:
        failures.append(f'itinerary must contain exactly trip.days records: {(len(itinerary) if isinstance(itinerary, list) else 0)}/{days}')
    else:
        period_descriptions = []
        photo_payloads = []
        for index, day in enumerate(itinerary, 1):
            if not isinstance(day, dict) or not nonempty(day.get('theme')):
                failures.append(f'itinerary day {index} needs a generated theme')
                continue
            periods = day.get('periods', {})
            if not isinstance(periods, dict) or any((not periods.get(name) for name in ('morning', 'afternoon', 'evening'))):
                failures.append(f'itinerary day {index} needs morning/afternoon/evening records')
            elif isinstance(periods, dict):
                for period_name in ('morning', 'afternoon', 'evening'):
                    value = periods.get(period_name)
                    if isinstance(value, dict) and require_fields(value, ('title', 'description')):
                        failures.append(f'itinerary day {index} {period_name} structured record needs title and description')
                    elif not isinstance(value, (str, dict)):
                        failures.append(f'itinerary day {index} {period_name} must be text or a title/description record')
                    else:
                        description = str(value.get('description', '') if isinstance(value, dict) else value).strip()
                        period_descriptions.append(description)
                        if len(re.sub('\\s+', '', description)) < 18 or re.search('第\\s*\\d+\\s*天|按地理顺序|慢慢进入状态|临时调整空间|代表性晚餐', description):
                            failures.append(f'itinerary day {index} {period_name} uses thin or generic filler instead of route-specific activity copy')
            minimum_stops = 2 if index in {1, days} else 3
            if len(day.get('stops', [])) < minimum_stops:
                failures.append(f'itinerary day {index} needs at least {minimum_stops} ordered stops for a usable route')
            else:
                for stop_index, stop in enumerate(day.get('stops', []), 1):
                    missing = require_fields(stop, ('place_id', 'arrival_time', 'dwell_minutes', 'transport_mode', 'transfer_minutes', 'distance_km', 'estimated_cost', 'practical_note', 'time_guard')) if isinstance(stop, dict) else ['record']
                    if missing:
                        failures.append(f"itinerary day {index} stop {stop_index} missing: {', '.join(missing)}")
                    elif len(re.sub('\\s+', '', str(stop.get('practical_note', '')))) < 18 or len(re.sub('\\s+', '', str(stop.get('time_guard', '')))) < 8:
                        failures.append(f'itinerary day {index} stop {stop_index} needs a practical visit note and useful time/queue fallback for Trip Mode')
            for advice_key in ('shopping_advice', 'photo_advice'):
                advice = day.get(advice_key, {})
                required = ('title', 'description') if advice_key == 'shopping_advice' else ('title', 'lighting', 'suitable_shots', 'portrait_tip', 'shooting_plan')
                if not isinstance(advice, dict) or require_fields(advice, required):
                    failures.append(f'itinerary day {index} needs complete {advice_key}; shopping appears only in Trip Mode, while photo advice appears in both the handbook and Trip Mode')
            photo = day.get('photo_advice', {})
            if not is_test_fixture:
                failures.extend(error['pointer']+': '+error['message'] for error in outfit_errors(photo, f'/itinerary/{index-1}/photo_advice'))
            if isinstance(photo, dict):
                shots = photo.get('suitable_shots', [])
                payload = json.dumps({key: photo.get(key) for key in ('title', 'lighting', 'suitable_shots', 'portrait_tip')}, ensure_ascii=False, sort_keys=True)
                photo_payloads.append(payload)
                searchable = ' '.join([str(photo.get('title', '')), str(photo.get('lighting', '')), ' '.join(map(str, shots))])
                if len(shots) < 2 or any((len(re.sub('\\s+', '', str(shot))) < 8 for shot in shots)):
                    failures.append(f'itinerary day {index} photography advice needs two substantive subject/viewpoint/composition ideas')
                plans = photo.get('shooting_plan', [])
                if not isinstance(plans, list) or not 2 <= len(plans) <= 3 or any((not isinstance(item, dict) or require_fields(item, ('time', 'title', 'note')) or len(re.sub('\\s+', '', str(item.get('note', '')))) < 12 for item in plans)):
                    failures.append(f'itinerary day {index} photography shooting_plan needs 2-3 route-specific time/title/note cards')
                plan_copy = ' '.join((str(item.get('note', '')) for item in plans if isinstance(item, dict)))
                if '手机' not in plan_copy or '相机' not in plan_copy:
                    failures.append(f'itinerary day {index} photography shooting_plan must include separate actionable phone and camera guidance')
                if re.search('城市与人像|街区关系|城市生活细节|早晚侧光更柔和', searchable):
                    failures.append(f'itinerary day {index} photography advice uses generic reusable copy')
            samples = day.get('photo_advice', {}).get('samples', [])
            if samples and any((not isinstance(item, dict) or require_fields(item, ('img', 'label', 'title', 'tip', 'motion', 'verified')) or item.get('verified') is not True for item in samples)):
                failures.append(f'itinerary day {index} photo samples must be verified local assets with complete composition notes; otherwise omit the samples array')
        if len(period_descriptions) != len(set(period_descriptions)):
            failures.append('itinerary period descriptions repeat across days; every day needs route-specific copy')
        if len(photo_payloads) != len(set(photo_payloads)):
            failures.append('photography advice repeats across days; every day needs distinct route-specific guidance')
    phases = data.get('journey_phases', [])
    if phases and (not isinstance(phases, list) or any((not nonempty(item.get('title')) for item in phases if isinstance(item, dict)))):
        failures.append('journey phases must be empty or contain complete destination-authored titles')
    groups = data.get('module_groups', {})
    n = max(4, days)
    for family in ('shopping', 'experiences', 'travel_notes'):
        value = groups.get(family, []) if isinstance(groups, dict) else []
        if not isinstance(value, list) or not value:
            failures.append(f'module_groups.{family} must contain destination-authored records')
    for family in ('shopping', 'experiences'):
        for index, group in enumerate(groups.get(family, []), 1):
            if not isinstance(group, dict) or not nonempty(group.get('title')) or (not group.get('items')):
                failures.append(f'{family} group {index} needs a title and non-empty items')
            elif any((not isinstance(item, dict) or not item.get('place_id') for item in group.get('items', []))):
                failures.append(f'{family} group {index} contains an item without place_id')
            if family == 'shopping' and isinstance(group, dict) and (not nonempty(group.get('subtitle'))):
                failures.append(f'shopping group {index} needs a truthful destination-specific subtitle such as 商场与店铺')
    shopping_count = sum((len(group.get('items', [])) for group in groups.get('shopping', []) if isinstance(group, dict)))
    experience_count = sum((len(group.get('items', [])) for group in groups.get('experiences', []) if isinstance(group, dict)))
    if shopping_count < 1:
        failures.append('shopping requires at least one destination-scaled referenced place')
    experience_groups = groups.get('experiences', [])
    experience_mode = str(trip.get('experience_mode', 'standard') if isinstance(trip, dict) else 'standard').strip().lower()
    if experience_mode not in {'standard', 'constrained', 'expanded'}:
        failures.append('trip.experience_mode must be standard, constrained or expanded')
    if experience_mode == 'standard' and (experience_count != 6 or len(experience_groups) != 3):
        failures.append(f'Standard experiences require exactly 6 options across exactly 3 groups: groups={len(experience_groups)}/3, options={experience_count}/6')
    if experience_mode == 'constrained' and (experience_count != 4 or len(experience_groups) != 2):
        failures.append(f'constrained experiences require exactly 4 options across exactly 2 groups: groups={len(experience_groups)}/2, options={experience_count}/4')
    if experience_mode == 'expanded' and (experience_count < 6 or len(experience_groups) < 3):
        failures.append(f'expanded experiences require at least 6 options across at least 3 groups: groups={len(experience_groups)}/3, options={experience_count}/6')
    for index, group in enumerate(experience_groups, 1):
        item_count = len(group.get('items', [])) if isinstance(group, dict) else 0
        if experience_mode in {'standard', 'constrained'} and item_count < 1:
            failures.append(f'Standard experience group {index} needs at least one useful option')
        elif experience_mode == 'expanded' and item_count < 2:
            failures.append(f'expanded experience group {index} needs at least two useful options')
    interest_text = ' '.join((str(item) for item in trip.get('interests', []))).lower() if isinstance(trip, dict) else ''
    bathing_requested = any((token in interest_text for token in ('温泉', '泡汤', '温浴', 'onsen', 'sento', 'spa')))
    if bathing_requested and str(data.get('country', '')).lower() in {'japan', '日本'}:
        experience_ids = [str(item.get('place_id')) for group in groups.get('experiences', []) if isinstance(group, dict) for item in group.get('items', []) if isinstance(item, dict) and item.get('place_id')]
        if len(experience_ids) != len(set(experience_ids)):
            failures.append('experience groups must not repeat the same place')
        experience_places = {str(place.get('id')): place for place in data.get('places', []) if isinstance(place, dict) and place.get('type') == 'experience'}
        bathing_ids = set()
        for place_id in experience_ids:
            record = experience_places.get(place_id, {})
            classification = ' '.join((str(record.get(field, '')) for field in ('experience_type', 'category', 'display_name', 'local_name', 'english_name', 'description'))).lower()
            if any((token in classification for token in ('onsen', 'bathing', '温泉', '入浴', '泡汤'))):
                bathing_ids.add(place_id)
        constraint_text = ' '.join((str(item) for item in data.get('trip', {}).get('constraints', []))).lower()
        bathing_excluded = any((token in constraint_text for token in ('避开温泉', '不要温泉', '不泡温泉', 'exclude onsen', 'no onsen', 'avoid bathing')))
        if not bathing_excluded and len(bathing_ids) < 2:
            failures.append(f'A Japan trip explicitly requesting bathing/onsen needs two distinct venues unless excluded: {len(bathing_ids)}/2')
    food = groups.get('food', {}) if isinstance(groups, dict) else {}
    for key in ('menu_primer', 'local_snacks', 'dedicated_trip', 'reliable_chains'):
        if not isinstance(food.get(key), list) or not food.get(key):
            failures.append(f'module_groups.food.{key} must be destination-authored and non-empty')
    for index, item in enumerate(food.get('menu_primer', []), 1):
        if not isinstance(item, dict) or require_fields(item, ('term', 'meaning', 'note')):
            failures.append(f'food.menu_primer item {index} needs term, meaning and practical note')
    for index, item in enumerate(food.get('local_snacks', []), 1):
        if not isinstance(item, dict) or require_fields(item, ('name', 'local_name', 'description', 'why_try', 'where_to_find')):
            failures.append(f'food.local_snacks item {index} needs names, description, why_try and where_to_find')
    if len(food.get('local_snacks', [])) != 4:
        failures.append(f"food.local_snacks requires exactly 4 entries: {len(food.get('local_snacks', []))}/4")
    menu_guide = food.get('menu_guide')
    if menu_guide is None:
        failures.append('food.menu_guide is required before rendering')
    elif not isinstance(menu_guide, dict) or require_fields(menu_guide, ('kicker', 'title', 'intro', 'cards')):
        failures.append('food.menu_guide must be complete')
    else:
        cards = menu_guide.get('cards', [])
        if not isinstance(cards, list) or len(cards) < 4:
            failures.append(f'food.menu_guide requires at least four guidance cards when supplied: {(len(cards) if isinstance(cards, list) else 0)}/4')
        else:
            for index, item in enumerate(cards, 1):
                if not isinstance(item, dict) or require_fields(item, ('title', 'note')) or len(str(item.get('note', '')).strip()) < 30:
                    failures.append(f'food.menu_guide card {index} needs a title and substantive destination-specific guidance')
    food_floors = {'dedicated_trip': 6, 'reliable_chains': 2}
    for key in ('dedicated_trip', 'reliable_chains'):
        if len(food.get(key, [])) < food_floors[key]:
            failures.append(f'food.{key} requires at least {food_floors[key]} places: {len(food.get(key, []))}/{food_floors[key]}')
        for index, item in enumerate(food.get(key, []), 1):
            if not isinstance(item, dict) or not item.get('place_id'):
                failures.append(f'food.{key} item {index} needs place_id')
    if len(food.get('reliable_chains', [])) > 4:
        failures.append(f"food.reliable_chains allows at most 4 places: {len(food.get('reliable_chains', []))}/4")
    if 'near_stay' in food or 'delivery' in food:
        failures.append('food must omit the retired near_stay and delivery families')
    dedicated_ids = {str(item.get('place_id')) for item in food.get('dedicated_trip', []) if isinstance(item, dict) and item.get('place_id')}
    reliable_chain_ids = {str(item.get('place_id')) for item in food.get('reliable_chains', []) if isinstance(item, dict) and item.get('place_id')}
    repeated_food_ids = dedicated_ids & reliable_chain_ids
    if repeated_food_ids:
        failures.append(f"dedicated_trip and reliable_chains must use distinct restaurant branches: {', '.join(sorted(repeated_food_ids))}")
    itinerary_ids = {str(stop.get('place_id')) for day in itinerary if isinstance(day, dict) for stop in day.get('stops', []) if isinstance(stop, dict) and stop.get('place_id')}
    scheduled_dedicated = dedicated_ids & itinerary_ids
    if days >= 3 and len(scheduled_dedicated) < 3:
        failures.append(f'itinerary must schedule at least 3 dedicated_trip restaurants: {len(scheduled_dedicated)}/3')
    preparation = groups.get('preparation', {}) if isinstance(groups, dict) else {}
    for key in ('essentials', 'confirm_ahead'):
        if not isinstance(preparation.get(key), list) or not preparation.get(key):
            failures.append(f'module_groups.preparation.{key} must be destination-authored and non-empty')
    check_count = len(preparation.get('essentials', [])) + len(preparation.get('confirm_ahead', []))
    if check_count < max(24, days * 3):
        failures.append(f'preparation requires at least {max(24, days * 3)} checks: {check_count}/{max(24, days * 3)}')
    language = groups.get('language', {}) if isinstance(groups, dict) else {}
    keyword_groups = language.get('keyword_groups', [])
    phrase_groups = language.get('phrase_groups', [])
    if len(keyword_groups) != 5 or len(phrase_groups) != 5:
        failures.append('language requires exactly five keyword groups and five phrase groups')
    keyword_count = sum((len(group.get('items', [])) for group in keyword_groups if isinstance(group, dict)))
    phrase_count = sum((len(group.get('items', [])) for group in phrase_groups if isinstance(group, dict)))
    if keyword_count < 25:
        failures.append(f'language requires at least 25 keyword entries: {keyword_count}/25')
    if phrase_count < 25:
        failures.append(f'language requires at least 25 complete phrases: {phrase_count}/25')
    for family_name, family in (('keyword_groups', keyword_groups), ('phrase_groups', phrase_groups)):
        for group_index, group in enumerate(family, 1):
            if isinstance(group, dict) and (not re.search('[\\u3400-\\u9fff]', str(group.get('title', '')))):
                failures.append(f'language.{family_name} group {group_index} title must be Chinese')
            if len(group.get('items', [])) != 5:
                failures.append(f'language.{family_name} group {group_index} needs exactly 5 entries')
    english_keyword_groups = language.get('english_keyword_groups', [])
    english_phrase_groups = language.get('english_phrase_groups', [])
    if not is_test_fixture and (len(english_keyword_groups) != 5 or len(english_phrase_groups) != 5):
        failures.append('every production handbook requires five English fallback keyword groups and five English fallback phrase groups')
    if not is_test_fixture:
        for family_name, family, field in (('english_keyword_groups', english_keyword_groups, 'term'), ('english_phrase_groups', english_phrase_groups, 'sentence')):
            for group_index, group in enumerate(family, 1):
                if isinstance(group, dict) and (not re.search('[\\u3400-\\u9fff]', str(group.get('title', '')))):
                    failures.append(f'language.{family_name} group {group_index} title must be Chinese')
                group_title = str(group.get('title', '')) if isinstance(group, dict) else ''
                if re.search('(?:\\(|（)\\s*(?:English|英语)\\s*(?:\\)|）)|英语版|中英对照', group_title, re.I):
                    failures.append(f'language.{family_name} group {group_index} title must not repeat the edition language: {group_title}')
                if len(group.get('items', [])) != 5:
                    failures.append(f'language.{family_name} group {group_index} needs exactly 5 bilingual entries')
                for item in group.get('items', []) if isinstance(group, dict) else []:
                    if isinstance(item, dict) and (not re.search('[A-Za-z]', str(item.get(field, '')))):
                        failures.append(f"English fallback entry must contain English text: {item.get(field, '')}")
    if str(data.get('country', '')).lower() in {'japan', '日本'}:
        missing_readings = sum((1 for group in keyword_groups + phrase_groups if isinstance(group, dict) for item in group.get('items', []) if isinstance(item, dict) and (not nonempty(item.get('reading')))))
        if missing_readings:
            failures.append(f'Japanese language entries require readings: {missing_readings} missing')
        repeated_readings = sum((1 for group in keyword_groups + phrase_groups if isinstance(group, dict) for item in group.get('items', []) if isinstance(item, dict) and str(item.get('reading', '')).strip() == str(item.get('term', item.get('sentence', ''))).strip()))
        if repeated_readings:
            failures.append(f'Japanese language readings must be useful romaji, not repeated Japanese text: {repeated_readings}')
        placeholder_readings = sum((1 for group in keyword_groups + phrase_groups if isinstance(group, dict) for item in group.get('items', []) if isinstance(item, dict) and re.search('\\bromaji\\b|(?:交通与定位|点餐与忌口|住宿沟通)\\s*\\d+', str(item.get('reading', '')), re.I)))
        if placeholder_readings:
            failures.append(f'Japanese language readings contain template placeholders: {placeholder_readings}')
        for family, field in ((keyword_groups, 'term'), (phrase_groups, 'sentence')):
            for group in family:
                for item in group.get('items', []):
                    if re.search('[（(](?:日本語|日语|Japanese)[）)]$', str(item.get(field, '')), re.I):
                        failures.append('Japanese entries must not append a language label to evade validation')
        if not language.get('english_keyword_groups') or not language.get('english_phrase_groups'):
            failures.append('Japan requires both a Japanese/romaji edition and an English fallback edition')
        for family, field in ((language.get('english_keyword_groups', []), 'term'), (language.get('english_phrase_groups', []), 'sentence')):
            for group in family:
                if not re.search('[\\u3400-\\u9fff]', str(group.get('title', ''))):
                    failures.append(f"English fallback group headings remain Chinese for navigation: {group.get('title', '')}")
                if len(group.get('items', [])) < 5:
                    failures.append(f"each English fallback group needs at least 5 bilingual entries: {group.get('title', '')}")
                for item in group.get('items', []) if isinstance(group, dict) else []:
                    if isinstance(item, dict) and (not re.search('[A-Za-z]', str(item.get(field, '')))):
                        failures.append(f"English language entry must contain English text, not translated Chinese: {item.get(field, '')}")
    notes = groups.get('travel_notes', []) if isinstance(groups, dict) else []
    for group in notes:
        for item in group.get('items', []):
            if item.get('priority') not in ('必须', '建议', '随缘'):
                failures.append('travel note requires explicit priority: ' + str(item.get('title', '')))
    note_topics = sum((len(group.get('items', [])) for group in notes if isinstance(group, dict)))
    required_note_categories = {'climate', 'etiquette', 'transport', 'safety', 'payment'}
    note_categories = {str(group.get('category', '')) for group in notes if isinstance(group, dict)}
    if len(notes) != 5 or note_topics != 20:
        failures.append(f'travel notes require five groups with four topics each: groups={len(notes)}/5, topics={note_topics}/20')
    if not required_note_categories.issubset(note_categories):
        failures.append('travel notes must include climate, culture/etiquette, transport, safety and payment categories')
    for group_index, group in enumerate(notes, 1):
        if not isinstance(group, dict) or not nonempty(group.get('summary')):
            failures.append(f'travel notes group {group_index} needs a useful summary')
            continue
        if len(group.get('items', [])) != 4:
            failures.append(f'travel notes group {group_index} needs exactly 4 topics')
        summary = str(group.get('summary', '')).strip()
        if len(re.sub('\\s+', '', summary)) < 24:
            failures.append(f'travel notes group {group_index} summary needs at least 24 useful characters')
        for topic_index, item in enumerate(group.get('items', []), 1):
            note = str(item.get('note', '')).strip() if isinstance(item, dict) else ''
            if not isinstance(item, dict) or not nonempty(item.get('title')) or (not nonempty(note)):
                failures.append(f'travel notes group {group_index} topic {topic_index} needs a title and a practical note')
                continue
            title = str(item.get('title', '')).strip()
            group_title = str(group.get('title', '')).strip()
            if re.fullmatch('(?:提示|贴士|注意事项?|建议|' + re.escape(group_title) + ')\\s*[0-9一二三四五六七八九十]+', title):
                failures.append(f'travel notes group {group_index} topic {topic_index} uses a mechanical numbered title: {title}')
            if len(re.sub('\\s+', '', title)) < 4:
                failures.append(f'travel notes group {group_index} topic {topic_index} needs a semantic decision-oriented title')
            if len(re.sub('\\s+', '', note)) < 34 or len(re.findall('[。！？!?；;]', note)) < 2:
                failures.append(f'travel notes group {group_index} topic {topic_index} needs two compact sentences and at least 34 useful characters')
    places = data.get('places', [])
    if not isinstance(places, list) or not places:
        failures.append('places must contain the researched destination inventory')
    else:
        ids = [str(place.get('id', '')).strip() for place in places if isinstance(place, dict)]
        if len(ids) != len(places) or any((not item for item in ids)) or len(ids) != len(set(ids)):
            failures.append('every place needs a unique stable id')
        place_by_id = {str(place.get('id')): place for place in places if isinstance(place, dict) and place.get('id')}
        scheduled_ids = {str(stop.get('place_id')) for day in itinerary if isinstance(day, dict) for stop in day.get('stops', []) if isinstance(stop, dict) and stop.get('place_id')}
        for place_id in sorted(scheduled_ids):
            place = place_by_id.get(place_id, {})
            coordinates = place.get('coordinates')
            has_pair = place.get('latitude') is not None and place.get('longitude') is not None
            has_pair = has_pair or (isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2)
            has_pair = has_pair or (isinstance(coordinates, dict) and coordinates.get('latitude', coordinates.get('lat')) is not None and (coordinates.get('longitude', coordinates.get('lng', coordinates.get('lon'))) is not None))
            if place and (not has_pair):
                failures.append(f'scheduled place {place_id} needs verified latitude/longitude for the offline Trip Mode route map')
        shopping_group_ids = {str(item.get('place_id')) for group in groups.get('shopping', []) if isinstance(group, dict) for item in group.get('items', []) if isinstance(item, dict)}
        misplaced_souvenirs = sorted((place_id for place_id in shopping_group_ids if place_by_id.get(place_id, {}).get('type') == 'souvenir'))
        if misplaced_souvenirs:
            failures.append('souvenirs must render only in the dedicated souvenir disclosure, not shopping groups: ' + ', '.join(misplaced_souvenirs))
        for place_id, place in place_by_id.items():
            missing = require_fields(place, ('type', 'display_name', 'map_query', 'source_url'))
            if missing:
                failures.append(f"place {place_id} missing: {', '.join(missing)}")
            if place.get('type') in {'sight', 'shop', 'experience', 'hotel'}:
                common = require_fields(place, ('hours', 'closed_days', 'images'))
                if common:
                    failures.append(f"place {place_id} missing operating/image data: {', '.join(common)}")
            if place.get('type') in {'sight', 'restaurant'}:
                if place.get('type') == 'restaurant':
                    ratings = place.get('ratings', [])
                    platforms = {str(item.get('platform', '')).lower() for item in ratings if isinstance(item, dict)}
                    if any((platform != 'google' for platform in platforms)):
                        failures.append(f'restaurant {place_id} may only use optional Google ratings')
                if place.get('type') == 'sight':
                    ratings = place.get('ratings', [])
                    platforms = {str(item.get('platform', '')).lower() for item in ratings if isinstance(item, dict)}
                    if any((platform != 'google' for platform in platforms)):
                        failures.append(f'sight {place_id} may only use optional Google ratings')
                ratings = place.get('ratings', [])
                google_records = [item for item in ratings if isinstance(item, dict) and str(item.get('platform', '')).strip().lower() == 'google']
                for rating_index, rating_item in enumerate(place.get('ratings', []), 1):
                    if not isinstance(rating_item, dict):
                        failures.append(f'place {place_id} rating {rating_index} must be a structured record')
                        continue
                    status = rating_item.get('status', 'verified')
                    if status == 'verified':
                        rating_missing = require_fields(rating_item, ('platform', 'rating', 'source_url', 'verified_at'))
                    elif status == 'unavailable':
                        rating_missing = require_fields(rating_item, ('platform', 'source_url', 'checked_at', 'reason'))
                    else:
                        rating_missing = ['status must be verified or unavailable']
                    if rating_missing:
                        failures.append(f"place {place_id} rating {rating_index} missing: {', '.join(rating_missing)}")
            if place.get('type') == 'sight':
                missing = require_fields(place, ('duration_minutes', 'scheduled_label'))
                if missing:
                    failures.append(f"sight {place_id} missing render data: {', '.join(missing)}")
                if len(str(place.get('description', '')).strip()) < 45:
                    failures.append(f'sight {place_id} needs a more useful description covering what is there and why it matters')
                if '可替换' in str(place.get('scheduled_label', '')):
                    failures.append(f'sight {place_id} scheduled_label must use the canonical label 备选, not 可替换')
            if place.get('type') == 'shop':
                missing = require_fields(place, ('category', 'buying_tip', 'brand_highlights', 'scheduled_label'))
                if missing:
                    failures.append(f"shop {place_id} missing practical shopping data: {', '.join(missing)}")
            if place.get('type') == 'restaurant':
                missing = require_fields(place, ('local_name', 'english_name', 'cuisine', 'signature_dishes', 'price_per_person', 'description'))
                if missing:
                    failures.append(f"restaurant {place_id} missing card data: {', '.join(missing)}")
                serialized = json.dumps(place, ensure_ascii=False)
                if any((token in serialized for token in ('未核取', '按门店与时段', '店内招牌套餐', '季节推荐菜'))):
                    failures.append(f'restaurant {place_id} contains unresolved or generic placeholder data')
                if len(str(place.get('description', '')).strip()) < 45:
                    failures.append(f'restaurant {place_id} must explain why it is worth visiting')
                if isinstance(place.get('signature_dishes'), (list, dict)):
                    failures.append(f'restaurant {place_id} signature_dishes must be researched display copy, not a raw array/object')
            if place.get('type') == 'experience':
                if place.get('experience_type') not in {'wellness', 'culture', 'craft', 'nature', 'adventure', 'performance', 'food_workshop', 'nightlife', 'urban_walk', 'food_culture', 'pop_culture', 'digital_art'}:
                    failures.append(f'experience {place_id} needs a controlled experience_type')
                if len(str(place.get('description', '')).strip()) < 60:
                    failures.append(f'experience {place_id} needs a substantive description of the activity, local relevance and traveler fit')
                if place.get('hazardous') is True and len(str(place.get('risk_assessment', '')).strip()) < 45:
                    failures.append(f'hazardous experience {place_id} needs a substantive risk assessment')
            if place.get('type') == 'souvenir':
                missing = require_fields(place, ('description', 'why_buy', 'best_for', 'where_to_buy', 'buying_tip'))
                if missing:
                    failures.append(f"souvenir {place_id} missing decision-help fields: {', '.join(missing)}")
            images = place.get('images', [])
            visual_types = {'hotel', 'sight', 'shop', 'experience', 'restaurant', 'souvenir'}
            place_type = place.get('type')
            required_images = 2 if place_type == 'hotel' or (place_type == 'sight' and place.get('gallery_featured') is True) else 1 if place_type in {'sight', 'shop', 'experience', 'restaurant'} else 0
            if isinstance(images, list) and len(images) < required_images:
                failures.append(f'place {place_id} needs at least {required_images} image declarations')
            if place_type == 'sight' and place.get('gallery_featured') is not True and isinstance(images, list) and (len(images) > 1):
                failures.append(f'ordinary sight {place_id} must use one image; set gallery_featured true only for a genuine gallery priority')
            for image_index, image in enumerate(images if isinstance(images, list) else [], 1):
                if not isinstance(image, dict):
                    continue
                if not args.allow_test_fixture:
                    media_class = str(image.get('media_class', '')).lower()
                    original_media_class = str(image.get('original_media_class', media_class)).lower()
                    if image.get('visual_subject_type') in {'official_logo', 'official_share_card'} and media_class != 'official_brand_asset':
                        failures.append(f'place {place_id} image {image_index}: brand artwork cannot be classified as a photo')
                    if not official_brand_allowed(image, quality_mode) and (media_class not in {'real_photo', 'official_photo', 'licensed_photo'} or original_media_class not in {'real_photo', 'official_photo', 'licensed_photo'}):
                        failures.append(f'place {place_id} image {image_index} must be a real/official/licensed exact-place photo; generated art, SVG renders, screenshots, text cards and placeholders are forbidden')
                    is_map_asset = image.get('source_type') in {'google_maps_photo', 'google_street_view'}
                    media_url = str(image.get('download_url', ''))
                    if re.search('(?:^|[/_-])favicon(?:\\.|[/_-])|wordpress[-_ ]?(?:logo|icon)|wp-admin/images/w-logo', media_url, re.I):
                        failures.append(f'place {place_id} image {image_index} is a favicon/CMS placeholder, not destination media')
                    if is_map_asset:
                        if image.get('visual_subject_type') != 'place_exterior':
                            if image.get('source_type') == 'google_street_view':
                                failures.append(f'place {place_id} Street View image must use visual_subject_type place_exterior')
                        required_image_fields = require_fields(image, ('file', 'source_page', 'source_identity_note'))
                    else:
                        required_image_fields = require_fields(image, ('download_url', 'source_page', 'source_identity_note'))
                    if required_image_fields:
                        failures.append(f"place {place_id} image {image_index} missing evidence-chain fields: {', '.join(required_image_fields)}")
                    if image.get('transcoded_from') and original_media_class != media_class:
                        failures.append(f'place {place_id} image {image_index} changed media identity during transcoding')
        sight_count = sum((1 for place in places if isinstance(place, dict) and place.get('type') == 'sight'))
        souvenir_count = sum((1 for place in places if isinstance(place, dict) and place.get('type') == 'souvenir'))
        souvenir_names = [re.sub('\\s+', '', str(place.get('display_name', '')).lower()) for place in places if isinstance(place, dict) and place.get('type') == 'souvenir']
        if len(souvenir_names) != len(set(souvenir_names)):
            failures.append('souvenir inventory contains duplicate display names')
        cuisines = {str(place.get('cuisine', '')).strip() for place in places if isinstance(place, dict) and place.get('type') == 'restaurant' and str(place.get('cuisine', '')).strip()}
        sight_floor = 8
        if sight_count < sight_floor:
            failures.append(f'places requires at least {sight_floor} sights, including optional first-visit choices: {sight_count}/{sight_floor}')
        souvenir_floor = 1
        if souvenir_count < souvenir_floor:
            failures.append(f'places requires at least {souvenir_floor} souvenirs: {souvenir_count}/{souvenir_floor}')
        if len(cuisines) < 4:
            failures.append(f'restaurant inventory needs at least four distinct cuisine labels: {len(cuisines)}/4')
        experience_places = [place_by_id.get(str(item.get('place_id')), {}) for group in groups.get('experiences', []) if isinstance(group, dict) for item in group.get('items', []) if isinstance(item, dict)]
        if bathing_requested and str(data.get('country', '')).lower() in {'japan', '日本'}:
            bathing_count = sum((1 for place in experience_places if re.search('温泉|入浴|銭湯|onsen|sento', json.dumps(place, ensure_ascii=False), re.I)))
            bathing_floor = 2
            if bathing_count < bathing_floor:
                failures.append(f'A Japan trip explicitly requesting bathing/onsen in {quality_mode} mode needs {bathing_floor} actual venue records, not only a matching group title: {bathing_count}/{bathing_floor}')
        experience_type_counts: dict[str, int] = {}
        for place in experience_places:
            experience_type = str(place.get('experience_type', ''))
            if experience_type:
                experience_type_counts[experience_type] = experience_type_counts.get(experience_type, 0) + 1
        required_experience_types = 2 if experience_mode == 'constrained' else 3
        if len(experience_type_counts) < required_experience_types:
            failures.append(f'signature experiences need at least {required_experience_types} distinct truthful experience types; uneven group sizes are allowed')
        dedicated_ids = {str(item.get('place_id')) for item in food.get('dedicated_trip', []) if isinstance(item, dict) and item.get('place_id')}
        dedicated_cuisines = {str(place_by_id[place_id].get('cuisine', '')).strip() for place_id in dedicated_ids if place_id in place_by_id and str(place_by_id[place_id].get('cuisine', '')).strip()}
        if len(dedicated_cuisines) < 4:
            failures.append(f'food.dedicated_trip needs at least four distinct cuisine labels across its six or more restaurants: {len(dedicated_cuisines)}/4')
        scheduled_sights = {str(stop.get('place_id')) for day in itinerary if isinstance(day, dict) for stop in day.get('stops', []) if isinstance(stop, dict)}
        selected_sights = {str(place.get('id')) for place in places if isinstance(place, dict) and place.get('type') == 'sight'}
        minimum_scheduled = min(len(selected_sights), max(1, days))
        if len(selected_sights & scheduled_sights) < minimum_scheduled:
            failures.append(f'schedule at least one mainstream sight per trip day where available; remaining sights may be labeled optional: {len(selected_sights & scheduled_sights)}/{minimum_scheduled}')
        if not is_test_fixture:
            restaurant_pairs: dict[str, list[tuple[str, str]]] = {}
            restaurant_verified_counts: dict[str, int] = {}
            for place in places:
                if not isinstance(place, dict) or place.get('type') != 'restaurant':
                    continue
                for item in place.get('ratings', []):
                    if isinstance(item, dict) and item.get('status', 'verified') == 'verified':
                        platform = str(item.get('platform', '')).strip().lower()
                        restaurant_verified_counts[platform] = restaurant_verified_counts.get(platform, 0) + 1
                        restaurant_pairs.setdefault(platform, []).append((str(item.get('rating')), str(item.get('review_count'))))
            for platform, pairs in restaurant_pairs.items():
                if len(pairs) >= 6 and len(set(pairs)) == 1:
                    failures.append(f'restaurant {platform} ratings repeat one identical score/review pair across {len(pairs)} records; verify each venue instead of using fixture data')
            repeated: dict[str, list[str]] = {}
            narrative_keys = {'summary', 'description', 'note', 'why_buy', 'best_for', 'buying_tip', 'risk_assessment', 'lighting', 'portrait_tip'}

            def collect_text(value, path='profile', key_name=''):
                if isinstance(value, dict):
                    for key, item in value.items():
                        collect_text(item, f'{path}.{key}', key)
                elif isinstance(value, list):
                    for index, item in enumerate(value):
                        collect_text(item, f'{path}[{index}]', key_name)
                elif isinstance(value, str) and key_name in narrative_keys:
                    normalized = re.sub('[\\s\\W_]+', '', value).lower()
                    if len(normalized) >= 24:
                        repeated.setdefault(normalized, []).append(path)
            collect_text({'itinerary': itinerary, 'module_groups': groups, 'places': places})
            duplicated = [paths for paths in repeated.values() if len(paths) >= 3]
            if duplicated:
                sample = '; '.join((', '.join(paths[:3]) for paths in duplicated[:4]))
                failures.append('high repeated-copy contamination across content records: ' + sample)
        referenced_ids = set()
        for day in itinerary if isinstance(itinerary, list) else []:
            referenced_ids.update((str(stop.get('place_id')) for stop in day.get('stops', []) if isinstance(stop, dict) and stop.get('place_id')))
        for family in ('shopping', 'experiences'):
            for group in groups.get(family, []):
                referenced_ids.update((str(item.get('place_id')) for item in group.get('items', []) if isinstance(item, dict) and item.get('place_id')))
        for key in ('dedicated_trip', 'reliable_chains'):
            referenced_ids.update((str(item.get('place_id')) for item in food.get(key, []) if isinstance(item, dict) and item.get('place_id')))
        referenced_ids.update((str(stay.get('place_id')) for stay in stays if isinstance(stay, dict) and stay.get('status') == 'confirmed' and stay.get('place_id')))
        unknown = sorted(referenced_ids - set(place_by_id))
        if unknown:
            failures.append('unbound place IDs: ' + ', '.join(unknown))
    if not args.allow_test_fixture:
        failures.extend(content_failures(data))
    bindings = data.get('render_bindings_file')
    if not nonempty(bindings):
        failures.append('render_bindings_file is required for the official renderer')
    if failures:
        for failure in failures:
            print('FAIL ' + failure)
        return 2
    print('PASS destination dataset is complete enough to render into the canonical product frame')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
