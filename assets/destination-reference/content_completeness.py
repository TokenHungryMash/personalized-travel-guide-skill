"""Reject unfinished full-edition drafts. These floors do not certify editorial quality."""
import re


def audit_completeness(guide, edition, editorial):
    if edition.get('contentCompletenessVersion', 0) < 1:
        return []  # Existing editions remain readable; new workbenches enable this.
    errors=[]
    def body(rows):
        return '\n\n'.join(x for row in rows if isinstance(row,list) for x in row[1:] if isinstance(x,str))
    sections={k:editorial.get(k,[]) for k in ('portrait','stays','culture','shopping')}
    sections.update({'areas:'+a['id']:editorial.get('area_sections',{}).get(a['id'],[]) for a in guide.get('areas',[])})
    for key,rows in sections.items():
        text=body(rows)
        if not text.strip():
            errors.append(key+': missing authored body')
    copies={}
    for item in editorial.get('route_experiences',[]):
        copy=re.sub(r'\s+','',item.get('copy',''))
        if len(copy)>=24 and copy in copies:
            errors.append('route_experiences: identical prose for '+copies[copy]+' and '+item.get('areaId','?'))
        copies[copy]=item.get('areaId','?')
    complete=0
    for scene in editorial.get('languageScenes',[]):
        if not scene.get('phrases'):
            continue  # Standalone local names/signs remain useful.
        counts=[len((editorial.get('phrases',{}) if kind=='phrases' else editorial.get('words',{})).get(scene.get(kind),[])) for kind in ('phrases','glossary','replies')]
        if counts[0]<4 or counts[1]<8 or counts[2]<2:
            errors.append('languageScenes.'+scene['id']+': incomplete conversation/glossary/replies '+str(counts)+'; English-only removes duplicate translation, not content')
        else:complete+=1
    if complete<6:
        errors.append('languageScenes: full travel edition needs at least six complete practical scenes (dining, transport, lodging, shopping, visits and help); local context may add scenes')
    return errors
