"""Regressions observed during a fresh Seoul build, without browser claims."""
import unittest
from _current_system_adapter import preparation_html
from validate_research_pack import validate, scaffold


class GenerationRegressionTests(unittest.TestCase):
    def test_draft_checklist_shape_renders_without_keyerror(self):
        profile={'module_groups':{'preparation':{'confirm_ahead':[
            {'title':'预约舞蹈课','note':'选择适合水平的课程','timing':'出发前','priority':'随缘'}]}}}
        base='<div class="prepare-block"><div class="prepare-heading"><span>02</span>old<a class="back-to-contents">back</a>'
        html=preparation_html(profile,base)
        self.assertIn('预约舞蹈课',html)
        self.assertIn('出发前 · 选择适合水平的课程',html)
        self.assertIn('data-priority="2"',html)

    def test_menu_wrong_field_is_rejected_before_compile(self):
        pack=scaffold('modules-practical')
        pack['food']['menu_guide']['cards']=[{'title':'点单','description':'内容'*30} for _ in range(4)]
        errors=validate('modules-practical',pack)
        self.assertTrue(any(e['pointer']=='/food/menu_guide/cards/0' for e in errors))

    def test_pending_support_is_empty_not_missing_or_wrong_type(self):
        pack={'sights':[{'id':'x'}],'support':[]}
        self.assertFalse(any(e['pointer']=='/support' for e in validate('places-core',pack)))
        pack['support']={}
        self.assertTrue(any(e['pointer']=='/support' for e in validate('places-core',pack)))

    def test_invalid_priority_is_not_silently_treated_as_recommended(self):
        pack=scaffold('modules-practical')
        pack['preparation']['essentials']=[{'title':'证件','note':'按实际证件准备','priority':'紧急'}]
        self.assertTrue(any(e['pointer']=='/preparation/essentials/0/priority' for e in validate('modules-practical',pack)))

    def test_missing_priority_is_rejected_in_pack_validation(self):
        pack=scaffold('modules-practical')
        pack['preparation']['essentials']=[{'title':'证件','note':'按实际证件准备'}]
        self.assertTrue(any(e['pointer']=='/preparation/essentials/0/priority' for e in validate('modules-practical',pack)))

    def test_short_experience_description_fails_before_compilation(self):
        item=scaffold('places-experiences')[0]
        item.update(id='walk', display_name='城市散步', map_query='Exact walk', source_url='https://example.com/walk', description='太短', hours='白天', closed_days=['待确认'], latitude=35.0, longitude=139.0)
        errors=validate('places-experiences',[item])
        self.assertTrue(any(e['pointer']=='/0/description' for e in errors))

if __name__=='__main__':unittest.main()
