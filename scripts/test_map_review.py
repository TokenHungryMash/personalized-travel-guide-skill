"""Regression cases for map coverage, stale coordinates and editorial review context."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from audit_maps import audit
from prepare_media_review import fingerprint, make_sheets, photo_usage


class MapReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        Image.new('RGB', (1400, 1100), 'white').save(self.root / 'map.png')
        self.guide = dict(places=[dict(id='a', name='A'), dict(id='b', name='B')],
                          days=[dict(id='d1', stops=[['09:00', 'a', ''], ['10:00', 'b', '']])])
        self.coordinates = dict(a=dict(latitude=0, longitude=0))
        self.map = dict(src='map.png', ids=['a', 'b'], mappedIds=['a'],
                        projection=dict(zoom=3, left=324, top=474, width=1400, height=1100),
                        pins=[dict(id='a', px=700, py=550, x=50, y=50)])
        self.maps = {key: copy.deepcopy(self.map) for key in ('d1', 'overview')}

    def run_audit(self):
        for name, value in [('content', self.guide), ('maps', self.maps), ('verified-coordinates', self.coordinates)]:
            (self.root / f'{name}.json').write_text(json.dumps(value), encoding='utf8')
        return audit(self.root)

    def test_known_pin_and_unknown_location_list(self):
        report = self.run_audit()
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['maps']['d1']['missingCoordinates'], ['b'])
        self.assertEqual(report['visualReview'], 'pending')

    def test_legacy_percent_pins_and_z_projection(self):
        for entry in self.maps.values():
            entry['projection']['z'] = entry['projection'].pop('zoom')
            entry['pins'][0].pop('px')
            entry['pins'][0].pop('py')
        self.assertEqual(self.run_audit()['errors'], [])
        for entry in self.maps.values():
            entry.pop('projection')
        report = self.run_audit()
        self.assertEqual(report['errors'], [])
        self.assertFalse(report['maps']['d1']['projectionChecked'])

    def test_route_missing_from_map(self):
        self.maps['d1']['ids'] = ['a']
        self.assertTrue(any('Itinerary stops missing' in message for message in self.run_audit()['errors']))

    def test_stale_map_does_not_cover_new_place(self):
        self.coordinates['a']['latitude'] = 85
        errors = self.run_audit()['errors']
        self.assertTrue(any('outside map coverage' in message for message in errors))
        self.assertTrue(any('recompute pins' in message for message in errors))

    def test_outside_pin_and_nonfinite_values(self):
        self.maps['d1']['pins'][0]['px'] = -3
        self.assertTrue(any('outside map bounds' in message for message in self.run_audit()['errors']))
        self.maps['d1']['pins'][0]['px'] = float('nan')
        self.assertTrue(any('non-finite' in message for message in self.run_audit()['errors']))

    def test_invalid_coordinate_rejected_on_legacy_map(self):
        self.maps['d1'].pop('projection')
        self.coordinates['a']['latitude'] = float('inf')
        self.assertTrue(any('finite numbers' in message for message in self.run_audit()['errors']))

    def test_projected_pin_requires_coordinates(self):
        self.coordinates.pop('a')
        errors = self.run_audit()['errors']
        self.assertTrue(any('projected pin without verified coordinates' in message for message in errors))

    def test_explicit_number_must_match_order(self):
        self.maps['d1']['pins'][0]['number'] = 2
        self.assertTrue(any('pin number differs' in message for message in self.run_audit()['errors']))
        self.maps['d1']['pins'][0].pop('number')
        self.assertEqual(self.run_audit()['errors'], [])

    def test_dimensions_and_duplicate_pins(self):
        self.maps['d1']['projection']['width'] = 1200
        self.maps['d1']['pins'].append(copy.deepcopy(self.maps['d1']['pins'][0]))
        errors = self.run_audit()['errors']
        self.assertTrue(any('Image dimensions' in message for message in errors))
        self.assertTrue(any('Duplicate pin' in message for message in errors))

    def test_map_visit_order_must_match_route(self):
        self.maps['d1']['ids'].reverse()
        self.assertTrue(any('visit order' in message for message in self.run_audit()['errors']))

    def test_editorial_context_exposes_wrong_subject_for_visual_review(self):
        self.guide['areas'] = [dict(day=0, name='筑地与代官山', deck='市场与街区', photo='wrong', ids=['a'])]
        usages, errors = photo_usage(self.root, self.guide, {}, dict(wrong=dict(src='map.png', caption='银座街景')))
        self.assertEqual(errors, [])
        self.assertIn('筑地与代官山', usages[0]['context'])
        self.assertEqual(usages[0]['caption'], '银座街景')
        sheets = make_sheets(self.root, self.root, 'editorial-review', usages)
        self.assertTrue(Path(sheets[0]).is_file())
        self.assertEqual(len(usages[0]['sha256']), 64)

    def test_resize_and_reencode_photo_match(self):
        image = Image.new('RGB', (800, 450), 'white')
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 25, 700, 310), fill='navy')
        draw.ellipse((100, 50, 220, 180), fill='yellow')
        image.save(self.root / 'old.png')
        image.resize((400, 225)).save(self.root / 'new.jpg', quality=80)
        difference = fingerprint(self.root / 'old.png') ^ fingerprint(self.root / 'new.jpg')
        self.assertLessEqual(difference.bit_count(), 20)


if __name__ == '__main__':
    unittest.main()
