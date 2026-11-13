"""Regression checks for new-workbench cleanup and destination prose validation."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL / 'assets/destination-reference'
sys.path.insert(0, str(TEMPLATE))
from destination_content import audit_relationships


class DestinationChecks(unittest.TestCase):
    def setUp(self):
        self.guide = json.loads((TEMPLATE / 'content.json').read_text(encoding='utf8'))
        self.edition = json.loads((TEMPLATE / 'edition.json').read_text(encoding='utf8'))
        self.editorial = json.loads((TEMPLATE / 'editorial-content.json').read_text(encoding='utf8'))

    def test_prose_and_compound_day_references(self):
        for value in ['第九天', '第 4 或 9 天', '第 4–9 天', 'D9 晚餐', 'DAY 9']:
            with self.subTest(value=value):
                editor = copy.deepcopy(self.editorial)
                editor['restaurant_groups'][0]['items'][0]['fit'] = value
                self.assertTrue(audit_relationships(self.guide, self.edition, editor))
        self.editorial['notes']['测试'] = [['资料', 'data:image/png;base64,IDR第九天']]
        self.assertEqual(audit_relationships(self.guide, self.edition, self.editorial), [])

    def test_edition_counts(self):
        self.edition.update(span='五天四晚', daysEnglish='FIVE')
        errors = audit_relationships(self.guide, self.edition, self.editorial)
        self.assertTrue(any('edition.span' in error for error in errors))
        self.assertTrue(any('edition.daysEnglish' in error for error in errors))

    def test_unknown_restaurant_is_rejected(self):
        self.editorial['restaurant_groups'][0]['items'][0]['id'] = 'removed-restaurant'
        errors = audit_relationships(self.guide, self.edition, self.editorial)
        self.assertTrue(any('removed-restaurant' in error for error in errors))

    def test_new_workbench_has_no_reference_outputs(self):
        with tempfile.TemporaryDirectory() as parent:
            target = Path(parent) / 'workbench'
            result = subprocess.run([sys.executable, str(SKILL / 'scripts/create_workbench.py'),
                                     str(target), '--project-id', 'regression-city'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((target / 'index.html').exists())
            self.assertFalse((target / 'build-manifest.json').exists())
            self.assertEqual(list(target.glob('*旅行杂志*.html')), [])
            self.assertEqual(json.loads((target / 'dining-image-sources.json').read_text()), {})
            metadata = json.loads((target / 'magazine-workbench.json').read_text(encoding='utf8'))
            self.assertEqual(metadata['reference_identity']['city'], self.edition['city'])
            self.assertEqual(json.loads((target / 'edition.json').read_text(encoding='utf8'))['slug'],
                             'regression-city')
            result = subprocess.run([sys.executable, str(SKILL / 'scripts/create_workbench.py'),
                                     str(target), '--project-id', 'other-city'], capture_output=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
