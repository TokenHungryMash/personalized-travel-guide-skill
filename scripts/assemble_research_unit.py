#!/usr/bin/env python3
"""One deterministic status/start/assemble/validate/finish operation for a place pack."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from research_checkpoint import update
from research_records import PACK_FILES
from write_research_json import write_json


def fingerprint(root, pack):
    """Hash semantic inputs, not timestamps, formatting or an invented unit name."""
    records = []
    for path in sorted((root/"research/records"/pack).glob("*.json")):
        text = path.read_text(encoding="utf-8-sig")
        try:
            value = json.loads(text)
        except ValueError:
            value = {"invalid_json_text": text}
        records.append([path.name, value])
    scripts = Path(__file__).resolve().parent
    dependencies = {}
    for path in (scripts/"research_records.py", scripts/"validate_research_pack.py", scripts/"write_research_json.py", scripts.parent/"assets/research-pack-contract.json"):
        dependencies[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {"records": records, "dependencies": dependencies}
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return digest, len(records), dependencies


def assemble(root, pack):
    root = root.resolve()
    state_path = root/".research-state/assembly-attempts.json"
    status = update(root, "status")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"schema_version": 1, "attempts": [], "rejections": []}
    digest, count, dependencies = fingerprint(root, pack)
    previous = next((row for row in reversed(state["attempts"]) if row["pack"] == pack and row["input_hash"] == digest), None)
    if status["status"] == "active":
        if not previous or previous["unit"] != status["unit"]:
            raise ValueError(f"Active unit {status['unit']} must finish or stop first; assembly cannot replace its timer")
        if status["stop_required"]:
            stopped = update(root, "stop", note="Assembly attempt exceeded five-minute wall clock")
            previous.update(status="overrun", elapsed_seconds=stopped["elapsed_seconds"], ended_at=time.time())
            write_json(state_path, state)
            raise ValueError("Assembly attempt exceeded five minutes; retained original timer, stop and repair")
        attempt = previous
    else:
        if previous:
            state["rejections"].append({"pack": pack, "input_hash": digest, "attempt_id": previous["unit"], "at": time.time(), "reason": "unchanged_input"})
            write_json(state_path, state)
            raise ValueError("Unchanged assembly input: do not blindly retry or rename the unit; correct records or validator dependencies first. Previous attempt history is retained.")
        number = 1 + sum(row["pack"] == pack for row in state["attempts"])
        unit = f"assembly-{pack}-attempt-{number:02d}"
        update(root, "start", unit, [pack])
        attempt = {"unit": unit, "pack": pack, "input_hash": digest, "record_count": count, "dependencies": dependencies, "status": "active", "started_at": time.time()}
        state["attempts"].append(attempt)
        write_json(state_path, state)
    # Bound the real child process too: a hung validator must not keep running
    # beyond the remaining wall-clock budget of an existing attempt.
    remaining = max(0.001, 300-update(root, "status")["elapsed_seconds"])
    try:
        result = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).with_name("research_records.py")), "assemble", str(root), pack, "--finish-unit"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=remaining)
    except subprocess.TimeoutExpired:
        update(root, "stop", note="Assembly child exceeded remaining five-minute wall-clock budget")
        result = subprocess.CompletedProcess([], 2, "", "ASSEMBLY TIMEOUT: child stopped at attempt wall-clock limit\n")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    timing = json.loads((root/".research-state/timing.json").read_text(encoding="utf-8"))
    row = next(row for row in reversed(timing["units"]) if row["unit"] == attempt["unit"])
    if row["status"] == "active":
        update(root, "stop", note="Assembly process exited without closing checkpoint")
        timing = json.loads((root/".research-state/timing.json").read_text(encoding="utf-8"))
        row = next(row for row in reversed(timing["units"]) if row["unit"] == attempt["unit"])
    attempt.update(status="overrun" if row["elapsed_seconds"] > 300 else row["status"], ended_at=row["ended_at"], elapsed_seconds=row["elapsed_seconds"], returncode=result.returncode, error=(result.stderr or result.stdout)[-4000:] if result.returncode else None)
    write_json(state_path, state)
    phase = [item for item in state["attempts"] if item["pack"] == pack]
    print(json.dumps({"assembly_attempt": attempt["unit"], "input_hash": digest, "status": attempt["status"], "phase_attempt_count": len(phase), "phase_wall_seconds": round(time.time()-min(item["started_at"] for item in phase), 3), "attempt_elapsed_seconds_total": round(sum(item.get("elapsed_seconds", 0) for item in phase), 3)}))
    return result.returncode if result.returncode else (0 if row["status"] == "complete" else 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbench", type=Path)
    parser.add_argument("pack", choices=tuple(PACK_FILES))
    args = parser.parse_args()
    try:
        return assemble(args.workbench, args.pack)
    except (OSError, ValueError) as error:
        parser.exit(2, f"ASSEMBLY UNIT FAILED: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
