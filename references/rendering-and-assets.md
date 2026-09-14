# Rendering and asset workflow

New destination builds use `current-system` by default, including when the profile omits `ui_system`. Exact personal restoration uses [current-system.md](current-system.md). Legacy `canonical` builds require an explicit profile selection; installer, bindings and audit must agree with that selection.

## Official byte-safe renderer

Set `cover.show_summary: false` to omit the cover introduction paragraph while retaining `cover.summary` as research metadata. The default remains visible.

`build_render_bindings.py` reads the validated profile and emits all 15 registered fragments plus destination runtime bindings. `render_destination.py` inserts those bindings into the selected product without whole-document serialization. It replaces only registered inner byte ranges and preserves the outer elements.

Command:

```text
python scripts/render_profile.py destination-profile.json workbench
```

The profile's `render_bindings_file` points to a JSON file with:

- `html`: selector plus complete canonical inner fragment generated from profile records;
- `runtime_files`: optional full content for the documented destination-bearing runtimes.

Allowed selectors are `.hero`, `.trip-pulse`, `#contents`, `.flight-band`, `#stay`, `#route`, `#sights`, `#shops`, `#move`, `#food`, `#booking`, `#words`, `#tips`, `.mobile-menu-panel` and the unique page-level `body > footer`. Bind every family needed by the product; partial bindings remain an unfinished workbench. Build fragments by cloning the matching canonical component subtree and rendering target records into it. Do not copy reference prose or venue records. The status strip, contents subtitle, mobile-directory identity and footer are destination-bearing surfaces and must be generated from the same profile rather than inherited from Bali.

`render_profile.py` validates and generates bindings before installing a clean template, then invokes the official renderer. Use this one command for first render and content repairs; it stops on the first failure. It preserves research, downloaded destination assets, generated maps and browser storage. It does not research, download, or claim interaction QA. The renderer rejects duplicate/unregistered selectors, empty fragments, changed locked files and changed inline styles and writes `RENDER_REPORT.json`.

New builds default to `map_delivery: screenshots`: follow [real map screenshots](screenshot-map-workflow.md), capture and visually review every day before importing. A route list alone is not an offline map. The release gate rejects missing daily captures. Online maps are an explicit opt-in: set `map_delivery: online` and record the actual user request in `online_map_user_statement`; follow [online map workflow](online-map-workflow.md) and disclose that its basemap requires network. Never silently downgrade after a capture failure. Existing restores retain their map mode.

## Contract-compliant generic adapters

If a fragment-production helper is needed, it must be destination-neutral and reusable. It may read profile records and produce binding fragments, but may not hardcode any destination. It must preserve canonical classes, nesting, controls and interaction hooks. Whole-document DOM serialization is prohibited; registered subtree serialization is allowed only when the original inline styles and locked-file hashes are restored and verified.

## Image evidence pipeline


1. Research the exact venue/product and record image declarations in its owning research pack; compile them into the profile. Resolve assets per place, not as one destination-wide candidate pool.
   - Use `file` for the relative asset path; the compiler also normalizes the accepted `local_file` alias before manifest/rendering. Put cover provenance (`source_page`, `download_url`, media class and identity observation) beside `cover.image`, not in an unconsumed sibling object.
2. Download locally using available browser/network tools; do not infer identity from filename.
   - When direct image URLs are already declared, `fetch_declared_assets.py profile asset-root` may batch-download them. It never decides identity.
   - The downloader creates a bounded delivery derivative for images over 1600 px or 2 MiB and records the source dimensions and derivative state in the fetch receipt. It does not change the declared media class or erase source provenance.
3. Run `build_asset_manifest.py profile output-manifest`.
4. Run `verify_assets.py profile manifest asset-root --machine-only --write` for file, decode, dimension and place-ID preflight. Rendering may proceed after this passes, producing an explicitly non-final `PREVIEW_READY` build.
5. Run `build_asset_contact_sheet.py manifest asset-root contact-sheet.jpg` and inspect every selected image/source label in one batch. Open only flagged, ambiguous, Open Graph, third-party or watermark-risk files individually at full size; an exact official body photo that is clear in a sufficiently large contact-sheet cell does not require a second redundant opening.
6. Only after inspection set `visually_confirmed: true`, `watermark_checked: true` and `subject_verified: true`.
   - Save explicit decisions as a JSON array and pass `--review-records reviews.json` to `build_asset_manifest.py`. Each row contains `file`, `place_id`, `source_page`, `download_url`, `media_class`, `original_media_class`, `visual_subject_type` (copied unchanged from the declaration), `sha256` of the local file, `verification_evidence` (an existing local evidence path), `visual_confirmation_note`, and true `source_identity_bound`, `visually_confirmed`, `watermark_checked`. Use one row per actually reviewed asset. Changed bytes, provenance or media classification invalidate the review. A valid hash-bound visual review may supply the source identity observation from its concrete visual_confirmation_note; ordinary declarations still need source_identity_note. Unreviewed rows remain false; the old blanket `--visual-evidence` flag is rejected.
7. After required QA, run check_handoff.py once; it includes the strict product audit and forward test.

Evidence states are independent:

- `http_accessible`: source/file request succeeded;
- `decoded`: local raster decodes and meets minimum size;
- `source_identity_bound`: source page explicitly names the same place ID;
- `visually_confirmed`: Agent inspected the visible subject;
- `watermark_checked`: Agent inspected the full-size image for corner, center and repeated stock watermarks;
- `subject_verified`: all applicable evidence is complete.

No tool may automatically turn file existence into `subject_verified: true`. If the host's image viewer fails, try the contact sheet in its browser once. If both visual surfaces fail, stop visual retries, retain `PREVIEW_READY`, and leave the relevant flags false; do not treat a sandbox defect as a reason to redo research or downloads.

Use a bounded candidate budget. For each required image slot, inspect at most three candidates from the preferred source tier and at most six candidates total. If none passes, switch source tier or replace the venue rather than scanning dozens of weak results. Reject obvious logos, banners, posters, maps, UI screenshots, social cards and known stock-preview hosts before downloading. Never rank approximately 30 candidates for every slot.

## Pending stays

Pending accommodation renders `.hotel-card.stay-pending` with neutral copy and no property image, address, booking link or map link. Confirmed accommodation uses the normal gallery and requires at least two distinct verified exact-property images; use three when reliable assets are readily available. Changing status from pending to confirmed requires rerendering the complete `#stay` family.

For a cover reusing a reviewed place image, `cover.derived_from` is the relative image **file path** (for example `assets/lake.jpg`), not a place ID. Review the whole candidate batch before repairing owning packs; batch changed declarations, recompile once, then fetch only changed candidates.
