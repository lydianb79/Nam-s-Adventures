using System.Collections.Generic;
using UnityEngine;

/// Tile grid parsed from Resources/Levels/*.txt plus the swept-AABB tile collision used by everything that moves.
public static class Level
{
    public static int W, H;
    public static char[,] g;
    public static readonly List<string[]> objects = new List<string[]>();
    public const float WaterLine = 1.55f;

    public static void Load(string name)
    {
        var txt = Resources.Load<TextAsset>("Levels/" + name).text.Replace("\r", "");
        var parts = txt.Split(new[] { "---\n" }, System.StringSplitOptions.None);
        var rows = new List<string>(parts[0].Split('\n'));
        while (rows.Count > 0 && rows[rows.Count - 1].Length == 0) rows.RemoveAt(rows.Count - 1);
        H = rows.Count; W = 0;
        foreach (var r in rows) W = Mathf.Max(W, r.Length);
        g = new char[W, H];
        for (int y = 0; y < H; y++)
        {
            string r = rows[H - 1 - y];
            for (int x = 0; x < W; x++) g[x, y] = x < r.Length ? r[x] : ' ';
        }
        objects.Clear();
        if (parts.Length > 1)
            foreach (var line in parts[1].Split('\n'))
                if (line.Trim().Length > 0) objects.Add(line.Trim().Split(' '));
    }

    public static char At(int x, int y) => (x < 0 || x >= W || y < 0 || y >= H) ? ' ' : g[x, y];
    public static bool Solid(int x, int y)
    {
        if (x < 0 || x >= W) return true;
        if (y < 0 || y >= H) return false;
        return g[x, y] == '#';
    }
    public static bool OneWay(int x, int y) => At(x, y) == '=';

    public struct Hit { public bool ground, wall, ceil; }

    /// Moves a box (p = bottom centre) through the grid, X then Y.
    public static Hit Move(ref Vector2 p, ref Vector2 v, float hw, float h, float dt, bool drop = false)
    {
        Hit r = default; const float E = 0.001f;
        float nx = p.x + v.x * dt;
        int y0 = Mathf.FloorToInt(p.y + E), y1 = Mathf.FloorToInt(p.y + h - E);
        if (v.x > 0)
        {
            int c = Mathf.FloorToInt(nx + hw);
            for (int y = y0; y <= y1; y++) if (Solid(c, y)) { nx = c - hw - E; v.x = 0; r.wall = true; break; }
        }
        else if (v.x < 0)
        {
            int c = Mathf.FloorToInt(nx - hw);
            for (int y = y0; y <= y1; y++) if (Solid(c, y)) { nx = c + 1 + hw + E; v.x = 0; r.wall = true; break; }
        }
        p.x = nx;

        float ny = p.y + v.y * dt;
        int x0 = Mathf.FloorToInt(p.x - hw + E), x1 = Mathf.FloorToInt(p.x + hw - E);
        if (v.y <= 0)
        {
            int rw = Mathf.FloorToInt(ny);
            for (int x = x0; x <= x1; x++)
                if (Solid(x, rw) || (!drop && OneWay(x, rw) && p.y >= rw + 1 - 0.002f))
                { ny = rw + 1; v.y = 0; r.ground = true; break; }
        }
        else
        {
            int rw = Mathf.FloorToInt(ny + h);
            for (int x = x0; x <= x1; x++) if (Solid(x, rw)) { ny = rw - h - E; v.y = 0; r.ceil = true; break; }
        }
        p.y = ny;
        return r;
    }

    public const float ZF = -1.5f, ZB = 3.6f;      // ground slab: front / back depth

    class MB
    {
        public List<Vector3> v = new List<Vector3>(); public List<Vector3> n = new List<Vector3>(); public List<Vector2> uv = new List<Vector2>(); public List<int> t = new List<int>();
        public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 nrm, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud)
        {
            int i = v.Count; v.Add(a); v.Add(b); v.Add(c); v.Add(d);
            n.Add(nrm); n.Add(nrm); n.Add(nrm); n.Add(nrm); uv.Add(ua); uv.Add(ub); uv.Add(uc); uv.Add(ud);
            t.Add(i); t.Add(i + 1); t.Add(i + 2); t.Add(i); t.Add(i + 2); t.Add(i + 3);
        }
        public void Tri(Vector3 a, Vector3 b, Vector3 c, Vector3 nrm, float va, float vb, float vc)
        {
            int i = v.Count; v.Add(a); v.Add(b); v.Add(c); n.Add(nrm); n.Add(nrm); n.Add(nrm);
            uv.Add(new Vector2(0.5f, va)); uv.Add(new Vector2(0.5f, vb)); uv.Add(new Vector2(0.5f, vc));
            t.Add(i); t.Add(i + 1); t.Add(i + 2);
        }
        public GameObject Build(string name, Transform root, Material m, bool shadows = true)
        {
            var mesh = new Mesh { indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            mesh.SetVertices(v); mesh.SetNormals(n); mesh.SetUVs(0, uv); mesh.SetTriangles(t, 0); mesh.RecalculateBounds();
            mesh.RecalculateTangents();      // URP Lit needs tangents, or axis-aligned faces render black
            var go = new GameObject(name); go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = m;
            if (!shadows) { r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; }
            return go;
        }
    }

    static Material TexMat(string tex, float tile, Color tint, float smooth)
    {
        var m = new Material(Rig.Toon);
        m.SetTexture("_BaseMap", Resources.Load<Texture2D>("Art/" + tex)); m.SetTextureScale("_BaseMap", new Vector2(tile, tile));
        m.SetColor("_BaseColor", tint); m.SetFloat("_Smoothness", smooth);
        return m;
    }

    /// Builds the 3D world geometry: extruded dirt slabs with a rounded grass cap, bamboo platforms, spikes, water.
    public static Material WaterMat;

    public static void BuildVisuals(Transform root, Theme th)
    {
        string[] scatter = th.L("scatter"); bool useBlades = th.B("blades"); float bladeH = th.F("bladeH", 1f);
        var dirt = new MB(); var grass = new MB(); var blades = new MB();
        // ground materials by theme: what the walking surface and the cut face are made of
        string top = th.S("top", "grass"), face = th.S("face", "earth");
        var dirtMat = TexMat(face == "earth" ? "tex_dirt" : "tex_face_" + face, face == "earth" ? 0.125f : 0.25f, th.C("faceTint"), 0.05f);
        Rig.Detail(dirtMat, face == "wood" ? "wood" : face == "brick" ? "brick" : face == "concrete" ? "plaster" : "stone", 0.7f);
        var grassMat = TexMat(top == "grass" ? "tex_grass" : "tex_top_" + top, 0.25f, th.C("topTint"), top == "tile" ? 0.45f : 0.12f);
        Rig.Detail(grassMat, top == "grass" || top == "moss" ? "leaf" : top == "wood" ? "wood" : top == "tile" ? "tile" : "stone", 0.6f);
        // blade material: dark at the root, sunlit at the tip; sways in the wind and parts around Nam
        var grad = new Texture2D(4, 32, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
        for (int yy = 0; yy < 32; yy++)
        {
            Color cc = Color.Lerp(th.C("bladeA"), th.C("bladeB"), Mathf.Pow(yy / 31f, 1.3f));
            for (int xx = 0; xx < 4; xx++) grad.SetPixel(xx, yy, cc);
        }
        grad.Apply();
        var bm = new Material(Rig.Toon);
        bm.SetTexture("_BaseMap", grad); bm.SetFloat("_Smoothness", 0.15f); bm.SetFloat("_Rim", 0.2f); bm.SetFloat("_Wind", 1f); bm.SetFloat("_WindUV", 1f); bm.SetFloat("_Cull", 0f);
        void Flush()
        {   // one set of meshes per 16 columns, so nearby lamps light the ground beneath them
            if (dirt.v.Count > 0) dirt.Build("dirt", root, dirtMat);
            if (grass.v.Count > 0) grass.Build("grass", root, grassMat);
            if (useBlades && blades.v.Count > 0) blades.Build("blades", root, bm, false);
            dirt = new MB(); grass = new MB(); blades = new MB();
        }
        Vector3 bladeN = new Vector3(0, 1f, -0.3f).normalized;
        void Blade(Vector3 p, float hgt, float wid, System.Random rg)
        {
            float a = (float)rg.NextDouble() * Mathf.PI, lean = hgt * (0.15f + (float)rg.NextDouble() * 0.45f), la = (float)rg.NextDouble() * Mathf.PI * 2;
            Vector3 d = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * wid, bend = new Vector3(Mathf.Cos(la), 0, Mathf.Sin(la)) * lean;
            Vector3 bl = p - d, brt = p + d, ml = p + Vector3.up * hgt * 0.55f + bend * 0.35f - d * 0.7f, mr = p + Vector3.up * hgt * 0.55f + bend * 0.35f + d * 0.7f, tip = p + Vector3.up * hgt + bend;
            blades.Tri(bl, ml, mr, bladeN, 0, 0.55f, 0.55f); blades.Tri(bl, mr, brt, bladeN, 0, 0.55f, 0); blades.Tri(ml, tip, mr, bladeN, 0.55f, 1, 0.55f);
        }
        Vector3 F = Vector3.back, U = Vector3.up, L = Vector3.left, R = Vector3.right;
        var rnd = new System.Random(5);
        for (int x = 0; x < W; x++)
        {
            if (x > 0 && x % 16 == 0) Flush();
            for (int y = 0; y < H; y++)
            {
                char c = g[x, y];
                if (c == '=') Rig.Spawn("oneway", root, new Vector3(x + 0.5f, y + 1, 0));
                else if (c == '^') Rig.Spawn("spike", root, new Vector3(x + 0.5f, y, 0));
                if (c != '#') continue;
                float y0 = y == 0 ? -6f : y, y1 = y + 1;
                // a few boulders poking out of the earth face
                if (th.S("face") != "wood" && th.S("face") != "concrete" && Solid(x, y + 1) && rnd.NextDouble() < 0.16)
                    Rig.Spawn("rock", root, new Vector3(x + (float)rnd.NextDouble(), y + (float)rnd.NextDouble() * 0.6f, ZF + 0.12f), (float)rnd.NextDouble() * 360f, 0.5f + (float)rnd.NextDouble() * 0.7f, false);
                // front
                dirt.Quad(new Vector3(x, y0, ZF), new Vector3(x, y1, ZF), new Vector3(x + 1, y1, ZF), new Vector3(x + 1, y0, ZF), F,
                          new Vector2(x, y0), new Vector2(x, y1), new Vector2(x + 1, y1), new Vector2(x + 1, y0));
                // sides
                if (x > 0 && !Solid(x - 1, y))
                    dirt.Quad(new Vector3(x, y0, ZB), new Vector3(x, y1, ZB), new Vector3(x, y1, ZF), new Vector3(x, y0, ZF), L,
                              new Vector2(ZB, y0), new Vector2(ZB, y1), new Vector2(ZF, y1), new Vector2(ZF, y0));
                if (x < W - 1 && !Solid(x + 1, y))
                    dirt.Quad(new Vector3(x + 1, y0, ZF), new Vector3(x + 1, y1, ZF), new Vector3(x + 1, y1, ZB), new Vector3(x + 1, y0, ZB), R,
                              new Vector2(ZF, y0), new Vector2(ZF, y1), new Vector2(ZB, y1), new Vector2(ZB, y0));
                if (Solid(x, y + 1)) continue;
                // ---- grass cap on top cells
                float t = y1;
                bool openL = x > 0 && !Solid(x - 1, y), openR = x < W - 1 && !Solid(x + 1, y);
                float xa = x - (openL ? 0.07f : 0f), xb = x + 1 + (openR ? 0.07f : 0f);
                grass.Quad(new Vector3(xa, t, ZF + 0.1f), new Vector3(xa, t, ZB), new Vector3(xb, t, ZB), new Vector3(xb, t, ZF + 0.1f), U,
                           new Vector2(xa, ZF), new Vector2(xa, ZB), new Vector2(xb, ZB), new Vector2(xb, ZF));
                // rounded front lip
                float[] pz = { ZF + 0.1f, ZF + 0.0f, ZF - 0.06f, ZF - 0.08f, ZF - 0.08f };
                float[] py = { 0f, -0.02f, -0.08f, -0.16f, -0.34f };
                for (int k = 0; k < 4; k++)
                {
                    Vector3 n0 = new Vector3(0, pz[k] - pz[k + 1], py[k + 1] - py[k]).normalized; n0 = new Vector3(0, Mathf.Abs(n0.y), -Mathf.Abs(n0.z)).normalized;
                    grass.Quad(new Vector3(xa, t + py[k + 1], pz[k + 1]), new Vector3(xa, t + py[k], pz[k]), new Vector3(xb, t + py[k], pz[k]), new Vector3(xb, t + py[k + 1], pz[k + 1]), n0,
                               new Vector2(xa, k), new Vector2(xa, k + 1), new Vector2(xb, k + 1), new Vector2(xb, k));
                }
                if (openL)
                {
                    grass.Quad(new Vector3(xa, t - 0.34f, ZB), new Vector3(xa, t, ZB), new Vector3(xa, t, ZF - 0.08f), new Vector3(xa, t - 0.34f, ZF - 0.08f), L, new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0));
                    grass.Quad(new Vector3(xa, t - 0.34f, ZF - 0.08f), new Vector3(xa, t, ZF - 0.08f), new Vector3(x + 0.01f, t, ZF - 0.08f), new Vector3(x + 0.01f, t - 0.34f, ZF - 0.08f), F, new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0));
                }
                if (openR)
                {
                    grass.Quad(new Vector3(xb, t - 0.34f, ZF - 0.08f), new Vector3(xb, t, ZF - 0.08f), new Vector3(xb, t, ZB), new Vector3(xb, t - 0.34f, ZB), R, new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0));
                }
                // a lush field of individual grass blades (short in the lane so feet stay readable)
                bool hazard = At(x, y + 1) == '^';
                for (int k = 0; useBlades && k < (hazard ? 30 : 92); k++)
                {
                    float u = (float)rnd.NextDouble();
                    float z = k < 60 ? Mathf.Lerp(0.5f, ZB - 0.06f, u) : k < 82 ? Mathf.Lerp(ZF + 0.1f, -0.5f, u) : Mathf.Lerp(-0.5f, 0.5f, u);
                    bool lane = k >= 82;
                    float hg = (lane ? 0.07f + (float)rnd.NextDouble() * 0.08f : 0.16f + (float)rnd.NextDouble() * 0.26f) * bladeH;
                    Blade(new Vector3(x + (float)rnd.NextDouble(), t - 0.01f, z), hg, 0.028f + (float)rnd.NextDouble() * 0.02f, rnd);
                }
                // scattered vegetation, kept out of the gameplay lane
                char above = At(x, y + 1);
                if ((above == ' ' || above == 'o') && scatter.Length > 0)
                {
                    for (int k = 0; k < 2; k++)
                    {
                        double r = rnd.NextDouble();
                        if (r > (useBlades ? 0.62 : 0.30)) continue;
                        bool front = rnd.NextDouble() < 0.3;
                        float z = front ? Mathf.Lerp(ZF + 0.2f, -0.8f, (float)rnd.NextDouble()) : Mathf.Lerp(0.95f, ZB - 0.35f, (float)rnd.NextDouble());
                        string mdl = scatter[rnd.Next(scatter.Length)];
                        bool small = mdl == "grass" || mdl == "flower" || mdl == "rice" || mdl == "fern" || mdl == "shell" || mdl == "starfish";
                        if (front && !small) continue;
                        Rig.Spawn(mdl, root, new Vector3(x + (float)rnd.NextDouble(), t, z), (float)rnd.NextDouble() * 360f, (small ? 0.7f : 0.55f) + (float)rnd.NextDouble() * (small ? 0.6f : 0.3f), mdl != "grass");
                    }
                }
            }
        }
        Flush();

        // water: animated surface + a vertical "cut" sheet in front of the ground
        var w = new MB(); float wy = WaterLine, x0 = -60, x1 = W + 60, zf = ZF - 0.06f;
        for (float x = x0; x < x1; x += 2f)
            for (float z = zf; z < 70f; z += (z < 8 ? 1.5f : 8f))
            {
                float z2 = Mathf.Min(70f, z + (z < 8 ? 1.5f : 8f));
                w.Quad(new Vector3(x, wy, z), new Vector3(x, wy, z2), new Vector3(x + 2, wy, z2), new Vector3(x + 2, wy, z), U, Vector2.zero, Vector2.zero, Vector2.zero, Vector2.zero);
            }
        for (float x = x0; x < x1; x += 2f)
            w.Quad(new Vector3(x, -6, zf), new Vector3(x, wy, zf), new Vector3(x + 2, wy, zf), new Vector3(x + 2, -6, zf), F, Vector2.zero, Vector2.zero, Vector2.zero, Vector2.zero);
        WaterMat = new Material(Resources.Load<Shader>("Shaders/NamWater"));
        WaterMat.SetColor("_Shallow", th.C("water", 0)); WaterMat.SetColor("_Deep", th.C("water", 1)); WaterMat.SetColor("_Foam", th.C("water", 2));
        WaterMat.SetColor("_SkyHorizon", th.C("waterSky", 0)); WaterMat.SetColor("_SkyZenith", th.C("waterSky", 1));
        w.Build("water", root, WaterMat, false);
    }
}
