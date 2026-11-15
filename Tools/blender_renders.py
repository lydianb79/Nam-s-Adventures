# Renders the 3D title logo and a posed Nam (for the app icon) with EEVEE.
#   NAM_NO_MAIN=1 /Applications/Blender.app/Contents/MacOS/Blender -b -P Tools/blender_renders.py -- <outdir>
import bpy, os, sys, math
from mathutils import Vector, Matrix, Euler
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["NAM_NO_MAIN"] = "1"
ns = {"__file__": os.path.join(HERE, "blender_models.py"), "__name__": "models"}
exec(compile(open(ns["__file__"]).read(), ns["__file__"], "exec"), ns)
out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene

def node_mat(name, col, rough=0.4, emis=0.0, ramp=None, image=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough
    if emis > 0:
        b.inputs["Emission Color"].default_value = (*col, 1); b.inputs["Emission Strength"].default_value = emis
    if ramp:
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); cr = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs[ramp[2]], cr.inputs[0])
        cr.color_ramp.elements[0].color = (*ramp[0], 1); cr.color_ramp.elements[1].color = (*ramp[1], 1)
        nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(image)
        mp = nt.nodes.new("ShaderNodeMapping"); tc = nt.nodes.new("ShaderNodeTexCoord"); mp.inputs["Scale"].default_value = (2, 1.5, 1)
        nt.links.new(tc.outputs["UV"], mp.inputs[0]); nt.links.new(mp.outputs[0], tex.inputs[0]); nt.links.new(tex.outputs[0], b.inputs["Base Color"])
    return m

def setup(w, h, key=3.5, world=0.9):
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    wd = bpy.data.worlds.new("w"); sc.world = wd; wd.use_nodes = True
    wd.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.8, 1.0, 1); wd.node_tree.nodes["Background"].inputs[1].default_value = world
    for name, rot, e in (("key", (0.9, 0.1, -0.6), key), ("fill", (1.1, 0, 2.2), key * 0.3)):
        l = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN")); l.data.energy = e; l.rotation_euler = rot; l.data.angle = 0.3; sc.collection.objects.link(l)

def camera(loc, target, lens=70, ortho=None):
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = loc; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = lens
    if ortho: cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    return cam

def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)

# ----------------------------------------------------------------------------- logo
def logo():
    clear(); setup(2000, 1000, 1.6, 0.35)
    font = bpy.data.fonts.load("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf")
    face = node_mat("face", (1, 0.8, 0.2), 0.3, 0.0, ramp=((1.0, 0.33, 0.02), (1.0, 0.78, 0.12), 1))
    red = node_mat("red", (0.55, 0.01, 0.01), 0.4); dark = node_mat("dark", (0.1, 0.02, 0.12), 0.6)
    def line(txt, z, size, rotz):
        for i, (mat_, off, ext, y) in enumerate(((face, 0.0, 0.07, -0.10), (red, 0.036, 0.16, 0.0), (dark, 0.07, 0.1, 0.22))):
            cu = bpy.data.curves.new("t", "FONT"); cu.body = txt; cu.font = font; cu.size = size; cu.align_x = "CENTER"
            cu.extrude = ext; cu.bevel_depth = 0.022 if i == 0 else 0.012; cu.bevel_resolution = 3; cu.offset = off; cu.space_character = 0.96
            ob = bpy.data.objects.new("t", cu); sc.collection.objects.link(ob); ob.data.materials.append(mat_)
            ob.rotation_euler = (math.pi / 2, 0, 0); ob.location = (0, y, z)
            ob.rotation_euler.rotate_axis("Z", rotz)
    line("Nam's", 0.62, 1.25, 0.04); line("Adventures", -0.5, 1.12, -0.03)
    camera((0.8, -17, -1.6), (0, 0, 0.3), lens=85)
    sc.render.filepath = os.path.join(out, "logo3d.png"); bpy.ops.render.render(write_still=True)

# ----------------------------------------------------------------------------- posed Nam
def nam_pose():
    clear(); setup(1400, 1400)
    m = ns["nam"](); m.build()
    for o in m.objs:
        if not o.name.startswith("M_") or o.name in ("M_lids", "M_mouthO"): o.hide_render = True
        for i, mt in enumerate(o.data.materials):
            nm = mt.name
            if nm.startswith("Tpants"): o.data.materials[i] = bpy.data.materials.get("pantsN") or node_mat("pantsN", (1, 1, 1), 0.8, image=os.path.join(HERE, "..", "Assets", "Resources", "Art", "tex_pants.png"))
            else:
                key = "N_" + nm
                o.data.materials[i] = bpy.data.materials.get(key) or node_mat(key, tuple(mt.diffuse_color[:3]), mt.roughness)
    joints = {j: [Vector(p), par] for j, (p, par) in m.joints.items()}
    objs = {o.name[2:]: o for o in m.objs if o.name.startswith("M_")}
    def descendants(j):
        r = [j]
        for k, (p, par) in joints.items():
            if par == j: r += descendants(k)
        return r
    def rot(j, rx=0, ry=0, rz=0):
        piv = joints[j][0].copy()
        M = Matrix.Translation(piv) @ Euler((math.radians(rx), math.radians(ry), math.radians(rz))).to_matrix().to_4x4() @ Matrix.Translation(-piv)
        for d in descendants(j):
            if d in objs: objs[d].matrix_world = M @ objs[d].matrix_world
            joints[d][0] = M @ joints[d][0]
    # cheer: left fist high, right hand out, a little hop
    rot("torso", rx=4, rz=-6, ry=-5); rot("head", rx=-6, rz=8, ry=6)
    rot("armL", rx=-150, ry=18); rot("foreL", rx=-25)
    rot("armR", rx=-35, ry=-30); rot("foreR", rx=-70)
    rot("legL", rx=-22); rot("shinL", rx=35); rot("legR", rx=18); rot("shinR", rx=25)
    rot("pony", rx=-10, ry=6)
    camera((1.9, -4.6, 1.35), (0.03, 0, 1.0), lens=80)
    sc.render.filepath = os.path.join(out, "nam_icon.png"); bpy.ops.render.render(write_still=True)

# ----------------------------------------------------------------------------- HUD icons from the 3D models
def nodeify(m):
    for o in m.objs:
        if not o.name.startswith("M_"): o.hide_render = True; continue
        for i, mt in enumerate(o.data.materials):
            nm = mt.name; key = "N_" + nm
            if key not in bpy.data.materials:
                em = 0.0
                try: em = int(nm.split("_e")[-1]) / 10
                except Exception: pass
                node_mat(key, tuple(mt.diffuse_color[:3]), mt.roughness, min(em, 1.0) * 0.6)
            o.data.materials[i] = bpy.data.materials[key]

def ui_icons():
    art = os.path.join(HERE, "..", "Assets", "Resources", "Art")
    for name, builder, loc, target, ortho in (
            ("ui_heart", "heart", (0.5, -6, 0.6), (0, 0, -0.05), 1.25),
            ("ui_coin", "coin", (0.9, -6, 0.5), (0, 0, 0), 0.74),
            ("ui_lotus", "lotus", (0, -5, 4.2), (0, 0, 0.12), 1.25),
            ("ui_somtam", "somtam", (0, -5, 4.6), (0, 0, 0.15), 1.3),
            ("ui_chili", "chili", (0, -6, 0.6), (0.02, 0, 0.42), 1.0),
            ("ui_sangsom", "sangsom", (1.5, -6, 1.2), (0, 0, 0.44), 1.05)):
        clear(); setup(256, 256, 2.6, 0.8)
        m = ns[builder](); m.build(); nodeify(m)
        if name == "ui_sangsom":
            for o in m.objs: o.rotation_euler = (0, 0.25, 0)
        camera(loc, target, ortho=ortho)
        sc.render.filepath = os.path.join(art, name + ".png"); bpy.ops.render.render(write_still=True)

logo(); nam_pose(); ui_icons()
