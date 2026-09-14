"""Product smoke checks stay read-only; installer regressions run only on request."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from _current_system_adapter import runtime_bindings
import quick_forward_test as forward


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


def fixture(root):
    profile = {
        'destination': 'Synthetic Fixture', 'display_name': '合成测试城',
        'country': 'Testland', 'year': 2026, 'places': [], 'itinerary': [],
        'trip': {'start_date': 'pending', 'end_date': 'pending'},
        'cover': {'image': 'assets/fixture.jpg', 'title': '测试', 'kicker': 'FIXTURE', 'summary': '合成测试'},
        'module_groups': {'language': {'language_code': 'en-US'}, 'travel_notes': []},
    }
    for source in (ROOT / 'assets/current-system/product').iterdir():
        if source.suffix in {'.js', '.css', '.json'}:
            shutil.copy2(source, root / source.name)
    for binding in runtime_bindings(profile):
        (root / binding['path']).write_text(binding['content'], encoding='utf-8')
    (root / 'destination-profile.json').write_text(json.dumps(profile), encoding='utf-8')
    sections = ''.join(f'<section id="{name}"></section>' for name in
                       ('contents', 'route', 'sights', 'shops', 'move', 'food', 'booking', 'words', 'tips'))
    scripts = ''.join(f'<script src="{path.name}"></script>' for path in sorted(root.glob('*.js')))
    (root / 'index.html').write_text(
        '<!doctype html><html><head><link rel="stylesheet" href="tokens.css"></head><body>'
        + sections + '<div class="movement-section hotel-chapter-fold"></div>' + scripts + '</body></html>',
        encoding='utf-8',
    )
    for folder in ('research', 'qa', '.research-backups'):
        target = root / folder / 'must-not-be-read.bin'
        target.parent.mkdir()
        target.write_bytes(b'not a public product input\xff')


def hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


@unittest.skipUnless(NODE, 'A real Node executable is required for JavaScript syntax tests')
class ProductSmokeScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        fixture(self.root)

    def check(self, node=NODE):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = forward.check_product(self.root, node)
        return result, output.getvalue()

    def test_default_main_does_not_install_copy_recurse_or_mutate(self):
        before = hashes(self.root)
        with patch.object(sys, 'argv', ['quick_forward_test.py', str(self.root), '--node', NODE]), \
                patch.object(forward, 'check_skill_regression', side_effect=AssertionError('unexpected Skill self-test')), \
                patch.object(shutil, 'copytree', side_effect=AssertionError('unexpected destination copy')), \
                patch.object(Path, 'rglob', side_effect=AssertionError('unexpected recursive workbench scan')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(forward.main(), 0)
        self.assertEqual(hashes(self.root), before)

    def test_bad_script_is_rejected_by_real_node(self):
        (self.root / 'invalid.js').write_text('const broken = ;', encoding='utf-8')
        path = self.root / 'index.html'
        path.write_text(path.read_text(encoding='utf-8').replace('</body>', '<script src="invalid.js"></script></body>'), encoding='utf-8')
        result, output = self.check()
        self.assertEqual(result, 2)
        self.assertIn('JavaScript syntax invalid.js', output)

    def test_missing_runtime_is_rejected_without_traceback(self):
        (self.root / 'trip-mode.js').unlink()
        result, output = self.check()
        self.assertEqual(result, 2)
        self.assertIn('Missing or unsafe runtime script: trip-mode.js', output)
        self.assertNotIn('Traceback', output)

    def test_profile_runtime_mismatch_is_rejected(self):
        path = self.root / 'audit-itinerary-data.js'
        path.write_text(path.read_text(encoding='utf-8') + '\n// unsynchronized content\n', encoding='utf-8')
        result, output = self.check()
        self.assertEqual(result, 2)
        self.assertIn('current runtime differs from profile adapter: audit-itinerary-data.js', output)

    def test_missing_chapter_is_rejected(self):
        path = self.root / 'index.html'
        path.write_text(path.read_text(encoding='utf-8').replace('id="contents"', 'id="removed"'), encoding='utf-8')
        result, output = self.check()
        self.assertEqual(result, 2)
        self.assertIn('product invariants lost: id="contents"', output)

    def test_absolute_host_node_works_when_path_discovery_fails(self):
        with patch.object(shutil, 'which', return_value=None):
            result, output = self.check(NODE)
        self.assertEqual(result, 0, output)


class NodeDiscovery(unittest.TestCase):
    def test_missing_node_does_not_claim_syntax_pass(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'JavaScript syntax not verified'):
                forward.resolve_node()

    @unittest.skipUnless(NODE, 'A real Node executable is required')
    def test_environment_node_can_live_outside_path(self):
        with patch.dict(os.environ, {'TRAVEL_GUIDE_NODE': NODE}), patch.object(shutil, 'which', return_value=None):
            self.assertEqual(forward.resolve_node(), str(Path(NODE).resolve()))


class SkillReleaseRegression(unittest.TestCase):
    def test_explicit_self_test_installs_and_rejects_dirty_fixture(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(forward.check_skill_regression(), 0)

    def test_installer_failure_is_not_hidden(self):
        failed = subprocess.CompletedProcess([], 1, '', 'synthetic installer failure')
        with patch.object(forward.subprocess, 'run', return_value=failed), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(forward.check_skill_regression(), 2)


if __name__ == '__main__':
    unittest.main()
