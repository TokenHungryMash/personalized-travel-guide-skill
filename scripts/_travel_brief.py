"""Preserve the approved written brief across deterministic initialization."""
import json
from datetime import date, timedelta
from pathlib import Path

IDENTITY_FIELDS = ('destination', 'country', 'start_date', 'end_date', 'days')
PREFERENCE_FIELDS = ('travelers', 'rhythm', 'interests', 'constraints', 'must_go', 'avoid',
                     'budget', 'budget_level', 'budget_total', 'local_daily_budget')


def merge_fields(previous: dict, incoming: dict) -> dict:
    merged = dict(previous)
    for key, value in incoming.items():
        merged[key] = merge_fields(merged[key], value) if isinstance(merged.get(key), dict) and isinstance(value, dict) else value
    return merged


def read_brief(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Cannot read approved brief JSON {path}: {exc}') from exc
    if not isinstance(value, dict):
        raise SystemExit(f'Approved brief must be a JSON object: {path}')
    validate_fields(value, str(path))
    return value


def validate_fields(value: dict, label: str) -> None:
    for key in ('destination', 'display_name', 'country', 'start_date', 'end_date', 'rhythm'):
        if key in value and not isinstance(value[key], str):
            raise SystemExit(f'{label}: {key} must be a string')
    if 'days' in value and (type(value['days']) is not int or value['days'] < 1):
        raise SystemExit(f'{label}: days must be a positive integer')
    if 'travelers' in value and not (isinstance(value['travelers'], str) and value['travelers'].strip()
                                    or type(value['travelers']) is int and value['travelers'] > 0):
        raise SystemExit(f'{label}: travelers must be a non-empty description or positive integer')
    for key in ('interests', 'constraints', 'must_go', 'avoid'):
        if key in value and not (isinstance(value[key], str)
                                 or isinstance(value[key], list) and all(isinstance(item, str) for item in value[key])):
            raise SystemExit(f'{label}: {key} must be a string or array of strings')
    for key in ('start_date', 'end_date'):
        if key in value and value[key] not in ('', 'pending'):
            try:
                date.fromisoformat(value[key])
            except ValueError as exc:
                raise SystemExit(f'{label}: {key} must be YYYY-MM-DD or pending') from exc


def resolve_brief(root: Path, *, brief_file: Path | None = None, state: dict | None = None,
                  overrides: dict | None = None, require_country: bool = True) -> dict:
    """Explicit preferences override; conflicting trip identities fail before writes."""
    result = {}
    sources = []
    existing = root / 'travel-brief.json'
    if existing.is_file():
        sources.append((str(existing), read_brief(existing)))
    if brief_file is not None and brief_file.resolve() != existing.resolve():
        sources.append((str(brief_file), read_brief(brief_file)))
    elif brief_file is not None and not existing.is_file():
        sources.append((str(brief_file), read_brief(brief_file)))
    if state:
        sources.append(('build state', {key: state[key] for key in IDENTITY_FIELDS if state.get(key) not in (None, '')}))
    sources.append(('explicit CLI arguments', {key: value for key, value in (overrides or {}).items() if value is not None}))
    for label, value in sources:
        validate_fields(value, label)
        value = {key: item.strip() if key in IDENTITY_FIELDS and isinstance(item, str) else item
                 for key, item in value.items()}
        for key in IDENTITY_FIELDS:
            old, new = result.get(key), value.get(key)
            if old not in (None, '', 'pending') and new not in (None, '', 'pending') and old != new:
                raise SystemExit(f'{label}: {key} conflicts with the approved brief ({old!r} != {new!r}); preserve the existing workbench and resolve the trip identity first')
        # A persisted pending identity must not erase a subsequently supplied fact.
        result = merge_fields(result, {key: item for key, item in value.items()
                              if key not in IDENTITY_FIELDS or item not in (None, '', 'pending')
                              or result.get(key) in (None, '', 'pending')})
    if not str(result.get('destination', '')).strip() or not result.get('days'):
        raise SystemExit('destination and positive days are required in --brief-file, the existing brief, build state or CLI arguments')
    if require_country and not str(result.get('country', '')).strip():
        raise SystemExit('country is required in the approved brief, build state or --country')
    result.setdefault('country', '')
    result.setdefault('start_date', 'pending')
    result.setdefault('display_name', result['destination'])
    result.setdefault('travelers', '2')
    result.setdefault('rhythm', 'relaxed')
    for key in ('interests', 'constraints', 'must_go', 'avoid'):
        result.setdefault(key, [])
    result.setdefault('defaults_authorized', True)
    if result['start_date'] not in ('', 'pending'):
        computed_end = (date.fromisoformat(result['start_date']) + timedelta(days=result['days'] - 1)).isoformat()
        if result.get('end_date') not in (None, '', 'pending', computed_end):
            raise SystemExit('end_date conflicts with start_date and days; the existing brief was not changed')
        result['end_date'] = computed_end
    else:
        result['start_date'] = 'pending'
        result.setdefault('end_date', 'pending')
    result['quality_mode'] = 'standard'
    return result
