import unittest
from _media_policy import official_brand_dimensions_usable

class BrandAssetQualityTests(unittest.TestCase):
    def test_normal_card_artwork_is_usable(self):
        self.assertTrue(official_brand_dimensions_usable(800, 400))
        self.assertTrue(official_brand_dimensions_usable(250, 250))

    def test_tiny_or_banner_thin_artwork_is_rejected(self):
        self.assertFalse(official_brand_dimensions_usable(102, 50))
        self.assertFalse(official_brand_dimensions_usable(775, 73))
        self.assertFalse(official_brand_dimensions_usable(1000, 100))

if __name__ == '__main__': unittest.main()
