"""Find outline-only prose and repeated copy; never certify usefulness by length."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re


def compact(value):
    return re.sub(r'\s+', '', value or '')


def body(rows):
    return '\n\n'.join(value for row in rows if isinstance(row, list)
                       for value in row[1:] if isinstance(value, str))


def audit(guide, editorial):
    errors, candidates, metrics = [], [], {}
    sections = {key: editorial.get(key, []) for key in ('portrait', 'stays', 'culture', 'shopping')}
    sections.update({'areas:' + a['id']: editorial.get('area_sections', {}).get(a['id'], [])
                     for a in guide.get('areas', [])})
    sections.update({'notes:' + key: value for key, value in editorial.get('notes', {}).items()})
    for key, rows in sections.items():
        text = compact(body(rows))
        metrics[key] = {'rows': len(rows), 'bodyCharacters': len(text)}
        if not text:
            errors.append(f'{key}: missing authored body')
    for area in guide.get('areas', []):
        deck = compact(area.get('deck', ''))
        prose = body(editorial.get('area_sections', {}).get(area['id'], []))
        if len(deck) >= 24 and deck in {compact(p) for p in prose.split('\n\n')}:
            errors.append(f'areas:{area["id"]}: body repeats the deck verbatim instead of adding information')
    groups = defaultdict(list)
    for item in editorial.get('route_experiences', []):
        text = compact(item.get('copy', ''))
        if len(text) >= 24:
            groups[text].append(item.get('areaId', '?'))
    for text, ids in groups.items():
        if len(ids) > 1:
            errors.append('experiences:' + ','.join(ids) + ': same full description reused across regions')
    sentences = defaultdict(set)
    for place in guide.get('places', []):
        for key in ('desc', 'walk', 'tip'):
            for text in re.split(r'[。！？\n]', place.get(key, '')):
                text = compact(text)
                if len(text) >= 24:
                    sentences[text].add(place['id'])
    for text, ids in sentences.items():
        if len(ids) >= 3:
            candidates.append({'places': sorted(ids), 'text': text,
                               'reason': 'repeated prose: keep only if this condition applies, never to pad length'})
    return {'errors': errors, 'reviewCandidates': candidates, 'metrics': metrics,
            'note': 'Counts flag suspicious drafts only. Read the page and record decisions in editorial-review.md; no numeric result proves content quality.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    from workbench_input import resolve_workbench, read_json
    root = resolve_workbench(parser, args.workbench, ('content.json', 'editorial-content.json'))
    result = audit(read_json(parser, root, 'content.json'), read_json(parser, root, 'editorial-content.json'))
    review = root / 'editorial-review.md'
    if not review.is_file() or not review.read_text(encoding='utf8').strip():
        result['errors'].append('editorial-review.md: missing actual page-based editorial review')
    result['result'] = 'fail' if result['errors'] else ('review-needed' if result['reviewCandidates'] else 'structural-pass')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(result['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
