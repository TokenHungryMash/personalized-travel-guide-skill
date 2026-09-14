import json, tempfile, unittest
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw
from _map_delivery import compress_capture
from package_handbook import package

class CompressionTests(unittest.TestCase):
    def test_jpeg_bytes_accepted_and_no_upscale(self):
        image=Image.new('RGB',(1400,1100),'white')
        draw=ImageDraw.Draw(image)
        for n in range(50):draw.line((n*28,0,1400-n*28,1100),fill='gray',width=2)
        draw.text((20,30),'OpenStreetMap TEST FIXTURE',fill='black')
        raw=BytesIO();image.save(raw,format='JPEG',quality=95)
        compressed,size,original=compress_capture(raw.getvalue())
        self.assertEqual(size,original)
        self.assertEqual(Image.open(BytesIO(compressed)).format,'WEBP')
        self.assertLess(len(compressed),len(raw.getvalue()))
    def test_size_limit_and_invalid_capture(self):
        raw=BytesIO();Image.new('RGB',(2800,2200),'white').save(raw,format='PNG')
        _,size,original=compress_capture(raw.getvalue())
        self.assertEqual(original,(2800,2200));self.assertEqual(size,(1600,1257))
        raw=BytesIO();Image.new('RGB',(300,200),'white').save(raw,format='PNG')
        with self.assertRaises(ValueError):compress_capture(raw.getvalue())
    def test_offline_flattens_map_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'build';(root/'media/routes').mkdir(parents=True)
            (root/'destination-profile.json').write_text(json.dumps({'map_delivery':'online','online_map_user_statement':'test fixture','places':[],'itinerary':[]}))
            (root/'media/routes/capture-day-1-1.svg').write_text('<svg><image href="data:image/webp;base64,VGVzdA=="/></svg>')
            (root/'index.html').write_text('<img src="media/routes/capture-day-1-1.svg">')
            html=package(root).read_text(encoding='utf-8')
            self.assertIn('src="data:image/webp;base64,VGVzdA=="',html)
            self.assertNotIn('data:image/svg+xml',html)
if __name__=='__main__':unittest.main()
