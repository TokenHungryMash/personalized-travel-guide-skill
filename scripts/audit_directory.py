"""Validate directory identity, usable photos, and declared destination coverage."""
from pathlib import Path
import argparse
import json
import sys
from PIL import Image
from workbench_input import resolve_workbench, read_json

TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/destination-reference'
sys.path.insert(0, str(TEMPLATE))
from schema_check import audit_schema
from coverage_release import effective_ids


def audit(root):
    root = Path(root).resolve()
    read = lambda name: json.loads((root / name).read_text(encoding='utf8'))
    data, photos, plan = [read(name) for name in ('content.json', 'place-photos.json', 'directory-plan.json')]
    errors = audit_schema(data) + audit_schema(photos, 'place-photos') + audit_schema(plan, 'directory-plan')
    warnings = []
    report = {'errors': errors, 'warnings': warnings}
    if not errors:
        places = {p['id']: p for p in data['places']}
        ids = set(places)
        if len(ids) != len(data['places']):
            errors.append('Duplicate place IDs')
        valid_photos = set()
        for pid, photo in photos.items():
            count_before = len(errors)
            if pid not in ids:
                errors.append('Unknown photo place ' + pid)
                continue
            if photo['subjectPlaceId'] != pid:
                errors.append(pid + ': photo subject mismatch')
            if photo['reviewed'] is not True:
                errors.append(pid + ': image identity has not been reviewed')
            if photo['role'] == 'area' and places[pid].get('identityScope', 'venue') != 'area':
                errors.append(pid + ': area image used for a specific venue; identityScope="area" only when the place itself is an area')
            for field in ('src', 'mobileSrc'):
                if field not in photo:
                    continue
                file = (root / photo[field]).resolve()
                if not file.is_relative_to(root) or not file.is_file():
                    errors.append(f'{pid}.{field}: missing local image within workbench')
                    continue
                try:
                    with Image.open(file) as im:
                        im.verify()
                    # Header verification alone accepts some truncated JPEGs.
                    with Image.open(file) as im:
                        im.load()
                except Exception:
                    errors.append(f'{pid}.{field}: invalid image')
            if len(errors) == count_before:
                valid_photos.add(pid)
        lo, hi = plan['targetRange']
        if lo > hi:
            errors.append('directory-plan.targetRange: minimum exceeds maximum')
        count = len(ids)
        effective_count = len(effective_ids(data))
        if effective_count < lo:
            errors.append(f'{effective_count} eligible places below declared {lo}; transport/lodging anchors are excluded; run audit_coverage.py for destination and dining requirements')
        if plan.get('tripDays', len(data['days'])) != len(data['days']):
            errors.append('directory-plan.tripDays differs from content.days')
        missing = sorted(ids - set(photos))
        pending = {pid: '' for pid in missing if not plan.get('photoExceptions', {}).get(pid, '').strip()}
        for pid in pending:
            errors.append(pid + ': missing photo without recorded research outcome; see pendingPhotoExceptions')
        for pid in set(plan.get('photoExceptions', {})) - ids:
            errors.append('photoExceptions: unknown place ' + pid)
        coverage = len(valid_photos) / max(1, count)
        if coverage < plan.get('imageCoverageTarget', .8):
            warnings.append(f'Photo coverage {coverage:.1%} below target; continue acquisition or disclose exact remaining gaps')
        for day in data['days']:
            for stop in day['stops']:
                if stop[1] not in ids:
                    errors.append('Unknown itinerary place ' + stop[1])
        report.update(places=count, effectivePlaces=effective_count, photos=len(valid_photos), photoRecords=len(photos), photoCoverage=round(coverage, 3),
                      missingPhotos=missing, pendingPhotoExceptions=pending,
                      pendingPhotoNames={pid: places[pid]['name'] for pid in pending})
    (root / 'directory-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    root = resolve_workbench(parser, args.workbench, ('content.json', 'place-photos.json', 'directory-plan.json'))
    for name in ('content.json', 'place-photos.json', 'directory-plan.json'):
        read_json(parser, root, name)
    report = audit(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report['errors']))
