import importlib.util,json,tempfile,unittest,random
from pathlib import Path
from PIL import Image
spec=importlib.util.spec_from_file_location('photo_quality',Path(__file__).resolve().parents[1]/'assets/destination-reference/audit_photo_quality.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PhotoQualityTests(unittest.TestCase):
 def test_rejects_low_resolution_and_cross_role_reencoding(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);random.seed(4);im=Image.effect_noise((2600,1700),60).convert('RGB');im.save(p/'cover.png');im.save(p/'copy.jpg',quality=95);im.resize((424,284)).save(p/'small.jpg')
   for name,obj in [('edition.json',{'cover':'cover','foodPhoto':'food','culturePhoto':'small'}),('content.json',{'areas':[]}),('place-photos.json',{}),('edition-photos.json',{'cover':{'src':'cover.png'},'food':{'src':'copy.jpg'},'small':{'src':'small.jpg'}})]: (p/name).write_text(json.dumps(obj))
   report=m.audit(p);self.assertTrue(any('424x284' in x for x in report['errors']));self.assertTrue(any('Repeated editorial' in x for x in report['errors']))
 def test_same_role_responsive_variant_allowed(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);Image.new('RGB',(2600,1700),'navy').save(p/'cover.jpg')
   for name,obj in [('edition.json',{'cover':'cover'}),('content.json',{'areas':[]}),('place-photos.json',{}),('edition-photos.json',{'cover':{'src':'cover.jpg','mobileSrc':'cover.jpg'}})]: (p/name).write_text(json.dumps(obj))
   self.assertEqual(m.audit(p)['errors'],[])
if __name__=='__main__':unittest.main()
