#!/usr/bin/env python3
"""All sound effects, built from the same Thai instrument voices as the music (ranat, khong, ching, khim,
drums, pi) so effects and soundtrack belong together. Needs numpy.

    python Tools/gen_sfx.py
"""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_music as gm
from gen_music import env, ranat, ranat_thum, khong, pi_nai, ching, drum, mong, krap, SR, OUT
from gen_music2 import pluck

rng = np.random.default_rng(8)
def hz(i, octave=0): return 311.0 * 2 ** ((7 * (i // 5) + [0, 1, 2, 4, 5][i % 5]) / 7.0 + octave)

class Mix:
    def __init__(s, seconds): s.n = int(seconds * SR); s.l = np.zeros(s.n); s.r = np.zeros(s.n)
    def add(s, t, sig, gain=1.0, pan=0.0):
        i = int(t * SR); m = min(len(sig), s.n - i)
        if m <= 0: return
        s.l[i:i + m] += sig[:m] * gain * np.cos((pan + 1) * np.pi / 4); s.r[i:i + m] += sig[:m] * gain * np.sin((pan + 1) * np.pi / 4)
    def save(s, name, peak=0.85, room=0.12, loop=False):
        l, r = s.l, s.r; n = s.n
        if room > 0:      # short bright room so effects sit in the same space as the music
            m = int(0.5 * SR); t = np.arange(m) / SR; g = np.random.default_rng(5)
            def ir(): h = g.standard_normal(m) * np.exp(-t * 11); h[:300] = 0; return h / np.sqrt((h ** 2).sum())
            if loop: conv = lambda x, h: np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)
            else: conv = lambda x, h: np.convolve(x, h)[:n]
            l = l + room * 2 * conv(l, ir()); r = r + room * 2 * conv(r, ir())
        if not loop:
            f = min(n, int(0.02 * SR)); l[-f:] *= np.linspace(1, 0, f); r[-f:] *= np.linspace(1, 0, f)
        pk = max(np.abs(l).max(), np.abs(r).max(), 1e-9); l = l / pk * peak; r = r / pk * peak
        data = (np.stack([l, r], 1) * 32767).astype("<i2")
        with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
        print("wrote", name)

def sweep(f0, f1, dur, shape=1.0, harm=0.25):
    n = int(dur * SR); t = np.arange(n) / SR; f = f0 + (f1 - f0) * (t / dur) ** shape
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + harm * np.sin(2 * ph)) * env(n, 0.004, dur * 0.5)

def noise(dur, lo, hi, decay=8.0):
    n = int(dur * SR); t = np.arange(n) / SR
    spec = np.fft.rfft(rng.standard_normal(n)); fr = np.fft.rfftfreq(n, 1 / SR); spec *= (fr > lo) & (fr < hi)
    s = np.fft.irfft(spec, n); return s / (np.abs(s).max() + 1e-9) * np.exp(-t * decay) * env(n, 0.002, 0.02)

def voice(f0, f1, dur, vowel):
    """One person shouting: a glottal buzz gliding in pitch through vowel formants."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 + (f1 - f0) * np.minimum(1, t / (dur * 0.35)); f = f * (1 + 0.012 * np.sin(2 * np.pi * rng.uniform(4.5, 6.5) * t))
    ph = 2 * np.pi * np.cumsum(f) / SR; F = {"a": (800, 1250, 2600), "o": (480, 880, 2500), "e": (520, 1800, 2500), "u": (360, 760, 2300)}[vowel]
    s = np.zeros(n)
    for h in range(1, 22):
        fh = f * h; a = sum(np.exp(-((fh - c) / (110 + 60 * k)) ** 2) * (1.0, 0.7, 0.35)[k] for k, c in enumerate(F)) + 0.03
        s += np.sin(ph * h + h) * a / h ** 0.4
    s += rng.standard_normal(n) * 0.04
    return s * env(n, 0.05, dur * 0.45)

def claps(dur, rate, seed=0):
    n = int(dur * SR); s = np.zeros(n); g = np.random.default_rng(20 + seed)
    for _ in range(int(dur * rate)):
        i = int(g.uniform(0, n - 900)); m = int(g.uniform(300, 800)); c = g.standard_normal(m) * np.exp(-np.arange(m) / g.uniform(40, 110))
        c = c - np.convolve(c, np.ones(9) / 9, "same"); s[i:i + m] += c * g.uniform(0.3, 1.0)
    return s

# ------------------------------------------------------------------------------------------------ effects
def all_sfx():
    m = Mix(0.22); m.add(0, sweep(330, 700, 0.16, 0.7), 0.7); m.add(0, ranat(hz(7, 1), 0.12), 0.35); m.save("sfx_jump", room=0.06)
    m = Mix(0.3); m.add(0, sweep(500, 1100, 0.18, 0.6), 0.6); m.add(0.0, ranat(hz(9, 1), 0.12), 0.35); m.add(0.07, ranat(hz(12, 1), 0.16), 0.4, 0.2); m.save("sfx_jump2", room=0.08)
    m = Mix(0.5); m.add(0, ching(True)[:int(0.4 * SR)], 0.8); m.add(0, khong(hz(10, 1), 0.4), 0.5); m.add(0.06, khong(hz(12, 1), 0.4), 0.6, 0.2); m.save("sfx_coin")
    m = Mix(0.7)
    for i, d in enumerate((5, 7, 10)): m.add(i * 0.08, ranat(hz(d, 1), 0.35), 0.7, -0.2 + i * 0.2); m.add(i * 0.08, ranat(hz(d, 2), 0.3), 0.4, -0.2 + i * 0.2)
    m.save("sfx_confirm")
    m = Mix(0.12); m.add(0, ranat(hz(7, 1), 0.1), 0.8); m.add(0, krap(0.05), 0.3); m.save("sfx_select", room=0.05)
    m = Mix(1.2)
    for i, d in enumerate((5, 7, 9, 10)): m.add(i * 0.11, khong(hz(d), 0.9), 0.7, -0.3 + i * 0.2)
    m.add(0.33, ching(True), 0.7, 0.3); m.add(0.33, mong(156, 0.8), 0.4); m.save("sfx_checkpoint", room=0.2)
    m = Mix(1.4)
    for i, d in enumerate((5, 6, 7, 8, 9, 10, 11, 12, 14, 15)): m.add(i * 0.055, pluck(hz(d, 1), 0.9, 0.9, True), 0.5, -0.5 + i * 0.1)
    m.add(0.55, ching(True), 0.6, 0.3); m.add(0.6, khong(hz(15, 1), 0.8), 0.4); m.save("sfx_lotus", room=0.25)
    m = Mix(1.3)
    for i, d in enumerate((5, 7, 9, 10, 12, 14, 15)): m.add(i * 0.07, ranat(hz(d, 1), 0.3), 0.6, 0.2); m.add(i * 0.07, ranat(hz(d, 2), 0.3), 0.4, 0.2)
    m.add(0.5, mong(156, 0.8), 0.5); m.add(0.5, ching(True), 0.6, -0.3); m.add(0.5, khong(hz(15), 0.8), 0.5); m.save("sfx_powerup", room=0.2)
    m = Mix(1.0); m.add(0, khong(hz(7), 0.8), 0.7, -0.2); m.add(0.14, khong(hz(10), 0.8), 0.8, 0.2); m.add(0.14, pluck(hz(10, 1), 0.7, 0.9, True), 0.35); m.save("sfx_heal", room=0.2)
    m = Mix(0.36); m.add(0, drum("pa"), 0.9); m.add(0, sweep(520, 180, 0.28, 0.6, 0.5), 0.6); m.add(0, noise(0.12, 800, 5000, 30), 0.4); m.save("sfx_hurt", room=0.08)
    m = Mix(1.7); m.add(0, pi_nai([hz(9, 1), hz(7, 1), hz(5, 1), hz(2, 1), hz(0, 1) * 0.7], [0.18, 0.18, 0.18, 0.25, 0.6]), 1.0); m.add(0.0, drum("pa"), 0.6); m.add(0.72, drum("tum"), 0.9); m.add(0.75, mong(98, 0.9), 0.4)
    m.save("sfx_die", room=0.2)
    m = Mix(0.26); m.add(0, drum("theng")[:int(0.2 * SR)], 0.9); m.add(0.01, sweep(300, 900, 0.12, 0.5), 0.45); m.add(0, noise(0.08, 1500, 7000, 40), 0.3); m.save("sfx_stomp", room=0.06)
    m = Mix(0.3); m.add(0, noise(0.28, 300, 3500, 14), 0.9); m.add(0, sweep(260, 120, 0.2, 1.0, 0.1), 0.4); m.save("sfx_poof", room=0.08)
    n = int(0.5 * SR); t = np.arange(n) / SR; f = 130 + 330 * (1 - np.exp(-t * 9)); boing = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.06 * np.sin(2 * np.pi * 26 * t))) / SR) * np.exp(-t * 6) * env(n, 0.003, 0.05)
    m = Mix(0.55); m.add(0, boing, 0.8); m.add(0, drum("tum")[:int(0.3 * SR)], 0.9); m.add(0, ching(False), 0.3, 0.3); m.save("sfx_spring", room=0.1)
    m = Mix(0.45)
    for i, (t0, f0) in enumerate(((0, 0.8), (0.07, 0.65), (0.15, 0.55), (0.22, 0.75))): m.add(t0, ranat_thum(hz(i % 3, -1) * f0, 0.15), 0.7, -0.3 + i * 0.2); m.add(t0, krap(0.05), 0.4)
    m.add(0.05, noise(0.35, 200, 2500, 9), 0.5); m.save("sfx_crumble", room=0.08)
    n = int(0.34 * SR); t = np.arange(n) / SR
    m = Mix(0.34); m.add(0, noise(0.32, 400, 6000, 7) * (0.4 + 0.6 * np.sin(np.pi * np.arange(int(0.32 * SR)) / (0.32 * SR))), 0.9); m.add(0, sweep(200, 520, 0.2, 0.5, 0.4), 0.3); m.save("sfx_fire", room=0.06)
    m = Mix(3.6); m.add(0, mong(98, 3.5), 1.0); m.add(0, mong(98 * 2.02, 2.6), 0.35); m.add(0, mong(49, 3.5), 0.5); m.add(0, noise(0.5, 1500, 8000, 9), 0.25); m.add(0, drum("tum"), 0.6); m.save("sfx_gong", room=0.3)
    # footsteps for three kinds of ground, landing, splash, spit
    m = Mix(0.09); m.add(0, noise(0.08, 300, 2600, 45), 0.8); m.add(0, sweep(140, 90, 0.05, 1, 0), 0.5); m.save("sfx_step_soft", room=0.03)
    m = Mix(0.1); m.add(0, ranat_thum(150, 0.09), 0.9); m.add(0, noise(0.05, 900, 4000, 70), 0.35); m.save("sfx_step_wood", room=0.05)
    m = Mix(0.09); m.add(0, noise(0.07, 1200, 7000, 60), 0.7); m.add(0, sweep(220, 150, 0.04, 1, 0), 0.5); m.save("sfx_step_hard", room=0.06)
    m = Mix(0.3); m.add(0, sweep(150, 60, 0.2, 0.6, 0.1), 0.9); m.add(0, noise(0.2, 200, 2200, 18), 0.6); m.save("sfx_land", room=0.06)
    n = int(1.0 * SR); t = np.arange(n) / SR
    m = Mix(1.0); m.add(0, noise(1.0, 300, 9000, 4.5), 0.9); m.add(0, sweep(180, 70, 0.35, 0.6, 0.1), 0.8)
    for _ in range(14): m.add(rng.uniform(0.15, 0.8), sweep(rng.uniform(700, 1800), rng.uniform(1900, 3200), 0.05, 1, 0), rng.uniform(0.08, 0.2), rng.uniform(-0.6, 0.6))      # droplets
    m.save("sfx_splash", room=0.15)
    # firework: thump, crackle, glitter
    m = Mix(1.8); n = int(1.5 * SR); t = np.arange(n) / SR
    m.add(0, np.sin(2 * np.pi * np.cumsum(70 * (1 + 1.5 * np.exp(-t * 20))) / SR) * np.exp(-t * 5), 1.0); m.add(0, noise(0.6, 100, 4000, 9), 0.8)
    for _ in range(90): m.add(rng.uniform(0.1, 1.5), noise(0.012, 2500, 12000, 200), rng.uniform(0.1, 0.5), rng.uniform(-0.8, 0.8))
    m.save("sfx_firework", room=0.3)

def cheer():
    """A table of friends (and the whole pier) erupting: shouts, whoops, whistles, clapping."""
    m = Mix(4.2)
    for i in range(34):
        f0 = rng.uniform(150, 420); up = rng.uniform(1.15, 1.7); d = rng.uniform(0.7, 1.9)
        m.add(rng.uniform(0, 0.9) + (0 if i < 20 else rng.uniform(0.8, 1.8)), voice(f0, f0 * up, d, rng.choice(["a", "e", "o", "u", "a"])), rng.uniform(0.25, 0.6), rng.uniform(-0.9, 0.9))
    for i in range(5):       # whoops and two-finger whistles
        d = rng.uniform(0.4, 0.8); m.add(rng.uniform(0.2, 2.6), sweep(rng.uniform(1300, 1700), rng.uniform(2400, 3200), d, 0.5, 0.05), 0.18, rng.uniform(-0.8, 0.8))
    c = claps(4.2, 55); m.add(0, c * np.minimum(1, np.arange(len(c)) / (0.5 * SR)), 0.5, -0.3); m.add(0, claps(4.2, 55, 1), 0.5, 0.3)
    fade = int(1.2 * SR); m.l[-fade:] *= np.linspace(1, 0, fade); m.r[-fade:] *= np.linspace(1, 0, fade)
    m.save("sfx_cheer", room=0.3)

def crowd_loop():
    """Seamless bed of happy clapping, chatter and the odd whoop for the party."""
    dur = 7.0; m = Mix(dur); n = m.n
    def wrap(t, sig, gain, pan):
        i = int(t * SR); k = 0
        while k < len(sig):
            q = min(len(sig) - k, n - i); m.l[i:i + q] += sig[k:k + q] * gain * np.cos((pan + 1) * np.pi / 4); m.r[i:i + q] += sig[k:k + q] * gain * np.sin((pan + 1) * np.pi / 4); k += q; i = 0
    for side, pan in ((0, -0.4), (1, 0.4)):
        c = claps(dur, 38, 5 + side); c = np.fft.irfft(np.fft.rfft(c) * 1.0, n); wrap(0, c, 0.5, pan)
    for i in range(16):
        f0 = rng.uniform(170, 400); wrap(rng.uniform(0, dur), voice(f0, f0 * rng.uniform(1.1, 1.5), rng.uniform(0.6, 1.3), rng.choice(["a", "e", "o"])), rng.uniform(0.12, 0.3), rng.uniform(-0.9, 0.9))
    for i in range(3): wrap(rng.uniform(0, dur), sweep(rng.uniform(1300, 1700), rng.uniform(2400, 3000), 0.5, 0.5, 0.05), 0.1, rng.uniform(-0.8, 0.8))
    m.save("amb_crowd", peak=0.7, room=0.25, loop=True)

if __name__ == "__main__":
    all_sfx(); cheer(); crowd_loop()
