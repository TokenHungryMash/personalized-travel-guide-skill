"""Network-free regressions for serial acquisition, provenance and resumability."""
from email.message import Message
from email.utils import formatdate
from pathlib import Path
from unittest.mock import patch
import io
import json
import tempfile
import unittest
import urllib.error

from PIL import Image

from fetch_photos import (API, Deferred, FetchError, HttpClient, Pipeline, atomic_bytes,
                          atomic_json, digest, parameters, retry_after, user_agent,
                          writer_lock)


# No real email is embedded in tests and no test reaches the network. This URL is
# a syntax-valid test fixture, not an operator identity for live use.
CONTACT = 'https://localhost.test/photo-test-contact'


class Clock:
    def __init__(self):
        self.value = 1700000000.0
        self.sleeps = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


class Response(io.BytesIO):
    def __init__(self, value, headers=None):
        super().__init__(json.dumps(value).encode('utf8') if isinstance(value, dict) else value)
        self.headers = headers or {}


class Transport:
    def __init__(self, *results):
        self.results = list(results)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        if not self.results:
            raise AssertionError('Unexpected network request: ' + request.full_url)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def http_error(status, retry=None):
    headers = Message()
    if retry is not None:
        headers['Retry-After'] = str(retry)
    return urllib.error.HTTPError(API, status, 'Test response', headers, io.BytesIO(b''))


def photo_bytes(size=(37, 19)):
    output = io.BytesIO()
    Image.new('RGB', size, '#93705d').save(output, format='JPEG')
    return output.getvalue()


def search_response():
    return {'batchcomplete': True, 'query': {'pages': [
        {'pageid': 123, 'ns': 6, 'title': 'File:東京 building.jpg', 'index': 1,
         'imageinfo': [{'url': 'https://upload.wikimedia.org/wikipedia/commons/a/a1/building.jpg',
                        'thumburl': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/building.jpg/2400px-building.jpg',
                        'descriptionurl': 'https://commons.wikimedia.org/wiki/File:Building.jpg',
                        'width': 4000, 'height': 3000, 'thumbwidth': 2500, 'thumbheight': 1875,
                        'mime': 'image/jpeg', 'thumbmime': 'image/jpeg', 'sha1': 'commons-original-sha1',
                        'extmetadata': {'Artist': {'value': '<a href="/u">A &amp; B</a>'},
                                        'LicenseShortName': {'value': 'CC BY-SA 4.0'},
                                        'LicenseUrl': {'value': 'https://creativecommons.org/licenses/by-sa/4.0/'},
                                        'ImageDescription': {'value': '<p>Building in 東京</p>'}}}]}
    ]}}


class PhotoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / '.photo-cache'
        self.clock = Clock()

    def client(self, transport, contact=CONTACT):
        return HttpClient(self.cache, contact, opener=transport, sleep=self.clock.sleep,
                          now=self.clock.now, interval=0)

    def test_contact_required_and_placeholders_rejected_before_request(self):
        transport = Transport()
        for value in (None, '', 'person@example.com', 'https://example.org/contact', 'a@b.com\r\nX: 1'):
            with self.subTest(value=value), self.assertRaises(FetchError):
                self.client(transport, value).get(API)
        self.assertEqual(transport.requests, [])

    def test_descriptive_user_agent_and_no_browser_impersonation(self):
        transport = Transport(Response(b'ok'))
        self.assertEqual(self.client(transport).get(API), b'ok')
        self.assertEqual(transport.requests[0].get_header('User-agent'), user_agent(CONTACT))
        self.assertIn('PhotoBot/', user_agent(CONTACT))

    def test_429_exponential_backoff_is_two_four_eight(self):
        transport = Transport(http_error(429), http_error(429), http_error(429), Response(b'ok'))
        self.assertEqual(self.client(transport).get(API), b'ok')
        self.assertEqual(self.clock.sleeps, [2, 4, 8])
        self.assertEqual(len({request.full_url for request in transport.requests}), 1)

    def test_retry_after_seconds_and_http_date_are_minima(self):
        future = formatdate(self.clock.now() + 25, usegmt=True)
        transport = Transport(http_error(429, 10), http_error(503, future), Response(b'ok'))
        self.assertEqual(self.client(transport).get(API), b'ok')
        self.assertEqual(self.clock.sleeps, [10, 15])
        self.assertEqual(retry_after('not a date', self.clock.now()), 0)

    def test_maxlag_http_200_honors_five_second_minimum(self):
        transport = Transport(Response({'error': {'code': 'maxlag', 'info': 'lag'}}, {'Retry-After': '3'}),
                              Response({'batchcomplete': True}))
        self.client(transport).get(API, as_json=True)
        self.assertEqual(self.clock.sleeps, [5])

    def test_long_cooldown_survives_restart_without_network(self):
        first = Transport(http_error(429, 120))
        with self.assertRaises(Deferred):
            self.client(first).get(API)
        second = Transport()
        with self.assertRaises(Deferred):
            self.client(second).get(API)
        self.assertEqual(len(first.requests), 1)
        self.assertEqual(second.requests, [])
        self.clock.value += 120
        self.assertEqual(self.client(Transport(Response(b'ok'))).get(API), b'ok')

    def test_retry_exhaustion_is_bounded_and_saved(self):
        transport = Transport(*[http_error(429) for _ in range(4)])
        with self.assertRaisesRegex(FetchError, '3 retries exhausted'):
            self.client(transport).get(API)
        self.assertEqual(len(transport.requests), 4)
        state = json.loads((self.cache / 'network-state.json').read_text())
        self.assertGreater(state['notBefore'], self.clock.now())

    def test_permanent_403_does_not_retry(self):
        transport = Transport(http_error(403))
        with self.assertRaisesRegex(FetchError, 'HTTP 403'):
            self.client(transport).get(API)
        self.assertEqual(self.clock.sleeps, [])
        self.assertEqual(len(transport.requests), 1)

    def test_connection_and_truncated_response_retry(self):
        transport = Transport(urllib.error.URLError('offline'), Response(b'a', {'Content-Length': '5'}), Response(b'ok'))
        self.assertEqual(self.client(transport).get(API), b'ok')
        self.assertEqual(self.clock.sleeps, [2, 4])

    def test_network_rejects_untrusted_url_before_contact_is_sent(self):
        transport = Transport()
        for url in ('http://upload.wikimedia.org/a.jpg', 'https://wikimedia.org.evil.test/a.jpg'):
            with self.assertRaises(FetchError):
                self.client(transport).get(url)
        self.assertEqual(transport.requests, [])

    def test_search_metadata_and_download_are_not_identity_review(self):
        transport = Transport(Response(search_response()), Response(photo_bytes()))
        pipeline = Pipeline(self.root, self.client(transport))
        result = pipeline.run({'placeId': 'tokyo-test', 'query': 'specific venue Tokyo'}, download=True)
        candidate = pipeline.records['candidates'][0]
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(candidate['author'], 'A & B')
        self.assertEqual(candidate['license'], 'CC BY-SA 4.0')
        self.assertEqual(candidate['fileTitle'], 'File:東京 building.jpg')
        self.assertEqual(candidate['caption'], 'Building in 東京')
        self.assertFalse(candidate['reviewed'])
        self.assertIsNone(candidate['subjectPlaceId'])
        self.assertEqual(candidate['identityStatus'], 'unreviewed')
        self.assertEqual((candidate['width'], candidate['height']), (37, 19))
        self.assertEqual(candidate['requestedWidth'], 2400)
        self.assertEqual(candidate['apiWidth'], 2500)
        self.assertTrue((self.root / candidate['src']).is_file())
        self.assertEqual(candidate['sha256'], digest(photo_bytes()))
        self.assertFalse((self.root / 'place-photos.json').exists())
        self.assertEqual(len(transport.requests), 2)

    def test_same_command_resumes_without_network_or_contact(self):
        task = {'placeId': 'p', 'query': 'venue Tokyo'}
        pipeline = Pipeline(self.root, self.client(Transport(Response(search_response()), Response(photo_bytes()))))
        pipeline.run(task, download=True)
        pipeline.records['candidates'][0]['manualNote'] = 'Preserve reviewer notes'
        pipeline.save()
        transport = Transport()
        resumed = Pipeline(self.root, self.client(transport, None))
        result = resumed.run(task, download=True)
        self.assertTrue(result['fromCache'])
        self.assertEqual(transport.requests, [])
        self.assertEqual(resumed.records['candidates'][0]['manualNote'], 'Preserve reviewer notes')

    def test_refresh_keeps_local_file_and_review_state(self):
        task = {'placeId': 'p', 'query': 'venue Tokyo'}
        pipeline = Pipeline(self.root, self.client(Transport(Response(search_response()), Response(photo_bytes()))))
        pipeline.run(task, download=True)
        candidate = pipeline.records['candidates'][0]
        candidate.update(reviewed=True, identityStatus='reviewed', subjectPlaceId='p')
        pipeline.save()
        response = search_response()
        response['query']['pages'][0]['imageinfo'][0]['extmetadata']['Artist']['value'] = 'Corrected author'
        transport = Transport(Response(response))
        resumed = Pipeline(self.root, self.client(transport))
        resumed.run(task, download=True, refresh=True)
        self.assertTrue(resumed.records['candidates'][0]['reviewed'])
        self.assertEqual(resumed.records['candidates'][0]['author'], 'Corrected author')
        self.assertEqual(len(transport.requests), 1)

    def test_no_results_and_network_failure_are_distinct(self):
        empty = Pipeline(self.root, self.client(Transport(Response({'batchcomplete': True}))))
        self.assertEqual(empty.run({'placeId': 'p', 'query': 'none'})['status'], 'no_results')
        failing = Pipeline(self.root, self.client(Transport(http_error(403))))
        with self.assertRaises(FetchError):
            failing.run({'placeId': 'q', 'query': 'blocked'})
        self.assertEqual(failing.records['searches'][-1]['status'], 'failed')

    def test_invalid_json_api_error_and_unexpected_payload_are_not_cached(self):
        for body in (b'<html>blocked</html>', {'error': {'code': 'badvalue'}}, {}):
            with self.subTest(body=body):
                client = self.client(Transport(Response(body)))
                with self.assertRaises(FetchError):
                    client.query(parameters({'query': 'test'}, 1, 2400))
        self.assertEqual(len(list(self.cache.glob('*.json'))), 1)  # network-state only

    def test_failed_download_keeps_search_and_does_not_install_html(self):
        pipeline = Pipeline(self.root, self.client(Transport(Response(search_response()), Response(b'<html>blocked</html>'))))
        with self.assertRaises(FetchError):
            pipeline.run({'placeId': 'p', 'query': 'venue'}, download=True)
        self.assertEqual(pipeline.records['searches'][0]['status'], 'complete')
        self.assertEqual(pipeline.records['candidates'][0]['downloadStatus'], 'failed')
        self.assertEqual(list(self.root.rglob('*.jpg')), [])
        self.assertEqual(list(self.root.rglob('*.part')), [])

    def test_atomic_failure_preserves_existing_file(self):
        path = self.root / 'existing.jpg'
        path.write_bytes(b'previous-good-file')
        with patch('fetch_photos.os.replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                atomic_bytes(path, b'new-file')
        self.assertEqual(path.read_bytes(), b'previous-good-file')
        self.assertEqual(list(self.root.glob('*.part')), [])

    def test_interrupted_plan_resumes_completed_images(self):
        pipeline = Pipeline(self.root, self.client(Transport(Response(search_response()), Response(photo_bytes()), http_error(403))))
        first = {'placeId': 'one', 'query': 'venue one'}
        second = {'placeId': 'two', 'query': 'venue two'}
        pipeline.run(first, download=True)
        with self.assertRaises(FetchError):
            pipeline.run(second, download=True)
        transport = Transport(Response(search_response()), Response(photo_bytes()))
        resumed = Pipeline(self.root, self.client(transport))
        resumed.run(first, download=True)
        resumed.run(second, download=True)
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(len(resumed.records['candidates']), 2)

    def test_download_size_limit_and_missing_metadata_are_explicit(self):
        with self.assertRaisesRegex(FetchError, 'exceeds'):
            self.client(Transport(Response(b'123456'))).get(API, limit=5)
        response = search_response()
        response['query']['pages'][0]['imageinfo'][0]['extmetadata'] = {}
        pipeline = Pipeline(self.root, self.client(Transport(Response(response))))
        pipeline.run({'placeId': 'p', 'fileTitle': 'File:東京 building.jpg'})
        self.assertEqual(pipeline.records['candidates'][0]['missingMetadata'], ['author', 'license'])
        self.assertFalse(pipeline.records['candidates'][0]['reviewed'])

    def test_unknown_place_or_existing_schema_not_overwritten(self):
        atomic_json(self.root / 'content.json', {'places': [{'id': 'known'}]})
        transport = Transport()
        with self.assertRaisesRegex(FetchError, 'Unknown'):
            Pipeline(self.root, self.client(transport)).run({'placeId': 'wrong', 'query': 'x'})
        self.assertEqual(transport.requests, [])
        atomic_json(self.root / 'photo-records.json', {'legacy': 'keep'})
        with self.assertRaisesRegex(FetchError, 'unknown schema'):
            Pipeline(self.root, self.client(transport))
        self.assertEqual(json.loads((self.root / 'photo-records.json').read_text()), {'legacy': 'keep'})

    def test_workbench_lock_releases_and_rejects_second_writer(self):
        path = self.cache / 'fetch.lock'
        with writer_lock(path):
            with self.assertRaises(FetchError):
                with writer_lock(path):
                    self.fail('Second writer must be rejected')
        with writer_lock(path):
            pass

    def test_invalid_plan_values_fail_before_network(self):
        transport = Transport()
        pipeline = Pipeline(self.root, self.client(transport))
        for task in ({'placeId': 'p', 'query': ['not', 'text']},
                     {'placeId': 'p', 'query': '   '},
                     {'placeId': 'p', 'fileTitle': 'File:A.jpg|File:B.jpg'}):
            with self.subTest(task=task), self.assertRaises(FetchError):
                pipeline.run(task)
        self.assertEqual(transport.requests, [])


if __name__ == '__main__':
    unittest.main()
