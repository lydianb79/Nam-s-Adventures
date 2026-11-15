# Builds every 3D model of Nam's Adventures and exports one FBX per model.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b -P Tools/blender_models.py -- [preview.png]
#
# Each model is a set of rigid parts.  A part mesh is called  M_<joint>  and every joint has a
# tiny marker mesh  J_<joint>@<parent>  at its pivot; Unity rebuilds the bone hierarchy from those
# (see Assets/Scripts/Rig.cs) and animates the joints in code.
# Blender axes while modelling:  -Y = front of the character,  +Z = up,  X = sideways.
# Material names carry the look:  <RRGGBB>_s<smoothness %>_e<emission x10>   or  T<texture>_<...>.
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "Assets", "Resources", "Models")
os.makedirs(OUT, exist_ok=True)
R = random.Random(11)
PI = math.pi
bpy.ops.wm.read_factory_settings(use_empty=True)

# ----------------------------------------------------------------------------- framework
_mats = {}
# surface detail by colour: which grey detail map the game projects onto a material
DETAIL = {}
for _k, _cols in {
    "wood": "9A6B3F 9A5E32 C98A52 B98552 A06F40 6E4826 7A5234 5A3A20 5A2A1A D9C56A A8913F 6FB24A 4E8E38 EAD9A0 C9B170 C0281F B3261E",
    "bark": "9A7B4F 7C6039 A79C92 9DB85A",
    "leaf": "4FB04A 2F8F45 86CF4E 3E9B4A 58B257 5FAE56 4A9A52 8FD65A 76C54D A8D24A E6D25A 7FCB58 6ABC4E 86CC55 7DBB4E",
    "stone": "9A9488 B9B3A4 A49D8E CFC9BA 8E8A80 E9DCA6 A9844F",
    "brick": "C8643C B2532F D98A5A",
    "tile": "D9542B 2F9A6B F0862A",
    "thatch": "C8963C A87A2C D9B26C",
    "weave": "D9B27A 4A4D58",
    "plaster": "FBF7EC FBF6EA E6DFCF C9683E 9C4A2A",
    "metal": "F2B632 FFD45A E9A91E B87A10 F0B428",
}.items():
    for _c in _cols.split(): DETAIL[_c] = _k

def mat(col, smooth=0.35, emis=0.0, tex=None):
    name = ("T%s_" % tex if tex else "") + "%s_s%d_e%d" % (col, round(smooth * 100), round(emis * 10))
    if col in DETAIL and not tex and emis < 1.0: name += "_d" + DETAIL[col]
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name)
    r, g, b = [int(col[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    m.diffuse_color = (lin(r), lin(g), lin(b), 1)
    m.roughness = 1 - smooth
    _mats[name] = m
    return m

def V(p): return Vector(p)

class Model:
    all = []
    def __init__(s, name):
        s.name = name; s.bms = {}; s.pm = {}; s.joints = {"root": (V((0, 0, 0)), None)}
        Model.all.append(s)
    def joint(s, name, pos, parent="root"):
        s.joints[name] = (V(pos), parent); return name
    def _bm(s, j):
        if j not in s.bms: s.bms[j] = bmesh.new(); s.pm[j] = []
        return s.bms[j]
    def _add(s, j, m, build, cut=None, rough=None):
        if j not in s.joints: raise Exception("unknown joint " + j)
        dst = s._bm(j)
        if m not in s.pm[j]: s.pm[j].append(m)
        mi = s.pm[j].index(m)
        bm = bmesh.new(); bm.loops.layers.uv.new("UVMap"); build(bm)
        if rough:           # (amount, frequency, vertical stretch): push vertices along their normals with fractal noise
            from mathutils import noise as _noise
            amt, fr, zs = (list(rough) + [1.0])[:3]
            off = V((R.uniform(0, 50), R.uniform(0, 50), R.uniform(0, 50)))
            bm.normal_update()
            for v in bm.verts:
                q = V((v.co.x * fr, v.co.y * fr, v.co.z * fr * zs)) + off
                v.co += v.normal * (_noise.fractal(q, 1.0, 2.0, 4) * amt)
        if cut:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                                   plane_co=V(cut[0]), plane_no=V(cut[1]).normalized(), clear_outer=True)
        for f in bm.faces: f.material_index = mi; f.smooth = True
        me = bpy.data.meshes.new("tmp"); bm.to_mesh(me); bm.free()
        dst.from_mesh(me); bpy.data.meshes.remove(me)

    # ---- primitives
    def sph(s, j, m, loc, sc, rot=(0, 0, 0), seg=26, cut=None, rough=None):
        if isinstance(sc, (int, float)): sc = (sc, sc, sc)
        M = Matrix.Translation(V(loc)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((sc[0], sc[1], sc[2], 1))
        s._add(j, m, lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=1, matrix=M, calc_uvs=True), cut, rough)
    def cyl(s, j, m, p0, p1, r0, r1=None, seg=16, caps=True):
        if r1 is None: r1 = r0
        p0, p1 = V(p0), V(p1); d = p1 - p0
        M = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        s._add(j, m, lambda bm: bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=d.length, matrix=M, calc_uvs=True))
    def cap(s, j, m, p0, p1, r0, r1=None, seg=18):
        if r1 is None: r1 = r0
        s.cyl(j, m, p0, p1, r0, r1, seg, caps=False); s.sph(j, m, p0, r0, seg=seg); s.sph(j, m, p1, r1, seg=seg)
    def chain(s, j, m, pts, radii, seg=16):
        for i in range(len(pts) - 1): s.cap(j, m, pts[i], pts[i + 1], radii[i], radii[i + 1], seg)
    def box(s, j, m, loc, size, rot=(0, 0, 0), bevel=0.02):
        M = Matrix.Translation(V(loc)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((size[0], size[1], size[2], 1))
        def b(bm):
            bmesh.ops.create_cube(bm, size=1, matrix=M, calc_uvs=True)
            if bevel > 0: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=min(bevel, min(size) * 0.45), segments=2, profile=0.5, affect="EDGES")
        s._add(j, m, b)
    def torus(s, j, m, loc, R_, r, rot=(0, 0, 0), seg=24, rseg=8, arc=2 * PI):
        M = Matrix.Translation(V(loc)) @ Euler(rot).to_matrix().to_4x4()
        def b(bm):
            n = seg if arc >= 2 * PI - 1e-6 else seg + 1
            rings = []
            for i in range(n):
                a = arc * i / seg
                ring = []
                for k in range(rseg):
                    t = 2 * PI * k / rseg
                    ring.append(bm.verts.new(M @ V(((R_ + r * math.cos(t)) * math.cos(a), (R_ + r * math.cos(t)) * math.sin(a), r * math.sin(t)))))
                rings.append(ring)
            m_ = seg if arc >= 2 * PI - 1e-6 else seg
            for i in range(m_):
                a_, b_ = rings[i], rings[(i + 1) % n]
                for k in range(rseg):
                    bm.faces.new((a_[k], b_[k], b_[(k + 1) % rseg], a_[(k + 1) % rseg]))
        s._add(j, m, b)
    def ell(s, j, m, p0, p1, w, t, seg=14):
        """Flat ellipsoid (leaf / petal) spanning p0 -> p1."""
        p0, p1 = V(p0), V(p1); d = p1 - p0
        M = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((w, t, d.length / 2, 1))
        s._add(j, m, lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=1, matrix=M, calc_uvs=True))
    def prism(s, j, m, loc, length, half_w, height, rot=(0, 0, 0)):
        """Gable roof: triangular prism along X, base centred on loc."""
        M = Matrix.Translation(V(loc)) @ Euler(rot).to_matrix().to_4x4()
        def b(bm):
            vs = [bm.verts.new(M @ V(p)) for p in ((-length / 2, -half_w, 0), (-length / 2, half_w, 0), (-length / 2, 0, height),
                                                   (length / 2, -half_w, 0), (length / 2, half_w, 0), (length / 2, 0, height))]
            for f in ((0, 2, 1), (3, 4, 5), (0, 3, 5, 2), (1, 2, 5, 4), (0, 1, 4, 3)): bm.faces.new([vs[i] for i in f])
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        s._add(j, m, b)

    # ---- output
    def build(s):
        s.objs = []
        col = bpy.context.scene.collection
        for j, bm in s.bms.items():
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle(0) > 0.75: e.smooth = False
            me = bpy.data.meshes.new(s.name + "_" + j); bm.to_mesh(me); bm.free()
            for m in s.pm[j]: me.materials.append(m)
            ob = bpy.data.objects.new("M_" + j, me); col.objects.link(ob); s.objs.append(ob)
        def marker(name, pos):
            me = bpy.data.meshes.new(name); e = 0.004
            me.from_pydata([pos + V((e, 0, -e)), pos + V((-e, e, -e)), pos + V((-e, -e, -e)), pos + V((0, 0, 2 * e)),
                            pos + V((-e, 0, e)), pos + V((e, -e, e)), pos + V((e, e, e)), pos + V((0, 0, -2 * e))],
                           [], [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0), (4, 5, 6), (4, 7, 5), (5, 7, 6), (6, 7, 4)])
            ob = bpy.data.objects.new(name, me); col.objects.link(ob); s.objs.append(ob)
        for j, (pos, parent) in s.joints.items():
            if j != "root": marker("J_%s@%s" % (j, parent), pos)
        marker("F_front", V((0, -1, 0))); marker("U_up", V((0, 0, 1)))
    def export(s):
        bpy.ops.object.select_all(action="DESELECT")
        for o in s.objs: o.select_set(True)
        bpy.context.view_layer.objects.active = s.objs[0]
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, s.name + ".fbx"), use_selection=True, object_types={"MESH"},
                                 apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y", bake_space_transform=False,
                                 mesh_smooth_type="OFF", add_leaf_bones=False, bake_anim=False, use_mesh_modifiers=False)

# shared palette
SKIN = mat("F0BE92", 0.3); INK = mat("22202A", 0.5); WHITE = mat("FFFFFF", 0.5); GOLD = mat("F2B632", 0.75)
RED = mat("D8362E", 0.45); BAMBOO = mat("D9C56A", 0.4); BAMBOO_D = mat("A8913F", 0.3); WOOD = mat("9A6B3F", 0.2)
LEAF = mat("4FB04A", 0.3); LEAF_D = mat("2F8F45", 0.3); LEAF_L = mat("86CF4E", 0.3)

def eye(m, j, x, y, z, r=0.06, pupil=0.55, look=(0, 0), white=WHITE, pm=INK):
    m.sph(j, white, (x, y, z), (r, r * 0.55, r * 1.15))
    m.sph(j, pm, (x + look[0] * r, y - r * 0.42, z + look[1] * r), (r * pupil, r * 0.3, r * pupil * 1.15))
    m.sph(j, WHITE, (x + look[0] * r + r * 0.18, y - r * 0.62, z + look[1] * r + r * 0.25), r * 0.16, seg=8)

# ----------------------------------------------------------------------------- Nam
def nam():
    m = Model("nam")
    SHIRT = mat("4A4D58", 0.25); PANTS = mat("FFFFFF", 0.2, tex="pants"); HAIR = mat("17171D", 0.7); HELM = mat("1C1C22", 0.92)
    CREAM = mat("F3E6C8", 0.3); LIP = mat("8E1F33", 0.5); BLUSH = mat("F2917F", 0.2); TONGUE = mat("E8697A", 0.4); FRAME = mat("15151A", 0.75)
    m.joint("hips", (0, 0, 0.52)); m.joint("torso", (0, 0, 0.58), "hips"); m.joint("head", (0, 0, 0.98), "torso")
    m.joint("pony", (0, 0.27, 1.2), "head"); m.joint("pony2", (0, 0.27, 0.95), "pony"); m.joint("lids", (0, -0.25, 1.27), "head")
    m.joint("eyes", (0, -0.27, 1.27), "head"); m.joint("brows", (0, -0.27, 1.38), "head"); m.joint("mouthA", (0, -0.27, 1.13), "head"); m.joint("mouthO", (0, -0.27, 1.12), "head")
    m.joint("bag", (-0.22, -0.02, 0.66), "hips")
    for sd, sx in (("L", 1), ("R", -1)):
        m.joint("arm" + sd, (0.2 * sx, 0, 0.9), "torso"); m.joint("fore" + sd, (0.27 * sx, 0, 0.73), "arm" + sd)
        m.joint("leg" + sd, (0.1 * sx, 0, 0.5), "hips"); m.joint("shin" + sd, (0.105 * sx, 0, 0.28), "leg" + sd)
        m.sph("arm" + sd, SHIRT, (0.21 * sx, 0, 0.9), 0.09)
        m.cap("arm" + sd, SKIN, (0.22 * sx, 0, 0.88), (0.27 * sx, 0, 0.73), 0.056)
        m.cap("fore" + sd, SKIN, (0.27 * sx, 0, 0.73), (0.29 * sx, -0.02, 0.58), 0.053, 0.048)
        m.sph("fore" + sd, SKIN, (0.292 * sx, -0.025, 0.55), 0.068)
        m.cap("leg" + sd, PANTS, (0.1 * sx, 0, 0.5), (0.105 * sx, 0, 0.28), 0.105, 0.105, seg=18)
        m.cyl("shin" + sd, PANTS, (0.105 * sx, 0, 0.3), (0.11 * sx, 0, 0.1), 0.105, 0.125, seg=18)
        m.sph("shin" + sd, PANTS, (0.105 * sx, 0, 0.29), 0.105)
        m.sph("shin" + sd, INK, (0.108 * sx, -0.05, 0.06), (0.088, 0.15, 0.062)); m.sph("shin" + sd, WHITE, (0.108 * sx, -0.05, 0.03), (0.092, 0.154, 0.03))
        m.cap("shin" + sd, WHITE, (0.07 * sx, -0.13, 0.09), (0.146 * sx, -0.13, 0.09), 0.012, seg=6)
    m.sph("hips", PANTS, (0, 0, 0.55), (0.205, 0.16, 0.135), seg=24)
    m.sph("torso", SHIRT, (0, 0, 0.76), (0.205, 0.155, 0.225), seg=24)
    # shirt print: cream geometric square
    m.box("torso", CREAM, (0, -0.14, 0.79), (0.16, 0.03, 0.16), bevel=0.012); m.box("torso", SHIRT, (0, -0.155, 0.79), (0.115, 0.02, 0.115), bevel=0.008)
    m.box("torso", CREAM, (0, -0.165, 0.79), (0.07, 0.015, 0.07), rot=(0, PI / 4, 0), bevel=0.006)
    m.torus("torso", CREAM, (0, 0, 0.76), 0.205, 0.02, rot=(PI / 2 - 0.15, 0.85, 0), seg=28, rseg=6)      # cross-body strap
    m.box("bag", INK, (-0.22, -0.02, 0.58), (0.11, 0.17, 0.16), bevel=0.035)
    m.cyl("bag", WHITE, (-0.278, -0.02, 0.57), (-0.28, -0.02, 0.63), 0.04, 0.0, seg=3)
    m.cyl("torso", SKIN, (0, 0, 0.93), (0, 0, 1.03), 0.062)
    # ---- head
    hz = 1.28
    m.sph("head", SKIN, (0, 0, hz), (0.315, 0.29, 0.295), seg=32)
    for sx in (1, -1): m.sph("head", SKIN, (0.305 * sx, 0.02, hz - 0.04), (0.04, 0.06, 0.07))
    # black hair: cap under the helmet, side locks, low ponytail
    m.sph("head", HAIR, (0, 0.03, hz), (0.325, 0.3, 0.305), seg=32, cut=((0, 0.0, 0), (0, -1, 0.3)))
    for sx in (1, -1):
        m.chain("head", HAIR, [(0.27 * sx, -0.13, hz + 0.12), (0.305 * sx, -0.1, hz - 0.02), (0.29 * sx, -0.07, hz - 0.17)], [0.05, 0.045, 0.02], seg=10)
        m.cap("brows", HAIR, (0.05 * sx, -0.275, hz + 0.105), (0.17 * sx, -0.255, hz + 0.115), 0.013)                # brows
    m.sph("head", HAIR, (0, -0.2, hz + 0.16), (0.24, 0.1, 0.07))                                                    # fringe peeking out
    # helmet: glossy black shell with rim, short visor, yellow sticker, chin strap
    m.sph("head", HELM, (0, 0.0, hz + 0.045), (0.36, 0.34, 0.325), seg=32, cut=((0, 0, hz + 0.07), (0, 0.16, -1)))
    m.torus("head", mat("2B2B33", 0.6), (0, 0, hz + 0.07), 0.35, 0.028, rot=(0.16, 0, 0), seg=36, rseg=8)
    m.sph("head", HELM, (0, -0.3, hz + 0.115), (0.23, 0.17, 0.04), rot=(0.2, 0, 0))
    m.sph("head", mat("E9E24E", 0.6), (0.0, -0.215, hz + 0.3), (0.085, 0.065, 0.03), rot=(0.8, 0, 0))
    for sx in (1, -1):
        m.box("head", HELM, (0.325 * sx, 0.02, hz + 0.0), (0.035, 0.12, 0.13), bevel=0.015)
        m.chain("head", mat("2B2B33", 0.4), [(0.325 * sx, 0.0, hz - 0.03), (0.27 * sx, -0.13, hz - 0.2), (0.1 * sx, -0.22, hz - 0.275), (0, -0.235, hz - 0.285)], [0.012] * 4, seg=6)
    for k in range(3): m.box("head", mat("2B2B33", 0.5), (-0.1 + k * 0.1, 0.02 + 0.0 * k, hz + 0.372 - abs(k - 1) * 0.012), (0.03, 0.2, 0.012), bevel=0.004)    # vents
    # face: big happy eyes behind chunky rectangular glasses, blush, open smile
    for sx in (1, -1):
        ex = 0.118 * sx; ez = hz - 0.01
        m.sph("head", WHITE, (ex, -0.245, ez), (0.068, 0.04, 0.078)); m.sph("eyes", mat("3A2418", 0.6), (ex - 0.008 * sx, -0.275, ez - 0.004), (0.046, 0.02, 0.054))
        m.sph("eyes", INK, (ex - 0.008 * sx, -0.288, ez - 0.004), (0.028, 0.012, 0.034)); m.sph("eyes", WHITE, (ex + 0.012, -0.296, ez + 0.022), 0.014, seg=8)
        m.sph("lids", SKIN, (ex, -0.262, ez), (0.074, 0.04, 0.084))
        # round glasses
        w, y = 0.098, -0.305
        m.torus("head", FRAME, (ex, y, ez), w, 0.016, rot=(PI / 2, 0, 0), seg=28, rseg=8)
        m.cap("head", FRAME, (ex + w * sx, y, ez + 0.02), (0.325 * sx, -0.06, ez + 0.03), 0.013, seg=6)
        m.sph("head", BLUSH, (0.2 * sx, -0.2, hz - 0.125), (0.055, 0.02, 0.034))
    m.cap("head", FRAME, (-0.02, -0.305, hz + 0.02), (0.02, -0.305, hz + 0.02), 0.015, seg=6)
    m.sph("head", SKIN, (0, -0.292, hz - 0.075), (0.03, 0.032, 0.026))
    m.sph("mouthA", LIP, (0, -0.262, hz - 0.15), (0.085, 0.03, 0.055), cut=((0, 0, hz - 0.135), (0, 0, 1)))
    m.sph("mouthA", WHITE, (0, -0.274, hz - 0.142), (0.066, 0.02, 0.016)); m.sph("mouthA", TONGUE, (0, -0.268, hz - 0.185), (0.04, 0.02, 0.018))
    m.sph("mouthO", LIP, (0, -0.27, hz - 0.165), (0.045, 0.025, 0.056)); m.sph("mouthO", TONGUE, (0, -0.282, hz - 0.185), (0.028, 0.014, 0.022))      # surprised "o"
    # open hair: worn loose over the shoulders and down the back. Two joints ("pony" upper, "pony2" lower)
    # let the lengths trail and whip behind the upper mass.
    m.sph("pony", HAIR, (0, 0.2, 1.08), (0.3, 0.15, 0.27), seg=28)
    m.sph("pony2", HAIR, (0, 0.24, 0.86), (0.27, 0.115, 0.25), seg=28)
    for sx in (1, -1):
        m.chain("pony", HAIR, [(0.27 * sx, 0.1, 1.2), (0.3 * sx, 0.1, 1.04), (0.28 * sx, 0.11, 0.93)], [0.085, 0.09, 0.08])
        m.chain("pony2", HAIR, [(0.28 * sx, 0.11, 0.95), (0.26 * sx, 0.13, 0.8), (0.2 * sx, 0.16, 0.64)], [0.08, 0.072, 0.028])
        m.chain("pony2", HAIR, [(0.14 * sx, 0.26, 0.92), (0.13 * sx, 0.27, 0.72), (0.1 * sx, 0.25, 0.6)], [0.1, 0.085, 0.03])
        m.chain("pony", HAIR, [(0.3 * sx, -0.03, 1.16), (0.31 * sx, -0.06, 1.0), (0.275 * sx, -0.085, 0.9)], [0.06, 0.065, 0.055])                         # locks in front of the shoulders
        m.chain("pony2", HAIR, [(0.275 * sx, -0.085, 0.92), (0.26 * sx, -0.095, 0.84), (0.24 * sx, -0.1, 0.76)], [0.055, 0.045, 0.018])
    m.chain("pony2", HAIR, [(0, 0.3, 0.86), (0, 0.3, 0.68), (0, 0.27, 0.56)], [0.11, 0.09, 0.03])
    return m

# ----------------------------------------------------------------------------- enemies
def monkey():
    m = Model("monkey")
    FUR = mat("8C5A3A", 0.2); TAN = mat("ECC99A", 0.25)
    m.joint("body", (0, 0, 0.3)); m.joint("head", (0, 0, 0.68), "body"); m.joint("tail", (0, 0.2, 0.3), "body")
    m.sph("body", FUR, (0, 0, 0.42), (0.28, 0.24, 0.3)); m.sph("body", TAN, (0, -0.1, 0.4), (0.2, 0.17, 0.22))
    for sd, sx in (("L", 1), ("R", -1)):
        m.joint("arm" + sd, (0.24 * sx, 0, 0.6), "body")
        m.cap("arm" + sd, FUR, (0.25 * sx, 0, 0.6), (0.36 * sx, -0.04, 0.3), 0.07, 0.06); m.sph("arm" + sd, TAN, (0.37 * sx, -0.05, 0.26), 0.08)
        m.sph("body", FUR, (0.15 * sx, -0.07, 0.07), (0.12, 0.18, 0.075)); m.sph("body", TAN, (0.15 * sx, -0.11, 0.055), (0.1, 0.14, 0.06))
        m.sph("head", FUR, (0.28 * sx, 0.02, 0.9), (0.1, 0.05, 0.11)); m.sph("head", TAN, (0.285 * sx, -0.012, 0.9), (0.065, 0.03, 0.075))
        eye(m, "head", 0.1 * sx, -0.225, 0.88, 0.062, look=(-0.15 * sx, -0.1))
        m.cap("head", INK, (0.04 * sx, -0.27, 0.935), (0.17 * sx, -0.25, 0.985), 0.018)             # angry brows
    m.sph("head", FUR, (0, 0, 0.86), (0.27, 0.25, 0.26), seg=24)
    m.sph("head", TAN, (0, -0.12, 0.85), (0.21, 0.16, 0.19)); m.sph("head", TAN, (0, -0.2, 0.775), (0.14, 0.11, 0.095))
    m.sph("head", INK, (0, -0.295, 0.8), (0.03, 0.02, 0.018))
    m.sph("head", INK, (0, -0.275, 0.745), (0.085, 0.04, 0.035)); m.box("head", WHITE, (0, -0.305, 0.755), (0.1, 0.02, 0.025), bevel=0.006)
    m.sph("head", FUR, (0, -0.02, 1.12), (0.06, 0.06, 0.07))
    pts = [(0, 0.2, 0.3), (0, 0.36, 0.28), (0, 0.48, 0.38), (0, 0.5, 0.55), (0, 0.42, 0.66), (0, 0.33, 0.6)]
    m.chain("tail", FUR, pts, [0.055, 0.05, 0.048, 0.045, 0.042, 0.04])
    return m

def crab():
    m = Model("crab")
    SH = mat("EB5338", 0.5); SH_D = mat("C83A28", 0.45); BEL = mat("F7A77A", 0.35)
    m.joint("body", (0, 0, 0.25))
    m.sph("body", SH, (0, 0, 0.32), (0.43, 0.3, 0.21), seg=24); m.sph("body", BEL, (0, -0.06, 0.26), (0.36, 0.26, 0.16))
    for i in range(5): m.sph("body", SH_D, (-0.24 + i * 0.12, 0.02 + 0.03 * (i % 2), 0.5), (0.035, 0.035, 0.02))
    m.sph("body", INK, (0, -0.27, 0.25), (0.09, 0.03, 0.03), cut=((0, 0, 0.25), (0, 0, -1)))
    for sd, sx in (("L", 1), ("R", -1)):
        m.cap("body", SH, (0.13 * sx, -0.2, 0.42), (0.16 * sx, -0.24, 0.6), 0.03)
        eye(m, "body", 0.165 * sx, -0.26, 0.66, 0.085, look=(-0.2 * sx, -0.1))
        m.cap("body", INK, (0.06 * sx, -0.32, 0.72), (0.25 * sx, -0.3, 0.8), 0.02)
        m.joint("legs" + sd, (0.33 * sx, 0, 0.26), "body")
        for k, y in enumerate((-0.12, 0.03, 0.18)):
            m.chain("legs" + sd, SH_D, [(0.33 * sx, y, 0.26), (0.52 * sx, y, 0.36), (0.62 * sx, y + 0.02, 0.03)], [0.05, 0.045, 0.02])
        m.joint("claw" + sd, (0.36 * sx, -0.14, 0.36), "body")
        m.cap("claw" + sd, SH_D, (0.36 * sx, -0.14, 0.36), (0.55 * sx, -0.2, 0.52), 0.06, 0.055)
        m.sph("claw" + sd, SH, (0.62 * sx, -0.22, 0.66), (0.14, 0.09, 0.17), rot=(0, -0.35 * sx, 0))
        m.sph("claw" + sd, SH, (0.5 * sx, -0.22, 0.72), (0.05, 0.06, 0.13), rot=(0, 0.5 * sx, 0))
    return m

def cobra():
    m = Model("cobra")
    G = mat("5F9E3B", 0.45); G_D = mat("3E7A2E", 0.4); BEL = mat("E9DFA0", 0.35); EYE = mat("F3D23C", 0.6)
    m.torus("root", G, (0, 0, 0.11), 0.34, 0.115, seg=28, rseg=10); m.torus("root", G_D, (0, 0, 0.28), 0.25, 0.11, seg=28, rseg=10)
    m.torus("root", G, (0, 0, 0.43), 0.15, 0.1, seg=24, rseg=10)
    m.joint("neck", (0, 0, 0.45)); m.joint("head", (0, -0.04, 0.95), "neck")
    m.chain("neck", G, [(0, 0, 0.42), (0, 0.03, 0.62), (0, 0, 0.82), (0, -0.04, 0.95)], [0.1, 0.1, 0.1, 0.1])
    m.sph("neck", G, (0, 0.02, 0.76), (0.3, 0.075, 0.27), seg=24); m.sph("neck", BEL, (0, -0.02, 0.74), (0.2, 0.06, 0.22))
    for k in range(4): m.cap("neck", G_D, (-0.14 + 0.02 * k, -0.08, 0.6 + k * 0.09), (0.14 - 0.02 * k, -0.08, 0.6 + k * 0.09), 0.012)
    m.sph("head", G, (0, -0.15, 1.0), (0.135, 0.21, 0.1)); m.sph("head", BEL, (0, -0.17, 0.965), (0.11, 0.18, 0.07))
    for sx in (1, -1):
        m.sph("head", EYE, (0.085 * sx, -0.22, 1.045), (0.04, 0.045, 0.04)); m.sph("head", INK, (0.1 * sx, -0.245, 1.045), (0.016, 0.025, 0.034))
        m.cap("head", G_D, (0.03 * sx, -0.3, 1.075), (0.13 * sx, -0.17, 1.1), 0.014)
    m.joint("tongue", (0, -0.34, 0.98), "head")
    m.cyl("tongue", RED, (0, -0.33, 0.98), (0, -0.46, 0.97), 0.014, 0.01)
    m.cyl("tongue", RED, (0, -0.46, 0.97), (0.04, -0.53, 0.99), 0.01, 0.002); m.cyl("tongue", RED, (0, -0.46, 0.97), (-0.04, -0.53, 0.99), 0.01, 0.002)
    return m

def mosquito():
    m = Model("mosquito")
    D = mat("2A2A36", 0.5); W = mat("F4F4F4", 0.4); WING = mat("CFE6FF", 0.9); EYE = mat("E0303A", 0.8, 0.5)
    m.joint("body", (0, 0, 0.4))
    m.sph("body", D, (0, 0, 0.42), (0.14, 0.17, 0.14)); m.sph("body", D, (0, -0.2, 0.46), 0.105)
    for sx in (1, -1): m.sph("body", EYE, (0.06 * sx, -0.27, 0.49), 0.045)
    m.cyl("body", D, (0, -0.28, 0.44), (0, -0.62, 0.3), 0.018, 0.004)
    for i in range(5): m.sph("body", W if i % 2 else D, (0, 0.14 + i * 0.1, 0.4 - i * 0.03), (0.105 - i * 0.012, 0.075, 0.105 - i * 0.012))
    for sx in (1, -1):
        for k, y in enumerate((-0.1, 0.0, 0.1)):
            m.chain("body", D, [(0.1 * sx, y, 0.36), (0.26 * sx, y - 0.05 + k * 0.05, 0.42), (0.34 * sx, y - 0.1 + k * 0.1, 0.02)], [0.014, 0.012, 0.008], seg=6)
    for sd, sx in (("L", 1), ("R", -1)):
        m.joint("wing" + sd, (0.06 * sx, 0.02, 0.54), "body")
        m.ell("wing" + sd, WING, (0.06 * sx, 0.02, 0.54), (0.5 * sx, 0.3, 0.74), 0.13, 0.012)
    return m

def durian():
    m = Model("durian")
    B = mat("A9B63A", 0.3); S1 = mat("8FA02E", 0.3); S2 = mat("C9D05A", 0.3)
    c = V((0, 0, 0.58)); rad = 0.46
    m.sph("root", B, c, (rad, rad, rad * 1.08), seg=24)
    n = 64
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n; r = math.sqrt(1 - z * z); a = i * 2.39996
        d = V((r * math.cos(a), r * math.sin(a), z * 1.08))
        m.cyl("root", S2 if i % 3 == 0 else S1, c + d * rad * 0.93, c + d * (rad + 0.15), 0.1, 0.0, seg=6)
    m.cyl("root", WOOD, (0, 0, 1.05), (0, 0, 1.22), 0.04, 0.05)
    m.joint("face", (0, -0.45, 0.58))
    for sx in (1, -1):
        eye(m, "face", 0.15 * sx, -0.47, 0.64, 0.085, look=(-0.2 * sx, -0.15))
        m.cap("face", INK, (0.04 * sx, -0.53, 0.7), (0.26 * sx, -0.5, 0.8), 0.026)
    for k in range(4): m.cap("face", INK, (-0.12 + k * 0.06, -0.52, 0.44 + (0.035 if k % 2 else 0)), (-0.06 + k * 0.06, -0.52, 0.44 + (0 if k % 2 else 0.035)), 0.014)
    return m

def ghost():
    m = Model("ghost")
    ROBE = mat("E4EEF6", 0.3); MASK = mat("FAF6EA", 0.4); HAT = mat("D9B26C", 0.2); GRN = mat("3FA65A", 0.4)
    m.joint("body", (0, 0, 0.1)); m.joint("head", (0, 0, 0.72), "body")
    m.cyl("body", ROBE, (0, 0, 0.02), (0, 0, 0.75), 0.36, 0.2, seg=20); m.sph("body", ROBE, (0, 0, 0.75), 0.2)
    for i in range(10):
        a = i * 2 * PI / 10
        m.sph("body", ROBE, (0.34 * math.cos(a), 0.34 * math.sin(a), 0.03), (0.11, 0.11, 0.09))
    for sd, sx in (("L", 1), ("R", -1)):
        m.joint("arm" + sd, (0.2 * sx, 0, 0.66), "body")
        m.cap("arm" + sd, ROBE, (0.2 * sx, 0, 0.66), (0.42 * sx, -0.14, 0.52), 0.085, 0.11)
        m.sph("head", RED, (0.25 * sx, 0.02, 1.0), (0.05, 0.13, 0.17)); m.sph("head", GOLD, (0.27 * sx, 0.0, 1.0), (0.03, 0.08, 0.1))
        m.sph("head", INK, (0.095 * sx, -0.19, 1.02), (0.075, 0.03, 0.085)); eye(m, "head", 0.095 * sx, -0.2, 1.02, 0.05, look=(-0.1 * sx, 0))
        m.sph("head", mat("F09AB0", 0.3), (0.13 * sx, -0.18, 0.9), (0.04, 0.02, 0.03))
    m.sph("head", MASK, (0, 0, 0.98), (0.23, 0.21, 0.3), seg=24)
    m.cyl("head", RED, (0, -0.19, 0.95), (0, -0.56, 0.86), 0.05, 0.004, seg=10)
    m.sph("head", RED, (0, -0.2, 0.82), (0.11, 0.03, 0.04), cut=((0, 0, 0.83), (0, 0, 1)))
    for k in range(4): m.box("head", WHITE, (-0.06 + k * 0.04, -0.225, 0.815), (0.03, 0.015, 0.03), bevel=0.005)
    m.cyl("head", HAT, (0, 0, 1.18), (0, 0, 1.72), 0.22, 0.0, seg=20)
    m.torus("head", RED, (0, 0, 1.2), 0.215, 0.025); m.torus("head", GRN, (0, 0, 1.3), 0.175, 0.02); m.torus("head", GOLD, (0, 0, 1.4), 0.135, 0.018)
    m.sph("head", RED, (0, 0, 1.72), 0.035)
    return m

# ----------------------------------------------------------------------------- collectibles
def coin():
    m = Model("coin")
    G1 = mat("F7BE22", 0.85, 0.3); G2 = mat("FFDF6B", 0.85, 0.4); G3 = mat("C9860E", 0.8)
    m.cyl("root", G1, (0, -0.035, 0), (0, 0.035, 0), 0.3, seg=32)
    m.torus("root", G2, (0, 0, 0), 0.285, 0.04, rot=(PI / 2, 0, 0), seg=32)
    for y in (-1, 1):
        m.cyl("root", G2, (0, 0.03 * y, 0), (0, 0.05 * y, 0), 0.2, 0.19, seg=28)
        # raised baht sign
        m.box("root", G3, (0, 0.055 * y, 0), (0.035, 0.02, 0.3), bevel=0.008)
        m.box("root", G3, (-0.05, 0.055 * y, 0), (0.035, 0.02, 0.22), bevel=0.008)
        m.torus("root", G3, (-0.03, 0.055 * y, 0.055), 0.055, 0.018, rot=(PI / 2, 0, 0), seg=14, rseg=6, arc=PI) if False else None
        for z in (0.055, -0.055):
            m.sph("root", G3, (0.02, 0.055 * y, z), (0.075, 0.012, 0.055))
    return m

def lotus():
    m = Model("lotus")
    P1 = mat("F06BA8", 0.35); P2 = mat("F8A3C8", 0.35); P3 = mat("FFD3E4", 0.35, 0.2); Y = mat("FFD23F", 0.4, 0.5)
    m.sph("root", LEAF_D, (0, 0, 0.03), (0.5, 0.5, 0.035), seg=24)
    for n, tilt, ln, w, mt, z in ((9, 1.15, 0.46, 0.13, P1, 0.07), (7, 0.75, 0.44, 0.12, P2, 0.09), (5, 0.35, 0.4, 0.1, P3, 0.1)):
        for i in range(n):
            a = i * 2 * PI / n + tilt
            d = V((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)))
            p0 = V((math.cos(a) * 0.05, math.sin(a) * 0.05, z))
            m.ell("root", mt, p0, p0 + d * ln, w, 0.035)
    m.sph("root", Y, (0, 0, 0.2), (0.1, 0.1, 0.09))
    return m

def somtam():
    m = Model("somtam")
    PL = mat("FAFAFF", 0.8); BL = mat("3D6FD0", 0.7); SH = mat("D9E89A", 0.3); SH2 = mat("B9D676", 0.3); CAR = mat("F4922E", 0.3)
    TOM = mat("E23B2E", 0.6); TOM2 = mat("F47A5A", 0.5); LIME = mat("7CC043", 0.5); NUT = mat("D9B27A", 0.3)
    m.sph("root", PL, (0, 0, 0.05), (0.56, 0.56, 0.06), seg=28); m.torus("root", BL, (0, 0, 0.065), 0.52, 0.03, seg=32)
    m.sph("root", SH2, (0, 0, 0.1), (0.36, 0.36, 0.14))
    for i in range(70):
        a = R.uniform(0, 2 * PI); rr = R.uniform(0, 0.34); h = 0.1 + (0.36 - rr) * 0.7 * R.uniform(0.6, 1)
        p = V((math.cos(a) * rr, math.sin(a) * rr, h)); b = R.uniform(0, 2 * PI); ln = R.uniform(0.12, 0.22)
        d = V((math.cos(b) * ln, math.sin(b) * ln, R.uniform(-0.05, 0.05)))
        m.cap("root", R.choice([SH, SH, SH2, CAR]), p - d, p + d, 0.016, 0.016, seg=6)
    for a in (0.3, 1.9, 3.5, 5.0):
        p = V((math.cos(a) * 0.22, math.sin(a) * 0.22, 0.27))
        m.sph("root", TOM, p, (0.085, 0.06, 0.07), rot=(0.4, 0.3, a)); m.sph("root", TOM2, p + V((0, 0, 0.03)), (0.06, 0.04, 0.045), rot=(0.4, 0.3, a))
    m.sph("root", LIME, (0.3, -0.18, 0.16), (0.1, 0.07, 0.07), rot=(0, 0.3, 0.6)); m.sph("root", LIME, (-0.3, 0.12, 0.16), (0.1, 0.07, 0.07), rot=(0, -0.3, 2.6))
    for i in range(9):
        a = i * 0.7; m.sph("root", NUT, (math.cos(a) * 0.17, math.sin(a) * 0.17, 0.33 + 0.02 * (i % 2)), (0.03, 0.022, 0.022), rot=(0, 0, a))
    pts = [(-0.1, -0.02, 0.4), (-0.02, 0.0, 0.43), (0.07, 0.01, 0.43), (0.14, 0.03, 0.4)]
    m.chain("root", RED, pts, [0.035, 0.032, 0.025, 0.008], seg=8); m.cyl("root", LEAF_D, (-0.1, -0.02, 0.4), (-0.16, -0.04, 0.42), 0.012, 0.008)
    return m

def sangsom():
    m = Model("sangsom")
    GL = mat("B4601C", 0.92); GL2 = mat("8A3F10", 0.92); LAB = mat("FFF3D2", 0.3); CAP = mat("1E1E24", 0.6)
    m.cyl("root", GL, (0, 0, 0.0), (0, 0, 0.52), 0.17, seg=24); m.sph("root", GL, (0, 0, 0.52), (0.17, 0.17, 0.13))
    m.sph("root", GL2, (0, 0, 0.02), (0.17, 0.17, 0.03))
    m.cyl("root", GL, (0, 0, 0.6), (0, 0, 0.8), 0.065, 0.055); m.cyl("root", CAP, (0, 0, 0.78), (0, 0, 0.88), 0.07); m.torus("root", GOLD, (0, 0, 0.775), 0.068, 0.012)
    m.cyl("root", LAB, (0, 0, 0.14), (0, 0, 0.42), 0.174, seg=24, caps=False)
    m.cyl("root", RED, (0, 0, 0.36), (0, 0, 0.42), 0.177, seg=24, caps=False); m.cyl("root", GOLD, (0, 0, 0.14), (0, 0, 0.18), 0.177, seg=24, caps=False)
    for y in (-1, 1):
        m.sph("root", RED, (0, 0.172 * y, 0.27), (0.055, 0.012, 0.055))
        for i in range(10):
            a = i * 2 * PI / 10
            m.cap("root", mat("F29A2E", 0.5), (math.cos(a) * 0.065, 0.176 * y, 0.27 + math.sin(a) * 0.065), (math.cos(a) * 0.085, 0.176 * y, 0.27 + math.sin(a) * 0.085), 0.008, seg=6)
    return m

def chili():
    m = Model("chili")
    C = mat("E2261C", 0.85)
    pts, rad = [], []
    for i in range(11):
        t = i / 10; a = -0.5 + t * 1.9
        pts.append((math.sin(a) * 0.42 - 0.12, 0, 0.72 - (1 - math.cos(a)) * 0.5 - t * 0.2)); rad.append(0.125 * (1 - t) ** 0.7 + 0.012)
    m.chain("root", C, pts, rad, seg=14)
    m.sph("root", LEAF_D, pts[0], (0.11, 0.11, 0.06)); m.chain("root", LEAF, [pts[0], (pts[0][0] - 0.03, 0, pts[0][2] + 0.12), (pts[0][0] + 0.06, 0, pts[0][2] + 0.22)], [0.035, 0.03, 0.022], seg=8)
    return m

def mango():
    m = Model("mango")
    m.sph("root", mat("FFB82E", 0.6), (0, 0, 0.32), (0.25, 0.21, 0.3), rot=(0, 0.25, 0), seg=24)
    m.sph("root", mat("F9743A", 0.6), (0.07, -0.03, 0.4), (0.19, 0.17, 0.2), rot=(0, 0.25, 0))
    m.cyl("root", WOOD, (0.07, 0, 0.6), (0.08, 0, 0.68), 0.018); m.ell("root", LEAF, (0.08, 0, 0.66), (0.3, 0, 0.74), 0.07, 0.015)
    return m

def fireball():
    m = Model("fireball")
    m.sph("root", mat("FFE066", 0.2, 4), (0, 0, 0), 0.16); m.sph("root", mat("FF7A1A", 0.2, 2.5), (0, 0.03, 0), (0.21, 0.24, 0.21))
    for i in range(6):
        a = i * PI / 3
        m.cyl("root", mat("FF4A12", 0.2, 2), (math.cos(a) * 0.1, 0.1, math.sin(a) * 0.1), (math.cos(a) * 0.14, 0.5, math.sin(a) * 0.14), 0.09, 0.0, seg=8)
    return m

def venom():
    m = Model("venom")
    m.sph("root", mat("9BE234", 0.9, 1.5), (0, 0, 0), (0.13, 0.17, 0.13)); m.cyl("root", mat("9BE234", 0.9, 1.5), (0, 0.08, 0), (0, 0.36, 0), 0.1, 0.0, seg=10)
    return m

def flame():
    m = Model("flame")   # 1 unit tall; scaled in game
    O = mat("FF4A12", 0.1, 3); Y = mat("FFB01E", 0.1, 5); W = mat("FFF4B0", 0.1, 8)
    def tongue(mt, x, y, r, h, lean):
        m.sph("root", mt, (x, y, r * 0.9), (r, r, r * 1.15)); m.chain("root", mt, [(x, y, r * 1.2), (x + lean * 0.5, y, r * 1.2 + (h - r * 1.2) * 0.55), (x + lean, y, h)], [r * 0.9, r * 0.55, 0.004], seg=12)
    tongue(O, 0, 0, 0.27, 1.0, 0.05); tongue(O, 0.17, 0.05, 0.16, 0.66, 0.1); tongue(O, -0.16, -0.04, 0.15, 0.58, -0.1); tongue(O, 0.02, 0.17, 0.14, 0.5, 0.02); tongue(O, -0.02, -0.17, 0.14, 0.54, -0.03)
    tongue(Y, 0, -0.02, 0.19, 0.72, 0.03); tongue(Y, 0.1, -0.05, 0.1, 0.42, 0.06); tongue(Y, -0.1, -0.06, 0.1, 0.38, -0.06)
    tongue(W, 0, -0.05, 0.11, 0.42, 0.0)
    return m

# ----------------------------------------------------------------------------- props
def lantern(m, j, p, col, emis=0.0, s=1.0):
    L = mat(col, 0.3, emis)
    m.sph(j, L, p, (0.2 * s, 0.2 * s, 0.25 * s))
    for k in range(6):
        a = k * PI / 6; m.torus(j, mat(col, 0.3, emis * 0.6), p, 0.203 * s, 0.008 * s, rot=(PI / 2, 0, a), seg=16, rseg=4) if False else None
    m.cyl(j, GOLD, V(p) + V((0, 0, 0.22 * s)), V(p) + V((0, 0, 0.29 * s)), 0.09 * s); m.cyl(j, GOLD, V(p) - V((0, 0, 0.29 * s)), V(p) - V((0, 0, 0.22 * s)), 0.09 * s)
    m.cyl(j, RED, V(p) - V((0, 0, 0.29 * s)), V(p) - V((0, 0, 0.5 * s)), 0.025 * s, 0.035 * s, seg=8)

def bamboo_pole(m, j, p0, p1, r, mt=BAMBOO, ring=BAMBOO_D, nodes=4):
    m.cyl(j, mt, p0, p1, r, seg=12)
    p0, p1 = V(p0), V(p1); d = p1 - p0
    q = d.to_track_quat("Z", "Y").to_euler()
    for i in range(1, nodes + 1):
        m.torus(j, ring, p0 + d * (i / (nodes + 1)), r, r * 0.22, rot=q, seg=12, rseg=5)

def checkpoint(on):
    m = Model("checkpoint_on" if on else "checkpoint_off")
    bamboo_pole(m, "root", (0, 0, 0), (0, 0, 2.1), 0.055, nodes=5)
    m.chain("root", BAMBOO, [(0, 0, 2.1), (0.08, 0, 2.25), (0.25, 0, 2.3), (0.4, 0, 2.22)], [0.05, 0.045, 0.04, 0.035])
    m.joint("lantern", (0.4, 0, 2.2))
    m.cyl("lantern", INK, (0.4, 0, 2.2), (0.4, 0, 2.0), 0.008, seg=6)
    lantern(m, "lantern", (0.4, 0, 1.72), "FFD95A" if on else "C8322C", 4.0 if on else 0.0)
    return m

def gong():
    m = Model("gong")
    RP = mat("C0281F", 0.5); ROOF = mat("2F9A6B", 0.45); TRIM = mat("F0862A", 0.45)
    for sx in (1, -1):
        m.cyl("root", RP, (1.05 * sx, 0, 0), (1.05 * sx, 0, 2.45), 0.1, seg=16)
        m.cyl("root", GOLD, (1.05 * sx, 0, 0), (1.05 * sx, 0, 0.14), 0.15); m.cyl("root", GOLD, (1.05 * sx, 0, 2.3), (1.05 * sx, 0, 2.45), 0.14)
        m.chain("root", GOLD, [(1.5 * sx, 0, 2.6), (1.7 * sx, 0, 2.72), (1.82 * sx, 0, 2.95)], [0.05, 0.04, 0.01])       # chofa finials
        m.chain("root", GOLD, [(1.15 * sx, 0, 3.0), (1.3 * sx, 0, 3.1), (1.38 * sx, 0, 3.28)], [0.045, 0.035, 0.01])
    m.box("root", RP, (0, 0, 2.5), (2.6, 0.22, 0.16), bevel=0.03)
    m.box("root", mat("FBF6EA", 0.25), (0, 0, 0.05), (3.0, 1.3, 0.12), bevel=0.03); m.box("root", mat("E6DFCF", 0.25), (0, -0.75, 0.02), (1.3, 0.4, 0.07), bevel=0.02)
    m.prism("root", TRIM, (0, 0, 2.58), 3.1, 0.62, 0.42); m.prism("root", ROOF, (0, 0, 2.62), 2.9, 0.56, 0.42)
    m.prism("root", TRIM, (0, 0, 2.95), 2.3, 0.44, 0.36); m.prism("root", ROOF, (0, 0, 2.99), 2.1, 0.38, 0.36)
    m.cyl("root", GOLD, (0, 0, 3.3), (0, 0, 3.75), 0.05, 0.0, seg=10)
    m.joint("gong", (0, 0, 2.42))
    for sx in (1, -1): m.cyl("gong", WOOD, (0.4 * sx, 0, 2.42), (0.35 * sx, 0, 1.85), 0.015, seg=6)
    G = mat("E9A91E", 0.9, 0.25); G2 = mat("FFD45A", 0.9, 0.4); G3 = mat("B87A10", 0.85)
    m.cyl("gong", G, (0, -0.05, 1.3), (0, 0.05, 1.3), 0.72, seg=40); m.torus("gong", G3, (0, 0, 1.3), 0.72, 0.055, rot=(PI / 2, 0, 0), seg=40)
    m.torus("gong", G3, (0, -0.05, 1.3), 0.45, 0.025, rot=(PI / 2, 0, 0), seg=32, rseg=6); m.sph("gong", G2, (0, -0.05, 1.3), (0.2, 0.1, 0.2))
    return m

def drum():
    m = Model("drum")
    m.sph("root", mat("D2332A", 0.5), (0, 0, 0.3), (0.47, 0.47, 0.42), seg=28, cut=((0, 0, 0.56), (0, 0, 1)))
    m.cyl("root", mat("D2332A", 0.5), (0, 0, 0.0), (0, 0, 0.1), 0.36, 0.42, seg=28)
    m.cyl("root", mat("F6E6C2", 0.3), (0, 0, 0.54), (0, 0, 0.6), 0.4, seg=28); m.torus("root", GOLD, (0, 0, 0.57), 0.4, 0.04, seg=28)
    m.torus("root", GOLD, (0, 0, 0.06), 0.4, 0.035, seg=28)
    for i in range(12):
        a = i * 2 * PI / 12; r = 0.475
        m.cyl("root", GOLD, (math.cos(a) * r, math.sin(a) * r, 0.5), (math.cos(a) * r * 0.99, math.sin(a) * r * 0.99, 0.2), 0.06, 0.0, seg=3)
    return m

def brazier():
    m = Model("brazier")
    CLAY = mat("C9683E", 0.2); CLAY_D = mat("9C4A2A", 0.2)
    m.cyl("root", CLAY, (0, 0, 0), (0, 0, 0.5), 0.27, 0.4, seg=24); m.torus("root", mat("9FA3AD", 0.6), (0, 0, 0.5), 0.4, 0.045)
    m.cyl("root", CLAY_D, (0, 0, 0.5), (0, 0, 0.53), 0.37, seg=24)
    m.box("root", INK, (0, -0.31, 0.2), (0.22, 0.08, 0.14), bevel=0.03); m.box("root", mat("FF9A2E", 0.2, 3), (0, -0.33, 0.19), (0.14, 0.05, 0.07), bevel=0.02)
    for i in range(7):
        a = i * 0.9; rr = 0.2 if i else 0
        m.sph("root", INK if i % 2 else mat("FF6A1E", 0.2, 2.5), (math.cos(a) * rr, math.sin(a) * rr, 0.55), (0.09, 0.09, 0.06))
    return m

def spike():
    m = Model("spike")
    T = mat("EAD9A0", 0.3); T2 = mat("C9B170", 0.3)
    for iy, y in enumerate((-0.45, 0.0, 0.45)):
        for ix in range(4):
            x = -0.375 + ix * 0.25 + (0.06 if iy % 2 else -0.03); h = 0.52 + 0.08 * ((ix + iy) % 2)
            m.cyl("root", T, (x, y, 0.0), (x + 0.02 * (ix - 1.5), y, h), 0.085, 0.0, seg=10); m.torus("root", T2, (x, y, 0.03), 0.085, 0.02, seg=10, rseg=5)
    return m

def raft():
    m = Model("raft")   # 3 long (x), top at z=0, centred
    for i in range(7):
        y = -0.72 + i * 0.24
        bamboo_pole(m, "root", (-1.5, y, -0.12), (1.5, y, -0.12), 0.12, nodes=5)
        m.sph("root", BAMBOO_D, (-1.5, y, -0.12), (0.02, 0.1, 0.1)); m.sph("root", BAMBOO_D, (1.5, y, -0.12), (0.02, 0.1, 0.1))
    for x in (-1.05, 1.05):
        m.box("root", WOOD, (x, 0, -0.02), (0.1, 1.74, 0.06), bevel=0.02); m.box("root", WOOD, (x, 0, -0.25), (0.14, 1.6, 0.08), bevel=0.02)
    return m

def crumble():
    m = Model("crumble")   # 1 wide, top at z=0
    W1 = mat("B98552", 0.2); W2 = mat("A06F40", 0.2); W3 = mat("6E4826", 0.2)
    for i, y in enumerate((-0.5, 0.0, 0.5)):
        m.box("root", W1 if i % 2 else W2, (0, y, -0.14), (1.0, 0.48, 0.26), bevel=0.035)
    for x, y, a in ((-0.2, -0.5, 0.5), (0.25, 0.0, -0.4), (-0.05, 0.5, 0.3), (0.3, -0.5, -0.6)):
        m.box("root", W3, (x, y, -0.005), (0.035, 0.36, 0.02), rot=(0, 0, a), bevel=0)
    m.box("root", W3, (0.1, -0.745, -0.12), (0.03, 0.01, 0.2), rot=(0, 0.4, 0), bevel=0); m.box("root", W3, (-0.25, -0.745, -0.14), (0.03, 0.01, 0.16), rot=(0, -0.5, 0), bevel=0)
    return m

def oneway():
    m = Model("oneway")   # 1 wide, top at z=0: bamboo poles lashed with rope
    ROPE = mat("7A5234", 0.2)
    for i in range(5):
        y = -0.52 + i * 0.26
        m.cyl("root", BAMBOO, (-0.5, y, -0.1), (0.5, y, -0.1), 0.1, seg=14, caps=False)
        m.torus("root", BAMBOO_D, (0.25 - 0.5 * (i % 2), y, -0.1), 0.1, 0.022, rot=(0, PI / 2, 0), seg=14, rseg=5)
    for x in (-0.3, 0.3):
        m.box("root", ROPE, (x, 0, -0.005), (0.05, 1.3, 0.025), bevel=0.01); m.box("root", ROPE, (x, 0, -0.2), (0.05, 1.3, 0.025), bevel=0.01)
    m.box("root", WOOD, (0, 0, -0.26), (0.16, 1.2, 0.1), bevel=0.02)
    return m

# ----------------------------------------------------------------------------- scenery
def banana():
    m = Model("banana")
    TR = mat("9DB85A", 0.3)
    m.chain("root", TR, [(0, 0, 0), (0.03, 0, 0.6), (0.0, 0, 1.2), (-0.04, 0, 1.75)], [0.15, 0.13, 0.11, 0.09])
    top = V((-0.04, 0, 1.75))
    for i in range(8):
        a = i * 2 * PI / 8 + 0.3; up = 0.55 if i % 2 else 0.2; ln = 1.15 if i % 2 else 1.3
        d = V((math.cos(a), math.sin(a), up)).normalized()
        mid = top + d * ln * 0.55; tip = mid + (d + V((0, 0, -0.75))).normalized() * ln * 0.5
        m.ell("root", LEAF if i % 2 else LEAF_D, top, mid, 0.2, 0.02); m.ell("root", LEAF_L if i % 3 == 0 else LEAF, mid - d * 0.08, tip, 0.17, 0.02)
        m.cap("root", LEAF_L, top, mid, 0.022, 0.012, seg=6)
    for i in range(7):
        a = i * 0.9; m.cap("root", mat("FFD83A", 0.5), (0.1 + math.cos(a) * 0.07, math.sin(a) * 0.07 - 0.08, 1.45 - i * 0.03), (0.13 + math.cos(a) * 0.11, math.sin(a) * 0.11 - 0.1, 1.28 - i * 0.03), 0.035, 0.025, seg=8)
    return m

def palm():
    m = Model("palm")
    TR = mat("9A7B4F", 0.2); TR2 = mat("7C6039", 0.2)
    pts = [(0, 0, 0), (0.1, 0, 0.7), (0.24, 0, 1.5), (0.36, 0, 2.3), (0.43, 0, 3.0), (0.45, 0, 3.5)]
    m.chain("root", TR, pts, [0.2, 0.155, 0.135, 0.12, 0.11, 0.1])
    m.sph("root", TR, (0, 0, 0.05), (0.27, 0.27, 0.16))
    for i in range(16):
        t = (i + 0.5) / 16 * 3.4; x = 0.133 * t + 0.0005 * t * t
        m.torus("root", TR2, (min(0.45, x), 0, t), 0.168 - t * 0.02, 0.018, seg=14, rseg=5)
    top = V((0.45, 0, 3.5))
    m.sph("root", mat("6FA83E", 0.3), top + V((0, 0, 0.05)), (0.16, 0.16, 0.2))
    # fronds: an arching rib with rows of drooping leaflets on both sides
    for i in range(11):
        a = i * 2 * PI / 11 + 0.2; up = 0.75 if i % 2 else 0.35
        d = V((math.cos(a), math.sin(a), up)).normalized(); side = V((-math.sin(a), math.cos(a), 0))
        p = top; prev = d; rib = [top.copy()]
        for k in range(7):
            nd = (prev + V((0, 0, -0.26))).normalized(); p = p + nd * 0.3; rib.append(p.copy()); prev = nd
        m.chain("root", LEAF_D, rib, [0.035, 0.03, 0.026, 0.022, 0.018, 0.014, 0.01, 0.005], seg=6)
        for k in range(1, 8):
            base = rib[k]; ln = 0.5 * math.sin((k / 8.0) * PI) ** 0.7 + 0.12
            for sgn in (1, -1):
                tip = base + side * sgn * ln * 0.8 + V((0, 0, -ln * 0.75)) + (rib[k] - rib[k - 1]) * 0.6
                m.ell("root", (LEAF, LEAF_L, LEAF_D)[(k + i) % 3], base, tip, 0.05, 0.008, seg=6)
    for a in (0.5, 2.6, 4.4): m.sph("root", mat("6E5A2E", 0.4), top + V((math.cos(a) * 0.15, math.sin(a) * 0.15, -0.14)), 0.115, seg=14)
    return m

def bamboo():
    m = Model("bamboo")
    G = mat("6FB24A", 0.45); G2 = mat("4E8E38", 0.4)
    for i, (x, y, h, lean) in enumerate(((0, 0, 3.1, 0.05), (0.22, 0.1, 2.6, 0.12), (-0.2, 0.05, 2.8, -0.1), (0.08, -0.16, 2.2, 0.02), (-0.1, 0.2, 3.3, -0.03))):
        top = (x + lean * h, y, h)
        m.cyl("root", G, (x, y, 0), top, 0.06, 0.045, seg=10)
        for k in range(1, 7):
            t = k / 7; m.torus("root", G2, (x + lean * h * t, y, h * t), 0.058, 0.014, seg=10, rseg=5)
        for k in range(5):
            t = 0.55 + k * 0.1; a = k * 2.4 + i
            p = V((x + lean * h * t, y, h * t)); d = V((math.cos(a), math.sin(a), 0.25)).normalized()
            m.ell("root", LEAF if k % 2 else LEAF_L, p, p + d * 0.42, 0.055, 0.01, seg=8)
    return m

def grass():
    m = Model("grass")
    for i in range(11):
        a = i * 2.4; rr = 0.04 + 0.03 * (i % 4); h = 0.3 + 0.28 * ((i * 7) % 5) / 4
        p = V((math.cos(a) * rr * 3, math.sin(a) * rr * 2, 0)); tip = p + V((math.cos(a) * 0.16, math.sin(a) * 0.1, h))
        m.cyl("root", (LEAF, LEAF_L, LEAF_D)[i % 3], p, tip, 0.035, 0.0, seg=5)
    return m

def rice():
    m = Model("rice")
    RG = mat("A8D24A", 0.3); RY = mat("E6D25A", 0.3)
    for i in range(13):
        a = i * 2.4; rr = 0.03 + 0.03 * (i % 4); h = 0.55 + 0.3 * ((i * 5) % 7) / 6
        p = V((math.cos(a) * rr * 3, math.sin(a) * rr * 2, 0)); mid = p + V((math.cos(a) * 0.1, math.sin(a) * 0.06, h * 0.7)); tip = mid + V((math.cos(a) * 0.2, math.sin(a) * 0.12, h * 0.25))
        m.cyl("root", RG, p, mid, 0.022, 0.015, seg=5); m.cyl("root", RY if i % 2 else RG, mid, tip, 0.015, 0.0, seg=5)
    return m

def flower():
    m = Model("flower")
    m.cyl("root", LEAF_D, (0, 0, 0), (0, 0, 0.26), 0.015, seg=5)
    for i in range(5):
        a = i * 2 * PI / 5; m.sph("root", WHITE, (math.cos(a) * 0.07, math.sin(a) * 0.07, 0.27), (0.06, 0.06, 0.02))
    m.sph("root", mat("FFD23F", 0.4, 0.3), (0, 0, 0.285), 0.04)
    return m

def cart():
    m = Model("cart")
    BL = mat("3C7DD9", 0.5); BL2 = mat("2A5DB0", 0.5); STEEL = mat("C9CED6", 0.8)
    m.box("root", BL, (0, 0, 0.62), (1.3, 0.7, 0.5), bevel=0.04); m.box("root", STEEL, (0, 0, 0.89), (1.4, 0.8, 0.06), bevel=0.02)
    m.box("root", WHITE, (0, -0.36, 0.64), (0.95, 0.02, 0.22), bevel=0.01); m.box("root", RED, (0, -0.375, 0.64), (0.5, 0.01, 0.08), bevel=0.004)
    for sx in (1, -1):
        for y in (-0.38, 0.38):
            m.torus("root", INK, (0.42 * sx, y, 0.22), 0.17, 0.055, rot=(PI / 2, 0, 0), seg=20); m.cyl("root", STEEL, (0.42 * sx, y - 0.03, 0.22), (0.42 * sx, y + 0.03, 0.22), 0.1)
    m.cap("root", STEEL, (0.65, -0.25, 0.8), (0.95, -0.25, 0.95), 0.02); m.cap("root", STEEL, (0.65, 0.25, 0.8), (0.95, 0.25, 0.95), 0.02); m.cap("root", STEEL, (0.95, -0.25, 0.95), (0.95, 0.25, 0.95), 0.02)
    m.cyl("root", STEEL, (-0.1, 0.2, 0.9), (-0.1, 0.2, 2.25), 0.025, seg=8)
    for i in range(8):                                                 # umbrella wedges red / white
        a0 = i * PI / 4; a1 = a0 + PI / 4; c = V((-0.1, 0.2, 2.3)); rr = 1.0; zz = 1.95
        def wedge(bm, a0=a0, a1=a1):
            vs = [bm.verts.new(c), bm.verts.new((c.x + math.cos(a0) * rr, c.y + math.sin(a0) * rr, zz)), bm.verts.new((c.x + math.cos((a0 + a1) / 2) * rr * 1.02, c.y + math.sin((a0 + a1) / 2) * rr * 1.02, zz - 0.02)), bm.verts.new((c.x + math.cos(a1) * rr, c.y + math.sin(a1) * rr, zz))]
            ws = [bm.verts.new(v.co - V((0, 0, 0.03))) for v in vs]
            bm.faces.new((vs[0], vs[1], vs[2])); bm.faces.new((vs[0], vs[2], vs[3])); bm.faces.new((ws[0], ws[2], ws[1])); bm.faces.new((ws[0], ws[3], ws[2]))
            bm.faces.new((vs[1], ws[1], ws[2], vs[2])); bm.faces.new((vs[2], ws[2], ws[3], vs[3]))
        m._add("root", RED if i % 2 else WHITE, wedge)
    m.sph("root", GOLD, (-0.1, 0.2, 2.32), 0.04)
    m.cyl("root", mat("7A5234", 0.3), (-0.35, -0.05, 0.92), (-0.35, -0.05, 1.12), 0.1, 0.14); m.cap("root", WOOD, (-0.33, -0.05, 1.1), (-0.25, -0.02, 1.32), 0.025)
    m.sph("root", mat("8FCB5A", 0.5), (0.1, -0.05, 1.02), (0.1, 0.1, 0.17), rot=(0.3, 1.2, 0)); m.cyl("root", mat("4FB04A", 0.85), (0.4, 0.1, 0.92), (0.4, 0.1, 1.15), 0.05); m.cyl("root", mat("F4922E", 0.85), (0.5, -0.12, 0.92), (0.5, -0.12, 1.1), 0.045)
    return m

def stool():
    m = Model("stool")
    P = mat("E0382E", 0.6)
    m.box("root", P, (0, 0, 0.42), (0.46, 0.46, 0.06), bevel=0.025)
    for sx in (1, -1):
        for sy in (1, -1): m.cyl("root", P, (0.24 * sx, 0.24 * sy, 0), (0.17 * sx, 0.17 * sy, 0.42), 0.035, 0.03, seg=8)
    for a in range(4): m.box("root", P, (0.2 * math.cos(a * PI / 2), 0.2 * math.sin(a * PI / 2), 0.2), (0.38 if a % 2 else 0.03, 0.03 if a % 2 else 0.38, 0.03), bevel=0.01)
    return m

def lanterns():
    m = Model("lanterns")
    for sx in (1, -1): bamboo_pole(m, "root", (1.3 * sx, 0, 0), (1.3 * sx, 0, 2.0), 0.04, mt=WOOD, ring=mat("6E4826", 0.2), nodes=3)
    pts = [(-1.3, 0, 1.95), (-0.65, 0, 1.68), (0, 0, 1.6), (0.65, 0, 1.68), (1.3, 0, 1.95)]
    m.chain("root", INK, pts, [0.012] * 5, seg=6)
    for x, z, c in ((-0.65, 1.38, "FFD95A"), (0, 1.3, "FF8FB0"), (0.65, 1.38, "FFD95A")): lantern(m, "root", (x, 0, z), c, 2.5, 0.85)
    return m

def bell():
    m = Model("bell")
    RP = mat("C0281F", 0.5)
    for sx in (1, -1):
        m.cyl("root", RP, (0.42 * sx, 0, 0), (0.42 * sx, 0, 1.25), 0.055); m.cyl("root", GOLD, (0.42 * sx, 0, 0), (0.42 * sx, 0, 0.1), 0.085)
    m.box("root", GOLD, (0, 0, 1.28), (1.1, 0.14, 0.1), bevel=0.03)
    m.joint("bell", (0, 0, 1.22))
    B = mat("F0B428", 0.9, 0.2)
    m.cyl("bell", B, (0, 0, 0.55), (0, 0, 1.05), 0.3, 0.14, seg=20); m.sph("bell", B, (0, 0, 1.05), 0.14); m.torus("bell", B, (0, 0, 0.56), 0.3, 0.035, seg=20)
    m.cyl("bell", WOOD, (0, 0, 1.15), (0, 0, 1.24), 0.02); m.sph("bell", mat("B87A10", 0.8), (0, 0, 0.5), 0.07)
    return m

def chedi():
    m = Model("chedi")
    B1 = mat("C8643C", 0.15); B2 = mat("B2532F", 0.15); B3 = mat("D98A5A", 0.15); MOSS = mat("6FA84A", 0.2)
    for i, (w, h) in enumerate(((2.2, 0.3), (1.9, 0.28), (1.6, 0.26))):
        m.box("root", (B1, B2, B1)[i], (0, 0, sum(x[1] for x in ((2.2, 0.3), (1.9, 0.28), (1.6, 0.26))[:i]) + h / 2), (w, w, h), bevel=0.03)
    m.sph("root", B3, (0, 0, 0.84), (0.68, 0.68, 0.8), seg=24, cut=((0, 0, 0.84), (0, 0, -1)))
    m.cyl("root", B2, (0, 0, 1.55), (0, 0, 1.75), 0.3, seg=4); z = 1.75
    for i in range(7):
        r = 0.26 - i * 0.03; m.torus("root", B1 if i % 2 else B3, (0, 0, z), r, 0.05, seg=16, rseg=6); z += 0.085
    m.cyl("root", B3, (0, 0, z - 0.04), (0, 0, z + 0.95), 0.07, 0.0, seg=10)
    for x, y, zz, s in ((0.6, -1.0, 0.25, 0.2), (-0.7, -0.85, 0.5, 0.16), (0.3, -0.66, 1.0, 0.14), (-0.95, -0.9, 0.12, 0.18)): m.sph("root", MOSS, (x, y, zz), (s, 0.05, s * 0.6))
    return m

def frangipani():
    m = Model("frangipani")
    TR = mat("A79C92", 0.2)
    m.chain("root", TR, [(0, 0, 0), (0.03, 0, 0.7), (0, 0, 1.1)], [0.12, 0.09, 0.08])
    br = [((0, 0, 1.1), (0.5, 0.1, 1.7)), ((0, 0, 1.1), (-0.45, -0.1, 1.75)), ((0, 0, 1.0), (0.1, 0.35, 1.9)), ((0.5, 0.1, 1.7), (0.8, 0, 2.05)), ((-0.45, -0.1, 1.75), (-0.75, 0.1, 2.1))]
    for a, b in br: m.cap("root", TR, a, b, 0.06, 0.04)
    for (x, y, z, s) in ((0.55, 0.1, 2.0, 0.5), (-0.5, -0.05, 2.05, 0.52), (0.1, 0.3, 2.3, 0.55), (0.9, 0, 2.2, 0.36), (-0.85, 0.1, 2.25, 0.38), (0, -0.2, 2.45, 0.42)):
        m.sph("root", LEAF if s > 0.45 else LEAF_L, (x, y, z), (s, s * 0.85, s * 0.8), seg=16)
        for k in range(5):
            a = k * 1.3 + x * 3; b = 0.3 + (k % 3) * 0.35
            p = V((x + math.cos(a) * math.cos(b) * s, y - abs(math.sin(a) * math.cos(b)) * s * 0.85, z + math.sin(b) * s * 0.8))
            m.sph("root", mat("FFF7D6", 0.3, 0.3), p, 0.07, seg=8); m.sph("root", mat("FFD23F", 0.3, 0.5), p + V((0, -0.03, 0)), 0.035, seg=8)
    return m

def banner():
    m = Model("banner")
    m.cyl("root", mat("C0281F", 0.5), (0, 0, 0), (0, 0, 2.6), 0.07, seg=12); m.cyl("root", GOLD, (0, 0, 0), (0, 0, 0.12), 0.11); m.cyl("root", GOLD, (0, 0, 2.55), (0, 0, 2.68), 0.1)
    for z in (0.7, 1.3, 1.9): m.torus("root", GOLD, (0, 0, z), 0.07, 0.022, seg=12, rseg=6)
    m.chain("root", GOLD, [(0, 0, 2.68), (0.04, 0, 2.85), (0.14, 0, 2.95)], [0.035, 0.025, 0.008])
    return m

def hut():
    m = Model("hut")   # stilt house: woven walls, layered thatch, veranda rail, ladder
    WALL = mat("D9B27A", 0.15); THATCH = mat("C8963C", 0.1); THATCH2 = mat("A87A2C", 0.1); DK = mat("5A3A20", 0.2)
    for sx in (1, -1):
        for sy in (1, -1): m.cyl("root", WOOD, (0.85 * sx, 0.62 * sy, -0.6), (0.85 * sx, 0.62 * sy, 0.9), 0.07, seg=10)
        m.cap("root", WOOD, (0.85 * sx, -0.62, 0.3), (0.85 * sx, 0.62, 0.3), 0.035, seg=8)
    m.cap("root", WOOD, (-0.85, -0.62, 0.3), (0.85, -0.62, 0.3), 0.035, seg=8)
    m.box("root", WOOD, (0, -0.1, 0.9), (2.2, 1.8, 0.1), bevel=0.02)
    m.box("root", WALL, (0, 0.05, 1.45), (1.7, 1.2, 1.0), bevel=0.02)
    for x in (-0.85, 0.85): m.box("root", WOOD, (x, 0.05, 1.45), (0.07, 1.26, 1.04), bevel=0.01)
    m.box("root", DK, (0.25, -0.56, 1.33), (0.42, 0.03, 0.76), bevel=0.01); m.box("root", WOOD, (0.25, -0.575, 1.73), (0.52, 0.03, 0.06), bevel=0.01)
    m.box("root", DK, (-0.45, -0.56, 1.55), (0.32, 0.03, 0.32), bevel=0.01)
    for x in (-0.62, -0.28): m.box("root", WOOD, (x, -0.575, 1.55), (0.03, 0.03, 0.38), bevel=0.005)
    m.box("root", WOOD, (-0.45, -0.575, 1.55), (0.38, 0.03, 0.03), bevel=0.005)
    for x in (-1.0, -0.5, 0.0, 0.75, 1.0): m.cyl("root", WOOD, (x, -0.92, 0.95), (x, -0.92, 1.32), 0.025, seg=6)
    m.cap("root", WOOD, (-1.0, -0.92, 1.32), (0.0, -0.92, 1.32), 0.028, seg=8); m.cap("root", WOOD, (0.75, -0.92, 1.32), (1.0, -0.92, 1.32), 0.028, seg=8)
    for sx in (-1, 1): m.cap("root", WOOD, (0.38 + 0.14 * sx, -1.0, 0.92), (0.38 + 0.14 * sx, -1.55, -0.55), 0.028, seg=6)
    for k in range(5): m.cap("root", WOOD, (0.24, -1.07 - k * 0.1, 0.72 - k * 0.27), (0.52, -1.07 - k * 0.1, 0.72 - k * 0.27), 0.022, seg=6)
    for i, (L, hw, z0, hgt) in enumerate(((2.7, 1.25, 1.86, 0.5), (2.55, 1.0, 2.04, 0.5), (2.4, 0.74, 2.24, 0.5), (2.25, 0.46, 2.44, 0.42))):
        m.prism("root", THATCH2 if i % 2 else THATCH, (0, 0.05, z0), L, hw, hgt)
    m.cap("root", THATCH2, (-1.2, 0.05, 2.86), (1.2, 0.05, 2.86), 0.07, seg=8)
    return m

def chedi_gold():
    m = Model("chedi_gold")
    W = mat("FBF7EC", 0.3); G = mat("F2B632", 0.85, 0.15); G2 = mat("FFD45A", 0.85, 0.25); R_ = mat("C0281F", 0.4)
    hs = ((2.4, 0.3), (2.0, 0.28), (1.65, 0.26)); z = 0
    for i, (w, h) in enumerate(hs):
        m.box("root", W, (0, 0, z + h / 2), (w, w, h), bevel=0.03); m.box("root", R_, (0, 0, z + h - 0.02), (w + 0.04, w + 0.04, 0.04), bevel=0.01); z += h
    m.sph("root", G, (0, 0, z), (0.72, 0.72, 0.85), seg=28, cut=((0, 0, z), (0, 0, -1)))
    m.cyl("root", G2, (0, 0, z + 0.72), (0, 0, z + 0.92), 0.32, seg=4); zz = z + 0.92
    for i in range(8):
        m.torus("root", G if i % 2 else G2, (0, 0, zz), 0.27 - i * 0.028, 0.05, seg=18, rseg=6); zz += 0.085
    m.cyl("root", G2, (0, 0, zz - 0.04), (0, 0, zz + 1.1), 0.07, 0.0, seg=10); m.sph("root", G2, (0, 0, zz + 1.1), 0.05)
    return m

def wat():
    m = Model("wat")   # temple hall, long side along X
    W = mat("FBF6EA", 0.25); TILE = mat("D9542B", 0.4); TRIM = mat("2F9A6B", 0.45); G = mat("F2B632", 0.85, 0.2); R_ = mat("B3261E", 0.4); DARK = mat("5A2A1A", 0.3)
    m.box("root", W, (0, 0, 0.2), (6.6, 3.8, 0.4), bevel=0.04); m.box("root", mat("E6DFCF", 0.25), (0, -2.1, 0.1), (2.2, 0.8, 0.2), bevel=0.03)
    m.box("root", W, (0, 0, 1.5), (5.4, 2.6, 2.2), bevel=0.03)
    for i in range(6):
        x = -2.5 + i * 1.0
        for y in (-1.55, 1.55):
            m.cyl("root", W, (x, y, 0.4), (x, y, 2.5), 0.13, seg=12); m.cyl("root", G, (x, y, 2.35), (x, y, 2.55), 0.17, 0.2, seg=12); m.cyl("root", G, (x, y, 0.4), (x, y, 0.55), 0.18, seg=12)
    for x in (-1.5, 0.5):
        m.box("root", R_, (x + 0.5, -1.31, 1.25), (0.7, 0.05, 1.5), bevel=0.01); m.box("root", G, (x + 0.5, -1.33, 2.1), (0.86, 0.05, 0.16), bevel=0.02)
    for x in (-2.2, 2.2): m.box("root", DARK, (x, -1.31, 1.5), (0.45, 0.04, 0.8), bevel=0.01); m.box("root", G, (x, -1.33, 1.98), (0.6, 0.04, 0.1), bevel=0.02)
    # three-tier roof
    for i, (L, hw, h, z) in enumerate(((6.6, 2.2, 1.1, 2.55), (5.0, 1.75, 1.0, 3.2), (3.4, 1.3, 0.95, 3.8))):
        m.prism("root", TRIM, (0, 0, z), L + 0.18, hw + 0.1, h); m.prism("root", TILE, (0, 0, z + 0.06), L, hw, h)
        m.cap("root", G, (-L / 2, 0, z + h + 0.05), (L / 2, 0, z + h + 0.05), 0.045, seg=8)
        for sx in (1, -1):
            m.chain("root", G, [(sx * L / 2, 0, z + h), (sx * (L / 2 + 0.22), 0, z + h + 0.22), (sx * (L / 2 + 0.3), 0, z + h + 0.6)], [0.07, 0.05, 0.01])          # chofa
            for sy in (1, -1): m.chain("root", G, [(sx * L / 2, sy * hw, z + 0.04), (sx * (L / 2 + 0.16), sy * (hw + 0.14), z + 0.12), (sx * (L / 2 + 0.2), sy * (hw + 0.2), z + 0.36)], [0.055, 0.04, 0.008])
            m.prism("root", G, (sx * (L / 2 - 0.02), 0, z + 0.1), 0.06, hw * 0.8, h * 0.8)
    m.cyl("root", G, (0, 0, 4.75), (0, 0, 5.5), 0.06, 0.0, seg=8)
    return m

def spirit():
    m = Model("spirit")   # san phra phum, the little spirit house
    W = mat("FBF6EA", 0.3); G = mat("F2B632", 0.85, 0.2); R_ = mat("C0281F", 0.45); MG = mat("FF9A1E", 0.4, 0.2)
    m.cyl("root", W, (0, 0, 0), (0, 0, 0.12), 0.26, 0.2, seg=16); m.cyl("root", W, (0, 0, 0.1), (0, 0, 1.0), 0.09, seg=12); m.cyl("root", W, (0, 0, 0.95), (0, 0, 1.08), 0.1, 0.3, seg=16)
    m.box("root", W, (0, 0, 1.12), (0.75, 0.6, 0.08), bevel=0.02); m.box("root", R_, (0, 0, 1.36), (0.46, 0.36, 0.4), bevel=0.02)
    m.box("root", mat("3A1A12", 0.3), (0, -0.185, 1.32), (0.16, 0.02, 0.26), bevel=0.01)
    for sx in (1, -1):
        for sy in (1, -1): m.cyl("root", G, (0.27 * sx, 0.21 * sy, 1.16), (0.27 * sx, 0.21 * sy, 1.56), 0.022, seg=8)
    for L, hw, h, z in ((0.8, 0.36, 0.26, 1.56), (0.56, 0.26, 0.24, 1.74)):
        m.prism("root", G, (0, 0, z), L + 0.04, hw + 0.03, h); m.prism("root", R_, (0, 0, z + 0.025), L, hw, h)
        for sx in (1, -1): m.chain("root", G, [(sx * L / 2, 0, z + h), (sx * (L / 2 + 0.06), 0, z + h + 0.07), (sx * (L / 2 + 0.08), 0, z + h + 0.18)], [0.022, 0.016, 0.004], seg=6)
    m.cyl("root", G, (0, 0, 1.98), (0, 0, 2.3), 0.03, 0.0, seg=8)
    for i in range(11):
        a = -0.9 + i * 0.18; m.sph("root", MG if i % 2 else mat("FFE066", 0.4, 0.2), (math.sin(a) * 0.34, -0.31, 1.2 - math.cos(a) * 0.16 + 0.1), 0.035, seg=8)
    m.sph("root", mat("F06BA8", 0.4), (0.25, -0.2, 1.2), 0.05, seg=8); m.cyl("root", mat("FFE9A0", 0.3), (-0.25, -0.2, 1.16), (-0.25, -0.2, 1.3), 0.012, seg=6)
    return m

def tuktuk():
    m = Model("tuktuk")
    B = mat("2F7FE0", 0.7); Y = mat("FFD12E", 0.7); CH = mat("D5DAE2", 0.9); SEAT = mat("C8322C", 0.5); TY = mat("1E1E24", 0.4)
    m.box("root", B, (0.25, 0, 0.5), (1.5, 1.0, 0.5), bevel=0.08); m.box("root", Y, (0.25, 0, 0.3), (1.54, 1.04, 0.1), bevel=0.03)
    m.sph("root", B, (-0.75, 0, 0.56), (0.42, 0.4, 0.34), seg=20); m.sph("root", mat("FFF6C8", 0.6, 3), (-1.13, 0, 0.6), (0.06, 0.1, 0.1))
    m.box("root", SEAT, (0.55, 0, 0.82), (0.6, 0.86, 0.16), bevel=0.05); m.box("root", SEAT, (0.86, 0, 1.05), (0.12, 0.86, 0.4), bevel=0.05); m.box("root", SEAT, (-0.25, 0, 0.82), (0.36, 0.5, 0.14), bevel=0.05)
    for x, y in ((-0.5, 0.46), (-0.5, -0.46), (0.95, 0.48), (0.95, -0.48)): m.cyl("root", CH, (x, y, 0.7), (x, y, 1.72), 0.025, seg=8)
    m.box("root", Y, (0.22, 0, 1.76), (1.75, 1.14, 0.09), bevel=0.04); m.box("root", B, (0.22, 0, 1.69), (1.79, 1.18, 0.07), bevel=0.03)
    for k in range(7): m.sph("root", mat(("E0382E", "FFD12E", "3FA65A")[k % 3], 0.4), (-0.6 + k * 0.27, -0.6, 1.62), (0.05, 0.02, 0.06), seg=8)
    m.cap("root", CH, (-0.72, -0.28, 1.0), (-0.72, 0.28, 1.0), 0.022, seg=8); m.cyl("root", CH, (-0.78, 0, 0.75), (-0.72, 0, 1.0), 0.025, seg=8)
    m.box("root", mat("BFE4FF", 0.9), (-0.55, 0, 1.3), (0.03, 0.9, 0.6), rot=(0, -0.25, 0), bevel=0.01)
    for x, y in ((-0.85, 0), (0.6, 0.56), (0.6, -0.56)):
        m.torus("root", TY, (x, y, 0.24), 0.17, 0.075, rot=(PI / 2, 0, 0), seg=20); m.cyl("root", CH, (x, y - 0.05, 0.24), (x, y + 0.05, 0.24), 0.1, seg=12)
    return m

def boat():
    m = Model("boat")   # long-tail boat, bow towards -X, waterline at z=0
    WD = mat("9A5E32", 0.35); WD2 = mat("C98A52", 0.3); ENG = mat("6E7480", 0.7)
    m.sph("root", WD, (0, 0, 0.12), (2.5, 0.52, 0.42), seg=28, cut=((0, 0, 0.3), (0, 0, 1)))
    m.sph("root", WD2, (0, 0, 0.3), (2.35, 0.44, 0.06), seg=24)
    m.chain("root", WD, [(-2.1, 0, 0.26), (-2.6, 0, 0.5), (-2.95, 0, 0.95), (-3.05, 0, 1.45)], [0.16, 0.13, 0.09, 0.05], seg=10)
    for i, c in enumerate(("E0382E", "FFD12E", "2F7FE0", "F06BA8", "3FA65A")):
        m.torus("root", mat(c, 0.4), (-2.72 - i * 0.07, 0, 0.62 + i * 0.16), 0.115 - i * 0.012, 0.03, rot=(0, 0.9, 0), seg=12, rseg=6)
        m.cap("root", mat(c, 0.4), (-2.72 - i * 0.07, 0.1, 0.6 + i * 0.16), (-2.6 - i * 0.05, 0.16, 0.3 + i * 0.14), 0.015, seg=6)
    for x in (-1.2, -0.3, 0.6): m.box("root", WD2, (x, 0, 0.34), (0.2, 0.86, 0.05), bevel=0.015)
    for x in (-0.9, 0.9):
        for sy in (1, -1): m.cyl("root", WD2, (x, 0.42 * sy, 0.3), (x, 0.42 * sy, 1.15), 0.02, seg=6)
    m.box("root", mat("2F7FE0", 0.3), (0, 0, 1.18), (2.1, 1.0, 0.04), bevel=0.015); m.box("root", mat("FFD12E", 0.3), (0, 0, 1.21), (1.7, 0.7, 0.03), bevel=0.01)
    m.box("root", ENG, (1.9, 0, 0.62), (0.5, 0.36, 0.34), bevel=0.05); m.cyl("root", ENG, (1.9, 0, 0.45), (1.9, 0, 0.3), 0.06, seg=8)
    m.cap("root", ENG, (2.1, 0, 0.62), (4.0, 0, -0.1), 0.03, seg=8); m.cap("root", WD2, (1.7, 0, 0.7), (1.0, 0.1, 0.95), 0.025, seg=8)
    return m

def buffalo():
    m = Model("buffalo")
    B = mat("5B5661", 0.3); B2 = mat("77717C", 0.3); HORN = mat("E8DFC6", 0.5)
    m.joint("head", (0, -0.75, 0.95))
    m.sph("root", B, (0, 0, 0.85), (0.5, 0.92, 0.52), seg=24); m.sph("root", B, (0, -0.55, 1.0), (0.4, 0.45, 0.42))
    for sx in (1, -1):
        for y in (-0.55, 0.55): m.cap("root", B, (0.27 * sx, y, 0.6), (0.28 * sx, y, 0.1), 0.12, 0.1); m.sph("root", INK, (0.28 * sx, y - 0.02, 0.06), (0.11, 0.13, 0.07))
        m.chain("head", HORN, [(0.2 * sx, -0.95, 1.22), (0.5 * sx, -0.85, 1.3), (0.66 * sx, -0.62, 1.42), (0.6 * sx, -0.38, 1.56)], [0.075, 0.06, 0.04, 0.012], seg=10)
        m.sph("head", B, (0.3 * sx, -0.9, 1.1), (0.13, 0.05, 0.08), rot=(0, 0.4 * sx, 0)); eye(m, "head", 0.19 * sx, -1.29, 1.1, 0.05)
        m.sph("head", INK, (0.07 * sx, -1.58, 0.93), (0.025, 0.02, 0.02))
    m.sph("head", B, (0, -1.08, 1.03), (0.3, 0.34, 0.28), seg=20); m.sph("head", B2, (0, -1.38, 0.95), (0.2, 0.22, 0.17))
    m.chain("root", B, [(0, 0.9, 0.95), (0, 1.05, 0.7), (0, 1.08, 0.42)], [0.04, 0.03, 0.02], seg=8); m.sph("root", INK, (0, 1.08, 0.36), (0.05, 0.05, 0.09))
    return m

def karst():
    m = Model("karst")   # limestone cliff tower (scaled up in game): craggy, streaked, with a jungle cap and hanging vines
    S1 = mat("B9B3A4", 0.1); S2 = mat("A49D8E", 0.1); S3 = mat("CFC9BA", 0.1); GV = mat("5FAE56", 0.1); GV2 = mat("4A9A52", 0.1)
    m.sph("root", S1, (0, 0, 2.5), (1.25, 1.05, 2.9), seg=48, rough=(0.34, 1.0, 0.3))
    m.sph("root", S2, (0.85, 0.15, 1.2), (0.85, 0.75, 1.55), seg=32, rough=(0.3, 1.2, 0.35))
    m.sph("root", S3, (-0.8, -0.15, 0.95), (0.75, 0.8, 1.25), seg=32, rough=(0.28, 1.3, 0.35))
    m.sph("root", S2, (0.15, -0.5, 3.9), (0.75, 0.65, 1.2), seg=28, rough=(0.24, 1.4, 0.4))
    for x, y, z, sc in ((0.05, 0, 5.25, 1.05), (0.5, -0.2, 4.9, 0.6), (-0.55, 0.1, 4.8, 0.62), (1.2, 0.1, 2.75, 0.5), (-1.2, -0.2, 2.2, 0.5), (0.3, -0.75, 5.0, 0.45), (-0.3, -0.95, 3.0, 0.34), (0.95, -0.55, 1.6, 0.36)):
        m.sph("root", GV if sc > 0.5 else GV2, (x, y, z), (sc, sc * 0.9, sc * 0.5), seg=16, rough=(0.1, 3.0))
    for i in range(9):          # vines trailing down from the cap
        a = i * 0.7 - 2.6; r = 1.0 + 0.1 * (i % 3); x, y = math.cos(a) * r, math.sin(a) * r * 0.85 - 0.1; ln = 0.7 + 0.5 * ((i * 7) % 5) / 4
        m.chain("root", GV2, [(x * 0.9, y * 0.9, 5.0), (x, y, 4.6), (x * 1.02, y * 1.02, 4.6 - ln)], [0.035, 0.03, 0.012], seg=6)
    return m

def terrace():
    m = Model("terrace")   # rice-terrace hill, radius ~5 (scaled in game): earth walls, green paddies, bund rims, rows of young rice
    G1 = mat("8FD65A", 0.35); G2 = mat("76C54D", 0.35); WALL = mat("7DBB4E", 0.1); RIM = mat("C9B26A", 0.1)
    for i in range(7):
        r = 5.0 - i * 0.62; z = i * 0.5
        m.cyl("root", WALL, (0, 0, z - 0.6), (0, 0, z + 0.46), r, r * 0.94, seg=44)
        m.cyl("root", G1 if i % 2 else G2, (0, 0, z + 0.44), (0, 0, z + 0.5), r * 0.925, r * 0.92, seg=44)
        m.torus("root", RIM, (0, 0, z + 0.5), r * 0.93, 0.05, seg=44, rseg=6)
        for k in range(int(r * 5)):
            a = k * 2.399 + i; rr = r * 0.93 - 0.12 - (k % 3) * 0.14
            if rr > (r - 0.62) * 0.95: m.cyl("root", LEAF_L, (math.cos(a) * rr, math.sin(a) * rr, z + 0.5), (math.cos(a) * rr, math.sin(a) * rr, z + 0.62), 0.03, 0.0, seg=4)
    m.sph("root", G2, (0, 0, 3.4), (0.9, 0.9, 0.5), seg=18)
    return m

def lotuspad():
    m = Model("lotuspad")
    P1 = mat("3E9B4A", 0.5); P2 = mat("58B257", 0.5)
    for x, y, r in ((0, 0, 0.42), (0.7, 0.3, 0.32), (-0.55, 0.45, 0.28), (0.25, -0.6, 0.3), (-0.6, -0.4, 0.22)):
        m.sph("root", P1 if r > 0.3 else P2, (x, y, 0.015), (r, r, 0.02), seg=16)
    for i in range(6):
        a = i * PI / 3; m.ell("root", mat("F8A3C8", 0.4), (0.7, 0.3, 0.04), (0.7 + math.cos(a) * 0.1, 0.3 + math.sin(a) * 0.1, 0.3), 0.06, 0.03, seg=8)
    m.sph("root", mat("FFD23F", 0.4, 0.3), (0.7, 0.3, 0.12), 0.05, seg=8)
    return m

def flags():
    m = Model("flags")
    for sx in (1, -1): bamboo_pole(m, "root", (2.0 * sx, 0, 0), (2.0 * sx, 0, 2.6), 0.045, nodes=4)
    cols = ("E0382E", "FFD12E", "2F7FE0", "F06BA8", "3FA65A", "FFFFFF", "FF8A1E", "8A5BD6", "E0382E")
    n = len(cols); pts = []
    for i in range(n + 1):
        t = i / n; x = -2.0 + 4.0 * t; pts.append(V((x, 0, 2.55 - 0.45 * math.sin(t * PI))))
    m.chain("root", INK, pts, [0.012] * (n + 1), seg=6)
    for i, c in enumerate(cols):
        a, b = pts[i] + V((0.04, 0, 0)), pts[i + 1] - V((0.04, 0, 0)); tip = (a + b) / 2 + V((0, 0, -0.42))
        def tri(bm, a=a, b=b, tip=tip):
            f = [bm.verts.new(a + V((0, -0.008, 0))), bm.verts.new(b + V((0, -0.008, 0))), bm.verts.new(tip + V((0, -0.008, 0)))]
            g = [bm.verts.new(a + V((0, 0.008, 0))), bm.verts.new(b + V((0, 0.008, 0))), bm.verts.new(tip + V((0, 0.008, 0)))]
            bm.faces.new((f[0], f[2], f[1])); bm.faces.new((g[0], g[1], g[2]))
        m._add("root", mat(c, 0.3), tri)
    return m

def butterfly(name, c1, c2):
    m = Model(name)
    m.cap("root", INK, (0, -0.06, 0), (0, 0.07, 0), 0.016, seg=6); m.sph("root", INK, (0, -0.085, 0.005), 0.022, seg=8)
    for sd, sx in (("L", 1), ("R", -1)):
        m.joint("wing" + sd, (0.012 * sx, 0, 0.005))
        m.ell("wing" + sd, mat(c1, 0.4, 0.3), (0.012 * sx, -0.02, 0.005), (0.17 * sx, -0.1, 0.005), 0.075, 0.006, seg=10)
        m.ell("wing" + sd, mat(c2, 0.4, 0.3), (0.012 * sx, 0.02, 0.005), (0.13 * sx, 0.1, 0.005), 0.055, 0.006, seg=10)
    return m

def heart():
    m = Model("heart")
    H = mat("F0283C", 0.85, 0.2)
    for sx in (1, -1):
        m.sph("root", H, (0.2 * sx, 0, 0.17), (0.27, 0.19, 0.27), seg=24)
        m.cap("root", H, (0.2 * sx, 0, 0.14), (0.0, 0, -0.36), 0.265, 0.035, seg=24)
    m.sph("root", H, (0, 0, 0.0), (0.26, 0.19, 0.3), seg=20)
    m.sph("root", WHITE, (-0.26, -0.16, 0.3), (0.07, 0.03, 0.05), rot=(0, 0.5, 0), seg=10)
    return m

def fence():
    m = Model("fence")
    for i in range(6): bamboo_pole(m, "root", (-1.0 + i * 0.4, 0, 0), (-1.0 + i * 0.4, 0, 0.62 + 0.06 * (i % 2)), 0.035, nodes=2)
    for z in (0.2, 0.48): m.cap("root", BAMBOO_D, (-1.15, -0.03, z), (1.15, -0.03, z), 0.028, seg=8)
    return m

def cloud():
    m = Model("cloud")
    C = mat("FFFFFF", 0.0, 0.6)
    for x, z, s in ((0, 0.1, 1.0), (1.0, 0.0, 0.75), (-1.05, -0.02, 0.8), (0.5, 0.5, 0.7), (-0.45, 0.45, 0.62), (1.8, -0.1, 0.5), (-1.85, -0.12, 0.48)):
        m.sph("root", C, (x, 0, z), (s, s * 0.7, s * 0.78), seg=16)
    return m

def blob():
    m = Model("blob"); m.sph("root", WHITE, (0, 0, 0), 1, seg=40); return m

def rock():
    m = Model("rock")
    for x, y, z, sc in ((0, 0, 0.2, 0.42), (0.35, 0.1, 0.12, 0.26), (-0.3, -0.05, 0.1, 0.22)):
        m.sph("root", mat("9A9488", 0.15) if sc > 0.3 else mat("8E8A80", 0.15), (x, y, z), (sc, sc * 0.82, sc * 0.72), rot=(0.3, 0.2, x), seg=16, rough=(0.09, 3.2))
    return m

BUILDERS = [nam, monkey, crab, cobra, mosquito, durian, ghost, coin, lotus, somtam, sangsom, chili, mango, fireball, venom, flame,
            lambda: checkpoint(False), lambda: checkpoint(True), gong, drum, brazier, spike, raft, crumble, oneway,
            banana, palm, bamboo, grass, rice, flower, cart, stool, lanterns, bell, chedi, frangipani, banner, hut, cloud, blob, rock,
            chedi_gold, wat, spirit, tuktuk, boat, buffalo, karst, terrace, lotuspad, flags, heart, fence,
            lambda: butterfly("butterfly_a", "FF9A1E", "FFD12E"), lambda: butterfly("butterfly_b", "5BB8FF", "C9E9FF"), lambda: butterfly("butterfly_c", "F06BA8", "FFFFFF")]

# ----------------------------------------------------------------------------- run
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for b in BUILDERS:
        m = b(); m.build(); m.export()
        print("exported", m.name, sum(len(o.data.polygons) for o in m.objs), "polys")
    if argv:
        # contact sheet (workbench render) to eyeball the models
        sc = bpy.context.scene
        x = 0; z = 0; rowh = 0; n = 0
        for m in Model.all:
            if m.name in ("blob",): continue
            w = max((max((o.matrix_world @ V(c)).x for c in o.bound_box) for o in m.objs if o.name.startswith("M_")), default=1) * 2 + 0.5
            w = max(w, 1.2)
            if x + w > 22: x = 0; z -= rowh + 0.6; rowh = 0
            for o in m.objs:
                if o.name.startswith("M_"): o.location = (x + w / 2, 0, z)
                else: o.hide_render = True
            h = max((max((o.matrix_world @ V(c)).z for c in o.bound_box) for o in m.objs if o.name.startswith("M_")), default=1)
            rowh = max(rowh, 4.2 if h > 3 else 2.8); x += w
        bpy.context.view_layer.update()
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = "ORTHO"; total_h = -z + 4.5; cam.data.ortho_scale = 24
        d = V((0.35, -1, 0.3)).normalized()
        centre = V((11, 0, z / 2 + 1.2))
        cam.location = centre + d * 60; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
        sc.render.resolution_x = 2400; sc.render.resolution_y = int(2400 * max(0.4, (total_h + 1) / 24)); sc.render.film_transparent = False
        sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.35, 0.5, 0.65)
        sc.render.filepath = argv[0]; bpy.ops.render.render(write_still=True)

if os.environ.get("NAM_NO_MAIN") != "1":
    main()
