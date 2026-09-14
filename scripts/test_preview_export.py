"""Portable preview delivery must work without inventing browser acceptance."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import check_handoff
from _build_state import digest, load_json
from _manual_qa import build_fingerprint
from package_handbook import package
import test_workflow_boundaries as workflow_fixtures


class PreviewExportTests(unittest.TestCase):
    def fixture(self, root, mode='unavailable'):
        workflow_fixtures.WorkflowBoundaries().fixture(root)
        profile = {'display_name': 'Preview Fixture', 'trip': {'quality_mode': 'standard'},
                   'map_delivery': 'online', 'online_map_user_statement': 'Synthetic explicit online map request',
                   'itinerary': []}
        (root / 'destination-profile.json').write_text(json.dumps(profile), encoding='utf-8')
        report = load_json(root / 'RENDER_REPORT.json')
        report['profile_sha256'] = digest(root / 'destination-profile.json')
        (root / 'RENDER_REPORT.json').write_text(json.dumps(report), encoding='utf-8')
        qa = {'validation_mode': mode, 'status': 'pending', 'build_fingerprint': build_fingerprint(root)}
        if mode == 'manual_representative':
            qa['user_authorized'] = True
        else:
            qa['host_limitation'] = {'reason': 'Synthetic browser denial', 'tool_reference': 'fixture-only',
                                     'checked_at': '2026-09-14T00:00:00Z'}
        (root / 'browser-qa.json').write_text(json.dumps(qa), encoding='utf-8')
        return qa

    def invoke(self, root, failed=None, package_error=None):
        def gate(script, *args):
            return script.name != failed, 'synthetic gate only'
        output = io.StringIO()
        package_args = {'side_effect': package_error} if package_error else {'wraps': package}
        with patch.object(sys, 'argv', ['check_handoff.py', str(root)]), \
                patch('_build_state.run', side_effect=gate), \
                patch('package_handbook.package', **package_args) as packer, \
                contextlib.redirect_stdout(output):
            code = check_handoff.main()
        return code, load_json(root / '.travel-build-state.json'), output.getvalue(), packer.call_count

    def test_unavailable_and_manual_wait_export_once_without_qa_promotion(self):
        for mode in ('unavailable', 'manual_representative'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as raw:
                root = Path(raw) / 'build'; root.mkdir()
                qa = self.fixture(root, mode)
                code, state, output, calls = self.invoke(root)
                self.assertEqual(code, 3)
                self.assertEqual(calls, 1)
                self.assertEqual(state['stage'], 'browser_qa_required')
                self.assertEqual(state['response_state'], 'waiting_for_review')
                self.assertTrue(state['final_response_allowed'])
                self.assertFalse(state['handoff_allowed'])
                self.assertFalse(state['checks']['browser_qa_pass'])
                self.assertIn('PREVIEW OPEN / DOWNLOAD', output)
                receipt = load_json(root / 'offline-export.json')
                self.assertTrue(Path(receipt['file']).is_file())
                self.assertEqual(load_json(root / 'browser-qa.json'), qa)
                self.assertFalse((root / 'offline-qa.json').exists())
                self.assertNotIn('HANDOFF ALLOWED', output)
                before = Path(receipt['file']).stat().st_mtime_ns
                _, repeated, _, calls = self.invoke(root)
                self.assertEqual(calls, 0)
                self.assertEqual(Path(receipt['file']).stat().st_mtime_ns, before)
                self.assertFalse(repeated['handoff_allowed'])
                Path(receipt['file']).write_text('synthetic damaged export', encoding='utf-8')
                _, repaired, _, calls = self.invoke(root)
                self.assertEqual(calls, 1)
                self.assertEqual(digest(Path(receipt['file'])), load_json(root / 'offline-export.json')['sha256'])
                self.assertFalse(repaired['handoff_allowed'])

    def test_bad_automatic_gates_never_export(self):
        for failed in ('verify_research_provenance.py', 'validate_destination_data.py', 'verify_assets.py',
                       'audit_product.py', 'quick_forward_test.py'):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as raw:
                root = Path(raw) / 'build'; root.mkdir()
                self.fixture(root)
                _, state, _, calls = self.invoke(root, failed=failed)
                self.assertEqual(calls, 0)
                self.assertFalse(state['final_response_allowed'])
                self.assertFalse((root / 'offline-export.json').exists())

    def test_stale_or_missing_limitation_never_exports(self):
        for defect in ('stale', 'missing_reference', 'unapproved_manual', 'failed_status'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as raw:
                root = Path(raw) / 'build'; root.mkdir()
                qa = self.fixture(root, 'manual_representative' if defect == 'unapproved_manual' else 'unavailable')
                if defect == 'stale': qa['build_fingerprint'] = 'old-version'
                elif defect == 'missing_reference': del qa['host_limitation']['tool_reference']
                elif defect == 'failed_status': qa['status'] = 'failed'
                else: qa['user_authorized'] = False
                (root / 'browser-qa.json').write_text(json.dumps(qa), encoding='utf-8')
                _, state, _, calls = self.invoke(root)
                self.assertEqual(calls, 0)
                self.assertFalse(state['final_response_allowed'])

    def test_export_failure_requires_repair_not_preview_or_completion(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / 'build'; root.mkdir()
            self.fixture(root)
            _, state, _, calls = self.invoke(root, package_error=OSError('synthetic output failure'))
            self.assertEqual(calls, 1)
            self.assertFalse(state['final_response_allowed'])
            self.assertFalse(state['handoff_allowed'])
            self.assertTrue(state['continuation_required'])
            self.assertFalse(state['user_input_required'])
            self.assertIn('Repair the reported offline export', state['next_required_action'])
            self.assertEqual(state['evidence']['offline_export'], 'synthetic output failure')


if __name__ == '__main__':
    unittest.main()
