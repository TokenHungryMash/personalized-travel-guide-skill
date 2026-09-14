import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from build_render_bindings import shops
from import_local_assets import import_assets
from verify_assets import shared_place_photo


class PracticalMediaTests(unittest.TestCase):
    def test_text_only_souvenir_has_no_empty_gallery(self):
        product = dict(id='gift', type='souvenir', display_name='Known gift', images=[],
                       why_buy='Recognizable gift', best_for='Friends', where_to_buy='Named shop', buying_tip='Check size')
        html = shops({'module_groups': {'shopping': []}}, {'gift': product})
        self.assertIn('Known gift', html)
        self.assertIn('Named shop', html)
        self.assertNotIn('shop-visual', html)
        self.assertNotIn('<img', html)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'profile.json'
            path.write_text(json.dumps({'places':[product]}), encoding='utf-8')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('validate_destination_data.py')), str(path)],capture_output=True,text=True,encoding='utf-8')
            self.assertNotIn('Traceback', result.stderr)
            self.assertNotIn('place gift needs at least 1 image', result.stdout)

    def test_same_place_is_explicit_and_source_bound(self):
        places = {'a':dict(type='sight', latitude=35,longitude=139),
                  'b':dict(type='experience', latitude=35,longitude=139,same_place_as='a')}
        a=dict(place_id='a',source_page='https://example.org/a',download_url='https://example.org/a.jpg',
               source_identity_bound=True,source_identity_note='Observed the named entrance and the matching address in this test fixture')
        b={**a,'place_id':'b'}
        self.assertTrue(shared_place_photo(a,b,places))
        places['c'] = dict(places['b'])
        self.assertTrue(shared_place_photo(b,{**a,'place_id':'c'},places))
        self.assertFalse(shared_place_photo(a,a,places))
        self.assertFalse(shared_place_photo(a,{**b,'download_url':'https://example.org/b.jpg'},places))
        places['b']['type']='souvenir'
        self.assertFalse(shared_place_photo(a,b,places))
        places['b'].update(type='experience',latitude=float('nan'))
        self.assertFalse(shared_place_photo(a,b,places))

    def test_local_import_verifies_bytes_and_keeps_multiple_owners(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            Image.new('RGB',(20,20),'green').save(root/'photo.png')
            (root/'actual-tool-output.txt').write_text('Synthetic acquisition evidence for a unit test',encoding='utf-8')
            declaration=dict(file='photo.png',source_page='https://example.org/p',download_url='https://example.org/p.png')
            profile={'places':[{'id':p,'images':[declaration]} for p in ('a','b')]}
            base={**declaration,'sha256':hashlib.sha256((root/'photo.png').read_bytes()).hexdigest(),
                  'evidence_file':'actual-tool-output.txt','acquisition_note':'Synthetic authorized file acquisition for testing'}
            records=[{**base,'place_id':p} for p in ('a','b')]
            rows=import_assets(profile,root,records)
            self.assertEqual(len(rows),2)
            self.assertTrue(all(r['status']=='cached' and r['network_verified'] is False for r in rows))
            records[0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'SHA256'):
                import_assets(profile,root,records)
            records[0]=dict(base,place_id='a',evidence_file='../outside.txt')
            with self.assertRaisesRegex(ValueError,'inside asset root'):
                import_assets(profile,root,records)


if __name__=='__main__':
    unittest.main()
