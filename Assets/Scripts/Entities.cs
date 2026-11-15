using UnityEngine;

/// A ride-able surface (raft, crumbling plank). Player lands on `top` between x0..x1.
public class Plat
{
    public float x0, x1, top;
    public Vector2 delta;
    public bool active = true;
    public System.Action onRide;
    public void OnRide() { onRide?.Invoke(); }
}

public abstract class Ent
{
    public Rig rig; public GameObject go;
    public Vector2 pos;               // bottom centre (gameplay plane, z = 0)
    public float hw = 0.4f, h = 0.8f;
    public bool dead;
    protected float t;

    protected void Init(Transform root, string model, Vector2 p, float yaw = 90f, float scale = 1f)
    {
        pos = p;
        rig = Rig.Spawn(model, root, new Vector3(p.x, p.y, 0), yaw, scale);
        go = rig.root.gameObject;
    }
    protected SpriteRenderer Halo(string sprite, Vector3 local, float scale, Color c, int order = 3)
    {
        var sr = Art.Make(sprite, go.transform.parent, Vector2.zero, order, 0.5f, 0.5f, true);
        sr.transform.SetParent(go.transform.parent, false);
        sr.transform.position = go.transform.position + local; sr.transform.localScale = Vector3.one * scale; sr.color = c;
        return sr;
    }
    public virtual void Tick(float dt) { }
    public bool Touch(Player p, float shrink = 0.05f)
    {
        return !p.deadState && !p.winState && Mathf.Abs(p.pos.x - pos.x) < p.hw + hw - shrink && p.pos.y < pos.y + h - shrink && p.pos.y + p.h > pos.y + shrink;
    }
    public virtual void Remove() { dead = true; if (go != null) Object.Destroy(go); }
    protected void Sync(float dy = 0, float z = 0) { go.transform.position = new Vector3(pos.x, pos.y + dy, z); }
    protected void Yaw(float y) { go.transform.rotation = Quaternion.Euler(0, y, 0); }
    protected static Player P => Game.I.player;
    protected static float S(float f, float ph = 0) => Mathf.Sin(Time.time * f + ph);
}

// =============================================================== collectibles

public class Coin : Ent
{
    int id; float phase;
    public Coin(Transform root, int x, int y, int id)
    {
        Init(root, "coin", new Vector2(x + 0.5f, y + 0.15f), 90, 0.95f);
        foreach (var r in go.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        hw = 0.3f; h = 0.7f; this.id = id; phase = x * 0.6f;
    }
    public override void Tick(float dt)
    {
        t += dt;
        Sync(0.35f + Mathf.Sin(t * 3f + phase) * 0.06f);
        Yaw(t * 200f + phase * 40f);
        if (Touch(P, 0))
        {
            Game.I.CollectCoin(id);
            Sfx.PlayAt(pos.x, "sfx_coin", 0.5f, 1f + (Game.I.coinStreak % 8) * 0.06f, 0);
            Fx.Burst("star", pos + Vector2.up * 0.4f, 5, 3.5f, 0.35f, 0.7f, new Color(1, 0.9f, 0.4f, 0.9f), 0, true);
            Remove();
        }
    }
}

public class Lotus : Ent
{
    int id; SpriteRenderer rays;
    public Lotus(Transform root, int x, int y, int id)
    {
        Init(root, "lotus", new Vector2(x + 0.5f, y), 90, 0.95f);
        rays = Halo("rays", new Vector3(0, 0.45f, 0.4f), 0.75f, new Color(1f, 0.7f, 0.9f, 0.5f));
        hw = 0.45f; h = 0.9f; this.id = id;
    }
    public override void Tick(float dt)
    {
        t += dt;
        Sync(0.15f + Mathf.Sin(t * 2.2f) * 0.12f);
        go.transform.rotation = Quaternion.Euler(-28f, t * 50f, 0);
        rays.transform.Rotate(0, 0, 40f * dt);
        if (Random.value < dt * 5f) Fx.Emit("spark", pos + new Vector2(Random.Range(-0.5f, 0.5f), Random.Range(0, 1f)), new Vector2(0, 0.6f), 0.7f, 1.2f, new Color(1f, 0.75f, 0.95f, 0.8f), 0, true);
        if (Touch(P, 0))
        {
            Game.I.CollectLotus(id);
            Sfx.PlayAt(pos.x, "sfx_lotus", 0.9f);
            Fx.Burst("star", pos + Vector2.up * 0.5f, 18, 6f, 0.8f, 1.4f, new Color(1f, 0.7f, 0.95f), 0, true);
            Remove();
        }
    }
    public override void Remove() { if (rays != null) Object.Destroy(rays.gameObject); base.Remove(); }
}

public enum Power { SomTam, SangSom, Chili, Mango }

public class PowerUp : Ent
{
    Power kind; SpriteRenderer bubble, glow; float dy, tilt;
    public PowerUp(Transform root, int x, int y, Power kind)
    {
        this.kind = kind;
        string s = kind == Power.SomTam ? "somtam" : kind == Power.SangSom ? "sangsom" : kind == Power.Chili ? "chili" : "mango";
        float sc = kind == Power.SomTam ? 0.72f : kind == Power.SangSom ? 0.85f : kind == Power.Chili ? 0.9f : 0.8f;
        dy = kind == Power.SomTam ? 0.42f : kind == Power.SangSom ? 0.2f : kind == Power.Chili ? 0.22f : 0.3f;
        tilt = kind == Power.SomTam ? -38f : -8f;
        Init(root, s, new Vector2(x + 0.5f, y + 0.05f), 90, sc);
        Color gc = kind == Power.SomTam ? new Color(0.5f, 1f, 0.4f) : kind == Power.SangSom ? new Color(1f, 0.75f, 0.2f) : kind == Power.Chili ? new Color(1f, 0.35f, 0.2f) : new Color(1f, 0.9f, 0.4f);
        glow = Halo("glow", new Vector3(0, 0.55f, 0.5f), 1.5f, new Color(gc.r, gc.g, gc.b, 0.55f));
        if (kind != Power.Mango)
        {
            bubble = Halo("bubble", new Vector3(0, 0.55f, -0.55f), 1.02f, Color.Lerp(Color.white, gc, 0.35f), 7);
            bubble.sharedMaterial = Art.Normal;
        }
        hw = 0.55f; h = 1.1f;
    }
    public override void Tick(float dt)
    {
        t += dt;
        float bob = Mathf.Sin(t * 2.4f) * 0.1f;
        Sync(dy + bob);
        go.transform.rotation = Quaternion.Euler(tilt, t * 70f, kind == Power.SangSom ? 14f : 0);
        glow.transform.localScale = Vector3.one * (1.5f + Mathf.Sin(t * 5f) * 0.15f);
        glow.transform.position = new Vector3(pos.x, pos.y + 0.55f + bob, 0.5f);
        if (bubble != null) bubble.transform.position = new Vector3(pos.x, pos.y + 0.55f + bob, -0.55f);
        if (!Touch(P, 0)) return;
        var p = P; Vector2 c = pos + Vector2.up * 0.55f;
        switch (kind)
        {
            case Power.SomTam:
                p.Heal(1); p.somtam = Player.SomtamTime;
                Game.I.Banner("SOM TAM!", "Fresh & healthy: +1 heart and DOUBLE JUMP", new Color(0.55f, 1f, 0.45f));
                Fx.Burst("star", c, 20, 7f, 0.7f, 1.3f, new Color(0.6f, 1f, 0.4f), 0, true);
                Sfx.PlayAt(pos.x, "sfx_heal", 0.9f); Sfx.PlayAt(pos.x, "sfx_powerup", 0.7f);
                break;
            case Power.SangSom:
                p.drunk = Player.DrunkTime;
                Game.I.Banner("SANGSOM!", "Sanuk rush: unstoppable for 10 seconds!", new Color(1f, 0.8f, 0.3f));
                Fx.Burst("star", c, 26, 8f, 0.8f, 1.5f, new Color(1f, 0.8f, 0.3f), 0, true);
                Sfx.PlayAt(pos.x, "sfx_powerup", 0.9f, 0.85f); Sfx.PlayAt(pos.x, "sfx_gong", 0.5f, 1.4f);
                break;
            case Power.Chili:
                p.chili = Player.ChiliTime;
                Game.I.Banner("PHRIK!", "Thai chili: press X / J to spit fire", new Color(1f, 0.45f, 0.3f));
                Fx.Burst("star", c, 20, 7f, 0.7f, 1.3f, new Color(1f, 0.5f, 0.2f), 0, true);
                Sfx.PlayAt(pos.x, "sfx_powerup", 0.9f, 1.15f); Sfx.PlayAt(pos.x, "sfx_fire", 0.8f, 0.7f);
                break;
            case Power.Mango:
                p.Heal(1);
                Fx.Burst("star", c, 10, 5f, 0.5f, 1.1f, new Color(1f, 0.9f, 0.4f), 0, true);
                Sfx.PlayAt(pos.x, "sfx_heal", 0.9f);
                break;
        }
        Game.I.FlashScreen(new Color(1, 1, 1, 0.25f));
        Remove();
    }
    public override void Remove()
    {
        if (glow != null) Object.Destroy(glow.gameObject);
        if (bubble != null) Object.Destroy(bubble.gameObject);
        base.Remove();
    }
}

public class Checkpoint : Ent
{
    bool on; int index; Light lamp; Transform root;
    public Checkpoint(Transform root, int x, int y, int index, bool alreadyOn)
    {
        this.root = root; this.index = index; on = alreadyOn;
        pos = new Vector2(x + 0.5f, y);
        Make();
        hw = 0.5f; h = 2f;
    }
    void Make()
    {
        if (rig != null) rig.Destroy();
        rig = Rig.Spawn(on ? "checkpoint_on" : "checkpoint_off", root, new Vector3(pos.x - 0.15f, pos.y, 0.9f), 90, 1f);
        go = rig.root.gameObject;
        if (on)
        {
            lamp = new GameObject("lamp").AddComponent<Light>(); lamp.transform.SetParent(go.transform, false);
            lamp.transform.localPosition = new Vector3(0, 1.7f, -0.5f);
            lamp.type = LightType.Point; lamp.color = new Color(1f, 0.8f, 0.4f); lamp.range = 6f; lamp.intensity = 6f;
        }
    }
    public override void Tick(float dt)
    {
        t += dt;
        rig.Rot("lantern", S(2.2f) * 7f, 0, S(1.7f, 1f) * 5f);
        if (on) { lamp.intensity = 6f + S(9f) * 0.8f; return; }
        if (Touch(P, 0))
        {
            on = true; Make();
            Game.I.SetCheckpoint(index, pos);
            Sfx.PlayAt(pos.x, "sfx_checkpoint", 0.9f);
            Fx.Burst("star", pos + Vector2.up * 1.7f, 14, 5f, 0.7f, 1.2f, new Color(1f, 0.85f, 0.4f), 0, true);
            P.Heal(1);
            Game.I.Banner("CHECKPOINT", "", new Color(1f, 0.9f, 0.5f), 1.2f);
        }
    }
}

public class Goal : Ent
{
    SpriteRenderer rays; bool hit;
    public Goal(Transform root, int x, int y)
    {
        Init(root, "gong", new Vector2(x + 0.5f, y), 90, 1f);
        go.transform.position = new Vector3(pos.x, pos.y, 1.0f);
        hw = 0.7f; h = 3f;
        rays = Halo("rays", new Vector3(0, 1.3f, 0.6f), 2.4f, new Color(1f, 0.85f, 0.4f, 0.4f), -5);
    }
    public override void Tick(float dt)
    {
        t += dt;
        rays.transform.Rotate(0, 0, 18f * dt);
        if (hit) { rig.Rot("gong", Mathf.Sin(t * 9f) * 22f * Mathf.Exp(-t * 0.7f), 0, 0); return; }
        rig.Rot("gong", S(1.3f) * 2f, 0, 0);
        if (Touch(P, 0)) { hit = true; t = 0; Game.I.Win(pos); }
    }
}

public class Drum : Ent
{
    float squashT;
    public Drum(Transform root, int x, int y) { Init(root, "drum", new Vector2(x + 0.5f, y), 90, 0.95f); hw = 0.42f; h = 0.6f; }
    public override void Tick(float dt)
    {
        var p = P;
        squashT = Mathf.Max(0, squashT - dt);
        float k = squashT / 0.3f; float s = 1f - Mathf.Sin(k * Mathf.PI * 2.5f) * 0.3f * k;
        rig.body.localScale = new Vector3(2f - s, s, 2f - s);
        if (Touch(p, 0) && p.vel.y <= 0.1f)
        {
            p.pos.y = pos.y + h; p.Bounce(27f);
            squashT = 0.3f;
            Sfx.PlayAt(pos.x, "sfx_spring", 0.9f);
            Fx.Burst("star", pos + Vector2.up * 0.7f, 8, 5f, 0.4f, 1.1f, new Color(1f, 0.9f, 0.5f), 0, true);
            Fx.Dust(pos + Vector2.up * 0.6f, 5);
        }
    }
}

public class Brazier : Ent
{
    Rig flame; Light lamp; float phase; SpriteRenderer halo;
    const float Off = 1.5f, Warn = 0.6f, On = 1.3f;
    public Brazier(Transform root, int x, int y)
    {
        Init(root, "brazier", new Vector2(x + 0.5f, y), 90, 1f);
        flame = Rig.Spawn("flame", go.transform, new Vector3(pos.x, pos.y + 0.5f, 0), 90, 1f, false);
        lamp = new GameObject("lamp").AddComponent<Light>(); lamp.transform.SetParent(go.transform, false); lamp.transform.localPosition = new Vector3(0, 1.4f, -0.8f);
        lamp.type = LightType.Point; lamp.color = new Color(1f, 0.55f, 0.2f); lamp.range = 7f; lamp.intensity = 0;
        halo = Halo("glow", new Vector3(0, 1.8f, 0.4f), 1f, Color.clear, 7);
        hw = 0.28f; h = 3.2f; phase = (x * 0.37f) % (Off + Warn + On);
    }
    public override void Tick(float dt)
    {
        t += dt;
        float c = (t + phase) % (Off + Warn + On);
        float k;   // flame height 0..1
        if (c < Off) k = 0;
        else if (c < Off + Warn)
        {
            k = 0.12f + Mathf.Abs(Mathf.Sin(t * 25f)) * 0.08f;
            if (Random.value < dt * 20f) Fx.Emit("dust", pos + new Vector2(Random.Range(-0.2f, 0.2f), 0.7f), new Vector2(Random.Range(-0.5f, 0.5f), 2.5f), 0.4f, 0.3f, new Color(1f, 0.6f, 0.15f), 0, true);
        }
        else
        {
            float u = c - Off - Warn;
            k = Mathf.Clamp01(u * 8f) * Mathf.Clamp01((On - u) * 6f);
            if (u < dt) Sfx.PlayAt(pos.x, "sfx_fire", Mathf.Clamp01(1.2f - Mathf.Abs(P.pos.x - pos.x) * 0.08f) * 0.6f, 0.6f);
            if (Random.value < dt * 30f) Fx.Emit("dust", pos + new Vector2(Random.Range(-0.2f, 0.2f), Random.Range(0.8f, 3f)), new Vector2(Random.Range(-0.6f, 0.6f), 3f), 0.4f, 0.3f, new Color(1f, 0.7f, 0.2f), 0, true);
        }
        float wob = 0.9f + 0.12f * Mathf.Sin(t * 31f);
        flame.root.localScale = new Vector3(wob * (0.8f + k * 0.4f), k * 2.9f * (0.95f + 0.06f * Mathf.Sin(t * 23f)), wob * (0.8f + k * 0.4f));
        flame.root.rotation = Quaternion.Euler(Mathf.Sin(t * 17f) * 3f, t * 300f, Mathf.Sin(t * 13f) * 4f);
        lamp.intensity = k * 14f;
        halo.color = new Color(1f, 0.6f, 0.2f, 0.5f * k); halo.transform.localScale = new Vector3(2.6f, 4.2f * Mathf.Max(0.2f, k), 1);
        if (k > 0.6f && Touch(P, 0.02f) && P.pos.y > pos.y - 0.2f) P.Hurt(pos.x);
    }
}

public class Crumble : Ent
{
    public Plat plat; float shake = -1, respawn; Vector2 home; float fallV;
    public Crumble(Transform root, int x, int y)
    {
        Init(root, "crumble", new Vector2(x + 0.5f, y + 1), 90, 1f);
        home = pos;
        plat = new Plat { x0 = x, x1 = x + 1, top = y + 1 };
        plat.onRide = () => { if (shake < 0) { shake = 0; Sfx.PlayAt(pos.x, "sfx_select", 0.5f, 0.6f); } };
    }
    public override void Tick(float dt)
    {
        if (!plat.active)
        {
            respawn -= dt;
            fallV += 30f * dt; pos.y -= fallV * dt;
            go.transform.Rotate(40f * dt, 0, 70f * dt);
            if (respawn <= 0)
            {
                plat.active = true; shake = -1; pos = home; fallV = 0; go.transform.rotation = Quaternion.Euler(0, 90, 0);
                Fx.Burst("dust", home + new Vector2(0, -0.1f), 5, 2f, 0.4f, 0.6f, new Color(1, 1, 1, 0.7f));
            }
            Sync(); return;
        }
        if (shake >= 0)
        {
            shake += dt;
            pos = home + new Vector2(Random.Range(-0.04f, 0.04f), Random.Range(-0.03f, 0.03f));
            if (shake > 0.45f)
            {
                plat.active = false; respawn = 3f; pos = home;
                Sfx.PlayAt(pos.x, "sfx_crumble", 0.8f);
                Fx.Dust(home + new Vector2(0, -0.2f), 5);
            }
        }
        Sync();
    }
}

public class Raft : Ent
{
    public Plat plat; Vector2 a, b; float period;
    public Raft(Transform root, float x, float y, float dx, float dy, float period)
    {
        Init(root, "raft", new Vector2(x, y), 90, 1f);
        a = pos; b = pos + new Vector2(dx, dy); this.period = period;
        plat = new Plat { x0 = x, x1 = x + 3, top = y };
    }
    public override void Tick(float dt)
    {
        t += dt;
        float k = 0.5f - 0.5f * Mathf.Cos(t / period * Mathf.PI);   // ease in/out, there and back in 2*period
        Vector2 np = Vector2.Lerp(a, b, k);
        plat.delta = np - pos; pos = np;
        plat.x0 = pos.x; plat.x1 = pos.x + 3; plat.top = pos.y;
        go.transform.position = new Vector3(pos.x + 1.5f, pos.y, 0);
        go.transform.rotation = Quaternion.Euler(S(1.6f) * 1.2f, 90, S(1.1f, 2f) * 0.8f);
    }
}

// =============================================================== enemies

public abstract class Enemy : Ent
{
    public bool stompable = true, fireproof = false;
    protected Vector2 vel; protected int dir = -1; protected float yaw = 180f;

    protected void Contact()
    {
        var p = P;
        if (!Touch(p)) return;
        if (p.Invincible) { Die(true); return; }
        if (stompable && p.vel.y < 0 && p.prevPos.y > pos.y + h * 0.4f)
        {
            p.pos.y = Mathf.Max(p.pos.y, pos.y + h * 0.6f);
            p.Bounce();
            Die(false);
            return;
        }
        p.Hurt(pos.x);
    }

    public virtual void Die(bool smashed)
    {
        Vector2 c = pos + Vector2.up * h * 0.5f;
        Sfx.PlayAt(pos.x, smashed ? "sfx_poof" : "sfx_stomp", 0.9f);
        Fx.Burst("dust", c, 10, 3.5f, 0.45f, 0.9f, new Color(1, 1, 1, 0.85f));
        Fx.Burst("star", c, 6, 6f, 0.45f, 1.2f, new Color(1f, 0.95f, 0.6f), 0, true);
        Fx.Emit("ui_coin", c, new Vector2(0, 7f), 0.5f, 0.3f, Color.white, -20f, false, 0, 0, false);
        Game.I.Freeze(0.05f); Fx.Shake(0.15f);
        Game.I.AddBonusCoin();
        Remove();
    }

    protected bool Walk(float dt, float speed)
    {
        vel.x = dir * speed;
        vel.y = Mathf.Max(vel.y - 50f * dt, -20f);
        var hit = Level.Move(ref pos, ref vel, hw, h, dt);
        if (hit.wall) dir = -dir;
        else if (hit.ground)
        {
            int ax = Mathf.FloorToInt(pos.x + dir * (hw + 0.15f)), ay = Mathf.FloorToInt(pos.y - 0.5f);
            if (!Level.Solid(ax, ay) && !Level.OneWay(ax, ay)) dir = -dir;
        }
        if (pos.y < 0) Remove();
        return hit.ground;
    }

    /// Smoothly turns the model to face `d` (+1 right / -1 left), angled a little towards the camera.
    protected void Face(int d, float dt, float toCam = 35f)
    {
        float target = d > 0 ? toCam : 180f - toCam;
        yaw = Mathf.LerpAngle(yaw, target, 1f - Mathf.Exp(-12f * dt));
        Yaw(yaw);
    }
}

public class Monkey : Enemy
{
    float hop;
    public Monkey(Transform root, int x, int y, string model = "monkey") { Init(root, model, new Vector2(x + 0.5f, y), 145, 1.05f); hw = 0.4f; h = 1.0f; hop = 1.5f + (x % 3) * 0.5f; }
    public override void Tick(float dt)
    {
        t += dt;
        bool g = Walk(dt, 2.3f);
        hop -= dt;
        if (g && hop <= 0 && Mathf.Abs(P.pos.x - pos.x) < 7f) { vel.y = 11f; hop = 2.2f; }
        if (dead) return;
        Face(dir, dt, 40f);
        float w = Mathf.Sin(t * 11f);
        rig.Rot("body", w * 9f, 0, g ? -4f : 10f);
        rig.Rot("head", -w * 5f, 0, Mathf.Sin(t * 5f) * 4f);
        rig.Rot("armL", 0, 0, g ? w * 38f : 150f); rig.Rot("armR", 0, 0, g ? -w * 38f : 150f);
        rig.Rot("tail", Mathf.Sin(t * 6f) * 14f, 0, Mathf.Sin(t * 4f) * 10f);
        Sync(g ? Mathf.Abs(w) * 0.06f : 0); Contact();
    }
}

public class Crab : Enemy
{
    public Crab(Transform root, int x, int y, string model = "crab") { Init(root, model, new Vector2(x + 0.5f, y), 90, 1.05f); hw = 0.55f; h = 0.75f; }
    public override void Tick(float dt)
    {
        t += dt;
        float c = t % 2.4f; bool moving = c < 1.7f;
        Walk(dt, moving ? 4.2f : 0f);    // scuttle, pause, scuttle
        if (dead) return;
        float w = moving ? Mathf.Sin(t * 26f) : 0;
        rig.Rot("legsL", w * 16f, 0, 0); rig.Rot("legsR", -w * 16f, 0, 0);
        float snap = moving ? 0 : Mathf.Abs(Mathf.Sin(t * 14f)) * 24f;
        rig.Rot("clawL", -10f - snap, 0, 0); rig.Rot("clawR", 10f + snap, 0, 0);
        rig.Rot("body", w * 2f + dir * (moving ? 6f : 0f), 0, 0);
        Sync(moving ? Mathf.Abs(w) * 0.03f : 0); Contact();
    }
}

public class Cobra : Enemy
{
    float cd = 1.5f;
    public Cobra(Transform root, int x, int y, string model = "cobra") { Init(root, model, new Vector2(x + 0.5f, y), 150, 1.05f); hw = 0.42f; h = 1.05f; }
    public override void Tick(float dt)
    {
        t += dt;
        var p = P;
        float dx = p.pos.x - pos.x;
        dir = dx > 0 ? 1 : -1;
        Face(dir, dt, 30f);
        cd -= dt;
        bool near = Mathf.Abs(dx) < 10f && Mathf.Abs(p.pos.y - pos.y) < 5f;
        float wind = (cd < 0.4f && near) ? Mathf.InverseLerp(0.4f, 0f, cd) : 0;         // rear back before spitting
        float lunge = cd > 2.0f ? Mathf.InverseLerp(2.0f, 2.3f, cd) : 0;                 // snap forward just after
        rig.Rot("neck", Mathf.Sin(t * 2.2f) * 7f, 0, wind * 16f - lunge * 26f + Mathf.Sin(t * 1.6f) * 3f);
        rig.Rot("head", 0, 0, -wind * 18f + lunge * 10f);
        var tg = rig.J("tongue"); if (tg != null) tg.localScale = Vector3.one * (Mathf.Sin(t * 5f) > 0.3f ? 1f : 0.01f);
        if (cd <= 0)
        {
            cd = 2.3f;
            if (near)
            {
                Game.I.Add(new Venom(Game.I.world, pos + new Vector2(dir * 0.5f, 0.95f), new Vector2(dir * 7.5f, 2.5f)));
                Sfx.PlayAt(pos.x, "sfx_poof", 0.5f, 1.6f);
            }
        }
        Contact();
    }
}

public class Mosquito : Enemy
{
    Vector2 home; float ph;
    public Mosquito(Transform root, int x, int y, string model = "mosquito") { Init(root, model, new Vector2(x + 0.5f, y), 150, 0.95f); home = pos; hw = 0.45f; h = 0.7f; ph = x * 1.3f; }
    public override void Tick(float dt)
    {
        t += dt;
        float px = pos.x;
        pos = home + new Vector2(Mathf.Sin(t * 1.3f + ph) * 2f, Mathf.Sin(t * 2.9f + ph) * 0.55f);
        Face(pos.x < px ? -1 : 1, dt, 25f);
        float f = Mathf.Sin(t * 70f) * 38f;
        rig.Rot("wingL", f + 10f, 0, 0); rig.Rot("wingR", -f - 10f, 0, 0);
        rig.Rot("body", 0, 0, -12f + Mathf.Sin(t * 2.9f + ph) * 8f);
        Sync(-0.1f); Contact();
    }
}

public class Durian : Enemy
{
    Vector2 home; int state; float st, spin;
    public Durian(Transform root, int x, int y, string model = "durian")
    {
        Init(root, model, new Vector2(x + 0.5f, y), 90, 0.95f);
        home = pos; hw = 0.5f; h = 1.15f; stompable = false; fireproof = true;
        if (rig.J("face") != null) rig.J("face").localScale = Vector3.one * 0.001f;
    }
    public override void Tick(float dt)
    {
        t += dt; st += dt;
        var p = P;
        Vector2 off = Vector2.zero;
        float face = state == 0 || state == 4 ? 0.001f : 1f;
        switch (state)
        {
            case 0:   // hanging, waiting
                off.y = Mathf.Sin(t * 2f) * 0.05f;
                if (Mathf.Abs(p.pos.x - pos.x) < 1.7f && p.pos.y < pos.y) { state = 1; st = 0; Sfx.PlayAt(pos.x, "sfx_select", 0.7f, 0.5f); }
                break;
            case 1:   // angry shake
                off = new Vector2(Random.Range(-0.07f, 0.07f), Random.Range(-0.04f, 0.04f));
                if (st > 0.4f) { state = 2; vel = Vector2.zero; }
                break;
            case 2:   // drop
                vel.y = Mathf.Max(vel.y - 55f * dt, -22f);
                var hit = Level.Move(ref pos, ref vel, hw, h, dt);
                if (hit.ground) { state = 3; st = 0; Fx.Shake(0.3f); Fx.Dust(pos, 8); Sfx.PlayAt(pos.x, "sfx_crumble", 0.8f, 0.7f); }
                if (pos.y < 0) { state = 4; }
                break;
            case 3:   // rest
                if (st > 0.9f) state = 4;
                break;
            case 4:   // rise back
                pos.y = Mathf.MoveTowards(pos.y, home.y, 3.2f * dt);
                spin += dt * 120f;
                if (pos.y >= home.y) state = 0;
                break;
        }
        var fj = rig.J("face"); if (fj != null) fj.localScale = Vector3.Lerp(fj.localScale, Vector3.one * face, 1f - Mathf.Exp(-20f * dt));
        go.transform.position = new Vector3(pos.x + off.x, pos.y + off.y, 0);
        go.transform.rotation = Quaternion.Euler(0, 90 + Mathf.Sin(spin * 0.05f) * 12f, state == 3 ? Mathf.Sin(st * 30f) * 4f * (1 - st) : 0);
        float sq = state == 3 ? 1f - Mathf.Sin(Mathf.Clamp01(st * 4f) * Mathf.PI) * 0.2f : 1f;
        rig.body.localScale = new Vector3(2f - sq, sq, 2f - sq);
        Contact();
    }
}

public class Ghost : Enemy
{
    float mood;
    public Ghost(Transform root, int x, int y, string model = "ghost") { Init(root, model, new Vector2(x + 0.5f, y), 150, 1.0f); hw = 0.4f; h = 1.2f; stompable = false; rig.OwnMaterials(); }
    public override void Tick(float dt)
    {
        t += dt;
        var p = P;
        Vector2 to = (p.pos + Vector2.up * 0.4f) - pos;
        bool watched = (to.x > 0) == (p.facing < 0);       // Nam is looking at the ghost -> it freezes and hides its face
        bool chase = to.magnitude < 13f && !watched;
        if (chase) pos += to.normalized * 2.7f * dt;
        mood = Mathf.MoveTowards(mood, chase ? 1 : 0, dt * 5f);
        Face(to.x > 0 ? 1 : -1, dt, 35f);
        rig.Tint(Color.Lerp(new Color(0.55f, 0.62f, 0.8f), Color.white, mood), new Color(0.25f, 0.1f, 0.35f) * mood * (0.6f + 0.4f * Mathf.Sin(t * 8f)));
        rig.Rot("armL", 0, 0, Mathf.Lerp(-75f, 55f + Mathf.Sin(t * 7f) * 15f, mood)); rig.Rot("armR", 0, 0, Mathf.Lerp(-75f, 55f - Mathf.Sin(t * 7f) * 15f, mood));
        rig.Rot("head", Mathf.Sin(t * 3f) * 6f * mood, 0, Mathf.Lerp(28f, -6f, mood));
        rig.Rot("body", 0, 0, -10f * mood);
        Sync(Mathf.Sin(t * 2.5f) * 0.1f); Contact();
    }
}

/// One of Nam's friends at the restaurant: waves, bounces and cheers when she arrives.
public class Friend : Ent
{
    int face; float ph; public static bool Cheering;
    public Friend(Transform root, string model, float x, float y, float z, int face)
    {
        pos = new Vector2(x + 0.5f, y); this.face = face; ph = x * 1.7f;
        rig = Rig.Spawn(model, root, new Vector3(pos.x, pos.y, z), face > 0 ? 40f : 140f, 1f);
        go = rig.root.gameObject;
    }
    public override void Tick(float dt)
    {
        t += dt;
        float w = Mathf.Sin(t * 9f + ph), hop = Cheering ? Mathf.Abs(Mathf.Sin(t * 5.5f + ph)) * 0.32f : Mathf.Abs(Mathf.Sin(t * 2.2f + ph)) * 0.04f;
        var p = go.transform.position; go.transform.position = new Vector3(p.x, pos.y + hop, p.z);
        float look = P.pos.x > pos.x ? 55f : 125f;
        go.transform.rotation = Quaternion.Slerp(go.transform.rotation, Quaternion.Euler(0, Cheering ? 78f : look, 0), 1f - Mathf.Exp(-6f * dt));
        // one arm waves out to the side; both go up when cheering
        rig.Rot("armR", 104 + w * 8f, 0, 30); rig.Rot("foreR", 55 + w * 32f, 0, 0);
        if (Cheering) { rig.Rot("armL", -104 - w * 8f, 0, 30); rig.Rot("foreL", -55 + w * 32f, 0, 0); }
        else { rig.Rot("armL", -8, 0, 6 + w * 3f); rig.Rot("foreL", 0, 0, 16); }
        rig.Rot("head", w * 4f, 0, Cheering ? -8f : 0); rig.Rot("torso", w * 2f, 0, 0);
        rig.Rot("legL", 0, 0, Cheering ? hop * 60f : 0); rig.Rot("legR", 0, 0, Cheering ? -hop * 40f : 0);
    }
}

// =============================================================== projectiles

public class Venom : Ent
{
    Vector2 vel;
    public Venom(Transform root, Vector2 p, Vector2 v) { Init(root, "venom", p, v.x > 0 ? 0 : 180, 0.9f); vel = v; hw = 0.18f; h = 0.3f; }
    public override void Tick(float dt)
    {
        t += dt;
        vel.y -= 9f * dt;
        pos += vel * dt;
        go.transform.position = new Vector3(pos.x, pos.y, 0);
        go.transform.rotation = Quaternion.Euler(0, vel.x > 0 ? 0 : 180, Mathf.Atan2(vel.y, Mathf.Abs(vel.x)) * Mathf.Rad2Deg);
        bool gone = t > 4f || Level.Solid(Mathf.FloorToInt(pos.x), Mathf.FloorToInt(pos.y));
        var p = P;
        if (!p.deadState && Mathf.Abs(p.pos.x - pos.x) < p.hw + hw && pos.y > p.pos.y && pos.y < p.pos.y + p.h) { p.Hurt(pos.x - vel.x); gone = true; }
        if (gone) { Fx.Burst("dust", pos, 5, 2.5f, 0.3f, 0.4f, new Color(0.6f, 1f, 0.3f, 0.9f)); Remove(); }
    }
}

public class Fireball : Ent
{
    Vector2 vel; Light lamp; int d;
    public Fireball(Transform root, Vector2 p, int dir)
    {
        Init(root, "fireball", p, dir > 0 ? 0 : 180, 0.85f);
        foreach (var r in go.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        lamp = go.AddComponent<Light>(); lamp.type = LightType.Point; lamp.color = new Color(1f, 0.55f, 0.15f); lamp.range = 5f; lamp.intensity = 8f;
        vel = new Vector2(dir * 15f, -3f); hw = 0.22f; h = 0.44f; d = dir;
        pos.y -= 0.22f;
    }
    public override void Tick(float dt)
    {
        t += dt;
        vel.y = Mathf.Max(vel.y - 48f * dt, -16f);
        var hit = Level.Move(ref pos, ref vel, hw, h, dt);
        if (hit.ground) vel.y = 9.5f;                       // bounce along the ground
        go.transform.position = new Vector3(pos.x, pos.y + 0.22f, 0);
        go.transform.rotation = Quaternion.Euler(t * 900f, d > 0 ? 0 : 180, Mathf.Atan2(vel.y, Mathf.Abs(vel.x)) * Mathf.Rad2Deg * 0.6f);
        if (Random.value < dt * 40f) Fx.Emit("dust", pos + Vector2.up * 0.2f, Random.insideUnitCircle * 0.5f, 0.3f, 0.35f, new Color(1f, Random.Range(0.4f, 0.8f), 0.1f), 0, true);
        bool gone = hit.wall || t > 2.2f || pos.y < 0.5f;
        foreach (var e in Game.I.ents)
        {
            if (e.dead || !(e is Enemy en)) continue;
            if (Mathf.Abs(en.pos.x - pos.x) < en.hw + hw && pos.y < en.pos.y + en.h && pos.y + h > en.pos.y)
            {
                if (!en.fireproof) en.Die(true);
                gone = true; break;
            }
        }
        if (gone)
        {
            Fx.Burst("dust", pos + Vector2.up * 0.2f, 8, 4f, 0.35f, 0.5f, new Color(1f, 0.6f, 0.15f), 0, true);
            Remove();
        }
    }
}
