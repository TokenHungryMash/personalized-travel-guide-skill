# Offline PNG map previews

For screenshots of the current real street map, use screenshot-map-workflow.md. Use scripts/render_offline_route.py only for a specifically supplied, licensed local raster tile cache. Never silently substitute an interactive map or a terrain illustration. Exact restore and existing handbooks remain unchanged during Skill maintenance.

Reuse verified itinerary coordinates. Input JSON: width, height, stops containing name, latitude, longitude. Command: python scripts/render_offline_route.py input.json --tiles LOCAL_CACHE --font LOCAL_CJK_FONT --attribution SOURCE_CREDIT --out OUTPUT_PREFIX --zoom 17. The cache uses z17_x123_y456.png names. Reuse Python/Pillow; no browser setup or new coordinate research.

Only use basemaps with documented permission for the intended static export and distribution. The script has no download path. Small quantity and overseas geography do not exempt tile-server policies. Do not bundle experiment tiles, private paths or proprietary fonts. Missing licensed cache is a map blocker, not permission to fabricate a basemap or repeatedly install tools. Continue other handbook work; disclose incomplete map delivery.

The renderer merges same-point numbers, wraps names and changes ALL labels to a full-name legend below the map when collisions remain. Output may grow vertically; never crop the legend. Lines indicate itinerary order, not actual navigation. Keep Google navigation separate.

This helper generates images only. Installing images in the handbook requires an explicit runtime/profile integration change; the existing online adapter is not automatically converted by running it. Do not claim offline integration is complete merely because PNG rendering passed.

Check the four-stop, repeated-start/end, dense long-name and missing-cache cases. Inspect 390px previews; metadata alone is not visual evidence. Stop after two repairs of the same failure. Preserve original test files and use a fresh output directory.
