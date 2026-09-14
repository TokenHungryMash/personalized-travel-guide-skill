import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class ResearchStatusModeTests(unittest.TestCase):

    def run_mode(self, mode):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'research-plan.json').write_text(json.dumps({'quality_mode': mode, 'batch_size': 2, 'packs': [{'id': 'framing', 'file': 'research/framing.json', 'purpose': 'fixture'}]}), encoding='utf-8')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('research_status.py')), str(root)], capture_output=True, text=True, encoding='utf-8')
            return result.stdout

    def test_standard_prints_pack_path_without_timer(self):
        output = self.run_mode('standard')
        self.assertIn('canonical pack', output)
        self.assertIn('production-flow.md', output)
        self.assertNotIn('TIMING:', output)
        self.assertNotIn('1-2 named places', output)
if __name__ == '__main__':
    unittest.main()
