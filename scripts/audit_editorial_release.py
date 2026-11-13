"""CLI for the same editorial release check used by build.py."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets/destination-reference'))
from editorial_release import audit, main, pointer, DOMAINS, FILES, question_for
if __name__ == '__main__':
    raise SystemExit(main())
