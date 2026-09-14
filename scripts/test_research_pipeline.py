#!/usr/bin/env python3
"""Smoke-test the research queue and compiler with an already valid profile."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call(script: Path, *args: str) -> None:
    result = subprocess.run([sys.executable, str(script), *args])
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("valid_profile", type=Path)
    args = parser.parse_args()
    source = json.loads(args.valid_profile.read_text(encoding="utf-8"))
    scripts = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="travel-research-test-") as raw:
        root = Path(raw)
        trip = source["trip"]
        call(
            scripts / "init_research_workspace.py", str(root),
            "--destination", source["destination"], "--display-name", source["display_name"],
            "--country", source["country"], "--days", str(trip["days"]),
        )
        framing = {key: value for key, value in source.items() if key not in {"itinerary", "places", "module_groups"}}
        write(root / "research/framing.json", framing)
        write(root / "research/itinerary.json", source["itinerary"])
        buckets = {name: [] for name in ("sights", "shops", "souvenirs", "experiences", "restaurants", "support")}
        mapping = {"sight": "sights", "shop": "shops", "souvenir": "souvenirs", "experience": "experiences", "restaurant": "restaurants"}
        for place in source["places"]:
            buckets[mapping.get(place.get("type"), "support")].append(place)
        groups = source["module_groups"]
        write(root / "research/places/core.json", {"sights": buckets["sights"], "support": buckets["support"]})
        write(root / "research/places/shopping.json", {"shops": buckets["shops"], "souvenirs": buckets["souvenirs"]})
        write(root / "research/places/experiences.json", buckets["experiences"])
        write(root / "research/places/restaurants.json", buckets["restaurants"])
        discovery = {"shopping": groups["shopping"], "experiences": groups["experiences"]}
        if trip.get("experience_mode") in {"expanded", "constrained"}:
            discovery["experience_mode"] = trip["experience_mode"]
        write(root / "research/modules/discovery.json", discovery)
        write(root / "research/modules/practical.json", {"food": groups["food"], "preparation": groups["preparation"]})
        write(root / "research/modules/language-notes.json", {"language": groups["language"], "travel_notes": groups["travel_notes"]})
        call(scripts / "research_status.py", str(root))
        call(scripts / "compile_destination_profile.py", str(root))
        compiled = json.loads((root / "destination-profile.json").read_text(encoding="utf-8"))
        # Place order is not semantic: compact packs group support nodes with
        # sights, while imported profiles may put support nodes last.
        compiled["places"] = sorted(compiled["places"], key=lambda p: p["id"])
        source["places"] = sorted(source["places"], key=lambda p: p["id"])
        if compiled != source:
            raise SystemExit("compiled profile differs from source profile")
    print("PASS research queue and compiler round-trip a valid profile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
