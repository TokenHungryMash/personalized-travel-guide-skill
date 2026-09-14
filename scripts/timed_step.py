"""Run one bundled step and record actual wall time, exit status and script name."""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench',type=Path)
    parser.add_argument('script')
    parser.add_argument('args',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    directory=Path(__file__).resolve().parent
    script=(directory/args.script).resolve()
    if script.parent!=directory or not script.is_file() or script.suffix!='.py' or script.name==Path(__file__).name:
        parser.error('select another bundled Python script')
    start=time.perf_counter()
    result=subprocess.run([sys.executable,str(script),*args.args])
    row={'script':script.name,'elapsed_seconds':round(time.perf_counter()-start,3),'exit_code':result.returncode,'finished_at':datetime.now(timezone.utc).isoformat()}
    args.workbench.mkdir(parents=True,exist_ok=True)
    with (args.workbench/'build-command-timings.jsonl').open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(row)+'\n')
    print('TIMING '+json.dumps(row),flush=True)
    return result.returncode

if __name__=='__main__':
    raise SystemExit(main())
