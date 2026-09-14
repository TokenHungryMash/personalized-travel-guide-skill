"""An existing trip resumes from its owning Skill, even with duplicate installs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillResumeRoot(unittest.TestCase):
    def create_prior(self, folder, skill_root=None):
        bench = Path(folder) / '已有 工作台'
        bench.mkdir()
        state = {
            'destination': 'Fixture City', 'start_date': '2026-11-04',
            'days': 6, 'handoff_allowed': False,
        }
        if skill_root is not None:
            state['skill_root'] = str(skill_root)
        state_path = bench / '.travel-build-state.json'
        state_path.write_text(json.dumps(state), encoding='utf-8')
        return bench, state_path.read_bytes()

    def attempt_start(self, folder):
        target = Path(folder) / 'new-workbench'
        result = subprocess.run([
            sys.executable, '-X', 'utf8', str(ROOT / 'scripts/start_build.py'), str(target),
            '--destination', 'Fixture City', '--country', 'Japan',
            '--start-date', '2026-11-04', '--days', '6',
            '--discussion-waived', '--user-statement', 'fixture waiver',
        ], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(target.exists(), 'A resume suggestion must not create another build')
        return result.stdout + result.stderr

    def continue_argv(self, output):
        return json.loads(next(line.removeprefix('CONTINUE_ARGV: ')
                               for line in output.splitlines() if line.startswith('CONTINUE_ARGV: ')))

    def test_duplicate_install_suggestion_runs_original_skill(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Path(folder) / '旧 Skill 安装'
            scripts = original / 'scripts'
            scripts.mkdir(parents=True)
            runner = scripts / 'advance_build.py'
            runner.write_text("print('ORIGINAL_SKILL_RESUMED')\n", encoding='utf-8')
            bench, original_bytes = self.create_prior(folder, original)
            command = self.continue_argv(self.attempt_start(folder))
            self.assertEqual(command, [sys.executable, str(runner.resolve()), str(bench.resolve()), '--run'])
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('ORIGINAL_SKILL_RESUMED', result.stdout)
            self.assertEqual((bench / '.travel-build-state.json').read_bytes(), original_bytes)

    def test_removed_original_skill_does_not_suggest_wrong_runner(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Path(folder) / 'removed-skill'
            bench, original_bytes = self.create_prior(folder, original)
            output = self.attempt_start(folder)
            self.assertIn('ORIGINAL SKILL UNAVAILABLE:', output)
            self.assertIn(str(original.resolve()), output)
            self.assertNotIn('CONTINUE_ARGV:', output)
            self.assertNotIn('NEXT_COMMAND:', output)
            self.assertEqual((bench / '.travel-build-state.json').read_bytes(), original_bytes)

    def test_legacy_state_without_skill_root_uses_current_install(self):
        with tempfile.TemporaryDirectory() as folder:
            bench, _ = self.create_prior(folder)
            command = self.continue_argv(self.attempt_start(folder))
            self.assertEqual(command[1], str(ROOT / 'scripts/advance_build.py'))
            self.assertEqual(command[2], str(bench.resolve()))


if __name__ == '__main__':
    unittest.main()
