"""Manifest downloads do not put URLs into command lines; no live network tests."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import Mock
from download_photos import load_plan,download_plan,DirectClient
from fetch_photos import FetchError
from test_fetch_photos import Clock,Transport,http_error,photo_bytes

class DownloadPlanTests(unittest.TestCase):
    def test_large_utf8_manifest_download_resume_and_actual_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);file=root/'候选清单.json'
            rows=[dict(id=f'place-{i}',placeId='museum',url='https://images.test/'+str(i)+'?q='+'x'*300,page='https://museum.test/visit',caption='玻璃与钢') for i in range(150)]
            file.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8-sig')
            self.assertGreater(file.stat().st_size,32768)
            plan=load_plan(file);client=Mock();client.get.return_value=photo_bytes()
            records=download_plan(root,plan,client)
            self.assertEqual(client.get.call_count,150)
            for row in records['candidates'].values():
                self.assertFalse(row['reviewed']);self.assertEqual((row['width'],row['height']),(37,19))
            download_plan(root,plan,client)
            self.assertEqual(client.get.call_count,150)
    def test_bad_ids_and_urls_rejected_before_downloading(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'plan.json'
            for row in [dict(id='../escape',placeId='x',url='https://images.test/a',page='https://source.test'),dict(id='x',placeId='x',url='file:///secret',page='https://source.test')]:
                f.write_text(json.dumps([row]),encoding='utf8')
                with self.assertRaises(FetchError):load_plan(f)
    def test_bad_image_records_failure_then_can_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=[dict(id='x',placeId='x',url='https://images.test/a',page='https://source.test')]
            client=Mock();client.get.return_value=b'<html>Access denied</html>'
            with self.assertRaises(FetchError):download_plan(root,rows,client)
            self.assertFalse((root/'media').exists())
            record=json.loads((root/'photo-download-records.json').read_text())
            self.assertEqual(next(iter(record['candidates'].values()))['status'],'failed')
            client.get.return_value=photo_bytes()
            self.assertEqual(next(iter(download_plan(root,rows,client)['candidates'].values()))['status'],'downloaded')
    def test_direct_403_stops_without_retry_or_identity_spoofing(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock=Clock();opener=Transport(http_error(403))
            client=DirectClient(tmp,opener=opener,sleep=clock.sleep,now=clock.now)
            with self.assertRaisesRegex(FetchError,'HTTP 403'):client.get('https://images.test/a')
            self.assertEqual(len(opener.requests),1)
