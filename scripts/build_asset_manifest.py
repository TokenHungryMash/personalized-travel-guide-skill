"""Build a provenance manifest from destination-profile image declarations."""
from __future__ import annotations
import argparse
import json
import hashlib
from datetime import date
from _content_integrity import identity_documented
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--visual-evidence', help='Deprecated; use --review-records')
    parser.add_argument('--review-records', type=Path, help='JSON array of per-asset hash-bound review decisions')
    args = parser.parse_args()
    if args.visual_evidence:
        parser.error('A contact-sheet path cannot verify every asset. Use --review-records; see references/rendering-and-assets.md')
    previous = json.loads(args.output.read_text(encoding='utf-8')) if args.output.is_file() else {}
    reviews = json.loads(args.review_records.read_text(encoding='utf-8-sig')) if args.review_records else []
    if not isinstance(reviews, list):
        parser.error('review-records must be an array')
    explicit_keys = {(r.get('place_id'), r.get('file')) for r in reviews}
    reviews += [r for r in previous.get('assets', []) if (r.get('place_id'), r.get('file')) not in explicit_keys]
    data = json.loads(args.profile.read_text(encoding='utf-8'))
    assets = []

    def review_flags(record: dict) -> dict:
        declared_bound = bool(record.get('source_identity_bound', False))
        for flag in ('source_identity_bound', 'visually_confirmed', 'watermark_checked', 'subject_verified'):
            record[flag] = False
        mode = 'standard'
        record['source_identity_bound'] = identity_documented(dict(record, source_identity_bound=declared_bound))
        review = next((r for r in reviews if r.get('file') == record.get('file') and r.get('place_id') == record.get('place_id')), None)
        if not review:
            return record
        if not review.get('verification_evidence'):
            return record
        root = args.profile.parent.resolve()
        file = (root / str(record.get('file', ''))).resolve()
        evidence = (root / str(review.get('verification_evidence', ''))).resolve()
        valid = file.is_relative_to(root) and evidence.is_relative_to(root) and file.is_file() and evidence.is_file() and all((review.get(k) == record.get(k) for k in ('source_page', 'download_url', 'media_class', 'original_media_class', 'visual_subject_type'))) and (review.get('sha256') == hashlib.sha256(file.read_bytes()).hexdigest()) and bool(review.get('visual_confirmation_note')) and all((review.get(k) is True for k in ('source_identity_bound', 'visually_confirmed', 'watermark_checked')))
        if not valid:
            print(f"REVIEW REQUIRED changed or incomplete evidence: {record.get('file')}")
            return record
        record.update({'sha256': review['sha256'], 'verification_evidence': review['verification_evidence'], 'visual_confirmation_note': review['visual_confirmation_note'], 'source_identity_note': record.get('source_identity_note') or review.get('source_identity_note') or review['visual_confirmation_note'], 'source_identity_bound': True, 'visually_confirmed': True, 'watermark_checked': True, 'subject_verified': True})
        return record
    cover = data.get('cover', {})
    cover_file = cover.get('image')
    if cover_file:
        derived = None
        derived_from = str(cover.get('derived_from', '')).strip()
        if derived_from:
            derived = next((image for place in data.get('places', []) for image in place.get('images', []) if isinstance(image, dict) and image.get('file') == derived_from), None)
        provenance = cover if cover.get('source_page') else derived or cover
        assets.append(review_flags({'file': cover_file, 'place_id': '__cover__', 'venue': data.get('display_name'), 'module': 'cover', 'role': 'hero', 'source_type': provenance.get('source_type') or ('official' if provenance.get('media_class') == 'official_photo' else 'licensed'), 'media_class': provenance.get('media_class'), 'original_media_class': provenance.get('original_media_class', provenance.get('media_class')), 'visual_subject_type': provenance.get('visual_subject_type', 'landscape'), 'source_page': provenance.get('source_page'), 'download_url': provenance.get('download_url'), 'transcoded_from': provenance.get('transcoded_from'), 'verification_evidence': provenance.get('verification_evidence'), 'retrieved_at': provenance.get('retrieved_at', date.today().isoformat()), 'http_accessible': bool(provenance.get('http_accessible', False)), 'decoded': False, 'source_identity_note': provenance.get('source_identity_note', ''), 'source_identity_bound': bool(provenance.get('source_identity_bound', False)), 'visually_confirmed': bool(provenance.get('visually_confirmed', False)), 'watermark_checked': bool(provenance.get('watermark_checked', False)), 'visual_confirmation_note': provenance.get('visual_confirmation_note'), 'subject_verified': bool(provenance.get('subject_verified', False))}))
    for place in data.get('places', []):
        for image in place.get('images', []):
            if not isinstance(image, dict):
                continue
            assets.append(review_flags({'file': image.get('file'), 'place_id': place.get('id'), 'venue': place.get('display_name'), 'module': image.get('module', place.get('type')), 'role': image.get('role', 'gallery'), 'source_type': image.get('source_type') or ('official' if image.get('media_class') == 'official_photo' else 'licensed'), 'media_class': image.get('media_class'), 'original_media_class': image.get('original_media_class', image.get('media_class')), 'visual_subject_type': image.get('visual_subject_type'), 'source_page': image.get('source_page'), 'download_url': image.get('download_url'), 'transcoded_from': image.get('transcoded_from'), 'verification_evidence': image.get('verification_evidence'), 'retrieved_at': image.get('retrieved_at', date.today().isoformat()), 'http_accessible': bool(image.get('http_accessible', False)), 'decoded': False, 'source_identity_note': image.get('source_identity_note', ''), 'source_identity_bound': bool(image.get('source_identity_bound', False)), 'visually_confirmed': bool(image.get('visually_confirmed', False)), 'watermark_checked': bool(image.get('watermark_checked', False)), 'visual_confirmation_note': image.get('visual_confirmation_note'), 'subject_verified': bool(image.get('subject_verified', False))}))
    manifest = {'destination': data.get('destination'), 'retrieved_at': date.today().isoformat(), 'assets': assets}
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    review_message = 'representative cover/flagged-asset QA only'
    print(f'PASS wrote {len(assets)} asset records; {review_message}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
