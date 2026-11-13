"""Audit authored travel content using the same rules as the builder."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
from workbench_input import resolve_workbench, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    root = resolve_workbench(parser, args.workbench, ('content.json',))
    module_path = Path(__file__).resolve().parents[1] / 'assets/destination-reference/travel_content.py'
    spec = importlib.util.spec_from_file_location('travel_content', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.insert(0, str(module_path.parent))
    from schema_check import audit_schema
    guide = read_json(parser, root, 'content.json')
    errors = audit_schema(guide)
    if not errors:
        errors = module.audit_content(guide)
    print('\n'.join(errors) if errors else 'PASS travel content minimums')
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
