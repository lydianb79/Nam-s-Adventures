using UnityEngine;

/// Nam: tight platformer controller (coyote time, jump buffering, variable jump height, run button, duck / slide)
/// plus the three power-ups:
///   Som Tam  -> heals a heart and grants a mid-air double jump
///   Chili    -> spit bouncing fireballs
///   SangSom  -> "sanuk" rush: invincible, faster, higher jumps, smashes enemies on contact
///
/// Animation is fully procedural. Every state (idle, run, air, skid, duck, slide, hurt) is a continuous pose
/// function; the final pose is a weighted blend whose weights are spring-smoothed, so there is never a pop
/// between states. Stride phase advances with distance travelled, so feet do not slide.
public class Player
{
    public Vector2 pos, vel, prevPos;
    public float hw = 0.3f, h = StandH;
    const float StandH = 1.45f, DuckH = 0.85f;
    public int facing = 1;
    public bool grounded, deadState, winState, ducking;
    public int hearts = 3;
    public const int MaxHearts = 3;
    public float invuln;
    public float somtam, chili, drunk;           // remaining power-up seconds
    public const float SomtamTime = 20f, ChiliTime = 16f, DrunkTime = 10f;
    public Plat rider;
    public float titlePose;     // 1 = stand facing the camera (title screen)

    public Rig rig; GameObject go; SpriteRenderer glow;
    float coyote, buffer, animT, fireCd, deadT, trailT, yaw = 25f, yawV, hairA, hairV, blinkT, dropT, maxSpeed = 6.6f, maxSpeedV;
    int airJumps; bool springing, wasGrounded;

    // ---- animation state
    const int N = 13;                                   // legL shinL legR shinR armL foreL armR foreR torso head twist roll hipY
    enum S { Idle, Run, Air, Skid, Duck, Slide, Hurt, Push, Count }
    readonly float[] w = new float[(int)S.Count], wv = new float[(int)S.Count], wt = new float[(int)S.Count];
    readonly float[] pose = new float[N], tmp = new float[N];
    float stride, sqY = 1f, sqV, land, landV, accelLean, accelLeanV, lastVx, speedSm, speedSmV, vySm, vySmV, wave, waveV;
    int lastStep;
    float hair2A, hair2V, flip, idleT, fidget = -1f, bagA, bagV, mouthO, mouthOV, browUp, browUpV; Vector2 look, lookV; bool pushing;

    public Player(Transform root, Vector2 start)
    {
        rig = Rig.Spawn("nam", root, start, 25f, 1f);
        rig.OwnMaterials();
        go = rig.root.gameObject;
        glow = Art.Make("glow", root, Vector2.zero, 9, 0.5f, 0.5f, true);
        glow.transform.localScale = Vector3.one * 1.7f; glow.color = Color.clear;
        pos = prevPos = start; w[(int)S.Idle] = 1;
        var ej = rig.J("eyes"); if (ej != null) eyeRest = ej.localPosition;
        var bj = rig.J("brows"); if (bj != null) browRest = bj.localPosition;
        var mo = rig.J("mouthO"); if (mo != null) mo.localScale = Vector3.one * 0.001f;
        Sync();
    }

    public Vector2 Center => pos + new Vector2(0, h * 0.5f);
    public bool Invincible => drunk > 0;

    bool CanStand()
    {
        int x0 = Mathf.FloorToInt(pos.x - hw + 0.01f), x1 = Mathf.FloorToInt(pos.x + hw - 0.01f);
        for (int x = x0; x <= x1; x++)
            if (Level.Solid(x, Mathf.FloorToInt(pos.y + StandH - 0.01f)) || Level.Solid(x, Mathf.FloorToInt(pos.y + DuckH + 0.05f))) return false;
        return true;
    }

    bool OnOneWay()
    {
        int x0 = Mathf.FloorToInt(pos.x - hw + 0.01f), x1 = Mathf.FloorToInt(pos.x + hw - 0.01f), y = Mathf.FloorToInt(pos.y - 0.5f);
        bool any = false;
        for (int x = x0; x <= x1; x++) { if (Level.Solid(x, y)) return false; any |= Level.OneWay(x, y); }
        return any;
    }

    public void Tick(float dt)
    {
        prevPos = pos;
        if (deadState) { TickDead(dt); return; }
        if (winState) { TickWin(dt); return; }

        // ---- timers ----
        invuln = Mathf.Max(0, invuln - dt);
        somtam = Mathf.Max(0, somtam - dt);
        chili = Mathf.Max(0, chili - dt);
        if (drunk > 0) { drunk -= dt; if (drunk <= 0) { drunk = 0; invuln = 1.2f; } }
        fireCd -= dt; buffer -= dt; coyote -= dt; dropT -= dt;
        if (In.JumpDown) buffer = 0.13f;

        // ---- ride moving platforms ----
        if (rider != null)
        {
            if (!rider.active) rider = null;
            else pos += rider.delta;
        }

        // ---- duck: hold down on the ground; stays down while there is no headroom ----
        bool wantDuck = In.Down && grounded && titlePose < 0.5f;
        bool duck = wantDuck || (ducking && !CanStand());
        if (duck != ducking)
        {
            ducking = duck; h = ducking ? DuckH : StandH;
            if (ducking) { sqV -= 2.2f; if (Mathf.Abs(vel.x) > 3.2f) { Sfx.Play("sfx_poof", 0.35f, 1.5f); Fx.Dust(pos, 4, Mathf.Sign(vel.x)); } }
            else sqV += 1.6f;
        }
        bool sliding = ducking && grounded && Mathf.Abs(vel.x) > 3.0f;

        // ---- horizontal ----
        float boost = drunk > 0 ? 1.3f : 1f;
        maxSpeed = Mathf.SmoothDamp(maxSpeed, (In.Run ? 10f : 6.6f) * boost, ref maxSpeedV, 0.12f, 100f, dt);      // run speed eases in and out
        float target = In.X * (ducking ? 2.6f : maxSpeed);
        float acc;
        if (!grounded) acc = 38f;
        else if (sliding) acc = 9f;                                                                                // a duck at speed becomes a slide
        else if (Mathf.Abs(target) < 0.01f) acc = 60f;
        else acc = (Mathf.Sign(target) != Mathf.Sign(vel.x) && Mathf.Abs(vel.x) > 0.5f) ? 85f : 55f;
        vel.x = Mathf.MoveTowards(vel.x, target, acc * dt);
        if (In.X != 0 && !sliding) facing = In.X > 0 ? 1 : -1;

        // ---- jump (or drop through a bamboo platform when ducking) ----
        if (buffer > 0)
        {
            if (ducking && grounded && OnOneWay()) { dropT = 0.18f; buffer = 0; coyote = 0; pos.y -= 0.03f; grounded = false; }
            else if (coyote > 0 && (!ducking || CanStand()))
            {
                vel.y = (17.2f + Mathf.Abs(vel.x) * 0.1f) * (drunk > 0 ? 1.08f : 1f);
                buffer = 0; coyote = 0; springing = false; grounded = false; rider = null;
                sqY = 1.16f; sqV = 3.5f;
                Sfx.Play("sfx_jump", 0.6f);
                Fx.Dust(pos, 5);
            }
            else if (somtam > 0 && airJumps > 0 && !grounded)
            {
                airJumps--; vel.y = 15.5f; buffer = 0; springing = false;
                sqY = 1.16f; sqV = 3.5f; flip = 1f;                    // somersault
                Sfx.Play("sfx_jump2", 0.7f);
                Fx.Burst("star", pos, 10, 4f, 0.5f, 1.2f, new Color(0.6f, 1f, 0.5f), 0, true);
                Fx.Burst("dust", pos, 6, 2.5f, 0.4f, 0.6f, new Color(0.8f, 1f, 0.7f, 0.8f));
            }
        }

        // ---- gravity (short hop when the button is released early) ----
        float gr = vel.y > 0 ? ((In.JumpHeld || springing) ? 42f : 110f) : 62f;
        vel.y = Mathf.Max(vel.y - gr * dt, -24f);

        // ---- fireballs ----
        if (chili > 0 && In.FireDown && fireCd <= 0)
        {
            fireCd = 0.22f;
            Game.I.Add(new Fireball(Game.I.world, pos + new Vector2(facing * 0.5f, ducking ? 0.5f : 0.85f), facing));
            Sfx.Play("sfx_fire", 0.7f);
            sqV -= 1.2f;
        }

        // ---- move & collide ----
        float oldY = pos.y; float vyBefore = vel.y;
        var hit = Level.Move(ref pos, ref vel, hw, h, dt, dropT > 0);
        bool onGround = hit.ground;
        Plat landed = null;
        if (vyBefore <= 0 && !onGround)
        {
            foreach (var pl in Game.I.plats)
            {
                if (!pl.active) continue;
                if (pos.x + hw < pl.x0 || pos.x - hw > pl.x1) continue;
                if (oldY >= pl.top - 0.05f && pos.y <= pl.top)
                { pos.y = pl.top; vel.y = 0; onGround = true; landed = pl; break; }
            }
        }
        rider = landed;
        if (landed != null) landed.OnRide();
        if (hit.ceil) Sfx.Play("sfx_select", 0.5f, 0.7f);
        pushing = hit.wall && In.X != 0 && onGround && !ducking;

        if (onGround)
        {
            if (!wasGrounded && vyBefore < -6f)
            {
                float impact = Mathf.InverseLerp(6f, 24f, -vyBefore);
                landV += 9f + impact * 9f;                    // knees absorb the landing
                Sfx.Play("sfx_land", 0.3f + impact * 0.5f, 1.1f - impact * 0.25f);
                sqV -= 1.5f + impact * 2.5f;
                Fx.Dust(pos, 4 + (int)(impact * 4));
                for (int i = -1; i <= 1; i += 2) for (int k = 0; k < 3; k++)          // a low ring of dust skims outwards
                    Fx.Emit("dust", pos + new Vector2(i * 0.15f, 0.06f), new Vector2(i * (2.5f + k * 1.6f + impact * 3f), 0.25f), 0.3f + k * 0.06f, 0.45f, new Color(0.8f, 0.78f, 0.7f, 0.45f), 0, false, 0, 4f);
                flip = 0;
            }
            coyote = 0.1f; airJumps = 1; springing = false;
        }
        grounded = onGround; wasGrounded = onGround;

        // ---- hazards ----
        if (pos.y < Level.WaterLine - 0.5f)
        {
            Fx.Burst("dust", new Vector2(pos.x, Level.WaterLine), 16, 5f, 0.7f, 0.8f, new Color(0.7f, 0.93f, 1f, 0.9f), -12f, false, 5f);
            Sfx.Play("sfx_splash", 0.9f);
            Die();
            return;
        }
        int sx0 = Mathf.FloorToInt(pos.x - hw + 0.08f), sx1 = Mathf.FloorToInt(pos.x + hw - 0.08f), sy = Mathf.FloorToInt(pos.y + 0.02f);
        for (int x = sx0; x <= sx1; x++)
            if (Level.At(x, sy) == '^' && pos.y - sy < 0.5f) { Hurt(x + 0.5f, true); break; }

        Animate(dt);
        Sync();
    }

    // =================================================================== animation
    // Joint frame: +X forward, +Y up; a positive angle swings a hanging limb forward, a negative knee angle bends it.

    static void Set(float[] p, float legL, float shinL, float legR, float shinR, float armL, float foreL, float armR, float foreR, float torso, float head, float twist = 0, float roll = 0, float hipY = 0)
    {
        p[0] = legL; p[1] = shinL; p[2] = legR; p[3] = shinR; p[4] = armL; p[5] = foreL; p[6] = armR; p[7] = foreR; p[8] = torso; p[9] = head; p[10] = twist; p[11] = roll; p[12] = hipY;
    }

    static float Ease(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }

    void Add(S s)
    {
        float k = w[(int)s];
        if (k <= 0.0005f) return;
        for (int i = 0; i < N; i++) pose[i] += tmp[i] * k;
    }

    void Animate(float dt)
    {
        animT += dt;
        float t = animT;
        float speed = Mathf.Abs(vel.x);
        speedSm = Mathf.SmoothDamp(speedSm, speed, ref speedSmV, 0.07f, 1000f, dt);
        vySm = Mathf.SmoothDamp(vySm, vel.y, ref vySmV, 0.05f, 1000f, dt);
        bool hurt = invuln > 1.25f && !Invincible;
        bool skid = grounded && !ducking && In.X != 0 && Mathf.Sign(In.X) != Mathf.Sign(vel.x) && speed > 2.5f;
        bool slide = ducking && grounded && speed > 3.0f;

        // ---- which states are active (targets), then spring the weights towards them
        for (int i = 0; i < wt.Length; i++) wt[i] = 0;
        float mv = Ease(speedSm / 1.6f);
        if (hurt) wt[(int)S.Hurt] = 1;
        else if (!grounded) wt[(int)S.Air] = 1;
        else if (slide) wt[(int)S.Slide] = 1;
        else if (ducking) wt[(int)S.Duck] = 1;
        else if (skid) wt[(int)S.Skid] = 1;
        else if (pushing) wt[(int)S.Push] = 1;
        else { wt[(int)S.Run] = mv; wt[(int)S.Idle] = 1 - mv; }
        float sum = 0;
        for (int i = 0; i < w.Length; i++)
        {
            float st = i == (int)S.Hurt ? 0.045f : i == (int)S.Air ? 0.075f : (i == (int)S.Duck || i == (int)S.Slide) ? 0.085f : 0.1f;
            w[i] = Mathf.Clamp01(Mathf.SmoothDamp(w[i], wt[i], ref wv[i], st, 1000f, dt)); sum += w[i];
        }
        if (sum < 0.001f) { w[(int)S.Idle] = 1; sum = 1; }
        for (int i = 0; i < w.Length; i++) w[i] /= sum;
        for (int i = 0; i < N; i++) pose[i] = 0;

        // ---- idle: breathing, a slow weight shift, the head drifting around
        float br = Mathf.Sin(t * 2.2f), sway = Mathf.Sin(t * 0.8f);
        Set(tmp, 3 + sway * 1.5f, -4 - sway, -3 + sway * 1.5f, -4 + sway, 5 + br * 3, 15 + br * 2, -5 - br * 3, 15 - br * 2, br * 1.6f, Mathf.Sin(t * 0.9f) * 4f - br, Mathf.Sin(t * 0.55f) * 5f, sway * 2.2f, br * 0.012f);
        Add(S.Idle);

        // ---- walk / run: phase follows the ground covered, so the stride matches the speed
        float r = Mathf.Clamp01(speedSm / 10f);
        if (grounded) stride += speed * dt / Mathf.Lerp(0.5f, 1.0f, r) * Mathf.PI * 0.5f + dt * 1.2f * mv;
        float s = Mathf.Sin(stride), c = Mathf.Cos(stride);
        // a footstep each time a foot comes down, voiced for the ground she is on
        int stepNow = Mathf.FloorToInt(stride / Mathf.PI);
        if (stepNow != lastStep)
        {
            lastStep = stepNow;
            if (grounded && !ducking && speedSm > 1.6f && titlePose < 0.5f)
            {
                string top = Game.I.theme != null ? Game.I.theme.S("top", "grass") : "grass";
                string snd = top == "wood" ? "sfx_step_wood" : (top == "stone" || top == "tile" || top == "gravel") ? "sfx_step_hard" : "sfx_step_soft";
                Sfx.Play(snd, Mathf.Lerp(0.16f, 0.34f, r), Mathf.Lerp(0.9f, 1.12f, r), 0.09f, (stepNow & 1) == 0 ? -0.12f : 0.12f);
            }
        }
        float A = Mathf.Lerp(22f, 54f, r), K = Mathf.Lerp(34f, 104f, r);
        float kneeL = Mathf.Pow(0.5f + 0.5f * Mathf.Cos(stride - 0.75f), 1.6f), kneeR = Mathf.Pow(0.5f - 0.5f * Mathf.Cos(stride - 0.75f), 1.6f);
        float armA = Mathf.Lerp(20f, 64f, r);
        Set(tmp, s * A + r * 8, -7 - K * kneeL, -s * A + r * 8, -7 - K * kneeR,
            -s * armA + 4, Mathf.Lerp(18, 72, r) - s * 12, s * armA + 4, Mathf.Lerp(18, 72, r) + s * 12,
            -4 - r * 15, 2 + r * 9 + Mathf.Cos(stride * 2) * 1.5f, s * Mathf.Lerp(6, 15, r), c * Mathf.Lerp(1.5f, 4f, r), Mathf.Cos(stride * 2) * Mathf.Lerp(0.014f, 0.05f, r));
        Add(S.Run);
        if (w[(int)S.Run] > 0.5f && speed > 7f && Mathf.Floor((stride - speed * dt * 2f) / Mathf.PI) != Mathf.Floor(stride / Mathf.PI)) Fx.Dust(pos, 1, Mathf.Sign(vel.x));

        // ---- air: one continuous pose driven by vertical speed (leap -> tuck at the apex -> reach for the ground)
        float u = Mathf.Clamp(vySm / 17f, -1.3f, 1.2f), fl = Mathf.Sin(t * 13f);
        float up = Ease(u / 0.7f), dn = Ease(-u / 0.8f);
        float tw = 1 - up - dn;
        Set(tmp, 48 * up + 34 * tw + (16 + fl * 6) * dn, -86 * up - 74 * tw - 28 * dn, -24 * up + 6 * tw + (-16 - fl * 6) * dn, -30 * up - 62 * tw - 44 * dn,
            166 * up + 118 * tw + (132 + fl * 12) * dn, 12 * up + 34 * tw + 16 * dn, -40 * up + 96 * tw + (146 - fl * 12) * dn, 36 * up + 34 * tw + 16 * dn,
            -7 * up - 2 * tw + 7 * dn, -10 * up + 2 * tw + 9 * dn, 0, 0, 0.02f * tw);
        Add(S.Air);

        // ---- skid: heels dug in, leaning back against the motion
        Set(tmp, 44, -8, 24, -56, 62, 40, -50, 30, 21, 6, 0, 0, -0.03f);
        Add(S.Skid);
        if (skid && Random.value < 0.5f) Fx.Dust(pos, 1, Mathf.Sign(vel.x));

        // ---- duck: a deep squat hugging the knees, shuffling when she creeps along
        float sh = Mathf.Sin(stride * 2f) * Mathf.Clamp01(speed / 2.6f);
        Set(tmp, 100 + sh * 10, -134 - sh * 8, 92 - sh * 10, -128 + sh * 8, 58 - sh * 8, 62, 50 + sh * 8, 66, -44 + br * 1.5f, 36, sh * 5, 0, -0.275f + br * 0.006f);
        Add(S.Duck);

        // ---- slide: low, front leg out, trailing arm up for balance
        Set(tmp, 78, -14, 104, -138, -34, 26, 112, 30, 26, -16, 0, 0, -0.31f);
        Add(S.Slide);
        if (slide && Random.value < dt * 40f) Fx.Dust(pos + Vector2.right * Mathf.Sign(vel.x) * 0.3f, 1, Mathf.Sign(vel.x));

        // ---- push: leaning into a wall with both hands, feet working
        float ps = Mathf.Sin(t * 9f);
        Set(tmp, 30 + ps * 20, -18 - Mathf.Max(0, ps) * 30, -34 - ps * 20, -20 - Mathf.Max(0, -ps) * 30, 82, 28 + ps * 6, 78, 30 - ps * 6, -26, 14, 0, 0, -0.03f + Mathf.Abs(ps) * 0.012f);
        Add(S.Push);

        // ---- hurt: thrown back, arms flailing
        float hf = Mathf.Sin(t * 30f);
        Set(tmp, 36, -50, -26, -40, 150 + hf * 24, 30, 160 - hf * 24, 30, 22, 18, 0, 0, 0);
        Add(S.Hurt);

        // ---- additive layers: landing crouch, leaning into acceleration, the title-screen wave
        landV += (-land * 260f - landV * 22f) * dt; land += landV * dt;                   // damped spring, tiny rebound
        float lk = Mathf.Clamp(land, -0.3f, 1.2f) * (1 - w[(int)S.Duck] - w[(int)S.Slide]);
        pose[0] += 30 * lk; pose[1] -= 56 * lk; pose[2] += 26 * lk; pose[3] -= 52 * lk; pose[8] -= 9 * lk; pose[9] += 6 * lk; pose[12] -= 0.13f * lk;
        pose[4] += 18 * lk; pose[6] += 18 * lk;
        float ax = dt > 0 ? (vel.x - lastVx) / dt * facing : 0; lastVx = vel.x;
        accelLean = Mathf.SmoothDamp(accelLean, Mathf.Clamp(grounded ? ax * 0.16f : 0, -9f, 9f), ref accelLeanV, 0.12f, 1000f, dt);
        pose[8] -= accelLean * (w[(int)S.Run] + w[(int)S.Idle]);
        wave = Mathf.SmoothDamp(wave, titlePose > 0.5f && grounded ? 1 : 0, ref waveV, 0.15f, 1000f, dt);
        if (wave > 0.001f)
        {
            pose[11] += Mathf.Sin(t * 1.1f) * 2f * wave;
        }

        // idle fidget: after a while she looks around and pushes her glasses up
        bool calm = w[(int)S.Idle] > 0.95f && titlePose < 0.5f;
        idleT = calm ? idleT + dt : 0;
        if (calm && fidget < 0 && idleT > 5.5f) { fidget = 0; idleT = Random.Range(-3f, 0f); }
        if (fidget >= 0)
        {
            fidget += dt / 2.2f;
            float fk = Mathf.Sin(Mathf.Clamp01(fidget) * Mathf.PI); fk = fk * fk * (3 - 2 * fk);
            if (!calm || fidget >= 1) fidget = -1;
            else
            {
                pose[6] = Mathf.Lerp(pose[6], 118 + Mathf.Sin(t * 14f) * 4f, fk); pose[7] = Mathf.Lerp(pose[7], 112, fk);
                pose[10] += Mathf.Sin(fidget * Mathf.PI * 2f) * 16f * fk; pose[9] += 5f * fk;
            }
        }

        // ---- apply
        rig.Rot("legL", 0, 0, pose[0]); rig.Rot("shinL", 0, 0, Mathf.Min(0, pose[1])); rig.Rot("legR", 0, 0, pose[2]); rig.Rot("shinR", 0, 0, Mathf.Min(0, pose[3]));
        rig.Rot("armL", -6, 0, pose[4]); rig.Rot("foreL", 0, 0, Mathf.Max(0, pose[5])); rig.Rot("armR", 6, 0, pose[6]); rig.Rot("foreR", 0, 0, Mathf.Max(0, pose[7]));
        if (wave > 0.001f)
        {   // title-screen wave: the arm goes up and out to her side (not towards the camera), hand swinging from the elbow
            float ws = Mathf.Sin(t * 8f);
            rig.Rot("armR", 102 + ws * 6f, 0, 34, wave); rig.Rot("foreR", 58 + ws * 30f, 0, 0, wave);      // elbow out wide, forearm up, clear of her hair
            rig.Rot("armL", -14, 0, pose[4], wave * 0.6f);
        }
        rig.Rot("torso", pose[11], pose[10], pose[8]); rig.Rot("head", -pose[11] * 0.5f, -pose[10] * 0.6f, pose[9]);
        var hips = rig.J("hips"); if (hips != null) hips.localPosition = new Vector3(hips.localPosition.x, 0.52f + pose[12], hips.localPosition.z);

        // ---- hair: a spring that trails behind movement and bounces with the stride
        float want = Mathf.Clamp(-speedSm * 3.2f + Mathf.Clamp(vySm, -20, 12) * 1.6f, -42f, 14f) - Mathf.Cos(stride * 2) * 3f * w[(int)S.Run] + pose[8] * -0.5f;
        hairV += ((want - hairA) * 80f - hairV * 10f) * dt; hairA += hairV * dt;
        rig.Rot("pony", 0, 0, hairA);
        float want2 = (hairA - want) * 0.6f + hairV * 0.045f + Mathf.Clamp(-speedSm * 2.2f + Mathf.Clamp(vySm, -22, 10) * 1.8f, -40f, 16f);      // the lengths lag the roots
        hair2V += ((want2 - hair2A) * 60f - hair2V * 7.5f) * dt; hair2A += hair2V * dt;
        rig.Rot("pony2", 0, 0, Mathf.Clamp(hair2A, -70f, 40f));
        // shoulder bag bounces on its strap
        bagV += ((-vySm * 1.4f - Mathf.Cos(stride * 2) * 9f * w[(int)S.Run] - bagA) * 120f - bagV * 12f) * dt; bagA += bagV * dt;
        rig.Rot("bag", Mathf.Clamp(bagA, -30f, 30f), 0, Mathf.Clamp(-accelLean * 1.5f, -14f, 14f));

        // ---- face: eyes glance where she is heading, brows lift and the mouth rounds when airborne or hurt
        Vector2 wantLook = new Vector2(Mathf.Clamp(vySm * 0.0011f, -0.014f, 0.014f) + (fidget >= 0 ? 0.004f : 0), w[(int)S.Idle] > 0.6f ? -0.012f * Mathf.Sin(t * 0.4f) : 0);
        look = Vector2.SmoothDamp(look, wantLook, ref lookV, 0.12f, 10f, dt);
        var eyes = rig.J("eyes"); if (eyes != null) eyes.localPosition = eyeRest + new Vector3(0, look.x, look.y);
        mouthO = Mathf.SmoothDamp(mouthO, (!grounded && Mathf.Abs(vySm) > 5f) || hurt || slide ? 1 : 0, ref mouthOV, 0.06f, 100f, dt);
        var mA = rig.J("mouthA"); if (mA != null) mA.localScale = Vector3.one * Mathf.Max(0.001f, 1 - mouthO);
        var mO = rig.J("mouthO"); if (mO != null) mO.localScale = Vector3.one * Mathf.Max(0.001f, mouthO);
        browUp = Mathf.SmoothDamp(browUp, hurt ? -0.012f : (!grounded ? 0.022f : (w[(int)S.Push] > 0.5f || skid ? -0.01f : 0)), ref browUpV, 0.08f, 10f, dt);
        var bw = rig.J("brows"); if (bw != null) bw.localPosition = browRest + new Vector3(0, browUp, 0);
        blinkT -= dt; if (blinkT < -0.12f) blinkT = Random.Range(1.8f, 4.5f);
        var lids = rig.J("lids"); if (lids != null) lids.localScale = Vector3.one * ((blinkT < 0 || hurt) ? 1f : 0.001f);

        // ---- facing: a sprung 3D turn, always angled a little towards the camera, banking into the turn
        float targetYaw = Mathf.Lerp(facing > 0 ? 28f : 152f, 78f, titlePose);
        yaw = Mathf.SmoothDampAngle(yaw, targetYaw, ref yawV, 0.075f, 2000f, dt);
        float bank = Mathf.Clamp(yawV * 0.012f, -10f, 10f);

        // ---- squash & stretch: a spring around 1 that keeps the volume
        sqV += ((1f - sqY) * 240f - sqV * 17f) * dt; sqY = Mathf.Clamp(sqY + sqV * dt, 0.7f, 1.35f);
        float sx = 1f / Mathf.Sqrt(sqY);
        rig.body.localScale = new Vector3(sx, sqY, sx);

        float lean = 0;
        Color emis = Color.black, gl = Color.clear;
        if (drunk > 0)
        {
            Color rb = Color.HSVToRGB(Mathf.Repeat(Time.time * 1.6f, 1f), 0.9f, 1f);
            emis = rb.linear * 0.55f; gl = rb; gl.a = 0.5f;
            lean = Mathf.Sin(Time.time * 9f) * 9f;
            if (drunk < 2f && Mathf.Repeat(drunk, 0.2f) < 0.1f) emis = Color.black;       // about to run out
        }
        else if (chili > 0) { emis = new Color(0.5f, 0.08f, 0.0f); gl = new Color(1f, 0.45f, 0.1f, 0.4f); }
        else if (somtam > 0) { emis = new Color(0.05f, 0.22f, 0.03f); gl = new Color(0.4f, 1f, 0.35f, 0.3f); }
        rig.Tint(Color.white, emis);
        // double-jump somersault: one eased turn about her middle
        float flipAng = 0;
        if (flip > 0) { flip = Mathf.Max(0, flip - dt / 0.5f); float fe = 1 - flip; fe = fe * fe * (3 - 2 * fe); flipAng = -fe * 360f * (facing > 0 ? 1 : -1); }
        flipRot = Quaternion.Euler(0, 0, flipAng);
        rig.root.rotation = flipRot * Quaternion.Euler(0, 0, lean) * Quaternion.Euler(0, yaw, 0) * Quaternion.Euler(bank, 0, 0);
        // faint speed streaks at a full sprint
        if (grounded && speed > 9.3f && Random.value < dt * 30f)
            Fx.Emit("white", pos + new Vector2(-Mathf.Sign(vel.x) * 0.3f, Random.Range(0.25f, 1.3f)), new Vector2(-vel.x * 0.35f, 0), 0.16f, 1.0f, new Color(1, 1, 1, 0.35f), 0, false, 0, 0, false);
        rig.Visible(!(invuln > 0 && !Invincible && Mathf.Repeat(invuln, 0.14f) < 0.06f));     // blink while hurt
        glow.color = gl;

        // ---- trails
        trailT -= dt;
        if (trailT <= 0)
        {
            trailT = 0.04f;
            if (drunk > 0)
            {
                var c2 = Color.HSVToRGB(Mathf.Repeat(Time.time * 1.6f, 1f), 0.8f, 1f);
                Fx.Emit("star", Center + Random.insideUnitCircle * 0.5f, Random.insideUnitCircle - vel * 0.1f, 0.6f, 1.3f, c2, 0, true);
                Fx.Emit("dust", Center + Random.insideUnitCircle * 0.3f, -vel * 0.05f, 0.35f, 0.9f, new Color(c2.r, c2.g, c2.b, 0.35f), 0, true);
            }
            else if (chili > 0 && Random.value < 0.6f)
                Fx.Emit("dust", pos + new Vector2(Random.Range(-0.3f, 0.3f), Random.Range(0.2f, h)), new Vector2(0, 1.5f), 0.4f, 0.4f, new Color(1f, Random.Range(0.4f, 0.8f), 0.1f, 0.9f), 0, true);
            else if (somtam > 0 && Random.value < 0.4f)
                Fx.Emit("spark", pos + new Vector2(Random.Range(-0.3f, 0.3f), Random.Range(0.1f, h)), new Vector2(0, 0.8f), 0.5f, 1.2f, new Color(0.6f, 1f, 0.4f, 0.8f), 0, true);
        }
    }

    /// Simple smoothed pose for the scripted states (death tumble, victory dance).
    void Pose(float dt, float legL, float shinL, float legR, float shinR, float armL, float foreL, float armR, float foreR, float torso, float head, float speed = 16f)
    {
        float k = 1f - Mathf.Exp(-speed * dt);
        rig.Rot("legL", 0, 0, legL, k); rig.Rot("shinL", 0, 0, shinL, k); rig.Rot("legR", 0, 0, legR, k); rig.Rot("shinR", 0, 0, shinR, k);
        rig.Rot("armL", -6, 0, armL, k); rig.Rot("foreL", 0, 0, foreL, k); rig.Rot("armR", 6, 0, armR, k); rig.Rot("foreR", 0, 0, foreR, k);
        rig.Rot("torso", 0, 0, torso, k); rig.Rot("head", 0, 0, head, k);
        var hips = rig.J("hips"); if (hips != null) hips.localPosition = Vector3.Lerp(hips.localPosition, new Vector3(hips.localPosition.x, 0.52f, hips.localPosition.z), k);
    }

    Quaternion flipRot = Quaternion.identity; Vector3 eyeRest, browRest;
    void Sync(float z = 0)
    {
        Vector3 mid = new Vector3(0, 0.8f, 0);                       // rotate the somersault about her middle, not her feet
        go.transform.position = new Vector3(pos.x, pos.y, z) + mid - flipRot * mid;
        glow.transform.position = new Vector3(pos.x, pos.y + h * 0.55f, z + 0.5f);
    }

    public void Bounce(float v = 0)
    {
        vel.y = v > 0 ? v : (In.JumpHeld ? 17.5f : 11f);
        springing = v > 0; airJumps = 1; grounded = false; rider = null;
        sqY = 1.14f; sqV = 3f;
    }

    public void Heal(int n) { hearts = Mathf.Min(MaxHearts, hearts + n); }

    public void Hurt(float fromX, bool spike = false)
    {
        if (deadState || winState || invuln > 0 || Invincible) return;
        hearts--;
        Sfx.Play("sfx_hurt", 0.9f);
        Fx.Shake(0.35f); Game.I.Freeze(0.08f);
        Fx.Burst("star", Center, 8, 6f, 0.4f, 1.2f, new Color(1, 0.9f, 0.5f), 0, true);
        if (hearts <= 0) { Die(); return; }
        invuln = 1.6f;
        vel = new Vector2(pos.x < fromX ? -7f : 7f, spike ? 13f : 9f);
        grounded = false; rider = null;
        Game.I.FlashScreen(new Color(1, 0.2f, 0.2f, 0.25f));
    }

    public void Die()
    {
        if (deadState) return;
        deadState = true; hearts = 0; deadT = 0; flipRot = Quaternion.identity;
        somtam = chili = drunk = 0;
        vel = new Vector2(0, 15f);
        glow.color = Color.clear; rig.Tint(Color.white, Color.black); rig.Visible(true); rig.body.localScale = Vector3.one;
        Sfx.Play("sfx_die", 0.9f);
        Fx.Shake(0.5f); Game.I.Freeze(0.25f);
        Game.I.OnPlayerDied();
    }

    void TickDead(float dt)
    {
        deadT += dt;
        vel.y -= 45f * dt;
        pos += vel * dt;
        Pose(dt, 40, -60, -30, -50, 160, 20, 170, 20, 20, 20, 30f);
        rig.root.rotation = Quaternion.Euler(0, 0, deadT * 420f) * Quaternion.Euler(0, 78f, 0);
        Sync(-2.2f);
    }

    public void Win()
    {
        winState = true; vel = Vector2.zero; animT = 0; ducking = false; h = StandH;
        somtam = chili = drunk = 0; glow.color = Color.clear; rig.Tint(Color.white, Color.black); rig.Visible(true);
    }

    void TickWin(float dt)
    {
        animT += dt;
        vel.x = 0; vel.y = Mathf.Max(vel.y - 62f * dt, -24f);
        var hit = Level.Move(ref pos, ref vel, hw, h, dt);
        if (hit.ground && animT % 0.7f < dt) { vel.y = 9f; }
        float wv2 = Mathf.Sin(animT * 12f);
        Pose(dt, hit.ground ? 4 : 30, hit.ground ? -6 : -60, hit.ground ? -4 : 20, hit.ground ? -6 : -50, 168 + wv2 * 12, 20 + wv2 * 20, 168 - wv2 * 12, 20 - wv2 * 20, -4, -12, 20f);
        yaw = Mathf.LerpAngle(yaw, 80f, 1f - Mathf.Exp(-10f * dt));
        rig.root.rotation = Quaternion.Euler(0, yaw, 0); rig.body.localScale = Vector3.one;
        rig.Rot("pony", 0, 0, Mathf.Sin(animT * 12f) * 8f - 4f);
        Sync();
    }

    public void Teleport(Vector2 p) { pos = prevPos = p; vel = Vector2.zero; rider = null; Sync(); }
}
