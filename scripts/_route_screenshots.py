"""Binding and markup for actual browser-captured street maps."""
import hashlib
import json
import re
from html import escape
from _offline_overview import verify_evidence

def capture_stops(day, places):
    return [{'number':i, 'place_id':s['place_id'], 'name':places[s['place_id']]['display_name'],
             'latitude':places[s['place_id']]['latitude'], 'longitude':places[s['place_id']]['longitude']}
            for i,s in enumerate(day['stops'],1)]

def day_fingerprint(day, places):
    value={'date':day.get('date'), 'stops':capture_stops(day,places)}
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def screenshots_html(day):
    rows=day.get('route_screenshots',[])
    if not rows:return ''
    return '<div class="route-screenshots">'+''.join(
        '<figure style="margin:12px 0"><a href="'+escape(r['file'],quote=True)+'" target="_blank" rel="noopener">'
        '<img style="display:block;width:100%;height:auto;border-radius:12px" loading="lazy" src="'+escape(r['file'],quote=True)+'" alt="'+escape(r['caption'],quote=True)+'"></a>'
        '<figcaption>'+escape(r['caption'])+' · 点击查看大图</figcaption></figure>' for r in rows)+ '<p>'+('含简化地理总览，非街道导航图；' if any(r.get('kind')=='offline_overview' for r in rows) else '真实街道底图截图，')+'可离线查看；连线只表示行程顺序，不是实际导航路线。</p></div>'

def verify_captures(root, profile):
    failures=[];places={p['id']:p for p in profile.get('places',[])}
    policy = profile.get('map_delivery', 'screenshots' if (root/'RESEARCH_PROVENANCE.json').is_file() else 'legacy')
    if policy == 'legacy' and (root/'RESEARCH_PROVENANCE.json').is_file():
        failures.append('new builds cannot bypass offline map checks with legacy policy')
    if policy not in ('screenshots', 'online', 'legacy'):
        failures.append('unknown map_delivery policy')
    if policy == 'online' and not profile.get('online_map_user_statement', '').strip():
        failures.append('online maps require the actual explicit user request in online_map_user_statement')
    for i,day in enumerate(profile.get('itinerary',[]),1):
        if policy == 'screenshots' and not day.get('route_screenshots'):
            failures.append(f'day {i}: missing required offline street-map screenshots; follow screenshot-map-workflow.md')
        for shot in day.get('route_screenshots',[]):
            if shot.get('kind') == 'offline_overview':
                try: verify_evidence(root, shot)
                except (ValueError, TypeError, KeyError) as exc: failures.append(f'day {i}: {exc}')
            file=shot.get('file','')
            if not re.fullmatch(r'media/routes/capture-day-\d+-\d+\.svg',file):
                failures.append(f'day {i}: unsafe route screenshot path');continue
            path=root/file
            if not path.is_file():failures.append(f'missing route screenshot: {file}');continue
            source=path.read_bytes()
            if hashlib.sha256(source).hexdigest()!=shot.get('sha256'):failures.append(f'stale route screenshot hash: {file}')
            if day_fingerprint(day,places)!=shot.get('capture_fingerprint'):failures.append(f'route changed since screenshot: {file}')
            if not re.search(rb'data:image/(?:png|jpeg|webp);base64,',source) or (shot.get('kind') != 'offline_overview' and b'OpenStreetMap' not in source):failures.append(f'screenshot lacks embedded capture/attribution: {file}')
    return failures
