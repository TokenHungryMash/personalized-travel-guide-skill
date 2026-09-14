#!/usr/bin/env python3
"""Catch known cross-file contract contradictions before handbook handoff."""
from __future__ import annotations

import json
import re
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    google_lookup = (root / "references/google-place-lookup.md").read_text(encoding="utf-8")
    release = (root / "references/release-validation.md").read_text(encoding="utf-8")
    content = (root / "references/content-model.md").read_text(encoding="utf-8")
    init = (root / "scripts/init_research_workspace.py").read_text(encoding="utf-8")
    handoff = (root / "scripts/check_handoff.py").read_text(encoding="utf-8")
    schema = json.loads((root / "assets/destination-profile.schema.json").read_text(encoding="utf-8"))
    contract = json.loads((root / "assets/research-pack-contract.json").read_text(encoding="utf-8"))
    validator = (root / "scripts/validate_research_pack.py").read_text(encoding="utf-8")
    profile_validator = (root / "scripts/validate_destination_data.py").read_text(encoding="utf-8")
    compiler = (root / "scripts/compile_destination_profile.py").read_text(encoding="utf-8")
    cloud_prepare = (root / "scripts/prepare_shared_cloud.py").read_text(encoding="utf-8")
    cloud_worker = (root / "assets/current-system/cloudflare/worker.js").read_text(encoding="utf-8")
    cloud_client = (root / "assets/current-system/cloudflare/cloud-shared.js").read_text(encoding="utf-8")
    cloud_schema = (root / "assets/current-system/cloudflare/schema.sql").read_text(encoding="utf-8")
    failures: list[str] = []
    bundle = root / 'assets/current-system'
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        path = bundle / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            failures.append('bundle checksum mismatch: ' + name)
    for field in ('time_anchors', 'dining_plan'):
        if field not in init or field not in contract['packs']['framing']['example']:
            failures.append('cold-start overview instructions missing: ' + field)
    if 'expanded by default and collapsible' in skill or 'runtime performs no network map rendering' in skill:
        failures.append('obsolete Trip Mode contract remains')

    checks = {
        "SKILL start_build command uses unsupported --end-date": "--end-date" in skill,
        "handbook handoff still prints a commercial audit dimension": '"commercial"' in handoff,
        "release QA permits text-only restaurants": "restaurant cards may remain text-led" in release,
        "image range conflicts with populated inventory": "26–30 useful images" in skill or "18–22" in skill,
        "research seed restores hotel-proximity restaurants": "restaurants near selected stay area" in init,
        "pending transport copy blocks editorial generation": "ask the user for the missing booked information" in content,
        "Google protocol is not routed from the Skill": "references/google-place-lookup.md" not in skill,
        "super edition lacks gateway failure recovery routing": "gateway-failure-recovery.md" not in skill,
        "generated food task still requires score and review count together": "only when the score and review count appear" in init,
        "generated tasks do not require full accessible Google coverage": "attempt every selected sight" not in init or "resolve every selected restaurant" not in init,
        "super edition still requires an all-rated restaurant batch": "an all-unavailable restaurant batch is incomplete" in init or "all restaurant" in init,
        "trip-decision importer is not wired before profile signing": "apply_trip_decisions" not in compiler,
        "quality modes are not routed from the Skill": "references/production-standard.md" not in skill,
        "cloud preparation does not require an upload namespace": "--uploads-kv-id" not in cloud_prepare or "kv_namespaces" not in cloud_prepare,
        "cloud attachment metadata schema is missing": "CREATE TABLE IF NOT EXISTS tickets" not in cloud_schema,
        "cloud attachment API is missing": "/api/tickets/file" not in cloud_worker or "/api/tickets/" not in cloud_worker,
        "cloud attachment client adapter is missing": "window.CloudTicketVault" not in cloud_client,
        "cloud PDF preview is blocked from same-origin framing": "SAMEORIGIN" not in cloud_worker,
        "cloud preparation does not require an explicit access choice": "--access-mode" not in cloud_prepare or "ACCESS_MODE" not in cloud_prepare,
        "code access is not a responsive form-backed secure session": any(token not in cloud_worker for token in ("ACCESS_CODE", "guide_access", "HttpOnly", "Secure", "SameSite=Lax", "<form")),
        "cloud template still uses browser-native HTTP Basic auth": "WWW-Authenticate" in cloud_worker or "Basic realm=" in cloud_worker,
    }
    failures.extend(label for label, failed in checks.items() if failed)

    # Validate navigable local references without requiring exact sentences.
    for document in [root / "SKILL.md", *sorted((root / "references").glob("*.md"))]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if target and not (document.parent / target).is_file():
                failures.append(f"broken reference in {document.relative_to(root)}: {target}")


    framing_paths = set(contract["packs"]["framing"]["required_paths"])
    profile_required = set(schema.get("required", []))
    for field in ("destination", "display_name", "country", "year", "trip", "cover", "transport", "stays", "render_bindings_file"):
        if field not in profile_required:
            failures.append(f"destination schema does not require framing root: {field}")
    for field in ("destination", "display_name", "country", "year", "stays", "render_bindings_file"):
        if field not in framing_paths:
            failures.append(f"research contract does not require framing root: {field}")
    itinerary_paths = set(contract["packs"]["itinerary"]["item_required_paths"])
    schema_day_required = set(schema["$defs"]["day"].get("required", []))
    schema_period_required = set(schema["$defs"]["day"]["properties"]["periods"].get("required", []))
    if not {"date", "theme", "summary", "periods", "stops"}.issubset(schema_day_required):
        failures.append("destination schema day roots disagree with research contract")
    if not {"periods.morning", "periods.afternoon", "periods.evening"}.issubset(itinerary_paths):
        failures.append("research contract must nest morning/afternoon/evening under periods")
    if schema_period_required != {"morning", "afternoon", "evening"}:
        failures.append("destination schema periods disagree with research contract")
    if "research-pack-contract.json" not in init or "CONTRACT" not in validator:
        failures.append("task generator or pack validator is not contract-derived")
    if "validate_research_pack.py" not in compiler:
        failures.append("compiler does not run the shared research-pack validator")

    with tempfile.TemporaryDirectory(prefix="travel-contract-audit-") as raw:
        workbench = Path(raw) / "cold-start"
        start = root / "scripts/start_build.py"
        init_script = root / "scripts/init_research_workspace.py"
        start_result = subprocess.run([sys.executable, str(start), str(workbench), "--destination", "Contract City", "--country", "Contract Country", "--start-date", "2026-11-10", "--days", "5", "--discussion-waived", "--user-statement", "fixture waiver"], capture_output=True)
        init_result = subprocess.run([sys.executable, str(init_script), str(workbench)], capture_output=True) if start_result.returncode == 0 else start_result
        if start_result.returncode or init_result.returncode:
            failures.append("dynamic cold-start task generation failed")
        else:
            brief = json.loads((workbench / "travel-brief.json").read_text(encoding="utf-8"))
            if brief.get("start_date") != "2026-11-10" or brief.get("end_date") != "2026-11-14":
                failures.append("cold-start brief does not inherit and derive trip dates")
            framing_task = json.loads((workbench / "research/tasks/framing.json").read_text(encoding="utf-8"))
            itinerary_task = json.loads((workbench / "research/tasks/itinerary.json").read_text(encoding="utf-8"))
            if framing_task.get("required_fields") != contract["packs"]["framing"]["required_paths"]:
                failures.append("generated framing task required_fields drifted from research contract")
            expected_itinerary = ["JSON array with exactly 5 day objects", *contract["packs"]["itinerary"]["item_required_paths"], "2+ stops (3+ on non-arrival/departure days)", "each stop has place_id/arrival_time/dwell_minutes/transport_mode/transfer_minutes/distance_km/estimated_cost"]
            if itinerary_task.get("required_fields") != expected_itinerary:
                failures.append("generated itinerary task required_fields drifted from research contract")

    food = schema["$defs"]["food"]["properties"]
    expected = {"local_snacks": (4, 4), "dedicated_trip": (6, None), "reliable_chains": (2, 4)}
    for key, (minimum, maximum) in expected.items():
        spec = food.get(key, {})
        if spec.get("minItems") != minimum or (maximum is not None and spec.get("maxItems") != maximum):
            failures.append(f"schema food.{key} count disagrees with the handbook contract")
    notes = schema["properties"]["module_groups"]["properties"]["travel_notes"]
    if notes.get("minItems") != 5 or notes.get("maxItems") != 5:
        failures.append("schema travel_notes must require exactly five folds")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("PASS Skill instructions, research seed, schema and handoff gate are internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
