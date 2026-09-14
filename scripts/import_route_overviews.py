"""Import reviewed geographic overviews only after evidenced capture failure."""
import argparse
import base64
import hashlib
import json
import shutil
import time
import io
from html import escape
from pathlib import Path
from PIL import Image
from _offline_overview import checked_file, verify_evidence
from _route_screenshots import day_fingerprint

def import_overviews(root, manifest):
    profile = json.loads((root/'destination-profile.json').read_text(encoding='utf-8'))
    if profile.get('map_delivery', 'screenshots') != 'screenshots':
        raise ValueError('set owning framing map_delivery to screenshots and recompile first')
    places = {p['id']:p for p in profile['places']}
    target = root/'research/itinerary.json'
    days = json.loads(target.read_text(encoding='utf-8'))
    rows = json.loads(manifest.read_text(encoding='utf-8'))['maps']
    if not rows or len({r['day'] for r in rows}) != len(rows):
        raise ValueError('empty or duplicate overview days')
    pending = []
    for row in rows:
        number = row['day']
        if type(number) is not int or not 1 <= number <= len(days):
            raise ValueError('invalid overview day')
        day = days[number-1]
        fingerprint = day_fingerprint(day, places)
        if row.get('capture_fingerprint') != fingerprint:
            raise ValueError('route changed since overview review')
        verify_evidence(root, row)
        original = checked_file(root, row['image'], row['sha256']).read_bytes()
        with Image.open(io.BytesIO(original)) as image:
            image.load()
            if image.width < 1000 or image.height < 700:
                raise ValueError('overview too small for full labels')
            image = image.convert('RGB')
            image.thumbnail((1600, 4000))
            w, h = image.size
            buffer = io.BytesIO()
            image.save(buffer, format='WEBP', quality=84)
            payload = buffer.getvalue()
        caption = f'第{number}天 · 简化地理总览，非街道导航图'
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>{escape(caption)} — {escape(row["attribution"])}</title><image width="{w}" height="{h}" href="data:image/webp;base64,{base64.b64encode(payload).decode()}"/></svg>'
        relative = f'media/routes/capture-day-{number}-1.svg'
        record = dict(row, kind='offline_overview', file=relative, caption=caption,
                      sha256=hashlib.sha256(svg.encode()).hexdigest(),
                      original_image_sha256=row['sha256'])
        pending.append((number, relative, svg, record))
    backup = root/'qa/offline-overview'
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup/f'itinerary-before-import-{time.time_ns()}.json')
    for number, relative, svg, record in pending:
        path = root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding='utf-8')
        days[number-1]['route_screenshots'] = [record]
    target.write_text(json.dumps(days, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('IMPORTED reviewed offline overviews. Recompile, render and run normal export QA.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    import_overviews(args.workbench.resolve(), args.manifest.resolve())

if __name__ == '__main__':
    main()
