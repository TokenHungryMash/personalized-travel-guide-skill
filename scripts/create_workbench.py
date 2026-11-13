"""Copy the approved reference without overwriting work or claiming city adaptation."""
from pathlib import Path
import argparse,json,re,shutil
from portable_files import workbench_ignore

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--project-id',required=True,help='Unique lowercase city-trip slug')
    parser.add_argument('--sample',action='store_true',help='Explicitly restore the Fukuoka reference')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',args.project_id):
        parser.error('--project-id must be a lowercase hyphenated slug')
    skill=Path(__file__).resolve().parents[1]
    target=args.destination.expanduser().resolve()
    if target.is_relative_to(skill) or skill.is_relative_to(target):
        parser.error('Choose a workbench outside the skill package')
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        parser.error('Target must be absent or empty; existing work is never overwritten')
    source=skill/('assets/fukuoka-reference' if args.sample else 'assets/destination-reference')
    shutil.copytree(source,target,dirs_exist_ok=True,ignore=workbench_ignore(source,sample=args.sample))
    if not args.sample:
        # This optional research ledger is specific to the reference restaurants.
        (target/'dining-image-sources.json').write_text('{}\n', encoding='utf-8')
        shutil.copy2(skill/'assets/authoring-examples.jsonc', target/'authoring-examples.jsonc')
        plan={'cityType':'待规划', 'targetRange':None, 'diningTargetRange':None, 'mealCoverage':{}, 'diningCategoryNotes':{}, 'imageCoverageTarget':0.8, 'photoExceptions':{}}
        (target/'directory-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        content=json.loads((target/'content.json').read_text(encoding='utf8'))
        content['$schema']='./content.schema.json'
        (target/'content.json').write_text(json.dumps(content, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        editorial=json.loads((target/'editorial-content.json').read_text(encoding='utf8'))
        for area, theme in zip(content['areas'], editorial['route_experiences']):
            theme['areaId']=area['id']
        (target/'editorial-content.json').write_text(json.dumps(editorial, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    # Keep browser data separate from both the approved book and other new journeys.
    storage_key='travel-magazine-v4-'+args.project_id
    for name in ['app.js','check-editorial.cjs']:
        path=target/name
        if not path.exists():continue
        text=path.read_text(encoding='utf-8').replace('fukuoka-private-journal-v4-20261106',storage_key).replace('travel-magazine-v4-bali-8d-v4-test',storage_key)
        path.write_text(text,encoding='utf-8')
    edition=target/'edition.json'
    if edition.exists():
        config=json.loads(edition.read_text(encoding='utf8'));config['slug']=args.project_id
        config['backupFormat']=args.project_id+'-backup';config['legacyMotionKeys']=[]
        if not args.sample:
            config['travelContentVersion']=1
            config['editorialEvidenceVersion']=1
            config['readerReferenceVersion']=2
            config['contentCompletenessVersion']=1
        edition.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf8')
    metadata={
        'skill':'build-personalized-travel-guide-open-source','version':'4.0.0',
        'project_id':args.project_id,'storage_key':storage_key,
        'reference_destination':'Fukuoka' if args.sample else 'Bali','cover':'static-photo' if args.sample else 'photo-overprint',
        'state':'reference-sample' if args.sample else 'reference-needs-authoring',
        'note':'Contains reference-destination facts. New cities require authoring, asset replacement, map/currency/language adaptation and fresh QA.'
    }
    if not args.sample:
        original=json.loads((source/'edition.json').read_text(encoding='utf8'))
        metadata['reference_identity']={key:original[key] for key in ('city','english','country','currency','languageName')}
    (target/'magazine-workbench.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Created:',target)
    print('State:',metadata['state'])
    print('Next: read references/template-workflow.md; author new-city content before claiming completion.' if not args.sample else 'Next: run python -X utf8 build.py inside the workbench, then inspect the output.')

if __name__=='__main__':main()
