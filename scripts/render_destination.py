#!/usr/bin/env python3
"""Byte-safe destination renderer for the canonical travel-handbook product.

The renderer replaces only registered destination-bearing element interiors and
destination runtime files. It does not parse/reserialize the whole document.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


ALLOWED_SELECTORS = {
    ".hero", ".trip-pulse", "#contents", ".flight-band", "#stay", "#route", "#sights", "#shops",
    "#move", "#food", "#booking", "#words", "#tips", ".mobile-menu-panel", "body > footer",
}
DESTINATION_RUNTIME_FILES = {
    "trip-mode.js", "itinerary-customizer.js",
    "checklist-memory.js", "better-interface.css",
}
LOCKED_FILES = {
    "design-fix.css", "desktop-rail.css", "desktop-rail.js", "guide-motion.js", "handbook-enhancements.js",
    "vocab-fix.css", "trip-mode.css", "itinerary-customizer.css",
    "theme-switcher.css", "theme-switcher.js", "gsap.min.js",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inline_styles(source: str) -> list[str]:
    return re.findall(r'<style\b[^>]*>.*?</style>', source, re.I | re.S)


def selector_pattern(selector: str) -> re.Pattern[str]:
    if selector.startswith("#"):
        value = re.escape(selector[1:])
        return re.compile(rf'<([a-zA-Z][\w:-]*)\b(?=[^>]*\bid=["\']{value}["\'])[^>]*>', re.I | re.S)
    if selector.startswith("."):
        value = re.escape(selector[1:])
        return re.compile(rf'<([a-zA-Z][\w:-]*)\b(?=[^>]*\bclass=["\'][^"\']*(?<![\w-]){value}(?![\w-])[^"\']*["\'])[^>]*>', re.I | re.S)
    value = re.escape(selector)
    return re.compile(rf'<({value})\b[^>]*>', re.I | re.S)


def element_inner_range(source: str, selector: str) -> tuple[int, int]:
    pattern_selector = "footer" if selector == "body > footer" else selector
    matches = list(selector_pattern(pattern_selector).finditer(source))
    if selector == "body > footer" and matches:
        matches = [matches[-1]]
    if len(matches) != 1:
        raise ValueError(f"selector must match exactly once: {selector} ({len(matches)})")
    opening = matches[0]
    tag = opening.group(1)
    token = re.compile(rf'</?{re.escape(tag)}\b[^>]*>', re.I | re.S)
    depth = 1
    for match in token.finditer(source, opening.end()):
        text = match.group(0)
        if text.startswith("</"):
            depth -= 1
            if depth == 0:
                return opening.end(), match.start()
        elif not text.rstrip().endswith("/>"):
            depth += 1
    raise ValueError(f"unclosed element for selector: {selector}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("workbench", type=Path)
    args = parser.parse_args()
    profile_path = args.profile.resolve()
    workbench = args.workbench.resolve()
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    manifest_path = workbench / "asset-manifest.json"
    if manifest_path.is_file():
        from audit_source_media import audit
        conflicts = audit(data, json.loads(manifest_path.read_text(encoding="utf-8-sig")))
        if conflicts:
            raise SystemExit("Source media conflicts before render:\n" + "\n".join(conflicts[:12]))
    bindings_name = str(data.get("render_bindings_file", "render-bindings.json"))
    bindings_path = (profile_path.parent / bindings_name).resolve()
    if not bindings_path.exists():
        raise SystemExit(f"missing render bindings: {bindings_path}")
    bindings = json.loads(bindings_path.read_text(encoding="utf-8"))
    index = workbench / "index.html"
    template_index = workbench / ".index.template.html"
    if not template_index.exists():
        template_index = index
    if not template_index.exists():
        raise SystemExit(f"missing canonical workbench template: {template_index}")

    system = bindings.get("ui_system", data.get("ui_system", "current-system"))
    if system not in {"canonical", "current-system"}:
        raise SystemExit("unknown UI system")
    if system != data.get("ui_system", "current-system"):
        raise SystemExit("profile and render bindings select different UI systems; regenerate bindings")
    canonical = Path(__file__).resolve().parent.parent / "assets" / system / "product"
    runtime_names = set(DESTINATION_RUNTIME_FILES)
    locked_files = set(LOCKED_FILES)
    if system == "current-system":
        from _current_system_adapter import runtime_bindings
        expected_runtime = runtime_bindings(data)
        if bindings.get("runtime_files") != expected_runtime:
            raise SystemExit("current-system runtime bindings do not match the source profile and approved adapter")
        runtime_names = {r["path"] for r in expected_runtime}
        locked_files = {p.name for p in canonical.iterdir() if p.suffix in {".css", ".js"}} - runtime_names
    install_report_path = workbench / "INSTALL_REPORT.json"
    if not install_report_path.exists():
        raise SystemExit("missing INSTALL_REPORT.json; install the workbench with install_ui_system.py")
    install_report = json.loads(install_report_path.read_text(encoding="utf-8"))
    canonical_index_hash = digest(canonical / "index.html")
    if install_report.get("install_method") != "official_installer":
        raise SystemExit("workbench was not created by the official installer")
    if install_report.get("canonical_index_sha256") != canonical_index_hash:
        raise SystemExit("installer report does not match the current canonical template")
    if not install_report.get("canonical_template_installed") or digest(template_index) != canonical_index_hash:
        raise SystemExit("canonical template changed before official render; reinstall a fresh canonical workbench")
    locked_before: dict[str, str] = {}
    for name in locked_files:
        candidate = workbench / name
        reference = canonical / name
        if not candidate.exists() or not reference.exists() or digest(candidate) != digest(reference):
            raise SystemExit(f"locked file differs before render: {name}")
        locked_before[name] = digest(candidate)

    source = template_index.read_text(encoding="utf-8")
    styles_before = inline_styles(source)
    html_bindings = bindings.get("html", [])
    seen: set[str] = set()
    replacements: list[tuple[int, int, str, str]] = []
    for record in html_bindings:
        selector = str(record.get("selector", ""))
        if selector not in ALLOWED_SELECTORS:
            raise SystemExit(f"unregistered destination selector: {selector}")
        if selector in seen:
            raise SystemExit(f"duplicate destination selector: {selector}")
        seen.add(selector)
        inner = record.get("inner_html")
        if not isinstance(inner, str) or not inner.strip():
            raise SystemExit(f"empty rendered fragment: {selector}")
        start, end = element_inner_range(source, selector)
        replacements.append((start, end, inner, selector))
    if not replacements:
        raise SystemExit("render bindings contain no HTML component families")
    missing_selectors = ALLOWED_SELECTORS - seen
    if missing_selectors:
        raise SystemExit("render bindings missing component families: " + ", ".join(sorted(missing_selectors)))
    for start, end, inner, _selector in sorted(replacements, reverse=True):
        source = source[:start] + inner + source[end:]

    title = f'{data.get("display_name", data.get("destination", ""))}旅行手册 · {data.get("year", "")}'
    source, title_count = re.subn(r'(?<=<title>).*?(?=</title>)', title, source, count=1, flags=re.I | re.S)
    if title_count != 1:
        raise SystemExit("canonical document title could not be updated safely")
    description = str(data.get("meta_description") or data.get("cover", {}).get("summary") or f'{data.get("display_name", "")}旅行手册')
    escaped_description = description.replace("&", "&amp;").replace('"', "&quot;")
    source, description_count = re.subn(
        r'(<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*\bcontent=["\'])[^"\']*(["\'][^>]*>)',
        lambda match: match.group(1) + escaped_description + match.group(2),
        source,
        count=1,
        flags=re.I | re.S,
    )
    if description_count != 1:
        raise SystemExit("canonical meta description could not be updated safely")
    body_match = re.search(r'<body\b[^>]*>', source, re.I | re.S)
    if not body_match:
        raise SystemExit("missing canonical body tag")
    body_tag = body_match.group(0)
    metadata = {
        "data-handbook-destination": data.get("destination", ""),
        "data-handbook-destination-short": data.get("display_name", ""),
        "data-handbook-year": data.get("year", ""),
        "data-handbook-default-theme": data.get("default_theme", "rainforest"),
        "data-handbook-id": data.get("handbook_id", data.get("destination", "")),
    }
    for attribute, value in metadata.items():
        escaped = str(value).replace("&", "&amp;").replace('"', "&quot;")
        if re.search(rf'\b{re.escape(attribute)}=["\'][^"\']*["\']', body_tag, re.I):
            body_tag = re.sub(rf'\b{re.escape(attribute)}=["\'][^"\']*["\']', f'{attribute}="{escaped}"', body_tag, count=1, flags=re.I)
        else:
            body_tag = body_tag[:-1] + f' {attribute}="{escaped}">'
    source = source[:body_match.start()] + body_tag + source[body_match.end():]
    # Remove legacy reference-destination storage namespaces from the exported page.
    # The destination-aware checklist runtime remains authoritative.
    source = source.replace("bali-packing-2026", "travel-handbook-packing-legacy")
    source = source.replace("bali-booking-2026", "travel-handbook-booking-legacy")
    if inline_styles(source) != styles_before:
        raise SystemExit("render attempted to modify canonical inline <style> bytes")
    pending_index = workbench / ".index.rendering.html"
    pending_index.write_text(source, encoding="utf-8")
    pending_index.replace(index)
    if template_index.name == ".index.template.html":
        template_index.unlink(missing_ok=True)
    installed_profile = (workbench / "destination-profile.json").resolve()
    if profile_path != installed_profile:
        shutil.copy2(profile_path, installed_profile)

    for record in bindings.get("runtime_files", []):
        name = str(record.get("path", ""))
        content = record.get("content")
        if name not in runtime_names:
            raise SystemExit(f"unregistered destination runtime: {name}")
        if not isinstance(content, str) or not content.strip():
            raise SystemExit(f"empty destination runtime content: {name}")
        (workbench / name).write_text(content, encoding="utf-8")

    for name, before in locked_before.items():
        if digest(workbench / name) != before:
            raise SystemExit(f"locked file changed during render: {name}")

    report = {
        "destination": data.get("destination"),
        "ui_system": system,
        "profile": str(profile_path),
        "bindings": str(bindings_path),
        "rendered_selectors": sorted(seen),
        "runtime_files": [record.get("path") for record in bindings.get("runtime_files", [])],
        "render_method": "official_renderer",
        "canonical_template_hash_verified": True,
        "canonical_index_sha256": canonical_index_hash,
        "rendered_index_sha256": digest(index),
        "profile_sha256": digest(installed_profile),
        "bindings_sha256": digest(bindings_path),
        "custom_page_builder_detected": False,
        "status": "rendered-workbench-still-requires-audit-and-browser-qa",
    }
    (workbench / "RENDER_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    marker = workbench / "ADAPTATION_REQUIRED.json"
    if marker.exists():
        marker.unlink()
    print(f"PASS rendered {len(seen)} destination component families without whole-document serialization")
    print("CONTINUE: acquire/verify assets, adapt runtimes, run strict audit and browser QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
