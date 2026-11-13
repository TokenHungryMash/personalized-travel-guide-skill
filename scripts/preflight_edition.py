"""Run current data preflight on an existing workbench without changing its files."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/destination-reference'))
from preflight import audit,main
if __name__=='__main__':raise SystemExit(main())
