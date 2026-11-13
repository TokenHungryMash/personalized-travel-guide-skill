"""Local JSON Schema checks with readable field paths; no network schema lookup."""
import json
from pathlib import Path


def audit_schema(data, name='content', root=None, language=''):
    if name=='editorial-content':
        from language_fields import normalized_language_content
        data=normalized_language_content(data,language)
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError('Missing jsonschema. In the workbench run: python -m pip install -r requirements.txt') from exc
    schema = json.loads(((root or Path(__file__).parent) / f'{name}.schema.json').read_text(encoding='utf8'))
    Draft202012Validator.check_schema(schema)
    errors = []
    for error in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: str(list(e.absolute_path))):
        path = name + '.json'
        for part in error.absolute_path:
            path += f'[{part}]' if isinstance(part, int) else '.' + part
        context = ''
        parts = list(error.absolute_path)
        if len(parts) >= 2 and isinstance(parts[1], int):
            item = data[parts[0]][parts[1]]
            if isinstance(item, dict):
                context = ' (id=' + str(item.get('id', '?')) + ')'
        hint = '；day 是 0-based，0=第1天，不自动减1' if parts and parts[-1] == 'day' else ''
        if parts and parts[0]=='preparation' and parts[-1]=='id':
            hint += '；新任务使用 prep-entry-documents 等稳定ID（小写字母/数字/连字符）；已有任务须保留原ID及勾选语义，不自动重编号'
        errors.append(f'{path}{context}: {error.message}{hint}')
    return errors
