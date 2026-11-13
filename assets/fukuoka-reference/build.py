from pathlib import Path
import json,html,re,base64,hashlib
from PIL import Image
from language import language_content
from practical import reservations, local_notes, souvenirs
from editorial import district, food_extra, city_portrait
from magazine import issue_ribbon, editor_spread, city_photo, afterword, night_interlude
R=Path(__file__).parent;G=json.loads((R/'content.json').read_text(encoding='utf-8'));P={p['id']:p for p in G['places']};E=html.escape
G['coordinates']=json.loads((R/'verified-coordinates.json').read_text(encoding='utf-8'))
photos=json.loads((R/'place-photos.json').read_text(encoding='utf-8'));G['placePhotos']=photos;G['images']={k:v['src'] for k,v in photos.items()};G['imageCaptions']={k:v['caption'] for k,v in photos.items()}
if (R/'maps.json').exists():G['maps']=json.loads((R/'maps.json').read_text(encoding='utf-8'))
chapters=[('orientation','GET YOUR BEARINGS','目的地介绍与行程总览'),('neighbourhoods','CITY LIFE','街区指南'),('itinerary','FOUR DAYS','每日详细行程'),('food','AT THE TABLE','美食与餐厅'),('shopping','GOOD FINDS','购物与伴手礼'),('culture','ART & CULTURE','景点与文化参观'),('directory','ADDRESS BOOK','地点搜索与收藏'),('fieldnotes','FIELD NOTES','交通与实用贴士'),('prepare','BEFORE YOU GO','行前清单与日语卡'),('tools','ON THE ROAD','记账、摄影参考与备份')]
chapter_notes={
'orientation':'先读福冈的地理、历史与饮食文化，再看四天路线总图。',
'neighbourhoods':'六个街区的半日走法、吃饭休息与可展开的文化阅读。',
'itinerary':'按时间查地点和交通，再看当天的天气备选提示。',
'food':'查具体用餐候选、屋台入座步骤、菜式与点餐用语。',
'shopping':'衣服、食品和工艺品去哪买，记录购物清单。',
'culture':'挑选寺社、博物馆、公园和海滨等参观地点。',
'directory':'按街区搜索，查地址、看详情、收藏地点。',
'fieldnotes':'查机场接驳、乘车、支付、天气和求助提醒。',
'prepare':'勾选出发前的准备事项，放大日语句子给对方看。',
'tools':'记录开销与还款，按天保存摄影参考，管理附件与备份。'}
toc_titles=['认识福冈','街区散步','四天行程','美食与餐厅','购物与伴手礼','文化与景点','地点库','交通与实用贴士','行前准备与日语','随身工具']
toc_descriptions=['城市故事 · 地理 · 路线总图','六个街区 · 连着走的安排','具体时间 · 交通 · 用餐','餐厅候选 · 屋台 · 点餐','去哪买 · 愿望单 · 保存方式','寺社 · 美术馆 · 公园与海岸','按街区查找 · 收藏 · 导航','8 个主题 · 48 条出行提示','预约清单 · 打包 · 沟通用语','记账 · 摄影参考 · 票据备份']
def toc_link(i,id,zh):
 return f'<a href="#{id}" class="toc-entry"><span class="toc-number">{i:02d}</span><span class="toc-copy"><strong>{toc_titles[i-1]}</strong><small>{toc_descriptions[i-1]}</small></span><span class="toc-arrow" aria-hidden="true">↗</span></a>'

chapter_indices={
 1:[('about-fukuoka','城市介绍'),('journey-overview','四天总图'),('stay-guide','住在哪一带')],
 2:[('area-hakata','博多'),('area-nakasu','中洲'),('area-tenjin','天神'),('area-ohori','大濠'),('area-momochi','海滨'),('area-dazaifu','太宰府')],
 3:[('day-tabs','选择日期'),('week-overview-fold','四天全览')],
 4:[('meal-addresses','两处用餐候选'),('yatai-guide','屋台入座'),('food-lexicon','点餐词典')],
 5:[('shopping-picks','去哪买'),('shopping-list','购物愿望单')],
 6:[('culture-places','寺社与展馆'),('coast-places','公园与海岸')],
 7:[('place-search','搜索与筛选'),('place-results','地点列表')],
 8:[('local-tips','按主题查找'),('contact-card','离线联络卡')],
 9:[('booking-list','预订事项'),('packing-list','行前清单'),('language-cards','日语卡')],
 10:[('travel-tools','随身工具'),('journal-note','旅途笔记')]}
def head(i,deck):
 id,en,zh=chapters[i-1];family='认识城市' if i in [1,2,4,5,6] else '安排四天' if i==3 else '随身查找'
 index=''.join(f'<a href="#{target}">{label}</a>' for target,label in chapter_indices[i])
 return f'<header class="section-head"><p class="folio"><span>{family} / {i:02d}</span><span>FUKUOKA · CITY EDITION</span></p><h2><span class="section-display" lang="en">{en}</span><span class="section-chinese">{zh}</span></h2><p class="section-summary">{deck}</p><nav class="chapter-index" aria-label="{zh}的内容">{index}</nav></header>'
def pic(k,plate=None):
 f=photos.get(k)
 if not f:return ''
 w,h=Image.open(R/f['src']).size
 photo=f'<img width="{w}" height="{h}" src="{f["src"]}" alt="{E(f["caption"])}" loading="lazy" data-zoom>'
 if plate:
  titles={'oldtown':('OLD','TOWN.'),'river':('RIVER','LIGHTS.'),'underground':('UNDER','GROUND.'),'streets':('SIDE','STREETS.'),'lake':('LAKE','SIDE.'),'coast':('SEA','SIDE.'),'dazaifu':('A DAY','OUT.'),'shopping':('CITY','FINDS.'),'culture':('SHRINE','VISIT.'),'ramen':('HAKATA','RAMEN.')}
  lines=''.join('<span>'+t+'</span>' for t in titles[plate])
  photo=f'<div class="photo-composition art-scene plate-{plate}">{photo}<div class="photo-type" aria-hidden="true">{lines}</div></div>'
 return f'<figure class="photo-{k}">{photo}<figcaption>{E(f["caption"])} · <a href="{E(f["page"])}" target="_blank" rel="noopener">来源 ↗</a></figcaption></figure>'
def refs(ids):return '<div class="shortlist">'+''.join(f'<button class="place-open" data-place="{id}"><span>{P[id]["kind"]}</span><strong>{P[id]["name"]}</strong><small>{P[id]["duration"]}</small><b>↗</b></button>' for id in ids)+'</div>'
def table(rows):return '<div class="editorial-table">'+''.join('<article><h4>'+a+'</h4><div><p>'+b+'</p></div></article>' for a,b in rows)+'</div>'
def section(i,deck,body):return f'<section id="{chapters[i-1][0]}" class="wrap chapter">'+head(i,deck)+body+'</section>'
def grouped_toc():
 return ''.join('<div class="toc-column">'+''.join(toc_link(i,chapters[i-1][0],chapters[i-1][2]) for i in nums)+'</div>' for nums in [range(1,6),range(6,11)])
nav=grouped_toc()
drawer_groups=[('先读城市',[1,2]),('安排这四天',[3,4,5,6]),('出门随身查',[7,8,9,10])]
drawer_nav=''.join('<section class="menu-group"><h3>'+title+'</h3>'+''.join(toc_link(i,chapters[i-1][0],chapters[i-1][2]) for i in nums)+'</section>' for title,nums in drawer_groups)
cover=photos.get('nakasu',photos.get('ohori',next(iter(photos.values()))))
h=['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>福冈 · 四天三晚 · 旅行杂志 4.0</title>'+''.join(f'<link rel="stylesheet" href="{f}">' for f in ['style.css','film-layout.css','body-font.css','serif-font.css','bali.css','map-ui.css','fukuoka.css','enhancements.css','editorial-layout.css','reader-components.css','tokens.css','magazine.css','fashion.css','art.css','ui-polish.css','font-supplement.css'])+'</head><body class="magazine-edition fashion-edition art-edition"><a class="skip" href="#main">跳到正文</a><header class="topbar"><div class="masthead-inner"><button id="menu-open" aria-label="打开全书目录" aria-controls="menu-dialog" aria-expanded="false"><svg class="nav-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h9"/></svg><span>目录</span><small>10 章</small></button><a class="masthead" href="#cover"><span>PRIVATE JOURNAL</span><small>福冈 · 四天三晚</small></a><button id="pocket-open"><span>旅行模式</span><svg class="nav-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 15 15 5M5 5h10v10"/></svg></button></div></header><main id="main">']
h.append('<section class="cover" id="cover"><div class="film-cover"><img id="cover-film" class="cover-still" src="'+cover['src']+'" alt="福冈中洲夜景"><div class="film-shade"></div><div class="film-content wrap"><div class="film-edition"><span>私人城市杂志 / 福冈特刊</span><span>JAPAN · 04 DAYS / 03 NIGHTS</span></div><div class="film-title"><p>博多 · 天神 · 太宰府</p><h1>FUKUOKA<span>福冈</span></h1></div><div class="film-bottom"><p>四天三晚，不自驾。<br>博多、天神和太宰府，安排在这四天里。</p><div class="film-actions"><a href="#reading-start">开始阅读 ↓</a></div></div></div></div><div class="film-caption wrap"><span>福冈 · 中洲的夜晚</span><a href="'+E(cover['page'])+'" target="_blank" rel="noopener">封面摄影来源 ↗</a></div></section>')
h.append(issue_ribbon()+editor_spread(pic))
h.append('<section class="journal-contents wrap" aria-labelledby="contents-title"><div class="contents-intro"><p class="kicker">CONTENTS / 目次</p><h2 id="contents-title"><span>IN THIS</span> <span>ISSUE.</span></h2><p>认识一座城，<br>再把四天过好。</p><div class="contents-stats"><span><b>04</b>天</span><span><b>10</b>章</span><span><b>20</b>个地点</span></div></div><nav class="contents-grid" aria-label="全书章节">'+grouped_toc()+'</nav></section>')

h.append(section(1,'先认识这座海港城市，再看四天的路线。福冈与博多的来历、街区与餐桌，都从这里读起。',city_photo(pic)+city_portrait()+'<div id="journey-overview"></div><div class="orientation-grid overview-stay" id="stay-guide"><aside class="aside-note"><p class="kicker">WHERE TO STAY</p><h3>博多或天神，<br>连续住三晚。</h3><p>博多更适合以车站、机场往返和补给为重点；天神更方便购物、晚餐与西铁太宰府日游。最后按真实酒店位置决定。</p>'+table([('博多站附近','先核对博多口或筑紫口、出入口电梯与最后一段步行。不要只看地图直线距离。'),('天神／渡边通','喜欢晚餐和购物可优先比较。酒店到地铁与西铁站的距离分别核对。'),('机场最后一段','国际航站楼与国内航站楼不同；地铁到达后是否需要接驳，会改变返程出发时间。')])+'</aside></div><details class="wide-detail"><summary>航班、酒店与交通记录<span>＋</span></summary><div class="reading-columns"><label>去程与返程<textarea data-note="flights" placeholder="日期 / 航班 / 航站楼 / 航司要求的到场时间"></textarea></label><label>三晚住处<textarea data-note="hotel" placeholder="日文名称 / 地址 / 电话 / 最近出口 / 行李寄存"></textarea></label><article><h4>地铁与西铁分开看</h4><p>福冈市内用地铁与步行衔接；太宰府按西铁列车安排。先按实际路线计单程，再决定是否买通票。</p></article><article><h4>不预设机场只要几分钟</h4><p>国内航站楼接地铁，国际到达须另外计算接驳、等候与步行。铁路乘车时间只是全过程的一段。</p></article></div></details>'))
body=''
for i,a in enumerate(G['areas'],1):body+=district(a,i,pic,refs)
h.append(section(2,'先看博多、天神、大濠和太宰府怎么逛。想去海滨，可以用它替换半天购物。',body))
h.append(night_interlude(pic))
h.append(section(3,'四天各有一张时间表。到达、停留、交通接着读，地图和当天提示就在旁边。','<div id="day-tabs" class="day-tabs" aria-label="选择旅行日"></div><div id="day-view"></div><details class="wide-detail" id="week-overview-fold"><summary>四天全览与取舍<span>＋</span></summary><div id="week-overview"></div><p>第二天的海滨替换天神购物；第三天的太宰府按博物馆开馆日安排；最后一天的市场与采购都可取消。</p></details>'))
food=[('豚骨拉面 / とんこつ','先选汤底与面条硬度，再决定加面。「替玉」通常只加面，不加一整碗汤。博多站餐饮区和天神都可就近找，不必为一碗面跨城。'),('水炊 / 水炊き','适合想坐下来慢慢吃的一顿鸡肉锅。先问套餐、人数、预约与取消规则，不把它安排在赶车前。'),('牛杂锅 / もつ鍋','看清内脏、汤底与份量；不吃内脏就换成水炊或普通定食。点之前问问同行的人能不能接受内脏。'),('明太子 / 明太子','试小份即可；购买时确认冷藏、保质期与带回国限制。不要把展示柜的常温陈列误认为长途携带条件。'),('芝麻鲭鱼 / ごまさば','菜单可能出现生食鱼类。对生食有顾虑就选熟食，过敏或饮食限制直接向店方说明。'),('乌冬与定食','连续吃浓汤拉面之后，换一顿简单乌冬或有蔬菜的定食。按当天街区找店即可。'),('梅枝饼 / 梅ヶ枝餅','太宰府参道的小份点心。现吃与伴手礼分开买；留意外皮烫、馅料与保质期。'),('屋台 / 屋台','入座前确认标价、最低点单与付款方式；少量点单，吃完让位。大风雨或临时休息都可能影响出摊。')]
h.append(section(4,'每天挑一顿想吃的，其他餐就近安排。下面整理了常见菜式和点餐用语。','<div class="food-feature">'+pic('ramen',plate='ramen')+'<div><p class="kicker">EATING IN FUKUOKA</p><h3>拉面、锅物，<br>还有河边的屋台。</h3><p>屋台的座位挨得近，能感受到街边吃饭的气氛。不想排队时，可以改去博多或天神的室内餐厅，不必每顿都追着榜单跑。</p><p>先看沿第二天路线挑出的两处用餐候选，再读屋台入座步骤与菜式词典。订位前确定日期、人数和饮食限制。</p></div></div>'+food_extra()+'<details class="reference-fold" id="food-lexicon"><summary><span>菜式与点餐词典</span><small>8 种常见菜式 ＋</small></summary>'+table(food)+'</details>'+'<h3 class="subheading">按所在区域找一顿饭</h3>'+refs(['hakata','nakasu','canal','yanagibashi','dazaifustation'])+'<div class="four-notes">'+''.join(f'<article><span>{i:02d}</span><h4>{a}</h4><p>{b}</p></article>' for i,(a,b) in enumerate([('午餐','编辑预留约 ¥1,000–2,000；吃什么与份量会改变花费。'),('普通晚饭','编辑预留约 ¥2,000–4,000；锅物、酒水与套餐另计。'),('排队上限','出门前自己定一个等待上限，肚子饿时及时启用备选。'),('菜单与过敏','把不能吃的食材写给店员看；不凭照片猜汤底。')],1))+'</div>'))
shopping=[('食品与伴手礼','博多站、机场和百货食品层适合集中比较。先分清常温／冷藏、自用／送礼，再看最短保质期。'),('衣服与鞋','把试穿留给天神与大名的一段完整下午。先记尺码、型号和退换条件，再比较价格。'),('工艺与日用品','在川端或旧城看看博多织、博多人形等工艺线索。确认产地、材质、重量与包装，不仅看“福冈限定”。'),('角色与动漫购物','可把博多站或天神购物的一段留给角色用品；先核对品牌官网门店、楼层与当前营业，限定商品是否有货，需要向店方确认。'),('免税与离境','日本免税流程可能随购买日期变化。本版不按未知日期计算税后价格；购物时向店方确认办理方式、所需证件与机场流程。')]
h.append(section(5,'购物跟着所在街区走。把真正想买的物品写下来，返程时就少一次折返。','<div class="shopping-feature" id="shopping-picks">'+pic('canal',plate='shopping')+'<div><p class="kicker">FOOD / FABRIC / EVERYDAY OBJECTS</p><h3>天神买衣服，<br>博多站挑伴手礼。</h3><p>福冈的购物可以很集中：天神看衣服，博多站补食品，太宰府买一份参道点心。买之前看看行李还装不装得下。</p></div></div>'+table(shopping)+souvenirs()+refs(['tenjin','daimyo','kawabata','hakata','canal'])+'<label class="wish-label" id="shopping-list">我的购物愿望单<textarea data-note="wishlist" rows="4" placeholder="物品 / 用途 / 预算 / 所在街区 / 冷藏与行李要求"></textarea></label>'))
h.append(section(6,'寺社、城迹、美术与海岸都保留。用替换安排保持四天的舒适度。','<div class="culture-split">'+pic('dazaifu',plate='culture')+'<div><p class="kicker">OLD STREETS, NEW CONNECTIONS</p><h3>旧城里的寺社，<br>太宰府的博物馆。</h3><p>博多的寺社可以穿插在旧城散步里，太宰府的博物馆则需要留出一段看展时间。先选感兴趣的主题，不必逛完所有展厅。</p><p>天满宫参拜区、展馆开馆与临时活动，以真实出发日公告为准。</p></div></div><h3 class="subheading" id="culture-places">旧城与展馆</h3>'+refs(['kushida','tochoji','machiya','artmuseum','dazaifu','kyuhaku'])+'<h3 class="subheading" id="coast-places">公园与海岸候选</h3>'+refs(['ohori','castle','tower','momochi'])))
h.append(section(7,'按街区、日文名称或类别查找。打开地点看地址与实用信息，收藏留待出门时查。','<div class="address-intro"><p><b>20</b><span>个地点<br>一份随身地址簿</span></p><div><span>FIND YOUR NEXT STOP</span><p>按街区翻，也按兴趣找。<br>走到附近时，再打开地址与导航。</p></div></div><div class="directory-search"><label><span>搜索地点</span><input id="place-search" type="search" placeholder="地名、日文名称或想做的事"></label><label><span>类别</span><select id="kind-filter"><option value="">全部类别</option>'+''.join(f'<option>{k}</option>' for k in dict.fromkeys(p['kind'] for p in G['places']))+'</select></label><button id="saved-filter" aria-pressed="false">只看收藏</button></div><div class="directory-layout"><aside class="directory-sidebar"><p class="kicker">按所在街区找</p><nav id="directory-areas" aria-label="地点库街区"></nav><p class="directory-help">先选所在街区，再按类别缩小范围。卡片下方可直接导航，完整地址与现场提示放在详情里。</p></aside><div class="directory-main"><div class="directory-status"><p id="result-count" tabindex="-1" role="status" aria-live="polite"></p><button data-directory-reset hidden>清除筛选 ×</button></div><div id="place-results" class="directory-results"></div><nav id="directory-pages" class="directory-pages" aria-label="地点库分页"></nav></div></div>'))
notes={'交通与路线':[('国际到达多算一段','地铁连国内航站楼，国际航站楼出发先确认接驳或直达巴士；不要直接套用地铁乘车时间。'),('太宰府看西铁','西铁福冈（天神）与地铁天神需步行衔接；是否在西铁二日市换乘，看当班列车。'),('地铁站名看完整','博多、天神、天神南与西铁福冈不是同一入口。转乘先跟标识，不凭中文简称判断。'),('行李先有去处','酒店寄存与车站柜子都是备选；别带大箱子穿过太宰府参道。')],'吃饭与支付':[('屋台看天气','出门前准备室内备选。坐下先看价格与规则，小团体更容易安排。'),('现金留备用','小店和摊位的付款方式各异；交通 IC、银行卡与少量日元分开放。'),('过敏先说明','面汤、酱汁与锅物可能含多种成分，直接给店员看限制。'),('收好小票','记账录入实际支付的日元总额，购物与日常餐饮分开记。')],'天气与现场':[('雨天换一段','大濠与海滨可换美术馆、地下街和商场；馆舍也需确认开馆。'),('湖边与海边有风','按实际天气备外套；台风等严重天气时按交通与场所公告调整。'),('参拜与拍照','参拜通道不停留拍长时间合影；室内展品拍摄看标识。'),('城市保持安静','商店内拍人先询问，住宅小街与公共交通压低声音。')],'联络与应急':[('先留当前地址','酒店日文名称、电话和司机／同行联系离线保存。'),('找就近帮助','突发状况先告诉酒店、车站或场所工作人员准确位置；紧急时联系当地急救与警方。'),('证件分开放','护照原件、复印件与备份照片避免放在同一个袋中。'),('返程留冗余','接驳、排队与安检不是铁路乘车时间的一部分；按航空公司要求倒推。')]}
body=''
for title,rows in {}.items():body+='<details class="note-fold"><summary><h3>'+title+'</h3><span>4 条 / ＋</span></summary>'+table(rows)+'</details>'
body='<div id="local-tips">'+local_notes()+'</div>'
h.append(section(8,'从落地到返程，按正在遇到的事情查。48 条提示，补上每一步具体该怎么做。',body+'<label class="wish-label" id="contact-card">离线联络卡<textarea data-note="contacts" rows="4" placeholder="酒店日文地址 / 电话 / 保险援助 / 同行与家人"></textarea></label>'))
checks={'随身与打包':['护照与有效旅行证件','签证或免签资格按本人情况核对','航班、航站楼与接驳方式','酒店日文地址和电话','手机网络与漫游设置','插头、充电器与充电宝航司要求','舒适步行鞋与轻便外套','折伞和个人常用药','少量日元与备用支付方式','购物袋与行李箱余量','下载交通与地点信息','把重要记录导出备份'],'日期与预订':['三晚住宿与入住日期一致','检查日本节假日及大型活动','调整太宰府日以匹配展馆开馆','确认天满宫参拜动线公告','重点晚餐确认人数与取消规则','雨备馆舍确认开放','确认西铁太宰府当日往返','核对需要买的交通票','确认返程酒店寄存与取件','按航司要求倒推到场时间','国际航站楼另留接驳余地','冷藏伴手礼确认携带要求']}
body='<div id="booking-list">'+reservations()+'</div>'+'<div class="check-summary" id="packing-list"><p id="check-count" aria-live="polite"></p><button id="checks-clear">清空勾选</button></div><div class="check-columns">';i=0
for title,items in checks.items():
 body+='<div><h3>'+title+'</h3>'
 for t in items:body+=f'<label class="check-row"><input type="checkbox" data-check="c{i}"><span>{t}</span></label>';i+=1
 body+='</div>'
body+='</div><div class="language-head" id="language-cards"><p class="kicker">POINT & SPEAK</p><h3>把这句话，给对方看。</h3><p>点开日语可放大显示；中文说明保留。</p></div><div class="language-grid">'
body=body.removesuffix('<div class="language-grid">')+language_content()
h.append(section(9,'日期确定后，再锁定航班、展览与重点晚餐。清单和日语卡可离线使用。',body))
h.append(section(10,'收藏、笔记、清单与日元账目保存在当前浏览器，支持导出备份。','<div class="tool-links" id="travel-tools"><button data-tool="ledger"><span>01 / 账本</span><strong>记账与还款 ↗</strong><small>费用、分摊、成员结算</small></button><button data-tool="photos"><span>02 / 相册</span><strong>摄影参考 ↗</strong><small>按天保存想拍的构图</small></button><button data-tool="files"><span>03 / 资料夹</span><strong>票据与照片 ↗</strong><small>预订截图、PDF 与附件</small></button><button id="export-data"><span>04 / 本机记录</span><strong>导出备份 ↓</strong><small>保存文字与已添加的附件</small></button><label class="button">导入备份<input id="import-data" type="file" accept="application/json" hidden></label></div><label class="wish-label" id="journal-note">旅途笔记<textarea data-note="journal" rows="5" placeholder="喜欢的餐桌、想再来的街区、今天临时改了什么……"></textarea></label><p id="storage-status" class="small" role="status"></p>'))
h.append(afterword(pic))
h.append('<section class="wrap colophon" id="sources"><h2>关于这一本福冈</h2><div><p>4 天 3 晚、不自驾的设计与内容样刊。日期、酒店、航班与饮食限制待定；停留时间、车程与预算为编辑预留，并非预约或实时报价。</p><p>封面为福冈中洲夜景摄影。地点资料照片不代表当前季节、装修或实时参拜动线。</p><p>地图来自 OpenFreeMap / OpenMapTiles / OpenStreetMap，连线表示四天建议访问顺序，不是实际导航道路。</p><details><summary>资料、图片与字体来源</summary><p>'+ ' · '.join(f'<a href="{u}" target="_blank" rel="noopener">{k} ↗</a>' for k,u in G['sources'].items())+'</p><p>地点图片及原始页面见图注与 place-photos.json；Wikimedia 图片作者和许可见原图页面。新增摄影 © Fukuoka Prefecture Tourism Association；均从官方摄影图库下载，来源见图注。字体为 Outfit、Noto Sans SC、Noto Serif SC。</p></details></div></section></main><footer class="wrap footer"><span>PRIVATE JOURNAL · FUKUOKA</span><a href="#cover">回到封面 ↑</a><span>博多 / 天神 / 太宰府</span></footer>')
dialogs=(R/'dialogs.html').read_text(encoding='utf-8');dialogs=re.sub(r'<dialog id="menu-dialog".*?</dialog>', '<dialog id="menu-dialog" aria-labelledby="menu-title"><div class="dialog-head"><div><p>福冈 / 四天三晚</p><h2 id="menu-title">全书目录</h2></div><button data-close aria-label="关闭目录">关闭 ×</button></div><nav class="drawer-nav" aria-label="全书目录章节">'+drawer_nav+'</nav><div class="menu-footer"><a href="#sources">资料与图片来源</a><button data-motion-toggle aria-pressed="false">动效：开启</button></div></dialog>',dialogs,flags=re.S).replace('东京','福冈').replace('浅草午餐','博多午餐').replace('8MB','20MB');h.append(dialogs)
h.append('<script id="guide-data" type="application/json">'+json.dumps(G,ensure_ascii=False).replace('</',r'<\/')+'</script><script src="map-ui.js"></script><script src="schedule.js"></script><script src="ledger-model.js"></script><script src="app.js"></script><script src="motion.js"></script><script src="art.js"></script></body></html>');out='\n'.join(h)
preview=re.sub(r'(href|src)="([^"?]+\.(?:css|js))"',lambda m:m[1]+'="'+m[2]+'?v='+hashlib.sha256((R/m[2]).read_bytes()).hexdigest()[:10]+'"',out);(R/'index.html').write_text(preview,encoding='utf-8')
for f in ['style.css','film-layout.css','body-font.css','serif-font.css','bali.css','map-ui.css','fukuoka.css','enhancements.css','editorial-layout.css','reader-components.css','tokens.css','magazine.css','fashion.css','art.css','ui-polish.css','font-supplement.css']:
 css=(R/f).read_text(encoding='utf-8') if (R/f).exists() else ''
 for p in (R/'fonts').glob('*.woff2'):css=css.replace('fonts/'+p.name,'data:font/woff2;base64,'+base64.b64encode(p.read_bytes()).decode())
 out=out.replace(f'<link rel="stylesheet" href="{f}">','<style>'+css+'</style>')
for f in ['app.js','map-ui.js','schedule.js','ledger-model.js','motion.js','art.js']:out=out.replace(f'<script src="{f}"></script>','<script>'+(R/f).read_text(encoding='utf-8')+'</script>')
for folder in ['media','maps']:
 for p in (R/folder).glob('*'):
  if p.suffix in ('.jpg','.webp') and folder+'/'+p.name in out:out=out.replace(folder+'/'+p.name,'data:image/'+('jpeg' if p.suffix=='.jpg' else 'webp')+';base64,'+base64.b64encode(p.read_bytes()).decode())
(R/'福冈-四天三晚旅行杂志.html').write_text(out,encoding='utf-8');print('Built',len(G['places']),'places',len(G['days']),'days',len(out),'bytes')
