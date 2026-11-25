"""Bisleri audio: original tense news-bed score + synthesized/pooled varied SFX on every MG event + low clip ambience + VO."""
import numpy as np, subprocess, wave, random, math, os
SR = 44100; END = 98.04; N = int(END * SR)
ROOT = "/home/user/bproj"; CLIPS = "/home/user/bisleri/dl/x/zip-staging/videos"; POOLD = "/home/user/mproj/out/audio/sfx"
SECT = [0.0, 9.86, 17.78, 25.24, 36.58, 46.63, 54.50, 64.18, 75.84, 85.77, END]
rng = np.random.default_rng(5)

def load(path, extra=()):
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, *extra, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(b, np.float32).reshape(-1, 2).copy()
def put(buf, x, t, g=1.0):
    s = int(t * SR)
    if s < 0: x = x[-s:]; s = 0
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * g
def db(d): return 10 ** (d / 20)
def st(m): return np.stack([m, m], 1).astype(np.float32)
def env(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def lp(x, fc):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR); X *= (1 / (1 + (f / fc) ** 4))[:, None] if x.ndim == 2 else 1 / (1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x), axis=0).astype(np.float32)
def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= ((f > lo) & (f < hi)); return np.fft.irfft(X, len(x)).astype(np.float32)
def smooth(x, k):
    c = np.cumsum(np.pad(x, (k // 2, k - k // 2)).astype(np.float64)); return ((c[k:] - c[:-k]) / k)[:len(x)].astype(np.float32)
def note(m): return 440 * 2 ** ((m - 69) / 12)

# ------------------------------------------------------------------ score
t_all = np.arange(N) / SR
BEAT = 0.6; BAR = 4 * BEAT
INT = [(0, .75), (9.86, .5), (17.78, .7), (25.24, .6), (36.58, .9), (46.63, .6), (54.5, .5), (64.18, .8), (69.64, 1.0), (75.84, .6), (85.77, .5), (94.6, .35)]
def intensity(t): return [v for s, v in INT if s <= t][-1]
CH = [[50, 53, 57], [46, 50, 53], [43, 46, 50], [45, 49, 52]]   # Dm Bb Gm A
STOPS = [(6.85, 7.25), (36.2, 36.58), (69.2, 69.64), (94.3, 94.67)]
mus = np.zeros((N, 2), np.float32)
# pad
pad = np.zeros(N, np.float32)
for i in range(int(END / (2 * BAR)) + 1):
    t0 = i * 2 * BAR; ch = CH[i % 4]; n = int(2 * BAR * SR); tt = np.arange(n) / SR
    seg = np.zeros(n, np.float32)
    for m in ch + [ch[0] + 12]:
        for det in (-.12, .12):
            f0 = note(m + det / 1)
            for h in range(1, 6): seg += np.sin(2 * np.pi * f0 * h * tt + h) / (h ** 1.6) * .05
    seg *= np.minimum(1, tt / 1.2) * np.minimum(1, (2 * BAR - tt) / .8)
    s = int(t0 * SR); e = min(N, s + n); pad[s:e] += seg[:e - s]
pad = lp(pad, 1800)
# bass pulse (8ths)
bass = np.zeros(N, np.float32)
for k in range(int(END / (BEAT / 2))):
    t0 = k * BEAT / 2; ch = CH[int(t0 // (2 * BAR)) % 4]; f0 = note(ch[0] - 12)
    n = int(.28 * SR); tt = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f0 * tt) + .35 * np.sin(2 * np.pi * 2 * f0 * tt)) * env(n, .005, .09) * (.9 if k % 2 == 0 else .6)
    s = int(t0 * SR); e = min(N, s + n); bass[s:e] += x[:e - s] * .35
# ticking clock hats (16ths)
hat = np.zeros(N, np.float32)
nz = bp(rng.standard_normal(int(.05 * SR)).astype(np.float32), 6000, 14000)
for k in range(int(END / (BEAT / 4))):
    t0 = k * BEAT / 4; n = len(nz); x = nz * env(n, .001, .012 if k % 4 else .03) * (.5 if k % 2 else .8)
    s = int(t0 * SR); e = min(N, s + n); hat[s:e] += x[:e - s] * .12
# kick on beats
kick = np.zeros(N, np.float32)
n = int(.35 * SR); tt = np.arange(n) / SR; kx = np.sin(2 * np.pi * (45 * tt + 90 * (1 - np.exp(-tt * 30)) / 30)) * env(n, .002, .12)
for k in range(int(END / BEAT)):
    t0 = k * BEAT; s = int(t0 * SR); e = min(N, s + n); kick[s:e] += kx[:e - s] * .5
# arpeggio plucks (higher sections)
arp = np.zeros(N, np.float32)
for k in range(int(END / (BEAT / 2))):
    t0 = k * BEAT / 2; ch = CH[int(t0 // (2 * BAR)) % 4]; m = ch[k % 3] + 12 + (12 if k % 8 == 7 else 0)
    n = int(.5 * SR); tt = np.arange(n) / SR; f0 = note(m)
    x = (np.sin(2 * np.pi * f0 * tt) + .3 * np.sin(2 * np.pi * 3 * f0 * tt)) * env(n, .003, .16)
    s = int(t0 * SR); e = min(N, s + n); arp[s:e] += x[:e - s] * .07
# per-layer intensity gating
I = np.array([intensity(x) for x in np.arange(0, END, .01)], np.float32); I = np.interp(t_all, np.arange(len(I)) * .01, I).astype(np.float32)
I = smooth(I, int(.3 * SR))
mono = pad * (.7 + .3 * I) + bass * np.clip(I * 1.2 - .1, 0, 1) + hat * np.clip(I * 1.4 - .5, 0, 1) + kick * np.clip(I * 2 - 1.1, 0, 1) + arp * np.clip(1.1 - I, 0, 1)
for a, b in STOPS:   # tension stops before hits
    s, e = int(a * SR), int(b * SR); ramp = np.linspace(1, .05, min(int(.08 * SR), e - s)); mono[s:s + len(ramp)] *= ramp; mono[s + len(ramp):e] *= .05
    r2 = int(.25 * SR); mono[e:e + r2] *= np.linspace(.3, 1, r2)
fo = int(2.5 * SR); mono[-fo:] *= np.linspace(1, 0, fo)
mono[:int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))
mus = np.stack([mono * 1.0, np.roll(mono, 300) * .96], 1).astype(np.float32)   # tiny width
mus /= np.abs(mus).max() + 1e-9

# ------------------------------------------------------------------ SFX
def s_stamp():
    n = int(.5 * SR); tt = np.arange(n) / SR
    th = np.sin(2 * np.pi * (60 * tt + 80 * (1 - np.exp(-tt * 40)) / 40)) * env(n, .001, .1)
    cl = bp(rng.standard_normal(n).astype(np.float32), 800, 5000) * env(n, .0005, .025) * .8
    return st(th + cl)
def s_pop():
    n = int(.12 * SR); tt = np.arange(n) / SR; f = 900 * np.exp(-tt * 18) + 300
    return st(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .035) * .7)
def s_tick():
    n = int(.04 * SR); return st(bp(rng.standard_normal(n).astype(np.float32), 2000, 9000) * env(n, .0003, .006) * 1.4)
def s_beep(f=1250, d=.09):
    n = int(d * SR); tt = np.arange(n) / SR; return st(np.sin(2 * np.pi * f * tt) * np.minimum(1, (d - tt) / .01) * np.minimum(1, tt / .005) * .35)
def s_ding():
    n = int(.9 * SR); tt = np.arange(n) / SR; x = sum(np.sin(2 * np.pi * 1318 * r * tt) * a for r, a in ((1, 1), (2.01, .4), (3.03, .2))) * env(n, .002, .25)
    return st(x * .3)
def s_buzz():
    n = int(.35 * SR); tt = np.arange(n) / SR; x = np.sign(np.sin(2 * np.pi * 140 * tt)) * .3 + np.sign(np.sin(2 * np.pi * 147 * tt)) * .3
    return st(lp(x.astype(np.float32), 2500) * np.minimum(1, (.35 - tt) / .03) * .6)
def s_glitch():
    n = int(.45 * SR); x = np.zeros(n, np.float32); p = 0
    while p < n:
        L = int(rng.integers(400, 3000)); kind = rng.integers(0, 3)
        seg = rng.standard_normal(L) if kind == 0 else np.sign(np.sin(2 * np.pi * rng.uniform(80, 900) * np.arange(L) / SR))
        if kind == 2: seg = np.zeros(L)
        x[p:p + L] = seg[:n - p] * .5; p += L
    x = np.round(x * 6) / 6; return st(x * env(n, .001, .25))
def s_whoosh(d=.55, up=True):
    n = int(d * SR); nz_ = rng.standard_normal(n).astype(np.float32); out = np.zeros(n, np.float32); hop = 1024
    for i in range(0, n, hop):
        fr = i / n; fc = 400 + 5000 * (fr if up else 1 - fr)
        out[i:i + hop] = bp(np.pad(nz_[i:i + hop], (0, max(0, hop - len(nz_[i:i + hop])))), fc * .5, fc * 1.6)[:len(out[i:i + hop])]
    e = np.sin(np.pi * np.arange(n) / n) ** 2; return st(out * e * .6)
def s_typing(d):
    x = np.zeros((int(d * SR) + SR // 10, 2), np.float32); t = 0
    while t < d: put(x, s_tick() * rng.uniform(.5, 1), t); t += rng.uniform(.05, .13)
    return x
def s_counter(d):
    x = np.zeros((int(d * SR) + SR // 10, 2), np.float32); t = 0; k = 0
    while t < d: put(x, s_beep(1800 + 40 * (k % 6), .025), t, .6); t += .055 + .06 * (t / d) ** 2; k += 1
    return x
pool = {n[:-4]: load(f"{POOLD}/{n}") for n in ("riser.wav", "sub_drop.wav", "deep_boom.wav", "reverse_cymbal.wav", "cloth_swish.wav", "sand_swish.wav")}
def pitch(x, f):
    idx = np.arange(0, len(x) - 1, f); return np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], 1).astype(np.float32)

fx = np.zeros((N, 2), np.float32)
def P(t, x, g=0, var=True):
    if var: x = pitch(x, rng.uniform(.88, 1.12))
    put(fx, x, t, db(g))
def END_AT(t, x, g=0): put(fx, x, t - len(x) / SR + .03, db(g))

# section transitions (match video: flash, glitch, whip, zoom, leak, glitch, whip, flash, zoom)
TR = ["flash", "glitch", "whip", "zoom", "leak", "glitch", "whip", "flash", "zoom"]
for i, tr in enumerate(TR, 1):
    t = SECT[i]
    if tr == "flash": P(t - .05, pool["sub_drop"], -8); P(t - .2, s_whoosh(.4), -10)
    elif tr == "glitch": P(t - .02, s_glitch(), -12)
    elif tr == "whip": P(t - .25, s_whoosh(.45, False), -8); P(t - .1, pool["cloth_swish"], -12)
    elif tr == "zoom": END_AT(t, pool["riser"], -14); P(t, pool["deep_boom"], -12)
    elif tr == "leak": END_AT(t, pool["reverse_cymbal"], -12); P(t, pool["sand_swish"], -14)
# MG events
P(0.0, pool["deep_boom"], -9)
for t in (.42, 1.14, 1.56, 1.88): P(t, s_pop(), -10)
P(2.8, s_whoosh(.35), -14); P(6.25, s_beep(), -14); P(7.25, s_stamp(), -4); P(7.25, pool["sub_drop"], -10)
P(10.95, s_whoosh(.35), -14); P(11.05, s_tick(), -8); P(13.44, s_pop(), -12); P(15.0, s_pop(), -11)
for i in range(6): P(16.1 + i * .09, s_tick(), -8)
for i in range(5): P(17.8 + i * .2, s_beep(1500 + 120 * i, .06), -14)
P(19.52, s_buzz(), -12); P(19.52, s_stamp(), -9); P(20.0, s_whoosh(.4), -15); P(20.97, s_counter(.8), -12)
P(23.3, s_beep(900, .08), -13); P(23.5, s_beep(900, .08), -13); P(24.0, s_pop(), -11)
P(25.24, s_tick(), -8); P(28.05, s_pop(), -12); P(28.78, s_whoosh(.35), -15); P(29.4, s_whoosh(.8), -17); P(30.9, s_ding(), -12)
P(33.5, s_glitch(), -10); P(33.5, pool["sub_drop"], -10); P(34.7, s_pop(), -10)
P(36.58, s_glitch(), -9); P(36.58, pool["deep_boom"], -7); P(38.16, s_buzz(), -16); P(39.4, s_pop(), -13)
P(42.18, s_whoosh(.4), -14); P(42.9, s_counter(1.5), -13); P(44.6, s_pop(), -12)
P(49.5, s_ding(), -12); P(51.3, s_beep(700, .12), -14); P(51.8, s_beep(700, .12), -15); P(52.9, s_stamp(), -6)
P(54.6, s_tick(), -8); P(56.9, s_pop(), -12); P(57.3, s_whoosh(1.2), -14); P(58.4, s_pop(), -12)
P(59.6, s_typing(1.0), -12); P(60.7, s_pop(), -11); P(62.63, pool["sub_drop"], -11)
for k in range(13): P(64.6 + 2.4 * k / 12, s_tick(), -11)
P(66.64, s_ding(), -12); END_AT(69.64, pool["riser"], -12); P(69.64, s_stamp(), -3); P(69.64, pool["deep_boom"], -8)
P(72.27, s_pop(), -12); P(72.67, s_stamp(), -9); P(73.86, s_stamp(), -9)
P(77.3, s_typing(1.6), -12); P(79.7, s_pop(), -11); P(81.2, s_beep(1600, .15), -14)
for k in range(10): P(83.05 + k * .07, s_beep(1400 + 90 * k, .03), -18)
P(84.0, s_beep(800, .1), -13); P(84.3, s_beep(800, .1), -13)
P(86.0, s_whoosh(.4), -14); P(86.2, s_ding(), -11); P(88.07, s_pop(), -10); P(89.17, s_whoosh(.4), -14)
P(90.1, s_counter(1.2), -13); P(92.6, s_counter(.6), -13); P(93.2, s_pop(), -11)
P(94.67, s_stamp(), -4); P(94.67, pool["deep_boom"], -9); P(96.89, s_whoosh(.4), -13); P(97.0, s_ding(), -10)

# ------------------------------------------------------------------ clip ambience
amb = np.zeros((N, 2), np.float32)
for i in range(10):
    dur = SECT[i + 1] - SECT[i]; rate = min(1.0, 9.75 / dur)
    a = load(f"{CLIPS}/b{i + 1:02d}-designed.mp4", ["-ss", "0.12", "-af", f"atempo={max(.5, rate):.4f}"] if rate < .999 else ["-ss", "0.12"])
    a = a[:int(dur * SR)]
    if len(a) < 100: continue
    f = int(.08 * SR); a[:f] *= np.linspace(0, 1, f)[:, None]; a[-f:] *= np.linspace(1, 0, f)[:, None]
    put(amb, a, SECT[i])
amb = lp(amb, 4000)

# ------------------------------------------------------------------ mix
vo = load("/home/user/bisleri/vo.mp3"); vo = np.pad(vo, ((0, max(0, N - len(vo))), (0, 0)))[:N]
e = np.abs(vo).mean(1); k = int(.2 * SR); e = smooth(e, k); e /= e.max() + 1e-9
sp = np.clip(e * 6, 0, 1)[:, None]
final = vo + mus * db(-17) * (1 - .45 * sp) + amb * db(-26) * (1 - .5 * sp) + fx * db(-2)
final /= max(1.0, np.abs(final).max() / .98)
with wave.open(f"{ROOT}/mix.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((final * 32767).astype("<i2").tobytes())
print("mix ok", len(final) / SR)
