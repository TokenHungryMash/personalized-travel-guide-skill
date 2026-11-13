"""Check research breadth and meal coverage, not prose quality or factual truth."""
import argparse
import json
from pathlib import Path

# Same destination bands as references/directory-standard.md. These are planning
# ranges, not ceilings; a larger researched library is allowed.
PLACE_RANGES = {
    'metropolis': [(30,45),(55,80),(75,110)],
    'city': [(20,30),(35,55),(50,70)],
    'island': [(15,25),(30,50),(45,65)],
    'small': [(12,20),(20,35),(30,45)],
}
DINING_RANGES = {
    'metropolis': [(6,10),(16,24),(24,36)],
    'city': [(4,8),(10,16),(16,24)],
    'island': [(4,8),(8,14),(14,20)],
    'small': [(3,6),(6,10),(10,16)],
}
NON_VISIT_ROLES = {'transport','lodging','placeholder','context'}
NON_VISIT_KINDS = {'交通','机场','车站','住宿','酒店','占位'}
MEAL_KINDS = {'美食','餐饮','餐厅','咖啡','甜品','饮品','小吃','面包店','餐食'}

def planned_ranges(plan, days):
    segments = plan.get('segments') if plan.get('cityType') == 'multi-city' else [{'cityType':plan.get('cityType'),'days':days}]
    if not isinstance(segments,list) or not segments:
        raise ValueError('multi-city requires researched segments with cityType and days')
    result = [0,0,0,0]
    for segment in segments:
        kind, duration = segment.get('cityType'), segment.get('days')
        if kind not in PLACE_RANGES or type(duration) is not int or not 1 <= duration <= 12:
            raise ValueError('cityType must be metropolis/city/island/small; split journeys longer than 12 days into segments')
        band = 0 if duration <= 3 else 1 if duration <= 7 else 2
        for i,value in enumerate((*PLACE_RANGES[kind][band],*DINING_RANGES[kind][band])):
            result[i] += value
    if sum(s['days'] for s in segments) != days:
        raise ValueError('segment days must sum to actual trip days')
    return result[:2],result[2:]

def effective_ids(content):
    result,seen = set(),set()
    for place in content.get('places',[]):
        if place.get('directoryRole') in NON_VISIT_ROLES or place.get('kind') in NON_VISIT_KINDS or place.get('availability')=='closed':
            continue
        identity = (place.get('query') or ((place.get('local') or place.get('name',''))+'|'+place.get('where',''))).strip().casefold()
        if not identity or identity in seen:
            continue
        seen.add(identity)
        result.add(place['id'])
    return result

def audit(content, editorial, plan):
    errors = []
    if not all(isinstance(value,dict) for value in (content,editorial,plan)):
        return {'errors':['content, editorial and directory-plan must be objects']}
    days = content.get('days',[])
    if plan.get('tripDays',len(days))!=len(days):errors.append('tripDays differs from the actual journey')
    places = {p['id']:p for p in content.get('places',[])}
    effective = effective_ids(content)
    try:
        place_range,dining_range = planned_ranges(plan,len(days))
    except (ValueError,KeyError,TypeError) as exc:
        errors.append('coverage planning: '+str(exc))
        place_range = dining_range = None
    override = plan.get('scopeOverride')
    if override:
        # Human review must verify the user scope or objective local limitation;
        # the author's time and image shortage are never a scope reduction.
        user_scope=isinstance(override,dict) and isinstance(override.get('userRequest'),str) and override['userRequest'].strip()
        availability=isinstance(override,dict) and override.get('basis')=='verified-availability' and isinstance(override.get('sources'),list) and override['sources'] and all(isinstance(s,str) and s.startswith(('https://','http://')) for s in override['sources'])
        if not isinstance(override,dict) or not (user_scope or availability) or not isinstance(override.get('reason'),str) or not override['reason'].strip():
            errors.append('scopeOverride requires actual userRequest or sourced verified-availability, plus reason')
        else:
            for field in ('targetRange','diningTargetRange'):
                r=override.get(field)
                minimum=0 if field=='diningTargetRange' else 1
                if not isinstance(r,list) or len(r)!=2 or any(type(n) is not int or n<minimum for n in r) or r[0]>r[1]:
                    errors.append('scopeOverride.'+field+': invalid [minimum, maximum]')
            if not errors:
                place_range,dining_range=override['targetRange'],override['diningTargetRange']
    if place_range:
        if plan.get('targetRange') != place_range:
            errors.append(f'targetRange must follow destination/trip scope: {place_range}, not actual inventory')
        if len(effective)<place_range[0]:
            errors.append(f'effective directory {len(effective)} < {place_range[0]}; transport, lodging anchors and duplicates do not count')
    items=[item for group in editorial.get('restaurant_groups',[]) for item in group.get('items',[])]
    for group in editorial.get('restaurant_groups',[]):
        for item in group.get('items',[]):
            if isinstance(item.get('why'),str) and item['why'].strip()==str(group.get('name','')).strip():
                errors.append(str(item.get('id'))+': restaurant reason repeats its category instead of explaining the choice')
    dining_ids={item.get('id') for item in items}
    if len(dining_ids)!=len(items):errors.append('restaurant_groups repeat the same venue in multiple recommendations')
    if dining_ids-effective:errors.append('restaurant candidates must be real eligible directory places: '+str(sorted(str(i) for i in dining_ids-effective)))
    for pid in dining_ids & effective:
        if places[pid].get('directoryRole')!='meal' and places[pid].get('kind') not in MEAL_KINDS:
            errors.append(str(pid)+': sightseeing/shops cannot count as restaurants; identify actual meal venues')
    if dining_range:
        if plan.get('diningTargetRange')!=dining_range:errors.append(f'diningTargetRange must follow destination/trip scope: {dining_range}')
        if len(dining_ids & effective)<dining_range[0]:errors.append(f'dining candidates {len(dining_ids & effective)} < {dining_range[0]}; research real alternatives, not duplicate cards')
    # Roles have to be considered, not mechanically populated with chains in a
    # destination that has none. A blank/missing role is still an unfinished plan.
    defaults={'值得专程吃','当地特色','日常连锁','咖啡与甜品'}
    group_names={g.get('name') for g in editorial.get('restaurant_groups',[]) if g.get('items')}
    adjustments=plan.get('diningCategoryNotes',{})
    for role in sorted(defaults-group_names) if not dining_range or dining_range[1]>0 else []:
        if not isinstance(adjustments.get(role),str) or not adjustments[role].strip():errors.append('missing dining role or researched adaptation: '+role)
    # This is an index of existing rendered candidates, not a second restaurant
    # database. Human review checks kitchen windows, geography and usable text.
    coverage=plan.get('mealCoverage',{})
    if not isinstance(coverage,dict):return {'errors':errors+['mealCoverage must be an object']}
    for index,day in enumerate(days):
        dayid=day['id'];entry=coverage.get(dayid,{})
        if not isinstance(entry,dict):errors.append(dayid+': mealCoverage entry must be an object');continue
        refs=set(day.get('dining',[]))
        if refs-dining_ids:errors.append(dayid+': dining contains non-recommended venue IDs')
        meals=entry.get('meals',{})
        if not isinstance(meals,dict):errors.append(dayid+': meals must be an object');continue
        unknown=set(meals)-{'breakfast','lunch','dinner','snack'}
        if unknown:errors.append(dayid+': unknown meal keys '+str(sorted(unknown)))
        required={'lunch','dinner'} if 0<index<len(days)-1 or entry.get('dayType')=='full' else set()
        whole_reason=isinstance(entry.get('reason'),str) and bool(entry['reason'].strip())
        exceptions=entry.get('notApplicable',{})
        if not isinstance(exceptions,dict):exceptions={}
        for meal in sorted(required-set(meals)):
            reason=exceptions.get(meal)
            if not whole_reason and (not isinstance(reason,str) or not reason.strip()):errors.append(dayid+': no '+meal+' coverage or actual notApplicable reason')
        explained=required and all(isinstance(exceptions.get(m),str) and exceptions[m].strip() for m in required)
        if not meals and not whole_reason and not explained:
            errors.append(dayid+': meal conditions are not planned')
        for meal,ids in meals.items():
            exception=entry.get('alternativeNotes',{}).get(meal,'')
            single_explained=isinstance(ids,list) and len(set(ids))==1 and isinstance(exception,str) and exception.strip()
            if not isinstance(ids,list) or (len(set(ids))<2 and not single_explained):
                errors.append(dayid+'/'+meal+': provide a real option and an alternative');continue
            if set(ids)-refs or set(ids)-dining_ids:
                errors.append(dayid+'/'+meal+': meal candidates must appear in this day dining and restaurant_groups')
    return {'errors':errors,'effectivePlaces':len(effective),'diningCandidates':len(dining_ids & effective),
            'placeRange':place_range,'diningRange':dining_range,
            'limit':'Coverage is not quality certification. Read actual prose, meal windows, venue suitability, sources and page visibility.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('workbench',type=Path)
    args=parser.parse_args()
    try:
        read=lambda name:json.loads((args.workbench/name).read_text(encoding='utf8'))
        report=audit(read('content.json'),read('editorial-content.json'),read('directory-plan.json'))
    except (OSError,ValueError,TypeError,KeyError) as exc:report={'errors':[str(exc)]}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return bool(report['errors'])

if __name__=='__main__':raise SystemExit(main())
