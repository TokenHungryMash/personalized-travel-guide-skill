"""Evidence gate shared by overview import and release checks."""
import hashlib

def checked_file(root, name, digest):
    path = (root / name).resolve()
    if not name or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('missing/unsafe overview evidence: ' + str(name))
    if not path.stat().st_size or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('stale/empty overview evidence: ' + name)
    return path

def verify_evidence(root, row):
    if row.get('visual_reviewed') is not True or not str(row.get('review_note', '')).strip():
        raise ValueError('overview needs actual visual review')
    if not row.get('source_url') or not row.get('attribution'):
        raise ValueError('overview needs real geographic source and attribution')
    checked_file(root, row.get('background_file', ''), row.get('background_sha256'))
    attempts = row.get('attempts', [])
    if not attempts:
        raise ValueError('original offline capture must be attempted before fallback')
    for attempt in attempts:
        if attempt.get('status') not in ('failed', 'denied') or not attempt.get('reason') or not attempt.get('checked_at'):
            raise ValueError('invalid original-map failure evidence')
        checked_file(root, attempt.get('log_file', ''), attempt.get('log_sha256'))
