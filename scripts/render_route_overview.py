"""Offline geographic overview; local OSM XML only, no automatic approval."""
import argparse, hashlib, json, math
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from _route_screenshots import capture_stops, day_fingerprint

def render(profile, outline, font_path, day_number, out):
    data=json.loads(profile.read_text(encoding='utf-8')); day=data['itinerary'][day_number-1]
    places={p['id']:p for p in data['places']}; stops=capture_stops(day,places)
    def merc(lon,lat):
        if not math.isfinite(lon) or not math.isfinite(lat) or abs(lat)>85 or abs(lon)>180: raise ValueError('invalid coordinates')
        return math.radians(lon),math.log(math.tan(math.pi/4+math.radians(lat)/2))
    xs,ys=zip(*(merc(s['longitude'],s['latitude']) for s in stops))
    scale=min(680/max(max(xs)-min(xs),1e-6),460/max(max(ys)-min(ys),1e-6))
    cx,cy=(max(xs)+min(xs))/2,(max(ys)+min(ys))/2
    def pixel(lon,lat):
        x,y=merc(lon,lat); return 600+(x-cx)*scale,610-(y-cy)*scale
    pts=[pixel(s['longitude'],s['latitude']) for s in stops]
    im=Image.new('RGB',(1200,1130+88*len(stops)),'#f7f4ed'); d=ImageDraw.Draw(im)
    font=lambda size:ImageFont.truetype(str(font_path),size)
    ink,red='#233d47','#b24f38'
    d.text((60,40),f"{data.get('display_name','旅行')} · DAY {day_number:02d}",font=font(44),fill=ink)
    d.text((60,110),'简化地理总览，非街道导航图',font=font(36),fill=red)
    d.text((60,170),'地点按坐标定位；箭头仅表示访问顺序。',font=font(26),fill=ink)
    layer=Image.new('RGB',im.size,'#e9eeeb'); ld=ImageDraw.Draw(layer)
    tree=ET.parse(outline).getroot()
    nodes={n.get('id'):pixel(float(n.get('lon')),float(n.get('lat'))) for n in tree.findall('node')}
    count=0
    for way in tree.findall('way'):
        tags={t.get('k'):t.get('v') for t in way.findall('tag')}; refs=[n.get('ref') for n in way.findall('nd')]
        if len(refs)<2 or any(n not in nodes for n in refs):continue
        geom=[nodes[n] for n in refs]
        if not any(60<x<1140 and 230<y<990 for x,y in geom):continue
        if tags.get('natural')=='water' and refs[0]==refs[-1]:ld.polygon(geom,fill='#b5d1dc')
        elif tags.get('waterway')=='river' or tags.get('natural')=='coastline':ld.line(geom,fill='#a3c4d1',width=4)
        elif tags.get('highway') in ('primary','secondary','trunk'):ld.line(geom,fill='#d0d8d4',width=5)
        else:continue
        count+=1
    if not count:raise ValueError('no relevant geographic background; blank maps are not accepted')
    mask=Image.new('L',im.size,0);ImageDraw.Draw(mask).rounded_rectangle((60,230,1140,990),radius=24,fill=255)
    im.paste(layer,(0,0),mask);d=ImageDraw.Draw(im)
    for a,b in zip(pts,pts[1:]):
        d.line((a,b),fill=red,width=5);length=math.dist(a,b)
        if length>60:
            ux,uy=(b[0]-a[0])/length,(b[1]-a[1])/length;mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
            d.polygon([(mx+ux*12,my+uy*12),(mx-ux*10-uy*8,my-uy*10+ux*8),(mx-ux*10+uy*8,my-uy*10-ux*8)],fill=red)
    boxes=[]
    for i,((x,y),stop) in enumerate(zip(pts,stops),1):
        text=f"{i:02d}  {stop['name']}";w=int(d.textlength(text,font=font(38)))+28;h=62;choices=[]
        for gap in (24,68,112,164,220):
            for left,top in ((x+gap,y-h/2),(x-gap-w,y-h/2),(x-w/2,y-gap-h),(x-w/2,y+gap)):
                right,bottom=left+w,top+h
                if not (80<=left and right<=1120 and 305<=top and bottom<=920):continue
                if any(left<r+10 and right+10>l and top<b+10 and bottom+10>t for l,t,r,b in boxes):continue
                if any(left-12<px<right+12 and top-12<py<bottom+12 for px,py in pts):continue
                hits=sum(left<ax+(bx-ax)*k/20<right and top<ay+(by-ay)*k/20<bottom for (ax,ay),(bx,by) in zip(pts,pts[1:]) for k in range(1,20))
                choices.append((gap+hits*25,(left,top,right,bottom)))
        if not choices:raise ValueError('labels do not fit; enlarge layout without moving coordinates')
        _,box=min(choices,key=lambda c:c[0]);boxes.append(box);left,top,right,bottom=box
        d.line(((x,y),(min(max(x,left),right),min(max(y,top),bottom))),fill='#758c91',width=2)
        d.rounded_rectangle(box,radius=10,fill='white',outline='#b5c6c7',width=2)
        d.text((left+14,top+29),text,font=font(38),fill=ink,anchor='lm')
    for x,y in pts:d.ellipse((x-9,y-9,x+9,y+9),fill=ink,outline='white',width=2)
    d.text((85,250),'上北下南 · 左西右东',font=font(26),fill=ink)
    d.text((85,933),'局部地理背景已简化',font=font(24),fill='#466a79')
    d.text((85,965),'© OpenStreetMap contributors · openstreetmap.org/copyright',font=font(18),fill='#526e78')
    d.text((60,1020),'当天地点 · 按行程顺序',font=font(36),fill=ink)
    for i,stop in enumerate(stops,1):
        text=f"{i:02d}  {stop['name']}"
        if d.textlength(text,font=font(36))>1080:raise ValueError('legend too long; enlarge layout')
        d.text((60,1100+(i-1)*88),text,font=font(36),fill=ink)
    out.mkdir(parents=True,exist_ok=True);path=out/f'day-{day_number}-overview.png'
    if path.exists():raise ValueError('use new output directory')
    im.save(path,optimize=True);im.thumbnail((390,3000));im.save(out/'phone-preview.png')
    receipt=dict(day=day_number,image=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),capture_fingerprint=day_fingerprint(day,places),background_file=str(outline),background_sha256=hashlib.sha256(outline.read_bytes()).hexdigest(),background_features=count,attribution='© OpenStreetMap contributors',markers_displaced=False,visual_reviewed=False,integrated_into_handbook=False)
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path)
    p.add_argument('--outline',type=Path,required=True);p.add_argument('--font',type=Path,required=True)
    p.add_argument('--day',type=int,default=1);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(render(a.profile,a.outline,a.font,a.day,a.out),ensure_ascii=False))
