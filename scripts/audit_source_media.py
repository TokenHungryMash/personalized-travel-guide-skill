#!/usr/bin/env python3
"""Reject manifest/source drift before rendering; never copy verification flags back to research."""
import json
from pathlib import Path

FIELDS = ("source_page", "download_url", "media_class", "original_media_class")

def audit(profile, manifest):
    declarations = {}
    cover = profile.get("cover", {})
    if cover.get("image"):
        declarations[("__cover__", cover["image"])] = cover
    for place in profile.get("places", []):
        for entry in place.get("images", []):
            if isinstance(entry, dict):
                declarations[(place.get("id"), entry.get("file"))] = entry
    errors = []
    for asset in manifest.get("assets", []):
        key = (asset.get("place_id"), asset.get("file"))
        source = declarations.get(key)
        # Legacy declarations can omit file; match only an unambiguous place.
        if source is None:
            candidates = [v for (pid, _), v in declarations.items() if pid == key[0]]
            source = candidates[0] if len(candidates) == 1 else None
        if source is None:
            errors.append(f"{key[0]}: manifest has no unique source image declaration")
            continue
        if key[0] == "__cover__" and cover.get("derived_from"):
            source = next((v for (_, file), v in declarations.items() if file == cover['derived_from']), source)
        for field in FIELDS:
            # The manifest defaults the optional original class to media_class.
            # Compare the same effective declaration, not absent vs derived.
            source_value = source.get(field)
            if field == "original_media_class" and source_value is None:
                source_value = source.get("media_class")
            if (source_value or "") != (asset.get(field) or ""):
                errors.append(f"{key[0]} {field}: manifest/source differ; repair the owning research pack, then recompile")
    return errors

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workbench", type=Path)
    args = p.parse_args()
    root = args.workbench
    errors = audit(json.loads((root/'destination-profile.json').read_text(encoding='utf-8-sig')),
                   json.loads((root/'asset-manifest.json').read_text(encoding='utf-8-sig')))
    for error in errors[:12]:
        print('FAIL ' + error)
    print(f"SOURCE MEDIA: {len(errors)} conflicts")
    return 2 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
