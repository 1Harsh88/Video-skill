"""Synthesize simple SFX at given times. usage: python sfx.py DUR out.wav whoosh:3.2 pop:8.1 chime:10.5 tick:2 rumble:0
kinds: whoosh pop chime tick rumble riser"""
import sys, wave, numpy as np
dur, out = float(sys.argv[1]), sys.argv[2]; sr = 44100; a = np.zeros(int(dur * sr)); g = np.random.default_rng(7)
def env(n, k): t = np.arange(n) / sr; return t, np.exp(-t * k)
def make(kind):
    if kind == 'whoosh': n = int(.7 * sr); x = np.convolve(g.standard_normal(n), np.ones(30) / 30, 'same'); return x * np.sin(np.linspace(0, np.pi, n)) ** 2 * 2
    if kind == 'pop': n = int(.4 * sr); t, e = env(n, 9); return np.sin(2 * np.pi * 160 * t * (1 - t)) * e + g.standard_normal(n) * np.exp(-t * 40) * .3
    if kind == 'chime': n = int(.9 * sr); t, e = env(n, 5); return (np.sin(2 * np.pi * 1320 * t) + .5 * np.sin(2 * np.pi * 1980 * t)) * e * .4
    if kind == 'tick': n = int(.05 * sr); t, e = env(n, 120); return g.standard_normal(n) * e * .6
    if kind == 'rumble': n = int(2 * sr); t = np.arange(n) / sr; return np.sin(2 * np.pi * 45 * t) * np.sin(np.linspace(0, np.pi, n)) * .7
    if kind == 'riser': n = int(1.5 * sr); t = np.arange(n) / sr; return np.sin(2 * np.pi * (200 + 600 * t / 1.5) * t) * (t / 1.5) ** 2 * .5
    raise SystemExit('unknown kind ' + kind)
for spec in sys.argv[3:]:
    k, t = spec.split(':'); s = make(k); i = int(float(t) * sr); a[i:i + len(s)] += s[:len(a) - i]
a = a / (np.abs(a).max() + 1e-9) * .8
with wave.open(out, 'wb') as f: f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes((a * 32767).astype(np.int16).tobytes())
print('wrote', out)
