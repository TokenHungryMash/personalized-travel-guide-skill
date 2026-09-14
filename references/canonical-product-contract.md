# Public handbook template contract

Current-system maintenance/restoration uses [current-system.md](current-system.md) and the bundled executable snapshot. The older canonical/profile contracts below remain for compatibility and content gates; they do not supersede current UI, map, ledger or cloud behavior.

Use `assets/canonical/product/` as the executable page scaffold. Its Bali content is public demonstration material; transport and accommodation entries are deliberately non-booking placeholders. Every destination build must replace all destination-bearing text, links, images and runtime data from a validated destination profile.

## Required result

Preserve the responsive editorial layout and these user-facing capabilities:

- cover, contents and eight ordered chapters;
- itinerary disclosures with morning, afternoon and evening detail;
- Mini Routes and map actions;
- sights, shopping, experiences, food, preparation, language and local notes;
- Trip Mode;
- the basic Adjust Itinerary flow for adding, deleting, editing and reordering stops, then copying a text request;
- theme selection, checklists, galleries and mobile navigation.

The current canonical edition includes local reference-photo upload inside Trip Mode, with large previews, full-screen viewing and browser-local persistence. This latest runtime is authoritative; do not replace it with an older private Trip Mode implementation.

Trip Mode uses the same narrow phone-first interface on desktop and mobile. Each day contains one collapsed, offline hand-drawn route generated from verified coordinates; it does not download map tiles at runtime. Google and Apple are the only navigation choices, with Google as the first-use default. Stop cards retain exact-place Xiaohongshu actions, practical visit notes and explicit time/queue fallbacks. No legacy destination constants or parallel Trip Mode implementation may remain.

## Adaptation rules

Run the official installer and renderer. Replace registered content through the destination profile and render bindings; do not build a second page architecture or perform a partial destination-name replacement.

Keep shared geometry and interaction files unchanged. Destination runtime files may replace destination names, day labels, storage namespaces and route-specific data while preserving their public behavior. Do not leave demo hotels, transport, dates, map links or destination terms in a completed export.

Google ratings are a normal research target but remain optional. Open one ordinary exact-place result first; if it opens, query every rating-bearing sight and restaurant and attempt to capture both score and review count. When one venue cannot open, retry that venue once through a shorter exact query or alternate canonical Google entry, then continue to a different real venue. Stop only after two different venues fail to open consecutively; any opened venue resets the count, and collected ratings are retained. An opened venue page without a reliable score is skipped individually and does not count as an access failure. Display a verified score even when its review count is unavailable, omitting only the count. A focused repair pass may fill ratings missed by an earlier erroneous stop-loss without rebuilding the handbook. Never invent a score or review count.

## Page order

1. Editorial cover and contents.
2. Transport and accommodation status.
3. Itinerary.
4. Sights.
5. Shopping and souvenirs.
6. Destination-specific experiences.
7. Food.
8. Before departure.
9. Language companion.
10. Local notes.

## Release checks

Verify both `1440×900` and `390×844` layouts. Check the cover, navigation, one expanded itinerary day and Mini Route, restaurant cards, language disclosures, local notes, Trip Mode, basic itinerary adjustment and every selectable theme. Respect reduced-motion preferences and maintain readable contrast and touch targets.

Run the strict product audit after rendering. A raw installed scaffold or an export containing demo data is not a finished handbook.
