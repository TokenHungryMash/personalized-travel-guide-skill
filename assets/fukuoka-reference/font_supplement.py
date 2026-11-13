"""Add only missing CJK glyphs; preserve existing font assets and keep the book offline."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fontTools.ttLib import TTFont
import urllib.request,urllib.parse,re,io
R=Path(__file__).parent
text=''.join((R/f).read_text(encoding='utf-8') for f in ['index.html','app.js','motion.js'])
needed={ord(c) for c in re.findall(r'[\u3000-\u9fff\uff00-\uffef]',text)}
jobs=[]
for css_name,family,google,weights in [('body-font.css','Tokyo Sans','Noto Sans SC',[400,700]),('serif-font.css','Bali Serif','Noto Serif SC',[400])]:
    have=set()
    for path in re.findall(r'url\(([^)]+)\)',(R/css_name).read_text(encoding='utf-8')):
        have.update(TTFont(R/path).getBestCmap())
    chars=''.join(chr(n) for n in sorted(needed-have))
    for weight in weights:
        for i in range(0,len(chars),350):jobs.append((family,google,weight,i//350,chars[i:i+350]))
def fetch(job):
    family,google,weight,index,chars=job
    name=('body' if family=='Tokyo Sans' else 'serif')+f'-extra-{weight}-{index}.woff2'
    target=R/'fonts'/name
    if not target.exists() or not set(map(ord,chars)).issubset(TTFont(target).getBestCmap()):
        url='https://fonts.googleapis.com/css2?family='+google.replace(' ','+')+':wght@'+str(weight)+'&display=swap&text='+urllib.parse.quote(chars)
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        css=urllib.request.urlopen(request,timeout=30).read().decode()
        asset=re.search(r'url\(([^)]+)\)',css).group(1)
        font=TTFont(io.BytesIO(urllib.request.urlopen(asset,timeout=30).read()));font.flavor='woff2';font.save(target)
        target.with_suffix('.source.txt').write_text(url+'\n'+asset,encoding='utf-8')
    missing=set(map(ord,chars))-set(TTFont(target).getBestCmap())
    assert not missing,missing
    ranges=','.join('U+'+format(ord(c),'X') for c in chars)
    return f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};font-display:swap;src:url(fonts/{name}) format('woff2');unicode-range:{ranges};}}"
with ThreadPoolExecutor(max_workers=3) as pool:rules=list(pool.map(fetch,jobs))
(R/'font-supplement.css').write_text('\n'.join(rules)+'\n',encoding='utf-8')
print('PASS: missing CJK glyphs supplied in',len(jobs),'font subsets')
