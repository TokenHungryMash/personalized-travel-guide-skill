"""Render a compiled profile through the selected official UI pipeline."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def render(profile, workbench):
    profile, workbench = Path(profile).resolve(), Path(workbench).resolve()
    data = json.loads(profile.read_text(encoding='utf-8'))
    system = data.get('ui_system', 'current-system')
    if system not in {'current-system', 'canonical'}:
        raise ValueError('Unknown ui_system: ' + str(system))
    bindings = (profile.parent / data.get('render_bindings_file', 'render-bindings.json')).resolve()
    scripts = Path(__file__).resolve().parent
    # Validate/generate first: invalid input must not overwrite a working page.
    steps = [
        ['validate_destination_data.py', str(profile)],
        ['build_render_bindings.py', str(profile), str(bindings)],
        ['install_ui_system.py', str(workbench), '--system', system, '--force-template'],
        ['render_destination.py', str(profile), str(workbench)],
    ]
    for script, *args in steps:
        subprocess.run([sys.executable, str(scripts / script), *args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    try:
        render(args.profile, args.workbench)
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
