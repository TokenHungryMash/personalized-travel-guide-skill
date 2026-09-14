#!/usr/bin/env python3
"""Read-only product/runtime checks, with explicit Skill release regressions."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


def check_skill_regression() -> int:
    """Test neutral installation and dirty-template rejection in isolated fixtures."""
    with tempfile.TemporaryDirectory(prefix="travel-handbook-release-") as tmp:
        install_target = Path(tmp) / "fresh-destination"
        installer = Path(__file__).resolve().parent / "install_ui_system.py"
        installed = subprocess.run(
            [sys.executable, str(installer), str(install_target), "--force-template"],
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if installed.returncode:
            print("FAIL destination-neutral installer failed")
            print((installed.stdout + installed.stderr).strip())
            return 2
        raster_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
        copied_rasters = [path for path in install_target.rglob("*") if path.is_file() and path.suffix.lower() in raster_suffixes]
        if copied_rasters:
            print("FAIL destination-neutral installer copied Bali raster media")
            return 2
        if not (install_target / "ADAPTATION_REQUIRED.json").exists():
            print("FAIL installer did not mark the raw canonical copy as unfinished")
            return 2

        # Regression fixture: imitate the exact failure this Skill used to let
        # through—rename only the first cover label while leaving Bali content,
        # routes and broken image references behind. The strict audit must reject it.
        dirty = Path(tmp) / "dirty-example-city"
        shutil.copytree(install_target, dirty)
        dirty_template = dirty / "index.html"
        if not dirty_template.exists():
            dirty_template = dirty / ".index.template.html"
        html = dirty_template.read_text(encoding="utf-8")
        adapted = html.replace("BALI", "EXAMPLE CITY", 1).replace("巴厘岛旅行手册", "示例城旅行手册", 1)
        (dirty / "index.html").write_text(adapted, encoding="utf-8")
        profile = {
            "destination": "Example City, Testland",
            "display_name": "示例城",
            "navigation_brand": "EXAMPLE CITY · 2026",
            "year": "2026",
            "aliases": ["Example City", "示例城"],
            "country": "Japan",
            "forbidden_reference_terms": ["Ubud", "Seminyak", "Bali"],
            "places": [{
                "id": "example-central-station",
                "type": "sight",
                "display_name": "示例中央车站",
                "map_query": "Example Central Station",
                "source_url": "https://example.org/station",
            }],
        }
        (dirty / "destination-profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        audit = Path(__file__).resolve().parent / "audit_product.py"
        rejected = subprocess.run(
            [sys.executable, str(audit), str(dirty), "--strict"],
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if rejected.returncode != 2 or "FAIL" not in rejected.stdout:
            print("FAIL strict audit did not report the unfinished fixture as rejected")
            print((rejected.stdout + rejected.stderr).strip())
            return 2

    print("PASS Skill neutral installation and dirty-workbench rejection regression")
    return 0


def loaded_assets(source_text: str, tag: str, attribute: str) -> list[str]:
    pattern = rf'<{tag}\b[^>]*\b{attribute}=["\']([^"\']+)["\']'
    return re.findall(pattern, source_text, re.I)


def resolve_node(explicit: str | None = None) -> str:
    requested = explicit or os.environ.get("TRAVEL_GUIDE_NODE")
    if requested:
        executable = shutil.which(requested)
        if executable:
            return executable
        path = Path(requested).expanduser()
        if path.is_file():
            return str(path.resolve())
        raise ValueError("Node executable not found: " + requested)
    executable = shutil.which("node")
    if not executable:
        raise ValueError("JavaScript syntax not verified: use --node <existing-node-executable> or TRAVEL_GUIDE_NODE when Node is outside PATH")
    return executable


def _check_product(source: Path, node: str | None = None) -> int:
    adapted = (source / "index.html").read_text(encoding="utf-8")
    invariants = (
        'id="contents"', 'id="route"', 'id="sights"', 'id="shops"',
        'id="move"', 'id="food"', 'id="booking"', 'id="words"', 'id="tips"',
        "trip-mode.js", "itinerary-customizer.js", "theme-switcher.js",
        "checklist-memory.js", "movement-section",
        "hotel-chapter-fold",
    )
    profile_file = source / 'destination-profile.json'
    profile_data = json.loads(profile_file.read_text(encoding='utf-8')) if profile_file.exists() else {}
    if profile_data.get('ui_system', 'current-system') == 'current-system':
        invariants = tuple(x for x in invariants if x != 'theme-switcher.js') + (
            'tokens.css', 'trip-route-maps.js', 'travel-utilities.js', 'shared-ledger.js',
            'local-ledger.js', 'reservation-check', 'trip-page-expense', 'speechSynthesis',
        )
    product_source = adapted + "\n" + "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in source.glob("*.js")
    )
    missing = [token for token in invariants if token not in product_source]
    if missing:
        print("FAIL product invariants lost: " + ", ".join(missing))
        return 2
    node_executable = resolve_node(node)
    for reference in dict.fromkeys(loaded_assets(adapted, "script", "src")):
        url = urlsplit(reference)
        if url.scheme or url.netloc:
            raise ValueError("Cannot verify external runtime script: " + reference)
        script = (source / unquote(url.path)).resolve()
        if not script.is_relative_to(source) or not script.is_file():
            raise ValueError("Missing or unsafe runtime script: " + reference)
        result = subprocess.run([node_executable, "--check", str(script)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            print(f"FAIL JavaScript syntax {reference}: {result.stderr.strip()}")
            return 2
    if profile_data.get('ui_system', 'current-system') == 'current-system':
        from _current_system_adapter import runtime_bindings
        for binding in runtime_bindings(profile_data):
            actual = (source / binding['path']).read_text(encoding='utf-8')
            if actual != binding['content']:
                print('FAIL current runtime differs from profile adapter: ' + binding['path'])
                return 2
        print('PASS current-system assets, script syntax and profile-derived runtimes')
        return 0
    rail = (source / "desktop-rail.js").read_text(encoding="utf-8", errors="ignore")
    order = "['route','行程'],['sights','景点指南'],['shops','购物'],['move','当地特色体验'],['food','餐饮指南'],['booking','出发前准备'],['words','语言随行锦囊'],['tips','旅游贴士']"
    if order not in rail:
        print("FAIL canonical chapter order was not retained")
        return 2
    if any(token in rail for token in ("panel.innerHTML", "BALI SOUVENIRS", "Threads of Life", "Bali Pulina")):
        print("FAIL shared navigation runtime still injects destination-specific content")
        return 2
    if "handbookDestination" not in rail:
        print("FAIL desktop navigation brand is not destination-driven")
        return 2
    trip_runtime = (source / "trip-mode.js").read_text(encoding="utf-8", errors="ignore")
    if "isHotel(" not in trip_runtime:
        print("FAIL Trip Mode does not suppress lodging-only Xiaohongshu actions")
        return 2
    if "name+' 出片'" in trip_runtime or 'name+" 出片"' in trip_runtime:
        print("FAIL place-card Xiaohongshu queries still append 出片 instead of using the exact place name")
        return 2
    css_source = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in source.glob("*.css")
    )
    compact_css = "".join(css_source.split())
    rail_invariants = (
        "--desktop-rail-width:188px",
        "grid-template-columns:30pxminmax(0,1fr)!important",
        "min-height:55px!important",
        "font-size:13px!important",
    )
    missing_rail = [token for token in rail_invariants if token not in compact_css]
    if missing_rail:
        print("FAIL canonical readable desktop-rail geometry was not retained: " + ", ".join(missing_rail))
        return 2
    cover_invariants = (
        "jungle-cover-image", "jungle-cover-shade", "jungle-cover-copy",
        "jungle-cover-kicker", 'class="lede"', "jungle-cover-bottom",
    )
    cover_start = adapted.find('class="hero jungle-cover')
    cover_end = adapted.find("</header>", cover_start) if cover_start >= 0 else -1
    cover_source = adapted[cover_start:cover_end] if cover_end > cover_start >= 0 else ""
    missing_cover = [token for token in cover_invariants if token not in cover_source]
    if missing_cover:
        print("FAIL cover copy and media are not one canonical full-viewport composition: " + ", ".join(missing_cover))
        return 2
    if "adventure-card" in adapted + css_source and "adventure-grid{grid-template-columns:repeat(3" in css_source.replace(" ", ""):
        print("FAIL adventure cards use a three-column parent grid that can collapse copy into vertical text")
        return 2
    print("PASS canonical product invariants and script syntax retained")
    return 0


def check_product(source: Path, node: str | None = None) -> int:
    """Inspect actual product files without copying or modifying the workbench."""
    try:
        return _check_product(Path(source).resolve(), node)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("FAIL product smoke check: " + str(exc))
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?")
    parser.add_argument("--node", help="existing Node executable; otherwise TRAVEL_GUIDE_NODE or PATH")
    parser.add_argument("--skill-self-test", action="store_true", help="explicitly run installation and dirty-template release regressions")
    args = parser.parse_args()
    if args.root is None and not args.skill_self_test:
        parser.error("root is required unless --skill-self-test is requested")
    if args.skill_self_test:
        result = check_skill_regression()
        if result:
            return result
    return check_product(args.root, args.node) if args.root is not None else 0


if __name__ == "__main__":
    sys.exit(main())
