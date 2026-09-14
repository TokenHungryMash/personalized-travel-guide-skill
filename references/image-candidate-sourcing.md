# Image candidate sourcing

Use this reference when collecting new exact-place images. Discovery and visual verification are separate stages.

## Source ladder

For every named place, start with its exact Google Maps place panel. Confirm the displayed name and branch/address, collect the visible rating/review count when present, and select one clearly relevant place photo from that same panel. Record the exact Maps URL as `source_page` and use `source_type: google_maps_photo`. A locally captured Maps photo may use `file` instead of `download_url`; keep any visible provider attribution and do not represent the photo as owned by the handbook.

If Maps has no usable image, is blocked, or cannot provide a usable local asset after one retry, use the first reasonable exact-place substitute: exact official detail page, official social/property page, reputable exact-property listing, or exact-pin Street View. Stop as soon as one candidate has the right entity, usable resolution and no obvious breakage. Wikidata, Commons and Openverse are optional fallbacks for public landmarks only; never traverse them routinely. Label Street View as a location reference. Do not query extra rating platforms merely because images are missing.

Google Places photo resource names may expire and its terms constrain persistent caching, so do not make it the default local static-asset source. Foursquare or Mapillary may be used when credentials and usage terms permit; absence of credentials is a normal fallback condition. Unsplash is suitable for a destination cover or generic editorial mood, never as proof of a named venue.

## Cheap rejection before visual review

- Official sources must be exact detail pages. Reject search, list and home pages and URLs or filenames containing `logo`, `default`, `share`, `sns`, `banner`, `favicon` or equivalent generic markers.
- Wikidata requires the intended entity, destination/country context and a plausible entity type before accepting its P18 image as a candidate.
- Openverse titles, creator metadata and source pages must retain meaningful venue-name or destination overlap. Reject portraits, celebrity appearances and event coverage for a building or shop unless the requested subject is that event.
- Reject non-image responses, watermarked previews and byte-identical duplicates before contact-sheet review. In standard mode small dimensions are advisory; inspect suspect aspect ratios rather than treating a size threshold as identity proof.
- Reject candidates outside the resolved country or beyond the configured radius unless the source is the exact official entity page.
- Reject category conflicts before download: portraits/events/logos/menus cannot satisfy a venue exterior slot; generic city panoramas cannot satisfy a named restaurant; a nearby building cannot satisfy the requested branch.


## Bounded batch workflow

1. Write one compact request per place with stable ID, exact local/English name, city, country, place kind, known official URL and, when known, Wikidata ID plus latitude/longitude. Resolve the entity once; do not repeat it in every source query.
2. Optionally run `scripts/research_image_candidates.py requests.json candidates.json` with a JSON array such as `[{"id":"venue-id","kind":"restaurant","display_name":"Exact branch","official_url":"https://example.org/branch"}]`. It caches results by normalized request, uses one host-aware bounded retry and stores full metadata without printing it.
3. Use the first usable Maps image. Only after that fails, keep one fallback candidate rather than ranking a shortlist.
4. Download or capture final selections in one batch and run decode/dimension checks. Inspect all final selections together on one contact sheet; individually open flagged files under image-and-source-policy.md.



Do not insert fixed per-image sleeps. Use the helper's small retry only after an actual transient failure, stop a throttled host, and reuse its cache. When an exact commercial official candidate is found, stop the open-media ladder for that venue; do not continue through Wikimedia merely to collect alternatives.

Use API-provided Wikimedia thumbnail URLs (normally 1200–1600 px), not handcrafted original-file redirects. This reduces large transfers and Wikimedia rate-limit retries. An embedding model may rank an already bounded shortlist, but similarity is never identity proof.

Persistent commercial-photo caching is allowed only when that provider's current terms permit the intended local/static export. A credential or a successful response does not grant redistribution rights.

When the bounded shortlist fails, change tier or replace the recommendation. Do not expand into an unbounded search and do not reuse an unrelated image.

## Failed host or helper

A helper is optional, not a production gate. If it is killed or unavailable, record the actual error and use already exposed browser/search results and exact official pages; do not repeatedly restart it or require Commons-only sourcing. Commercial venues stop before Wikidata/Commons/Openverse. For landmarks, reject wrong entity types (e.g. a person for a district); P18 is a candidate, not verified identity. Stop a source after two consecutive timeouts/failures in the current batch and carry that observation to subsequent venues. Preserve good packs and repair only named contract errors; never restart all nine packs.

Other-branch photography is not exact-branch photography and cannot fill that requirement. The existing alternative is an associated official logo/share card, explicitly classified official_brand_asset with original_media_class unchanged, source_type official, and visual_subject_type official_logo/official_share_card. Explain the brand relationship in source_identity_note and label the visible card as brand artwork, not branch imagery. If no permissible exact image or honest brand artwork exists, replace the optional venue once with a nearby interest-matched candidate. If still blocked, report the specific gap without fabricated imagery or a success claim. Do not require the user to choose A/B/C for routine optional replacements already within the brief; preserve explicitly required venues and explain unresolved constraints.

Brand artwork must also be usable as a normal card: at least 240 px on the long edge and 120 px on the short edge, with an aspect ratio no wider than 6:1. Tiny logos and narrow masthead banners do not satisfy the fallback even when their identity is correct. Continue the bounded official lookup, then replace an optional venue when no stronger associated artwork exists.
