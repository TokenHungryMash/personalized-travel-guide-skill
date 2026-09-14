"""Exercise independent Chinese records, atomic assembly and honest core unit limits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from research_checkpoint import update

SCRIPT = Path(__file__).with_name("research_records.py")


class RecordAssembly(unittest.TestCase):
    def run_cli(self, root, action, *args, code=0):
        process = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), action, str(root), "places-core", *args], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, code, process.stdout+process.stderr)
        self.assertNotIn("Traceback", process.stderr)
        return json.loads(process.stdout)

    def record(self, id, type="sight"):
        return {"id": id, "type": type, "display_name": "中文景点“引号”与逗号，保存原文", "latitude": 35.0, "longitude": 139.0, "map_query": "Fixture exact map", "source_url": "https://example.org/fixture", "description": "Offline fixture with enough descriptive characters to meet the local record contract.", "hours": "Fixture hours unconfirmed", "closed_days": ["Unconfirmed fixture"], "duration_minutes": 60, "scheduled_label": "可选"}

    def test_multi_record_cli_assembly_and_failed_record_preserves_saved_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/"多记录 中文目录"
            root.mkdir()
            created = self.run_cli(root, "new", "--id", "a", "--type", "sight")
            self.assertEqual(created["status"], "draft_scaffold")
            for id, kind in (("a", "sight"), ("b", "sight"), ("station", "station")):
                stage = root/"research/drafts"/(id+".next.json")
                stage.write_text(json.dumps(self.record(id, kind), ensure_ascii=False), encoding="utf-8")
                self.run_cli(root, "add", "--record", str(stage))
            update(root, "start", "core-assembly", ["core-pack"])
            result = self.run_cli(root, "assemble", "--finish-unit")
            target = Path(result["file"])
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual([record["id"] for record in data["sights"]], ["a", "b"])
            self.assertEqual(len(data["support"]), 1)
            self.assertEqual(data["sights"][0]["display_name"], self.record("a")["display_name"])
            self.assertEqual(result["checkpoint"]["status"], "complete")
            original = target.read_bytes()
            bad = root/"research/drafts/bad.json"
            bad.write_text('{"id":"b" "type":"sight"}', encoding="utf-8")
            update(root, "start", "core-repair", ["b"])
            result = self.run_cli(root, "add", "--record", str(bad), "--finish-unit", code=2)
            self.assertEqual(result["checkpoint"]["status"], "stopped")
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(json.loads((root/"research/records/places-core/b.json").read_text(encoding="utf-8"))["id"], "b")

    def test_core_limit_and_overrun_cannot_be_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "at most 2"):
                update(folder, "start", "core-01", ["a", "b", "c"], now=100)
            update(folder, "start", "core-01", ["a"], now=100)
            self.assertTrue(update(folder, "status", now=405)["stop_required"])
            with self.assertRaisesRegex(ValueError, "active unit"):
                update(folder, "start", "core-renamed", ["a"], now=406)
            ended = update(folder, "finish", now=407)
            self.assertEqual(ended["status"], "overrun")
            self.assertEqual(ended["elapsed_seconds"], 307)


if __name__ == "__main__":
    unittest.main()
