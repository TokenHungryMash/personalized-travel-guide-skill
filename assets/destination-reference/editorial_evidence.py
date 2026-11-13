"""Check source wiring, not the truth or usefulness of authored prose."""
from datetime import date
from urllib.parse import urlparse


def audit_reader_reference_evidence(editorial, required=False):
    """Validate nearby task/restaurant sources, independently of legacy row maps."""
    sources = editorial.get('editorial_sources', {})
    if not isinstance(sources, dict):
        return ['editorial_sources: expected object']
    errors = []
    collections = [('preparation', editorial.get('preparation', [])),
                   ('restaurant_groups', editorial.get('restaurant_groups', []))]
    for name, groups in collections:
        if not isinstance(groups, list):
            errors.append(f'{name}: expected array')
            continue
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict) or not isinstance(group.get('items'), list):
                errors.append(f'{name}[{group_index}].items: expected array')
                continue
            for item_index, item in enumerate(group['items']):
                path = f'{name}[{group_index}].items[{item_index}].sources'
                if not isinstance(item, dict):
                    errors.append(f'{name}[{group_index}].items[{item_index}]: expected object')
                    continue
                if 'sources' not in item:
                    if required:
                        errors.append(f'{path}: required when edition.readerReferenceVersion=1')
                    continue
                ids = item['sources']
                if not isinstance(ids, list) or not ids or any(not isinstance(key, str) or key not in sources for key in ids):
                    errors.append(f'{path}: missing or unknown source ID')
    return errors


def audit_evidence(editorial, required=False, area_ids=None):
    sources = editorial.get('editorial_sources', {})
    refs = editorial.get('section_sources', {})
    advice = editorial.get('editorial_advice', {})
    errors = audit_reader_reference_evidence(editorial)
    if not isinstance(sources, dict) or not isinstance(refs, dict) or not isinstance(advice, dict):
        return ['editorial_sources, section_sources and editorial_advice must be objects']
    for key, source in sources.items():
        if not isinstance(source, dict):
            errors.append(f'editorial_sources.{key}: expected object')
            continue
        parsed = urlparse(str(source.get('url', '')))
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            errors.append(f'editorial_sources.{key}.url: expected source page URL')
        if not isinstance(source.get('title'), str) or not source['title'].strip():
            errors.append(f'editorial_sources.{key}.title: missing readable title')
        try:
            date.fromisoformat(source.get('checked', ''))
        except (ValueError, TypeError):
            errors.append(f'editorial_sources.{key}.checked: use YYYY-MM-DD')
    sections = {k: editorial.get(k, []) for k in ('portrait', 'stays', 'culture', 'shopping')}
    sections.update({'notes:' + k: rows for k, rows in editorial.get('notes', {}).items()})
    sections.update({k: editorial[k] for k in ('food_types', 'snacks') if k in editorial})
    if 'reservations' in refs or 'reservations' in advice:
        sections['reservations'] = editorial.get('reservations', [])
    sections.update({'areas:' + k: rows for k, rows in editorial.get('area_sections', {}).items()})
    sections.update({'experiences:' + item.get('areaId', str(i)): [[item.get('title', ''), item.get('copy', ''), item.get('extra', '')]] for i,item in enumerate(editorial.get('route_experiences', []))})
    if area_ids is not None:
        authored = set(editorial.get('area_sections', {}))
        expected = set(area_ids)
        for key in sorted(authored - expected):
            errors.append(f'area_sections.{key}: unknown area ID')
        if required:
            for key in sorted(expected - authored):
                errors.append(f'area_sections.{key}: missing regional introduction')
    for key, mapping in refs.items():
        if key not in sections or not isinstance(mapping, dict):
            errors.append(f'section_sources.{key}: unknown section or non-object mapping')
            continue
        for index, ids in mapping.items():
            if not str(index).isascii() or not str(index).isdigit() or int(index) >= len(sections[key]):
                errors.append(f'section_sources.{key}.{index}: nonexistent row')
            if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in sources for i in ids):
                errors.append(f'section_sources.{key}.{index}: missing or unknown source ID')
    for key, mapping in advice.items():
        if key not in sections or not isinstance(mapping, dict):
            errors.append(f'editorial_advice.{key}: unknown section or non-object mapping')
            continue
        for index, reason in mapping.items():
            if not str(index).isascii() or not str(index).isdigit() or int(index) >= len(sections[key]):
                errors.append(f'editorial_advice.{key}.{index}: nonexistent row')
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f'editorial_advice.{key}.{index}: explain why this is original advice without external facts')
    if required:
        for key, rows in sections.items():
            if not rows:
                errors.append(f'{key}: missing practical content')
            for i, row in enumerate(rows):
                if not isinstance(row, list) or len(row) < 2 or not any(isinstance(x, str) and x.strip() for x in row[1:]):
                    errors.append(f'{key}[{i}]: missing body')
                if str(i) not in refs.get(key, {}) and str(i) not in advice.get(key, {}):
                    errors.append(f'{key}[{i}]: add nearby source references')
    return errors
