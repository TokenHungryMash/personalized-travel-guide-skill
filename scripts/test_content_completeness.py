import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).resolve().parents[1]/'assets/destination-reference/content_completeness.py'
s=importlib.util.spec_from_file_location('completeness',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class CompletenessTests(unittest.TestCase):
    def fixture(self):
        t={k:[['主题','有实质内容的说明。'*30]] for k in ('portrait','stays','culture','shopping')}
        t.update(phrases={},words={},languageScenes=[])
        for i in range(6):
            k=str(i);t['phrases'][k]=[{}]*4;t['words']['g'+k]=[{}]*8;t['words']['r'+k]=[{}]*2
            t['languageScenes'].append(dict(id=k,phrases=k,glossary='g'+k,replies='r'+k))
        return t
    def test_english_is_not_abbreviated(self):
        t=self.fixture();t['words']={}
        for lang in ('en','en-GB','ja'):
            self.assertTrue(m.audit_completeness({},dict(contentCompletenessVersion=1,lang=lang),t))
    def test_full_scene_structure_passes_in_either_language(self):
        for lang in ('en','ja'):
            self.assertEqual(m.audit_completeness({},dict(contentCompletenessVersion=1,lang=lang),self.fixture()),[])
    def test_old_singapore_shape_is_rejected(self):
        t=self.fixture();t['portrait']=[];t['languageScenes']=t['languageScenes'][:3]
        errors=m.audit_completeness({},dict(contentCompletenessVersion=1),t)
        self.assertTrue(any('portrait' in e for e in errors));self.assertTrue(any('six complete' in e for e in errors))
    def test_legacy_not_silently_broken(self):
        self.assertEqual(m.audit_completeness({}, {}, {}),[])
    def test_short_body_is_not_rejected_by_character_count(self):
        t=self.fixture();t['portrait']=[['地形','看火山。'],['生活','逛市场。']]
        self.assertEqual(m.audit_completeness({},dict(contentCompletenessVersion=1),t),[])
