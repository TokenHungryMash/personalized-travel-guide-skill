import base64
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from package_handbook import package
from _offline_qa import export_state, CHECKS
from _official_classification import classify
from research_image_candidates import product_candidates
from _official_images import is_ui_image
from _build_state import evaluation_fingerprint
import network_session

class ReleaseRegression(unittest.TestCase):
    def fixture(self, root):
        (root/'assets').mkdir()
        (root/'assets/photo.png').write_bytes(b'image-fixture')
        (root/'destination-profile.json').write_text(json.dumps({'display_name':'Test City','map_delivery':'online','online_map_user_statement':'Use online maps','itinerary':[]}))
        (root/'index.html').write_text('<html><head></head><body><img src="assets/photo.png"><a href="assets/photo.png"><img src="assets/photo.png"></a><script>const image="assets/photo.png";</script></body></html>')

    def test_payload_dedup_and_no_research_leak(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'build';root.mkdir();self.fixture(root)
            output=package(root);text=output.read_text(encoding='utf-8')
            self.assertEqual(text.count(base64.b64encode(b'image-fixture').decode()),1)
            self.assertIn('MutationObserver',text)
            self.assertNotIn('assets/photo.png',text)
            self.assertEqual(json.loads((root/'offline-export.json').read_text(encoding='utf-8'))['image_occurrences'],4)

    def test_external_export_change_invalidates_cached_status(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'build';root.mkdir();self.fixture(root)
            output=package(root)
            before=evaluation_fingerprint(root)
            output.write_text(output.read_text(encoding='utf-8')+'changed', encoding='utf-8')
            self.assertNotEqual(before,evaluation_fingerprint(root))

    def test_network_session_is_local_and_preserves_explicit_deny(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'network-session.json').write_text(json.dumps({'workbench':str(root.resolve()),'allow_known_fake_ip':True,'evidence':'synthetic fixture'}))
            argv=['network_session',str(root),'--run','research_status.py',str(root)]
            with patch.object(sys,'argv',argv), patch.dict(os.environ,{},clear=True), patch('network_session.subprocess.run') as run:
                run.return_value.returncode=0
                self.assertEqual(network_session.main(),0)
                self.assertEqual(run.call_args.kwargs['env']['TRAVEL_GUIDE_ALLOW_FAKE_IP'],'1')
                self.assertNotIn('TRAVEL_GUIDE_ALLOW_FAKE_IP',os.environ)
            with patch.object(sys,'argv',argv), patch.dict(os.environ,{'TRAVEL_GUIDE_ALLOW_FAKE_IP':'0'},clear=True), patch('network_session.subprocess.run') as run:
                network_session.main()
                self.assertEqual(run.call_args.kwargs['env']['TRAVEL_GUIDE_ALLOW_FAKE_IP'],'0')

    def test_export_gate_missing_pass_changed_and_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'build';root.mkdir();self.fixture(root)
            self.assertEqual(export_state(root)[0],'offline_export_required')
            output=package(root)
            self.assertEqual(export_state(root)[0],'offline_qa_required')
            sha=hashlib.sha256(output.read_bytes()).hexdigest()
            qa={'export_sha256':sha,'validation_mode':'browser','status':'passed','tested_url':'http://localhost/export.html','tool_reference':'actual-browser-result','checked_at':'2026-01-01','checks':{k:{'passed':True,'note':'fixture observation'} for k in CHECKS}}
            (root/'offline-qa.json').write_text(json.dumps(qa))
            self.assertEqual(export_state(root)[0],'complete')
            qa['checks']['map_viewer']['passed']=False
            (root/'offline-qa.json').write_text(json.dumps(qa))
            self.assertEqual(export_state(root)[0],'offline_qa_required')
            qa.update(status='pending',validation_mode='unavailable',host_limitation={'reason':'file denied','tool_reference':'denial','checked_at':'2026-01-01'})
            (root/'offline-qa.json').write_text(json.dumps(qa))
            self.assertTrue(export_state(root)[2])
            output.write_text(output.read_text(encoding='utf-8')+'changed', encoding='utf-8')
            self.assertEqual(export_state(root)[0],'offline_export_required')

    def test_ui_and_social_images_are_not_photos(self):
        for filename in ['snav_active.jpg','tenpo01_title01.jpg','btn_buy.png','ttl_spirit.jpg']:
            self.assertTrue(is_ui_image('https://example.com/'+filename),filename)
        self.assertFalse(is_ui_image('https://example.com/temple_photo.jpg'))
        row={'local_name':'Example Museum'}
        page={'images':[{'url':'https://example.com/og.jpg','context':'Example Museum','metadata_key':'og:image'}, {'url':'https://example.com/photo.jpg','context':'Example Museum','metadata_key':'body:src'}]}
        result=classify(row,page)
        self.assertEqual(result[0]['media_class'],'official_brand_asset')
        self.assertEqual(result[1]['media_class'],'official_photo')

    def test_product_nav_does_not_outscore_real_product(self):
        page={'status':'ok','title':'Little Cake','images':[{'url':'https://example.com/snav_active.jpg','context':'Little Cake','metadata_key':'body:src'},{'url':'https://example.com/cake.jpg','context':'Little Cake','metadata_key':'body:src'}]}
        with patch('research_image_candidates.probe',return_value=page):
            result=product_candidates({'product_name':'Little Cake','official_url':'https://example.com/cake'},2)
        self.assertEqual(len(result['candidates']),1)
        self.assertTrue(result['candidates'][0]['image_url'].endswith('/cake.jpg'))

if __name__=='__main__': unittest.main()
