"""Assemble AI-generated (or any) clips into a finished video: fit to aspect, trim, crossfade,
voiceover, ducked music, word-highlight captions, loudness-normalised.

usage: python assemble.py edit.json out.mp4

edit.json:
{
  "W": 1080, "H": 1920, "fps": 30,
  "fade": 0.4,                          # crossfade seconds between clips (0 = hard cut)
  "clips": [ {"file": "c1.mp4", "in": 0, "out": 4.5, "fit": "cover"},   # fit: cover|contain
             {"file": "photo.jpg", "dur": 3, "zoom": 1.08} ],            # stills get a slow push-in
  "clip_audio": 0.0,                    # 0..1 volume of the clips' own audio
  "voice": "vo.mp3",                    # optional
  "music": "bed.mp3", "music_db": -18,  # optional, ducked under voice
  "words": "words.json",                # optional [[start,end,word],...] -> captions
  "caption": {"font": "Baloo 2", "size": 84, "y": 0.72, "color": "FFFFFF", "hi": "00D7FF"}   # hi = BGR hex
}
"""
import json, os, subprocess, sys, tempfile

cfg = json.load(open(sys.argv[1])); out = sys.argv[2]
base = os.path.dirname(os.path.abspath(sys.argv[1]))
P = lambda f: f if os.path.isabs(f) else os.path.join(base, f)
W, H, FPS = cfg.get("W", 1080), cfg.get("H", 1920), cfg.get("fps", 30)
fade = float(cfg.get("fade", 0.4)); tmp = tempfile.mkdtemp(prefix="asm_")

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit("ffmpeg failed:\n" + " ".join(cmd) + "\n" + r.stderr[-2000:])

def has_audio(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", f], capture_output=True, text=True)
    return bool(r.stdout.strip())

# 1) normalise every clip to W x H, fps, with a stereo track (silent if none)
parts, durs = [], []
for i, c in enumerate(cfg["clips"]):
    f = P(c["file"]); o = os.path.join(tmp, f"p{i:03d}.mp4")
    still = f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    fit = c.get("fit", "cover")
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if fit == "cover"
          else f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black")
    if still:
        d = float(c.get("dur", 3)); z = float(c.get("zoom", 1.08)); n = int(d * FPS)
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='1+({z}-1)*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:s={W}x{H}:fps={FPS}")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-t", str(d), "-i", f, "-f", "lavfi", "-t", str(d), "-i", "anullsrc=r=48000:cl=stereo",
               "-vf", vf + ",format=yuv420p", "-map", "0:v", "-map", "1:a", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-shortest", o]
    else:
        a, b = float(c.get("in", 0)), c.get("out"); d = (float(b) - a) if b is not None else None
        tin = ["-ss", str(a)] + (["-t", str(d)] if d else [])
        if has_audio(f):
            cmd = ["ffmpeg", "-y", *tin, "-i", f, "-vf", vf + f",fps={FPS},format=yuv420p", "-af", "aresample=48000,aformat=channel_layouts=stereo",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", o]
        else:
            cmd = ["ffmpeg", "-y", *tin, "-i", f, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf + f",fps={FPS},format=yuv420p",
                   "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", o]
    run(cmd)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", o], capture_output=True, text=True)
    parts.append(o); durs.append(float(r.stdout.strip()))

# 2) join with crossfades
joined = os.path.join(tmp, "joined.mp4")
if len(parts) == 1 or fade <= 0:
    lst = os.path.join(tmp, "l.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
else:
    ins, fc, off = [], [], 0.0; v, a = "[0:v]", "[0:a]"
    for p in parts: ins += ["-i", p]
    for i in range(1, len(parts)):
        off += durs[i - 1] - fade
        fc.append(f"{v}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.3f}[v{i}]")
        fc.append(f"{a}[{i}:a]acrossfade=d={fade}[a{i}]"); v, a = f"[v{i}]", f"[a{i}]"
    run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(fc), "-map", v, "-map", a,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", joined])

# 3) captions (ASS, word highlight)
vf = "null"
if cfg.get("words"):
    cap = {"font": "Baloo 2", "size": 84, "y": 0.72, "color": "FFFFFF", "hi": "00D7FF", **cfg.get("caption", {})}
    words = json.load(open(P(cfg["words"]), encoding="utf-8"))
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1][0] - w[1] if i + 1 < len(words) else 9
        if len(cur) >= 4 or gap > 0.35 or w[2][-1:] in ".,!?।": chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    ts = lambda s: f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"
    mv = int(H * (1 - cap["y"]))
    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "", "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: C,{cap['font']},{cap['size']},&H00{cap['color']},&H00{cap['color']},&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,6,2,2,60,60,{mv},1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for ch in chunks:
        end = max(ch[-1][1], ch[0][0] + 0.6)
        for j, w in enumerate(ch):
            s = w[0]; e = ch[j + 1][0] if j + 1 < len(ch) else end
            txt = " ".join((f"{{\\c&H{cap['hi']}&}}{x[2]}{{\\c&H{cap['color']}&}}" if k == j else x[2]) for k, x in enumerate(ch))
            ass.append(f"Dialogue: 0,{ts(s)},{ts(e)},C,,0,0,0,,{txt}")
    ap = os.path.join(tmp, "cap.ass"); open(ap, "w", encoding="utf-8").write("\n".join(ass) + "\n")
    fd = cfg.get("fontsdir")
    vf = f"ass={ap}" + (f":fontsdir={P(fd)}" if fd else "")

# 4) audio mix: clip audio + voice + ducked music, loudnorm
ins = ["-i", joined]; fa = [f"[0:a]volume={cfg.get('clip_audio', 0.0)}[ca]"]; mix = ["[ca]"]
if cfg.get("voice"):
    ins += ["-i", P(cfg["voice"])]; fa.append("[1:a]aresample=48000,asplit=2[vo][vsc]"); mix.append("[vo]")
if cfg.get("music"):
    k = len(ins) // 2; ins += ["-stream_loop", "-1", "-i", P(cfg["music"])]
    fa.append(f"[{k}:a]aresample=48000,volume={cfg.get('music_db', -18)}dB[mu]")
    if cfg.get("voice"): fa.append("[mu][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[mud]"); mix.append("[mud]")
    else: mix.append("[mu]")
elif cfg.get("voice"): fa.append("[vsc]anullsink")
fa.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[aout]")
run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(fa) + f";[0:v]{vf}[vout]", "-map", "[vout]", "-map", "[aout]",
     "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
print("wrote", out, f"({sum(durs) - fade * max(0, len(durs) - 1):.1f}s)")
