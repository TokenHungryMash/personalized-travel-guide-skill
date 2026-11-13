"""Read-only data preflight; no fonts, photographs, HTML writing or automatic review."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True

def audit(root):
    root=Path(root)
    checks={}
    try:
        from editorial_release import FILES, audit as review_audit
        raw={name:(root/name).read_bytes() for name in FILES}
        data={name:json.loads(payload) for name,payload in raw.items()}
        guide,editorial,edition=(data[name] for name in FILES)
        from destination_content import audit_relationships
        checks['structure']=audit_relationships(guide,edition,editorial)
        if not checks['structure']:
            from content_completeness import audit_completeness
            from editorial_evidence import audit_evidence
            from travel_content import audit_content
            checks['completeness']=audit_completeness(guide,edition,editorial)
            checks['sources']=audit_evidence(editorial,required=edition.get('editorialEvidenceVersion',0)>=1,area_ids=[a['id'] for a in guide['areas']])
            checks['travel']=audit_content(guide) if edition.get('travelContentVersion',0)>=1 else []
            from coverage_release import audit as coverage_audit
            try:checks['coverage']=coverage_audit(guide,editorial,json.loads((root/'directory-plan.json').read_text(encoding='utf8')))['errors']
            except (OSError,ValueError,TypeError,KeyError) as exc:checks['coverage']=[str(exc)]
            try:
                hashes={name:hashlib.sha256(payload).hexdigest() for name,payload in raw.items()}
                review=json.loads((root/'editorial-review.json').read_text(encoding='utf8'))
                checks['review']=review_audit(data,hashes,review)
            except (OSError,ValueError,TypeError,KeyError) as exc:checks['review']=[str(exc)]
    except (OSError,ValueError,TypeError,KeyError) as exc:
        checks['input']=[str(exc)]
    draft_errors=[f'{key}: {error}' for key,errors in checks.items() if key not in ('coverage','review') for error in errors]
    return {'checks':checks,'draftErrors':draft_errors,
            'dataReadyForPreview':not draft_errors,'dataReadyForRelease':not any(checks.values()),
            'limit':'Read-only data checks. Media quality, actual page reading and browser checks remain required; no answer or ready status is generated.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('workbench',type=Path)
    parser.add_argument('--draft',action='store_true',help='Report coverage/review gaps without blocking a structurally valid draft')
    args=parser.parse_args();report=audit(args.workbench)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return not report['dataReadyForPreview' if args.draft else 'dataReadyForRelease']

if __name__=='__main__':raise SystemExit(main())
