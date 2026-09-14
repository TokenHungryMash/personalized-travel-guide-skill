#!/usr/bin/env python3
"""Bind a workbench launcher to its directory and the current installed Skill."""
import argparse
import sys
from pathlib import Path


def install(root):
    root = Path(root).resolve()
    skill = Path(__file__).resolve().parent.parent
    wrapper = (skill/"scripts/work_unit.ps1").as_posix().replace("'", "''")
    source = (skill/"assets/workbench-launcher.ps1").read_text(encoding="utf-8")
    target = root/"travel.ps1"
    root.mkdir(parents=True, exist_ok=True)
    interpreter = Path(sys.executable).as_posix().replace("'", "''")
    target.write_text(source.replace("__SKILL_WRAPPER__", wrapper).replace("__PYTHON_EXECUTABLE__", interpreter), encoding="utf-8-sig")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbench", type=Path)
    args = parser.parse_args()
    print(install(args.workbench))
