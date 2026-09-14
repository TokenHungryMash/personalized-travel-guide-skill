import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import verify_assets


class CoverReuse(unittest.TestCase):
    def check_assets(self, ids):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = io.BytesIO()
            Image.new("RGB", (640, 480), "green").save(image, "PNG")
            assets = []
            for index, place_id in enumerate(ids):
                name = f"image-{index}.png"
                (root / name).write_bytes(image.getvalue())
                assets.append({"file": name, "place_id": place_id,
                               "source_page": "https://example.com/place",
                               "download_url": "https://example.com/image.png",
                               "source_type": "official", "media_class": "official_photo",
                               "visual_subject_type": "place_exterior", "source_identity_bound": True, "source_identity_note": "Synthetic source observation for this image fixture only"})
            profile = {"trip": {"quality_mode": "standard"},
                       "cover": {"image": "cover.png"},
                       "places": [{"id": "sight"}, {"id": "other"}]}
            (root / "profile.json").write_text(json.dumps(profile))
            (root / "manifest.json").write_text(json.dumps({"assets": assets}))
            (root / "asset-fetch-report.json").write_text(json.dumps([
                {**a, "status": "ok", "sha256": hashlib.sha256((root / a['file']).read_bytes()).hexdigest()} for a in assets]))
            args = ["verify_assets", str(root / "profile.json"), str(root / "manifest.json"), str(root), "--machine-only"]
            with patch("sys.argv", args), contextlib.redirect_stdout(io.StringIO()):
                return verify_assets.main()

    def test_cover_reuse_passes_in_either_order(self):
        for ids in (["__cover__", "sight"], ["sight", "__cover__"]):
            self.assertEqual(self.check_assets(ids), 0)

    def test_duplicate_gallery_still_fails_with_cover(self):
        for ids in (["__cover__", "sight", "sight"], ["sight", "__cover__", "sight"]):
            self.assertEqual(self.check_assets(ids), 2)

    def test_different_places_still_fail(self):
        self.assertEqual(self.check_assets(["__cover__", "sight", "other"]), 2)


if __name__ == "__main__":
    unittest.main()
