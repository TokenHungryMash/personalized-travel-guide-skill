"""Content exceptions relax volume, never broken references or incomplete shapes."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets/destination-reference'))
from travel_content import audit_content


class TravelContentContract(unittest.TestCase):
    def guide(self, kind='交通'):
        place = dict(id='stop', kind=kind, desc='介绍' * 20, walk='走法' * 20, tip='条件' * 20)
        return dict(places=[place], days=[dict(id=f'd{i}', stops=[['上午', 'stop', '']], photoPlan=[]) for i in range(1, 4)])

    def test_transfer_only_middle_day_does_not_require_photography(self):
        self.assertEqual(audit_content(self.guide()), [])

    def test_photo_exception_cannot_hide_invalid_place_or_missing_fields(self):
        guide = self.guide()
        guide['days'][1].update(photoExceptionReason='测试输入：用户要求减少摄影', photoPlan=[dict(placeId='missing')])
        errors = '\n'.join(audit_content(guide))
        self.assertIn('摄影地点不在当天路线', errors)
        self.assertIn('缺少字段', errors)

    def test_explicit_short_photo_plan_can_relax_volume(self):
        guide = self.guide('景观')
        for day in guide['days']:
            day['photoExceptionReason'] = '测试输入：用户要求每处只给简短提示'
            day['photoPlan'] = [dict(time='上午', placeId='stop', title='主体', light='看光线', composition='保留主体', portrait='留出通道', settings='手机主摄')]
        self.assertEqual(audit_content(guide), [])
        del guide['days'][1]['photoExceptionReason']
        self.assertEqual(audit_content(guide), [])

    def test_route_ids_are_not_shopping_advice(self):
        g=self.guide();g['days'][0]['shopping']=['stop']
        self.assertTrue(any('shopping' in x for x in audit_content(g)))

    def test_concise_place_copy_needs_distinct_complete_fields_not_padding(self):
        g=self.guide();g['places'][0].update(desc='跨城车站。',walk='按站牌找对应方向。',tip='上车前核对终点。')
        self.assertEqual(audit_content(g),[])
        g['places'][0]['tip']=g['places'][0]['desc']
        self.assertTrue(any('不可重复' in x for x in audit_content(g)))

    def test_all_day_text_is_not_three_periods(self):
        g=self.guide();g['days'][0].update(lead='全天',move='交通',guard='提醒',periods=['全天','交通','提醒'])
        self.assertTrue(any('periods' in x for x in audit_content(g)))

    def test_duplicate_photo_prose_is_rejected_even_with_exception(self):
        g=self.guide();d=g['days'][0];d['photoExceptionReason']='用户精简'
        shot=dict(time='上午',placeId='stop',title='角度',light='光',composition='构图',portrait='人',settings='参数')
        d['photoPlan']=[shot,dict(shot,title='另一个标题')]
        self.assertTrue(any('重复摄影' in x for x in audit_content(g)))


if __name__ == '__main__':
    unittest.main()
