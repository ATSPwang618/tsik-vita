"""Lossless selection and original-ID regression tests for the JA/ZC pack."""
import importlib.util
import io
import struct
import unittest
from pathlib import Path
from PIL import Image

spec = importlib.util.spec_from_file_location('bilingual', Path(__file__).with_name('make-tsukihime-ja-zc.py'))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

class BilingualTests(unittest.TestCase):
    def test_tombstone_does_not_shift_following_archive_indices(self):
        records=bytearray(bytes(32)+b'NEXT.NXZ'+bytes(24))
        records[:32]=b.tombstone_name()
        self.assertEqual(len(records),64)
        self.assertEqual(records[32:40],b'NEXT.NXZ')

    def test_uneven_rows_match_production_decoder_floor_rules(self):
        im=Image.new('RGBA',(4,15))
        for y in range(15): im.paste((y,30,60,255),(0,y,4,y+1))
        buf=io.BytesIO();im.save(buf,'PNG');payload=buf.getvalue()
        raw=struct.pack('<4s7I',b'KIMG',1,8,31,4,15,7,len(payload))+payload
        out=b.select_strip(raw)
        self.assertEqual(struct.unpack_from('<4I',out,8),(8,14,4,6))
        image=Image.open(io.BytesIO(out[32:])).convert('RGBA')
        self.assertEqual(image.crop((0,3,4,6)).tobytes(),im.crop((0,7,4,10)).tobytes())

    def test_strips_keep_japanese_and_chinese_pixels_in_order(self):
        im = Image.new('RGBA', (8, 12))
        for k, color in enumerate(['red', 'green', 'blue', 'yellow']):
            im.paste(color, (0, k*3, 8, (k+1)*3))
        payload = io.BytesIO(); im.save(payload, 'PNG')
        raw = struct.pack('<4s7I', b'KIMG', 1, 16, 24, 8, 12, 7, len(payload.getvalue())) + payload.getvalue()
        result = b.select_strip(raw)
        self.assertEqual(struct.unpack_from('<4I', result, 8), (16, 12, 8, 6))
        selected = Image.open(io.BytesIO(result[32:])).convert('RGBA')
        for slot, old in enumerate([0, 2]):
            self.assertEqual(selected.crop((0,slot*3,8,(slot+1)*3)).tobytes(), im.crop((0,old*3,8,(old+1)*3)).tobytes())

    def test_script_keeps_exact_pairs_and_removes_unused_fifth_pair(self):
        blocks = [bytes([i])*10000 for i in range(10)]
        selected = b.select_script(b.pack_mzp(blocks))
        self.assertEqual(b.unpack_mzp(selected), [blocks[i] for i in [0,1,4,5]])

    def test_system_strings_keep_exact_language_rows(self):
        rows = [[f'{lang}:{i}'.encode() for i in range(7)] for lang in range(4)]
        raw = b.pack_sysmes(bytes(16), rows)
        self.assertEqual(b.sysmes_rows(b.select_sysmes(raw)), [rows[0], rows[2]])

    def test_guide_cells_follow_physical_language_slots(self):
        raw = struct.pack('<4H', 3, 0, 0, 0) + b''.join(bytes([i])*24 for i in range(4)) + bytes(1024)
        self.assertEqual(b.select_guide(raw), raw[:8] + bytes([0])*24 + bytes([2])*24)

    def test_language_removal_only_matches_exact_path_components(self):
        for name in ['en/test.ttf', 'zt3/font.otf', 'movie/prologue_en.mp4', 'saveicon_zt.tga']:
            self.assertTrue(b.remove_loose(name), name)
        for name in ['stream/bgm_event.nxa', 'movie/ending.mp4', 'movie/prologue_zc.mp4', 'exfont_nx01.bffnt']:
            self.assertFalse(b.remove_loose(name), name)

if __name__ == '__main__': unittest.main()
