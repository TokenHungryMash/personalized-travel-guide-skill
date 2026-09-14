# Eight-module travel guide content model

Route copy: keep `transport_mode` as its supported research value; rendering localizes transport labels. When `distance_basis: coordinate_straight_line` is used, the renderer supplies one route-level explanation per day. Use optional day `route_note` for a more specific shared explanation; do not repeat the same distance disclaimer in every stop's `practical_note`. A stop's transfer fields describe arrival from its preceding stop; the display between two stops therefore uses the destination stop's fields.

## Product inventory

These are the existing full-handbook product defaults, not instructions to schedule every reference choice. Trip length and interests determine the scheduled subset; optional alternatives remain clearly labeled. Do not silently relax machine-enforced minimums. Exact field shapes and executable counts come from `assets/research-pack-contract.json` and the generated pack task.

1. Itinerary — one day and Mini Route per trip day, ordered stops, realistic transfers, authored period descriptions and route-specific photography advice. Author each stop's practical visit note and time/queue fallback in the same pass; collect its verified coordinates during the normal place lookup. Trip Mode consumes these existing fields and must never trigger a second research pass.
2. Sights — at least eight useful first-visit choices, split into scheduled and optional choices.
3. Shopping — reputable shops or markets followed by a souvenir section with optional product photos.
5. Food — destination-authored menu primer, exactly four local snacks, at least six dedicated-trip restaurants across four cuisine/scene labels, and four well-known local-chain fallbacks by default (two to four only for an explicit narrower brief or documented lack of suitable choices).
6. Preparation — essential and confirm-ahead checklists with at least 24 useful items total.
7. Language — five keyword and five phrase groups with five entries each, plus practical English fallback when relevant. Label that edition once as `英语备用`; group headings are plain Chinese without `(English)`、`（英语）` or `中英对照`, while English and its concise Chinese meaning stay inside the cards.
8. Local notes — exactly five folds for weather, culture/etiquette, transport, safety and payment, with four practical topics each.

## Unnumbered framing: cover, transport and stay

Include destination cover, dates, route, complete flight/train/ferry legs, arrival and departure buffers, hotel galleries, addresses, stay dates, neighborhood positioning and map links.

Place the exact-property hotel disclosure immediately before Chapter 01. It is part of the itinerary setup but does not consume a chapter number. Include the canonical eight-module editorial contents page: 01–08 in two columns on desktop, one column on mobile, separated by fine rules with no card wall or arrow bubbles. Also keep the slim persistent chapter rail on wide desktop; it supplements rather than replaces the contents page. Use a compact drawer or sheet on mobile. Hotel galleries must be sourced for the exact property; do not substitute a user attachment merely because it appeared beside the hotel brief.

When transport details are incomplete, show canonical-shaped `待确认` transport placeholders and continue the handbook. Ask for missing booked information only when the user wants those facts filled. Never retain reference flights or airports. Phase/section headlines around the itinerary are optional semantic fields: use them only when supported by real hotel, region or trip-phase boundaries, and write them for the target destination rather than translating Bali's forest/sea narrative.

Render one flight/rail card per confirmed leg. Without confirmed legs, render only outbound/return placeholders—not an assumed connection. Derive the large route title and small explanatory line from those same records so neither can retain a reference transfer, duration, terminal or hotel departure recommendation.

## 01 Daily itinerary

Each day includes date, area, clear title, morning/afternoon/evening, stop duration, transport mode, distance, realistic time, approximate spend and rationale. Write the three period descriptions from the actual ordered stops: name the places/districts, explain the transition, and include concrete meal, rest, weather or departure buffers. Generic numbered-day filler is invalid. Each stop also gets one substantive `practical_note` and one `time_guard` that states a latest departure, queue limit, shortening rule or transfer buffer. Record verified coordinates for scheduled places during the same lookup; this is not a second research task. Add a compact route visualization for every day, including arrival and departure days. Show ordered stops and labelled transfer legs; collapse density rather than removing the route on mobile. The handbook day ends with a route-specific photography note and a two-to-three-card `shooting_plan`: name scheduled places, state useful light/timing, give distinct subject/viewpoint/composition ideas and one practical portrait/etiquette instruction. No two days may reuse the same photography payload. Shopping guidance appears only inside Trip Mode. A shopping-free day says why instead of inheriting island copy or inventing a detour.

Use [itinerary selection logic](itinerary-selection-logic.md) before writing daily prose. Questionnaire interests must materially change the selected stops: roughly two thirds of discretionary scheduled stops should support them. When choices are delegated, retain essential first-visit identity while leaning toward contemporary neighborhoods, food, design, shopping, visual atmosphere and approachable evening options that suit a young adult audience. This is a ranking preference, never a reason to ignore explicit constraints or force generic viral venues.

Every stop-level `practical_note` must change what the traveler does on site. Include the useful entrance, visit order, meal/rest choice, queue decision, shopping boundary or bad-weather fallback that matters at that exact stop. Pair it with a measurable `time_guard` whenever delay affects the next stop. Reject generic advice such as “根据体力调整”“注意安全”“拍照打卡” when it does not name an action or decision. Derive these notes from the same place and route research; do not open another research pass only to lengthen the copy.

For every `shooting_plan` card, write for a phone-photography beginner: include a usable standing position or camera height, a lens/framing suggestion, what the subject should do, and one exposure, crowd, safety or etiquette check. Keep this guidance compact and derive it from the existing route research; it must not trigger another image or venue search.

## 02 Sights and landmarks

Separate scheduled and optional places. Provide at least eight useful first-visit sights per destination or major base, even when only the mainstream subset fits the itinerary; label the rest as optional choices. Every card includes native/local and user-language names, hours/weekly closure, suggested duration, best time, practical cautions, possible visit day, official-site link, map link and one verified image. A Google rating may be added only when it is directly available during the normal exact-place lookup. If absent, omit it without another search and without rendering an unavailable placeholder. Only deliberately marked `gallery_featured` sights receive a second genuinely different verified image and gallery controls.

## 03 Shopping and souvenirs

Curate reputable shops, markets, design stores and shopping streets. Follow them immediately with a must-buy/souvenir subsection; retain text-only cards when product photos are unavailable. Illustrated souvenir cards inherit the shopping cards' image ratio; text-only cards omit the visual column while retaining typography, spacing and buying advice. Explain what the product is, where to buy it, how to choose it and any packing/customs caution.

Select recognizable, useful purchases before searching for images: destination classics, nationally established gifts available along the route, and practical beauty/personal-care products when relevant. Name a specific product/brand or a clearly defined useful category. Do not invent “a district's anime merchandise” or “a landmark's limited sweets” merely to fill a module. Interest-specific goods supplement these choices when their brand/product and purchase location are concrete. For Japan, user-mentioned examples such as 白色恋人 and 东京香蕉 illustrate recognizable branded gifts, not a mandatory list for every city; distinguish product origin from the current destination and verify local availability before recommending a shop. “药妆” alone is not actionable: identify the brand/category, intended use and buying checks without unsupported medical claims. Never choose a weak item because its photo is easier to obtain, or delete a useful recommendation only because its photo is unavailable.

## 04 Destination-specific experiences

Adapt to the destination and traveler interests: onsen, yoga, gym, dance, spa, surfing, workshops, performances, nightlife, seasonal events or family activities. Include exact-place imagery, area, hours/weekly closure, route/base-area fit, why it fits and map/course link. Show distance from the hotel only when a hotel is selected and the distance is actually verified. In Standard mode, target three user-choice categories with six researched experiences total and uneven group sizes allowed. If a third category cannot produce a truthful, coordinate-verified and exact-image-qualified option after the bounded source ladder, `constrained` mode in standard only may render two strong categories with four options total and uneven group sizes allowed. Record that failure in the candidate ledger; never pad the module with generic filler or unrelated images. Do not research or render extras merely because more candidates exist. Expand only when the traveler explicitly requests an experience-heavy handbook; destination abundance alone is not permission to expand. Do not use neighborhoods as the top-level disclosure taxonomy; location belongs in card metadata and routing. Do not reuse a generic Bali fitness taxonomy where a new destination has more valuable signature experiences.

Category labels must summarize the records actually inside them. Culture walks, galleries and museums belong under a culture/art heading; onsen belongs under bathing/recovery; workshops belong under craft/learning. A category whose heading and cards describe different experience types is invalid, even if the card geometry is correct.

## 05 Food guide

The **worth-a-special-trip** family contains at least six individually researched restaurants. It must cover at least four genuinely distinct cuisine or dining-scene labels rather than repeating one popular category under different names. Choose the mix from the destination: representative local dishes, seafood or meat specialties, noodles/rice, casual neighborhood places and a more complete meal are useful patterns when the destination supports them. Add exactly four representative local snacks and a second restaurant family of four well-known established local chains by default for low-effort fallback meals. Omit delivery and the former hotel-proximity family.

Start with the canonical editorial menu-reading primer: destination-specific kicker, large practical headline, explanatory introduction, at least four guidance cards and a nested collapsible dictionary of local dish/menu expressions. Do not reduce it to an unstyled list or one-line disclosure. Then separate:

The primer is destination-authored content, not canonical copy. Write it for a first-time visitor encountering that destination's ordering flow and unfamiliar menu: local dish/category terms, portion conventions, set menus or service charges, allergy/ingredient communication, queue/reservation customs and the shortest useful local-language/English phrases. Do not reuse Bali ingredients, Indonesian menu terms or service assumptions in another country.

1. **Local snacks** — exactly four food-first entries explaining what each snack is, its flavor or texture, where it is commonly found and how to order it. A representative shop may be named, but this family is not another restaurant ranking.
2. **Worth a dedicated trip** — distinctive cooking, setting or destination significance; explain why the travel is justified. On trips of three or more days, at least three of these exact restaurant place IDs must appear in itinerary stops. Match the branch and opening hours to the day's route; label the remainder as same-area alternatives rather than leaving the entire family optional.
3. **Dependable local chains** — four well-known, locally characteristic, established chains by default (two to four only for explicit narrower scope or a documented suitability limit) with multiple branches, predictable service and easy-to-find evidence. Treat them as low-effort backups for late arrival, queues, rain or a tired evening—not as hotel-distance claims. Name the exact branch when one is scheduled.

Every restaurant includes one useful image, cuisine, venue type, signature dishes, per-person range, hours/closure, visit-day connection and direct map link. Record the Google rating only when it appears during the same exact-place panel visit; missing ratings trigger no follow-up search and never block the restaurant or handbook. Use the exact Google Maps place photo first, then make at most one fallback attempt using exact-pin Street View, official venue/social media or a reputable exact-place listing. standard mode requires branch/name binding plus machine decode checks and recorded dimensions (small dimensions are warnings); batch visual inspection follows image-and-source-policy.md. If both attempts fail, use an allowed identity-bound official-brand fallback or replace the venue once rather than starting a broad image search. Every displayed rating includes a source URL and retrieval date. Never invent ratings or repeat example scores.

## 06 Before departure

Use **essential items** and **book/confirm ahead** only. Do not add a visa/entry family to the handbook. Render both checklist families in the same standard two-column visual language on desktop and ordinary phone widths; fall back to one column only when needed for legibility. Store checkbox state locally.

Populate both families from the target destination, dates and actual itinerary. Entry documents, rail/airport transfers, restaurant/experience bookings, weather gear, payment and connectivity must be locally relevant. Canonical Bali excursions such as Nusa Penida, Bali transport apps or tropical-only packing items must not survive in another destination unless independently required there.

## 07 Language companion

| Family | Entry fields |
| --- | --- |
| keyword_groups / phrase_groups | term, meaning, reading (Japanese: required useful romaji) |
| english_keyword_groups | term, meaning |
| english_phrase_groups | sentence, meaning |

`roman` is not a rendering field. Each family has five Chinese-titled groups with five entries each. Use the generated scaffold before authoring.


Organize by scenario with collapsible groups:

- destination-language words: local script, romanization when useful, user-language meaning;
- place-name components and signs;
- menu vocabulary, transport, directions, payment, culture/temple etiquette and emergencies;
- practical English sentences for hotels, restaurants, drivers, payments, transport and problem-solving.

For English-speaking destinations, emphasize local vocabulary and conventions instead of elementary English.

Keep all scenario/group headings in plain Chinese. Label the fallback edition once as `英语备用`; do not append `(English)`, `（英语）`, `英语版` or `中英对照` to group headings. Put English terms or sentences inside the cards with concise Chinese meaning beneath. Every keyword and phrase family contains at least five groups, and every group contains at least five useful entries.

## 08 Local travel notes

Use exactly five folds with four titled topics each: weather/climate, culture and etiquette, local transport, safety, and payment. Every topic keeps a natural, decision-oriented Chinese subheading; reject “提示1/提示2”, “当地交通 1” and any category-name-plus-number template. Each fold summary must state a destination-specific decision in at least 24 useful Chinese characters. Each topic note must contain at least 34 useful Chinese characters and two compact sentences: local context followed by an action, exception or fallback. These are validator and final-render audit requirements, not optional writing guidance. Use authoritative sources for medical, legal and entry claims.

## Visual coverage contract

- framing: destination cover and exact-property hotel galleries.
- 01: a Mini Route and photography note for every day; photography advice identifies real light, viewpoint, composition or timing rather than generic “take photos”. The shopping note remains data for Trip Mode only.
- 02: one exact-place image per sight; add one genuinely different second view only for `gallery_featured` priorities.
- 03: exact-place images for shops and markets; souvenir product photos are optional only after the bounded search described in image-and-source-policy.md, or an explicit user text-only request. Text-only souvenir cards retain buying advice and omit the image container.
- 04: exact-place images for every activity, studio, spa, onsen, workshop or nightlife card.
- 05: one image for every restaurant; use the bounded Google Maps/Street View/official-or-listing ladder and never reuse one venue's photo or generic dish as another venue.
- 06: use icons and checklist visuals; add photography only when it carries information.
- 07: prioritize readable language layouts; decorative imagery is optional.
- 08: remain text-led by default; add contextual imagery only when explicitly requested and still within the media budget.

The second half must not become a sequence of plain text blocks. Balance utility with verified imagery, compact cards and progressive disclosure.

## Evidence hierarchy

Use official venue, transport and government sources first; then reliable booking platforms and established destination publications. Use community reviews to identify recurring experience patterns, not as the sole source for safety or operating status. Ratings and review totals change: state retrieval date or use approximate counts.
# Rendering-specific content rules

- The cover display always uses one destination-authored Chinese editorial title on the first line and the fixed word `ITINERARY` on the second line. Agents do not author, translate or replace that second display line.
- The cover date label omits the year and is paired with a small `X天 / X晚` duration label.
- The hero display title is a short editorial destination phrase. Do not repeat the city name, dates, duration (`X天X夜`) or traveler count there; those already have dedicated cover fields.
- Every language group heading is Chinese. English or destination-language text belongs inside each card with a Chinese meaning, never as the group heading alone.
- Sight and restaurant cards show a Google rating only when a verified optional record exists. A guide with zero ratings is complete.
- Shopping subtitles are semantic (`商场与店铺` by default; `店铺与集市` only for a real market). Inventory must reflect actual high-demand local shopping and souvenir behavior.
- Menu guidance requires four substantive first-time-visitor cards before the collapsible dictionary. Menu-primer entries require a local term, user-language meaning and a practical ordering note.
- Every travel-note topic must contain a substantive explanation, not a one-line placeholder.

## Truthful activity grouping

Keep the standard six options and three display groups, but group sizes may be uneven. Never relabel an activity to meet a category quota. In addition to existing types, use `urban_walk`, `food_culture`, `pop_culture`, and `digital_art` for matching activities. A market is not a craft workshop; browsing anime merchandise is not a performance. The activity type describes the activity, while display groups may combine related types. Shared Chinese/Japanese kanji are valid language entries; do not append language names to make fields artificially different.


## Mainstream selection and source feasibility

For unspecified preferences, prefer well-known, established restaurants, recognizable established sights and mainstream concrete purchases when route, taste and budget fit are comparable. Check official information and image feasibility during normal selection. Do not seek obscure venues merely to make recommendations look original. Popularity is a practical default, not proof of quality and not a reason for detours, unsuitable food or crowding. Keep distinct local cuisines and the user's interests represented. A chain still needs a verified exact branch; brand recognition does not make another branch's photo interchangeable. Never rank an unsuitable venue above a suitable one just because its image is easier to download. Apply the souvenir shortlist rule before searching for photos, and use the text-only fallback only after the bounded search with recorded outcomes.


Daily photography and outfits are separate deliverables. Under photo_advice retain photography tips and include outfit_advice with women/men/practical_note; see research-data-shapes.md. Show both concrete outfits and the day's weather/route adjustment in the daily itinerary and the “摄影穿搭” tab. A portrait_tip or renamed tab alone does not satisfy outfit guidance.
