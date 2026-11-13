import copy
import unittest
from audit_coverage import audit
from coverage_release import effective_ids,planned_ranges

class CoverageTests(unittest.TestCase):
    def fixture(self):
        places=[{'id':str(i),'name':'Place '+str(i),'kind':'美食' if i<16 else '文化','query':'Unique '+str(i)} for i in range(55)]
        days=[{'id':'d'+str(i),'dining':[str(j) for j in range(4)]} for i in range(6)]
        content={'places':places,'days':days}
        roles=['值得专程吃','当地特色','日常连锁','咖啡与甜品']
        editorial={'restaurant_groups':[{'name':role,'items':[{'id':str(k*4+i)} for i in range(4)]} for k,role in enumerate(roles)]}
        plan={'cityType':'metropolis','targetRange':[55,80],'diningTargetRange':[16,24],
              'mealCoverage':{d['id']:{'meals':{'lunch':['0','1'],'dinner':['2','3']}} for d in days}}
        return content,editorial,plan
    def test_complete_coverage_and_larger_library_are_allowed(self):
        c,e,p=self.fixture();self.assertEqual(audit(c,e,p)['errors'],[])
        c['places'] += [{'id':'extra'+str(i),'name':'Extra '+str(i)} for i in range(30)]
        self.assertEqual(audit(c,e,p)['errors'],[])
    def test_paris_style_shrunk_inventory_cannot_self_certify(self):
        c,e,p=self.fixture();c['places']=c['places'][:14]
        e['restaurant_groups']=[{'name':'当地特色','items':[{'id':'0'},{'id':'1'}]}]
        p['targetRange']=[14,24];p['scaleException']='Only had time for the main route'
        for d in c['days']:d['dining']=[]
        report=audit(c,e,p)
        self.assertTrue(any('targetRange' in x for x in report['errors']))
        self.assertTrue(any('effective directory' in x for x in report['errors']))
        self.assertTrue(any('dining candidates' in x for x in report['errors']))
        self.assertTrue(any('must appear in this day' in x for x in report['errors']))
    def test_transport_placeholders_and_duplicate_venues_do_not_count(self):
        c,e,p=self.fixture()
        c['places'][0]['kind']='交通';c['places'][1]['directoryRole']='placeholder'
        c['places'][2]['query']=c['places'][3]['query']
        self.assertEqual(len(effective_ids(c)),52)
        c['places'][4]['availability']='closed';c['places'][5]['directoryRole']='context'
        self.assertEqual(len(effective_ids(c)),50)
    def test_category_adaptation_does_not_waive_meals_or_inventory(self):
        c,e,p=self.fixture();e['restaurant_groups'][2]['name']='家庭小馆'
        self.assertTrue(any('日常连锁' in x for x in audit(c,e,p)['errors']))
        p['diningCategoryNotes']={'日常连锁':'目的地无适用连锁，保留经研究的家庭小馆作为日常选择'}
        self.assertEqual(audit(c,e,p)['errors'],[])
        p['mealCoverage']['d2']['meals'].pop('lunch')
        self.assertTrue(any('no lunch' in x for x in audit(c,e,p)['errors']))
    def test_user_scope_override_is_explicit_not_scale_excuse(self):
        c,e,p=self.fixture();c['places']=c['places'][:20]
        p['targetRange']=[20,30];p['scopeOverride']={'userRequest':'只制作这20处指定地点的专题','reason':'用户明确收窄','targetRange':[20,30],'diningTargetRange':[16,24]}
        self.assertEqual(audit(c,e,p)['errors'],[])
        del p['scopeOverride']['userRequest']
        self.assertTrue(audit(c,e,p)['errors'])
    def test_multi_city_accumulates_real_segments(self):
        self.assertEqual(planned_ranges({'cityType':'multi-city','segments':[{'cityType':'city','days':3},{'cityType':'small','days':3}]},6),([32,50],[7,14]))
    def test_meal_option_requires_alternative_in_actual_day(self):
        c,e,p=self.fixture();p['mealCoverage']['d2']['meals']['lunch']=['0']
        self.assertTrue(any('real option and an alternative' in x for x in audit(c,e,p)['errors']))
        p['mealCoverage']['d2']['alternativeNotes']={'lunch':'实际只有这间开放；若关闭则使用已准备的便携午餐，资料见研究记录'}
        self.assertEqual(audit(c,e,p)['errors'],[])
    def test_full_board_reason_or_per_meal_reasons_do_not_require_duplicate_explanation(self):
        c,e,p=self.fixture()
        for entry in [{'reason':'当天船票已含午晚餐，见船公司行程'}, {'notApplicable':{'lunch':'已含船餐','dinner':'已含船餐'}}]:
            p['mealCoverage']['d2']=entry
            self.assertEqual(audit(c,e,p)['errors'],[])
    def test_meal_typo_and_sight_as_restaurant_are_rejected(self):
        c,e,p=self.fixture();p['mealCoverage']['d0']['meals']={'lunh':['0','1']}
        c['places'][0]['kind']='文化'
        errors=audit(c,e,p)['errors']
        self.assertTrue(any('unknown meal keys' in x for x in errors))
        self.assertTrue(any('cannot count as restaurants' in x for x in errors))
    def test_category_name_is_not_a_restaurant_reason(self):
        c,e,p=self.fixture();e['restaurant_groups'][0]['items'][0]['why']='值得专程吃'
        self.assertTrue(any('reason repeats its category' in x for x in audit(c,e,p)['errors']))
    def test_verified_remote_scope_can_have_no_external_restaurants(self):
        c,e,p=self.fixture();e['restaurant_groups']=[]
        p['scopeOverride']={'basis':'verified-availability','sources':['https://example.org/operator/boarding'],'reason':'全程船上包餐，无外部餐厅停靠','targetRange':[55,80],'diningTargetRange':[0,0]}
        p['diningTargetRange']=[0,0]
        for day in c['days']:
            day['dining']=[];p['mealCoverage'][day['id']]={'reason':'船上包餐'}
        self.assertEqual(audit(c,e,p)['errors'],[])

if __name__=='__main__':unittest.main()
