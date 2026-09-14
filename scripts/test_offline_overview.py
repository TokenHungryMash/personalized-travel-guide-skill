import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from _offline_overview import verify_evidence
from _route_screenshots import day_fingerprint, verify_captures, screenshots_html
from import_route_overviews import import_overviews

class OverviewTests(unittest.TestCase):
    def test_renderer_preserves_binding_and_rejects_empty_background(self):
        from render_route_overview import render
        font = Path('C:/Windows/Fonts/msyh.ttc')
        if not font.exists(): self.skipTest('CJK test font not installed')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            places=[dict(id='a',display_name='西侧地点',latitude=35,longitude=139),
                    dict(id='b',display_name='东侧地点',latitude=35.002,longitude=139.004)]
            day=dict(stops=[dict(place_id='a'),dict(place_id='b')])
            profile=root/'profile.json'
            profile.write_text(json.dumps(dict(display_name='合成测试',places=places,itinerary=[day])))
            osm=root/'map.osm'
            osm.write_text('<osm><node id="1" lat="35" lon="139.001"/><node id="2" lat="35.002" lon="139.003"/><way id="1"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="river"/></way></osm>')
            result=render(profile,osm,font,1,root/'out')
            self.assertFalse(result['markers_displaced'])
            self.assertFalse(result['visual_reviewed'])
            self.assertEqual(result['capture_fingerprint'],day_fingerprint(day,{p['id']:p for p in places}))
            self.assertTrue(Path(result['image']).is_file())
            osm.write_text('<osm/>')
            with self.assertRaisesRegex(ValueError,'no relevant geographic'):
                render(profile,osm,font,1,root/'empty')

    def test_failure_gate_import_and_stale_route(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'research').mkdir()
            place = dict(id='station', display_name='测试站', latitude=35, longitude=139)
            day = dict(date='2026-11-04', stops=[dict(place_id='station')])
            profile = dict(map_delivery='screenshots', places=[place], itinerary=[day])
            (root/'destination-profile.json').write_text(json.dumps(profile))
            (root/'research/itinerary.json').write_text(json.dumps([day]))
            Image.new('RGB', (1200,1100), 'white').save(root/'sample.png')
            (root/'background.json').write_text('{"type":"test geometry"}')
            (root/'failure.log').write_text('Synthetic capture timeout fixture')
            sha = lambda name: hashlib.sha256((root/name).read_bytes()).hexdigest()
            row = dict(day=1, image='sample.png', sha256=sha('sample.png'),
                       capture_fingerprint=day_fingerprint(day, {'station':place}),
                       visual_reviewed=True, review_note='Synthetic review fixture',
                       background_file='background.json', background_sha256=sha('background.json'),
                       source_url='https://example.org/fixture', attribution='Test geographic data')
            with self.assertRaisesRegex(ValueError, 'must be attempted'):
                verify_evidence(root, row)
            row['attempts'] = [dict(status='failed', reason='timeout', checked_at='2026-09-14',
                                   log_file='failure.log', log_sha256=sha('failure.log'))]
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps(dict(maps=[row])))
            import_overviews(root, manifest)
            profile['itinerary'] = json.loads((root/'research/itinerary.json').read_text(encoding='utf-8'))
            self.assertEqual(verify_captures(root, profile), [])
            html = screenshots_html(profile['itinerary'][0])
            self.assertIn('简化地理总览', html)
            self.assertNotIn('真实街道底图截图', html)
            profile['places'][0]['latitude'] += .1
            self.assertTrue(any('route changed' in x for x in verify_captures(root, profile)))
            (root/'failure.log').write_text('changed')
            self.assertTrue(any('stale/empty' in x for x in verify_captures(root, profile)))

if __name__ == '__main__':
    unittest.main()
