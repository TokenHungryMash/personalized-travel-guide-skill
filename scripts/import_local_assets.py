"""Record already acquired local images without claiming a network download."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from PIL import Image


def import_assets(profile, root, evidence):
    root = root.resolve()
    declarations = {(str(p['id']), str(i.get('file') or i.get('local_file'))): i
                    for p in profile.get('places', []) for i in p.get('images', []) if isinstance(i, dict)}
    cover = profile.get('cover', {})
    if cover.get('image'):
        declarations[('__cover__', str(cover['image']))] = cover
    rows = []
    for item in evidence:
        key = (str(item.get('place_id')), str(item.get('file')))
        declaration = declarations.get(key)
        if declaration is None:
            raise ValueError(f'{key}: no matching image declaration')
        path = (root / key[1]).resolve()
        log = (root / str(item.get('evidence_file', ''))).resolve()
        if not path.is_relative_to(root) or not log.is_relative_to(root):
            raise ValueError(f'{key}: local paths must stay inside asset root')
        if not log.is_file() or log.stat().st_size == 0 or len(str(item.get('acquisition_note', '')).strip()) < 12:
            raise ValueError(f'{key}: saved acquisition evidence and descriptive note required')
        for field in ('download_url', 'source_page'):
            url = item.get(field, '')
            parsed = urlparse(url)
            if not url or url != declaration.get(field) or parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f'{key}: {field} must match the HTTPS declaration without credentials')
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != item.get('sha256'):
            raise ValueError(f'{key}: acquisition SHA256 does not match actual local bytes')
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            width, height = image.size
        rows.append({**item, 'place_id': key[0], 'file': key[1], 'sha256': digest,
                     'status': 'cached', 'acquisition_method': 'local_import',
                     'network_verified': False, 'width': width, 'height': height,
                     'imported_at': datetime.now(timezone.utc).isoformat()})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('asset_root', type=Path)
    parser.add_argument('evidence', type=Path, help='JSON array of actual authorized acquisition records')
    args = parser.parse_args()
    try:
        rows = import_assets(json.loads(args.profile.read_text(encoding='utf-8-sig')), args.asset_root,
                             json.loads(args.evidence.read_text(encoding='utf-8-sig')))
        target = args.asset_root / 'asset-fetch-report.json'
        existing = json.loads(target.read_text(encoding='utf-8')) if target.exists() else []
        merged = {(r['place_id'], r['file']): r for r in existing}
        merged.update({(r['place_id'], r['file']): r for r in rows})
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(list(merged.values()), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temporary.replace(target)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'FAIL local import: {exc}')
        return 2
    print(f'PASS imported {len(rows)} local asset records; network access and subject identity were NOT verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
