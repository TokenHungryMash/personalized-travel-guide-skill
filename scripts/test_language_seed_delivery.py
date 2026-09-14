import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class LanguageSeedDeliveryTests(unittest.TestCase):
    def test_japanese_seed_uses_local_contract_in_both_pack_modes(self):
        script=Path(__file__).with_name('seed_deterministic_packs.py')
        for compact in (False,True):
            with self.subTest(compact=compact), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                (root/'travel-brief.json').write_text(json.dumps({'display_name':'东京','country':'日本'}),encoding='utf-8')
                (root/'research-plan.json').write_text(json.dumps({'packs':[{'id':'modules-language-notes'}] if compact else []}),encoding='utf-8')
                subprocess.run([sys.executable,str(script),str(root)],check=True,capture_output=True)
                path=root/('research/modules/language-notes.json' if compact else 'research/modules/language.json')
                data=json.loads(path.read_text(encoding='utf-8'))
                if compact:data=data['language']
                local=[item for group in data['phrase_groups'] for item in group['items']]
                self.assertEqual(len(local),25)
                for item in local:
                    self.assertTrue(item.get('term'))
                    self.assertNotIn('sentence',item)
                english=[item for group in data['english_phrase_groups'] for item in group['items']]
                self.assertTrue(english)
                for item in english:self.assertTrue(item.get('sentence'))
                self.assertTrue(data['_draft'])

if __name__=='__main__':unittest.main()
