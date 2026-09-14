"""Render a small, licensed OSM vector extract into offline route basemap tiles.

Uses only the current profile's geographic extents; never downloads raster tile
services or a region-wide extract. OSM geometry is retained for attribution.
"""
import argparse
import hashlib
import json
import math
import urllib.request
import urllib.parse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version
from _current_system_adapter import trip_days


def world(lon, lat, z):
    n = 256 * 2 ** z
    a = math.radians(lat)
    return ((lon + 180) / 360 * n, (1 - math.log(math.tan(a) + 1 / math.cos(a)) / math.pi) / 2 * n)


def geographic(x, y, z):
    n = 256 * 2 ** z
    return (x / n * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n)))))


def required_tiles(days):
    tiles = set()
    bounds = []
    for day in days:
        for start in range(0, len(day['stops']), 4):
            stops = day['stops'][start:start + 5]
            if start and len(stops) == 1:
                break
            for stop in stops:
                lat, lon = stop.get('latitude'), stop.get('longitude')
                if (not isinstance(lat, (int, float)) or not isinstance(lon, (int, float))
                        or not math.isfinite(lat) or not math.isfinite(lon)
                        or abs(lat) > 85 or abs(lon) > 180):
                    raise ValueError('Missing/invalid verified coordinates for ' + str(stop.get('name')))
            for z in range(16, 7, -1):
                pixels = [world(s['longitude'], s['latitude'], z) for s in stops]
                xs, ys = zip(*pixels)
                if max(xs) - min(xs) <= 390 and max(ys) - min(ys) <= 455:
                    break
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            x0, x1 = math.floor((cx - 330) / 256), math.floor((cx + 330) / 256)
            y0, y1 = math.floor((cy - 345) / 256), math.floor((cy + 345) / 256)
            tiles.update((z, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1))
            west, north = geographic(x0 * 256, y0 * 256, z)
            east, south = geographic((x1 + 1) * 256, (y1 + 1) * 256, z)
            bounds.append((south, west, north, east))
    return tiles, bounds


def index_paths(ways, tiles):
    """Project each way once per zoom, preserving source draw order per tile."""
    result = {key: [] for key in tiles}
    for z in sorted({key[0] for key in tiles}):
        visible = [key for key in sorted(tiles) if key[0] == z]
        for way in ways:
            pts = [world(g['lon'], g['lat'], z) for g in way['geometry']]
            xs, ys = zip(*pts)
            xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
            for key in visible:
                _, tx, ty = key
                if xmax < tx*256-20 or xmin > tx*256+276 or ymax < ty*256-20 or ymin > ty*256+276:
                    continue
                result[key].append((way.get('tags', {}), [(x-tx*256, y-ty*256) for x, y in pts]))
    return result


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tiles_cached(out, signature, tiles):
    try:
        record = json.loads((out / 'tile-cache.json').read_text(encoding='utf-8'))
        expected = {f'tiles/{z}/{x}/{y}.png' for z, x, y in tiles}
        return (record['signature'] == signature and set(record['files']) == expected
                and (out / 'SOURCES.md').is_file()
                and all(file_hash(out / name) == value for name, value in record['files'].items()))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    days = trip_days(profile)
    tiles, bounds = required_tiles(days)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / 'days.json').write_text(json.dumps(days, ensure_ascii=False), encoding='utf-8')
    from _osm_extract import fetch_extract
    raw_path = out / "osm-extract.json"
    raw = fetch_extract(bounds, out)
    ways = [w for w in raw['elements'] if len(w.get('geometry', [])) >= 2]
    if len(ways) < 10:
        raise ValueError('Insufficient real geographic background geometry')
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 10)
    except OSError:
        font = ImageFont.load_default()
    font_path = Path(getattr(font, 'path', ''))
    signature = hashlib.sha256((file_hash(raw_path) + file_hash(Path(__file__)) + pillow_version
                               + (file_hash(font_path) if font_path.is_file() else 'default-font')).encode()).hexdigest()
    if tiles_cached(out, signature, tiles):
        print(f'Reused {len(tiles)} verified tiles from this build; no network request or reprojection.')
        return
    indexed = index_paths(ways, tiles)
    for z, tx, ty in sorted(tiles):
        image = Image.new('RGB', (256, 256), '#f0eee7')
        draw = ImageDraw.Draw(image)
        paths = indexed[z, tx, ty]
        for tags, pts in paths:
            if tags.get('natural') == 'water' or tags.get('waterway') == 'riverbank':
                draw.polygon(pts, fill='#bfdde5')
            elif tags.get('leisure') == 'park' or tags.get('natural') in {'wood', 'scrub'} or tags.get('landuse') in {'forest', 'grass', 'meadow', 'recreation_ground'}:
                draw.polygon(pts, fill='#d5e4c5')
            elif tags.get('landuse') and pts[0] == pts[-1]:
                draw.polygon(pts, fill='#e6e2d9')
        for tags, pts in paths:
            if tags.get('waterway'):
                draw.line(pts, fill='#acd3df', width=3)
            if tags.get('railway'):
                draw.line(pts, fill='#aaa6a0', width=2)
            road = tags.get('highway')
            if road:
                width = 7 if road in {'primary', 'secondary', 'trunk'} else 5 if road in {'tertiary', 'residential'} else 2
                draw.line(pts, fill='#d0c9b9', width=width + 2)
                draw.line(pts, fill='#fffaf0' if width >= 5 else '#fffdf8', width=width)
        labels = []
        for tags, pts in paths:
            if tags.get('highway') not in {'primary', 'secondary', 'tertiary'} or not tags.get('name'):
                continue
            x, y = pts[len(pts) // 2]
            if not (8 < x < 190 and 8 < y < 238) or any(abs(x-a) < 75 and abs(y-b) < 24 for a, b in labels):
                continue
            labels.append((x, y))
            draw.text((x, y), tags['name'], font=font, fill='#67685f', stroke_width=1, stroke_fill='#fffdf8')
        target = out / 'tiles' / str(z) / str(tx) / f'{ty}.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target)
    (out / 'SOURCES.md').write_text('© OpenStreetMap contributors, ODbL. https://www.openstreetmap.org/copyright\nSmall live vector extract from https://overpass-api.de/api/interpreter; locally rendered raster basemap. Original query and geometry retained here.\n', encoding='utf-8')
    files = {f'tiles/{z}/{x}/{y}.png': file_hash(out / f'tiles/{z}/{x}/{y}.png') for z, x, y in tiles}
    (out / 'tile-cache.json').write_text(json.dumps({'signature': signature, 'files': files}), encoding='utf-8')
    print(f'Rendered {len(tiles)} tiles from {len(ways)} OSM ways; no external raster tile cache used.')


if __name__ == '__main__':
    main()
