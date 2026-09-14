# Bounded research, safe writes and trial recovery

Read when the current research batch starts, especially for a timed cold-start trial. The nine source packs and their content/source requirements are unchanged. `PHASE 2/6` is a dependency barrier containing multiple packs; it is not a five-minute unit. Do not try to research and author all sights plus shopping in one uninterrupted operation.

## Real work units

On Windows use the [runner command contract](runner-command-contract.md): one stable PowerShell wrapper for start/status/finish/stop and optional final save+finish. Its interpreter path is already verified. Avoid manual bookkeeping tool-code construction. The Python API below remains the cross-platform equivalent.

At the beginning of the run start `research_checkpoint.py <workbench> start --unit framing --items framing`. The first timestamp starts measured run time; record initialization before it separately if initialization has already happened. After saving the output, run `... finish --note <saved-output-and-result>`. These commands maintain `.research-state/timing.json`, including stopped and overrun units. They do not auto-terminate tools; check `... status` between tool batches and use bounded tool timeouts.

For a places pack use these independently useful units:

For standard core places, select one venue by default while Google-panel, official identity/coordinates or exact-image work remains unresolved. Select two only when the available evidence makes both look cheap enough to finish with roughly a minute reserved for record writing/validation. This is advance workload planning, not a promised duration; use measured prior-unit costs when available. Three core places are rejected by the timer wrapper. Keep a slow venue in its original timer; never rename or restart unfinished work to hide an overrun.

1. Shortlist: freeze the candidate IDs and daily area fit in a small JSON draft, without polished descriptions. Do this once per pack.
2. Qualify and author 1–2 named venues per unit: batch exact official/source searches, then independent page reads. Collect identity/branch, coordinates with their attributable source, hours/reservation facts, practical notes and up to two candidate images in the same lookup. Save complete records from that unit to a partial draft under `research/drafts/`. Use `--unit places-core-01 --items <id-a> <id-b>`; choose concrete IDs before starting.
3. Assemble: merge the already researched draft records into the canonical pack scaffold, validate the complete pack and close the unit. Full pack minimums remain in force; partial drafts never count as pack completion.

Use [record commands](runner-command-contract.md) for place packs: author one independent JSON object, `add-record` it immediately, then `assemble-pack` once its records are complete. The helper groups records into sights/support or shops/souvenirs and writes arrays safely. Do not hand-write a multi-place JSON array/object for a timed batch. A failed single-record parse leaves earlier accepted records intact.

Itinerary units cover one authored day at a time, followed by full itinerary assembly. Practical/language units review one existing seeded content family at a time, then assemble and validate the full module pack. Other small packs may fit in one unit. Select the unit boundaries before research; never reset the timer on the same unfinished venue, rename an overrun unit or split recorded elapsed time after the fact. Keep overall run wall time and per-pack summed unit time so repeated tiny units cannot conceal slow execution.

In an explicitly requested test/fix loop, use the user's limit (currently five minutes per unit, not five minutes per dependency phase). On an overrun or two consecutive failures of the same concrete delivered business command, preserve evidence and stop the runner for the repair owner. Successful real commands reset the business streak. Adapter JS/schema/identifier errors mean the script never ran: they never increment business failures or trigger a two-error stop, and must not finish/stop/reset a timer. Correct the invocation using the host’s documented tool interface; see runner-command-contract.md for CLI arguments. Actual wall time continues through adapter correction and still triggers the five-minute limit. Reporting an unsuccessful trial to the repair owner is permitted even if the handoff gate is false; never label that guide accepted. Ordinary production follows the correction loop and has no universal total deadline.

## Batch the mechanical work

For a single official page, including the framing cover source, use the bundled standard-library CLI:

```text
python scripts/probe_official_page.py "https://official.example/place" --output <workbench>/research/drafts/official-page.json --timeout 10
```

On PowerShell invoke the selected Python executable with `&` and quote each path/URL argument separately. The script handles HTML parsing internally. Do not assume `requests` or `bs4` exists, install them for this lookup, or build complex Python regex/HTML one-liners across PowerShell quoting. A working Python plus Pillow is the pipeline's runtime contract; the page probe itself needs only the standard library.

Read its JSON: `ok` returns candidate image URLs plus page title/description; `no_image` is a successfully fetched page without a usable declared image. `timeout`, `network_error`, `http_error`, `invalid_url`, `not_html` and `too_large` explain unsuccessful probes without a stack trace. Missing metadata is not proof the venue has no photos. Use the existing bounded source ladder; no repeated same-source probing or improvised parser fallback. Timeout is a 1–30 second socket timeout, not a complete-stage timer; the research checkpoint remains authoritative for total elapsed time.


For souvenirs/products, supply `kind: souvenir` (existing `type`/`place_kind` souvenir labels also work), `product_name` or the exact local `display_name`, and `official_url`. Add verified spelling aliases through `product_aliases` only when useful. The helper reads JSON-LD product images, body images, lazy attributes, srcset/picture sources and inline CSS backgrounds; it may follow at most two same-site links carrying the exact product name. No nearby-street, Wikidata geography or generic open-media fallback runs for products. UI/navigation images and other products are filtered even when the site title contains the desired product.


For each 1–2 venue unit, collect official URL, exact map query/URL, coordinate source, and candidate-image requests together. Run `research_image_candidates.py requests.json candidates.json --workers 3 --per-place 2` once for that unit. The helper ends extra lookup for identity-bearing official photos or correctly associated standard brand media; shared tourism-site artwork does not end the photo ladder. This is a candidate shortlist, not visual verification or proof of coordinates. Obtain missing coordinates from an exact official/map entity source; never infer them from the image or district. Keep verified facts in the canonical record and reuse them in itinerary/modules.

The image helper now prints a validated structured summary containing `schema`, `source_file`, counts, empty IDs and each place's candidate URLs/source pages/coordinates. Use this stdout directly; do not add a file-reading tool call after a successful collection. The official-page probe also prints its metadata when `--output` saves a file. These outputs contain the data needed for the next decision.

An official tourism portal is not the same identity as each venue it lists. The helper detects shared OGP across same-host pages in a batch, common/default artwork URLs and images lacking venue identifiers. These are `official_share_card`/`official_brand_asset`, kept in `official_artwork`; they do not become exact-place photos and cannot terminate photo lookup. A portal's logo cannot fill an unrelated shrine's card. Correct venue/chain-brand artwork may still satisfy standard mode when its actual association is verified. Identity-bearing body images take priority; only qualified exact-subject candidates or correctly associated standard brand media end the ladder.

If candidate output must be recovered after a context change, use one parameterized command:

```text
python scripts/inspect_research_json.py "<exact source_file printed by producer>"
```

Copy the producer's exact path and quote it as one argument, including Chinese characters/spaces. This inspector returns the same `travel-image-candidate-summary/v1` schema, or `input_missing`/`input_invalid` with a useful error and exit code 2. It checks JSON shape only, never factual or visual correctness. Do not invent a second filename or construct temporary JavaScript/PowerShell/Python parsing code through the host tool adapter just to inspect candidate JSON; use producer stdout or this CLI. Normal tool orchestration still uses the host's documented tool interface.

Batch exact-name rating searches and independent exact-venue page reads with the available tools. Follow the entrypoint's Google capability probe and per-venue identity/visible-panel rules; do not scrape an invented endpoint or treat a parser miss as a Google failure. Keep score, count when exposed, exact source URL and retrieval date together. Optional absent ratings never block standard delivery. Source fetching can be parallel; identity and factual decisions still require reading the returned evidence. Do not serialize a separate rating, coordinate and image research pass over the entire destination.

## Safe JSON writes

Never use `Delete File` and `Add File` for the same existing path in one `apply_patch` call. Use `Update File` with actual context for a small edit. For new data or whole-pack replacement, create a fresh `*.next.json` using `Add File` once, then run:

```text
python scripts/write_research_json.py <target.json> --from-file <target.next.json> --workbench <workbench> --pack-id <pack-id>
```

Initialization creates `research/drafts`, `research/places`, `research/modules` and `research/tasks` before any source authoring. Save staging JSON inside one of those directories before invoking the writer; it cannot read a staging file that was never saved. Do not run validation against an absent target after an earlier staging write failed.

The helper parses object/array JSON, rejects null/nonfinite values, checks the pack before replacement, writes a temporary sibling, and atomically replaces the target. It preserves a parseable previous file as `target.json.bak`. `--workbench` restricts target paths and automatic parent creation to the resolved `workbench/research` tree; without it the CLI can infer an initialized ancestor containing `research-plan.json`. Traversal or linked paths escaping that tree are rejected. Use a new staging filename when the old one already exists, or edit it with `Update File`; never Delete+Add it in the same patch. For partial drafts omit `--pack-id`, keep them under `research/drafts/`, and do not claim semantic validation. Python callers may pass an in-memory object to `write_research_json.write_json(..., workbench=root)`; avoid embedding generated JSON in interpolating shell strings. After one patch failure, switch to this method rather than repeating a destructive replacement pattern.

## Resume versus a fresh trial

Resume within the same run: retain valid framing and completed records, fix the cause, validate only affected packs, then query the controller. Keep the same Skill root and original run start time. Recompile downstream outputs if source packs changed. Never delete correct framing because a later pack failed.

For a mechanical `assemble-unit` validator gap, correct and save the required records (such as missing core support), then repeat the identical command. The helper hashes semantic record content and validator dependencies, creates a new attempt only for changed inputs, and preserves previous errors/timers in `.research-state/assembly-attempts.json`. Formatting edits, renaming units, or returning to a failed hash do not unlock another attempt. This is dependency repair, not permission to restart unfinished research. Status retains the full assembly phase wall time across attempts and repair intervals. An active attempt reuses its original timer; the child process is bounded by the remaining five-minute budget.

Fresh cold trial after a Skill repair: create a new, nonexistent workbench directory, run `start_build.py` and initialize from the same user brief and defaults. Do not copy framing, packs, image caches, manifests or guide text from the stopped run. The previous run is preserved for diagnosis; its user brief may define the identical test inputs. Count each attempt and repair time separately and report the overall wall time. Cold-start isolation and incremental recovery are different choices and must be named accurately.
