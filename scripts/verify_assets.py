"""Verify local image files, decoding, dimensions and profile/manifest binding."""
from __future__ import annotations
from _content_integrity import identity_documented
import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageChops, ImageOps, ImageStat
from _media_policy import official_brand_allowed, official_brand_dimensions_usable
REAL_MEDIA = {'real_photo', 'official_photo', 'licensed_photo'}
NON_REAL_MEDIA = {'generated_editorial', 'generated', 'illustration', 'text_card', 'placeholder', 'html_screenshot', 'svg_render'}

def visual_signature(path):
    """Small decoded fingerprint; robust to metadata, JPEG and tiny pixel edits."""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        return image.resize((48, 48), Image.Resampling.LANCZOS)

def near_duplicate(first, second):
    if min((max(ImageStat.Stat(x).stddev) for x in (first, second))) < 12:
        return False
    return max(ImageStat.Stat(ImageChops.difference(first, second)).rms) < 3

def shared_place_photo(first, second, places):
    """Explicit same-place relationship only; never infer identity from proximity."""
    a, b = str(first.get('place_id')), str(second.get('place_id'))
    if a == b or a not in places or b not in places:
        return False
    pa, pb = places[a], places[b]
    if pa.get('type') == 'souvenir' or pb.get('type') == 'souvenir':
        return False
    root_a, root_b = pa.get('same_place_as', a), pb.get('same_place_as', b)
    if root_a != root_b or root_a not in places:
        return False
    if not all(first.get(k) and first.get(k) == second.get(k) for k in ('source_page', 'download_url')):
        return False
    try:
        if any(not math.isfinite(float(p[k])) for p in (pa,pb) for k in ('latitude','longitude')) or any(abs(float(pa[k])-float(pb[k])) > 0.0001 for k in ('latitude','longitude')):
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return identity_documented(first) and identity_documented(second)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('asset_root', type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--machine-only', action='store_true', help='check files, dimensions and provenance before visual review')
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    fetch_report_path = args.asset_root / 'asset-fetch-report.json'
    try:
        fetch_rows = json.loads(fetch_report_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        fetch_rows = []
    fetch_by_file = {(str(row.get('place_id')), str(row.get('file'))): row for row in fetch_rows if isinstance(row, dict) and row.get('file')}
    place_ids = {str(place.get('id')) for place in profile.get('places', []) if place.get('id')}
    places = {str(place.get('id')): place for place in profile.get('places', []) if place.get('id')}
    souvenir_ids = {str(place.get('id')) for place in profile.get('places', []) if place.get('type') == 'souvenir'}
    if profile.get('cover', {}).get('image'):
        place_ids.add('__cover__')
    failures = []
    warnings = []
    mode = 'standard'
    content_hashes: dict[str, list] = {}
    visual_signatures = []
    media_counts = {key: 0 for key in ('real_photo', 'official_photo', 'licensed_photo', 'generated_editorial', 'illustration', 'placeholder', 'other')}
    for index, asset in enumerate(manifest.get('assets', []), 1):
        if str(asset.get('place_id')) not in place_ids:
            failures.append(f'asset {index} has unknown place_id')
        path = args.asset_root / str(asset.get('file', ''))
        decoded = False
        width = height = 0
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f"missing image: {asset.get('file')}")
        else:
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    image.load()
                    width, height = image.width, image.height
                    decoded = image.width > 0 and image.height > 0
                    if image.width < 480 or image.height < 320:
                        warnings.append(f"low resolution: {asset.get('file')} ({image.width}x{image.height})")
            except Exception as exc:
                failures.append(f"undecodable image {asset.get('file')}: {exc}")
        asset['decoded'] = decoded
        media_class = str(asset.get('media_class', '')).strip().lower()
        original_media_class = str(asset.get('original_media_class', media_class)).strip().lower()
        media_counts[media_class if media_class in media_counts else 'other'] += 1
        exact_place = str(asset.get('place_id')) != '__cover__'
        brand_ok = official_brand_allowed(asset, mode)
        if brand_ok and decoded and not official_brand_dimensions_usable(width, height):
            failures.append(f"official brand artwork is too small or banner-thin for a handbook card; find a stronger official asset or replace the optional venue: {asset.get('file')} ({width}x{height})")
        if exact_place and (not brand_ok) and (media_class not in REAL_MEDIA or original_media_class not in REAL_MEDIA):
            failures.append(f"exact-place media must be a real/official/licensed photo and may not be generated, illustrated or a rendered text card: {asset.get('file')}")
        if media_class in NON_REAL_MEDIA and exact_place:
            failures.append(f"non-real media is forbidden for named places: {asset.get('file')}")
        subject_type = str(asset.get('visual_subject_type', '')).strip().lower()
        if str(asset.get('place_id')) in souvenir_ids and (not brand_ok) and (subject_type != 'product'):
            failures.append(f"souvenir media must depict the exact product or use the standard official-brand exception; nearby streets/venues are not product images: {asset.get('file')}")
        allowed_subjects = {'place_exterior', 'place_interior', 'room', 'dish', 'product', 'experience_scene', 'landscape'}
        if exact_place and (not brand_ok) and (subject_type not in allowed_subjects):
            failures.append(f"exact-place media needs an allowed visual_subject_type, not {subject_type or 'missing'}: {asset.get('file')}")
        if asset.get('transcoded_from') and original_media_class != media_class:
            failures.append(f"transcoding must preserve original_media_class; format conversion cannot turn generated media into a photo: {asset.get('file')}")
        is_map_asset = asset.get('source_type') in {'google_maps_photo', 'google_street_view'}
        provenance_fields = ('source_page', 'source_type', 'media_class') + (() if is_map_asset else ('download_url',))
        missing_evidence = [field for field in provenance_fields if not str(asset.get(field, '')).strip()]
        if missing_evidence:
            failures.append(f"asset provenance missing {', '.join(missing_evidence)}: {asset.get('file')}")
        is_street_view = asset.get('source_type') == 'google_street_view'
        if exact_place and (not is_map_asset) and (not str(asset.get('download_url', '')).startswith(('http://', 'https://'))):
            failures.append(f"exact-place media needs a direct http(s) image download_url: {asset.get('file')}")
        if is_street_view and subject_type != 'place_exterior':
            failures.append(f"Google Street View fallback must be a labelled place_exterior location reference: {asset.get('file')}")
        fetch = fetch_by_file.get((str(asset.get('place_id')), str(asset.get('file'))), {})
        if exact_place and fetch.get('status') not in {'ok', 'cached'}:
            failures.append(f"exact-place media lacks a successful asset-fetch-report record: {asset.get('file')}")
        if fetch.get('status') == 'cached' and (not decoded):
            failures.append(f"cached asset report is stale because the local file is missing or invalid: {asset.get('file')}")
        if decoded and exact_place and (fetch.get('status') in {'ok', 'cached'}):
            if not is_map_asset or fetch.get('sha256'):
                actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                if fetch.get('sha256') != actual_hash:
                    failures.append(f"asset fetch receipt hash missing or stale: {asset.get('file')}")
            for field in ('place_id', 'source_page') + (() if is_map_asset else ('download_url',)):
                if fetch.get(field) != asset.get(field):
                    failures.append(f"asset fetch receipt {field} differs from declaration: {asset.get('file')}")
        if fetch.get('padded'):
            if fetch.get('padding_mode') != 'contain_white_no_upscale':
                failures.append(f"unsupported image padding mode: {asset.get('file')}")
            source_width = int(fetch.get('source_width') or 0)
            source_height = int(fetch.get('source_height') or 0)
            if min(source_width, source_height) < 320:
                warnings.append(f"padded image source is too small: {asset.get('file')} ({source_width}x{source_height})")
        evidence = str(asset.get('verification_evidence', '')).strip()
        evidence_path = args.asset_root / evidence if evidence else None
        if not args.machine_only and exact_place and (not evidence or evidence_path is None or (not evidence_path.is_file())):
            failures.append(f"exact-place media needs a saved full-size visual verification evidence file: {asset.get('file')}")
        source_fingerprint = ' '.join((str(asset.get(field, '')).lower() for field in ('source_page', 'download_url', 'file')))
        stock_preview_hosts = ('alamy', 'gettyimages', 'shutterstock', 'dreamstime')
        if any((token in source_fingerprint for token in stock_preview_hosts)):
            failures.append(f"commercial stock preview/watermark source is not allowed: {asset.get('file')}")
        blocked_asset_tokens = ('logo', 'og-image', 'og_image', 'ogp', 'share-card', 'share_card', 'social-card')
        if not args.machine_only and exact_place and (not brand_ok) and any((token in source_fingerprint for token in blocked_asset_tokens)) and (not asset.get('visually_confirmed')):
            failures.append(f"probable logo or Open Graph share card is forbidden for exact places: {asset.get('file')}")
        if decoded and exact_place:
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            previous = content_hashes.get(file_hash)
            if previous:
                if not all(shared_place_photo(asset, prior, places) for prior in previous):
                    failures.append(f"duplicate image bytes do not count as distinct gallery media: {asset.get('file')} duplicates {previous[0].get('file')}")
                previous.append(asset)
            else:
                content_hashes[file_hash] = [asset]
                signature = visual_signature(path)
                for previous_file, previous_signature in visual_signatures:
                    if near_duplicate(signature, previous_signature):
                        failures.append(f"near-duplicate image content: {asset.get('file')} resembles {previous_file}; inspect the actual sources, do not edit pixels or weaken the check")
                        break
                visual_signatures.append((str(asset.get('file')), signature))
        if not identity_documented(asset):
            failures.append(f"source identity needs an exact-subject observation, not an official-domain label: {asset.get('file')}")
        if not args.machine_only and (not asset.get('visually_confirmed')):
            failures.append(f"visual confirmation pending: {asset.get('file')}")
        elif not args.machine_only and len(str(asset.get('visual_confirmation_note', '')).strip()) < 12:
            failures.append(f"visual confirmation note must state what proves exact-place identity: {asset.get('file')}")
        if not args.machine_only and (not asset.get('watermark_checked')):
            failures.append(f"full-size watermark inspection pending: {asset.get('file')}")
        if not args.machine_only and (not asset.get('subject_verified')):
            failures.append(f"subject verification pending: {asset.get('file')}")
        if not args.machine_only and asset.get('subject_verified') and (not (asset.get('source_identity_bound') and asset.get('visually_confirmed') and asset.get('watermark_checked') and decoded)):
            failures.append(f"subject_verified lacks evidence chain: {asset.get('file')}")
    if args.write:
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    media_audit = {'media_pass': not failures, 'counts': media_counts, 'failures': failures, 'warnings': warnings}
    for warning in warnings:
        print('WARN ' + warning)
    report_name = 'MEDIA_PREFLIGHT.json' if args.machine_only else 'MEDIA_AUDIT.json'
    (args.asset_root / report_name).write_text(json.dumps(media_audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if failures:
        for failure in failures:
            print('FAIL ' + failure)
        return 2
    print('PASS asset machine preflight; visual review remains pending' if args.machine_only else 'PASS every local image decodes and has complete exact-place provenance plus visual confirmation')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
