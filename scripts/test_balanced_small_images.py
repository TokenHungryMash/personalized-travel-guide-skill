import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from fetch_declared_assets import contain_on_white, fetch

class SmallImages(unittest.TestCase):

    def test_native_bytes_and_dimensions_are_preserved(self):
        for size in ((256, 256), (400, 400), (1200, 800)):
            buffer = io.BytesIO()
            Image.new('RGB', size, 'red').save(buffer, format='PNG')
            payload = buffer.getvalue()
            result = contain_on_white(payload, Path('image.png'))
            self.assertEqual(result, (payload, *size, None))

    def test_cached_small_image_avoids_download(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'small.png'
            Image.new('RGB', (256, 256), 'red').save(target)
            image = {'file': 'small.png', 'download_url': 'https://example.com/small.png', 'source_page': 'https://example.com/place'}
            image['_fetch_receipt'] = {**image, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
            with patch('fetch_declared_assets.SAFE_OPENER.open', side_effect=AssertionError('must not download')):
                row, error, downloaded = fetch(('venue', image, target), 0, False, 'standard')
            self.assertEqual(row['status'], 'cached')
            self.assertIsNone(error)
            self.assertFalse(downloaded)

    def test_cached_oversized_image_is_optimized_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'large.jpg'
            Image.new('RGB', (3200, 2400), 'blue').save(target, format='JPEG', quality=95)
            old_size = target.stat().st_size
            image = {'file': 'large.jpg', 'download_url': 'https://example.com/large.jpg', 'source_page': 'https://example.com/place'}
            image['_fetch_receipt'] = {**image, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
            with patch('fetch_declared_assets.SAFE_OPENER.open', side_effect=AssertionError('must not download')):
                row, error, downloaded = fetch(('venue', image, target), 0, False, 'standard')
            self.assertEqual(row['status'], 'cached')
            self.assertTrue(row['delivery_resized'])
            self.assertLess(target.stat().st_size, old_size)
            self.assertEqual(row['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertIsNone(error)
            self.assertFalse(downloaded)

    def test_oversized_photo_becomes_bounded_delivery_derivative(self):
        buffer = io.BytesIO()
        Image.new('RGB', (3200, 2400), 'blue').save(buffer, format='JPEG', quality=95)
        result = contain_on_white(buffer.getvalue(), Path('image.jpg'))
        self.assertLessEqual(max(result[1:3]), 1600)
        self.assertTrue(result[3]['delivery_resized'])
        self.assertEqual(result[3]['source_dimensions'], [3200, 2400])
        with Image.open(io.BytesIO(result[0])) as image:
            self.assertEqual(image.size, result[1:3])
if __name__ == '__main__':
    unittest.main()
