"""Prepare large map capture pages or import reviewed actual screenshots."""
import argparse, base64, hashlib, json, math, shutil, time
from pathlib import Path
from html import escape
from PIL import Image
from _map_delivery import compress_capture
from _route_screenshots import capture_stops, day_fingerprint

def chunks(stops):
    groups=[]
    for stop in stops:
        if not groups or len(groups[-1])>=4 or max(abs(stop['latitude']-groups[-1][0]['latitude']),abs(stop['longitude']-groups[-1][0]['longitude']))>.006:
            groups.append([])
        groups[-1].append(stop)
    return groups

def prepare(root):
    data=json.loads((root/'destination-profile.json').read_text(encoding='utf-8'))
    places={p['id']:p for p in data['places']}
    folder=root/'qa'/'route-capture';folder.mkdir(parents=True,exist_ok=True)
    script=Path(__file__).with_name('route-capture-page.js').read_text(encoding='utf-8')
    tasks=[]
    for di,day in enumerate(data['itinerary'],1):
        stops=capture_stops(day,places)
        if not stops:raise ValueError(f'day {di}: no stops')
        if any(isinstance(s[k],bool) or not isinstance(s[k],(int,float)) or not math.isfinite(s[k]) or abs(s[k])>(85 if k=='latitude' else 180) for s in stops for k in ('latitude','longitude')):
            raise ValueError(f'day {di}: invalid coordinates')
        # One offline overview per day; street-level navigation stays in external links.
        views=[('总览',stops)]
        for vi,(label,selected) in enumerate(views,1):
            stem=f'day-{di}-{vi}'
            payload={'stops':selected,'title':f'第{di}天 · {label}', 'overview':label=='总览'}
            page='<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css"><style>body{margin:0;font-family:system-ui,sans-serif}#sheet{position:relative;width:1400px;height:1100px;background:#f5f2e9}#map{position:absolute;inset:70px 0 56px}#heading{position:absolute;top:16px;left:28px;font-size:28px;font-weight:bold}#credit{position:absolute;bottom:10px;left:24px;font-size:16px}.label{position:absolute;width:270px;padding:8px;box-sizing:border-box;background:#fffef9;border:2px solid #28594f;border-radius:10px;color:#183f34;font-size:24px;line-height:1.25;overflow-wrap:anywhere}.pin{position:absolute;border-radius:50%;width:12px;height:12px;background:#28594f;border:2px solid white;transform:translate(-50%,-50%)}</style><div id="sheet"><div id="map"></div><div id="heading"></div><div id="credit">OpenFreeMap · © OpenMapTiles · Data from OpenStreetMap<br>虚线仅表示行程顺序，不代表实际步行或乘车路线</div></div><script>window.CAPTURE_INPUT='+json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')+';</script><script src="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js"></script><script>'+script+'</script>'
            (folder/(stem+'.html')).write_text(page,encoding='utf-8')
            tasks.append({'day':di,'view':vi,'page':stem+'.html','png':stem+'.png','caption':payload['title'],
                          'stop_numbers':[s['number'] for s in selected], 'day_fingerprint':day_fingerprint(day,places)})
    plan={'schema_version':2,'tasks':tasks,'width':1400,'height':1100,'device_scale_factor':1}
    (folder/'capture-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PREPARED {len(tasks)} views: {folder}; no screenshots captured yet')

def import_captures(root):
    folder=root/'qa'/'route-capture';plan=json.loads((folder/'capture-plan.json').read_text(encoding='utf-8'))
    report=json.loads((folder/'capture-report.json').read_text(encoding='utf-8'))
    records={r['png']:r for r in report['captures']}
    profile=json.loads((root/'destination-profile.json').read_text(encoding='utf-8'));places={p['id']:p for p in profile['places']}
    target=root/'research'/'itinerary.json';days=json.loads(target.read_text(encoding='utf-8'))
    original_days=json.loads(json.dumps(days))
    compression_signature=hashlib.sha256(Path(__file__).with_name('_map_delivery.py').read_bytes()).hexdigest()
    if plan.get('schema_version',1)>=2:
        if len(plan['tasks'])!=len(days) or sorted(t['day'] for t in plan['tasks'])!=list(range(1,len(days)+1)):
            raise ValueError('capture plan must contain exactly one overview per day')
    pending=[]
    for task in plan['tasks']:
        row=records[task['png']];day=days[task['day']-1]
        if day_fingerprint(day,places)!=task['day_fingerprint']:raise ValueError('route changed; prepare fresh captures')
        if plan.get('schema_version',1)>=2:
            page=(folder/task['page']).resolve()
            if not page.is_relative_to(folder.resolve()):raise ValueError('unsafe capture page path')
            if row.get('day_fingerprint')!=task['day_fingerprint'] or row.get('page_sha256')!=hashlib.sha256(page.read_bytes()).hexdigest():
                raise ValueError('capture page or route changed; recapture affected day')
            if task['stop_numbers']!=[s['number'] for s in capture_stops(day,places)]:
                raise ValueError('daily overview must include every scheduled stop')
        if row.get('status')!='captured' or row.get('visual_reviewed') is not True:raise ValueError(f"{task['png']}: screenshot and human visual review required")
        if plan.get('schema_version',1)>=2 and not str(row.get('review_note','')).strip():raise ValueError('capture needs an actual visual review note')
        observed=row.get('observed_state',{})
        if plan.get('schema_version',1)>=2 and observed.get('status')!='ready':raise ValueError('capture must be ready before import')
        if observed.get('tiles_loaded') is not True or observed.get('labels')!=len(task['stop_numbers']):raise ValueError('capture lacks ready basemap/all place labels')
        path=(folder/task['png']).resolve()
        if not path.is_relative_to(folder.resolve()):raise ValueError('unsafe screenshot path')
        payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if digest!=row['sha256']:raise ValueError('screenshot hash mismatch')
        relative=f"media/routes/capture-day-{task['day']}-{task['view']}.svg"
        previous=next((s for s in day.get('route_screenshots',[]) if s.get('file')==relative),{})
        derivative=root/relative
        if (previous.get('original_capture_sha256')==digest and previous.get('capture_fingerprint')==task['day_fingerprint']
                and previous.get('caption')==task['caption'] and previous.get('compression_signature')==compression_signature
                and derivative.is_file() and previous.get('sha256')==hashlib.sha256(derivative.read_bytes()).hexdigest()):
            pending.append((task['day']-1,relative,None,previous));continue
        compressed,(w,h),original_size=compress_capture(payload)
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>{escape(task["caption"])} — OpenFreeMap © OpenMapTiles Data from OpenStreetMap</title><image width="{w}" height="{h}" href="data:image/webp;base64,{base64.b64encode(compressed).decode()}"/></svg>'
        pending.append((task['day']-1,relative,svg,{'file':relative,'caption':task['caption'],'capture_fingerprint':task['day_fingerprint'],'sha256':hashlib.sha256(svg.encode()).hexdigest(),'original_capture_sha256':digest,'compression_signature':compression_signature,'delivery_format':'webp','delivery_bytes':len(compressed),'original_bytes':len(payload),'original_dimensions':original_size,'delivery_dimensions':[w,h]}))
    if {di for di,_,_,_ in pending}!=set(range(len(days))):raise ValueError('capture plan must cover every day')
    for day in days:day['route_screenshots']=[]
    for di,relative,svg,row in pending:
        path=root/relative
        if svg is not None:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(svg,encoding='utf-8')
        days[di]['route_screenshots'].append(row)
    if days==original_days:
        print('UNCHANGED: reviewed maps and itinerary reused; no compression, backup or source rewrite required.')
        return
    shutil.copy2(target,folder/f'itinerary-before-import-{time.time_ns()}.json')
    target.write_text(json.dumps(days,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('IMPORTED actual screenshots into owning itinerary. Run research_status.py to recompile, then advance_build.py --run and follow its next stage.')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','import']);parser.add_argument('workbench',type=Path)
    args=parser.parse_args()
    try:(prepare if args.action=='prepare' else import_captures)(args.workbench.resolve())
    except (OSError,ValueError,KeyError,TypeError) as exc:print('FAIL '+str(exc));return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
