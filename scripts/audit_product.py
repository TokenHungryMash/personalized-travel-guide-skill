"""Audit a generated travel handbook against the current production product."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from PIL import Image
REQUIRED_FILES = ('better-interface.css', 'desktop-rail.css', 'desktop-rail.js', 'guide-motion.js', 'gsap.min.js', 'handbook-enhancements.js', 'trip-mode.css', 'trip-mode.js', 'itinerary-customizer.css', 'itinerary-customizer.js', 'theme-switcher.css', 'theme-switcher.js', 'checklist-memory.js')
MODULE_IDS = ('route', 'sights', 'shops', 'move', 'food', 'booking', 'words', 'tips')
MODULE_LABELS = ('行程', '景点指南', '购物', '当地特色体验', '餐饮指南', '出发前准备', '语言随行锦囊', '旅游贴士')
MOBILE_MODULE_LABELS = ('行程', '景点指南', '购物', '当地特色体验', '餐饮指南', '出发前准备', '语言锦囊', '旅游贴士')
THEME_IDS = ('rainforest', 'coast', 'terracotta', 'ink', 'burgundy', 'midnight')
REFERENCE_DESTINATION_TERMS = ('Ubud', '乌布', 'Seminyak', '水明漾', 'Threads of Life', 'Bali Pulina', 'Hujan Locale', 'Sacred Monkey Forest', '圣猴森林', 'Tirta Empul', '圣泉寺', 'FINNS', 'Merah Putih', 'Mahandita', 'iSuite', 'BALI 2026', 'BALI ITINERARY', 'BALI SOUVENIRS', 'Yoga Barn', 'Red Gunpowder', 'Berawa', 'Nusa Penida', '佩妮达', 'Kelingking', 'Sanur Harbour', 'Singakerta', 'Kebun Bistro', 'Warung Mendez', 'Brunch Club', '向海而居', '住进林间', 'FOLLOW THE TIDE', 'INTO THE GREEN', 'Bali Belly', 'Canang Sari', 'Nyepi', 'Bank Indonesia')
RASTER_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}
LOCKED_RUNTIME_FILES = ('design-fix.css', 'desktop-rail.css', 'desktop-rail.js', 'guide-motion.js', 'handbook-enhancements.js', 'vocab-fix.css', 'trip-mode.css', 'itinerary-customizer.css', 'theme-switcher.css', 'theme-switcher.js', 'gsap.min.js')
DESTINATION_RUNTIME_FILES = ('trip-mode.js', 'itinerary-customizer.js', 'checklist-memory.js')

def normalize_quoted_literals(source: str) -> str:
    """Remove quoted literal payloads while retaining executable/CSS structure."""
    return re.sub('(["\\\'])(?:\\\\.|(?!\\1).)*\\1', lambda match: match.group(1) + '__LITERAL__' + match.group(1), source, flags=re.S)

def count(html: str, pattern: str) -> int:
    return len(re.findall(pattern, html, re.I | re.S))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--standard-fast', action='store_true', help='standard release audit: retain structure/provenance checks without publication-depth per-asset review')
    args = parser.parse_args()
    root = args.root.resolve()
    index = root / 'index.html'
    failures: list[str] = []
    warnings: list[str] = []
    if not index.exists():
        print(f'FAIL missing {index}')
        return 2
    html = index.read_text(encoding='utf-8')
    if (root / 'ADAPTATION_REQUIRED.json').exists():
        failures.append('unfinished adaptation workbench: CONTINUE editing; remove ADAPTATION_REQUIRED.json only after complete destination replacement and QA')
    profile_path = root / 'destination-profile.json'
    profile = {}
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding='utf-8'))
        except Exception as exc:
            failures.append(f'invalid destination-profile.json: {exc}')
    declared_destination = str(profile.get('destination', '')).strip()
    display_name = str(profile.get('display_name', '')).strip()
    current_system = profile.get('ui_system', 'current-system') == 'current-system'
    from _route_screenshots import verify_captures
    failures.extend(verify_captures(root, profile))
    required_files = REQUIRED_FILES
    if current_system:
        from _current_system_adapter import ROOT as current_root, runtime_bindings
        required_files = tuple((p.name for p in current_root.iterdir() if p.suffix in {'.js', '.css'} and p.name in html))
        try:
            expected_runtime = {r['path']: r['content'] for r in runtime_bindings(profile)}
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f'incomplete current-system profile: {exc}')
            expected_runtime = {}
        map_runtime = expected_runtime.get('trip-route-maps.js', '')
        for ref in sorted(set(re.findall('media/routes/day-\\d+\\.svg', map_runtime))):
            map_path = root / ref
            if not map_path.is_file():
                failures.append(f'missing generated route map: {ref}')
            else:
                map_source = map_path.read_text(encoding='utf-8')
                if 'data:image/png;base64,' not in map_source or 'OpenStreetMap' not in map_source:
                    failures.append(f'route map lacks embedded basemap/attribution: {ref}')
        for name, content in expected_runtime.items():
            candidate = root / name
            if not candidate.is_file() or candidate.read_text(encoding='utf-8') != content:
                failures.append(f'current-system profile/runtime binding mismatch: {name}')
        for p in current_root.iterdir():
            if p.suffix in {'.js', '.css'} and p.name not in expected_runtime:
                q = root / p.name
                if not q.is_file() or q.read_bytes() != p.read_bytes():
                    failures.append(f'current-system locked dependency mismatch: {p.name}')
    is_canonical_bali = 'bali' in declared_destination.lower() or '巴厘岛' in declared_destination if declared_destination else '巴厘岛' in html or 'BALI' in html[:20000]
    if not is_canonical_bali and (not declared_destination):
        failures.append('non-Bali export requires destination-profile.json with a destination')
    if not is_canonical_bali:
        if not display_name or display_name == 'REPLACE_ME':
            failures.append('non-Bali export requires a real display_name')
        title_text = ' '.join(re.findall('<(?:h1|title)\\b[^>]*>(.*?)</(?:h1|title)>', html, re.I | re.S))
        title_text = re.sub('<[^>]+>', ' ', title_text)
        aliases = [display_name] + [str(value) for value in profile.get('aliases', []) if value]
        if aliases and (not any((alias.casefold() in title_text.casefold() for alias in aliases))):
            failures.append('cover/document title does not identify the declared destination')
        transport = profile.get('transport', {}) if isinstance(profile, dict) else {}
        transport_status = str(transport.get('status', 'pending')).strip().lower() if isinstance(transport, dict) else 'pending'
        flight_band_match = re.search('<section\\b[^>]*class=["\\\'][^"\\\']*\\bflight-band\\b[^"\\\']*["\\\'][^>]*>(.*?)</section>', html, re.I | re.S)
        flight_source = flight_band_match.group(1) if flight_band_match else ''
        flight_cards = count(flight_source, 'class=["\\\'][^"\\\']*\\bflight-card\\b')
        if transport_status not in {'confirmed', 'pending'}:
            failures.append('destination-profile transport.status must be confirmed or pending')
        if transport_status == 'pending':
            if flight_cards != 2:
                failures.append(f'pending transport must render exactly outbound + return cards: {flight_cards}/2')
            if not re.search('去程[^<]{0,20}待确认|待确认[^<]{0,20}去程', flight_source) or not re.search('回程[^<]{0,20}待确认|待确认[^<]{0,20}回程', flight_source):
                failures.append('pending transport cards must explicitly identify outbound and return as 待确认')
            concrete_time = re.search('\\b(?:[01]?\\d|2[0-3]):[0-5]\\d\\b', flight_source)
            inherited_detail = re.search('(?:转机约|飞行约|从.{0,20}酒店出发|\\bT[1-9]\\b|国际机场|Airport)', flight_source, re.I)
            if concrete_time or inherited_detail:
                failures.append('pending transport contains invented/reference times, terminals, airports, transfer duration or hotel-departure advice')
        else:
            legs = transport.get('legs', []) if isinstance(transport, dict) else []
            if not isinstance(legs, list) or not legs:
                failures.append('confirmed transport requires a non-empty transport.legs dataset')
            elif flight_cards != len(legs):
                failures.append(f'transport card count does not match confirmed legs: cards={flight_cards}, legs={len(legs)}')
    profile_places = profile.get('places', []) if isinstance(profile, dict) else []
    if not is_canonical_bali:
        if not isinstance(profile_places, list) or not profile_places:
            failures.append('non-Bali export requires a populated destination-profile places dataset')
        else:
            place_ids = [str(place.get('id', '')).strip() for place in profile_places if isinstance(place, dict)]
            if any((not place_id for place_id in place_ids)) or len(place_ids) != len(set(place_ids)):
                failures.append('destination-profile place IDs must be present and unique')
            incomplete_places = [place for place in profile_places if not isinstance(place, dict) or not place.get('type') or (not place.get('display_name')) or (not place.get('map_query')) or (not place.get('source_url'))]
            if incomplete_places:
                failures.append(f'destination-profile has incomplete place records: {len(incomplete_places)}')
    css_text = '\n'.join((path.read_text(encoding='utf-8', errors='ignore') for path in root.glob('*.css')))
    canonical_root = Path(__file__).resolve().parent.parent / 'assets' / ('current-system' if current_system else 'canonical') / 'product'
    if not is_canonical_bali:
        render_report_path = root / 'RENDER_REPORT.json'
        if not render_report_path.exists():
            failures.append('missing RENDER_REPORT.json: final index.html must be produced by render_destination.py')
        else:
            try:
                render_report = json.loads(render_report_path.read_text(encoding='utf-8'))
                if render_report.get('render_method') != 'official_renderer':
                    failures.append('render provenance is not official_renderer')
                if render_report.get('canonical_template_hash_verified') is not True:
                    failures.append('canonical template hash was not verified by the renderer')
                if render_report.get('custom_page_builder_detected') is not False:
                    failures.append('custom page builder detected')
                if render_report.get('rendered_index_sha256') != hashlib.sha256(index.read_bytes()).hexdigest():
                    failures.append('index.html changed after the official renderer completed')
            except Exception as exc:
                failures.append(f'invalid RENDER_REPORT.json: {exc}')
        canonical_size = (canonical_root / 'index.html').stat().st_size
        if index.stat().st_size < canonical_size * 0.35:
            failures.append(f'index.html is abnormally small for the canonical product: {index.stat().st_size} bytes vs {canonical_size} reference bytes')
        allowed_css = {path.name for path in canonical_root.glob('*.css')}
        extra_css = sorted((path.name for path in root.glob('*.css') if path.name not in allowed_css))
        if extra_css:
            failures.append('unregistered destination-specific CSS files are forbidden: ' + ', '.join(extra_css))
        canonical_html = (canonical_root / 'index.html').read_text(encoding='utf-8', errors='ignore')
        candidate_inline_styles = [re.sub('\\r\\n?', '\n', block).strip() for block in re.findall('<style\\b[^>]*>(.*?)</style>', html, re.I | re.S)]
        canonical_inline_styles = [re.sub('\\r\\n?', '\n', block).strip() for block in re.findall('<style\\b[^>]*>(.*?)</style>', canonical_html, re.I | re.S)]
        if candidate_inline_styles != canonical_inline_styles:
            failures.append('embedded layout CSS differs from the canonical Bali product; use semantic theme tokens instead of component overrides')

        def loaded_assets(source: str, tag: str, attribute: str) -> list[str]:
            pattern = f"""<{tag}\\b[^>]*\\b{attribute}=["\\']([^"\\']+)["\\']"""
            return [Path(value.split('?', 1)[0]).name for value in re.findall(pattern, source, re.I)]
        candidate_css_order = loaded_assets(html, 'link', 'href')
        canonical_css_order = loaded_assets(canonical_html, 'link', 'href')
        candidate_js_order = loaded_assets(html, 'script', 'src')
        canonical_js_order = loaded_assets(canonical_html, 'script', 'src')
        if candidate_css_order != canonical_css_order:
            failures.append(f'stylesheet load list/order differs from canonical product: candidate={candidate_css_order}, canonical={canonical_css_order}')
        if candidate_js_order != canonical_js_order:
            failures.append(f'script load list/order differs from canonical product: candidate={candidate_js_order}, canonical={canonical_js_order}')
        candidate_interface = root / 'better-interface.css'
        canonical_interface = canonical_root / 'better-interface.css'
        if candidate_interface.exists() and canonical_interface.exists():
            candidate_shape = normalize_quoted_literals(candidate_interface.read_text(encoding='utf-8', errors='ignore'))
            canonical_shape = normalize_quoted_literals(canonical_interface.read_text(encoding='utf-8', errors='ignore'))
            if candidate_shape != canonical_shape:
                failures.append('better-interface.css changed selectors/declarations; only quoted destination text and cover URL may differ')
        for filename in () if current_system else LOCKED_RUNTIME_FILES:
            candidate_runtime = root / filename
            canonical_runtime = canonical_root / filename
            if candidate_runtime.exists() and canonical_runtime.exists():
                if hashlib.sha256(candidate_runtime.read_bytes()).digest() != hashlib.sha256(canonical_runtime.read_bytes()).digest():
                    failures.append(f'locked component runtime was modified instead of adapted through data/tokens: {filename}')
        destination_runtime_contract = {'trip-mode.js': ('trip-mode-overlay', 'trip-mode-panel', 'trip-stop', 'trip-stop-actions', 'TRIP_MODE_DATA', 'trip-day-map', 'trip-time-guard', 'data-trip-provider'), 'itinerary-customizer.js': ('itinerary-customizer__panel', 'custom-timeline', 'data-restore', 'data-copy'), 'checklist-memory.js': ('localStorage', 'input[type="checkbox"]')}
        if current_system:
            destination_runtime_contract = {'trip-mode.js': ('trip-mode-overlay', 'trip-mode-panel', 'TRIP_MODE_DATA', 'data-trip-provider', 'data-trip-page'), 'travel-utilities.js': ('createSharedLedger', 'trip-page-expense', 'speechSynthesis', 'reservation-check'), 'shared-ledger.js': ('avatar', 'participants'), 'local-ledger.js': ('localStorage',), 'itinerary-customizer.js': ('BaliCustomizer',)}
        for filename, tokens in destination_runtime_contract.items():
            runtime_path = root / filename
            if runtime_path.exists():
                runtime_text = runtime_path.read_text(encoding='utf-8', errors='ignore')
                missing_tokens = [token for token in tokens if token not in runtime_text]
                if missing_tokens:
                    failures.append(f"destination runtime changed canonical product behavior: {filename}: {', '.join(missing_tokens)}")
    for filename in required_files:
        path = root / filename
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f'missing runtime asset: {filename}')
        if filename not in html and filename != 'itinerary-customizer.css':
            failures.append(f'index.html does not load: {filename}')
    cover_contract = ('hero jungle-cover', 'jungle-cover-image', 'jungle-cover-shade', 'jungle-cover-copy', 'jungle-cover-kicker', 'class="lede"', 'jungle-cover-bottom')
    missing_cover = [token for token in cover_contract if token not in html]
    if missing_cover:
        failures.append('cover does not preserve canonical composition: ' + ', '.join(missing_cover))
    cover_start = html.find('class="hero jungle-cover')
    cover_end = html.find('</header>', cover_start) if cover_start >= 0 else -1
    cover_source = html[cover_start:cover_end] if cover_start >= 0 and cover_end > cover_start else ''
    if cover_source and (not all((token in cover_source for token in ('jungle-cover-copy', 'jungle-cover-bottom')))):
        failures.append('cover copy/bottom metadata must remain inside the full-viewport image header')
    positions = []
    for module_id in MODULE_IDS:
        match = re.search(f"""\\bid=["\\']{module_id}["\\']""", html)
        if not match:
            failures.append(f'missing module #{module_id}')
        else:
            positions.append(match.start())
    if not re.search('\\bid=["\\\']stay["\\\']', html):
        failures.append('missing unnumbered exact-property stay disclosure')
    canonical_dom = ('stay',) + MODULE_IDS
    dom_positions = [html.find(f'id="{module_id}"') for module_id in canonical_dom]
    if any((position < 0 for position in dom_positions)) or dom_positions != sorted(dom_positions):
        failures.append('source DOM does not use stay > 01–08 canonical order')
    contents = re.search('\\bid=["\\\']contents["\\\']', html)
    if not contents or (positions and contents.start() > positions[0]):
        failures.append('standalone contents must appear before module 01')
    nav_source = html
    rail = root / 'desktop-rail.js'
    if rail.exists():
        nav_source += rail.read_text(encoding='utf-8', errors='ignore')
    contents_links = set(re.findall('(?:href=["\\\']#|\\[["\\\'])(stay|route|sights|shops|move|food|booking|words|tips)', nav_source))
    logical_links = {'route' if item == 'stay' else item for item in contents_links}
    if len(logical_links) < 8:
        failures.append(f'contents/navigation module links incomplete: {len(logical_links)}/8')
    contents_start = html.find('id="contents"')
    contents_end_candidates = [position for position in (html.find('id="stay"', contents_start), html.find('id="route"', contents_start)) if position > contents_start]
    contents_source = html[contents_start:min(contents_end_candidates)] if contents_start >= 0 and contents_end_candidates else ''
    html_nav_order = []
    for match in re.finditer('href=["\\\']#(stay|route|sights|shops|move|food|booking|words|tips)["\\\']', contents_source, re.I):
        module = match.group(1).lower()
        if module == 'stay':
            module = 'route'
        if module not in html_nav_order:
            html_nav_order.append(module)
    if tuple(html_nav_order[:8]) != MODULE_IDS:
        failures.append('HTML contents/navigation does not use exact 01–08 canonical order')
    contents_entries = {}
    for module_id in MODULE_IDS:
        href_pattern = '(?:stay|route)' if module_id == 'route' else re.escape(module_id)
        match = re.search(f"""<a\\b[^>]*href=["\\']#{href_pattern}["\\'][^>]*>\\s*<span[^>]*>\\s*\\d{{2}}\\s*</span>\\s*<b[^>]*>(.*?)</b>""", contents_source, re.I | re.S)
        contents_entries[module_id] = re.sub('<[^>]+>', '', match.group(1)).strip() if match else None
    wrong_contents_labels = [f'{module_id}={contents_entries.get(module_id)!r}' for module_id, expected in zip(MODULE_IDS, MODULE_LABELS) if contents_entries.get(module_id) != expected]
    if wrong_contents_labels:
        failures.append('contents uses shortened/noncanonical labels: ' + ', '.join(wrong_contents_labels))
    mobile_panel = re.search('<nav\\b[^>]*class=["\\\'][^"\\\']*\\bmobile-menu-panel\\b[^>]*>(.*?)</nav>', html, re.I | re.S)
    mobile_source = mobile_panel.group(1) if mobile_panel else ''
    mobile_entries = {}
    for module_id in MODULE_IDS:
        match = re.search(f"""<a\\b[^>]*href=["\\']#{module_id}["\\'][^>]*>\\s*<b[^>]*>\\s*\\d{{2}}\\s*</b>\\s*<span[^>]*>(.*?)</span>""", mobile_source, re.I | re.S)
        mobile_entries[module_id] = re.sub('<[^>]+>', '', match.group(1)).strip() if match else None
    wrong_mobile_labels = [f'{module_id}={mobile_entries.get(module_id)!r}' for module_id, expected in zip(MODULE_IDS, MOBILE_MODULE_LABELS) if mobile_entries.get(module_id) != expected]
    if wrong_mobile_labels:
        failures.append('mobile directory uses shortened/noncanonical labels: ' + ', '.join(wrong_mobile_labels))
    if rail.exists():
        rail_text = rail.read_text(encoding='utf-8', errors='ignore')
        expected_order = "['route','行程'],['sights','景点指南'],['shops','购物'],['move','当地特色体验'],['food','餐饮指南'],['booking','出发前准备'],['words','语言随行锦囊'],['tips','旅游贴士']"
        if expected_order not in rail_text:
            failures.append('desktop chapter rail does not use the canonical 01–08 order')
        if not is_canonical_bali and re.search('(?:panel\\.innerHTML|BALI SOUVENIRS|Threads of Life)', rail_text, re.I):
            failures.append('shared navigation runtime contains destination-specific fallback content')
    if not is_canonical_bali:
        body_tag = re.search('<body\\b[^>]*>', html, re.I)
        if not body_tag or not re.search('\\bdata-handbook-destination(?:-short)?=', body_tag.group(0), re.I):
            failures.append('non-Bali export must declare its navigation destination on <body>')
    days = count(html, '<details\\s+class=["\\\'][^"\\\']*\\bday(?=\\s|["\\\'])')
    routes = count(html, 'class=["\\\'][^"\\\']*\\bday-route-map\\b')
    stops = count(html, 'class=["\\\']route-stop["\\\']')
    print(f'itinerary days={days}, Mini Routes={routes}, stops={stops}')
    if days == 0 or routes != days:
        failures.append(f'one Mini Route is required per day: days={days}, routes={routes}')
    if stops < max(2, days * 2):
        failures.append('itinerary stop density is too low')
    day_component_counts = {'day-index': count(html, 'class=["\\\'][^"\\\']*\\bday-index\\b'), 'day-detail': count(html, 'class=["\\\'][^"\\\']*\\bday-detail\\b'), 'route-mobile-summary': count(html, 'class=["\\\'][^"\\\']*\\broute-mobile-summary\\b'), 'route-title': count(html, 'class=["\\\'][^"\\\']*\\broute-title\\b'), 'route-glass-button': count(html, 'class=["\\\'][^"\\\']*\\broute-glass-button\\b'), 'route-map-content': count(html, 'class=["\\\'][^"\\\']*\\broute-map-content\\b'), 'route-map-head': count(html, 'class=["\\\'][^"\\\']*\\broute-map-head\\b'), 'route-map-track': count(html, 'class=["\\\'][^"\\\']*\\broute-map-track\\b')}
    incomplete_day_components = [f'{name}={value}/{days}' for name, value in day_component_counts.items() if value < days]
    if incomplete_day_components:
        failures.append('itinerary does not preserve canonical Bali day/Mini Route components: ' + ', '.join(incomplete_day_components))
    period_total = 0
    for period in ('上午', '下午', '晚上'):
        period_count = count(html, f'<strong[^>]*>\\s*{period}\\s*</strong>')
        period_total += period_count
        if period_count < max(1, days - 1):
            failures.append(f'itinerary {period} rows are too sparse: {period_count}/{max(1, days - 1)}')
    if period_total < max(3, days * 3 - 2):
        failures.append(f'itinerary morning/afternoon/evening density is too low: {period_total}/{max(3, days * 3 - 2)}')
    stays_data = profile.get('stays', []) if isinstance(profile, dict) else []
    pending_stays = [stay for stay in stays_data if isinstance(stay, dict) and stay.get('status') == 'pending']
    confirmed_stays = [stay for stay in stays_data if isinstance(stay, dict) and stay.get('status') == 'confirmed']
    hotels = count(html, 'class=["\\\'][^"\\\']*\\bhotel-card\\b')
    galleries = count(html, 'class=["\\\'][^"\\\']*\\bgallery-wrap\\b')
    images = count(html, '<img\\b')
    if not is_canonical_bali and pending_stays and (not confirmed_stays):
        if not re.search('class=["\\\'][^"\\\']*\\bhotel-card\\b[^"\\\']*\\bstay-pending\\b', html, re.I):
            failures.append('pending stay must render a canonical-shaped .hotel-card.stay-pending placeholder')
        stay_start = html.find('id="stay"')
        stay_end = html.find('id="route"', stay_start)
        stay_source = html[stay_start:stay_end] if stay_end > stay_start >= 0 else ''
        if re.search('<img\\b|https?://', stay_source, re.I):
            failures.append('pending stay placeholder must not invent property images or booking/map links')
    elif hotels == 0 or galleries < hotels:
        failures.append(f'hotel/gallery coverage incomplete: hotels={hotels}, galleries={galleries}')
    disclosure_summaries = count(html, '<details\\b[^>]*>\\s*<summary\\b')
    disclosure_buttons = count(html, '<summary\\b[^>]*>[\\s\\S]*?<i\\b[^>]*>\\s*[＋+−-]\\s*</i>')
    if disclosure_summaries < 8 or disclosure_buttons < 8:
        failures.append(f'fold/disclosure controls incomplete: summaries={disclosure_summaries}, visible controls={disclosure_buttons}')
    hotel_blocks = re.findall('<article\\s+class=["\\\'][^"\\\']*\\bhotel-card\\b[^"\\\']*["\\\'][^>]*>.*?</article>', html, re.I | re.S)
    for number, block in enumerate(hotel_blocks, 1):
        if 'stay-pending' in block:
            continue
        image_count = count(block, '<img\\b')
        if image_count < 2:
            failures.append(f'hotel {number} must have at least 2 exact-property images: {image_count}/2')
        if not all((token in block for token in ('gallery-arrow prev', 'gallery-arrow next', 'gallery-count'))):
            failures.append(f'hotel {number} gallery controls/count are incomplete')
    n = max(4, days)
    experience_mode = str(profile.get('trip', {}).get('experience_mode', 'standard')).strip().lower() if isinstance(profile.get('trip'), dict) else 'standard'
    experience_floor = 4 if experience_mode == 'constrained' else 6
    experience_group_floor = 2 if experience_mode == 'constrained' else 3
    sights = count(html, 'class=["\\\'][^"\\\']*\\bsight-card\\b')
    shops = count(html, '(?:class=["\\\'][^"\\\']*\\bshop-row\\b|\\bdata-shopping-card\\b)')
    experiences = count(html, '(?:\\bdata-experience-card\\b|class=["\\\'][^"\\\']*\\b(?:movement-card|spa-card)\\b)')
    experience_groups = count(html, 'class=["\\\'][^"\\\']*\\b(?:experience-category|movement-section)\\b')
    souvenir_sections = count(html, '\\bdata-souvenir-list\\b')
    food_chapters = len([tag for tag in re.findall('<details\\b[^>]*class=["\\\'][^"\\\']*\\bfood-chapter\\b[^"\\\']*["\\\'][^>]*>', html, re.I) if 'menu-primer' not in tag and 'local-snacks' not in tag])
    restaurants = count(html, 'class=["\\\'][^"\\\']*\\brestaurant\\b')
    if sights < n:
        failures.append(f'sight library below day-scaled floor: {sights}/{n}')
    sights_start = html.find('id="sights"')
    sights_end = html.find('id="shops"', sights_start) if sights_start >= 0 else -1
    sights_source = html[sights_start:sights_end] if sights_end > sights_start >= 0 else ''
    if not re.search('<details\\b[^>]*class=["\\\'][^"\\\']*\\bmobile-section-fold\\b[^>]*>\\s*<summary\\b', sights_source, re.I | re.S):
        failures.append('sights must retain the canonical mobile-section-fold disclosure shell')
    if shops < n:
        (warnings if is_canonical_bali else failures).append(f'shopping library below day-scaled floor: {shops}/{n}')
    if experiences < experience_floor:
        (warnings if is_canonical_bali else failures).append(f'signature-experience library below compact floor: {experiences}/{experience_floor}')
    if experience_groups < experience_group_floor:
        (warnings if is_canonical_bali else failures).append(f'experience chapter needs at least {experience_group_floor} type-based disclosure groups: {experience_groups}/{experience_group_floor}')
    if souvenir_sections < 1:
        (warnings if is_canonical_bali else failures).append('shopping module requires an souvenir/must-buy subsection')
    if not is_canonical_bali:
        for family, pattern, child_pattern in (('shopping', '<details\\b[^>]*class=["\\\'][^"\\\']*\\bshop-region\\b[^"\\\']*["\\\'][^>]*>(.*?)</details>', '\\bshop-row\\b|\\bdata-shopping-card\\b'), ('experience', '<details\\b[^>]*class=["\\\'][^"\\\']*\\b(?:experience-category|movement-section)\\b[^"\\\']*["\\\'][^>]*>(.*?)</details>', '\\bmovement-card\\b|\\bspa-card\\b|\\bexperience-card\\b'), ('food', '<details\\b(?=[^>]*class=["\\\'][^"\\\']*\\bfood-chapter\\b)(?![^>]*class=["\\\'][^"\\\']*\\b(?:menu-primer|local-snacks)\\b)[^>]*>(.*?)</details>', '\\brestaurant\\b')):
            for number, block in enumerate(re.findall(pattern, html, re.I | re.S), 1):
                if not re.search(child_pattern, block, re.I):
                    failures.append(f'empty {family} disclosure {number}: inherited heading/filter has no destination records')
    sight_blocks = re.findall('<article\\s+class=["\\\'][^"\\\']*\\bsight-card\\b[^"\\\']*["\\\'][^>]*>(.*?)</article>', html, re.I | re.S)
    sight_profile = [place for place in profile.get('places', []) if isinstance(place, dict) and place.get('type') == 'sight']
    for number, block in enumerate(sight_blocks, 1):
        gallery_featured = number <= len(sight_profile) and sight_profile[number - 1].get('gallery_featured') is True
        requirements = {'two distinct gallery images' if gallery_featured else 'one exact-place image': count(block, '<img\\b') >= (2 if gallery_featured else 1), 'sliding gallery track': 'photo-strip' in block, 'gallery previous/next controls': all((token in block for token in ('gallery-arrow prev', 'gallery-arrow next'))) if gallery_featured else True, 'live gallery count': 'gallery-count' in block if gallery_featured else True, 'scheduled/optional marker': bool(re.search('(?:第\\s*\\d+\\s*天|已排入|可选|备选|自由替换)', block)), 'suggested duration': 'sight-facts' in block or bool(re.search('(?:建议停留|停留).*?分钟', block)), 'hours/closure': 'hours-line' in block and bool(re.search('(?:开放|营业|休馆|周休|闭馆)', block)), 'Google Maps action': 'Google Maps' in block}
        missing = [label for label, passed in requirements.items() if not passed]
        if missing:
            message = f"sight {number} metadata/gallery incomplete: {', '.join(missing)}"
            (warnings if is_canonical_bali and missing == ['two distinct gallery images'] else failures).append(message)
        if not is_canonical_bali and (not re.search(r'<a\b[^>]*href=["\']https?://[^"\']+["\'][^>]*>\s*(?:官网|来源|official|source)', block, re.I)):
            failures.append(f'sight {number} is missing an official/source action')
        if re.search('Tabelog|食べログ', block, re.I):
            failures.append(f'sight {number} must not display restaurant-platform ratings')
        has_score = bool(re.search('\\b[1-5]\\.\\d\\b', block))
        has_reviews = bool(re.search('(?:约\\s*)?[\\d,.]+\\s*(?:条|则|reviews?)', block, re.I))
        if has_reviews and (not has_score):
            failures.append(f'sight {number} review count cannot appear without a verified score')
    snack_cards = count(html, 'class=["\\\'][^"\\\']*\\bsnack-card\\b')
    has_dedicated_heading = '值得专程去' in html
    has_chain_heading = '本地连锁安心选' in html
    if food_chapters < 2 or restaurants < 8:
        failures.append(f'food depth below required structure: chapters={food_chapters}/2, restaurant cards={restaurants}/8')
    if snack_cards != 4:
        failures.append(f'food requires exactly four local snack cards: {snack_cards}/4')
    if not has_dedicated_heading or not has_chain_heading:
        failures.append('food must retain separate worth-a-special-trip and dependable local-chain sections')
    if re.search('(?:酒店|住宿).{0,8}(?:附近|周边).{0,8}餐厅|外卖.{0,8}(?:餐厅|推荐)', html, re.I):
        failures.append('food must not restore hotel-proximity or delivery restaurant modules')
    restaurant_blocks = re.findall('<article\\b(?=[^>]*class=["\\\'][^"\\\']*\\brestaurant\\b)[^>]*>(.*?)</article>', html, re.I | re.S)
    for number, block in enumerate(restaurant_blocks, 1):
        if not re.search('<img\\b[^>]+src=["\\\'][^"\\\']+["\\\']', block, re.I):
            failures.append(f'restaurant {number} must render one local image')
    checks = count(html, '<input[^>]+type=["\\\']checkbox["\\\']')
    current_reservations = re.findall('<article\\b[^>]*class="audit-reservation"[^>]*>.*?</article>', html, re.S) if current_system else []
    valid_current_reservations = [row for row in current_reservations if re.search('<h4>[^<]+</h4>', row) and 'data-reservation-id=' in row and ('reservation-notes' in row)]
    checks += len(valid_current_reservations)
    vocab = count(html, '<details\\s+class=["\\\'][^"\\\']*\\bvocab\\b')
    phrases = count(html, '<details\\s+class=["\\\'][^"\\\']*\\bphrase-group\\b')
    tips = count(html, '<details\\s+class=["\\\'][^"\\\']*\\btips-page\\b')
    print(f'depth checks={checks}, vocabulary={vocab}, phrases={phrases}, local-notes={tips}')
    checklist_floor = max(24, days * 3)
    if checks < checklist_floor:
        failures.append(f'before-departure checklist below floor: {checks}/{checklist_floor}')
    booking_match = re.search('<section\\b[^>]*id=["\\\']booking["\\\'][^>]*>(.*?)</section>', html, re.I | re.S)
    booking_source = booking_match.group(1) if booking_match else ''
    visible_checks = re.findall('<label>\\s*<input[^>]+type=["\\\']checkbox["\\\'][^>]*>\\s*<span>[^<]*</span>\\s*<div>\\s*<b>\\s*[^<\\s][^<]*</b>.*?</div>\\s*</label>', booking_source, re.I | re.S)
    visible_checks += valid_current_reservations
    if len(visible_checks) < checklist_floor:
        failures.append(f'before-departure checklist items must render visible titles: {len(visible_checks)}/{checklist_floor}')
    if vocab < 5 or phrases < 5:
        failures.append(f'language groups below floor: vocabulary={vocab}/5, phrases={phrases}/5')
    tip_blocks = re.findall('<details\\b[^>]*class=["\\\'][^"\\\']*\\btips-page\\b[^>]*>(.*?)</details>', html, re.I | re.S)
    if len(tip_blocks) != 5:
        failures.append(f'travel notes need exactly five rendered folds: {len(tip_blocks)}/5')
    for group_number, block in enumerate(tip_blocks, 1):
        topics = re.findall('<div\\b[^>]*>\\s*<h4>(.*?)</h4>\\s*<p>(.*?)</p>\\s*</div>', block, re.I | re.S)
        if len(topics) != 4:
            failures.append(f'travel notes fold {group_number} needs exactly four rendered topics: {len(topics)}/4')
        for topic_number, (raw_title, raw_note) in enumerate(topics, 1):
            title = re.sub('<[^>]+>', '', raw_title).strip()
            note = re.sub('<[^>]+>', '', raw_note).strip()
            if re.fullmatch('(?:提示|贴士|注意事项?|建议|.{2,10})\\s*[0-9一二三四五六七八九十]+', title):
                failures.append(f'travel notes fold {group_number} topic {topic_number} has a mechanical numbered heading: {title}')
            if len(re.sub('\\s+', '', title)) < 4 or len(re.sub('\\s+', '', note)) < 34 or len(re.findall('[。！？!?；;]', note)) < 2:
                failures.append(f'travel notes fold {group_number} topic {topic_number} is editorially thin')
    vocab_item_rows = sum((count(block, '<div\\b') for block in re.findall('<details\\s+class=["\\\'][^"\\\']*\\bvocab\\b[^>]*>(.*?)</details>', html, re.I | re.S)))
    phrase_item_rows = sum((count(block, '<div\\b') for block in re.findall('<details\\s+class=["\\\'][^"\\\']*\\bphrase-group\\b[^>]*>(.*?)</details>', html, re.I | re.S)))
    if vocab_item_rows < 25:
        failures.append(f'language keyword entries below floor: {vocab_item_rows}/25')
    if phrase_item_rows < 25:
        failures.append(f'language phrase entries below floor: {phrase_item_rows}/25')
    for label, pattern in (('keyword', '<details\\s+class=["\\\'][^"\\\']*\\bvocab\\b[^>]*>(.*?)</details>'), ('phrase', '<details\\s+class=["\\\'][^"\\\']*\\bphrase-group\\b[^>]*>(.*?)</details>')):
        for number, block in enumerate(re.findall(pattern, html, re.I | re.S), 1):
            if count(block, '<div\\b') < 5:
                failures.append(f'language {label} group {number} has fewer than 5 entries')
    if tips < 5:
        failures.append(f'local-note folds below floor: {tips}/5')
    tip_topics = count(html, '<div\\b[^>]*>\\s*<h4>')
    tip_floor = 20
    if tip_topics < tip_floor:
        failures.append(f'destination-specific travel-note topics below floor: {tip_topics}/{tip_floor}')
    runtime_contract = {'Trip Mode': ('TRIP MODE', 'TRIP_MODE_DATA', 'trip-day-map', 'trip-time-guard', 'data-trip-provider', 'trip-mode-dock'), 'Adjust Itinerary': ('调整行程', '复制文字申请', 'syncTheme'), 'theme picker': ('handbook-theme-launch',) + THEME_IDS}
    if current_system:
        runtime_contract = {'Trip Mode': ('TRIP_MODE_DATA', 'trip-mode-panel', 'data-trip-provider', 'data-trip-page'), 'Adjust Itinerary': ('调整行程', '复制文字申请', 'syncTheme'), 'Travel utilities': ('travel-info-fold', 'reservation-check', 'speechSynthesis', 'createSharedLedger')}
    joined_runtime = html
    for filename in ('trip-mode.js', 'itinerary-customizer.js', 'theme-switcher.js', 'handbook-enhancements.js', 'travel-utilities.js'):
        path = root / filename
        if path.exists():
            joined_runtime += path.read_text(encoding='utf-8', errors='ignore')
    for label, tokens in runtime_contract.items():
        missing = [token for token in tokens if token not in joined_runtime]
        if missing:
            failures.append(f"{label} runtime incomplete: {', '.join(missing)}")
    local_refs = sorted(set(re.findall('(?:src|href)=["\\\']([^"\\\'?]+)', html)))
    media = [ref for ref in local_refs if Path(ref).suffix.lower() in RASTER_SUFFIXES]
    decoded = 0
    for ref in media:
        if ref.startswith(('http://', 'https://', 'data:')):
            continue
        path = root / ref
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f'missing local image: {ref}')
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            decoded += 1
        except Exception as exc:
            failures.append(f'undecodable image {ref}: {exc}')
    print(f'images in HTML={images}, local raster references={len(media)}, decoded={decoded}')
    manifest_path = root / 'asset-manifest.json'
    if not manifest_path.exists():
        message = 'asset-manifest.json is missing; every newly researched destination must provide image provenance'
        (warnings if is_canonical_bali else failures).append(message)
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            entries = manifest.get('assets', []) if isinstance(manifest, dict) else []
            manifest_destination = str(manifest.get('destination', '')).strip() if isinstance(manifest, dict) else ''
            if not manifest_destination or manifest_destination == 'REPLACE_ME':
                failures.append('asset manifest destination is missing or unchanged')
            if declared_destination and manifest_destination and (declared_destination.lower() not in manifest_destination.lower()) and (manifest_destination.lower() not in declared_destination.lower()):
                failures.append(f'destination mismatch: profile={declared_destination!r}, manifest={manifest_destination!r}')
            required_asset_fields = ('file', 'place_id', 'venue', 'module', 'role', 'source_type', 'source_page', 'retrieved_at', 'http_accessible', 'decoded', 'source_identity_bound')
            if not args.standard_fast:
                required_asset_fields += ('visually_confirmed', 'watermark_checked', 'visual_confirmation_note', 'subject_verified')
            incomplete = [entry for entry in entries if not isinstance(entry, dict) or any((field not in entry or entry.get(field) in (None, '') for field in required_asset_fields)) or (not args.standard_fast and entry.get('subject_verified') is not True)]
            if incomplete:
                failures.append(f'asset manifest has incomplete entries: {len(incomplete)}')
                for number, entry in enumerate(entries, 1):
                    if not isinstance(entry, dict):
                        failures.append(f'asset entry {number}: expected an object')
                        continue
                    missing = [field for field in required_asset_fields if field not in entry or entry.get(field) in (None, '')]
                    if not args.standard_fast and entry.get('subject_verified') is not True:
                        missing.append('subject_verified must be true after actual review')
                    if missing:
                        failures.append('asset ' + str(entry.get('place_id', number)) + ' [' + str(entry.get('file', 'missing file')) + ']: ' + ', '.join(missing))
            unsupported_verification = [entry for entry in entries if isinstance(entry, dict) and entry.get('subject_verified') is True and (not (entry.get('decoded') is True and entry.get('source_identity_bound') is True and (entry.get('visually_confirmed') is True) and (entry.get('watermark_checked') is True)))]
            if unsupported_verification and (not args.standard_fast):
                failures.append(f'asset subject verification lacks complete evidence chain: {len(unsupported_verification)}')
            manifest_files = {str(entry.get('file', '')).replace('\\', '/') for entry in entries}
            manifest_file_list = [str(entry.get('file', '')).replace('\\', '/') for entry in entries if entry.get('file')]
            from verify_assets import shared_place_photo
            identity_places = {p['id']: p for p in profile_places if isinstance(p, dict) and p.get('id')}
            for asset_file in set(manifest_file_list):
                owners = [e for e in entries if str(e.get('file', '')).replace('\\', '/') == asset_file]
                cover = profile.get('cover', {})
                if cover.get('derived_from') == asset_file:
                    source_owners = [e for e in owners if e.get('place_id') != '__cover__']
                    owners = [e for e in owners if e.get('place_id') != '__cover__' or not any(
                        all(e.get(k) and e.get(k) == source.get(k) for k in ('source_page', 'download_url'))
                        for source in source_owners)]
                if any(not shared_place_photo(a, b, identity_places) for n, a in enumerate(owners) for b in owners[n+1:]):
                    failures.append('asset manifest reuses one file without verified same-place identity: ' + asset_file)
            unmanifested = [ref for ref in media if not ref.startswith(('http://', 'https://', 'data:')) and ref.replace('\\', '/') not in manifest_files]
            if unmanifested and (not is_canonical_bali):
                failures.append(f'referenced local images missing from asset manifest: {len(unmanifested)}')
            missing_manifest_files = [name for name in manifest_files if name and (not (root / name).exists())]
            if missing_manifest_files:
                failures.append(f'asset manifest references missing files: {len(missing_manifest_files)}')
            if not is_canonical_bali:
                profile_by_id = {str(place.get('id', '')).strip(): place for place in profile_places if isinstance(place, dict) and place.get('id')}
                profile_by_id['__cover__'] = {'display_name': profile.get('display_name', '')}
                bad_asset_identity = []
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    place_id = str(entry.get('place_id', '')).strip()
                    place = profile_by_id.get(place_id)
                    if not place:
                        bad_asset_identity.append(str(entry.get('file', '')))
                        continue
                    venue = str(entry.get('venue', '')).strip().casefold()
                    display_name = str(place.get('display_name', '')).strip().casefold()
                    if venue and display_name and (venue != display_name):
                        bad_asset_identity.append(str(entry.get('file', '')))
                if bad_asset_identity:
                    failures.append(f'asset/place identity mismatch: {len(bad_asset_identity)}')
                all_rasters = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file() and path.suffix.lower() in RASTER_SUFFIXES and (not any((part.lower() in {'qa', 'browser-qa', 'qa-evidence', 'screenshots'} for part in path.relative_to(root).parts[:-1]))) and (path.name.lower() not in {'asset-contact-sheet.jpg', 'asset-contact-sheet.jpeg', 'asset-contact-sheet.png'})}
                orphan_rasters = sorted(all_rasters - manifest_files)
                if orphan_rasters:
                    failures.append('unmanifested raster assets remain (possible reference-destination contamination): ' + ', '.join(orphan_rasters[:8]) + (f' … +{len(orphan_rasters) - 8}' if len(orphan_rasters) > 8 else ''))
                card_pattern = re.compile('<article\\b(?=[^>]*class=["\\\'][^"\\\']*\\b(?:hotel-card|sight-card|shop-row|movement-card|restaurant)\\b)[^>]*>(.*?)</article>', re.I | re.S)
                for card_number, match in enumerate(card_pattern.finditer(html), 1):
                    opening = match.group(0).split('>', 1)[0]
                    place_match = re.search('\\bdata-place-id=["\\\']([^"\\\']+)["\\\']', opening, re.I)
                    if not place_match and re.search('\\bstay-pending\\b', opening, re.I):
                        continue
                    if not place_match:
                        failures.append(f'place-bearing card {card_number} lacks data-place-id')
                        continue
                    place_id = place_match.group(1)
                    if place_id not in profile_by_id:
                        failures.append(f'place-bearing card {card_number} uses unknown place-id: {place_id}')
                        continue
                    card_refs = re.findall('<img\\b[^>]*\\bsrc=["\\\']([^"\\\'?]+)', match.group(0), re.I)
                    manifest_by_file = {str(entry.get('file', '')).replace('\\', '/'): str(entry.get('place_id', '')) for entry in entries if isinstance(entry, dict)}
                    wrong_refs = [ref for ref in card_refs if not any(str(e.get('file', '')).replace('\\', '/') == ref.replace('\\', '/') and str(e.get('place_id', '')) == place_id for e in entries)]
                    if wrong_refs:
                        failures.append(f'place-bearing card {card_number} references media for another place: ' + ', '.join(wrong_refs))
        except Exception as exc:
            failures.append(f'invalid asset-manifest.json: {exc}')
    if not is_canonical_bali:
        runtime_sources = [html]
        for source_path in sorted(root.glob('*.js')):
            runtime_sources.append(source_path.read_text(encoding='utf-8', errors='ignore'))
        for source_path in sorted(root.glob('*.json')):
            if source_path.name not in {'destination-profile.json', 'asset-manifest.json', '.travel-build-state.json'}:
                runtime_sources.append(source_path.read_text(encoding='utf-8', errors='ignore'))
        runtime_sources[0] = re.sub('<(?:style|script)\\b[^>]*>.*?</(?:style|script)>', '', runtime_sources[0], flags=re.I | re.S)
        visible_source = '\n'.join(runtime_sources)
        css_content_literals = '\n'.join((match.group(0) for match in re.finditer('content\\s*:\\s*(?:"[^"]*"|\\\'[^\\\']*\\\')', css_text, re.I)))
        contamination_source = visible_source + '\n' + css_content_literals
        contaminated = [term for term in REFERENCE_DESTINATION_TERMS if re.search(re.escape(term), contamination_source, re.I)]
        extra_terms = profile.get('forbidden_reference_terms', []) if isinstance(profile, dict) else []
        contaminated.extend((term for term in extra_terms if isinstance(term, str) and term and re.search(re.escape(term), contamination_source, re.I)))
        contaminated = sorted(set(contaminated), key=str.lower)
        if contaminated:
            failures.append('reference-destination contamination remains: ' + ', '.join(contaminated))
    for gallery in re.findall('<div class="gallery-wrap[^>]*>(.*?)</div>\\s*</div>', html, re.I | re.S):
        refs = re.findall('<img[^>]+src="([^"?]+)', gallery, re.I)
        fingerprints = []
        for ref in refs:
            path = root / ref
            if path.exists():
                fingerprints.append(hashlib.sha256(path.read_bytes()).hexdigest())
                try:
                    with Image.open(path) as image:
                        if image.width < 480 or image.height < 320:
                            warnings.append(f'gallery image is low resolution: {ref} ({image.width}x{image.height})')
                except Exception:
                    pass
        if len(fingerprints) != len(set(fingerprints)):
            failures.append('a gallery contains duplicate image files')
    if re.search('>\\s*(?:动态复核|评分待定|图片待补|TODO)\\s*<', html):
        failures.append('unresolved placeholder content remains')
    if re.search('(?:html|body|\\[data-handbook-theme[^\\]]*\\])[^\\{]*\\{[^}]*\\bfilter\\s*:\\s*(?:hue-rotate|sepia|saturate|grayscale|contrast)\\s*\\(', css_text, re.I | re.S):
        failures.append('themes must use semantic color tokens, not global recoloring filters')
    if re.search('writing-mode\\s*:\\s*vertical', css_text, re.I):
        failures.append('vertical writing mode is forbidden for handbook content')
    if re.search('word-break\\s*:\\s*break-all', css_text, re.I):
        failures.append('break-all creates one-character columns and is forbidden')
    if not re.search('@media[^\\{]*(?:1180|1200)[^\\{]*\\{[^}]*\\.desktop-chapter-rail', css_text, re.I | re.S) and 'desktop-rail.css' not in html:
        warnings.append('verify desktop rail is hidden below the wide-desktop breakpoint')
    if ('travel-info-fold' if current_system else 'hotel-chapter-fold') not in joined_runtime:
        failures.append('hotel disclosure must be the compact fold immediately before itinerary')
    theme_css = root / 'theme-switcher.css'
    if theme_css.exists():
        theme_source = theme_css.read_text(encoding='utf-8', errors='ignore')
        for theme_id in THEME_IDS:
            if f'data-handbook-theme="{theme_id}"' not in theme_source:
                failures.append(f'theme lacks explicit semantic token block: {theme_id}')
        semantic_tokens = ('--hb-page', '--hb-deep', '--hb-surface', '--hb-on-dark', '--hb-on-light', '--hb-action')
        for token in semantic_tokens:
            if theme_source.count(token) < len(THEME_IDS):
                failures.append(f'theme semantic token coverage is incomplete: {token}')
    for warning in warnings:
        print('WARN ' + warning)
    for failure in failures:
        print('FAIL ' + failure)
    if args.strict and failures:
        return 2
    return 0
if __name__ == '__main__':
    sys.exit(main())
