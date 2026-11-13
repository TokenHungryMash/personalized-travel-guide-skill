"""Verify traceable editorial review evidence, not semantic truth or usefulness."""
import argparse
import hashlib
import json
from pathlib import Path

FILES=('content.json','editorial-content.json','edition.json')
QUESTIONS={
 'portrait:identity':'这是什么样的城市或地区？地理格局如何影响它的城市面貌，而非本次交通路线？',
 'portrait:formation':'哪些历史或形成过程塑造了今天的地方？正文怎样解释它们与眼前建筑、街道或景观的关系？',
 'portrait:life':'今天的人怎样生活？当地文化、饮食、产业或社区差异有哪些具体表现，而非景点名单？',
 'stays':'不同住宿区的环境、日常配套和连接条件有什么区别？不同偏好如何选择，代价是什么？',
 'culture':'当地文化对象是什么、为何值得理解、到场具体看什么？参观条件和适用人群有哪些限制？',
 'shopping':'按当地实际品类和用途去哪里比较？如何判断品质、使用与携带条件，而非通用包装提醒？',
 'food_types':'当地食物的食材、做法、口味和吃法是什么？怎样根据人数与口味选择，并找到具体候选？',
 'notes':'本旅程最常遇到的交通和日常问题如何一步步处理？失败后的处理与适用条件在哪里？',
 'preparation':'出发前哪些任务实际适用、去哪里办理、做到什么才算完成？未知身份和日期怎样处理？',
 'languageScenes':'能在实际场景找到可出示的表达、词语和常见回答吗？当地语及备用英语是否正确分流？',
 'area':'这一真实区域有什么不同于其他区域的空间、文化与生活特征？现场有什么可观察的细节，而非某一天的路线摘要？',
 'travel':'仅用当天旅行模式，怎样理解每站、衔接交通和吃饭、处理营业限制与备选？购物或补给是否适用，如何操作？'}
DOMAINS=tuple(k for k in QUESTIONS if k not in ('area','travel'))

def question_for(domain):
    return QUESTIONS[domain if domain in QUESTIONS else domain.split(':')[0]]

def review_targets(data,domain):
    """Point the reviewer to existing text; never prefill an answer or ready status."""
    guide=data['content.json'];editorial=data['editorial-content.json'];targets=[]
    def add(file,path):
        try:
            if isinstance(pointer(data[file],path),str):targets.append({'file':file,'pointer':path})
        except (KeyError,IndexError,ValueError,TypeError):pass
    if domain.startswith('travel:'):
        index=next(i for i,d in enumerate(guide['days']) if d['id']==domain.split(':',1)[1]);day=guide['days'][index]
        stop_ids={s[1] for s in day.get('stops',[])}
        for i,place in enumerate(guide.get('places',[])):
            if place['id'] in stop_ids:add('content.json',f'/places/{i}/desc')
        for edge in day.get('transfers',{}):add('content.json',f'/days/{index}/transfers/'+edge.replace('~','~0').replace('/','~1')+'/label')
        for gi,group in enumerate(editorial.get('restaurant_groups',[])):
            for ri,item in enumerate(group['items']):
                if item['id'] in day.get('dining',[]):
                    for field in ('fit','note','order'):add('editorial-content.json',f'/restaurant_groups/{gi}/items/{ri}/{field}')
        for i in range(len(day.get('alternatives',[]))):
            for field in ('trigger','replace','traffic','check'):add('content.json',f'/days/{index}/alternatives/{i}/{field}')
        add('content.json',f'/days/{index}/guard')
    return targets

def pointer(document,path):
    if not isinstance(path,str) or not path.startswith('/'):
        raise ValueError('expected JSON pointer')
    for part in path[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        document=document[int(part)] if isinstance(document,list) else document[part]
    return document

def substantive_path(file,path):
    """Reject labels as evidence without trying to score prose by character count."""
    parts=path.strip('/').split('/')
    if file=='edition.json':return False
    if file=='editorial-content.json':
        head=parts[0]
        if head in ('portrait','stays','culture','shopping','food_types','snacks'):
            return len(parts)==3 and parts[-1].isdigit() and int(parts[-1])>0
        if head in ('area_sections','notes'):
            return len(parts)==4 and parts[-1].isdigit() and int(parts[-1])>0
        if head=='preparation':return len(parts)==5 and parts[-1]=='detail'
        if head in ('phrases','words'):return len(parts)==4 and parts[-1] in ('local','zh','english','roman','note')
        if head=='restaurant_groups':return len(parts)==5 and parts[-1] in ('why','order','fit','budget','note')
        return False
    if file=='content.json':
        if parts[0]=='places':return len(parts)==3 and parts[-1] in ('desc','walk','tip')
        if parts[0]=='days' and len(parts)>=3:
            field=parts[2]
            if field in ('lead','move','guard','budget'):return len(parts)==3
            if field in ('periods','shopping'):return len(parts)==4 and parts[-1].isdigit()
            if field=='stops':return len(parts)==5 and parts[-1]=='2'
            if field=='schedules':return len(parts)==6 and parts[-1]=='guard'
            if field=='transfers':return len(parts)==5 and parts[-1]=='label'
            if field=='alternatives':return len(parts)==5 and parts[-1] in ('trigger','replace','traffic','check')
            if field=='photoPlan':return len(parts)==5 and parts[-1] in ('light','composition','portrait','settings')
    return False

def audit(data,hashes,review,scope=None):
    errors=[]
    expected=set(DOMAINS)
    expected.update('area:'+a['id'] for a in data['content.json']['areas'])
    expected.update('travel:'+d['id'] for d in data['content.json']['days'])
    if scope:
        scope=[sub for domain in scope for sub in (['portrait:identity','portrait:formation','portrait:life'] if domain=='portrait' else [domain])]
        unknown=set(scope)-expected
        if unknown:errors.append('Unknown scope: '+str(sorted(unknown)))
        expected=set(scope)
    if review.get('inputHashes')!=hashes:
        errors.append('Review is absent or stale: inputHashes must match all three current content files')
    checks=review.get('checks',[])
    if not isinstance(checks,list):return errors+['checks must be an array']
    seen=set()
    for check in checks:
        if not isinstance(check,dict):
            errors.append('check must be an object');continue
        domain=check.get('domain')
        if domain not in expected:continue
        if domain in seen:errors.append(str(domain)+': duplicate review')
        seen.add(domain)
        for field in ('question','answer','pageLocation'):
            if not isinstance(check.get(field),str) or not check[field].strip():
                errors.append(str(domain)+': missing '+field)
        if check.get('question')!=question_for(domain):
            errors.append(str(domain)+': review question must use the fixed chapter contract; do not replace it with a question tailored to weak copy')
        if check.get('status')!='ready':errors.append(str(domain)+': unresolved review; state remaining work honestly')
        evidence=check.get('evidence',[])
        if not isinstance(evidence,list):
            errors.append(str(domain)+': evidence must be an array');continue
        if not evidence:errors.append(str(domain)+': missing actual content evidence')
        linked=False
        cited_places=set();cited_restaurants=set();cited_transfers=set();cited_alternative=False
        for item in evidence:
            try:
                file=item['file'];path=item['pointer'];quote=item['quote']
                value=pointer(data[file],path)
                if not isinstance(value,str) or not isinstance(quote,str) or not quote.strip() or quote not in value:
                    raise ValueError('quote is not present at the named string field')
                if not substantive_path(file,path):
                    raise ValueError('evidence must cite substantive body, not titles, IDs or labels')
                if quote.strip() not in [value.strip(),*[part.strip() for part in value.split('\n\n') if part.strip()]]:
                    raise ValueError('cite a complete paragraph or complete field, not a clipped substring')
                parts=path.strip('/').split('/')
                if file=='content.json' and parts[0]=='places' and parts[-1]=='desc':
                    cited_places.add(data[file]['places'][int(parts[1])]['id'])
                if file=='editorial-content.json' and parts[0]=='restaurant_groups':
                    cited_restaurants.add(data[file]['restaurant_groups'][int(parts[1])]['items'][int(parts[3])]['id'])
                if domain.startswith('travel:'):
                    dayid=domain.split(':',1)[1]
                    idx=next(i for i,d in enumerate(data['content.json']['days']) if d['id']==dayid)
                    linked |= file=='content.json' and path.startswith('/days/'+str(idx)+'/')
                    if file=='content.json' and path.startswith('/days/'+str(idx)+'/transfers/'):
                        cited_transfers.add(parts[3].replace('~1','/').replace('~0','~'))
                    cited_alternative |= file=='content.json' and path.startswith('/days/'+str(idx)+'/alternatives/')
                elif domain.startswith('area:'):
                    key=domain.split(':',1)[1].replace('~','~0').replace('/','~1')
                    linked |= file=='editorial-content.json' and path.startswith('/area_sections/'+key+'/')
                else:
                    prefix='/languageScenes/' if domain=='languageScenes' else '/'+domain.split(':')[0]+'/'
                    # Language evidence should include actual usable phrases/words, not scene labels.
                    linked |= file=='editorial-content.json' and (path.startswith(('/phrases/','/words/')) if domain=='languageScenes' else path.startswith(prefix))
            except (KeyError,ValueError,IndexError,TypeError,StopIteration) as exc:
                errors.append(str(domain)+': invalid evidence: '+str(exc))
        if not linked:errors.append(str(domain)+': evidence must belong to this section/day')
        if domain.startswith('travel:'):
            day=next(d for d in data['content.json']['days'] if d['id']==domain.split(':',1)[1])
            stops={s[1] for s in day.get('stops',[])}
            if stops-cited_places:errors.append(domain+': cite every actual stop introduction, not only move/budget or one stop')
            if set(day.get('transfers',{}))-cited_transfers:errors.append(domain+': cite each actual transfer description')
            if day.get('dining') and not set(day['dining']) & cited_restaurants:errors.append(domain+': cite actual restaurant details linked to this day')
            if day.get('alternatives') and not cited_alternative:errors.append(domain+': cite actual alternative conditions')
        if domain=='food_types' and data['editorial-content.json'].get('restaurant_groups') and not cited_restaurants:
            errors.append(domain+': food introduction also needs evidence from actual restaurant recommendations')
    errors.extend(domain+': missing review' for domain in sorted(expected-seen))
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('workbench',type=Path)
    p.add_argument('--scope',nargs='+',help='Existing revision only: affected domain keys; new editions must omit')
    p.add_argument('--init',action='store_true',help='Create a pending review worksheet; never overwrite an existing review')
    args=p.parse_args();root=args.workbench
    try:
        raw={f:(root/f).read_bytes() for f in FILES}
        data={f:json.loads(v) for f,v in raw.items()}
        hashes={f:hashlib.sha256(v).hexdigest() for f,v in raw.items()}
        if args.init:
            domains=list(DOMAINS)+['area:'+a['id'] for a in data['content.json']['areas']]+['travel:'+d['id'] for d in data['content.json']['days']]
            review={'inputHashes':hashes,'checks':[dict(domain=d,question=question_for(d),answer='',pageLocation='',status='pending',evidence=[],reviewTargets=review_targets(data,d)) for d in domains]}
            with (root/'editorial-review.json').open('x',encoding='utf8') as f:
                json.dump(review,f,ensure_ascii=False,indent=2)
            print('Created pending worksheet. This is not a completed review.');return 0
        review=json.loads((root/'editorial-review.json').read_text(encoding='utf8'))
        errors=audit(data,hashes,review,args.scope)
    except (OSError,ValueError,TypeError) as exc:errors=[str(exc)]
    print(json.dumps({'result':'fail' if errors else 'evidence-linked','errors':errors,
        'limit':'Human review still required: matching quotes do not prove useful answers, correct facts or rendered visibility.'},ensure_ascii=False,indent=2))
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
