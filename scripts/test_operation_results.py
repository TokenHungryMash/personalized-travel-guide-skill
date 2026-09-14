"""Consecutive-operation failure semantics; adapter incidents never mutate timers."""
import json
from pathlib import Path
import tempfile
import unittest
from record_operation import record
from research_checkpoint import update


class OperationResults(unittest.TestCase):
    def test_recovered_nonconsecutive_adapter_errors_do_not_accumulate(self):
        with tempfile.TemporaryDirectory() as folder:
            for step in ("core-a-read", "shopping-write", "core-assemble"):
                result = record(folder, step, "failure", "adapter")
                self.assertFalse(result["stop_required"])
                self.assertEqual(result["business_streak"], 0)
                success = record(folder, step, "success")
                self.assertEqual(success["adapter_streak"], 0)
            self.assertFalse(record(folder, "new-step", "failure", "adapter")["stop_required"])

    def test_same_step_consecutive_failures_stop_but_other_step_resets(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(record(folder, "assemble|core", "failure")["stop_required"])
            self.assertTrue(record(folder, "assemble|core", "failure")["stop_required"])
            self.assertFalse(record(folder, "download|asset-a", "failure")["stop_required"])
            record(folder, "download|asset-a", "success")
            self.assertFalse(record(folder, "assemble|core", "failure", "adapter")["stop_required"])
            self.assertFalse(record(folder, "assemble|core", "failure", "adapter")["stop_required"])

    def test_undelivered_errors_never_count_and_do_not_erase_real_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            first = record(folder, "real-command", "failure")
            self.assertEqual(first["business_streak"], 1)
            for index in range(5):
                incident = record(folder, "bad-js", "failure", "adapter", f"adapter-{index}")
                self.assertFalse(incident["stop_required"])
                self.assertEqual(incident["business_streak"], 1)
            second = record(folder, "real-command", "failure")
            self.assertTrue(second["stop_required"])
            self.assertEqual(second["business_streak"], 2)

    def test_reporting_never_changes_timer_and_duplicate_events_do_not_count_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            update(folder, "start", "core-01", ["a"], now=100)
            path = Path(folder)/".research-state/timing.json"
            original = path.read_bytes()
            record(folder, "read-a", "failure", "adapter", "tool-result-1")
            duplicate = record(folder, "read-a", "failure", "adapter", "tool-result-1")
            self.assertTrue(duplicate["duplicate_event"])
            self.assertEqual(duplicate["adapter_streak"], 1)
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(update(folder, "status", now=405)["stop_required"])
            self.assertEqual(json.loads(path.read_text())["units"][0]["started_at"], 100)


if __name__ == "__main__":
    unittest.main()
