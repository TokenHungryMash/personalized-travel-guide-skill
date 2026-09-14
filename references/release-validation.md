# Release validation

This reference owns completion states and QA scope. It applies after official rendering; maintenance tests only the changed contracts unless shared UI/runtime behavior changed.

## Response states

| Controller result | Action and allowed wording |
| --- | --- |
| `response_state: in_progress` | Continue the next required action and focused repairs. Do not claim completion. `preview_ready` alone is not release evidence. |
| `response_state: waiting_for_review` | Automatic gates passed, and current-build evidence records authorized pending human QA or a real unavailable browser surface. A preview response may end the turn. Full handoff and browser QA remain pending. |
| `response_state: complete` | Required QA and automatic gates passed. Claim completion only after `check_handoff.py` prints `HANDOFF ALLOWED`. |

`final_response_allowed` distinguishes a permitted preview/review response from continued agent work. `handoff_allowed` separately controls full completion; never substitute one for the other. Failed data, research, media, render or automatic gates cannot enter the review-wait state. A user's approval of the workflow is not test evidence.

After source/render/QA work is ready, run `check_handoff.py <workbench>` using the verified interpreter. It executes the applicable strict audit and forward test, records state and returns nonzero while handoff remains pending. Do not run those same scripts separately first. A nonzero code requires the printed next action, which may be continuing work or waiting for review.

A full release requires the official render, current compiled profile and asset manifest, no `ADAPTATION_REQUIRED.json`, current research provenance, passing asset/structure checks and actual applicable QA. Missing optional ratings and unprovided transport/stays are valid pending content, not release blockers. Keep `RESEARCH_PROVENANCE.json` and `MEDIA_AUDIT.json`.

## Automated browser QA

Questionnaire-only checks are separate from handbook release QA. The questionnaire uses visually styled `label[for]` controls over hidden radio/checkbox inputs; click the visible label and verify the associated input's checked state. A timeout clicking a hidden input does not establish a broken questionnaire. Fill the visible date text fields (the native picker inputs are intentionally hidden), submit the form, then verify the generated request contains the chosen values. Test copying only after output is shown; if the browser denies clipboard access, verify the visible manual-copy fallback rather than claiming clipboard success. Installation itself needs file integrity and questionnaire delivery, not this entire browser matrix or the development suite.

Use `browser-qa.json` with `validation_mode: representative` and actual desktop/mobile observations. Bind it to `build_fingerprint` from `_manual_qa.build_fingerprint(workbench)` for the version actually tested. Missing or stale fingerprints invalidate acceptance; never replace the fingerprint alone to make old observations pass. Record measured `inner_width`, `inner_height`, `horizontal_overflow: false` and mobile `match_media_mobile: true`. Never infer measurements or successful interactions from source code.

| Scope | Required sample |
| --- | --- |
| standard | Desktop cover/contents and mobile sight/Trip Mode; no horizontal overflow; one disclosure and Trip Mode opened/closed. Two saved screenshots, one per viewport. |


Do not create galleries just to test them. When a representative sample has no multi-image gallery, record `interactions.galleries: not_applicable` and omit its sampled ID. Inspect the static mobile card instead. For every build, repair any observed broken control even outside the minimum sample.

Use the authorized browser surface. For local HTTP preview, `preview_server.py <workbench>` binds an available loopback port and reports the root, URL and build hash; verify that identity and stop only the process started for this preview. Technical lack of file support may use an authorized loopback surface. Respect explicit security denials immediately; never change URL/browser/engine to bypass them.

If screenshot saving fails after one supported retry, record the actual limitation and two observed desktop/mobile states with tool references. Never fabricate observations. This does not waive interaction checks.

## Browser unavailable: preview response

If automated local-page inspection is genuinely unavailable, finish automatic checks and record in `browser-qa.json`:

```json
{
  "validation_mode": "unavailable",
  "status": "pending",
  "build_fingerprint": "<from _manual_qa.build_fingerprint(workbench)>",
  "host_limitation": {
    "reason": "<actual capability limitation or denial>",
    "tool_reference": "<actual tool result identifier>",
    "checked_at": "<observation timestamp>"
  }
}
```

Rerun the controller after recording this evidence. If all automatic gates pass it permits a review response, never a browser pass. For a new guide provide a neutral “查看手册” link; for an update say “已更新，刷新页面看看效果，有不合适的地方告诉我。” No extra workflow-consent question is needed merely to show the page. Keep unobserved QA pending, disclose concrete defects affecting use, and answer verification questions honestly. Do not repeat browser attempts after a known denial. Changed build bytes invalidate this review record.

For a current-build unavailable record (or explicitly authorized pending human QA below), run `check_handoff.py` after automatic gates pass. It creates or reuses the self-contained HTML for review without upgrading QA or handoff status. If export fails, repair that error first; do not attach the workbench index.html alone. Ordinary missing QA, stale records and failed automatic gates do not qualify for this exception.

## User-selected human QA (standard)

For explicit human interaction QA, record `validation_mode: manual_representative`, `user_authorized: true`, `status: pending`, and `build_fingerprint` from `_manual_qa.build_fingerprint(workbench)`. Ask once for actual desktop cover/contents and mobile cover/sight layout, no overflow or obstructed controls, disclosure open/close, Trip Mode open/close, and day switching with corresponding stops changing. Screenshots are optional and do not prove interaction.

Only after actual feedback set `status: passed` and populate `human_confirmation` with `checked_at`, `message_reference` and the user's quoted `user_statement`. Under `checks`, record `desktop_layout`, `mobile_layout`, `no_horizontal_overflow`, `disclosures`, `trip_mode`, `trip_day_switch`; each needs `passed: true` and a specific reported `note`. Failed/untested checks remain false/pending; repair known defects before renewed review. Do not construct evidence from consent, sample text or code inspection.

Keep the fingerprint of the tested version; never refresh it to disguise a later edit. After feedback run `check_handoff.py` for full release. Human evidence stays labeled human-confirmed. Report waiting time separately if reporting duration.

## Incremental repair and maintenance

Fix failures in owning data/assets/code, then recheck affected behavior. Copy-only edits reuse valid evidence for unchanged interactions according to the incremental plan. Do not rerun a destination-wide search or every UI interaction for a local copy change. Known unrelated or broken images remain failures regardless of dimensions; standard small images are warnings under the image policy.

For a material Skill/code change, run `audit_skill_consistency.py`, affected regression tests and a non-Bali cold-start fixture. Check generated task requirements as well as validator behavior. Shared UI/runtime changes additionally require the relevant browser matrix; instruction/controller-only maintenance does not require rebuilding a real destination.

Daily `quick_forward_test.py` inspects the current public files read-only; it does not copy research/QA/history folders or rerun the Skill installer regression. For installer or release-contract maintenance, use `quick_forward_test.py --skill-self-test` (also covered by `test_quick_forward_scope.py`). Product invariants, real Node syntax checks and profile-derived runtime consistency remain daily checks.

## Semantic limits of automatic gates

A passing structural/media preflight does not certify image subjects, source truth, coordinate precision or real browser behavior. Inspect the contact sheet for wrong subjects and brand artwork misclassified as photos; repair declarations from observed sources. Never manufacture evidence flags, padding copy, category labels or ratings to obtain a pass. Conditional and overnight schedule wording requires route review because the numeric overlap check handles only explicit same-day clock times.


### Paired delivery
After preview QA, check_handoff.py exports a standalone offline HTML and returns offline_qa_required. It must not print HANDOFF ALLOWED until the actual export has passed the checks below. Use the exported self-contained HTML as the primary open/download link. A separate webpage link is optional and must be verified with its complete resource tree. Never attach the workbench index.html alone; it depends on sibling JS/CSS/media. Test the exported HTML itself in the supported browser, including chapter navigation, disclosure, Trip Mode and day switching. A host preview may disable JavaScript even for self-contained files: report the observed limitation and provide the HTML for a normal browser; do not promise universal preview compatibility or assert 404s without observed evidence. Tell the user: “双击离线 HTML 即可在本地离线打开，无需解压；导航外链与共享功能需要联网。” No ZIP for the handbook. The installable Skill may still be distributed as ZIP.



Priority labels and single-image layout follow [the UI contract](product-ui-contract.md); verify the affected presentation within the applicable QA sample, not a separate repeated matrix.

## Export acceptance record

`offline-export.json` is generated by the packer and records the artifact path, SHA-256 and build fingerprint. Test that exact artifact in the authorized browser. A loopback preview of the exported HTML is acceptable when the host technically lacks file support; record the actual tested URL and do not claim file-scheme or disconnected testing. Never use another URL or browser to work around an explicit policy denial.

Write `offline-qa.json` with `validation_mode: browser`, `status: passed`, `export_sha256` copied from the current receipt, `tested_url`, `checked_at`, and `tool_reference`. In `checks`, provide `chapter_navigation`, `disclosures`, `trip_mode`, `trip_day_switch`, and `map_viewer`; each is `{passed: true, note: <actual observation>}`. The map check includes fit/zoom, internal scrolling and closing. For an explicitly online map build, record why the local image viewer is not applicable and test its actual map interface instead. Never prefill passing records. Changed source or artifact bytes invalidate acceptance. Rerun `check_handoff.py`; it reuses the tested artifact.

If an actual host limitation prevents export QA, keep `status: pending`, set `validation_mode: unavailable`, bind `export_sha256`, and supply `host_limitation.reason`, `tool_reference`, and `checked_at`. This permits a clearly labeled preview response, not full completion. Do not rerun research or ask for workflow approval.
