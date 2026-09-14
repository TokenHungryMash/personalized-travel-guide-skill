# Resumable research and profile pipeline

Use this pipeline for every complete new-destination build. It exists because a production handbook requires many verified records; the solution is bounded persisted batches, not a smaller or generic handbook.

## Contract

1. After the itinerary discussion is approved or explicitly waived, run `start_build.py`, then `init_research_workspace.py`. Preserve the agreed outline in `itinerary-outline.md`; do not initialize full research while waiting for itinerary feedback.
2. Run `research_status.py`. Work only on the printed bounded batch (normally two independent packs; use `--batch-size 1` only after a repeated failure on a weaker host).
3. Establish area framing, then qualify and freeze place records before writing the full itinerary and downstream module bindings. Save each JSON and run the exact `validate_research_pack.py` command printed by the status tool.
4. Rerun `research_status.py`; repeat without asking the user to say “继续”.
5. Run `compile_destination_profile.py` only when all packs exist.
6. Correct validation errors in their source packs and recompile. Never repair profile defects by editing rendered HTML.

Pack completion means a real JSON file with researched content, not a prose note, placeholder, AI-generated place image or copied canonical destination record. An absent or empty optional `ratings` array is valid. `research_status.py` performs an early pack-contract check and writes compact JSON-pointer errors under `.contract-errors/`; the final validator remains authoritative for cross-pack floors and relationships.

## Pack ownership

- `framing.json`: top-level destination fields, `trip`, `cover`, `transport`, `stays`, optional `journey_phases`, `local_rating_platform`, and `render_bindings_file`.
- `itinerary.json`: one array containing every canonical day, each with a practical theme, three periods and ordered stops. Airport, station and pending/confirmed stay nodes remain visible where relevant.
- `places/core.json`: an object containing `sights` and `support` arrays.
- `places/shopping.json`: an object containing `shops` and `souvenirs` arrays.
- `places/experiences.json` and `places/restaurants.json`: complete record arrays for their focused families.
- `modules/discovery.json`: `shopping` and `experiences` canonical groups containing place-ID references.
- `modules/practical.json`: `food` and `preparation`; food uses `menu_primer`, exactly four `local_snacks`, `dedicated_trip`, and `reliable_chains`. Delivery and the former hotel-proximity family are omitted.
- `modules/language-notes.json`: `language` plus five travel-note groups covering weather, culture/etiquette, transport, safety and payment.

This nine-pack layout is the Standard default. The compiler can still read the older split layout solely for backward compatibility; new builds must not recreate it.

## Research order

The queue enforces phase barriers: `framing` → `places-core + places-shopping` → `places-experiences + places-food` → `itinerary` → `modules-discovery + modules-practical` → `modules-language-notes`. Packs within a `+` phase may run together; later phases never appear until the earlier phase validates. This preserves concurrent independent research without allowing a full itinerary to bind places before image-bearing eligibility is known.


`init_research_workspace.py` writes a machine-readable task specification for every pack under `research/tasks/` and a compact `.research-state/candidate-ledger.json`. Read only the current task file. Do not load all task specs, the full canonical HTML, every reference document or validator source into one model context. `seed_deterministic_packs.py` supplies conservative preparation, language-category and travel-note drafts; these remain pending through `_draft: true` until an Agent reviews them for the destination.

For image-bearing packs, use an eligibility-first shortlist. Before committing a venue, confirm (1) exact entity/branch, (2) a verified coordinate pair or exact-pin source, and (3) at least one plausible exact-place image candidate. Record `keep`, `replace` or `pending` plus short failure reasons in the candidate ledger. This is a small decision log, not a prose progress report. It prevents context loss and avoids researching polished copy for a venue that cannot pass release.

For unfamiliar containers, consult [research-data-shapes.md](research-data-shapes.md). It is the authoritative container contract for group objects, wrapped `place_id` references, pending/confirmed transport and stays, restaurant signature dishes and rating availability. The generated task file defines counts and destination-specific fields; this reference defines their JSON shapes. Do not discover those shapes through validator retries.

Use exact local/English map queries and stable IDs from the beginning. A place appears once in `places` and may be referenced from itinerary and multiple module groups. Images remain declarations until fetched and visually verified by the asset workflow.


Do not resolve a destination-wide coordinate list through dozens of uncached Wikidata calls. Reuse cached entity results. On the first 429, stop parallel requests to that host and respect `Retry-After`; make at most one later low-frequency attempt, then use an exact official/map entity source or replace the candidate. Never infer coordinates from a district name or draw false geography.

## Failure handling

- A failed source or unavailable image affects one pack. Substitute the source/place and continue.
- A validator error names a data contract defect. Fix only the JSON pointers listed for that pack and recompile; do not regenerate unaffected packs.
- Safe syntax repair may remove a UTF-8 BOM, Markdown JSON fences and trailing commas. It must never invent facts, coerce semantic types, create missing records or silently discard unknown fields.
- `research_status.py` returning nonzero means more work remains; it is not a blocker or handoff condition.
- `destination-profile.json` is generated output. Do not manually diverge it from the packs.
- When a valid source pack changes after compilation, the controller invalidates the old signature and routes automatically to `profile_required`. Recompile instead of diagnosing this expected dependency change as a new research failure.

## Retrying from an older export

An older rendered guide may be inspected for candidate names, but it is not a valid input contract. The current pipeline recognizes a `destination-profile.json` without both `research-plan.json` and `RESEARCH_PROVENANCE.json` as unsigned legacy output and routes the build to `research_required` instead of `profile_invalid`. Initialize fresh packs in the current workbench and let the compiler replace the ignored profile.

Migrate by evidence family, not by copying files:

- retain already gated flight/hotel selections only through the complete records in `trip-decisions.json`;
- turn old place names into current research queries and write newly sourced records into the printed pack batch;
- write `shopping_advice` and `photo_advice` in every day pack before it can count complete;
- re-source old local images unless they already have the current source page, direct URL or decodable-file contract, fetch row, full-size evidence and exact-subject note;
- never manufacture provenance by hashing copied old packs or by adding verification flags to an old manifest.

This is a bounded gap rebuild: passing decision records are preserved and only handbook research/media gaps are redone. Old incompatibility is expected migration work, not an unrecoverable failure.

## Context and code budget

- Keep destination facts in JSON packs and reusable behavior in Skill scripts; never embed a destination dataset in `SKILL.md` or a destination-specific Python/JavaScript file.
- Read only the current pack's task spec and the reference relevant to that pack.
- Use the compiler and renderer instead of reproducing canonical markup in the prompt.
- Prefer stable generic functions and schemas to per-destination branches. Country-specific facts belong in researched data, not `if destination == ...` code.
- Do not print full profiles, HTML or manifests to the conversation. Report counts, failing IDs and file paths.
- A new helper must replace repeated manual work and have a smoke test; do not add one-off wrappers that merely rename another command.
