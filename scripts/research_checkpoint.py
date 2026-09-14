#!/usr/bin/env python3
"""Time real bounded work units without treating a whole dependency phase as a stopwatch."""
import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import time
from write_research_json import write_json


def update(root, action, unit=None, items=None, note="", limit=300, now=None):
    now = time.time() if now is None else now
    path = Path(root) / ".research-state" / "timing.json"
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"started_at": now, "units": []}
    active = next((row for row in reversed(state["units"]) if row["status"] == "active"), None)
    if action == "start":
        if active:
            raise ValueError(f"finish or stop active unit {active['unit']} before starting another")
        if not unit or not items:
            raise ValueError("start requires --unit and --items naming concrete records/outputs")
        if re.match(r"(?:places-)?core(?:[-_/]|$)", unit) and len(items) > 2:
            raise ValueError("core research units allow at most 2 places; use 1 when Google/source/image work is unresolved, before starting the timer")
        if limit <= 0:
            raise ValueError("limit must be positive")
        active = {"unit": unit, "items": items, "started_at": now, "started_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(), "limit_seconds": limit, "status": "active"}
        state["units"].append(active)
    elif action in {"finish", "stop"}:
        if not active:
            raise ValueError("no active work unit")
        elapsed = max(0, now - active["started_at"])
        active.update(ended_at=now, elapsed_seconds=round(elapsed, 3), note=note,
                      status="stopped" if action == "stop" else "overrun" if elapsed > active["limit_seconds"] else "complete")
    elapsed = max(0, now - active["started_at"]) if active else 0
    overrun = bool(active and (active["status"] == "overrun" or (active["status"] == "active" and elapsed > active["limit_seconds"])))
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, state)
    phases = {}
    for row in state["units"]:
        if row["unit"].startswith("assembly-"):
            phase = row["unit"].split("-attempt-")[0]
            summary = phases.setdefault(phase, {"attempt_count": 0, "started_at": row["started_at"], "attempt_elapsed_seconds_total": 0})
            summary["attempt_count"] += 1
            summary["started_at"] = min(summary["started_at"], row["started_at"])
            summary["attempt_elapsed_seconds_total"] += row.get("elapsed_seconds", max(0, now-row["started_at"]))
            summary["phase_wall_seconds"] = round(max(0, now-summary["started_at"]), 3)
    return {"unit": active["unit"] if active else None, "status": active["status"] if active else "idle", "elapsed_seconds": round(elapsed, 3), "total_wall_seconds": round(max(0, now-state["started_at"]), 3), "stop_required": overrun, "assembly_phases": phases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbench", type=Path)
    parser.add_argument("action", choices=("start", "status", "finish", "stop"))
    parser.add_argument("--unit")
    parser.add_argument("--items", nargs="+")
    parser.add_argument("--note", default="")
    parser.add_argument("--limit-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        result = update(args.workbench, args.action, args.unit, args.items, args.note, args.limit_seconds)
    except (OSError, ValueError) as error:
        parser.exit(2, f"CHECKPOINT FAILED: {error}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["stop_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
