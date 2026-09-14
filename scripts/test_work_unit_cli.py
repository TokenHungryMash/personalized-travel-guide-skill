"""Exercise the Windows wrapper and save/finish integration through real processes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from test_workdir_free_launcher import require_script_execution

SCRIPTS = Path(__file__).resolve().parent
SHELL = shutil.which("pwsh") or shutil.which("powershell")


@unittest.skipUnless(os.name == "nt" and SHELL, "Windows wrapper requires PowerShell")
class WorkUnitCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_script_execution(SHELL)

    def invoke(self, root, action, *args, code=0):
        result = subprocess.run([SHELL, "-NoProfile", "-File", str(SCRIPTS/"work_unit.ps1"), action, ".", "-PythonExecutable", sys.executable, *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, code, result.stdout+result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def timing(self, root):
        return json.loads((root/".research-state/timing.json").read_text(encoding="utf-8"))

    def test_start_status_save_and_auto_finish(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/"中文 工作单元"
            root.mkdir()
            self.invoke(root, "start", "core-01", "-Items", "a,b")
            status = json.loads(self.invoke(root, "status").stdout)
            self.assertEqual(status["status"], "active")
            stage = root/"research/drafts/批次 next.json"
            stage.parent.mkdir(parents=True)
            stage.write_text('{"records": ["a", "b"]}', encoding="utf-8")
            self.invoke(root, "save", "-Target", "research/drafts/批次.json", "-Source", "research/drafts/批次 next.json")
            last = self.timing(root)["units"][-1]
            self.assertEqual(last["status"], "complete")
            self.assertEqual(last["items"], ["a", "b"])
            self.assertGreater(last["elapsed_seconds"], 0)
            self.assertTrue((root/"research/drafts/批次.json").is_file())
            self.invoke(root, "finish", code=2)

    def test_failed_save_stops_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.invoke(root, "start", "framing", "-Items", "framing")
            target = root/"research/framing.json"
            target.parent.mkdir()
            target.write_text('{"keep": true}', encoding="utf-8")
            stage = target.with_suffix(".next.json")
            stage.write_text('{}', encoding="utf-8")
            self.invoke(root, "save", "-Target", "research/framing.json", "-Source", "research/framing.next.json", "-Pack", "framing", code=2)
            self.assertEqual(json.loads(target.read_text()), {"keep": True})
            self.assertEqual(self.timing(root)["units"][-1]["status"], "stopped")

    def test_overrun_save_is_retained_and_nonzero(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.invoke(root, "start", "core-01", "-Items", "a")
            state = self.timing(root)
            # Simulate a unit started over five minutes ago, without sleeping
            # during tests. The production command receives no clock override.
            state["units"][0]["started_at"] = time.time()-301
            state["started_at"] = state["units"][0]["started_at"]
            (root/".research-state/timing.json").write_text(json.dumps(state), encoding="utf-8")
            source = root/"research/drafts/next.json"
            source.parent.mkdir(parents=True)
            source.write_text('{"a": true}', encoding="utf-8")
            self.invoke(root, "save", "-Target", "research/drafts/saved.json", "-Source", "research/drafts/next.json", code=2)
            last = self.timing(root)["units"][-1]
            self.assertEqual(last["status"], "overrun")
            self.assertGreaterEqual(last["elapsed_seconds"], 301)
            self.assertTrue((root/"research/drafts/saved.json").is_file())

    def test_explicit_finish_and_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.invoke(root, "start", "lookup-01", "-Items", "a")
            self.invoke(root, "finish", "-Note", "Saved source evidence")
            self.invoke(root, "start", "lookup-02", "-Items", "b")
            self.invoke(root, "stop", "-Note", "Repeated failure")
            self.assertEqual([unit["status"] for unit in self.timing(root)["units"]], ["complete", "stopped"])

    def test_record_commands_are_wired_to_same_wrapper(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for id, kind in (("a", "sight"), ("station", "station")):
                self.invoke(root, "start", "core-"+id, "-Items", id)
                self.invoke(root, "new-record", id, "-Pack", "places-core", "-RecordType", kind)
                path = root/"research/drafts"/(id+".next.json")
                record = json.loads(path.read_text(encoding="utf-8"))
                record.update(latitude=35.0, longitude=139.0, display_name="中文地点", map_query="Exact fixture map", source_url="https://example.org", description="An offline fixture description long enough for the canonical record validator.", hours="Fixture hours unconfirmed", closed_days=["Unconfirmed fixture"], duration_minutes=30, scheduled_label="optional")
                path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
                self.invoke(root, "add-record", "-Pack", "places-core", "-Source", str(path.relative_to(root)))
            self.invoke(root, "start", "core-assembly", "-Items", "core-pack")
            self.invoke(root, "assemble-pack", "-Pack", "places-core")
            self.assertTrue((root/"research/places/core.json").is_file())
            self.assertEqual([row["status"] for row in self.timing(root)["units"]], ["complete"]*3)

    def test_one_call_assembles_eight_sights_and_records_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/"八景点 中文"
            records = root/"research/records/places-core"
            records.mkdir(parents=True)
            for index in range(9):
                row = {"id": f"place-{index}", "type": "sight" if index < 8 else "station", "display_name": f"中文地点{index}", "latitude": 35.0, "longitude": 139.0, "map_query": "Exact fixture", "source_url": "https://example.org", "description": "Offline fixture description long enough for canonical per-record validation.", "hours": "Fixture hours unconfirmed", "closed_days": ["Unconfirmed fixture"], "duration_minutes": 60, "scheduled_label": "optional"}
                (records/(row["id"]+".json")).write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
            self.invoke(root, "assemble-unit", "-Pack", "places-core")
            pack = json.loads((root/"research/places/core.json").read_text(encoding="utf-8"))
            self.assertEqual(len(pack["sights"]), 8)
            self.assertEqual(len(pack["support"]), 1)
            self.assertEqual(self.timing(root)["units"][-1]["status"], "complete")
            operations = json.loads((root/".research-state/operation-results.json").read_text(encoding="utf-8"))
            self.assertEqual(operations["business_streak"], 0)

    def test_auto_failure_counter_and_adapter_report_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.invoke(root, "assemble-unit", "-Pack", "places-core", code=2)
            self.invoke(root, "assemble-unit", "-Pack", "places-core", code=2)
            operations = json.loads((root/".research-state/operation-results.json").read_text(encoding="utf-8"))
            self.assertEqual(operations["business_streak"], 2)
            # Successful status is recovery and resets the consecutive streak.
            self.invoke(root, "status")
            before = (root/".research-state/timing.json").read_bytes()
            self.invoke(root, "report", "-Step", "read-next", "-Outcome", "failure", "-Layer", "adapter", "-EventId", "adapter-1")
            self.assertEqual((root/".research-state/timing.json").read_bytes(), before)
            operations = json.loads((root/".research-state/operation-results.json").read_text(encoding="utf-8"))
            self.assertEqual(operations["business_streak"], 0)
            self.assertEqual(operations["adapter_streak"], 1)


if __name__ == "__main__":
    unittest.main()
