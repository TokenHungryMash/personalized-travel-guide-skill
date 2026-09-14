"""Launch from an unrelated directory; batch shopping/food without a workdir field."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
SHELL = shutil.which("pwsh") or shutil.which("powershell")


def require_script_execution(shell):
    """Probe a harmless local script, without changing any execution policy."""
    with tempfile.TemporaryDirectory() as folder:
        probe = Path(folder)/'probe.ps1'
        probe.write_text("Write-Output 'TRAVEL_SCRIPT_PROBE_OK'\n", encoding='utf8')
        result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-File', str(probe)], capture_output=True, text=True, encoding='utf8', errors='replace', timeout=20)
    output = result.stdout + result.stderr
    if result.returncode == 0 and 'TRAVEL_SCRIPT_PROBE_OK' in result.stdout:
        return
    if any(marker in output for marker in ('PSSecurityException', 'UnauthorizedAccess', 'running scripts is disabled', '禁止运行脚本', 'is not digitally signed')):
        raise unittest.SkipTest('Optional PowerShell launcher blocked by execution policy; direct Python remains available. Launcher behavior NOT verified.')
    raise AssertionError('PowerShell probe failed for an unexpected reason: ' + output)


class ScriptExecutionProbe(unittest.TestCase):
    def test_policy_denial_is_an_explicit_skip(self):
        from unittest.mock import patch
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'PSSecurityException')):
            with self.assertRaises(unittest.SkipTest):
                require_script_execution('synthetic-shell')

    def test_other_failures_are_not_hidden_as_skips(self):
        from unittest.mock import patch
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'unexpected failure')):
            with self.assertRaises(AssertionError):
                require_script_execution('synthetic-shell')


@unittest.skipUnless(os.name == "nt" and SHELL, "Windows launcher requires PowerShell")
class BoundLauncher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_script_execution(SHELL)

    def test_invalid_explicit_interpreter_does_not_silently_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'guide'
            launcher = self.init(root)
            env = dict(os.environ, TRAVEL_GUIDE_PYTHON=str(root/'missing-python.exe'))
            result = subprocess.run([SHELL, '-NoProfile', '-File', str(launcher), 'status'], env=env, capture_output=True, text=True, encoding='utf8')
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn('TRAVEL_GUIDE_PYTHON', result.stderr)

    def init(self, root):
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS/"init_research_workspace.py"), str(root), "--destination", "Fixture", "--country", "Japan", "--days", "4"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn("OPTIONAL POWERSHELL LAUNCHER:", result.stdout)
        return root/"travel.ps1"

    def invoke(self, launcher, caller, *args, code=0):
        # The caller is deliberately another directory, proving that launcher's
        # binding rather than an exec_command.workdir field selects the workbench.
        result = subprocess.run([SHELL, "-NoProfile", "-File", str(launcher), *args], cwd=caller, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, code, result.stdout+result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def record(self, id, kind):
        return {"id": id, "type": kind, "display_name": "中文店铺或产品", "latitude": 35.0, "longitude": 139.0, "map_query": "Exact fixture", "source_url": "https://example.org", "description": "An independently authored offline fixture description with sufficient length.", "why_buy": "Synthetic local specialty", "best_for": "Fixture travelers", "where_to_buy": "Fixture shop", "category": "local", "buying_tip": "Fixture buying guidance", "brand_highlights": ["Fixture"], "scheduled_label": "optional", "hours": "Fixture hours unconfirmed", "closed_days": ["Unconfirmed fixture"], "signature_dishes": "Fixture dish A and dish B"}

    def test_shopping_and_restaurants_batch_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as folder:
            caller = Path(folder)/"调用目录"
            caller.mkdir()
            root = Path(folder)/"绑定 工作台"
            launcher = self.init(root)
            for pack, kinds in (("places-shopping", ["shop", "souvenir"]), ("places-food", ["restaurant", "restaurant"])):
                source = root/"research/drafts"/pack
                source.mkdir()
                for index, kind in enumerate(kinds):
                    (source/f"record-{index}.json").write_text(json.dumps(self.record(f"{kind}-{index}", kind), ensure_ascii=False), encoding="utf-8")
                self.invoke(launcher, caller, "start", pack+"-01", "-Items", "record-a,record-b")
                self.invoke(launcher, caller, "batch-record", "-Pack", pack, "-Source", "research/drafts/"+pack)
                self.invoke(launcher, caller, "assemble-unit", "-Pack", pack)
            self.assertTrue((root/"research/places/shopping.json").is_file())
            self.assertTrue((root/"research/places/restaurants.json").is_file())
            self.assertFalse((caller/".research-state").exists())
            self.assertFalse((caller/"research").exists())
            timing = json.loads((root/".research-state/timing.json").read_text())
            self.assertEqual([unit["status"] for unit in timing["units"]], ["complete"]*4)

    def test_batch_validates_every_record_before_saving_any(self):
        with tempfile.TemporaryDirectory() as folder:
            caller = Path(folder)
            root = caller/"工作台"
            launcher = self.init(root)
            source = root/"research/drafts/bad-batch"
            source.mkdir()
            (source/"a.json").write_text(json.dumps(self.record("a", "restaurant")), encoding="utf-8")
            (source/"b.json").write_text('{"id":"b" "type":"restaurant"}', encoding="utf-8")
            self.invoke(launcher, caller, "start", "food-01", "-Items", "a,b")
            self.invoke(launcher, caller, "batch-record", "-Pack", "places-food", "-Source", "research/drafts/bad-batch", code=2)
            self.assertFalse((root/"research/records/places-food/a.json").exists())


if __name__ == "__main__":
    unittest.main()
