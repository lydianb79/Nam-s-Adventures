using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;

/// A spawned 3D model with its joint hierarchy. Models come from Tools/blender_models.py:
/// rigid part meshes "M_<joint>" plus marker meshes "J_<joint>@<parent>" at every pivot.
/// The loader rebuilds the bone hierarchy in a canonical frame: +X = the model's front, +Y = up.
public class Rig
{
    public Transform root;      // world placement + yaw
    public Transform body;      // child used for squash / tilt
    readonly Dictionary<string, Transform> joints = new Dictionary<string, Transform>();
    Renderer[] rends; Material[][] own; Color[][] ownBase; Color[][] ownEmis;

    static readonly Dictionary<string, GameObject> templates = new Dictionary<string, GameObject>();
    static readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();
    static Transform templateRoot;
    static readonly Regex detRe = new Regex(@"_d([a-z]+)");
    // surface detail presets: tiles per unit, colour strength, relief
    static readonly Dictionary<string, Vector3> details = new Dictionary<string, Vector3>
    {
        { "wood", new Vector3(2.4f, 0.34f, 0.6f) }, { "bark", new Vector3(1.6f, 0.5f, 1.0f) }, { "leaf", new Vector3(2.6f, 0.26f, 0.35f) },
        { "stone", new Vector3(0.9f, 0.5f, 0.9f) }, { "brick", new Vector3(1.5f, 0.55f, 0.9f) }, { "tile", new Vector3(1.6f, 0.55f, 1.0f) },
        { "thatch", new Vector3(1.4f, 0.55f, 0.9f) }, { "weave", new Vector3(3.0f, 0.4f, 0.7f) }, { "plaster", new Vector3(1.6f, 0.22f, 0.4f) },
        { "metal", new Vector3(3.2f, 0.2f, 0.5f) },
    };
    public static void Detail(Material m, string kind, float scaleMul = 1f)
    {
        if (!details.TryGetValue(kind, out var d)) return;
        m.SetTexture("_Detail", Resources.Load<Texture2D>("Art/det_" + kind));
        m.SetTexture("_DetailN", Resources.Load<Texture2D>("Art/det_" + kind + "_n"));
        m.SetFloat("_DetailScale", d.x * scaleMul); m.SetFloat("_DetailAmt", d.y); m.SetFloat("_DetailBump", d.z);
    }
    static readonly Regex suffixRe = new Regex(@"[\._ ]\d{3}$");
    static readonly Regex matRe = new Regex(@"^(?:T([A-Za-z0-9]+)_)?([0-9A-Fa-f]{6})_s(\d+)_e(\d+)");

    public Transform J(string name) { joints.TryGetValue(name, out var t); return t; }

    static Shader toon;
    public static Shader Toon { get { if (toon == null) toon = Resources.Load<Shader>("Shaders/NamToon"); return toon; } }
    static readonly HashSet<string> windy = new HashSet<string> { "palm", "banana", "bamboo", "grass", "rice", "flower", "frangipani", "flags", "lotuspad" };

    /// Material from a name like "RRGGBB_s35_e0" (optionally "T<texture>_" in front, "|w" behind for wind sway).
    public static Material Mat(string name)
    {
        if (mats.TryGetValue(name, out var m)) return m;
        m = new Material(Toon) { name = name };
        var mt = matRe.Match(name);
        if (!mt.Success) { Debug.LogWarning("Odd material name: " + name); mats[name] = m; return m; }
        ColorUtility.TryParseHtmlString("#" + mt.Groups[2].Value, out var col);
        float smooth = int.Parse(mt.Groups[3].Value) / 100f, emis = int.Parse(mt.Groups[4].Value) / 10f;
        m.SetColor("_BaseColor", col); m.SetFloat("_Smoothness", smooth);
        m.SetColor("_EmissionColor", col.linear * emis);
        m.SetFloat("_Rim", emis > 0 ? 0.15f : 0.55f);
        if (name.EndsWith("|w")) m.SetFloat("_Wind", 1f);
        var dm = detRe.Match(name);
        if (dm.Success) Detail(m, dm.Groups[1].Value);
        if (mt.Groups[1].Success)
        {
            m.SetTexture("_BaseMap", Resources.Load<Texture2D>("Art/tex_" + mt.Groups[1].Value));
            m.SetTextureScale("_BaseMap", new Vector2(2f, 1.5f));
        }
        mats[name] = m;
        return m;
    }

    static GameObject Template(string model)
    {
        if (templates.TryGetValue(model, out var t) && t != null) return t;
        if (templateRoot == null) { templateRoot = new GameObject("RigTemplates").transform; templateRoot.gameObject.SetActive(false); }
        var prefab = Resources.Load<GameObject>("Models/" + model);
        if (prefab == null) { Debug.LogError("Missing model: " + model); prefab = GameObject.CreatePrimitive(PrimitiveType.Cube); }
        var inst = Object.Instantiate(prefab);
        inst.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
        var rs = inst.GetComponentsInChildren<MeshRenderer>();
        Vector3 f = Vector3.forward, u = Vector3.up;
        foreach (var r in rs) r.name = suffixRe.Replace(r.name, "");        // Blender de-duplicates names as "x.001"
        foreach (var r in rs) { if (r.name == "F_front") f = r.bounds.center; else if (r.name == "U_up") u = r.bounds.center; }
        inst.transform.rotation = Quaternion.Euler(0, 90, 0) * Quaternion.Inverse(Quaternion.LookRotation(f.normalized, u.normalized));

        var root = new GameObject(model);
        var body = new GameObject("body").transform; body.SetParent(root.transform, false);
        var js = new Dictionary<string, Transform>(); var parents = new Dictionary<string, string>();
        js["root"] = body;
        foreach (var r in rs)
        {
            if (!r.name.StartsWith("J_")) continue;
            var parts = r.name.Substring(2).Split('@');
            var j = new GameObject("j_" + parts[0]).transform; j.position = r.bounds.center;
            js[parts[0]] = j; parents[parts[0]] = parts.Length > 1 ? parts[1] : "root";
        }
        foreach (var kv in parents) js[kv.Key].SetParent(js.TryGetValue(kv.Value, out var p) ? p : body, true);
        foreach (var r in rs)
        {
            if (!r.name.StartsWith("M_")) continue;
            string jn = r.name.Substring(2);
            r.transform.SetParent(js.TryGetValue(jn, out var p) ? p : body, true);
            var sm = r.sharedMaterials;
            for (int i = 0; i < sm.Length; i++) sm[i] = Mat((sm[i] != null ? sm[i].name : "FFFFFF_s30_e0") + (windy.Contains(model) ? "|w" : ""));
            r.sharedMaterials = sm;
        }
        Object.Destroy(inst);
        root.transform.SetParent(templateRoot, false);
        templates[model] = root;
        return root;
    }

    public static Rig Spawn(string model, Transform parent, Vector3 pos, float yaw = 90f, float scale = 1f, bool shadows = true)
    {
        var go = Object.Instantiate(Template(model), parent);
        go.name = model;
        var rig = new Rig { root = go.transform };
        rig.root.position = pos; rig.root.rotation = Quaternion.Euler(0, yaw, 0); rig.root.localScale = Vector3.one * scale;
        rig.body = rig.root.Find("body");
        foreach (var t in go.GetComponentsInChildren<Transform>()) if (t.name.StartsWith("j_")) rig.joints[t.name.Substring(2)] = t;
        rig.rends = go.GetComponentsInChildren<Renderer>();
        if (!shadows) foreach (var r in rig.rends) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        return rig;
    }

    public void Rot(string joint, float x, float y, float z, float blend = 1f)
    {
        if (!joints.TryGetValue(joint, out var t)) return;
        var q = Quaternion.Euler(x, y, z);
        t.localRotation = blend >= 1f ? q : Quaternion.Slerp(t.localRotation, q, blend);
    }

    public void Visible(bool v) { foreach (var r in rends) if (r != null) r.enabled = v; }

    /// Gives this rig private material copies so it can be tinted / made to glow.
    public void OwnMaterials()
    {
        own = new Material[rends.Length][]; ownBase = new Color[rends.Length][]; ownEmis = new Color[rends.Length][];
        var map = new Dictionary<Material, Material>();
        for (int i = 0; i < rends.Length; i++)
        {
            var sm = rends[i].sharedMaterials; own[i] = new Material[sm.Length]; ownBase[i] = new Color[sm.Length]; ownEmis[i] = new Color[sm.Length];
            for (int k = 0; k < sm.Length; k++)
            {
                if (!map.TryGetValue(sm[k], out var c))
                {
                    c = new Material(sm[k]);
                    map[sm[k]] = c;
                }
                own[i][k] = c; ownBase[i][k] = c.GetColor("_BaseColor"); ownEmis[i][k] = c.GetColor("_EmissionColor");
            }
            rends[i].sharedMaterials = own[i];
        }
    }

    public void Tint(Color mul, Color emisAdd)
    {
        if (own == null) OwnMaterials();
        for (int i = 0; i < own.Length; i++)
            for (int k = 0; k < own[i].Length; k++)
            {
                own[i][k].SetColor("_BaseColor", ownBase[i][k] * mul);
                own[i][k].SetColor("_EmissionColor", ownEmis[i][k] + emisAdd);
            }
    }

    public void Destroy() { if (root != null) Object.Destroy(root.gameObject); }
}
