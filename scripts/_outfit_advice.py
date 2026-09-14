"""One outfit contract for research, profile validation and static rendering."""
from html import escape


def outfit_errors(photo, base):
    advice = photo.get('outfit_advice') if isinstance(photo, dict) else None
    if not isinstance(advice, dict):
        return [{'pointer':base+'/outfit_advice', 'code':'outfit_advice',
                 'message':'expected {women, men, practical_note}: two outfit suggestions and route/weather adjustments'}]
    return [{'pointer':base+'/outfit_advice/'+key, 'code':'outfit_advice',
             'message':'expected non-empty outfit text; see research-data-shapes.md'}
            for key in ('women','men','practical_note') if not isinstance(advice.get(key), str) or not advice[key].strip()]


def outfit_html(photo):
    advice = photo.get('outfit_advice', {})
    if not isinstance(advice, dict):
        return ''
    rows = ''.join('<div><strong>'+label+'</strong><p>'+escape(advice[key])+'</p></div>'
                   for key,label in (('women','女生穿搭'),('men','男生穿搭'),('practical_note','当天调整'))
                   if isinstance(advice.get(key),str) and advice[key].strip())
    return '<div class="photo-note-grid outfit-advice">'+rows+'</div>' if rows else ''
