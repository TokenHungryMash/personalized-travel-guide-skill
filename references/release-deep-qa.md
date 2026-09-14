# Deep and legacy QA details



Ordinary destination builds use only the representative scope in release-validation.md: two viewport screenshots (or its documented observation fallback), one disclosure and Trip Mode opened/closed. The four-screenshot matrix below applies to `validation_mode: publication_depth` for shared UI/runtime changes, not ordinary destination content. Do not expand routine QA merely because this reference was opened.

## Publication-depth browser matrix


Inspect at approximately 1440×900 and 390×844. Test these states, not only the closed page:

1. cover and each of six themes;
   - phase/section headlines describe the target trip and appear only when the trip has a real phase split;
   - unresolved transport shows exactly two generic cards; confirmed transfers show exactly the supplied legs; headline and fine print agree with them;
2. editorial contents plus desktop rail/mobile menu;
   - opening the mobile menu and clicking any chapter link closes the panel, backdrop and expanded trigger state before scrolling;
   - verify that the target chapter actually reaches the viewport, not only that `location.hash` changes. If the automation click suppresses native anchor scrolling, retry with the DOM element's native `.click()` and inspect the target bounding rectangle. A manual/controlled scroll may be used to inspect the target layout, but it does not by itself prove anchor navigation. Record a harness limitation separately from a page-runtime failure.
3. the selected hotel gallery with arrows, swipe and count; only `gallery_featured` sights require a second image and gallery controls;
4. a closed and expanded itinerary day;
5. one short and one long Mini Route;
6. Trip Mode on arrival, full and departure days;
   - hotels and lodging properties have no Xiaohongshu action;
   - every other stop, including airports and terminals, has a Xiaohongshu action whose query is exactly the place name, without automatically appending “出片”;
7. Adjust Itinerary: rename theme, change time, reorder, add, delete, undo, restore and package export;
8. signature experience, shopping and souvenir disclosures;
   - every disclosure heading accurately names the records inside it; no inherited Bali taxonomy or empty destination selector remains;
9. scheduled and optional sights, with gallery interaction only on `gallery_featured` records;
10. essential/reservation checklists and persistence;
    - no reference-destination excursion, platform, packing assumption or venue remains;
11. both restaurant families, the four-snack section and representative actions; every restaurant card retains its required exact-place image;
    - menu primer reflects the target destination's real ordering/menu conventions rather than Bali copy;
12. keyword and phrase groups in closed/open states;
   - every group heading remains plain Chinese without a redundant language suffix; the edition is labelled once as `英语备用`; its cards contain English text followed by Chinese meaning; every group has at least five entries;
13. local-note folds;
   - five folds with four titled practical topics each, covering weather, culture/etiquette, transport, safety and payment;
14. mobile bottom/floating controls without overlap.

Capture evidence while testing. Save at least these four screenshots under `qa-evidence/` until handoff: desktop cover, mobile cover, desktop contents with rail, and one mobile sight gallery with controls/count visible. Also capture any state that failed once after it is fixed. Do not claim browser QA from source inspection alone.

For the cover, overlay a temporary safe-zone guide or inspect bounding boxes and verify that kicker, title, lede/tags and bottom metadata are all inside the image composition at both viewports. The cover fails when the image ends before the title block, text is pushed into a separate paper region, supporting metadata falls below the fold, or any text/background pair is visibly low contrast.

For navigation, inspect computed bounding rectangles for every number and label. Any intersection between their rectangles is failure. At wide desktop the rail must retain the canonical column width and row height; at mobile the desktop rail must have no visible box. Do not accept a rail merely because all eight strings exist in the DOM.

For every gallery family, click next twice, click previous once, swipe on mobile and verify that the image transform/source and live count change together. Static three-image markup is not a working gallery.

Desktop automation that emits mouse drag events does not prove touch swipe. When the browser harness cannot synthesize real touch/pointer events, record swipe as unverified and test arrows plus live count as a separate fallback; do not mark the touch row passed from mouse dragging alone.

Use the host's normal persistent browser session when available. If a platform's browser CLI destroys its session between commands, do not keep reinstalling or repeating the same navigation. Make one bounded fallback to a single one-shot browser script that performs the representative matrix in one process. If the file surface is technically unsupported and loopback preview is authorized, use the preview server. A security denial is not permission to switch surfaces. These are platform-neutral fallbacks; they must not add a manual step to hosts whose browser tooling already works.

Treat the following screenshot signatures as immediate hard failures, even if content/count audits pass:

- the cover photograph occupies only a short strip while title, description, tags, date or metadata sit in a separate white/paper block below it;
- any cover text is outside the image composition, clipped, pale-on-pale or below the first viewport;
- desktop navigation numbers visually intersect labels, labels wrap into the number track, or the rail is narrower than the canonical wide-desktop rail;
- a sight displays multiple gallery images simultaneously in separated positions, or leaves a large blank canvas around them;
- a chapter loses the component family defined by the selected current-system or explicit legacy baseline.
- a target-destination itinerary reuses Bali narrative semantics such as forest/sea phase copy, fixed Bali day themes, Berawa, yoga/SPA categories unrelated to their cards, Indonesian menu guidance or Bali-only reservation items;
- transport cards contain invented or reference flights/airports when the user did not provide booked legs; incomplete transport must remain visibly marked 待确认;
- an unresolved transport block contains more than two cards, concrete times/airports, a transfer duration or a hotel departure recommendation;
- a shopping, experience or food disclosure has a heading but no destination record inside it;
- any navigation surface abbreviates or renames one of the eight locked Chinese product labels;
- an itinerary day is not a canonical `details.day`, lacks the same summary/plus control, omits an 上午/下午/晚上 row, or replaces the Bali dark journey surface with an unrelated pale card;
- the sights grid is no longer wrapped by the canonical `mobile-section-fold`, even when all sight cards exist.
- For explicit legacy canonical parity only: any embedded `<style>` block differs from the canonical product or adds late component overrides; destination styling must use only the documented semantic token and cover-crop layers.
- For explicit legacy canonical parity only: the candidate loads any CSS or JavaScript not loaded by the canonical Bali product, changes their load order, modifies a byte-locked file, or changes more than quoted destination literals in `better-interface.css`;
- a destination-bearing runtime still contains canonical Bali destinations/venues or changes canonical DOM class names, controls or interaction hooks while replacing its data;
- the candidate was produced by a destination-specific page-builder script, an unrestricted whole-document serializer, or copied from an older export that already failed the current audit. The official byte-safe renderer and contract-compliant destination-neutral adapters are allowed.

For the desktop rail, collect `getBoundingClientRect()` for the rail and every link's number and label at `1440×900`. Fail if the rail is materially narrower than `188px`, a row is below `55px`, number/label rectangles intersect, labels clip or wrap, or the rail appears in normal document flow. For the cover, collect image/header/copy rectangles and fail unless the image covers the header and every copy rectangle is contained by the header. These are required browser assertions, not optional visual notes.

Before visual QA, inspect the export directory itself: every raster must appear in `asset-manifest.json`, every manifest entry must identify a destination-profile `place_id`, and no canonical Bali raster or venue fallback may remain in JavaScript. Then visually compare the subject of every hotel, shopping, experience and food image with its card title; file existence alone is not a pass.

Use check_handoff.py for the final strict audit and forward test before presenting a finished version; do not duplicate those commands. If `ADAPTATION_REQUIRED.json` exists or the audit reports any failure, keep it as an unfinished workbench, correct the dataset, rerun the audit and only then perform browser QA.

Do not confuse “do not present the workbench” with “stop working”. The required response to this marker or any correctable audit failure is to continue editing in the same task. The agent should report progress only while continuing tool work, not as a final answer. No user “继续” message is required.

## Canonical parity matrix

For current-system builds compare against `assets/current-system/product/index.html`; for explicit legacy tasks use `assets/canonical/product/index.html`. Compare at the same
viewport. Verify the following as product parity, not as a loose resemblance:

| Surface | Required state |
| --- | --- |
| contents | open editorial 01–08 index, correct labels/order, no card-wall substitute |
| desktop rail | fixed left column only at wide desktop; no overlap, wrapping or top-page fallback |
| mobile directory | compact trigger and sheet; no desktop rail and no clipped labels |
| hotel | unnumbered disclosure immediately before itinerary; the selected property has 2 distinct verified images, arrows, swipe and count |
| itinerary | one day disclosure and one Mini Route per day; arrival, transfer and departure included |
| sights | one verified image by default; only `gallery_featured` records have 2 distinct images and gallery controls; all retain scheduled/optional marker, duration, hours/closure, map and official link; a verified Google score is optional |
| shopping | exact-place cards plus souvenir cards; text-only souvenirs stay in the same disclosure without empty image containers |
| experiences | destination-specific exact-place cards with images, hours, hotel distance and map/course action |
| food | exactly four local snacks, six or more dedicated restaurants and two to four dependable local-chain fallbacks; restaurants retain images, price, cuisine, hours and day/route context; optional verified Google ratings always show the score and add review count when reliably available |
| preparation | two top-level checklist families with persistent progress |
| language | separate keyword and phrase systems, each with five or more useful folds and five or more entries per fold |
| local notes | exactly five substantial disclosures—weather, culture/etiquette, transport, safety and payment—with four topics each |

## Visual regression blockers

Reject the export immediately when any of these appears in any theme or viewport:

- body copy or control text is pale-on-pale, dark-on-dark, translucent or hidden by inheritance;
- Mini Route eyebrow/day theme and “查看路线/收起路线” controls are lower than normal-text contrast or inherit white/translucent text on a pale route surface;
- a destination theme is implemented with `filter`, `opacity` or a colored overlay over another theme instead of explicit semantic tokens;
- normal content uses `writing-mode: vertical-*`, one-character columns, `word-break: break-all`, or a width that collapses ordinary sentences;
- a horizontal place/experience card is nested inside a multi-column grid whose remaining copy column becomes narrower than readable text; test the longest Latin and Chinese venue names, not only short examples;
- navigation numbers overlap labels, labels wrap one character per line, the wide rail appears at the top of the document, or mobile and desktop navigation are visible together;
- an expanded disclosure creates unexplained blank space, clips its content, loses its close control, or cannot be collapsed without scrolling back to the start;
- a gallery shows only its first image, repeats one image, has nonfunctional controls, or fails swipe/count updates;
- any required image is broken, unrelated to the named place, overexposed/unreadable, or missing its manifest record;
- modules 03–08 degrade into plain text or lose the canonical card/disclosure family;
- the cover photograph and cover copy render as vertically separate blocks, the destination title is outside the canonical safe zone, or the chosen image palette and semantic theme visibly disagree;
- a sight presents three images simultaneously as a collage/scattered masonry field instead of the canonical single-viewport sliding gallery;
- any horizontal overflow exists at 390 px, or any control/content is unreachable at 200% zoom.

Inspect closed and expanded states. A closed-only screenshot is not evidence that a disclosure works.
