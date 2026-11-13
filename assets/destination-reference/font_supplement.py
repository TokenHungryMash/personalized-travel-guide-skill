"""Incrementally supplement the configured CJK font families without replacing active files."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fontTools.ttLib import TTFont
import base64
import hashlib
import io
import os
import re
import tempfile
import urllib.parse
import urllib.request

CJK = re.compile(r'[\u3000-\u9fff\uff00-\uffef\U00020000-\U0002ffff]')
FACE = re.compile(r'@font-face\s*\{[^}]+\}', re.I)


def declarations(rule):
    return {key.lower(): value.strip() for key, value in re.findall(r'([\w-]+)\s*:\s*([^;{}]+)', rule)}


def covered_glyphs(payload, rule):
    with TTFont(io.BytesIO(payload)) as font:
        covered = set(font.getBestCmap() or {})
    ranges = declarations(rule).get('unicode-range')
    if ranges:
        permitted = set()
        for token in ranges.split(','):
            value = token.strip().upper().removeprefix('U+')
            if '?' in value:
                low, high = value.replace('?', '0'), value.replace('?', 'F')
            else:
                low, _, high = value.partition('-')
                high = high or low
            permitted.update(range(int(low, 16), int(high, 16) + 1))
        covered &= permitted
    return covered


def font_bytes(root, rule):
    match = re.search(r'url\(\s*[\'"]?([^\)\'"\s]+)', rule, re.I)
    if not match:
        raise ValueError('Font face lacks a readable src URL')
    url = match.group(1)
    if url.startswith('data:'):
        return base64.b64decode(url.split(',', 1)[1], validate=True)
    path = (root / urllib.parse.unquote(url)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Font path leaves workbench: {url}')
    return path.read_bytes()


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        temp.write(payload)
        temporary = Path(temp.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def download_subset(job):
    family, google, weight, chars = job
    url = 'https://fonts.googleapis.com/css2?' + urllib.parse.urlencode({
        'family': f'{google}:wght@{weight}', 'display': 'swap', 'text': chars,
    })
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    css = urllib.request.urlopen(request, timeout=30).read().decode()
    payloads = []
    coverage = set()
    for rule in FACE.findall(css):
        asset = re.search(r'url\(\s*[\'"]?([^\)\'"\s]+)', rule).group(1)
        payload = urllib.request.urlopen(asset, timeout=30).read()
        coverage |= covered_glyphs(payload, rule)
        with TTFont(io.BytesIO(payload)) as font:
            font.flavor = 'woff2'
            buffer = io.BytesIO()
            font.save(buffer)
        payload = buffer.getvalue()
        name = f'extra-{weight}-{hashlib.sha256(payload).hexdigest()}.woff2'
        glyphs = covered_glyphs(payload, rule) & set(map(ord, chars))
        if glyphs:
            ranges = ','.join(f'U+{code:X}' for code in sorted(glyphs))
            local_rule = (f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};"
                          f"font-display:swap;src:url(fonts/{name}) format('woff2');unicode-range:{ranges};}}")
            payloads.append((name, payload, local_rule, url + '\n' + asset))
    missing = set(map(ord, chars)) - coverage
    if missing:
        raise ValueError(f'{family} weight {weight}: download missing ' + ''.join(map(chr, sorted(missing))))
    return payloads


def supplement(root, fetch=download_subset):
    root = Path(root).resolve()
    inputs = [root / 'index.html', *root.glob('*.js'), *root.glob('*.css')]
    needed = set(map(ord, CJK.findall(''.join(path.read_text(encoding='utf8') for path in inputs))))
    supplement_path = root / 'font-supplement.css'
    existing = supplement_path.read_text(encoding='utf8') if supplement_path.exists() else ''
    jobs = []
    for filename, google in [('body-font.css', 'Noto Sans SC'), ('serif-font.css', 'Noto Serif SC')]:
        base = (root / filename).read_text(encoding='utf8')
        faces = FACE.findall(base)
        if not faces:
            raise ValueError(f'{filename}: no font faces')
        family = declarations(faces[0])['font-family'].strip('\'"')
        weights = sorted({declarations(rule).get('font-weight', '400') for rule in faces})
        for weight in weights:
            covered = set()
            for rule in faces + FACE.findall(existing):
                props = declarations(rule)
                if props.get('font-family', '').strip('\'"') == family and props.get('font-weight', '400') == weight:
                    covered |= covered_glyphs(font_bytes(root, rule), rule)
            chars = ''.join(map(chr, sorted(needed - covered)))
            for offset in range(0, len(chars), 250):
                jobs.append((family, google, weight, chars[offset:offset + 250]))
    if not jobs:
        return 0
    # Finish every download before publishing any new CSS reference.
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, jobs))
    rules = []
    for group in results:
        for name, payload, rule, provenance in group:
            atomic_write(root / 'fonts' / name, payload)
            atomic_write(root / 'fonts' / (name + '.source.txt'), provenance.encode('utf8'))
            rules.append(rule)
    atomic_write(supplement_path, (existing.rstrip() + '\n' + '\n'.join(rules) + '\n').encode('utf8'))
    return len(rules)


if __name__ == '__main__':
    print('PASS: added', supplement(Path(__file__).parent), 'font subsets; existing coverage preserved')
