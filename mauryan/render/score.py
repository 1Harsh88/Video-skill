"""Original score (no third-party music) + transition SFX pool for the Mauryan video.
Writes out/audio/score.wav (13:04.7) and out/audio/sfx/*.wav"""
import numpy as np, wave, os
SR = 44100; DUR = 784.67
OUT = "/home/user/mproj/out/audio"; os.makedirs(f"{OUT}/sfx", exist_ok=True)
rng = np.random.default_rng(11)

def write(path, x):
    x = np.clip(x, -1, 1); st = x if x.ndim == 2 else np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())

def hz(semi, base=146.83): return base * 2 ** (semi / 12)   # D3 = Sa
def env_adsr(n, a, r):
    t = np.arange(n) / SR; e = np.minimum(1, t / max(a, 1e-3)); e *= np.clip((n / SR - t) / max(r, 1e-3), 0, 1); return e.astype(np.float32)
def lp(x, k):   # one-pole lowpass, k in (0,1]
    y = np.empty_like(x); acc = 0.0
    for i in range(0, len(x), 4096):
        seg = x[i:i + 4096]; out = np.empty_like(seg)
        for j, v in enumerate(seg): acc += k * (v - acc); out[j] = acc
        y[i:i + 4096] = out
    return y
def lp_fast(x, cutoff):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / (1 + (f / cutoff) ** 4); return np.fft.irfft(X, len(x)).astype(np.float32)

N = int(DUR * SR); T = np.arange(N, dtype=np.float32) / SR
mix = np.zeros((N, 2), np.float32)

def add(x, start, gain=1.0, pan=0.0):
    s = int(start * SR); e = min(N, s + len(x))
    if e <= s: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[s:e, 0] += x[:e - s] * gain * l; mix[s:e, 1] += x[:e - s] * gain * r

# ---------- section map (start, end, mood) ----------
SECT = [(0, 33.4, "dark"), (33.4, 184.4, "story"), (184.4, 228.2, "march"), (228.2, 335.1, "majesty"), (335.1, 380.3, "tender"),
        (380.3, 416.2, "dark"), (416.2, 499.4, "tension"), (499.4, 550.5, "war"), (550.5, 720.0, "peace"), (720.0, 748.6, "dark"), (748.6, DUR, "resolve")]

# ---------- tanpura-like drone (Sa-Pa-Sa'-Sa, buzzing) ----------
def tanpura(seconds, base=146.83, level=.18):
    n = int(seconds * SR); out = np.zeros(n, np.float32); t = np.arange(n) / SR
    notes = [base * 1.5 / 2, base, base, base / 2]           # Pa(low) Sa Sa Sa(low)
    pluck = 0.0; i = 0
    while pluck < seconds:
        f = notes[i % 4]; m = int(3.2 * SR); s = int(pluck * SR)
        tt = np.arange(m) / SR; e = np.exp(-tt / 2.4) * (1 - np.exp(-tt * 40))
        tone = sum(np.sin(2 * np.pi * f * h * tt + h) / h ** 0.9 for h in range(1, 14))
        tone *= 1 + 0.35 * np.sin(2 * np.pi * 0.7 * tt)        # jawari shimmer
        seg = (tone * e).astype(np.float32); e2 = min(n, s + m); out[s:e2] += seg[:e2 - s]
        pluck += 0.62; i += 1
    return out / np.max(np.abs(out) + 1e-6) * level

def pad(seconds, semis, base=146.83, level=.12, bright=900):
    n = int(seconds * SR); t = np.arange(n) / SR; x = np.zeros(n, np.float32)
    for s in semis:
        f = hz(s, base)
        for d in (-0.15, 0, 0.17):
            ph = rng.uniform(0, 6.28)
            saw = sum(np.sin(2 * np.pi * f * (1 + d / 100) * k * t + ph * k) / k for k in range(1, 9))
            x += saw.astype(np.float32)
    x = lp_fast(x, bright); x *= env_adsr(n, 3, 3)
    return x / (np.max(np.abs(x)) + 1e-6) * level

SCALE = [0, 1, 3, 5, 7, 8, 10, 12, 13, 15]   # Bhairavi-like
def bansuri(seconds, seed, base=293.66, level=.10, density=.5):
    r = np.random.default_rng(seed); n = int(seconds * SR); x = np.zeros(n, np.float32); t = 0.6; idx = 4
    while t < seconds - 1:
        L = r.choice([0.9, 1.4, 2.2, 3.0]); idx = int(np.clip(idx + r.choice([-2, -1, -1, 0, 1, 1, 2]), 0, len(SCALE) - 1))
        f = hz(SCALE[idx], base); m = int(L * SR); tt = np.arange(m) / SR
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * tt) * np.clip(tt / .4, 0, 1)
        glide = 1 + 0.03 * np.exp(-tt * 12) * r.choice([-1, 1])
        ph = np.cumsum(2 * np.pi * f * vib * glide / SR)
        tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
        breath = r.standard_normal(m) * 0.035
        e = env_adsr(m, 0.12, 0.5)
        s = int(t * SR); e2 = min(n, s + m); x[s:e2] += ((tone + breath) * e)[:e2 - s].astype(np.float32)
        t += L + r.choice([0.2, 0.6, 1.2, 2.5]) / density
    x = lp_fast(x, 3500)
    return x / (np.max(np.abs(x)) + 1e-6) * level

def drum_hit(kind, r):
    m = int(0.9 * SR); tt = np.arange(m) / SR
    if kind == "dha":     # deep dhol / bayan
        f = 70 + 60 * np.exp(-tt * 18); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5)
    elif kind == "na":    # tabla-like ring
        x = (np.sin(2 * np.pi * 520 * tt) + .4 * np.sin(2 * np.pi * 1040 * tt)) * np.exp(-tt * 14) * .5
    else:                 # slap
        x = r.standard_normal(m) * np.exp(-tt * 40) * .4 + np.sin(2 * np.pi * 180 * tt) * np.exp(-tt * 20) * .4
    return x.astype(np.float32)

def rhythm(seconds, bpm, pattern, seed, level=.22):
    r = np.random.default_rng(seed); n = int(seconds * SR); x = np.zeros(n, np.float32); step = 60 / bpm / 2; t = 0; i = 0
    while t < seconds:
        k = pattern[i % len(pattern)]
        if k != ".":
            h = drum_hit({"D": "dha", "n": "na", "s": "slap"}[k], r) * r.uniform(.75, 1.0)
            s = int(t * SR); e = min(n, s + len(h)); x[s:e] += h[:e - s]
        t += step; i += 1
    return x / (np.max(np.abs(x)) + 1e-6) * level

def heartbeat(seconds, bpm=58, level=.2):
    n = int(seconds * SR); x = np.zeros(n, np.float32); t = 0.3
    while t < seconds:
        for off, g in ((0, 1), (0.28, .6)):
            m = int(.35 * SR); tt = np.arange(m) / SR
            h = np.sin(2 * np.pi * (45 + 30 * np.exp(-tt * 20)) * tt) * np.exp(-tt * 9) * g
            s = int((t + off) * SR); e = min(n, s + m); x[s:e] += h[:e - s].astype(np.float32)
        t += 60 / bpm
    return x * level

def wind(seconds, level=.07, seed=5):
    r = np.random.default_rng(seed); n = int(seconds * SR); x = lp_fast(r.standard_normal(n).astype(np.float32), 500)
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * np.arange(n) / SR / 7.0)
    return x / (np.max(np.abs(x)) + 1e-6) * level * mod

def fade(x, a=2.0, b=2.0):
    n = len(x); e = np.ones(n, np.float32); A, B = int(a * SR), int(b * SR)
    e[:A] = np.linspace(0, 1, A); e[-B:] = np.minimum(e[-B:], np.linspace(1, 0, B)); return x * e

for k, (s, e, mood) in enumerate(SECT):
    L = e - s + 2.0
    if mood in ("story", "majesty", "tender", "peace", "resolve"):
        add(fade(tanpura(L, level=.11)), s, pan=-.2)
        chords = {"story": [0, 7, 12], "majesty": [0, 3, 7, 12], "tender": [0, 3, 7], "peace": [0, 7, 15], "resolve": [0, 4, 7, 12]}[mood]
        add(fade(pad(L, chords, level=.07, bright=1200 if mood == "majesty" else 800), 3, 3), s, pan=.2)
        add(fade(bansuri(L, k, density={"story": .5, "majesty": .6, "tender": .4, "peace": .35, "resolve": .45}[mood], level=.06)), s, pan=.15)
        if mood in ("story", "majesty"): add(fade(rhythm(L, 72, "D..n.n..D.n.s..", k, level=.07)), s)
    elif mood == "march":
        add(fade(tanpura(L, level=.10)), s); add(fade(rhythm(L, 96, "D.nDs.nDD.n.s.nn", k, level=.16)), s)
        add(fade(pad(L, [0, 7, 12, 15], level=.07, bright=1500)), s)
    elif mood == "war":
        add(fade(rhythm(L, 110, "DDs.DnsDD.sDn.sD", k, level=.2)), s); add(fade(pad(L, [-12, 0, 1, 7], level=.09, bright=700)), s)
        add(fade(wind(L, .05)), s)
    elif mood == "tension":
        add(fade(pad(L, [0, 1, 7], level=.08, bright=600)), s); add(fade(rhythm(L, 64, "D.......n.......", k, level=.08)), s)
        add(fade(tanpura(L, level=.06)), s)
    else:  # dark
        add(fade(pad(L, [-12, 0, 1], level=.09, bright=400), 2, 2), s); add(fade(heartbeat(L, level=.14)), s); add(fade(wind(L, .05)), s)

mix = mix / (np.max(np.abs(mix)) + 1e-6) * 0.7
write(f"{OUT}/score.wav", mix)

# ---------- transition SFX pool (12 different sounds) ----------
def S(name, x): write(f"{OUT}/sfx/{name}.wav", (x / (np.max(np.abs(x)) + 1e-6) * .9).astype(np.float32))
def tt(sec): return np.arange(int(sec * SR), dtype=np.float32) / SR
t = tt(1.2); S("wind_gust", lp_fast(rng.standard_normal(len(t)).astype(np.float32), 900) * np.sin(np.pi * t / 1.2) ** 2)
t = tt(1.4); S("reverse_cymbal", (rng.standard_normal(len(t)) * (t / 1.4) ** 3).astype(np.float32) * (1 - lp_fast(np.ones(len(t), np.float32), 1)))
t = tt(1.6); S("deep_boom", np.sin(2 * np.pi * (40 + 50 * np.exp(-t * 6)) * t) * np.exp(-t * 2.2) + lp_fast(rng.standard_normal(len(t)).astype(np.float32), 200) * np.exp(-t * 4) * .5)
t = tt(1.8); S("riser", np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / 1.8) ** 2) / SR) * (t / 1.8) ** 2 * .6 + lp_fast(rng.standard_normal(len(t)).astype(np.float32), 3000) * (t / 1.8) ** 3 * .4)
t = tt(0.6); S("cloth_swish", lp_fast(rng.standard_normal(len(t)).astype(np.float32), 2500) * np.sin(np.pi * t / .6) ** 3)
t = tt(1.0); S("fire_whoosh", lp_fast(rng.standard_normal(len(t)).astype(np.float32), 1200) * np.sin(np.pi * t) ** 2 * (1 + .5 * np.sin(2 * np.pi * 23 * t)))
t = tt(1.5); S("sword_shing", sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2400, 3), (3700, 4), (5200, 6))) * np.clip(t / .03, 0, 1) + rng.standard_normal(len(t)) * np.exp(-t * 30) * .3)
t = tt(2.2); S("chime", sum(np.sin(2 * np.pi * f * t) * np.exp(-t * 1.8) for f in (1318, 1975, 2637)) / 3)
t = tt(3.0); S("temple_bell", sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((523, 1, 1.0), (1046, .5, 1.4), (1568, .35, 2.0), (2093, .2, 2.6), (2800, .15, 3.5))))
t = tt(1.0); S("drum_hit", np.sin(2 * np.pi * (60 + 80 * np.exp(-t * 25)) * t) * np.exp(-t * 6) + rng.standard_normal(len(t)) * np.exp(-t * 50) * .3)
t = tt(1.4); S("sub_drop", np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 2.5) + 30) / SR) * np.exp(-t * 1.6))
t = tt(0.9); S("sand_swish", lp_fast(rng.standard_normal(len(t)).astype(np.float32), 5000) * np.sin(np.pi * t / .9) ** 4 * .7)
print("score + sfx written")
