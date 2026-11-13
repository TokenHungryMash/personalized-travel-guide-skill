"""Truncated images must not inflate verified photo coverage."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from audit_directory import audit, TEMPLATE


class DirectoryImages(unittest.TestCase):
    def test_full_decode_required_for_coverage(self):
        guide = json.loads((TEMPLATE / 'content.json').read_text(encoding='utf8'))
        pid = guide['places'][0]['id']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo = {'src': 'photo.jpg', 'page': 'https://commons.wikimedia.org/', 'caption': 'Verified test fixture',
                     'subjectPlaceId': pid, 'role': 'venue', 'reviewed': True}
            plan = {'targetRange': [0, 100], 'photoExceptions': {p['id']: 'Test fixture has no photo' for p in guide['places'] if p['id'] != pid}}
            for name, data in [('content.json', guide), ('place-photos.json', {pid: photo}), ('directory-plan.json', plan)]:
                (root / name).write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
            buffer = io.BytesIO()
            Image.new('RGB', (200, 200), 'red').save(buffer, 'JPEG')
            (root / 'photo.jpg').write_bytes(buffer.getvalue()[:-2])
            report = audit(root)
            self.assertIn('invalid image', '\n'.join(report['errors']))
            self.assertEqual(report['photos'], 0)
            (root / 'photo.jpg').write_bytes(buffer.getvalue())
            report = audit(root)
            self.assertEqual(report['errors'], [])
            self.assertEqual(report['photos'], 1)


if __name__ == '__main__':
    unittest.main()
