# Itinerary selection logic

Use this logic while choosing places and assembling days. It is a selection pass over the normal research pool, not an additional research stage.

## Preference order

Apply inputs in this order:

1. explicit must-go, avoidance, health, dietary, mobility and time constraints;
2. selected questionnaire interests;
3. first-visit essentials and destination identity;
4. route quality, opening hours, rest and weather resilience;
5. the default audience tendency below.

Never override an explicit preference with a demographic assumption.

Treat explicit subculture tags literally. `二次元、动漫与游戏文化` may raise the rank of destination-relevant animation districts, game culture, official stores, exhibitions or themed events. `K-pop、偶像与韩流文化` may raise the rank of official or established music, performance, album, agency-area and fan-culture destinations. Do not merge these into generic shopping or generic “internet-famous” places, and do not apply either tag when the user did not select it or the destination lacks a credible scene.

## Default audience tendency

When preferences are missing or delegated to the Agent, assume a visually discerning young adult traveler from China who values recognizable highlights plus contemporary city life. Favor a standard mix of:

- one or two genuinely iconic anchors rather than an exhaustive landmark checklist;
- food, cafes or desserts that are locally meaningful rather than famous only online;
- walkable contemporary neighborhoods, design/creative districts and attractive streets;
- destination-relevant fashion, beauty, select shops or markets;
- selected contemporary subcultures such as animation/games or K-pop when the destination genuinely supports them;
- sunset, skyline, riverside or an approachable evening scene when the city supports it;
- one or two signature cultural experiences with clear local identity.

Do not force nightlife, shopping, cafes or photography onto users who excluded them. Do not use “young” as permission for unsafe, exhausting, expensive or purely viral choices.

## Candidate selection

For restaurants, sights and souvenirs, prefer mainstream, established and locally representative choices when traveler interest, route, budget and quality are comparable. For sights this means recognizable landmarks and established attractions; for restaurants, reputable venues with an exact branch; for souvenirs, concrete recognizable products/brands rather than vague categories or obscure novelty items. Check official information and exact-subject image feasibility during this same shortlist pass. Easier image sourcing is a tie-breaker between suitable choices, never a reason to override must-go requests or choose an unsuitable recommendation. Apply the bounded souvenir search in image-and-source-policy.md before choosing a text-only card.

Shortlist before deep research. For every candidate, judge only five reusable dimensions: preference match, destination distinctiveness, route fit, practical confidence and time cost. Reject a candidate early when it fails two of the first four or consumes disproportionate travel time.

Avoid low-interest filler: generic workshops available in any city, repetitive museums/temples, remote photo spots with little else nearby, commercial “traditional experiences” with weak local identity, and activities selected only to fill a category. A featured experience must answer both “why here?” and “why for this traveler?” in one concrete sentence.

In Standard mode, at least four of the six experience choices should directly match the traveler's selected interests. With no selected interests, use three varied categories drawn from the destination's strongest contemporary, food/design, evening, wellness or signature-culture scenes; do not default to craft classes or formal cultural activities merely because they are easy to source. In standard only, if the bounded evidence ladder forces constrained mode, all four retained choices should match the selected interests or the destination's strongest mainstream-young-adult scenes.

## Day construction

Build each full day around one geographic area and one primary anchor. Add one or two compatible secondary places, a meal/rest window and at most one optional evening extension. Arrival and departure days remain lighter.

Across the trip:

- roughly two thirds of scheduled discretionary stops should directly support selected interests;
- include first-visit essentials without letting them occupy every day;
- avoid more than two same-type attractions in one day unless explicitly requested;
- avoid cross-city backtracking for a single weak candidate;
- alternate dense and lighter periods, and preserve at least one realistic rest/meal buffer per half day;
- place shopping, cafes, nightlife and optional experiences where they are already on the route;
- author `shopping_advice.description` as two or three short paragraphs separated by newlines, normally about 100–180 Chinese characters total: exact scheduled area/shops, priority categories with reasons, suggested browsing time and one or two practical purchase checks. Use the day's existing records; do not invent discounts, stock or tax eligibility. Non-shopping days explain why and when to shop instead. Legacy `url`/`link_label` fields may remain for schema compatibility but Trip Mode does not render a jump link;
- keep unselected niche experiences in Chapter 04 choices rather than forcing them into the daily itinerary.

## Final coherence check

Before writing prose, review the ordered stops once: preference coverage, repeated attraction types, geographic backtracking, opening-hours conflicts, meal/rest gaps and overly late-to-early transitions. Fix those six issues from existing candidates. Do not launch a fresh broad search unless a required day has no viable anchor.
