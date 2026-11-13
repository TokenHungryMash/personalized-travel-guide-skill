"""Validate reader reference identities, source wiring and legacy compatibility."""
import copy
import json
from pathlib import Path
import sys
import unittest

TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/destination-reference'
sys.path.insert(0, str(TEMPLATE))
from destination_content import audit_relationships
from editorial_evidence import audit_reader_reference_evidence
from schema_check import audit_schema


class ReaderReferenceValidation(unittest.TestCase):
    def setUp(self):
        load = lambda name: json.loads((TEMPLATE / name).read_text(encoding='utf8'))
        self.guide, self.edition, self.editorial = [load(name) for name in
            ('content.json', 'edition.json', 'editorial-content.json')]
        self.edition['readerReferenceVersion'] = 1
        self.editorial['editorial_sources'] = {'official': {
            'url': 'https://example.com/visitor', 'title': 'Visitor information',
            'checked': '2026-11-12'}}
        self.editorial['preparation'] = [{
            'title': '出发前', 'items': [
                dict(id='c0', title='核对证件', detail='核对有效期并保存副本。', priority='必须', sources=['official']),
                dict(id='prep-ticket-check', title='核对车票', detail='确认日期及上下车站。', priority='建议', sources=['official'])]}]
        self.editorial['phrases'] = {
            '餐饮': [dict(id='food-allergy', local='I am allergic to {ingredient}.',
                        zh='我对 {ingredient} 过敏。', roman='', note='请对方确认具体食材。',
                        input=dict(key='ingredient', label='过敏食材', required=True,
                                   options=[dict(value='peanuts', label='花生')], placeholder='填写具体食材'))],
            '问路': [['Where is the station?', '车站在哪里？']]}
        self.editorial['words'] = {'回答': [
            ['Closed', '休息中'], dict(local='Open', zh='营业中', roman='')]}
        for group in self.editorial['restaurant_groups']:
            for item in group['items']:
                item['sources'] = ['official']
        self.restaurant = self.editorial['restaurant_groups'][0]['items'][0]
        self.guide['days'][0]['dining'] = [self.restaurant['id']]

    def errors(self):
        return '\n'.join(audit_relationships(self.guide, self.edition, self.editorial))

    def test_mixed_new_and_legacy_content_passes_without_mutation(self):
        before = copy.deepcopy((self.guide, self.edition, self.editorial))
        self.assertEqual(self.errors(), '')
        self.assertEqual((self.guide, self.edition, self.editorial), before)
    def test_english_only_empty_fallback_fields_are_unused_and_not_mutated(self):
        self.edition['lang']='en-GB'
        row=self.editorial['phrases']['餐饮'][0]
        row['english']='';row['input']['englishLabel']=''
        row['input']['options'][0]['english']='  '
        self.editorial['words']['回答'][1]['english']=''
        before=copy.deepcopy(self.editorial)
        self.assertEqual(self.errors(),'')
        self.assertEqual(self.editorial,before)
        from language_fields import normalized_language_content
        normalized=normalized_language_content(self.editorial,'en-GB')
        self.assertNotIn('english',normalized['phrases']['餐饮'][0])
        self.edition['lang']='fr'
        self.assertIn('english',self.errors())

    def test_new_preparation_replaces_checklist_and_legacy_remains_valid(self):
        del self.editorial['checklist']
        self.assertEqual(self.errors(), '')
        load = lambda name: json.loads((TEMPLATE / name).read_text(encoding='utf8'))
        self.assertEqual(audit_relationships(load('content.json'), load('edition.json'),
                                            load('editorial-content.json')), [])
        del self.editorial['preparation']
        self.assertIn('editorial-content.json', self.errors())

    def test_task_ids_and_priorities_are_constrained(self):
        for value in ('task-1', 'prep-UPPER', 'prep-', 'prep-two words', 1):
            with self.subTest(id=value):
                self.editorial['preparation'][0]['items'][0]['id'] = value
                self.assertIn('preparation[0].items[0].id', self.errors())
        self.editorial['preparation'][0]['items'][0]['id'] = 'prep-valid-2'
        self.editorial['preparation'][0]['items'][0]['priority'] = '紧急'
        self.assertIn('priority', self.errors())

    def test_duplicate_task_ids_across_stages_are_rejected(self):
        duplicate = copy.deepcopy(self.editorial['preparation'][0]['items'][0])
        self.editorial['preparation'].append(dict(title='出发当天', items=[duplicate]))
        self.assertIn('preparation[1].items[0].id', self.errors())
        self.assertIn('duplicate', self.errors())

    def test_duplicate_phrase_ids_and_legacy_generated_collision_are_rejected(self):
        first = self.editorial['phrases']['餐饮'][0]
        self.editorial['phrases']['其他'] = [copy.deepcopy(first)]
        self.assertIn('phrase IDs must be unique', self.errors())
        del self.editorial['phrases']['其他']
        first['id'] = 'phrase-1-0'
        self.assertIn('phrase IDs must be unique', self.errors())

    def test_input_types_and_unrecognised_fields_fail_schema_before_relationships(self):
        original = copy.deepcopy(self.editorial['phrases']['餐饮'][0]['input'])
        changes = [('required', 'true'), ('required', 1), ('options', {}),
                   ('options', ['peanuts']), ('options', [{'value': 10, 'label': '花生'}]),
                   ('options', [{'value': 'peanuts', 'label': None}]),
                   ('options', [{'value': 'peanuts', 'label': '花生', 'unexpected': True}]),
                   ('unknown', 'silently ignored')]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                self.editorial['phrases']['餐饮'][0]['input'] = {**original, key: value}
                self.assertTrue(audit_schema(self.editorial, 'editorial-content'))
                self.assertIn('phrases.餐饮[0]', self.errors())
        self.editorial['phrases']['餐饮'][0]['input'] = original
        del self.editorial['phrases']['餐饮'][0]['input']['required']
        self.assertIn('phrases.餐饮[0]', self.errors())

    def test_input_option_values_are_unambiguous(self):
        self.editorial['phrases']['餐饮'][0]['input']['options'].append(
            dict(value='peanuts', label='另一种显示文字'))
        self.assertIn('option values must be unique', self.errors())

    def test_new_word_shape_and_unknown_new_task_fields_are_checked(self):
        self.editorial['words']['回答'][1]['roman'] = []
        self.assertIn('words.回答[1]', self.errors())
        self.editorial['words']['回答'][1]['roman'] = ''
        self.editorial['preparation'][0]['items'][0]['unknown'] = 'ignored'
        self.assertIn('preparation[0].items[0]', self.errors())
        self.assertIn('Additional properties', self.errors())

    def test_dining_requires_known_restaurant_venue(self):
        day = self.guide['days'][0]
        day['dining'] = ['missing-restaurant']
        self.assertIn('d1.dining[0]: unknown place', self.errors())
        restaurant_ids = {item['id'] for group in self.editorial['restaurant_groups'] for item in group['items']}
        day['dining'] = [next(place['id'] for place in self.guide['places'] if place['id'] not in restaurant_ids)]
        self.assertIn('must belong to restaurant_groups', self.errors())
        day['dining'] = [self.restaurant['id']]
        next(place for place in self.guide['places'] if place['id'] == self.restaurant['id'])['identityScope'] = 'area'
        self.assertIn('is an area, not a restaurant venue', self.errors())

    def test_dining_is_unique_id_array_without_modifying_stops(self):
        stops = copy.deepcopy(self.guide['days'][0]['stops'])
        for value in (self.restaurant['id'], [100], [self.restaurant['id']] * 2):
            with self.subTest(value=value):
                self.guide['days'][0]['dining'] = value
                self.assertIn('content.json.days[0].dining', self.errors())
        self.assertEqual(self.guide['days'][0]['stops'], stops)

    def test_restaurant_cannot_repeat_within_or_across_groups(self):
        for target in (0, 1):
            with self.subTest(group=target):
                self.editorial['restaurant_groups'][target]['items'].append(copy.deepcopy(self.restaurant))
                self.assertIn('each restaurant belongs to one group only', self.errors())
                self.editorial['restaurant_groups'][target]['items'].pop()

    def test_sources_required_in_new_version_but_optional_for_legacy(self):
        del self.editorial['preparation'][0]['items'][0]['sources']
        del self.restaurant['sources']
        errors = self.errors()
        self.assertIn('preparation[0].items[0].sources', errors)
        self.assertIn('restaurant_groups[0].items[0].sources', errors)
        self.edition.pop('readerReferenceVersion')
        self.assertEqual(self.errors(), '')

    def test_sources_if_present_must_exist_even_in_legacy_mode(self):
        self.edition.pop('readerReferenceVersion')
        self.editorial['preparation'][0]['items'][0]['sources'] = ['unknown']
        self.restaurant['sources'] = ['unknown']
        errors = self.errors()
        self.assertIn('preparation[0].items[0].sources: missing or unknown source ID', errors)
        self.assertIn('restaurant_groups[0].items[0].sources: missing or unknown source ID', errors)
        self.assertTrue(audit_reader_reference_evidence(self.editorial))

    def test_malformed_structures_short_circuit_relationship_audit(self):
        self.editorial['preparation'] = [None]
        self.editorial['restaurant_groups'][0]['items'] = [None]
        self.editorial['phrases'] = {'坏条目': [None]}
        errors = self.errors()
        for path in ('preparation[0]', 'restaurant_groups[0].items[0]', 'phrases.坏条目[0]'):
            self.assertIn(path, errors)
        self.assertNotIn('unknown source ID', errors)

    def with_language_scenes(self):
        self.editorial['phrases']['餐饮'][0]['english'] = 'I am allergic to the ingredient shown above.'
        field = self.editorial['phrases']['餐饮'][0]['input']
        field['englishLabel'] = '过敏食材（英语）'
        field['englishPlaceholder'] = 'Enter the ingredient'
        field['options'][0]['english'] = 'peanuts'
        self.editorial['phrases']['问路'] = [dict(id='station-question', local='Where is the station?',
            zh='车站在哪里？', roman='', english='Where is the station?')]
        self.editorial['words'] = {
            '常备 · 菜单': [dict(local='Menu', zh='菜单', roman='', english='Menu')],
            '回答': [dict(local='Closed', zh='休息中', roman='', english='Closed')]}
        self.editorial['languageScenes'] = [
            dict(id='food', label='点餐', phrases='餐饮', glossary='常备 · 菜单', replies='回答'),
            dict(id='transport', label='交通', phrases='问路')]

    def test_scene_contract_keeps_complete_english_and_local_groups(self):
        self.with_language_scenes()
        before = copy.deepcopy(self.editorial)
        self.assertEqual(self.errors(), '')
        self.assertEqual(self.editorial, before)

    def test_new_workbook_requires_scene_and_english_contract_without_weakening_sources(self):
        self.edition['readerReferenceVersion'] = 2
        self.assertIn('languageScenes: required', self.errors())
        self.with_language_scenes()
        self.assertEqual(self.errors(), '')
        del self.editorial['phrases']['问路'][0]['english']
        self.assertIn('phrases.问路[0].english', self.errors())
        del self.restaurant['sources']
        self.assertIn('restaurant_groups[0].items[0].sources: required', self.errors())

    def test_scene_identity_reference_and_coverage_are_checked(self):
        self.with_language_scenes()
        self.editorial['languageScenes'][1]['id'] = 'food'
        self.assertIn('scene IDs must be unique', self.errors())
        self.editorial['languageScenes'][1]['id'] = 'transport'
        self.editorial['languageScenes'][1]['phrases'] = 'missing'
        self.assertIn('unknown phrases group', self.errors())
        self.assertIn("phrases group '问路' is not assigned", self.errors())
        self.editorial['languageScenes'][1]['phrases'] = '餐饮'
        self.assertIn('each language group belongs to one scene', self.errors())
        self.editorial['languageScenes'][1]['phrases'] = '问路'
        self.editorial['languageScenes'][0]['replies'] = '常备 · 菜单'
        self.assertIn('unknown replies group', self.errors())

    def test_scene_contract_rejects_untranslated_words_and_input_options(self):
        self.with_language_scenes()
        del self.editorial['phrases']['餐饮'][0]['english']
        self.editorial['words']['常备 · 菜单'][0] = ['Menu', '菜单']
        del self.editorial['phrases']['餐饮'][0]['input']['englishLabel']
        del self.editorial['phrases']['餐饮'][0]['input']['options'][0]['english']
        errors = self.errors()
        for expected in ('phrases.餐饮[0].english', 'words.常备 · 菜单[0].english',
                         'input.englishLabel', 'input.options[0].english'):
            self.assertIn(expected, errors)

    def test_scene_contract_rejects_empty_malformed_or_unassigned_groups(self):
        self.with_language_scenes()
        self.editorial['words']['常备 · 菜单'] = []
        self.assertIn('referenced group must not be empty', self.errors())
        self.editorial['words']['未显示'] = [['Wait', '等候']]
        self.assertIn("replies group '未显示' is not assigned", self.errors())
        for value in ([], [dict(id='empty', label='空场景')], [dict(id='bad id', label='错误', phrases='餐饮')]):
            with self.subTest(scenes=value):
                self.editorial['languageScenes'] = value
                self.assertIn('languageScenes', self.errors())

    def test_subject_reference_uses_a_real_input_without_duplicating_its_identity(self):
        self.with_language_scenes()
        followup = dict(id='shared-equipment', local='Do you use the same equipment?',
            zh='会共用器具吗？', roman='', english='Do you use the same equipment?',
            subjectFrom='food-allergy')
        self.editorial['phrases']['餐饮'].append(followup)
        self.assertEqual(self.errors(), '')
        followup['subjectFrom'] = 'missing'
        self.assertIn('unknown phrase ID', self.errors())
        followup['subjectFrom'] = 'station-question'
        self.assertIn('source phrase must have an input', self.errors())
        followup['subjectFrom'] = followup['id']
        self.assertIn('cannot reference itself', self.errors())
        followup['subjectFrom'] = 'food-allergy'
        followup['input'] = copy.deepcopy(self.editorial['phrases']['餐饮'][0]['input'])
        self.assertIn('phrases.餐饮[1]', self.errors())


    def test_english_editions_do_not_require_or_render_duplicate_translations(self):
        from reader_reference import language_html
        self.with_language_scenes()
        self.edition['readerReferenceVersion'] = 2
        for groups in (self.editorial['phrases'], self.editorial['words']):
            for rows in groups.values():
                for row in rows:
                    row.pop('english', None)
                    if row.get('input'):
                        row['input'].pop('englishLabel', None)
                        for option in row['input']['options']:
                            option.pop('english', None)
        for code in ('en', 'en-GB', 'en-US'):
            self.edition['lang'] = code
            self.assertEqual(self.errors(), '')
            html = language_html(self.editorial, code, '英语')
            self.assertNotIn('data-language-mode=', html)
            self.assertNotIn('data-language-text="english"', html)
            self.assertNotIn('data-phrase-input="english"', html)
            self.assertEqual(html.count('data-phrase-input="local"'), 1)
        self.edition['lang'] = 'ja'
        self.assertIn('.english:', self.errors())
        self.assertIn('englishLabel', self.errors())

    def test_non_english_render_keeps_both_languages_and_shared_input_keys(self):
        from reader_reference import language_html
        self.with_language_scenes()
        html = language_html(self.editorial, 'ja', '日语')
        self.assertIn('data-language-mode="english"', html)
        self.assertIn('data-phrase-input="english"', html)
        self.assertIn('data-note="phrase:food-allergy:ingredient"', html)
        self.assertIn('data-note="phrase:food-allergy:ingredient:english"', html)


if __name__ == '__main__':
    unittest.main()
