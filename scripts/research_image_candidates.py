"""Resolve place identity, then collect a cached top-N image shortlist."""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, html, json, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from inspect_research_json import summarize_candidates
from probe_official_page import probe
from _official_images import matching, is_ui_image
from _official_classification import classify, shared_artwork_urls
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
UA = 'Mozilla/5.0 travel-guide-image-research/2.0'
GENERIC = re.compile('(?:logo|default|share|sns|banner|favicon|sprite|portrait|concert|event|celebrity)', re.I)
UI_IMAGE = re.compile('(?:globalnavi|(?:^|[/_\\-])(?:icon|nav|menu|button|spacer|loading)|banner|basketball|バスケット)', re.I)

def place_kind(row):
    raw = ' '.join((str(row.get(key) or '').lower() for key in ('kind', 'type', 'place_kind')))
    if row.get('product_name') or any((word in raw for word in ('souvenir', 'product', '伴手礼', '纪念品'))):
        return 'souvenir'
    return next((kind for kind in ('restaurant', 'shop', 'hotel', 'experience', 'sight') if kind in raw), raw)

def product_candidates(row, limit):
    """Products have no geographic fallback. Follow at most two exact same-site links."""
    name = row.get('product_name') or row.get('display_name') or row.get('local_name')
    result = {**row, 'resolved_identity': {'wikidata_id': None, 'coordinates': [row['latitude'], row['longitude']] if row.get('latitude') is not None and row.get('longitude') is not None else None}, 'candidates': [], 'brand_fallback_candidates': [], 'errors': [], 'search_stopped': 'product-only official ladder; geographic/open-media fallback disabled'}
    if not name or not row.get('official_url'):
        return {**result, 'product_media_status': 'needs_product_input', 'next_action': 'Supply exact product_name and official_url; do not run nearby-place image search'}
    pages = [(row['official_url'], probe(row['official_url'], product_name=name))]
    seen = set()
    for page_url, page in pages:
        if page_url in seen:
            continue
        seen.add(page_url)
        if page.get('status') not in {'ok', 'no_image'}:
            result['errors'].append({'source': 'official_product', 'url': page_url, 'error': page.get('status')})
            continue
        page_slug = urllib.parse.urlsplit(page_url).path.rstrip('/').rsplit('/', 1)[-1]
        title_matches = matching(name, page.get('title', ''))
        for image in page.get('images', []):
            context = image.get('context', '')
            url = image['url']
            hint = context + ' ' + url
            logo = bool(re.search('logo', url, re.I))
            share = image.get('metadata_key', '').startswith(('og:', 'twitter:'))
            if logo or share:
                brand = row.get('brand_name')
                if brand and (matching(brand, context) or (share and matching(brand, page.get('title', '')))):
                    result['brand_fallback_candidates'].append(item('official_product_brand', page_url, url, context or page.get('title', ''), 60, source_type='official', media_class='official_brand_asset', original_media_class='official_brand_asset', visual_subject_type='official_logo' if logo else 'official_share_card', brand_name=brand, product_name=name, brand_relationship_verification_required=True))
                continue
            if is_ui_image(url) or UI_IMAGE.search(hint):
                continue
            exact = matching(name, context)
            aliases = [value for value in row.get('product_aliases', []) if isinstance(value, str)]
            alias = any((matching(value, context + ' ' + urllib.parse.unquote(url)) for value in aliases))
            slug_hint = title_matches and len(page_slug) >= 4 and (page_slug.casefold() in Path(urllib.parse.urlsplit(url).path).stem.casefold())
            if not (exact or alias or slug_hint):
                continue
            risks = ['promotional hero candidate: inspect packaging versus banner/composite'] if re.search(r'mainimg|mainvisual|hero|キービジュアル', hint, re.I) else []
            result['candidates'].append(item('official_product_image', page_url, url, context.strip() or name, (100 if exact else 85) - (40 if risks else 0), candidate_risks=risks, visual_subject_type='product', product_name=name, product_identity_evidence='exact name in image/JSON-LD context' if exact else 'explicit product alias' if alias else 'product page title plus matching image filename; visual review required', metadata_key=image.get('metadata_key'), identity_check_required=True))
        if any(not c.get('candidate_risks') for c in result['candidates']):
            break
        if len(pages) == 1:
            links = list(dict.fromkeys((link['url'] for link in page.get('product_links', []) if link['url'] not in seen)))[:2]
            pages.extend(((url, probe(url, product_name=name)) for url in links))
    result['candidates'] = sorted({candidate['image_url']: candidate for candidate in result['candidates']}.values(), key=lambda c: c['candidate_score'], reverse=True)[:limit]
    result['brand_fallback_candidates'] = list({candidate['image_url']: candidate for candidate in result['brand_fallback_candidates']}.values())[:2]
    if result['candidates']:
        result.update(product_media_status='product_candidates', next_action='Probe/decode these candidates once and visually confirm the exact product; never substitute a street scene')
    elif result['brand_fallback_candidates']:
        result.update(product_media_status='brand_fallback_available', next_action='In standard mode confirm product-to-brand relationship, then use an official_brand_asset with official_logo/official_share_card; do not label it product photography')
    else:
        result.update(product_media_status='product_media_gap', next_action='Official product lookup has no qualified photo. Inspect one reputable exact-product retailer or tourism source and check permitted use; record actual URLs/results in .research-state/candidate-ledger.json. This helper has not searched that alternate. Only after that bounded attempt fails, or an explicit access denial blocks it, retain images: [] with the reason and buying advice. Never treat missing input or parser no_image as proof that no photo exists; do not widen to geographic images.')
    return result

def fetch(url: str, as_json: bool=False):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json' if as_json else 'text/html'})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.load(response) if as_json else response.read(1500000).decode('utf-8', 'replace')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt:
                raise
            time.sleep(1)

def item(source, page, image, title='', score=0, **extra):
    return {'source': source, 'source_page': page, 'image_url': html.unescape(image), 'title': title, 'candidate_score': score, 'status': 'candidate', 'subject_verified': False, 'visually_confirmed': False, **extra}

def words(value):
    return {part for part in re.split('[^\\w\\u3400-\\u9fff]+', str(value).casefold()) if len(part) > 1}

def rank_score(row, candidate):
    haystack = ' '.join((str(candidate.get(k, '')) for k in ('title', 'context', 'source_page')))
    query = ' '.join((str(row.get(k, '')) for k in ('query', 'local_name', 'english_name', 'city', 'country')))
    score = int(candidate.get('candidate_score', 0)) + min(24, len(words(haystack) & words(query)) * 4)
    return score - (40 if GENERIC.search(haystack + ' ' + str(candidate.get('image_url', ''))) else 0)

def official(row, page_data=None, shared_urls=()):
    page = row.get('official_url')
    if not page:
        return []
    data = page_data if page_data is not None else probe(page, product_name=row.get('english_name') or row.get('local_name') or row.get('display_name') or row.get('query'))
    if data.get('status') not in {'ok', 'no_image'}:
        raise ValueError(f"official page probe: {data.get('status')}")
    results = []
    for classified in classify(row, data, shared_urls):
        results.append(item(classified['source'], data.get('final_url', page), classified['url'], classified.get('context') or row.get('query', ''), classified['candidate_score'], **{key: classified[key] for key in ('entity_bound', 'media_class', 'original_media_class', 'shared_site_artwork', 'classification_reason')}, **{'visual_subject_type': classified['visual_subject_type']} if classified.get('visual_subject_type') else {}))
    return results

def claim_coordinates(claims):
    try:
        value = claims['P625'][0]['mainsnak']['datavalue']['value']
        return (float(value['latitude']), float(value['longitude']))
    except (KeyError, IndexError, TypeError, ValueError):
        return None

def wikidata(row):
    query = ' '.join((str(row.get(k, '')) for k in ('query', 'city', 'country'))).strip()
    entity_query = str(row.get('english_name') or row.get('query') or row.get('local_name') or '').strip()
    ids = [row['wikidata_id']] if row.get('wikidata_id') else []
    params = urllib.parse.urlencode({'action': 'wbsearchentities', 'search': entity_query, 'language': 'en', 'format': 'json', 'limit': 3})
    ids.extend((hit['id'] for hit in fetch('https://www.wikidata.org/w/api.php?' + params, True).get('search', []) if hit['id'] not in ids))
    result, coords, chosen = ([], None, None)
    for entity_id in ids[:3]:
        entity = fetch(f'https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json', True).get('entities', {}).get(entity_id, {})
        claims, labels, descriptions = (entity.get('claims', {}), entity.get('labels', {}), entity.get('descriptions', {}))
        label = (labels.get('en') or next(iter(labels.values()), {})).get('value', '')
        context = (descriptions.get('en') or next(iter(descriptions.values()), {})).get('value', '')
        if not words(label + ' ' + context) & words(query):
            continue
        coords, chosen = (claim_coordinates(claims) or coords, entity_id)
        for claim in claims.get('P18', [])[:2]:
            filename = claim['mainsnak']['datavalue']['value']
            params = urllib.parse.urlencode({'action': 'query', 'titles': f'File:{filename}', 'prop': 'imageinfo', 'iiprop': 'url|mime|extmetadata', 'iiurlwidth': 1600, 'format': 'json'})
            page = next(iter(fetch('https://commons.wikimedia.org/w/api.php?' + params, True).get('query', {}).get('pages', {}).values()), {})
            info = (page.get('imageinfo') or [{}])[0]
            url = info.get('thumburl') or info.get('url')
            if url:
                result.append(item('wikidata_p18', f'https://www.wikidata.org/wiki/{entity_id}', url, label, 90, entity_id=entity_id, context=context, coordinates=coords, license_metadata=info.get('extmetadata', {}), identity_check_required=True))
        if result:
            break
    return (result, coords, chosen)

def commons_geo(row, coords, entity_id):
    if not coords:
        return []
    radius = max(50, min(int(row.get('radius_m', 400)), 1000))
    params = urllib.parse.urlencode({'action': 'query', 'generator': 'geosearch', 'ggsprimary': 'all', 'ggsnamespace': 6, 'ggsradius': radius, 'ggscoord': f'{coords[0]}|{coords[1]}', 'ggslimit': 8, 'prop': 'imageinfo|coordinates', 'iiprop': 'url|mime|extmetadata', 'iiurlwidth': 1600, 'format': 'json'})
    result = []
    for page in fetch('https://commons.wikimedia.org/w/api.php?' + params, True).get('query', {}).get('pages', {}).values():
        info = (page.get('imageinfo') or [{}])[0]
        url, title = (info.get('thumburl') or info.get('url'), page.get('title', ''))
        if not url or GENERIC.search(title):
            continue
        point = (page.get('coordinates') or [{}])[0]
        result.append(item('commons_geosearch', f"https://commons.wikimedia.org/?curid={page.get('pageid')}", url, title, 60, entity_id=entity_id, coordinates=[point.get('lat'), point.get('lon')], radius_m=radius, license_metadata=info.get('extmetadata', {}), identity_check_required=True))
    return result[:4]

def openverse(row):
    query = ' '.join((str(row.get(k, '')) for k in ('query', 'city', 'country'))).strip()
    api = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode({'q': query, 'page_size': 5, 'mature': 'false'})
    result = []
    for found in fetch(api, True).get('results', []):
        image = found.get('url') or found.get('thumbnail')
        if image and (not GENERIC.search((found.get('title') or '') + ' ' + image)):
            result.append(item('openverse', found.get('foreign_landing_url') or found.get('detail_url') or api, image, found.get('title') or '', 20, license=found.get('license'), creator=found.get('creator'), identity_check_required=True))
    return result[:3]

def collect(row, limit, page_data=None, shared_urls=()):
    if place_kind(row) in {'restaurant', 'shop', 'hotel', 'experience'} and not row.get('official_url'):
        return {**row, 'candidates': [], 'errors': [], 'search_stopped': 'official source not supplied; source search has not been exhausted', 'next_action': 'Supply a verified exact-branch official_url from existing identity research or inspect an exact-branch listing; do not search Commons for other branches', 'input_status': 'needs_official_url'}
    if place_kind(row) == 'souvenir':
        return product_candidates(row, limit)
    candidates, errors, entity_id = ([], [], row.get('wikidata_id'))
    coords = (float(row['latitude']), float(row['longitude'])) if row.get('latitude') is not None and row.get('longitude') is not None else None
    for name, resolver in (('official', lambda: official(row, page_data, shared_urls)),):
        try:
            candidates.extend(resolver())
        except Exception as error:
            errors.append({'source': name, 'error': type(error).__name__})
    commercial = place_kind(row) in {'restaurant', 'shop', 'hotel', 'experience', 'souvenir'}
    artwork = [candidate for candidate in candidates if candidate.get('media_class') == 'official_brand_asset']
    candidates = [candidate for candidate in candidates if candidate.get('entity_bound') and candidate.get('media_class') != 'official_brand_asset']
    allowed_brand = [candidate for candidate in artwork if candidate.get('entity_bound') and (not candidate.get('shared_site_artwork'))]
    if candidates or allowed_brand:
        candidates = candidates or allowed_brand
        ranked = sorted(candidates, key=lambda candidate: rank_score(row, candidate), reverse=True)
        return {**row, 'resolved_identity': {'wikidata_id': entity_id, 'coordinates': coords}, 'candidates': ranked[:limit], 'official_artwork': artwork, 'errors': errors, 'search_stopped': 'identity-bearing official candidates found; artwork stays semantically classified'}
    if commercial:
        return {**row, 'resolved_identity': {'wikidata_id': entity_id, 'coordinates': coords}, 'candidates': [], 'official_artwork': artwork, 'errors': errors, 'search_stopped': 'commercial official candidates exhausted; do not search open-media libraries for branch photography', 'next_action': 'inspect one exact-branch listing or clearly associated official logo/share card; otherwise replace this candidate once'}
    try:
        found, resolved, entity_id = wikidata(row)
        candidates.extend(found)
        coords = coords or resolved
    except Exception as error:
        errors.append({'source': 'wikidata', 'error': type(error).__name__})
    fallback_resolvers = (('commons_geosearch', lambda: commons_geo(row, coords, entity_id)), ('openverse', lambda: openverse(row)))
    for name, resolver in fallback_resolvers:
        try:
            candidates.extend(resolver())
        except Exception as error:
            errors.append({'source': name, 'error': type(error).__name__})
    unique = {}
    for candidate in candidates:
        candidate['candidate_score'] = rank_score(row, candidate)
        key = candidate['image_url'].split('?')[0]
        if key not in unique or candidate['candidate_score'] > unique[key]['candidate_score']:
            unique[key] = candidate
    ranked = sorted(unique.values(), key=lambda x: x['candidate_score'], reverse=True)
    return {**row, 'resolved_identity': {'wikidata_id': entity_id, 'coordinates': coords}, 'candidates': ranked[:limit], 'official_artwork': artwork, 'errors': errors, 'search_stopped': 'bounded photo ladder completed; shared site artwork cannot stand in for this venue'}

def cache_key(row, limit):
    return hashlib.sha256(json.dumps({'v': 8, 'row': row, 'limit': limit}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('requests', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--per-place', type=int, default=2)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    try:
        rows = json.loads(args.requests.read_text(encoding='utf-8-sig'))
        if not isinstance(rows, list) or any((not isinstance(row, dict) or not (row.get('id') or row.get('query')) for row in rows)):
            raise ValueError('requests JSON must be an array of objects with id or query')
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({'status': 'input_missing' if isinstance(error, FileNotFoundError) else 'input_invalid', 'source_file': str(args.requests.resolve()), 'error': str(error)}, ensure_ascii=False))
        return 2
    limit = max(1, min(args.per_place, 6))
    cache_path = args.output.parent / '.image-candidate-cache.json'
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        cache = {}
    results, work = ([None] * len(rows), [])
    for index, row in enumerate(rows):
        key = cache_key(row, limit)
        if not args.refresh and key in cache:
            results[index] = cache[key]
        else:
            work.append((index, key, row))
    page_rows = {row['official_url']: row for _, _, row in work if row.get('official_url') and place_kind(row) != 'souvenir'}
    pages = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 3))) as pool:
        futures = {pool.submit(probe, url, product_name=row.get('english_name') or row.get('local_name') or row.get('display_name') or row.get('query')): url for url, row in page_rows.items()}
        for future in concurrent.futures.as_completed(futures):
            pages[futures[future]] = future.result()
    shared_urls = shared_artwork_urls(pages)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 3))) as pool:
        futures = {pool.submit(collect, row, limit, pages.get(row.get('official_url')), shared_urls): (index, key) for index, key, row in work}
        for future in concurrent.futures.as_completed(futures):
            index, key = futures[future]
            results[index] = cache[key] = future.result()
    final = [row for row in results if row is not None]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summarize_candidates(final, source_file=args.output, cached=len(rows) - len(work)), ensure_ascii=False, indent=2))
    return 0
if __name__ == '__main__':
    sys.exit(main())
