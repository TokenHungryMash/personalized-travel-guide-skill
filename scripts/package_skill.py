#!/usr/bin/env python3
"""Build a clean portable ZIP after validating the bundled files."""
import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

def package_files(root):
    allowed_roots = {'assets', 'references', 'scripts', 'agents'}
    allowed_files = {'SKILL.md', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', '.gitignore', '.gitattributes'}
    skipped = {'__pycache__', '.git', 'node_modules', '.venv', '.pytest_cache', '.wrangler', 'research', 'qa-evidence'}
    result = []
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            continue
        if relative.parts[0] not in allowed_roots and relative.as_posix() not in allowed_files:
            continue
        if any(part in skipped for part in relative.parts) or path.name.startswith(('.env', '.dev.vars')) or path.suffix in {'.pyc', '.pyo', '.zip', '.log', '.tmp', '.bak', '.pem', '.key'}:
            continue
        # This historical browser harness requires an unbundled private destination.
        if relative.as_posix() == 'scripts/test-system-browser.cjs':
            continue
        result.append(path)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.is_relative_to(root) or output.exists():
        parser.error('Choose a new ZIP path outside the Skill directory; existing files are preserved.')
    subprocess.run([sys.executable, str(root/'scripts/audit_skill_consistency.py')], check=True)
    files = package_files(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, (Path('build-personalized-travel-guide-open-source')/path.relative_to(root)).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise SystemExit('ZIP integrity check failed')
    print(f'PASS packaged {len(files)} files: {output}')

if __name__ == '__main__':
    main()
