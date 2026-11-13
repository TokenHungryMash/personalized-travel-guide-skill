import shutil,subprocess,sys,tempfile,unittest,os
from pathlib import Path

class BuildReleaseGateTests(unittest.TestCase):
    def run_build(self,preview=False,ready=False,covered=True,check=False):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            shutil.copy2(Path(__file__).resolve().parents[1]/'assets/destination-reference/build.py',p/'build.py')
            (p/'editorial_release.py').write_text('raise SystemExit('+('0' if ready else '1')+')',encoding='utf8')
            (p/'coverage_release.py').write_text('raise SystemExit('+('0' if covered else '1')+')',encoding='utf8')
            (p/'preflight.py').write_text('import sys\nraise SystemExit('+('0' if ready and covered else '(0 if "--draft" in sys.argv else 1)')+')',encoding='utf8')
            (p/'audit_photo_quality.py').write_text('',encoding='utf8')
            (p/'edition-renderer.py').write_text("from pathlib import Path\nimport os\nPath(__file__).with_name('stage.txt').write_text(os.environ['JOURNAL_BUILD_STAGE'])",encoding='utf8')
            result=subprocess.run([sys.executable,str(p/'build.py')]+(['--preview'] if preview else [])+(['--check'] if check else []),capture_output=True)
            return result.returncode,(p/'stage.txt').read_text() if (p/'stage.txt').exists() else None
    def test_default_build_cannot_skip_failed_review(self):
        code,stage=self.run_build();self.assertNotEqual(code,0);self.assertIsNone(stage)
    def test_explicit_preview_can_be_reviewed_before_release(self):
        self.assertEqual(self.run_build(preview=True),(0,'preview'))
    def test_reviewed_release_reaches_renderer(self):
        self.assertEqual(self.run_build(ready=True),(0,'release'))
    def test_check_never_calls_renderer_and_preserves_release_gate(self):
        self.assertEqual(self.run_build(check=True,ready=True),(0,None))
        self.assertEqual(self.run_build(check=True,preview=True),(0,None))
        code,stage=self.run_build(check=True)
        self.assertNotEqual(code,0);self.assertIsNone(stage)
    def test_review_ready_cannot_release_unfinished_directory_and_dining(self):
        code,stage=self.run_build(ready=True,covered=False)
        self.assertNotEqual(code,0);self.assertIsNone(stage)
        self.assertEqual(self.run_build(preview=True,covered=False),(0,'preview'))
    def test_direct_release_renderer_also_checks_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            shutil.copy2(Path(__file__).resolve().parents[1]/'assets/destination-reference/edition-renderer.py',p/'edition-renderer.py')
            (p/'coverage_release.py').write_text("print('COVERAGE_REJECTED');raise SystemExit(1)",encoding='utf8')
            result=subprocess.run([sys.executable,str(p/'edition-renderer.py'),str(p)],env={**os.environ,'JOURNAL_BUILD_STAGE':'release'},capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('COVERAGE_REJECTED',result.stdout)
