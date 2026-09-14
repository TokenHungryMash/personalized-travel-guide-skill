"""Probe/download declared images concurrently; identity still requires visual QA."""
from __future__ import annotations
import argparse, hashlib, json, socket, time, threading, urllib.error, urllib.request
from _network_policy import address_allowed
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, urlsplit, urlunsplit, quote
from PIL import Image, ImageOps
MIN_WIDTH = 480
MIN_HEIGHT = 320
DELIVERY_MAX_EDGE = 1600
DELIVERY_QUALITY = 85

def validate_public_https_url(url):
    parsed = urlparse(url)
    if parsed.scheme.lower() != 'https' or not parsed.hostname:
        raise ValueError('image URL must use public HTTPS')
    if parsed.username or parsed.password:
        raise ValueError('image URL must not contain credentials')
    if parsed.port not in (None, 443):
        raise ValueError('image URL must use the default HTTPS port')
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f'image host cannot be resolved: {exc}') from exc
    if not addresses:
        raise ValueError('image host resolved to no addresses')
    for address in addresses:
        if not address_allowed(address, parsed.hostname):
            raise ValueError('image URL resolves to a non-public address')

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
SAFE_OPENER = urllib.request.build_opener(SafeRedirectHandler())

def contain_on_white(payload, target, mode='standard'):
    """Create a bounded delivery image while preserving visual content and provenance."""
    with Image.open(BytesIO(payload)) as source:
        source.load()
        image = ImageOps.exif_transpose(source)
        original = image.size
        needs_resize = max(original) > DELIVERY_MAX_EDGE
        oversized_payload = len(payload) > 2 * 1024 * 1024
        if not needs_resize and not oversized_payload:
            return (payload, source.width, source.height, None)
        if needs_resize:
            image.thumbnail((DELIVERY_MAX_EDGE, DELIVERY_MAX_EDGE), Image.Resampling.LANCZOS)
        output = BytesIO()
        suffix = target.suffix.lower()
        if suffix in {'.jpg', '.jpeg'}:
            image.convert('RGB').save(output, format='JPEG', quality=DELIVERY_QUALITY, optimize=True, progressive=True)
        elif suffix == '.webp':
            image.convert('RGB').save(output, format='WEBP', quality=DELIVERY_QUALITY, method=6)
        else:
            image.save(output, format='PNG', optimize=True)
        return (output.getvalue(), image.width, image.height, {'source_dimensions': list(original), 'delivery_resized': needs_resize, 'delivery_optimized': True})


def normalize_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@!$&'()*+,;=-._~"), quote(parts.query, safe="=&?/%:@!$'()*+,;~-._"), ''))
HOST_LOCKS = {}
HOST_LOCKS_GUARD = threading.Lock()
HOST_STOPPED = set()
HOST_LAST_REQUEST = {}

def fetch(task, retries, overwrite, mode='standard'):
    cached = cached_result(task, overwrite, mode)
    if cached is not None:
        return cached
    host = urlparse(str(task[1].get('download_url', ''))).hostname or ''
    with HOST_LOCKS_GUARD:
        lock = HOST_LOCKS.setdefault(host, threading.Semaphore(1))
    with lock:
        if host in HOST_STOPPED:
            place_id, image, _ = task
            error = 'host throttled earlier in this batch; queued request skipped'
            return ({'place_id': place_id, 'file': image.get('file'), 'status': 'failed', 'error': error}, error, False)
        # Wikimedia requests are serial and spaced, including failed requests.
        if host.endswith('wikimedia.org'):
            delay = 3 - (time.monotonic() - HOST_LAST_REQUEST.get(host, 0))
            if delay > 0:
                time.sleep(delay)
        result = _fetch(task, retries, overwrite, mode)
        HOST_LAST_REQUEST[host] = time.monotonic()
        if result[0].get('http_status') == 429:
            HOST_STOPPED.add(host)
        return result

def cached_result(task, overwrite, mode='standard'):
    place_id, image, target = task
    url, name = (str(image.get('download_url', '')).strip(), str(image.get('file', '')).strip())
    receipt = image.get('_fetch_receipt', {})
    # Permanent source failures remain useful until the URL/source changes.
    # --overwrite explicitly retries; transient/network-policy failures are never cached.
    if (not overwrite and receipt.get('status') == 'failed'
            and receipt.get('http_status') in {404, 410}
            and urlparse(url).hostname != 'wsrv.nl'
            and receipt.get('download_url') == url
            and receipt.get('source_page') == image.get('source_page')):
        error = 'unchanged source previously returned HTTP ' + str(receipt['http_status']) + '; select another verified URL or use --overwrite to retry'
        return ({**receipt, 'place_id': place_id, 'file': name, 'error': error, 'cached_failure': True}, error, False)
    if target.exists() and (not overwrite) and (receipt.get('download_url') == url) and (receipt.get('source_page') == image.get('source_page')) and (receipt.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest()):
        try:
            current = target.read_bytes()
            optimized, width, height, derivative = contain_on_white(current, target, mode)
            if derivative:
                temporary = target.with_suffix(target.suffix + '.part')
                temporary.write_bytes(optimized)
                temporary.replace(target)
                receipt = {**receipt, 'sha256': hashlib.sha256(optimized).hexdigest(), **derivative}
                image['_fetch_receipt'] = receipt
                image.update({'width': width, 'height': height, **derivative})
            with Image.open(target) as existing:
                existing.verify()
            if width > 0 and height > 0:
                row = {**receipt, 'place_id': place_id, 'file': name, 'status': 'cached', 'width': width, 'height': height}
                if image.get('padding_mode') == 'contain_white_no_upscale':
                    row.update({'padded': True, 'padding_mode': 'contain_white_no_upscale', 'source_width': image.get('source_width'), 'source_height': image.get('source_height')})
                return (row, None, False)
        except Exception:
            pass
    return None

def _fetch(task, retries, overwrite, mode='standard'):
    cached = cached_result(task, overwrite, mode)
    if cached is not None:
        return cached
    place_id, image, target = task
    url, name = (str(image.get('download_url', '')).strip(), str(image.get('file', '')).strip())
    request_url = normalize_url(url)
    if not url:
        msg = f'{place_id} {name}: local file is missing/invalid and no download_url was supplied'
        return ({'place_id': place_id, 'file': name, 'status': 'failed', 'error': msg}, msg, False)
    try:
        request_url = normalize_url(request_url)
        validate_public_https_url(request_url)
    except Exception as exc:
        msg = f'{place_id} {url}: {exc}'
        return ({'place_id': place_id, 'file': name, 'status': 'failed', 'error': str(exc)}, msg, False)
    error = None
    for attempt in range(max(0, retries) + 1):
        try:
            request = urllib.request.Request(request_url, headers={'User-Agent': 'Mozilla/5.0 travel-handbook-asset-fetcher/3.0'})
            with SAFE_OPENER.open(request, timeout=18) as response:
                mime = response.headers.get('Content-Type', '').split(';', 1)[0].lower()
                if not (mime.startswith('image/') or mime in {'', 'application/octet-stream'}):
                    raise ValueError(f'not an image response: {mime}')
                payload = response.read(25 * 1024 * 1024 + 1)
            if len(payload) > 25 * 1024 * 1024:
                raise ValueError('image exceeds 25 MiB limit')
            with Image.open(BytesIO(payload)) as decoded:
                decoded.verify()
            payload, width, height, derivative = contain_on_white(payload, target, mode)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + '.part')
            temporary.write_bytes(payload)
            temporary.replace(target)
            update = {'http_accessible': True, 'url_checked_at': datetime.now(timezone.utc).isoformat(), 'mime_type': mime, 'width': width, 'height': height}
            row = {'place_id': place_id, 'file': name, 'status': 'ok', 'mime_type': mime, 'width': width, 'height': height}
            receipt = {'download_url': url, 'source_page': image.get('source_page'), 'sha256': hashlib.sha256(payload).hexdigest()}
            if derivative:
                update.update(derivative)
                receipt.update(derivative)
            update['_fetch_receipt'] = receipt
            row.update(receipt)
            image.update(update)
            return (row, None, True)
        except Exception as exc:
            error = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                break  # Stop the host queue; a short retry is not a backoff.
            transient_http = isinstance(exc, urllib.error.HTTPError) and exc.code in {429, 500, 502, 503, 504}
            transient_network = not isinstance(exc, urllib.error.HTTPError) and isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError))
            transient_http = transient_http or (isinstance(exc, urllib.error.HTTPError) and exc.code == 404 and (urlparse(request_url).hostname == 'wsrv.nl'))
            if (transient_http or transient_network) and attempt < retries:
                time.sleep(min(4, 2 ** attempt))
                continue
            break
    msg = f'{place_id} {url}: {error}'
    return ({'place_id': place_id, 'file': name, 'status': 'failed', 'error': str(error), 'http_status': getattr(error, 'code', None), 'download_url': url, 'source_page': image.get('source_page')}, msg, False)

def collect_tasks(data, asset_root, selected, receipts):
    """Collect cover and place assets using the same cache and path checks."""
    failures, tasks = ([], [])
    declarations = list(data.get('places', []))
    cover = data.get('cover')
    if isinstance(cover, dict) and cover.get('image'):
        if not isinstance(cover['image'], str):
            failures.append('__cover__: cover.image must be a file path string')
        else:
            cover['file'] = cover['image']
            declarations.append({'id': '__cover__', 'images': [cover]})
    for place in declarations:
        place_id = str(place.get('id', ''))
        if selected and place_id not in selected:
            continue
        for image in place.get('images', []):
            if not isinstance(image, dict):
                continue
            name = str(image.get('file') or image.get('local_file') or '').strip()
            if name:
                image['file'] = name
            if not name and image.get('download_url'):
                suffix = Path(urlparse(str(image['download_url'])).path).suffix.lower()
                if suffix not in {'.jpg', '.jpeg', '.png', '.webp'}:
                    suffix = '.jpg'
                name = f'assets/places/{place_id}{suffix}'
                image['file'] = name
            if not name:
                failures.append(f'{place_id}: image declaration needs file')
                continue
            latest = receipts.get((place_id, name), {})
            if (not image.get('_fetch_receipt') or
                    (latest.get('download_url') == image.get('download_url') and
                     latest.get('source_page') == image.get('source_page'))):
                image['_fetch_receipt'] = latest
            target = (asset_root / name).resolve()
            if not target.is_relative_to(asset_root.resolve()):
                failures.append(f'{place_id}: asset file must stay inside asset_root')
                continue
            tasks.append((place_id, image, target))
    # A cover or an explicitly shared place may own the same physical image.
    # Different sources cannot safely write to that one target, even serially.
    target_sources = {}
    for _, image, target in tasks:
        target_sources.setdefault(target, set()).add((str(image.get('download_url', '')).strip(), str(image.get('source_page', ''))))
    if selected:
        # A bounded repair must not overwrite a file owned by an unselected row.
        for place in declarations:
            if str(place.get('id', '')) in selected:
                continue
            for image in place.get('images', []):
                if not isinstance(image, dict):
                    continue
                name = str(image.get('file') or image.get('local_file') or '').strip()
                if not name:
                    continue
                target = (asset_root / name).resolve()
                if target in target_sources:
                    target_sources[target].add((str(image.get('download_url', '')).strip(), str(image.get('source_page', ''))))
    conflicts = {target for target, sources in target_sources.items() if len(sources) > 1}
    for target in sorted(conflicts):
        failures.append(f'{target.relative_to(asset_root.resolve())}: conflicting image sources share one file; use distinct paths or correct the source declarations')
    return ([task for task in tasks if task[2] not in conflicts], failures)

def fetch_group(tasks, retries, overwrite, mode='standard'):
    """Acquire one shared file, retaining a separate receipt for each declaration.

    collect_tasks has already rejected differing URL/source bindings per target.
    Sharing acquisition bytes never copies visual/subject identity approval.
    """
    leader, result, failed_cache = tasks[0], None, None
    if len(tasks) > 1:
        for task in tasks:
            cached = cached_result(task, overwrite, mode)
            if cached is not None:
                if cached[0].get('status') == 'cached':
                    leader, result = task, cached
                    break
                failed_cache = (task, cached)
        if result is None and failed_cache is not None:
            leader, result = failed_cache
    if result is None:
        result = fetch(leader, retries, overwrite, mode)
    row, error, downloaded = result
    results = []
    for task in tasks:
        if task is leader:
            results.append(result)
            continue
        place_id, image, _ = task
        shared = {**row, 'place_id': place_id, 'file': image['file'], 'reused_from_place_id': leader[0]}
        if error is None:
            shared['status'] = 'cached'
            image['_fetch_receipt'] = dict(shared)
            for key in ('http_accessible', 'url_checked_at', 'mime_type', 'width', 'height',
                        'source_dimensions', 'delivery_resized', 'delivery_optimized'):
                if key in leader[1]:
                    image[key] = leader[1][key]
            image.update({key: shared[key] for key in ('width', 'height') if key in shared})
        results.append((shared, error, False))
    return results

def write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)

def checkpoint_report(path, previous_rows, new_rows):
    """Persist completed download results atomically before other workers finish."""
    merged = {(row.get('place_id'), row.get('file')): row for row in previous_rows if isinstance(row, dict) and row.get('file')}
    merged.update({(row.get('place_id'), row.get('file')): row for row in new_rows if row.get('file')})
    write_json_atomic(path, list(merged.values()))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', type=Path)
    parser.add_argument('asset_root', type=Path)
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--place-id', action='append', default=[])
    parser.add_argument('--retries', type=int, default=1)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--resume-report', type=Path, action='append', default=[], help='Additional existing downloader report to reuse; URL/source/hash must still match')
    args = parser.parse_args()
    data = json.loads(args.profile.read_text(encoding='utf-8'))
    selected = set(args.place_id)
    failures, report, tasks = ([], [], [])
    previous_path = args.asset_root / 'asset-fetch-report.json'
    try:
        previous_rows = json.loads(previous_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        previous_rows = []
    receipt_rows = []
    for path in args.resume_report:
        rows = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(rows, list):
            parser.error('--resume-report must contain an array from the downloader')
        receipt_rows.extend(rows)
    receipt_rows.extend(previous_rows)
    receipts = {(row.get('place_id'), row.get('file')): row for row in receipt_rows if isinstance(row, dict) and row.get('status') in {'ok', 'cached', 'failed'}}
    tasks, failures = collect_tasks(data, args.asset_root, selected, receipts)
    groups = {}
    for task in tasks:
        groups.setdefault(task[2], []).append(task)
    downloaded = 0
    print(f'FETCH START tasks={len(tasks)} unique_files={len(groups)}; completed receipts are checkpointed; use --place-id for bounded batches', flush=True)
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 12))) as pool:
        for future in as_completed([pool.submit(fetch_group, group, args.retries, args.overwrite, 'standard') for group in groups.values()]):
            for row, failure, did_download in future.result():
                report.append(row)
                checkpoint_report(previous_path, previous_rows, report)
                print(f"FETCH {len(report)}/{len(tasks)} {row.get('place_id')} {row.get('status')}", flush=True)
                downloaded += int(did_download)
                if failure:
                    failures.append(failure)
    write_json_atomic(args.profile, data)
    args.asset_root.mkdir(parents=True, exist_ok=True)
    provenance_path = args.asset_root / 'RESEARCH_PROVENANCE.json'
    if provenance_path.is_file():
        import hashlib
        provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
        provenance['profile_sha256'] = hashlib.sha256(args.profile.read_bytes()).hexdigest()
        write_json_atomic(provenance_path, provenance)
    report_path = args.asset_root / 'asset-fetch-report.json'
    if selected and report_path.is_file():
        try:
            previous = json.loads(report_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            previous = []
        merged = {(str(row.get('place_id')), str(row.get('file'))): row for row in previous if isinstance(row, dict) and row.get('file')}
        merged.update({(str(row.get('place_id')), str(row.get('file'))): row for row in report if row.get('file')})
        report = list(merged.values())
    report.sort(key=lambda row: (row.get('place_id', ''), row.get('file', '')))
    for row in report:
        if row.get('status') in {'ok', 'cached'} and (row.get('width', 0) < MIN_WIDTH or row.get('height', 0) < MIN_HEIGHT):
            row['resolution_warning'] = 'Low resolution accepted in standard mode; do not replace solely for dimensions.'
            print(f"WARN low resolution retained: {row.get('file')} ({row.get('width')}x{row.get('height')})")
    write_json_atomic(report_path, report)
    print(f'downloaded={downloaded}; workers={max(1, min(args.workers, 12))}; report=asset-fetch-report.json; identity is NOT verified by download success')
    for failure in failures:
        print('FAIL ' + failure)
    return 2 if failures else 0
if __name__ == '__main__':
    raise SystemExit(main())
