import json
import tempfile
import unittest
from pathlib import Path
from _build_state import qa_is_complete
from _manual_qa import build_fingerprint

class RepresentativeQATests(unittest.TestCase):

    def make_root(self, mode: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix='travel-standard-fast-'))
        (root / 'destination-profile.json').write_text(json.dumps({'trip': {'quality_mode': mode}, 'places': [{'id': 's1', 'images': [{'file': 'assets/s1.jpg'}]}]}), encoding='utf-8')
        for name in ('desktop.png', 'mobile.png'):
            (root / name).write_bytes(b'evidence')
        qa = {'validation_mode': 'representative', 'desktop': {'passed': True, 'inner_width': 1280, 'inner_height': 800, 'horizontal_overflow': False}, 'mobile': {'passed': True, 'inner_width': 390, 'inner_height': 844, 'horizontal_overflow': False, 'match_media_mobile': True}, 'interactions': {'disclosures': True, 'trip_mode': True}, 'screenshots': ['desktop.png', 'mobile.png']}
        qa['build_fingerprint'] = build_fingerprint(root)
        (root / 'browser-qa.json').write_text(json.dumps(qa), encoding='utf-8')
        return root

    def test_standard_accepts_two_representative_samples(self):
        ok, failures = qa_is_complete(self.make_root('standard'))
        self.assertTrue(ok, failures)

    def test_changed_runtime_invalidates_old_browser_observations(self):
        root=self.make_root('standard')
        (root/'trip-mode.js').write_text('changed runtime',encoding='utf-8')
        self.assertTrue(any('build changed' in f for f in qa_is_complete(root)[1]))
if __name__ == '__main__':
    unittest.main()
