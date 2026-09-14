import unittest
from build_render_bindings import source_link

class SourceLinks(unittest.TestCase):
    def test_official_target_wins_over_map_provenance(self):
        link=source_link({'source_url':'https://www.google.com/maps/place/example','official_url':'https://example.org/visit'})
        self.assertIn('href="https://example.org/visit"',link)
        self.assertIn('官网',link)

    def test_map_source_is_not_mislabeled_official(self):
        link=source_link({'source_url':'https://www.google.com/maps/place/example'})
        self.assertIn('来源',link)
        self.assertNotIn('官网',link)

if __name__=='__main__':unittest.main()
