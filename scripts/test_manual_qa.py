import json
from pathlib import Path
import tempfile
import unittest
from _build_state import qa_is_complete
from _manual_qa import REQUIRED_CHECKS, build_fingerprint


class ManualQA(unittest.TestCase):
    def test_consent_is_not_evidence_and_changed_build_invalidates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.html").write_text("fixture")
            (root / "destination-profile.json").write_text(json.dumps({"trip": {"quality_mode": "standard"}}))
            qa = {"validation_mode": "manual_representative", "user_authorized": True,
                  "status": "pending", "build_fingerprint": build_fingerprint(root)}
            def check():
                (root / "browser-qa.json").write_text(json.dumps(qa))
                return qa_is_complete(root)[0]
            self.assertFalse(check())
            qa["status"] = "passed"
            self.assertFalse(check())
            qa["human_confirmation"] = {"checked_at": "2026-09-12T00:00:00Z",
                "message_reference": "synthetic test fixture", "user_statement": "Fixture confirms all requested checks."}
            qa["checks"] = {key: {"passed": True, "note": "Synthetic observation for test only"} for key in REQUIRED_CHECKS}
            self.assertTrue(check())
            qa["checks"]["trip_day_switch"]["passed"] = False
            self.assertFalse(check())
            qa["checks"]["trip_day_switch"]["passed"] = True
            (root / "index.html").write_text("changed")
            self.assertFalse(check())
            qa["build_fingerprint"] = build_fingerprint(root)
            self.assertTrue(check())



if __name__ == "__main__":
    unittest.main()
