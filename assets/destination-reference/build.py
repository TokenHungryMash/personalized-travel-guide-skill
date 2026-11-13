from pathlib import Path
import sys,runpy,argparse,os
R=Path(__file__).parent
import subprocess
parser=argparse.ArgumentParser()
parser.add_argument('--preview',action='store_true',help='Build a draft for editorial/browser review, not a deliverable')
parser.add_argument('--check',action='store_true',help='Read-only data preflight; no images, fonts or HTML are built')
args=parser.parse_args()
subprocess.run([sys.executable,'-X','utf8',str(R/'preflight.py'),str(R)]+(['--draft'] if args.preview else []),check=True)
if args.check:raise SystemExit(0)
os.environ['JOURNAL_BUILD_STAGE']='preview' if args.preview else 'release'
subprocess.run([sys.executable, '-X', 'utf8', str(R/'audit_photo_quality.py'), str(R)], check=True)
sys.argv=[str(R/"edition-renderer.py"),str(R)]
runpy.run_path(str(R/"edition-renderer.py"),run_name="__main__")
