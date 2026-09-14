# Real street-map screenshots

For newly requested screenshot/offline maps, retain the existing MapLibre 5.6.0 / OpenFreeMap Liberty source and verified destination coordinates. Do not reuse Bali maps, screenshot assets, labels or trip data, or competitor artwork. Phone delivery uses local captured images; it must not depend on a working phone WebGL renderer or external map CDN. Existing online guides stay unchanged until reviewed screenshots are imported.

## Prepare, capture, review, import

The capture runner resumes successful captures only when page bytes, route fingerprint, output bytes, viewport and ready-state label counts still match. It preserves existing review flags without upgrading them. A fully cached plan does not launch a browser. Changed or interrupted views are retried individually; do not delete the report to restart a healthy batch.

New capture plans use schema version 2. A host-managed capture must record `page_sha256` from the captured HTML bytes and `day_fingerprint` from that task alongside the actual image hash, `observed_state.status: ready`, label count, and a nonempty human review note. Never copy fresh bindings onto an old image. Import rejects a changed page or route even if the old image hash itself still matches. Existing version-1 plans retain compatibility; prepare a new plan for changed routes.

Repeated import reuses a verified delivery derivative only when original bytes, route, caption, compression implementation and derivative hash all match. An unchanged import does not recompress, rewrite itinerary data or create another backup. Recompile/rerender only when content actually changed.

After the current profile compiles, use the verified Python interpreter:

```text
python scripts/route_screenshots.py prepare <workbench>
node scripts/capture_route_maps.cjs <workbench> --browser <existing-browser-executable>
python scripts/route_screenshots.py import <workbench>
python scripts/research_status.py <workbench>
python scripts/advance_build.py <workbench> --run
```

The capture command uses an authorized Playwright or playwright-core installation and an installed browser. It neither installs dependencies nor changes browser policies. For an isolated host-managed driver, pass `--driver <absolute-path-to-playwright-core>` together with `--browser <installed-browser-executable>`. This supports Codex and WorkBuddy without host-specific tool names or machine paths. If the host permits dependency setup, one isolated driver installation is appropriate; a bundled Chromium download is unnecessary when an authorized system Chrome is available. Probe one prepared page and inspect its real image before capturing the full plan. A host with its own authorized browser may instead open the prepared `qa/route-capture/day-N-M.html` pages, wait for `CAPTURE_STATE.status == ready`, capture the full `#sheet`, and save its actual observations/hash in capture-report.json. Never change browser, URL or engine to bypass an explicit access denial. Stop after two failures, preserving logs and completed PNGs. CLI success is not visual review.

Pages are 1400×1100 CSS pixels, captured at device scale 1 by default (higher-density originals are accepted). Generate exactly one offline overview per day containing all scheduled stops; do not automatically generate local views. Keep full place-name labels and leader lines without moving coordinates. A failed layout or unloaded tiles must not produce an accepted screenshot. Map labels use available source-language names; do not invent Chinese translations for unnamed roads. Wide-area overviews show location distribution and itinerary order, not every road name. Keep readable typography and external navigation links for street-level directions.

Open each actual PNG at full resolution. Confirm real streets/buildings, relevant road names, all expected place labels, no clipping/overlap, and legible OpenFreeMap / OpenMapTiles / OpenStreetMap attribution. Only after observing it set that capture's `visual_reviewed: true` in capture-report.json, with a short review note. The importer requires actual PNG/JPEG/WebP bytes/hash, ready-state evidence and the current route fingerprint; it keeps the original capture untouched under qa and compresses a delivery derivative to WebP quality 84, maximum width 1600 without upscaling, inside a portable SVG wrapper and writes route_screenshots to the owning research/itinerary.json. The PNG originals stay under qa, not the public media inventory. Source SVG/hash/route freshness is audited; rerendering cannot replace screenshots with unrelated trip assets.

The main itinerary and Trip Mode show the same single daily overview, with an open-large-image link. On phones, open the image to inspect labels; use external navigation for street-level directions. Images work offline; no live navigation/traffic claim is made. Exporters must embed the SVG files and their embedded raster payloads; the single-file exporter directly embeds the captured raster to avoid nested base64 growth for single-file mobile delivery.

If original screenshots fail after bounded authorized attempts, follow [offline overview fallback](offline-map-fallback.md). A reviewed geographic overview with failure evidence is the only new-build fallback; do not switch to online maps. An unreviewed diagram, old trip image or empty canvas remains pending. Static map data attribution guidance: https://openfreemap.org/#attribution .

## Single-file phone sample and acceptance

This optional map-only artifact is for an explicitly requested separate phone sample or map-viewer maintenance. Ordinary handbook production imports the daily overviews into the handbook and uses its export QA; it does not also build a second sample or request another visual-approach approval.

The preferred phone/offline presentation is real road imagery, full place-name labels and itinerary-order lines. Reuse the prepared views and reviewed screenshots; do not switch basemap schemes or repeat destination research. Keep exactly one overview per day. Do not truncate long names to fit the image.

After capture and visual review, run `node scripts/pack_phone_maps.cjs <workbench> [output.html]`. This dependency-free Node packer produces a standalone map-only HTML with embedded PNGs, a complete 17px place-name list under every view, and a 100–400% large-image viewer with scrolling and close controls. It requires the actual PNG/hash, ready-state evidence, matching label counts and a nonempty visual review note. It does not import maps into the full handbook or prove phone acceptance. The default output is `手机离线连线地图.html` inside the workbench. For a separate sample package, copy the prepared `qa/route-capture` directory and the capture/pack scripts; no destination data belongs in the Skill itself.

Before delivery, open the generated file through `file:` in an authorized browser at a 390px viewport with networking disabled. Confirm every image decodes, no page-wide horizontal overflow, full names remain readable without clipping/ellipsis, zoom steps and scrolling work, and closing returns to the page. Record actual image counts, errors, network attempts and file size. Do not hard-code a particular trip's counts, image size or successful QA claims. Large embedded files must be tested as the actual delivered file; a desktop viewport test alone does not establish phone compatibility.

Report desktop offline verification and real-device verification separately. User approval of the visual approach does not imply phone testing. Once the sample is accepted for integration, use the existing import/render flow above for the main itinerary and Trip Mode, then export and check the latest complete handbook. Preserve full names and in-page zoom access in phone delivery; do not deliver an older handbook just because its filename says offline. Static maps provide no live navigation or traffic. Keep cloud upload subject to the user's authorization.

## Compact delivery and host screenshots
Set the required viewport after navigation if the host resets it. Measure the visible sheet before capturing; prefer its exact rectangle over a full-page image with blank margins. Read the real data-capture-state DOM attribute for readiness; it is populated only after loaded tiles and successful labels. A browser may return JPEG bytes despite a .png filename; the importer detects the actual format rather than requiring a manual extension trick. Keep the original hash, dimensions and bytes in the provenance. Visually inspect the compressed delivery derivative as well as the original for legible labels and attribution. Do not discard roads or attribution to shrink files. Report final offline HTML size; investigate a map-heavy result over 20 MB before delivery.

If a host clip capture introduces scale-related blank margins despite a matching sheet rectangle, use an actual whole-viewport capture with the viewport exactly matching the sheet, then inspect the pixels. Never accept padded output as a successful map. The standalone handbook exporter supplies an in-page image dialog for embedded maps, avoiding top-level data-URL navigation. Test its fit/zoom, internal scrolling and close controls in the actual delivered HTML. This is a local image viewer, not a live map or a policy bypass.
