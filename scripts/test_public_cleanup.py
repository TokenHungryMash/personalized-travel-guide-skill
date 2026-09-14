"""Exercise release paths previously missed by scaffold-only checks."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from fetch_declared_assets import validate_public_https_url
from probe_official_page import validate_url


class PublicCleanup(unittest.TestCase):
    def test_asset_manifest_audit_handles_both_validation_depths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'index.html').write_text('<!doctype html><html><body>Fixture</body></html>', encoding='utf8')
            (root/'asset-manifest.json').write_text(json.dumps({'destination': 'Fixture', 'assets': [{'file': 'missing.jpg'}]}), encoding='utf8')
            for flags in (['--strict'], ['--strict', '--standard-fast']):
                result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).with_name('audit_product.py')), str(root), *flags], capture_output=True, text=True, encoding='utf8')
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 2, output)
                self.assertIn('asset manifest has incomplete entries: 1', output)
                self.assertNotIn('Namespace', output)
                self.assertNotIn('Traceback', output)

    def test_fetch_and_probe_share_explicit_proxy_policy(self):
        for validator in (validate_public_https_url, validate_url):
            for allow in ('0', '1'):
                for address in ('127.0.0.1', '192.168.1.1', '169.254.169.254', '198.18.0.1', 'fdfe:dcba:9876::1', '8.8.8.8'):
                    with self.subTest(validator=validator.__name__, allow=allow, address=address), patch.dict(os.environ, {'TRAVEL_GUIDE_ALLOW_FAKE_IP': allow}), patch.object(socket, 'getaddrinfo', return_value=[(0, 0, 0, '', (address, 443))]):
                        if address == '8.8.8.8' or (allow == '1' and address in ('198.18.0.1', 'fdfe:dcba:9876::1')):
                            validator('https://example.org/image.jpg')
                        else:
                            with self.assertRaises(ValueError):
                                validator('https://example.org/image.jpg')
            with patch.dict(os.environ, {'TRAVEL_GUIDE_ALLOW_FAKE_IP': '1'}), patch.object(socket, 'getaddrinfo', return_value=[(0, 0, 0, '', ('198.18.0.1', 443))]):
                with self.assertRaises(ValueError):
                    validator('https://198.18.0.1/image.jpg')


if __name__ == '__main__':
    unittest.main()
