#!/usr/bin/env python3
"""Audit and package this v4 skill into a new portable ZIP without local build output."""
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from portable_files import is_destination_output, is_runtime_artifact

PACKAGE_NAME = 'build-personalized-travel-guide-open-source'
ALLOWED_ROOTS = {'assets', 'references', 'scripts', 'agents'}
ALLOWED_FILES = {'SKILL.md', 'README.md', 'README.en.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', '.gitignore', '.gitattributes'}


def frozen_manifest(root):
    manifest = root / 'assets/reference-manifest.json'
    return json.loads(manifest.read_text(encoding='utf8'))['files'] if manifest.is_file() else {}


def package_files(root):
    root = Path(root).resolve()
    protected = frozen_manifest(root)
    files = []
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        name = relative.as_posix()
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        if name not in protected:
            if relative.parts[0] not in ALLOWED_ROOTS and name not in ALLOWED_FILES:
                continue
            if is_runtime_artifact(relative) or path.name.startswith(('.env', '.dev.vars')):
                continue
            if path.suffix.lower() in {'.zip', '.pem', '.key'}:
                continue
            if relative.parts[:2] == ('assets', 'destination-reference') and is_destination_output(Path(*relative.parts[2:])):
                continue
        files.append(path)
    included = {path.relative_to(root).as_posix() for path in files}
    for name, digest in protected.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or name not in included:
            raise ValueError('Missing or unsafe frozen reference asset: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen reference asset changed: ' + name)
    return sorted(files)


def check_output(root, output):
    if output.is_relative_to(root) or output.exists():
        raise ValueError('Choose a new ZIP path outside the skill directory; existing files are preserved.')
    if output.suffix.lower() != '.zip':
        raise ValueError('Output path must end in .zip.')


def write_package(root, output):
    """Also used by tiny fixture regressions; the CLI runs the full skill audit first."""
    root, output = Path(root).resolve(), Path(output).expanduser().resolve()
    check_output(root, output)
    files = package_files(root)
    expected = [(Path(PACKAGE_NAME) / path.relative_to(root)).as_posix() for path in files]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path, name in zip(files, expected):
            archive.write(path, name)
    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad or archive.namelist() != expected:
            raise ValueError('ZIP integrity check failed: ' + str(bad or 'file list mismatch'))
        for item in archive.infolist():
            if not item.filename.isascii() and not item.flag_bits & 0x800:
                raise ValueError('ZIP filename is missing its UTF-8 flag: ' + item.filename)
        for name, digest in frozen_manifest(root).items():
            if hashlib.sha256(archive.read(PACKAGE_NAME + '/' + name)).hexdigest() != digest:
                raise ValueError('Packaged frozen asset differs from its manifest: ' + name)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New .zip path outside this skill')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.expanduser().resolve()
    try:
        check_output(root, output)
    except ValueError as error:
        parser.error(str(error))
    subprocess.run([sys.executable, '-X', 'utf8', str(root / 'scripts/audit_package.py')], check=True)
    count = write_package(root, output)
    print(f'PASS packaged {count} files under {PACKAGE_NAME}/: {output}')


if __name__ == '__main__':
    main()
