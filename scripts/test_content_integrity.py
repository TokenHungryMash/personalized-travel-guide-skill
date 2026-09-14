import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from _content_integrity import content_failures, identity_documented, clock_minutes, date_key


class IntegrityTests(unittest.TestCase):
    def profile(self):
        return {'places': [{'id': 'shop', 'coordinate_source': {'url': 'https://example.org/shop', 'note': 'Exact entrance map pin', 'precision': 'entrance'}},
                           {'id': 'meal', 'type': 'restaurant', 'display_name': 'Meal', 'coordinate_source': {'url': 'https://example.org/meal', 'note': 'Exact restaurant map pin', 'precision': 'entrance'}}],
                'itinerary': [{'date': '2026-11-07', 'stops': [
                    {'place_id': 'shop', 'arrival_time': '10:00', 'dwell_minutes': 120, 'transfer_minutes': 0},
                    {'place_id': 'meal', 'arrival_time': '12:30', 'dwell_minutes': 60, 'transfer_minutes': 30}]}],
                'dining_plan': [{'date': '11月7日', 'place_id': 'meal', 'title': 'Meal'}]}

    def test_consistent_plan(self):
        self.assertEqual(content_failures(self.profile()), [])

    def test_overlap_and_transfer(self):
        for time in ['10:30', '12:10']:
            p = self.profile(); p['itinerary'][0]['stops'][1]['arrival_time'] = time
            self.assertTrue(any('overlap' in e for e in content_failures(p)))

    def test_dining_wrong_day(self):
        p = self.profile(); p['dining_plan'][0]['date'] = '11月8日'
        self.assertTrue(any('not scheduled' in e for e in content_failures(p)))

    def test_coordinates_without_evidence(self):
        p = self.profile(); p['places'][0].pop('coordinate_source')
        self.assertTrue(any('coordinate_source' in e for e in content_failures(p)))

    def test_official_domain_not_identity(self):
        r = {'source_page': 'https://example.org', 'source_identity_bound': True, 'source_type': 'official'}
        self.assertFalse(identity_documented(r))
        r['source_identity_note'] = 'Source caption identifies the exact branch exterior.'
        self.assertTrue(identity_documented(r))

    def test_conditional_time_not_invented(self):
        self.assertIsNone(clock_minutes('抵达后'))
        self.assertIsNone(clock_minutes('23:00 或次日 01:00'))
        self.assertEqual(clock_minutes('13:00（示例）'), 780)

    def test_manifest_does_not_promote_official_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = {'trip': {'quality_mode': 'standard'}, 'places': [
                {'id': 'venue', 'images': [{'file': 'photo.jpg', 'source_page': 'https://example.org/venue',
                  'source_type': 'official', 'source_identity_bound': True}]}]}
            (root / 'profile.json').write_text(json.dumps(profile), encoding='utf8')
            subprocess.run([sys.executable, str(Path(__file__).with_name('build_asset_manifest.py')),
                            str(root / 'profile.json'), str(root / 'manifest.json')], check=True, capture_output=True)
            asset = json.loads((root / 'manifest.json').read_text(encoding='utf8'))['assets'][0]
            self.assertFalse(asset['source_identity_bound'])
            self.assertFalse(asset['subject_verified'])

    def test_nonfinite_and_boolean_durations_rejected(self):
        for value in [float('nan'), float('inf'), True, -1, '60']:
            p = self.profile(); p['itinerary'][0]['stops'][0]['dwell_minutes'] = value
            self.assertTrue(any('finite nonnegative' in e for e in content_failures(p)))

    def test_year_and_invalid_dates(self):
        p = self.profile(); p['dining_plan'][0]['date'] = '2027-11-07'
        self.assertTrue(any('outside the itinerary' in e for e in content_failures(p)))
        self.assertIsNone(date_key('2026-02-30'))

    def test_unassigned_meal_requires_explicit_flexibility(self):
        p = self.profile(); p['dining_plan'][0] = {'date': '11月7日', 'title': '自由选择晚餐'}
        self.assertTrue(any('named meals need' in e for e in content_failures(p)))
        p['dining_plan'][0]['flexible'] = True
        self.assertEqual(content_failures(p), [])

    def test_flexible_flag_does_not_bypass_named_restaurant(self):
        p = self.profile(); p['dining_plan'][0].update(date='11月8日', flexible=True)
        self.assertTrue(any('not scheduled' in e for e in content_failures(p)))

    def test_source_requires_real_url_shape_and_precision(self):
        r = {'source_identity_bound': True, 'source_page': 'https:', 'source_identity_note': 'Long enough but no actual source host.'}
        self.assertFalse(identity_documented(r))
        p = self.profile(); p['places'][0]['coordinate_source']['precision'] = 'verified'
        self.assertTrue(any('precision must' in e for e in content_failures(p)))


if __name__ == '__main__':
    unittest.main()
