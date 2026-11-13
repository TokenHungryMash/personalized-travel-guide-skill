"""Read-only preflight catches authoring failures before media processing."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/destination-reference'
sys.path.insert(0, str(TEMPLATE))
from preflight import audit

def snapshot(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}

class PreflightTests(unittest.TestCase):
    def test_malformed_input_is_reported_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'content.json').write_text('{bad',encoding='utf8')
            before=snapshot(root);report=audit(root)
            self.assertFalse(report['dataReadyForPreview'])
            self.assertFalse(report['dataReadyForRelease'])
            self.assertIn('input',report['checks'])
            self.assertEqual(before,snapshot(root))
    def test_missing_release_materials_are_reported_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('content.json','editorial-content.json','edition.json'):
                shutil.copy2(TEMPLATE/name,root/name)
            before=snapshot(root);report=audit(root)
            self.assertEqual(report['checks']['structure'],[])
            self.assertTrue(report['checks']['coverage'])
            self.assertTrue(report['checks']['review'])
            self.assertFalse(report['dataReadyForRelease'])
            self.assertEqual(before,snapshot(root))
    def test_invalid_preparation_id_has_actionable_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('content.json','editorial-content.json','edition.json'):
                shutil.copy2(TEMPLATE/name,root/name)
            file=root/'editorial-content.json';data=json.loads(file.read_text(encoding='utf8'))
            data['preparation']=[{'title':'准备','items':[{'id':'entry','title':'证件','detail':'确认有效期','priority':'必须','sources':['official']}]}]
            file.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
            before=snapshot(root);report=audit(root)
            self.assertFalse(report['dataReadyForPreview'])
            self.assertIn('prep-entry-documents',' '.join(report['checks']['structure']))
            self.assertEqual(before,snapshot(root))
