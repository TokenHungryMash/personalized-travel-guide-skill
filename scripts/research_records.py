#!/usr/bin/env python3
"""Store one valid place record at a time and assemble canonical packs without hand-written arrays."""
import argparse
import json
from pathlib import Path
import re
import sys
from validate_research_pack import validate, scaffold
from write_research_json import write_json, research_target
from research_checkpoint import update

PACK_FILES = {"places-core": "core.json", "places-shopping": "shopping.json", "places-experiences": "experiences.json", "places-food": "restaurants.json"}
TYPES = {"places-core": {"sight", "airport", "station", "transport", "hotel", "support"}, "places-shopping": {"shop", "souvenir"}, "places-experiences": {"experience"}, "places-food": {"restaurant"}}


def group(pack_id, records):
    if pack_id == "places-core":
        return {"sights": [row for row in records if row["type"] == "sight"], "support": [row for row in records if row["type"] != "sight"]}
    if pack_id == "places-shopping":
        return {"shops": [row for row in records if row["type"] == "shop"], "souvenirs": [row for row in records if row["type"] == "souvenir"]}
    return records


def check_record(pack_id, record):
    if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", record["id"]):
        raise ValueError("record must be one object with a stable ASCII id (letters/digits/_/-)")
    if record.get("type") not in TYPES[pack_id]:
        raise ValueError(f"record type does not belong to {pack_id}")
    errors = validate(pack_id, group(pack_id, [record]))
    # Empty sibling families are expected for a single record. Record-field
    # checks still use the canonical validator; assembly validates the whole pack.
    errors = [error for error in errors if re.match(r"/(?:sights|support|shops|souvenirs)/0(?:/|$)|/0(?:/|$)", error["pointer"])]
    if errors:
        raise ValueError(json.dumps(errors, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("new", "add", "batch", "assemble"))
    parser.add_argument("workbench", type=Path)
    parser.add_argument("pack_id", choices=tuple(PACK_FILES))
    parser.add_argument("--record", type=Path, help="One independently authored JSON object; relative to workbench")
    parser.add_argument("--id", dest="record_id", help="For new: stable place id")
    parser.add_argument("--type", dest="record_type", help="For new: canonical place type")
    parser.add_argument("--finish-unit", action="store_true", help="Close active unit only after this final add/assemble succeeds")
    args = parser.parse_args()
    root = args.workbench.resolve()
    try:
        if args.finish_unit and update(root, "status")["status"] != "active":
            raise ValueError("--finish-unit requires an active timer")
        records_dir = root/"research/records"/args.pack_id
        if args.action == "new":
            if args.finish_unit:
                raise ValueError("a scaffold cannot finish a work unit")
            if not args.record_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.record_id) or args.record_type not in TYPES[args.pack_id]:
                raise ValueError("new requires --id and --type belonging to the pack")
            seed = scaffold(args.pack_id)
            candidates = sum(seed.values(), []) if isinstance(seed, dict) else seed
            record = next((row.copy() for row in candidates if row["type"] == args.record_type), candidates[0].copy())
            record.update(id=args.record_id, type=args.record_type)
            target = root/"research/drafts"/(args.record_id+".next.json")
            if target.exists():
                raise ValueError(f"staging record already exists; edit it in place: {target}")
            write_json(target, record, workbench=root)
            result = {"status": "draft_scaffold", "file": str(target), "next_action": "Fill this single object, then add it; null placeholders are not researched facts"}
        elif args.action in {"add", "batch"}:
            if args.record is None:
                raise ValueError("add requires --record")
            source = args.record if args.record.is_absolute() else root/args.record
            sources = [source] if args.action == "add" else sorted(source.glob("*.json")) if source.is_dir() else []
            if not sources:
                raise ValueError("batch requires a directory containing only the intended independent record JSON files")
            records = []
            for source in sources:
                record = json.loads(source.read_text(encoding="utf-8-sig"))
                check_record(args.pack_id, record)
                records.append(record)
            if len({record["id"] for record in records}) != len(records):
                raise ValueError("duplicate record IDs in batch; nothing was saved")
            # Validate every record before the first write, so malformed batch
            # input cannot partially replace previously accepted source records.
            for record in records:
                target = records_dir/(record["id"]+".json")
                write_json(target, record, workbench=root)
            result = {"status": "record_saved" if args.action == "add" else "record_batch_saved", "ids": [record["id"] for record in records], "record_count": len(records), "directory": str(records_dir), "pack_complete": False}
            if args.action == "add":
                result.update(id=records[0]["id"], file=str(target))
        else:
            records = []
            for path in sorted(records_dir.glob("*.json")):
                research_target(path, root)
                record = json.loads(path.read_text(encoding="utf-8-sig"))
                check_record(args.pack_id, record)
                if path.stem != record["id"]:
                    raise ValueError(f"record filename/id mismatch: {path}")
                records.append(record)
            if not records:
                raise ValueError(f"no saved records: {records_dir}; add records first")
            target = root/"research/places"/PACK_FILES[args.pack_id]
            write_json(target, group(args.pack_id, records), args.pack_id, root)
            result = {"status": "pack_assembled", "file": str(target), "record_count": len(records), "local_contract_valid": True, "next_action": "Run research_status; final compiler checks counts, relationships and provenance"}
        if args.finish_unit:
            result["checkpoint"] = update(root, "finish", note=f"{args.action} saved {target}")
        print(json.dumps(result, ensure_ascii=False))
        return 2 if result.get("checkpoint", {}).get("stop_required") else 0
    except (OSError, ValueError) as error:
        result = {"status": "record_operation_failed", "error": str(error)}
        if args.finish_unit:
            try:
                result["checkpoint"] = update(root, "stop", note=f"{args.action} failed: {str(error)[:500]}")
            except (OSError, ValueError):
                pass
        print(json.dumps(result, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
