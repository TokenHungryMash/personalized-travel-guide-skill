"""Run the same coverage checks used by the formal edition builder."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/destination-reference'))
from coverage_release import audit, main
if __name__=='__main__':raise SystemExit(main())
