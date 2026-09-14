"""Synthetic fixtures test packaging integrity, not real-map/browser acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from PIL import Image
from route_screenshots import prepare


class PhonePackTest(unittest.TestCase):
    def test_offline_payload_and_rejection_of_changed_or_unreviewed_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'qa' / 'route-capture'
            folder.mkdir(parents=True)
            Image.new('RGB', (1400, 1100), 'white').save(folder / 'one.png')
            digest = hashlib.sha256((folder / 'one.png').read_bytes()).hexdigest()
            name = '完整地点名称 <测试> & long place name'
            (folder / 'one.html').write_text('<script>window.CAPTURE_INPUT=' + json.dumps({'stops': [{'number': 1, 'name': name}]}) + ';</script>', encoding='utf-8')
            (folder / 'capture-plan.json').write_text(json.dumps({'tasks': [{'png': 'one.png', 'page': 'one.html', 'caption': '测试', 'stop_numbers': [1]}]}), encoding='utf-8')
            row = {'png': 'one.png', 'status': 'captured', 'sha256': digest, 'visual_reviewed': True, 'review_note': 'Synthetic unit-test fixture only', 'observed_state': {'status': 'ready', 'tiles_loaded': True, 'labels': 1}}
            def run():
                (folder / 'capture-report.json').write_text(json.dumps({'captures': [row]}), encoding='utf-8')
                return subprocess.run(['node', str(Path(__file__).with_name('pack_phone_maps.cjs')), str(root)], capture_output=True)
            self.assertEqual(run().returncode, 0)
            output = root / '手机离线连线地图.html'
            html = output.read_text(encoding='utf-8')
            self.assertIn('data:image/png;base64,', html)
            self.assertIn('完整地点名称 &lt;测试&gt; &amp;', html)
            self.assertNotIn('src="https:', html)
            output.unlink()
            row['visual_reviewed'] = False
            self.assertEqual(run().returncode, 2)
            self.assertFalse(output.exists())
            row['visual_reviewed'] = True
            row['sha256'] = 'tampered'
            self.assertEqual(run().returncode, 2)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
