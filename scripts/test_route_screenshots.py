import hashlib,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from unittest.mock import patch
from route_screenshots import prepare, import_captures, compress_capture
from _route_screenshots import verify_captures, screenshots_html
from _current_system_adapter import runtime_bindings
from test_current_system_build import profile

class ScreenshotTests(unittest.TestCase):
    def test_one_overview_per_day_keeps_all_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=profile()
            data['places'][-1]['latitude']+=.2
            (root/'destination-profile.json').write_text(json.dumps(data),encoding='utf-8')
            prepare(root)
            plan=json.loads((root/'qa/route-capture/capture-plan.json').read_text(encoding='utf-8'))
            self.assertEqual(len(plan['tasks']),len(data['itinerary']))
            for task,day in zip(plan['tasks'],data['itinerary']):
                self.assertEqual(task['view'],1)
                self.assertEqual(len(task['stop_numbers']),len(day['stops']))
                self.assertIn('总览',task['caption'])

    def make(self,root):
        data=profile();data['itinerary']=data['itinerary'][:1];data['itinerary'][0]['date']='2026-11-03'
        (root/'research').mkdir()
        (root/'destination-profile.json').write_text(json.dumps(data),encoding='utf-8')
        (root/'research/itinerary.json').write_text(json.dumps(data['itinerary']),encoding='utf-8')
        prepare(root)
        return data

    def test_prepare_has_no_claimed_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.make(root);folder=root/'qa/route-capture'
            plan=json.loads((folder/'capture-plan.json').read_text(encoding='utf-8'))
            self.assertTrue(plan['tasks'])
            page=(folder/plan['tasks'][0]['page']).read_text(encoding='utf-8')
            self.assertIn('tiles.openfreemap.org/styles/liberty',page)
            self.assertIn('CAPTURE_STATE',page)
            self.assertFalse(list(folder.glob('*.png')))

    def test_import_review_and_route_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.make(root);folder=root/'qa/route-capture'
            tasks=json.loads((folder/'capture-plan.json').read_text(encoding='utf-8'))['tasks'];rows=[]
            for task in tasks:
                # Synthetic unit-test fixture, never a real map or a delivery asset.
                p=folder/task['png'];Image.new('RGB',(1400,1100),'green').save(p)
                rows.append({'png':task['png'],'status':'captured','visual_reviewed':False,
                             'day_fingerprint':task['day_fingerprint'],
                             'page_sha256':hashlib.sha256((folder/task['page']).read_bytes()).hexdigest(),
                             'review_note':'Synthetic fixture only, not actual visual evidence',
                             'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                             'observed_state':{'status':'ready','tiles_loaded':True,'labels':len(task['stop_numbers'])}})
            report=folder/'capture-report.json';report.write_text(json.dumps({'captures':rows}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'visual review'):import_captures(root)
            for row in rows:row['visual_reviewed']=True
            report.write_text(json.dumps({'captures':rows}),encoding='utf-8');import_captures(root)
            source_before=(root/'research/itinerary.json').read_bytes()
            backups_before=list(folder.glob('itinerary-before-import-*'))
            with patch('route_screenshots.compress_capture',side_effect=AssertionError('unchanged map must not recompress')):
                import_captures(root)
            self.assertEqual(source_before,(root/'research/itinerary.json').read_bytes())
            self.assertEqual(backups_before,list(folder.glob('itinerary-before-import-*')))
            saved=json.loads(source_before)[0]['route_screenshots'][0]
            derivative=root/saved['file'];derivative.write_bytes(b'damaged derivative')
            with patch('route_screenshots.compress_capture',wraps=compress_capture) as compress:
                import_captures(root)
                self.assertEqual(compress.call_count,1)
            self.assertEqual(hashlib.sha256(derivative.read_bytes()).hexdigest(),saved['sha256'])
            data['itinerary']=json.loads((root/'research/itinerary.json').read_text(encoding='utf-8'))
            self.assertEqual(verify_captures(root,data),[])
            rendered=screenshots_html(data['itinerary'][0]);self.assertIn('点击查看大图',rendered)
            js={r['path']:r['content'] for r in runtime_bindings(data)}['trip-route-maps.js']
            self.assertIn("mode:'screenshots'",js);self.assertNotIn('maplibre',js)
            data['places'][0]['latitude']+=.01
            self.assertTrue(any('route changed' in s for s in verify_captures(root,data)))
            (folder/tasks[0]['page']).write_text('changed label page',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'capture page or route changed'):
                import_captures(root)

if __name__=='__main__':unittest.main()
