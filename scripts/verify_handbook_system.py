#!/usr/bin/env python3
"""Check byte-exact restore and offline asset invariants; not a browser QA substitute."""
import argparse,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();out=a.output.resolve();root=Path(__file__).resolve().parents[1]/'assets/current-system';m=json.loads((root/'manifest.json').read_text('utf8'));errors=[];count=0
 for name,expected in m['files'].items():
  if not name.startswith('product/'):continue
  f=out/Path(name).relative_to('product');count+=1
  if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=expected:errors.append('missing/changed: '+name)
 html=(out/'index.html').read_text('utf8')
 for href in re.findall(r'(?:src|href)="([^"?#]+)(?:[?#][^"]*)?"',html):
  if re.match(r'(?:https?:|data:|mailto:|tel:)',href):continue
  if href.endswith(('.js','.css','.webp','.png','.svg','.woff2')) and not (out/href).exists():errors.append('missing dependency: '+href)
 for f in (out/'media/routes').glob('day-*.svg'):
  tree=ET.fromstring(f.read_text('utf8'))
  for el in tree.iter():
   if el.tag.endswith('image'):
    href=el.get('href','');
    if not href.startswith('data:image/'):errors.append('external/unembedded SVG image: '+f.name)
 for forbidden in ['access-code.txt','.dev.vars','wrangler.jsonc','default.toml']:
  if list(out.rglob(forbidden)):errors.append('sensitive/deployment file in restore: '+forbidden)
 print(json.dumps({'files_checked':count,'errors':errors,'browser_qa':'separate required behavior check'},ensure_ascii=False,indent=2))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
