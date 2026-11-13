"""Small synthetic regressions for clean initialization and v4 ZIP portability."""
import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_skill import PACKAGE_NAME, package_files, write_package
from portable_files import workbench_ignore


class PortablePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='journal-portable-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'fixture-skill'
        self.destination = self.root / 'assets/destination-reference'
        self.sample = self.root / 'assets/fukuoka-reference'
        self.files = {
            'SKILL.md': 'fixture',
            'scripts/build.py': '# builder',
            'references/中文说明.md': '保留 Unicode 文件名',
            'assets/destination-reference/dialogs.html': '<dialog></dialog>',
            'assets/destination-reference/index.html': 'generated',
            'assets/destination-reference/Tokyo-five-days.html': 'generated',
            'assets/destination-reference/旅行手册.html': 'generated',
            'assets/destination-reference/æ—…è¡Œ-äº¬.HTML': 'mojibake generated',
            'assets/destination-reference/legacy.htm': 'generated',
            'assets/destination-reference/build-manifest.json': '{}',
            'assets/destination-reference/QA.json': '{}',
            'assets/destination-reference/directory-audit.json': '{}',
            'assets/destination-reference/browser-report.json': '{}',
            'assets/destination-reference/edition.json': '{}',
            'assets/destination-reference/maps/d1-atlas.html': 'render input',
            'assets/destination-reference/maps/地图.webp': 'map bytes',
            'assets/destination-reference/maps/tile-cache/tile.png': 'cached',
            'assets/destination-reference/qa/screenshots.png': 'QA',
            'assets/destination-reference/qa-current-engine/report.json': '{}',
            'assets/destination-reference/.photo-cache/network-state.json': '{}',
            'assets/destination-reference/__pycache__/build.pyc': 'cached',
            'assets/destination-reference/node_modules/dependency/index.js': 'local dependency',
            'assets/fukuoka-reference/dialogs.html': 'frozen input',
            'assets/fukuoka-reference/福冈样刊.html': 'frozen artifact',
            'assets/fukuoka-reference/build-manifest.json': 'frozen manifest',
            'assets/fukuoka-reference/maps/overview.html': 'frozen map input',
            'assets/intake-questionnaire/index.html': 'questionnaire input',
            'scripts/__pycache__/cached.pyc': 'cached',
            'research/private.txt': 'not part of skill',
        }
        for name, content in self.files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf8')
        manifest = {name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
                    for name in self.files if name.startswith('assets/fukuoka-reference/')}
        (self.root / 'assets/reference-manifest.json').write_text(json.dumps({'files': manifest}), encoding='utf8')

    def test_default_copy_excludes_outputs_by_role_and_preserves_map_inputs(self):
        target = self.base / 'new-workbench'
        shutil.copytree(self.destination, target, ignore=workbench_ignore(self.destination))
        self.assertEqual({path.relative_to(target).as_posix() for path in target.rglob('*') if path.is_file()}, {
            'dialogs.html', 'edition.json', 'maps/d1-atlas.html', 'maps/地图.webp'
        })
        self.assertTrue((self.destination / 'æ—…è¡Œ-äº¬.HTML').is_file(), 'Initialization must not delete source output')

    def test_sample_copy_keeps_frozen_html_and_manifest(self):
        target = self.base / 'sample-workbench'
        shutil.copytree(self.sample, target, ignore=workbench_ignore(self.sample, sample=True))
        self.assertEqual({path.relative_to(target).as_posix() for path in target.rglob('*') if path.is_file()}, {
            'dialogs.html', '福冈样刊.html', 'build-manifest.json', 'maps/overview.html'
        })

    def test_zip_has_v4_root_utf8_names_and_preserves_frozen_assets(self):
        output = self.base / '技能包.zip'
        count = write_package(self.root, output)
        prefix = PACKAGE_NAME + '/'
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            self.assertEqual(count, len(names))
            self.assertTrue(all(name.startswith(prefix) for name in names))
            self.assertIsNone(archive.testzip())
            destination_prefix = prefix + 'assets/destination-reference/'
            self.assertEqual({name.removeprefix(destination_prefix) for name in names if name.startswith(destination_prefix)}, {
                'dialogs.html', 'edition.json', 'maps/d1-atlas.html', 'maps/地图.webp'
            })
            for name, content in self.files.items():
                if name.startswith('assets/fukuoka-reference/'):
                    self.assertEqual(archive.read(prefix + name).decode('utf8'), content)
            self.assertIn(prefix + 'assets/intake-questionnaire/index.html', names)
            self.assertEqual(archive.read(prefix + 'references/中文说明.md').decode('utf8'), '保留 Unicode 文件名')
            self.assertTrue(archive.getinfo(prefix + 'references/中文说明.md').flag_bits & 0x800)
            self.assertFalse(any('node_modules/' in name or '__pycache__/' in name or '/qa-' in name or '/research/' in name for name in names))

    def test_existing_or_internal_output_is_never_overwritten(self):
        output = self.base / 'existing.zip'
        output.write_bytes(b'existing data')
        with self.assertRaisesRegex(ValueError, 'new ZIP path'):
            write_package(self.root, output)
        self.assertEqual(output.read_bytes(), b'existing data')
        internal = self.root / 'new.zip'
        with self.assertRaisesRegex(ValueError, 'new ZIP path'):
            write_package(self.root, internal)
        self.assertFalse(internal.exists())

    def test_missing_or_changed_frozen_asset_blocks_packaging(self):
        asset = self.sample / '福冈样刊.html'
        asset.write_text('changed', encoding='utf8')
        output = self.base / 'changed.zip'
        with self.assertRaisesRegex(ValueError, 'Frozen reference asset changed'):
            write_package(self.root, output)
        self.assertFalse(output.exists())
        asset.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or unsafe frozen reference asset'):
            package_files(self.root)


if __name__ == '__main__':
    unittest.main()
