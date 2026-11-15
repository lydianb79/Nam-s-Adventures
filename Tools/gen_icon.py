#!/usr/bin/env python3
"""Composites the title logo and the macOS app icon from the Blender renders.
   gen_icon.py <render dir>   (expects logo3d.png and nam_icon.png from blender_renders.py)"""
import sys, os, math
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "Assets", "Resources", "Art")
ICON = os.path.join(HERE, "..", "Assets", "Icon", "icon_1024.png")
R = sys.argv[1]

def trim(im, pad=0):
    b = im.getbbox(); return im.crop((max(0, b[0] - pad), max(0, b[1] - pad), min(im.width, b[2] + pad), min(im.height, b[3] + pad)))

def shadow(im, off=(0, 14), blur=14, col=(40, 10, 50), a=150):
    sh = Image.new("RGBA", im.size, (*col, 0)); sh.putalpha(im.split()[3].point(lambda v: v * a // 255)); sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, off); out.alpha_composite(im); return out

# ---- logo: 3D title + the Thai subtitle strip from the original logo
logo3d = trim(Image.open(os.path.join(R, "logo3d.png")).convert("RGBA"), 30)
thai = Image.open(os.path.join(HERE, "logo_thai.png")).convert("RGBA")      # Thai subtitle lettering
W = 1500; s = (W - 80) / logo3d.width
l3 = logo3d.resize((int(logo3d.width * s), int(logo3d.height * s)), Image.LANCZOS)
ts = 0.95; th = thai.resize((int(thai.width * ts), int(thai.height * ts)), Image.LANCZOS)
H = l3.height + th.height + 30
canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
canvas.alpha_composite(l3, ((W - l3.width) // 2, 0)); canvas.alpha_composite(th, ((W - th.width) // 2, l3.height - 4))
from PIL import ImageEnhance
canvas = ImageEnhance.Color(ImageEnhance.Brightness(canvas).enhance(1.16)).enhance(1.12)
shadow(canvas).save(os.path.join(ART, "logo3d.png")); print("logo", canvas.size)

# ---- icon: keep the original rounded frame (gold rim + drop shadow), repaint the inside, add the 3D Nam
# frame: soft drop shadow + gold rim, drawn here
base = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
sh = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([104, 116, 920, 932], 184, fill=(0, 0, 0, 110)); base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
rim = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0)); rdw = ImageDraw.Draw(rim)
rdw.rounded_rectangle([100, 100, 924, 924], 186, fill=(92, 52, 8, 255)); rdw.rounded_rectangle([104, 104, 920, 920], 182, fill=(214, 150, 24, 255))
for i in range(12):
    t = i / 11; c = (int(255 - 40 * t), int(226 - 70 * t), int(120 - 90 * t), 255); rdw.rounded_rectangle([106 + i, 106 + i, 918 - i, 918 - i], 180 - i, outline=c, width=1)
base.alpha_composite(rim)
N = 1024; x0, y0, x1, y1 = 118, 118, 906, 906; rad = 168
bg = Image.new("RGBA", (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(bg)
for y in range(N):
    t = y / N
    stops = [(0.0, (62, 38, 120)), (0.42, (176, 58, 128)), (0.7, (246, 140, 78)), (1.0, (255, 196, 96))]
    for i in range(len(stops) - 1):
        if stops[i][0] <= t <= stops[i + 1][0]:
            k = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0]); c = tuple(int(stops[i][1][j] + (stops[i + 1][1][j] - stops[i][1][j]) * k) for j in range(3)); break
    d.line([0, y, N, y], fill=(*c, 255))
sun = (512, 610)
rays = Image.new("RGBA", (N, N), (0, 0, 0, 0)); rd = ImageDraw.Draw(rays)
for i in range(14):
    a0 = i * 2 * math.pi / 14 - 0.1; a1 = a0 + math.pi / 18
    rd.polygon([sun, (sun[0] + math.cos(a0) * 900, sun[1] + math.sin(a0) * 900), (sun[0] + math.cos(a1) * 900, sun[1] + math.sin(a1) * 900)], fill=(255, 240, 200, 46))
bg.alpha_composite(rays)
glow = Image.new("RGBA", (N, N), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
gd.ellipse([sun[0] - 230, sun[1] - 230, sun[0] + 230, sun[1] + 230], fill=(255, 236, 170, 235)); glow = glow.filter(ImageFilter.GaussianBlur(45)); bg.alpha_composite(glow)
d = ImageDraw.Draw(bg); PUR = (92, 44, 112, 255)
def chedi(cx, base_y, s):
    for w, h in ((150, 26), (120, 24), (92, 22)):
        d.rectangle([cx - w * s / 2, base_y - h * s, cx + w * s / 2, base_y], fill=PUR); base_y -= h * s
    d.pieslice([cx - 44 * s, base_y - 60 * s, cx + 44 * s, base_y + 60 * s], 180, 360, fill=PUR); base_y -= 56 * s
    d.polygon([(cx - 16 * s, base_y), (cx + 16 * s, base_y), (cx, base_y - 150 * s)], fill=PUR)
chedi(770, 800, 1.25); chedi(650, 800, 0.7)
# temple roof silhouette on the left
for i, (w, y) in enumerate(((330, 800), (250, 700), (170, 630))):
    d.polygon([(250 - w / 2, y), (250 + w / 2, y), (250 + w / 2 - 50, y - 86), (250 - w / 2 + 50, y - 86)], fill=PUR)
    d.line([(250 - w / 2 - 16, y - 2), (250 - w / 2 - 34, y - 34)], fill=(250, 200, 80, 255), width=6); d.line([(250 + w / 2 + 16, y - 2), (250 + w / 2 + 34, y - 34)], fill=(250, 200, 80, 255), width=6)
d.polygon([(232, 546), (268, 546), (250, 430)], fill=PUR)
d.rectangle([150, 760, 350, 900], fill=PUR)
# ground
d.ellipse([-200, 770, N + 200, 1250], fill=(92, 190, 70, 255)); d.ellipse([-200, 786, N + 200, 1266], fill=(118, 208, 78, 255))
# Nam
nam = trim(Image.open(os.path.join(R, "nam_icon.png")).convert("RGBA"))
s = 800 / nam.height; nam = nam.resize((int(nam.width * s), int(nam.height * s)), Image.LANCZOS)
nam = shadow(nam, (10, 14), 16, (50, 20, 70), 120)
bg.alpha_composite(nam, (512 - nam.width // 2 + 6, 206))
# heart-empty HUD icon = darkened heart
h = Image.open(os.path.join(ART, "ui_heart.png")).convert("RGBA"); r, g, b, a = h.split()
grey = Image.merge("RGBA", (r.point(lambda v: 30 + v // 9), r.point(lambda v: 22 + v // 12), r.point(lambda v: 44 + v // 8), a.point(lambda v: v * 3 // 4)))
grey.save(os.path.join(ART, "ui_heart_empty.png"))
# clip to the rounded square and drop it into the frame
mask = Image.new("L", (N, N), 0); ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], rad, fill=255)
out = base.copy(); out.paste(bg, (0, 0), mask)
out.save(ICON); print("icon ok")
