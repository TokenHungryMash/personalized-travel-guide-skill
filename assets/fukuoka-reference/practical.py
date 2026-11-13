from html import escape as E

def reservations():
 rows=[('flights','必须','航班与机场到场时间','确认航站楼、航空公司要求的到场时刻，再倒推取行李和出发时间。'),('hotel','必须','三晚住宿与行李寄存','填好酒店日文地址、入住日期、电话；返程前确认取行李的地点。'),('museum','建议','两座美术／博物馆的开放日','第二天市美术馆、第三天九州国立博物馆分别检查。雨备馆休息时，午餐也一起换。'),('dinner','建议','第二天水炊晚餐','日期和人数确定后再预约。把确认时刻记入当天备注，确认成功的凭证存到餐厅附件。'),('tower','随缘','福冈塔与海滨支线','先看天气和能见度，再决定是否用半天替换购物；不为了清空清单强行去。')]
 return '<section class="reservation-section" id="reservation-list"><p class="kicker">BOOK & CONFIRM</p><h3>预约与确认</h3><p>勾选表示已经处理，不代表系统替你完成预订。</p>'+''.join(f'<article class="reservation-row"><h4>{t}</h4><div><b>{p}</b><label><input type="checkbox" data-reservation="{k}"><span>待处理</span></label></div><p>{v}</p></article>' for k,p,t,v in rows)+'</section>'

from fieldnotes import local_notes

def souvenirs():
 return '''<section class="souvenir-edit"><p class="kicker">TAKE HOME</p><h3>伴手礼先选用途，再选包装</h3><div class="meal-pair"><article><h4>明月堂 · 博多通りもん</h4><p>白豆沙馅的软质点心，适合分送。购买前按人数选盒装数量，查看过敏原与最短保质期；不为盒子好看买过量。</p><p><a href="https://www.meigetsudo.co.jp/ic/torimon" target="_blank" rel="noopener">商品说明</a> · <a href="https://www.meigetsudo.co.jp/store-map" target="_blank" rel="noopener">官方门店</a></p></article><article><h4>梅枝饼 · 现吃与带走分开</h4><p>太宰府参道的红豆馅点心，先买一块现吃。若买冷冻装作礼物，须问清保存与运输要求，不按常温饼干处理。</p><p><a href="https://dazaifu.org/introduce/shop346/" target="_blank" rel="noopener">太宰府观光协会：かさの家</a></p></article></div></section>'''
