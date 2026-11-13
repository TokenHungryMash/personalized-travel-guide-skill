from html import escape as E
PHRASES={
'点餐':[('一人です。','Hitori desu.','一位。'),('メニューを見せてください。','Menyuu o misete kudasai.','请给我看菜单。'),('おすすめは何ですか。','Osusume wa nan desu ka.','有什么推荐？'),('これはいくらですか。','Kore wa ikura desu ka.','这个多少钱？'),('お会計をお願いします。','Okaikei o onegai shimasu.','请结账。')],
'交通':[('太宰府駅に行きたいです。','Dazaifu eki ni ikitai desu.','我想去太宰府站。'),('乗り換えは必要ですか。','Norikae wa hitsuyou desu ka.','需要换乘吗？'),('国際線ターミナルはどこですか。','Kokusaisen taaminaru wa doko desu ka.','国际航站楼在哪里？'),('この電車は博多に行きますか。','Kono densha wa Hakata ni ikimasu ka.','这班车去博多吗？'),('エレベーターはどこですか。','Erebeetaa wa doko desu ka.','电梯在哪里？')],
'购物':[('カードは使えますか。','Kaado wa tsukaemasu ka.','可以刷卡吗？'),('袋をください。','Fukuro o kudasai.','请给我袋子。'),('試着してもいいですか。','Shichaku shite mo ii desu ka.','可以试穿吗？'),('別のサイズはありますか。','Betsu no saizu wa arimasu ka.','有其他尺码吗？'),('写真を撮ってもいいですか。','Shashin o totte mo ii desu ka.','可以拍照吗？')],
'住宿与预约':[('予約しています。','Yoyaku shite imasu.','我有预约。'),('荷物を預けてもいいですか。','Nimotsu o azukete mo ii desu ka.','可以寄存行李吗？'),('チェックインは何時ですか。','Chekku in wa nanji desu ka.','几点入住？'),('禁煙の部屋をお願いします。','Kinen no heya o onegai shimasu.','请安排禁烟房。'),('予約を確認したいです。','Yoyaku o kakunin shitai desu.','我想确认预约。')],
'求助与沟通':[('日本語があまり話せません。','Nihongo ga amari hanasemasen.','我不太会说日语。'),('中国語のメニューはありますか。','Chuugokugo no menyuu wa arimasu ka.','有中文菜单吗？'),('これに何が入っていますか。','Kore ni nani ga haitte imasu ka.','里面有什么食材？'),('助けてください。','Tasukete kudasai.','请帮帮我。'),('ホテルに連絡していただけますか。','Hoteru ni renraku shite itadakemasu ka.','可以帮我联系酒店吗？')]}
WORDS={
'菜单':['水炊き|mizutaki|鸡肉锅','もつ鍋|motsunabe|牛杂锅','替玉|kaedama|加面','定食|teishoku|套餐饭','単品|tanpin|单点'],
'车站':['入口|iriguchi|入口','出口|deguchi|出口','乗換|norikae|换乘','改札|kaisatsu|检票口','終電|shuuden|末班车'],
'购物':['税込|zeikomi|含税','現金|genkin|现金','試着|shichaku|试穿','要冷蔵|you reizou|需要冷藏','賞味期限|shoumi kigen|赏味期限'],
'场所':['神社|jinja|神社','美術館|bijutsukan|美术馆','博物館|hakubutsukan|博物馆','公園|kouen|公园','商店街|shoutengai|商店街'],
'现场标识':['本日休業|honjitsu kyuugyou|今天休息','準備中|junbichuu|尚未营业','予約|yoyaku|预约','禁煙|kinen|禁止吸烟','撮影禁止|satsuei kinshi|禁止拍摄']}
def language_content():
 h='<div class="language-grid">'
 for title,rows in PHRASES.items():
  h+='<details><summary>'+title+'<span>5句 ＋</span></summary>'+''.join(f'<button class="phrase" data-jp="{E(j)}" data-rom="{E(r)}" data-zh="{E(z)}"><strong lang="ja">{j}</strong><small>{r}</small><span>{z}</span></button>' for j,r,z in rows)+'</details>'
 h+='</div><h3 class="subheading">看懂菜单与路牌</h3><div class="language-grid">'
 for title,rows in WORDS.items():
  h+='<details><summary>'+title+'<span>5词 ＋</span></summary>'
  for row in rows:
   j,r,z=row.split('|');h+=f'<button class="phrase" data-jp="{j}" data-rom="{r}" data-zh="{z}"><strong lang="ja">{j}</strong><small>{r}</small><span>{z}</span></button>'
  h+='</details>'
 return h+'</div>'
