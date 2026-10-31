"""Synthetic regression tests for archive repair; no game data required."""
import importlib.util
import io
import struct
import unittest
import hashlib
import json
import tempfile
from unittest.mock import patch
from pathlib import Path
from PIL import Image

spec = importlib.util.spec_from_file_location('repair', Path(__file__).with_name('repair-tsukihime-assets.py'))
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)

def kimg(image, logical, codec=7):
    out = io.BytesIO()
    image.save(out, 'PNG')
    data = out.getvalue()
    return struct.pack('<4s7I', b'KIMG', 1, *logical, *image.size, codec, len(data))+data

class RepairImages(unittest.TestCase):
    def test_archive_repair_preserves_source_and_accepts_unnamed_parts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'input'; source.mkdir(); output = root/'output'
            entries = []
            for name in repair.ARCHIVES:
                dimensions = (1100, 100) if name == 'w_allpac' else (8, 8)
                raw = kimg(Image.new('RGBA', dimensions, (19, 57, 123, 87)), dimensions)
                raw += b'\0' * (-len(raw) % 2048)
                (source/f'{name}.mrg').write_bytes(raw)
                (source/f'{name}.hed').write_bytes(struct.pack('<IHH', 0, len(raw)//2048, len(raw)//2048)+b'\xff'*8)
                if name != 'parts': (source/f'{name}.nam').write_bytes(b'IMG0001.NXGZ'.ljust(32, b'\0'))
                entries.append(dict(name=name, pixels=dimensions[0]*dimensions[1], bytes=len(raw)))
            files = [dict(path=p.name, bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in source.iterdir()]
            manifest = dict(method='native-540p-encoded-unorm-v2', files=files, archives=entries,
                            verification=dict(files_hashed=True, resampled=False))
            (source/'vita-540p-assets.json').write_text(json.dumps(manifest), encoding='utf-8')
            original = {p.name:p.read_bytes() for p in source.iterdir()}
            with patch.object(repair, 'strip_names', return_value=set()):
                repair.run(source, output, root/'report.json')
            self.assertEqual(original, {p.name:p.read_bytes() for p in source.iterdir()})
            self.assertFalse((output/'parts.nam').exists())
            fixed = json.loads((output/'vita-540p-assets.json').read_text(encoding='utf-8'))
            self.assertEqual(fixed['runtime_image_repair']['images'], 1)
            self.assertTrue(fixed['verification']['resampled'])
            for row in fixed['files']:
                self.assertEqual(repair.file_sha(output/row['path']), row['sha256'])
            self.assertEqual((output/'parts.mrg').read_bytes(), original['parts.mrg'])

    def test_panorama_keeps_logical_size_and_unorm_alpha(self):
        raw = kimg(Image.new('RGBA', (1400, 1100), (19, 57, 123, 87)), (2800, 2200))
        data, row = repair.repair_image(raw, 'IMG0001', set(), None)
        header = struct.unpack_from('<4s7I', data)
        self.assertEqual(header[2:4], (2800, 2200))
        self.assertLessEqual(header[4], 960)
        self.assertLessEqual(header[5], 540)
        self.assertEqual(header[6], 7)
        image = Image.open(io.BytesIO(data[32:])).convert('RGBA')
        self.assertEqual(image.getchannel('A').getextrema(), (87, 87))
        self.assertEqual(row['source_codec'], 7)

    def test_four_languages_are_not_resized_as_one_long_picture(self):
        raw = kimg(Image.new('RGBA', (960, 2160), (1, 2, 3, 255)), (1920, 4320), 2)
        data, row = repair.repair_image(raw, 'IMG0010', {'IMG0010'}, None)
        self.assertIsNone(row)
        self.assertEqual(data, raw)

    def test_oversized_strips_resize_each_language_separately(self):
        image = Image.new('RGBA', (1000, 2160))
        for k in range(4):
            image.paste((20+k*50, 90, 130, 255), (0, k*540, 1000, (k+1)*540))
        data, row = repair.repair_image(kimg(image, (2000, 4320), 2), 'IMG0010', {'IMG0010'}, None)
        result = Image.open(io.BytesIO(data[32:])).convert('RGBA')
        self.assertEqual(row['strips'], 4)
        self.assertEqual(struct.unpack_from('<II', data, 8), (2000, 4320))
        for k in range(4):
            self.assertEqual(result.getpixel((10, k*(result.height//4)+10)), (20+k*50, 90, 130, 255))

if __name__ == '__main__':
    unittest.main()
