#!/usr/bin/env python3
"""Restore the approved complete handbook without depending on its original workspace."""
import argparse,hashlib,json,shutil
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--replace-owned',action='store_true',help='Update files in an earlier restore; unrelated files are not deleted')
 args=p.parse_args();root=Path(__file__).resolve().parents[1]/'assets/current-system';manifest=json.loads((root/'manifest.json').read_text('utf8'));out=args.output.resolve()
 if out.exists() and any(out.iterdir()) and not args.replace_owned:raise SystemExit('Target is not empty. Choose a new folder or explicitly use --replace-owned for an intended update.')
 # Validate the complete bundle before writing anything: a broken source must
 # never leave a partial target that requires the user to delete it and retry.
 for key,expected in manifest['files'].items():
  if not key.startswith('product/'):continue
  source=(root/key).resolve();target=(out/Path(key).relative_to('product')).resolve()
  if not source.is_relative_to(root) or not target.is_relative_to(out):raise SystemExit('Unsafe bundle path')
  if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise SystemExit('Source bundle checksum mismatch; target unchanged. Reinstall the corrected Skill package: '+key)
 copied=[]
 for key,expected in manifest['files'].items():
  if not key.startswith('product/'):continue
  source=root/key
  if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise SystemExit('Bundle checksum mismatch: '+key)
  relative=Path(key).relative_to('product');target=(out/relative).resolve()
  if not target.is_relative_to(out):raise SystemExit('Unsafe bundle path')
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);copied.append(str(relative))
 (out/'SYSTEM_RESTORE.json').write_text(json.dumps({'version':manifest['version'],'reference_destination':'Bali','content_mode':'exact approved reference; not a newly researched itinerary','files':copied,'cloud_sync':False},ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'restored':len(copied),'index':str(out/'index.html'),'cloud_sync':False},ensure_ascii=False))
if __name__=='__main__':main()
