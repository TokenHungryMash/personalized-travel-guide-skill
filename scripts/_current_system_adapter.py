"""Profile-only adaptation of the approved current-system runtime.

The snapshot is an interface source, never a source of destination facts.
"""
import json
import re
from html import escape
from pathlib import Path
from _display_labels import transport_label, route_note

ROOT = Path(__file__).resolve().parent.parent / 'assets' / 'current-system' / 'product'


def trip_days(profile):
    places = {str(p['id']): p for p in profile['places']}
    result = []
    for day in profile['itinerary']:
        row = dict(day)
        row['route_note'] = route_note(day)
        row['stops'] = []
        for i, stop in enumerate(day['stops']):
            p = places[str(stop['place_id'])]
            nxt = day['stops'][i + 1] if i + 1 < len(day['stops']) else {}
            row['stops'].append({**stop, 'name': p['display_name'], 'time': stop['arrival_time'],
                'map_query': p['map_query'], 'map_url': 'https://www.google.com/maps/search/?api=1&query=' + __import__('urllib.parse', fromlist=['quote']).quote(p['map_query']),
                'latitude': p.get('latitude'), 'longitude': p.get('longitude'),
                'transport_mode': transport_label(nxt.get('transport_mode', '')), 'transfer_minutes': nxt.get('transfer_minutes'), 'distance_km': nxt.get('distance_km')})
        row['time_range'] = day.get('time_range', '按当天安排')
        row['pace_label'] = day.get('pace_label', '可按体力删减')
        result.append(row)
    return result


def runtime_bindings(profile):
    name = str(profile['display_name'])
    trip = profile['trip']
    count = len(profile['itinerary'])
    cover = profile['cover']
    slug = re.sub('[^a-z0-9]+', '-', profile['destination'].lower()).strip('-') or 'travel'
    namespace = profile.get('handbook_id', slug + '-' + str(profile['year']))
    dates = f"{trip['start_date']} — {trip['end_date']}" if trip['start_date'] != 'pending' else '日期待确认'
    h = lambda x: escape(str(x), quote=True)
    language_code = profile['module_groups']['language'].get('language_code', 'en-US')
    currency = {'日本': 'JPY', 'Japan': 'JPY', '韩国': 'KRW', 'South Korea': 'KRW', '印度尼西亚': 'IDR', 'Indonesia': 'IDR', '中国': 'CNY', 'China': 'CNY', '美国': 'USD', 'United States': 'USD', '香港': 'HKD', 'Hong Kong': 'HKD'}.get(str(profile.get('country', '')))
    if not currency:
        currency = {'ja': 'JPY', 'ko': 'KRW', 'id': 'IDR', 'zh-CN': 'CNY', 'zh-HK': 'HKD', 'en-US': 'USD'}.get(language_code.split('-')[0] if language_code.startswith(('ja-', 'ko-', 'id-')) else language_code, 'USD')
    config = {'destination': name, 'days': count, 'dates': dates, 'namespace': namespace, 'currency': currency,
              'language': language_code,
              'start_date': trip['start_date'], 'end_date': trip['end_date']}
    data = trip_days(profile)
    chapters = [['route', '行程', '路线与每日安排'], ['stay', '航班与住宿', '已确认资料与待办'],
                ['sights', '景点', '已安排与可选'], ['food', '餐饮指南', '小吃、餐厅与菜单'],
                ['shops', '购物指南', '门店与伴手礼'], ['move', '当地特色体验', '按兴趣替换'],
                ['booking', '出发前准备', '预约与行李'], ['words', '语言锦囊', '当地语言与英语'], ['tips', '旅游贴士', '实用提醒']]
    nav = ''.join(f'<a href="#{x[0]}" data-page="{x[0]}"><span>{i:02}</span>{h(x[1])}</a>' for i, x in enumerate(chapters, 1))
    sidebar = f'<a class="atlas-brand" href="#home"><span class="atlas-mark">旅</span><div>{h(name)}<span>TRAVEL FIELD NOTES</span></div></a><div class="atlas-trip-label">{count}天{count-1}晚<small>{h(dates)} · 人数{h(trip.get("travelers","待确认"))}</small></div><nav aria-label="手册章节"><a href="#home" data-page="home"><span>⌂</span>旅行首页</a>{nav}</nav><div class="atlas-sidebar-foot"><span class="atlas-dot"></span>离线手册<small>内容与图片随手册保存。</small></div>'
    home = f'<div class="atlas-home-title"><div><p class="atlas-eyebrow">{h(cover["kicker"])}</p><h1>{h(cover["title"])}</h1></div><span class="atlas-edition">{h(name)} / {h(profile["year"])}<br>旅行手册</span></div><div class="atlas-cover"><img src="{h(cover["image"])}" alt="{h(name)}旅行封面"><div class="atlas-cover-shade"></div><div class="atlas-cover-copy"><p>{h(cover["kicker"])}</p><h2>{h(name)}<br><em>{h(cover["title"])}</em></h2><span>{h(cover["summary"])}</span><a class="atlas-primary" href="#route">翻开{count}天行程 <span>↗</span></a></div><div class="atlas-cover-caption">{h(dates)}<span>{count}天{count-1}晚</span></div></div><div class="atlas-quickline"><div><b>{count:02}</b><span>天的旅行安排</span></div><div><b>{count-1:02}</b><span>晚的城市停留</span></div><div><b>08</b><span>个随行章节</span></div><button class="atlas-trip-open">进入旅行模式 <span>↗</span><small>路线 · 地图 · 摄影 · 记账</small></button></div><div class="atlas-section-title"><h2>每天的旅行书签</h2><span>点一天，展开详细安排</span></div><div class="atlas-day-list"></div><div class="atlas-bottom-note"><span>TRAVEL FIELD NOTES</span><p>内容与图片可离线阅读；导航和外部服务需联网。</p><a href="#booking">检查行李与预约 ↗</a></div>'
    maps = []
    for di, day in enumerate(data):
        for start in range(0, len(day['stops']), 4):
            if start and len(day['stops'][start:]) == 1:
                break
            maps.append({'dayIndex': di, 'file': f'media/routes/day-{len(maps)+1}.svg'})
    result = []
    for path in ROOT.iterdir():
        if path.suffix not in {'.js', '.css', '.json'} or path.name == 'gsap.min.js':
            continue
        source = path.read_text(encoding='utf-8')
        original = source
        if path.name in {'content-revision.js', 'itinerary-overrides.js'}:
            source = '// Reference-only content disabled; destination data comes from the compiled profile.\n'
        elif path.name == 'audit-itinerary-data.js':
            source = 'window.HANDBOOK_CONFIG=' + json.dumps(config, ensure_ascii=False) + ';\nwindow.BALI_ITINERARY=' + json.dumps(data, ensure_ascii=False) + ';\n'
        elif path.name == 'trip-route-maps.js':
            if any(day.get('route_screenshots') for day in profile['itinerary']):
                from _route_screenshots import screenshots_html
                cards=[screenshots_html(day) for day in profile['itinerary']]
                if not all(cards):
                    raise ValueError('screenshot map mode requires every day; do not silently mix incomplete maps')
                source="(function(){var cards="+json.dumps(cards,ensure_ascii=False).replace('<','\\u003c')+";window.TripRouteMaps={mode:'screenshots',render:function(day,index){return cards[index]||'<p>路线截图待补充</p>'}}})();"
            else:
                source = Path(__file__).with_name('online-route-map.js').read_text(encoding='utf-8')
        elif path.name == 'redesign.js':
            source = re.sub(r' const chapters=.*?;\n', ' const chapters=' + json.dumps(chapters, ensure_ascii=False) + ';\n', source, count=1)
            source = re.sub(r' sidebar\.innerHTML=`.*?`;\n', lambda m: ' sidebar.innerHTML=' + json.dumps(sidebar, ensure_ascii=False) + ';\n', source, count=1)
            source = re.sub(r' home\.innerHTML=`.*?`;\n', lambda m: ' home.innerHTML=' + json.dumps(home, ensure_ascii=False) + ';\n', source, count=1)
            source = source.replace('「乌布」', '「景点」')
        elif path.name == 'mobile-edition.js':
            # Unknown dates must not start the reference itinerary's countdown.
            source = source.replace("if(!cover)return;", "if(!cover||!window.HANDBOOK_CONFIG||window.HANDBOOK_CONFIG.start_date==='pending')return;")
            source = re.sub(r"const departure=Date.parse\(.*?\),tripEnd=Date.parse\(.*?\);", "const departure=Date.parse(window.HANDBOOK_CONFIG.start_date),tripEnd=Date.parse(window.HANDBOOK_CONFIG.end_date);", source)
            source = source.replace('09.18 · 07:20 上海出发', h(dates)).replace('享受岛屿时光', '按当天安排出发')
            source = source.replace('专程去的餐厅、酒店附近的选择，还有不想出门时的外卖清单。', '当地小吃、专程餐厅与本地连锁，按当天路线选择。')
        elif path.name == 'inline-1.js':
            source = '\n'.join(line for line in source.splitlines() if "var start=new Date(" not in line)
        elif path.name == 'trip-mode.js':
            # Keep shopping guidance readable in Trip Mode itself; no exit link.
            shopping = "function shopping(d){var n=d.shopping_advice;if(!n)return'';var paragraphs=String(n.description||'').split(/\\n+/).filter(function(t){return t.trim()}).map(function(t){return '<p>'+esc(t)+'</p>'}).join('');return '<details class=\"trip-shopping-tip\"><summary><span><small>SHOPPING · 顺路逛</small><b>'+esc(n.title)+'</b></span><i>＋</i></summary><div class=\"trip-shopping-body\">'+paragraphs+'</div></details>'}"
            source, replaced = re.subn(r'^function shopping\(d\).*$', lambda m: shopping, source, count=1, flags=re.M)
            if replaced != 1:
                raise ValueError('current-system shopping renderer marker missing')
            backup = "function backupPlan(d){var value=String(d.fallback||'').trim();if(!value)return'';return '<details class=\"trip-shopping-tip trip-backup-tip\"><summary><span><small>PLAN B · 天气与体力</small><b>备选方案</b></span><i>＋</i></summary><div class=\"trip-shopping-body\">'+value.split(/\\n+/).filter(function(t){return t.trim()}).map(function(t){return '<p>'+esc(t)+'</p>'}).join('')+'</div></details>'}"
            source = source.replace(shopping, shopping + '\n' + backup, 1)
            anchor = "</details><div class=\"trip-overview\"><span>今日地点<b>'+d.stops.length+' 站</b></span><span>行程时段<b>'+esc(d.time_range||((d.stops[0]&&d.stops[0].time)||'待定')+'起')+'</b></span><span>节奏<b>'+esc(d.pace_label||'按时推进')+'</b></span></div></section>"
            if source.count(anchor) != 1:
                raise ValueError('current-system itinerary overview marker missing')
            source = source.replace(anchor, "</details></section>'+backupPlan(d)+'", 1)
            source = source.replace('摄影与要点</button>', '摄影与穿搭</button>')
            source = source.replace('摄影与穿搭</button>', '摄影穿搭</button>')
            outfit_js = "function outfits(n){var a=n.outfit_advice||{};return [['women','女生穿搭'],['men','男生穿搭'],['practical_note','当天调整']].map(function(pair){return typeof a[pair[0]]==='string'&&a[pair[0]].trim()?'<article class=\"trip-shot trip-outfit\"><b>'+pair[1]+'</b><div><span>'+esc(a[pair[0]])+'</span></div></article>':''}).join('')}\n"
            source = source.replace('function photo(d,di){', outfit_js+'function photo(d,di){', 1)
            photo_anchor = "return'<section class=\"trip-photo-card\">"
            if photo_anchor not in source:
                raise ValueError('current-system photo card marker missing')
            source = source.replace(photo_anchor, 'cards+=outfits(n);'+photo_anchor, 1)
            source = source.replace("function backupPlan(d){", "function routeNote(d){return d.route_note?'<p class=\"trip-route-note\">'+esc(d.route_note)+'</p>':''}\nfunction backupPlan(d){", 1)
            source = source.replace("'+backupPlan(d)+'", "'+backupPlan(d)+routeNote(d)+'", 1)
            source = source.replace('PHOTO NOTES · 摄影和当日要点', 'PHOTO NOTES · 摄影与穿搭').replace("n.title||'摄影与当日要点'", "n.title||'摄影与穿搭'").replace('<strong>现场提醒</strong>', '<strong>摄影与穿搭提醒</strong>')
            source = source.replace(" panel.dataset.tripView=view;", " panel.dataset.tripView=view;\n var shell=$('.trip-mode-panel',panel);if(shell)shell.dataset.tripView=view;")
            source = source.replace("var d=list[i],c=$('.trip-mode-content',panel);", "var d=list[i],c=$('.trip-mode-content',panel),activeTab=$('.trip-view-tabs [data-trip-view].is-active',panel),currentView=activeTab?activeTab.dataset.tripView:(panel.dataset.tripView||'itinerary');panel.dataset.tripView=currentView;")
            source = source.replace("selectView(panel,panel.dataset.tripView||'itinerary');", "if(currentView!=='expense')selectView(panel,currentView);")
            source = re.sub(r'function mapQuery\(name\)\{.*?\}\n', "function mapQuery(name){return name+' '+destination()}\n", source, count=1)
            source = re.sub(r'function mapPoints\(d\)\{.*?\}\n', '', source, count=1)
            source = source.replace('travel-handbook-trip-companion-v2', namespace + '-reference-photos').replace('travel-handbook-trip-day', namespace + '-trip-day')
        elif path.name == 'shared-ledger.js':
            # Keep the ledger useful across destinations: expose JPY and select
            # the compiled destination currency instead of inheriting Bali/Korea.
            if '<option>JPY</option>' not in source:
                source = source.replace('<option>KRW</option>', '<option>JPY</option><option>KRW</option>')
            source = source.replace('data-fx-refresh>自动校准', 'data-fx-refresh>刷新最新汇率').replace('联网时自动读取最新参考汇率，也可手动修改。', '联网时读取最新参考汇率；离线时可手动填写。')
            marker = " const fxStoreKey='travel-ledger-fx:'+(window.HANDBOOK_CONFIG?.slug||document.title||location.pathname);"
            currency_setup = marker + "\n const destinationCurrency=window.HANDBOOK_CONFIG?.currency||'USD';[fxFrom,form.elements.currency].forEach(select=>{if(![...select.options].some(o=>o.value===destinationCurrency))select.add(new Option(destinationCurrency,destinationCurrency),0);select.value=destinationCurrency});"
            source = source.replace(marker, currency_setup, 1)
            saved_marker = " try{const saved=JSON.parse(localStorage.getItem(fxStoreKey)||'null');if(saved){fxFrom.value=saved.from||fxFrom.value;fxTo.value=saved.to||fxTo.value;fxRate.value=saved.rate||fxRate.value}}catch(e){}"
            default_pair = " try{const saved=JSON.parse(localStorage.getItem(fxStoreKey)||'null');fxRate.value=saved&&saved.from===destinationCurrency&&saved.to==='CNY'?saved.rate:''}catch(e){fxRate.value=''}\n fxFrom.value=destinationCurrency;fxTo.value='CNY';"
            source = source.replace(saved_marker, default_pair, 1)
            source = source.replace("function renderFx(){", "function renderFx(){if(!fxRate.value||!(Number(fxRate.value)>0)){fxResult.textContent='—';return}", 1)
            source = source.replace("const data=await res.json();", "const data=await res.json();if(fxFrom.value!==from||fxTo.value!==to)return;", 1)
            source = source.replace("()=>calibrateFx(true)));", "()=>{fxRate.value='';renderFx();calibrateFx(true)}));", 1)
            if 'data-fx-refresh' not in source:
                source = source.replace('<small>按银行卡或换汇渠道的当前汇率填写，仅用于估算。</small>', '<button type="button" data-fx-refresh>自动校准</button><small data-fx-status>联网时自动读取最新参考汇率，也可手动修改。</small>', 1)
                source = source.replace(",fxResult=$('[data-fx-result]');", ",fxResult=$('[data-fx-result]'),fxRefresh=$('[data-fx-refresh]'),fxStatus=$('[data-fx-status]');", 1)
                render_marker = " function renderFx(){const amount=Number(fxAmount.value)||0,rate=Number(fxRate.value)||0;fxResult.textContent=Number(amount*rate).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});try{localStorage.setItem(fxStoreKey,JSON.stringify({from:fxFrom.value,to:fxTo.value,rate:rate}))}catch(e){}}"
                calibrate = "\n async function calibrateFx(force){const from=fxFrom.value,to=fxTo.value;if(from===to){fxRate.value='1';fxStatus.textContent='同币种汇率为 1';renderFx();return}const cacheKey=fxStoreKey+':latest:'+from+':'+to;try{const cached=JSON.parse(localStorage.getItem(cacheKey)||'null');if(!force&&cached&&Date.now()-cached.savedAt<21600000){fxRate.value=cached.rate;fxStatus.textContent='参考汇率 · '+cached.date+' 更新';renderFx();return}}catch(e){}fxRefresh.disabled=true;fxStatus.textContent='正在获取最新参考汇率…';try{const res=await fetch('https://api.frankfurter.dev/v2/rate/'+encodeURIComponent(from)+'/'+encodeURIComponent(to));if(!res.ok)throw Error('rate');const data=await res.json();if(!Number.isFinite(Number(data.rate)))throw Error('rate');fxRate.value=Number(data.rate).toFixed(Number(data.rate)<.01?6:4);try{localStorage.setItem(cacheKey,JSON.stringify({rate:fxRate.value,date:data.date,savedAt:Date.now()}))}catch(e){}fxStatus.textContent='参考汇率 · '+data.date+' 更新';renderFx()}catch(e){fxStatus.textContent='暂时无法自动校准，可继续手动填写'}finally{fxRefresh.disabled=false}}"
                source = source.replace(render_marker, render_marker + calibrate, 1)
                source = source.replace(" ;[fxAmount,fxFrom,fxTo,fxRate].forEach(x=>x.addEventListener('input',renderFx));renderFx();", " ;[fxAmount,fxRate].forEach(x=>x.addEventListener('input',renderFx));[fxFrom,fxTo].forEach(x=>x.addEventListener('change',()=>calibrateFx(true)));fxRefresh.addEventListener('click',()=>calibrateFx(true));renderFx();calibrateFx(false);", 1)
        elif path.name == 'travel-utilities.js':
            source = source.replace('两段航班 · 两处住宿', '交通与住宿按已确认资料展示')
            source = re.sub(r"const category=.*?;\n", "const category=row.dataset.category||'行程';\n", source, count=1)
            source = re.sub(r"const level=/Kebun.*?;\n", "const level=Number(row.dataset.priority||0);\n", source, count=1)
            source = re.sub(r'const extraTips=\[.*?\];', 'const extraTips=[];', source, count=1, flags=re.S)
            source = re.sub(r'const mustTips=new Set\(.*?\);', 'const mustTips=new Set(' + json.dumps([x['title'] for g in profile['module_groups']['travel_notes'] for x in g['items'] if x.get('priority') == '必须'], ensure_ascii=False) + ');', source, count=1)
            source = re.sub(r'const mustTips=new Set\(.*?\);', '', source)
            source = re.sub(r'const flexibleTips=new Set\(.*?\);', '', source)
            source = source.replace("const level=mustTips.has(h.textContent.trim())?0:flexibleTips.has(h.textContent.trim())?2:1;", "const level=['必须','建议','随缘'].indexOf(card.dataset.tipPriority);if(level<0){console.error('Missing tip priority',h.textContent);return;}")
            source = source.replace("const lang=/巴厘岛常见词|地名辨认|印尼语/.test(group)?'id-ID':'en-US'", "const lang=row.closest('.language-edition')?.querySelector('h3')?.textContent==='英语备用'?'en-US':window.HANDBOOK_CONFIG.language")
            source = source.replace('<b>A7C II</b>', '<b>${esc(c.model)}</b>')
            source = source.replace('预约勾选两人共享', '预约勾选由同行成员共享')
            source = source.replace("panel.dataset.tripView='expense';all('[data-trip-view]'", "panel.dataset.tripView='expense';const overlay=panel.closest('.trip-mode-overlay');if(overlay)overlay.dataset.tripView='expense';all('[data-trip-view]'")
        elif path.name == 'manifest.json':
            source = json.dumps({'name': name + '旅行手册', 'short_name': name + '手册', 'start_url': './index.html', 'display': 'standalone'}, ensure_ascii=False)
        # Namespaces and generic static identity text; never copy personal state.
        # Runtime storage namespaces are destination-specific, but bundled font
        # filenames are immutable assets copied from the canonical product.
        # Rewriting bali-sans/bali-serif in fonts.css creates references to
        # files that are never installed and produces two avoidable 404s.
        if path.name != 'fonts.css':
            source = re.sub(r'\bbali(?=[-:])', namespace, source)
        source = source.replace('2026 巴厘岛双人旅行手册', str(profile['year']) + ' ' + name + '旅行手册').replace('巴厘岛', name)
        if path.suffix == '.css':
            if path.name == 'travel-utilities.css':
                source += '''
/* Static galleries contain one full-width figure, not one column of a two-image strip. */
body.atlas-ui #atlas-main .movement-visual,body.atlas-ui #atlas-main .gallery-wrap.is-static{width:100%!important;max-width:100%!important;min-width:0!important}

body.atlas-ui #atlas-main .gallery-wrap.is-static .photo-strip{display:block!important;width:100%!important}
body.atlas-ui #atlas-main .gallery-wrap.is-static .photo-strip>figure{display:block!important;width:100%!important;min-width:100%!important;max-width:100%!important;margin:0!important;flex:0 0 100%!important}
body.atlas-ui #atlas-main .gallery-wrap.is-static .photo-strip>figure img{display:block!important;width:100%!important;object-fit:cover}
/* Food editorial components and compact preparation rows. */
body.atlas-ui .trip-backup-tip{background:#f3ecdf!important;border:1px solid #ddcfb8!important;color:#4d493e!important}
body.atlas-ui .trip-backup-tip>summary :is(small,b){color:#635339!important}
body.atlas-ui .trip-backup-tip .trip-shopping-body p{color:#4d493e!important;line-height:1.8!important}
body.atlas-ui #booking .packing-checklist label>div{display:flex!important;flex-wrap:wrap;align-items:center;gap:6px 10px;min-width:0}
body.atlas-ui #booking .packing-checklist label>div>b{font-size:15px!important;line-height:1.5!important}
body.atlas-ui #booking .packing-checklist label>div>small{display:block!important;flex-basis:100%;font-size:13px!important;line-height:1.65!important;margin:0!important}
body.atlas-ui #booking .packing-priority{display:inline-block!important;font:500 11px/1.5 var(--interface-font),sans-serif!important;padding:3px 7px!important;border-radius:6px;white-space:nowrap;margin:0!important;color:#455449;background:#e8eee7}
body.atlas-ui #booking .packing-priority.is-must{color:#773d2d;background:#f4e3d9}
body.atlas-ui #booking .packing-priority.is-recommended{color:#6b572b;background:#f2e9cc}
body.atlas-ui #booking .packing-priority.is-optional{color:#586457;background:#e9ede5}
body.atlas-ui #food :is(.menu-editorial,.snack-grid){font-family:var(--interface-font),sans-serif!important;font-size:15px;line-height:1.75}
body.atlas-ui #food .menu-editorial{padding:18px 20px 22px;min-width:0}
body.atlas-ui #food .menu-editorial>h3{font-size:24px!important;line-height:1.4!important;font-weight:650!important;margin:6px 0 10px!important}
body.atlas-ui #food .menu-intro{max-width:68ch;margin:0 0 20px!important}
body.atlas-ui #food :is(.menu-guide-grid,.snack-grid){display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
body.atlas-ui #food :is(.menu-guide-grid>article,.snack-card){min-width:0;padding:18px!important;background:var(--color-sand,#f6f3ec);border:1px solid #7d857b26;border-radius:12px}
body.atlas-ui #food .menu-guide-grid h4{font-size:17px!important;font-weight:650!important;line-height:1.5!important;margin:0 0 8px!important}
body.atlas-ui #food :is(.menu-guide-grid p,.snack-card p){margin:0!important;line-height:1.75!important}
body.atlas-ui #food .snack-grid{padding:16px 20px 22px}
body.atlas-ui #food .snack-card h3{display:block!important;font:650 19px/1.5 var(--interface-font),sans-serif!important;margin:0!important}
body.atlas-ui #food .snack-card>small{display:block;margin:2px 0 12px;font:14px/1.5 var(--interface-font),sans-serif;opacity:.75}
body.atlas-ui #food .snack-card dl{margin:12px 0 0}
body.atlas-ui #food .snack-card dl>div{display:grid;grid-template-columns:5em minmax(0,1fr);gap:10px;margin-top:8px}
body.atlas-ui #food .snack-card dt{font-weight:600;font-size:13px}
body.atlas-ui #food .snack-card dd{margin:0;font-size:14px}
body.atlas-ui #food .menu-dictionary{margin-top:20px}
body.atlas-ui #food .menu-primer-grid{padding:0 16px 12px}
body.atlas-ui #food .menu-primer-grid>div{display:grid;grid-template-columns:minmax(90px,1fr) minmax(100px,1fr) minmax(0,3fr);gap:8px 18px;align-items:baseline;padding:12px 0;border-bottom:1px solid #7d857b26}
body.atlas-ui #food .menu-primer-grid b{font-size:16px;font-weight:650}
body.atlas-ui #food .menu-primer-grid p{margin:0!important;font-size:14px!important;line-height:1.6!important}
body.atlas-ui #food :is(.food-chapter,.menu-dictionary)>summary{display:flex!important;align-items:center!important;gap:12px!important;padding:12px 20px!important;min-height:48px!important}
body.atlas-ui #food :is(.food-chapter,.menu-dictionary)>summary b{font-size:18px!important;line-height:1.4!important;flex:1;min-width:0}
body.atlas-ui #food :is(.food-chapter,.menu-dictionary)>summary i{flex:0 0 auto}
body.atlas-ui #booking .audit-reservation{grid-template-columns:minmax(0,1fr) auto auto 36px!important;gap:8px!important;padding:8px 0!important;align-items:center!important}
body.atlas-ui #booking .audit-reservation>time{display:none!important}
body.atlas-ui #booking .audit-reservation>h4{grid-column:1!important;grid-row:1!important;margin:0!important;font-size:14px!important;line-height:1.4!important}
body.atlas-ui #booking .reservation-type{display:none!important}
body.atlas-ui #booking .audit-reservation>.audit-priority{grid-column:2!important;grid-row:1!important;font-size:11px!important;padding:3px 5px!important}
body.atlas-ui #booking .audit-reservation>.reservation-check{grid-column:3!important;grid-row:1!important;min-height:36px!important;gap:0!important;font-size:0!important}
body.atlas-ui #booking .reservation-check input{width:20px!important;height:20px!important;margin:0!important}
body.atlas-ui #booking .audit-reservation>.reservation-notes{grid-column:4!important;grid-row:1!important;align-self:center!important}
body.atlas-ui #booking .audit-reservation>.reservation-notes>summary{width:36px!important;min-width:36px!important;height:36px!important;min-height:36px!important;border:0!important}
body.atlas-ui #booking .audit-reservation>.reservation-notes[open]{grid-column:1/-1!important;grid-row:2!important}
body.atlas-ui #booking .reservation-notes[open]>summary{margin-left:auto!important}
body.atlas-ui #booking .reservation-notes p{margin:4px 0 8px!important;font-size:14px!important;line-height:1.65!important}
@media(max-width:640px){
body.atlas-ui #food :is(.menu-guide-grid,.snack-grid){grid-template-columns:minmax(0,1fr);gap:12px}
body.atlas-ui #food :is(.menu-editorial,.snack-grid){padding:14px 12px 18px}
body.atlas-ui #food .menu-primer-grid>div{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
body.atlas-ui #food .menu-primer-grid p{grid-column:1/-1}
body.atlas-ui #booking .audit-reservations{padding:14px!important}
}
'''
            if path.name == 'interface-polish.css':
                source += '''
/* Center tool contents and let the cover introduction breathe. */
body.atlas-ui .atlas-desktop-tools :is(.atlas-desktop-adjust,.trip-mode-launch){display:inline-flex!important;align-items:center!important;justify-content:center!important;padding:0 14px!important;text-align:center!important}
body.atlas-ui .atlas-desktop-tools button :is(svg,span){transform:none!important}
body.atlas-ui .atlas-desktop-tools button span{display:inline-block;line-height:1!important}
body.atlas-ui #top.hero.jungle-cover .lede{background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important;backdrop-filter:none!important;padding:0!important;font-family:"Noto Serif SC","Songti SC","STSong","SimSun",serif!important;font-size:clamp(18px,1.35vw,22px)!important;font-weight:500!important;line-height:1.85!important;letter-spacing:.06em!important;color:#fffaf0!important;text-shadow:0 2px 10px rgba(0,0,0,.65)!important;text-wrap:pretty;max-width:42em!important}
'''
            source = re.sub(r'media/(?:asset-\d+|cover[^\)\'" ]*)\.(?:webp|jpg|png)', cover['image'], source)
            source = source.replace('BALI 2026', profile['destination'].upper() + ' ' + str(profile['year']))
        if source != original:
            result.append({'path': path.name, 'content': source})
    return result


def preparation_html(profile, base):
    """Keep current compact priority rows, including user-maintained check state."""
    h = lambda x: escape(str(x), quote=True)
    items = profile['module_groups']['preparation']['confirm_ahead']
    rows = []
    for i, item in enumerate(items):
        item = dict(item)
        item['item'] = item.get('item') or item.get('title') or ''
        item['detail'] = item.get('detail') or item.get('note') or ''
        if item.get('timing'):
            item['detail'] = str(item['timing']) + ' · ' + item['detail']
        level = {'必须': 0, '建议': 1, '随缘': 2}.get(item.get('priority'), 1)
        rows.append(f'<article class="audit-reservation" data-priority="{level}" data-order="{i}" data-category="{h(item.get("category","行程"))}"><time>{h(item.get("timing",""))}</time><h4>{h(item["item"])}</h4><span class="audit-priority">{h(item.get("priority","建议"))}</span><label>处理状态<select data-reservation-id="prepare-{i}"><option>未处理</option><option>已预约，有凭证</option></select></label><details class="reservation-notes"><summary aria-label="展开预约说明" title="展开预约说明"></summary><p>{h(item.get("detail",""))}</p></details></article>')
    panel = '<div class="audit-reservations"><h3>预约与确认</h3><p>勾选仅表示已处理，不代表商家确认。</p><div class="reservation-toolbar"><div class="reservation-sort" role="group" aria-label="预约排序"><button type="button" data-reservation-sort="priority" aria-pressed="true">按优先级</button></div></div><div class="audit-reservation-list">' + ''.join(rows) + '</div></div>'
    start = base.find('<div class="prepare-block"><div class="prepare-heading"><span>02</span>')
    end = base.find('<a class="back-to-contents"', start)
    if start < 0 or end < 0:
        raise ValueError('preparation fragment injection marker missing')
    return base[:start] + panel + base[end:]
