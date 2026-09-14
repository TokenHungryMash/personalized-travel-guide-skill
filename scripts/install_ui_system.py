#!/usr/bin/env python3
"""Install the travel-handbook product as an adaptation workbench."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export", type=Path)
    parser.add_argument("--system", choices=("current-system", "canonical"), default="current-system")
    parser.add_argument(
        "--force-template",
        action="store_true",
        help="replace an existing index.html with the canonical product template",
    )
    parser.add_argument(
        "--include-reference-media",
        action="store_true",
        help="copy Bali reference raster media (inspection/Bali maintenance only)",
    )
    args = parser.parse_args()
    export = args.export.resolve()
    skill_assets = Path(__file__).resolve().parent.parent / "assets"
    product = skill_assets / args.system / "product"
    if not product.exists():
        raise SystemExit(f"missing canonical product bundle: {product}")
    canonical_index_hash = hashlib.sha256((product / "index.html").read_bytes()).hexdigest()
    raster_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
    copied = 0
    skipped_reference_media = 0
    for source in product.rglob("*"):
        if not source.is_file():
            continue
        if source.suffix.lower() in raster_suffixes and not args.include_reference_media:
            skipped_reference_media += 1
            continue
        relative = source.relative_to(product)
        if not args.include_reference_media and relative.parts[0] in {"media", "audit-routes"}:
            continue
        target = export / (".index.template.html" if relative.as_posix() == "index.html" and not args.include_reference_media else relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative.as_posix() == "index.html" and target.exists() and not args.force_template:
            continue
        shutil.copy2(source, target)
        copied += 1
    # A media-free copy is intentionally an unfinished component workbench,
    # never a destination draft. The destination dataset must already have
    # passed validate_destination_data.py before any reference records are
    # replaced. The release audit refuses this workbench until the complete
    # dataset has been rendered and final QA passes.
    if not args.include_reference_media:
        marker = {
            "state": "adaptation-required",
            "agent_action": "continue-working",
            "not_a_blocker": True,
            "reason": "Canonical markup is component scaffolding only; render a prevalidated destination dataset before release.",
            "required_next": [
                "complete destination-profile.json before adapting HTML",
                "run validate_destination_data.py destination-profile.json",
                "create asset-manifest.json",
                "render every record family from destination-profile.json without string replacement",
                "run audit_product.py --strict and browser QA",
                "remove this marker only after every gate passes",
            ],
        }
        (export / "ADAPTATION_REQUIRED.json").write_text(
            json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    installed_index = export / ("index.html" if args.include_reference_media else ".index.template.html")
    install_report = {
        "install_method": "official_installer",
        "ui_system": args.system,
        "canonical_index_sha256": canonical_index_hash,
        "installed_index_sha256": hashlib.sha256(installed_index.read_bytes()).hexdigest() if installed_index.exists() else "",
        "canonical_template_installed": installed_index.exists() and hashlib.sha256(installed_index.read_bytes()).hexdigest() == canonical_index_hash,
        "custom_page_builder_detected": False,
    }
    (export / "INSTALL_REPORT.json").write_text(json.dumps(install_report, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(skill_assets / "asset-manifest.template.json", export / "asset-manifest.template.json")
    shutil.copy2(skill_assets / "destination-profile.template.json", export / "destination-profile.template.json")
    shutil.copy2(skill_assets / "render-bindings.template.json", export / "render-bindings.template.json")
    shutil.copy2(skill_assets / "destination-profile.schema.json", export / "destination-profile.schema.json")
    print(f"installed canonical adaptation workbench ({copied} files)")
    if skipped_reference_media:
        print(f"skipped {skipped_reference_media} Bali reference raster assets; continue working automatically until every destination-bearing field and image is replaced")
    print("CONTINUE: installer success is an intermediate milestone; render content, acquire images, audit and perform browser QA")
    print(f"template {installed_index}")
    print(f"installed {export / 'asset-manifest.template.json'}")
    print(f"installed {export / 'destination-profile.template.json'}")
    print(f"installed {export / 'render-bindings.template.json'}")
    print(f"installed {export / 'destination-profile.schema.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
