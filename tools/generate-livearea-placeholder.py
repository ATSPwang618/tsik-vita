#!/usr/bin/env python3
"""Generate Tsukihime-branded placeholder LiveArea art for the TSUKIHIME PSP2 package.

The VPK package checker requires indexed-colour PNGs of exact sizes:
  icon0.png 128x128, pic0.png 960x544, livearea/contents/bg.png 840x500,
  livearea/contents/startup.png 280x158.
These are placeholders (no official art is stored in this repository); replace them
with real artwork and re-run tools/check-vita-package.py after any replacement.

Usage: py -3 tools/generate-livearea-placeholder.py [--out <sce_sys dir>]
"""
import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path(r"C:\Windows\Fonts")
FONT_BOLD = FONT_DIR / "segoeuib.ttf"
FONT_REGULAR = FONT_DIR / "segoeui.ttf"

TITLE = "TSUKIHIME"
SUBTITLE = "A piece of blue glass moon"
FOOTER = "PS Vita port  |  960 x 540"


def font(size, bold=True):
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def gradient(width, height):
    top, bottom = (5, 8, 18), (16, 30, 62)
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        r = round(top[0] + (bottom[0] - top[0]) * t)
        g = round(top[1] + (bottom[1] - top[1]) * t)
        b = round(top[2] + (bottom[2] - top[2]) * t)
        for x in range(width):
            pixels[x, y] = (r, g, b)
    return image


def add_sky(image, seed=7):
    random.seed(seed)
    draw = ImageDraw.Draw(image)
    for _ in range(image.width * image.height // 2200):
        x = random.randrange(image.width)
        y = random.randrange(image.height)
        tone = random.choice([(120, 140, 190), (180, 200, 240), (90, 110, 160)])
        draw.point((x, y), fill=tone)


def add_moon(image, cx, cy, radius):
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for step in range(14, 0, -1):
        r = radius + step * radius // 6
        alpha = max(4, 26 - step * 2)
        gdraw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(190, 214, 255, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.28))
    image.paste(glow, (0, 0), glow)

    moon = Image.new("RGBA", image.size, (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(moon)
    mdraw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(232, 240, 255, 255))
    # a few darker maria-like blotches to avoid a flat disc
    for fx, fy, fr in ((-0.28, -0.18, 0.26), (0.22, 0.1, 0.3), (-0.05, 0.36, 0.2)):
        bx = cx + int(radius * fx)
        by = cy + int(radius * fy)
        br = int(radius * fr)
        mdraw.ellipse((bx - br, by - br, bx + br, by + br), fill=(208, 220, 242, 255))
    mask = moon.split()[3].filter(ImageFilter.GaussianBlur(1.2))
    moon.putalpha(mask)
    image.paste(moon, (0, 0), moon)


def text_center(draw, y, text, font_obj, fill, letter_spacing=0):
    if letter_spacing:
        widths = [draw.textlength(ch, font=font_obj) for ch in text]
        total = sum(widths) + letter_spacing * (len(text) - 1)
        x = (draw.im.size[0] - total) / 2
        for ch, width in zip(text, widths):
            draw.text((x, y), ch, font=font_obj, fill=fill)
            x += width + letter_spacing
    else:
        width = draw.textlength(text, font=font_obj)
        draw.text(((draw.im.size[0] - width) / 2, y), text, font=font_obj, fill=fill)


def make_icon(size=128):
    image = gradient(size, size).convert("RGBA")
    add_sky(image, seed=11)
    add_moon(image, size * 0.52, size * 0.42, size * 0.2)
    draw = ImageDraw.Draw(image)
    text_center(draw, size * 0.66, TITLE, font(max(11, size // 10)), (245, 248, 255), 1)
    return image.convert("RGB")


def make_pic(width, height, big):
    image = gradient(width, height).convert("RGBA")
    add_sky(image, seed=3)
    add_moon(image, width * 0.76, height * 0.36, height * 0.24)
    draw = ImageDraw.Draw(image)
    left = int(width * 0.07)
    title_font = font(int(height * 0.14) if big else int(height * 0.1))
    sub_font = font(int(height * 0.055) if big else int(height * 0.045), bold=False)
    foot_font = font(int(height * 0.04) if big else int(height * 0.035), bold=False)
    draw.text((left, int(height * 0.3)), TITLE, font=title_font, fill=(240, 245, 255))
    draw.text((left + 2, int(height * 0.3) + int(height * 0.14) + 6), SUBTITLE,
              font=sub_font, fill=(150, 190, 255))
    draw.line((left, int(height * 0.72), left + int(width * 0.28), int(height * 0.72)),
              fill=(80, 120, 200), width=max(1, height // 260))
    draw.text((left, int(height * 0.78)), FOOTER, font=foot_font, fill=(130, 150, 190))
    return image.convert("RGB")


def indexed(image):
    return image.quantize(colors=256, method=Image.Quantize.MEDIANCUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "knife/vita/sce_sys")
    args = parser.parse_args()
    out = args.out.resolve()
    (out / "livearea/contents").mkdir(parents=True, exist_ok=True)
    icon = indexed(make_icon(128))
    icon.save(out / "icon0.png", optimize=True)
    pic = indexed(make_pic(960, 544, big=True))
    pic.save(out / "pic0.png", optimize=True)
    bg = indexed(make_pic(840, 500, big=False))
    bg.save(out / "livearea/contents/bg.png", optimize=True)
    startup_image = gradient(280, 158).convert("RGBA")
    add_sky(startup_image, seed=5)
    add_moon(startup_image, 210, 62, 34)
    draw = ImageDraw.Draw(startup_image)
    draw.text((20, 92), TITLE, font=font(22), fill=(240, 245, 255))
    draw.text((22, 120), SUBTITLE, font=font(11, bold=False), fill=(150, 190, 255))
    startup = indexed(startup_image.convert("RGB"))
    startup.save(out / "livearea/contents/startup.png", optimize=True)
    for name in ("icon0.png", "pic0.png", "livearea/contents/bg.png", "livearea/contents/startup.png"):
        with (out / name).open("rb") as stream:
            header = stream.read(26)
        assert header[:8] == b"\x89PNG\r\n\x1a\n" and header[25] == 3, name
        print("wrote", out / name)


if __name__ == "__main__":
    main()
