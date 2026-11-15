#!/usr/bin/env python3
"""Soundtrack for levels 2-25, the ending and the firework sound. Needs numpy.

    python Tools/gen_music2.py            # everything
    python Tools/gen_music2.py 7 13 end   # only some

Every level gets its own piece: its own tune (grown from a per-level seed), tempo, register, mode, lead
instrument, rhythm section and ambience, in one of seven Thai ensemble styles:
  piphat   - ranat ek running in octaves over the khong wong melody, taphon drums, ching
  mahori   - khim (hammered dulcimer) and saw (fiddle), gentle hand drums
  isan     - phin (lute) riffs over a khaen (mouth organ) drone and a driving mor lam groove
  lanna    - sueng (northern lute) and pi, slow and airy, with a gong cycle
  klongyao - long-drum parade: hook on the ranat, shouting drums, clappers, cymbal crashes
  talung   - southern shadow-play band: fast oboe line over quick paired drums and mong gongs
  night    - khim and saw over a soft pulse, for the lantern-lit levels
All use the Thai 7-step equal tuning, like the level 1 and title music (see gen_music.py).
"""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_music as gm
from gen_music import Track, env, ranat, ranat_thum, khong, pi_nai, ching, drum, mong, krap, chap_yai, SR, OUT

rng = np.random.default_rng(3)

# ------------------------------------------------------------------------------------------------ extra instruments
def pluck(f, dur=0.7, bright=0.7, double=False):
    """Plucked string (phin, sueng) - or two strings a hair apart for the khim."""
    n = int(dur * SR); p = max(2, int(SR / f)); buf = rng.uniform(-1, 1, p)
    for _ in range(int(3 - bright * 3)): buf = 0.5 * (buf + np.roll(buf, 1))
    damp = 0.9965 - 0.002 * (1 - bright); chunks = []
    for _ in range(n // p + 1):
        chunks.append(buf.copy()); buf = damp * 0.5 * (buf + np.roll(buf, 1))
    s = np.concatenate(chunks)[:n] * env(n, 0.001, 0.03)
    if double:
        s2 = pluck(f * 1.005, dur, bright); m = min(len(s), len(s2)); s = s[:m] + 0.7 * s2[:m]
    return s

def khaen(freqs, dur):
    """Free-reed mouth organ: buzzy sustained chord with a breathing pulse."""
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in freqs:
        for h, a in ((1, 1.0), (2, 0.55), (3, 0.5), (4, 0.22), (5, 0.25), (6, 0.1)): s += a * np.sin(2 * np.pi * f * h * t + rng.uniform(0, 6.28))
    return s * (0.85 + 0.15 * np.sin(2 * np.pi * 5.5 * t)) / len(freqs) * env(n, 0.02, 0.05)

def saw(freqs, durs, gain=1.0):
    """Saw u / saw duang: two-string fiddle - a legato line with slides, vibrato and a nasal body."""
    total = sum(durs); n = int(total * SR); t = np.arange(n) / SR; f = np.zeros(n); pos = 0; prev = freqs[0] * 0.97
    for fr, d in zip(freqs, durs):
        m = int(d * SR); g = int(min(0.09, d * 0.4) * SR); seg = np.full(m, fr); seg[:g] = np.exp(np.linspace(np.log(prev), np.log(fr), g))
        f[pos:pos + m] = seg[:max(0, min(m, n - pos))]; pos += m; prev = fr
    f[pos:] = prev
    f *= 1 + 0.009 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t * 2)
    ph = 2 * np.pi * np.cumsum(f) / SR; s = np.zeros(n)
    for h in range(1, 12):
        form = 0.3 + 1.0 * np.exp(-((f * h - 900) / 500) ** 2) + 0.5 * np.exp(-((f * h - 2300) / 700) ** 2)
        s += np.sin(ph * h + 0.3 * h) * form / h
    return s * env(n, 0.05, 0.1) * gain * 0.22

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 3.5) * env(n, 0.004, 0.03)

def shaker(dur=0.07):
    n = int(dur * SR); t = np.arange(n) / SR
    s = rng.uniform(-1, 1, n); s = s - np.convolve(s, np.ones(6) / 6, "same")
    return s * np.exp(-t * 60) * 0.5

def ambience(T, kind):
    """A quiet bed under the music: rain, surf, night insects, a stream, city hum."""
    n = T.n; t = np.arange(n) / SR
    def band(lo, hi):
        spec = np.fft.rfft(rng.standard_normal(n)); fr = np.fft.rfftfreq(n, 1 / SR)
        spec *= (fr > lo) & (fr < hi); s = np.fft.irfft(spec, n); return s / (np.abs(s).max() + 1e-9)
    if kind == "rain": s = band(1500, 9000) * 0.05 + band(200, 900) * 0.04
    elif kind == "sea": s = band(200, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * t * 4 / (n / SR) * 1.0)) ** 2 * 0.09       # four swells per loop
    elif kind == "stream": s = band(900, 5000) * (0.8 + 0.2 * np.sin(2 * np.pi * t * 3.1)) * 0.05
    elif kind == "night":
        s = np.sin(2 * np.pi * 4300 * t) * (np.sin(2 * np.pi * 17 * t) > 0.2) * (np.sin(2 * np.pi * 0.9 * t) > 0) * 0.012 + band(5500, 8000) * 0.01
    elif kind == "city": s = band(60, 400) * 0.05
    elif kind == "cave":
        s = band(80, 300) * 0.04
        for k in range(int(n / SR * 1.2)):
            i = int(rng.uniform(0, n - 4000)); d = np.sin(2 * np.pi * rng.uniform(900, 1700) * np.arange(3000) / SR) * np.exp(-np.arange(3000) / 500) * 0.05; s[i:i + 3000] += d
    else: return
    T.l += s; T.r += np.roll(s, 1200)

# ------------------------------------------------------------------------------------------------ composing
MODES = {"a": [0, 1, 2, 4, 5], "b": [0, 1, 3, 4, 5], "c": [0, 2, 3, 4, 6]}

class Piece:
    def __init__(s, seed, bpm, base, mode, seconds=44):
        s.r = np.random.default_rng(seed); s.bpm = bpm; s.beat = 60.0 / bpm; s.base = base; s.mode = MODES[mode]
        n_ph = max(4, int(round(seconds * bpm / 60 / 16 / 2)) * 2)             # phrases of 16 beats, an even number of them
        A = s.phrase(4, False); A2 = s.vary(A); B = s.phrase(7, True); B2 = s.vary(B)
        pool = {4: [A, A2, B, A2], 6: [A, A2, B, B2, A, A2], 8: [A, A2, B, A2, B2, B, A, A2], 10: [A, A2, B, A2, B2, B, A, A2, B, A2]}
        s.form = pool.get(n_ph, pool[8]); s.skel = [x for ph in s.form for x in ph]
        s.T = Track(len(s.skel) * s.beat)

    def hz(s, i, octave=0): return s.base * 2 ** ((7 * (i // 5) + s.mode[i % 5]) / 7.0 + octave)

    def phrase(s, centre, lift):
        """16 skeleton tones: a 4-tone cell answered, repeated and resolved (stepwise, with the odd leap)."""
        r = s.r; cell = [centre]
        for _ in range(3): cell.append(int(np.clip(cell[-1] + r.choice([-2, -1, -1, 1, 1, 2]), 1, 11)))
        answer = [int(np.clip(c + r.choice([1, 2, -1]), 1, 12)) for c in cell]
        run = [cell[-1]]
        for _ in range(3): run.append(int(np.clip(run[-1] + (1 if lift else -1) * r.choice([1, 1, 2]), 0, 12)))
        end = [run[-1], int(np.clip(run[-1] - 1, 0, 12)), 5 if not lift else 7, 5 if not lift else 7]
        return cell + answer + run + end

    def vary(s, ph):
        out = list(ph); r = s.r
        for k in (5, 9, 10): out[k] = int(np.clip(out[k] + r.choice([-1, 1]), 0, 12))
        out[12:] = [out[11], int(np.clip(out[11] + 1, 0, 12)), 5, 5]
        return out

    def weave(s):
        return gm.weave(s.skel)

    def held(s, every=2):
        """Skeleton thinned to longer notes for the singing instruments: (frequencies' indices, durations in beats)."""
        idx = [s.skel[k + every - 1] for k in range(0, len(s.skel), every)]
        return idx, [every * s.beat] * len(idx)

# percussion cycles: (beat offset inside an 8-beat cycle, stroke, gain)
GROOVES = {
    "taphon": [(0, "theng", .9), (1, "ting", .5), (1.5, "pa", .4), (2, "theng", .75), (2.5, "ting", .4), (3, "pa", .5), (3.5, "ting", .5), (4, "theng", .9), (4.75, "ting", .35), (5, "ting", .5), (5.5, "theng", .6), (6, "pa", .5), (6.5, "ting", .5), (7, "theng", .8), (7.5, "pa", .45), (7.75, "pa", .4)],
    "soft": [(0, "theng", .6), (2, "ting", .35), (3.5, "ting", .3), (4, "theng", .55), (5.5, "ting", .3), (6, "ting", .35), (7, "theng", .4)],
    "isan": [(0, "tum", .9), (0.5, "pa", .4), (1, "pa", .6), (1.5, "theng", .7), (2, "tum", .85), (2.75, "pa", .4), (3, "pa", .6), (3.5, "theng", .6), (4, "tum", .9), (4.5, "pa", .4), (5, "pa", .6), (5.5, "theng", .7), (6, "tum", .85), (6.5, "theng", .6), (7, "pa", .6), (7.25, "pa", .5), (7.5, "pa", .6)],
    "parade": [(0, "theng", 1), (0.75, "pa", .5), (1, "pa", .6), (1.5, "theng", .85), (2, "theng", .9), (2.5, "pa", .55), (3, "ting", .6), (3.5, "pa", .55), (4, "theng", 1), (4.75, "pa", .5), (5, "pa", .6), (5.5, "theng", .85), (6, "pa", .6), (6.5, "theng", .8), (7, "theng", .9), (7.25, "pa", .5), (7.5, "pa", .6), (7.75, "ting", .5)],
    "talung": [(k * 0.5, ("ting" if k % 4 in (1, 2) else "theng" if k % 4 == 0 else "pa"), (.8 if k % 4 == 0 else .5)) for k in range(16)],
    "slow": [(0, "tum", .7), (3, "ting", .3), (4, "theng", .5), (6, "ting", .3), (7, "ting", .35)],
}

def compose(name, style, seed, bpm, base, mode, amb=None, seconds=44):
    P = Piece(seed, bpm, base, mode, seconds); T = P.T; beat = P.beat; s16 = beat / 4; e8 = beat / 2
    skel = P.skel; N = len(skel); run = P.weave()
    groove = GROOVES[{"piphat": "taphon", "mahori": "soft", "isan": "isan", "lanna": "slow", "klongyao": "parade", "talung": "talung", "night": "soft"}[style]]
    for k, n in enumerate(skel):
        t = k * beat; sec = k // 16; nxt = skel[(k + 1) % N]; first = sec == 0 and k < 8
        # --- time keepers
        if style in ("piphat", "mahori", "klongyao", "night", "talung"): T.add(t, ching(k % 2 == 0), 0.38 if k % 2 == 0 else 0.55, 0.55)
        elif style == "lanna" and k % 2 == 0: T.add(t, ching(k % 4 == 0), 0.3, 0.5)
        elif style == "isan": T.add(t + e8, shaker(), 0.5, 0.5); T.add(t, ching(False), 0.25, 0.5)
        if not first or style in ("klongyao", "isan", "talung"):
            for off, kind, g in groove:
                if int(off) == k % 8: T.add(t + (off - int(off)) * beat, drum(kind), g * (0.8 if style in ("mahori", "night", "lanna") else 1.0), -0.1 if kind in ("theng", "tum") else 0.15)
        if k % 16 == 15 and style not in ("lanna", "night"):
            for off, kind in ((0.5, "tum"), (0.75, "pa")): T.add(t + off * beat, drum(kind), 0.7)
        if style in ("klongyao", "talung") and k % 2 == 0: T.add(t, mong(156 if k % 4 == 0 else 131, 1.1), 0.36, -0.15)
        if style == "klongyao" and k % 2 == 1: T.add(t, krap(), 0.5, 0.4)
        if style in ("klongyao",) and k % 32 == 0: T.add(t, chap_yai(), 0.8, 0.2)
        if style == "lanna" and k % 8 == 0: T.add(t, mong(P.hz(0, -2), 2.6), 0.4, -0.1)
        # --- the tune
        if style == "piphat":
            T.add(t, khong(P.hz(n)), 0.5, -0.35)
            if k >= 8:
                for j in range(4):
                    g = 0.48 if j == 0 else 0.34; f = P.hz(run[k * 4 + j], 1)
                    T.add(t + j * s16, ranat(f), g, 0.3); T.add(t + j * s16, ranat(f * 2), g * 0.7, 0.3)
            if k % 2 == 1: T.add(t + e8, ranat_thum(P.hz(n, -1)), 0.5, -0.1); T.add(t + beat * 0.75, ranat_thum(P.hz(nxt + 1, -1)), 0.33, -0.1)
        elif style in ("mahori", "night"):
            for j, d in enumerate((n, n + 2, nxt + 1, n + 2) if style == "mahori" else (n, n + 2)):
                T.add(t + j * (s16 if style == "mahori" else e8), pluck(P.hz(d, 1), 1.2, 0.9, True), 0.42 if j == 0 else 0.3, -0.25 + 0.5 * (j % 2))
            if k % 2 == 0: T.add(t, khong(P.hz(n, 0), 1.6), 0.36, -0.3)
            if k % 4 == 0: T.add(t, bass(P.hz(n, -2), beat * 2), 0.5)
        elif style == "isan":
            for j, d in enumerate((n, n + 1 if k % 2 else n - 1)):
                T.add(t + j * e8, pluck(P.hz(d, 1), 0.5, 0.75), 0.7 if j == 0 else 0.55, 0.25)
            if k % 2 == 0: T.add(t, pluck(P.hz(0, 0), 0.6, 0.6), 0.3, 0.25)                 # drone string
            if k % 4 in (0, 2): T.add(t + (0 if k % 4 == 0 else e8), khaen([P.hz(0, 0), P.hz(3, 0), P.hz(5, 0)] if (k // 8) % 2 == 0 else [P.hz(1, 0), P.hz(4, 0), P.hz(6, 0)], beat * 1.2), 0.17, -0.45)
            T.add(t, bass(P.hz(0 if (k // 4) % 4 != 2 else 3, -2), beat * 0.9), 0.7); T.add(t + beat * 0.75, bass(P.hz(0 if (k // 4) % 4 != 2 else 3, -2), beat * 0.3), 0.4)
        elif style == "lanna":
            T.add(t, pluck(P.hz(n, 1), 1.4, 0.55), 0.6, 0.2)
            if k % 2 == 1: T.add(t + e8, pluck(P.hz(nxt, 1), 1.0, 0.55), 0.4, 0.2)
            if k % 4 == 0: T.add(t, pluck(P.hz(0, 0), 2.0, 0.5), 0.35, -0.2); T.add(t + beat, pluck(P.hz(3, 0), 1.6, 0.5), 0.25, -0.2)
        elif style == "klongyao":
            for j in range(2):
                f = P.hz(run[k * 4 + j * 2], 1); g = 0.6 if j == 0 else 0.45
                T.add(t + j * e8, ranat(f), g, 0.3); T.add(t + j * e8, ranat(f * 2), g * 0.7, 0.3)
            T.add(t, khong(P.hz(n), 0.9), 0.45, -0.35)
            if k % 2 == 0: T.add(t, ranat_thum(P.hz(0 if (k // 8) % 2 == 0 else 2, -1), 0.4), 0.55, -0.1)
        elif style == "talung":
            T.add(t, khong(P.hz(n), 0.8), 0.4, -0.3); T.add(t + e8, ranat_thum(P.hz(n + 1, -1), 0.3), 0.45, -0.1)
            if k % 4 == 0: T.add(t, bass(P.hz(0, -2), beat), 0.5)
    # --- singing lines over whole sections
    def sing(fn, sections, every, octave, gain, pan):
        for sec in sections:
            if sec * 16 >= N: continue
            idx = [skel[sec * 16 + q + every - 1] for q in range(0, 16, every)]
            T.add(sec * 16 * beat, fn([P.hz(i, octave) for i in idx], [every * beat] * len(idx)), gain, pan)
    n_sec = N // 16
    if style == "piphat": sing(pi_nai, [s for s in range(n_sec) if s % 4 == 2], 2, 1, 0.9, 0.0)
    elif style == "mahori": sing(saw, [s for s in range(n_sec) if s % 2 == 1], 2, 1, 1.0, 0.1)
    elif style == "night": sing(saw, list(range(1, n_sec)), 2, 1, 0.9, 0.1)
    elif style == "lanna": sing(pi_nai, [s for s in range(n_sec) if s % 2 == 1], 4, 1, 0.7, 0.05); sing(saw, [s for s in range(n_sec) if s % 4 == 2], 2, 0, 0.6, -0.2)
    elif style == "klongyao": sing(pi_nai, [s for s in range(n_sec) if s % 4 in (2, 3)], 1, 1, 0.8, 0.0)
    elif style == "talung": sing(pi_nai, list(range(n_sec)), 1, 1, 0.95, 0.05)
    elif style == "isan": sing(saw, [s for s in range(n_sec) if s % 4 == 3], 2, 1, 0.6, -0.1)
    T.add(0, mong(110, 3.0), 0.45)
    if amb: ambience(T, amb)
    T.save(name + ".wav", peak=0.76)

# level -> (style, seed, bpm, base pitch, mode, ambience)
LEVELS = {
    2: ("isan", 202, 132, 220.0, "a", None),        # Banana Grove
    3: ("mahori", 203, 104, 294.0, "b", "stream"),  # Floating Market
    4: ("lanna", 204, 76, 262.0, "c", None),        # Bamboo Forest
    5: ("klongyao", 205, 122, 277.0, "a", None),    # Elephant Trail
    6: ("lanna", 206, 84, 330.0, "a", None),        # Tea Hills
    7: ("mahori", 207, 116, 349.0, "a", "stream"),  # Emerald Falls
    8: ("isan", 208, 144, 247.0, "b", None),        # Sunflower Fields
    9: ("piphat", 209, 132, 294.0, "c", None),      # Monkey Temple
    10: ("isan", 210, 126, 196.0, "c", None),       # Durian Orchard
    11: ("klongyao", 211, 146, 311.0, "b", "city"), # Railway Market
    12: ("mahori", 212, 124, 392.0, "c", "city"),   # Bangkok Rooftops
    13: ("night", 213, 110, 277.0, "b", "city"),    # Chinatown Night
    14: ("klongyao", 214, 152, 330.0, "a", None),   # Songkran Splash
    15: ("piphat", 215, 108, 247.0, "b", None),     # Ayutthaya Dusk
    16: ("night", 216, 84, 330.0, "a", "night"),    # Lantern Festival
    17: ("night", 217, 92, 262.0, "c", "night"),    # Loy Krathong
    18: ("lanna", 218, 68, 208.0, "b", "cave"),     # Cave of Light
    19: ("talung", 219, 118, 262.0, "a", None),     # Mangrove Maze
    20: ("piphat", 220, 140, 262.0, "c", "rain"),   # Monsoon Run
    21: ("talung", 221, 132, 330.0, "b", "sea"),    # Island Hopping
    22: ("isan", 222, 138, 262.0, "a", "sea"),      # Coral Beach
    23: ("talung", 223, 108, 233.0, "c", "sea"),    # Fishing Village
    24: ("klongyao", 224, 134, 247.0, "c", "night"),# Night Market
    25: ("piphat", 225, 150, 349.0, "a", "sea"),    # Seafood Road
}

def ending():
    """Grand, joyful finale: parade drums, the whole ensemble on a rising hook, cymbal crashes all the way."""
    P = Piece(777, 148, 311.0, "a", 52); T = P.T; beat = P.beat; e8 = beat / 2
    hook = [5, 7, 9, 7, 10, 9, 7, 9, 10, 12, 10, 9, 7, 9, 10, 10]
    ans = [9, 7, 5, 7, 9, 10, 9, 7, 5, 7, 9, 7, 5, 4, 5, 5]
    high = [10, 12, 14, 12, 10, 12, 14, 15, 14, 12, 10, 12, 14, 12, 10, 10]
    P.form = [hook, ans, hook, ans, high, ans, hook, ans]; P.skel = [x for ph in P.form for x in ph]; skel = P.skel; N = len(skel)
    P.T = T = Track(N * beat); run = gm.weave(skel)
    for k, n in enumerate(skel):
        t = k * beat
        T.add(t, ching(k % 2 == 0), 0.4 if k % 2 == 0 else 0.6, 0.55)
        for off, kind, g in GROOVES["parade"]:
            if int(off) == k % 8: T.add(t + (off - int(off)) * beat, drum(kind), g, -0.1 if kind == "theng" else 0.15)
        if k % 2 == 0: T.add(t, mong(156 if k % 4 == 0 else 131, 1.2), 0.42, -0.15)
        if k % 2 == 1: T.add(t, krap(), 0.55, 0.4)
        if k % 16 == 0: T.add(t, chap_yai(), 0.9, 0.2); T.add(t, drum("tum"), 1.0)
        if k % 16 == 15: T.add(t + 0.5 * beat, drum("tum"), 0.9); T.add(t + 0.75 * beat, drum("tum"), 0.8)
        for j in range(4):
            f = P.hz(run[k * 4 + j], 1); g = 0.5 if j == 0 else 0.36
            T.add(t + j * beat / 4, ranat(f), g, 0.3); T.add(t + j * beat / 4, ranat(f * 2), g * 0.7, 0.3)
        T.add(t, khong(P.hz(n), 0.9), 0.5, -0.35); T.add(t, khong(P.hz(n + 2), 0.9), 0.3, -0.35)
        if k % 2 == 0: T.add(t, ranat_thum(P.hz(0 if (k // 8) % 2 == 0 else 2, -1), 0.4), 0.6, -0.1); T.add(t, bass(P.hz(0 if (k // 8) % 2 == 0 else 2, -2), beat), 0.6)
        if k % 4 in (0, 2): T.add(t, khaen([P.hz(0), P.hz(2), P.hz(5)], beat * 1.4), 0.12, -0.45)
    for sec in range(N // 16):
        idx = skel[sec * 16:(sec + 1) * 16]
        if sec % 2 == 0: T.add(sec * 16 * beat, pi_nai([P.hz(i, 1) for i in idx], [beat] * 16, 0.9), 0.85, 0.0)
        else: T.add(sec * 16 * beat, saw([P.hz(i, 1) for i in idx[1::2]], [beat * 2] * 8), 0.8, -0.1)
    T.save("music_ending.wav", peak=0.8)

def firework():
    n = int(1.5 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(70 * (1 + 1.5 * np.exp(-t * 20))) / SR) * np.exp(-t * 5) + rng.uniform(-1, 1, n) * np.exp(-t * 14) * 0.8
    crack = np.zeros(n)
    for _ in range(60):
        i = int(rng.uniform(0.12, 1.2) * SR); m = 300; crack[i:i + m] += rng.uniform(-1, 1, m) * np.exp(-np.arange(m) / 40) * rng.uniform(0.2, 0.6) * np.exp(-i / SR * 1.5)
    s = boom * 0.9 + crack * 0.6; s = np.tanh(s * 1.2) / np.abs(s).max() * 0.85
    data = (np.stack([s, s], 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, "sfx_firework.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
    print("wrote sfx_firework.wav")

if __name__ == "__main__":
    want = sys.argv[1:]
    for n, (style, seed, bpm, base, mode, amb) in LEVELS.items():
        if want and str(n) not in want: continue
        compose("music_l%02d" % n, style, seed, bpm, base, mode, amb)
    if not want or "end" in want: ending()
