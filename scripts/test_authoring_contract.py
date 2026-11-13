"""Failures reported by new destination authors should identify actionable fields."""
import copy
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'assets/destination-reference'
sys.path.insert(0, str(TEMPLATE))
from destination_content import audit_relationships
from schema_check import audit_schema
from travel_content import audit_content
from audit_directory import audit
from validate_edition import validate


class AuthoringContract(unittest.TestCase):
    def setUp(self):
        load = lambda name: json.loads((TEMPLATE / name).read_text(encoding='utf8'))
        self.guide, self.edition, self.editorial = [load(name) for name in ('content.json', 'edition.json', 'editorial-content.json')]

    def errors(self):
        return '\n'.join(audit_relationships(self.guide, self.edition, self.editorial))

    def test_day_index_is_explicit_and_not_rewritten(self):
        area = self.guide['areas'][0]
        for value in (-1, len(self.guide['days']), '1', True):
            with self.subTest(value=value):
                area['day'] = value
                error = self.errors()
                self.assertIn(area['id'], error)
                self.assertIn('0-based', error)
                self.assertEqual(area['day'], value)

    def test_missing_and_extra_schedule_keys(self):
        day = self.guide['days'][0]
        pid = day['stops'][0][1]
        day['schedules']['standard']['obsolete'] = day['schedules']['standard'].pop(pid)
        error = self.errors()
        self.assertIn('missing=', error)
        self.assertIn(pid, error)
        self.assertIn("extra=['obsolete']", error)

    def test_route_experiences_order_and_count(self):
        self.editorial['route_experiences'][0]['areaId'] = 'wrong-area'
        self.assertIn('expected', self.errors())
        self.editorial['route_experiences'].pop()
        self.assertIn('one entry per area', self.errors())

    def test_map_url_allowed_but_missing_or_invalid_link_rejected(self):
        self.guide['places'][0]['url'] = 'https://www.google.com/maps/search/?api=1&query=Tokyo'
        self.assertEqual(audit_schema(self.guide), [])
        self.guide['places'][0]['url'] = 'not a URL'
        self.assertIn('places[0].url', '\n'.join(audit_schema(self.guide)))

    def test_photo_counts_explain_field_gaps(self):
        day = self.guide['days'][0]
        day['photoPlan'] = [{'placeId': day['stops'][0][1], 'title': '测试', 'light': '光' * 20,
                             'composition': '景' * 50, 'portrait': '', 'settings': '设' * 57}]
        errors = '\n'.join(audit_content(self.guide))
        self.assertIn('photoPlan[0]', errors)
        self.assertIn('缺少字段', errors)
        self.assertIn('portrait', errors)
        self.assertIn('time', errors)

    def test_file_argument_reports_parent_without_traceback(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/audit_travel_content.py'),
                                 str(TEMPLATE / 'content.json')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'workbench directory', result.stderr)
        self.assertIn(b'parent directory', result.stderr)
        self.assertNotIn(b'Traceback', result.stderr)

    def test_missing_photos_produce_editable_pending_list(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for file, data in [('content.json', self.guide), ('place-photos.json', {}),
                               ('directory-plan.json', {'targetRange': [0, 100], 'photoExceptions': {}})]:
                (root / file).write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
            report = audit(root)
            self.assertEqual(set(report['pendingPhotoExceptions']), {p['id'] for p in self.guide['places']})
            self.assertTrue(all(value == '' for value in report['pendingPhotoExceptions'].values()))
            self.assertEqual(report['photos'], 0)
            # A partial/invalid photo record should produce a schema path, not KeyError.
            (root / 'place-photos.json').write_text('{"airport": {"reviewed": false}}')
            report = audit(root)
            self.assertIn('place-photos.json.airport', '\n'.join(report['errors']))

    def test_template_matches_both_content_schemas(self):
        self.assertEqual(audit_schema(self.guide), [])
        self.assertEqual(audit_schema(self.editorial, 'editorial-content'), [])

    def test_examples_cover_the_documented_content_structure(self):
        # This fixture only uses line comments outside strings; preserve URL //.
        text = (ROOT / 'assets/authoring-examples.jsonc').read_text(encoding='utf8')
        examples = json.loads(re.sub(r'(?m)(^|\s)//.*$', '', text))
        self.assertEqual(audit_schema(examples['content.json']), [])
        self.assertEqual(audit_schema(examples['editorial-content.json'], 'editorial-content'), [])

    def test_missing_area_and_day_fields_report_paths(self):
        cases = [('areas', field) for field in ('en', 'route', 'tip')]
        cases += [('days', field) for field in
                  ('area', 'title', 'lead', 'move', 'guard', 'budget', 'photo', 'periods', 'shopping', 'transfers')]
        for collection, field in cases:
            with self.subTest(collection=collection, field=field):
                guide = copy.deepcopy(self.guide)
                del guide[collection][0][field]
                errors = '\n'.join(audit_relationships(guide, self.edition, self.editorial))
                self.assertIn(f'content.json.{collection}[0]', errors)
                self.assertIn(field, errors)

    def test_route_experience_fields_are_checked_before_renderer(self):
        for field in ('tone', 'words', 'title', 'copy', 'extra', 'place', 'label'):
            with self.subTest(field=field):
                editorial = copy.deepcopy(self.editorial)
                del editorial['route_experiences'][0][field]
                errors = '\n'.join(audit_relationships(self.guide, self.edition, editorial))
                self.assertIn('editorial-content.json.route_experiences[0]', errors)
                self.assertIn(field, errors)
                with self.assertRaisesRegex(ValueError, 'route_experiences'):
                    validate(self.guide, self.edition, editorial, {})

    def test_restaurant_group_and_item_required_fields(self):
        for field in ('name', 'en', 'items'):
            with self.subTest(group=field):
                editorial = copy.deepcopy(self.editorial)
                del editorial['restaurant_groups'][0][field]
                errors = '\n'.join(audit_relationships(self.guide, self.edition, editorial))
                self.assertIn('editorial-content.json.restaurant_groups[0]', errors)
                self.assertIn(field, errors)
        for field in ('id', 'why', 'order', 'fit', 'budget', 'note'):
            with self.subTest(item=field):
                editorial = copy.deepcopy(self.editorial)
                del editorial['restaurant_groups'][0]['items'][0][field]
                errors = '\n'.join(audit_relationships(self.guide, self.edition, editorial))
                self.assertIn('editorial-content.json.restaurant_groups[0].items[0]', errors)
                self.assertIn(field, errors)

    def test_renderer_table_shapes_are_not_generic_arrays(self):
        cases = [
            ('portrait', [['heading', 'body', 'extra']], 'portrait[0]'),
            ('stays', [[]], 'stays[0]'),
            ('food_types', [['heading', 100]], 'food_types[0][1]'),
            ('shopping', {'wrong': 'object'}, 'shopping'),
            ('culture', [None], 'culture[0]'),
            ('notes', {'transport': 'wrong'}, 'notes.transport'),
            ('reservations', [['title', {'wrong': 'object'}]], 'reservations[0][1]'),
            ('phrases', {'food': [['single column']]}, 'phrases.food[0]'),
            ('checklist', {'before': [100]}, 'checklist.before[0]'),
            ('source_labels', {'source': []}, 'source_labels.source'),
        ]
        for field, value, path in cases:
            with self.subTest(field=field):
                editorial = copy.deepcopy(self.editorial)
                editorial[field] = value
                errors = '\n'.join(audit_relationships(self.guide, self.edition, editorial))
                self.assertIn('editorial-content.json.' + path, errors)

    def test_wrong_nested_types_report_paths_without_key_errors(self):
        guide = copy.deepcopy(self.guide)
        guide['days'][0]['title'] = []
        guide['days'][0]['periods'] = 'wrong'
        guide['days'][0]['shopping'] = None
        first = next(iter(guide['days'][0]['transfers']))
        guide['days'][0]['transfers'][first]['minutes'] = 'twenty'
        editorial = copy.deepcopy(self.editorial)
        editorial['route_experiences'][0]['words'] = {'wrong': 'object'}
        editorial['restaurant_groups'][0]['items'] = 'wrong'
        errors = '\n'.join(audit_relationships(guide, self.edition, editorial))
        for path in ('content.json.days[0].title', 'content.json.days[0].periods',
                     'content.json.days[0].shopping', f'content.json.days[0].transfers.{first}.minutes',
                     'editorial-content.json.route_experiences[0].words',
                     'editorial-content.json.restaurant_groups[0].items'):
            self.assertIn(path, errors)

    def test_optional_legacy_fields_and_extension_keys_remain_compatible(self):
        guide = copy.deepcopy(self.guide)
        for place in guide['places']:
            place.pop('walk', None)
        for day in guide['days']:
            day.pop('photoPlan', None)
        guide['futureExtension'] = {'kept': True}
        editorial = copy.deepcopy(self.editorial)
        for key in ('restaurant_groups', 'snacks', 'source_labels'):
            editorial.pop(key, None)
        editorial['futureExtension'] = ['kept']
        self.assertEqual(audit_schema(guide), [])
        self.assertEqual(audit_schema(editorial, 'editorial-content'), [])

    def test_missing_editorial_sections_report_file_and_key(self):
        for key in ('portrait', 'stays', 'route_experiences', 'food_types', 'shopping',
                    'culture', 'notes', 'reservations', 'checklist', 'phrases'):
            with self.subTest(key=key):
                editorial = copy.deepcopy(self.editorial)
                del editorial[key]
                errors = '\n'.join(audit_relationships(self.guide, self.edition, editorial))
                self.assertIn('editorial-content.json', errors)
                self.assertIn(key, errors)

    def test_duplicate_area_and_place_ids_are_reported(self):
        self.guide['areas'][1]['id'] = self.guide['areas'][0]['id']
        self.editorial['route_experiences'][1]['areaId'] = self.guide['areas'][0]['id']
        self.assertIn('content.json.areas[1].id', self.errors())
        self.assertIn('duplicate', self.errors())
        self.guide['places'][1]['id'] = self.guide['places'][0]['id']
        self.assertIn('content.json.places[1].id', self.errors())


if __name__ == '__main__':
    unittest.main()
