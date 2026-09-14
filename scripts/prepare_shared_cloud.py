#!/usr/bin/env python3
"""Create a reviewable Cloudflare project, without deploying or copying credentials."""
import argparse,json,shutil,re
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('handbook',type=Path);p.add_argument('output',type=Path);p.add_argument('--name',required=True);p.add_argument('--database-id',required=True);p.add_argument('--database-name',required=True);p.add_argument('--uploads-kv-id',required=True,help='Cloudflare KV namespace id used for shared PDF/image attachments');p.add_argument('--access-mode',required=True,choices=('open','code'),help='Explicitly selected sharing access mode');a=p.parse_args()
 if not re.fullmatch(r'[a-z0-9-]{1,63}',a.name):raise SystemExit('Invalid Worker name')
 source=a.handbook.resolve();out=a.output.resolve();kit=Path(__file__).resolve().parents[1]/'assets/current-system/cloudflare'
 if out.exists() and any(out.iterdir()):raise SystemExit('Use an empty deployment directory')
 if not (source/'index.html').exists():raise SystemExit('Missing handbook index.html')
 public=out/'public';public.mkdir(parents=True)
 for item in source.iterdir():
  if item.is_file() and (item.name=='index.html' or item.suffix in {'.js','.css','.woff2','.png'}):shutil.copy2(item,public/item.name)
  elif item.is_dir() and item.name in {'media','fonts','audit-routes','assets'}:shutil.copytree(item,public/item.name)
 for name in ['worker.js','schema.sql']:shutil.copy2(kit/name,out/name)
 shutil.copy2(kit/'cloud-shared.js',public/'cloud-shared.js')
 html=(public/'index.html').read_text('utf8')
 if 'cloud-shared.js' not in html:
  anchor='<script src="travel-utilities.js'
  if anchor not in html:raise SystemExit('Install the current-system ledger runtime first')
  html=html.replace(anchor,'<script src="cloud-shared.js" defer></script>'+anchor)
 (public/'index.html').write_text(html,encoding='utf8')
 if not re.fullmatch(r'[0-9a-f]{32}',a.uploads_kv_id):raise SystemExit('Invalid uploads KV namespace id')
 config={'name':a.name,'main':'worker.js','compatibility_date':'2026-09-12','compatibility_flags':['nodejs_compat'],'workers_dev':True,'preview_urls':False,'vars':{'ACCESS_MODE':a.access_mode},'assets':{'directory':'./public','binding':'ASSETS','run_worker_first':True},'d1_databases':[{'binding':'DB','database_name':a.database_name,'database_id':a.database_id}],'kv_namespaces':[{'binding':'UPLOADS','id':a.uploads_kv_id}],'observability':{'enabled':True,'head_sampling_rate':0.1}}
 (out/'wrangler.jsonc').write_text(json.dumps(config,indent=2),encoding='utf8')
 seed=[]
 for ident,options in re.findall(r'<select[^>]+data-reservation-id="([^"]+)"[^>]*>(.*?)</select>',html,re.S):
  if not re.fullmatch(r'[\w-]{1,100}',ident):raise SystemExit('Invalid reservation id')
  checked=bool(re.search(r'<option[^>]*selected[^>]*>已预约，有凭证</option>',options));seed.append("INSERT OR IGNORE INTO checks(id,checked) VALUES ('%s',%d);"%(ident,checked))
 (out/'seed.sql').write_text('\n'.join(seed),encoding='utf8')
 (out/'.gitignore').write_text('.wrangler/\n.dev.vars\n',encoding='utf8')
 print(f'Prepared only. Access mode: {a.access_mode}. '+('Before deploy, set ACCESS_CODE with the platform secret mechanism; protected access uses the built-in mobile/desktop form and secure cookie. ' if a.access_mode=='code' else '')+'Shared members, ledger, reservation checks, links, images and PDFs are enabled; each attachment is limited to 20 MB. Apply schema.sql once, then seed.sql, verify account and deploy only after user authorization. No account id, tokens or old-project deletion copied.')
if __name__=='__main__':main()
