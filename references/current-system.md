# Current handbook system · 2026-09-12

Default new-build maps: [real map screenshots](screenshot-map-workflow.md), with reviewed local captures for every day. The compiler selects `map_delivery: screenshots`; the handoff gate rejects missing captures. Interactive online maps require an explicit user request recorded in `online_map_user_statement` and `map_delivery: online`. Exact snapshot restoration is unchanged.

Use this reference for restoring/updating the approved handbook, preserving its UI, route maps, or installing the ledger/cloud runtime. This is a product baseline, not another destination-research pass.

## Two different operations

**Public component restore:** the bundled product is a neutral UI scaffold, without personal orders, venue photos, font binaries or offline tiles. Restoring it previews components; a complete handbook must use the research/profile renderer.

**Another destination:** use the research/profile pipeline for facts, then `render_profile.py <profile> <workbench>`. It selects `current-system` by default and invokes the official installer, bindings and renderer with one consistent UI selection. `_current_system_adapter.py` derives destination runtime content from the profile; reference-only content scripts are disabled. `assets/canonical/product` is used only when the profile explicitly selects `ui_system: canonical`. Reuse the shared ledger components and the screenshot map workflow; configure names, dates, language and storage namespace per trip. Do not use an unadapted restore as a new-destination result. Ordinary content/asset gates and applicable interaction QA remain required.

## Restore commands

```text
python scripts/restore_handbook_system.py <output>
python scripts/verify_handbook_system.py <output>
```

Use a verified Python binary on Windows. `--replace-owned` explicitly overwrites bundled files only; it never deletes unrelated files or local browser storage. Updating the Skill is not permission to publish a site, delete old sites, create a database, upload local user records, or change account settings. A prior one-off request to delete six websites must not become a reusable automation.

## Interface contract

Keep all eight content chapters, plus a single flight-and-stay disclosure which opens and closes. Navigation says 景点 rather than invented chapter synonyms. Entry disclosures use readable text on a paper surface; do not restore image-background text overlays, oversized blank shortcut cards or duplicate feature navigation. Venue photos remain inside actual venue cards.

Keep the same phone-oriented Trip Mode on desktop and mobile: itinerary, map, photography/outfits and ledger tabs. Keep the day strip visible in every tab; switching dates preserves the active tab. Preserve normal navigation, adjustment requests, checklist persistence and locally uploaded reference photos. Do not append a second Trip Mode.

Ledger baseline: system sans-serif, 24px main heading, 16px section headings, 13–14px content, 12px field labels, 16px input text, 44px input/select heights, 40px minimum compact action buttons, 12px form gaps, 16px section spacing, 10px control radius. Keep common left edges; numbers use tabular digits and right alignment. Member checkbox hit areas contain a 16px native checkbox, never an absolutely positioned control. Local/cloud use the same CSS and components. Test narrow controls with actual Chinese labels, not just empty boxes.

## Content and consistency contract

- One approved itinerary is the source for main route, Mini Route, Trip Mode, scheduled sight badges, restaurant plan, shopping plan, reservations and evening confirmations. Retain explicit user decisions; do not silently delete stops or leave “not scheduled” on an included attraction.
- Preserve route-specific shopping entries. Do not fall back to “今天不特意安排购物” when scheduled shops exist.
- Food summary states meal type, cuisine, a brief useful introduction and price basis (per person/two people; currency; estimate/verified, tax if known). Do not invent current prices.
- Reservation cards show priority: 必须 → 建议 → 随缘, preserving authored order inside each level. Do not add a sort-mode switch. Compact checkbox and disclosure live in the same row. A tick reflects user handling, not proof of merchant confirmation. Preserve explicit paid bookings as source facts.
- Travel tips also use 必须/建议/随缘; apply priority to relevant records, not blanket danger labels. Add specific useful advice instead of repeating generic travel phrases.
- Vocabulary/phrases themselves are the speech control. No separate full-width “朗读” button per word; accessible name, stop/replay and device-voice availability feedback remain.
- Photo advice names the actual scene, lighting direction/time window, camera position/composition, lens/focal length and actionable settings where relevant. A7C II guidance is an equipment-specific option, not a default camera owned by every user. Never silently assume a lens.

## Maps

New builds follow [screenshot map workflow](screenshot-map-workflow.md). Do not confuse its actual browser captures with the legacy offline tools below. The following SVG/tile instructions apply only to explicit offline-map work. The public component scaffold has no bundled map tiles. Offline work requires its own licensed cache.

`node scripts/build_system_routes.cjs days.json output tiles-directory [vector.json]` accepts `{days:[{theme,stops:[{name,stopIndex,routeOrder,latitude,longitude}]}]}` or a day array. Tiles are local PNGs at `z/x/y.png`, supplied from an authorized source that permits the intended caching/use; optional vector geometry uses `{ways:[{p:[[lon,lat]],t:{...OSM tags}}]}`. This tool does not scrape Maps or download an entire region. Missing coordinates/tiles are explicit errors, never substituted hotel coordinates, previous-stop coordinates or broken-image icons.

Route links follow the itinerary array exactly, with original indices. Start and return stay separate even at one coordinate. Marker geometry remains geographic; label positions may move, connected with leader lines. One small direction arrow per segment; 4px route stroke at a 600-unit map width. Labels are real text, medium weight, complete and wrapped, never raster text or ellipsis. Dense days split into overlapping map panels at five stops; the shared boundary retains the same itinerary number. All panels belong to the same day; splitting must not imply new times or reorder the trip. Broad flight legs need a separately labelled geographic overview, not an invented street itinerary.

Embed raster bytes into the SVG before release. External SVG `<image href=https:...>` often fails when the SVG is displayed through `<img>` or file://. A successful tile download must be an actual image; HTTP errors and blank placeholders are not usable backgrounds. Preserve source attribution/licensing. Inspect one map plus any changed/flagged panels, not all photos repeatedly. Layout candidate scoring cannot guarantee every pathological name fits: unresolved collisions require label relocation/panel splitting, never hiding text. Keep a regression case for repeated start/end, long names and 3/5/8 stops.

## Accounting and shared persistence

Members have stable IDs, editable names, optional cropped/compressed 128px JPEG avatars and versions; maximum 12. Transactions reference IDs, not display names. Select payer and participants; equal split is the supported mode. Use integer hundredths, deterministic remainder assignment, separate currencies and net settlement suggestions. Do not imply support for custom ratios, automatic FX, bank payments or an AI model.

Settlement registration is bookkeeping only after actual payment. It reduces balances, is excluded from spending totals and can be reversed. Same-snapshot repayments use deterministic IDs to avoid duplicate registration. Expense updates use version checks; conflicts keep user input and require an explicit decision. Never use whole-array last-write-wins for cloud expenses. Poll only active shared surfaces every 5 seconds; saving updates the current display immediately. Avoid a MutationObserver that modifies its own observed subtree unconditionally.

Local mode stores members/avatars/transactions and reference photos locally, with persistence and storage-failure feedback. The reference's old transactions remain; ambiguous “共同” payers require confirmation before settlement. Generic runtime namespaces storage per handbook and must not import unrelated Bali records. Cloud mode shares members, avatars, expenses, repayments, reservation checks, saved attachments and photography reference samples through the bound attachment store. Personal packing and custom route edits remain local. Do not promise all browser state is shared.

## Cloud package

```text
python scripts/prepare_shared_cloud.py <restored-handbook> <empty-cloud-folder> --name <worker-name> --database-id <actual-id> --database-name <actual-name> --uploads-kv-id <actual-kv-id> --access-mode <open|code>
```

This prepares files only: Worker, public assets, one-time schema, repeat-safe reservation seed and shared link/image/PDF storage support, including Trip Mode photography reference samples. The authorized deployment flow creates a dedicated KV namespace and passes its real ID through `--uploads-kv-id`. Each image/PDF is limited to 20 MB; metadata stays in D1 and file bytes stay in KV. It does not deploy, choose an account or create resources. Use the Cloudflare skill/current official documentation for actual provisioning, quotas and deployment. Never embed the original user's account ID, database ID, workers.dev hostname, tokens or deletion commands in a new project.

### Cloud access choice

部署云端前，若本次会话尚未明确访问方式，必须多问一句：「要不要设置访问码来保护隐私？不设置的话，拿到链接的人可能查看共享的行程、成员、账目和附件。」等待用户选择后再发布；部署授权本身不等于同意公开访问。已明确选择的沿用，不重复询问。本地生成不触发此问题。

The bundled reference edition is **open/免码**, reflecting an earlier reference choice only; it is not a default authorization for a new user. Pass the user's explicit choice through `--access-mode`. For `code`, set `ACCESS_CODE` with Wrangler or the deployment platform's secret mechanism before deployment; never put it in `wrangler.jsonc`, public assets, URLs, logs or the repository.

Code mode defaults to the bundled responsive in-page access-code form on both phones and computers. It asks only for the code, validates it server-side, then issues an `HttpOnly; Secure; SameSite=Lax` session cookie. Do not use HTTP Basic or another browser-native username/password dialog unless the user explicitly requests that mechanism. The protection must cover the handbook, shared read/write APIs and attachment bytes; a client-only overlay is insufficient. Verify direct navigation shows the form, missing/wrong codes are denied, the correct code opens the guide, refresh preserves the authorized session, and a separate unauthenticated session still cannot read an API or attachment. Test at mobile 390px and desktop width. If protection is not ready, keep deployment pending rather than silently publishing open access. If the user explicitly chooses open mode, preserve it together with same-origin write checks and server validation.

## Verification and maintenance

For an authorized cloud delivery, verify the deployed guide in two independent browser sessions: add a PDF, an image and a web link in session A and open them in B; rename/delete the attachments and verify B reflects the change. Add a member and an expense with selected participants, edit it, record a repayment and verify amounts/settlement in B after synchronization or refresh. Verify reload persistence and clean up only the test records created for this check. Both file bytes and metadata must be shared; local Data URLs or a static-only deployment do not satisfy this contract. Report unverified cloud checks honestly. “文档” currently means PDF (not arbitrary Office files); each uploaded PDF/image is limited to 20 MB.

Observed baseline results and executable test names are recorded in [current-system-verification.md](current-system-verification.md). These results distinguish browser behavior from static verification and do not substitute for checks after future edits.

Exact restore: verify SHA-256 bundle parity, dependency existence, SVG embedded backgrounds and no secret/deployment files; then exercise the actual restored page. Test disclosures open/close, Trip Mode/day switch, ledger member add/edit/avatar, selected participants, transaction edit/delete, settlement/reversal, reload persistence, word speech capability feedback and mobile 320/390 plus desktop width. Missing browser speech voices are a platform limitation, not false playback evidence. Cloud changes additionally need independent browser sessions, anonymous behavior appropriate to access mode, conflict detection and no leaked test records. Use local fixtures for tests by default.

When shared code changes, update product/runtime/cloud copies together, regenerate manifest hashes, restore into an empty directory and run the affected behavior checks. Do not keep editing only a screenshot, detached demo, deployed file or this prose. Do not claim exhaustive production QA from a manifest check. Skill maintenance does not rerun destination research or redeploy user websites.

To deliver an installable Skill, run `python scripts/package_skill.py <new-output.zip>`. It verifies bundle checksums and ZIP integrity and omits generated caches. A checksum mismatch is a source-package defect: fix the reviewed source and regenerate its manifest before packaging, never ask users to delete their handbooks. Use `--replace-owned` only for an intended update of a known restored output; otherwise choose a new output folder.
