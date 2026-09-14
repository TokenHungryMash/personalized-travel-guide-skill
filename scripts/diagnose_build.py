"""Read-only early batch diagnostics. This is not a completion or QA gate."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('workbench',type=Path);args=parser.parse_args()
    root=args.workbench;scripts=Path(__file__).resolve().parent;issues=[]
    for path in (root/'research').rglob('*.json'):
        if 'drafts' in path.parts or 'tools' in path.parts:continue
        try:json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError,ValueError) as exc:issues.append(f'{path.relative_to(root)}: {exc}')
    profile=root/'destination-profile.json'
    if profile.is_file():
        for name,arguments in [('verify_research_provenance.py',[str(root)]),('preflight_text_width.py',[str(profile)])]:
            result=subprocess.run([sys.executable,str(scripts/name),*arguments],capture_output=True,text=True,encoding='utf-8',errors='replace')
            if result.returncode:issues.append(result.stdout.strip() or result.stderr.strip())
    manifest=root/'asset-manifest.json'
    if manifest.is_file():
        data=json.loads(manifest.read_text(encoding='utf-8'));fields=('file','place_id','venue','module','role','source_type','source_page','retrieved_at','verification_evidence','visual_confirmation_note')
        for row in data.get('assets',[]):
            if not isinstance(row,dict):issues.append('manifest entry must be an object');continue
            missing=[key for key in fields if not row.get(key)]
            pending=[key for key in ('visually_confirmed','watermark_checked','subject_verified') if row.get(key) is not True]
            if missing or pending:issues.append(f"{row.get('place_id')} [{row.get('file')}]: missing={missing}; review pending={pending}")
    capture=root/'qa/route-capture/capture-report.json'
    if capture.is_file():
        for row in json.loads(capture.read_text(encoding='utf-8')).get('captures',[]):
            if row.get('status')!='captured' or row.get('visual_reviewed') is not True:issues.append(f"map {row.get('png')}: capture/visual review pending")
    print(json.dumps({'diagnostic_only':True,'handoff_allowed':False,'issues':issues,'next_action':'Repair owning data in one batch; inspect actual media before recording reviews. Run research_status.py after source edits. Diagnostics are not task completion.'},ensure_ascii=False,indent=2))
    return 2 if issues else 0

if __name__=='__main__':raise SystemExit(main())
