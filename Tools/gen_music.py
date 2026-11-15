#!/usr/bin/env python3
"""Synthesizes the soundtrack in the style of a Thai piphat ensemble. Needs numpy.

What makes it Thai rather than generically "East Asian":
  * tuning: 7 equal steps per octave (171 cents each), not the Western/Chinese 12-tone scale
  * texture: the khong wong (gong circle) states a plain skeleton melody while the ranat ek
    (xylophone) runs around it in constant octaves of sixteenth notes
  * colotomy: ching (ring) / chap (choke) hand cymbals mark every beat pair
  * pi nai (quadruple-reed oboe) with slides, and taphon-style drum strokes
"""
import os, wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "..", "Assets", "Resources", "Audio")
rng = np.random.default_rng(11)

BASE = 311.0                                    # pitch of scale step 0
PENT = [0, 1, 2, 4, 5]                          # the five main tones inside the 7-step octave
def step(i):                                    # melodic index -> 7-TET degree
    return 7 * (i // 5) + PENT[i % 5]
def hz7(deg):
    return BASE * 2 ** (deg / 7.0)

class Track:
    def __init__(self, seconds):
        self.n = int(seconds * SR); self.l = np.zeros(self.n); self.r = np.zeros(self.n)
    def add(self, t, sig, gain=1.0, pan=0.0):
        i = int(t * SR) % self.n
        gl = gain * np.cos((pan + 1) * np.pi / 4); gr = gain * np.sin((pan + 1) * np.pi / 4)
        k = 0
        while k < len(sig):                     # wrap tails so the loop is seamless
            m = min(len(sig) - k, self.n - i)
            self.l[i:i + m] += sig[k:k + m] * gl; self.r[i:i + m] += sig[k:k + m] * gr
            k += m; i = 0
    def save(self, name, peak=0.8, loop=True, wet=0.2, rms_db=-17.5):
        """Master and write: room reverb, a little stereo width, even loudness, soft limiter.
        For loops the reverb is convolved circularly, so tails wrap round and the loop stays seamless."""
        l, r = self.l.copy(), self.r.copy(); n = self.n
        if not loop: l = np.concatenate([l, np.zeros(SR)]); r = np.concatenate([r, np.zeros(SR)]); n = len(l)
        # impulse response: early taps + a decaying, progressively darker noise tail (a wooden hall / sala)
        g = np.random.default_rng(99); m = int(1.5 * SR); t = np.arange(m) / SR
        def ir(seed_shift):
            h = g.standard_normal(m) * np.exp(-t * 4.2)
            for _ in range(3): h = 0.5 * (h + np.roll(h, 1))                       # darken
            h[:int(0.012 * SR)] = 0                                                # pre-delay
            for d, a in ((0.017, 0.5), (0.029, -0.4), (0.043, 0.3), (0.061, 0.22)):
                h[int((d + seed_shift) * SR)] += a * 6
            return h / np.sqrt((h ** 2).sum())
        hl, hr = ir(0.0), ir(0.004)
        def conv(x, h):
            return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)
        mono = 0.5 * (l + r)
        wl = conv(l * 0.7 + mono * 0.3, hl); wr = conv(r * 0.7 + mono * 0.3, hr)
        l = l + wet * wl * 2.2; r = r + wet * wr * 2.2
        mid = 0.5 * (l + r); side = 0.5 * (l - r) * 1.25; l = mid + side; r = mid - side      # a touch wider
        rms = np.sqrt(np.mean(l ** 2 + r ** 2) / 2) + 1e-9
        gain = 10 ** (rms_db / 20) / rms
        l = np.tanh(l * gain * 1.1) / 1.1; r = np.tanh(r * gain * 1.1) / 1.1              # soft limiter
        pk = max(np.abs(l).max(), np.abs(r).max())
        if pk > 0.97: l *= 0.97 / pk; r *= 0.97 / pk
        data = (np.stack([l, r], 1) * 32767).astype("<i2")
        with wave.open(os.path.join(OUT, name), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
        print("wrote", name, "%.1fs" % (n / SR))

def env(n, a=0.002, rel=0.02):
    e = np.ones(n); na = max(1, int(a * SR)); nr = max(1, min(n, int(rel * SR)))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr)
    return e

def ranat(f, dur=0.22, hard=1.0):
    """Ranat ek: rosewood bar, hard mallet -> bright click, quick decay, tuned 4th-ish overtone."""
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 16)
         + 0.5 * hard * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 42)
         + 0.22 * hard * np.sin(2 * np.pi * f * 9.5 * t) * np.exp(-t * 90))
    s += rng.uniform(-1, 1, n) * np.exp(-t * 600) * 0.35 * hard
    return s * env(n, 0.0008, 0.015)

def ranat_thum(f, dur=0.5):
    """Ranat thum: lower, bamboo bars, padded mallet -> mellow and woody."""
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 7) + 0.25 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 30)
    return s * env(n, 0.003, 0.03)

def khong(f, dur=1.3):
    """Khong wong: small bossed bronze gong - round, bell-like, gentle beating."""
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2) + 0.6 * np.sin(2 * np.pi * f * 1.004 * t) * np.exp(-t * 3.6)
         + 0.32 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t * 5.5) + 0.14 * np.sin(2 * np.pi * f * 3.03 * t) * np.exp(-t * 9)
         + 0.08 * np.sin(2 * np.pi * f * 4.6 * t) * np.exp(-t * 16))
    return s * env(n, 0.004, 0.08)

def pi_nai(freqs, durs, gain=1.0):
    """Pi nai: reedy, nasal oboe. Takes a legato line; slides between pitches, adds vibrato and turns."""
    total = sum(durs); n = int(total * SR); t = np.arange(n) / SR
    f = np.zeros(n); pos = 0; prev = freqs[0] * 0.94
    for fr, d in zip(freqs, durs):
        m = int(d * SR); g = int(min(0.07, d * 0.35) * SR)
        seg = np.full(m, fr); seg[:g] = np.exp(np.linspace(np.log(prev), np.log(fr), g))        # slide into the note
        if d > 0.5:                                                                             # little upper turn mid-note
            k = int(m * 0.55); w = int(0.06 * SR); seg[k:k + w] *= 2 ** (1 / 7.0)
        f[pos:pos + m] = seg[:max(0, min(m, n - pos))]; pos += m; prev = fr
    f[pos:] = prev
    f *= 1 + 0.011 * np.sin(2 * np.pi * 5.8 * t) * np.minimum(1, t * 1.5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.zeros(n)
    for h in range(1, 15):
        fh = f * h
        form = 0.25 + 1.0 * np.exp(-((fh - 1250) / 520) ** 2) + 0.7 * np.exp(-((fh - 2700) / 700) ** 2)   # nasal formants
        s += np.sin(ph * h) * form / h ** 0.7
    s += np.convolve(rng.uniform(-1, 1, n), np.ones(8) / 8, "same") * 0.05
    return s * env(n, 0.03, 0.09) * gain * 0.2

def ching(open_=True):
    """Ching (rings) / chap (choked) - thick little bronze cup cymbals."""
    dur = 0.6 if open_ else 0.08
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f, a in ((2890, 1), (4410, 0.85), (5930, 0.7), (7480, 0.5), (9120, 0.35)):
        s += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    s *= np.exp(-t * (7.5 if open_ else 55))
    return s * env(n, 0.0005, 0.01) * 0.3

def drum(kind):
    """Taphon-style strokes: 'theng' (deep, open), 'ting' (high, ringing), 'pa' (slap), 'tum' (big klong that)."""
    if kind == "theng": f, dec, dur, nz = 92, 9, 0.4, 0.2
    elif kind == "ting": f, dec, dur, nz = 255, 17, 0.25, 0.12
    elif kind == "tum": f, dec, dur, nz = 62, 6, 0.6, 0.3
    else: f, dec, dur, nz = 330, 45, 0.1, 1.0
    n = int(dur * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.5 * np.exp(-t * 40))) / SR
    s = np.sin(ph) * np.exp(-t * dec) + 0.3 * np.sin(1.6 * ph) * np.exp(-t * dec * 1.8) + rng.uniform(-1, 1, n) * np.exp(-t * 180) * nz
    return s * env(n, 0.001, 0.02)

def mong(f=156, dur=2.2):
    """Khong mong: the hanging gong that answers the drums."""
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + 0.4 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 3.5) + 0.15 * np.sin(2 * np.pi * f * 2.97 * t) * np.exp(-t * 5)
    return s * (1 + 0.08 * np.sin(2 * np.pi * 4 * t)) * env(n, 0.006, 0.2)

def weave(skel):
    """Ranat ek realisation: four sixteenths per beat that walk stepwise into the next skeleton tone."""
    out = []
    for k, a in enumerate(skel):
        b = skel[(k + 1) % len(skel)]; d = b - a; sg = 1 if d > 0 else -1
        if d == 0: g = [a, a + 1, a, a - 1]
        elif abs(d) == 1: g = [a, a - sg, a, b + sg] if k % 2 else [a, a + sg * 2, a + sg, a]
        else: g = [a, a + sg, a + int(round(d * 0.5)), b - sg]
        out += g
    return out

# skeleton phrases, 16 beats each, as indices into the five-tone ladder (5 = one octave up)
A  = [4, 5, 4, 3,  2, 3, 4, 5,  6, 5, 4, 3,  4, 3, 2, 2]
A2 = [4, 5, 4, 3,  2, 3, 4, 5,  7, 6, 5, 6,  5, 4, 5, 5]
B  = [7, 6, 5, 6,  7, 8, 7, 6,  5, 6, 5, 4,  3, 4, 5, 5]
B2 = [7, 8, 9, 8,  7, 6, 7, 8,  7, 6, 5, 4,  5, 4, 3, 2]
C  = [2, 2, 4, 5,  7, 5, 4, 5,  2, 3, 4, 3,  2, 1, 0, 0]
C2 = [0, 1, 2, 3,  4, 3, 2, 3,  4, 5, 6, 5,  4, 3, 4, 4]

def level_theme():
    bpm = 126; beat = 60 / bpm; s16 = beat / 4
    form = [A, A2, B, A2, C, C2, B2, A]
    skel = [n for ph in form for n in ph]
    T = Track(len(skel) * beat)
    run = weave(skel)
    for k, n in enumerate(skel):
        t = k * beat; sec = k // 16
        # khong wong: the plain melody, with an octave on phrase endings
        T.add(t, khong(hz7(step(n))), 0.5, -0.35)
        if k % 16 == 15: T.add(t, khong(hz7(step(n) - 7)), 0.4, -0.35)
        # ching / chap
        T.add(t, ching(k % 2 == 0), 0.42 if k % 2 == 0 else 0.6, 0.55)
        # drums: a rolling eight-beat cycle with a fill at the end of each phrase
        c = k % 8
        pat = {0: [(0, "theng", 0.9)], 1: [(0, "ting", 0.5), (0.5, "pa", 0.4)], 2: [(0, "theng", 0.75), (0.5, "ting", 0.4)], 3: [(0, "pa", 0.5), (0.5, "ting", 0.5)],
               4: [(0, "theng", 0.9), (0.75, "ting", 0.35)], 5: [(0, "ting", 0.5), (0.5, "theng", 0.6)], 6: [(0, "pa", 0.5), (0.5, "ting", 0.5)], 7: [(0, "theng", 0.8), (0.5, "pa", 0.45), (0.75, "pa", 0.4)]}[c]
        if k % 16 == 15: pat = [(0, "tum", 0.9), (0.25, "ting", 0.5), (0.5, "tum", 0.8), (0.75, "pa", 0.6)]
        if sec >= 1 or k >= 8:
            for off, kind, g in pat: T.add(t + off * beat, drum(kind), g, 0.1 if kind != "tum" else -0.1)
        if k % 4 == 3 and sec >= 2: T.add(t, mong(), 0.3, -0.1)
        # ranat ek in running octaves (drops out for the first half phrase, softer under the pi)
        if k >= 8:
            quiet = sec in (4, 5)
            for j in range(4):
                n16 = run[k * 4 + j]; g = (0.5 if j == 0 else 0.36) * (0.6 if quiet else 1.0)
                T.add(t + j * s16, ranat(hz7(step(n16) + 7)), g, 0.3); T.add(t + j * s16, ranat(hz7(step(n16) + 14)), g * 0.75, 0.3)
        # ranat thum: syncopated answers an octave below
        if sec >= 1 and k % 2 == 1:
            T.add(t + beat * 0.5, ranat_thum(hz7(step(n) - 7)), 0.5, -0.1); T.add(t + beat * 0.75, ranat_thum(hz7(step(skel[(k + 1) % len(skel)] + 1) - 7)), 0.35, -0.1)
    # pi nai sings a broadened version of the tune over sections C and C2, and the last B2
    for sec in (4, 5, 6):
        ph = form[sec]; fr = []; du = []
        for q in range(0, 16, 2): fr.append(hz7(step(ph[q + 1]) + 7)); du.append(beat * 2)
        T.add(sec * 16 * beat, pi_nai(fr, du), 1.0, 0.0)
    T.add(0, mong(110, 3.0), 0.5)
    T.save("music_level.wav")

def krap(dur=0.07):
    """Krap: hardwood clappers."""
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * 1450 * t) + 0.6 * np.sin(2 * np.pi * 2300 * t)) * np.exp(-t * 70) + rng.uniform(-1, 1, n) * np.exp(-t * 250) * 0.5
    return s * env(n, 0.0005, 0.01)

def chap_yai(dur=1.4):
    """Chap yai: the big flat cymbals that crash on section starts."""
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in (1830, 2470, 3120, 3960, 4850, 6100, 7300, 8900):
        s += np.sin(2 * np.pi * f * (1 + 0.002 * rng.uniform(-1, 1)) * t + rng.uniform(0, 6.28)) / (f / 1830) ** 0.5
    s += rng.uniform(-1, 1, n) * 0.6
    return s * np.exp(-t * 4.5) * env(n, 0.001, 0.1) * 0.16

def title_theme():
    """Catchy title tune in the style of a klong yao (long drum) parade: a short hook that keeps coming
    back, call and answer, festive 'pa - theng - mong' drumming, clappers on the off-beats."""
    bpm = 138; beat = 60 / bpm; e8 = beat / 2; bar = 4 * beat
    R = None
    H1 = [5, 5, 7, 5,  4, 5, R, 5,   7, 7, 9, 7,  5, R, R, R]          # the hook
    H2 = [9, 9, 7, 9,  10, 9, 7, 5,  4, 5, 7, 5,  4, R, 2, R]          # its answer
    H2b = [9, 9, 7, 9, 10, 9, 7, 5,  4, 5, 7, 9,  10, R, 10, R]        # answer that lifts into the bridge
    H3 = [10, R, 10, 9, 7, 9, 10, R, 12, R, 10, 9, 7, R, R, R]         # bridge, higher
    H4 = [9, 7, 5, 7,  9, 7, 5, 4,   2, 4, 5, 4,  5, R, 5, R]
    form = [None, H1, H2, H1, H2b, H3, H4, H3, H4, H1, H2, H1, H2]      # None = two-bar drum break
    T = Track(len(form) * 2 * bar)
    for si, ph in enumerate(form):
        t0 = si * 2 * bar
        last = si == len(form) - 1
        if si in (1, 5, 9): T.add(t0, chap_yai(), 0.9, 0.2)
        # ---- klong yao drums + gong + cymbals + clappers (two-bar cycle)
        for b in range(8):
            t = t0 + b * beat
            T.add(t, ching(b % 2 == 0), 0.4 if b % 2 == 0 else 0.6, 0.55)
            if b % 2 == 0: T.add(t, mong(156 if b % 4 == 0 else 131, 1.2), 0.42, -0.15)
            if b % 2 == 1 and si > 0: T.add(t, krap(), 0.55, 0.4); T.add(t + e8 * 0.5 if b % 4 == 3 else t, krap(), 0.0)
        drums = [(0, "theng", 1.0), (0.75, "pa", 0.5), (1, "pa", 0.6), (1.5, "theng", 0.85), (2, "theng", 0.9), (2.5, "pa", 0.55), (3, "ting", 0.6), (3.5, "pa", 0.55),
                 (4, "theng", 1.0), (4.75, "pa", 0.5), (5, "pa", 0.6), (5.5, "theng", 0.85), (6, "pa", 0.6), (6.5, "theng", 0.8), (7, "theng", 0.9), (7.25, "pa", 0.5), (7.5, "pa", 0.6), (7.75, "ting", 0.5)]
        if ph is None:      # break: the drums talk on their own
            drums = [(0, "tum", 1.0), (0.5, "pa", 0.6), (1, "theng", 0.9), (1.5, "pa", 0.6), (1.75, "pa", 0.5), (2, "tum", 1.0), (2.5, "theng", 0.8), (3, "pa", 0.7), (3.5, "pa", 0.6),
                     (4, "theng", 0.9), (4.5, "theng", 0.8), (5, "pa", 0.7), (5.5, "theng", 0.8), (6, "pa", 0.6), (6.25, "pa", 0.6), (6.5, "theng", 0.9), (6.75, "pa", 0.6), (7, "tum", 1.0), (7.5, "tum", 0.9)]
        for off, kind, g in drums: T.add(t0 + off * beat, drum(kind), g * 0.95, -0.1 if kind in ("theng", "tum") else 0.15)
        if ph is None: continue
        # ---- the tune: ranat ek in octaves (long notes become rolls), khong wong on the beat, low ranat ostinato
        high = si >= 9
        for i, n in enumerate(ph):
            t = t0 + i * e8
            if n is None: continue
            length = 1
            while i + length < 16 and ph[i + length] is None: length += 1
            reps = 1 if length == 1 else length * 2          # tremolo roll through held notes
            for r in range(reps):
                tt = t + r * e8 / 2; g = (0.6 if r == 0 else 0.34) * (1.0 if i % 2 == 0 else 0.85)
                T.add(tt, ranat(hz7(step(n) + 7)), g, 0.3); T.add(tt, ranat(hz7(step(n) + 14)), g * 0.7, 0.3)
            if i % 2 == 0: T.add(t, khong(hz7(step(n)), 0.9), 0.5, -0.35)
        ost = [0, R, 2, R, 0, 0, 2, R,  0, R, 2, R, 3, 2, 0, R] if ph not in (H3, H4) else [2, R, 4, R, 2, 2, 4, R,  2, R, 4, R, 5, 4, 2, R]
        for i, n in enumerate(ost):
            if n is not None: T.add(t0 + i * e8, ranat_thum(hz7(step(n) - 7), 0.4), 0.6, -0.1)
        # ---- pi nai doubles the hook on the bridge and the last time round, sliding between the notes
        if ph in (H3, H4) or high:
            fr, du = [], []
            for i, n in enumerate(ph):
                if n is None:
                    if du: du[-1] += e8
                    continue
                fr.append(hz7(step(n) + 7)); du.append(e8)
            T.add(t0, pi_nai(fr, du, 0.9), 0.85, 0.0)
    T.save("music_title.wav", peak=0.78)

def win_jingle():
    beat = 60 / 150; s16 = beat / 4
    T = Track(6.4)
    up = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 9, 10, 9, 10, 10]
    for i, n in enumerate(up):
        T.add(i * s16, ranat(hz7(step(n) + 7), 0.3), 0.55, 0.25); T.add(i * s16, ranat(hz7(step(n) + 14), 0.3), 0.4, 0.25)
    for i, n in enumerate([5, 7, 9, 10]):
        T.add(i * beat, khong(hz7(step(n)), 2.5), 0.6, -0.3); T.add(i * beat, ching(i % 2 == 0), 0.5, 0.5)
    t = 4 * beat
    for n in (5, 7, 10): T.add(t, khong(hz7(step(n)), 4.0), 0.6, -0.2)
    T.add(t, mong(110, 4.0), 0.7); T.add(t, drum("tum"), 1.0); T.add(t + s16 * 2, drum("tum"), 0.8); T.add(t, ching(True), 0.6, 0.5)
    for j in range(24): T.add(t + 0.2 + j * 0.07, ranat(hz7(step(10) + 7 + (7 if j % 2 else 0)), 0.2), 0.3 * (1 - j / 26), 0.25)     # tremolo roll
    T.save("jingle_win.wav", loop=False, rms_db=-19)

if __name__ == "__main__":
    level_theme(); title_theme(); win_jingle()
