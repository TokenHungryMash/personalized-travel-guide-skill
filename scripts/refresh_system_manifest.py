#!/usr/bin/env python3
"""Re-sign intended component updates; use only after reviewing the changed bundle."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'assets/current-system'
target=root/'manifest.json';data=json.loads(target.read_text('utf8'))
data['files']={str(f.relative_to(root)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for directory in ['product','runtime','cloudflare'] for f in sorted((root/directory).rglob('*')) if f.is_file()}
target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print('Updated',len(data['files']),'bundle hashes; run restore and affected behavior checks before release.')
