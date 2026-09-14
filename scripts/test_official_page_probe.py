"""Offline HTML/transport fixtures for the dependency-free metadata CLI."""
from email.message import Message
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

import probe_official_page as page


class OfficialPageProbe(unittest.TestCase):
    def test_attribute_order_entities_relative_urls_and_logo(self):
        raw = b'<title>Shop &amp; Place</title><meta content="/logo.png?a=1&amp;b=2" property="og:image"><meta NAME="description" content="A &amp; B">'
        result = page.parse_metadata(raw, "https://example.org/place/")
        self.assertEqual(result["title"], "Shop & Place")
        self.assertEqual(result["images"][0]["url"], "https://example.org/logo.png?a=1&b=2")
        self.assertFalse(result["images"][0]["subject_verified"])
        self.assertFalse(result["official_identity_verified"])
        self.assertEqual(result["description"], "A & B")

    def test_encoding_and_missing_image(self):
        raw = '<meta charset="shift_jis"><title>福岡</title>'.encode("shift_jis")
        result = page.parse_metadata(raw, "https://example.org")
        self.assertEqual(result["title"], "福岡")
        self.assertEqual(result["status"], "no_image")
        raw = '<title>福岡</title>'.encode("utf-8-sig")
        self.assertEqual(page.parse_metadata(raw, "https://example.org")["title"], "福岡")
        result = page.parse_metadata(b'<meta charset="unknown-charset"><title>fixture</title>', "https://example.org")
        self.assertTrue(result["encoding_warning"])

    def test_disallowed_url_and_redirect(self):
        for url in ("file:///tmp/x", "http://example.org", "https://u:p@example.org", "https://example.org:8443"):
            self.assertEqual(page.probe(url)["status"], "invalid_url")
        with patch.object(socket, "getaddrinfo", return_value=[(0, 0, 0, "", ("127.0.0.1", 443))]):
            self.assertEqual(page.probe("https://example.org")["status"], "invalid_url")
            with self.assertRaises(ValueError):
                page.PublicRedirect().redirect_request(None, None, 302, "redirect", {}, "https://localhost")
        with patch.object(socket, "getaddrinfo", return_value=[(0, 0, 0, "", ("198.18.0.1", 443))]):
            with patch.dict('os.environ', {'TRAVEL_GUIDE_ALLOW_FAKE_IP': '0'}):
                with self.assertRaises(ValueError):
                    page.validate_url("https://example.org")
            with patch.dict('os.environ', {'TRAVEL_GUIDE_ALLOW_FAKE_IP': '1'}):
                self.assertEqual(page.validate_url("https://example.org"), "https://example.org")

    def test_timeout_network_and_http_errors_are_structured(self):
        failures = [(TimeoutError("slow"), "timeout"), (urllib.error.URLError("offline"), "network_error"), (urllib.error.HTTPError("https://example.org", 429, "limited", {}, None), "http_error")]
        for error, status in failures:
            with patch.object(page, "validate_url"), patch.object(page.urllib.request, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                result = page.probe("https://example.org", timeout=7)
                self.assertEqual(result["status"], status)
                self.assertEqual(opener.return_value.open.call_count, 1)
                self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 7)

    def test_response_limits_and_content_type(self):
        for mime, body, status in (("text/html", b'<meta property="og:image" content="/share.jpg">', "ok"), ("application/json", b'{}', "not_html"), ("text/html", b'x'*(page.MAX_BYTES+1), "too_large")):
            response = MagicMock()
            response.headers = {"Content-Type": mime}
            response.read.return_value = body
            response.geturl.return_value = "https://example.org/page"
            with patch.object(page, "validate_url"), patch.object(page.urllib.request, "build_opener") as opener:
                opener.return_value.open.return_value.__enter__.return_value = response
                self.assertEqual(page.probe("https://example.org")["status"], status)

    def test_cli_runs_without_site_packages_and_writes_error_result(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/"nested/result.json"
            command = [sys.executable, "-S", "-X", "utf8", str(Path(page.__file__)), "file:///invalid", "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(output.read_text())["status"], "invalid_url")
            summary = json.loads(result.stdout)
            self.assertEqual(summary["output_file"], str(output.resolve()))
            self.assertEqual(summary["status"], "invalid_url")
            self.assertEqual(summary["images"], [])
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
