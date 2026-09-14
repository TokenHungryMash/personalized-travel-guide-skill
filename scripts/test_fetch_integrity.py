"""Offline checks for shared acquisitions and interruption-safe resume data."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import fetch_declared_assets as assets


class FetchIntegrity(unittest.TestCase):
    def run_fetch(self, root, profile, opener):
        profile_path = root / 'profile.json'
        profile_path.write_text(json.dumps(profile), encoding='utf-8')
        with patch('sys.argv', ['fetch', str(profile_path), str(root)]), \
                patch.object(assets, 'validate_public_https_url'), \
                patch.object(assets, 'HOST_STOPPED', set()), \
                patch.object(assets.SAFE_OPENER, 'open', side_effect=opener) as opened, \
                contextlib.redirect_stdout(io.StringIO()):
            status = assets.main()
        return status, opened.call_count, json.loads(profile_path.read_text(encoding='utf-8'))

    def test_cover_and_same_place_reuse_one_acquisition_with_separate_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            buffer = io.BytesIO()
            Image.new('RGB', (600, 400), 'blue').save(buffer, format='PNG')
            payload = buffer.getvalue()
            declaration = {'file': 'shared.png', 'download_url': 'https://images.test/shared.png',
                           'source_page': 'https://images.test/place'}
            profile = {'cover': {**declaration, 'image': 'shared.png'}, 'places': [
                {'id': 'sight', 'images': [dict(declaration)]},
                {'id': 'activity', 'same_place_as': 'sight', 'images': [dict(declaration)]}]}
            def response(*args, **kwargs):
                body = io.BytesIO(payload)
                body.headers = {'Content-Type': 'image/png'}
                return body
            status, requests, saved = self.run_fetch(root, profile, response)
            self.assertEqual(status, 0)
            self.assertEqual(requests, 1)
            rows = json.loads((root / 'asset-fetch-report.json').read_text(encoding='utf-8'))
            self.assertEqual({row['place_id'] for row in rows}, {'sight', 'activity', '__cover__'})
            self.assertEqual(sum(row['status'] == 'ok' for row in rows), 1)
            self.assertTrue(all(row['sha256'] == hashlib.sha256(payload).hexdigest() for row in rows))
            self.assertNotIn('source_identity_bound', saved['cover'])
            self.assertTrue(all('_fetch_receipt' in place['images'][0] for place in saved['places']))

    def test_conflicting_sources_cannot_overwrite_one_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'shared.png'
            target.write_bytes(b'existing user bytes')
            profile = {'places': [{'id': name, 'images': [{'file': 'shared.png',
                'download_url': 'https://images.test/' + name + '.png'}]} for name in ['a', 'b']]}
            status, requests, _ = self.run_fetch(root, profile, AssertionError('conflicts must fail before network'))
            self.assertEqual(status, 2)
            self.assertEqual(requests, 0)
            self.assertEqual(target.read_bytes(), b'existing user bytes')
            tasks, failures = assets.collect_tasks(profile, root, {'a'}, {})
            self.assertEqual(tasks, [])
            self.assertTrue(any('conflicting image sources' in failure for failure in failures))

    def test_failed_atomic_replace_preserves_previous_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'asset-fetch-report.json'
            path.write_text('[{"status":"ok"}]', encoding='utf-8')
            with patch.object(Path, 'replace', side_effect=OSError('interrupted replace')):
                with self.assertRaises(OSError):
                    assets.write_json_atomic(path, [{'status': 'new'}])
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), [{'status': 'ok'}])

    def test_shared_group_prefers_verified_cache_and_overwrite_fetches_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'shared.png'
            Image.new('RGB', (600, 400), 'blue').save(target)
            image = {'file': 'shared.png', 'download_url': 'https://images.test/shared.png',
                     'source_page': 'https://images.test/place'}
            valid = {**image, '_fetch_receipt': {**image,
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}}
            failed = {**image, '_fetch_receipt': {**image, 'status': 'failed', 'http_status': 404}}
            tasks = [('new', dict(image), target), ('failed', failed, target), ('cached', valid, target)]
            with patch.object(assets, 'fetch', side_effect=AssertionError('valid shared cache must win')):
                results = assets.fetch_group(tasks, 1, False)
            self.assertTrue(all(row['status'] == 'cached' and error is None and not downloaded
                                for row, error, downloaded in results))
            with patch.object(assets, 'fetch', return_value=({'status': 'failed'}, 'forced attempt failed', False)) as fetch:
                results = assets.fetch_group(tasks, 1, True)
            self.assertEqual(fetch.call_count, 1)
            self.assertTrue(all(error == 'forced attempt failed' for _, error, _ in results))

    def test_final_report_does_not_rewrite_checkpoint_in_place(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report_path = root / 'asset-fetch-report.json'
            real_write_text = Path.write_text
            def guarded_write(path, *args, **kwargs):
                self.assertNotEqual(path, report_path, 'never truncate the saved checkpoint in place')
                return real_write_text(path, *args, **kwargs)
            with patch.object(Path, 'write_text', guarded_write):
                status, requests, _ = self.run_fetch(root, {'places': []}, AssertionError('no tasks'))
            self.assertEqual(status, 0)
            self.assertEqual(requests, 0)
            self.assertEqual(json.loads(report_path.read_text(encoding='utf-8')), [])


if __name__ == '__main__':
    unittest.main()
