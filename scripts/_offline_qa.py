"""Hash-bound acceptance of the actual exported artifact, separate from preview QA."""
import hashlib
import json
from pathlib import Path
from _manual_qa import build_fingerprint

CHECKS = ('chapter_navigation', 'disclosures', 'trip_mode', 'trip_day_switch', 'map_viewer')

def read(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def export_state(root):
    root = Path(root)
    receipt = read(root / 'offline-export.json')
    artifact = Path(receipt.get('file') or '') if isinstance(receipt.get('file', ''), str) else Path('')
    if (not artifact.is_file() or receipt.get('build_fingerprint') != build_fingerprint(root)
            or hashlib.sha256(artifact.read_bytes()).hexdigest() != receipt.get('sha256')):
        return 'offline_export_required', 'Export is missing or changed; run check_handoff.py.', False
    qa = read(root / 'offline-qa.json')
    if qa.get('export_sha256') != receipt['sha256']:
        return 'offline_qa_required', 'Test the actual exported HTML; save hash-bound offline-qa.json.', False
    if qa.get('status') == 'passed' and qa.get('validation_mode') == 'browser' and isinstance(qa.get('checks'), dict):
        if all(isinstance(qa.get('checks', {}).get(k), dict)
               and qa['checks'][k].get('passed') is True
               and str(qa['checks'][k].get('note', '')).strip() for k in CHECKS):
            if all(str(qa.get(k, '')).strip() for k in ('tested_url', 'tool_reference', 'checked_at')):
                return 'complete', 'Exported artifact interactions verified.', False
    limitation = qa.get('host_limitation', {})
    if not isinstance(limitation, dict): limitation = {}
    blocked = (qa.get('validation_mode') == 'unavailable' and qa.get('status') == 'pending'
               and all(isinstance(limitation.get(k), str) and limitation[k].strip()
                       for k in ('reason', 'tool_reference', 'checked_at')))
    return 'offline_qa_required', 'Export QA pending; a host limitation is not a pass.', blocked
