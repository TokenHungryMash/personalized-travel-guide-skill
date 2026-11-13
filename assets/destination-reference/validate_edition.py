"""Validate reusable presentation and actionable alternatives before rendering."""
def validate(g,c,t,photos):
    from destination_content import audit_relationships
    relationship_errors = audit_relationships(g, c, t)
    if relationship_errors:
        raise ValueError('\n'.join(relationship_errors))
    if c.get('travelContentVersion', 0) >= 1:
        from travel_content import audit_content
        errors = audit_content(g)
        if errors:
            raise ValueError('\n'.join(errors))
    from content_completeness import audit_completeness
    completeness_errors = audit_completeness(g,c,t)
    if completeness_errors:
        raise ValueError('Incomplete edition:\n'+'\n'.join(completeness_errors))
    places={p['id'] for p in g['places']}
    assert len(places)==len(g['places']), 'Duplicate place IDs'
    for key in ['editorTitle','experienceLead','closingPhoto','closingWords','closingCopy','coverMood']:
        assert c.get(key), 'Missing edition configuration: '+key
    assert c['cover'] in photos and c['closingPhoto'] in photos, 'Cover/closing photo missing'
    assert c['coverMood']=='night' or c.get('coverMoodReason'), 'Explain a deliberate non-night cover choice'
    for index,(a,theme) in enumerate(zip(g['areas'],t['route_experiences'])):
        if a['photo'] not in photos:
            raise ValueError(f'areas[{index}] (id={a["id"]}).photo={a["photo"]!r}: missing photo record')
    for i,d in enumerate(g['days']):
        choices=d.get('alternatives',[])
        minimum=1 if i in [0,len(g['days'])-1] else 2
        assert len(choices)>=minimum, f'{d["id"]}: needs {minimum} useful alternatives'
        triggers=set()
        for a in choices:
            for field in ['trigger','title','replace','time','traffic','check']:
                assert isinstance(a.get(field),str) and a[field].strip(), f'{d["id"]}: missing alternative {field}'
            assert a['trigger'] not in triggers, f'{d["id"]}: repeated alternative trigger'
            triggers.add(a['trigger'])
            assert isinstance(a.get('route'),list) and all(id in places for id in a['route']), f'{d["id"]}: unknown alternative place'
            assert len(set(a['route']))==len(a['route']), f'{d["id"]}: duplicated alternative place'
