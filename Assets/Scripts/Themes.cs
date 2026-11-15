using System.Collections.Generic;
using UnityEngine;

/// One level's look and cast: sky, light, fog, water, ground, scenery lists, enemy models, music.
/// Loaded from Resources/Levels/themes.txt, which Tools/gen_levels.py writes (26 entries: 25 levels + ending).
public class Theme
{
    readonly Dictionary<string, string> kv = new Dictionary<string, string>();
    static readonly List<Theme> all = new List<Theme>();
    public const int LevelCount = 25;

    public static Theme Get(int index)          // 1-based; LevelCount + 1 is the ending scene
    {
        if (all.Count == 0) LoadAll();
        return all[Mathf.Clamp(index - 1, 0, all.Count - 1)];
    }

    static void LoadAll()
    {
        Theme cur = null;
        foreach (var raw in Resources.Load<TextAsset>("Levels/themes").text.Replace("\r", "").Split('\n'))
        {
            string line = raw.Trim();
            if (line.Length == 0) continue;
            if (line[0] == '[') { cur = new Theme(); all.Add(cur); continue; }
            int eq = line.IndexOf('=');
            if (cur != null && eq > 0) cur.kv[line.Substring(0, eq)] = line.Substring(eq + 1);
        }
    }

    public string S(string key, string def = "") => kv.TryGetValue(key, out var v) ? v : def;
    public float F(string key, float def = 0) => kv.TryGetValue(key, out var v) && float.TryParse(v, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var f) ? f : def;
    public bool B(string key) => F(key) > 0.5f;
    public string[] L(string key)
    {
        string v = S(key);
        return v.Length == 0 ? new string[0] : v.Split(',');
    }
    public static Color Hex(string hex, float a = 1f) { ColorUtility.TryParseHtmlString("#" + hex, out var c); c.a = a; return c; }
    public Color C(string key, int index = 0, string def = "FFFFFF")
    {
        var l = L(key);
        return Hex(index < l.Length ? l[index] : (l.Length > 0 ? l[l.Length - 1] : def));
    }
    public string Name => S("name", "Level");
    public string Sub => S("sub");
    public string Pick(string key, System.Random r) { var l = L(key); return l.Length == 0 ? null : l[r.Next(l.Length)]; }
}
