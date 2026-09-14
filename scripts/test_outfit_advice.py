import copy
import unittest
from _outfit_advice import outfit_errors, outfit_html
from _current_system_adapter import runtime_bindings
from validate_research_pack import CONTRACT, validate
from test_current_system_build import profile


class OutfitAdviceTests(unittest.TestCase):
    def test_both_suggestions_are_required_early(self):
        day=copy.deepcopy(CONTRACT['packs']['itinerary']['example_item'])
        day['photo_advice'].pop('outfit_advice')
        errors=validate('itinerary',[day])
        self.assertIn('/0/photo_advice/outfit_advice',[e['pointer'] for e in errors])
        day['photo_advice']['outfit_advice']={'women':'外套、长裤、步行鞋','men':'针织衫、长裤、运动鞋','practical_note':'按当日预报增减衣层'}
        self.assertFalse([e for e in validate('itinerary',[day]) if e['code']=='outfit_advice'])
        day['photo_advice']['outfit_advice']['men']=''
        self.assertIn('/0/photo_advice/outfit_advice/men',[e['pointer'] for e in validate('itinerary',[day])])

    def test_static_card_escapes_and_renders_both(self):
        photo={'outfit_advice':{'women':'<裙装>配外套','men':'长裤与步行鞋','practical_note':'遇雨加防水外层'}}
        html=outfit_html(photo)
        self.assertIn('女生穿搭',html)
        self.assertIn('男生穿搭',html)
        self.assertIn('&lt;裙装&gt;',html)
        self.assertNotIn('<裙装>',html)
        self.assertEqual(outfit_errors(photo,'/photo_advice'),[])

    def test_trip_mode_uses_same_payload(self):
        data=profile()
        data['itinerary'][0]['photo_advice']={'outfit_advice':{'women':'女性搭配文本','men':'男性搭配文本','practical_note':'路线相关调整'}}
        js={r['path']:r['content'] for r in runtime_bindings(data)}['trip-mode.js']
        self.assertIn('cards+=outfits(n);',js)
        self.assertIn('女生穿搭',js)
        self.assertIn('男生穿搭',js)
        self.assertIn('esc(a[pair[0]])',js)


if __name__=='__main__':
    unittest.main()
