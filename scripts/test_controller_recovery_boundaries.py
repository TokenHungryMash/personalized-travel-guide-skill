"""Exercise version isolation and map ordering before expensive render/release gates."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _build_state import STATE_NAME, evaluate
import test_workflow_boundaries


class ControllerRecoveryBoundaries(unittest.TestCase):
    def test_direct_handoff_rejects_other_skill_before_writes_or_checks(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state_path = root / STATE_NAME
            original = json.dumps({'skill_root': str(root / 'other-skill')})
            state_path.write_text(original, encoding='utf8')
            with patch('_build_state.run') as runner:
                with self.assertRaisesRegex(SystemExit, 'SKILL ROOT CONFLICT'):
                    evaluate(root, run_gates=True)
                runner.assert_not_called()
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('check_handoff.py')), str(root)],
                                    capture_output=True, text=True, encoding='utf8')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('SKILL ROOT CONFLICT', result.stderr)
            self.assertEqual(state_path.read_text(encoding='utf8'), original)
            self.assertEqual([p.name for p in root.iterdir()], [STATE_NAME])

    def test_missing_maps_are_requested_before_install_render_or_final_checks(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            test_workflow_boundaries.WorkflowBoundaries().fixture(root)
            profile = root / 'destination-profile.json'
            data = json.loads(profile.read_text(encoding='utf8'))
            data.update(map_delivery='screenshots', itinerary=[{'stops': []}])
            profile.write_text(json.dumps(data), encoding='utf8')
            (root / 'index.html').unlink()
            with patch('_build_state.run', return_value=(True, 'synthetic gate')) as runner:
                state = evaluate(root, run_gates=True)
            self.assertEqual(state['stage'], 'maps_required')
            self.assertTrue(state['continuation_required'])
            self.assertFalse(state['handoff_allowed'])
            self.assertFalse(state['final_response_allowed'])
            self.assertIn('day 1', state['evidence']['route_maps'])
            scripts_run = [c.args[0].name for c in runner.call_args_list]
            self.assertNotIn('audit_product.py', scripts_run)
            self.assertNotIn('quick_forward_test.py', scripts_run)
            data.update(map_delivery='online', online_map_user_statement='我明确需要在线互动地图')
            profile.write_text(json.dumps(data), encoding='utf8')
            with patch('_build_state.run', return_value=(True, 'synthetic gate')):
                self.assertEqual(evaluate(root, run_gates=True)['stage'], 'workbench_required')


if __name__ == '__main__':
    unittest.main()
