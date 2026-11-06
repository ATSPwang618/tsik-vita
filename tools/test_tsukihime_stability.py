"""Stable-pack regressions: preflight all potentially expanded story images."""
import importlib.util
import io
import json
import struct
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from restore_tsukihime_quality import kimg,members,atlas
from vita_image_metadata import image_info,runtime_layout

spec=importlib.util.spec_from_file_location('stable',Path(__file__).with_name('stabilize-tsukihime-assets.py'))
stable=importlib.util.module_from_spec(spec);spec.loader.exec_module(stable)

class StableTests(unittest.TestCase):
    def test_archive_aliases_and_interrupted_commit_recover_without_duplicate_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);name='w_allpac'
            raw=kimg(Image.new('RGBA',(600,600),(180,40,91,127)),(1200,1200),7)
            encoded=stable.pack(raw);stored=(len(encoded)+2047)//2048
            (root/f'{name}.mrg').write_bytes(encoded+b'\0'*(-len(encoded)%2048))
            row=struct.pack('<IHH',0,stored,(len(raw)+2047)//2048)
            (root/f'{name}.hed').write_bytes(row+row+struct.pack('<IHH',0xffffffff,0,0))
            (root/f'{name}.nam').write_bytes(b'IMG_A.NXGZ'.ljust(32,b'\0')+b'IMG_B.NXGZ'.ljust(32,b'\0'))
            files=[dict(path=p.name,bytes=p.stat().st_size,sha256=stable.sha_file(p)) for p in root.iterdir()]
            stable.write_json(root/'vita-540p-assets.json',dict(files=files,archives=[dict(name=name,textures=1,pixels=360000)],
                statistics={},verification={}))
            commit=stable.complete_transaction
            stable.complete_transaction=lambda _:None
            try:stable.rewrite_archive(root,name,set(),2)
            finally:stable.complete_transaction=commit
            # Model interruption between archive replacement and header replacement.
            (root/f'{name}.mrg.stable-partial').replace(root/f'{name}.mrg')
            stable.complete_transaction(root)
            stable.complete_transaction(root) # replay is harmless after completion
            self.assertFalse((root/'.stable-transaction.json').exists())
            records,_=stable.rows(root,name);self.assertEqual(records[0],records[1])
            manifest=json.loads((root/'vita-540p-assets.json').read_bytes())
            for file in manifest['files']:
                p=root/file['path'];self.assertEqual(stable.sha_file(p),file['sha256'])
            self.assertEqual(manifest['stability_preprocessing']['archives'][name]['resized'],1)

    def test_every_possible_shape_is_bounded_including_pitch_and_pow2(self):
        for w,h in [(1020,1016),(537,1928),(960,540),(2048,400),(400,2048),(1,2048),(2048,1),(257,509),(316,569)]:
            nw,nh=stable.stable_size(w,h)
            self.assertLessEqual(nw,w);self.assertLessEqual(nh,h)
            self.assertLessEqual(max(nw,nh),960)
            self.assertLessEqual(stable.rgba_charge(nw,nh),512*1024)
            self.assertLessEqual(stable.native_charge(nw,nh),512*1024)
        self.assertEqual(stable.stable_size(120,200),(120,200))

    def test_previous_failing_image_is_preprocessed_and_logical_size_kept(self):
        old=kimg(Image.new('RGBA',(1020,1016),(180,40,91,127)),(2591,2582),7)
        value,change=stable.reduce_image(old,strips=1)
        info=image_info(value)
        self.assertEqual(info['logical'],[2591,2582]);self.assertTrue(change)
        self.assertLessEqual(runtime_layout(info)['rgba_new_page_bytes'],512*1024)
        px=Image.open(io.BytesIO(value[32:])).convert('RGBA')
        self.assertEqual(px.getpixel((px.width//2,px.height//2))[3],127)
        self.assertEqual(stable.reduce_image(value,strips=1),(value,None))

    def test_language_slots_never_bleed_and_small_members_remain_byte_exact(self):
        src=Image.new('RGBA',(960,1080),(200,30,60,255));src.paste((20,60,220,127),(0,540,960,1080))
        value,change=stable.reduce_image(kimg(src,(1920,2160),2),strips=2)
        info=image_info(value);self.assertEqual(info['logical'],[1920,2160]);self.assertTrue(change)
        px=Image.open(io.BytesIO(value[32:])).convert('RGBA');self.assertEqual(px.height%2,0)
        self.assertEqual(px.getpixel((0,px.height//2-1)),(200,30,60,255))
        self.assertEqual(px.getpixel((0,px.height//2)),(20,60,220,127))
        self.assertLessEqual(runtime_layout(info,2)['rgba_new_page_bytes'],512*1024)
        small=kimg(Image.new('RGBA',(120,200),(1,2,3,128)),(240,400),7)
        self.assertEqual(stable.reduce_image(small,strips=1),(small,None))

    def test_reject_invalid_language_split_before_conversion(self):
        raw=kimg(Image.new('RGBA',(960,1081)),(1920,2162),7)
        with self.assertRaisesRegex(ValueError,'strip'):stable.reduce_image(raw,strips=2)

    def test_gxt_preserves_codec_and_alpha_while_reducing_physical_extent(self):
        raw=kimg(Image.new('RGBA',(600,600),(180,40,91,127)),(1200,1200),9)
        value,change=stable.reduce_image(raw,strips=1);info=image_info(value)
        self.assertTrue(change);self.assertEqual(info['codec'],9);self.assertEqual(info['logical'],[1200,1200])
        self.assertLessEqual(info['gpu_payload_bytes'],512*1024)
        self.assertLessEqual(runtime_layout(info)['rgba_new_page_bytes'],512*1024)
        rgba,size,_,_=stable.native().gxt_decode(value[32:])
        self.assertLessEqual(abs(rgba.getpixel((size[0]//2,size[1]//2))[3]-127),8)

if __name__=='__main__':unittest.main()
