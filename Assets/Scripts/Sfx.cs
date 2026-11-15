using System.Collections.Generic;
using UnityEngine;

/// Audio: pooled one-shots (optionally placed in the world: panned and attenuated by distance from the
/// camera), two music decks that cross-fade, one looping ambience deck, volume settings, and a low-pass
/// that muffles the music while the game is paused.
public static class Sfx
{
    static AudioSource[] pool;
    static readonly AudioSource[] music = new AudioSource[2];
    static readonly AudioLowPassFilter[] lowpass = new AudioLowPassFilter[2];
    static AudioSource loop; static float loopVol, loopTarget;
    static int deck; static float deckVolume;
    static int next;
    static readonly Dictionary<string, AudioClip> clips = new Dictionary<string, AudioClip>();
    public static float MusicPitch = 1f;
    public static float ListenerX, HalfWidth = 10f;       // camera centre and half the visible width, for positional sound
    public static bool Muffled;                           // true while paused
    public static float MusicVolume = 1f, FxVolume = 1f;  // 0..1, from Settings ▸ Audio
    const float FadeTime = 0.35f;
    static float cutoff = 22000f;

    public static void Init(GameObject host)
    {
        pool = new AudioSource[16];
        for (int i = 0; i < pool.Length; i++) { pool[i] = host.AddComponent<AudioSource>(); pool[i].playOnAwake = false; }
        for (int i = 0; i < 2; i++)
        {   // each deck on its own object so it can carry its own filter
            var go = new GameObject("MusicDeck" + i); go.transform.SetParent(host.transform, false);
            music[i] = go.AddComponent<AudioSource>(); music[i].loop = true; music[i].playOnAwake = false; music[i].volume = 0;
            lowpass[i] = go.AddComponent<AudioLowPassFilter>(); lowpass[i].cutoffFrequency = 22000f;
        }
        loop = host.AddComponent<AudioSource>(); loop.loop = true; loop.playOnAwake = false; loop.volume = 0;
        MusicVolume = PlayerPrefs.GetInt("volMusic", 80) / 100f; FxVolume = PlayerPrefs.GetInt("volFx", 100) / 100f;
    }

    static AudioClip Clip(string name)
    {
        if (!clips.TryGetValue(name, out var c)) { c = Resources.Load<AudioClip>("Audio/" + name); clips[name] = c; if (c == null) Debug.LogError("Missing audio: " + name); }
        return c;
    }

    public static void Play(string name, float vol = 1f, float pitch = 1f, float jitter = 0.04f, float pan = 0f)
    {
        var c = Clip(name); if (c == null || vol <= 0.001f) return;
        var s = pool[next]; next = (next + 1) % pool.Length;
        s.pitch = pitch + Random.Range(-jitter, jitter);
        s.volume = vol * FxVolume; s.panStereo = pan;
        s.clip = c; s.Play();
    }

    /// A sound at a place in the level: panned left / right and quieter the further it is off screen.
    public static void PlayAt(float worldX, string name, float vol = 1f, float pitch = 1f, float jitter = 0.04f)
    {
        float d = (worldX - ListenerX) / Mathf.Max(1f, HalfWidth);
        float far = Mathf.Abs(d);
        Play(name, vol * Mathf.Clamp01(1.9f - far) * (far > 1f ? 0.7f : 1f), pitch, jitter, Mathf.Clamp(d * 0.75f, -0.85f, 0.85f));
    }

    /// Switches the music with a quick cross-fade (null = fade to silence).
    public static void Music(string name, float vol = 0.55f)
    {
        var c = name == null ? null : Clip(name);
        if (music[deck].clip == c && (c == null || music[deck].isPlaying)) { deckVolume = c == null ? 0 : vol; return; }
        deck = 1 - deck;                                   // the old deck keeps playing while it fades out
        music[deck].Stop(); music[deck].clip = c; music[deck].volume = 0; music[deck].pitch = 1f;
        if (c != null) music[deck].Play();
        deckVolume = c == null ? 0 : vol;
    }

    /// Starts, changes or (null) fades out the looping ambience.
    public static void Loop(string name, float vol = 0.5f)
    {
        if (name == null) { loopTarget = 0; return; }
        var c = Clip(name); if (c == null) return;
        if (loop.clip != c || !loop.isPlaying) { loop.clip = c; loop.volume = 0; loopVol = 0; loop.Play(); }
        loopTarget = vol;
    }

    public static void Tick(float dt)
    {
        for (int i = 0; i < 2; i++)
        {
            float target = i == deck ? deckVolume * MusicVolume * (Muffled ? 0.6f : 1f) : 0f;
            music[i].volume = Mathf.MoveTowards(music[i].volume, target, dt * 0.6f / FadeTime);
            if (i != deck && music[i].volume <= 0.0001f && music[i].isPlaying) music[i].Stop();
        }
        music[deck].pitch = Mathf.MoveTowards(music[deck].pitch, MusicPitch, dt * 1.5f);
        cutoff = Mathf.Lerp(cutoff, Muffled ? 700f : 22000f, 1f - Mathf.Exp(-9f * dt));
        for (int i = 0; i < 2; i++) lowpass[i].cutoffFrequency = cutoff;
        loopVol = Mathf.MoveTowards(loopVol, loopTarget, dt * 0.8f); loop.volume = loopVol * FxVolume;
        if (loopVol <= 0.0001f && loopTarget <= 0 && loop.isPlaying) loop.Stop();
    }
}
