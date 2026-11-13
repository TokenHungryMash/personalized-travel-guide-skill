"""Source wiring failures must stop a new authored edition before rendering."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets/destination-reference'))
from editorial_evidence import audit_evidence


class EvidenceContract(unittest.TestCase):
    def setUp(self):
        self.t = {k: [['Decision', 'A concrete answer.']] for k in ('portrait', 'stays', 'culture', 'shopping')}
        self.t['notes'] = {'Transport': [['Ticket', 'Operator coverage and alternative.']]}
        self.t['editorial_sources'] = {'official': {'url': 'https://example.com/visitor', 'title': 'Visitor information', 'checked': '2026-11-12'}}
        self.t['section_sources'] = {k: {'0': ['official']} for k in ('portrait', 'stays', 'culture', 'shopping', 'notes:Transport')}

    def test_complete_wiring(self):
        self.assertEqual(audit_evidence(self.t, True), [])

    def test_broken_row_or_source(self):
        self.t['section_sources']['culture']['0'] = ['missing']
        self.assertIn('unknown source', ' '.join(audit_evidence(self.t, True)))
        self.t['section_sources']['culture'] = {'9': ['official']}
        error = ' '.join(audit_evidence(self.t, True))
        self.assertIn('nonexistent row', error)
        self.assertIn('culture[0]', error)

    def test_required_body_and_source_cannot_be_empty(self):
        self.t['shopping'][0] = ['Only a title']
        del self.t['section_sources']['stays']
        errors = ' '.join(audit_evidence(self.t, True))
        self.assertIn('missing body', errors)
        self.assertIn('stays[0]', errors)

    def test_invalid_date_and_url(self):
        self.t['editorial_sources']['official'].update(url='javascript:alert(1)', checked='recently')
        errors = ' '.join(audit_evidence(self.t, True))
        self.assertIn('URL', errors)
        self.assertIn('YYYY-MM-DD', errors)

    def test_legacy_content_without_sources_is_not_relabelled_verified(self):
        legacy = copy.deepcopy(self.t)
        del legacy['section_sources']
        del legacy['editorial_sources']
        self.assertEqual(audit_evidence(legacy), [])
        self.assertTrue(audit_evidence(legacy, True))

    def test_original_advice_requires_explicit_reason(self):
        del self.t['section_sources']['portrait']['0']
        self.t['editorial_advice'] = {'portrait': {'0': 'Tradeoff based on this authored itinerary only.'}}
        self.assertEqual(audit_evidence(self.t, True), [])
        self.t['editorial_advice']['portrait']['0'] = ''
        self.assertIn('explain why', ' '.join(audit_evidence(self.t, True)))
        self.t['editorial_advice']['portrait'] = {'5': 'Wrong row'}
        self.assertIn('nonexistent row', ' '.join(audit_evidence(self.t, True)))

    def test_area_coverage_and_sources_are_not_silently_lost(self):
        self.assertIn('missing regional introduction', ' '.join(audit_evidence(self.t, True, ['west'])))
        self.t['area_sections'] = {'west': [['District', 'Distinctive local facts.']]}
        self.t['section_sources']['areas:west'] = {'0': ['official']}
        self.assertEqual(audit_evidence(self.t, True, ['west']), [])
        self.t['area_sections']['other'] = [['Wrong area', 'This would never render.']]
        self.assertIn('unknown area ID', ' '.join(audit_evidence(self.t, True, ['west'])))

    def test_food_facts_need_sources_in_new_editions(self):
        self.t['food_types'] = [['Local dish', 'Ingredients and ordering choices.']]
        self.assertIn('food_types[0]', ' '.join(audit_evidence(self.t, True)))
        self.t['section_sources']['food_types'] = {'0': ['official']}
        self.assertEqual(audit_evidence(self.t, True), [])

    def test_experience_advice_is_supported_without_a_source_mapping(self):
        self.t['route_experiences'] = [dict(areaId='west', title='A route choice', copy='An original preference-based suggestion.', extra='')]
        self.assertIn('experiences:west[0]', ' '.join(audit_evidence(self.t, True)))
        self.t['editorial_advice'] = {'experiences:west': {'0': 'Original route tradeoff without external facts.'}}
        self.assertEqual(audit_evidence(self.t, True), [])
        self.t['editorial_advice']['experiences:west']['1'] = 'No second experience row exists.'
        self.assertIn('nonexistent row', ' '.join(audit_evidence(self.t, True)))


if __name__ == '__main__':
    unittest.main()
