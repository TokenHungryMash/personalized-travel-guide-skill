"""Package a portable public handbook, never research or browser evidence."""
import argparse
import json
import re
import zipfile
import hashlib
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit
from html.parser import HTMLParser
from _route_screenshots import verify_captures

class Resources(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ('script','img','source','iframe') and a.get('src'): self.refs.append(a['src'])
        if tag=='link' and a.get('href') and a.get('rel') in ('stylesheet','icon','manifest','preload'): self.refs.append(a['href'])

def package(root, output=None):
    root=Path(root).resolve()
    profile=json.loads((root/'destination-profile.json').read_text(encoding='utf-8'))
    errors=verify_captures(root,profile)
    if errors: raise ValueError('; '.join(errors))
    files={p for p in root.iterdir() if p.suffix in ('.js','.css') and p.is_file()}
    files.add(root/'index.html')
    if (root/'manifest.json').exists(): files.add(root/'manifest.json')
    for folder in ('assets','media'):
        if (root/folder).exists():
            files.update(p for p in (root/folder).rglob('*') if p.is_file())
    for p in files:
        if p.is_symlink() or not p.resolve().is_relative_to(root): raise ValueError('Unsafe bundle path: '+str(p))
        if p.suffix.lower() not in ('.html','.js','.css','.json','.jpg','.jpeg','.png','.webp','.gif','.svg','.ico','.woff','.woff2','.ttf','.otf'):
            raise ValueError('Unexpected public asset: '+str(p))
    def require(ref, parent):
        if ref.startswith(('data:','#')): return
        parts=urlsplit(ref)
        if parts.scheme or parts.netloc: raise ValueError('External runtime dependency: '+ref)
        target=(parent/unquote(parts.path)).resolve()
        if target not in files: raise ValueError('Missing portable dependency: '+ref)
    for p in files:
        if p.suffix=='.html':
            parser=Resources(); parser.feed(p.read_text(encoding='utf-8'))
            for ref in parser.refs: require(ref,p.parent)
        if p.suffix=='.css':
            for ref in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)',p.read_text(encoding='utf-8')): require(ref.strip(),p.parent)
        if p.suffix=='.svg':
            for ref in re.findall(r'(?:href|src)=[\"\']([^\"\']+)',p.read_text(encoding='utf-8')): require(ref,p.parent)
    online=profile.get('map_delivery')=='online'
    if not online and not all(d.get('route_screenshots') for d in profile.get('itinerary',[])):
        raise ValueError('Offline delivery requires screenshots for every day')
    name=re.sub(r'[<>:"/\\|?*]', '_',profile.get('display_name','旅行'))
    days=len(profile.get('itinerary',[]))
    import base64, mimetypes
    output=Path(output).resolve() if output else root.parent/f'{name}{days}天{max(days-1,0)}晚-离线手册.html'
    if output.is_relative_to(root) or output.suffix.lower() != '.html': raise ValueError('Choose an HTML output outside workbench')
    def data_uri(p):
        if p.name.startswith('capture-day-') and p.suffix=='.svg':
            # The single captured raster already contains labels and attribution.
            # Avoid base64-encoding its base64 payload again inside an SVG URI.
            capture=re.search(r'<image\b[^>]*href="(data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+)"',p.read_text(encoding='utf-8'))
            if capture:return capture.group(1)
        mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode('ascii')
    html=(root/'index.html').read_text(encoding='utf-8')
    def script(m):
        if m.group(1).startswith('data:'): return m.group(0)
        return '<script>'+ (root/urlsplit(m.group(1)).path).read_text(encoding='utf-8').replace('</script','<\\/script')+'</script>'
    html=re.sub(r'<script\b[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>',script,html,flags=re.I)
    def stylesheet(m):
        tag=m.group(0)
        href=re.search(r'href=["\']([^"\']+)',tag)
        if href and 'stylesheet' in tag:
            return '<style>'+ (root/urlsplit(href.group(1)).path).read_text(encoding='utf-8')+'</style>'
        return tag
    html=re.sub(r'<link\b[^>]*>',stylesheet,html,flags=re.I)
    for p in sorted(files,key=lambda p:len(p.relative_to(root).as_posix()),reverse=True):
        relative=p.relative_to(root).as_posix()
        if p.suffix not in ('.html','.js','.css') and relative in html:
            html=html.replace(relative,data_uri(p))
    viewer=Path(__file__).with_name('offline_image_viewer.html').read_text(encoding='utf-8')
    html=html.replace('</body>',viewer+'</body>') if '</body>' in html else html+viewer
    # Replace repeated binary payloads in markup, CSS and dynamic runtime strings.
    # A synchronous head bootstrap hydrates existing and subsequently inserted media.
    payloads = Counter(re.findall(r'data:image/[^;,\s"\x27]+;base64,[A-Za-z0-9+/=]+', html))
    table = {}
    for uri, count in payloads.items():
        if count > 1:
            token = 'data:application/x-travel-asset,' + hashlib.sha256(uri.encode()).hexdigest()
            table[token] = uri
            html = html.replace(uri, token)
    if table:
        loader = Path(__file__).with_name('offline_media_loader.js').read_text(encoding='utf-8')
        bootstrap = '<script>' + loader.replace('__TRAVEL_MEDIA_TABLE__', json.dumps(table, separators=(',', ':'))) + '</script>'
        head = re.search(r'<head\b[^>]*>', html, re.I)
        if head: html = html[:head.end()] + bootstrap + html[head.end():]
        else: html = bootstrap + html
    parser=Resources();parser.feed(html)
    for ref in parser.refs:
        if not ref.startswith(('data:','#')): raise ValueError('Unembedded resource: '+ref)
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix('.html.tmp');temp.write_text(html,encoding='utf-8');temp.replace(output)
    from _manual_qa import build_fingerprint
    (root/'offline-export.json').write_text(json.dumps({'file':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'build_fingerprint':build_fingerprint(root),'bytes':output.stat().st_size,'unique_image_payloads':len(payloads),'image_occurrences':sum(payloads.values()),'deduplicated_payloads':len(table)},ensure_ascii=False,indent=2),encoding='utf-8')
    return output

def main():
    parser=argparse.ArgumentParser();parser.add_argument('workbench',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    print('OFFLINE PACKAGE PASS:',package(args.workbench,args.output))
    print('Use this self-contained HTML as the primary open/download link. Never attach the workbench index alone. 双击离线 HTML 可在允许 JavaScript 的浏览器中打开。')
if __name__=='__main__': main()
