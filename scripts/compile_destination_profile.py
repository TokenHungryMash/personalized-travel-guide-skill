"""Compile bounded research packs into the canonical destination profile."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def module_payload(value, key: str):
    if isinstance(value, dict) and value.get('_draft') is True:
        raise SystemExit(f'{key} is still a generated draft; review destination facts and set _draft to false')
    if key == 'travel_notes' and isinstance(value, dict) and ('groups' in value):
        return value['groups']
    if isinstance(value, dict):
        return {name: item for name, item in value.items() if not name.startswith('_')}
    return value

def normalize_journey_phases(profile):
    """Omitted grouping means one chronological group, never invisible days."""
    phases = profile.get('journey_phases') or []
    count = len(profile.get('itinerary', []))
    if not phases or all((not phase.get('day_numbers') for phase in phases)):
        profile['journey_phases'] = [{'title': f'{count} 天行程', 'day_numbers': list(range(1, count + 1))}]
        return
    numbers = [n for phase in phases for n in phase.get('day_numbers', [])]
    if any((type(n) is not int for n in numbers)) or sorted(numbers) != list(range(1, count + 1)):
        raise SystemExit('journey_phases.day_numbers must cover every day exactly once; omit journey_phases for automatic chronological grouping')

def normalize_image_paths(profile):
    """Resolve the accepted research alias before downstream tools read file."""
    for place in profile.get('places', []):
        for image in place.get('images', []):
            if isinstance(image, dict) and not image.get('file') and image.get('local_file'):
                image['file'] = image['local_file']

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    root = args.workbench.resolve()
    plan = load(root / 'research-plan.json')
    missing = [item for item in plan.get('packs', []) if not (root / item['file']).is_file()]
    if missing:
        print('FAIL incomplete research packs: ' + ', '.join((item['id'] for item in missing)))
        print(f"CONTINUE: {sys.executable} {Path(__file__).with_name('research_status.py')} {root}")
        return 2
    pack_paths = [root / item['file'] for item in plan.get('packs', [])]
    forbidden = (b'"test_fixture"', b'generated-fixture', b'local-regression-fixture', b'smoke_test', b'example.com')
    contaminated = [str(path.relative_to(root)) for path in pack_paths if any((token in path.read_bytes().lower() for token in forbidden))]
    if contaminated:
        print('FAIL production research packs contain test/example provenance: ' + ', '.join(contaminated))
        return 2
    pack_validator = Path(__file__).with_name('validate_research_pack.py')
    for item in plan.get('packs', []):
        result = subprocess.run([sys.executable, str(pack_validator), item['id'], str(root / item['file'])])
        if result.returncode:
            print(f"CONTINUE: fix {item['file']} against assets/research-pack-contract.json before compilation")
            return result.returncode
    framing = load(root / 'research/framing.json')
    profile = dict(framing)
    profile.setdefault('map_delivery', 'screenshots')
    brief_path = root / 'travel-brief.json'
    brief = load(brief_path) if brief_path.is_file() else {}
    profile.setdefault('trip', {}).setdefault('quality_mode', brief['quality_mode'])
    compact = (root / 'research/itinerary.json').is_file()
    if compact:
        itinerary = load(root / 'research/itinerary.json')
        if not isinstance(itinerary, list):
            raise SystemExit('research/itinerary.json must be a JSON array')
        profile['itinerary'] = itinerary
        core = load(root / 'research/places/core.json')
        shopping = load(root / 'research/places/shopping.json')
        if not isinstance(core, dict) or not isinstance(shopping, dict):
            raise SystemExit('compact core/shopping place packs must be JSON objects')
        place_families = (core.get('sights', []), core.get('support', []), shopping.get('shops', []), shopping.get('souvenirs', []), load(root / 'research/places/experiences.json'), load(root / 'research/places/restaurants.json'))
        if any((not isinstance(value, list) for value in place_families)):
            raise SystemExit('every compact place family must be a JSON array')
        profile['places'] = [record for family in place_families for record in family]
        discovery = load(root / 'research/modules/discovery.json')
        practical = load(root / 'research/modules/practical.json')
        language_notes = load(root / 'research/modules/language-notes.json')
        for name, value in (('discovery', discovery), ('practical', practical), ('language-notes', language_notes)):
            if not isinstance(value, dict):
                raise SystemExit(f'research/modules/{name}.json must be a JSON object')
        modules = {**discovery, **practical, **language_notes}
        profile['module_groups'] = {name: module_payload(modules[name], name) for name in ('shopping', 'experiences', 'food', 'preparation', 'language', 'travel_notes')}
        if discovery.get('experience_mode') in {'constrained', 'expanded'}:
            profile.setdefault('trip', {})['experience_mode'] = discovery['experience_mode']
    else:
        profile['itinerary'] = [load(root / f'research/itinerary/day-{day:02d}.json') for day in range(1, int(plan['days']) + 1)]
        places = []
        for name in ('sights', 'shops', 'souvenirs', 'experiences', 'restaurants', 'support'):
            value = load(root / f'research/places/{name}.json')
            if not isinstance(value, list):
                raise SystemExit(f'research/places/{name}.json must be a JSON array')
            places.extend(value)
        profile['places'] = places
        profile['module_groups'] = {name: module_payload(load(root / f'research/modules/{name}.json'), name) for name in ('shopping', 'experiences', 'food', 'preparation', 'language', 'travel_notes')}
    normalize_image_paths(profile)
    normalize_journey_phases(profile)
    from apply_trip_decisions import apply as apply_trip_decisions
    profile = apply_trip_decisions(root, profile)
    profile_path = root / 'destination-profile.json'
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    validator = Path(__file__).with_name('validate_destination_data.py')
    result = subprocess.run([sys.executable, str(validator), str(profile_path)])
    if result.returncode:
        print('CONTINUE: correct the specific research pack named by validation; do not patch rendered HTML')
        return result.returncode
    manifest_path = root / 'asset-manifest.json'
    if manifest_path.is_file():
        from audit_source_media import audit
        conflicts = audit(profile, load(manifest_path))
        if conflicts:
            for conflict in conflicts[:12]:
                print('STALE DERIVED MEDIA ' + conflict)
            print(f'SOURCE MEDIA: {len(conflicts)} conflicts. Rebuilding declarations; changed images still require download and visual review.')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('build_asset_manifest.py')), str(profile_path), str(manifest_path)])
            if result.returncode:
                return result.returncode
    pack_hashes = {str(path.relative_to(root)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in pack_paths}
    provenance = {'compiler': 'compile_destination_profile.py', 'research_plan_sha256': hashlib.sha256((root / 'research-plan.json').read_bytes()).hexdigest(), 'pack_count': len(pack_paths), 'pack_sha256': pack_hashes, 'profile_sha256': hashlib.sha256(profile_path.read_bytes()).hexdigest(), 'test_fixture_detected': False}
    (root / 'RESEARCH_PROVENANCE.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS compiled validated profile: {profile_path}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
