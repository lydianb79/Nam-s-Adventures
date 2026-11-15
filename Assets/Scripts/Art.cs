using System.Collections.Generic;
using UnityEngine;

/// Sprite / material cache. All art lives in Resources/Art as plain textures (128 px = 1 world unit).
public static class Art
{
    public const float PPU = 128f;
    static readonly Dictionary<string, Sprite> cache = new Dictionary<string, Sprite>();
    static Material matNormal, matAdd;

    public static Sprite Get(string name, float px = 0.5f, float py = 0f)
    {
        string key = name + "|" + px + "|" + py;
        if (cache.TryGetValue(key, out var s)) return s;
        var tex = Resources.Load<Texture2D>("Art/" + name);
        if (tex == null) { Debug.LogError("Missing art: " + name); tex = Texture2D.whiteTexture; }
        s = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(px, py), PPU, 0, SpriteMeshType.FullRect);
        s.name = name;
        cache[key] = s;
        return s;
    }

    public static Material Normal
    {
        get { if (matNormal == null) { matNormal = new Material(Resources.Load<Shader>("Shaders/NamSprite")); matNormal.SetFloat("_Dst", 10); } return matNormal; }
    }
    public static Material Additive
    {
        get { if (matAdd == null) { matAdd = new Material(Resources.Load<Shader>("Shaders/NamSprite")); matAdd.SetFloat("_Dst", 1); } return matAdd; }
    }

    public static SpriteRenderer Make(string sprite, Transform parent, Vector2 pos, int order, float px = 0.5f, float py = 0f, bool additive = false)
    {
        var go = new GameObject(sprite);
        go.transform.SetParent(parent, false);
        go.transform.position = new Vector3(pos.x, pos.y, 0);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = Get(sprite, px, py);
        sr.sortingOrder = order;
        sr.sharedMaterial = additive ? Additive : Normal;
        return sr;
    }

    static MaterialPropertyBlock mpb;
    public static void Flash(SpriteRenderer sr, float amount, Color c)
    {
        if (mpb == null) mpb = new MaterialPropertyBlock();
        sr.GetPropertyBlock(mpb);
        mpb.SetFloat("_Flash", amount);
        mpb.SetColor("_FlashColor", c);
        sr.SetPropertyBlock(mpb);
    }
}
