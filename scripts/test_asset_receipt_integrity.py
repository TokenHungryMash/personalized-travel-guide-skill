"""Regression: altered duplicate photos and invented/stale receipts cannot pass."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class AssetIntegrityTest(unittest.TestCase):
    def run_check(self, duplicate=False, stale=False, wrong_source=False, cover=False, shared=False, machine_only=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Synthetic test fixtures only, never destination media.
            base = Image.new("RGB", (600, 400))
            base.putdata([((x * 3 + y) % 256, (y * 2) % 256, x % 256)
                          for y in range(400) for x in range(600)])
            base.save(root / "a.jpg", quality=93)
            if duplicate or cover:
                other = Image.open(root / "a.jpg").convert("RGB")
                other.putpixel((10, 10), (0, 0, 0))
                other.save(root / "b.jpg", quality=90)
            else:
                base.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(root / "b.jpg")
            assets, receipts = [], []
            for name in ("a", "b"):
                pid = "__cover__" if cover and name == "b" else name
                row = dict(file=name + ".jpg", place_id=pid,
                           source_page="https://example.org/" + name,
                           download_url="https://example.org/" + name + ".jpg",
                           source_type="official", media_class="official_photo",
                           original_media_class="official_photo", visual_subject_type="place_exterior",
                           source_identity_bound=True, source_identity_note="Synthetic fixture identity observation for this test image")
                assets.append(row)
                receipts.append(dict(row, status="ok", sha256=hashlib.sha256((root / row['file']).read_bytes()).hexdigest()))
            if stale:
                receipts[0]['sha256'] = '0' * 64
            if wrong_source:
                receipts[0]['download_url'] = 'https://example.org/unrelated.jpg'
            profile = {'trip': {'quality_mode': 'standard'}, 'places': [{'id': 'a'}, {'id': 'b'}]}
            if shared:
                profile['places'] = [dict(id='a',type='sight',latitude=35,longitude=139),
                                     dict(id='b',type='experience',latitude=35,longitude=139,same_place_as='a')]
                for field in ('file','source_page','download_url'):
                    assets[1][field] = assets[0][field]
                    receipts[1][field] = receipts[0][field]
                receipts[1]['sha256'] = receipts[0]['sha256']
            if cover:
                profile['cover'] = {'image': 'b.jpg'}
            for file, data in [('profile.json', profile), ('manifest.json', {'assets': assets}), ('asset-fetch-report.json', receipts)]:
                (root / file).write_text(json.dumps(data), encoding='utf8')
            proc = subprocess.run([sys.executable, str(Path(__file__).with_name('verify_assets.py')),
                                   str(root / 'profile.json'), str(root / 'manifest.json'), str(root), *(['--machine-only'] if machine_only else [])], capture_output=True, text=True, encoding='utf-8')
            return proc.returncode, proc.stdout

    def test_distinct_images_pass(self):
        self.assertEqual(self.run_check()[0], 0)

    def test_full_mode_rejects_unreviewed_receipts(self):
        code, output = self.run_check(machine_only=False)
        self.assertEqual(code, 2, output)
        self.assertIn('visual', output.lower())

    def test_reencoded_pixel_edit_rejected(self):
        code, output = self.run_check(duplicate=True)
        self.assertEqual(code, 2)
        self.assertIn('near-duplicate image content', output)

    def test_stale_receipt_rejected(self):
        code, output = self.run_check(stale=True)
        self.assertEqual(code, 2)
        self.assertIn('receipt hash missing or stale', output)

    def test_substituted_url_rejected(self):
        code, output = self.run_check(wrong_source=True)
        self.assertEqual(code, 2)
        self.assertIn('receipt download_url differs', output)

    def test_cover_reuse_allowed(self):
        self.assertEqual(self.run_check(cover=True)[0], 0)

    def test_shared_file_retains_separate_place_receipts(self):
        code, output = self.run_check(shared=True)
        self.assertEqual(code, 0, output)


if __name__ == '__main__':
    unittest.main()
