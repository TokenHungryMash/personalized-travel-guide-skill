import hashlib
'Product HTML fixtures, geographic-fallback regression and optional live checks.'
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
from PIL import Image
from probe_official_page import parse_metadata, PublicRedirect, validate_url
from research_image_candidates import collect
TORIMON = '<title>商品 | 博多通りもん 明月堂</title>\n<img src="/logo_meigetsudo.svg" alt="明月堂">\n<a href="/ic/torimon"><img src="/cat_torimon.jpg" alt="博多通りもん">博多通りもん</a>\n<img src="/cat_other.jpg" alt="別の商品">'
MENBEI = '<title>めんべいご案内ページ | 福太郎</title>\n<img src="/globalnavi-03-off.gif" alt="辛子めんたい風味めんべい">\n<img src="/banner-07.gif" alt="バスケットボールチーム 福太郎めんべい">\n<img src="/logo-01.gif" alt="山口油屋福太郎">\n<img src="/img/menbei02_top.jpg" alt="">'

class ProductImages(unittest.TestCase):

    def test_promotional_hero_does_not_hide_exact_product_photo(self):
        page={'status':'ok','title':'Exact Product','images':[
            {'url':'https://example.org/mainimg.jpg','context':'Exact Product'},
            {'url':'https://example.org/box.jpg','context':'Exact Product'}]}
        with patch('research_image_candidates.probe',return_value=page):
            result=collect({'id':'gift','type':'souvenir','display_name':'Exact Product','official_url':'https://example.org/item'},1)
        self.assertTrue(result['candidates'][0]['image_url'].endswith('/box.jpg'))
        self.assertFalse(result['candidates'][0]['subject_verified'])


    def test_generated_tasks_require_mainstream_selection_and_attempted_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('init_research_workspace.py')), tmp, '--destination', 'Fixture', '--country', 'Fixture', '--days', '3'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for pack, term in [('places-core', 'mainstream'), ('places-food', 'well-known'), ('places-shopping', 'mainstream')]:
                task = json.loads((Path(tmp) / 'research' / 'tasks' / (pack + '.json')).read_text(encoding='utf-8'))
                self.assertIn(term, json.dumps(task))
                self.assertIn('never skip lookup', task['souvenir_media'])
                self.assertIn('candidate-ledger.json', task['souvenir_media'])

    def test_empty_official_probe_requires_alternate_not_immediate_text_only(self):
        with patch('research_image_candidates.probe', return_value={'status': 'no_image', 'images': [], 'product_links': []}):
            result = collect({'id': 'gift', 'type': 'souvenir', 'display_name': 'Exact Product', 'official_url': 'https://example.org/item'}, 2)
        self.assertEqual(result['product_media_status'], 'product_media_gap')
        self.assertIn('Inspect one reputable exact-product', result['next_action'])
        self.assertIn('has not searched that alternate', result['next_action'])
        self.assertIn('candidate-ledger.json', result['next_action'])

    def test_missing_product_input_is_not_exhausted_search(self):
        with patch('research_image_candidates.probe') as probe:
            result = collect({'id': 'gift', 'type': 'souvenir', 'display_name': 'Exact Product'}, 2)
        self.assertEqual(result['product_media_status'], 'needs_product_input')
        probe.assert_not_called()

    def test_real_page_structures_exclude_navigation_and_other_products(self):
        for name, html, suffix, selected in (('博多通りもん', TORIMON, 'items/', 'cat_torimon.jpg'), ('めんべい', MENBEI, 'menbei02/', 'menbei02_top.jpg')):
            url = 'https://example.org/' + suffix
            parsed = parse_metadata(html.encode(), url, product_name=name)
            with patch('research_image_candidates.probe', return_value=parsed), patch('research_image_candidates.wikidata') as wd, patch('research_image_candidates.commons_geo') as geo:
                result = collect({'id': 'product', 'display_name': name, 'place_kind': 'souvenir sweet', 'official_url': url}, 2)
            self.assertEqual(len(result['candidates']), 1)
            candidate = result['candidates'][0]
            self.assertTrue(candidate['image_url'].endswith(selected))
            self.assertEqual(candidate['visual_subject_type'], 'product')
            self.assertFalse(candidate['subject_verified'])
            wd.assert_not_called()
            geo.assert_not_called()

    def test_jsonld_lazy_srcset_and_css(self):
        html = '<script type="application/ld+json">{"@graph":[{"@type":"Product","name":"Exact Product","image":{"url":"/ld.jpg"}}]}</script>\n<img alt="Exact Product" data-src="/lazy.jpg" src="data:placeholder">\n<img alt="Exact Product" data-original="/original.jpg">\n<img alt="Exact Product" srcset="/small.jpg 320w, /large.jpg 1600w">\n<picture><source srcset="/picture.jpg 1600w"><img alt="Exact Product" src="data:placeholder"></picture>\n<div data-product-name="Exact Product" style="background-image: url(\'/background.jpg\')"></div>'
        parsed = parse_metadata(html.encode(), 'https://example.org/item', product_name='Exact Product')
        urls = {image['url'] for image in parsed['images']}
        self.assertEqual(urls, {'https://example.org/' + name for name in ('ld.jpg', 'lazy.jpg', 'original.jpg', 'large.jpg', 'picture.jpg', 'background.jpg')})

    def test_same_site_product_link_is_bounded(self):
        first = parse_metadata(b'<a href="/item">Exact Product</a><a href="https://other.example/item">Exact Product</a>', 'https://example.org/list', product_name='Exact Product')
        second = parse_metadata(b'<img alt="Exact Product" data-src="/item.jpg">', 'https://example.org/item', product_name='Exact Product')
        with patch('research_image_candidates.probe', side_effect=[first, second]) as probe:
            result = collect({'id': 'p', 'type': 'souvenir', 'display_name': 'Exact Product', 'official_url': 'https://example.org/list'}, 2)
            self.assertEqual(probe.call_count, 2)
            self.assertEqual(result['candidates'][0]['source_page'], 'https://example.org/item')

    def test_asset_gate_rejects_street_accepts_product_and_official_brand(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (600, 400), 'white').save(root / 'asset.png')
            (root / 'profile.json').write_text(json.dumps({'trip': {'quality_mode': 'standard'}, 'places': [{'id': 'p', 'type': 'souvenir'}]}))
            (root / 'asset-fetch-report.json').write_text(json.dumps([{'file': 'asset.png', 'status': 'ok'}]))
            asset = {'place_id': 'p', 'file': 'asset.png', 'media_class': 'official_photo', 'source_type': 'official', 'source_page': 'https://example.org/item', 'download_url': 'https://example.org/item.png', 'source_identity_bound': True, 'source_identity_note': 'Synthetic fixture identity observation for the declared subject'}
            (root / 'asset-fetch-report.json').write_text(json.dumps([{**asset, 'status': 'ok', 'sha256': hashlib.sha256((root / 'asset.png').read_bytes()).hexdigest()}]))
            for subject, code in (('landscape', 2), ('product', 0), ('official_logo', 0)):
                value = {**asset, 'visual_subject_type': subject}
                if subject == 'official_logo':
                    value['media_class'] = 'official_brand_asset'
                    value['original_media_class'] = 'official_brand_asset'
                (root / 'manifest.json').write_text(json.dumps({'assets': [value]}))
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('verify_assets.py')), str(root / 'profile.json'), str(root / 'manifest.json'), str(root), '--machine-only'], capture_output=True)
                self.assertEqual(result.returncode, code, result.stdout)

def live():
    rows = [{'id': 'torimon', 'display_name': '博多通りもん', 'brand_name': '明月堂', 'place_kind': 'souvenir sweet', 'official_url': 'https://www.meigetsudo.co.jp/info/category/items/'}, {'id': 'menbei', 'display_name': 'めんべい', 'brand_name': '福太郎', 'place_kind': 'souvenir cracker', 'official_url': 'https://www.fukutaro.co.jp/menbei02/'}]
    for row in rows:
        result = collect(row, 2)
        print(json.dumps({'id': row['id'], 'status': result['product_media_status'], 'candidates': result['candidates']}, ensure_ascii=False))
        assert result['product_media_status'] == 'product_candidates', result
        for candidate in result['candidates']:
            url = candidate['image_url']
            validate_url(url)
            with urllib.request.build_opener(PublicRedirect()).open(url, timeout=10) as response:
                payload = response.read(8000001)
            assert len(payload) <= 8000000
            with Image.open(BytesIO(payload)) as image:
                print(f"LIVE IMAGE {row['id']}: {image.size}; {url}")
                image.verify()
if __name__ == '__main__':
    if '--live' in sys.argv:
        live()
    else:
        unittest.main()
