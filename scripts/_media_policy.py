"""Shared ordinary-edition official identity artwork policy."""

def official_brand_allowed(asset, mode):
    return asset.get('source_type') == 'official' and asset.get('media_class') == 'official_brand_asset' and (asset.get('original_media_class', asset.get('media_class')) == 'official_brand_asset') and (asset.get('visual_subject_type') in {'official_logo', 'official_share_card'})

def official_brand_dimensions_usable(width, height):
    """Reject tiny or banner-thin artwork that cannot carry a normal handbook card."""
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        return False
    long_edge, short_edge = max(width, height), min(width, height)
    return long_edge >= 240 and short_edge >= 120 and long_edge / short_edge <= 6
