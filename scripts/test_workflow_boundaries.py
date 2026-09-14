"""Exercise generated mode contracts and pending-review state transitions."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from _build_state import digest, evaluate, print_state, qa_is_complete
from _manual_qa import build_fingerprint

class WorkflowBoundaries(unittest.TestCase):
    def test_intake_defaults_cannot_authorize_production(self):
        with tempfile.TemporaryDirectory() as folder:
            for flag in ('--itinerary-approved', '--discussion-waived'):
                root = Path(folder) / flag.lstrip('-')
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('start_build.py')), str(root), '--destination', 'Gate City', '--days', '3', flag, '--user-statement', '按默认。'], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(root.exists())

    def test_start_build_requires_explicit_itinerary_gate(self):
        script = Path(__file__).with_name('start_build.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'blocked'
            result = subprocess.run(
                [sys.executable, str(script), str(root), '--destination', 'Gate City', '--country', 'Gate Country', '--days', '3'],
                capture_output=True,
                text=True, encoding='utf-8',
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(root.exists())
            self.assertIn('--itinerary-approved', result.stderr)

    def test_start_build_persists_verbatim_itinerary_gate(self):
        script = Path(__file__).with_name('start_build.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'approved'
            statement = '按刚才这版展开完整手册'
            result = subprocess.run(
                [sys.executable, str(script), str(root), '--destination', 'Gate City', '--country', 'Gate Country', '--days', '3', '--itinerary-approved', '--user-statement', statement],
                capture_output=True,
                text=True, encoding='utf-8',
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads((root / 'itinerary-approval.json').read_text(encoding='utf-8'))
            state = json.loads((root / '.travel-build-state.json').read_text(encoding='utf-8'))
            self.assertEqual(record['status'], 'approved')
            self.assertEqual(record['user_statement'], statement)
            self.assertEqual(state['itinerary_gate'], record)

    def test_installed_adaptation_template_advances_to_render(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            (root / 'index.html').unlink()
            (root / '.index.template.html').write_text('<!doctype html>', encoding='utf8')
            (root / 'ADAPTATION_REQUIRED.json').write_text('{}', encoding='utf8')
            with patch('_build_state.run', return_value=(True, 'synthetic gate')):
                state = evaluate(root, run_gates=False)
            self.assertEqual(state['stage'], 'render_required')


    def fixture(self, root, mode='standard'):
        for name in ('research-plan.json', 'RESEARCH_PROVENANCE.json', 'asset-manifest.json', 'trip-decisions.json'):
            (root / name).write_text('{}', encoding='utf-8')
        profile = root / 'destination-profile.json'
        profile.write_text(json.dumps({'trip': {'quality_mode': mode}}), encoding='utf-8')
        (root / 'index.html').write_text('synthetic non-Bali test fixture', encoding='utf-8')
        (root / 'RENDER_REPORT.json').write_text(json.dumps({'profile_sha256': digest(profile), 'bindings_sha256': 'fixture', 'render_method': 'official_renderer', 'canonical_template_hash_verified': True, 'custom_page_builder_detected': False}), encoding='utf-8')

    def evaluate_qa(self, root, qa, failed_script=None):
        (root / 'browser-qa.json').write_text(json.dumps(qa), encoding='utf-8')

        def run(script, *args):
            return (script.name != failed_script, 'synthetic test gate')
        with patch('_build_state.run', side_effect=run):
            return evaluate(root, run_gates=True)

    def test_manual_wait_is_not_handoff_and_flags_agree(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root)
            qa = {'validation_mode': 'manual_representative', 'user_authorized': True, 'status': 'pending', 'build_fingerprint': build_fingerprint(root)}
            state = self.evaluate_qa(root, qa)
            self.assertEqual(state['response_state'], 'waiting_for_review')
            self.assertTrue(state['final_response_allowed'])
            self.assertTrue(state['user_input_required'])
            self.assertFalse(state['handoff_allowed'])
            self.assertFalse(state['continuation_required'])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                print_state(state)
            self.assertIn('FINAL_RESPONSE_ALLOWED: true', output.getvalue())
            self.assertNotIn('FORBIDDEN', output.getvalue())
            qa['user_authorized'] = False
            self.assertFalse(self.evaluate_qa(root, qa)['final_response_allowed'])

    def test_unavailable_needs_real_record_and_cannot_bypass_failed_gates(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root)
            qa = {'validation_mode': 'unavailable', 'status': 'pending', 'build_fingerprint': build_fingerprint(root), 'host_limitation': {'reason': 'synthetic denial', 'tool_reference': 'fixture-only', 'checked_at': '2026-09-13T00:00:00Z'}}
            state = self.evaluate_qa(root, qa)
            self.assertTrue(state['final_response_allowed'])
            self.assertFalse(state['handoff_allowed'])
            for failed in ('verify_research_provenance.py', 'validate_destination_data.py', 'verify_assets.py', 'audit_product.py', 'quick_forward_test.py'):
                with self.subTest(failed=failed):
                    self.assertFalse(self.evaluate_qa(root, qa, failed)['final_response_allowed'])
            del qa['host_limitation']['tool_reference']
            self.assertFalse(self.evaluate_qa(root, qa)['final_response_allowed'])

    def test_publication_depth_does_not_accept_representative_shortcut(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root)
            for name in ('desktop.png', 'mobile.png'):
                (root / name).write_bytes(b'synthetic fixture')
            qa = {'validation_mode': 'representative', 'desktop': {'passed': True, 'inner_width': 1440, 'inner_height': 900, 'horizontal_overflow': False}, 'mobile': {'passed': True, 'inner_width': 390, 'inner_height': 844, 'horizontal_overflow': False, 'match_media_mobile': True}, 'interactions': {'disclosures': True, 'trip_mode': True}, 'screenshots': ['desktop.png', 'mobile.png']}
            qa['build_fingerprint'] = build_fingerprint(root)
            (root / 'browser-qa.json').write_text(json.dumps(qa), encoding='utf-8')
            self.assertTrue(qa_is_complete(root)[0])
            qa['validation_mode'] = 'publication_depth'
            (root / 'browser-qa.json').write_text(json.dumps(qa), encoding='utf-8')
            self.assertFalse(qa_is_complete(root)[0])
if __name__ == '__main__':
    unittest.main()
