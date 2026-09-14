"""Cold-start and distribution checks using disposable local fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from _content_integrity import content_failures
from package_skill import package_files

ROOT = Path(__file__).resolve().parents[1]


class PublicRelease(unittest.TestCase):
    def test_package_excludes_local_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ['SKILL.md', '.gitattributes', 'scripts/helper.py', 'scripts/test-system-browser.cjs', 'scripts/.env', 'assets/.dev.vars', 'research/booking.json', '.wrangler/state.json', 'notes.txt']:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic fixture', encoding='utf8')
            self.assertEqual({p.relative_to(root).as_posix() for p in package_files(root)}, {'SKILL.md', '.gitattributes', 'scripts/helper.py'})

    def run_script(self, name, *args):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'scripts'/name), *map(str, args)], capture_output=True, text=True, encoding='utf8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_cold_start_uses_this_root_and_single_standard(self):
        with tempfile.TemporaryDirectory() as folder:
            bench = Path(folder)/'中文 guide'
            self.run_script('start_build.py', bench, '--destination', 'Test City', '--country', 'Japan', '--start-date', '2026-11-04', '--days', '4', '--discussion-waived', '--user-statement', 'fixture waiver')
            output = self.run_script('init_research_workspace.py', bench)
            command = json.loads(next(line.removeprefix('CONTINUE_ARGV: ') for line in output.splitlines() if line.startswith('CONTINUE_ARGV: ')))
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True, encoding='utf8')
            # A fresh workspace is intentionally incomplete: status exits 2 and
            # identifies the first pending pack, rather than claiming success.
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn('NEXT BATCH', result.stdout)
            self.assertIn('framing.json', result.stdout)
            state = json.loads((bench/'.travel-build-state.json').read_text(encoding='utf8'))
            self.assertEqual(Path(state['skill_root']), ROOT)
            self.assertEqual(state['quality_mode'], 'standard')
            tasks = list((bench/'research/tasks').glob('*.json'))
            self.assertEqual(len(tasks), 9)
            for file in tasks:
                task = json.loads(file.read_text(encoding='utf8'))
                self.assertNotIn('functions.exec', json.dumps(task))
                self.assertNotIn('tools.exec_command', json.dumps(task))
                self.assertEqual(task['execution_policy']['agent_mode'], 'single_agent_default')
                self.assertIs(task['execution_policy']['subagents_require_explicit_user_request'], True)
                self.assertFalse(any('where to stay' in q for q in task['search_queries']))
                self.assertIn('exactly one reviewed offline overview per day',task['map_delivery'])
                if file.stem.startswith('places-'):
                    self.assertIn('source_identity_note', json.dumps(task))

    def test_no_edition_selector_in_cli_or_questionnaire(self):
        self.assertNotIn('--quality-mode', self.run_script('start_build.py', '--help'))
        self.assertNotIn('--quality-mode', self.run_script('init_research_workspace.py', '--help'))
        text = (ROOT/'assets/intake-questionnaire/index.html').read_text(encoding='utf8')
        self.assertIn('build-personalized-travel-guide-open-source', text)
        self.assertNotIn('普通版', text)
        self.assertNotIn('高端版', text)

    def test_external_mode_cannot_change_standard(self):
        self.assertTrue(any('Unsupported production standard' in e for e in content_failures({'trip': {'quality_mode': 'other'}})))

    def test_no_personal_media_or_credentials_in_current_bundle(self):
        for file in (ROOT/'assets/current-system').rglob('*'):
            if file.is_file():
                self.assertNotIn(file.suffix.lower(), {'.jpg', '.jpeg', '.png', '.webp', '.woff', '.woff2', '.env'})
                if file.suffix in {'.html', '.js', '.json'}:
                    text = file.read_text(encoding='utf8')
                    for token in ['Mahandita', 'Ekosistem', 'CX303', 'CX783', 'HO1356']:
                        self.assertNotIn(token, text, str(file))


if __name__ == '__main__':
    unittest.main()
