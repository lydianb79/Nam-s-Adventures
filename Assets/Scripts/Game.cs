using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// Boots itself (no scene setup needed), builds the level from text, runs the game loop.
public class Game : MonoBehaviour
{
    public static Game I;
    public Player player;
    public Transform world;
    public readonly List<Ent> ents = new List<Ent>();
    readonly List<Ent> pending = new List<Ent>();
    public readonly List<Plat> plats = new List<Plat>();

    enum State { Title, Play, Dead, Win, Ending }
    State state;
    bool paused;
    Camera cam; Transform camT; Vector2 camPos; float lookX, zoom = 1f;
    const float Ortho = 5.7f;          // half of the visible height on the gameplay plane (z = 0)
    const float Fov = 30f;
    bool shots; Vector2? focus; float focusZoom = 0.3f;

    // levels
    public int level = 1; public Theme theme; int unlocked = 1;
    System.Action afterIris;            // runs once the iris wipe has fully closed
    float fwT, endT = -1f, selCooldown, cheerT; bool arrived;

    // run stats
    readonly HashSet<int> collected = new HashSet<int>();
    public int coins, coinTotal, coinStreak, lotus, deaths;
    float runTime, streakT, freeze, stateT;
    int checkpoint = -1; Vector2 checkpointPos, startPos;
    readonly bool[] lotusGot = new bool[3];
    readonly List<int> lotusIds = new List<int>();

    // backdrop
    Transform sky, sun, backdrop, starsRoot; DepthOfField dof; UniversalAdditionalLightData sunData;
    Light sunL; Texture2D cookie; ColorAdjustments colorAdj; SpriteRenderer skySr, sunSr, raysSr;
    readonly List<(Transform t, float speed)> risers = new List<(Transform, float)>();
    readonly List<Transform> clouds = new List<Transform>();
    readonly List<(Transform t, float ph, float amp)> bobbers = new List<(Transform, float, float)>();
    readonly List<(Rig rig, Vector3 home, float ph)> butterflies = new List<(Rig, Vector3, float)>();
    float petalT;
    float pollenT;

    // HUD
    Font font;
    Image[] heartImg = new Image[Player.MaxHearts]; Image[] lotusImg = new Image[3];
    Text coinText, timeText, bannerText, bannerSub, promptText, resultText, pauseText, recTitle, recStars, recTime, recCoins, recLotus, recHint, endText, endHint;
    GameObject recBest, endRoot; bool recShow;
    CanvasGroup recordGroup;
    Image fade, flash, logo; GameObject hudRoot, titleRoot, resultRoot, pauseRoot;
    GameObject[] powerRow = new GameObject[3]; Image[] powerBar = new Image[3];
    float bannerT, bannerDur, fadeA, fadeTarget; Color flashC;
    Image iris; Material irisMat; float irisR, irisTarget = 2.3f, startT = -1f; bool logoSfx;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Boot()
    {
        if (I != null) return;
        var go = new GameObject("Game");
        DontDestroyOnLoad(go);
        I = go.AddComponent<Game>();
    }

    void Awake()
    {
        I = this;
        Application.targetFrameRate = -1; QualitySettings.vSyncCount = 1;
        var args = System.Environment.GetCommandLineArgs();
        int si = System.Array.IndexOf(args, "-shots");
        shots = si >= 0 && si + 1 < args.Length;
        foreach (var c in FindObjectsByType<Camera>()) Destroy(c.gameObject);
        var cgo = new GameObject("Main Camera"); cgo.tag = "MainCamera";
        cam = cgo.AddComponent<Camera>(); camT = cgo.transform;
        cam.orthographic = false; cam.fieldOfView = Fov; cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.62f, 0.84f, 0.97f); cam.nearClipPlane = 1f; cam.farClipPlane = 520f; cam.allowHDR = true; cam.allowMSAA = true;
        var cd = cam.GetUniversalAdditionalCameraData();
        cd.renderPostProcessing = true; cd.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing; cd.antialiasingQuality = AntialiasingQuality.High; cd.renderShadows = true;
        cgo.AddComponent<AudioListener>();
        var vol = new GameObject("PostFx").AddComponent<Volume>(); vol.isGlobal = true; vol.sharedProfile = Resources.Load<VolumeProfile>("NamVolume");
        vol.sharedProfile.TryGet(out dof); vol.sharedProfile.TryGet(out colorAdj);

        // sun + soft sky fill
        var lgo = new GameObject("Sun"); sunL = lgo.AddComponent<Light>();
        sunL.type = LightType.Directional; sunL.color = new Color(1f, 0.94f, 0.82f); sunL.intensity = 1.0f; sunL.shadows = LightShadows.Soft; sunL.shadowStrength = 0.72f;
        lgo.transform.rotation = Quaternion.Euler(40f, 32f, 0);
        // drifting cloud shadows: a tileable soft pattern used as the sun's light cookie
        cookie = new Texture2D(256, 256, TextureFormat.RGBA32, false, true) { wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Bilinear };
        var cpx = new Color[256 * 256];
        for (int cy = 0; cy < 256; cy++)
            for (int cx = 0; cx < 256; cx++)
            {
                float u = cx / 256f * Mathf.PI * 2, v = cy / 256f * Mathf.PI * 2;
                float f = Mathf.Cos(u + 0.3f) + Mathf.Cos(v * 2 + 1.7f) * 0.8f + Mathf.Cos(u * 2 + v + 0.9f) * 0.7f + Mathf.Cos(u - v * 2 + 2.4f) * 0.6f + Mathf.Cos(u * 3 - v + 4.1f) * 0.4f + Mathf.Cos(u * 2 + v * 3 + 5.2f) * 0.3f;
                float lit = Mathf.Lerp(0.58f, 1f, Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(-1.2f, -0.2f, f)));
                cpx[cy * 256 + cx] = new Color(lit, lit, Mathf.Lerp(1f, lit, 0.8f), 1);
            }
        cookie.SetPixels(cpx); cookie.Apply();
        sunL.cookie = cookie;
        sunData = sunL.GetUniversalAdditionalLightData(); sunData.lightCookieSize = new Vector2(52f, 52f);
        sunData.softShadowQuality = SoftShadowQuality.High;
        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.66f, 0.80f, 1.0f); RenderSettings.ambientEquatorColor = new Color(0.62f, 0.66f, 0.6f); RenderSettings.ambientGroundColor = new Color(0.40f, 0.46f, 0.32f);
        Shader.SetGlobalColor("_NamSky", new Color(0.40f, 0.50f, 0.72f)); Shader.SetGlobalColor("_NamGround", new Color(0.34f, 0.30f, 0.26f));
        RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear; RenderSettings.fogColor = new Color(0.72f, 0.88f, 0.97f);
        RenderSettings.fogStartDistance = 34f; RenderSettings.fogEndDistance = 300f;

        Sfx.Init(gameObject);
        Fx.Init();
        font = Font.CreateDynamicFontFromOSFont(new[] { "Arial Rounded MT Bold", "Thonburi", "Helvetica Neue" }, 64);
        unlocked = Mathf.Clamp(PlayerPrefs.GetInt("unlocked", 1), 1, Theme.LevelCount);
        sky = new GameObject("sky").transform; sky.SetParent(camT, false); skySr = sky.gameObject.AddComponent<SpriteRenderer>(); skySr.sortingOrder = -100; skySr.sharedMaterial = Art.Normal;
        sunSr = Art.Make("glow", camT, Vector2.zero, -98, 0.5f, 0.5f, true); sun = sunSr.transform;
        raysSr = Art.Make("rays", sun, Vector2.zero, -99, 0.5f, 0.5f, true); raysSr.transform.localScale = Vector3.one * 3.0f;
        BuildHud();
        level = Mathf.Clamp(PlayerPrefs.GetInt("lastLevel", 1), 1, unlocked);
        LoadLevel(level);
        ResetRun();
        BuildWorld();
        RefreshTitlePanel();
        state = State.Title; zoom = 0.6f; camPos = TargetCam();
        Sfx.Music("music_title", 0.6f);
        fadeA = 0; fadeTarget = 0; irisR = 0; irisTarget = 2.3f;       // the title opens with an iris wipe
        NativeMenu.Install();
        NativeMenu.SettingsOpened += () => { if (state == State.Play && !paused) paused = true; };      // pause while the Settings window is up
        NativeMenu.ApplyRenderScale();
        if (shots) { Application.runInBackground = true; StartCoroutine(ShotTour(args[si + 1])); }
        else if (NativeMenu.StartFullscreen) NativeMenu.GoFullscreen();      // Settings ▸ Display ▸ Start in full screen (on by default); Esc drops to a window
        else NativeMenu.GoWindowed();
    }

    // ------------------------------------------------------------------ world

    void ResetRun()
    {
        collected.Clear(); coins = 0; lotus = 0; deaths = 0; runTime = 0; checkpoint = -1; coinStreak = 0;
        for (int i = 0; i < 3; i++) lotusGot[i] = false;
    }

    void BuildWorld()
    {
        if (world != null) Destroy(world.gameObject);
        world = new GameObject("World").transform;
        ents.Clear(); pending.Clear(); plats.Clear(); lotusIds.Clear();
        Level.BuildVisuals(world, theme);
        var cast = theme.L("enemies"); string En(int i, string def) => i < cast.Length && cast[i].Length > 0 ? cast[i] : def;
        bool night = theme.B("night"); int lamps = 0;
        coinTotal = 0; int cp = 0;
        for (int x = 0; x < Level.W; x++)
            for (int y = 0; y < Level.H; y++)
            {
                char c = Level.g[x, y]; int id = x + y * 1000;
                switch (c)
                {
                    case 'P': startPos = new Vector2(x + 0.5f, y); break;
                    case 'o': coinTotal++; if (!collected.Contains(id)) ents.Add(new Coin(world, x, y, id)); break;
                    case 'L': lotusIds.Add(id); if (!collected.Contains(id)) ents.Add(new Lotus(world, x, y, id)); break;
                    case 'S': ents.Add(new PowerUp(world, x, y, Power.SomTam)); break;
                    case 'G': ents.Add(new PowerUp(world, x, y, Power.SangSom)); break;
                    case 'H': ents.Add(new PowerUp(world, x, y, Power.Chili)); break;
                    case 'M': ents.Add(new PowerUp(world, x, y, Power.Mango)); break;
                    case 'K': ents.Add(new Checkpoint(world, x, y, cp, cp <= checkpoint)); cp++; break;
                    case 'X': ents.Add(new Goal(world, x, y)); break;
                    case 'D': ents.Add(new Drum(world, x, y)); break;
                    case 'B': ents.Add(new Brazier(world, x, y)); break;
                    case 'C': { var e = new Crumble(world, x, y); ents.Add(e); plats.Add(e.plat); break; }
                    case 'm': ents.Add(new Monkey(world, x, y, En(0, "monkey"))); break;
                    case 'r': ents.Add(new Crab(world, x, y, En(1, "crab"))); break;
                    case 'c': ents.Add(new Cobra(world, x, y, En(2, "cobra"))); break;
                    case 'q': ents.Add(new Mosquito(world, x, y, En(3, "mosquito"))); break;
                    case 'd': ents.Add(new Durian(world, x, y, En(4, "durian"))); break;
                    case 'g': ents.Add(new Ghost(world, x, y, En(5, "ghost"))); break;
                }
            }
        foreach (var o in Level.objects)
        {
            if (o[0] == "raft")
            {
                var r = new Raft(world, F(o[1]), F(o[2]), F(o[3]), F(o[4]), F(o[5]));
                ents.Add(r); plats.Add(r.plat);
            }
            else if (o[0] == "decor")
            {
                string m; float z = 1.9f, sc = 1f, yaw = 90f;
                switch (o[1])
                {
                    case "w2_0": m = "banana"; z = 1.6f; sc = 1.15f; yaw = 60f + F(o[2]) * 37f; break;
                    case "w1_0": m = "cart"; z = 2.1f; break;
                    case "w1_2": m = "stool"; z = 1.5f; yaw = 70f; break;
                    case "w2_1": m = "rice"; z = 1.0f; sc = 1.2f; break;
                    case "w2_2": m = "bamboo"; z = 2.2f; yaw = 90f + F(o[2]) * 50f; break;
                    case "w5_2": m = "bell"; z = 2.0f; break;
                    case "w5_0": m = "banner"; z = 1.4f; break;
                    case "w5_1": m = "lanterns"; z = 2.4f; break;
                    case "w4_1": m = "frangipani"; z = 2.3f; sc = 1.3f; break;
                    case "w4_0": m = "chedi"; z = 2.0f; sc = 1.1f; break;
                    default: m = o[1]; break;
                }
                if (o.Length >= 7) { z = F(o[4]); yaw = F(o[5]); sc = F(o[6]); }
                var rg = Rig.Spawn(m, world, new Vector3(F(o[2]) + 0.5f, F(o[3]), z), yaw, sc);
                // lights on anything that glows (always for lantern strings, otherwise after dark)
                bool glows = m == "lanterns" || m == "lantern_row" || m == "lamp_post" || m == "market_stall" || m == "neon_sign" || m == "noodle_cart" || m == "grill_cart"
                             || m == "krathong_stand" || m == "restaurant" || m == "crystal" || m == "stone_lantern" || m == "sky_lantern" || m == "seafood_sign";
                if (glows && (night || m == "lanterns") && lamps < 60)
                {
                    lamps++;
                    var lamp = new GameObject("lamp").AddComponent<Light>(); lamp.transform.SetParent(rg.root, false); lamp.transform.localPosition = new Vector3(0, m == "lamp_post" ? 2.4f : 1.4f, 0); lamp.transform.position += Vector3.back * 0.9f;
                    lamp.type = LightType.Point; lamp.range = m == "restaurant" ? 16f : 7f; lamp.intensity = m == "restaurant" ? 14f : 6f;
                    lamp.color = m == "neon_sign" ? new Color(1f, 0.35f, 0.8f) : m == "crystal" ? new Color(0.5f, 0.9f, 1f) : new Color(1f, 0.78f, 0.45f);
                }
            }
            else if (o[0] == "friend")
                ents.Add(new Friend(world, o[1], F(o[2]), F(o[3]), F(o[4]), (int)F(o[5])));
        }
        player = new Player(world, checkpoint >= 0 ? checkpointPos : startPos);
        camPos = TargetCam(); lookX = 0;
        ApplyCamera(0);
    }

    static float F(string s) => float.Parse(s, System.Globalization.CultureInfo.InvariantCulture);

    public void Add(Ent e) { pending.Add(e); }

    Transform Blob(Vector3 pos, Vector3 scale, string hex, bool shadows = false)
    {
        var r = Rig.Spawn("blob", backdrop, pos, 0, 1f, shadows);
        r.root.localScale = scale;
        foreach (var mr in r.root.GetComponentsInChildren<Renderer>()) { mr.sharedMaterial = Rig.Mat(hex + "_s8_e0"); mr.receiveShadows = true; }
        return r.root;
    }

    // ------------------------------------------------------------------ levels & themes

    void LoadLevel(int n)
    {
        level = n; theme = Theme.Get(n);
        Level.Load(n > Theme.LevelCount ? "ending" : "level" + n);
        ApplyTheme();
        BuildBackdrop();
    }

    /// Sky gradient, sun or moon, light, ambient, fog and exposure for the current theme.
    void ApplyTheme()
    {
        var th = theme; bool night = th.B("night");
        var tex = new Texture2D(2, 64, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
        for (int y = 0; y < 64; y++)
        {
            float v = y / 63f;                                    // 0 horizon .. 1 zenith
            Color c = v < 0.45f ? Color.Lerp(th.C("sky", 2), th.C("sky", 1), v / 0.45f) : Color.Lerp(th.C("sky", 1), th.C("sky", 0), (v - 0.45f) / 0.55f);
            tex.SetPixel(0, y, c); tex.SetPixel(1, y, c);
        }
        tex.Apply();
        skySr.sprite = Sprite.Create(tex, new Rect(0, 0, 2, 64), new Vector2(0.5f, 0.5f), 8f);
        cam.backgroundColor = th.C("sky", 2);
        sunL.color = th.C("sun"); sunL.intensity = th.F("sunI", 1f);
        var sd = th.L("sunDir"); sunL.transform.rotation = Quaternion.Euler(sd.Length > 0 ? float.Parse(sd[0], System.Globalization.CultureInfo.InvariantCulture) : 40f, sd.Length > 1 ? float.Parse(sd[1], System.Globalization.CultureInfo.InvariantCulture) : 32f, 0);
        sunL.cookie = night ? null : cookie;                     // cloud shadows by day only
        Shader.SetGlobalColor("_NamSky", th.C("ambSky")); Shader.SetGlobalColor("_NamGround", th.C("ambGround"));
        RenderSettings.fogColor = th.C("fog"); RenderSettings.fogStartDistance = th.F("fogStart", 34f); RenderSettings.fogEndDistance = th.F("fogEnd", 300f);
        if (colorAdj != null) colorAdj.postExposure.value = th.F("exposure", 0.08f);
        sunSr.color = night ? new Color(0.85f, 0.9f, 1f, th.B("stars") ? 0.95f : 0f) : new Color(th.C("sun").r, th.C("sun").g, th.C("sun").b, 0.9f);
        raysSr.color = night ? Color.clear : new Color(1f, 0.95f, 0.7f, 0.12f);

        if (starsRoot != null) Destroy(starsRoot.gameObject);
        starsRoot = new GameObject("stars").transform; starsRoot.SetParent(camT, false);
        if (th.B("stars"))
        {
            var r = new System.Random(5);
            for (int i = 0; i < 140; i++)
            {
                var st = Art.Make("spark", starsRoot, Vector2.zero, -97, 0.5f, 0.5f, true);
                st.transform.localPosition = new Vector3(((float)r.NextDouble() - 0.5f) * 440f, ((float)r.NextDouble() - 0.15f) * 150f, 470f);
                st.transform.localScale = Vector3.one * (3f + (float)r.NextDouble() * 7f);
                st.color = new Color(1f, 1f, 0.9f + (float)r.NextDouble() * 0.1f, 0.5f + (float)r.NextDouble() * 0.5f);
            }
        }
    }

    Rig Scn(string model, Vector3 pos, float yaw, float scale, bool shadows = true) => string.IsNullOrEmpty(model) ? null : Rig.Spawn(model, backdrop, pos, yaw, scale, shadows);

    /// Layered 3D scenery built from the theme's recipe: things on the water, a middle layer (rice terraces,
    /// rolling hills, dunes, forest, cliffs or a row of buildings), far landmarks, mountains, clouds, stars,
    /// rising lanterns, out-of-focus foreground and fluttering life.
    void BuildBackdrop()
    {
        if (backdrop != null) Destroy(backdrop.gameObject);
        backdrop = new GameObject("Backdrop").transform;
        clouds.Clear(); bobbers.Clear(); butterflies.Clear(); risers.Clear();
        var th = theme;
        var rnd = new System.Random(21 + level * 13);
        float Rn(float a, float b) => a + (float)rnd.NextDouble() * (b - a);
        string[] trees = th.L("trees"), props = th.L("hillProps"), crowns = th.L("crowns"), hc = th.L("hillColors");
        string Tree() => trees.Length > 0 ? trees[rnd.Next(trees.Length)] : null;
        string Prop() => (props.Length > 0 && rnd.NextDouble() < 0.3) ? props[rnd.Next(props.Length)] : Tree();
        string HillCol() => hc.Length > 0 ? hc[rnd.Next(hc.Length)] : "7FCB58";
        float wl = Level.WaterLine; int W = Level.W;

        // --- on the water
        string pads = th.S("pads");
        if (pads.Length > 0)
            for (float x = -30; x < W + 40; x += Rn(2.2f, 5f))
                Scn(pads, new Vector3(x, wl + 0.02f, Rn(4.3f, 9f)), Rn(0, 360), Rn(0.8f, 1.5f), false);
        var isl = th.L("islands"); var extras = th.L("extras");
        if (isl.Length > 0)
            for (float x = -20; x < W + 40; x += Rn(22, 36))
            {
                float z = Rn(8f, 12.5f), sx = Rn(3f, 5.5f);
                Blob(new Vector3(x, wl - 0.35f, z), new Vector3(sx, 0.9f, 2.2f), isl[rnd.Next(isl.Length)]);
                Scn(Tree(), new Vector3(x + Rn(-1, 1), wl + 0.35f, z), Rn(0, 360), Rn(1.0f, 1.5f));
                if (extras.Length > 0 && rnd.NextDouble() < 0.45)
                {
                    var e = Scn(extras[rnd.Next(extras.Length)], new Vector3(x + sx + Rn(0.5f, 2f), wl - 0.62f, z - Rn(0.5f, 2f)), Rn(20, 160), 1.15f);
                    if (e != null) bobbers.Add((e.root, Rn(0, 6), 0.03f));
                }
            }
        var fl = th.L("floaters");
        if (fl.Length > 0)
            for (float x = 6; x < W + 20; x += Rn(30, 52))
            {
                var b = Scn(fl[rnd.Next(fl.Length)], new Vector3(x, wl - 0.02f, Rn(5.5f, 8f)), rnd.NextDouble() < 0.5 ? 100f : 80f, 1.0f);
                if (b != null) bobbers.Add((b.root, Rn(0, 6), 0.07f));
            }

        // --- middle layer
        string hills = th.S("hills");
        if (hills == "terrace")
        {
            int hill = 0;
            for (float x = -40; x < W + 60; x += Rn(26, 36), hill++)
            {
                float s = Rn(2.3f, 3.3f), z = 15f + 5f * s + Rn(0, 4), by = -1.6f;
                if (hill % 3 == 2) { Blob(new Vector3(x, -0.5f, z - 3f), new Vector3(Rn(11, 16), Rn(6f, 9f), 7f), HillCol(), true); continue; }
                Scn(th.S("hillModel", "terrace"), new Vector3(x, by, z), Rn(0, 360), s);
                float top = by + 3.55f * s;
                string crown = crowns.Length > 0 ? crowns[hill % crowns.Length] : null;
                Scn(crown, new Vector3(x, top, z - 0.5f * s), crown == "wat" ? Rn(80, 100) : 90, crown == "wat" ? 0.42f * s : 0.7f * s);
                for (int i = 0; i < 9; i++)
                {
                    int tier = rnd.Next(0, 5); float a = Rn(200, 340) * Mathf.Deg2Rad;      // front half of the hill
                    float r = (5.0f - tier * 0.62f) * 0.93f * s - 0.5f;
                    string m = Prop();
                    Scn(m, new Vector3(x + Mathf.Cos(a) * r, by + (tier * 0.5f + 0.5f) * s - 0.05f, z + Mathf.Sin(a) * r), Rn(40, 140), m == "hut" ? 1.3f : Rn(1.3f, 2.0f));
                }
            }
        }
        else if (hills == "blob" || hills == "dune")
        {
            for (float x = -45; x < W + 60; x += Rn(17, 26))
            {
                float z = Rn(17, 24), sx = Rn(11, 17), sy = hills == "dune" ? Rn(3f, 5f) : Rn(5.5f, 9.5f);
                Blob(new Vector3(x, -0.5f, z), new Vector3(sx, sy, 7f), HillCol(), true);
                int n = rnd.Next(3, 7);
                for (int i = 0; i < n; i++)
                {
                    float u = Rn(-0.6f, 0.6f), zz = Rn(-0.55f, -0.15f);
                    float hy = -0.5f + sy * Mathf.Sqrt(Mathf.Max(0, 1 - u * u - zz * zz));
                    string m = Prop();
                    Scn(m, new Vector3(x + u * sx, hy - (m == "hut" || m == "beach_hut" ? 0.2f : 0.5f), z + zz * 7f), Rn(40, 140), m == "hut" || m == "beach_hut" ? Rn(1.4f, 1.8f) : Rn(1.5f, 2.4f));
                }
            }
        }
        else if (hills == "forest")
        {
            for (float x = -50; x < W + 70; x += 46f) Blob(new Vector3(x, wl - 1.3f, 16f), new Vector3(34f, 2.0f, 11f), HillCol(), true);     // a low bank
            for (float x = -40; x < W + 60; x += Rn(1.8f, 3.6f))
            {
                float z = Rn(7.5f, 24f);
                Scn(Prop(), new Vector3(x, wl + 0.45f - Mathf.Abs(z - 16f) * 0.03f, z), Rn(0, 360), Rn(1.3f, 2.3f) * (1f + (z - 8f) * 0.02f));
            }
        }
        else if (hills == "cliff")
        {
            for (float x = -40; x < W + 60; x += Rn(15, 25))
            {
                float z = Rn(15, 25), s = Rn(2.2f, 3.8f);
                Scn("karst", new Vector3(x, -2f, z), Rn(0, 360), s);
                Blob(new Vector3(x + Rn(-3, 3), wl - 0.4f, z - 3f - s), new Vector3(Rn(4, 7), 1.0f, 2.6f), isl.Length > 0 ? isl[0] : "86CC55");
                for (int i = 0; i < 3; i++) Scn(Prop(), new Vector3(x + Rn(-4, 4), wl + 0.3f, z - 3f - s + Rn(-1, 1)), Rn(0, 360), Rn(1.1f, 1.7f));
            }
        }
        else if (hills == "city")
        {
            var bld = th.L("buildings");
            for (float x = -60; x < W + 80; x += 50f) Blob(new Vector3(x, wl - 1.25f, 19f), new Vector3(36f, 1.9f, 12f), th.B("night") ? "3A3A46" : "9A948A", true);    // quay
            for (int row = 0; row < 2 && bld.Length > 0; row++)
                for (float x = -40; x < W + 60; x += Rn(5.5f, 8.5f) * (1f + row * 0.5f))
                {
                    string m = bld[rnd.Next(bld.Length)];
                    Scn(m, new Vector3(x, wl + 0.35f, row == 0 ? Rn(11.5f, 14.5f) : Rn(20f, 27f)), 90 + Rn(-8, 8), Rn(1.0f, 1.35f) * (1f + row * 0.55f));
                    if (row == 0 && rnd.NextDouble() < 0.35) Scn(Tree(), new Vector3(x + Rn(2, 4), wl + 0.35f, Rn(10.5f, 12.5f)), Rn(0, 360), Rn(1.2f, 1.7f));
                }
        }

        // --- far landmarks, hazy mountains, clouds
        var far = th.L("far");
        if (far.Length > 0)
            for (float x = -90; x < W + 120; x += Rn(42, 70))
                Scn(far[rnd.Next(far.Length)], new Vector3(x, -3f, Rn(78, 100)), Rn(0, 360), Rn(4.2f, 6.5f), false);
        var mts = th.L("mountains");
        if (mts.Length > 0)
            for (float x = -160; x < W + 200; x += Rn(50, 80))
                Blob(new Vector3(x, -8f, Rn(125, 155)), new Vector3(Rn(48, 78), Rn(20, 34), 20f), mts[rnd.Next(mts.Length)]);
        int nCloud = (int)th.F("clouds", 16);
        for (int i = 0; i < nCloud; i++)
        {
            var c = Scn("cloud", new Vector3(Rn(-120, W + 160), Rn(22, 52), Rn(90, 170)), 90, Rn(3.5f, 7f), false);
            foreach (var mr in c.root.GetComponentsInChildren<Renderer>()) mr.sharedMaterial = Rig.Mat(th.S("cloudCol", "FFFFFF") + "_s0_e" + (th.B("night") ? "1" : "6"));
            clouds.Add(c.root);
        }
        // --- paper lanterns drifting up into the night
        int nLan = (int)th.F("lanterns", 0);
        for (int i = 0; i < nLan; i++)
        {
            var l = Scn("sky_lantern", new Vector3(Rn(-30, W + 40), Rn(4, 44), Rn(7, 80)), Rn(0, 360), Rn(0.9f, 1.8f), false);
            if (l != null) risers.Add((l.root, Rn(0.25f, 0.7f)));
        }

        // --- out-of-focus things close to the camera, tops just peeking into view
        var fore = th.L("fore");
        if (fore.Length > 0)
            for (float x = 4; x < W; x += Rn(13, 22))
            {
                int cx = Mathf.Clamp(Mathf.RoundToInt(x), 0, W - 1); float surf = 3;
                for (int yy = Level.H - 1; yy >= 0; yy--) if (Level.Solid(cx, yy)) { surf = yy + 1; break; }
                var f = Scn(fore[rnd.Next(fore.Length)], new Vector3(x, 0, Rn(-8f, -6.5f)), Rn(0, 360), 1.7f, false);
                if (f == null) continue;
                var b = new Bounds(f.root.position, Vector3.zero);
                foreach (var mr in f.root.GetComponentsInChildren<Renderer>()) b.Encapsulate(mr.bounds);
                f.root.position += Vector3.up * (surf - 0.9f - b.max.y);
            }
        // --- butterflies by day, fireflies by night
        var bf = th.L("flutter");
        if (bf.Length > 0)
            for (float x = 5; x < W; x += Rn(9, 17))
            {
                int cx = Mathf.Clamp(Mathf.RoundToInt(x), 0, W - 1); float surf = 3;
                for (int yy = Level.H - 1; yy >= 0; yy--) if (Level.Solid(cx, yy)) { surf = yy + 1; break; }
                butterflies.Add((Rig.Spawn(bf[rnd.Next(bf.Length)], backdrop, new Vector3(x, surf + 1.5f, 1.5f), 0, 1.25f, false), new Vector3(x, surf + Rn(1.0f, 2.6f), Rn(0.9f, 2.6f)), Rn(0, 10)));
            }
    }

    void TickLife(float dt)
    {
        float t = Time.time;
        foreach (var c in clouds) { var p = c.position; p.x += dt * 0.6f; if (p.x > Level.W + 170) p.x = -130; c.position = p; }
        foreach (var r in risers) { var p = r.t.position; p.y += dt * r.speed; p.x += Mathf.Sin(t * 0.4f + p.z) * dt * 0.15f; if (p.y > 48) p.y = 3; r.t.position = p; }
        foreach (var b in bobbers)
        {
            var p = b.t.position; p.y += Mathf.Cos(t * 1.3f + b.ph) * b.amp * dt * 1.3f; b.t.position = p;
            var e = b.t.eulerAngles; b.t.rotation = Quaternion.Euler(Mathf.Sin(t * 1.1f + b.ph) * 2f, e.y, Mathf.Sin(t * 0.8f + b.ph) * 1.5f);
        }
        foreach (var b in butterflies)
        {
            float ph = b.ph + t;
            Vector3 p = b.home + new Vector3(Mathf.Sin(ph * 0.7f) * 2.2f, Mathf.Sin(ph * 1.9f) * 0.5f + Mathf.Sin(ph * 0.5f) * 0.4f, Mathf.Sin(ph * 0.45f) * 0.8f);
            Vector3 d = p - b.rig.root.position; b.rig.root.position = p;
            if (d.sqrMagnitude > 1e-8f) b.rig.root.rotation = Quaternion.Slerp(b.rig.root.rotation, Quaternion.LookRotation(d.normalized, Vector3.up) * Quaternion.Euler(0, -90, 0), 0.2f);
            float f = Mathf.Sin(ph * 22f) * 62f;
            b.rig.Rot("wingL", f, 0, 0); b.rig.Rot("wingR", -f, 0, 0);
        }
    }

    // ------------------------------------------------------------------ loop

    void Update()
    {
        In.Poll();
        NativeMenu.Pump();
        float rdt = Mathf.Min(Time.unscaledDeltaTime, 1f / 30f);
        float dt = rdt;
        if (freeze > 0) { freeze -= rdt; dt = 0; }
        stateT += rdt;
        bool pauseKey = In.Pause;
        if (In.Esc) { if (Screen.fullScreen && !shots) NativeMenu.GoWindowed(); else pauseKey = true; }   // Esc: fullscreen -> window, then pause

        // a closed iris hands over to whatever was waiting (next level, level select, ending, title)
        if (afterIris != null)
        {
            irisTarget = 0;
            if (irisR <= 0.001f) { var a = afterIris; afterIris = null; a(); irisTarget = 2.3f; }
        }
        bool busy = afterIris != null;

        switch (state)
        {
            case State.Title:
                // left / right picks any level reached so far
                selCooldown -= rdt;
                if (!busy && startT < 0 && stateT > 1.5f && Mathf.Abs(In.X) > 0.5f && selCooldown <= 0)
                {
                    int want = Mathf.Clamp(level + (In.X > 0 ? 1 : -1), 1, unlocked);
                    selCooldown = 0.28f;
                    if (want != level)
                    {
                        Sfx.Play("sfx_select");
                        afterIris = () => { LoadLevel(want); ResetRun(); BuildWorld(); RefreshTitlePanel(); stateT = 3f; PlayerPrefs.SetInt("lastLevel", want); };
                    }
                }
                if (!busy && startT < 0 && In.Confirm && stateT > 0.4f)
                {   // start: Nam hops, the iris closes on her, then the level opens
                    startT = 0; Sfx.Play("sfx_confirm"); Sfx.Play("sfx_jump", 0.6f);
                    player.Bounce(13f); irisTarget = 0;
                    Fx.Burst("star", player.Center, 14, 6f, 0.6f, 1.1f, new Color(1f, 0.9f, 0.5f), 0, true);
                }
                if (startT >= 0)
                {
                    startT += rdt;
                    if (startT > 0.62f && irisR <= 0.001f) { startT = -1; StartRun(); break; }
                }
                if (In.Quit) Application.Quit();
                player.titlePose = 1f;
                In.X = 0; In.JumpDown = false; In.FireDown = false; In.Run = false;
                player.Tick(Mathf.Min(rdt, 0.02f));
                break;
            case State.Play:
                if (pauseKey) { paused = !paused; Sfx.Play("sfx_select"); }
                if (paused)
                {
                    if (In.Restart) { paused = false; StartRun(); }
                    if (In.Quit) Application.Quit();
                    dt = 0;
                }
                else if (dt > 0) { runTime += dt; Simulate(dt); }
                break;
            case State.Dead:
                if (dt > 0) Simulate(dt);
                if (stateT > 1.0f) fadeTarget = 1;
                if (stateT > 1.45f && fadeA >= 0.99f) { BuildWorld(); state = State.Play; stateT = 0; fadeTarget = 0; }
                break;
            case State.Win:
                if (dt > 0) Simulate(dt);
                if (Random.value < rdt * 6f) Fx.Confetti(camPos + new Vector2(0, 3f), 6);
                if (stateT > 2.6f && !resultRoot.activeSelf) ShowResults();
                if (!busy && stateT > 3.2f && In.Confirm)
                {
                    Sfx.Play("sfx_confirm");
                    if (level >= Theme.LevelCount) afterIris = StartEnding;
                    else { int next = level + 1; afterIris = () => { LoadLevel(next); StartRun(); }; }
                }
                if (!busy && stateT > 3.2f && In.Restart) { Sfx.Play("sfx_select"); afterIris = StartRun; }
                if (In.Quit) Application.Quit();
                break;
            case State.Ending:
                // Nam walks up to the restaurant on her own; her friends cheer; the sky fills with fireworks
                In.X = (!arrived && player.pos.x < 21.3f) ? 1 : 0; In.JumpDown = In.JumpHeld = In.Run = In.FireDown = In.Down = false;
                if (dt > 0) Simulate(dt);
                if (!arrived && player.pos.x >= 21.3f)
                {
                    arrived = true; endT = 0; player.Win(); Friend.Cheering = true;
                    Sfx.Play("sfx_cheer", 1f, 1f, 0); Sfx.Loop("amb_crowd", 0.55f); cheerT = 3.5f;       // everyone erupts, then keeps clapping
                    Sfx.Play("jingle_win", 0.7f, 1f, 0); Fx.Confetti(camPos + new Vector2(0, 3f), 120); FlashScreen(new Color(1, 1, 0.8f, 0.5f));
                }
                if (arrived)
                {
                    endT += rdt; cheerT -= rdt;
                    if (cheerT <= 0) { cheerT = Random.Range(5f, 8f); Sfx.Play("sfx_cheer", 0.55f, Random.Range(0.94f, 1.08f), 0, Random.Range(-0.3f, 0.3f)); }     // fresh waves of cheering
                }
                fwT -= rdt;
                if (fwT <= 0) { Firework(); fwT = arrived ? Random.Range(0.18f, 0.6f) : Random.Range(0.8f, 1.5f); }
                if (arrived && Random.value < rdt * 5f) Fx.Confetti(camPos + new Vector2(0, 3f), 8);
                if (!busy && arrived && endT > 6f && In.Confirm) { Sfx.Play("sfx_confirm"); afterIris = GoTitle; }
                if (In.Quit) Application.Quit();
                break;
        }

        Fx.Tick(rdt);
        Sfx.MusicPitch = (player != null && player.drunk > 0) ? 1.22f : 1f;
        Sfx.ListenerX = camPos.x; Sfx.HalfWidth = Ortho * cam.aspect * Mathf.Max(0.5f, zoom); Sfx.Muffled = paused;
        Sfx.Tick(rdt);
        Ambient(rdt);
        TickLife(rdt);
        if (sunData != null) sunData.lightCookieOffset = new Vector2(Time.time * 1.1f, Time.time * 0.35f);
        if (player != null) Shader.SetGlobalVector("_NamPlayer", new Vector4(player.pos.x, player.pos.y, 0, Mathf.Abs(player.vel.x)));
        UpdateCamera(paused ? 0 : rdt);
        UpdateHud(rdt);
    }

    void Simulate(float dt)
    {
        streakT -= dt; if (streakT <= 0) coinStreak = 0;
        for (int i = 0; i < ents.Count; i++) if (!ents[i].dead) ents[i].Tick(dt);
        player.Tick(dt);
        if (pending.Count > 0) { ents.AddRange(pending); pending.Clear(); }
        ents.RemoveAll(e => e.dead);
    }

    void StartRun()
    {
        ResetRun(); state = State.Play; BuildWorld(); stateT = 0; paused = false;
        resultRoot.SetActive(false); endRoot.SetActive(false);
        Sfx.Music(theme.S("music", "music_level"), 0.5f);
        fadeA = 0; fadeTarget = 0; irisR = 0; irisTarget = 2.3f; zoom = 0.55f;      // iris opens on Nam while the camera pulls back
        Banner("LEVEL " + level, theme.Name, new Color(1f, 0.9f, 0.45f), 2.6f);
        bannerT = -0.55f;
        PlayerPrefs.SetInt("lastLevel", level);
    }

    /// After level 25: the seafood restaurant, where everyone is waiting.
    void StartEnding()
    {
        LoadLevel(Theme.LevelCount + 1);
        collected.Clear(); checkpoint = -1; arrived = false; endT = -1; fwT = 1.2f; Friend.Cheering = false;
        state = State.Ending; BuildWorld(); stateT = 0; paused = false;
        resultRoot.SetActive(false);
        Sfx.Music("music_ending", 0.6f);
        irisR = 0; irisTarget = 2.3f; zoom = 0.7f;
        Banner("THE SEAFOOD RESTAURANT", "Everyone is waiting for Nam", new Color(1f, 0.85f, 0.45f), 3.2f);
        bannerT = -0.6f;
    }

    void GoTitle()
    {
        endRoot.SetActive(false); resultRoot.SetActive(false); Sfx.Loop(null);
        LoadLevel(1); ResetRun(); BuildWorld(); RefreshTitlePanel();
        state = State.Title; stateT = 3f; startT = -1; paused = false;
        Sfx.Music("music_title", 0.6f);
    }

    /// One firework: a bright flash and a sphere of sparks that droop and fade, sometimes with a second ring.
    void Firework()
    {
        float hw = Ortho * cam.aspect * zoom;
        Vector2 p = camPos + new Vector2(Random.Range(-hw * 0.9f, hw * 0.9f), Random.Range(1.2f, 4.6f) * zoom);
        Color c = Color.HSVToRGB(Random.value, Random.Range(0.55f, 0.95f), 1f);
        Color c2 = Color.HSVToRGB(Random.value, 0.7f, 1f);
        int n = Random.Range(34, 52); float sp = Random.Range(5.5f, 8.5f);
        for (int i = 0; i < n; i++)
        {
            float a = i * Mathf.PI * 2f / n + Random.Range(-0.05f, 0.05f);
            Vector2 v = new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * sp * Random.Range(0.85f, 1.05f);
            Fx.Emit("spark", p, v, Random.Range(1.1f, 1.7f), 2.4f, c, -4.5f, true, 0, 1.7f, true, 30);
            if (i % 3 == 0) Fx.Emit("star", p, v * 0.55f, Random.Range(0.9f, 1.3f), 1.0f, c2, -3.5f, true, 200f, 1.7f, true, 30);
        }
        Fx.Emit("glow", p, Vector2.zero, 0.35f, 12f, new Color(c.r, c.g, c.b, 0.55f), 0, true, 0, 0, true, 29);
        Sfx.PlayAt(p.x, "sfx_firework", Random.Range(0.45f, 0.8f), Random.Range(0.8f, 1.25f), 0);
        FlashScreen(new Color(c.r, c.g, c.b, 0.07f));
    }

    // ------------------------------------------------------------------ game events

    public void Freeze(float t) { freeze = Mathf.Max(freeze, t); }
    public void CollectCoin(int id) { collected.Add(id); coins++; coinStreak++; streakT = 0.6f; }
    public void AddBonusCoin() { coins++; }
    public void CollectLotus(int id)
    {
        collected.Add(id); lotus++;
        int i = lotusIds.IndexOf(id); if (i >= 0 && i < 3) lotusGot[i] = true;
        Banner("LOTUS " + lotus + " / 3", "", new Color(1f, 0.7f, 0.9f), 1.4f);
    }
    public void SetCheckpoint(int index, Vector2 pos) { if (index > checkpoint) { checkpoint = index; checkpointPos = pos; } }
    public void OnPlayerDied() { if (state != State.Play) return; deaths++; state = State.Dead; stateT = 0; }
    public void Win(Vector2 gongPos)
    {
        if (state != State.Play) return;
        state = State.Win; stateT = 0;
        player.Win();
        Sfx.Music(null); Sfx.Play("sfx_gong", 1f, 1f, 0); Sfx.Play("jingle_win", 0.9f, 1f, 0);
        if (level < Theme.LevelCount && level + 1 > unlocked) { unlocked = level + 1; PlayerPrefs.SetInt("unlocked", unlocked); PlayerPrefs.Save(); }
        Fx.Shake(0.5f); FlashScreen(new Color(1, 1, 0.8f, 0.6f));
        Fx.Burst("star", gongPos + Vector2.up * 1.5f, 40, 10f, 1.2f, 1.6f, new Color(1f, 0.85f, 0.4f), 0, true);
        Fx.Confetti(camPos + new Vector2(0, 3f), 80);
    }
    public void FlashScreen(Color c) { flashC = c; }
    public void Banner(string title, string sub, Color c, float dur = 2.4f)
    {
        bannerText.text = title; bannerSub.text = sub; bannerText.color = c; bannerT = 0; bannerDur = dur;
    }

    void Ambient(float dt)
    {
        float hw = Ortho * cam.aspect;
        string kind = theme.S("particles", "petal");
        petalT -= dt;
        if (petalT <= 0)
        {
            Vector2 top = camPos + new Vector2(Random.Range(-hw, hw * 1.3f), Ortho + 0.5f);
            Vector2 any = camPos + new Vector2(Random.Range(-hw, hw), Random.Range(-Ortho, Ortho));
            switch (kind)
            {
                case "petal":      // frangipani petals drifting on the breeze
                    petalT = 0.3f;
                    Fx.Emit("petal", top, new Vector2(Random.Range(-1.6f, -0.5f), Random.Range(-1.3f, -0.7f)), 9f, Random.Range(0.6f, 1.1f), new Color(1f, 1f, 1f, 0.95f), 0, false, Random.Range(-140f, 140f), 0, false, 16);
                    break;
                case "leaf":
                    petalT = 0.25f;
                    Fx.Emit("petal", top, new Vector2(Random.Range(-1.8f, -0.4f), Random.Range(-1.5f, -0.8f)), 9f, Random.Range(0.6f, 1.0f), Color.Lerp(new Color(0.45f, 0.75f, 0.25f), new Color(0.85f, 0.7f, 0.25f), Random.value), 0, false, Random.Range(-200f, 200f), 0, false, 16);
                    break;
                case "rain":
                    petalT = 0.012f;
                    for (int i = 0; i < 3; i++) Fx.Emit("white", camPos + new Vector2(Random.Range(-hw, hw * 1.4f), Ortho + 0.5f), new Vector2(-5f, -26f), 0.5f, 0.9f, new Color(0.8f, 0.88f, 1f, 0.45f), 0, false, 0, 0, false, 16);
                    break;
                case "drop":       // Songkran: water flying everywhere
                    petalT = 0.07f;
                    Fx.Emit("spark", any, new Vector2(Random.Range(-3f, 3f), Random.Range(2f, 6f)), 0.9f, 1.6f, new Color(0.6f, 0.9f, 1f, 0.8f), -14f, false, 0, 0, true, 16);
                    break;
                case "firefly":
                    petalT = 0.2f;
                    Fx.Emit("spark", any, Random.insideUnitCircle * 0.5f, Random.Range(2f, 3.5f), Random.Range(1.2f, 2.2f), new Color(0.8f, 1f, 0.4f, 0.9f), 0, true, 0, 0, true, 16);
                    break;
                case "lantern":    // warm motes rising
                    petalT = 0.18f;
                    Fx.Emit("spark", any, new Vector2(Random.Range(-0.3f, 0.3f), Random.Range(0.4f, 1.0f)), Random.Range(3f, 5f), Random.Range(1.4f, 2.6f), new Color(1f, 0.7f, 0.3f, 0.8f), 0, true, 0, 0, true, 16);
                    break;
                case "spark":      // embers from the grills
                    petalT = 0.1f;
                    Fx.Emit("spark", any, new Vector2(Random.Range(-0.6f, 0.6f), Random.Range(0.8f, 2f)), Random.Range(1.2f, 2.4f), Random.Range(0.8f, 1.5f), new Color(1f, 0.55f, 0.2f, 0.9f), 0, true, 0, 0, true, 16);
                    break;
                default: petalT = 1f; break;
            }
        }
        pollenT -= dt;
        if (pollenT > 0 || theme.B("night") || kind == "rain") return;
        pollenT = 0.12f;
        Vector2 p = camPos + new Vector2(Random.Range(-hw, hw), Random.Range(-Ortho, Ortho));
        Fx.Emit("dust", p, new Vector2(Random.Range(-0.6f, -0.1f), Random.Range(0.05f, 0.4f)), Random.Range(3f, 5f), Random.Range(0.06f, 0.16f), new Color(1f, 1f, 0.8f, 0.45f), 0, true, 0, 0, false, 15);
    }

    // ------------------------------------------------------------------ camera

    Vector2 TargetCam()
    {
        float hw = Ortho * cam.aspect;
        if (state == State.Title) return new Vector2(player.pos.x + 2.9f + Mathf.Sin(Time.unscaledTime * 0.35f) * 0.35f, player.pos.y + 1.75f + Mathf.Sin(Time.unscaledTime * 0.5f) * 0.08f);
        if (state == State.Ending) return new Vector2(Mathf.Lerp(Mathf.Max(hw * 0.7f, player.pos.x + 4f), 26.5f, Ease01(endT / 2.5f)), 6.4f);
        float x = Mathf.Clamp(player.pos.x + lookX, hw, Mathf.Max(hw, Level.W - hw));
        float y = Mathf.Max(player.pos.y + 1.6f, Ortho);
        return new Vector2(x, y);
    }

    void UpdateCamera(float dt)
    {
        if (player == null) return;
        if (state == State.Title)
        {   // opening shot: sweep down from high above the village and settle on Nam
            float x = Mathf.Clamp01(stateT / 2.4f), e = 1f - Mathf.Pow(1f - x, 3f);
            Vector2 t = TargetCam();
            camPos = Vector2.Lerp(t + new Vector2(11f, 6.5f), t, e);
            zoom = Mathf.Lerp(1.75f, 0.53f + Mathf.Sin(Time.unscaledTime * 0.4f) * 0.012f, e) - (startT > 0 ? Mathf.Min(startT, 0.7f) * 0.2f : 0f);   // close on Nam, breathing slightly; push in when starting
            ApplyCamera(dt);
            return;
        }
        if (state == State.Ending)
        {
            camPos = Vector2.Lerp(camPos, TargetCam(), 1f - Mathf.Exp(-3f * dt));
            zoom = Mathf.Lerp(zoom, 0.92f, 1f - Mathf.Exp(-2f * dt));
            ApplyCamera(dt);
            return;
        }
        if (dt > 0 && !player.deadState)
        {
            float wantLook = player.winState ? 0 : player.facing * 1.8f + Mathf.Clamp(player.vel.x * 0.22f, -2.2f, 2.2f);
            lookX = Mathf.Lerp(lookX, wantLook, 1f - Mathf.Exp(-2.2f * dt));
            Vector2 t = TargetCam();
            camPos.x = Mathf.Lerp(camPos.x, t.x, 1f - Mathf.Exp(-9f * dt));
            // vertical: lazy while airborne inside a dead zone, snappy when landed or near the screen edge
            float dy = t.y - camPos.y;
            float k = (player.grounded || Mathf.Abs(dy) > 2.6f) ? 5f : 1.2f;
            if (dy < -1.5f) k = 9f;
            camPos.y = Mathf.Lerp(camPos.y, t.y, 1f - Mathf.Exp(-k * dt));
            zoom = Mathf.Lerp(zoom, state == State.Ending ? 0.92f : player.winState ? 0.8f : 1f, 1f - Mathf.Exp(-3f * dt));
        }
        ApplyCamera(dt);
    }

    /// Perspective camera a fixed distance in front of the lane, raised a little so the tops of the ground show.
    void ApplyCamera(float dt)
    {
        Vector2 sh = Random.insideUnitCircle * Fx.shake * 0.45f;
        float roll = 0, z = zoom;
        if (player != null && player.drunk > 0 && !paused)
        {
            float a = Mathf.Clamp01(player.drunk) * Mathf.Clamp01(Player.DrunkTime - player.drunk + 0.3f);
            roll = Mathf.Sin(Time.time * 2.3f) * 2.6f * a; z *= 1f + Mathf.Sin(Time.time * 3.1f) * 0.025f * a;
        }
        Vector3 look = new Vector3(camPos.x + sh.x, camPos.y + sh.y, 0);
        if (focus.HasValue) { look = focus.Value; z = focusZoom; }
        float dist = Ortho / Mathf.Tan(Fov * 0.5f * Mathf.Deg2Rad) * z;
        camT.position = look + new Vector3(0, 1.5f * z, -dist);
        if (dof != null) dof.focusDistance.value = dist;
        camT.rotation = Quaternion.LookRotation(look - camT.position, Vector3.up) * Quaternion.Euler(0, 0, roll);

        // sky + sun ride with the camera, far away
        float sd = 480f, sh2 = sd * Mathf.Tan(Fov * 0.5f * Mathf.Deg2Rad) * 2f, sw = sh2 * cam.aspect;
        sky.localPosition = new Vector3(0, 0, sd); sky.localRotation = Quaternion.identity; sky.localScale = new Vector3(sw / 0.25f * 1.3f, sh2 / 8f * 1.3f, 1);
        bool moon = theme != null && theme.B("night");
        sun.localPosition = new Vector3(sw * (moon ? -0.28f : 0.3f), sh2 * 0.3f, sd - 5f); sun.localScale = Vector3.one * sh2 * (moon ? 0.045f : 0.11f); sun.Rotate(0, 0, 3f * dt);
    }

    // ------------------------------------------------------------------ HUD

    RectTransform Rt(GameObject go, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size)
    {
        var rt = go.GetComponent<RectTransform>(); if (rt == null) rt = go.AddComponent<RectTransform>();
        rt.SetParent(parent, false);
        rt.anchorMin = rt.anchorMax = anchor; rt.pivot = anchor; rt.anchoredPosition = pos; rt.sizeDelta = size;
        return rt;
    }

    Image Img(string sprite, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size)
    {
        var go = new GameObject(sprite, typeof(RectTransform));
        var im = go.AddComponent<Image>(); im.sprite = Art.Get(sprite, 0.5f, 0.5f); im.raycastTarget = false; im.preserveAspect = true;
        Rt(go, parent, anchor, pos, size);
        return im;
    }

    Text Txt(string s, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size, int fs, TextAnchor align, Color c)
    {
        var go = new GameObject("text", typeof(RectTransform));
        var t = go.AddComponent<Text>(); t.font = font; t.fontSize = fs; t.alignment = align; t.color = c; t.text = s; t.raycastTarget = false;
        t.horizontalOverflow = HorizontalWrapMode.Overflow; t.verticalOverflow = VerticalWrapMode.Overflow; t.fontStyle = FontStyle.Bold;
        var o = go.AddComponent<Outline>(); o.effectColor = new Color(0.16f, 0.08f, 0.2f, 1f); o.effectDistance = new Vector2(3, -3);
        var sh = go.AddComponent<Shadow>(); sh.effectColor = new Color(0.16f, 0.08f, 0.2f, 0.8f); sh.effectDistance = new Vector2(0, -6);
        Rt(go, parent, anchor, pos, size);
        return t;
    }

    Image Full(Transform parent, Color c)
    {
        var go = new GameObject("full", typeof(RectTransform));
        var im = go.AddComponent<Image>(); im.color = c; im.raycastTarget = false;
        var rt = go.GetComponent<RectTransform>(); rt.SetParent(parent, false);
        rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one; rt.offsetMin = rt.offsetMax = Vector2.zero;
        return im;
    }

    void BuildHud()
    {
        var cgo = new GameObject("HUD");
        var canvas = cgo.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = 10;
        var sc = cgo.AddComponent<CanvasScaler>(); sc.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; sc.referenceResolution = new Vector2(1920, 1080); sc.matchWidthOrHeight = 1f;
        var root = cgo.transform;
        Vector2 TL = new Vector2(0, 1), TR = new Vector2(1, 1), TC = new Vector2(0.5f, 1), C = new Vector2(0.5f, 0.5f), BC = new Vector2(0.5f, 0);

        flash = Full(root, Color.clear);

        hudRoot = new GameObject("hud", typeof(RectTransform)); var hr = hudRoot.GetComponent<RectTransform>(); hr.SetParent(root, false);
        hr.anchorMin = Vector2.zero; hr.anchorMax = Vector2.one; hr.offsetMin = hr.offsetMax = Vector2.zero;
        for (int i = 0; i < heartImg.Length; i++) heartImg[i] = Img("ui_heart", hr, TL, new Vector2(36 + i * 78, -30), new Vector2(72, 72));
        Img("ui_coin", hr, TL, new Vector2(36, -116), new Vector2(64, 64));
        coinText = Txt("0", hr, TL, new Vector2(112, -112), new Vector2(300, 72), 52, TextAnchor.MiddleLeft, Color.white);
        for (int i = 0; i < 3; i++) lotusImg[i] = Img("ui_lotus", hr, TC, new Vector2((i - 1) * 92, -22), new Vector2(84, 84));
        timeText = Txt("0:00", hr, TR, new Vector2(-40, -30), new Vector2(300, 72), 52, TextAnchor.MiddleRight, Color.white);
        string[] icons = { "ui_somtam", "ui_chili", "ui_sangsom" };
        Color[] cols = { new Color(0.5f, 0.95f, 0.4f), new Color(1f, 0.4f, 0.25f), new Color(1f, 0.78f, 0.25f) };
        for (int i = 0; i < 3; i++)
        {
            var row = new GameObject("power", typeof(RectTransform)); Rt(row, hr, TL, new Vector2(36, -200 - i * 76), new Vector2(320, 70));
            Img(icons[i], row.transform, new Vector2(0, 0.5f), new Vector2(0, 0), new Vector2(68, 68));
            var bg = Img("white", row.transform, new Vector2(0, 0.5f), new Vector2(80, 0), new Vector2(210, 22)); bg.preserveAspect = false; bg.color = new Color(0.16f, 0.08f, 0.2f, 0.75f);
            var bar = Img("white", row.transform, new Vector2(0, 0.5f), new Vector2(84, 0), new Vector2(202, 14)); bar.preserveAspect = false; bar.color = cols[i];
            bar.type = Image.Type.Filled; bar.fillMethod = Image.FillMethod.Horizontal; bar.fillOrigin = 0;
            powerRow[i] = row; powerBar[i] = bar;
        }
        bannerText = Txt("", root, C, new Vector2(0, 190), new Vector2(1600, 160), 120, TextAnchor.MiddleCenter, Color.white);
        bannerSub = Txt("", root, C, new Vector2(0, 90), new Vector2(1600, 70), 46, TextAnchor.MiddleCenter, Color.white);

        titleRoot = new GameObject("title", typeof(RectTransform)); var tr = titleRoot.GetComponent<RectTransform>(); tr.SetParent(root, false);
        tr.anchorMin = Vector2.zero; tr.anchorMax = Vector2.one; tr.offsetMin = tr.offsetMax = Vector2.zero;
        logo = Img("logo3d", tr, C, new Vector2(250, 150), new Vector2(1150, 584));
        promptText = Txt("PRESS  SPACE  TO  START", tr, C, new Vector2(250, -235), new Vector2(1400, 80), 56, TextAnchor.MiddleCenter, new Color(1f, 0.95f, 0.6f));
        // bottom of the title: level name and the best run so far
        var rec = new GameObject("record", typeof(RectTransform)); var rrt = rec.GetComponent<RectTransform>(); rrt.SetParent(tr, false);
        rrt.anchorMin = new Vector2(0, 0); rrt.anchorMax = new Vector2(1, 0); rrt.pivot = new Vector2(0.5f, 0); rrt.offsetMin = Vector2.zero; rrt.offsetMax = new Vector2(0, 190);
        recordGroup = rec.AddComponent<CanvasGroup>();
        var band = Full(rrt, new Color(0.10f, 0.03f, 0.16f, 0.5f));
        var line = Img("white", rrt, new Vector2(0.5f, 1), new Vector2(0, 0), new Vector2(1920 * 2, 5)); line.preserveAspect = false; line.color = new Color(1f, 0.8f, 0.3f, 0.9f);
        Img("ui_lotus", rrt, new Vector2(0.5f, 1), new Vector2(-470, 34), new Vector2(76, 76)); Img("ui_lotus", rrt, new Vector2(0.5f, 1), new Vector2(470, 34), new Vector2(76, 76));
        recTitle = Txt("", rrt, new Vector2(0.5f, 1), new Vector2(0, -18), new Vector2(1400, 60), 44, TextAnchor.MiddleCenter, new Color(1f, 0.88f, 0.45f));
        recHint = Txt("", rrt, new Vector2(0.5f, 1), new Vector2(0, -150), new Vector2(1400, 40), 26, TextAnchor.MiddleCenter, new Color(1, 1, 1, 0.7f));
        recBest = new GameObject("best", typeof(RectTransform)); Rt(recBest, rrt, new Vector2(0.5f, 1), Vector2.zero, new Vector2(10, 10));
        var rb = recBest.transform;
        Txt("BEST RUN", rb, new Vector2(0.5f, 1), new Vector2(-520, -96), new Vector2(300, 50), 34, TextAnchor.MiddleRight, new Color(1, 1, 1, 0.85f));
        recStars = Txt("", rb, new Vector2(0.5f, 1), new Vector2(-290, -94), new Vector2(240, 56), 50, TextAnchor.MiddleCenter, new Color(1f, 0.82f, 0.25f));
        recTime = Txt("", rb, new Vector2(0.5f, 1), new Vector2(-70, -96), new Vector2(200, 50), 42, TextAnchor.MiddleCenter, Color.white);
        Img("ui_coin", rb, new Vector2(0.5f, 1), new Vector2(90, -92), new Vector2(54, 54));
        recCoins = Txt("", rb, new Vector2(0.5f, 1), new Vector2(190, -96), new Vector2(120, 50), 42, TextAnchor.MiddleLeft, Color.white);
        Img("ui_lotus", rb, new Vector2(0.5f, 1), new Vector2(330, -90), new Vector2(60, 60));
        recLotus = Txt("", rb, new Vector2(0.5f, 1), new Vector2(450, -96), new Vector2(160, 50), 42, TextAnchor.MiddleLeft, Color.white);

        pauseRoot = new GameObject("pause", typeof(RectTransform)); var pr = pauseRoot.GetComponent<RectTransform>(); pr.SetParent(root, false);
        pr.anchorMin = Vector2.zero; pr.anchorMax = Vector2.one; pr.offsetMin = pr.offsetMax = Vector2.zero;
        Full(pr, new Color(0.1f, 0.03f, 0.15f, 0.6f));
        pauseText = Txt("PAUSED\n<size=44>P  resume      R  restart level      Q  quit</size>", pr, C, Vector2.zero, new Vector2(1600, 300), 110, TextAnchor.MiddleCenter, Color.white);
        pauseRoot.SetActive(false);

        resultRoot = new GameObject("result", typeof(RectTransform)); var rr = resultRoot.GetComponent<RectTransform>(); rr.SetParent(root, false);
        rr.anchorMin = Vector2.zero; rr.anchorMax = Vector2.one; rr.offsetMin = rr.offsetMax = Vector2.zero;
        Full(rr, new Color(0.1f, 0.03f, 0.15f, 0.55f));
        resultText = Txt("", rr, C, new Vector2(0, 20), new Vector2(1600, 800), 60, TextAnchor.MiddleCenter, Color.white);
        resultRoot.SetActive(false);

        endRoot = new GameObject("ending", typeof(RectTransform)); var er = endRoot.GetComponent<RectTransform>(); er.SetParent(root, false);
        er.anchorMin = Vector2.zero; er.anchorMax = Vector2.one; er.offsetMin = er.offsetMax = Vector2.zero;
        endText = Txt("", er, TC, new Vector2(0, -50), new Vector2(1700, 420), 54, TextAnchor.UpperCenter, Color.white);
        endHint = Txt("", er, BC, new Vector2(0, 36), new Vector2(1700, 60), 40, TextAnchor.MiddleCenter, new Color(1f, 0.95f, 0.63f));
        endRoot.SetActive(false);

        fade = Full(root, Color.black);
        iris = Full(root, Color.white);
        irisMat = new Material(Resources.Load<Shader>("Shaders/NamIris")); iris.material = irisMat;
    }

    /// Title panel: selected level, its best run, and a hint when more levels can be chosen.
    void RefreshTitlePanel()
    {
        // the level name only appears once there is a choice of levels; with nothing to show the panel stays hidden
        recTitle.text = unlocked > 1 ? "LEVEL " + level + "   ·   " + theme.Name.ToUpper() : "";
        int bs = PlayerPrefs.GetInt("best" + level + "Stars", 0);
        recBest.SetActive(bs > 0); recShow = unlocked > 1 || bs > 0;
        if (bs > 0)
        {
            recStars.text = new string('★', bs) + new string('☆', 3 - bs);
            recTime.text = Fmt(PlayerPrefs.GetFloat("best" + level + "Time", 0));
            recCoins.text = PlayerPrefs.GetInt("best" + level + "Coins", 0).ToString();
            recLotus.text = PlayerPrefs.GetInt("best" + level + "Lotus", 0) + " / 3";
        }
        recHint.text = unlocked > 1 ? "◀   ▶   choose a level   (" + unlocked + " of " + Theme.LevelCount + " reached)" : "";
    }

    void ShowResults()
    {
        resultRoot.SetActive(true);
        int stars = 1 + (lotus == 3 ? 1 : 0) + (deaths == 0 ? 1 : 0);
        string st = new string('★', stars) + new string('☆', 3 - stars);
        // remember the best run of this level (more stars first, then the faster time)
        string k = "best" + level;
        int bestS = PlayerPrefs.GetInt(k + "Stars", 0);
        if (stars > bestS || (stars == bestS && runTime < PlayerPrefs.GetFloat(k + "Time", 1e9f)))
        {
            PlayerPrefs.SetInt(k + "Stars", stars); PlayerPrefs.SetFloat(k + "Time", runTime); PlayerPrefs.SetInt(k + "Coins", coins); PlayerPrefs.SetInt(k + "Lotus", lotus);
            PlayerPrefs.Save();
        }
        string next = level >= Theme.LevelCount ? "SPACE  to the restaurant!" : "SPACE  next level";
        resultText.text = "<size=120><color=#FFE066>ไชโย!  LEVEL " + level + " CLEAR</color></size>\n<size=110><color=#FFD23F>" + st + "</color></size>\n\n" +
            "Baht coins   " + coins + "\nLotus flowers   " + lotus + " / 3\nTime   " + Fmt(runTime) + "\nOops   " + deaths +
            "\n\n<size=44><color=#FFF2A0>" + next + "        R  play again        Q  quit</color></size>";
    }

    void UpdateEnding()
    {
        bool show = state == State.Ending && arrived && endT > 1.4f;
        if (endRoot.activeSelf != show) endRoot.SetActive(show);
        if (!show) return;
        int stars = 0, coinsAll = 0, lotusAll = 0; float time = 0;
        for (int i = 1; i <= Theme.LevelCount; i++)
        {
            stars += PlayerPrefs.GetInt("best" + i + "Stars", 0); coinsAll += PlayerPrefs.GetInt("best" + i + "Coins", 0);
            lotusAll += PlayerPrefs.GetInt("best" + i + "Lotus", 0); time += PlayerPrefs.GetFloat("best" + i + "Time", 0);
        }
        float a = Mathf.Clamp01((endT - 1.4f) * 1.5f);
        string more = "";
        endHint.text = endT > 6f ? "SPACE  back to the title        Q  quit" : "";
        endText.text = "<size=130><color=#FFE066>NAM MADE IT!</color></size>\n<size=58>Dinner with friends at the seafood restaurant</size>\n" +
            "<size=44><color=#FFD23F>★ " + stars + " / " + (Theme.LevelCount * 3) + "</color>      Baht coins " + coinsAll + "      Lotus " + lotusAll + " / " + (Theme.LevelCount * 3) + "      Time " + Fmt(time) + "</size>" + more;
        endText.color = new Color(1, 1, 1, a);
        endText.rectTransform.localScale = Vector3.one * (1f + Mathf.Sin(Time.unscaledTime * 2.2f) * 0.012f);
    }

    static float Ease01(float x) { x = Mathf.Clamp01(x); return 1f - (1f - x) * (1f - x) * (1f - x); }
    static string Fmt(float t) { int s = (int)t; return (s / 60) + ":" + (s % 60).ToString("00"); }

    void UpdateHud(float dt)
    {
        bool inGame = state != State.Title && state != State.Ending;
        UpdateEnding();
        hudRoot.SetActive(inGame); titleRoot.SetActive(state == State.Title); pauseRoot.SetActive(paused);
        if (state == State.Title)
        {
            // logo drops in with a bounce once the camera is close; prompt follows
            float k = Mathf.Clamp01((stateT - 1.25f) / 0.6f), k1 = k - 1f;
            float pop = 1f + 2.70158f * k1 * k1 * k1 + 1.70158f * k1 * k1;                      // "back" ease-out overshoot
            float outK = startT >= 0 ? Mathf.Clamp01(startT / 0.35f) : 0f;
            if (k > 0 && !logoSfx) { logoSfx = true; Sfx.Play("sfx_lotus", 0.6f, 1.1f); Sfx.Play("sfx_spring", 0.5f, 0.8f); }
            logo.rectTransform.localScale = Vector3.one * Mathf.Max(0.001f, pop * (1f + Mathf.Sin(Time.unscaledTime * 1.5f) * 0.015f) * (1f + outK * 0.6f));
            logo.rectTransform.localRotation = Quaternion.Euler(0, 0, Mathf.Sin(Time.unscaledTime * 0.9f) * 1.2f + (1f - k) * -14f);
            logo.rectTransform.anchoredPosition = new Vector2(250, 150 + (1f - k) * 520f + outK * 260f);
            logo.color = new Color(1, 1, 1, Mathf.Clamp01(k * 4f) * (1f - outK));
            float pa = Mathf.Clamp01((stateT - 2.3f) * 2.5f) * (1f - outK);
            promptText.color = new Color(1f, 0.95f, 0.6f, (0.55f + 0.45f * Mathf.Sin(Time.unscaledTime * 4f)) * pa);
            recordGroup.alpha = recShow ? Mathf.Clamp01((stateT - 2.0f) * 2f) * (1f - outK) : 0f;
            recordGroup.transform.localPosition = new Vector3(recordGroup.transform.localPosition.x, recordGroup.transform.localPosition.y, 0);
            ((RectTransform)recordGroup.transform).anchoredPosition = new Vector2(0, -(1f - Ease01((stateT - 2.0f) * 1.6f)) * 200f - outK * 220f);
        }
        else if (inGame)
        {
            for (int i = 0; i < heartImg.Length; i++)
            {
                heartImg[i].sprite = Art.Get(i < player.hearts ? "ui_heart" : "ui_heart_empty", 0.5f, 0.5f);
                float pulse = (player.hearts == 1 && i == 0) ? 1f + Mathf.Abs(Mathf.Sin(Time.unscaledTime * 6f)) * 0.18f : 1f;
                heartImg[i].rectTransform.localScale = Vector3.one * pulse;
            }
            coinText.text = coins.ToString();
            for (int i = 0; i < 3; i++) lotusImg[i].color = lotusGot[i] ? Color.white : new Color(0.12f, 0.06f, 0.18f, 0.55f);
            timeText.text = Fmt(runTime);
            float[] v = { player.somtam / Player.SomtamTime, player.chili / Player.ChiliTime, player.drunk / Player.DrunkTime };
            int row = 0;
            for (int i = 0; i < 3; i++)
            {
                bool on = v[i] > 0; powerRow[i].SetActive(on);
                if (!on) continue;
                powerBar[i].fillAmount = v[i];
                powerRow[i].GetComponent<RectTransform>().anchoredPosition = new Vector2(36, -200 - row * 76); row++;
            }
        }
        // banner pop
        bannerT += dt;
        float a = bannerDur <= 0 ? 0 : Mathf.Clamp01(bannerT * 6f) * Mathf.Clamp01((bannerDur - bannerT) * 3f);
        var bc = bannerText.color; bc.a = a; bannerText.color = bc; bannerSub.color = new Color(1, 1, 1, a);
        float sc = 1f + Mathf.Max(0, 0.25f - bannerT) * 1.6f;
        bannerText.rectTransform.localScale = Vector3.one * sc;
        bannerText.gameObject.SetActive(a > 0.01f); bannerSub.gameObject.SetActive(a > 0.01f);

        // iris wipe, centred on Nam
        irisR = Mathf.MoveTowards(irisR, irisTarget, dt * (irisTarget > irisR ? 2.6f + irisR * 2.5f : 2.2f + irisR * 4f));
        bool irisOn = irisR < 2.29f;
        if (iris.gameObject.activeSelf != irisOn) iris.gameObject.SetActive(irisOn);
        if (irisOn && player != null)
        {
            Vector3 vp = cam.WorldToViewportPoint(new Vector3(player.pos.x, player.pos.y + 0.85f, 0));
            irisMat.SetVector("_Center", new Vector4(Mathf.Clamp01(vp.x), Mathf.Clamp01(vp.y), 0, 0));
            irisMat.SetFloat("_Radius", irisR * irisR * 0.45f + irisR * 0.12f - 0.02f); irisMat.SetFloat("_Aspect", cam.aspect);
        }
        fadeA = Mathf.MoveTowards(fadeA, fadeTarget, dt * 3.5f); fade.color = new Color(0.08f, 0.02f, 0.12f, fadeA);
        flashC.a = Mathf.MoveTowards(flashC.a, 0, dt * 1.8f); flash.color = flashC;
    }

    // ------------------------------------------------------------------ automated screenshot tour (-shots <dir>)

    IEnumerator ShotTour(string dir)
    {
        System.IO.Directory.CreateDirectory(dir);
        string only = System.Environment.GetEnvironmentVariable("NAM_LEVELS") ?? "";      // e.g. "3,7,12" to tour a few levels
        yield return new WaitForSecondsRealtime(3.1f);
        ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "00_title.png"));
        yield return new WaitForSecondsRealtime(0.3f);
        for (int n = 1; n <= Theme.LevelCount; n++)
        {
            if (only.Length > 0 && System.Array.IndexOf(only.Split(','), n.ToString()) < 0) continue;
            var sw = System.Diagnostics.Stopwatch.StartNew();
            LoadLevel(n); long tLoad = sw.ElapsedMilliseconds; StartRun();
            Debug.Log("LOADTIME level " + n + " backdrop=" + tLoad + "ms world=" + (sw.ElapsedMilliseconds - tLoad) + "ms");
            yield return new WaitForSecondsRealtime(1.3f);
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "L" + n.ToString("00") + "a.png"));
            yield return new WaitForSecondsRealtime(0.25f);
            float x = Level.W * 0.52f; int cx = Mathf.FloorToInt(x); float y = 12;
            for (int tries = 0; tries < 12 && !Level.Solid(cx, 0); tries++) cx++;
            for (int yy = Level.H - 1; yy >= 0; yy--) if (Level.Solid(cx, yy)) { y = yy + 1; break; }
            player.Teleport(new Vector2(cx + 0.5f, y)); camPos = TargetCam();
            for (float tt = 0; tt < 1.1f; tt += Time.unscaledDeltaTime) { player.invuln = 2f; yield return null; }
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "L" + n.ToString("00") + "b.png"));
            yield return new WaitForSecondsRealtime(0.25f);
            Debug.Log("TOUR level " + n + " " + theme.Name + " W=" + Level.W + " ents=" + ents.Count + " fps=" + (1f / Time.smoothDeltaTime).ToString("F0"));
        }
        if (only.Length == 0 || only.Contains("end"))
        {
            // win on the last level, then the ending
            LoadLevel(Theme.LevelCount); StartRun(); yield return new WaitForSecondsRealtime(0.6f);
            var goal = ents.Find(q => q is Goal);
            player.Teleport(goal.pos); yield return new WaitForSecondsRealtime(3.4f);
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "W_results.png")); yield return new WaitForSecondsRealtime(0.3f);
            In.Bot = () => { In.Confirm = true; }; yield return null; yield return null; In.Bot = null;
            yield return new WaitForSecondsRealtime(3.5f);
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "E1_walk.png"));
            yield return new WaitForSecondsRealtime(5.5f);
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "E2_party.png"));
            yield return new WaitForSecondsRealtime(4.0f);
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "E3_party.png"));
            yield return new WaitForSecondsRealtime(0.3f);
            Debug.Log("ENDING state=" + state + " arrived=" + arrived + " x=" + player.pos.x.ToString("F1"));
        }
        if (only.Length == 0)
        {
            // controller sanity on level 2: run + jump, then fall in the water and respawn
            LoadLevel(2); StartRun(); yield return new WaitForSecondsRealtime(0.5f);
            int fr = 0; In.Bot = () => { In.X = 1; In.Run = true; In.JumpHeld = true; In.JumpDown = (fr++ % 45) == 20; };
            float x0 = player.pos.x; yield return new WaitForSecondsRealtime(1.6f); In.Bot = null;
            Debug.Log("BOT moved=" + (player.pos.x - x0).ToString("F1") + " state=" + state);
            int d0 = deaths; int px = 0; while (px < Level.W && Level.Solid(px, 0)) px++;
            player.Teleport(new Vector2(px + 0.5f, 2.0f)); yield return new WaitForSecondsRealtime(3.2f);
            Debug.Log("RESPAWN state=" + state + " deaths=" + (deaths - d0) + " hearts=" + player.hearts);
        }
        Debug.Log("SHOTS_DONE");
        Application.Quit();
    }
}
