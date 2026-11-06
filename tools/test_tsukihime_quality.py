"""Quality regressions: real cell density, original strips and bounded GPU data."""
import io
import struct
import unittest
from PIL import Image
from restore_tsukihime_quality import (PIXELS, atlas, improve, kimg, members,
                                       native, quality_size, thumbnail_pages)
from vita_image_metadata import image_info, runtime_layout


class QualityTests(unittest.TestCase):
    def test_story_grade_pitch_and_physical_page_exceed_compact_rgba_size(self):
        layout = runtime_layout(dict(physical=[1020,1016], codec=9, cdram_allocation_bytes=1048576))
        self.assertEqual(layout['rgba_bytes'], 4145280)
        self.assertEqual(layout['rgba_pitch_bytes'], 4161536)
        self.assertEqual(layout['rgba_pool_slice_bytes'], 4161536)
        self.assertEqual(layout['rgba_new_page_bytes'], 4194304)

    def test_codec_specific_axes_and_selected_language_share_rgba_budget(self):
        info = dict(physical=[600,1700], codec=9, cdram_allocation_bytes=1048576)
        self.assertEqual(runtime_layout(info)['selected_physical'], [600,1700])
        with self.assertRaisesRegex(ValueError, 'axis'): runtime_layout(dict(info, codec=2))
        self.assertEqual(runtime_layout(dict(info, codec=2),2)['selected_physical'], [600,850])
        with self.assertRaisesRegex(ValueError, 'budget'):
            runtime_layout(dict(info,physical=[2048,1080]))
        with self.assertRaisesRegex(ValueError, 'axis'):
            runtime_layout(dict(info,physical=[2049,1]))
    def test_tall_portrait_preserves_density_without_raising_cpu_work_budget(self):
        w, h = quality_size(1199, 4302)
        self.assertGreaterEqual(h, 1620)  # At least 3x the old 151x540 portrait.
        self.assertGreater(w, 500)
        self.assertLessEqual(max(w, h), 2048)
        self.assertLessEqual(w*h, PIXELS)
        self.assertAlmostEqual(w/h, 1199/4302, delta=0.001)

    def test_small_original_variant_is_not_downsampled_again(self):
        self.assertEqual(quality_size(430, 243), (430, 243))

    def test_original_forest_has_at_least_one_texel_per_fitted_screen_pixel(self):
        w, h = quality_size(1404, 844)
        self.assertGreaterEqual(w, 897)
        self.assertGreaterEqual(h, 539)

    def test_both_cpu_routes_remain_bounded_for_large_panorama(self):
        for shape in [(3848,5620), (4095,39), (4500,112), (3512,187), (2670,1266)]:
            for png in [False, True]:
                w, h = quality_size(*shape, png=png)
                self.assertLessEqual(w*h, PIXELS)
                self.assertLessEqual(w, 960 if png else 2048)
                self.assertLessEqual(h, 1080 if png else 2048)

    def test_gxt_decodes_original_encoded_colours_and_partial_edge_alpha(self):
        source = Image.new('RGBA', (57, 135), (220, 40, 80, 100))
        value = kimg(source, source.size, 9)
        info = image_info(value)
        decoded, size, _, _ = native().gxt_decode(value[32:])
        self.assertEqual(size, source.size)
        for p in [decoded.getpixel((0,0)), decoded.getpixel((56,134))]:
            for actual, expected in zip(p, (220,40,80,100)):
                self.assertLessEqual(abs(actual-expected), 8)
        self.assertEqual(info['codec'], 9)

    def test_bilingual_rebuild_selects_japanese_and_simplified_chinese(self):
        source = Image.new('RGBA', (80, 1600))
        colours = [(220,40,80,255), (0,255,0,255), (30,60,200,255), (255,255,0,255)]
        for i, color in enumerate(colours): source.paste(color, (0, i*400, 80, (i+1)*400))
        old = kimg(Image.new('RGBA', (30,300)), (80,800), 2)
        result, change = improve(old, source, strips=2)
        image = Image.open(io.BytesIO(result[32:])).convert('RGBA')
        self.assertEqual(image.getpixel((0,0)), colours[0])
        self.assertEqual(image.getpixel((0,image.height//2)), colours[2])
        self.assertEqual(change['logical'], [80,800])
        self.assertEqual(change['strips'], 2)

    def test_every_original_cell_maps_to_a_full_density_page(self):
        # Unique cell colours catch wrong row stride, page boundaries and the
        # partly filled final page. Decode the actual generated PNG payloads.
        original = Image.new('RGBA', (5544,4840))
        for i in range(1980):
            x, y = i%36*154, i//36*88
            original.paste((i%251, i//251, 80, 255), (x,y,x+154,y+88))
        pages = dict(members(thumbnail_pages(original)))
        self.assertEqual(len(pages), 28)
        for page_index in range(28):
            value = pages[f'cg_thumb_page_{page_index}']
            info = image_info(value)
            image = Image.open(io.BytesIO(value[32:])).convert('RGBA')
            for local in range(min(72, 1980-page_index*72)):
                i = page_index*72+local
                self.assertEqual(image.getpixel((local%6*116+58, local//6*66+33)),
                                 (i%251, i//251, 80, 255))
            self.assertEqual(info['physical'], [696,792])
            self.assertEqual(info['logical'], [924,1056])

    def test_original_non_divisible_language_height_keeps_fractional_strip_origins(self):
        source = Image.new('RGBA', (316,1138))
        for i, colour in enumerate([(220,40,80,255),(0,255,0,255),(30,60,200,255),(255,255,0,255)]):
            source.paste(colour, (0, 1138*i//4, 316, 1138*(i+1)//4))
        old = kimg(Image.new('RGBA', (119,212)), (316,568), 2)
        result, _ = improve(old, source, strips=2)
        image = Image.open(io.BytesIO(result[32:])).convert('RGBA')
        for x in [0, image.width-1]:
            self.assertEqual(image.getpixel((x,0)), (220,40,80,255))
            self.assertEqual(image.getpixel((x,image.height//2)), (30,60,200,255))


if __name__ == '__main__': unittest.main()
