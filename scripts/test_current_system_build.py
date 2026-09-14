"""Offline regression coverage for fresh UI selection and route build reuse."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from _current_system_adapter import runtime_bindings, trip_days
from _manual_qa import build_fingerprint
from _build_state import evaluation_fingerprint
from prepare_osm_route_tiles import file_hash, index_paths, required_tiles, tiles_cached, world
from render_profile import render


def profile():
    places = [{'id': str(i), 'display_name': f'测试地点 {i}', 'map_query': f'Place {i} Test City',
               'latitude': 35+i*.001, 'longitude': 139+i*.001} for i in range(8)]
    return {'destination': 'Test City', 'display_name': '测试城', 'year': 2026,
            'handbook_id': 'isolated-fixture',
            'trip': {'start_date': 'pending', 'end_date': 'pending'},
            'cover': {'image': 'assets/new.jpg', 'title': '街角', 'kicker': 'TEST', 'summary': '新资料'},
            'module_groups': {'language': {'language_code': 'ja-JP'}, 'travel_notes': []},
            'places': places,
            'itinerary': [{'stops': [{'place_id': str(i), 'arrival_time': '09:00',
                'transport_mode': 'walk', 'transfer_minutes': i, 'distance_km': i*.1}
                for i in range(n)]} for n in (3, 5, 8)]}


class CurrentBuildTests(unittest.TestCase):
    def test_route_transfer_and_note_agree_across_surfaces(self):
        from build_render_bindings import route
        data=profile()
        day=data['itinerary'][0]
        day.update(theme='路线',date='2026-11-03',periods={'morning':'','afternoon':'','evening':''})
        day['stops'][0]['transfer_minutes']=0
        day['stops'][1].update(transport_mode='train',transfer_minutes=37,distance_basis='coordinate_straight_line')
        day['stops'][2].update(transport_mode='walk',transfer_minutes=12)
        data['itinerary']=[day]
        data['trip']['days']=1
        html=route(data,{p['id']:p for p in data['places']})
        self.assertIn('<span>轨道交通</span><b>37 分钟</b>',html)
        self.assertIn('<span>步行</span><b>12 分钟</b>',html)
        self.assertEqual(html.count('距离为坐标间直线估算'),1)
        rendered=trip_days(data)[0]
        self.assertEqual(rendered['stops'][0]['transport_mode'],'轨道交通')
        self.assertEqual(rendered['stops'][0]['transfer_minutes'],37)
        self.assertEqual(day['stops'][1]['transport_mode'],'train')
        runtimes=runtime_bindings(data)
        # Both caption and explanatory copy are generated, not patched into a trip.
        text=str(runtimes)
        self.assertIn('摄影穿搭</button>',text)
        self.assertIn('routeNote(d)',text)

    def test_compiled_default_phase_does_not_duplicate_route_heading(self):
        from compile_destination_profile import normalize_journey_phases
        from build_render_bindings import route
        data = {'trip': {'days': 2}, 'itinerary': [
            {'theme': name, 'stops': [], 'periods': {'morning': '', 'afternoon': '', 'evening': ''}}
            for name in ('首日', '次日')]}
        normalize_journey_phases(data)
        html = route(data, {})
        self.assertEqual(html.count('2 天行程'), 1)
        self.assertEqual(html.count('class="day"'), 2)
        data['journey_phases'] = [{'title': '前半程', 'day_numbers': [1]}, {'title': '后半程', 'day_numbers': [2]}]
        html = route(data, {})
        self.assertIn('<h3>前半程</h3>', html)
        self.assertIn('<h3>后半程</h3>', html)
        self.assertEqual(html.count('class="day"'), 2)

    def test_status_tracks_current_code_and_output_media_not_reference_photos(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            skill = base / 'skill'
            code = skill / 'assets/current-system/product/runtime.js'
            photo = skill / 'assets/current-system/product/media/reference.jpg'
            photo.parent.mkdir(parents=True)
            code.write_text('first')
            photo.write_bytes(b'old photo')
            root = base / 'workbench'
            root.mkdir()
            with patch('_build_state.__file__', str(skill / 'scripts/_build_state.py')):
                before = evaluation_fingerprint(root)
                photo.write_bytes(b'different irrelevant reference')
                self.assertEqual(before, evaluation_fingerprint(root))
                code.write_text('changed runtime')
                self.assertNotEqual(before, evaluation_fingerprint(root))
                before = evaluation_fingerprint(root)
                (root / 'actual.jpg').write_bytes(b'new output image')
                self.assertNotEqual(before, evaluation_fingerprint(root))

    def test_default_and_explicit_legacy_select_same_installer_and_bindings(self):
        for system in (None, 'canonical'):
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                data = profile()
                if system:
                    data['ui_system'] = system
                source = root / 'profile.json'
                source.write_text(json.dumps(data), encoding='utf-8')
                with patch('render_profile.subprocess.run') as run:
                    render(source, root / 'output')
                commands = [call.args[0] for call in run.call_args_list]
                self.assertEqual(Path(commands[0][1]).name, 'validate_destination_data.py')
                self.assertIn(system or 'current-system', commands[2])
                self.assertEqual(Path(commands[-1][1]).name, 'render_destination.py')

    def test_failed_validation_does_not_install(self):
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / 'profile.json'
            source.write_text(json.dumps(profile()), encoding='utf-8')
            with patch('render_profile.subprocess.run', side_effect=subprocess.CalledProcessError(2, 'validate')) as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    render(source, Path(raw) / 'output')
                self.assertEqual(run.call_count, 1)

    def test_payload_transfer_direction_panel_split_and_fresh_identity(self):
        data = profile()
        original = copy.deepcopy(data)
        days = trip_days(data)
        self.assertEqual(days[0]['stops'][0]['transfer_minutes'], 1)
        self.assertIsNone(days[0]['stops'][-1]['transfer_minutes'])
        bindings = {r['path']: r['content'] for r in runtime_bindings(data)}
        route_runtime = bindings['trip-route-maps.js']
        self.assertIn('tiles.openfreemap.org/styles/liberty', route_runtime)
        self.assertIn('route list remains available without network or WebGL', route_runtime)
        for text in bindings.values():
            for stale in ('Ubud', 'Seminyak', 'Kebun Bistro', '乌布', '水明漾'):
                self.assertNotIn(stale, text)
        self.assertIn('ja-JP', bindings['audit-itinerary-data.js'])
        self.assertIn('"currency": "JPY"', bindings['audit-itinerary-data.js'])
        self.assertIn('<option>JPY</option>', bindings['shared-ledger.js'])
        self.assertIn('api.frankfurter.dev/v2/rate/', bindings['shared-ledger.js'])
        self.assertIn('isolated-fixture', bindings['trip-mode.js'])
        self.assertEqual(data, original)

    def test_projection_index_matches_original_geometry(self):
        ways = [{'tags': {'highway': 'primary'}, 'geometry': [
            {'lon': 139+i*.0001, 'lat': 35+i*.0001} for i in range(15)]}]
        tiles, _ = required_tiles(trip_days(profile()))
        indexed = index_paths(ways, tiles)
        for (z, tx, ty), actual in indexed.items():
            pts = [(world(g['lon'], g['lat'], z)[0]-tx*256,
                    world(g['lon'], g['lat'], z)[1]-ty*256) for g in ways[0]['geometry']]
            xs, ys = zip(*pts)
            visible = not (max(xs)<-20 or min(xs)>276 or max(ys)<-20 or min(ys)>276)
            self.assertEqual(actual, [(ways[0]['tags'], pts)] if visible else [])

    def test_projection_calls_scale_with_zooms_not_tile_count(self):
        tiles, _ = required_tiles(trip_days(profile()))
        ways = [{'geometry': [{'lon': 139, 'lat': 35}, {'lon': 139.01, 'lat': 35.01}]}]
        with patch('prepare_osm_route_tiles.world', wraps=world) as project:
            index_paths(ways, tiles)
        self.assertEqual(project.call_count, 2*len({z for z, _, _ in tiles}))
        self.assertGreater(len(tiles), len({z for z, _, _ in tiles}))

    def test_missing_coordinate_rejected_before_network(self):
        days = trip_days(profile())
        days[0]['stops'][0]['latitude'] = None
        with self.assertRaisesRegex(ValueError, 'verified coordinates'):
            required_tiles(days)

    def test_cache_rejects_changed_tile_and_signature(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tile = root / 'tiles/1/0/0.png'
            tile.parent.mkdir(parents=True)
            tile.write_bytes(b'fixture')
            (root / 'SOURCES.md').write_text('source')
            (root / 'tile-cache.json').write_text(json.dumps({'signature': 'one', 'files': {
                'tiles/1/0/0.png': file_hash(tile)}}))
            self.assertTrue(tiles_cached(root, 'one', {(1, 0, 0)}))
            self.assertFalse(tiles_cached(root, 'two', {(1, 0, 0)}))
            tile.write_bytes(b'changed')
            self.assertFalse(tiles_cached(root, 'one', {(1, 0, 0)}))

    def test_manual_qa_invalidated_when_embedded_map_changes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / 'media/routes/day-1.svg'
            target.parent.mkdir(parents=True)
            target.write_text('first')
            before = build_fingerprint(root)
            target.write_text('changed')
            self.assertNotEqual(before, build_fingerprint(root))


if __name__ == '__main__':
    unittest.main()
