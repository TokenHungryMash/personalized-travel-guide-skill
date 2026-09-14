"""Real CLI path and stdout-schema regressions; cached fixtures avoid all network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from inspect_research_json import SCHEMA, inspect_file, summarize_candidates
from research_image_candidates import cache_key

SCRIPTS = Path(__file__).resolve().parent


class CandidateInspection(unittest.TestCase):
    def fixture(self):
        return {"id": "shop-a", "query": "福岡 店", "resolved_identity": {"coordinates": [33.5, 130.4]}, "candidates": [{"source": "official_og_image", "source_page": "https://example.org/shop", "image_url": "https://example.org/logo.png", "subject_verified": False}], "errors": []}

    def cli(self, script, *args):
        result = subprocess.run([sys.executable, "-S", "-X", "utf8", str(SCRIPTS/script), *map(str, args)], capture_output=True, text=True, encoding="utf-8")
        self.assertNotIn("Traceback", result.stderr)
        return result, json.loads(result.stdout)

    def test_chinese_space_path_and_inspector_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"中文 文件夹"/"候选 图片.json"
            path.parent.mkdir()
            path.write_text(json.dumps([self.fixture()], ensure_ascii=False), encoding="utf-8-sig")
            result, summary = self.cli("inspect_research_json.py", path)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(summary["schema"], SCHEMA)
            self.assertEqual(summary["source_file"], str(path.resolve()))
            self.assertEqual(summary["candidate_count"], 1)
            self.assertEqual(summary["places"][0]["candidates"][0]["image_url"], "https://example.org/logo.png")
            self.assertEqual(summary["verification_status"], "candidates_only_identity_and_visual_review_required")

    def test_producer_stdout_is_enough_without_another_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/"冷启动 回归"
            root.mkdir()
            request = {"id": "shop-a", "query": "福岡 店"}
            request_path = root/"输入 请求.json"
            output = root/"结果 候选.json"
            request_path.write_text(json.dumps([request]), encoding="utf-8")
            (root/".image-candidate-cache.json").write_text(json.dumps({cache_key(request, 2): self.fixture()}), encoding="utf-8")
            result, summary = self.cli("research_image_candidates.py", request_path, output)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(summary["cached_count"], 1)
            self.assertEqual(summary["source_file"], str(output.resolve()))
            self.assertEqual(summary["places"][0]["coordinates"], [33.5, 130.4])
            self.assertEqual(summary["places"][0]["candidates"][0]["source_page"], "https://example.org/shop")

    def test_missing_invalid_and_empty_are_distinguished(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder)/"不存在 文件.json"
            result, summary = self.cli("inspect_research_json.py", missing)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(summary["status"], "input_missing")
            result, summary = self.cli("research_image_candidates.py", missing, Path(folder)/"output.json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(summary["status"], "input_missing")
            missing.write_text('{"wrong": true}', encoding="utf-8")
            self.assertEqual(inspect_file(missing)["status"], "input_invalid")
            row = self.fixture()
            row["candidates"] = []
            summary = summarize_candidates([row])
            self.assertEqual(summary["empty_ids"], ["shop-a"])
            self.assertEqual(summary["candidate_count"], 0)
            row["candidates"] = [{}]
            with self.assertRaisesRegex(ValueError, "/0/candidates/0/image_url"):
                summarize_candidates([row])


if __name__ == "__main__":
    unittest.main()
