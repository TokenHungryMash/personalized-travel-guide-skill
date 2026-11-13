"""File-role filters shared by clean workbenches and portable skill packages."""
from pathlib import Path
import re


def is_runtime_artifact(relative):
    """Exclude reproducible caches, QA output and local dependencies anywhere."""
    relative = Path(relative)
    for part in relative.parts:
        name = part.lower()
        if name in {'__pycache__', 'node_modules', '.git', '.venv', 'venv', 'qa', 'cache', '.cache'}:
            return True
        if name.startswith('qa-') or name.endswith(('-cache', '_cache')):
            return True
    return relative.suffix.lower() in {'.pyc', '.pyo', '.log', '.tmp', '.bak'}


def is_destination_output(relative):
    """The editable template has one root HTML input; maps/*.html are inputs too."""
    relative = Path(relative)
    if len(relative.parts) != 1:
        return False
    name = relative.name.lower()
    if relative.suffix.lower() in {'.html', '.htm'}:
        return name != 'dialogs.html'
    return name in {'build-manifest.json', 'qa.json', 'report.json'} or bool(
        re.fullmatch(r'(?:.+-(?:audit|report)|(?:audit|qa)-.+)\.json', name)
    )


def workbench_ignore(source, *, sample=False):
    """A copytree callback, filtering before copying rather than deleting afterward."""
    source = Path(source).resolve()

    def ignore(directory, names):
        relative_directory = Path(directory).resolve().relative_to(source)
        return [name for name in names
                if is_runtime_artifact(relative_directory / name)
                or (not sample and is_destination_output(relative_directory / name))]

    return ignore
