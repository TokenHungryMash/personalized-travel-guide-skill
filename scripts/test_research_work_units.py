"""Offline regressions for atomic pack writes, honest stop-loss and bounded discovery."""
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch
from research_checkpoint import update
from write_research_json import write_json
import research_image_candidates as images

class ResearchWorkUnits(unittest.TestCase):

    def test_empty_cold_workspace_staging_and_all_nine_pack_paths(self):
        scripts = Path(__file__).resolve().parent

        def run(script, *args):
            result = subprocess.run([sys.executable, '-X', 'utf8', str(scripts / script), *map(str, args)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'brand-new-run'
            self.assertFalse(root.exists())
            run('start_build.py', root, '--destination', 'Cold fixture', '--country', 'Japan', '--days', 4, '--discussion-waived', '--user-statement', 'fixture waiver')
            run('init_research_workspace.py', root)
            for name in ('drafts', 'places', 'modules', 'tasks'):
                self.assertTrue((root / 'research' / name).is_dir(), name)
            staging = root / 'research/drafts/shortlist.next.json'
            staging.write_text('{"candidate_ids": ["fixture-a"]}', encoding='utf-8')
            run('write_research_json.py', root / 'research/drafts/shortlist.json', '--from-file', staging, '--workbench', root)
            plan = json.loads((root / 'research-plan.json').read_text(encoding='utf-8'))
            self.assertEqual(len(plan['packs']), 9)
            from validate_research_pack import scaffold
            for pack in plan['packs']:
                target = root / pack['file']
                staged = target.with_suffix('.next.json')
                value = scaffold(pack['id'])
                staged.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
                run('write_research_json.py', target, '--from-file', staged)
                self.assertEqual(json.loads(target.read_text(encoding='utf-8')), value)

    def test_parent_creation_is_confined_and_missing_source_is_concise(self):
        scripts = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'run'
            nested = root / 'research/drafts/batch/a.json'
            write_json(nested, {'ok': True}, workbench=root)
            self.assertTrue(nested.is_file())
            outside = root / 'research/../../escape/a.json'
            with self.assertRaises(ValueError):
                write_json(outside, {}, workbench=root)
            self.assertFalse((Path(folder) / 'escape').exists())
            missing = root / 'research/drafts/not-saved.json'
            result = subprocess.run([sys.executable, '-X', 'utf8', str(scripts / 'write_research_json.py'), str(nested), '--from-file', str(missing), '--workbench', str(root)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2)
            self.assertIn('staging JSON missing', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual(json.loads(nested.read_text()), {'ok': True})
            errors = root / 'errors.json'
            result = subprocess.run([sys.executable, '-X', 'utf8', str(scripts / 'validate_research_pack.py'), 'framing', str(missing), '--errors', str(errors)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stdout + result.stderr)
            self.assertEqual(json.loads(errors.read_text())['errors'][0]['code'], 'input_missing')

    def test_invalid_replacement_preserves_original_and_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pack.json'
            write_json(path, {'a': 1})
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                write_json(path, None)
            with self.assertRaises(ValueError):
                write_json(path, {'a': float('nan')})
            with self.assertRaises(ValueError):
                write_json(path, {}, 'framing')
            self.assertEqual(path.read_bytes(), original)
            write_json(path, [{'a': '第二版'}])
            self.assertEqual(path.with_suffix('.json.bak').read_bytes(), original)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), [{'a': '第二版'}])
            self.assertEqual(list(path.parent.glob('*.tmp')), [])

    def test_overrun_retained_and_active_timer_cannot_be_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            update(folder, 'start', 'core-01', ['a', 'b'], now=100)
            with self.assertRaises(ValueError):
                update(folder, 'start', 'core-02', ['c'], now=300)
            self.assertTrue(update(folder, 'status', now=401)['stop_required'])
            self.assertTrue(update(folder, 'finish', now=402)['stop_required'])
            update(folder, 'start', 'core-02', ['c'], now=410)
            result = update(folder, 'finish', now=450)
            self.assertEqual(result['total_wall_seconds'], 350)
            state = json.loads((Path(folder) / '.research-state/timing.json').read_text())
            self.assertEqual(state['units'][0]['status'], 'overrun')
            self.assertEqual(state['units'][0]['elapsed_seconds'], 302)

    def test_official_sight_candidates_skip_open_media_without_claiming_review(self):
        candidate = images.item('official_body_image', 'https://example.org/place', 'https://example.org/place.png', entity_bound=True, media_class='official_photo')
        with patch.object(images, 'official', return_value=[candidate]), patch.object(images, 'wikidata') as wd, patch.object(images, 'openverse') as ov:
            result = images.collect({'kind': 'sight', 'quality_mode': 'standard'}, 2)
            wd.assert_not_called()
            ov.assert_not_called()
            self.assertEqual(len(result['candidates']), 1)
            self.assertFalse(result['candidates'][0]['subject_verified'])
            self.assertIsNone(result['resolved_identity']['coordinates'])
if __name__ == '__main__':
    unittest.main()
