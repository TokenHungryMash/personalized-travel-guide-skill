"""Deterministic content checks; passing does not certify source truth or visuals."""
import re
import math
from datetime import date
from urllib.parse import urlparse


def web_url(value):
    try:
        parsed = urlparse(str(value))
        return parsed.scheme in {'http', 'https'} and bool(parsed.hostname)
    except ValueError:
        return False


def nonnegative_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def identity_documented(record):
    """A URL and official label alone are not an identity observation."""
    return (record.get('source_identity_bound') is True
            and web_url(record.get('source_page', ''))
            and len(str(record.get('source_identity_note', '')).strip()) >= 12)


def clock_minutes(value):
    match = re.fullmatch(r'\s*([01]?\d|2[0-3]):([0-5]\d)(?:\s*[（(](?:示例|预计|计划)[）)])?\s*', str(value))
    return int(match[1]) * 60 + int(match[2]) if match else None


def date_key(value, year=None):
    text = str(value)
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    try:
        if match:
            return date(int(match[1]), int(match[2]), int(match[3]))
        match = re.search(r'(\d{1,2})月(\d{1,2})日', text)
        return date(year, int(match[1]), int(match[2])) if match and year else None
    except ValueError:
        return None


def content_failures(data):
    failures = []
    if data.get("trip", {}).get("quality_mode", "standard") != "standard":
        failures.append("Unsupported production standard; omit trip.quality_mode or use standard")
    places = {p.get('id'): p for p in data.get('places', []) if isinstance(p, dict)}
    days = [d for d in data.get('itinerary', []) if isinstance(d, dict)]
    scheduled = set()
    for day in days:
        previous_end = None
        previous_id = None
        for stop in day.get('stops', []):
            if not isinstance(stop, dict):
                continue
            pid = stop.get('place_id')
            scheduled.add(pid)
            start = clock_minutes(stop.get('arrival_time'))
            dwell, transfer = stop.get('dwell_minutes'), stop.get('transfer_minutes')
            for key, value in [('dwell_minutes', dwell), ('transfer_minutes', transfer)]:
                if not nonnegative_number(value):
                    failures.append(f'{pid}: {key} must be a finite nonnegative number')
            if start is not None and previous_end is not None and nonnegative_number(transfer):
                if start < previous_end + transfer:
                    earliest = previous_end + transfer
                    failures.append(f'{day.get("date")}: time overlap or insufficient transfer from {previous_id} to {pid}; incoming transfer={transfer:g} min, earliest arrival={int(earliest)//60:02d}:{int(earliest)%60:02d}, shortage={earliest-start:g} min; fix owning itinerary')
            previous_end = start + dwell if start is not None and nonnegative_number(dwell) else None
            previous_id = pid
    for pid in sorted(scheduled, key=str):
        place = places.get(pid, {})
        if not place:
            continue
        evidence = place.get('coordinate_source', {})
        if not isinstance(evidence, dict) or not all(evidence.get(k) for k in ('url', 'note', 'precision')):
            failures.append(f'{pid}: scheduled coordinates need coordinate_source url, note and precision; do not guess district centroids')
        elif not web_url(evidence['url']):
            failures.append(f'{pid}: coordinate_source.url must identify the actual source')
        elif evidence['precision'] not in {'entrance', 'building', 'area'}:
            failures.append(f'{pid}: coordinate_source.precision must be entrance, building or area')
    for meal in data.get('dining_plan', []):
        if not isinstance(meal, dict):
            continue
        matching = [d for d in days if date_key(d.get('date')) and date_key(d.get('date')) == date_key(meal.get('date'), date_key(d.get('date')).year)]
        if not matching and data.get('trip', {}).get('start_date') == 'pending':
            relative = re.fullmatch(r'Day ([1-9]\d*)', str(meal.get('date', '')))
            if relative:
                matching = [d for d in days if d.get('date') == meal.get('date')]
        if not matching:
            failures.append(f'dining_plan {meal.get("date")}: date is invalid or outside the itinerary')
        pid = meal.get('place_id')
        if not pid:
            title = str(meal.get('title', ''))
            candidates = [p for p in places.values() if p.get('type') == 'restaurant' and title and title in {str(p.get(k, '')) for k in ('display_name', 'local_name', 'english_name')}]
            pid = candidates[0]['id'] if len(candidates) == 1 else None
        if not pid and meal.get('flexible') is not True:
            failures.append(f'dining_plan {meal.get("date")}: named meals need place_id; set flexible true only for genuinely unassigned meals')
        if pid and (pid not in places or places[pid].get('type') != 'restaurant'):
            failures.append(f'dining_plan {meal.get("date")}: {pid} is not a known restaurant')
        if pid and (not matching or not any(s.get('place_id') == pid for d in matching for s in d.get('stops', []) if isinstance(s, dict))):
            failures.append(f'dining_plan {meal.get("date")}: {pid} is not scheduled on that day; synchronize the owning packs')
    return failures
