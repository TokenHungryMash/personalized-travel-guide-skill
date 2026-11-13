"""Reject undersized or unintentionally repeated editorial photos before building."""
import json,hashlib,sys
from pathlib import Path
from PIL import Image,ImageOps

def audit(root):
    root=Path(root);read=lambda n:json.loads((root/n).read_text(encoding='utf-8-sig'))
    edition=read('edition.json');guide=read('content.json');photos=read('place-photos.json')|read('edition-photos.json')
    uses=[(k,edition[k]) for k in ('cover','foodPhoto','culturePhoto','closingPhoto') if edition.get(k)]
    uses += [('area:'+str(a.get('id')),a.get('photo')) for a in guide.get('areas',[])]
    rows=[];errors=[]
    for role,key in uses:
        record=photos.get(key,{})
        for field in ('src','mobileSrc'):
            if field=='mobileSrc' and not record.get(field):continue
            name=record.get(field,'');path=(root/name).resolve()
            try:
                if not path.is_relative_to(root.resolve()):raise ValueError('asset escapes workbench')
                with Image.open(path) as src:
                    im=ImageOps.exif_transpose(src).convert('RGB');width,height=im.size
                    pixels=im.convert('L').resize((17,16)).tobytes()
                signature=sum((pixels[y*17+x]>pixels[y*17+x+1]) << (y*16+x) for y in range(16) for x in range(16))
                floor=(2400,1400) if role=='cover' else (1600,900)
                if max(width,height)<floor[0] or min(width,height)<floor[1]:
                    errors.append(f'{role}/{field} ({key}): {name} is {width}x{height}; need long/short edges >= {floor}. Replace source or redesign its large-image use; do not upscale.')
                row=dict(role=role,field=field,key=key,src=name,width=width,height=height,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),fingerprint=f'{signature:064x}')
                for previous in rows:
                    if previous['role']==role:continue
                    distance=(signature^int(previous['fingerprint'],16)).bit_count()
                    if previous['sha256']==row['sha256'] or distance<=8:
                        errors.append(f'Repeated editorial photo: {previous["role"]}/{previous["src"]} and {role}/{name} (distance={distance}). Use a different composition; directory thumbnails may reuse editorial photos.')
                rows.append(row)
            except (OSError,ValueError) as e:errors.append(f'{role}/{field} ({key}): {e}')
    return dict(errors=errors,images=rows,visualReview='pending: check sharpness, subject and crop in final HTML at desktop and mobile sizes')

if __name__=='__main__':
    root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).parent).resolve()
    report=audit(root);qa=root/'qa-photo-quality';qa.mkdir(exist_ok=True)
    (qa/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('\n'.join(report['errors']) if report['errors'] else f'PASS editorial photo dimensions and duplicates: {len(report["images"])} image variants; visual review still required.')
    raise SystemExit(bool(report['errors']))
