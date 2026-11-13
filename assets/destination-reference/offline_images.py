"""Resize embedded photographs by use while preserving map pixels and source files."""
from pathlib import Path
import base64
import hashlib
import html
import io
import json
import math
import re
from collections import Counter

from PIL import Image, ImageOps

DEFAULTS = {'coverMaxEdge': 2560, 'spreadMaxEdge': 2000, 'placeMaxEdge': 900,
            'quality': 84, 'warnMiB': 30, 'deduplicate': True}
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.webp', '.png', '.gif', '.avif'}
DATA_IMAGE = r'data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=]+'


def settings(edition):
    config = DEFAULTS | edition.get('offlineImages', {})
    if not isinstance(config['deduplicate'],bool):raise ValueError('offlineImages.deduplicate must be boolean')
    for key in ('coverMaxEdge', 'spreadMaxEdge', 'placeMaxEdge'):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f'offlineImages.{key} must be a positive integer')
    if isinstance(config['quality'], bool) or not isinstance(config['quality'], int) or not 1 <= config['quality'] <= 100:
        raise ValueError('offlineImages.quality must be an integer from 1 to 100')
    if isinstance(config['warnMiB'], bool) or not isinstance(config['warnMiB'], (int, float)) or not math.isfinite(config['warnMiB']) or config['warnMiB'] <= 0:
        raise ValueError('offlineImages.warnMiB must be a positive finite number')
    return config


def encode_image(payload, max_edge, quality, preserve=False):
    with Image.open(io.BytesIO(payload)) as opened:
        # Camera JPEGs may contain an MPF auxiliary image (for example an HDR
        # gain map). Pillow exposes these MPO files as multiple frames, but
        # they are still photographs, not timed animations. Embed the primary
        # frame and leave the original source bytes untouched.
        is_mpo = opened.format == 'MPO'
        if is_mpo:
            opened.seek(0)
        original_size = opened.size
        original_mime = Image.MIME.get(opened.format)
        if original_mime is None:
            raise ValueError(f'Unsupported image format: {opened.format}')
        if preserve or (getattr(opened, 'n_frames', 1) > 1 and not is_mpo):
            return payload, original_mime, original_size, original_size, 'original-map' if preserve else 'original-animation'
        orientation = opened.getexif().get(274, 1)
        image = ImageOps.exif_transpose(opened)
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        has_alpha = 'A' in image.getbands() or 'transparency' in opened.info
        image = image.convert('RGBA' if has_alpha else 'RGB')
        buffer = io.BytesIO()
        options = {'format': 'WEBP', 'method': 4, 'quality': quality, 'lossless': has_alpha}
        if opened.info.get('icc_profile') and opened.mode in ('RGB', 'RGBA'):
            options['icc_profile'] = opened.info['icc_profile']
        image.save(buffer, **options)
        encoded = buffer.getvalue()
        if not is_mpo and image.size == original_size and orientation == 1 and len(payload) <= len(encoded):
            return payload, original_mime, original_size, original_size, 'original-smaller'
        return encoded, 'image/webp', original_size, image.size, 'lossless-alpha' if has_alpha else 'webp'


def image_roles(root, edition, places, editorial, maps, config):
    roles = {}

    def add(entry, role, limit):
        for field in ('src', 'mobileSrc'):
            source = entry.get(field)
            if source and (source not in roles or limit > roles[source][1]):
                roles[source] = (role, limit)

    for entry in places.values():
        add(entry, 'place', config['placeMaxEdge'])
    for entry in editorial.values():
        add(entry, 'spread', config['spreadMaxEdge'])
    cover = (places | editorial).get(edition.get('cover'))
    if cover:
        add(cover, 'cover', config['coverMaxEdge'])
    for entry in maps.values():
        for field in ('src', 'mobileSrc'):
            if entry.get(field):
                roles[entry[field]] = ('map', 0)
    for folder in ('media', 'maps'):
        for path in (root / folder).rglob('*'):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                source = path.relative_to(root).as_posix()
                roles.setdefault(source, ('map', 0) if folder == 'maps' else ('spread', config['spreadMaxEdge']))
    return roles


def pool_images(markup,known_uris):
    """Keep the first static image visible; share subsequent static/data references.

    The application still receives ordinary data URLs. No blob lifecycle, network
    request, global fetch monkeypatch, or rewrite of a user's uploaded files.
    """
    counts=Counter(re.findall(DATA_IMAGE,markup))
    selected={uri:hashlib.sha256(uri.encode('ascii')).hexdigest() for uri in known_uris if counts[uri]>1}
    if not selected:return markup
    first={};used=set()
    def attribute(match):
        attr,quote,uri=match.groups()
        if uri not in selected:return match.group(0)
        key=selected[uri];used.add(key)
        if key not in first:
            first[key]=uri
            return match.group(0)+f' data-offline-asset-{attr}="{key}"'
        return f'data-offline-{attr}={quote}offline-image:{key}{quote}'
    markup=re.sub(r'\b(src|srcset|poster)=(["\x27])('+DATA_IMAGE+r')\2',attribute,markup)
    def refs(value):
        if isinstance(value,str) and value in selected:
            key=selected[value];used.add(key);return 'offline-image:'+key
        if isinstance(value,list):return [refs(item) for item in value]
        if isinstance(value,dict):return {key:refs(item) for key,item in value.items()}
        return value
    pattern=re.compile(r'(<script\b[^>]*\bid=["\x27]guide-data["\x27][^>]*>)(.*?)(</script>)',re.S)
    def guide(match):
        return match[1]+json.dumps(refs(json.loads(match[2])),ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')+match[3]
    markup=pattern.sub(guide,markup,count=1)
    if not used:return markup
    pool={key:uri for uri,key in selected.items() if key in used and key not in first}
    runtime=Path(__file__).with_name('offline-image-pool.js').read_text(encoding='utf8')
    bootstrap='<script id="offline-image-pool" type="application/json">'+json.dumps(pool,separators=(',',':'))+'</script><script>'+runtime+'</script>'
    match=pattern.search(markup)
    if match:return markup[:match.end()]+bootstrap+markup[match.end():]
    return markup.replace('</body>',bootstrap+'</body>',1) if '</body>' in markup else markup+bootstrap


def inline_images(root, markup, edition, places, editorial, maps):
    root = Path(root).resolve()
    config = settings(edition)
    roles = image_roles(root, edition, places, editorial, maps, config)
    cache = {}
    records = []
    original_total = 0
    embedded_total = 0
    source_uris = {}
    referenced_markup = markup
    for source, (role, limit) in roles.items():
        if source not in referenced_markup and html.escape(source, quote=True) not in referenced_markup:
            continue
        # Match complete local paths, including HTML-escaped attribute values.
        names = sorted({source, html.escape(source, quote=True)}, key=len, reverse=True)
        pattern = re.compile(r'(?<![\w./:%-])(?:' + '|'.join(re.escape(name) for name in names) + r')(?=[\s\"\x27)<> ,]|$)')
        count = len(pattern.findall(markup))
        if not count:
            continue
        path = (root / source).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'Embedded image is missing or outside workbench: {source}')
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        key = (digest, limit, config['quality'], role == 'map')
        cache_hit = key in cache
        if not cache_hit:
            cache[key] = encode_image(payload, limit, config['quality'], preserve=role == 'map')
        encoded, mime, before, after, mode = cache[key]
        uri = 'data:' + mime + ';base64,' + base64.b64encode(encoded).decode('ascii')
        source_uris[source]=uri
        markup = pattern.sub(lambda match: uri, markup)
        original_total += count * (len(base64.b64encode(payload)) + len('data:' + mime + ';base64,'))
        embedded_total += count * len(uri)
        records.append(dict(source=source, role=role, sourceBytes=len(payload), payloadBytes=len(encoded),
                            originalSize=list(before), embeddedSize=list(after), occurrences=count,
                            embeddedBytes=count * len(uri), encoding=mode, cacheHit=cache_hit))
    expanded_total=embedded_total
    if config['deduplicate']:
        markup=pool_images(markup,set(source_uris.values()))
    stored_counts=Counter(re.findall(DATA_IMAGE,markup))
    stored={uri:stored_counts[uri]*len(uri) for uri in set(source_uris.values())}
    embedded_total=sum(stored.values())
    unique_total=sum(len(uri) for uri in stored if stored_counts[uri])
    assigned=set()
    for record in records:
        uri=source_uris[record['source']]
        record['referenceBytes']=record['embeddedBytes']
        record['embeddedBytes']=0 if uri in assigned else stored[uri]
        assigned.add(uri)
    report = dict(configuration=config, images=sorted(records, key=lambda item: item['embeddedBytes'], reverse=True),
                  referencedFiles=len(records), conversions=len(cache), imageBytes=embedded_total,
                  uniqueImageBytes=unique_total, repeatedImageBytes=embedded_total - unique_total,
                  compressionSavedImageBytes=original_total-expanded_total,dedupSavedImageBytes=expanded_total-embedded_total,
                  originalImageBytes=original_total, savedImageBytes=original_total - embedded_total)
    return markup, report


def write_size_report(root, artifact, report, build_id):
    root = Path(root)
    artifact = Path(artifact)
    payload = artifact.read_bytes()
    report = dict(report, artifact=artifact.name, buildId=build_id,
                  sha256=hashlib.sha256(payload).hexdigest(), artifactBytes=len(payload))
    limit = report['configuration']['warnMiB'] * 1024 * 1024
    report['overThreshold'] = len(payload) > limit
    report['otherBytes'] = len(payload) - report['imageBytes']
    target = root / 'qa-size' / 'report.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    label = 'WARNING' if report['overThreshold'] else 'SIZE'
    print(f'{label}: HTML {len(payload) / 1048576:.1f} MiB; images {report["imageBytes"] / 1048576:.1f} MiB; '
          f'saved {report["savedImageBytes"] / 1048576:.1f} MiB; repeated image payload {report["repeatedImageBytes"] / 1048576:.1f} MiB.')
    if report['overThreshold']:
        print(f'WARNING: HTML exceeds offlineImages.warnMiB ({report["configuration"]["warnMiB"]}); '
              'review largest assets and repeated placements in qa-size/report.json.')
    return report
