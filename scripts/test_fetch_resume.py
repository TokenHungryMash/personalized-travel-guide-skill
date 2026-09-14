import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from fetch_declared_assets import checkpoint_report, collect_tasks, fetch
import research_status
import fetch_declared_assets as downloader

class FetchResume(unittest.TestCase):
    def test_throttle_stops_network_but_keeps_verified_cache(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);target=root/'a.png'
            Image.new('RGB',(40,30),'blue').save(target)
            image=dict(file='a.png',download_url='https://images.test/a.png',source_page='https://images.test/a')
            image['_fetch_receipt']=dict(download_url=image['download_url'],source_page=image['source_page'],sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            with patch.object(downloader,'HOST_STOPPED',{'images.test'}),patch.object(downloader.SAFE_OPENER,'open',side_effect=AssertionError('no network after 429')):
                row, error, downloaded=fetch(('a',image,target),0,False)
                self.assertEqual(row['status'],'cached')
                self.assertIsNone(error)
                row,error,downloaded=fetch(('b',dict(image,file='b.png'),root/'b.png'),0,False)
                self.assertEqual(row['status'],'failed')
                self.assertIn('queued request skipped',error)

    def test_checkpoint_reused_after_recompile_without_profile_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root/'photo.png'
            Image.new('RGB',(600,400),'red').save(target)
            receipt = dict(place_id='p',file='photo.png',status='ok',download_url='https://example.org/p.png',source_page='https://example.org/p',sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            report = root/'asset-fetch-report.json'
            checkpoint_report(report,[],[receipt])
            data = {'places':[{'id':'p','images':[{'local_file':'photo.png','download_url':receipt['download_url'],'source_page':receipt['source_page'],'_fetch_receipt':{}}]}]}
            rows = json.loads(report.read_text())
            tasks, errors = collect_tasks(data,root,set(),{('p','photo.png'):rows[0]})
            self.assertEqual(errors,[])
            with patch('fetch_declared_assets.SAFE_OPENER.open',side_effect=AssertionError('must use real saved receipt')):
                row,error,downloaded = fetch(tasks[0],0,False)
            self.assertEqual(row['status'],'cached')
            self.assertIsNone(error)
            self.assertFalse(downloaded)

    def test_successful_status_keeps_final_plan_signature(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            (root/'research-plan.json').write_text(json.dumps({'packs':[]}))
            def compiler(*args,**kwargs):
                (root/'RESEARCH_PROVENANCE.json').write_text(json.dumps({'research_plan_sha256':'pre-status','profile_sha256':'unchanged'}))
                return subprocess.CompletedProcess([],0,'compiled','')
            with patch('research_status.subprocess.run',side_effect=compiler),patch('sys.argv',['status',str(root)]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(research_status.main(),0)
            record=json.loads((root/'RESEARCH_PROVENANCE.json').read_text())
            self.assertEqual(record['research_plan_sha256'],hashlib.sha256((root/'research-plan.json').read_bytes()).hexdigest())
            self.assertEqual(record['profile_sha256'],'unchanged')

if __name__=='__main__': unittest.main()
