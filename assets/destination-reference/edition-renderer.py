from pathlib import Path
import json,html,re,base64,sys,hashlib,os,subprocess
from urllib.parse import quote
from PIL import Image, ImageOps
R=Path(sys.argv[1]); E=html.escape
if os.environ.get('JOURNAL_BUILD_STAGE','preview')=='release':
 for checker in ('coverage_release.py','editorial_release.py'):
  subprocess.run([sys.executable,'-X','utf8',str(R/checker),str(R)],check=True)
identity_files=[p for p in R.iterdir() if p.suffix in ['.py','.js','.json','.css'] and p.name not in ['build-manifest.json','QA.json','directory-audit.json','magazine-workbench.json']]+list((R/'media').glob('*'))+list((R/'maps').glob('*.webp'))+list((R/'fonts').glob('*.woff2'))
build_id=hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in sorted(identity_files) if p.is_file())).hexdigest()[:20]
G=json.loads((R/'content.json').read_text(encoding='utf8')); C=json.loads((R/'edition.json').read_text(encoding='utf8')); T=json.loads((R/'editorial-content.json').read_text(encoding='utf8'))
from language_fields import normalized_language_content
T=normalized_language_content(T,C.get('lang',''))
photos=json.loads((R/'place-photos.json').read_text(encoding='utf8'))
photo_editorial=json.loads((R/'edition-photos.json').read_text(encoding='utf8'));allphotos=photos|photo_editorial
from validate_edition import validate
validate(G,C,T,allphotos)
G['edition']={k:v for k,v in C.items() if k!='verification'};G['coordinates']=json.loads((R/'verified-coordinates.json').read_text(encoding='utf8'));G['maps']=json.loads((R/'maps.json').read_text(encoding='utf8'));G['placePhotos']=photos;G['images']={k:v['src'] for k,v in photos.items()};G['imageCaptions']={k:v['caption'] for k,v in photos.items()};P={p['id']:p for p in G['places']}
from editorial_evidence import audit_evidence
evidence_errors=audit_evidence(T,required=C.get('editorialEvidenceVersion',0)>=1,area_ids=[a['id'] for a in G['areas']])
if evidence_errors:raise ValueError('\n'.join(evidence_errors))
N=len(G['days']); city=C['city']; span=C['span']; en=C['english']
chapters=[('orientation','GET YOUR BEARINGS','认识'+city,'城市背景 · 生活风貌 · 住宿选择'),('neighbourhoods','ISLAND LIFE' if en=='BALI' else 'CITY LIFE','街区与当地生活','区域特色 · 街头文化 · 值得细看'),('itinerary',C['daysEnglish']+' DAYS','每日详细行程','具体时刻 · 交通预留 · 天气备选'),('food','AT THE TABLE','美食与餐厅','吃什么 · 去哪吃 · 如何点餐'),('shopping','GOOD FINDS','购物与伴手礼','材质与用途 · 地点 · 愿望单'),('culture','ART & CULTURE','文化与参观','看懂当地 · 参观候选 · 现场礼仪'),('directory','ADDRESS BOOK','地点库','搜索筛选 · 收藏 · 地址导航'),('fieldnotes','FIELD NOTES','交通与实用贴士','按主题查找 · 现场问题 · 联络卡'),('prepare','BEFORE YOU GO','行前准备与语言卡','预约事项 · 打包清单 · 沟通用语'),('tools','ON THE ROAD','随身工具','记账 · 笔记 · 照片票据 · 备份')]
chapter_order=['orientation', 'neighbourhoods', 'itinerary', 'food', 'culture', 'shopping', 'fieldnotes', 'prepare', 'directory', 'tools']
chapters=sorted(chapters,key=lambda c:chapter_order.index(c[0]))
chapter_pages={}
cssfiles=['style.css','film-layout.css','body-font.css','serif-font.css','bali.css','map-ui.css','map-polish.css','fukuoka.css','enhancements.css','editorial-layout.css','reader-components.css','tokens.css','magazine.css','fashion.css','art.css','ui-polish.css','font-supplement.css','edition.css','directory.css','ledger.css','travel-readability.css','magazine-polish.css','photo-overprint.css','reader-density.css','mobile-travel.css','travel-alternatives.css','editorial-premium.css','travel-interior.css','impeccable-editorial.css','impeccable-interior.css','travel-reference.css']
def image_dimensions(source):
 with Image.open(R/source) as image:
  return ImageOps.exif_transpose(image).size
def photo_crop(f):
 if not (f.get('position') or f.get('mobilePosition')):return ''
 positions=[f.get('position','50% 50%'),f.get('mobilePosition',f.get('position','50% 50%'))]
 for value in positions:
  if not re.fullmatch(r'\d+(?:\.\d+)?% \d+(?:\.\d+)?%',value) or any(float(n)>100 for n in re.findall(r'[\d.]+',value)):raise ValueError('Photo position must be two percentages within 0–100: '+value)
 return ' data-editorial-crop style="--editorial-position:'+positions[0]+';--editorial-position-mobile:'+positions[1]+';object-position:var(--editorial-position)"'
def pic(k,words=None,cls=''):
 f=allphotos.get(k)
 if not f:return ''
 w,h=image_dimensions(f['src'])
 image=f'<img src="{f["src"]}" width="{w}" height="{h}" alt="{E(f["caption"])}" loading="lazy" data-zoom{photo_crop(f)}>'
 if f.get('mobileSrc'):image='<picture><source media="(max-width:700px)" srcset="'+f['mobileSrc']+'">'+image+'</picture>'
 if words:image='<div class="edition-plate '+cls+'">'+image+'<div class="edition-type" aria-hidden="true">'+''.join('<span>'+E(s)+'</span>' for s in words)+'</div></div>'
 return '<figure>'+image+'<figcaption>'+E(f['caption'])+' · <a target="_blank" rel="noopener" href="'+E(f['page'])+'">摄影来源 ↗</a></figcaption></figure>'
def evidence(key,index):
 ids=T.get('section_sources',{}).get(key,{}).get(str(index),[])
 sources=T.get('editorial_sources',{})
 if not ids:return ''
 return '<p class="editorial-source-links">'+''.join('<a href="'+E(sources[sid]['url'],quote=True)+'" target="_blank" rel="noopener">'+E(sources[sid]['title'])+' ↗</a>' for sid in ids)+'</p>'
def paragraphs(text):return ''.join(('<p class="numeric-opening">' if part.strip()[0].isdigit() else '<p>')+E(part.strip())+'</p>' for part in text.split('\n\n') if part.strip())
def table(rows,key=None):return '<div class="editorial-table">'+''.join('<article><h4>'+E(r[0])+'</h4><div>'+''.join(paragraphs(part) for part in r[1:])+evidence(key,i)+'</div></article>' for i,r in enumerate(rows))+'</div>'
def refs(ids):return '<div class="shortlist">'+''.join(f'<button class="place-open" data-place="{id}"><span>{E(P[id]["kind"])}</span><strong>{E(P[id]["name"])}</strong><small>{E(P[id]["duration"])}</small><b>↗</b></button>' for id in ids if id in P)+'</div>'
from reader_reference import preparation_html, language_html, source_links

def restaurants():
 groups=[]
 for gi,group in enumerate(T.get('restaurant_groups',[]),1):
  cards=[]
  for a in group['items']:
   p=P[a['id']]
   nav='https://www.google.com/maps/search/?api=1&query='+quote(p.get('query',p['local']+' '+C['english']))
   cards.append('<details class="restaurant-pick" id="eat-'+a['id']+'" data-restaurant-id="'+E(a['id'])+'"><summary><span class="restaurant-summary-copy"><strong>'+E(p['name'])+'</strong><span>'+E(a.get('summary',p['area']+' · '+a['order']))+'</span></span><span class="restaurant-toggle" aria-hidden="true"></span></summary><div class="restaurant-detail"><p class="restaurant-reason">'+E(a['why'])+'</p><dl><div><dt>怎么点</dt><dd>'+E(a['order'])+'</dd></div><div><dt>安排参考</dt><dd>'+E(a['fit'])+'</dd></div><div><dt>预算档</dt><dd>'+E(a['budget'])+'</dd></div><div><dt>地址</dt><dd>'+E(p['where'])+'</dd></div></dl><p class="restaurant-note">'+E(a['note'])+'</p>'+source_links(a.get('sources',[]),T.get('editorial_sources',{}))+'<div class="restaurant-actions"><a href="'+E(nav)+'" target="_blank" rel="noopener">地图导航 ↗</a><a href="'+E(p['url'])+'" target="_blank" rel="noopener">资料来源 ↗</a><button data-place="'+a['id']+'">打开地点卡 ↗</button></div></div></details>')
  market=group.get('kind')=='market'
  groups.append('<section class="restaurant-group'+(' restaurant-markets' if market else '')+'"><header><p class="kicker">'+E(group['en'])+'</p><h3>'+E(group['name'])+'<small>'+str(len(cards))+(' 处' if market else ' 家')+'</small></h3>'+('<p>'+E(group['intro'])+'</p>' if group.get('intro') else '')+'</header><div class="restaurant-picks">'+''.join(cards)+'</div></section>')
 return '<div class="restaurant-guide-head"><h3>按想吃的来选</h3><p>点开店名，查看点单、预算与导航</p></div><div id="restaurant-guide">'+''.join(groups)+'</div>' if groups else ''
def toc(i):
 id,eng,zh,desc=chapters[i-1];return f'<a href="#{id}" class="toc-entry"><span class="toc-number">{i:02}</span><span class="toc-copy"><strong>{zh}</strong><small>{desc}</small></span><span class="toc-arrow">↗</span></a>'
def nav():return ''.join('<div class="toc-column">'+''.join(toc(i) for i in ids)+'</div>' for ids in [range(1,6),range(6,11)])
def section(key,deck,body):
 i=chapter_order.index(key)+1
 id,eng,zh,_=chapters[i-1]
 return f'<section id="{id}" class="wrap chapter" data-chapter="{i:02}"><header class="section-head" data-number="{i:02}"><p class="folio"><span>PRIVATE JOURNAL / {i:02}</span><span>{en} · {N:02} DAYS</span></p><h2><span class="section-display" lang="en">{eng}</span><span class="section-chinese">{zh}</span></h2><p class="section-summary">{deck}</p></header>{body}</section>'
cover=allphotos[C['cover']]
cover_width,cover_height=image_dimensions(cover['src'])
h=['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+city+' · '+span+' · 旅行杂志4.0</title>'+''.join(f'<link rel="stylesheet" href="{f}">' for f in cssfiles)+'</head><body data-days="'+str(N)+'" class="magazine-edition fashion-edition art-edition destination-edition overprint-edition"><a class="skip" href="#main">跳到正文</a><header class="topbar"><div class="masthead-inner"><button id="menu-open" aria-label="打开全书目录" aria-controls="menu-dialog" aria-expanded="false"><span>☰ 目录</span><small>10 章</small></button><a class="masthead" href="#cover"><span>PRIVATE JOURNAL</span><small>'+city+' · '+span+'</small></a><button id="pocket-open"><span>旅行模式 ↗</span></button></div></header><main id="main">']
h.append(f'''<section class="cover overprint-cover" id="cover" aria-labelledby="cover-title">
 <img id="cover-film" style="--cover-position:{E(C.get('coverPosition','50% 45%'))};--cover-position-mobile:{E(C.get('coverPositionMobile','50% 50%'))}" src="{cover['src']}" alt="{E(cover['caption'])}" width="{cover_width}" height="{cover_height}" fetchpriority="high" decoding="async">
 <div class="cover-ink-content">
  <div class="cover-ink-meta"><span>私人旅行杂志 / {E(city)}特刊</span><span>{E(C['country'])} · {N:02} DAYS / {N-1:02} NIGHTS</span></div>
  <div class="cover-ink-title" style="--cover-title-vw:{min(22,110/max(5,len(en))):.2f}vw;--cover-title-mobile:{min(25.5,130/max(5,len(en))):.2f}vw"><p>{E(C['coverLine'])}</p><div><h1 id="cover-title">{E(en)}</h1><span class="cover-city">{E(city)}</span></div></div>
  <div class="cover-ink-footer"><p>{C['coverNote']}</p><a class="cover-read" href="#reading-start">开始阅读 <span aria-hidden="true">↓</span></a></div>
 </div>
</section><div class="cover-photo-credit wrap"><span>{E(C.get('coverCredit',en))}</span><a href="{E(cover['page'])}" target="_blank" rel="noopener">{E(cover['caption'])} · 摄影来源 ↗</a></div>''')
h.append('<nav class="issue-days wrap" aria-label="逐日路线速览">'+''.join('<button data-overview-detail="'+str(i)+'"><span>'+str(i+1).zfill(2)+'</span><strong>'+E(d['area'])+'</strong></button>' for i,d in enumerate(G['days']))+'</nav>')
h.append(f'<div class="issue-ribbon wrap"><span>THE {en} EDIT</span><span>{C["coverLine"]}</span><span>PRIVATE JOURNAL / {N:02} DAYS</span></div><section class="edition-opening wrap" id="reading-start"><div><p class="kicker">EDITOR’S LETTER / 写在出发之前</p><h2>{C['editorTitle']}</h2><p class="editor-lead">{C["openingLead"]}</p></div><div><p>{C["intro"]}</p><p>从城市背景读到街区，再查看每日安排。出门后用「旅行模式」查时间和地址。收藏、账目、笔记与附件保存在当前浏览器，可导出备份。</p><p class="small">{span}，含抵达与返程。请按实际航班和住宿确认接送、预约与预算；行程中的时刻为建议安排。</p><a href="#journey-overview">直接看全程路线 ↗</a></div></section>')
h.append('<section class="journal-contents wrap"><div class="contents-intro"><p class="kicker">CONTENTS / 目次</p><h2><span>IN THIS</span><span>ISSUE.</span></h2><p>认识目的地，<br>再安排每一天。</p><div class="contents-stats"><span><b>'+str(N).zfill(2)+'</b>天</span><span><b>10</b>章</span><span><b>'+str(len(P))+'</b>地点</span></div></div><nav class="contents-grid" aria-label="全书章节">'+nav()+'</nav></section>')
portrait='<article class="city-portrait"><div class="city-portrait-body">'+''.join('<section><h4>'+E(row[0])+'</h4>'+paragraphs(row[1])+evidence('portrait',i)+'</section>' for i,row in enumerate(T['portrait']))+'</div></article>'
chapter_pages['orientation']=section('orientation',C['portraitLead'],portrait+'<h3 class="subheading">住在哪一带</h3>'+table(T['stays'],'stays')+'<details class="wide-detail"><summary>航班、酒店与接送记录<span>＋</span></summary><div class="reading-columns"><label>航班与到场要求<textarea data-note="flights" placeholder="航班 / 航站楼 / 到场时间 / 接送集合点"></textarea></label><label>住处与联系方式<textarea data-note="hotel" placeholder="当地名称 / 地址 / 电话 / 入住与退房 / 寄存"></textarea></label></div></details>')
# Route essays follow authored areas; no silent truncation or fixed city count.
themes=T['route_experiences']
assert len(themes)==len(G['areas']), 'Every area needs a route experience'
body='<nav class="route-essays" aria-label="区域索引">'+''.join(f'<a href="#area-{a["id"]}"><span>{i:02}</span><strong>{E(a["name"])}</strong><b>↓</b></a>' for i,a in enumerate(G['areas'],1))+'</nav>'
for i,(a,t) in enumerate(zip(G['areas'],themes),1):
 day=a['day'];f=allphotos[a['photo']];w,hh=image_dimensions(f['src'])
 mobile_source='<source media="(max-width:700px)" srcset="'+f['mobileSrc']+'">' if f.get('mobileSrc') else ''
 rows=T.get('area_sections',{}).get(a['id'],[])
 prose=''.join('<section class="district-section"><h4>'+E(row[0])+'</h4>'+''.join(paragraphs(p) for p in row[1:])+evidence('areas:'+a['id'],j)+'</section>' for j,row in enumerate(rows)) if rows else '<section class="district-section">'+paragraphs(a['body'])+'</section>'
 body+=f'''<article class="route-essay" id="area-{a['id']}">
  <header class="essay-running"><span>{i:02} / {E(a['en'])}</span><span>{E(a['name'])}</span></header>
  <figure class="essay-figure"><div class="ink-scene ink-{t['tone']}" style="--photo-max:{min(w,1800)}px"><picture>{mobile_source}<img src="{f['src']}" width="{w}" height="{hh}" alt="{E(f['caption'])}" loading="lazy" data-zoom{photo_crop(f)}></picture><div class="ink-words" aria-hidden="true">{''.join('<span>'+E(x)+'</span>' for x in t['words'])}</div></div><figcaption>{E(f['caption'])} · <a href="{E(f['page'])}" target="_blank" rel="noopener">摄影来源 ↗</a></figcaption></figure>
  <header class="area-introduction"><h3>{E(a['name'])}</h3><p>{E(a['deck'])}</p></header>
  <div class="area-reading"><div class="area-sections">{prose}</div><aside class="area-notebook"><h4>{E(t['title'])}</h4>{paragraphs(t['copy'])}{paragraphs(t['extra'])}{evidence('experiences:'+a['id'],0)}<button class="text-link" data-place="{t['place']}">{E(t['label'])} ↗</button><div class="area-geography"><h4>片区位置</h4>{paragraphs(a['route'])}{paragraphs(a['tip'])}</div></aside></div>
  <div class="area-itinerary-link"><button class="text-link" data-overview-detail="{day}">查看这一带的行程 →</button></div>{refs(a['ids'])}
 </article>'''
chapter_pages['neighbourhoods']=section('neighbourhoods',C['experienceLead'],body)
chapter_pages['itinerary']=section('itinerary','时刻用于理解一天的节奏。出门前核对预约与交通，遇上雨天按当天的备选安排走。','<div id="journey-overview"></div><div id="day-tabs" class="day-tabs" aria-label="选择旅行日"></div><div id="day-view"></div><details class="wide-detail" id="week-overview-fold"><summary>全程路线一览<span>＋</span></summary><div id="week-overview"></div></details>')
chapter_pages['food']=section('food','先决定想吃什么，再在当天区域里选餐厅。点单前确认份量、食材和总价。','<div class="edition-feature">'+pic(C['foodPhoto'],C['foodWords'])+'<div><p class="kicker">EATING IN '+en+'</p><h3>'+C['foodTitle']+'</h3><p>'+C['foodLead']+'</p></div></div>'+restaurants()+('' if T.get('restaurant_groups') else refs([p['id'] for p in G['places'] if p['kind']=='美食']))+'<div class="food-reading"><details class="wide-detail"><summary>看懂当地菜单<span>＋</span></summary>'+table(T['food_types'],'food_types')+'</details><details class="wide-detail"><summary>甜食与小吃<span>＋</span></summary>'+table(T.get('snacks',[]),'snacks')+'</details></div>')
chapter_pages['shopping']=section('shopping','从用途、材质和行李空间开始，少一些临出发前的折返。',table(T['shopping'],'shopping')+refs([p['id'] for p in G['places'] if p['kind']=='购物'])+'<label class="wish-label">购物愿望单<textarea data-note="wishlist" rows="4" placeholder="物品 / 用途 / 预算 / 所在区域 / 取件与包装"></textarea></label>')
chapter_pages['culture']=section('culture',C['cultureLead'],'<div class="edition-feature">'+pic(C['culturePhoto'],C['cultureWords'])+'<div><p class="kicker">LOOK A LITTLE CLOSER</p><h3>'+C['cultureTitle']+'</h3><p>'+C['cultureCopy']+'</p></div></div>'+table(T['culture'],'culture')+refs([p['id'] for p in G['places'] if p['kind'] in ['文化','自然','散步','海滩','体验']]))
chapter_pages['directory']=section('directory','按当地名称、街区或类别查找。照片用于认地点，完整地址与提示放在详情里。',f'<div class="address-intro"><p><b>{len(P)}</b><span>个地点<br>一份随身地址簿</span></p><div><span>FIND YOUR NEXT STOP</span><p>搜索 · 收藏 · 导航</p></div></div><div class="directory-search"><label><span>搜索地点</span><input id="place-search" type="search" placeholder="地名、当地名称或想做的事"></label><label><span>类别</span><select id="kind-filter"><option value="">全部类别</option>'+''.join('<option>'+E(k)+'</option>' for k in dict.fromkeys(p['kind'] for p in G['places']))+'</select></label><button id="saved-filter" aria-pressed="false">只看收藏</button></div><div class="directory-layout"><aside class="directory-sidebar"><p class="kicker">按所在区域找</p><nav id="directory-areas" aria-label="地点库区域"></nav></aside><div class="directory-main"><div class="directory-status"><p id="result-count" tabindex="-1" role="status" aria-live="polite"></p><button data-directory-reset hidden>清除筛选 ×</button></div><div id="place-results" class="directory-results"></div><nav id="directory-pages" class="directory-pages" aria-label="地点库分页"></nav></div></div>')
notes=''
for i,(name,rows) in enumerate(T['notes'].items()):notes+='<details class="note-fold" '+('open' if i==0 else '')+'><summary><h3>'+name+'</h3><span>'+str(len(rows))+' 条 / ＋</span></summary>'+table(rows,'notes:'+name)+'</details>'
chapter_pages['fieldnotes']=section('fieldnotes','出门前读一次，遇到具体问题再按主题查。',notes+'<label class="wish-label">离线联络卡<textarea data-note="contacts" rows="4" placeholder="酒店当地地址 / 电话 / 司机 / 保险援助 / 同行与家人"></textarea></label>')
body='<h3 class="subheading">需要提前确认的事</h3>'+table([r[:3] for r in T['reservations']],'reservations')+preparation_html(T)+language_html(T,C['lang'],C.get('languageName'))
chapter_pages['prepare']=section('prepare','按准备阶段逐项处理；清单和语言卡也可在旅行模式里打开。',body)
chapter_pages['tools']=section('tools','收藏、笔记、清单与'+C['currencyName']+'账目保存在当前浏览器，出发前后都可备份。','<div class="tool-links" id="travel-tools"><button data-tool="ledger"><span>01 / 账本</span><strong>记账与还款 ↗</strong><small>费用、分摊、成员结算</small></button><button data-tool="photos"><span>02 / 相册</span><strong>摄影参考 ↗</strong><small>按天保存想拍的构图</small></button><button data-tool="files"><span>03 / 资料夹</span><strong>票据与照片 ↗</strong><small>预订截图、PDF 与附件</small></button><button id="export-data"><span>04 / 本机记录</span><strong>导出备份 ↓</strong><small>保存文字与已添加的附件</small></button><label class="button">导入备份<input id="import-data" type="file" accept="application/json" hidden></label></div><label class="wish-label" id="journal-note">旅途笔记<textarea data-note="journal" rows="5" placeholder="喜欢的餐桌、想再来的街区、今天发生的事……"></textarea></label><p id="storage-status" class="small" role="status"></p>')
h.extend(chapter_pages[key] for key in chapter_order)
h.append('<section class="journal-finale"><div class="closing-photo">'+pic(C['closingPhoto'],C['closingWords'],'closing-plate')+'</div><div class="wrap closing-copy"><p class="kicker">UNTIL NEXT TIME / 写在旅程之后</p><p>'+C['closingCopy']+'</p><a href="#cover">回到封面 ↑</a></div></section>')

h.append('<section class="wrap source-notes" id="sources"><details><summary>资料与摄影来源</summary><div class="source-links">'+''.join(f'<a href="{E(u)}" target="_blank" rel="noopener">{E(T.get("source_labels",{}).get(k,k))} ↗</a>' for k,u in G['sources'].items())+'</div><p>照片署名与来源见各图图注。</p></details></section></main><footer class="wrap footer"><span>PRIVATE JOURNAL · '+en+'</span><a href="#cover">回到封面 ↑</a><span>'+span+'</span></footer>')

dialogs=(R/'dialogs.html').read_text(encoding='utf8');dialogs=re.sub(r'<dialog id="menu-dialog".*?</dialog>','<dialog id="menu-dialog" aria-labelledby="menu-title"><div class="dialog-head"><div><p>'+city+' / '+span+'</p><h2 id="menu-title">全书目录</h2></div><button data-close>关闭 ×</button></div><nav class="drawer-nav">'+nav()+'</nav><div class="menu-footer"><a href="#sources">资料与图片来源</a><button data-motion-toggle aria-pressed="false">动效：开启</button></div></dialog>',dialogs,flags=re.S)
dialogs=dialogs.replace('{{CITY}}',city).replace('{{LANGUAGE}}',C['languageName']).replace('{{CURRENCY}}',C['currencyName']).replace('8MB','20MB');h.append(dialogs)
h.append('<script id="guide-data" type="application/json">'+json.dumps(G,ensure_ascii=False).replace('</',r'<\/')+'</script>'+''.join(f'<script src="{f}"></script>' for f in ['map-layout.js','map-ui.js','schedule.js','ledger-model.js','member-avatars.js','ledger-demo.js','ledger-ui.js','travel-alternatives.js','travel-reference.js','app.js','reader-context.js','motion.js','vendor/gsap.min.js','art.js','impeccable-interior.js'])+'</body></html>');out='\n'.join(h);out=out.replace('<head>','<head><meta name="travel-build-id" content="'+build_id+'">')
(R/'index.html').write_text(out,encoding='utf8')
for f in cssfiles:
 css=(R/f).read_text(encoding='utf8') if (R/f).exists() else ''
 for p in (R/'fonts').glob('*.woff2'):css=css.replace('fonts/'+p.name,'data:font/woff2;base64,'+base64.b64encode(p.read_bytes()).decode())
 out=out.replace(f'<link rel="stylesheet" href="{f}">','<style>'+css+'</style>')
for f in ['map-layout.js','app.js','map-ui.js','schedule.js','ledger-model.js','member-avatars.js','ledger-demo.js','ledger-ui.js','travel-alternatives.js','reader-context.js','motion.js','vendor/gsap.min.js','art.js','impeccable-interior.js','travel-reference.js']:out=out.replace(f'<script src="{f}"></script>','<script>'+(R/f).read_text(encoding='utf8')+'</script>')
from offline_images import inline_images, write_size_report
out,image_report=inline_images(R,out,C,photos,photo_editorial,G['maps'])
import os
build_stage=os.environ.get('JOURNAL_BUILD_STAGE','preview')
artifact=R/(city+'-'+span+'旅行杂志4.0'+('-待验收预览' if build_stage!='release' else '')+'.html')
from font_audit import check_final_html
check_final_html(R,out,build_stage,build_id)
artifact.write_text(out,encoding='utf8');print('Built',build_stage,city,len(P),'places',N,'days',round(len(out.encode())/1024/1024,1),'MB')

write_size_report(R,artifact,image_report,build_id)
(R/'build-manifest.json').write_text(json.dumps({'buildId':build_id,'stage':build_stage,'slug':C['slug'],'city':city,'days':N,'artifact':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf8')
