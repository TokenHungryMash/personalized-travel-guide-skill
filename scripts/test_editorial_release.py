import unittest
from audit_editorial_release import audit, question_for
from editorial_release import substantive_path,review_targets

class ReviewTests(unittest.TestCase):
    def fixture(self):
        data={'content.json':{'areas':[],'days':[{'id':'d1','guard':'入场前确认预约'}]},'editorial-content.json':{'portrait':[['城市','港口形成了市场生活']]},'edition.json':{}}
        review={'inputHashes':{'test':'hash'},'checks':[{'domain':'portrait:formation','question':question_for('portrait:formation'),'answer':'港口与市场相连','pageLocation':'认识城市','status':'ready','evidence':[{'file':'editorial-content.json','pointer':'/portrait/0/1','quote':'港口形成了市场生活'}]}]}
        return data,review
    def test_matching_evidence(self):
        d,r=self.fixture();self.assertEqual(audit(d,r['inputHashes'],r,['portrait:formation']),[])
    def test_stale_missing_and_invented_are_rejected(self):
        d,r=self.fixture();r['checks'][0]['evidence'][0]['quote']='虚构文字'
        e=audit(d,{},r,['portrait:formation','travel:d1'])
        self.assertTrue(any('stale' in x for x in e));self.assertTrue(any('invalid evidence' in x for x in e));self.assertTrue(any('missing review' in x for x in e))
    def test_wrong_domain_and_unresolved_rejected(self):
        d,r=self.fixture();r['checks'][0].update(domain='travel:d1',status='pending')
        e=audit(d,r['inputHashes'],r,['travel:d1'])
        self.assertTrue(any('belong' in x for x in e));self.assertTrue(any('unresolved' in x for x in e))

class FixedQuestionsTests(unittest.TestCase):
    def test_review_targets_include_each_stop_transfer_meal_and_alternative(self):
        data={'content.json':{'places':[{'id':'a','desc':'馆藏介绍'},{'id':'b','desc':'街区介绍'}],'days':[{'id':'d1','stops':[['10:00','a',''],['12:00','b','']],'transfers':{'a>b':{'label':'实际走法'}},'dining':['r'],'alternatives':[{'trigger':'闭馆','check':'查预约'}]}]},'editorial-content.json':{'restaurant_groups':[{'items':[{'id':'r','fit':'午餐','note':'店休条件','order':'菜式'}]}]}}
        targets=review_targets(data,'travel:d1');paths={item['pointer'] for item in targets}
        for path in ['/places/0/desc','/places/1/desc','/days/0/transfers/a>b/label','/restaurant_groups/0/items/0/fit','/days/0/alternatives/0/trigger']:
            self.assertIn(path,paths)
        self.assertTrue(all(set(item)=={'file','pointer'} for item in targets))
    def test_move_and_budget_cannot_certify_whole_travel_day(self):
        d,r=ReviewTests().fixture()
        d['content.json']['places']=[{'id':'museum','desc':'具体馆藏与来历'}]
        day=d['content.json']['days'][0]
        day.update(stops=[['10:00','museum','预约提示']],move='步行或候车',budget='整趟预算',transfers={'museum>meal':{'label':'沿街走到餐厅'}},dining=['meal'],alternatives=[{'trigger':'闭馆'}])
        r['checks'][0].update(domain='travel:d1',question=question_for('travel:d1'),evidence=[{'file':'content.json','pointer':'/days/0/move','quote':'步行或候车'},{'file':'content.json','pointer':'/days/0/budget','quote':'整趟预算'}])
        errors=audit(d,r['inputHashes'],r,['travel:d1'])
        for expected in ['stop introduction','transfer description','restaurant details','alternative conditions']:
            self.assertTrue(any(expected in error for error in errors))
    def test_actual_transfer_body_is_reviewable_but_minutes_are_not_prose(self):
        d,r=ReviewTests().fixture()
        d['content.json']['days'][0]['transfers']={'pier>market':{'label':'从码头穿过广场步行至市场入口','minutes':15}}
        r['checks'][0].update(domain='travel:d1',question=question_for('travel:d1'),evidence=[{'file':'content.json','pointer':'/days/0/transfers/pier>market/label','quote':'从码头穿过广场步行至市场入口'}])
        self.assertEqual(audit(d,r['inputHashes'],r,['travel:d1']),[])
        self.assertFalse(substantive_path('content.json','/days/0/transfers/pier>market/minutes'))
    def test_time_and_place_id_are_not_travel_prose(self):
        self.assertFalse(substantive_path('content.json','/days/0/stops/0/0'))
        self.assertFalse(substantive_path('content.json','/days/0/stops/0/1'))
        self.assertTrue(substantive_path('content.json','/days/0/stops/0/2'))
    def test_title_and_clipped_phrase_do_not_prove_an_answer(self):
        for path,quote in [('/portrait/0/0','城市'),('/portrait/0/1','港口')]:
            d,r=ReviewTests().fixture();r['checks'][0]['evidence'][0].update(pointer=path,quote=quote)
            self.assertTrue(any('invalid evidence' in e for e in audit(d,r['inputHashes'],r,['portrait:formation'])))
    def test_old_istanbul_orientation_question_cannot_certify_city_intro(self):
        d,r=ReviewTests().fixture()
        r['checks'][0]['question']='怎么认方向？'
        self.assertTrue(any('fixed chapter contract' in e for e in audit(d,r['inputHashes'],r,['portrait:formation'])))
    def test_full_portrait_scope_requires_identity_history_and_life(self):
        d,r=ReviewTests().fixture()
        errors=audit(d,r['inputHashes'],r,['portrait'])
        self.assertTrue(any('portrait:identity: missing review' in e for e in errors))
        self.assertTrue(any('portrait:life: missing review' in e for e in errors))
