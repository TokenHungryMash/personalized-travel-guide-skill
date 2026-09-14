"""Regression checks for display types, source drift, review binding and incremental scope."""
import hashlib
import html
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from audit_source_media import audit
from build_render_bindings import e
from validate_research_pack import validate
from compile_destination_profile import normalize_image_paths

SCRIPTS = Path(__file__).parent

class ProductionContract(unittest.TestCase):
    def test_research_local_file_reaches_manifest(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            data={'places':[{'id':'a','images':[{'local_file':'assets/a.jpg','media_class':'licensed_photo'}]}]}
            normalize_image_paths(data)
            (root/'profile.json').write_text(json.dumps(data))
            result=subprocess.run([sys.executable,str(SCRIPTS/'build_asset_manifest.py'),str(root/'profile.json'),str(root/'manifest.json')],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            manifest=json.loads((root/'manifest.json').read_text())
            self.assertEqual(manifest['assets'][0]['file'],'assets/a.jpg')
            self.assertEqual(audit(data,manifest),[])

    def test_display(self):
        self.assertEqual(html.unescape(e(['周一', '<临时公告>'])), '周一 · <临时公告>')
        self.assertNotIn('<临时公告>', e(['<临时公告>']))
        with self.assertRaises(ValueError):
            e({'title': 'wrong shape'})

    def test_early_quality(self):
        data = {'language': {'keyword_groups': []}, 'travel_notes': [
            {'items': [{'title': '中洲夜间，'}]}]}
        self.assertTrue(any(x['code'] == 'title' for x in validate('modules-language-notes', data)))
        errors = validate('modules-practical', {'food': {}, 'preparation': {'essentials': [], 'confirm_ahead': []}})
        self.assertTrue(any(x['pointer'] == '/preparation' for x in errors))

    def test_source_drift(self):
        source = {'file': 'assets/a.jpg', 'source_page': 'https://venue.test/a', 'download_url': 'https://venue.test/new.jpg'}
        profile = {'places': [{'id': 'a', 'images': [source]}]}
        self.assertEqual(audit(profile, {'assets': [{**source, 'place_id': 'a'}]}), [])
        self.assertTrue(audit(profile, {'assets': [{**source, 'place_id': 'a', 'download_url': 'https://venue.test/old.jpg'}]}))

    def test_manifest_default_original_class_is_not_drift(self):
        source = {'file':'a.jpg','media_class':'official_photo'}
        profile = {'places':[{'id':'a','images':[source]}]}
        asset = {**source,'place_id':'a','original_media_class':'official_photo'}
        self.assertEqual(audit(profile,{'assets':[asset]}), [])
        source['original_media_class'] = 'official_brand_asset'
        self.assertTrue(audit(profile,{'assets':[asset]}))

    def test_review_requires_matching_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'a.jpg').write_bytes(b'reviewed bytes')
            (root/'sheet.jpg').write_bytes(b'evidence fixture')
            source = {'file':'a.jpg','source_page':'https://venue.test/a','download_url':'https://venue.test/a.jpg','subject_verified':True}
            (root/'profile.json').write_text(json.dumps({'places':[{'id':'a','images':[source]}]}))
            command = [sys.executable,str(SCRIPTS/'build_asset_manifest.py'),str(root/'profile.json'),str(root/'manifest.json')]
            subprocess.run(command,check=True,capture_output=True)
            self.assertFalse(json.loads((root/'manifest.json').read_text())['assets'][0]['subject_verified'])
            row = {**source,'place_id':'a','sha256':hashlib.sha256(b'reviewed bytes').hexdigest(),
                   'verification_evidence':'sheet.jpg','visual_confirmation_note':'Visible exact sign',
                   'source_identity_bound':True,'visually_confirmed':True,'watermark_checked':True}
            (root/'reviews.json').write_text(json.dumps([row]))
            subprocess.run(command+['--review-records',str(root/'reviews.json')],check=True,capture_output=True)
            self.assertTrue(json.loads((root/'manifest.json').read_text())['assets'][0]['subject_verified'])
            manifest = json.loads((root/'manifest.json').read_text())
            self.assertEqual(manifest['assets'][0]['source_identity_note'], 'Visible exact sign')
            changed = json.loads((root/'profile.json').read_text())
            changed['places'][0]['images'][0]['media_class'] = 'official_brand_asset'
            (root/'profile.json').write_text(json.dumps(changed))
            subprocess.run(command+['--review-records',str(root/'reviews.json')],check=True,capture_output=True)
            self.assertFalse(json.loads((root/'manifest.json').read_text())['assets'][0]['subject_verified'])
            changed['places'][0]['images'][0].pop('media_class')
            (root/'profile.json').write_text(json.dumps(changed))
            (root/'a.jpg').write_bytes(b'changed bytes')
            subprocess.run(command+['--review-records',str(root/'reviews.json')],check=True,capture_output=True)
            changed = json.loads((root/'manifest.json').read_text())['assets'][0]
            self.assertFalse(changed['subject_verified'])
            self.assertFalse(changed['visually_confirmed'])

    def test_incremental_copy_and_restaurant_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            profile = {'places':[{'id':'r','type':'restaurant','description':'old','images':[{'file':'a.jpg'}]}]}
            path = root/'destination-profile.json'
            path.write_text(json.dumps(profile))
            cmd = [sys.executable,str(SCRIPTS/'plan_incremental_validation.py'),str(root)]
            subprocess.run(cmd+['--write'],check=True,capture_output=True)
            profile['places'][0]['description'] = 'new'
            path.write_text(json.dumps(profile))
            plan = json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True, encoding='utf-8').stdout)
            self.assertNotIn('media',plan['required_stages'])
            self.assertIn('render',plan['required_stages'])
            profile['places'][0]['images'][0]['file'] = 'b.jpg'
            path.write_text(json.dumps(profile))
            plan = json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True, encoding='utf-8').stdout)
            self.assertIn('media',plan['required_stages'])

if __name__ == '__main__':
    unittest.main()
