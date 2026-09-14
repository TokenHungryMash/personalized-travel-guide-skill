# Production flow

Produce a useful eight-module handbook with concise, destination-specific content. Preserve factual correctness, the approved UI and the traveler’s interests. Avoid extra alternatives and aesthetic upgrades once the output is useful.

## Start and source ownership

After itinerary approval, preserve the current user inputs in a compact JSON brief and pass it with `start_build.py <workbench> --brief-file <current-brief.json> ...`. Include destination, country, dates/days, travelers, rhythm, interests, constraints, must_go, avoid and budget when supplied; do not ask the questionnaire again. This imports user inputs only, not prior destination research. For an explicit cold start keep the brief outside the new empty workbench. Initialization retains all existing brief fields, applies only explicitly supplied preference overrides, and rejects conflicting trip identities before writing. The generated task's `brief_file` and `traveler_preferences` carry these inputs to every pack.

Reuse itinerary approval or an explicit discussion waiver from the conversation; otherwise follow [itinerary discussion](itinerary-discussion.md). Run the controller in the workbench and read its current task. [Pipeline](research-and-profile-pipeline.md) owns pack paths and dependencies; [data shapes](research-data-shapes.md) supplies unfamiliar JSON containers. The bundled template is reusable code, not a destination output directory.

Use one agent by default for every pack and the final itinerary. Do not delegate to subagents unless the user explicitly requests it for this task. The single agent may run independent tool calls and bounded downloads concurrently. Per-venue timers, attempt ledgers and assembly commands belong to record-level recovery, not healthy ordinary production. Validate completed packs and repair the reported fields. Avoid reopening successful sources unless facts, route fit, media or user constraints require it.

## Research and selection

- Qualify exact venue/branch identity, coordinate evidence and image feasibility together. Reuse those facts in itinerary and cards. Follow [Google lookup](google-place-lookup.md) for initial venue visits and optional rating outcomes; do not add a separate rating pass.
- Freeze a useful geographic shortlist. Apply [selection](itinerary-selection-logic.md) to interests, route fit and time cost; replace a failed candidate instead of creating a surplus comparison project.
- Use seeded language/preparation drafts after destination review. Keep `_draft` until reviewed. Descriptions should explain traveler value and practical action; do not pad prose, relabel activities or alter valid local-language text to satisfy a checker.
- Use the generated task’s exact paths and field shapes. Pending transport/stays and unavailable ratings are valid. Unknown closure rules must be marked unconfirmed, not silently treated as daily opening.

## Images

[Image policy](image-and-source-policy.md) owns accepted media and provenance; [rendering](rendering-and-assets.md) owns acquisition and review commands.

One adequate exact-place image is normally sufficient. A correctly associated official brand asset is allowed with its honest classification. A successfully decoded small image is advisory in standard mode: do not upscale, pad or replace it solely to meet a size threshold. Wrong subjects, broken files and fabricated provenance remain failures.

Use media already found with the venue. If unresolved, request one candidate with the bundled helper and at most one alternate source before replacing the candidate or recording the gap. Download declarations concurrently. Inspect all selected images together on one contact sheet for subject mismatches; open only ambiguous, cropped, logo-like or watermark-risk files individually. This batch inspection is not blanket proof: record only observations actually made. Ordinary clear images need no separate full-size evidence file; source identity observations are still required.

## Finish

### Avoid repeated work

The controller and network session already record command wall time and exit status in `build-command-timings.jsonl`. For a standalone deterministic command not run by either, use `python scripts/timed_step.py <workbench> <script.py> <args>`; do not wrap an already timed command again. This measures tool execution, not research/thinking or total end-to-end time; do not claim a complete speedup from these records alone.

Run the existing network-session probe before the first external source/download batch, and reuse its evidenced workbench setting for subsequent network commands. For downloads the default is one transient retry; unchanged HTTP 404/410 failures are cached until the source URL changes or an explicit `--overwrite` retry is requested. Resume successful assets by URL/source/hash. Do not rerun a whole batch to recover one failed venue.

The automatic assets stage also runs through network_session.py, so the same evidenced network setting applies whether a command is run manually or by the controller. Stage and nested-command timing records may overlap; do not add both as if they were independent durations. The offline packer validates all public dependencies but only encodes media actually referenced in the assembled HTML/runtime.

For browser QA, reuse one supported session. Navigate before setting a temporary viewport, measure the actual viewport, and use only documented load states and observed selectors. Navigate to a chapter before clicking its hidden controls. Capture layout observations while doing the required interactions. Preview QA and exported-file acceptance cover different artifacts: keep both required records, but do not repeat a full visual matrix for export acceptance. On content-only maintenance reuse evidence for unchanged behavior and test affected maps/content plus the required exported-file interactions. Never bypass a browser policy denial or mark unobserved interactions as passed.

Make one coherence review using existing facts: day theme versus stops, opening hours, duration plus transfers, meal/rest windows, interest fit and useful fallbacks. Repair actual defects without an unrelated research or editorial expansion.

Compile and render through the controller. [Release validation](release-validation.md) owns browser samples, genuine capability limitations, user-selected human QA and completion states. Run `check_handoff.py` when ready; it already runs the applicable audit and forward test. Recheck changed inputs or failures, not unchanged passing stages. No elapsed-time target permits incomplete content or invented evidence.

For Skill maintenance use the maintenance route in `SKILL.md`; ordinary destination generation does not run the Skill’s whole regression suite.


For newly requested phone/offline map screenshots, the controller requests `maps_required` after profile/assets validation and before installing/rendering the page. Follow screenshot-map-workflow.md using the existing coordinates and OpenFreeMap source: prepare, capture, visually review and import one overview per day, then recompile the changed itinerary. No destination research or asset redownload is needed. Missing or stale captures return to this focused stage, not a full rebuild. If the original capture cannot be completed, follow offline-map-fallback.md: evidenced failure first, then reviewed geographic offline overview; no online fallback. Historical interactive guides retain compatibility.


### Paired delivery
Follow [release validation](release-validation.md#paired-delivery) for the standalone offline HTML and actual export acceptance. It is the primary artifact; workbench index.html alone is not portable. A permitted pending-review export remains unverified and is never a full handoff.


## Before cross-pack compilation
Check these while authoring, not only after individual pack validation: each restaurant has a verified image; dedicated_trip and reliable_chains are disjoint; the itinerary includes at least three dedicated restaurants; independent venues do not share one photo. A sight and experience describing the same physical venue use the supported same_place_as relationship, never a fabricated identity. Photography guidance separates 手机 and 相机. Recheck meal end times plus transfers after inserting stops. Local-language phrase items use term; English fallback sentences retain sentence. Individual pack validity does not certify cross-pack consistency.

For reported shell failures, follow runner-command-contract.md immediately after one failed utility probe. Do not repeatedly try Bash variants on Windows. Discover image URLs from actual source pages or supported APIs, never guessed filenames; use the bounded retry and proxy rules in fetch-recovery.md. Browser interaction selectors must come from observed DOM.

Before external research, use the workbench-local network probe/session in [runner setup](runner-command-contract.md). Before the first render, run `diagnose_build.py <workbench>` and repair the named source/media issues as one batch; a diagnostic or regression PASS is not a completed handbook.
