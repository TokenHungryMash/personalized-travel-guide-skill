"""Validate a workbench argument before constructing child paths."""
from pathlib import Path
import json


def resolve_workbench(parser, value, required=()):
    root = Path(value).expanduser().resolve()
    if root.is_file():
        parser.error(f'Expected a workbench directory, got file: {root}. Pass its parent directory: {root.parent}')
    if not root.is_dir():
        parser.error(f'Workbench directory does not exist: {root}')
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        parser.error(f'{root}: missing required files: {", ".join(missing)}')
    return root


def read_json(parser, root, name):
    try:
        return json.loads((root / name).read_text(encoding='utf8'))
    except (OSError, ValueError) as exc:
        parser.error(f'{root / name}: {exc}')
