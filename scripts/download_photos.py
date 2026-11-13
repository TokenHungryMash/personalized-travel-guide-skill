"""Download already-selected image URLs from a UTF-8 JSON plan, never shell arguments.

Candidates remain unreviewed. Reuses bounded serial networking and atomic writes
from fetch_photos; does not promote downloaded images into the magazine.
"""
from pathlib import Path
import argparse
import os
import re
import sys
import urllib.parse
import urllib.request
from fetch_photos import (HttpClient, FetchError, atomic_bytes, atomic_json,
                          read_json, digest, image_details, local_file, stamp,
                          user_agent, wikimedia_url, writer_lock)


def https_url(url):
    try:
        p=urllib.parse.urlsplit(url)
        return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password and p.port in (None,443)
    except (ValueError,TypeError):
        return False


class HttpsRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, contact):
        self.contact=contact
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if not https_url(newurl):
            raise FetchError('Image redirect must remain HTTPS: '+newurl)
        if wikimedia_url(newurl):
            user_agent(self.contact)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


class DirectClient(HttpClient):
    def __init__(self, cache, contact=None, **kwargs):
        kwargs.setdefault('opener',urllib.request.build_opener(HttpsRedirect(contact)).open)
        super().__init__(cache,contact,**kwargs)
    def validate_url(self,url):
        if not https_url(url):raise FetchError('Image URL must be HTTPS without credentials: '+str(url))
    def request_agent(self,url):
        if self.contact or wikimedia_url(url):return user_agent(self.contact)
        return 'TravelMagazinePhotoDownloader/1.0'


def load_plan(file):
    rows=read_json(file)
    if not isinstance(rows,list) or not rows:raise FetchError('Plan must be a non-empty JSON array.')
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,dict):raise FetchError(f'Plan row {i+1} must be an object.')
        key=row.get('id')
        if not isinstance(key,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',key) or key in seen:
            raise FetchError(f'Plan row {i+1}: id must be unique, lowercase and filename-safe.')
        seen.add(key)
        if not isinstance(row.get('placeId'),str) or not row['placeId'].strip():raise FetchError(f'{key}: placeId is required.')
        if not https_url(row.get('url')) or not https_url(row.get('page')):raise FetchError(f'{key}: url and source page must be HTTPS URLs.')
    return rows


def download_plan(root,rows,client):
    root=Path(root).resolve()
    records_file=root/'photo-download-records.json'
    records=read_json(records_file,{'schemaVersion':1,'candidates':{}})
    if records.get('schemaVersion')!=1 or not isinstance(records.get('candidates'),dict):raise FetchError('Unknown download record format; left untouched.')
    for task in rows:
        key=task['id']+'-'+digest(task['url'])[:16]
        previous=records['candidates'].get(key,{})
        if previous.get('status')=='downloaded' and previous.get('src'):
            target=local_file(root,previous['src'])
            if target.is_file() and digest(target.read_bytes())==previous.get('sha256'):continue
        row={**task,'status':'pending','reviewed':False,'identityStatus':'unreviewed','checkedAt':stamp()}
        records['candidates'][key]=row
        try:
            body=client.get(task['url'])
            width,height,extension=image_details(body)
            # Actual decoded format decides extension; HTML error bodies never install.
            relative='media/photo-candidates/'+key+extension
            target=local_file(root,relative)
            atomic_bytes(target,body)
            row.update(status='downloaded',src=relative,sha256=digest(body),bytes=len(body),
                       width=width,height=height)
        except (FetchError,OSError,ValueError) as exc:
            row.update(status='failed',lastError=str(exc))
            atomic_json(records_file,records)
            # Stop this batch, preserving its checkpoint; rerun or select a new source.
            raise
        atomic_json(records_file,records)
    return records


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench',type=Path)
    parser.add_argument('--plan',type=Path,required=True,help='UTF-8 JSON [{id,placeId,url,page,caption?}]')
    parser.add_argument('--contact',default=os.environ.get('JOURNAL_MEDIA_CONTACT'))
    args=parser.parse_args(argv)
    try:
        rows=load_plan(args.plan)  # Validate the whole file before any request.
        root=args.workbench.resolve()
        if not root.is_dir():raise FetchError('Workbench directory does not exist.')
        cache=root/'.photo-cache'
        with writer_lock(cache/'fetch.lock'):
            download_plan(root,rows,DirectClient(cache,args.contact))
        print(f'Processed {len(rows)} candidates. Actual dimensions and sources: {root / "photo-download-records.json"}. Identity review still required.')
        return 0
    except (FetchError,OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);return 1
    except KeyboardInterrupt:
        print('Interrupted; completed candidates are saved. Rerun the same plan.',file=sys.stderr);return 130


if __name__=='__main__':raise SystemExit(main())
