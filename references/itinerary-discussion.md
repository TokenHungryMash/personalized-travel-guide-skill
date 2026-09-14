# Itinerary discussion before production


## One compact proposal

Use the current brief, including interests, must-go places, exclusions, rhythm and known arrival/departure constraints. If optional information is missing, state a reasonable assumption instead of adding another intake round. With no dates or flights, keep the first/last days conditional and avoid exact schedules.

Show one preferred outline, normally one row per day: area, one main anchor plus compatible secondary stops, evening plan, and pace. Follow with two or three concrete tradeoffs: what the interests receive more time for, what is omitted, and which decision could materially change the route. Distinguish optional replacements from additional commitments. Do not write restaurant libraries, full descriptions, packing/language chapters or photography guides at this stage.

Use the itinerary-selection rules. Verify only facts that could overturn the outline, such as whether a date-dependent anchor exists, its location or a closure conflict. Keep uncertain venues as candidates and exact times/prices unconfirmed. Do not conduct a separate exhaustive research pass, chase ratings, download images, generate HTML or build maps. Reuse any verified planning sources after approval so the discussion does not become duplicate work.

Ask a single direct question after the reviewable proposal, for example: `这个方向是否合适？想调整哪一天，还是按这版展开完整手册？` This is the requested itinerary approval, not an additional generic permission flow. Wait for the reply; do not run full research in the background while waiting.

`start_build.py` is the executable gate. Call it only with exactly one of `--itinerary-approved` or `--discussion-waived`, plus `--user-statement` containing the user's actual words. Do not quote the questionnaire request, your own proposal, `按默认`, or inferred consent as that statement. The script records the gate in `itinerary-approval.json` and the build state.

This gate checks structured declarations and rejects known intake-only replies. It cannot authenticate conversation messages or prevent an agent from bypassing the entry point. Never claim script tests prove host compliance. A host acceptance test must observe questionnaire delivery, proposal, waiting, and production after actual approval. Choosing a recommended destination completes destination selection only; show the daily proposal next.

## Approval and revisions

- `按这版做` or an equally clear acceptance of the displayed outline authorizes production. A supplied itinerary explicitly approved earlier in the current conversation also qualifies; do not ask twice.
- New keywords or `按默认` authorize drafting an outline, not approval of a route the user has not seen.
- If the user revises the direction, update the outline only. If they explicitly say to implement their revision and proceed, that authorizes the revised plan without another confirmation.
- `不要讨论，直接生成` explicitly waives this step. Do not infer a waiver from a brief request to generate a handbook.
- Preserve the agreed daily areas, core interests and important exclusions in `itinerary-outline.md` beside the eventual workbench profile. Include the actual confirming/waiving user statement and any known pending facts. Do not fabricate consent or use a generated suggestion as user approval.
- Once approved, continue autonomously through production. A same-area restaurant replacement, adjusted stop timing or minor closure workaround does not require another approval. If evidence makes an approved core experience impossible or changes a whole day's direction, explain the specific conflict and discuss the affected day only.

The outline is the selection brief, not source evidence and not a replacement for canonical research packs. After approval, research the selected route and the handbook's required optional inventory in the normal bounded batches.
