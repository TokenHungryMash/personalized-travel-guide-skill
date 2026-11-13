# Travel Guide Skill 4.0

[中文](README.md)

Travel Magazine 4.0 combines destination guides, daily itineraries, and travel tools in a single HTML file that opens offline. Use it before departure to understand the city, compare restaurants, and plan routes. Switch to Travel Mode on the road to check the day’s schedule, find alternatives, take notes, and split expenses.

Large destination photographs and color-overprint typography give it a magazine feel, with layouts designed for both desktop reading and quick mobile access.

## Main Features

### Understand the destination before following a route

City introductions cover geography, history, and everyday life. Neighborhood guides explain local character and details worth noticing. Culture, food, and shopping have their own editorial coverage rather than repeating the daily itinerary.

### Detailed itineraries with room for changes

Each day includes stop order, suggested times, visit durations, transfers, and meal options, alongside an offline route map. Alternatives explain what to replace, how to get there, and what to check when weather, closures, reservations, or energy levels change.

Opening hours, regular closing days, and last-entry restrictions are considered during planning. When travel dates are not fixed, relevant conditions remain explicit.

### A place directory beyond the scheduled stops

Directory coverage is planned around the destination’s size, character, and trip length. It includes attractions, cultural venues, restaurants, cafés, and shopping locations.

Search, area filters, favorites, and detailed entries make places easier to find. Entries include addresses, sources, and navigation links. Photos are checked against the actual subject; places without reliable images retain informative text entries.

### Food and shopping recommendations that help you choose

Dining recommendations default to four categories: “Worth a Special Trip,” “Local Specialties,” “Everyday Chains,” and “Coffee & Sweets,” adapted to the destination. Expand an entry for the reasons to visit, what to order, budget guidance, branch location, and opening considerations.

Shopping coverage explains local product categories, uses, differences, and specific places to browse. Daily shopping suggestions connect to the places actually being visited.

### Travel Mode built for mobile use

Date navigation, compact timelines, transfer details, and navigation links support quick checks on the go. Daily reminders and alternatives share a collapsible section, with meal options and language tools close at hand.

Switching tools preserves the selected day and reading position, reducing repeated trips back to the main guide.

### Notes, photography references, and place attachments

Keep daily travel notes, read location-specific photography suggestions, and upload reference images. Tickets and supporting material live within the relevant place details. Uploaded images can be viewed in full, including tall images that would otherwise be cropped.

### Expense tracking for traveling together

Add and manage participants, upload avatars, record and edit expenses, split costs, and track repayments. Currencies are totaled separately, amounts use thousands separators, and shortcuts connect entry forms, transaction lists, and settlements.

Optional demo entries can be loaded and cleared to explore the features.

### Preparation checklists and practical language tools

Preparation tasks are grouped by when they need attention: advance arrangements, checks near departure, and final carry-on checks. Tasks describe what to do and what completion means, with requirements adapted to the destination.

Language tools organize phrases, vocabulary, and common replies around situations such as dining, transport, accommodation, shopping, visits, and asking for help. They support large-text display and fill-in details. Non-English destinations include local-language content and fallback English; English-speaking destinations use one English set with Chinese explanations.

### Single-file offline access and backups

Photos, fonts, maps, and code are embedded in the HTML, so no local server is needed. Personal notes, favorites, expenses, and attachments can be backed up and restored.

External navigation, booking websites, and source links still require internet access. Personal records are stored in the current browser; moving them between devices requires exporting and importing a backup.

## This Update

Improved manifest-based image downloads, image deduplication, and final font-coverage checks. Added earlier data checks and clearer daily Travel Mode review steps, and reconciled older workflow instructions. This maintenance round passed 157 automated tests.

## Install or Upgrade

The repository and Skill name remain unchanged: `build-personalized-travel-guide-open-source`.

1. Download the [latest installation ZIP](https://github.com/TokenHungryMash/personalized-travel-guide-skill/releases/latest/download/personalized-travel-guide-open-source-skill.zip), or the complete repository from its default branch.
2. Put the complete Skill folder in your agent’s skills directory. Replace the previous Skill installation rather than leaving duplicate copies. Keep personal workbenches and browser data separately.
3. Invoke `$build-personalized-travel-guide-open-source` to start a guide.
4. Check that `metadata.version` in the installed `SKILL.md` is `4.0.0`. The normal flow is questionnaire, itinerary approval, then magazine production; an explicit request to generate directly can skip discussion.

Links pinned to `v3.0.0` still download that historical version. Use the latest ZIP above or the default branch for 4.0. Existing 3.0 guides and browser records are not automatically migrated.

Requires Python 3.10+ and the workbench’s Python dependencies. Browser verification requires Node.js, Chromium, and the relevant dependencies. Production requires online research, file access, image inspection, and browser capabilities; the finished file can be read offline. This 4.0 release ships the offline magazine workflow, without the 3.0 Cloudflare deployment tools or drag-and-drop itinerary editing.

## License

Original code and documentation use the [MIT License](LICENSE). Included example photographs, maps, fonts, and third-party code retain their own source and licensing terms; they are not automatically covered by MIT. See [Third-Party Notices](THIRD_PARTY_NOTICES.md).
