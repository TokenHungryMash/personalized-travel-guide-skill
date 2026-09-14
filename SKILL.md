---
name: build-personalized-travel-guide-open-source
description: 生成、更新或还原个性化旅行手册网页，含八模块、旅行模式与记账；支持按需 Cloudflare 共享部署。
---

# Personalized travel handbook

Build destination-specific content in the user’s workbench using the bundled `assets/current-system/product/` template. Do not write destination facts into the installed Skill or its template. Preserve the approved responsive interface, eight chapters, Mini Routes, Trip Mode, itinerary adjustment and saved state. The public template is an empty component scaffold, never evidence for a destination. Restoring it previews components; it is not a completed handbook.

## 对话语言

面向中文用户，安装说明、进度更新、问题说明、问卷交付和最终回复使用中文；代码、命令、路径及专有名词保留原样。用户明确要求其他语言时遵从用户。此要求约束对外回复，不声称控制宿主内部思考语言。

## Installation and questionnaire entry

After an authorized installation or when asked to start/open the questionnaire, expose `assets/intake-questionnaire/index.html` immediately as an actual clickable file. If the host cannot link installed assets, copy this self-contained file to the user workspace and attach/link that copy. A statement that installation succeeded or an instruction to invoke the Skill again is not questionnaire delivery. Opening the file does not require Python, Pillow, Node, restoration or tests. Honor host security review; do not add full development tests to installation. Never claim the browser opened successfully without an observed result.

## Choose the task

Read only the applicable route and the references needed for its current stage.

| Request | Route |
| --- | --- |
| New handbook | Follow the three gates below in order. Read [Intake](references/first-use-intake.md), then [itinerary discussion](references/itinerary-discussion.md). |
| Existing content change | Edit the owning research packs; use [rendering](references/rendering-and-assets.md) and affected [release checks](references/release-validation.md). Preserve unchanged research and valid evidence. |
| Exact restoration | [Current system](references/current-system.md): restore and verify the bundled snapshot. |
| UI/runtime repair or redesign | [Maintenance](references/internal-design-and-maintenance.md) and the affected section of [UI contract](references/product-ui-contract.md). |
| Map change | For new handbook maps require [real map screenshots](references/screenshot-map-workflow.md). If the original capture fails after bounded authorized attempts, use [offline overview fallback](references/offline-map-fallback.md); never offer online maps as recovery. Preserve historical online-guide compatibility only. Licensed local raster-cache requests use [offline preview](references/offline-map-preview.md). Exact restores retain embedded maps. |
| Authorized shared deployment | [Current system](references/current-system.md). Preserve the approved open/免码 sharing behavior and verify the changed cloud functions. |
| Skill diagnosis or maintenance | Inspect relevant instructions/scripts and validate the changed contracts. Do not start destination research or regenerate a handbook. |

## Boundaries

- **New-handbook gate:** (1) collect the questionnaire output or an equivalent written brief; (2) show one compact daily itinerary proposal; (3) wait for the user to approve that displayed proposal. Do not research the full handbook, create a production workbench, download images, build maps or render HTML before gate 3. `按默认` completes intake only. The sole exception is an explicit instruction to skip discussion and generate directly.
- A complete brief starts a compact itinerary proposal. Reuse approval already given in the current conversation. `不要讨论，直接生成` waives discussion; `按默认` waives the questionnaire, not route review. Record the actual approval/waiver in `itinerary-outline.md` when creating the workbench.
- Use the current brief; reuse earlier destinations or personal records only when requested. Missing optional preferences use defaults. Transport/stays remain pending unless the user supplies bookings or a complete `trip-decisions.json`; this product does not research or compare flight/hotel options.
- Resolve scripts and references from this Skill root. A persisted workbench from another root must resume with its original scripts; do not mix versions. Overseas destinations do not select the legacy international Skill. `ui_system: canonical` is for explicit legacy compatibility only.
- Never invent venues, coordinates, hours, prices, ratings, source access or QA evidence. Verify changing facts or state uncertainty. Preserve asset provenance and repair actual failures rather than manufacturing passing records.
- Before cloud deployment, ask once whether the user wants an access code to protect private information, unless their access-mode choice is already explicit in this conversation. Explain that anyone with an open link may access shared content; do not interpret deployment approval as approval for open access. When code protection is chosen, default to the bundled responsive access-code page plus a secure server session on both phones and computers; require no username and never use the browser-native HTTP Basic prompt unless the user explicitly requests it. Follow [cloud access choice](references/current-system.md) and wait for the choice before publishing.
- Deployment and shared uploads follow existing user authorization. Communicate material limitations honestly; local/cloud data boundaries and the once-only deployment offer are in [intake](references/first-use-intake.md).

## Production after route approval

Default to one agent for research, itinerary decisions, authoring and verification. Do not spawn subagents unless the user explicitly requests them for this task; a request to optimize, speed up or use defaults is not permission. Concurrent tool calls and bounded asset downloads within that one agent remain allowed. Use [standard fast path](references/production-flow.md) and [source ownership](references/single-agent-production.md). Read [delegation](references/fast-build-orchestration.md) only after an explicit delegation request.

Use a verified Python interpreter (on Windows see [runner setup](references/runner-command-contract.md)). Preserve the current approved inputs with `--brief-file` as described in the production flow so initialization does not drop interests, travelers or constraints. The commands below are relative to this Skill root:

```text
python scripts/start_build.py <workbench> --brief-file <current-brief.json> --destination <name> --country <country> --start-date YYYY-MM-DD --days N --itinerary-approved --user-statement "<verbatim user approval>"
python scripts/advance_build.py <workbench>
```

The controller supplies the next stage and current pack task. Use [pipeline](references/research-and-profile-pipeline.md) for pack ownership/dependencies, [content model](references/content-model.md) for module content, [selection](references/itinerary-selection-logic.md) for route decisions, and [data shapes](references/research-data-shapes.md) for unfamiliar fields. Read the reference needed for the current decision, not this entire list.

Resolve place identity, coordinates, visible rating and image feasibility in the same visit under [Google lookup](references/google-place-lookup.md). Use [image policy](references/image-and-source-policy.md) for asset acceptance. Reuse facts across chapters and Trip Mode; do not create separate enrichment passes.

The compiled profile is the content source. Install/render through [official rendering](references/rendering-and-assets.md); repair owning packs rather than final HTML. Keep the product inventory and UI implemented by the bundle; authoring details live in the content model, not a second component-building task.

Offline maps default to exactly one full-day overview per itinerary day, preserving image resolution, full place labels and external navigation links. Do not automatically add local-area captures. Attempt the original street-map capture first; only evidenced failure permits the geographic offline-overview fallback. No online-map fallback.

## Completion and recovery

[Release validation](references/release-validation.md) owns QA scope and the response states. Run `check_handoff.py <workbench>` after source, render and required QA work; it already runs the appropriate strict audit and forward test.

- **In progress:** initialization, regression-test success and a completed research batch are intermediate results, not a stopping point. When `continuation_required: true` and `user_input_required: false`, send progress in commentary and execute the next action in the same turn; do not end with a final response or ask the user to say “继续”. Skill scripts report this condition but cannot enforce a host-level stop hook. Follow the controller's next action and repair named failures. A patch mismatch, bad JSON or failed optional source is a reason for a focused correction, not a request for the user to say “继续”.
- **Waiting for review:** only after automatic gates pass, a recorded browser limitation or authorized pending human QA may allow a preview response. `final_response_allowed` permits that response; `handoff_allowed` remains false and QA stays pending.
- **Complete:** claim full completion only after `HANDOFF ALLOWED`. Do not repeat passing checks without changed inputs or an unresolved concern.

手册完成后，按 [intake](references/first-use-intake.md) 询问一次：“手册已完成。需要我帮你上传到云端，让同行人共享 PDF 文档、图片、链接和记账吗？”用户已授权部署时直接继续，不重复询问；未同意时保留本地版。云端交付必须包含附件文件与元数据、成员、账目、分摊及还款的共享，并按 [current system](references/current-system.md) 验证，不能仅上传静态网页便声称共享完成。

Use [fetch recovery](references/fetch-recovery.md) for asset/map failures and [gateway recovery](references/gateway-failure-recovery.md) for platform failures. Stop repeating an unsuccessful method, preserve partial work, and diagnose its cause. A documented external blocker may require user input; workload alone does not.

Skill/code maintenance is complete when the requested rules and their generated tasks agree, affected regression tests and `audit_skill_consistency.py` pass, and remaining limitations are stated. Continue through fixing failures caused by the change; a first patch is not completion. UI/runtime changes additionally use the maintenance QA scope. Do not regenerate a real destination to validate an instruction-only edit.

Use the single [production standard](references/production-standard.md). No edition selection or quality-tier question is needed.


### Paired delivery
Use the self-contained offline HTML as the primary artifact, never the workbench index.html alone or a handbook ZIP. [Release validation](references/release-validation.md#export-acceptance-record) owns export creation, hash-bound acceptance and pending-review exceptions. Tell the user: “双击离线 HTML 即可在本地离线打开，无需解压；导航外链与共享功能需要联网。”



The [UI contract](references/product-ui-contract.md) owns priority labels and single-image layout; apply those existing components without a separate redesign pass.

## Explicit cold starts
When the user explicitly requests 冷启动/不复用/independent rebuild, use `start_build.py <new-empty-workbench> ... --cold-start`. Do not resume any matching old workbench. Reuse Skill code and the empty product template only; reacquire destination facts, images, maps and QA evidence. Do not copy a prior handbook’s research packs, authoring scripts, downloaded media or validation records. Retain prior builds unchanged.
