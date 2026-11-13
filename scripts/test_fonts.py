"""Regression checks for incremental glyph coverage and failed-download recovery."""
import base64
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


fonts = module('supplement_test', ROOT / 'assets/destination-reference/font_supplement.py')
audit = module('audit_test', ROOT / 'scripts/audit_fonts.py')
from font_audit import check_final_html
SOURCE = (ROOT / 'assets/destination-reference/fonts/body-400-0.woff2').read_bytes()
with TTFont(io.BytesIO(SOURCE)) as source:
    CODES = sorted(code for code in source.getBestCmap() if 0x4e00 <= code <= 0x9fff)[:3]


def payload(codes):
    with TTFont(io.BytesIO(SOURCE)) as font:
        cutter = subset.Subsetter()
        cutter.populate(unicodes=codes)
        cutter.subset(font)
        font.flavor = 'woff2'
        buffer = io.BytesIO()
        font.save(buffer)
        return buffer.getvalue()


def rule(family, weight, url, codes):
    ranges = ','.join(f'U+{code:X}' for code in codes)
    return f"@font-face{{font-family:'{family}';font-weight:{weight};src:url({url});unicode-range:{ranges};}}"


class FontRegression(unittest.TestCase):
    def test_final_caption_invalidates_release_even_after_previous_font_check(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            data='data:font/woff2;base64,'+base64.b64encode(payload(CODES[:1])).decode()
            css=rule('Custom Sans','400',data,CODES[:1])+rule('Custom Serif','400',data,CODES[:1])
            css+=":root{--font-body:'Custom Sans';--font-serif:'Custom Serif'}"
            initial='<style>'+css+'</style><p>'+chr(CODES[0])+'</p>'
            self.assertEqual(check_final_html(root,initial,'release','before')['result'],'pass')
            final=initial+'<figcaption>'+chr(CODES[1])+'</figcaption>'
            with self.assertRaisesRegex(ValueError,'font_supplement.py'):
                check_final_html(root,final,'release','after')
            self.assertEqual(check_final_html(root,final,'preview','draft')['result'],'missing-glyphs')

    def test_incremental_and_failed_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'fonts').mkdir()
            (root / 'fonts/base.woff2').write_bytes(payload(CODES[:1]))
            (root / 'body-font.css').write_text(rule('Custom Sans', '400', 'fonts/base.woff2', CODES[:1]) + rule('Custom Sans', '700', 'fonts/base.woff2', CODES[:1]), encoding='utf8')
            (root / 'serif-font.css').write_text(rule('Custom Serif', '400', 'fonts/base.woff2', CODES[:1]), encoding='utf8')
            (root / 'index.html').write_text(''.join(map(chr, CODES[:2])), encoding='utf8')
            calls = []

            def fetch(job):
                calls.append(job)
                family, _, weight, chars = job
                data = payload(map(ord, chars))
                name = hashlib.sha256((family + weight).encode() + data).hexdigest() + '.woff2'
                return [(name, data, rule(family, weight, 'fonts/' + name, map(ord, chars)), 'test fixture')]

            self.assertEqual(fonts.supplement(root, fetch), 3)
            previous = (root / 'font-supplement.css').read_bytes()
            self.assertEqual(fonts.supplement(root, fetch), 0)
            self.assertEqual(len(calls), 3)
            self.assertEqual((root / 'font-supplement.css').read_bytes(), previous)
            old_files = {p.name: p.read_bytes() for p in (root / 'fonts').iterdir()}
            (root / 'index.html').write_text(''.join(map(chr, CODES)), encoding='utf8')

            def fail(job):
                raise OSError('simulated network failure')

            with self.assertRaises(OSError):
                fonts.supplement(root, fail)
            self.assertEqual((root / 'font-supplement.css').read_bytes(), previous)
            self.assertEqual({p.name: p.read_bytes() for p in (root / 'fonts').iterdir()}, old_files)
            self.assertEqual(fonts.supplement(root, fetch), 3)
            self.assertTrue((root / 'font-supplement.css').read_bytes().startswith(previous.rstrip()))
            for name, data in old_files.items():
                self.assertEqual((root / 'fonts' / name).read_bytes(), data)

    def test_weight_and_unicode_range(self):
        with tempfile.TemporaryDirectory() as folder:
            html = Path(folder) / 'index.html'
            data = 'data:font/woff2;base64,' + base64.b64encode(payload(CODES[:2])).decode()
            css = rule('Custom Sans', '400', data, CODES[:2])
            css += rule('Custom Sans', '700', data, CODES[:1])
            css += rule('Custom Serif', '400', data, CODES[:2])
            css += ":root{--font-body:Arial,'Custom Sans',sans-serif;--font-serif:Georgia,'Custom Serif',serif}"
            html.write_text('<style>' + css + '</style>' + ''.join(map(chr, CODES[:2])), encoding='utf8')
            result = audit.inspect(html)
            self.assertEqual(result['Custom Sans']['weights']['400'], '')
            self.assertEqual(result['Custom Sans']['weights']['700'], chr(CODES[1]))
            self.assertEqual(result['Custom Sans']['missing'], chr(CODES[1]))
            self.assertEqual(result['Custom Serif']['missing'], '')
            html.write_text('<style>' + css + rule('Custom Sans', '900', 'fonts/external.woff2', CODES[:2]) + '</style>' + ''.join(map(chr, CODES[:2])), encoding='utf8')
            result = audit.inspect(html)
            self.assertEqual(result['Custom Sans']['weights']['900'], ''.join(map(chr, CODES[:2])))


if __name__ == '__main__':
    unittest.main()

