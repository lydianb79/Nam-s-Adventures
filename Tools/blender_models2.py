# Models for levels 2-25 and the ending: themed props, scenery, enemy casts, Nam's friends, the restaurant.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b -P Tools/blender_models2.py -- [preview.png]
#
# Reuses the framework (Model, primitives, palette) from blender_models.py; see that file for conventions:
# -Y is the model's front, +Z up; rigid parts hang off named joints that the game animates.
import bpy, os, sys, math
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["NAM_NO_MAIN"] = "1"
ns = {"__file__": os.path.join(HERE, "blender_models.py"), "__name__": "models"}
exec(compile(open(ns["__file__"]).read(), ns["__file__"], "exec"), ns)
Model, mat, eye, lantern, bamboo_pole, V, PI, R = [ns[k] for k in ("Model", "mat", "eye", "lantern", "bamboo_pole", "V", "PI", "R")]
SKIN, INK, WHITE, GOLD, RED, BAMBOO, BAMBOO_D, WOOD, LEAF, LEAF_D, LEAF_L = [ns[k] for k in ("SKIN", "INK", "WHITE", "GOLD", "RED", "BAMBOO", "BAMBOO_D", "WOOD", "LEAF", "LEAF_D", "LEAF_L")]
cos, sin = math.cos, math.sin

DKW = mat("6E4826", 0.2); PLK = mat("C98A52", 0.3); STONE = mat("B9B3A4", 0.1); STONE_D = mat("A49D8E", 0.1); STONE_L = mat("CFC9BA", 0.1)
PLASTER = mat("FBF6EA", 0.25); BRICK = mat("C8643C", 0.15); BRICK_D = mat("B2532F", 0.15); TILE = mat("D9542B", 0.4); THATCH = mat("C8963C", 0.1)
STEEL = mat("C9CED6", 0.8); DARK = mat("2B2B33", 0.5); BLUE = mat("2F7FE0", 0.6); YEL = mat("FFD12E", 0.6); GRN = mat("3FA65A", 0.5); PINK = mat("F06BA8", 0.5)
ORANGE = mat("FF9A1E", 0.5); SAND = mat("F2E0A8", 0.1); GLASS = mat("BFE4FF", 0.9); BARK = mat("9A7B4F", 0.2); BARK_D = mat("7C6039", 0.2)
def GLOW(col, e=3.0): return mat(col, 0.3, e)
BUILD = []
def model(f): BUILD.append(f); return f

def recolor(builder, name, cmap):
    """Builds an existing model with some colours swapped (enemy colour variants)."""
    def b():
        old = ns["mat"]
        ns["mat"] = lambda col, *a, **k: old(cmap.get(col, col), *a, **k)
        try: m = ns[builder]()
        finally: ns["mat"] = old
        m.name = name; return m
    BUILD.append(b)

def canopy(m, c, r, col=LEAF, col2=LEAF_L, n=7, squash=0.8, rough=(0.08, 2.5)):
    c = V(c); m.sph("root", col, c, (r, r * 0.9, r * squash), seg=18, rough=rough)
    for i in range(n):
        a = i * 2.399; d = V((cos(a), sin(a) * 0.9, 0.25 + 0.5 * ((i * 3) % 4) / 3)) * r * 0.62
        m.sph("root", col2 if i % 2 else col, c + d, (r * 0.55, r * 0.5, r * 0.45), seg=14, rough=rough)

def stilts(m, w, d, h, r=0.06, depth=1.0):
    for sx in (-1, 1):
        for sy in (-1, 1): m.cyl("root", DKW, (w / 2 * sx, d / 2 * sy, -depth), (w / 2 * sx, d / 2 * sy, h), r, seg=8)

def wheel(m, p, r=0.17, axis="y"):
    rot = (PI / 2, 0, 0) if axis == "y" else (0, PI / 2, 0)
    m.torus("root", DARK, p, r, r * 0.42, rot=rot, seg=18);
    q = V(p); o = V((0, 0.05, 0)) if axis == "y" else V((0.05, 0, 0))
    m.cyl("root", STEEL, q - o, q + o, r * 0.6, seg=12)

def fruit_pile(m, c, cols=("FF9A1E", "E0382E", "FFD12E", "8FCB5A"), n=9, r=0.07, spread=0.2):
    c = V(c)
    for i in range(n):
        a = i * 2.399; rr = spread * math.sqrt((i + 0.5) / n)
        m.sph("root", mat(cols[i % len(cols)], 0.5), c + V((cos(a) * rr, sin(a) * rr, r * 0.6 + (spread - rr) * 0.5)), r, seg=10)

# ================================================================================================ small props
@model
def crate():
    m = Model("crate")
    m.box("root", PLK, (0, 0, 0.3), (0.62, 0.62, 0.6), bevel=0.02)
    for z in (0.08, 0.3, 0.52): m.box("root", DKW, (0, -0.315, z), (0.66, 0.02, 0.07), bevel=0.005)
    for x in (-0.3, 0.3): m.box("root", DKW, (x, -0.315, 0.3), (0.06, 0.03, 0.62), bevel=0.005)
    fruit_pile(m, (0, 0, 0.6), n=7, spread=0.22)
    return m

@model
def fruit_basket():
    m = Model("fruit_basket")
    m.cyl("root", mat("D9B27A", 0.15), (0, 0, 0), (0, 0, 0.26), 0.2, 0.3, seg=18); m.torus("root", DKW, (0, 0, 0.26), 0.3, 0.025, seg=18, rseg=6)
    fruit_pile(m, (0, 0, 0.24), cols=("FFB82E", "E0382E", "8FCB5A", "F06BA8"), n=10, r=0.075, spread=0.22)
    return m

@model
def wheelbarrow():
    m = Model("wheelbarrow")
    m.box("root", GRN, (0, 0, 0.42), (0.9, 0.55, 0.3), rot=(0, 0.12, 0), bevel=0.05)
    wheel(m, (-0.55, 0, 0.18), 0.17)
    for sy in (-1, 1):
        m.cap("root", DKW, (-0.5, 0.2 * sy, 0.25), (0.95, 0.27 * sy, 0.62), 0.025, seg=8); m.cyl("root", DKW, (0.3, 0.2 * sy, 0.3), (0.35, 0.2 * sy, 0.0), 0.025, seg=6)
    fruit_pile(m, (0, 0, 0.55), cols=("FFD83A", "FFD83A", "8FCB5A"), n=8, r=0.085, spread=0.25)
    return m

@model
def haybale():
    m = Model("haybale")
    H1 = mat("C8963C", 0.1)
    m.cyl("root", H1, (-0.45, 0, 0.4), (0.45, 0, 0.4), 0.4, seg=20)
    for x in (-0.25, 0.25): m.torus("root", DKW, (x, 0, 0.4), 0.405, 0.015, rot=(0, PI / 2, 0), seg=20, rseg=5)
    return m

@model
def scarecrow():
    m = Model("scarecrow")
    m.cyl("root", WOOD, (0, 0, 0), (0, 0, 1.7), 0.035, seg=6); m.cap("root", WOOD, (-0.6, 0, 1.25), (0.6, 0, 1.25), 0.03, seg=6)
    m.box("root", mat("3D6FD0", 0.2), (0, 0, 1.05), (0.5, 0.2, 0.6), bevel=0.06)
    for sx in (-1, 1): m.cap("root", mat("3D6FD0", 0.2), (0.25 * sx, 0, 1.25), (0.55 * sx, 0, 1.25), 0.07, seg=8); m.sph("root", THATCH, (0.63 * sx, 0, 1.25), 0.07, seg=8)
    m.sph("root", mat("E8D9B0", 0.15), (0, 0, 1.55), 0.19, seg=14); eye(m, "root", 0.07, -0.16, 1.58, 0.035); eye(m, "root", -0.07, -0.16, 1.58, 0.035)
    m.cyl("root", THATCH, (0, 0, 1.68), (0, 0, 1.92), 0.36, 0.0, seg=16); m.cap("root", RED, (-0.06, -0.185, 1.48), (0.06, -0.185, 1.48), 0.012, seg=6)
    return m

@model
def sunflower():
    m = Model("sunflower")
    m.chain("root", LEAF_D, [(0, 0, 0), (0.02, 0, 0.7), (0, -0.03, 1.35)], [0.035, 0.03, 0.025], seg=8)
    for z, a in ((0.45, 0.5), (0.75, 3.3), (1.0, 1.9)): m.ell("root", LEAF, (0, 0, z), (cos(a) * 0.36, sin(a) * 0.36, z + 0.12), 0.11, 0.012, seg=8)
    c = V((0, -0.1, 1.42))
    for i in range(14):
        a = i * 2 * PI / 14; m.ell("root", mat("FFC81E", 0.4, 0.2), c, c + V((cos(a) * 0.3, -0.04, sin(a) * 0.3)), 0.06, 0.02, seg=8)
    m.sph("root", mat("6E4826", 0.2), c + V((0, -0.03, 0)), (0.13, 0.05, 0.13), seg=14)
    return m

@model
def fern():
    m = Model("fern")
    for i in range(9):
        a = i * 2 * PI / 9; d = V((cos(a), sin(a), 0)); p = V((0, 0, 0)); pts = [p.copy()]
        for k in range(5): p = p + d * 0.13 + V((0, 0, 0.12 - k * 0.045)); pts.append(p.copy())
        for k in range(5): m.ell("root", (LEAF, LEAF_L, LEAF_D)[(i + k) % 3], pts[k], pts[k + 1], 0.075 - k * 0.011, 0.01, seg=6)
    return m

@model
def tea_bush():
    m = Model("tea_bush")
    T1 = mat("2F8F45", 0.3); T2 = mat("4FB04A", 0.3)
    m.sph("root", T1, (0, 0, 0.22), (0.42, 0.36, 0.3), seg=16, rough=(0.05, 4)); m.sph("root", T2, (0.12, -0.05, 0.36), (0.26, 0.22, 0.16), seg=12, rough=(0.04, 4))
    m.sph("root", T2, (-0.16, 0.04, 0.34), (0.22, 0.2, 0.15), seg=12, rough=(0.04, 4))
    return m

@model
def tea_basket():
    m = Model("tea_basket")
    m.cyl("root", mat("D9B27A", 0.15), (0, 0, 0), (0, 0, 0.5), 0.2, 0.3, seg=18); m.torus("root", DKW, (0, 0, 0.5), 0.3, 0.025, seg=18, rseg=6)
    m.sph("root", LEAF, (0, 0, 0.5), (0.27, 0.27, 0.12), seg=12, rough=(0.04, 5))
    return m

@model
def stone_lantern():
    m = Model("stone_lantern")
    m.box("root", STONE_D, (0, 0, 0.06), (0.44, 0.44, 0.12), bevel=0.03); m.cyl("root", STONE, (0, 0, 0.1), (0, 0, 0.6), 0.09, seg=10)
    m.box("root", STONE_L, (0, 0, 0.64), (0.4, 0.4, 0.08), bevel=0.02); m.box("root", GLOW("FFD98A", 3.0), (0, 0, 0.8), (0.22, 0.22, 0.22), bevel=0.02)
    for sx in (-1, 1):
        for sy in (-1, 1): m.box("root", STONE, (0.13 * sx, 0.13 * sy, 0.8), (0.05, 0.05, 0.26), bevel=0.01)
    m.cyl("root", STONE_D, (0, 0, 0.92), (0, 0, 1.12), 0.36, 0.05, seg=4); m.sph("root", STONE_L, (0, 0, 1.14), 0.05, seg=8)
    return m

@model
def ruin_column():
    m = Model("ruin_column")
    m.box("root", BRICK_D, (0, 0, 0.1), (0.6, 0.6, 0.2), bevel=0.03)
    m.cyl("root", BRICK, (0, 0, 0.2), (0, 0, 1.5), 0.22, 0.2, seg=12); m.sph("root", BRICK, (0.03, 0, 1.5), (0.2, 0.2, 0.12), seg=10, rough=(0.06, 5))
    m.sph("root", mat("6FA84A", 0.2), (0.1, -0.2, 0.5), (0.12, 0.05, 0.16), seg=8)
    return m

@model
def ruin_wall():
    m = Model("ruin_wall")
    for i, (x, h) in enumerate(((-1.0, 1.5), (-0.5, 1.9), (0.0, 1.3), (0.5, 0.9), (1.0, 1.4))):
        m.box("root", BRICK if i % 2 else BRICK_D, (x, 0, h / 2), (0.52, 0.5, h), bevel=0.03)
    m.box("root", mat("D98A5A", 0.15), (0, 0, 0.12), (2.7, 0.62, 0.24), bevel=0.03)
    for x, z in ((-0.6, 1.3), (0.2, 0.7), (0.9, 1.0)): m.sph("root", mat("6FA84A", 0.2), (x, -0.27, z), (0.16, 0.05, 0.12), seg=8)
    return m

@model
def brick_arch():
    m = Model("brick_arch")
    for sx in (-1, 1): m.box("root", BRICK if sx > 0 else BRICK_D, (0.85 * sx, 0, 1.0), (0.5, 0.55, 2.0), bevel=0.03)
    m.torus("root", BRICK, (0, 0, 2.0), 0.85, 0.27, rot=(PI / 2, 0, 0), seg=20, rseg=8, arc=PI)
    m.box("root", mat("D98A5A", 0.15), (0, 0, 3.0), (2.5, 0.6, 0.25), bevel=0.03)
    return m

@model
def prang():
    m = Model("prang")     # Khmer-style tower
    z = 0
    for w, h in ((2.4, 0.35), (2.0, 0.35), (1.6, 0.4)):
        m.box("root", BRICK_D, (0, 0, z + h / 2), (w, w, h), bevel=0.03); z += h
    m.box("root", BRICK, (0, 0, z + 0.6), (1.3, 1.3, 1.2), bevel=0.04); m.box("root", DARK, (0, -0.66, z + 0.5), (0.4, 0.04, 0.8), bevel=0.02); z += 1.2
    for i in range(6):
        r = 0.72 - i * 0.09; m.cyl("root", BRICK if i % 2 else mat("D98A5A", 0.15), (0, 0, z), (0, 0, z + 0.36), r, r * 0.88, seg=12)
        for k in range(8):
            a = k * PI / 4; m.sph("root", BRICK_D, (cos(a) * r * 0.98, sin(a) * r * 0.98, z + 0.18), (0.1, 0.1, 0.16), seg=6)
        z += 0.36
    m.cyl("root", GOLD, (0, 0, z), (0, 0, z + 0.7), 0.1, 0.0, seg=8)
    return m

@model
def bodhi_tree():
    m = Model("bodhi_tree")
    m.chain("root", BARK, [(0, 0, 0), (0.05, 0, 0.9), (-0.05, 0, 1.7)], [0.34, 0.26, 0.2], seg=12)
    for a in range(5): m.chain("root", BARK_D, [(cos(a * 1.3) * 0.3, sin(a * 1.3) * 0.3, 0.5), (cos(a * 1.3) * 0.55, sin(a * 1.3) * 0.55, 0.0)], [0.1, 0.06], seg=8)
    for p in ((0.8, 0, 2.3), (-0.8, 0.1, 2.4), (0, 0.4, 2.8)): m.cap("root", BARK, (0, 0, 1.6), p, 0.12, 0.07, seg=8)
    canopy(m, (0, 0, 3.0), 1.5, mat("4A9A52", 0.1), mat("5FAE56", 0.1), n=9)
    m.torus("root", mat("FF9A1E", 0.4), (0, 0, 0.9), 0.28, 0.035, seg=16, rseg=6)       # saffron sash
    return m

@model
def jungle_tree():
    m = Model("jungle_tree")
    m.chain("root", BARK, [(0, 0, 0), (0.08, 0, 1.3), (0, 0, 2.6)], [0.3, 0.2, 0.16], seg=12)
    for a in range(4): m.chain("root", BARK_D, [(cos(a * 1.6) * 0.2, sin(a * 1.6) * 0.2, 0.7), (cos(a * 1.6) * 0.6, sin(a * 1.6) * 0.6, 0.0)], [0.09, 0.03], seg=8)   # buttress roots
    canopy(m, (0, 0, 3.4), 1.35, LEAF_D, LEAF, n=8)
    for i in range(5):
        a = i * 1.3; x, y = cos(a) * 0.9, sin(a) * 0.8
        m.chain("root", mat("4A9A52", 0.1), [(x, y, 3.0), (x * 1.05, y * 1.05, 2.3), (x * 1.02, y, 1.7 + 0.2 * (i % 2))], [0.03, 0.025, 0.012], seg=6)        # lianas
    return m

@model
def pine():
    m = Model("pine")
    m.cyl("root", BARK_D, (0, 0, 0), (0, 0, 1.0), 0.11, 0.08, seg=8)
    for i in range(5):
        r = 0.85 - i * 0.15; m.cyl("root", mat("2F8F45", 0.3) if i % 2 else mat("3E9B4A", 0.5), (0, 0, 0.6 + i * 0.5), (0, 0, 1.4 + i * 0.5), r, 0.0, seg=10)
    return m

@model
def durian_tree():
    m = Model("durian_tree")
    m.chain("root", BARK, [(0, 0, 0), (0.04, 0, 1.0), (0, 0, 1.9)], [0.2, 0.15, 0.12], seg=10)
    canopy(m, (0, 0, 2.6), 1.1, LEAF_D, LEAF, n=7, squash=1.0)
    for i in range(5):
        a = i * 1.3 + 0.4; p = V((cos(a) * 0.6, sin(a) * 0.5 - 0.2, 1.75 + 0.12 * (i % 2)))
        m.cyl("root", BARK_D, p + V((0, 0, 0.3)), p, 0.012, seg=5); m.sph("root", mat("A9B63A", 0.3), p + V((0, 0, -0.14)), (0.15, 0.15, 0.18), seg=8, rough=(0.04, 12))
    return m

@model
def rubber_tree():
    m = Model("rubber_tree")
    T = mat("A79C92", 0.2)
    m.chain("root", T, [(0, 0, 0), (0.06, 0, 1.6), (0, 0, 3.2)], [0.16, 0.12, 0.09], seg=10)
    m.torus("root", DKW, (0.02, 0, 1.0), 0.14, 0.012, rot=(0.5, 0, 0), seg=12, rseg=5); m.cyl("root", DARK, (0.0, -0.17, 0.8), (0.0, -0.17, 0.93), 0.07, 0.085, seg=10)     # tapping cut + cup
    canopy(m, (0, 0, 3.7), 0.95, LEAF, LEAF_L, n=6, squash=0.7)
    return m

@model
def mangrove():
    m = Model("mangrove")
    m.chain("root", BARK_D, [(0, 0, 0.9), (0.05, 0, 1.6), (0, 0, 2.2)], [0.16, 0.13, 0.1], seg=10)
    for i in range(9):
        a = i * 2 * PI / 9; r = 0.7 + 0.25 * (i % 3) / 2
        m.chain("root", BARK, [(0, 0, 1.0), (cos(a) * r * 0.55, sin(a) * r * 0.55, 0.75), (cos(a) * r, sin(a) * r, -0.5)], [0.07, 0.055, 0.035], seg=8)
    canopy(m, (0, 0, 2.6), 0.95, mat("3E9B4A", 0.5), LEAF, n=7, squash=0.6)
    return m

@model
def bamboo_tall():
    m = Model("bamboo_tall")
    G = mat("6FB24A", 0.45); G2 = mat("4E8E38", 0.4)
    for i, (x, y, h, lean) in enumerate(((0, 0, 6.5, 0.04), (0.3, 0.1, 5.6, 0.07), (-0.28, 0.06, 6.0, -0.05), (0.1, -0.2, 5.0, 0.02))):
        m.cyl("root", G, (x, y, 0), (x + lean * h, y, h), 0.075, 0.05, seg=10)
        for k in range(1, 11): m.torus("root", G2, (x + lean * h * k / 11, y, h * k / 11), 0.072, 0.015, seg=10, rseg=5)
        for k in range(7):
            t = 0.6 + k * 0.058; a = k * 2.4 + i; p = V((x + lean * h * t, y, h * t)); d = V((cos(a), sin(a), 0.2)).normalized()
            m.ell("root", LEAF if k % 2 else LEAF_L, p, p + d * 0.6, 0.07, 0.01, seg=8)
    return m

@model
def stalagmite():
    m = Model("stalagmite")
    for x, y, h, r in ((0, 0, 1.5, 0.28), (0.3, 0.1, 0.9, 0.18), (-0.28, -0.05, 0.7, 0.16)):
        m.cyl("root", STONE if h > 1 else STONE_D, (x, y, 0), (x, y, h), r, 0.02, seg=10); m.sph("root", STONE_L, (x, y, 0.05), (r * 1.15, r * 1.15, 0.1), seg=10)
    return m

@model
def stalactite():
    m = Model("stalactite")          # hangs: tip at the bottom (enemy that drops)
    m.joint("face", (0, -0.2, 0.75))
    m.cyl("root", STONE, (0, 0, 1.15), (0, 0, 0.05), 0.34, 0.02, seg=12); m.sph("root", STONE_D, (0, 0, 1.12), (0.36, 0.36, 0.12), seg=12)
    for sx in (-1, 1): eye(m, "face", 0.1 * sx, -0.26, 0.85, 0.06, look=(-0.2 * sx, -0.2)); m.cap("face", INK, (0.03 * sx, -0.3, 0.92), (0.17 * sx, -0.27, 0.98), 0.02)
    return m

@model
def crystal():
    m = Model("crystal")
    C1 = mat("7FE8FF", 0.9, 2.0); C2 = mat("B48CFF", 0.9, 2.0)
    for i, (x, y, h, r, tilt) in enumerate(((0, 0, 0.9, 0.14, 0), (0.18, 0.05, 0.6, 0.1, 0.35), (-0.17, 0.02, 0.5, 0.09, -0.4), (0.03, -0.14, 0.4, 0.08, 0.1))):
        top = V((x + sin(tilt) * h, y, cos(tilt) * h))
        m.cyl("root", C1 if i % 2 == 0 else C2, (x, y, 0), top * 0.8 + V((x, y, 0)) * 0.2, r, r * 0.9, seg=6); m.cyl("root", C1 if i % 2 == 0 else C2, top * 0.8 + V((x, y, 0)) * 0.2, top, r * 0.9, 0.0, seg=6)
    m.sph("root", STONE_D, (0, 0, 0.03), (0.35, 0.3, 0.08), seg=10, rough=(0.03, 6))
    return m

@model
def pool_rock():
    m = Model("pool_rock")
    m.sph("root", STONE, (0, 0, 0.3), (1.1, 0.8, 0.5), seg=20, rough=(0.14, 2)); m.sph("root", STONE_D, (0.9, 0.2, 0.2), (0.6, 0.5, 0.35), seg=14, rough=(0.1, 3))
    m.sph("root", mat("5FE8D8", 0.9, 0.3), (-0.1, -0.1, 0.72), (0.6, 0.42, 0.06), seg=16)
    m.sph("root", mat("6FA84A", 0.2), (-0.8, -0.5, 0.25), (0.3, 0.12, 0.2), seg=8)
    return m

@model
def waterfall():
    m = Model("waterfall")
    m.sph("root", STONE, (0, 0.6, 2.6), (2.4, 1.3, 2.9), seg=32, rough=(0.3, 1.0, 0.4)); m.sph("root", STONE_D, (-1.6, 0.3, 1.4), (1.2, 1.0, 1.7), seg=20, rough=(0.25, 1.4))
    m.sph("root", STONE_L, (1.7, 0.3, 1.2), (1.1, 1.0, 1.5), seg=20, rough=(0.25, 1.4))
    W1 = mat("DFFAFF", 0.9, 1.0); W2 = mat("9FE8F0", 0.9, 0.6)
    for i, x in enumerate((-0.45, -0.15, 0.15, 0.45)):
        m.chain("root", W1 if i % 2 else W2, [(x, -0.5, 5.0), (x * 1.1, -0.85, 4.2), (x * 1.2, -1.0, 2.2), (x * 1.3, -1.05, 0.1)], [0.2, 0.22, 0.25, 0.3], seg=10)
    for i in range(7): m.sph("root", WHITE, (-0.8 + i * 0.27, -1.1, 0.12), (0.26, 0.2, 0.16), seg=10)
    for x, y, z, s in ((0, 0.2, 5.4, 1.1), (-1.5, 0.2, 3.3, 0.7), (1.7, 0.2, 2.9, 0.7), (1.0, 0, 5.0, 0.6)): m.sph("root", mat("5FAE56", 0.1), (x, y, z), (s, s * 0.8, s * 0.45), seg=12, rough=(0.1, 3))
    return m

@model
def elephant():
    m = Model("elephant")
    E = mat("8E8A94", 0.25); E2 = mat("A6A2AC", 0.25); TUSK = mat("F3EDDC", 0.6)
    m.joint("head", (0, -1.0, 1.7))
    m.sph("root", E, (0, 0, 1.45), (0.85, 1.25, 0.85), seg=24)
    for sx in (-1, 1):
        for y in (-0.7, 0.7): m.cyl("root", E, (0.45 * sx, y, 1.0), (0.45 * sx, y, 0.0), 0.24, 0.26, seg=12); m.sph("root", E2, (0.45 * sx, y - 0.08, 0.06), (0.26, 0.3, 0.07), seg=10)
        m.sph("head", E2, (0.72 * sx, -1.05, 1.85), (0.1, 0.5, 0.62), rot=(0, 0.25 * sx, 0.3 * sx), seg=16)
        eye(m, "head", 0.36 * sx, -1.72, 1.92, 0.06)
        m.chain("head", TUSK, [(0.26 * sx, -1.7, 1.45), (0.33 * sx, -2.0, 1.3), (0.3 * sx, -2.2, 1.45)], [0.07, 0.055, 0.015], seg=8)
    m.sph("head", E, (0, -1.3, 1.85), (0.6, 0.62, 0.62), seg=20)
    m.chain("head", E, [(0, -1.8, 1.7), (0, -2.05, 1.2), (0, -2.05, 0.65), (0, -2.3, 0.4), (0, -2.5, 0.6)], [0.2, 0.17, 0.13, 0.1, 0.07], seg=10)
    m.chain("root", E, [(0, 1.2, 1.5), (0, 1.4, 1.0), (0, 1.4, 0.6)], [0.05, 0.04, 0.03], seg=6)
    m.box("root", RED, (0, 0, 2.28), (1.2, 1.0, 0.06), bevel=0.02); m.box("root", GOLD, (0, 0, 2.31), (0.9, 0.7, 0.04), bevel=0.01)
    return m

# ================================================================================================ market, street, city
def awning(m, c, w, d, h, cols=("E0382E", "FFFFFF"), stripes=6):
    for i in range(stripes):
        x = -w / 2 + (i + 0.5) * w / stripes
        m.box("root", mat(cols[i % len(cols)], 0.3), (c[0] + x, c[1], c[2] + h), (w / stripes, d, 0.05), rot=(0.25, 0, 0), bevel=0.0)

@model
def fruit_stall():
    m = Model("fruit_stall")
    m.box("root", PLK, (0, 0, 0.45), (1.8, 0.8, 0.9), bevel=0.03); m.box("root", DKW, (0, -0.41, 0.45), (1.84, 0.02, 0.08), bevel=0.0)
    for i, x in enumerate((-0.6, 0, 0.6)): fruit_pile(m, (x, -0.05, 0.9), cols=(("FF9A1E", "FFB82E"), ("E0382E", "F06BA8"), ("8FCB5A", "FFD83A"))[i], n=10, r=0.08, spread=0.24)
    for sx in (-1, 1): m.cyl("root", DKW, (0.85 * sx, 0.35, 0.9), (0.85 * sx, 0.35, 2.0), 0.03, seg=6); m.cyl("root", DKW, (0.85 * sx, -0.35, 0.9), (0.85 * sx, -0.5, 1.8), 0.03, seg=6)
    awning(m, (0, -0.1, 0), 2.1, 1.2, 1.95, ("3FA65A", "FFFFFF"))
    return m

@model
def awning_stall():
    m = Model("awning_stall")
    m.box("root", BLUE, (0, 0, 0.4), (1.6, 0.7, 0.8), bevel=0.03); m.box("root", STEEL, (0, 0, 0.82), (1.7, 0.8, 0.05), bevel=0.01)
    for i in range(5): m.cyl("root", mat(("E0382E", "FFD12E", "3FA65A", "FF9A1E", "F06BA8")[i], 0.6), (-0.6 + i * 0.3, -0.1, 0.84), (-0.6 + i * 0.3, -0.1, 1.05), 0.07, seg=10)
    for sx in (-1, 1): m.cyl("root", STEEL, (0.8 * sx, 0.3, 0.8), (0.8 * sx, 0.3, 2.1), 0.025, seg=6); m.cyl("root", STEEL, (0.8 * sx, -0.3, 0.8), (0.8 * sx, -0.6, 1.9), 0.025, seg=6)
    awning(m, (0, -0.15, 0), 2.0, 1.3, 2.05, ("E0382E", "FFD12E"))
    return m

@model
def market_stall():
    m = Model("market_stall")
    m.box("root", mat("7A5234", 0.3), (0, 0, 0.42), (2.0, 0.8, 0.84), bevel=0.03); m.box("root", STEEL, (0, 0, 0.86), (2.1, 0.9, 0.05), bevel=0.01)
    for i in range(6): m.sph("root", mat(("FF9A1E", "E23B2E", "D9B27A")[i % 3], 0.5), (-0.75 + i * 0.3, -0.1, 0.95), (0.11, 0.11, 0.07), seg=10)
    for sx in (-1, 1): m.cyl("root", DKW, (1.0 * sx, 0.35, 0), (1.0 * sx, 0.35, 2.3), 0.035, seg=6); m.cyl("root", DKW, (1.0 * sx, -0.4, 0), (1.0 * sx, -0.4, 2.1), 0.035, seg=6)
    awning(m, (0, 0, 0), 2.4, 1.3, 2.25, ("C8322C", "FFF3D2"))
    for i in range(7): m.sph("root", GLOW(("FFD98A", "FF8FB0", "9FE8FF")[i % 3], 4.0), (-0.9 + i * 0.3, -0.62, 1.95), 0.06, seg=8)
    m.cap("root", DARK, (-1.0, -0.62, 2.0), (1.0, -0.62, 2.0), 0.008, seg=5)
    return m

@model
def noodle_cart():
    m = Model("noodle_cart")
    m.box("root", STEEL, (0, 0, 0.6), (1.4, 0.7, 0.5), bevel=0.03); m.box("root", GLASS, (0, -0.05, 1.15), (1.2, 0.5, 0.6), bevel=0.02)
    m.cyl("root", STEEL, (-0.35, 0, 0.85), (-0.35, 0, 1.05), 0.2, seg=14); m.sph("root", WHITE, (-0.35, 0, 1.1), (0.22, 0.22, 0.14), seg=10)      # steam pot
    for i in range(4): m.sph("root", mat("F3E6C8", 0.3), (0.1 + i * 0.15, -0.1, 0.95), (0.07, 0.07, 0.05), seg=8)
    for x in (-0.5, 0.5): wheel(m, (x, -0.36, 0.2), 0.2)
    m.box("root", GLOW("FF4A3A", 3.0), (0, -0.33, 1.6), (1.1, 0.04, 0.24), bevel=0.02); m.box("root", RED, (0, 0, 1.5), (1.4, 0.75, 0.06), bevel=0.02)
    return m

@model
def grill_cart():
    m = Model("grill_cart")
    m.box("root", DARK, (0, 0, 0.6), (1.1, 0.6, 0.3), bevel=0.03); m.box("root", GLOW("FF7A1E", 3.5), (0, 0, 0.77), (0.95, 0.45, 0.04), bevel=0.0)
    for i in range(6):
        x = -0.4 + i * 0.16; m.cap("root", WOOD, (x, -0.28, 0.82), (x, 0.28, 0.82), 0.008, seg=5)
        for k in range(3): m.sph("root", mat(("B5653A", "E0382E", "8FCB5A")[k], 0.4), (x, -0.12 + k * 0.12, 0.83), 0.04, seg=8)
    for sx in (-1, 1): m.cyl("root", STEEL, (0.45 * sx, 0, 0), (0.45 * sx, 0, 0.5), 0.03, seg=6); wheel(m, (0.45 * sx, -0.3, 0.14), 0.14)
    return m

@model
def neon_sign():
    m = Model("neon_sign")
    m.cyl("root", DARK, (0, 0, 0), (0, 0, 3.2), 0.05, seg=8)
    for i, (z, c, w) in enumerate(((2.7, "FF4AC8", 1.0), (2.1, "4AE8FF", 0.8), (1.55, "FFE04A", 0.9))):
        m.box("root", DARK, (0.1 + w / 2, 0, z), (w, 0.1, 0.42), bevel=0.02); m.box("root", GLOW(c, 5.0), (0.1 + w / 2, -0.06, z), (w - 0.12, 0.03, 0.3), bevel=0.03)
        for k in range(3): m.box("root", DARK, (0.3 + k * (w - 0.3) / 2.5, -0.08, z), (0.07, 0.02, 0.2), bevel=0.0)
    return m

@model
def lantern_row():
    m = Model("lantern_row")
    for sx in (-1, 1): m.cyl("root", DKW, (1.8 * sx, 0, 0), (1.8 * sx, 0, 2.5), 0.045, seg=8)
    pts = [V((-1.8 + 3.6 * i / 8, 0, 2.45 - 0.4 * sin(i / 8 * PI))) for i in range(9)]
    m.chain("root", DARK, pts, [0.01] * 9, seg=5)
    for i in range(1, 8): lantern(m, "root", pts[i] - V((0, 0, 0.3)), ("E0382E", "FFD95A", "E0382E", "FF8FB0")[i % 4], 3.0, 0.62)
    return m

@model
def lamp_post():
    m = Model("lamp_post")
    m.cyl("root", DARK, (0, 0, 0), (0, 0, 0.25), 0.12, 0.07, seg=10); m.cyl("root", DARK, (0, 0, 0.2), (0, 0, 2.6), 0.045, seg=8)
    m.chain("root", DARK, [(0, 0, 2.6), (0.15, 0, 2.85), (0.45, 0, 2.9)], [0.04, 0.035, 0.03], seg=8)
    m.cyl("root", DARK, (0.45, 0, 2.86), (0.45, 0, 2.7), 0.06, 0.16, seg=10); m.sph("root", GLOW("FFE9B0", 6.0), (0.45, 0, 2.62), 0.12, seg=12)
    return m

@model
def seafood_sign():
    m = Model("seafood_sign")
    for sx in (-1, 1): m.cyl("root", DKW, (0.8 * sx, 0, 0), (0.8 * sx, 0, 2.2), 0.05, seg=8)
    m.box("root", mat("2A5DB0", 0.5), (0, 0, 1.75), (1.9, 0.1, 0.9), bevel=0.04); m.box("root", GLOW("FFE9B0", 2.0), (0, -0.06, 1.75), (1.7, 0.02, 0.72), bevel=0.03)
    # a big red crab on the board
    m.sph("root", mat("EB5338", 0.5), (0, -0.1, 1.72), (0.36, 0.06, 0.24), seg=16)
    for sx in (-1, 1):
        m.chain("root", mat("C83A28", 0.45), [(0.3 * sx, -0.1, 1.8), (0.5 * sx, -0.1, 1.95), (0.58 * sx, -0.1, 2.05)], [0.05, 0.05, 0.08], seg=8)
        for k in range(3): m.cap("root", mat("C83A28", 0.45), (0.3 * sx, -0.1, 1.68 - k * 0.07), (0.56 * sx, -0.1, 1.55 - k * 0.09), 0.025, seg=6)
        eye(m, "root", 0.1 * sx, -0.14, 1.92, 0.05)
    return m

@model
def shophouse():
    m = Model("shophouse")      # 3-storey Sino-Portuguese shophouse, ~4.2 wide
    cols = ("F2C84A", "7FC8B8", "F09AB0", "FBF6EA"); c = cols[int(R.uniform(0, 4))]
    m.box("root", mat(c, 0.25), (0, 0, 3.0), (4.2, 3.0, 6.0), bevel=0.04)
    m.box("root", DARK, (0, -1.5, 0.9), (3.4, 0.1, 1.7), bevel=0.02); m.box("root", GLOW("FFD98A", 1.5), (0, -1.58, 0.9), (3.0, 0.08, 1.3), bevel=0.02)
    awning(m, (0, -1.9, 0), 4.2, 1.0, 2.0, ("C8322C", "FFF3D2"), 8)
    for fl in (2.9, 4.6):
        for x in (-1.3, 0, 1.3):
            m.box("root", mat("3A5A8E", 0.7), (x, -1.53, fl), (0.75, 0.1, 1.05), bevel=0.02); m.torus("root", PLASTER, (x, -1.56, fl + 0.5), 0.375, 0.05, rot=(PI / 2, 0, 0), seg=14, rseg=6, arc=PI)
            for sx in (-1, 1): m.box("root", mat("2F9A6B", 0.45), (x + 0.5 * sx, -1.62, fl), (0.2, 0.04, 1.0), rot=(0, 0, 0.5 * sx), bevel=0.01)
        m.box("root", PLASTER, (0, -1.55, fl - 0.65), (4.3, 0.2, 0.12), bevel=0.02)
    m.box("root", PLASTER, (0, -1.5, 6.1), (4.4, 0.3, 0.3), bevel=0.03); m.prism("root", TILE, (0, 0, 6.0), 4.3, 1.6, 0.9)
    return m

@model
def skyscraper():
    m = Model("skyscraper")
    c = ("5A7A9E", "7A8AA8", "4A6A8A")[int(R.uniform(0, 3))]; w = R.uniform(2.6, 3.6); h = R.uniform(10, 16)
    m.box("root", mat(c, 0.7), (0, 0, h / 2), (w, w, h), bevel=0.05)
    for i in range(int(h / 0.9)):
        m.box("root", GLOW("FFE9B0", 1.2) if (i * 7) % 3 == 0 else mat("9FC4E8", 0.9), (0, -w / 2 - 0.03, 0.8 + i * 0.9), (w * 0.84, 0.1, 0.45), bevel=0.0)
    m.box("root", mat(c, 0.7), (0, 0, h + 0.4), (w * 0.6, w * 0.6, 0.8), bevel=0.05); m.cyl("root", STEEL, (0, 0, h + 0.8), (0, 0, h + 2.4), 0.04, seg=6)
    m.sph("root", GLOW("FF4A3A", 5.0), (0, 0, h + 2.4), 0.08, seg=8)
    return m

@model
def water_tank():
    m = Model("water_tank")
    for sx in (-1, 1):
        for sy in (-1, 1): m.cyl("root", STEEL, (0.4 * sx, 0.4 * sy, 0), (0.4 * sx, 0.4 * sy, 0.8), 0.03, seg=6)
    m.cyl("root", mat("3D6FD0", 0.5), (0, 0, 0.8), (0, 0, 1.9), 0.6, seg=20); m.cyl("root", mat("2A5DB0", 0.5), (0, 0, 1.9), (0, 0, 2.15), 0.6, 0.1, seg=20)
    for z in (1.1, 1.5): m.torus("root", STEEL, (0, 0, z), 0.61, 0.02, seg=20, rseg=5)
    return m

@model
def antenna():
    m = Model("antenna")
    m.cyl("root", STEEL, (0, 0, 0), (0, 0, 3.0), 0.03, seg=6)
    for z, w in ((2.8, 0.9), (2.5, 0.7), (2.2, 0.5)): m.cap("root", STEEL, (-w / 2, 0, z), (w / 2, 0, z), 0.015, seg=5)
    m.sph("root", STEEL, (0.2, -0.1, 1.5), (0.4, 0.12, 0.4), rot=(0.4, 0, 0), seg=14, cut=((0, -0.1, 0), (0, -1, 0.4))); m.sph("root", GLOW("FF4A3A", 4.0), (0, 0, 3.02), 0.05, seg=8)
    return m

@model
def clothesline():
    m = Model("clothesline")
    for sx in (-1, 1): m.cyl("root", STEEL, (1.3 * sx, 0, 0), (1.3 * sx, 0, 1.9), 0.03, seg=6)
    m.cap("root", DARK, (-1.3, 0, 1.85), (1.3, 0, 1.85), 0.008, seg=5)
    for i, (x, c, w, hh) in enumerate(((-0.9, "FFFFFF", 0.5, 0.6), (-0.3, "E0382E", 0.4, 0.45), (0.25, "2F7FE0", 0.5, 0.7), (0.85, "FFD12E", 0.4, 0.5))):
        m.box("root", mat(c, 0.2), (x, 0, 1.83 - hh / 2), (w, 0.02, hh), rot=(0.08 * (i - 1.5), 0, 0), bevel=0.0)
    return m

@model
def flowerpot_big():
    m = Model("flowerpot_big")
    m.cyl("root", mat("C9683E", 0.2), (0, 0, 0), (0, 0, 0.4), 0.2, 0.3, seg=14); m.torus("root", mat("9C4A2A", 0.2), (0, 0, 0.4), 0.3, 0.035, seg=14, rseg=6)
    canopy(m, (0, 0, 0.75), 0.36, LEAF, LEAF_L, n=5)
    for i in range(5): a = i * 1.3; m.sph("root", mat(("F06BA8", "FFD12E")[i % 2], 0.4), (cos(a) * 0.3, sin(a) * 0.3, 0.85), 0.07, seg=8)
    return m

@model
def flowerpot():
    m = Model("flowerpot")          # enemy: falls from a balcony
    m.joint("face", (0, -0.3, 0.45))
    m.cyl("root", mat("C9683E", 0.2), (0, 0, 0.05), (0, 0, 0.75), 0.3, 0.44, seg=16); m.torus("root", mat("9C4A2A", 0.2), (0, 0, 0.75), 0.44, 0.05, seg=16, rseg=6)
    canopy(m, (0, 0, 1.0), 0.34, LEAF, LEAF_L, n=4)
    for i in range(4): a = i * 1.6; m.sph("root", PINK, (cos(a) * 0.26, sin(a) * 0.26, 1.12), 0.08, seg=8)
    for sx in (-1, 1): eye(m, "face", 0.13 * sx, -0.38, 0.5, 0.075, look=(-0.2 * sx, -0.15)); m.cap("face", INK, (0.03 * sx, -0.44, 0.58), (0.22 * sx, -0.41, 0.66), 0.024)
    m.cap("face", INK, (-0.09, -0.4, 0.33), (0.09, -0.4, 0.33), 0.016)
    return m

@model
def bucket():
    m = Model("bucket")             # enemy: a full bucket of water tipping from above
    m.joint("face", (0, -0.3, 0.5))
    m.cyl("root", mat("2F7FE0", 0.6), (0, 0, 0.05), (0, 0, 0.9), 0.32, 0.46, seg=18); m.torus("root", mat("2A5DB0", 0.5), (0, 0, 0.9), 0.46, 0.035, seg=18, rseg=6)
    m.sph("root", mat("9FE8FF", 0.9, 0.5), (0, 0, 0.9), (0.42, 0.42, 0.08), seg=14); m.torus("root", STEEL, (0, 0, 0.95), 0.46, 0.015, rot=(PI / 2, 0, 0), seg=16, rseg=5, arc=PI)
    for sx in (-1, 1): eye(m, "face", 0.13 * sx, -0.4, 0.55, 0.075, look=(-0.2 * sx, -0.15)); m.cap("face", INK, (0.03 * sx, -0.46, 0.63), (0.22 * sx, -0.43, 0.71), 0.024)
    return m

@model
def coconut():
    m = Model("coconut")            # enemy: drops from above
    m.joint("face", (0, -0.4, 0.58))
    m.sph("root", mat("7A5234", 0.25), (0, 0, 0.58), (0.5, 0.5, 0.54), seg=20, rough=(0.03, 8))
    for i in range(3): a = i * 2.1 + 0.5; m.ell("root", LEAF_D, (0, 0, 1.05), (cos(a) * 0.4, sin(a) * 0.4, 1.2), 0.1, 0.02, seg=8)
    for sx in (-1, 1): eye(m, "face", 0.15 * sx, -0.47, 0.64, 0.085, look=(-0.2 * sx, -0.15)); m.cap("face", INK, (0.04 * sx, -0.53, 0.7), (0.26 * sx, -0.5, 0.8), 0.026)
    m.sph("face", INK, (0, -0.5, 0.42), (0.07, 0.03, 0.05), seg=8)
    return m

@model
def water_barrel():
    m = Model("water_barrel")
    m.cyl("root", mat("2F7FE0", 0.6), (0, 0, 0), (0, 0, 0.9), 0.36, seg=18)
    for z in (0.25, 0.65): m.torus("root", mat("2A5DB0", 0.5), (0, 0, z), 0.365, 0.03, seg=18, rseg=6)
    m.sph("root", mat("9FE8FF", 0.9, 0.5), (0, 0, 0.9), (0.33, 0.33, 0.05), seg=14); m.cyl("root", mat("E0382E", 0.6), (0.15, -0.1, 0.9), (0.2, -0.2, 1.2), 0.05, seg=8)
    return m

@model
def pickup_truck():
    m = Model("pickup_truck")
    C = mat("E0382E", 0.75)
    m.box("root", C, (0, 0, 0.7), (4.0, 1.6, 0.6), bevel=0.1); m.box("root", C, (-0.9, 0, 1.35), (1.5, 1.5, 0.8), bevel=0.15); m.box("root", GLASS, (-0.9, -0.76, 1.4), (1.2, 0.03, 0.5), bevel=0.03)
    m.box("root", DARK, (1.0, 0, 1.02), (1.9, 1.4, 0.06), bevel=0.0)
    for x in (-1.3, 1.3): wheel(m, (x, -0.8, 0.36), 0.36); wheel(m, (x, 0.8, 0.36), 0.36)
    m.sph("root", GLOW("FFF6C8", 3.0), (-2.0, -0.5, 0.75), (0.05, 0.14, 0.1), seg=8)
    for i, x in enumerate((0.5, 1.0, 1.5)): m.cyl("root", mat("2F7FE0", 0.6), (x, 0.1 * (i - 1), 1.05), (x, 0.1 * (i - 1), 1.6), 0.22, seg=12)          # water barrels in the back
    return m

@model
def train():
    m = Model("train")      # the market train
    Yc = mat("FFD12E", 0.6); Bc = mat("2A5DB0", 0.6)
    m.box("root", Yc, (0, 0, 1.55), (7.0, 1.8, 1.5), bevel=0.12); m.box("root", Bc, (0, 0, 0.75), (7.0, 1.84, 0.5), bevel=0.06); m.box("root", STEEL, (0, 0, 2.36), (6.8, 1.6, 0.14), bevel=0.05)
    for i in range(7): m.box("root", GLASS, (-2.7 + i * 0.9, -0.91, 1.75), (0.6, 0.03, 0.6), bevel=0.04)
    m.box("root", RED, (0, -0.92, 1.22), (7.0, 0.02, 0.12), bevel=0.0)
    for x in (-2.6, -1.9, 1.9, 2.6): wheel(m, (x, -0.8, 0.32), 0.32); wheel(m, (x, 0.8, 0.32), 0.32)
    m.sph("root", GLOW("FFF6C8", 4.0), (-3.5, 0, 1.3), (0.05, 0.18, 0.18), seg=10)
    m.box("root", DKW, (0, 0, 0.03), (8.0, 0.1, 0.06), bevel=0.0)
    return m

# ================================================================================================ festival, water, coast
@model
def lanna_umbrella():
    m = Model("lanna_umbrella")
    m.cyl("root", BAMBOO, (0, 0, 0), (0.25, 0, 1.9), 0.03, seg=6)
    c = V((0.25, 0, 1.9)); col = ("E0382E", "FFD12E", "F06BA8", "3FA65A")[int(R.uniform(0, 4))]
    m.cyl("root", mat(col, 0.4), c - V((0, 0, 0.3)), c + V((0, 0, 0.05)), 0.95, 0.03, seg=20)
    for i in range(10): a = i * PI / 5; m.sph("root", mat("FFF3D2", 0.4), c + V((cos(a) * 0.6, sin(a) * 0.6, -0.16)), (0.09, 0.09, 0.02), seg=8)
    m.sph("root", GOLD, c + V((0, 0, 0.08)), 0.05, seg=8)
    return m

@model
def tung():
    m = Model("tung")       # Lanna temple banner
    m.cyl("root", BAMBOO, (0, 0, 0), (0, 0, 3.0), 0.035, seg=6); m.cap("root", BAMBOO, (0, 0, 2.9), (0.5, 0, 2.9), 0.02, seg=6)
    for i, c in enumerate(("E0382E", "FFD12E", "FFFFFF", "3FA65A", "E0382E", "FFD12E")):
        m.box("root", mat(c, 0.2), (0.3, 0, 2.7 - i * 0.36), (0.34, 0.015, 0.34), bevel=0.0)
    m.cyl("root", RED, (0.3, 0, 0.72), (0.3, 0, 0.5), 0.06, 0.0, seg=6)
    return m

@model
def sky_lantern():
    m = Model("sky_lantern")
    m.cyl("root", GLOW("FFC870", 3.0), (0, 0, 0), (0, 0, 0.5), 0.2, 0.26, seg=14, caps=False); m.sph("root", GLOW("FFC870", 3.0), (0, 0, 0.5), (0.26, 0.26, 0.14), seg=14)
    m.sph("root", GLOW("FFF2A0", 8.0), (0, 0, 0.06), 0.07, seg=8)
    return m

@model
def krathong():
    m = Model("krathong")       # floating banana-leaf basket with a candle
    m.cyl("root", LEAF_D, (0, 0, 0), (0, 0, 0.1), 0.22, 0.26, seg=14)
    for i in range(10): a = i * PI / 5; m.ell("root", LEAF if i % 2 else LEAF_L, (cos(a) * 0.2, sin(a) * 0.2, 0.08), (cos(a) * 0.34, sin(a) * 0.34, 0.24), 0.07, 0.015, seg=6)
    for i in range(6): a = i * PI / 3; m.sph("root", mat(("F06BA8", "FFD12E", "FF9A1E")[i % 3], 0.4), (cos(a) * 0.12, sin(a) * 0.12, 0.13), 0.045, seg=8)
    m.cyl("root", mat("FFF3D2", 0.3), (0, 0, 0.1), (0, 0, 0.3), 0.02, seg=6); m.sph("root", GLOW("FFD060", 8.0), (0, 0, 0.34), (0.03, 0.03, 0.055), seg=8)
    return m

@model
def krathong_stand():
    m = Model("krathong_stand")
    m.box("root", PLK, (0, 0, 0.4), (1.3, 0.6, 0.8), bevel=0.03); m.box("root", mat("F06BA8", 0.3), (0, -0.31, 0.5), (1.3, 0.02, 0.5), bevel=0.0)
    for x in (-0.4, 0, 0.4):
        m.cyl("root", LEAF_D, (x, 0, 0.8), (x, 0, 0.86), 0.13, 0.16, seg=10); m.sph("root", mat("FFD12E", 0.4), (x, 0, 0.9), 0.07, seg=8); m.sph("root", GLOW("FFD060", 6.0), (x, 0, 1.04), 0.03, seg=6)
    return m

@model
def pavilion():
    m = Model("pavilion")       # royal pavilion in the cave
    m.box("root", PLASTER, (0, 0, 0.15), (2.6, 2.0, 0.3), bevel=0.04)
    for sx in (-1, 1):
        for sy in (-1, 1): m.cyl("root", RED, (1.0 * sx, 0.7 * sy, 0.3), (1.0 * sx, 0.7 * sy, 1.9), 0.07, seg=10); m.cyl("root", GOLD, (1.0 * sx, 0.7 * sy, 1.75), (1.0 * sx, 0.7 * sy, 1.9), 0.1, seg=10)
    for i, (L, hw, z, h) in enumerate(((2.9, 1.2, 1.9, 0.7), (2.1, 0.85, 2.35, 0.65), (1.3, 0.5, 2.75, 0.6))):
        m.prism("root", GOLD, (0, 0, z), L + 0.1, hw + 0.06, h); m.prism("root", mat("D9542B", 0.4), (0, 0, z + 0.04), L, hw, h)
        for sx in (-1, 1): m.chain("root", GOLD, [(sx * L / 2, 0, z + h), (sx * (L / 2 + 0.14), 0, z + h + 0.14), (sx * (L / 2 + 0.18), 0, z + h + 0.4)], [0.045, 0.03, 0.006], seg=6)
    m.cyl("root", GLOW("FFD45A", 1.5), (0, 0, 3.35), (0, 0, 4.2), 0.05, 0.0, seg=8)
    return m

@model
def dock_post():
    m = Model("dock_post")
    m.cyl("root", DKW, (0, 0, -1.2), (0, 0, 1.0), 0.11, 0.09, seg=10); m.torus("root", mat("D9B27A", 0.15), (0, 0, 0.7), 0.1, 0.03, seg=10, rseg=6); m.torus("root", mat("D9B27A", 0.15), (0, 0, 0.62), 0.1, 0.03, seg=10, rseg=6)
    m.sph("root", WOOD, (0, 0, 1.0), (0.1, 0.1, 0.05), seg=8)
    return m

@model
def net_pile():
    m = Model("net_pile")
    N = mat("3FA6A0", 0.2)
    m.sph("root", N, (0, 0, 0.14), (0.5, 0.36, 0.2), seg=14, rough=(0.06, 5)); m.sph("root", mat("2F8F8A", 0.2), (0.2, 0.05, 0.26), (0.26, 0.22, 0.14), seg=10, rough=(0.05, 6))
    for i in range(5): a = i * 1.3; m.sph("root", mat(("FF9A1E", "FFFFFF")[i % 2], 0.5), (cos(a) * 0.38, sin(a) * 0.26, 0.2), 0.065, seg=8)
    return m

@model
def fish_rack():
    m = Model("fish_rack")
    for sx in (-1, 1): bamboo_pole(m, "root", (1.0 * sx, 0, 0), (1.0 * sx, 0, 1.6), 0.035, nodes=2)
    for z in (1.55, 1.1): m.cap("root", BAMBOO_D, (-1.05, 0, z), (1.05, 0, z), 0.025, seg=6)
    for row, z in enumerate((1.5, 1.05)):
        for i in range(6):
            x = -0.8 + i * 0.32 + row * 0.1
            m.sph("root", mat(("C9CED6", "E8B48A")[(i + row) % 2], 0.6), (x, 0, z - 0.2), (0.06, 0.025, 0.16), seg=8); m.cyl("root", STEEL, (x, 0, z - 0.36), (x, 0, z - 0.46), 0.05, 0.0, seg=4)
    return m

@model
def pier_house():
    m = Model("pier_house")     # wooden house on stilts over the water
    stilts(m, 2.6, 1.8, 0.9, 0.08, 1.4)
    m.box("root", PLK, (0, -0.2, 0.92), (3.4, 2.6, 0.12), bevel=0.02); m.box("root", mat("7FC8B8", 0.2), (0, 0.1, 1.75), (2.8, 1.9, 1.6), bevel=0.03)
    m.box("root", DKW, (0.6, -0.86, 1.55), (0.6, 0.04, 1.15), bevel=0.01); m.box("root", GLOW("FFD98A", 1.5), (-0.6, -0.86, 1.85), (0.7, 0.04, 0.6), bevel=0.02)
    for x in (-0.95, -0.25): m.box("root", PLASTER, (x, -0.88, 1.85), (0.05, 0.03, 0.66), bevel=0.0)
    m.prism("root", mat("B3261E", 0.4), (0, 0.1, 2.55), 3.3, 1.35, 0.9); m.prism("root", TILE, (0, 0.1, 2.6), 3.1, 1.22, 0.9)
    for x in (-1.6, -0.8, 0.0, 0.8, 1.6): m.cyl("root", DKW, (x, -1.45, 0.98), (x, -1.45, 1.4), 0.03, seg=6)
    m.cap("root", DKW, (-1.6, -1.45, 1.4), (1.6, -1.45, 1.4), 0.03, seg=6)
    return m

def hull(m, col, col2, L=2.2, w=0.5, h=0.4):
    m.sph("root", col, (0, 0, 0.12), (L, w, h), seg=24, cut=((0, 0, 0.28), (0, 0, 1))); m.sph("root", col2, (0, 0, 0.28), (L * 0.94, w * 0.86, 0.05), seg=20)

@model
def boat_fruit():
    m = Model("boat_fruit")
    hull(m, mat("9A5E32", 0.35), PLK, 2.0, 0.5, 0.4)
    for i, x in enumerate((-1.0, -0.4, 0.2)): fruit_pile(m, (x, 0, 0.3), cols=(("FFD83A", "8FCB5A"), ("E0382E", "FF9A1E"), ("F06BA8", "FFB82E"))[i], n=9, r=0.08, spread=0.26)
    m.cyl("root", BAMBOO, (1.0, 0, 0.3), (1.05, 0, 1.3), 0.02, seg=6); m.cyl("root", THATCH, (1.05, 0, 1.2), (1.05, 0, 1.45), 0.55, 0.0, seg=16)     # vendor's hat on a pole
    m.cap("root", WOOD, (1.5, 0.3, 0.45), (2.6, 0.7, -0.1), 0.025, seg=6)
    return m

@model
def fishing_boat():
    m = Model("fishing_boat")
    hull(m, mat("2A5DB0", 0.5), PLK, 2.8, 0.75, 0.55)
    m.box("root", mat("E0382E", 0.5), (0, 0, 0.36), (5.2, 1.3, 0.1), bevel=0.04)
    m.box("root", PLASTER, (0.7, 0, 0.9), (1.4, 0.95, 1.0), bevel=0.05); m.box("root", GLOW("FFD98A", 1.5), (0.7, -0.48, 1.0), (1.0, 0.03, 0.4), bevel=0.02); m.box("root", mat("3FA65A", 0.5), (0.7, 0, 1.45), (1.6, 1.1, 0.1), bevel=0.03)
    m.cyl("root", DKW, (-0.9, 0, 0.4), (-0.9, 0, 2.6), 0.04, seg=6); m.cap("root", DKW, (-0.9, 0, 2.2), (0.6, 0, 1.6), 0.025, seg=6)
    for i in range(6): m.sph("root", GLOW(("9FFFB0", "FFE9B0")[i % 2], 5.0), (-0.9 + i * 0.28, 0, 2.2 - i * 0.11), 0.06, seg=8)       # squid-fishing lamps
    m.sph("root", mat("3FA6A0", 0.2), (-1.7, 0, 0.5), (0.5, 0.4, 0.2), seg=10, rough=(0.05, 5))
    return m

@model
def kayak():
    m = Model("kayak")
    c = ("FF9A1E", "E0382E", "FFD12E")[int(R.uniform(0, 3))]
    m.sph("root", mat(c, 0.7), (0, 0, 0.08), (1.6, 0.32, 0.22), seg=20); m.sph("root", DARK, (0, 0, 0.2), (0.4, 0.2, 0.06), seg=12)
    m.cap("root", STEEL, (-0.7, 0.35, 0.3), (0.7, -0.35, 0.3), 0.015, seg=6)
    for sx in (-1, 1): m.sph("root", DARK, (0.75 * sx, -0.37 * sx, 0.3), (0.16, 0.03, 0.08), rot=(0, 0, -0.46), seg=8)
    return m

@model
def beach_hut():
    m = Model("beach_hut")
    stilts(m, 2.0, 1.4, 0.5, 0.07, 0.6)
    m.box("root", PLK, (0, 0, 0.52), (2.6, 2.0, 0.1), bevel=0.02); m.box("root", mat("D9B27A", 0.15), (0, 0.15, 1.2), (2.2, 1.5, 1.3), bevel=0.03)
    m.box("root", DKW, (0.4, -0.61, 1.1), (0.5, 0.04, 1.05), bevel=0.01); m.box("root", DARK, (-0.55, -0.61, 1.3), (0.5, 0.04, 0.45), bevel=0.01)
    for i, (L, hw, z) in enumerate(((3.0, 1.45, 1.8), (2.8, 1.1, 2.05), (2.6, 0.7, 2.3))): m.prism("root", THATCH if i % 2 == 0 else mat("A87A2C", 0.1), (0, 0.1, z), L, hw, 0.55)
    return m

@model
def sunbed():
    m = Model("sunbed")
    m.box("root", PLK, (0.1, 0, 0.28), (1.5, 0.6, 0.06), bevel=0.02); m.box("root", PLK, (-0.9, 0, 0.5), (0.6, 0.6, 0.06), rot=(0, 0.7, 0), bevel=0.02)
    m.box("root", mat("FFFFFF", 0.3), (0.1, 0, 0.33), (1.4, 0.52, 0.05), bevel=0.02)
    for x in (-0.5, 0.7):
        for sy in (-1, 1): m.cyl("root", DKW, (x, 0.25 * sy, 0), (x, 0.25 * sy, 0.27), 0.025, seg=6)
    m.cyl("root", BAMBOO, (-0.3, 0.6, 0), (-0.3, 0.6, 2.0), 0.03, seg=6)
    for i in range(8):
        a0 = i * PI / 4; m.cyl("root", mat(("2F7FE0", "FFFFFF")[i % 2], 0.3), (-0.3 + cos(a0 + PI / 8) * 0.5, 0.6 + sin(a0 + PI / 8) * 0.5, 1.85), (-0.3, 0.6, 2.05), 0.42, 0.0, seg=3)
    return m

@model
def sandcastle():
    m = Model("sandcastle")
    S2 = mat("EAD498", 0.1)
    m.box("root", SAND, (0, 0, 0.15), (0.9, 0.7, 0.3), bevel=0.04)
    for x, y in ((-0.38, -0.28), (0.38, -0.28), (-0.38, 0.28), (0.38, 0.28)): m.cyl("root", S2, (x, y, 0), (x, y, 0.5), 0.13, 0.11, seg=10); m.cyl("root", SAND, (x, y, 0.5), (x, y, 0.68), 0.13, 0.0, seg=10)
    m.cyl("root", S2, (0, 0, 0.3), (0, 0, 0.7), 0.17, 0.14, seg=10); m.cyl("root", WOOD, (0, 0, 0.7), (0, 0, 1.0), 0.01, seg=5); m.box("root", RED, (0.07, 0, 0.93), (0.14, 0.01, 0.1), bevel=0.0)
    return m

@model
def starfish():
    m = Model("starfish")
    for i in range(5): a = i * 2 * PI / 5; m.cap("root", mat("FF7A4A", 0.4), (0, 0, 0.04), (cos(a) * 0.2, sin(a) * 0.2, 0.03), 0.055, 0.02, seg=8)
    return m

@model
def shell():
    m = Model("shell")
    S1 = mat("FFD3E4", 0.6)
    for i in range(7):
        a = -1.0 + i * 0.33; m.ell("root", S1 if i % 2 else mat("FFF3D2", 0.6), (0, 0, 0.03), (sin(a) * 0.2, 0.02, 0.03 + cos(a) * 0.2), 0.045, 0.03, seg=6)
    return m

@model
def tea_terrace():
    m = Model("tea_terrace")
    G1 = mat("3E9B4A", 0.5); G2 = mat("2F8F45", 0.3); WALL = mat("7DBB4E", 0.1)
    for i in range(7):
        r = 5.0 - i * 0.62; z = i * 0.5
        m.cyl("root", WALL, (0, 0, z - 0.6), (0, 0, z + 0.5), r, r * 0.94, seg=40)
        n = int(r * 9)
        for k in range(n):
            a = k * 2 * PI / n; rr = r * 0.9
            m.sph("root", G1 if (k + i) % 2 else G2, (cos(a) * rr, sin(a) * rr, z + 0.55), (0.28, 0.28, 0.17), seg=6)
    m.sph("root", G2, (0, 0, 3.5), (0.9, 0.9, 0.5), seg=14)
    return m

# ================================================================================================ the restaurant
@model
def seafood_table():
    m = Model("seafood_table")
    m.cyl("root", STEEL, (0, 0, 0), (0, 0, 0.7), 0.05, seg=8); m.cyl("root", STEEL, (0, 0, 0), (0, 0, 0.04), 0.3, seg=14)
    m.cyl("root", mat("FFFFFF", 0.3), (0, 0, 0.7), (0, 0, 0.76), 0.75, seg=28); m.cyl("root", mat("E0382E", 0.3), (0, 0, 0.6), (0, 0, 0.705), 0.76, 0.74, seg=28)
    # dishes: a whole fish, prawns, crab, som tam, rice
    m.sph("root", PLASTER, (0, 0, 0.78), (0.3, 0.2, 0.02), seg=14); m.sph("root", mat("E8B48A", 0.5), (0, 0, 0.83), (0.24, 0.09, 0.06), seg=12); m.cyl("root", mat("E8B48A", 0.5), (0.22, 0, 0.83), (0.34, 0, 0.83), 0.01, 0.09, seg=4)
    for k in range(3): m.sph("root", LEAF, (-0.1 + k * 0.1, 0, 0.9), (0.03, 0.05, 0.01), seg=6)
    for i in range(4):
        a = i * PI / 2 + 0.6; c = V((cos(a) * 0.48, sin(a) * 0.48, 0.78))
        m.sph("root", PLASTER, c, (0.16, 0.16, 0.02), seg=12)
        if i == 0:
            for k in range(5): b = k * 1.26; m.torus("root", mat("FF8A5A", 0.5), c + V((cos(b) * 0.07, sin(b) * 0.07, 0.04)), 0.04, 0.018, seg=8, rseg=5, arc=4.5)
        elif i == 1: m.sph("root", mat("EB5338", 0.5), c + V((0, 0, 0.05)), (0.11, 0.08, 0.05), seg=10)
        elif i == 2: m.sph("root", mat("B9D676", 0.3), c + V((0, 0, 0.04)), (0.11, 0.11, 0.05), seg=8, rough=(0.02, 14)); m.sph("root", RED, c + V((0.03, 0, 0.08)), 0.025, seg=6)
        else: m.sph("root", WHITE, c + V((0, 0, 0.03)), (0.1, 0.1, 0.07), seg=10)
    for i in range(4):
        a = i * PI / 2; m.cyl("root", mat(("FF9A1E", "9FE8FF", "8FCB5A", "F06BA8")[i], 0.9), (cos(a) * 0.62, sin(a) * 0.62, 0.76), (cos(a) * 0.62, sin(a) * 0.62, 0.94), 0.04, 0.05, seg=8)
        m.box("root", mat("E0382E", 0.6), (cos(a) * 1.05, sin(a) * 1.05, 0.42), (0.36, 0.36, 0.05), bevel=0.02)
        for sx in (-1, 1):
            for sy in (-1, 1): m.cyl("root", mat("E0382E", 0.6), (cos(a) * 1.05 + 0.15 * sx, sin(a) * 1.05 + 0.15 * sy, 0), (cos(a) * 1.05 + 0.12 * sx, sin(a) * 1.05 + 0.12 * sy, 0.42), 0.025, seg=6)
    return m

@model
def restaurant():
    m = Model("restaurant")     # open-air seafood restaurant on a deck: thatched roof, lantern strings, big sign, grill
    stilts(m, 9.0, 3.0, 0.0, 0.1, 1.6)
    m.box("root", PLK, (0, 0, -0.02), (10.5, 4.2, 0.14), bevel=0.02)
    for x in (-4.6, -1.6, 1.6, 4.6):
        for y in (-1.6, 1.6): m.cyl("root", DKW, (x, y, 0), (x, y, 3.2), 0.1, seg=10)
    m.box("root", mat("7FC8B8", 0.2), (0, 1.75, 1.6), (9.4, 0.15, 3.0), bevel=0.02)
    for i in range(5): m.box("root", GLOW("FFD98A", 1.2), (-3.6 + i * 1.8, 1.66, 2.0), (1.0, 0.04, 0.9), bevel=0.03)
    # kitchen counter with grill and fish tank
    m.box("root", mat("7A5234", 0.3), (2.6, 1.2, 0.5), (3.4, 0.8, 1.0), bevel=0.03); m.box("root", STEEL, (2.6, 1.2, 1.02), (3.5, 0.9, 0.05), bevel=0.01)
    m.box("root", GLOW("FF7A1E", 3.0), (3.4, 1.2, 1.08), (1.0, 0.5, 0.04), bevel=0.0); m.box("root", mat("9FE8FF", 0.9, 0.6), (1.8, 1.2, 1.4), (1.2, 0.5, 0.65), bevel=0.02)
    for k in range(3): m.sph("root", mat("FF9A1E", 0.6), (1.5 + k * 0.3, 1.0, 1.35 + 0.1 * (k % 2)), (0.1, 0.03, 0.05), seg=8)
    # roof: three thatch layers + ridge
    for i, (L, hw, z, h) in enumerate(((11.6, 3.0, 3.2, 1.0), (10.8, 2.3, 3.75, 1.0), (10.0, 1.5, 4.3, 0.95), (9.2, 0.8, 4.85, 0.7))):
        m.prism("root", THATCH if i % 2 == 0 else mat("A87A2C", 0.1), (0, 0, z), L, hw, h)
    m.cap("root", DKW, (-4.7, 0, 5.55), (4.7, 0, 5.55), 0.09, seg=8)
    # sign with a glowing crab
    m.box("root", mat("2A5DB0", 0.5), (0, -2.2, 3.9), (5.2, 0.16, 1.2), bevel=0.05); m.box("root", GLOW("FFE9B0", 2.5), (0, -2.3, 3.9), (4.9, 0.03, 0.98), bevel=0.04)
    m.sph("root", mat("EB5338", 0.5), (0, -2.36, 3.86), (0.55, 0.08, 0.36), seg=18)
    for sx in (-1, 1):
        m.chain("root", mat("C83A28", 0.45), [(0.45 * sx, -2.36, 3.98), (0.78 * sx, -2.36, 4.2), (0.9 * sx, -2.36, 4.36)], [0.07, 0.07, 0.12], seg=8)
        for k in range(3): m.cap("root", mat("C83A28", 0.45), (0.45 * sx, -2.36, 3.8 - k * 0.1), (0.85 * sx, -2.36, 3.6 - k * 0.12), 0.035, seg=6)
        eye(m, "root", 0.15 * sx, -2.42, 4.16, 0.075)
        for k in range(4): m.sph("root", GLOW(("FFD12E", "FF4AC8")[k % 2], 5.0), (sx * (1.4 + k * 0.32), -2.33, 3.9), 0.09, seg=8)
    # lantern strings under the eaves, front and sides
    for y in (-2.05,):
        pts = [V((-5.0 + 10.0 * i / 16, y, 3.0 - 0.35 * abs(sin(i / 16 * PI * 4)))) for i in range(17)]
        m.chain("root", DARK, pts, [0.012] * 17, seg=5)
        for i in range(1, 16): lantern(m, "root", pts[i] - V((0, 0, 0.3)), ("E0382E", "FFD95A", "FF8FB0", "9FE8FF")[i % 4], 3.5, 0.6)
    # railing
    for x in [-5.1 + i * 0.85 for i in range(13)]: m.cyl("root", DKW, (x, 2.0, 0.05), (x, 2.0, 0.8), 0.035, seg=6)
    m.cap("root", DKW, (-5.1, 2.0, 0.8), (5.1, 2.0, 0.8), 0.04, seg=6)
    return m

# ================================================================================================ friends
def person(name, shirt, pants, hair, style, skin="F0BE92", extra=None):
    def b():
        m = Model(name)
        SH = mat(shirt, 0.25); PA = mat(pants, 0.2); HA = mat(hair, 0.6); SK = mat(skin, 0.3)
        m.joint("hips", (0, 0, 0.52)); m.joint("torso", (0, 0, 0.58), "hips"); m.joint("head", (0, 0, 0.98), "torso")
        for sd, sx in (("L", 1), ("R", -1)):
            m.joint("arm" + sd, (0.2 * sx, 0, 0.9), "torso"); m.joint("fore" + sd, (0.27 * sx, 0, 0.73), "arm" + sd)
            m.joint("leg" + sd, (0.1 * sx, 0, 0.5), "hips"); m.joint("shin" + sd, (0.105 * sx, 0, 0.28), "leg" + sd)
            m.sph("arm" + sd, SH, (0.21 * sx, 0, 0.9), 0.09); m.cap("arm" + sd, SK, (0.22 * sx, 0, 0.88), (0.27 * sx, 0, 0.73), 0.056)
            m.cap("fore" + sd, SK, (0.27 * sx, 0, 0.73), (0.29 * sx, -0.02, 0.58), 0.053, 0.048); m.sph("fore" + sd, SK, (0.292 * sx, -0.025, 0.55), 0.068)
            m.cap("leg" + sd, PA, (0.1 * sx, 0, 0.5), (0.105 * sx, 0, 0.28), 0.095, 0.09); m.cap("shin" + sd, PA if style != "shorts" else SK, (0.105 * sx, 0, 0.28), (0.108 * sx, 0, 0.1), 0.085, 0.07)
            m.sph("shin" + sd, mat("FFFFFF", 0.4) if style != "flip" else mat("2F7FE0", 0.5), (0.108 * sx, -0.05, 0.05), (0.085, 0.15, 0.055))
        m.sph("hips", PA, (0, 0, 0.55), (0.2, 0.155, 0.13), seg=20); m.sph("torso", SH, (0, 0, 0.76), (0.2, 0.15, 0.22), seg=20); m.cyl("torso", SK, (0, 0, 0.93), (0, 0, 1.03), 0.062)
        hz = 1.28
        m.sph("head", SK, (0, 0, hz), (0.31, 0.285, 0.29), seg=28)
        for sx in (1, -1):
            m.sph("head", SK, (0.3 * sx, 0.02, hz - 0.04), (0.04, 0.06, 0.07)); eye(m, "head", 0.115 * sx, -0.245, hz - 0.01, 0.06)
            m.cap("head", HA, (0.05 * sx, -0.27, hz + 0.1), (0.17 * sx, -0.25, hz + 0.115), 0.012); m.sph("head", mat("F2917F", 0.2), (0.2 * sx, -0.2, hz - 0.12), (0.05, 0.02, 0.032))
        m.sph("head", mat("8E1F33", 0.5), (0, -0.262, hz - 0.15), (0.085, 0.03, 0.055), cut=((0, 0, hz - 0.135), (0, 0, 1))); m.sph("head", WHITE, (0, -0.274, hz - 0.142), (0.066, 0.02, 0.016))
        m.sph("head", SK, (0, -0.29, hz - 0.075), (0.028, 0.03, 0.024))
        m.sph("head", HA, (0, 0.03, hz + 0.02), (0.325, 0.3, 0.3), seg=28, cut=((0, 0.0, hz + 0.02), (0, -0.75, -0.35)))
        if style == "bun": m.sph("head", HA, (0, 0.05, hz + 0.36), 0.12, seg=14)
        elif style == "long":
            m.sph("head", HA, (0, 0.2, 1.06), (0.3, 0.14, 0.3), seg=20)
            for sx in (1, -1): m.chain("head", HA, [(0.28 * sx, 0.05, 1.2), (0.3 * sx, 0.06, 1.0), (0.26 * sx, 0.1, 0.84)], [0.08, 0.08, 0.03])
        elif style == "spiky":
            for i in range(7): a = i * 0.9; m.cyl("head", HA, (cos(a) * 0.14, sin(a) * 0.12 + 0.02, hz + 0.26), (cos(a) * 0.22, sin(a) * 0.2, hz + 0.44), 0.07, 0.0, seg=6)
        elif style == "cap":
            m.sph("head", mat("E0382E", 0.4), (0, 0, hz + 0.06), (0.33, 0.31, 0.27), seg=24, cut=((0, 0, hz + 0.1), (0, 0, -1))); m.sph("head", mat("E0382E", 0.4), (0, -0.3, hz + 0.12), (0.2, 0.17, 0.03))
        elif style in ("shorts", "flip"):
            for sx in (1, -1): m.sph("head", HA, (0.2 * sx, 0.24, hz + 0.02), 0.11, seg=12)      # pigtails
        if extra: extra(m, hz)
        return m
    BUILD.append(b)

def glasses(m, hz):
    for sx in (1, -1): m.torus("head", INK, (0.118 * sx, -0.305, hz - 0.01), 0.095, 0.014, rot=(PI / 2, 0, 0), seg=20, rseg=6)
    m.cap("head", INK, (-0.02, -0.305, hz + 0.02), (0.02, -0.305, hz + 0.02), 0.012, seg=6)
def flower(m, hz): m.sph("head", PINK, (0.24, -0.12, hz + 0.2), 0.07, seg=8); m.sph("head", YEL, (0.25, -0.17, hz + 0.2), 0.03, seg=6)
def beard(m, hz): m.sph("head", mat("3A2A20", 0.4), (0, -0.2, hz - 0.2), (0.17, 0.1, 0.1), seg=12)
person("friend_a", "FF9A1E", "2F7FE0", "17171D", "bun", extra=flower)
person("friend_b", "3FA65A", "F3E6C8", "3A2A20", "spiky", "E0A878", extra=glasses)
person("friend_c", "F06BA8", "FFFFFF", "6E4826", "long")
person("friend_d", "2F7FE0", "4A4D58", "17171D", "cap", "D99A6C", extra=beard)
person("friend_e", "FFD12E", "E0382E", "17171D", "flip", extra=glasses)

# ================================================================================================ enemies
def critter(name, body, belly, shape):
    """Walking enemy with the joints the Monkey class animates: body, head, armL, armR, tail."""
    def b():
        m = Model(name); B = mat(body, 0.3); L = mat(belly, 0.3)
        m.joint("body", (0, 0, 0.3)); m.joint("head", (0, -0.1, 0.6), "body"); m.joint("tail", (0, 0.25, 0.3), "body")
        for sd, sx in (("L", 1), ("R", -1)): m.joint("arm" + sd, (0.22 * sx, -0.05, 0.42), "body")
        shape(m, B, L)
        return m
    BUILD.append(b)

def rat_shape(m, B, L):
    m.sph("body", B, (0, 0.05, 0.34), (0.3, 0.42, 0.3), seg=18); m.sph("body", L, (0, -0.02, 0.26), (0.22, 0.3, 0.2))
    m.sph("head", B, (0, -0.32, 0.56), (0.24, 0.3, 0.22), seg=16); m.sph("head", mat("F09AB0", 0.4), (0, -0.62, 0.52), 0.05, seg=8)
    for sx in (-1, 1):
        m.sph("head", B, (0.2 * sx, -0.2, 0.8), (0.13, 0.04, 0.14)); m.sph("head", mat("F09AB0", 0.3), (0.2 * sx, -0.23, 0.8), (0.085, 0.03, 0.095)); eye(m, "head", 0.1 * sx, -0.5, 0.64, 0.05, look=(-0.1 * sx, -0.1))
        m.cap("head", INK, (0.03 * sx, -0.56, 0.71), (0.15 * sx, -0.5, 0.76), 0.014); m.cap("arm" + ("L" if sx > 0 else "R"), B, (0.2 * sx, -0.05, 0.4), (0.24 * sx, -0.2, 0.08), 0.06, 0.05)
        m.sph("body", B, (0.18 * sx, 0.2, 0.08), (0.1, 0.16, 0.08))
    m.box("head", WHITE, (0, -0.6, 0.44), (0.07, 0.02, 0.06), bevel=0.005)
    m.chain("tail", mat("F09AB0", 0.3), [(0, 0.4, 0.25), (0, 0.65, 0.15), (0, 0.85, 0.25), (0, 0.95, 0.45)], [0.04, 0.035, 0.025, 0.012], seg=8)

def frog_shape(m, B, L):
    m.sph("body", B, (0, 0, 0.36), (0.38, 0.4, 0.3), seg=18); m.sph("body", L, (0, -0.1, 0.3), (0.3, 0.3, 0.22))
    m.sph("head", B, (0, -0.2, 0.62), (0.34, 0.3, 0.2), seg=16); m.cap("head", INK, (-0.2, -0.47, 0.57), (0.2, -0.47, 0.57), 0.014)
    for sx in (-1, 1):
        m.sph("head", B, (0.18 * sx, -0.22, 0.82), 0.12, seg=12); eye(m, "head", 0.18 * sx, -0.31, 0.84, 0.085, look=(-0.1 * sx, -0.1))
        m.cap("arm" + ("L" if sx > 0 else "R"), B, (0.26 * sx, -0.1, 0.36), (0.36 * sx, -0.26, 0.06), 0.06, 0.05); m.sph("arm" + ("L" if sx > 0 else "R"), L, (0.38 * sx, -0.3, 0.04), (0.1, 0.12, 0.03))
        m.sph("body", B, (0.34 * sx, 0.15, 0.2), (0.16, 0.26, 0.18)); m.sph("body", L, (0.4 * sx, -0.02, 0.04), (0.12, 0.2, 0.035))

def dog_shape(m, B, L):
    m.sph("body", B, (0, 0.1, 0.5), (0.26, 0.46, 0.26), seg=18)
    for sx in (-1, 1):
        m.cap("arm" + ("L" if sx > 0 else "R"), B, (0.16 * sx, -0.2, 0.4), (0.17 * sx, -0.22, 0.06), 0.065, 0.055); m.cap("body", B, (0.16 * sx, 0.4, 0.4), (0.17 * sx, 0.42, 0.06), 0.07, 0.055)
        m.sph("head", B, (0.17 * sx, -0.32, 0.98), (0.07, 0.05, 0.13), rot=(0, 0.3 * sx, 0)); eye(m, "head", 0.1 * sx, -0.56, 0.86, 0.05, look=(-0.1 * sx, -0.1))
        m.cap("head", INK, (0.03 * sx, -0.61, 0.93), (0.16 * sx, -0.56, 0.98), 0.016)
    m.sph("head", B, (0, -0.4, 0.8), (0.22, 0.24, 0.21), seg=16); m.sph("head", L, (0, -0.62, 0.72), (0.12, 0.16, 0.1)); m.sph("head", INK, (0, -0.77, 0.75), 0.04, seg=8)
    m.box("head", WHITE, (0, -0.72, 0.65), (0.12, 0.02, 0.035), bevel=0.005)
    m.chain("tail", B, [(0, 0.5, 0.6), (0, 0.66, 0.8), (0, 0.62, 0.98)], [0.05, 0.04, 0.025], seg=8)

def hermit_shape(m, B, L):
    for i in range(4):     # spiral shell
        m.sph("body", mat(("F2D8B0", "E8B48A")[i % 2], 0.5), (0, 0.12 + i * 0.03, 0.34 + i * 0.16), (0.42 - i * 0.09, 0.42 - i * 0.09, 0.2 - i * 0.03), seg=14)
    m.sph("head", B, (0, -0.3, 0.3), (0.22, 0.2, 0.16), seg=12)
    for sx in (-1, 1):
        m.cap("head", B, (0.08 * sx, -0.4, 0.38), (0.1 * sx, -0.46, 0.6), 0.02); eye(m, "head", 0.1 * sx, -0.5, 0.64, 0.065, look=(-0.2 * sx, -0.1))
        j = "arm" + ("L" if sx > 0 else "R"); m.cap(j, B, (0.2 * sx, -0.25, 0.25), (0.36 * sx, -0.42, 0.25), 0.05); m.sph(j, B, (0.42 * sx, -0.5, 0.3), (0.1, 0.13, 0.09))
        for k in range(2): m.cap("body", L, (0.25 * sx, -0.1 + k * 0.16, 0.2), (0.44 * sx, -0.12 + k * 0.2, 0.02), 0.035, 0.02, seg=6)

def skipper_shape(m, B, L):
    m.chain("body", B, [(0, -0.2, 0.3), (0, 0.15, 0.26), (0, 0.5, 0.18)], [0.24, 0.2, 0.1], seg=14); m.sph("body", L, (0, -0.05, 0.2), (0.18, 0.3, 0.12))
    m.sph("head", B, (0, -0.36, 0.42), (0.25, 0.24, 0.22), seg=14); m.cap("head", INK, (-0.16, -0.58, 0.36), (0.16, -0.58, 0.36), 0.014)
    for sx in (-1, 1):
        m.sph("head", B, (0.11 * sx, -0.38, 0.64), 0.09, seg=10); eye(m, "head", 0.11 * sx, -0.45, 0.66, 0.07, look=(-0.1 * sx, 0))
        m.sph("arm" + ("L" if sx > 0 else "R"), L, (0.3 * sx, -0.2, 0.12), (0.2, 0.12, 0.03), rot=(0, 0, 0.5 * sx))
    m.ell("tail", B, (0, 0.5, 0.18), (0, 0.85, 0.3), 0.03, 0.2, seg=8); m.ell("body", mat("FF9A1E", 0.4), (0, 0.0, 0.48), (0, 0.3, 0.7), 0.02, 0.14, seg=8)

critter("rat", "7A7480", "C9C4CC", rat_shape); critter("frog", "5FAE4A", "D9E89A", frog_shape); critter("soidog", "C9965A", "F3E6C8", dog_shape)
critter("hermit", "EB6A48", "C83A28", hermit_shape); critter("mudskipper", "8E8468", "C9C09A", skipper_shape)

recolor("crab", "crab_blue", {"EB5338": "3A8AE0", "C83A28": "2A5DB0", "F7A77A": "BFE4FF"})

@model
def scorpion():
    m = Model("scorpion")       # crab-class joints: body, legsL/R, clawL/R
    S = mat("3A2A20", 0.7); S2 = mat("5A3A2A", 0.6)
    m.joint("body", (0, 0, 0.25))
    m.sph("body", S, (0, 0, 0.3), (0.34, 0.4, 0.16), seg=16)
    pts = [(0, 0.35, 0.34), (0, 0.6, 0.55), (0, 0.6, 0.85), (0, 0.4, 1.02), (0, 0.2, 0.98)]
    m.chain("body", S2, pts, [0.1, 0.09, 0.08, 0.07, 0.06], seg=10); m.cyl("body", mat("E0382E", 0.6), (0, 0.2, 0.98), (0, 0.02, 0.86), 0.06, 0.0, seg=8)
    for sd, sx in (("L", 1), ("R", -1)):
        eye(m, "body", 0.1 * sx, -0.36, 0.4, 0.06, look=(-0.2 * sx, -0.1)); m.cap("body", INK, (0.03 * sx, -0.42, 0.47), (0.17 * sx, -0.39, 0.53), 0.018)
        m.joint("legs" + sd, (0.3 * sx, 0, 0.26), "body")
        for y in (-0.15, 0.03, 0.2): m.chain("legs" + sd, S2, [(0.3 * sx, y, 0.26), (0.48 * sx, y, 0.34), (0.56 * sx, y + 0.02, 0.02)], [0.04, 0.035, 0.015], seg=6)
        m.joint("claw" + sd, (0.28 * sx, -0.3, 0.3), "body")
        m.cap("claw" + sd, S2, (0.28 * sx, -0.3, 0.3), (0.5 * sx, -0.5, 0.36), 0.05); m.sph("claw" + sd, S, (0.56 * sx, -0.6, 0.4), (0.12, 0.17, 0.08)); m.sph("claw" + sd, S, (0.46 * sx, -0.66, 0.42), (0.04, 0.12, 0.05))
    return m

@model
def gecko():
    m = Model("gecko")          # cobra-class joints: neck, head, tongue
    G = mat("7FC8B0", 0.5); SP = mat("FF8A5A", 0.5)
    m.chain("root", G, [(0, 0.1, 0.2), (0, 0.45, 0.18), (0.15, 0.75, 0.14), (0.3, 0.95, 0.1)], [0.2, 0.15, 0.09, 0.03], seg=12)
    for sx in (-1, 1):
        for y in (0.0, 0.4): m.cap("root", G, (0.16 * sx, y, 0.18), (0.36 * sx, y - 0.1, 0.05), 0.05, 0.04, seg=8); m.sph("root", G, (0.4 * sx, y - 0.14, 0.03), (0.09, 0.09, 0.025), seg=8)
    m.joint("neck", (0, 0, 0.25)); m.joint("head", (0, -0.2, 0.7), "neck")
    m.chain("neck", G, [(0, 0.05, 0.25), (0, -0.05, 0.5), (0, -0.18, 0.7)], [0.2, 0.17, 0.15], seg=12)
    for i in range(6): m.sph("neck", SP, (0.1 * (-1) ** i, 0.12 - i * 0.03, 0.3 + i * 0.07), 0.035, seg=6)
    m.sph("head", G, (0, -0.32, 0.78), (0.2, 0.26, 0.15), seg=14)
    for sx in (-1, 1): m.sph("head", mat("FFD12E", 0.7), (0.13 * sx, -0.36, 0.88), 0.075, seg=10); m.sph("head", INK, (0.15 * sx, -0.42, 0.88), (0.02, 0.03, 0.06), seg=8)
    m.joint("tongue", (0, -0.56, 0.74), "head"); m.cyl("tongue", PINK, (0, -0.55, 0.74), (0, -0.78, 0.72), 0.03, 0.015, seg=6)
    return m

@model
def squid():
    m = Model("squid")
    Q = mat("F09AB0", 0.6); Q2 = mat("FFD3E4", 0.5)
    for i in range(8): a = i * PI / 4; m.chain("root", Q, [(cos(a) * 0.14, sin(a) * 0.14, 0.3), (cos(a) * 0.32, sin(a) * 0.32, 0.12), (cos(a) * 0.44, sin(a) * 0.44, 0.03)], [0.06, 0.045, 0.02], seg=8)
    m.joint("neck", (0, 0, 0.3)); m.joint("head", (0, 0, 0.7), "neck")
    m.sph("neck", Q, (0, 0, 0.55), (0.26, 0.24, 0.34), seg=16)
    m.sph("head", Q, (0, 0, 0.98), (0.22, 0.2, 0.3), seg=14); m.cyl("head", Q2, (0, 0, 1.15), (0, 0, 1.4), 0.2, 0.0, seg=3)
    for sx in (-1, 1): eye(m, "neck", 0.12 * sx, -0.2, 0.58, 0.08, look=(-0.1 * sx, 0)); m.cap("neck", INK, (0.03 * sx, -0.25, 0.68), (0.2 * sx, -0.22, 0.74), 0.018)
    m.joint("tongue", (0, -0.24, 0.42), "head"); m.cyl("tongue", Q2, (0, -0.2, 0.42), (0, -0.32, 0.4), 0.05, 0.035, seg=8)
    return m

def flyer(name, body, wing, shape):
    def b():
        m = Model(name)
        m.joint("body", (0, 0, 0.4))
        for sd, sx in (("L", 1), ("R", -1)): m.joint("wing" + sd, (0.1 * sx, 0, 0.5), "body")
        shape(m, mat(body, 0.4), mat(wing, 0.5))
        return m
    BUILD.append(b)

def dragonfly_shape(m, B, W):
    m.sph("body", B, (0, -0.1, 0.45), (0.12, 0.18, 0.12)); m.chain("body", B, [(0, 0.05, 0.45), (0, 0.4, 0.42), (0, 0.8, 0.38)], [0.07, 0.05, 0.03], seg=8)
    for sx in (-1, 1):
        m.sph("body", mat("3FE0A0", 0.8, 0.5), (0.07 * sx, -0.26, 0.5), 0.07, seg=10)
        j = "wing" + ("L" if sx > 0 else "R")
        m.ell(j, W, (0.08 * sx, -0.05, 0.52), (0.62 * sx, -0.15, 0.6), 0.1, 0.008, seg=8); m.ell(j, W, (0.08 * sx, 0.1, 0.52), (0.55 * sx, 0.25, 0.58), 0.09, 0.008, seg=8)

def bird_shape(big, beak, crest=None):
    def s(m, B, W):
        k = 1.25 if big else 1.0
        m.sph("body", B, (0, 0.05, 0.42), (0.2 * k, 0.3 * k, 0.2 * k), seg=14); m.sph("body", B, (0, -0.24 * k, 0.56), 0.15 * k, seg=12)
        m.cyl("body", mat(beak, 0.6), (0, -0.36 * k, 0.55), (0, -0.36 * k - (0.42 if big else 0.16), 0.5), 0.06 * k, 0.015, seg=8)
        if crest: m.sph("body", mat(crest, 0.5), (0, -0.4 * k, 0.68), (0.06, 0.16, 0.06), seg=8)
        m.ell("body", B, (0, 0.25 * k, 0.42), (0, 0.6 * k, 0.4), 0.1, 0.02, seg=8)
        for sx in (-1, 1):
            eye(m, "body", 0.09 * sx * k, -0.33 * k, 0.6, 0.045 * k, look=(-0.1 * sx, 0)); m.cap("body", INK, (0.03 * sx, -0.38 * k, 0.66), (0.14 * sx * k, -0.33 * k, 0.7), 0.012)
            j = "wing" + ("L" if sx > 0 else "R"); m.ell(j, W, (0.1 * sx, 0.0, 0.5), (0.7 * sx * k, 0.1, 0.56), 0.17 * k, 0.015, seg=10)
    return s

def bat_shape(m, B, W):
    m.sph("body", B, (0, 0, 0.42), (0.17, 0.17, 0.2), seg=14); m.sph("body", B, (0, -0.1, 0.62), 0.14, seg=12)
    for sx in (-1, 1):
        m.cyl("body", B, (0.09 * sx, -0.08, 0.72), (0.12 * sx, -0.08, 0.9), 0.05, 0.0, seg=6); m.sph("body", mat("FF4A3A", 0.6, 1.5), (0.06 * sx, -0.22, 0.64), 0.035, seg=8)
        m.cyl("body", WHITE, (0.03 * sx, -0.22, 0.56), (0.03 * sx, -0.22, 0.5), 0.012, 0.0, seg=5)
        j = "wing" + ("L" if sx > 0 else "R")
        for k in range(3): m.ell(j, W, (0.1 * sx, 0, 0.5), ((0.7 - k * 0.1) * sx, -0.1 + k * 0.2, 0.62 - k * 0.12), 0.11, 0.008, seg=6)
        m.cap(j, B, (0.1 * sx, 0, 0.5), (0.72 * sx, -0.1, 0.62), 0.018, seg=6)

flyer("dragonfly", "3A8AE0", "CFF0FF", dragonfly_shape); flyer("hornbill", "22202A", "3A3A46", bird_shape(True, "FFC81E", "FFC81E")); flyer("pigeon", "8E8A94", "A6A2AC", bird_shape(False, "F09AB0"))
flyer("seagull", "FFFFFF", "C9CED6", bird_shape(False, "FF9A1E")); flyer("bat", "4A3A5A", "6A5A7E", bat_shape)

@model
def firefly():
    m = Model("firefly")
    m.sph("root", GLOW("D8FF6A", 8.0), (0, 0, 0), 0.05, seg=8)
    for sd, sx in (("L", 1), ("R", -1)): m.joint("wing" + sd, (0.01 * sx, 0, 0.01)); m.ell("wing" + sd, mat("FFFFFF", 0.4, 1.0), (0.01 * sx, 0, 0.01), (0.09 * sx, 0, 0.03), 0.03, 0.004, seg=6)
    return m

@model
def wisp():
    m = Model("wisp")           # ghost-class: a floating lantern spirit
    m.joint("body", (0, 0, 0.1)); m.joint("head", (0, 0, 0.7), "body")
    m.sph("body", GLOW("FFB45A", 1.5), (0, 0, 0.55), (0.34, 0.34, 0.42), seg=18)
    for i in range(8): a = i * PI / 4; m.torus("body", mat("C8322C", 0.4), (0, 0, 0.55), 0.345, 0.012, rot=(PI / 2, 0, a), seg=16, rseg=4)
    m.cyl("body", GOLD, (0, 0, 0.92), (0, 0, 1.02), 0.16, seg=12); m.cyl("body", GOLD, (0, 0, 0.08), (0, 0, 0.18), 0.16, seg=12)
    for i in range(5): a = i * 1.26; m.cyl("body", RED, (cos(a) * 0.1, sin(a) * 0.1, 0.08), (cos(a) * 0.12, sin(a) * 0.12, -0.2), 0.02, 0.008, seg=5)
    for sx in (-1, 1):
        m.sph("head", INK, (0.12 * sx, -0.31, 0.62), (0.07, 0.03, 0.09), seg=10); m.sph("head", GLOW("FFF2A0", 6.0), (0.12 * sx, -0.335, 0.62), (0.03, 0.015, 0.045), seg=8)
        m.joint("arm" + ("L" if sx > 0 else "R"), (0.3 * sx, 0, 0.6), "body"); m.cap("arm" + ("L" if sx > 0 else "R"), GLOW("FFB45A", 1.5), (0.3 * sx, 0, 0.6), (0.5 * sx, -0.1, 0.45), 0.06, 0.08)
    m.sph("head", INK, (0, -0.32, 0.42), (0.12, 0.03, 0.07), seg=10, cut=((0, 0, 0.44), (0, 0, 1)))
    return m

@model
def jellyfish():
    m = Model("jellyfish")
    J = mat("C8A0FF", 0.9, 1.0); J2 = mat("F0D8FF", 0.9, 1.5)
    m.joint("body", (0, 0, 0.1)); m.joint("head", (0, 0, 0.8), "body")
    m.sph("head", J, (0, 0, 0.85), (0.42, 0.42, 0.36), seg=18, cut=((0, 0, 0.8), (0, 0, -1))); m.sph("head", J2, (0, 0, 0.8), (0.4, 0.4, 0.06), seg=16)
    for i in range(8): a = i * PI / 4; m.chain("body", J2 if i % 2 else J, [(cos(a) * 0.26, sin(a) * 0.26, 0.78), (cos(a) * 0.3, sin(a) * 0.3, 0.45), (cos(a) * 0.22, sin(a) * 0.22, 0.1)], [0.04, 0.03, 0.012], seg=6)
    for sx in (-1, 1):
        eye(m, "head", 0.13 * sx, -0.36, 0.95, 0.07, look=(-0.1 * sx, -0.1)); m.cap("head", INK, (0.04 * sx, -0.4, 1.03), (0.2 * sx, -0.37, 1.08), 0.016)
        m.joint("arm" + ("L" if sx > 0 else "R"), (0.3 * sx, 0, 0.75), "body"); m.cap("arm" + ("L" if sx > 0 else "R"), J, (0.3 * sx, 0, 0.75), (0.5 * sx, -0.05, 0.5), 0.05, 0.03)
    return m

# ================================================================================================ run
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ok = 0
    for b in BUILD:
        try:
            m = b(); m.build(); m.export(); ok += 1
        except Exception as e:
            import traceback; print("FAILED", getattr(b, "__name__", "?"), "->", e); traceback.print_exc()
    print("exported %d of %d models" % (ok, len(BUILD)))
    if argv:
        sc = bpy.context.scene; x = 0; z = 0; rowh = 0
        for m in [mm for mm in Model.all if hasattr(mm, "objs")]:
            parts = [o for o in m.objs if o.name.startswith("M_")]
            if not parts: continue
            xs = [(o.matrix_world @ V(c)).x for o in parts for c in o.bound_box]; zs = [(o.matrix_world @ V(c)).z for o in parts for c in o.bound_box]
            w = max(1.2, max(xs) - min(xs) + 0.5); h = max(zs)
            if x + w > 44: x = 0; z -= rowh + 0.8; rowh = 0
            for o in m.objs:
                if o.name.startswith("M_"): o.location = (x + w / 2 - (max(xs) + min(xs)) / 2, 0, z)
                else: o.hide_render = True
            rowh = max(rowh, h + 0.3); x += w
        bpy.context.view_layer.update()
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = "ORTHO"; cam.data.ortho_scale = 47
        d = V((0.3, -1, 0.28)).normalized(); centre = V((22, 0, (z + rowh) / 2 + 2))
        cam.location = centre + d * 120; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); cam.data.clip_end = 400
        sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
        sc.render.resolution_x = 3000; sc.render.resolution_y = int(3000 * max(0.5, (-z + rowh + 8) / 47)); sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.35, 0.5, 0.65)
        sc.render.filepath = argv[0]; bpy.ops.render.render(write_still=True)

main()
