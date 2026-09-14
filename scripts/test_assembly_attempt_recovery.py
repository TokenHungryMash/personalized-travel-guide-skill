"""Real CLI recovery after a canonical pack gap, without timer/history resets."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from assemble_research_unit import assemble, fingerprint
from research_checkpoint import update
from install_workbench_launcher import install
from test_work_unit_cli import SHELL
from test_workdir_free_launcher import require_script_execution

SCRIPTS = Path(__file__).resolve().parent


class AssemblyRecovery(unittest.TestCase):
    def invoke(self, root, *args, code=0):
        if not SHELL:
            self.skipTest('Optional wrapper requires PowerShell; direct Python tests still run')
        require_script_execution(SHELL)
        result = subprocess.run([SHELL, "-NoProfile", "-File", str(root/"travel.ps1"), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, code, result.stdout+result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def row(self, id, kind):
        return {"id": id, "type": kind, "display_name": "中文精确地点", "latitude": 35.0, "longitude": 139.0, "map_query": "Fixture exact address", "source_url": "https://example.org/place", "description": "Offline description long enough for the real canonical record validation checks.", "hours": "Fixture hours unconfirmed", "closed_days": ["Unconfirmed fixture"], "duration_minutes": 60, "scheduled_label": "optional"}

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_invalid_coordinates_fix_retry_preserves_history_and_failure_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/"中文 独立工作台"
            root.mkdir()
            install(root)
            sight = root/"research/records/places-core/sight.json"
            invalid = self.row("sight", "sight")
            invalid.pop("latitude")
            self.write(sight, invalid)
            first = self.invoke(root, "assemble-unit", "-Pack", "places-core", code=2)
            self.assertIn("latitude", first.stdout+first.stderr)
            ledger = root/".research-state/assembly-attempts.json"
            failed = json.loads(ledger.read_text())["attempts"][0]
            self.assertEqual(failed["status"], "stopped")
            # Whitespace changes cannot unlock the same semantic input hash.
            sight.write_text(json.dumps(invalid, indent=4), encoding="utf-8")
            second = self.invoke(root, "assemble-unit", "-Pack", "places-core", code=2)
            self.assertIn("Unchanged assembly input", second.stderr)
            operation = json.loads((root/".research-state/operation-results.json").read_text())
            self.assertEqual(operation["business_streak"], 2)
            self.write(sight, self.row("sight", "sight"))
            for id, kind in (("airport", "airport"), ("station", "station")):
                self.write(root/f"research/drafts/support/{id}.json", self.row(id, kind))
            self.invoke(root, "start", "support-repair", "-Items", "airport,station")
            self.invoke(root, "batch-record", "-Pack", "places-core", "-Source", "research/drafts/support")
            self.invoke(root, "assemble-unit", "-Pack", "places-core")
            saved = json.loads(ledger.read_text())
            self.assertEqual(saved["attempts"][0], failed)
            self.assertEqual([a["status"] for a in saved["attempts"]], ["stopped", "complete"])
            self.assertEqual(len(saved["rejections"]), 1)
            self.assertNotEqual(saved["attempts"][0]["input_hash"], saved["attempts"][1]["input_hash"])
            pack = json.loads((root/"research/places/core.json").read_text(encoding="utf-8"))
            self.assertEqual(len(pack["support"]), 2)
            phase = json.loads(self.invoke(root, "status").stdout)["assembly_phases"]["assembly-places-core"]
            self.assertEqual(phase["attempt_count"], 2)
            self.assertGreaterEqual(phase["phase_wall_seconds"], phase["attempt_elapsed_seconds_total"])

    def test_active_same_hash_overrun_cannot_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            install(root)
            digest, count, deps = fingerprint(root, "places-core")
            name = "assembly-places-core-attempt-01"
            update(root, "start", name, ["places-core"], now=time.time()-301)
            self.write(root/".research-state/assembly-attempts.json", {"schema_version": 1, "attempts": [{"unit": name, "pack": "places-core", "input_hash": digest, "record_count": count, "dependencies": deps, "status": "active", "started_at": time.time()-301}], "rejections": []})
            self.invoke(root, "assemble-unit", "-Pack", "places-core", code=2)
            self.invoke(root, "assemble-unit", "-Pack", "places-core", code=2)
            attempts = json.loads((root/".research-state/assembly-attempts.json").read_text())["attempts"]
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["status"], "overrun")
            self.assertGreater(attempts[0]["elapsed_seconds"], 300)

    def test_other_active_unit_is_not_replaced_by_changed_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            install(root)
            update(root, "start", "core-01", ["sight"])
            self.invoke(root, "assemble-unit", "-Pack", "places-core", code=2)
            self.assertEqual(update(root, "status")["unit"], "core-01")

    def test_hung_child_uses_remaining_budget_and_closes_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("assemble_research_unit.subprocess.run", side_effect=subprocess.TimeoutExpired("fixture", 300)) as child:
                self.assertEqual(assemble(root, "places-core"), 2)
            self.assertGreater(child.call_args.kwargs["timeout"], 0)
            self.assertLessEqual(child.call_args.kwargs["timeout"], 300)
            ledger = json.loads((root/".research-state/assembly-attempts.json").read_text())
            self.assertEqual(ledger["attempts"][0]["status"], "stopped")
            self.assertIn("TIMEOUT", ledger["attempts"][0]["error"])
            self.assertEqual(update(root, "status")["status"], "idle")

    def test_standard_rating_gap_is_not_a_validator_gate(self):
        # Isolate rating diagnostics with a partial profile; unrelated full-profile
        # failures remain expected and are not presented as a production pass.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"profile.json"
            for ratings in ([], [{"platform": "Google", "status": "unavailable", "source_url": "https://maps.google.com/?cid=123", "checked_at": "2026-09-09T00:00:00Z", "reason": "Exact fixture entity/address matched; visible panel exposes no attributable score"}]):
                self.write(path, {"trip": {"days": 4, "quality_mode": "standard"}, "places": [dict(self.row("rating-gap", "sight"), ratings=ratings)]})
                result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS/"validate_destination_data.py"), str(path)], capture_output=True, text=True, encoding="utf-8")
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("place rating-gap rating", result.stdout)
                self.assertNotIn("Google rating record", result.stdout)
                self.assertIn("missing destination", result.stdout)


if __name__ == "__main__":
    unittest.main()
