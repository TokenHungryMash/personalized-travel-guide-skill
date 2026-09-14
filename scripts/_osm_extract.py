"""Bounded serial Overpass jobs with content-addressed, resumable receipts."""
import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINTS = ('https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter',
             'https://overpass.osm.ch/api/interpreter',
             'https://overpass.openstreetmap.fr/api/interpreter')
GROUPS = (('[highway]', '[railway=rail]'),
          ('[waterway]', '[landuse]', '[natural]', '[leisure=park]'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def jobs(bounds):
    cells = set()
    for south, west, north, east in bounds:
        for y in range(math.floor(south * 10), math.ceil(north * 10)):
            for x in range(math.floor(west * 10), math.ceil(east * 10)):
                cells.add((y, x))
                if len(cells) > 100:
                    raise ValueError('Route extent exceeds 100 grid cells; split long-distance route maps before fetching')
    result = []
    for y, x in sorted(cells):
        bbox = ','.join(f'{v:.7f}' for v in (y/10, x/10, (y+1)/10, (x+1)/10))
        for group in GROUPS:
            query = '[out:json][timeout:25];(' + ''.join('way'+s+'('+bbox+');' for s in group) + ');out geom;'
            result.append(query)
    return result

def atomic(path, data):
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_bytes(data)
    temporary.replace(path)

def fetch_extract(bounds, out, budget=240, opener=urllib.request.urlopen, sleep=time.sleep):
    out = Path(out)
    cache = out / 'osm-cells'
    cache.mkdir(parents=True, exist_ok=True)
    queries = jobs(bounds)
    deadline = time.monotonic() + budget
    completed = []
    for index, query in enumerate(queries):
        key = digest(query.encode())
        path, receipt = cache / (key+'.json'), cache / (key+'.receipt.json')
        try:
            data = path.read_bytes()
            record = json.loads(receipt.read_text('utf-8'))
            if record['query_sha256'] != key or record['sha256'] != digest(data):
                raise ValueError('stale receipt')
            raw = json.loads(data)
            if raw.get('remark') or not isinstance(raw.get('elements'), list):
                raise ValueError('incomplete extract')
        except (OSError, ValueError, KeyError, TypeError):
            error = None
            success = False
            for attempt in range(3):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                endpoint = ENDPOINTS[(index+attempt) % len(ENDPOINTS)]
                request = urllib.request.Request(endpoint, data=urllib.parse.urlencode({'data':query}).encode(), headers={'User-Agent':'TravelHandbookRouteExtract/2.0'})
                try:
                    with opener(request, timeout=min(35, remaining)) as response:
                        data = response.read(16*1024*1024+1)
                    if len(data) > 16*1024*1024:
                        raise ValueError('cell response exceeds 16 MiB; reduce route extent')
                    raw = json.loads(data)
                    if raw.get('remark') or not isinstance(raw.get('elements'), list):
                        raise ValueError('incomplete extract: '+str(raw.get('remark')))
                    atomic(path, data)
                    atomic(receipt, json.dumps({'query_sha256':key,'sha256':digest(data),'endpoint':endpoint}).encode())
                    success = True
                    break
                except (OSError, ValueError) as exc:
                    error = exc
                    if isinstance(exc, urllib.error.HTTPError) and exc.code not in {429,500,502,503,504}:
                        break
                    if attempt < 2:
                        delay = min(2**(attempt+1), max(0, deadline-time.monotonic()))
                        sleep(delay)
            else:
                raw = None
            if not success:
                raise RuntimeError(f'OSM job {index+1}/{len(queries)} incomplete: {error}; completed cells retained in {cache}. Rerun the same command to resume.')
        completed.append(path)
        print(f'OSM {index+1}/{len(queries)} ready', flush=True)
    target = out / 'osm-extract.json'
    temporary = target.with_suffix('.json.part')
    seen = set()
    with temporary.open('w', encoding='utf-8') as stream:
        stream.write('{"elements":[')
        first = True
        for path in completed:
            for item in json.loads(path.read_text('utf-8'))['elements']:
                identity = (item.get('type'), item.get('id'))
                if identity in seen:
                    continue
                seen.add(identity)
                if not first:
                    stream.write(',')
                json.dump(item, stream, ensure_ascii=False)
                first = False
        stream.write(']}')
    temporary.replace(target)
    atomic(out/'query.txt', '\n'.join(queries).encode())
    return json.loads(target.read_text('utf-8'))
