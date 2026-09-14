"""Compress real screenshot pixels for delivery; never synthesize map evidence."""
from io import BytesIO
from PIL import Image, ImageOps

def compress_capture(payload, max_width=1600, quality=84):
    with Image.open(BytesIO(payload)) as source:
        source.load()
        if source.format not in {'PNG', 'JPEG', 'WEBP'}:
            raise ValueError('capture must be a PNG, JPEG or WebP raster')
        image=ImageOps.exif_transpose(source).convert('RGB')
        original=image.size
        if image.width<1400 or image.height<1100:
            raise ValueError('capture must be at least 1400 by 1100 pixels')
        if image.width>max_width:
            image.thumbnail((max_width,round(max_width*original[1]/original[0])),Image.Resampling.LANCZOS)
        output=BytesIO()
        image.save(output,format='WEBP',quality=quality,method=6)
        return output.getvalue(),image.size,original
