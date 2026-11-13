"""Oversized photographic spreads; fixed guide content and tools stay intact."""

def issue_ribbon():
    return '''<div class="issue-ribbon wrap"><span>THE FUKUOKA EDIT</span><span>街头 / 海岸 / 餐桌</span><span>编辑于 2026.11</span></div>'''

def editor_spread(pic):
    return '''<section class="fashion-opening" id="reading-start" aria-labelledby="editors-title"><div class="art-scene art-nightfall"><header class="fashion-opening-title wrap"><p>福冈，从夜色里开始。</p><h2 id="editors-title"><span>AFTER</span> <span>HOURS.</span></h2><div><span>NAKASU, FUKUOKA</span><span>四天三晚 · 私人城市手册</span></div></header><div class="fashion-opening-photo">'''+pic('nightwalk')+'''</div></div><div class="fashion-opening-note wrap"><p class="editor-lead">市区住三晚，<br>留一天去太宰府。</p><div><p>这四天安排了博多寺社、天神购物、大濠公园和太宰府。参道上可以买梅枝饼，晚上再选一顿想吃的福冈料理。</p><p>先读城市与街区，出门后用「旅行模式」查当天地点。地址簿可以搜索、收藏和打开导航；账目和笔记保存在当前浏览器。</p><a href="#orientation">先认识福冈 ↗</a><p class="issue-assumptions">4 天 3 晚为样刊假设，含抵达与返程；旅行日期、航班、酒店与人数未定。预算与停留时间为编辑预留，资料照片不代表出行当季或实时状态。</p></div></div></section>'''


def city_photo(pic):
    return '''<div class="fashion-coast fashion-city"><div class="fashion-bleed art-scene art-seaside"><div class="art-seaside-type" aria-hidden="true"><span>BAY</span><span>CITY.</span></div>'''+pic('bay-city')+'''</div><div class="fashion-caption-row"><h3>BY THE<br>WATER.</h3><div><p>博多湾 · 福冈塔</p><p>海滨百道在市中心西侧。想看海，把这半天留给沙滩和福冈塔；想继续逛店，就留在天神。</p></div></div></div>'''

def night_interlude(pic):
    return '''<section class="fashion-night" aria-labelledby="night-title"><div class="wrap"><div class="night-section-note"><span>AFTER DARK</span><p>天神 / 晚饭以后</p><a href="#yatai-guide">屋台怎么吃 ↗</a></div><div class="art-scene art-afterdark"><header><p>FUKUOKA / YATAI</p><h2 id="night-title"><span>NIGHT</span> <span>SHIFT.</span></h2></header><div class="fashion-night-layout">'''+pic('tenjin-night')+'''</div></div><div class="art-night-copy"><p class="night-chinese">入夜以后，<br>街边多了一排餐桌。</p><p>屋台的位子不多。先看价目表，问问还有没有空位。排队太久或遇到休息，就去后面的餐厅候选。</p><a href="#meal-addresses">两处用餐候选 ↗</a></div></div></section>'''

def afterword(pic):
    return '''<section class="fashion-afterword" aria-labelledby="afterword-title"><div class="art-scene art-garden"><h2 id="afterword-title"><span>UNTIL</span><span>NEXT TIME.</span></h2><div class="fashion-afterword-photo">'''+pic('ohori-garden')+'''</div></div><div class="wrap fashion-afterword-copy"><p class="art-end-label">FUKUOKA<br>またね。 / 下次见</p><div><p class="afterword-chinese">哪家店，<br>下次还想来？</p><p>店名、吃了什么、从哪个站走过去——现在记一两句，回来以后才找得到。</p><a href="#journal-note">写进旅途笔记 ↗</a></div></div></section>'''
