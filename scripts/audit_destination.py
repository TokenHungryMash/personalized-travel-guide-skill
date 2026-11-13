"""Audit destination prose, day references and optional reference-city leftovers."""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from workbench_input import resolve_workbench, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    root = resolve_workbench(parser, args.workbench, ('content.json','edition.json','editorial-content.json'))
    template = Path(__file__).resolve().parents[1] / 'assets/destination-reference'
    sys.path.insert(0, str(template))
    spec = importlib.util.spec_from_file_location('destination_content', template / 'destination_content.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def read(name):
        return read_json(parser, root, name)
    guide, edition, editorial = [read(name) for name in ('content.json', 'edition.json', 'editorial-content.json')]
    errors = module.audit_relationships(guide, edition, editorial)
    metadata_path = root / 'magazine-workbench.json'
    metadata = read('magazine-workbench.json') if metadata_path.exists() else {}
    reference = metadata.get('reference_identity')
    if reference is None and metadata.get('reference_destination') == 'Bali':
        reference = {'city': '巴厘岛', 'english': 'BALI', 'country': 'INDONESIA',
                     'currency': 'IDR', 'languageName': '印尼语'}
    warnings = []
    if reference and edition['city'] != reference['city']:
        terms = [value for key, value in reference.items() if value != edition.get(key)]
        for label, content in [('content', guide), ('edition', edition), ('editorial', editorial)]:
            for path, value in module.text_fields(content, label):
                for term in terms:
                    pattern = rf'(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])' if term.isascii() else re.escape(term)
                    if re.search(pattern, value, re.IGNORECASE):
                        warnings.append({'path': path, 'referenceTerm': term, 'text': value})
    result = {'errors': errors, 'reviewCandidates': warnings,
              'note': 'Review candidates may be legitimate comparisons. Inspect context. CSS, scripts and encoded media are excluded.'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
