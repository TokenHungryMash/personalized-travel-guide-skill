"""Editorial spreads shared by the preview and self-contained edition."""
from html import escape as E

def source(url, label):
    return f'<a href="{url}" target="_blank" rel="noopener">{label} ↗</a>'

KUSHIDA='https://www.gofukuoka.jp/spots/detail/26906'
DAZAIFU='https://www.dazaifutenmangu.or.jp/en/plan/recommended-itineraries/full-day/'
MUSEUM='https://www.fukuoka-art-museum.jp/en/guide/restaurant/'
HANAMIDORI='https://www.hanamidori.net/stores/0927385583/'
YATAI='https://www.crossroadfukuoka.jp/en/articles/yatai'

# Time ranges below are editorial allocations, not measured navigation times.
GUIDES={
'hakata':dict(time='2–3 小时',start='祇园一带开始，川端结束',day=0,
 route=[('先看寺院','东长寺留一站，之后步行往栉田神社。抵达较晚就从神社开始，不为了凑齐地点赶路。'),('再走老街','参拜后沿川端通慢走，看看日用品与工艺店。对民俗感兴趣，再加博多町家民俗馆。')],
 rest='逛完后接运河城餐饮区，或回博多站吃饭。行李先寄存，旧城散步结束后再取。',
 cut='只剩一小时：栉田神社＋川端通。雨势大：缩短寺社停留，保留有顶棚的商店街。',
 title='从一座神社看博多的祭典',
 story='栉田神社是博多祇园山笠祭的中心。知道这一点再看神社，参拜和城市节庆就有了联系。院中的银杏也是可以停下来观察的细节。普通旅行日可以从现场展示了解祭典，不应期待每天都能看到祭典队伍。',url=KUSHIDA,label='福冈市官方：栉田神社'),
'nakasu':dict(time='晚饭前后 1–2 小时',start='运河城至那珂川水岸',day=0,
 route=[('先沿河走','先看看河岸和摊位菜单，再决定在哪一处停下。把散步和吃饭分开考虑，屋台没开也不影响看夜景。'),('再决定入座','不必为了吃屋台换到远处街区。眼前的摊位菜式合适、价格清楚、有座位，比追一张名单更重要。')],
 rest='进屋台前先找洗手间。背包收好，尽量不带购物大袋和行李箱。',
 cut='下雨或不想等位：结束河边散步，回运河城餐饮区选室内晚饭。该备选是区域，并非已选定餐厅。',
 title='屋台不是只有拉面',
 story='屋台也会卖烤串、关东煮和煎饺等菜式，菜单因摊而异。选择前先想好是吃一顿正餐，还是吃过晚饭后再尝一点。座位紧凑，用餐结束后不久坐，给下一组客人留出位置。',url=YATAI,label='福冈县官方：屋台与用餐礼仪'),
'tenjin':dict(time='半天，约 3–4 小时',start='天神地下街 → 大名 → 今泉',day=1,
 route=[('先买确定要买的','地下街和百货先完成尺码、型号明确的采购。想买衣服，就给试穿留时间，不把整段下午排满店名。'),('再留一段随意逛','走到大名后再看街边服饰店。第二天晚餐候选在今泉，接近订位时间就停止向外走。')],
 rest='晚餐候选为博多華味鳥天神店。地址和订位入口见美食章；白天需要休息时就近选择有座位的店。',
 cut='雨天把购物集中在地下街与相连商场；少走路时取消大名，保留晚餐。',
 title='这半天先决定买什么',
 story='天神与大名在本行程中承担不同任务：前者先完成集中购物，后者留给街头小店。把“必买”和“看看再说”分开，就知道什么时候可以离开。当前没有为大名选定具体独立店；如果目标是古着或设计品牌，还需按偏好补店。',url=HANAMIDORI,label='晚餐候选：天神店官方资料'),
'ohori':dict(time='含午餐约 3–4 小时',start='大濠公园 → 市美术馆',day=1,
 route=[('湖边走一段','早晨先散步，按体力决定走多远。接下来还要看展，不必把环湖一周当任务。'),('看展后就地午餐','到美术馆先挑感兴趣的展览；看完可在馆内吃午饭，再往天神走。')],
 rest='馆内 1F 咖啡馆适合小食与饮料，2F 餐厅适合坐下来吃午餐。两处均随美术馆休馆，不能当周一的固定备选。',
 cut='不想看展：用城迹替换美术馆。下雨：缩短公园散步；遇休馆日则直接改天神。',
 title='午饭留在公园旁边',
 story='这一段最容易出现的折返，是看完展专门跨城吃午饭，又回来继续散步。把午餐留在馆内，就能连续完成公园、看展和休息，再集中去天神。这里推荐的是衔接方便，并不把馆内餐厅当成必须专程前往的美食目的地。',url=MUSEUM,label='美术馆官方：咖啡馆与餐厅'),
'momochi':dict(time='预留半天，含往返',start='福冈塔周边 → 海滨百道',day=1,
 route=[('先决定是否登塔','看天气与能见度，再决定登塔或只在地面逛。选了登塔，就缩短海边散步。'),('海边留一段空白','走到海边后可以坐坐，不必再追加市区景点。回程交通单独查看，不能把地图直线当作步行路线。')],
 rest='先吃过午饭再来，带水。这里暂未选定餐厅，不把海边随时有座位当作安排前提。',
 cut='替换第二天下午的购物，不叠加到原路线后。大风雨时放弃海边，回到原定天神安排。',
 title='海边的代价是半天购物',
 story='四天里并非一定要同时完成海岸、寺社、看展和购物。这条支线适合想看看海的人；如果购物是此行重点，就保留天神，不必为了凑齐福冈地标再横穿城市。日落也只是可选体验，不是必须赶上的时刻。',url='https://www.fukuokatower.co.jp/',label='福冈塔官方：出发前查开放安排'),
'dazaifu':dict(time='一日往返',start='西铁太宰府站 → 参道 → 天满宫',day=2,
 route=[('上午留给参道与参拜','从车站沿参道走向天满宫。点心和参拜都留些时间，不把整段只当成通往景点的路。'),('下午再选看展','午餐后去九州国立博物馆，或继续在参道附近慢走。博物馆休馆时直接采用后者。')],
 rest='梅枝饼是点心，不能代替午饭。午餐安排在参道附近，本版尚未确定餐厅；带孩子或有饮食限制时需提前选店。',
 cut='少走路就取消博物馆，参道与天满宫后回天神。不要在同一天再加另一个远郊。',
 title='留意梅花纹样，再尝一块梅枝饼',
 story='菅原道真与梅花的联系贯穿天满宫。参拜时可以留意梅花纹样，再在参道尝红豆馅的梅枝饼。下午若进九州国立博物馆，可沿着日本与亚洲交流这条线索看展；这样参道、神社和博物馆之间便有了内容上的联系。',url=DAZAIFU,label='天满宫官方：一日参观线索')}

def district(a,i,pic,refs):
    g=GUIDES[a['id']]
    styles={'hakata':'opening','nakasu':'river','tenjin':'pair','ohori':'panorama','momochi':'coast','dazaifu':'closing'}
    layout=styles[a['id']]
    photo_key={'momochi':'momochi','dazaifu':'dazaifu-street'}.get(a['id'],a['photo'])
    plate={'hakata':'oldtown','nakasu':'river','tenjin':'underground','ohori':'lake','momochi':'coast','dazaifu':'dazaifu'}[a['id']]
    companion='<div class="district-companion">'+pic('daimyo',plate='streets')+'</div>' if a['id']=='tenjin' else ''
    quick=f'<div class="district-quick"><span class="district-duration"><small>建议停留</small><strong>{g["time"]}</strong></span><span class="district-start"><small>从这里开始</small>{g["start"]}</span><button data-overview-detail="{g["day"]}">第 {g["day"]+1} 天详细行程 ↗</button></div>'
    rhythm='<dl class="dayout-rhythm"><div><dt>上午</dt><dd>走参道，参拜天满宫</dd></div><div><dt>下午</dt><dd>九州国立博物馆看展</dd></div><div><dt>晚上</dt><dd>回天神，吃一顿晚饭</dd></div></dl>' if a['id']=='dazaifu' else ''
    deck='<span>沿参道去天满宫，</span><span>下午看展</span>' if a['id']=='dazaifu' else a['deck']
    steps=''.join(f'<li><strong>{E(t)}</strong><p>{E(p)}</p></li>' for t,p in g['route'])
    return f'''<article class="district district-guide spread-{layout}" id="area-{a['id']}">
    <div class="district-title"><span>{i:02d}</span><h3>{a['name']}</h3><p>{a['en']}</p></div>
    {quick}<div class="district-spread">{pic(photo_key,plate=plate)}{companion}<div class="district-lead"><p class="kicker">这一带怎么逛</p><h4>{deck}</h4><p>{a['body']}</p>{rhythm}<p class="district-route">{a['route']}</p></div></div>
    <details class="district-practical"><summary><strong>走法、吃饭与休息</strong><span>实用速查 ＋</span></summary><div class="district-field"><div><p class="kicker">一段连着走的安排</p><ol class="walk-sequence">{steps}</ol></div><aside><h4>吃饭与休息</h4><p>{g['rest']}</p><h4>时间少了怎么改</h4><p>{g['cut']}</p></aside></div></details>
    <details class="editorial-read"><summary>再读一点：{g['title']}<span>展开阅读 ＋</span></summary><div><p>{g['story']}</p><p class="source-note">{source(g['url'],g['label'])} · 资料查阅 2026.11.10；路线时长为编辑预留。</p></div></details>
    {refs(a['ids'])}</article>'''

def food_extra():
    return f'''<div class="meal-addresses" id="meal-addresses"><header><p class="kicker">TWO PLACES TO SIT DOWN</p><h3>先把两顿饭落到实处</h3><p>沿第二天的路线选：一处解决看展后的午饭，一处安排购物后的晚餐。</p></header>
    <div class="meal-pair"><article><p class="meal-index">01 / 大濠 · 午餐</p><h4>美术馆 2F 餐厅</h4><p>看展后直接吃午餐，不再为找店往返。只想喝杯咖啡或吃点小食，可去 1F 咖啡馆。</p><dl><dt>在哪里</dt><dd>大濠公园 1-6，福冈市美术馆内。</dd><dt>怎么选</dt><dd>正餐选 2F，短休息选 1F；价格按当日菜单。</dd><dt>先确认</dt><dd>餐厅与咖啡馆随馆休息。当天不开馆时，改在天神用餐。</dd></dl><p class="source-note">{source(MUSEUM,'楼层、菜单与营业安排')}</p><button data-place="artmuseum">美术馆详情 ↗</button></article>
    <article><p class="meal-index">02 / 今泉 · 晚餐</p><h4>博多華味鳥 天神店</h4><p>想吃一顿鸡肉水炊时选这里。放在天神与大名购物之后，晚餐不必另换街区。</p><dl><dt>在哪里</dt><dd>今泉 1-20-2，天神 MENT B1；西铁福冈（天神）站步行约 3 分钟。</dd><dt>菜单参考</dt><dd>官网「味」套餐含税 ¥4,500。酒水及其他加点另计，订位时复核。</dd><dt>先确认</dt><dd>人数、套餐与饮食限制；晚餐候选尚未预订。</dd></dl><p class="source-note">{source(HANAMIDORI,'门店菜单、电话与预约')} · 核对 2026.11.10</p><button data-place="hanamidori">晚餐详情 ↗</button></article></div></div>
    <article class="yatai-guide" id="yatai-guide"><div><p class="kicker">AT THE COUNTER</p><h3>第一次坐进屋台</h3><p>把它安排成可以替换的一顿饭。天气、座位和当天菜单，都比打卡名单更影响体验。</p><p class="source-note">礼仪参考：{source(YATAI,'福冈县官方屋台指南')}</p></div><ol class="counter-steps"><li><strong>出发前</strong><p>先去洗手间，收好大件行李。留一个室内晚餐备选。</p></li><li><strong>坐下前</strong><p>看菜单、价格和付款方式，问清座位再入座。不要靠猜图片点一整桌。</p></li><li><strong>点餐时</strong><p>按菜单选自己能接受的菜。先少量点，不清楚份量就问店员，再决定加什么。</p></li><li><strong>吃完后</strong><p>结账后给等位的人留座，不把有限席位当长时间聊天休息的地方。</p></li></ol></article>'''

def city_portrait():
    return f'''<article class="city-portrait" id="about-fukuoka">
    <header><p class="kicker">INTRODUCING FUKUOKA / 认识福冈</p><h3>一座城，<br>福冈与博多两个名字。</h3><p class="city-standfirst">福冈在日本九州北部，面向博多湾。铁路车站叫博多，机场和城市叫福冈；两种名字，也留下了这座城市不同的来路。</p></header>
    <div class="city-portrait-body"><section><h4>先把它放回地图上</h4><p>福冈是九州的重要交通门户。从这里可以继续乘铁路前往九州其他地区，也可以只住在城里，把时间留给寺社、商店街、餐桌和海边。博多湾向外连接玄界滩，隔海面向朝鲜半岛与中国大陆。理解福冈，可以先从这片海开始：它很早就是人员、货物与文化往来的入口。</p><p class="source-note">{source('https://www.japan.travel/en/destinations/kyushu/fukuoka/','JNTO：福冈与九州')} · {source('https://bunkazai.city.fukuoka.lg.jp/fukuoka-histories/detail/1','福冈市文化财：城市历史')}</p></section>
    <section><h4>为什么又叫福冈，又叫博多？</h4><p>博多的名字更早，历史上是靠港口贸易发展起来的商人之町。黑田长政在它西侧营建城堡与城下町，命名为福冈。那珂川两侧，逐渐形成了商人之町博多与城下町福冈并存的格局。今天两者同属福冈市，博多这个名字仍留在车站、街区、工艺与食物里。</p><p>这段历史并不只在博物馆里。旧城的寺社和祭典，可以放在博多的商人文化中理解；向西到舞鹤公园看城迹，则接上了城下町的另一段历史。过河时知道两岸的来历，地图上的地名就更容易记住。</p><p class="source-note">{source('https://bunkazai.city.fukuoka.lg.jp/fukuoka-histories/detail/1','福冈市文化财：博多与福冈')} · {source('https://www.welcome-fukuoka.or.jp/travelinfo/fukuoka_h_info/','福冈观光会议局：那珂川两岸')}</p></section>
    <section><h4>餐桌也是认识城市的入口</h4><p>豚骨拉面只是其中一餐。水炊是鸡肉锅，牛杂锅适合能接受内脏的人；乌冬、鱼料理和小份点心，也可以穿插在几天里。没必要每顿都吃得浓重，更不必把所有名物挤在抵达当天。</p><p>到了晚上，屋台把吃饭带到街边。它们不是统一的美食广场：每摊菜单不同，座位紧挨着，能否入座要看当天情况。喜欢这种近距离用餐，可以留一晚试试；想坐得宽松、慢慢吃，就选室内餐厅。这是两种不同的晚餐体验。</p><p class="source-note">{source('https://www.japan.travel/en/destinations/kyushu/fukuoka/','JNTO：福冈饮食')} · {source(YATAI,'福冈县官方：屋台文化')} · 菜式与点餐另见美食章。</p></section>
    <section><h4>初次来，先认识这几片地方</h4><p><strong>博多与旧城</strong>把车站商业、寺社和老商店街放在相邻的街区里；<strong>中洲</strong>适合沿河看夜景，再决定在哪里吃晚饭。往西到<strong>天神与大名</strong>，内容转为百货、地下街和服饰小店。继续向西，<strong>大濠与舞鹤</strong>是湖边散步、看展和城迹；<strong>百道</strong>则让城市朝向海岸。</p><p><strong>太宰府是福冈县内另一座城市</strong>，不属于福冈市中心的街区。这本手册把它安排成往返一日：参道、天满宫与九州国立博物馆连着看。四天三晚能看到的是福冈市与一次近郊出游，并不是把整个福冈县走完。</p></section></div>
    <aside class="city-reader-note"><strong>这一本怎么读</strong><p>想先认识城市，接着读六个街区；想先判断四天是否适合自己，就往下看路线总览。街区里的文化短文可以慢读，地址、用餐与交通留到安排当天再查。</p><a href="#journey-overview">看四天路线 ↓</a><a href="#neighbourhoods">读街区指南 ↗</a></aside>
    </article>'''

def city_lenses():
    return '''<div class="city-lenses"><article><span>01 / 看城市</span><h4>寺社与商店街放在一起读</h4><p>博多旧城的参观串进街巷，不必一处寺社结束就坐车离开。川端通接在参拜后，能让这半天从景点回到日常生活。</p><a href="#area-hakata">读博多街区指南 ↗</a></article><article><span>02 / 留时间</span><h4>正餐也占一段行程</h4><p>水炊晚餐留出完整时段，屋台则允许临时替换。吃饭的位置确定下来，购物和散步才不容易越走越远。</p><a href="#meal-addresses">看具体用餐候选 ↗</a></article><article><span>03 / 去郊外</span><h4>太宰府单独留一天</h4><p>把参道、天满宫和博物馆连起来。不赶着再去另一座城，才能同时容下参拜、点心和看展。</p><a href="#area-dazaifu">读太宰府指南 ↗</a></article></div>'''
