# Research pack data shapes

## Before submitting packs

- Souvenirs: choose recognizable, concrete products using content-model.md §03; keep why_buy/best_for/where_to_buy/buying_tip. `images: []` is valid after the bounded official + one exact-product alternate search and recorded outcomes under image-and-source-policy.md (or an explicit user text-only request); it renders a text-only card; do not substitute street photos or remove good products to satisfy image quotas.
- Photography: 2–3 shooting_plan cards per day; their notes collectively include actionable 手机 and 相机 guidance. Each day also needs `photo_advice.outfit_advice: {women, men, practical_note}` with non-empty strings; this is separate from portrait_tip.
- Food: dedicated_trip and reliable_chains have disjoint place IDs; for 3+ days, schedule at least 3 dedicated_trip IDs. Prefer route-fit during selection, not extra detours to satisfy counts.
- Experiences: use the controlled experience_type list below.
- Travel notes: each group needs a summary of at least 24 characters.
- Scheduled places: coordinate_source contains url/note/precision; itinerary transfers belong to the arriving stop.

For the exact same physical place represented by two records (e.g. a sight and an activity there), set the dependent place's `same_place_as` to the original place ID. Share the unchanged photo, source_page and download_url, retain identity observations for both records and their verified matching coordinates (within 0.0001 degrees). Never alter coordinates to enable reuse. Each (place_id, file) retains its own receipt. This exception does not allow street photos for souvenirs, different branches/nearby buildings, or duplicates within one gallery; near-identical altered files are still rejected. Prefer the original bytes and file path. The photo must actually depict both records' subject; a shared location alone does not prove a specific activity took place.

If research_status.py reports contract_invalid, its complete compiler output is also saved to `.contract-errors/compiled-profile.txt`; read it once and fix the full named error list instead of reverse-engineering validators.

Use these minimal shapes when authoring research packs. Add researched fields required by the generated task, but do not change these container types.

The machine-readable authority is `assets/research-pack-contract.json`. Generated research tasks, early pack validation, compilation and consistency auditing all read that file. The examples below are explanatory views of the same contract.

## Framing roots and itinerary periods

`destination`, `display_name`, `country` and required string `year` are four separate root fields. They are not nested inside a `destination` object. Dates and trip preferences live under `trip`:

```json
{
  "destination": "Sample City",
  "display_name": "示例城市",
  "country": "Sample Country",
  "year": "2026",
  "trip": {"start_date": "2026-11-10", "end_date": "2026-11-14", "days": 5, "rhythm": "relaxed", "travelers": "2", "interests": [], "constraints": []}
}
```

Every itinerary day has one `periods` object. Morning, afternoon and evening are children of that object, never three root fields:

```json
{
  "date": "2026-11-10",
  "theme": "老城与河岸",
  "summary": "上午进入老城，下午沿河步行，晚间在同区用餐。",
  "periods": {
    "morning": {"title": "老城", "description": "从中央市场步行到古城门。"},
    "afternoon": {"title": "河岸", "description": "沿河参观寺院并预留咖啡休息。"},
    "evening": {"title": "夜市", "description": "在河岸夜市用餐后返回住宿区。"}
  }
}
```

## Place references and groups

Experience records use controlled `experience_type` values: `wellness`, `culture`, `craft`, `nature`, `adventure`, `performance`, `food_workshop`, `nightlife`, `urban_walk`, `food_culture`, `pop_culture`, or `digital_art`. Use the type matching the actual activity; keep group membership meaningful. An empty `support` array is valid when no booked transport or stay support nodes are known.

Module groups never contain a bare string ID. Wrap every reference:

```json
{
  "title": "温泉与入浴",
  "subtitle": "日归泡汤",
  "items": [{"place_id": "onsen-01"}, {"place_id": "onsen-02"}]
}
```

The referenced place exists exactly once in a `places/*.json` array and owns its description, links, hours and images. Itinerary stops also use an object with `place_id`; they are not strings.

## Pending and confirmed transport

Unknown transport is:

```json
{"status": "pending", "legs": []}
```

Confirmed transport is `{"status":"confirmed","legs":[...]}`. Each leg is an object containing `direction`, `date`, `service_number`, `origin`, `destination`, `departure_time` and `arrival_time`; add terminals only when verified. Never mix pending placeholders with confirmed legs.

## Pending and confirmed stays

Unknown accommodation is represented by one status object and no property place:

```json
[{"status": "pending", "place_id": null, "check_in": null, "check_out": null, "notes": "住宿待确认"}]
```

A confirmed stay uses `status: "confirmed"`, a real hotel `place_id`, `check_in` and `check_out`. That hotel must exist once in the places pack and carry two verified image declarations. Do not create a hotel-area record for a pending stay.

When a complete `trip-decisions.json` exists, `compile_destination_profile.py` applies its selected records through `apply_trip_decisions.py` before validation and provenance signing. User-supplied booked facts may still be placed directly in the framing pack. Never scrape or reconstruct another product's HTML; missing or malformed facts remain in the neutral pending state.

## Daily shopping and photography guidance

Each new itinerary day supplies a nonempty `fallback` string, optionally with newline-separated paragraphs. Trip Mode renders this as its own “备选方案” card immediately below shopping, open by default. Describe a concrete rain/cold or low-energy trigger, the stops to cancel, and a useful same-area replacement sequence using already researched venues; arrival/departure days prioritize actual travel timing and rest. Do not merely write “下雨去室内”. The same field may also appear in the day's existing decision notes; do not create conflicting copies.

Every itinerary stop also supplies `practical_note` and `time_guard`. `practical_note` says what to do, what to notice and how to use the stop without generic filler. `time_guard` gives one useful decision boundary: latest sensible departure, maximum queue, a shortening rule or a transfer buffer. Write both while the route is authored; Trip Mode reuses them without another research or generation pass. Every scheduled place records verified `latitude` and `longitude` (or an equivalent `coordinates` pair) during the normal exact-place lookup so the offline hand-drawn route keeps correct relative geography. Never guess coordinates.

For photography, the two or three `shooting_plan` cards must collectively include separate, actionable settings for both `手机` and `相机`. Phone guidance names the lens button (such as 0.5×/1×/2×), camera height and exposure or night-mode choice. Camera guidance names a focal-length range and useful aperture, shutter, ISO or stabilization choice. Generic light-only advice is incomplete.

Every itinerary day has `shopping_advice` for Trip Mode only. Write `title` and a self-contained `description` of two or three short paragraphs (newline-separated, normally 100–180 Chinese characters): where to browse, priority purchases and reasons, time allowance, and practical purchase checks. An intentionally shopping-free day explains why and identifies a better shopping day. `url` and `link_label` remain legacy schema fields only; current Trip Mode renders no souvenir/shopping jump button. Never render this block in the main itinerary or retain reference-destination copy.

Every day also has `photo_advice` with `title`, `lighting`, at least two non-empty `suitable_shots` entries, `portrait_tip`, and a compact `shooting_plan` of two or three `{time,title,note}` cards tied to scheduled places. These are protected authored fields: name scheduled places, lighting direction/time, subject/viewpoint/composition and a route-specific portrait or etiquette constraint. They must differ across days; do not seed them with reusable generic prose. The main itinerary renders the canonical two-column text card; Trip Mode reuses the same payload and keeps direct local sample upload. Optional `samples` may be injected only when every item is verified. If no verified local sample exists, omit `samples`; never render a broken placeholder. The generic bottom “小红书找人像样片” action is intentionally absent, while exact-place Xiaohongshu buttons on Trip Mode stop cards remain.

## Restaurant names, dishes and ratings

The essentials checklist visibly labels each item `必须` / `建议` / `随缘` and uses that exact sort order, preserving authored order within a level. Do not merely say “按重要性” while hiding the levels. Choose levels from actual traveler needs, without forcing unnecessary items into the must-have tier; keep the item title and explanation visually separate.

Food cards show the user's Chinese `name` as the snack heading and `local_name` separately below. Keep menu-guide cards and dictionary rows styled in the current-system runtime: a dictionary row separates the local term, Chinese meaning and ordering note. Do not let these components fall back to an unstyled prose stack.

Preparation essentials carry `priority` (`必须`, `建议`, `随缘`) and are authored in descending practical importance within each level: documents, payment, communication and personally necessary medication before comfort extras. Confirm-ahead records use the same meaningful priorities; do not stamp all records as `建议`. Current reservation rows collapse to a compact line with title, priority, completion checkbox and disclosure; keep timing and detailed instructions available when expanded.

The food module uses `local_snacks` (exactly four authored food entries), `dedicated_trip` (six or more restaurant references) and `reliable_chains` (four well-known chain choices by default, with exact restaurant-branch references; two to four for explicit narrower scope or a documented suitability limit). Do not emit `near_stay` or `delivery`. For trips of three or more days, at least three IDs from `dedicated_trip` also occur in itinerary stops; their times and branches must be compatible with the route. A chain fallback is locally characteristic and established across multiple branches, not merely a famous independent restaurant.

`signature_dishes` is concise researched display copy naming two or more specific dishes, not a raw JSON array, generic phrase, or placeholder:

```json
{
  "local_name": "店舗の現地語名",
  "english_name": "Official English Name",
  "signature_dishes": "dish one · dish two",
  "ratings": [
    {"platform": "Google", "status": "verified", "rating": 4.4, "review_count": 1280, "source_url": "https://…", "verified_at": "YYYY-MM-DD"}
  ]
}
```

`ratings` may be omitted or empty when no reliable numeric score was obtained. Follow [Google place lookup](google-place-lookup.md) for initial attempts, outcome evidence and access stop-loss. Never equate an empty array with a failed lookup. Verified records need the exact matched Google place URL and actual retrieval date; review count may be omitted when not exposed.

## Cross-module integrity

Scheduled places carry `coordinate_source: {"url": "actual consulted map or official page URL", "note": "what identifies the place and pin", "precision": "entrance | building | area"}`. Keep area pins explicitly approximate; never call them verified entrances. Named dining-plan meals carry `place_id` and the same date as their itinerary stop; genuinely unassigned meals may omit the ID only with `flexible: true`. All meals need a valid itinerary date; use ISO dates for explicit years and across year boundaries. The flexibility flag never waives checks on a named restaurant. Arrival time plus dwell and the next stop's transfer must fit before the next arrival. Conditional/overnight times need explicit human review; the checker does not invent times from prose.

## Place types and timeline

`places/core.json.sights` requires `type: sight`; `shopping.json.shops` requires `shop`; `souvenirs` requires `souvenir`; food requires `restaurant`; experiences requires `experience`. Temple/shrine/shopping_street/nightlife are semantic descriptions or `subtype`, not replacements for these renderer types. Souvenirs require why_buy, best_for, where_to_buy and buying_tip; reference them only in the souvenir section, never shopping groups.

Stops must be in chronological array order. For every next stop: arrival >= previous arrival + previous dwell + current transfer_minutes. Meals consume their own time; split a neighborhood visit around a meal rather than scheduling both simultaneously. A planned finish does not verify last-train availability: verify the actual service or keep it uncertain.

`transfer_minutes` belongs to the arriving stop and means travel FROM the previous stop TO this stop, not departure toward the following stop. Example: the previous stop ends 17:45 and this stop declares 25 minutes of travel, so arrival cannot precede 18:10. Do not reduce the travel estimate merely to make the audit pass. `distance_km` and `transport_mode` describe the same incoming leg.


## Outfit advice (main itinerary and Trip Mode)

Every day includes `photo_advice.outfit_advice` with `women`, `men`, and `practical_note` as authored strings. Provide a concrete women's and men's outfit (top/layers, bottoms, comfortable shoes and useful accessory), adapted to that day's places, expected walking, season and indoor/outdoor transitions. These are interchangeable style references, not rules about gender; respect any explicit style or accessibility preference. Reuse layers/shoes across days instead of requiring a new suitcase of outfits. `practical_note` explains rain/wind/temperature adjustments and relevant venue constraints; no invented live forecast, dress code or arbitrary extra search is needed. Do not replace these fields with photography settings, a generic packing list or the heading “摄影与穿搭”. Both the main daily card and Trip Mode render the same source data. For an older workbench missing the fields, add them only to research/itinerary.json and recompile; do not repeat research or downloads.

## Flat food and separate souvenirs
`food.dedicated_trip` and `food.reliable_chains` are flat arrays such as `[{"place_id":"restaurant-01"}]`, never `[{"title":"...","items":[...]}]`. Only shopping/experience category groups use title/items wrappers. `shopping` is an array of category groups referencing shops only. Souvenir records live in `places/shopping.json.souvenirs` and are rendered automatically in the dedicated section.

When dates are pending, use exact `Day 1` through `Day N` labels consistently in itinerary and dining_plan; do not invent calendar dates. `trip.travelers` is a value such as `待定`, not `人数待定` because the interface already provides its label.
