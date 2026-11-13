"""Exercise offline image compression without touching a destination workbench."""
from pathlib import Path
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import random
import re
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('offline_images', ROOT / 'assets/destination-reference/offline_images.py')
images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(images)


def decoded(markup):
    return [base64.b64decode(value) for value in re.findall(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', markup)]


class OfflineImageTests(unittest.TestCase):
    def test_pool_shares_payload_between_static_images_mobile_source_and_guide(self):
        uri='data:image/png;base64,'+base64.b64encode(b'fixture-image').decode()
        other='data:image/webp;base64,'+base64.b64encode(b'another-image').decode()
        data={'images':{'place':uri},'placePhotos':{'place':{'src':uri,'mobileSrc':other}},'maps':{'d1':{'src':other}}}
        markup='<html><body><img id="cover" src="'+uri+'"><picture><source srcset="'+other+'"><img src="'+uri+'"></picture><script id="guide-data" type="application/json">'+json.dumps(data)+'</script><script>/*application*/</script></body></html>'
        result=images.pool_images(markup,{uri,other})
        self.assertEqual(result.count(uri),1);self.assertEqual(result.count(other),1)
        self.assertIn('<img id="cover" src="'+uri+'"',result)
        self.assertIn('data-offline-src=',result)
        self.assertLess(result.index('const pool ='),result.index('/*application*/'))
        text=re.search(r'<script id="guide-data"[^>]*>(.*?)</script>',result,re.S)[1]
        self.assertTrue(json.loads(text)['images']['place'].startswith('offline-image:'))
    def test_pool_embeds_json_only_image_once_without_static_anchor(self):
        uri='data:image/png;base64,aW1hZ2U='
        markup='<script id="guide-data" type="application/json">'+json.dumps({'a':uri,'b':uri})+'</script>'
        result=images.pool_images(markup,{uri})
        self.assertEqual(result.count(uri),1)
        self.assertIn('id="offline-image-pool"',result)
    def test_two_source_attributes_have_independent_static_anchors(self):
        uri='data:image/png;base64,aW1hZ2U='
        other='data:image/png;base64,b3RoZXI='
        result=images.pool_images('<img src="'+uri+'" srcset="'+other+'"><script id="guide-data">'+json.dumps({'a':uri,'b':other})+'</script>',{uri,other})
        self.assertIn('data-offline-asset-src=',result)
        self.assertIn('data-offline-asset-srcset=',result)
        self.assertEqual(result.count(uri),1);self.assertEqual(result.count(other),1)
    def test_unused_and_unique_images_do_not_get_a_pool(self):
        uri='data:image/png;base64,aW1hZ2U='
        markup='<img src="'+uri+'">'
        self.assertEqual(images.pool_images(markup,{uri}),markup)
    def test_roles_source_preservation_and_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'media').mkdir()
            (root / 'maps').mkdir()
            noise = Image.frombytes('RGB', (2000, 1200), random.Random(3).randbytes(2000 * 1200 * 3))
            noise.save(root / 'media/large.jpg', quality=95)
            (root / 'media/copy.jpg').write_bytes((root / 'media/large.jpg').read_bytes())
            noise.resize((1700, 1100)).save(root / 'maps/map.png')
            alpha = Image.new('RGBA', (1000, 600), (20, 30, 40, 0))
            alpha.paste((40, 80, 180, 180), (50, 50, 900, 550))
            alpha.save(root / 'media/alpha.png')
            before = {path: hashlib.sha256(path.read_bytes()).digest() for path in root.rglob('*') if path.is_file()}
            markup = ('<img src="media/large.jpg"><img src="media/copy.jpg">'
                      '<img src="media/alpha.png"><img src="maps/map.png">'
                      '<script type="application/json">{"photo":"media/large.jpg"}</script>'
                      '<a href="https://example.org/media/large.jpg">source</a>')
            edition = {'cover': 'hero', 'offlineImages': {'coverMaxEdge': 1800, 'spreadMaxEdge': 1600, 'deduplicate':False}}
            editorial = {'hero': {'src': 'media/large.jpg'}, 'second': {'src': 'media/copy.jpg'}}
            with patch.object(images, 'encode_image', wraps=images.encode_image) as convert:
                result, report = images.inline_images(root, markup, edition,
                    {'alpha': {'src': 'media/alpha.png'}}, editorial, {'overview': {'src': 'maps/map.png'}})
                self.assertEqual(convert.call_count, 4)  # Different role limits require distinct variants.
            self.assertIn('https://example.org/media/large.jpg', result)
            output = decoded(result)
            self.assertEqual(Image.open(io.BytesIO(output[0])).size, (1800, 1080))
            self.assertEqual(Image.open(io.BytesIO(output[1])).size, (1600, 960))
            self.assertEqual(Image.open(io.BytesIO(output[2])).size, (900, 540))
            self.assertIn('A', Image.open(io.BytesIO(output[2])).getbands())
            self.assertEqual(output[3], (root / 'maps/map.png').read_bytes())
            self.assertEqual(output[0], output[4])
            self.assertLess(len(output[0]), (root / 'media/large.jpg').stat().st_size)
            self.assertGreater(report['repeatedImageBytes'], 0)
            self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).digest() for path in before})
            with patch.object(images, 'encode_image', wraps=images.encode_image) as convert:
                _, cached = images.inline_images(root, markup, {}, {}, editorial, {'overview': {'src': 'maps/map.png'}})
                self.assertEqual(convert.call_count, 3)
                self.assertEqual(sum(row['cacheHit'] for row in cached['images']), 1)

    def test_animation_and_orientation(self):
        first = Image.new('RGB', (60, 40), 'red')
        second = Image.new('RGB', (60, 40), 'blue')
        for image_format in ['GIF', 'PNG', 'WEBP']:
            with self.subTest(animation=image_format):
                animated = io.BytesIO()
                first.save(animated, format=image_format, save_all=True, append_images=[second], duration=100, loop=0)
                result = images.encode_image(animated.getvalue(), 30, 84)
                self.assertEqual(result[0], animated.getvalue())
                self.assertEqual(result[4], 'original-animation')
        exif = first.getexif()
        exif[274] = 6
        rotated = io.BytesIO()
        first.save(rotated, format='JPEG', exif=exif)
        result = images.encode_image(rotated.getvalue(), 1800, 84)
        self.assertEqual(result[3], (40, 60))
        small = io.BytesIO()
        first.resize((12, 8)).save(small, format='PNG')
        result = images.encode_image(small.getvalue(), 900, 84)
        self.assertEqual(result[3], (12, 8))

    def test_mpo_camera_photo_uses_primary_frame(self):
        primary = Image.new('RGB', (640, 480), 'red')
        auxiliary = Image.new('RGB', (640, 480), 'blue')
        camera_photo = io.BytesIO()
        primary.save(camera_photo, format='MPO', save_all=True, append_images=[auxiliary])
        payload = camera_photo.getvalue()
        with Image.open(io.BytesIO(payload)) as source:
            self.assertEqual(source.format, 'MPO')
            self.assertEqual(source.n_frames, 2)
        result = images.encode_image(payload, 320, 84)
        self.assertEqual(result[1], 'image/webp')
        self.assertEqual(result[2:4], ((640, 480), (320, 240)))
        self.assertEqual(result[4], 'webp')
        with Image.open(io.BytesIO(result[0])) as output:
            self.assertEqual(getattr(output, 'n_frames', 1), 1)
            red, green, blue = output.convert('RGB').getpixel((160, 120))
            self.assertGreater(red, 200)
            self.assertLess(blue, 40)
        self.assertEqual(images.encode_image(payload, 320, 84, preserve=True)[0], payload)

    def test_config_threshold_and_small_transparent_images(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'media').mkdir()
            payload = io.BytesIO()
            Image.new('RGBA', (20, 10), (255, 0, 0, 127)).save(payload, format='PNG')
            path = root / 'media/small.png'
            path.write_bytes(payload.getvalue())
            markup = '<img src="media/small.png">'
            config = {'offlineImages': {'placeMaxEdge': 10, 'warnMiB': 0.00001}}
            result, report = images.inline_images(root, markup, config, {'p': {'src': 'media/small.png'}}, {}, {})
            image = Image.open(io.BytesIO(decoded(result)[0]))
            self.assertEqual(image.size, (10, 5))
            self.assertEqual(image.convert('RGBA').getpixel((3, 2))[3], 127)
            artifact = root / 'trip.html'
            artifact.write_text(result, encoding='utf8')
            log = io.StringIO()
            with contextlib.redirect_stdout(log):
                report = images.write_size_report(root, artifact, report, 'test-build')
            self.assertTrue(report['overThreshold'])
            self.assertIn('WARNING', log.getvalue())
            self.assertEqual(json.loads((root / 'qa-size/report.json').read_text())['sha256'], hashlib.sha256(artifact.read_bytes()).hexdigest())
            with self.assertRaises(ValueError):
                images.settings({'offlineImages': {'warnMiB': float('nan')}})


if __name__ == '__main__':
    unittest.main()
