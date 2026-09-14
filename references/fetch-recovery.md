# Fetch recovery and early contracts

Read when a host reports map, image or source-access failures. Preserve completed work; do not restart the handbook or weaken handoff gates.

## Offline maps

`prepare_osm_route_tiles.py` uses `_osm_extract.py`: deduplicated global 0.10° cells, two selector groups, serial requests, at most three attempts per job with endpoint rotation and exponential backoff. Each invocation has a 240-second network budget. Each successful job is atomically stored in `osm-cells/` with its query SHA-256, response SHA-256 and endpoint. Rerun the identical command to fetch only missing or corrupted jobs. A successful empty cell is valid; a response containing an Overpass `remark` is incomplete. The merged extract deduplicates `(type,id)` while writing one cell at a time. Never delete the cell cache after a timeout, automatically rerun indefinitely, disable TLS verification, or use `overpass.osm.jp` as a default endpoint. Very large/long-distance routes must be split before fetching, not expanded into hundreds of metropolitan cells.

## Images and sources

Download the declared HTTPS source directly. Do not silently rewrite Wikimedia to a proxy. Requests to the same host run serially; Wikimedia requests are spaced by at least three seconds. Independent hosts may run concurrently. An HTTP 429 stops pending network requests to that host for the current invocation; verified cache hits still work. Do not immediately rerun the same throttled batch. Transient 5xx/network failures use the configured retry limit. Only an explicitly declared `wsrv.nl` URL gets bounded host-specific 404 retries; an origin 404 is not generically transient. After a source failure, use one exact-place official alternate (official social or tourism/venue listing), then one reputable exact-place listing. If neither verifies the fact, retain uncertainty or omit dynamic claims. TLS errors never justify disabling certificate checks.

Asset receipts match place ID, file, download URL, source page and actual SHA-256. Filename equality alone is not a cache hit. Map receipts likewise bind request identity to response bytes. Changed source inputs or damaged bytes invalidate only affected jobs; caches from another cold-start build are not reusable research.

## Pack and evidence requirements

All physical place records except souvenir product records require finite numeric `latitude` and `longitude` in the place pack. Confirm the exact branch with its map identity during normal lookup. Geocoding may locate a candidate, but its name/address must be checked before using the coordinates; never invent coordinates or use a city centroid. Renderer latitude range is -85 to 85, longitude -180 to 180. Missing coordinates fail early with a JSON pointer.

For sights, shops and experiences, `hours` and `closed_days` must contain explanatory text (or a nonempty text array for `closed_days`). If no closure is verified, say “休息日待确认，以官方公告为准”; do not fabricate one or use an empty array just to fill the field.

Full media verification requires `visually_confirmed`, `watermark_checked`, `subject_verified` and the applicable source identity binding. Set these only after actual inspection. Keep `verification_evidence` inside the workbench, and bind review/download receipts to current file SHA-256. Machine-only preflight does not establish visual identity. Keep diagnostic raster screenshots under `qa/`, `browser-qa/`, `qa-evidence/` or `screenshots/`; elsewhere, undeclared rasters are reported as orphan assets. These directories are for actual QA evidence, never a way to hide product images from auditing.

## Google response interpretation

An HTTP 200 JavaScript shell is not an opened place panel. A raw-HTML probe that cannot render it must report the limitation and use the authorized browser panel when available. `no_visible_rating` is valid only after the exact-place panel opened and no attributable rating was visible. Otherwise use `access_failed` for a rendering/access limitation or `identity_unresolved` when identity was not established, explaining the actual evidence. Apply the existing two-place access-stop rule and omit scores; do not run thirteen identical shell-only probes. A host-created `google_probe.py` is not bundled by this Skill and must obey this protocol.

## Interrupted image batches

The downloader atomically checkpoints asset-fetch-report.json after each completed result and flushes progress. Recompilation may drop profile-embedded receipts; the downloader reloads matching receipts from that report and verifies URL/source/hash before using cached bytes. Never hand-write receipts or modify the compiled profile to force a cache hit. Change incorrect URL/file/source declarations in the owning research pack, compile once, then resume the official downloader. Use small --place-id batches after actual host timeouts; do not launch untracked background loops. Empty logs or a pipeline's final command exit code are not success evidence.

Within one batch, declarations sharing the same resolved file, direct URL and source page use one acquisition (including an allowed cover or same-place reuse), while retaining a receipt per place/file. A matching verified local receipt can satisfy the shared file without another request; this does not copy visual identity approval between places or waive same-place validation. Conflicting sources targeting one file fail before downloading; correct their declarations instead of allowing one source to overwrite the other. Final profile, provenance and report saves also use atomic replacement so the last save does not truncate an earlier successful checkpoint.

Pass the workbench as `asset_root` when declaration paths already begin with `assets/`; otherwise files would land under `assets/assets/`. If an earlier run saved its genuine report elsewhere, pass `--resume-report <existing-report.json>`; the downloader reads it without modifying that original and still checks current paths, URLs and byte hashes. This is recovery within the same trip, not reuse of another trip's research.

Network policy rejection is not permission to use an unchecked direct downloader. A documented Fake-IP proxy setting applies only after confirming that environment and its permitted ranges; never use it to override a host access denial. When blocked, preserve the verified data and report the actual remaining constraint. Product cards require exact product imagery or honestly labeled allowed brand artwork; store interiors do not become product images because the goods are sold there.


## Existing local media from an authorized acquisition

If the host already saved real image bytes through an authorized tool, use `python scripts/import_local_assets.py <profile> <asset_root> <evidence.json>`. The evidence JSON is an array with `place_id`, `file`, `source_page`, `download_url`, `sha256`, `evidence_file` (saved actual acquisition log relative to asset_root), and `acquisition_note`. Copy URLs and acquisition facts from the actual tool output, not guesses. SHA256 must match the actual saved bytes. The importer decodes images, checks bindings, and atomically merges records keyed by (place_id, file). It does not edit the compiled profile, perform a network request, verify source identity, or claim it downloaded anything; records say local_import/network_verified=false. Run the normal manifest, identity and media checks afterward. Never handwrite asset-fetch-report.json or _fetch_receipt to manufacture success.

This path is for legitimately acquired local files, not a way to evade a network/security denial. A non-public-address error means DNS returned a disallowed address, not that DNS resolution failed. Diagnose the resolver/proxy; only confirmed Fake-IP deployments may use the documented bounded proxy setting. Do not disable address checks or fetch through unrestricted urllib to bypass them. If no authorized source works, preserve progress and report the real limitation.


### Observed source failures
HTTP success is not image success: reject HTML responses, decode downloaded bytes, and record 404/TLS/timeout separately. Do not disable TLS verification. For a failed candidate, use a verified exact venue/product page and retain its provenance. Inspect the actual subject before approval: restroom entrances, menu stands, promotional banners and branded collages are not substitutes for venue interiors or product packaging. Official provenance alone does not establish the desired subject; correct visual_subject_type to what is actually visible. Never bulk-mark candidates verified or upscale low-resolution images to pass checks.
