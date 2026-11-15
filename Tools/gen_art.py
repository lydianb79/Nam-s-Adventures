#!/usr/bin/env python3
"""Generates the effect textures (glow, sparkles, bubble, dust, rays, petal, sky gradient)
and the tiling surface textures used by the 3D world. Needs Pillow."""
import math, os
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "Assets", "Resources", "Art")
SS = 4
INK = (42, 26, 46, 255)

def canvas(w, h):
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)

def fin(im, w, h, name):
    im = im.resize((w, h), Image.LANCZOS)
    im.save(os.path.join(OUT, name))
    print("wrote", name)

def S(v):
    return [tuple(c * SS for c in p) for p in v]

def bubble():
    w = h = 160
    im, d = canvas(w, h)
    c = w * SS / 2
    r = 70 * SS
    d.ellipse([c - r, c - r, c + r, c + r], fill=(255, 255, 255, 46), outline=(255, 255, 255, 235), width=4 * SS)
    d.arc([c - r * 0.78, c - r * 0.78, c + r * 0.78, c + r * 0.78], 200, 262, fill=(255, 255, 255, 240), width=6 * SS)
    d.ellipse([c + r * 0.38, c + r * 0.42, c + r * 0.52, c + r * 0.56], fill=(255, 255, 255, 200))
    fin(im, w, h, "bubble.png")

def dust():
    w = h = 64
    im, d = canvas(w, h)
    d.ellipse([6 * SS, 6 * SS, 58 * SS, 58 * SS], fill=(255, 255, 255, 255))
    im = im.filter(ImageFilter.GaussianBlur(3 * SS))
    fin(im, w, h, "dust.png")

def rays():
    # soft god-ray fan used behind the goal gong / power-ups
    w = h = 512
    im, d = canvas(w, h)
    c = w * SS / 2
    for i in range(12):
        a0 = i * math.pi / 6
        a1 = a0 + math.pi / 14
        d.polygon([(c, c), (c + math.cos(a0) * c, c + math.sin(a0) * c), (c + math.cos(a1) * c, c + math.sin(a1) * c)],
                  fill=(255, 255, 255, 120))
    im = im.resize((w, h), Image.LANCZOS)
    px = im.load()
    for y in range(h):
        for x in range(w):
            r = math.hypot(x - w / 2, y - h / 2) / (w / 2)
            p = px[x, y]
            px[x, y] = (255, 255, 255, int(p[3] * max(0, 1 - r) ** 1.3))
    im.save(os.path.join(OUT, "rays.png"))
    print("wrote rays.png")

if __name__ == "__main__" and len(__import__("sys").argv) == 1:
    bubble(); dust(); rays()


def fx():
    # soft radial glow
    n = 256; im = Image.new("RGBA", (n, n)); px = im.load()
    for y in range(n):
        for x in range(n):
            r = math.hypot(x - n / 2 + .5, y - n / 2 + .5) / (n / 2); a = max(0.0, 1 - r) ** 2.2
            px[x, y] = (255, 255, 255, int(255 * a))
    im.save(os.path.join(OUT, "glow.png"))
    n = 32; im = Image.new("RGBA", (n, n)); px = im.load()
    for y in range(n):
        for x in range(n):
            r = math.hypot(x - n / 2 + .5, y - n / 2 + .5) / (n / 2); px[x, y] = (255, 255, 255, int(255 * max(0.0, 1 - r) ** 1.5))
    im.save(os.path.join(OUT, "spark.png"))
    # four-point sparkle
    n = 64; im, d = canvas(n, n); c = n * SS / 2
    d.polygon([(c, 2 * SS), (c + 5 * SS, c - 5 * SS), (n * SS - 2 * SS, c), (c + 5 * SS, c + 5 * SS), (c, n * SS - 2 * SS), (c - 5 * SS, c + 5 * SS), (2 * SS, c), (c - 5 * SS, c - 5 * SS)], fill=(255, 255, 255, 255))
    fin(im, n, n, "star.png")
    Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(os.path.join(OUT, "white.png"))
    # frangipani petal
    n = 48; im, d = canvas(n, n)
    d.ellipse([10 * SS, 4 * SS, 38 * SS, 44 * SS], fill=(255, 250, 240, 255)); d.ellipse([16 * SS, 26 * SS, 32 * SS, 44 * SS], fill=(255, 224, 120, 255))
    d.ellipse([12 * SS, 6 * SS, 30 * SS, 30 * SS], fill=(255, 255, 255, 255))
    fin(im.filter(ImageFilter.GaussianBlur(SS)), n, n, "petal.png")
    # sky gradient (top -> horizon)
    im = Image.new("RGBA", (32, 1024)); d = ImageDraw.Draw(im)
    stops = [(0.0, (38, 128, 230)), (0.45, (96, 180, 245)), (0.8, (190, 230, 252)), (1.0, (236, 247, 255))]
    for y in range(1024):
        t = y / 1023
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                k = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0]); c = tuple(int(stops[i][1][j] + (stops[i + 1][1][j] - stops[i][1][j]) * k) for j in range(3)); break
        d.line([0, y, 32, y], fill=(*c, 255))
    im.save(os.path.join(OUT, "sky.png"))
    print("wrote glow / spark / star / white / petal / sky")

# ---- tiling textures for the 3D look (run:  gen_art.py tex) ----
def textures():
    import random
    r = random.Random(3)
    # elephant-pants pattern: black / white triangles
    n = 256; im = Image.new("RGB", (n, n), (250, 248, 240)); d = ImageDraw.Draw(im); c = n // 2
    for y in range(2):
        for x in range(2):
            x0, y0 = x * c, y * c
            if (x + y) % 2 == 0: d.polygon([(x0, y0), (x0 + c, y0), (x0, y0 + c)], fill=(24, 24, 30))
            else: d.polygon([(x0 + c, y0), (x0 + c, y0 + c), (x0, y0 + c)], fill=(24, 24, 30))
            d.polygon([(x0 + c * .5, y0 + c * .3), (x0 + c * .7, y0 + c * .7), (x0 + c * .3, y0 + c * .7)], fill=(250, 248, 240) if (x + y) % 2 == 0 else (24, 24, 30))
    im.save(os.path.join(OUT, "tex_pants.png"))
    # dirt: soft earthy blotches + pebbles (tileable)
    n = 512; im = Image.new("RGB", (n, n), (150, 96, 58)); d = ImageDraw.Draw(im)
    def wrap_ellipse(cx, cy, rx, ry, col):
        for ox in (-n, 0, n):
            for oy in (-n, 0, n): d.ellipse([cx - rx + ox, cy - ry + oy, cx + rx + ox, cy + ry + oy], fill=col)
    for i in range(70):
        s = r.uniform(18, 60); k = r.uniform(-14, 14)
        wrap_ellipse(r.uniform(0, n), r.uniform(0, n), s, s * r.uniform(.5, .9), (int(150 + k), int(96 + k * .7), int(58 + k * .5)))
    im = im.filter(ImageFilter.GaussianBlur(6)); d = ImageDraw.Draw(im)
    for i in range(46):
        s = r.uniform(5, 13); cx, cy = r.uniform(0, n), r.uniform(0, n)
        wrap_ellipse(cx, cy + 2, s, s * .75, (112, 68, 40)); wrap_ellipse(cx, cy, s, s * .75, r.choice([(196, 150, 104), (176, 124, 80), (206, 170, 130)]))
    im = im.filter(ImageFilter.GaussianBlur(0.8)); im.save(os.path.join(OUT, "tex_dirt.png"))
    # grass: mown stripes + speckles
    im = Image.new("RGB", (n, n), (118, 200, 74)); d = ImageDraw.Draw(im)
    for i in range(0, n, 128): d.rectangle([i, 0, i + 63, n], fill=(128, 208, 82))
    for i in range(500):
        cx, cy = r.uniform(0, n), r.uniform(0, n); s = r.uniform(2, 5)
        wrap_ellipse(cx, cy, s, s * 1.6, r.choice([(100, 184, 62), (146, 220, 96), (108, 192, 68)]))
    im = im.filter(ImageFilter.GaussianBlur(1.5)); im.save(os.path.join(OUT, "tex_grass.png"))
    print("wrote tex_pants / tex_dirt / tex_grass")

import sys
if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "tex":
    textures()
if __name__ == "__main__" and len(sys.argv) == 1:
    fx()
