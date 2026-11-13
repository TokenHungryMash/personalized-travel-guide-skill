"""Read-only final HTML per-weight CJK coverage check."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/destination-reference'))
from font_audit import inspect

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html',type=Path)
    result=inspect(parser.parse_args().html)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(1 if any(value['missing'] for value in result.values()) else 0)
