"""Offline regressions for ordinary-build rework; no destination research."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from fetch_declared_assets import collect_tasks
from validate_research_pack import validate
from PIL import Image

SCRIPTS = Path(__file__).resolve().parent

class OrdinaryPipeline(unittest.TestCase):
    def test_decoding_is_saved_without_claiming_visual_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new('RGB', (800, 600), 'blue').save(root/'a.jpg')
            (root/'profile.json').write_text(json.dumps({'places': []}))
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps({'assets': [{'file': 'a.jpg', 'place_id': 'a', 'decoded': False,
                'visually_confirmed': False, 'subject_verified': False}]}))
            subprocess.run([sys.executable, str(SCRIPTS/'verify_assets.py'), str(root/'profile.json'),
                str(manifest), str(root), '--machine-only', '--write'], capture_output=True)
            record = json.loads(manifest.read_text())['assets'][0]
            self.assertTrue(record['decoded'])
            self.assertFalse(record['visually_confirmed'])
            self.assertFalse(record['subject_verified'])

    def test_cover_batch_and_targeted_repair(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            profile = {'cover': {'image': 'assets/cover.jpg', 'download_url': 'https://example.org/cover.jpg'},
                       'places': [{'id': 'a', 'images': [{'file': 'assets/a.jpg'}]}]}
            tasks, failures = collect_tasks(profile, root, set(), {})
            self.assertEqual(failures, [])
            self.assertEqual({t[0] for t in tasks}, {'a', '__cover__'})
            cover_task = next(t for t in tasks if t[0] == '__cover__')
            cover_task[1]['width'] = 1600
            self.assertEqual(profile['cover']['width'], 1600)
            tasks, failures = collect_tasks(profile, root, {'a'}, {})
            self.assertEqual([t[0] for t in tasks], ['a'])
            profile['cover']['image'] = '../escape.jpg'
            tasks, failures = collect_tasks(profile, root, set(), {})
            self.assertTrue(failures)
            self.assertNotIn('__cover__', [t[0] for t in tasks])

    def test_early_contract_errors(self):
        errors = validate('framing', {'cover': {'image': {'file': 'a.jpg'}}})
        self.assertIn('/cover/image', [e['pointer'] for e in errors])
        errors = validate('places-shopping', {'shops': [{'type': 'shop'}], 'souvenirs': []})
        self.assertIn('/shops/0/closed_days', [e['pointer'] for e in errors])
        errors = validate('modules-language-notes', {'language': {}, 'travel_notes': {'groups': []}})
        self.assertTrue(any(e['pointer'] == '/travel_notes' and e['code'] == 'container_type' for e in errors))
        errors = validate('modules-language-notes', {'language': {}, 'travel_notes': [{'category': 'weather'}]})
        self.assertIn('/travel_notes/0/category', [e['pointer'] for e in errors])

    def test_seed_reuses_language_and_keeps_drafts_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'travel-brief.json').write_text(json.dumps({'display_name': '福冈', 'country': 'Japan'}), encoding='utf-8')
            (root/'research-plan.json').write_text(json.dumps({'packs': [{'id': 'modules-language-notes'}]}), encoding='utf-8')
            command = [sys.executable, str(SCRIPTS/'seed_deterministic_packs.py'), str(root)]
            subprocess.run(command, check=True, capture_output=True)
            path = root/'research/modules/language-notes.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertTrue(data['_draft'])
            self.assertTrue(data['language']['_draft'])
            self.assertIsInstance(data['travel_notes'], list)
            self.assertEqual(len(data['travel_notes']), 5)
            self.assertTrue(data['language']['keyword_groups'][0]['items'][0]['reading'])
            self.assertTrue(data['language']['english_phrase_groups'])
            path.write_text('{"user_edit": true}', encoding='utf-8')
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(json.loads(path.read_text()), {'user_edit': True})

if __name__ == '__main__':
    unittest.main()
