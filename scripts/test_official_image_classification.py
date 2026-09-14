"""Shared portal OGP must never be promoted to a venue photo."""
import json
import sys
import unittest
from unittest.mock import patch
from _official_classification import classify, shared_artwork_urls
from probe_official_page import parse_metadata, probe
from research_image_candidates import collect, official

def fixture(name, url):
    return parse_metadata(f'''<title>{name}</title><meta property="og:image" content="/img/common/ogp.png"><img src="/img/common/logo.svg" alt="CITY TOURIST GUIDE"><img src="/photo/{name.replace(' ', '-')}.jpg" alt="{name}">'''.encode(), url, product_name=name)

class OfficialClassification(unittest.TestCase):

    def test_generic_shared_ogp_and_real_body_photo_are_separate(self):
        pages = {'https://example.org/spots/1': fixture('Kushida Shrine', 'https://example.org/spots/1'), 'https://example.org/spots/2': fixture('Ohori Park', 'https://example.org/spots/2')}
        shared = shared_artwork_urls(pages)
        self.assertEqual(shared, {'https://example.org/img/common/ogp.png'})
        for url, page in pages.items():
            row = {'id': 'fixture', 'english_name': page['title'], 'official_url': url, 'type': 'sight'}
            classified = classify(row, page, shared)
            artwork = next((image for image in classified if image['url'].endswith('ogp.png')))
            self.assertEqual(artwork['visual_subject_type'], 'official_share_card')
            self.assertFalse(artwork['entity_bound'])
            result = collect(row, 2, page, shared)
            self.assertTrue(result['candidates'])
            self.assertTrue(all((candidate['media_class'] == 'official_photo' for candidate in result['candidates'])))

    def test_only_generic_artwork_does_not_short_circuit_photo_ladder(self):
        page = parse_metadata(b'<title>Shrine</title><meta property="og:image" content="/img/common/ogp.png">', 'https://example.org/place')
        with patch('research_image_candidates.wikidata', return_value=([], None, None)) as wd, patch('research_image_candidates.commons_geo', return_value=[]) as geo, patch('research_image_candidates.openverse', return_value=[]):
            result = collect({'id': 'shrine', 'query': 'Shrine', 'type': 'sight', 'official_url': 'https://example.org/place'}, 2, page)
            self.assertEqual(result['candidates'], [])
            self.assertEqual(result['official_artwork'][0]['media_class'], 'official_brand_asset')
            wd.assert_called_once()
            geo.assert_called_once()

def live():
    urls = ['https://www.gofukuoka.jp/spots/detail/26906', 'https://www.gofukuoka.jp/spots/detail/26928']
    pages = {url: probe(url) for url in urls}
    pages = {url: probe(url, product_name=page['title']) for url, page in pages.items()}
    shared = shared_artwork_urls(pages)
    assert 'https://www.gofukuoka.jp/img/common/ogp.png' in shared
    for url, page in pages.items():
        result = collect({'id': 'live-fixture', 'english_name': page['title'], 'type': 'sight', 'official_url': url}, 2, page, shared)
        assert result['candidates']
        assert all((candidate['media_class'] == 'official_photo' and '/img/common/' not in candidate['image_url'] for candidate in result['candidates']))
        print(json.dumps({'title': page['title'], 'photo_candidates': [candidate['image_url'] for candidate in result['candidates']], 'shared_ogp_class': 'official_share_card; not venue-bound'}, ensure_ascii=False))
if __name__ == '__main__':
    if '--live' in sys.argv:
        live()
    else:
        unittest.main()
