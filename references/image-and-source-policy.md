# Image and source policy


## Cover selection

The cover may reuse a correctly sourced destination sight/place photo. This is not duplicate gallery padding and must not trigger rejection or replacement research. Keep the cover and place provenance intact; duplicate images within a place gallery or between different named places remain invalid.

Search for a landscape or city image that is unmistakably tied to the destination and supports both desktop landscape and mobile portrait crops. Prefer official tourism media, licensed editorial libraries, Wikimedia Commons with clear licensing, reputable destination publications or user-supplied photography. Keep enough negative space for the title.

When no suitable licensable image exists, generate a destination-specific cover from researched visual cues. Label generated imagery honestly. Do not fabricate a named hotel, restaurant or landmark through image generation.

## Place-card selection

### Souvenir search before text-only fallback

An optional image is not permission to skip lookup. During normal research, look up the exact product/local name and brand on its official product page or catalogue; inspect the returned body/lazy/structured images and at most two exact same-site links. Reuse an existing verified search record instead of repeating work. A parser `no_image` only describes that page probe, not the whole product's image availability.

If no usable exact-product photo is found, inspect one reputable retailer's exact-product page or an official tourism product listing and verify identity and permitted use. Do not search nearby streets or widen into repeated Commons searches. Correctly associated permitted official-brand artwork remains a labeled fallback, not product photography. Save the product ID, actual attempted URLs, observed outcomes and final choice/reason in `.research-state/candidate-ledger.json`, preserving existing entries. Missing input is unfinished research, not an exhausted search. An explicit security denial stops dependent access and is recorded honestly; never fabricate a second attempted source.

Only after that bounded search fails (or recorded access restrictions prevent it), retain `images: []` with useful buying advice. An explicit user request for text-only output also permits skipping image lookup. Do not remove a strong recommendation just for missing imagery. Text-only remains valid in the data validator for existing guides and user-specified output; the research task must perform and record the search before using that fallback in a new build.

Use an image of the exact place. Start from the exact Google Maps place panel and reuse that visit for identity, location, rating and image collection. In standard mode, record the matching place name/address in source_identity_note and run local decode checks; inspect the selected batch together. Separate full-size visual evidence and verified visual booleans are not required for an unambiguous ordinary photo. Use the short fallback in [image-candidate-sourcing.md](image-candidate-sourcing.md) only when Maps fails.

Every restaurant in Standard mode receives one image. A Google Maps place photo is the default; an exact-pin Google Street View fallback uses `source_type: google_street_view`, `visual_subject_type: place_exterior`, and the label **门店街景 · 位置参考**. Review the selected batch under the policy above. Reject obviously unrelated businesses, map-only imagery, loading states and generic cuisine stock. If Maps plus one fallback fails, use an allowed official-brand fallback or replace that restaurant once. Standard mode uses one image per ordinary sight, shop, experience and restaurant. Only a deliberately selected `gallery_featured` sight and the selected primary hotel receive a second, genuinely different view. Do not borrow another venue's image or count duplicates as different gallery views. After the bounded souvenir search above, souvenirs may use images: [] without blocking production: keep useful product recommendations and buying advice, omit the visual container, and do not search repeatedly or delete recommendations solely for missing photos. If an image is supplied, exact-product/allowed official-brand rules still apply.

For photographic named-place images, record `visual_subject_type` as `place_exterior`, `place_interior`, `room`, `dish`, `product`, `experience_scene`, or `landscape`. Logos, Open Graph/share cards, posters, maps, text cards and generic brand graphics are not place photos after conversion. Byte-identical files cannot fill multiple gallery positions.

Souvenir cards require the exact product (`visual_subject_type: product`), or the existing standard official-brand exception. Nearby shopping streets and manufacturer buildings cannot stand in for the product. A brand logo/share image remains `official_logo`/`official_share_card` with `official_brand_asset`; verify and describe its relationship to the named product in the existing source/visual evidence. An unrelated brand is invalid. The candidate helper separates product candidates, explicit brand fallbacks and unresolved gaps; follow its bounded next action instead of widening to geographical images.

Use generic stock only as an explicitly labeled illustration and never for a named venue card.

Reject watermarked stock previews and search-result composites, including visible Alamy, Getty Images, Shutterstock, Dreamstime or similar marks. Known commercial-stock preview URLs are not acceptable travel assets even when they decode. A legitimately licensed clean original must have a separate source/license record and must not carry a watermark.

## Hotel identity and user attachments

Source hotel images independently from the exact property's official site, a reputable lodging listing, or public map/business material. Cross-check property name, neighborhood or address, and visible room or exterior details before use.

For named-place photography (all editions), `media_class` and `original_media_class` must both be one of `real_photo`, `official_photo` or `licensed_photo`. A restaurant-only Street View capture is classified as `real_photo`, with `source_type: google_street_view`, exact-pin/storefront evidence and the mandatory location-reference label. `generated_editorial` is permitted only for a cover or non-place decorative background. Other `illustration`, `text_card`, `placeholder`, `html_screenshot` and `svg_render` assets never satisfy an exact-place slot. Rasterizing SVG/HTML or converting formats does not change media identity; record `transcoded_from` and preserve the original class.


Do not infer that an uploaded image depicts the hotel merely because it was attached to the same request. Unless the user explicitly says the image is confirmed property photography, treat it as mood, layout or visual-reference material only. Never present it as a hotel image or copy it into the hotel gallery without verification.

Keep source provenance per asset in a compact manifest containing venue, source page, source type, retrieval date and local filename. Prefer the official property source when equivalent images exist.


## Storage and performance


Preserve downloaded image bytes and native dimensions. Small dimensions are advisory: assess visible quality and exact subject identity. Do not add white padding merely to meet a pixel floor, and do not report padding when no transformation occurred. Legacy padded assets remain verifiable from their original receipts.

- Localize stable images when usage terms permit.
- Resize card images to a roughly 1200–1600 px long edge.
- Prefer WebP/AVIF or optimized progressive JPEG, usually quality 70–82.
- Use `loading="lazy"` for card images, but preload or set high fetch priority for the cover only.
- Add descriptive alt text and reserve width/height or aspect ratio to prevent layout shift.
- Keep attribution visible but visually quiet; do not place a large source badge over the subject.

## Verification

Download receipts must come from actual acquisition. Preserve their place ID, source page, direct URL and SHA-256 of the saved bytes; never manually mark a failed request `ok` or rewrite a receipt to match a substituted file. A documented legitimate conversion needs a new acquisition/conversion receipt, not a changed identity claim. Missing optional ratings and browser-access restrictions do not relax asset correctness.

Before using a candidate, verify that its source names the same venue/branch. An official domain, guessed page number, first search result or `og:image` tag alone does not establish identity. Inspect ambiguous candidates once; an unrelated tourism page or category photograph must be rejected. Classify logos/share artwork honestly using the standard exception, without claiming a branch photograph. Never copy, recolor, crop, add pixels to or re-encode one picture merely to defeat duplicate detection. The verifier checks both byte duplicates and near-identical decoded images locally; this does not require another network lookup.


For an unchanged official image, reuse its visual-review cache when the local byte hash, direct URL, source page, place ID and prior contact-sheet row all still match. A changed byte, URL, place binding or crop invalidates that visual cache. Download checks may rerun independently without forcing a new identity review.

When visual review is actually required, inspect the file at readable size. Do not create a review task merely to set `visually_confirmed` in standard mode.


For the cover, verify nonzero natural dimensions and the intended crop at approximately 390×844 and 1440×900. For all images, confirm no broken references in the local export.

If an image cannot be verified, omit or replace the venue rather than filling the card with unrelated scenery.

Treat Wikimedia 429 responses as host throttling, not evidence that the file does not exist. Stop concurrent requests to that host, apply low-frequency backoff, reuse already downloaded valid files, and then switch to an allowed stable thumbnail/proxy or another licensed exact-subject source. Do not repeatedly hammer Commons or fall back to an old guide asset.

Do not ship repeated proxy imagery: one restaurant photo cannot stand in for another restaurant, a park photo cannot represent an onsen, and one scenic image cannot be cloned across a three-image gallery. When only one exact-place image is verifiable, use one deliberate image surface or replace the recommendation; never manufacture a gallery by repetition.

For an adapted destination, do not leave canonical reference assets in the candidate, even temporarily. A localized name over a Bali photo is a failed place card. Finish a destination asset manifest first, then wire only its files into the page. The manifest destination and each asset venue must match the current export.


## Identity observations

Each image declaration carries `source_identity_note`: a concrete observation from the source caption, branch page or inspected image identifying this exact venue/product (at least 12 characters). After that observation actually establishes identity, explicitly set `source_identity_bound: true`, or supply a hash-bound visual review through the manifest builder. The text note alone does not set this boolean automatically. The boolean alone and an official domain cannot establish identity either. The manifest preserves both; machine preflight requires both. This is an auditable declaration, not machine proof that the photo is correct: visually inspect uncertain/global-navigation/logo candidates and the contact sheet, and never invent observations to pass. Preserve original media classification.


### Observed source failures
HTTP success is not image success: reject HTML responses, decode downloaded bytes, and record 404/TLS/timeout separately. Do not disable TLS verification. For a failed candidate, use a verified exact venue/product page and retain its provenance. Inspect the actual subject before approval: restroom entrances, menu stands, promotional banners and branded collages are not substitutes for venue interiors or product packaging. Official provenance alone does not establish the desired subject; correct visual_subject_type to what is actually visible. Never bulk-mark candidates verified or upscale low-resolution images to pass checks.
