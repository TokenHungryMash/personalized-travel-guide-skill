"""Controller wiring uses the evidenced workbench network session."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import advance_build

class AdvanceNetworkTests(unittest.TestCase):
    def test_asset_stage_uses_network_session_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            (root/'network-session.json').write_text(json.dumps({'fixture':'unchanged'}))
            state={'handoff_allowed':False,'stage':'assets_required'}
            with patch('sys.argv',['advance_build.py',str(root),'--run']), patch.object(advance_build,'ensure_runtime',return_value=Path(advance_build.__file__).resolve().parent.parent), patch.object(advance_build,'evaluate',return_value=state), patch.object(advance_build.subprocess,'run',return_value=subprocess.CompletedProcess([],2)) as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(advance_build.main(),2)
            command=run.call_args.args[0]
            self.assertEqual(Path(command[1]).name,'network_session.py')
            self.assertEqual(command[2:5],[str(root),'--run','fetch_declared_assets.py'])
            self.assertEqual(run.call_count,1)  # failed download must not build a manifest
            self.assertEqual(json.loads((root/'network-session.json').read_text()),{'fixture':'unchanged'})

if __name__=='__main__':unittest.main()
