"""Approved intake reaches the real generated tasks without default overwrites."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent


class BriefPreservationTests(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def read(self, path):
        return json.loads(path.read_text(encoding='utf-8'))

    def command(self, script, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                                capture_output=True, text=True, encoding='utf-8')
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def user_brief(self):
        return {'destination': 'Preference Fixture', 'country': 'Japan', 'start_date': '2026-11-04',
                'days': 4, 'travelers': '4 adults', 'rhythm': 'balanced', 'interests': ['games', 'food'],
                'constraints': ['step-free access'], 'must_go': ['Approved anchor'], 'avoid': ['nightclubs'],
                'budget': {'level': 'mainstream', 'total_trip': '18000 CNY', 'extra_note': 'shopping separate'},
                'defaults_authorized': False, 'other_notes': {'user_field': 'preserve me'}}

    def start(self, root, *args, expected=0):
        return self.command('start_build.py', root, '--itinerary-approved', '--user-statement',
                            'Synthetic approval of the displayed route', *args, expected=expected)

    def test_brief_file_survives_automatic_initialization_and_reaches_each_task(self):
        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw); root = parent / 'build'; source = parent / 'approved.json'
            supplied = self.user_brief(); self.write(source, supplied)
            self.start(root, '--brief-file', source)
            self.command('advance_build.py', root, '--run', expected=2)
            actual = self.read(root / 'travel-brief.json')
            for key, value in supplied.items(): self.assertEqual(actual[key], value, key)
            self.assertEqual(actual['end_date'], '2026-11-07')
            tasks = list((root / 'research/tasks').glob('*.json'))
            self.assertEqual(len(tasks), 9)
            for path in tasks:
                task = self.read(path)
                self.assertEqual(task['brief_file'], 'travel-brief.json')
                for key in ('travelers', 'rhythm', 'interests', 'constraints', 'must_go', 'avoid', 'budget'):
                    self.assertEqual(task['traveler_preferences'][key], supplied[key], str(path) + key)
                if task['task_id'] == 'framing':
                    for key in ('travelers', 'rhythm', 'interests', 'constraints'):
                        self.assertEqual(task['neutral_json_example']['trip'][key], supplied[key])
            decisions = self.read(root / 'trip-decisions.json')
            self.assertEqual(decisions['budget_plan']['level'], 'mainstream')
            self.assertEqual(decisions['budget_plan']['total_trip'], '18000 CNY')

    def test_existing_brief_preserved_with_only_explicit_preference_overrides(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / 'build'; supplied = self.user_brief()
            self.write(root / 'travel-brief.json', supplied)
            self.command('init_research_workspace.py', root, '--travelers', '3 adults', '--rhythm', 'slow')
            actual = self.read(root / 'travel-brief.json')
            self.assertEqual(actual['travelers'], '3 adults'); self.assertEqual(actual['rhythm'], 'slow')
            for key in supplied.keys() - {'travelers', 'rhythm'}: self.assertEqual(actual[key], supplied[key], key)

    def test_invalid_imports_or_conflicting_identity_never_overwrite_existing_data(self):
        for script in ('start_build.py', 'init_research_workspace.py'):
            for failure in ('invalid_json', 'array', 'bad_days', 'conflicting_destination', 'conflicting_dates'):
                with self.subTest(script=script, failure=failure), tempfile.TemporaryDirectory() as raw:
                    parent = Path(raw); root = parent / 'build'; source = parent / 'incoming.json'
                    supplied = self.user_brief(); self.write(root / 'travel-brief.json', supplied)
                    before = (root / 'travel-brief.json').read_bytes()
                    incoming = dict(supplied)
                    if failure == 'conflicting_destination': incoming['destination'] = 'Different Trip'
                    if failure == 'conflicting_dates': incoming['end_date'] = '2026-12-31'
                    if failure == 'bad_days': incoming['days'] = True
                    self.write(source, [] if failure == 'array' else incoming)
                    if failure == 'invalid_json': source.write_text('{broken', encoding='utf-8')
                    args = ['--brief-file', source]
                    if script == 'start_build.py':
                        args += ['--itinerary-approved', '--user-statement', 'Synthetic approval']
                    result = self.command(script, root, *args, expected=None)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual((root / 'travel-brief.json').read_bytes(), before)
                    self.assertFalse((root / 'research-plan.json').exists())
                    self.assertFalse((root / '.travel-build-state.json').exists())

    def test_cold_start_uses_only_the_explicit_current_brief(self):
        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw); previous = parent / 'previous'; root = parent / 'new'
            old = self.user_brief(); old['interests'] = ['old trip interest']
            self.write(previous / 'travel-brief.json', old)
            old_bytes = (previous / 'travel-brief.json').read_bytes()
            source = parent / 'current-approved.json'; current = self.user_brief(); self.write(source, current)
            self.start(root, '--cold-start', '--brief-file', source)
            self.command('advance_build.py', root, '--run', expected=2)
            self.assertEqual(self.read(root / 'travel-brief.json')['interests'], current['interests'])
            self.assertEqual((previous / 'travel-brief.json').read_bytes(), old_bytes)
            result = self.start(previous, '--cold-start', '--brief-file', source, expected=None)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((previous / 'travel-brief.json').read_bytes(), old_bytes)

    def test_cli_budget_and_travelers_do_not_erase_original_budget_or_extras(self):
        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw); root = parent / 'build'; source = parent / 'approved.json'
            supplied = self.user_brief(); self.write(source, supplied)
            self.start(root, '--brief-file', source, '--travelers', '5', '--budget-total', '22000 CNY')
            actual = self.read(root / 'travel-brief.json')
            self.assertEqual(actual['travelers'], '5')
            self.assertEqual(actual['budget'], supplied['budget'])
            self.assertEqual(actual['budget_total'], '22000 CNY')
            self.assertEqual(self.read(root / 'trip-decisions.json')['budget_plan']['total_trip'], '22000 CNY')

    def test_partial_import_preserves_unmentioned_nested_user_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw); root = parent / 'build'; source = parent / 'amendment.json'
            supplied = self.user_brief(); self.write(root / 'travel-brief.json', supplied)
            self.write(source, {'budget': {'total_trip': '20000 CNY'}, 'interests': ['games', 'food', 'design']})
            self.command('init_research_workspace.py', root, '--brief-file', source)
            actual = self.read(root / 'travel-brief.json')
            self.assertEqual(actual['budget'], {**supplied['budget'], 'total_trip': '20000 CNY'})
            self.assertEqual(actual['other_notes'], supplied['other_notes'])
            self.assertEqual(actual['interests'], ['games', 'food', 'design'])


if __name__ == '__main__':
    unittest.main()
