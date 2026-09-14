"""Human-attested representative QA, separate from browser automation."""
import hashlib
from pathlib import Path

REQUIRED_CHECKS = ("desktop_layout", "mobile_layout", "no_horizontal_overflow",
                   "disclosures", "trip_mode", "trip_day_switch")


def build_fingerprint(root: Path) -> str:
    result = hashlib.sha256()
    paths = {root / "index.html", root / "destination-profile.json"}
    paths.update(root.glob("*.css"))
    paths.update(root.glob("*.js"))
    paths.update(p for p in (root / "assets").rglob("*") if p.is_file())
    paths.update(p for p in (root / "media").rglob("*") if p.is_file())
    for path in sorted(paths):
        result.update(path.relative_to(root).as_posix().encode())
        result.update(path.read_bytes() if path.is_file() else b"MISSING")
    return result.hexdigest()


def validate_manual_qa(root, qa, standard):
    failures = []
    if not standard:
        failures.append("manual representative QA is available only in standard mode")
    if qa.get("user_authorized") is not True:
        failures.append("manual QA requires explicit user authorization")
    if qa.get("status") != "passed":
        failures.append("manual QA awaits actual user test results")
    if qa.get("build_fingerprint") != build_fingerprint(root):
        failures.append("manual QA build changed; renew affected human checks")
    confirmation = qa.get("human_confirmation")
    if not isinstance(confirmation, dict):
        confirmation = {}
    for field in ("checked_at", "message_reference", "user_statement"):
        if not isinstance(confirmation.get(field), str) or not confirmation[field].strip():
            failures.append(f"manual QA missing human confirmation: {field}")
    checks = qa.get("checks")
    if not isinstance(checks, dict):
        checks = {}
    for key in REQUIRED_CHECKS:
        row = checks.get(key)
        if not isinstance(row, dict) or row.get("passed") is not True or not str(row.get("note", "")).strip():
            failures.append(f"manual interaction/layout check pending: {key}")
    return not failures, failures
