#!/usr/bin/env python3
"""Generates the tileable greyscale surface-detail maps (mean ~0.5) that the world shader projects onto
models for colour variation and relief, plus the richer earth texture for the terrain. Needs numpy + Pillow."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "Assets", "Resources", "Art")
N = 256
rng = np.random.default_rng(5)

def noise(n=N, fx=8.0, fy=8.0, power=1.6, seed=None):
    """Periodic filtered noise: random spectrum shaped by an (anisotropic) falloff. Tiles perfectly."""
    r = np.random.default_rng(seed) if seed is not None else rng
    f = np.fft.fft2(r.standard_normal((n, n)))
    ky = np.fft.fftfreq(n)[:, None] * n; kx = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt((kx / fx) ** 2 + (ky / fy) ** 2); k[0, 0] = 1
    out = np.real(np.fft.ifft2(f / (1 + k ** 2) ** power))
    out -= out.min(); out /= out.max()
    return out

def norm(a, contrast=1.0):
    a = a - a.mean(); a = a / (np.abs(a).max() + 1e-9) * 0.5 * contrast + 0.5
    return np.clip(a, 0, 1)

def save(name, a, n=N, relief=7.0):
    a = np.clip(a, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8), "L").convert("RGB").save(os.path.join(OUT, name + ".png"))
    # matching normal map (tangent space, +V up), so relief is mip-filtered instead of derived per pixel on screen
    h = np.asarray(Image.fromarray((a * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float64) / 255.0
    gu = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * relief
    gv = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * 0.5 * relief          # image rows run downwards, V runs upwards
    nz = 1.0 / np.sqrt(gu * gu + gv * gv + 1.0)
    nm = np.stack([-gu * nz * 0.5 + 0.5, -gv * nz * 0.5 + 0.5, nz * 0.5 + 0.5], -1)
    Image.fromarray((np.clip(nm, 0, 1) * 255).astype(np.uint8), "RGB").save(os.path.join(OUT, name + "_n.png"))
    print("wrote", name, "+ normal map")

yy, xx = np.mgrid[0:N, 0:N] / N

def wood():      # long grain running along V, a few darker pores
    g = noise(fx=40, fy=2.2, power=1.2) * 0.7 + noise(fx=90, fy=5, power=1.0) * 0.3
    rings = np.sin((xx * 9 + noise(fx=3, fy=3) * 2.2) * 2 * np.pi) * 0.5 + 0.5
    save("det_wood", norm(g * 0.75 + rings * 0.25, 1.0))

def bark():      # deep vertical ridges
    warp = noise(fx=5, fy=3) * 0.5
    ridg = 1 - np.abs(np.sin((xx * 7 + warp) * np.pi))
    save("det_bark", norm(ridg ** 0.7 * 0.7 + noise(fx=30, fy=6, power=1.0) * 0.3, 1.15))

def leaf():      # soft blotches with fine diagonal veins
    v = np.sin(((xx + yy * 0.6) * 22 + noise(fx=4, fy=4) * 1.5) * 2 * np.pi) * 0.5 + 0.5
    save("det_leaf", norm(noise(fx=6, fy=6) * 0.7 + v * 0.3, 0.8))

def stone():     # lumpy rock with thin cracks
    a = noise(fx=4, fy=4, power=1.3) * 0.6 + noise(fx=16, fy=16, power=1.2) * 0.3 + noise(fx=50, fy=50, power=1.0) * 0.1
    c = np.abs(noise(fx=7, fy=7, power=1.4, seed=3) - 0.5); crack = np.clip(1 - c * 22, 0, 1) ** 2
    save("det_stone", norm(a, 1.1) * (1 - crack * 0.55))

def brick():     # 8 courses of bricks with mortar joints
    rows, cols = 8, 4
    h = np.zeros((N, N)); tone = rng.uniform(0.38, 0.66, (rows, cols + 1))
    for y in range(N):
        r = y * rows // N
        for x in range(N):
            xo = (x + (N // cols // 2 if r % 2 else 0)) % N; c = xo * cols // N
            fy = (y * rows / N) % 1; fx_ = (xo * cols / N) % 1
            mortar = fy < 0.1 or fx_ < 0.045
            h[y, x] = 0.16 if mortar else tone[r, c]
    h = np.asarray(Image.fromarray((h * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))) / 255.0
    save("det_brick", np.clip(h + (noise(fx=40, fy=40, power=1.0) - 0.5) * 0.14, 0, 1))

def tile():      # overlapping rounded roof tiles
    rows, cols = 8, 8
    fy = (yy * rows) % 1; r = np.floor(yy * rows)
    fx_ = ((xx * cols) + (r % 2) * 0.5) % 1
    arc = np.sqrt(np.clip(1 - (fx_ * 2 - 1) ** 2, 0, 1))           # rounded profile across each tile
    shade = 0.35 + 0.45 * arc * (0.55 + 0.45 * fy)                  # lower edge catches light, upper edge sits in shadow
    shade *= np.where(fy < 0.12, 0.55, 1.0)
    save("det_tile", np.clip(shade + (noise(fx=30, fy=30, power=1.0) - 0.5) * 0.1, 0, 1))

def thatch():    # layered straw
    s = noise(fx=70, fy=3, power=1.0)
    band = (yy * 6) % 1
    save("det_thatch", norm(s, 1.1) * (0.62 + 0.38 * band ** 0.5))

def weave():     # basket weave, over / under
    c = 8; u = (xx * c) % 1; v = (yy * c) % 1; cell = (np.floor(xx * c) + np.floor(yy * c)) % 2
    a = np.where(cell == 0, np.sin(u * np.pi) ** 0.6 * (0.75 + 0.25 * np.sin(v * 6 * np.pi)), np.sin(v * np.pi) ** 0.6 * (0.75 + 0.25 * np.sin(u * 6 * np.pi)))
    save("det_weave", norm(a, 1.0))

def plaster():
    save("det_plaster", norm(noise(fx=10, fy=10, power=1.2) * 0.6 + noise(fx=45, fy=45, power=1.0) * 0.4, 0.55))

def metal():     # softly hammered
    pts = rng.uniform(0, 1, (70, 2)); d = np.full((N, N), 9.0)
    for px, py in pts:
        dx = np.minimum(np.abs(xx - px), 1 - np.abs(xx - px)); dy = np.minimum(np.abs(yy - py), 1 - np.abs(yy - py))
        d = np.minimum(d, np.sqrt(dx * dx + dy * dy))
    save("det_metal", norm(d, 0.6))

def earth():
    """Terrain face: horizontal strata, embedded stones with light and shadow, fine grit. Tiles in X and Y."""
    n = 1024
    base = noise(n, fx=5, fy=14, power=1.3, seed=11); grit = noise(n, fx=120, fy=120, power=0.9, seed=12)
    Y, X = np.mgrid[0:n, 0:n] / n
    strata = np.sin((Y * 6 + noise(n, fx=3, fy=30, power=1.5, seed=13) * 0.9) * 2 * np.pi) * 0.5 + 0.5
    v = 0.5 + (base - 0.5) * 0.5 + (strata - 0.5) * 0.22 + (grit - 0.5) * 0.12
    col = np.stack([np.clip(0.66 * v + 0.26, 0, 1), np.clip(0.42 * v + 0.17, 0, 1), np.clip(0.26 * v + 0.09, 0, 1)], -1)
    im = Image.fromarray((col * 255).astype(np.uint8), "RGB"); d = ImageDraw.Draw(im, "RGBA")
    r = np.random.default_rng(21)
    for i in range(75):
        cx, cy = r.uniform(0, n), r.uniform(0, n); s = r.uniform(5, 19); sy = s * r.uniform(0.6, 0.9)
        tone = r.choice([(206, 176, 138), (182, 142, 104), (222, 196, 160), (160, 132, 110)])
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                x, y = cx + ox, cy + oy
                d.ellipse([x - s - 2, y - sy + 3, x + s + 2, y + sy + 6], fill=(70, 40, 22, 150))                      # contact shadow
                d.ellipse([x - s, y - sy, x + s, y + sy], fill=(*[int(t * 0.8) for t in tone], 255))
                d.ellipse([x - s * 0.82, y - sy * 0.86, x + s * 0.62, y + sy * 0.5], fill=(*tone, 255))                   # lit upper face
                d.ellipse([x - s * 0.5, y - sy * 0.62, x + s * 0.05, y - sy * 0.16], fill=(255, 245, 225, 70))
    im = im.filter(ImageFilter.GaussianBlur(0.7)); im.save(os.path.join(OUT, "tex_dirt.png")); print("wrote tex_dirt 1024")

if __name__ == "__main__":
    wood(); bark(); leaf(); stone(); brick(); tile(); thatch(); weave(); plaster(); metal(); earth()


# ---------------------------------------------------------------------------------------------- themed ground
def rgb(n_arr, c0, c1):
    """Greyscale array -> colour ramp between two RGB tuples."""
    a = np.clip(n_arr, 0, 1)[..., None]
    return np.array(c0)[None, None, :] * (1 - a) + np.array(c1)[None, None, :] * a

def save_rgb(name, arr):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(0.6)).save(os.path.join(OUT, name + ".png")); print("wrote", name)

def grounds():
    n = 512
    Y, X = np.mgrid[0:n, 0:n] / n
    base = lambda fx, fy, seed, p=1.3: noise(n, fx=fx, fy=fy, power=p, seed=seed)
    # --- walking surfaces
    save_rgb("tex_top_sand", rgb(base(6, 6, 31) * 0.6 + np.sin((Y * 14 + base(3, 3, 32) * 1.6) * 2 * np.pi) * 0.06 + base(90, 90, 33, 0.9) * 0.3, (224, 200, 148), (252, 236, 190)))
    planks = 8
    px = (X * planks) % 1; board = np.floor(X * planks)
    wood = base(60, 3, 34, 1.0) * 0.5 + ((board * 37) % 7) / 7 * 0.35
    gapl = np.where((px < 0.04) | (px > 0.96), 0.0, 1.0)
    save_rgb("tex_top_wood", rgb(wood, (150, 104, 62), (212, 164, 108)) * (0.35 + 0.65 * gapl)[..., None])
    c = 4; u = (X * c) % 1; v = ((Y * c) + (np.floor(X * c) % 2) * 0.5) % 1
    joint = np.where((u < 0.035) | (v < 0.035), 0.0, 1.0)
    tone = ((np.floor(X * c) * 13 + np.floor((Y * c) + (np.floor(X * c) % 2) * 0.5) * 7) % 5) / 5
    save_rgb("tex_top_stone", rgb(base(10, 10, 35) * 0.5 + tone * 0.4, (150, 146, 140), (212, 208, 200)) * (0.45 + 0.55 * joint)[..., None])
    save_rgb("tex_top_mud", rgb(base(5, 5, 36) * 0.7 + base(40, 40, 37, 1.0) * 0.3, (112, 92, 60), (170, 150, 100)))
    r_, cc = 8, 8
    fy = (Y * r_) % 1; rr = np.floor(Y * r_); fx_ = ((X * cc) + (rr % 2) * 0.5) % 1
    arc = np.sqrt(np.clip(1 - (fx_ * 2 - 1) ** 2, 0, 1))
    save_rgb("tex_top_tile", rgb(0.3 + 0.6 * arc * (0.5 + 0.5 * fy), (150, 62, 40), (226, 120, 72)) * np.where(fy < 0.1, 0.6, 1.0)[..., None])
    save_rgb("tex_top_moss", rgb(base(7, 7, 38) * 0.6 + base(50, 50, 39, 1.0) * 0.4, (58, 120, 56), (140, 196, 96)))
    grav = base(90, 90, 40, 0.8)
    save_rgb("tex_top_gravel", rgb(grav * 0.7 + base(6, 6, 41) * 0.3, (120, 112, 104), (196, 188, 176)))
    # --- cut faces
    px = (X * 6) % 1
    pil = base(70, 2.5, 42, 1.0) * 0.6 + ((np.floor(X * 6) * 29) % 5) / 5 * 0.3
    save_rgb("tex_face_wood", rgb(pil, (104, 70, 42), (176, 128, 82)) * (0.3 + 0.7 * np.where((px < 0.05) | (px > 0.95), 0.0, 1.0))[..., None] * (0.8 + 0.2 * np.sin(Y * 2 * np.pi * 3))[..., None])
    rows, cols = 10, 5
    fy = (Y * rows) % 1; r2 = np.floor(Y * rows); fx2 = ((X * cols) + (r2 % 2) * 0.5) % 1
    mortar = np.where((fy < 0.1) | (fx2 < 0.045), 0.0, 1.0)
    tone = ((r2 * 17 + np.floor((X * cols) + (r2 % 2) * 0.5) * 11) % 6) / 6
    brick = rgb(tone * 0.6 + base(30, 30, 43, 1.0) * 0.4, (150, 70, 44), (212, 122, 80))
    save_rgb("tex_face_brick", brick * mortar[..., None] + np.array((196, 180, 160))[None, None, :] * (1 - mortar)[..., None] * 0.9)
    crack = np.clip(1 - np.abs(base(6, 6, 44, 1.4) - 0.5) * 20, 0, 1) ** 2
    save_rgb("tex_face_rock", rgb(base(4, 7, 45) * 0.6 + base(24, 24, 46, 1.1) * 0.4, (104, 100, 96), (188, 182, 172)) * (1 - crack * 0.5)[..., None])
    # concrete wall with rows of windows (rooftops, streets)
    conc = rgb(base(8, 8, 47) * 0.5 + 0.3, (170, 166, 160), (226, 222, 214))
    wu = (X * 4) % 1; wv = (Y * 4) % 1
    win = ((wu > 0.22) & (wu < 0.78) & (wv > 0.28) & (wv < 0.8))
    glass = np.array((70, 98, 130))[None, None, :] * (0.8 + 0.4 * (wv[..., None] - 0.28))
    save_rgb("tex_face_concrete", np.where(win[..., None], glass, conc * np.where((wv < 0.06), 0.8, 1.0)[..., None]))
    strata = np.sin((Y * 9 + base(3, 20, 48, 1.5) * 0.8) * 2 * np.pi) * 0.5 + 0.5
    save_rgb("tex_face_sandstone", rgb(strata * 0.5 + base(12, 12, 49) * 0.5, (196, 160, 110), (244, 218, 168)))

if __name__ == "__main__":
    grounds()
