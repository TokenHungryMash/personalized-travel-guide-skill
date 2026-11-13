"""Check final inline HTML glyph coverage before publishing a release."""
from pathlib import Path
import base64
import hashlib
import json
import re
import font_supplement as fonts

def inspect_text(text):
    wanted = set(map(ord, fonts.CJK.findall(text)))
    faces = {}
    for rule in fonts.FACE.findall(text):
        props = fonts.declarations(rule)
        name = props.get('font-family', '').strip('\'"')
        data = re.search(r'data:font/woff2;base64,([A-Za-z0-9+/=]+)', rule)
        if not name:
            continue
        weight = props.get('font-weight', '400')
        coverage = faces.setdefault(name, {}).setdefault(weight, set())
        if data:
            coverage.update(fonts.covered_glyphs(base64.b64decode(data.group(1), validate=True), rule))
    required = []
    for role in ('body', 'serif'):
        values = re.findall(r'--font-' + role + r'\s*:\s*([^;}]+)', text)
        if not values:
            raise ValueError(f'Missing --font-{role} configuration')
        candidates = [name.strip().strip('\'"') for name in values[-1].split(',')]
        family = next((name for name in candidates if name in faces), None)
        if family is None:
            raise ValueError(f'Configured {role} family must be embedded')
        required.append(family)
    report = {}
    for family in required:
        missing_by_weight = {weight: ''.join(map(chr, sorted(wanted - glyphs)))
                             for weight, glyphs in faces[family].items()}
        missing = set(''.join(missing_by_weight.values()))
        report[family] = dict(needed=len(wanted), missing=''.join(sorted(missing)), weights=missing_by_weight)
    return report


def inspect(file):
    return inspect_text(Path(file).read_text(encoding='utf8'))

def check_final_html(root, text, stage, build_id):
    coverage = inspect_text(text)
    missing = any(item['missing'] for item in coverage.values())
    report = {'buildId': build_id, 'sha256': hashlib.sha256(text.encode('utf8')).hexdigest(),
              'stage': stage, 'result': 'missing-glyphs' if missing else 'pass', 'coverage': coverage}
    folder = Path(root) / 'qa-fonts'
    folder.mkdir(exist_ok=True)
    (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if missing:
        detail = '; '.join(f"{family}: {item['missing']}" for family,item in coverage.items() if item['missing'])
        message = 'Final HTML font coverage failed: '+detail+'. Run python -X utf8 font_supplement.py, then rebuild; see qa-fonts/report.json.'
        if stage == 'release':
            raise ValueError(message+' Existing release and manifest were not replaced.')
        print('PREVIEW WARNING: '+message)
    else:
        print('PASS final HTML embedded CJK font coverage (all configured weights).')
    return report
