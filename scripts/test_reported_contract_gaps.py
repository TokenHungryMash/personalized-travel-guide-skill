"""Offline regressions for reported pack/compile and source-ladder gaps."""
import unittest
from unittest.mock import patch
from validate_research_pack import validate, scaffold
from research_image_candidates import collect

class ReportedGaps(unittest.TestCase):
    def test_semantic_type_fails_in_owning_pack(self):
        row = scaffold('places-core')
        row['sights'][0]['type'] = 'shrine'
        self.assertTrue(any(e['pointer']=='/sights/0/type' and e['code']=='enum' for e in validate('places-core',row)))

    def test_souvenir_fields_fail_early(self):
        row = scaffold('places-shopping')
        self.assertTrue(any(e['pointer']=='/souvenirs/0/why_buy' for e in validate('places-shopping',row)))

    def test_language_legacy_names_fail_early(self):
        row = scaffold('modules-language-notes')
        row['language']['keyword_groups'] = [{'title':'购物','items':[{'term':'ありがとう','meaning':'谢谢','roman':'arigatou'}]}]
        row['language']['english_phrase_groups'] = [{'title':'购物','items':[{'term':'Thank you','meaning':'谢谢'}]}]
        errors = validate('modules-language-notes',row)
        self.assertTrue(any(e['pointer'].endswith('/reading') for e in errors))
        self.assertTrue(any(e['pointer'].endswith('/sentence') for e in errors))

    def test_timeline_catches_meal_overlap_before_compile(self):
        row = scaffold('itinerary')
        row[0]['stops'] = [{'place_id':'walk','arrival_time':'12:00','dwell_minutes':90,'transfer_minutes':0}, {'place_id':'meal','arrival_time':'12:30','dwell_minutes':60,'transfer_minutes':10}]
        self.assertTrue(any(e['code']=='timeline' and 'overlap' in e['message'] for e in validate('itinerary',row)))
        row[0]['stops'][1]['arrival_time'] = '13:40'
        self.assertFalse(any(e['code']=='timeline' for e in validate('itinerary',row)))

    def test_commercial_failure_never_calls_open_media(self):
        with patch('research_image_candidates.official', return_value=[]), patch('research_image_candidates.wikidata') as wd, patch('research_image_candidates.openverse') as ov, patch('research_image_candidates.commons_geo') as commons:
            result = collect({'id':'restaurant','kind':'restaurant','official_url':'https://example.org/branch'},2)
        wd.assert_not_called()
        ov.assert_not_called()
        commons.assert_not_called()
        self.assertEqual(result['candidates'],[])
        self.assertIn('replace',result['next_action'])

    def test_missing_official_input_is_not_source_exhaustion(self):
        with patch('research_image_candidates.official') as official, patch('research_image_candidates.wikidata') as wd:
            result = collect({'id':'restaurant','kind':'restaurant'},2)
        official.assert_not_called()
        wd.assert_not_called()
        self.assertEqual(result['input_status'],'needs_official_url')

    def test_unresolved_image_blocks_owning_pack(self):
        row = scaffold('places-food')
        row[0]['images'] = [{'source_type':'unresolved','download_url':''}]
        self.assertTrue(any(e['code']=='image_unresolved' for e in validate('places-food',row)))

if __name__ == '__main__':
    unittest.main()
