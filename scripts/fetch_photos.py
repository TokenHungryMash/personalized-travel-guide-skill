"""Fetch small, serial Wikimedia Commons photo candidate sets; never assert identity.

Requires Pillow (already in the workbench requirements). Network traffic requires
the operator's real contact via --contact or JOURNAL_MEDIA_CONTACT. See
references/photo-pipeline.md for review/promotion and the record schema.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import http.client
import io
import json
import math
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image


API = 'https://commons.wikimedia.org/w/api.php'
BACKOFF = (2, 4, 8)
FORMATS = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp', 'TIFF': '.tif', 'GIF': '.gif'}
RETRY_CODES = {429, 500, 502, 503, 504}
MAX_BYTES = 50 * 1024 * 1024


class FetchError(RuntimeError):
    """An actionable acquisition failure, never a claim that no photo exists."""


class Deferred(FetchError):
    """A server cooldown is too long for this invocation; state is preserved."""


def stamp(epoch=None):
    return datetime.fromtimestamp(time.time() if epoch is None else epoch, timezone.utc).isoformat(timespec='seconds')


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf8')).hexdigest()


def atomic_bytes(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.part', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8'))


def read_json(path, default=None):
    return json.loads(Path(path).read_text(encoding='utf-8-sig')) if Path(path).exists() else default


def user_agent(contact):
    contact = (contact or '').strip()
    if not contact or any(ord(char) < 32 or ord(char) > 126 for char in contact):
        raise FetchError('Set --contact or JOURNAL_MEDIA_CONTACT to your real email or HTTPS contact page; no network request was made.')
    email = re.fullmatch(r'[^\s@()<>]+@([^\s@()<>]+\.[^\s@()<>]+)', contact)
    url = urllib.parse.urlsplit(contact)
    host = email.group(1) if email else (url.hostname if url.scheme == 'https' and not url.username and not url.password else None)
    if not host or any(host == domain or host.endswith('.' + domain) for domain in ('example.com', 'example.org', 'example.net', 'invalid', 'localhost')):
        raise FetchError('Contact must be a real operator email or HTTPS contact page, not a placeholder. Its ownership cannot be verified by this script.')
    return f'TravelMagazinePhotoBot/1.0 ({contact})'


def retry_after(value, now):
    if not value:
        return 0
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - now
        except (TypeError, ValueError, OverflowError):
            return 0
    return max(0, seconds) if math.isfinite(seconds) else 0


def wikimedia_url(url):
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme == 'https' and not parsed.username and not parsed.password
            and parsed.port in (None, 443) and bool(parsed.hostname)
            and (parsed.hostname == 'wikimedia.org' or parsed.hostname.endswith('.wikimedia.org')))


class WikimediaRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if not wikimedia_url(newurl):
            raise FetchError('Refusing a redirect outside HTTPS Wikimedia hosts: ' + newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class HttpClient:
    """Single synchronous connection at a time, bounded retries and durable cooldown.

    A long Retry-After is never shortened. The next invocation reads the same
    notBefore value. Cache refresh does not reset it or change host/user agent.
    """
    def __init__(self, cache, contact=None, *, opener=None, sleep=time.sleep, now=time.time,
                 max_wait=60, interval=1):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.state_path = self.cache / 'network-state.json'
        self.state = read_json(self.state_path, {})
        self.contact = contact
        self.opener = opener or urllib.request.build_opener(WikimediaRedirect()).open
        self.sleep, self.now, self.max_wait, self.interval = sleep, now, max_wait, interval

    def cooldown(self, seconds, reason):
        self.state['notBefore'] = max(float(self.state.get('notBefore', 0)), self.now() + seconds)
        self.state['reason'] = reason
        atomic_json(self.state_path, self.state)

    def wait_ready(self):
        delay = max(0, float(self.state.get('notBefore', 0)) - self.now())
        if delay > self.max_wait:
            raise Deferred(f"Cooldown until {stamp(self.state['notBefore'])}; resume later with the same command. {self.state.get('reason', '')}")
        if delay:
            self.sleep(delay)

    def validate_url(self, url):
        if not wikimedia_url(url):
            raise FetchError('Only API-provided HTTPS Wikimedia URLs are supported: ' + url)

    def request_agent(self, url):
        return user_agent(self.contact)

    def get(self, url, *, as_json=False, limit=MAX_BYTES):
        self.validate_url(url)
        agent = self.request_agent(url)  # Validate before even the first request.
        for attempt in range(len(BACKOFF) + 1):
            self.wait_ready()
            headers = {}
            minimum = 0
            try:
                request = urllib.request.Request(url, headers={'User-Agent': agent, 'Accept': 'application/json' if as_json else 'image/*'})
                with self.opener(request, timeout=45) as response:
                    headers = response.headers
                    chunks, size = [], 0
                    while True:
                        chunk = response.read(min(65536, limit + 1 - size))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        size += len(chunk)
                        if size > limit:
                            raise FetchError(f'Response exceeds {limit} bytes; no file was installed.')
                    length = headers.get('Content-Length')
                    if length and str(length).isdigit() and size != int(length):
                        raise http.client.IncompleteRead(b''.join(chunks), int(length) - size)
                    body = b''.join(chunks)
                value = body
                if as_json:
                    try:
                        value = json.loads(body)
                    except (ValueError, UnicodeError) as error:
                        raise FetchError('API returned invalid JSON; this is a failed search, not no results.') from error
                    if not isinstance(value, dict):
                        raise FetchError('Unexpected API response type.')
                    error = value.get('error')
                    if error:
                        code = error.get('code', 'unknown')
                        if code not in ('maxlag', 'ratelimited', 'readonly'):
                            raise FetchError(f"API error {code}: {error.get('info', '')}")
                        minimum = 5 if code == 'maxlag' else 0
                        reason = f'API {code}'
                    else:
                        self.cooldown(self.interval, 'Serial request spacing')
                        return value
                else:
                    self.cooldown(self.interval, 'Serial request spacing')
                    return value
            except urllib.error.HTTPError as error:
                headers = error.headers or {}
                code = error.code
                error.close()
                if code not in RETRY_CODES:
                    raise FetchError(f'HTTP {code}; stopped without changing host or User-Agent.') from error
                minimum = 5 if headers.get('X-Database-Lag') else 0
                reason = f'HTTP {code}'
            except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as error:
                reason = 'Transient connection failure: ' + str(error)
            wait = max(BACKOFF[min(attempt, len(BACKOFF) - 1)], minimum, retry_after(headers.get('Retry-After'), self.now()))
            self.cooldown(wait, reason)
            if attempt == len(BACKOFF):
                raise FetchError(f'{reason}; 3 retries exhausted. State saved; do not bypass the cooldown.')
        raise AssertionError('Unreachable')

    def query(self, params, *, refresh=False):
        url = API + '?' + urllib.parse.urlencode(sorted(params.items()))
        path = self.cache / (digest(url) + '.json')
        cached = read_json(path)
        if cached and not refresh:
            return cached['response'], cached['fetchedAt'], True
        response = self.get(url, as_json=True, limit=4 * 1024 * 1024)
        if 'query' not in response and 'batchcomplete' not in response:
            raise FetchError('Unexpected API response; refusing to record it as no results.')
        fetched = stamp(self.now())
        atomic_json(path, {'url': url, 'fetchedAt': fetched, 'response': response})
        return response, fetched, False


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value):
    parser = PlainText()
    parser.feed(str(value or ''))
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()


def parameters(task, limit, width):
    params = {'action': 'query', 'format': 'json', 'formatversion': 2, 'maxlag': 5,
              'prop': 'imageinfo', 'iiprop': 'url|size|mime|thumbmime|sha1|extmetadata',
              'iiextmetadatafilter': 'Artist|LicenseShortName|LicenseUrl|ImageDescription|Credit|Attribution|DateTimeOriginal',
              'iiurlwidth': width}
    if task.get('fileTitle'):
        params['titles'] = task['fileTitle']
    else:
        params.update(generator='search', gsrsearch=task['query'], gsrnamespace=6, gsrlimit=limit)
    return params


def candidate_from_page(page, place_id):
    infos = page.get('imageinfo') or []
    if not infos:
        return None
    info = infos[0]
    metadata = info.get('extmetadata') or {}
    field = lambda key: plain((metadata.get(key) or {}).get('value'))
    url = info.get('thumburl') or info.get('url', '')
    identity = '\n'.join([place_id, page['title'], info.get('sha1', ''), url])
    author, license_name = field('Artist'), field('LicenseShortName')
    candidate = {'candidateId': digest(identity)[:24], 'placeId': place_id,
                 'fileTitle': page['title'], 'page': info.get('descriptionurl', ''),
                 'author': author, 'license': license_name, 'licenseUrl': field('LicenseUrl'),
                 'credit': field('Credit'), 'attribution': field('Attribution'),
                 'caption': field('ImageDescription'), 'source': url,
                 'originalUrl': info.get('url', ''), 'commonsSha1': info.get('sha1', ''),
                 'originalWidth': info.get('width'), 'originalHeight': info.get('height'),
                 'apiWidth': info.get('thumbwidth', info.get('width')),
                 'apiHeight': info.get('thumbheight', info.get('height')),
                 'mime': info.get('thumbmime', info.get('mime', '')),
                 'dateTaken': field('DateTimeOriginal'),
                 'reviewed': False, 'identityStatus': 'unreviewed', 'subjectPlaceId': None,
                 'role': None, 'src': None, 'downloadStatus': 'not_downloaded'}
    candidate['missingMetadata'] = [key for key in ('fileTitle', 'page', 'author', 'license') if not candidate[key]]
    return candidate


def image_details(body):
    try:
        with Image.open(io.BytesIO(body)) as image:
            width, height, image_format = image.width, image.height, image.format
            image.verify()
        with Image.open(io.BytesIO(body)) as image:
            image.load()  # Detect truncated streams that verify() alone may accept.
    except Exception as error:
        raise FetchError('Download is not a complete, decodable image; no file was installed.') from error
    if image_format not in FORMATS or width < 1 or height < 1:
        raise FetchError('Unsupported image format; use a Commons raster thumbnail or another candidate.')
    return width, height, FORMATS[image_format]


def local_file(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise FetchError('Candidate path escapes the workbench.')
    return path


class Pipeline:
    def __init__(self, root, client):
        self.root, self.client = Path(root).resolve(), client
        self.path = self.root / 'photo-records.json'
        self.records = read_json(self.path, {'schemaVersion': 1, 'searches': [], 'candidates': []})
        if (self.records.get('schemaVersion') != 1 or not isinstance(self.records.get('searches'), list)
                or not isinstance(self.records.get('candidates'), list)):
            raise FetchError('Existing photo-records.json uses an unknown schema; left untouched.')

    def save(self):
        atomic_json(self.path, self.records)

    def download(self, candidate):
        if candidate.get('src') and candidate.get('sha256'):
            path = local_file(self.root, candidate['src'])
            if path.is_file():
                body = path.read_bytes()
                if digest(body) == candidate['sha256']:
                    image_details(body)
                    candidate['downloadStatus'] = 'downloaded'
                    return
            if candidate.get('reviewed'):
                raise FetchError('A reviewed candidate is missing or changed; do not silently replace it. Recheck its identity first.')
        body = self.client.get(candidate['source'])
        width, height, suffix = image_details(body)
        relative = f"media/photo-candidates/{candidate['candidateId']}{suffix}"
        atomic_bytes(local_file(self.root, relative), body)
        candidate.update(src=relative, width=width, height=height, sha256=digest(body),
                         bytes=len(body), downloadedAt=stamp(self.client.now()), downloadStatus='downloaded')
        candidate.pop('lastError', None)

    def run(self, task, *, limit=3, width=2400, download=False, refresh=False):
        if not 1 <= limit <= 3 or not 64 <= width <= 4096:
            raise FetchError('Use 1–3 candidates and a requested width between 64 and 4096 pixels.')
        place_id = task.get('placeId')
        if not isinstance(place_id, str) or not place_id.strip():
            raise FetchError('Each task requires a nonempty placeId.')
        if bool(task.get('query')) == bool(task.get('fileTitle')):
            raise FetchError('Each task requires exactly one query or fileTitle.')
        for key in ('query', 'fileTitle'):
            if task.get(key) and (not isinstance(task[key], str) or not task[key].strip()):
                raise FetchError(key + ' must be a nonempty string.')
        if task.get('fileTitle') and not task['fileTitle'].startswith('File:'):
            raise FetchError('Use the canonical Commons File: title.')
        if task.get('fileTitle') and '|' in task['fileTitle']:
            raise FetchError('Use one File: title per task, not a batch of titles.')
        content = read_json(self.root / 'content.json')
        if content is not None and place_id not in {place['id'] for place in content.get('places', [])}:
            raise FetchError('Unknown content.json placeId: ' + place_id)
        params = parameters(task, limit, width)
        search_id = digest(json.dumps([place_id, params], sort_keys=True, ensure_ascii=False))[:24]
        search = next((item for item in self.records['searches'] if item['searchId'] == search_id), None)
        if search is None:
            search = dict(searchId=search_id, placeId=place_id, query=task.get('query'), fileTitle=task.get('fileTitle'),
                          candidateIds=[], status='pending')
            self.records['searches'].append(search)
        search.update(status='searching', attemptedAt=stamp(self.client.now()))
        self.save()
        try:
            response, fetched, cached = self.client.query(params, refresh=refresh)
            pages = response.get('query', {}).get('pages', [])
            if not isinstance(pages, list):
                raise FetchError('Unexpected API pages structure; no candidates imported.')
            found = []
            known = {candidate['candidateId']: candidate for candidate in self.records['candidates']}
            for page in sorted(pages, key=lambda entry: entry.get('index', 0)):
                candidate = candidate_from_page(page, place_id)
                if candidate is None:
                    continue
                candidate.update(requestedWidth=width, metadataCheckedAt=fetched)
                existing = known.get(candidate['candidateId'])
                if existing is None:
                    candidate['discoveredAt'] = fetched
                    self.records['candidates'].append(candidate)
                else:
                    # Refresh provenance without erasing review/local-file history.
                    # An older cache entry must not undo more recent metadata.
                    if fetched >= existing.get('metadataCheckedAt', ''):
                        protected = {'reviewed', 'identityStatus', 'subjectPlaceId', 'role', 'src', 'downloadStatus'}
                        if existing.get('reviewed'):
                            protected.add('caption')
                        existing.update({key: value for key, value in candidate.items() if key not in protected})
                    candidate = existing
                found.append(candidate)
            search.update(status='complete' if found else 'no_results', checkedAt=fetched, fromCache=cached,
                          candidateIds=[item['candidateId'] for item in found], warnings=response.get('warnings', {}))
            search.pop('lastError', None)
            self.save()
            if download:
                for candidate in found:
                    try:
                        self.download(candidate)
                    except (FetchError, OSError) as error:
                        candidate.update(downloadStatus='failed', lastError=str(error))
                        self.save()
                        raise
                    self.save()
            return search
        except (FetchError, OSError, ValueError, KeyboardInterrupt) as error:
            # A failed download does not erase evidence of a successful search.
            if search['status'] == 'searching':
                search['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
            search['lastError'] = str(error) or 'Interrupted'
            self.save()
            raise


@contextmanager
def writer_lock(path):
    """OS lock releases on a crash; no stale PID lock prevents checkpoint recovery."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise FetchError('Another photo fetcher is using this workbench; wait for it to finish.') from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    parser.add_argument('--place-id')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--query', help='A specific place name plus city; File namespace is automatic')
    group.add_argument('--file-title', help='Exact Commons File: title for metadata and download')
    group.add_argument('--plan', type=Path, help='JSON list of {placeId, query} or {placeId, fileTitle}')
    parser.add_argument('--contact', default=os.environ.get('JOURNAL_MEDIA_CONTACT'))
    parser.add_argument('--limit', type=int, choices=(1, 2, 3), default=3)
    parser.add_argument('--width', type=int, default=2400)
    parser.add_argument('--download', action='store_true', help='Download candidates; never mark them reviewed')
    parser.add_argument('--refresh', action='store_true', help='Refresh API metadata, retaining downloads and server cooldown')
    args = parser.parse_args(argv)
    root = args.workbench.resolve()
    if not root.is_dir():
        parser.error('workbench must be an existing directory')
    if not args.plan and not args.place_id:
        parser.error('--place-id is required with --query or --file-title')
    if args.plan and args.place_id:
        parser.error('--place-id cannot be combined with --plan')
    try:
        tasks = read_json(args.plan) if args.plan else [dict(placeId=args.place_id, query=args.query, fileTitle=args.file_title)]
        if not isinstance(tasks, list) or not tasks or not all(isinstance(task, dict) for task in tasks):
            raise FetchError('Plan must be a nonempty JSON list of task objects.')
        cache = root / '.photo-cache'
        with writer_lock(cache / 'fetch.lock'):
            pipeline = Pipeline(root, HttpClient(cache, args.contact))
            for task in tasks:  # Deliberately serial; first network failure stops the plan.
                result = pipeline.run(task, limit=args.limit, width=args.width, download=args.download, refresh=args.refresh)
                print(json.dumps(result, ensure_ascii=False))
        print('Saved photo-records.json. Candidates remain unreviewed; inspect identity before copying into place-photos.json.')
        return 0
    except (FetchError, OSError, ValueError) as error:
        print('Photo acquisition stopped: ' + str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Interrupted; completed searches and downloads are saved. Rerun the same command.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
