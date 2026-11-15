using System.Collections.Generic;
using UnityEngine;

/// Lightweight pooled sprite particles + camera shake.
public static class Fx
{
    class P { public Transform t; public SpriteRenderer sr; public Vector2 v; public float life, max, grav, size, spin, drag; public Color c; public bool shrink; }
    static readonly List<P> live = new List<P>();
    static readonly Stack<P> free = new Stack<P>();
    static Transform root;
    public static float shake;

    public static void Init()
    {
        live.Clear(); free.Clear();
        root = new GameObject("Fx").transform;
    }

    public static void Emit(string sprite, Vector2 pos, Vector2 vel, float life, float size, Color c, float grav = 0, bool additive = false, float spin = 0, float drag = 0, bool shrink = true, int order = 20)
    {
        if (live.Count > 1400) return;
        P p;
        if (free.Count > 0) { p = free.Pop(); p.t.gameObject.SetActive(true); }
        else
        {
            p = new P();
            var go = new GameObject("p"); go.transform.SetParent(root, false);
            p.t = go.transform; p.sr = go.AddComponent<SpriteRenderer>();
        }
        p.sr.sprite = Art.Get(sprite, 0.5f, 0.5f);
        p.sr.sharedMaterial = additive ? Art.Additive : Art.Normal;
        p.sr.sortingOrder = order;
        p.sr.color = c; p.c = c;
        p.t.position = new Vector3(pos.x, pos.y, order >= 30 ? -3f : -0.9f); p.t.localScale = Vector3.one * size; p.t.rotation = Quaternion.Euler(0, 0, Random.Range(0, 360f));
        p.v = vel; p.life = p.max = life; p.grav = grav; p.size = size; p.spin = spin; p.drag = drag; p.shrink = shrink;
        live.Add(p);
    }

    public static void Burst(string sprite, Vector2 pos, int n, float speed, float life, float size, Color c, float grav = 0, bool additive = false, float up = 0)
    {
        for (int i = 0; i < n; i++)
        {
            float a = Random.Range(0, Mathf.PI * 2);
            var v = new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * speed * Random.Range(0.4f, 1f) + new Vector2(0, up);
            Emit(sprite, pos + Random.insideUnitCircle * 0.15f, v, life * Random.Range(0.6f, 1f), size * Random.Range(0.6f, 1.1f), c, grav, additive, Random.Range(-360f, 360f), 2f);
        }
    }

    public static void Dust(Vector2 pos, int n = 4, float dir = 0)
    {
        for (int i = 0; i < n; i++)
            Emit("dust", pos + new Vector2(Random.Range(-0.2f, 0.2f), 0.05f), new Vector2(Random.Range(-1.5f, 1.5f) - dir * 1.5f, Random.Range(0.3f, 1.4f)), Random.Range(0.25f, 0.5f), Random.Range(0.35f, 0.7f), new Color(0.78f, 0.76f, 0.68f, 0.5f), 0, false, 0, 3f);
    }

    public static void Confetti(Vector2 pos, int n)
    {
        Color[] cols = { new Color(1, 0.3f, 0.35f), new Color(1, 0.8f, 0.2f), new Color(0.3f, 0.85f, 0.5f), new Color(0.35f, 0.65f, 1f), new Color(1f, 0.5f, 0.85f) };
        for (int i = 0; i < n; i++)
            Emit("white", pos + new Vector2(Random.Range(-6f, 6f), Random.Range(0f, 2f)), new Vector2(Random.Range(-2f, 2f), Random.Range(2f, 9f)), Random.Range(1.5f, 3f), Random.Range(1.5f, 3f), cols[Random.Range(0, cols.Length)], -9f, false, Random.Range(-500f, 500f), 1.2f, false, 30);
    }

    public static void Tick(float dt)
    {
        for (int i = live.Count - 1; i >= 0; i--)
        {
            var p = live[i];
            p.life -= dt;
            if (p.life <= 0) { p.t.gameObject.SetActive(false); free.Push(p); live.RemoveAt(i); continue; }
            p.v.y += p.grav * dt;
            p.v *= Mathf.Clamp01(1f - p.drag * dt);
            p.t.position += (Vector3)(p.v * dt);
            p.t.Rotate(0, 0, p.spin * dt);
            float k = p.life / p.max;
            if (p.shrink) p.t.localScale = Vector3.one * p.size * Mathf.Lerp(0.3f, 1f, k);
            var c = p.c; c.a *= Mathf.Clamp01(k * 2f); p.sr.color = c;
        }
        shake = Mathf.MoveTowards(shake, 0, dt * 1.6f);
    }

    public static void Shake(float amount) { shake = Mathf.Max(shake, amount); }
}
