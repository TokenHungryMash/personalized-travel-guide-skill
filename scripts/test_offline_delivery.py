import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from _route_screenshots import verify_captures
from _display_labels import transport_label
from build_render_bindings import hero
from test_current_system_build import profile
from package_handbook import package
from unittest.mock import patch

class OfflineDeliveryTests(unittest.TestCase):
    def test_export_embeds_interaction_dependencies_and_rejects_missing_script(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'build';root.mkdir()
            p=profile();p.update(map_delivery='online',online_map_user_statement='需要在线互动地图')
            (root/'destination-profile.json').write_text(json.dumps(p))
            (root/'index.html').write_text('<html><head><link rel="stylesheet" href="ui.css?v=1"></head><body><button id="go">Open</button><script src="ui.js?v=1"></script></body></html>')
            (root/'ui.css').write_text('button {color: red;}')
            with self.assertRaisesRegex(ValueError,'Missing portable dependency'):package(root)
            (root/'ui.js').write_text('document.getElementById("go").onclick=()=>{document.body.dataset.open="yes";};')
            output=package(root)
            html=output.read_text(encoding='utf-8')
            self.assertIn('document.body.dataset.open="yes"',html)
            self.assertIn('button {color: red;}',html)
            self.assertNotIn('src="ui.js',html)
            self.assertNotIn('href="ui.css',html)
    def test_new_build_cannot_ship_zero_maps(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'RESEARCH_PROVENANCE.json').write_text('{}')
            self.assertEqual(len(verify_captures(root,profile())),3)
            p=profile();p['map_delivery']='legacy'
            self.assertTrue(verify_captures(root,p))
    def test_online_requires_actual_user_request(self):
        with tempfile.TemporaryDirectory() as d:
            p=profile();p['map_delivery']='online'
            self.assertTrue(verify_captures(Path(d),p))
            p['online_map_user_statement']='用户明确要求互动在线地图'
            self.assertEqual(verify_captures(Path(d),p),[])
    def test_cover_summary_can_be_hidden(self):
        p=profile();p['cover']['show_summary']=False
        self.assertNotIn('新资料',hero(p))
        p['cover']['show_summary']=True
        self.assertIn('新资料',hero(p))
        self.assertEqual(transport_label('public_transit'),'公共交通')
    def test_package_checks_resources_and_excludes_research(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'build';root.mkdir()
            p=profile();p.update(map_delivery='online',online_map_user_statement='需要在线互动地图')
            (root/'destination-profile.json').write_text(json.dumps(p))
            (root/'research').mkdir();(root/'research/private.json').write_text('private')
            (root/'index.html').write_text('<img src="assets/photo.png">')
            with self.assertRaisesRegex(ValueError,'Missing portable'): package(root)
            (root/'assets').mkdir();(root/'assets/photo.png').write_bytes(b'fixture')
            (root/'assets/unused.png').write_bytes(b'unreferenced fixture')
            import base64
            real_encode=base64.b64encode
            def encode(payload):
                self.assertNotEqual(payload,b'unreferenced fixture','unused assets must not be encoded')
                return real_encode(payload)
            with patch('base64.b64encode',side_effect=encode):
                output=package(root)
            self.assertEqual(output.suffix,'.html')
            html=output.read_text(encoding='utf-8')
            self.assertIn('data:image/png;base64,',html)
            self.assertIn('id="offline-image-viewer"',html)
            self.assertIn("a.setAttribute('href','#offline-image-viewer')",html)
            self.assertIn("box.showModal()",html)
            self.assertNotIn('private',html)
            (root/'index.html').write_text('<script src="https://example.com/runtime.js"></script>')
            with self.assertRaisesRegex(ValueError,'External runtime'): package(root)
if __name__=='__main__': unittest.main()
