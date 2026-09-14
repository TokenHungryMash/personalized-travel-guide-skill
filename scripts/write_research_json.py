#!/usr/bin/env python3
"""Validate JSON before an atomic replacement; preserve the previous valid bytes."""
import argparse
import json
import os
from pathlib import Path
import tempfile


def research_target(target, workbench):
    root = Path(workbench).resolve()
    allowed = (root / "research").resolve()
    target = Path(target).resolve()
    if not allowed.is_relative_to(root) or not target.is_relative_to(allowed) or target == allowed:
        raise ValueError(f"target must stay inside workbench/research: {target}")
    if target.suffix.lower() != ".json":
        raise ValueError("research target must be a .json file")
    backup = target.with_suffix(target.suffix + ".bak").resolve()
    if not backup.is_relative_to(allowed):
        raise ValueError("backup path escapes workbench/research")
    return target


def write_json(target, value, pack_id=None, workbench=None):
    target = research_target(target, workbench) if workbench is not None else Path(target)
    if not isinstance(value, (dict, list)):
        raise ValueError("research JSON must be a non-null object or array")
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    json.loads(encoded)
    if pack_id:
        from validate_research_pack import validate
        errors = validate(pack_id, value)
        if errors:
            raise ValueError(json.dumps(errors, ensure_ascii=False))
    if not target.parent.is_dir():
        if workbench is None:
            raise ValueError("missing target directory; supply workbench to create a research directory safely")
        target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if target.exists():
            old = target.read_bytes()
            # Preserve only parseable JSON; never replace the last valid backup
            # with an already damaged target.
            try:
                previous = json.loads(old.decode("utf-8-sig"))
                valid = isinstance(previous, (dict, list))
            except (UnicodeError, ValueError):
                valid = False
            if valid:
                target.with_suffix(target.suffix + ".bak").write_bytes(old)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--from-file", required=True, type=Path)
    parser.add_argument("--workbench", type=Path, help="Restrict target/automatic parent creation to this workbench's research directory")
    parser.add_argument("--pack-id", help="Validate a complete pack; omit for explicitly partial drafts/checkpoints")
    parser.add_argument("--finish-unit", action="store_true", help="Final write of a work unit: finish its active timer on success; stop on failure")
    args = parser.parse_args()
    root = args.workbench
    try:
        if root is None:
            root = next((parent for parent in args.target.resolve().parents if (parent / "research-plan.json").is_file()), None)
        if root is None:
            raise ValueError("supply --workbench, or initialize research-plan.json before writing research data")
        if args.finish_unit:
            from research_checkpoint import update
            checkpoint = update(root, "status")
            if checkpoint["status"] != "active":
                raise ValueError("--finish-unit requires an active work unit; start it before authoring")
        research_target(args.target, root)
        if not args.from_file.is_file():
            raise ValueError(f"staging JSON missing: {args.from_file}; save it first in research/drafts or its initialized canonical directory")
        value = json.loads(args.from_file.read_text(encoding="utf-8-sig"))
        write_json(args.target, value, args.pack_id, workbench=root)
    except (OSError, ValueError) as error:
        if args.finish_unit and root is not None:
            from research_checkpoint import update
            try:
                result = update(root, "stop", note=f"JSON write failed: {str(error)[:500]}")
                print("CHECKPOINT " + json.dumps(result, ensure_ascii=False))
            except (OSError, ValueError):
                pass
        parser.exit(2, f"JSON WRITE FAILED: {error}\n")
    print(f"JSON SAVED: {args.target}")
    if args.finish_unit:
        from research_checkpoint import update
        result = update(root, "finish", note=f"Saved {args.target}" + (f"; validated {args.pack_id}" if args.pack_id else "; partial draft JSON only"))
        print("CHECKPOINT " + json.dumps(result, ensure_ascii=False))
        return 2 if result["stop_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
