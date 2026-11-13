"""Prepare hash-bound map and editorial-photo review sheets and flag reused photos."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from audit_maps import audit as audit_maps, local_asset, read_json


def fingerprint(path):
    with Image.open(path) as source:
        pixels = ImageOps.exif_transpose(source).convert('L').resize((17, 16)).tobytes()
    return sum(
        (pixels[y * 17 + x] > pixels[y * 17 + x + 1]) << (y * 16 + x)
        for y in range(16) for x in range(16)
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review_font():
    for path in ('C:/Windows/Fonts/msyh.ttc', '/System/Library/Fonts/PingFang.ttc',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'):
        if Path(path).is_file():
            return ImageFont.truetype(path, 17)
    return ImageFont.load_default()


def wrap(draw, text, font, width):
    lines, line = [], ''
    for character in text:
        if line and draw.textlength(line + character, font=font) > width:
            lines.append(line)
            line = ''
        line += character
    return [*lines, line]


def make_sheets(root, qa, name, entries):
    sheets = []
    font = review_font()
    for start in range(0, len(entries), 9):
        batch = entries[start:start + 9]
        sheet = Image.new('RGB', (1260, ((len(batch) + 2) // 3) * 445), 'white')
        draw = ImageDraw.Draw(sheet)
        for index, entry in enumerate(batch):
            x, y = (index % 3) * 420, (index // 3) * 445
            try:
                asset = local_asset(root, entry['src'])
                with Image.open(asset) as source:
                    preview = ImageOps.exif_transpose(source).convert('RGB')
                    preview.thumbnail((412, 305))
                sheet.paste(preview, (x, y))
                entry['sha256'] = digest(asset)
            except (ValueError, OSError) as error:
                entry['error'] = str(error)
                draw.rectangle((x, y, x + 411, y + 304), fill='#f6d6d6')
            label = f"{start + index + 1}. {entry['context']} | {entry.get('caption', '')}"
            for row, line in enumerate(wrap(draw, label, font, 408)[:5]):
                draw.text((x + 4, y + 310 + row * 23), line, font=font, fill='black')
        path = qa / (name + (f'-{start // 9 + 1}' if start else '') + '.png')
        sheet.save(path)
        sheets.append(str(path))
    return sheets


def photo_usage(root, guide, edition, photos):
    usages, errors = [], []
    places = {place['id']: place for place in guide['places']}

    def add(context, key, intended_places):
        entry = photos.get(key)
        if not entry:
            errors.append(f'{context}: missing photo {key}')
            return
        for field in ('src', 'mobileSrc'):
            if entry.get(field):
                usages.append(dict(context=context + (' / 手机图' if field == 'mobileSrc' else ''),
                                   photoKey=key, src=entry[field], caption=entry.get('caption', ''),
                                   source=entry.get('page', ''), intendedPlaces=intended_places))

    for field, title in (('cover', '封面'), ('foodPhoto', '餐饮专题'),
                         ('culturePhoto', '文化专题'), ('closingPhoto', '收尾')):
        if edition.get(field):
            heading_field = {'foodPhoto': 'foodTitle', 'culturePhoto': 'cultureTitle', 'cover': 'coverNote', 'closingPhoto': 'closingCopy'}[field]
            heading = edition.get(heading_field, '').replace('<br>', ' ')
            add(title + ' · ' + edition.get('city', '') + ' · ' + heading, edition[field], [])
    for area in guide.get('areas', []):
        area_day = area.get('day')
        day_label = f'第 {area_day + 1} 天 · ' if isinstance(area_day, int) else ''
        context = day_label + area.get('name', area.get('id', '')) + ' · ' + area.get('deck', '')
        add(context, area.get('photo'), [places[pid]['name'] for pid in area.get('ids', []) if pid in places])
    return usages, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    parser.add_argument('--compare', type=Path, action='append', default=[],
                        help='Previous edition media directory, for read-only photo comparison')
    args = parser.parse_args()
    root = args.workbench.resolve()
    qa = root / 'qa-media'
    qa.mkdir(exist_ok=True)
    try:
        map_report = audit_maps(root)
        maps = read_json(root / 'maps.json')
        guide = read_json(root / 'content.json')
        edition = read_json(root / 'edition.json')
        editorial = read_json(root / 'edition-photos.json')
        places = read_json(root / 'place-photos.json')
        photos = places | editorial
        usages, errors = photo_usage(root, guide, edition, photos)
        days = {day['id']: day for day in guide['days']}
        map_entries = [dict(context=key + ' · ' + entry.get('title', ''), src=entry.get('src'),
                            caption=' / '.join(stop[1] for stop in days.get(key, {}).get('stops', [])))
                       for key, entry in maps.items()]
        map_sheets = make_sheets(root, qa, 'map-review', map_entries)
        photo_sheets = make_sheets(root, qa, 'editorial-review', usages)
        for usage in [*map_entries, *usages]:
            if usage.get('error'):
                errors.append(usage['context'] + ': ' + usage['error'])
        selected = {local_asset(root, usage['src']) for usage in usages}
        selected.update({
            local_asset(root, entry[field])
            for entry in places.values()
            for field in ('src', 'mobileSrc') if entry.get(field)
        })
        # Decode every selected thumbnail, even when it is absent from the editorial sheet.
        signatures = {path: fingerprint(path) for path in selected}
        archive, archive_errors = {}, []
        for folder in args.compare:
            folder = folder.resolve()
            if not folder.is_dir():
                parser.error(f'Comparison directory not found: {folder}')
            for path in folder.rglob('*'):
                if path.is_file() and path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.avif'}:
                    try:
                        archive[path] = fingerprint(path)
                    except OSError as error:
                        archive_errors.append(f'{path}: {error}')
        matches = []
        for path, current in sorted(signatures.items()):
            for previous, signature in archive.items():
                distance = (current ^ signature).bit_count()
                if distance <= 20:
                    matches.append(dict(photo=str(path.relative_to(root)), previous=str(previous), distance=distance))
        errors.extend(map_report['errors'])
        report = dict(mapSheet=map_sheets[0] if map_sheets else None, mapSheets=map_sheets,
                      editorialSheets=photo_sheets, mapVisualReview='pending', editorialVisualReview='pending',
                      mapAudit=map_report, editorialUsage=usages, mapAssets=map_entries,
                      photos=len(selected), comparedArchivePhotos=len(archive), possibleMatches=matches,
                      archiveReadErrors=archive_errors, errors=errors,
                      selectedAssets={str(path.relative_to(root)): digest(path) for path in sorted(selected)})
        manifest = root / 'build-manifest.json'
        if manifest.is_file():
            build = read_json(manifest)
            report['buildId'] = build.get('buildId')
            report['artifactSha256'] = build.get('sha256')
        (qa / 'media-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
        print(json.dumps({key: value for key, value in report.items()
                          if key not in {'editorialUsage', 'mapAssets', 'selectedAssets'}}, ensure_ascii=False, indent=2, allow_nan=False))
        return bool(errors or matches or archive_errors)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'Media review failed: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
