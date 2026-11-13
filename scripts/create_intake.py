"""Create a standalone intake questionnaire with known trip details filled in."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--destination')
    parser.add_argument('--days', type=int, choices=range(1, 61), metavar='1–60')
    parser.add_argument('--notes')
    parser.add_argument('--prefill', type=Path, help='JSON object of known form values')
    args = parser.parse_args()
    fields = json.loads(args.prefill.read_text(encoding='utf-8-sig')) if args.prefill else {}
    if not isinstance(fields, dict):
        parser.error('prefill must be a JSON object')
    fields.update({key: value for key in ('destination', 'days', 'notes')
                   if (value := getattr(args, key)) is not None})
    fields.pop('requestMode', None)
    output = args.output.resolve()
    draft_id = hashlib.sha256(str(output).encode('utf8')).hexdigest()[:16]
    payload = json.dumps({'draftId': draft_id, 'fields': fields}, ensure_ascii=False)
    payload = payload.replace('<', '\\u003c')
    template = Path(__file__).resolve().parents[1] / 'assets/intake-questionnaire/index.html'
    marker = 'id="intake-prefill">{}</script>'
    html = template.read_text(encoding='utf8')
    if html.count(marker) != 1:
        parser.error('template prefill marker is missing or duplicated')
    with output.open('x', encoding='utf8') as stream:
        stream.write(html.replace(marker, 'id="intake-prefill">' + payload + '</script>'))
    print(output)


if __name__ == '__main__':
    main()
