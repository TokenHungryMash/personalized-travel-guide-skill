#!/usr/bin/env python3
"""Count consecutive failures of one concrete operation; never mutate its work timer."""
import argparse
import json
from pathlib import Path
import time
from write_research_json import write_json


def record(root, step, outcome, layer="business", event_id=None):
    if not step or outcome not in {"success", "failure"} or layer not in {"business", "adapter"}:
        raise ValueError("step, success/failure outcome and business/adapter layer are required")
    path = Path(root)/".research-state/operation-results.json"
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"schema_version": 2, "events": [], "step": None, "business_streak": 0, "adapter_streak": 0}
    if event_id and any(event.get("event_id") == event_id for event in state["events"]):
        return {"duplicate_event": True, "step": state["step"], "business_streak": state["business_streak"], "adapter_streak": state["adapter_streak"], "stop_required": state["business_streak"] >= 2}
    if layer == "adapter":
        # Nothing reached the business command. Preserve delivered-command
        # history and timer state; adapter incidents never cause repeat-stop.
        state["adapter_streak"] = state["adapter_streak"]+1 if state.get("adapter_step") == step and outcome == "failure" else 1 if outcome == "failure" else 0
        state["adapter_step"] = step
    else:
        if outcome == "success" or step != state["step"]:
            state["business_streak"] = 0
        state["adapter_streak"] = 0
        state["step"] = step
        if outcome == "failure":
            state["business_streak"] += 1
    state["layer"] = layer
    state["events"].append({"step": step, "outcome": outcome, "layer": layer, "event_id": event_id, "at": time.time()})
    state["events"] = state["events"][-100:]
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, state)
    return {"step": step, "layer": layer, "outcome": outcome, "business_streak": state["business_streak"], "adapter_streak": state["adapter_streak"], "stop_required": state["business_streak"] >= 2, "timer_unchanged": True, "adapter_next_action": "retry the exact canonical launcher template" if layer == "adapter" else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbench", type=Path)
    parser.add_argument("step")
    parser.add_argument("outcome", choices=("success", "failure"))
    parser.add_argument("--layer", choices=("business", "adapter"), default="business")
    parser.add_argument("--event-id")
    args = parser.parse_args()
    try:
        result = record(args.workbench, args.step, args.outcome, args.layer, args.event_id)
    except (OSError, ValueError) as error:
        parser.exit(2, f"OPERATION REPORT FAILED: {error}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["stop_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
