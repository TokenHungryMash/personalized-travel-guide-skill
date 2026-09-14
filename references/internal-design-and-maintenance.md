# Internal design and maintenance

Current-system maintenance/restoration uses [current-system.md](current-system.md) and the bundled executable snapshot. The older canonical/profile contracts below remain for compatibility and content gates; they do not supersede current UI, map, ledger or cloud behavior.


## Preserve the product, adapt the destination

Keep the eight module roles, DOM hierarchy, responsive geometry, disclosures, galleries, Mini Routes, Trip Mode, Adjust Itinerary, checklist persistence and navigation hooks. Regenerate destination copy, route logic, category names, local systems, links, places and imagery. Omit an unsupported decorative phase rather than leaving an empty heading.

Reject reference-destination semantics even when the pixels match: no inherited Bali phase names, transport assumptions, yoga/SPA taxonomy, menu guidance, reservation copy, place IDs or image fallbacks.

## Destination-derived visual direction

Derive the atmosphere from landscape, climate, architecture, local materials, vegetation or urban light, regional transitions and the user's emotional brief. Express it through semantic tokens rather than destination-specific component CSS:

- `--atmosphere-deep`
- `--atmosphere-mid`
- `--paper`
- `--ink`
- `--muted`
- `--accent-warm`
- `--region-two`

The latest bundled six-theme system remains the runtime authority. A destination chooses the default and optional semantic token values; it does not fork theme geometry, use global filters or overwrite stored user choice.

## Cover and readability

- Current destination builds center each desktop tool's icon and label as one group, with equal horizontal padding and no independent vertical offsets. Cover introduction text keeps no filled capsule or border: use a slightly larger Chinese serif stack, comfortable line height, and a restrained shadow over the image. Preserve the cover gradient for contrast.

- Choose a real destination image with useful negative space for copy and separately verify desktop landscape and mobile portrait crops.
- Keep the image as a real element with `object-fit: cover`; use a mobile crop hook when needed.
- Preload/high-priority only the cover. Lazy-load card imagery.
- Keep copy inside the cover safe zone with readable contrast at approximately 1440x900 and 390x844.
- Body and control text should meet WCAG AA. Dark and paper surfaces use explicit on-dark/on-light token pairs.
- Glass belongs to navigation, controls and selected large surfaces. Do not nest pale translucent reading cards.
- Motion communicates state, uses transform/opacity where practical, remains interruptible and respects `prefers-reduced-motion`.

## Density and route semantics

Let trip length guide reference breadth without reviving obsolete count rules. A relaxed pace reduces scheduled stops, not the usefulness of the reference chapters. Construct each day from coordinates, area clusters, hours, daylight/reservation needs, realistic transfers, meal/rest windows and a weather or energy substitute.

Regional evidence may supplement Google when locally important—such as Naver/Kakao context in South Korea or a locally relevant map/review platform in China—but preserve native scales and source labels. Michelin appears only for an actual listing.

## Maintenance isolation

Historical products, screenshots and comparison fixtures belong under internal QA or test-fixture directories and never in the production fallback path. A reference product is evidence for regression, not a source of destination records.

For a shared runtime change, run publication-depth QA across six themes, desktop/mobile navigation, disclosures, galleries, Mini Routes, latest Trip Mode, Adjust Itinerary, checklist persistence and reduced motion. For ordinary content edits, use the existing incremental validation plan.

Use [product UI contract](product-ui-contract.md) for current component dimensions, controls, responsive behavior and Trip Mode details.
