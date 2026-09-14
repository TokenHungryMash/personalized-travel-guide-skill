"""Separate exact-subject image candidates from site-wide official artwork."""
import re
from urllib.parse import urlsplit, unquote
from _official_images import matching, is_ui_image


def shared_artwork_urls(pages):
    seen = {}
    for page_url, page in pages.items():
        for image in page.get("images", []):
            if image.get("metadata_key", "").startswith(("og:", "twitter:")):
                key = (urlsplit(page_url).hostname, image["url"])
                seen.setdefault(key, set()).add(page_url)
    return {key[1] for key, urls in seen.items() if len(urls) > 1}


def classify(row, page, shared_urls=()):
    names = [row.get(key) for key in ("local_name", "english_name", "display_name", "query")]
    names += row.get("image_identity_terms", [])
    names = [name for name in names if isinstance(name, str) and name.strip()]
    result = []
    for image in page.get("images", []):
        url = image["url"]
        context = image.get("context", "")
        key = image.get("metadata_key", "")
        logo = bool(re.search(r"(?:logo|logotype)", url, re.I))
        share = key.startswith(("og:", "twitter:"))
        shared = url in shared_urls
        generic = bool(re.search(r"(?:/(?:common|shared|global)/.*(?:ogp|og[-_]image|share)|default[-_]?(?:og|image)|site[-_]?(?:brand|share))", url, re.I))
        exact = any(matching(name, context + " " + unquote(url)) for name in names)
        ui = bool(re.search(r"(?:gnavi|globalnavi|(?:^|[/_\-])(?:icon|nav|menu|button|spacer|loading))", url, re.I))
        if (ui or is_ui_image(url)) and not logo:
            continue
        # Social metadata is artwork until a pixel review establishes photography.
        art = logo or shared or generic or share
        brand = row.get("brand_name")
        brand_match = bool(brand and matching(brand, context))
        entity_bound = (exact or brand_match) and not shared and not generic
        if art:
            result.append({**image, "source": "official_artwork", "media_class": "official_brand_asset", "original_media_class": "official_brand_asset", "visual_subject_type": "official_logo" if logo else "official_share_card", "entity_bound": entity_bound, "shared_site_artwork": shared or generic, "classification_reason": "shared/general site artwork" if shared or generic else "official artwork; require exact venue/brand association", "candidate_score": 60})
        elif exact:
            promotional = bool(re.search(r'(?:banner|mainimg|mainvisual|hero|キービジュアル)', url, re.I))
            result.append({**image, "source": "official_body_image" if key.startswith("body:") else "official_specific_image", "media_class": "official_photo", "original_media_class": "official_photo", "entity_bound": True, "shared_site_artwork": False, "classification_reason": "promotional hero risk; inspect pixels before selection" if promotional else "image context/URL carries exact requested identity; visual review pending", "candidate_score": 50 if promotional else 100})
    return result
