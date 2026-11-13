"""Check authored destination relationships without scanning embedded media or CSS."""
import re


def text_fields(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in {'src', 'mobileSrc', 'image', 'url', 'page', 'query', 'sources', 'source_labels'}:
                yield from text_fields(child, f'{path}.{key}')
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from text_fields(child, f'{path}[{index}]')
    elif isinstance(value, str) and not value.startswith(('data:', 'http://', 'https://')):
        yield path, value


def day_number(value):
    if value.isdigit():
        return int(value)
    digits = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
              '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    if '十' in value:
        tens, ones = value.split('十', 1)
        return digits.get(tens, 1) * 10 + digits.get(ones, 0)
    return digits.get(value)


def english_number(value):
    words = ('ZERO ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE '
             'THIRTEEN FOURTEEN FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN').split()
    values = {word: number for number, word in enumerate(words)}
    values.update(TWENTY=20, THIRTY=30, FORTY=40, FIFTY=50, SIXTY=60,
                  SEVENTY=70, EIGHTY=80, NINETY=90)
    parts = value.upper().replace('-', ' ').split()
    if parts and all(part in values for part in parts):
        return sum(values[part] for part in parts)
    if value.isdigit():
        return int(value)
    return None


def audit_language_scenes(editorial, language=''):
    """Ensure scene navigation exposes every authored group and its English fallback."""
    if 'languageScenes' not in editorial:
        return []  # Existing workbooks retain their legacy group structure.
    errors, scene_ids = [], {}
    phrases, words = editorial['phrases'], editorial.get('words', {})
    collections = {
        'phrases': phrases,
        'glossary': {key: value for key, value in words.items() if key.startswith('常备 · ')},
        'replies': {key: value for key, value in words.items() if not key.startswith('常备 · ')},
    }
    covered = {kind: {} for kind in collections}
    for index, scene in enumerate(editorial['languageScenes']):
        path = f'languageScenes[{index}]'
        if scene['id'] in scene_ids:
            errors.append(f'{path}.id={scene["id"]!r}: duplicate of {scene_ids[scene["id"]]}; scene IDs must be unique')
        else:
            scene_ids[scene['id']] = path
        for kind, groups in collections.items():
            if kind not in scene:
                continue
            group = scene[kind]
            if group not in groups:
                errors.append(f'{path}.{kind}={group!r}: unknown {kind} group')
                continue
            if group in covered[kind]:
                errors.append(f'{path}.{kind}={group!r}: duplicate of {covered[kind][group]}; each language group belongs to one scene')
            else:
                covered[kind][group] = path
            if not groups[group]:
                errors.append(f'{path}.{kind}={group!r}: referenced group must not be empty')
            for row_index, row in enumerate(groups[group]):
                row_path = f'{"phrases" if kind == "phrases" else "words"}.{group}[{row_index}]'
                if language.lower().split('-')[0] != 'en' and (not isinstance(row, dict) or not row.get('english', '').strip()):
                    errors.append(f'{row_path}.english: languageScenes requires an explicit English expression')
                if language.lower().split('-')[0] != 'en' and isinstance(row, dict) and 'input' in row:
                    field = row['input']
                    if not field.get('englishLabel', '').strip():
                        errors.append(f'{row_path}.input.englishLabel: required for the separate English input')
                    for option_index, option in enumerate(field['options']):
                        if not option.get('english', '').strip():
                            errors.append(f'{row_path}.input.options[{option_index}].english: required for English presentation')
    for kind, groups in collections.items():
        for group in groups:
            if group not in covered[kind]:
                errors.append(f'languageScenes: {kind} group {group!r} is not assigned to a scene')
    return errors


def audit_relationships(guide, edition, editorial):
    from schema_check import audit_schema
    structural_errors = audit_schema(guide) + audit_schema(editorial, 'editorial-content', language=edition.get('lang',''))
    if structural_errors:
        return structural_errors
    errors = []
    if edition.get('readerReferenceVersion', 0) >= 2 and 'languageScenes' not in editorial:
        errors.append('languageScenes: required when edition.readerReferenceVersion>=2; provide scene links and English fallback')
    errors.extend(audit_language_scenes(editorial, edition.get('lang', '')))
    from editorial_evidence import audit_reader_reference_evidence
    errors.extend(audit_reader_reference_evidence(
        editorial, required=edition.get('readerReferenceVersion', 0) >= 1))
    for collection in ('places', 'areas'):
        seen = {}
        for index, item in enumerate(guide[collection]):
            if item['id'] in seen:
                errors.append(f'content.json.{collection}[{index}].id={item["id"]!r}: duplicate of {collection}[{seen[item["id"]]}].id; IDs must be unique')
            else:
                seen[item['id']] = index
    days = guide['days']
    places = {place['id'] for place in guide['places']}
    if not days:
        errors.append('days: itinerary is empty')
    if [day['id'] for day in days] != [f'd{i+1}' for i in range(len(days))]:
        errors.append('days: IDs must follow itinerary order d1, d2, ...')
    span = re.fullmatch(r'\s*([0-9零一二两三四五六七八九十]+)\s*[天日]\s*([0-9零一二两三四五六七八九十]+)\s*晚\s*', edition.get('span', ''))
    if span and (day_number(span[1]) != len(days) or day_number(span[2]) != len(days) - 1):
        errors.append('edition.span: day/night counts differ from itinerary')
    count = english_number(edition.get('daysEnglish', ''))
    if count is not None and count != len(days):
        errors.append('edition.daysEnglish: count differs from itinerary')
    for day in days:
        stop_ids = [stop[1] for stop in day['stops']]
        scheduled = set(day['schedules']['standard'])
        missing, extra = sorted(set(stop_ids) - scheduled), sorted(scheduled - set(stop_ids))
        if missing or extra:
            errors.append(f'{day["id"]}.schedules.standard must match stops exactly; missing={missing}, extra={extra}')
        if len(stop_ids) != len(set(stop_ids)):
            errors.append(f'{day["id"]}: duplicate route stop')
        for place_id in stop_ids + day.get('gentle', []) + day.get('rain', []):
            if place_id not in places:
                errors.append(f'{day["id"]}: unknown place {place_id}')
    for index, area in enumerate(guide['areas']):
        if not 0 <= area['day'] < len(days):
            errors.append(f'areas[{index}] (id={area["id"]}).day={area["day"]}: expected 0..{len(days)-1} (0-based; 0=第1天)')
        for place_id in area['ids']:
            if place_id not in places:
                errors.append(f'areas[{index}]: unknown place {place_id}')
    themes = editorial.get('route_experiences', [])
    if not isinstance(themes, list):
        errors.append('editorial-content.json.route_experiences: expected an array aligned with areas')
    else:
        if len(themes) != len(guide['areas']):
            errors.append(f'route_experiences: {len(themes)} entries for {len(guide["areas"])} areas; one entry per area in the same order')
        for index, (area, theme) in enumerate(zip(guide['areas'], themes)):
            if not isinstance(theme, dict):
                errors.append(f'route_experiences[{index}]: expected an object for area {area["id"]}')
                continue
            if theme.get('areaId', area['id']) != area['id']:
                errors.append(f'route_experiences[{index}].areaId={theme["areaId"]!r}: expected {area["id"]!r}; same order as areas')
            if theme.get('place') not in area['ids']:
                errors.append(f'route_experiences[{index}].place={theme.get("place")!r}: must belong to areas[{index}] ({area["id"]}).ids')
    restaurant_ids = {}
    place_by_id = {place['id']: place for place in guide['places']}
    for group_index, group in enumerate(editorial.get('restaurant_groups', [])):
        for item_index, item in enumerate(group['items']):
            path = f'restaurant_groups[{group_index}].items[{item_index}].id'
            if item['id'] not in places:
                errors.append(f'{path}: unknown restaurant {item["id"]}')
            elif place_by_id[item['id']].get('identityScope') == 'area':
                errors.append(f'{path}: {item["id"]} is an area, not a restaurant venue')
            if item['id'] in restaurant_ids:
                errors.append(f'{path}={item["id"]!r}: duplicate of {restaurant_ids[item["id"]]}; each restaurant belongs to one group only')
            else:
                restaurant_ids[item['id']] = path
    for day in days:
        for index, place_id in enumerate(day.get('dining', [])):
            path = f'{day["id"]}.dining[{index}]'
            if place_id not in places:
                errors.append(f'{path}: unknown place {place_id}')
            elif place_by_id[place_id].get('identityScope') == 'area':
                errors.append(f'{path}: {place_id} is an area, not a restaurant venue')
            if place_id not in restaurant_ids:
                errors.append(f'{path}: {place_id} must belong to restaurant_groups')
    task_ids = {}
    for group_index, group in enumerate(editorial.get('preparation', [])):
        for item_index, task in enumerate(group['items']):
            path = f'preparation[{group_index}].items[{item_index}].id'
            if task['id'] in task_ids:
                errors.append(f'{path}={task["id"]!r}: duplicate of {task_ids[task["id"]]}; task IDs must be unique')
            else:
                task_ids[task['id']] = path
    phrase_ids = {}
    phrase_by_id = {}
    for group_index, (group, phrases) in enumerate(editorial['phrases'].items()):
        for item_index, phrase in enumerate(phrases):
            # Legacy cards also have DOM/state identities; authored IDs may not collide.
            phrase_id = phrase['id'] if isinstance(phrase, dict) else f'phrase-{group_index}-{item_index}'
            path = f'phrases.{group}[{item_index}]'
            if phrase_id in phrase_ids:
                errors.append(f'{path}.id={phrase_id!r}: duplicate of {phrase_ids[phrase_id]}; phrase IDs must be unique')
            else:
                phrase_ids[phrase_id] = path
                phrase_by_id[phrase_id] = phrase
            if isinstance(phrase, dict) and 'input' in phrase:
                values = [option['value'] for option in phrase['input']['options']]
                if len(values) != len(set(values)):
                    errors.append(f'{path}.input.options: option values must be unique')
    for phrase_id, phrase in phrase_by_id.items():
        if not isinstance(phrase, dict) or 'subjectFrom' not in phrase:
            continue
        source_id = phrase['subjectFrom']
        path = phrase_ids[phrase_id] + '.subjectFrom'
        if source_id == phrase_id:
            errors.append(f'{path}: a phrase cannot reference itself')
        elif source_id not in phrase_by_id:
            errors.append(f'{path}={source_id!r}: unknown phrase ID')
        elif not isinstance(phrase_by_id[source_id], dict) or 'input' not in phrase_by_id[source_id]:
            errors.append(f'{path}={source_id!r}: source phrase must have an input')
    for place_id in edition.get('overviewIds', []):
        if place_id not in places:
            errors.append(f'overviewIds: unknown place {place_id}')
    # Inspect prose, excluding URLs, images and scripts. A data-URI can contain any word.
    for label, content in [('content', guide), ('edition', edition), ('editorial', editorial)]:
        for path, value in text_fields(content, label):
            matches = re.finditer(
                r'第\s*([0-9零一二两三四五六七八九十]+(?:\s*[或与和、至到–—-]\s*第?\s*[0-9零一二两三四五六七八九十]+)*)\s*天', value)
            for match in matches:
                numbers = re.findall(r'[0-9零一二两三四五六七八九十]+', match[1])
                if any(day_number(number) is not None and not 1 <= day_number(number) <= len(days)
                       for number in numbers):
                    errors.append(f'{path}: {match[0]} outside {len(days)}-day trip')
            for match in re.finditer(r'(?<![A-Za-z0-9])(?:DAY\s+|D)(\d+)(?![A-Za-z0-9])', value, re.I):
                if not 1 <= int(match[1]) <= len(days):
                    errors.append(f'{path}: {match[0]} outside {len(days)}-day trip')
    return errors
