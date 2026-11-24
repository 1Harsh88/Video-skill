"""Final audio: VO + original score (+ short low Momentum excerpts) ducked under VO + varied transition SFX + clip ambience.
Also writes Hindi captions (ASS)."""
import json, os, subprocess, wave, numpy as np, random
MA = "/home/user/video-skill/mauryan"; OUT = "/home/user/mproj/out/audio"
SR = 44100; DUR = 784.67; N = int(DUR * SR)
ROWS = json.load(open(f"{MA}/shots_v2.json")); CMAP = json.load(open(f"{MA}/media/clip_map.json"))
from shots import REPL, FB, FPS

def load(path, start=None, dur=None):
    cmd = ["ffmpeg", "-loglevel", "error"]
    if start is not None: cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", path]
    if dur is not None: cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    b = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(b, np.float32).reshape(-1, 2).copy()
def put(buf, x, t, g=1.0):
    s = int(t * SR)
    if s < 0: x = x[-s:]; s = 0
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * g
def db(d): return 10 ** (d / 20)
def fadein(x, a): n = int(a * SR); x[:n] *= np.linspace(0, 1, n)[:, None]; return x
def fadeout(x, b): n = int(b * SR); x[-n:] *= np.linspace(1, 0, n)[:, None]; return x

vo = load(f"{MA}/audio/vo_full.mp3"); vo = np.pad(vo, ((0, max(0, N - len(vo))), (0, 0)))[:N]
score = load(f"{OUT}/score.wav")[:N]; score = np.pad(score, ((0, N - len(score)), (0, 0)))

# Momentum: three short, low excerpts at uplifting moments (cross-faded over the score)
mom = load(f"{MA}/audio/bg_music.mp3")
mus = score * db(-4)
for at, src, L in ((204.6, 30.0, 10.0), (273.6, 60.0, 11.0), (754.0, 88.0, 12.0)):
    seg = fadeout(fadein(mom[int(src * SR):int((src + L) * SR)].copy(), 2.0), 2.5)
    s, e = int(at * SR), int(at * SR) + len(seg)
    dip = np.ones((e - s, 1), np.float32) * 0.45
    mus[s:e] *= dip; put(mus, seg, at, db(-9))

# clip ambience (the generated clips' own sound), very low and dull
amb = np.zeros((N, 2), np.float32)
for r in ROWS:
    if r["type"] != "VIDEO": continue
    sid = r["id"]; s, e = FB[sid]; n = e - s; need = n / FPS
    src, off = (REPL[sid][0], REPL[sid][1]) if sid in REPL else (sid, 0.35)
    if off + need > 7.9: off = max(0, 7.9 - need)
    a = load(os.path.join(MA, "media/zip_dl/x", CMAP[src]), off, need)
    if len(a) < 200: continue
    a = fadeout(fadein(a, .15), .2)
    put(amb, a, s / FPS, 1.0)
# dull it: simple lowpass via FFT per channel
def lowpass(x, fc):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR)[:, None]; X *= 1 / (1 + (f / fc) ** 4); return np.fft.irfft(X, len(x), axis=0).astype(np.float32)
amb = lowpass(amb, 3500)

# ducking envelope from VO
env = np.abs(vo).mean(1)
win = int(0.25 * SR); k = np.ones(win, np.float32) / win
env = np.convolve(env, k, "same"); env = env / (env.max() + 1e-9)
speech = np.clip(env * 6, 0, 1)
duck = 1 - 0.55 * speech                     # music down ~7 dB while speaking
mus *= duck[:, None]; amb *= (1 - 0.6 * speech)[:, None]

# transition SFX: varied by mood, never the same twice in a row, not on every cut
SECT = [(0, "dark"), (33.4, "story"), (184.4, "march"), (228.2, "majesty"), (335.1, "tender"), (380.3, "dark"), (416.2, "tension"),
        (499.4, "war"), (550.5, "peace"), (720.0, "dark"), (748.6, "resolve")]
POOL = {"dark": ["sub_drop", "deep_boom", "wind_gust", "reverse_cymbal"], "war": ["drum_hit", "deep_boom", "sword_shing", "sub_drop", "fire_whoosh"],
        "march": ["drum_hit", "sword_shing", "fire_whoosh", "cloth_swish", "deep_boom"], "peace": ["chime", "temple_bell", "wind_gust", "cloth_swish", "sand_swish"],
        "tender": ["chime", "wind_gust", "sand_swish", "temple_bell"], "resolve": ["temple_bell", "chime", "wind_gust", "riser"],
        "story": ["cloth_swish", "sand_swish", "reverse_cymbal", "wind_gust", "fire_whoosh", "chime"], "majesty": ["riser", "temple_bell", "cloth_swish", "sand_swish", "reverse_cymbal"],
        "tension": ["reverse_cymbal", "sub_drop", "wind_gust", "sand_swish"]}
ENDS_AT_CUT = {"reverse_cymbal", "riser"}
sfx = {n[:-4]: load(f"{OUT}/sfx/{n}") for n in os.listdir(f"{OUT}/sfx")}
fx = np.zeros((N, 2), np.float32); rnd = random.Random(42); last = None; log = []
prev_type = None
for i, r in enumerate(ROWS[1:], 1):
    t = r["start"]; mood = [m for s, m in SECT if s <= t][-1]
    changed = r["type"] != prev_type; prev_type = r["type"]
    if not (changed or rnd.random() < 0.38): continue
    choices = [c for c in POOL[mood] if c != last]; name = rnd.choice(choices); last = name
    x = sfx[name]; at = t - len(x) / SR + 0.05 if name in ENDS_AT_CUT else t - 0.08
    g = db(-17) if name in ("temple_bell", "chime") else db(-14)
    put(fx, x, at, g); log.append((round(t, 1), name))
json.dump(log, open(f"{OUT}/sfx_log.json", "w"))
from collections import Counter; print("sfx placed:", len(log), Counter(n for _, n in log))

final = vo * db(0) + mus * db(-5) + amb * db(-20) + fx
# write wav, loudnorm afterwards in assembly
st = np.clip(final, -1, 1)
with wave.open(f"{OUT}/mix_raw.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())
print("mix written")

# ---------- Hindi captions (ASS) ----------
TL = json.load(open(f"{MA}/audio/timeline.json"))
def ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f"{h}:{m:02d}:{s:05.2f}"
lines = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 2", "",
         "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
         "Style: Cap,Mukta ExtraBold,56,&H00F2F6FA,&H000000FF,&H00101010,&H64000000,0,0,0,0,100,100,0,0,1,3.2,1.5,2,200,200,46,1", "",
         "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for s in TL:
    words = s["text"].replace("—", " — ").split(); words = [w for w in words if w != "—"]
    if not words: continue
    chunks, cur = [], []
    for wd in words:
        cur.append(wd)
        if len(cur) >= 6 or wd.endswith(("…", ",", "।", "?", "!")) and len(cur) >= 3: chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    tot = sum(len(" ".join(c)) for c in chunks); t0 = s["start"] + 0.05; span = (s["end"] - s["start"]) * 0.97
    for c in chunks:
        d = span * len(" ".join(c)) / tot
        lines.append(f"Dialogue: 0,{ts(t0)},{ts(t0 + d - 0.04)},Cap,,0,0,0,,{' '.join(c)}"); t0 += d
open(f"{OUT}/captions.ass", "w").write("\n".join(lines) + "\n")
print("captions written", len(lines))
