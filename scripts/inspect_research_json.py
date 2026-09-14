#!/usr/bin/env python3
"""Validate and summarize saved image candidates with one literal path argument."""
import argparse
import json
from pathlib import Path
import sys

SCHEMA = "travel-image-candidate-summary/v1"


def summarize_candidates(rows, source_file=None, cached=None):
    if not isinstance(rows, list):
        raise ValueError("/: expected an array of place candidate results")
    places = []
    for index, row in enumerate(rows):
        prefix = f"/{index}"
        if not isinstance(row, dict):
            raise ValueError(f"{prefix}: expected a place object")
        identifier = row.get("id") or row.get("query")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"{prefix}: expected a nonempty id or query")
        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"{prefix}/candidates: expected an array")
        compact = []
        for candidate_index, candidate in enumerate(candidates):
            point = f"{prefix}/candidates/{candidate_index}"
            if not isinstance(candidate, dict):
                raise ValueError(f"{point}: expected a candidate object")
            for key in ("image_url", "source_page"):
                if not isinstance(candidate.get(key), str) or not candidate[key].strip():
                    raise ValueError(f"{point}/{key}: expected a nonempty URL string")
            compact.append({key: candidate.get(key) for key in ("source", "source_page", "image_url", "title", "candidate_score", "review_risk", "visual_subject_type", "product_name", "product_identity_evidence")})
        identity = row.get("resolved_identity") or {}
        if not isinstance(identity, dict):
            raise ValueError(f"{prefix}/resolved_identity: expected an object")
        places.append({"id": identifier, "query": row.get("query"), "coordinates": identity.get("coordinates"), "candidates": compact, "errors": row.get("errors", []), "search_stopped": row.get("search_stopped"), "product_media_status": row.get("product_media_status"), "next_action": row.get("next_action"), "brand_fallback_candidates": row.get("brand_fallback_candidates", []), "official_artwork": row.get("official_artwork", [])})
    return {"schema": SCHEMA, "status": "ok", "source_file": str(Path(source_file).resolve()) if source_file else None, "place_count": len(places), "candidate_count": sum(len(row["candidates"]) for row in places), "cached_count": cached, "empty_ids": [row["id"] for row in places if not row["candidates"]], "verification_status": "candidates_only_identity_and_visual_review_required", "places": places}


def inspect_file(path):
    path = Path(path)
    try:
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        return summarize_candidates(rows, source_file=path)
    except FileNotFoundError:
        return {"schema": SCHEMA, "status": "input_missing", "source_file": str(path.resolve()), "error": "Candidate JSON does not exist; use the exact source_file/output path printed by the producer"}
    except (OSError, UnicodeError, ValueError) as error:
        return {"schema": SCHEMA, "status": "input_invalid", "source_file": str(path.resolve()), "error": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Exact candidate JSON path printed by research_image_candidates.py")
    args = parser.parse_args()
    result = inspect_file(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
