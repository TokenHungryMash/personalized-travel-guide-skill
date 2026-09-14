#!/usr/bin/env python3
"""Plan the narrowest handbook validation stages from stable section hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def runtime_digest(path: Path) -> str:
    """Generated day data is covered by itinerary hashes, not runtime QA."""
    source = path.read_text(encoding="utf-8")
    if path.name == "trip-mode.js":
        source = re.sub(r"var TRIP_MODE_DATA=.*?;(?=\s*(?:\r?\n|$))", "var TRIP_MODE_DATA=[];", source, count=1)
    elif path.name == "itinerary-customizer.js":
        source = re.sub(r"var titles=\[.*?\];", "var titles=[];", source, count=1)
    return digest(source)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbench", type=Path)
    parser.add_argument("--write", action="store_true", help="save current hashes after printing the plan")
    args = parser.parse_args()
    root = args.workbench.resolve()
    profile_path = root / "destination-profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    places = profile.get("places", []) if isinstance(profile.get("places"), list) else []
    groups = profile.get("module_groups", {}) if isinstance(profile.get("module_groups"), dict) else {}
    sections = {
        "cover": profile.get("cover", {}),
        "stays": {"stays": profile.get("stays", []), "hotels": [p for p in places if isinstance(p, dict) and p.get("type") == "hotel"]},
        "itinerary": profile.get("itinerary", []),
        "sights": [p for p in places if isinstance(p, dict) and p.get("type") == "sight"],
        "shopping": {"places": [p for p in places if isinstance(p, dict) and p.get("type") in {"shop", "souvenir"}], "groups": groups.get("shopping")},
        "experiences": {"places": [p for p in places if isinstance(p, dict) and p.get("type") == "experience"], "groups": groups.get("experiences")},
        "food": {"places": [p for p in places if isinstance(p, dict) and p.get("type") == "restaurant"], "groups": groups.get("food")},
        "preparation": groups.get("preparation"),
        "language": groups.get("language"),
        "notes": groups.get("travel_notes"),
        "manifest": file_digest(root / "asset-manifest.json"),
        "media": {"cover": {k: profile.get("cover", {}).get(k) for k in ("image", "source_page", "download_url", "derived_from")},
                  "places": [{"id": p.get("id"), "images": p.get("images", [])} for p in places if p.get("images")]},
        # Generated HTML changes on every copy edit; it is not runtime source.
        "runtime": {str(path.relative_to(root)): runtime_digest(path) for path in sorted(root.iterdir())
                    if path.suffix in {".js", ".css"}},
    }
    current = {name: digest(value) for name, value in sections.items()}
    cache_path = root / ".validation-cache.json"
    previous = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
    old = previous.get("section_sha256", {}) if isinstance(previous, dict) else {}
    changed = [name for name, value in current.items() if old.get(name) != value]
    if not old:
        stages = ["data", "media", "render", "strict-audit", "forward-test", "representative-browser-qa"]
    elif "runtime" in changed:
        stages = ["data", "media", "render", "strict-audit", "forward-test", "publication-depth-browser-qa"]
    else:
        stages = []
        if changed:
            stages.extend(["data"])
        if any(name in changed for name in ("media", "manifest")):
            stages.append("media")
        if changed:
            stages.extend(["render", "strict-audit", "forward-test", "representative-browser-qa"])
    print(json.dumps({"changed_sections": changed, "required_stages": list(dict.fromkeys(stages)), "unchanged_sections": [name for name in current if name not in changed]}, ensure_ascii=False, indent=2))
    if args.write:
        cache_path.write_text(json.dumps({"schema_version": 1, "section_sha256": current}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS wrote incremental validation cache: {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
