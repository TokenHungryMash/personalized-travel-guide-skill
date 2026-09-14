#!/usr/bin/env python3
"""Cold-start regression using only generated task instructions and examples."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


def run(*args: str) -> None:
    result = subprocess.run([sys.executable, *args], capture_output=True)
    if result.returncode:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise SystemExit(output)


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    scripts = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="travel-cold-start-") as raw:
        root = Path(raw) / "chiang-mai"
        run(str(scripts / "start_build.py"), str(root), "--destination", "Chiang Mai", "--country", "Thailand", "--start-date", "2026-11-10", "--days", "5", "--discussion-waived", "--user-statement", "fixture waiver")
        state = json.loads((root / ".travel-build-state.json").read_text(encoding="utf-8"))
        assert state["quality_mode"] == "standard", "new builds must default to the ordinary edition"
        run(str(scripts / "init_research_workspace.py"), str(root))
        brief = json.loads((root / "travel-brief.json").read_text(encoding="utf-8"))
        assert brief["start_date"] == "2026-11-10"
        assert brief["end_date"] == "2026-11-14"

        framing_task = json.loads((root / "research/tasks/framing.json").read_text(encoding="utf-8"))
        assert set(framing_task["delegation_contract"]) == {"scope", "context", "handoff"}
        assert "target_file" in framing_task["delegation_contract"]["scope"]
        framing = framing_task["neutral_json_example"]
        framing["destination"] = "Chiang Mai"
        framing["display_name"] = "清迈"
        framing["country"] = "Thailand"
        framing["trip"].update({"start_date": brief["start_date"], "end_date": brief["end_date"], "days": brief["days"]})
        write(root / framing_task["target_file"], framing)
        run(str(scripts / "validate_research_pack.py"), "framing", str(root / framing_task["target_file"]))

        itinerary_task = json.loads((root / "research/tasks/itinerary.json").read_text(encoding="utf-8"))
        seed = itinerary_task["neutral_json_example"]
        itinerary = []
        for offset in range(5):
            day = json.loads(json.dumps(seed, ensure_ascii=False))
            day["date"] = (date.fromisoformat(brief["start_date"]) + timedelta(days=offset)).isoformat()
            day["theme"] = f"第 {offset + 1} 天路线"
            itinerary.append(day)
        write(root / itinerary_task["target_file"], itinerary)
        run(str(scripts / "validate_research_pack.py"), "itinerary", str(root / itinerary_task["target_file"]))
    print("PASS cold start inherits dates and generated framing/itinerary instructions validate without validator-source knowledge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
