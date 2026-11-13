"""Audit offline map coverage and Web Mercator pin coordinates without changing maps."""
import argparse
import json
import math
from pathlib import Path

from PIL import Image


PIXEL_TOLERANCE = 1.5


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def local_asset(root, source):
    if not isinstance(source, str) or not source:
        raise ValueError('Missing local image source')
    path = (root / source).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f'Invalid local image: {source}')
    return path


def coordinate_pair(coordinate):
    latitude, longitude = coordinate.get('latitude'), coordinate.get('longitude')
    if not finite_number(latitude) or not finite_number(longitude):
        raise ValueError('Coordinates must be finite numbers')
    if not -85.05112878 <= latitude <= 85.05112878 or not -180 <= longitude <= 180:
        raise ValueError('Coordinate outside Web Mercator range')
    return latitude, longitude


def project(coordinate, projection):
    latitude, longitude = coordinate_pair(coordinate)
    zoom = projection.get('zoom', projection.get('z'))
    scale = 256 * 2 ** zoom
    x = (longitude + 180) / 360 * scale - projection['left']
    y = (1 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2 * scale - projection['top']
    return x, y


def audit(root):
    root = Path(root).resolve()
    guide = read_json(root / 'content.json')
    maps = read_json(root / 'maps.json')
    coordinate_file = root / 'verified-coordinates.json'
    coordinates = read_json(coordinate_file) if coordinate_file.is_file() else {}
    place_ids = {place['id'] for place in guide['places']}
    routes = {day['id']: list(dict.fromkeys(stop[1] for stop in day['stops'])) for day in guide['days']}
    errors, warnings, results = [], [], {}
    expected = {'overview', *routes}
    if set(maps) != expected:
        errors.append(f'Map keys differ from itinerary: missing {sorted(expected - set(maps))}, extra {sorted(set(maps) - expected)}')

    for key, entry in maps.items():
        prefix = f'{key}: '
        try:
            asset = local_asset(root, entry.get('src'))
            with Image.open(asset) as source:
                source.load()
                image_width, image_height = source.size
        except (ValueError, OSError) as error:
            errors.append(prefix + str(error))
            continue
        ids = entry.get('ids', [])
        if not isinstance(ids, list) or any(not isinstance(pid, str) for pid in ids):
            errors.append(prefix + 'ids must be a list of place IDs')
            continue
        if len(ids) != len(set(ids)):
            errors.append(prefix + 'Duplicate place IDs')
        unknown = set(ids) - place_ids
        if unknown:
            errors.append(prefix + f'Unknown places {sorted(unknown)}')
        if key in routes:
            missing = set(routes[key]) - set(ids)
            if missing:
                errors.append(prefix + f'Itinerary stops missing from map list {sorted(missing)}')
            if [pid for pid in ids if pid in routes[key]] != routes[key]:
                errors.append(prefix + 'Map visit order differs from itinerary')
            extra = set(ids) - set(routes[key])
            if extra:
                warnings.append(prefix + f'Additional map places require editorial review {sorted(extra)}')

        projection = entry.get('projection') or {}
        width, height = projection.get('width', 1400), projection.get('height', 1100)
        if not all(finite_number(value) and value > 0 for value in (width, height)):
            errors.append(prefix + 'Invalid projection dimensions')
            continue
        if (width, height) != (image_width, image_height):
            errors.append(prefix + f'Image dimensions {image_width}x{image_height} differ from projection {width}x{height}')
        has_projection = all(field in projection for field in ('left', 'top')) and ('zoom' in projection or 'z' in projection)
        if projection and not has_projection:
            warnings.append(prefix + 'Projection is incomplete; geographic placement cannot be verified')
        if has_projection:
            zoom = projection.get('zoom', projection.get('z'))
            valid = all(finite_number(projection[field]) for field in ('left', 'top')) and finite_number(zoom) and 0 <= zoom <= 24
            if not valid:
                errors.append(prefix + 'Invalid Web Mercator projection values')
                has_projection = False
        elif not projection:
            warnings.append(prefix + 'Legacy map has no projection metadata; geographic placement requires visual review')

        pins = entry.get('pins', [])
        if not isinstance(pins, list):
            errors.append(prefix + 'pins must be a list')
            continue
        seen, valid_pins = set(), {}
        for pin in pins:
            if not isinstance(pin, dict):
                errors.append(prefix + 'Pin must be an object')
                continue
            pid = pin.get('id')
            if pid not in ids or pid not in place_ids:
                errors.append(prefix + f'Pin references an unlisted or unknown place {pid}')
                continue
            if pid in seen:
                errors.append(prefix + f'Duplicate pin {pid}')
            seen.add(pid)
            if 'number' in pin and (not isinstance(pin['number'], int) or isinstance(pin['number'], bool) or pin['number'] != ids.index(pid) + 1):
                errors.append(prefix + f'{pid} pin number differs from map visit order')
            if any(field in pin and not finite_number(pin[field]) for field in ('px', 'py', 'x', 'y')):
                errors.append(prefix + f'{pid} has non-finite or non-numeric pin coordinates')
                continue
            px = pin.get('px', pin.get('x', math.nan) * width / 100)
            py = pin.get('py', pin.get('y', math.nan) * height / 100)
            if not finite_number(px) or not finite_number(py):
                errors.append(prefix + f'{pid} has no usable pin coordinates')
                continue
            if not 0 <= px <= width or not 0 <= py <= height:
                errors.append(prefix + f'{pid} pin outside map bounds')
            if 'x' in pin and abs(pin['x'] * width / 100 - px) > PIXEL_TOLERANCE:
                errors.append(prefix + f'{pid} pixel and percentage x coordinates disagree')
            if 'y' in pin and abs(pin['y'] * height / 100 - py) > PIXEL_TOLERANCE:
                errors.append(prefix + f'{pid} pixel and percentage y coordinates disagree')
            valid_pins[pid] = (px, py)
        if 'mappedIds' in entry and entry['mappedIds'] != [pin.get('id') for pin in pins if isinstance(pin, dict)]:
            errors.append(prefix + 'mappedIds differ from pins; regenerate map metadata')

        missing_coordinates, missing_pins = [], []
        for pid in ids:
            coordinate = coordinates.get(pid)
            if not isinstance(coordinate, dict) or not coordinate:
                missing_coordinates.append(pid)
                if has_projection and pid in valid_pins:
                    errors.append(prefix + f'{pid} has a projected pin without verified coordinates')
                continue
            try:
                coordinate_pair(coordinate)
            except ValueError as error:
                errors.append(prefix + f'{pid}: {error}')
                continue
            if pid not in valid_pins:
                missing_pins.append(pid)
                errors.append(prefix + f'{pid} has coordinates but no usable pin')
            if has_projection:
                try:
                    x, y = project(coordinate, projection)
                except ValueError as error:
                    errors.append(prefix + f'{pid}: {error}')
                    continue
                if not 0 <= x <= width or not 0 <= y <= height:
                    errors.append(prefix + f'{pid} geographic location falls outside map coverage; recapture the map')
                if pid in valid_pins and math.dist(valid_pins[pid], (x, y)) > PIXEL_TOLERANCE:
                    errors.append(prefix + f'{pid} pin disagrees with geographic projection; recompute pins')
        if missing_coordinates:
            warnings.append(prefix + f'Coordinates unavailable for {missing_coordinates}; keep unverified locations explicit')
        results[key] = dict(width=image_width, height=image_height, projectionChecked=has_projection,
                            missingCoordinates=missing_coordinates, missingPins=missing_pins)
    return dict(errors=errors, warnings=warnings, maps=results, visualReview='pending')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.workbench)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'Map audit failed: {error}\n')
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return bool(report['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
