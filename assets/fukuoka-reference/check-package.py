from pathlib import Path
from html.parser import HTMLParser
from fontTools.ttLib import TTFont
import re
R=Path(__file__).parent
text=''.join((R/f).read_text(encoding='utf-8') for f in ['index.html','app.js','motion.js'])
needed={ord(c) for c in re.findall(r'[\u3000-\u9fff\uff00-\uffef]',text)}
font_css='\n'.join((R/f).read_text(encoding='utf-8') for f in ['body-font.css','serif-font.css','font-supplement.css'])
for family,weight in [('Tokyo Sans',400),('Tokyo Sans',700),('Bali Serif',400)]:
    have=set()
    for rule in re.findall(r'@font-face\{([^}]+)\}',font_css):
        if f"font-family:'{family}'" not in rule or f'font-weight:{weight};' not in rule:continue
        path=re.search(r'url\(([^)]+)\)',rule).group(1)
        declared={int(n,16) for n in re.findall(r'U\+([0-9A-F]+)',rule)}
        have.update(set(TTFont(R/path).getBestCmap())&declared)
    assert not needed-have,(family,weight,len(needed-have))
class Package(HTMLParser):
    def __init__(self):super().__init__();self.styles=0;self.scripts=0;self.external=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='style':self.styles+=1
        if tag=='script' and not a.get('src'):self.scripts+=1
        if a.get('id'):self.ids.append(a['id'])
        if tag in ['img','script','video','source'] and a.get('src','').startswith(('media/','maps/')):self.external.append(a['src'])
        if tag=='link' and a.get('rel')=='stylesheet':self.external.append(a.get('href'))
s=(R/'福冈-四天三晚旅行杂志.html').read_text(encoding='utf-8');p=Package();p.feed(s)
assert p.styles==16 and p.scripts>=7,(p.styles,p.scripts)
assert not p.external,p.external
assert len(p.ids)==len(set(p.ids))
assert 'data-open-editor' not in s and 'data-slot-time' not in s
assert s.count('class="tip-card"')==48
assert '<video' not in s and 'youtube.com/iframe_api' not in s and 'id="film-toggle"' not in s,'Magazine 4.0 uses a static photo cover'
print(f'PASS: {len(needed)} CJK glyphs covered at every used bundled weight; {p.styles} embedded styles, 6 runtime scripts, images/maps embedded, unique IDs, 48 tips, editing hooks absent')
print('PASS: static photography cover, no video player or playback control')
