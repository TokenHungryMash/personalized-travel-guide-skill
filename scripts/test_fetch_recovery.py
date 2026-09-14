import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
import _osm_extract as osm
import fetch_declared_assets as assets
from validate_research_pack import validate

class RecoveryTests(unittest.TestCase):
    def test_permanent_failure_cache_is_bound_to_source_and_overridable(self):
        with tempfile.TemporaryDirectory() as directory:
            image={'file':'test.jpg','download_url':'https://example.org/a.jpg','source_page':'https://example.org/place'}
            image['_fetch_receipt']={**image,'status':'failed','http_status':404}
            task=('p',image,Path(directory)/'test.jpg')
            with patch.object(assets,'_fetch',side_effect=AssertionError('network must not run')):
                row,_,_=assets.fetch(task,1,False)
                self.assertTrue(row['cached_failure'])
            self.assertIsNone(assets.cached_result(task,True))
            image['download_url']='https://example.org/b.jpg'
            self.assertIsNone(assets.cached_result(task,False))
            image['download_url']='https://example.org/a.jpg'
            image['_fetch_receipt']['http_status']=503
            self.assertIsNone(assets.cached_result(task,False))

    bounds = [(35.01,139.01,35.02,139.02)]

    def test_dedup_resume_and_merge(self):
        self.assertEqual(len(osm.jobs(self.bounds*3)),2)
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def first(req, **kw):
                calls.append(req.full_url)
                if len(calls)>1:
                    raise urllib.error.HTTPError(req.full_url,429,'busy',{},None)
                return io.BytesIO(b'{"elements":[{"type":"way","id":1}]}')
            with self.assertRaises(RuntimeError):
                osm.fetch_extract(self.bounds, directory, opener=first, sleep=lambda _:None)
            self.assertEqual(len(list(Path(directory).glob('osm-cells/*.receipt.json'))),1)
            self.assertGreater(len(set(calls)),1)
            calls.clear()
            def resumed(req, **kw):
                calls.append(req.full_url)
                return io.BytesIO(b'{"elements":[{"type":"way","id":1},{"type":"way","id":2}]}')
            result=osm.fetch_extract(self.bounds,directory,opener=resumed)
            self.assertEqual(len(calls),1)
            self.assertEqual(len(result['elements']),2)
            osm.fetch_extract(self.bounds,directory,opener=lambda *a,**k:self.fail('cache contacted network'))

    def test_corrupted_cache_cannot_pass_failed_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            good=lambda *a,**k:io.BytesIO(b'{"elements":[]}')
            osm.fetch_extract(self.bounds,directory,opener=good)
            next(Path(directory).glob('osm-cells/*.json')).write_text('bad')
            def bad(*a,**k):raise TimeoutError('timeout')
            with self.assertRaises(RuntimeError):osm.fetch_extract(self.bounds,directory,opener=bad,sleep=lambda _:None)

    def test_origin_404_not_retried_or_rewritten(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(assets,'validate_public_https_url'), patch.object(assets.SAFE_OPENER,'open') as opened:
            opened.side_effect=urllib.error.HTTPError('https://upload.wikimedia.org/test.jpg',404,'missing',{},None)
            row,error,_=assets.fetch(('p',{'file':'test.jpg','download_url':'https://upload.wikimedia.org/test.jpg'},Path(directory)/'test.jpg'),2,False)
            self.assertEqual(opened.call_count,1)
            self.assertIn('upload.wikimedia.org',opened.call_args.args[0].full_url)
            self.assertEqual(row['status'],'failed')

    def test_coordinate_preflight(self):
        place={'type':'restaurant','latitude':True,'longitude':float('nan')}
        self.assertEqual(len([e for e in validate('places-food',[place]) if e['code']=='coordinates']),2)
        place.update(latitude=35.6,longitude=139.7)
        self.assertFalse([e for e in validate('places-food',[place]) if e['code']=='coordinates'])

if __name__=='__main__':unittest.main()
