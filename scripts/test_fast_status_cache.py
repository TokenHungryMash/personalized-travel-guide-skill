"""Check fast status reuse without skipping changed inputs or final checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _build_state import digest, evaluate, save
from plan_incremental_validation import runtime_digest


class FastStatusTests(unittest.TestCase):
    def test_status_reuses_checks_but_edits_and_final_gate_recheck(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            profile = root / "destination-profile.json"
            profile.write_text(json.dumps({"trip": {"quality_mode": "standard"}}), encoding="utf-8")
            for name in ("research-plan.json", "RESEARCH_PROVENANCE.json", "asset-manifest.json", "trip-decisions.json"):
                (root / name).write_text("{}", encoding="utf-8")
            (root / "index.html").write_text("test", encoding="utf-8")
            (root / "RENDER_REPORT.json").write_text(json.dumps({"profile_sha256": digest(profile), "bindings_sha256": "test"}), encoding="utf-8")
            asset = root / "image.jpg"
            asset.write_bytes(b"first")
            with patch("_build_state.run", return_value=(True, "PASS")) as runner, patch("_build_state.qa_is_complete", return_value=(True, [])), patch("_offline_qa.export_state", return_value=('complete', 'fixture export QA', False)):
                save(root, evaluate(root, run_gates=False))
                self.assertGreater(runner.call_count, 0)
                runner.reset_mock()
                self.assertTrue(evaluate(root, run_gates=False)["handoff_allowed"])
                runner.assert_not_called()
                asset.write_bytes(b"changed")
                save(root, evaluate(root, run_gates=False))
                self.assertGreater(runner.call_count, 0)
                runner.reset_mock()
                evaluate(root, run_gates=True)
                self.assertGreater(runner.call_count, 0)

    def test_injected_data_does_not_masquerade_as_runtime_change(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "trip-mode.js"
            path.write_text('var TRIP_MODE_DATA=[{"theme":"one; day"}];\nfunction render(){return 1}', encoding="utf-8")
            original = runtime_digest(path)
            path.write_text('var TRIP_MODE_DATA=[{"theme":"two", "stops":[]}];\nfunction render(){return 1}', encoding="utf-8")
            self.assertEqual(original, runtime_digest(path))
            path.write_text('var TRIP_MODE_DATA=[];\nfunction render(){return 2}', encoding="utf-8")
            self.assertNotEqual(original, runtime_digest(path))


if __name__ == "__main__":
    unittest.main()
