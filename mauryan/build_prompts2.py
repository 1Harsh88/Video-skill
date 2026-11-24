import json, re
from prompts_v2 import BIBLE, V, I, M, G
T = json.load(open("audio/timeline.json")); P = json.load(open("shots_plan2.json"))
VSTYLE = ("Style: cinematic photoreal historical epic, ancient India (4th-3rd century BCE), moody cinematic palette, warm light against deep shadows, "
          "soft haze, subtle film grain. Avoid: text, letters, logos, subtitles, watermarks, modern objects, extra limbs, distorted faces. Aspect ratio 16:9, 8 seconds.")
ISTYLE = ("Cinematic photoreal still image, ancient India (4th-3rd century BCE), dramatic chiaroscuro lighting, moody warm-and-teal palette, "
          "rich detail, shallow depth of field, 16:9 aspect ratio. No text, no letters, no logos, no watermark.")
sub = lambda s: re.sub(r"\{(\w+)\}", lambda m: BIBLE[m.group(1)], s)
fmt = lambda t: f"{int(t//60)}:{t%60:04.1f}"
errs, rows, cnt = [], [], {"V": 0, "I": 0, "M": 0, "G": 0}
pre = {"V": "v", "I": "i", "M": "m", "G": "g"}; name = {"V": "VIDEO", "I": "IMAGE", "M": "3D MAP", "G": "MOTION GFX"}
for p in P:
    t, n, b = p["type"], p["n"], p["beat"]
    src = {"V": V, "I": I, "M": M, "G": G}[t].get(b, [])
    if len(src) != n: errs.append(f"beat {b} {t} needs {n}, has {len(src)}")
    vo = " ".join(T[i]["text"] for i in range(p["s"], p["e"] + 1))
    seg = p["dur"] / max(1, len(src))
    for k, txt in enumerate(src):
        cnt[t] += 1
        pr = sub(txt) + (" " + VSTYLE if t == "V" else ". " + ISTYLE if t == "I" else "")
        rows.append(dict(id=f"{pre[t]}{cnt[t]:03d}", type=name[t], beat=b, start=round(p["start"] + k * seg, 2), dur=round(seg, 2), vo=vo, prompt=pr))
print("errors:", errs or "none", cnt, "covered", round(sum(r["dur"] for r in rows), 1))
assert not errs
json.dump(rows, open("shots_v2.json", "w"), ensure_ascii=False, indent=1)
def dump(path, typ):
    with open(path, "w") as f:
        for r in rows:
            if r["type"] == typ: f.write(f"{r['id']} · {fmt(r['start'])} · {r['dur']:.1f}s\n{r['prompt']}\n\n")
dump("03_video_prompts.txt", "VIDEO"); dump("04_image_prompts.txt", "IMAGE"); dump("05_3d_map_shots.txt", "3D MAP"); dump("06_motion_graphics.txt", "MOTION GFX")
out = ["# मौर्य साम्राज्य — शॉट लिस्ट v2 (ऑडियो 13:04.7)", "",
       f"**कुल:** {cnt['V']} वीडियो (हर क्लिप 8 सेकंड बनाएँ, मैं ज़रूरत भर काटूँगा) · {cnt['I']} इमेज (≤ 2.5 s) · {cnt['M']} 3D मैप शॉट · {cnt['G']} मोशन ग्राफ़िक्स (मैप और ग्राफ़िक्स मैं बनाऊँगा)", "",
       "**फ़ाइल नाम:** `v001.mp4…v100.mp4`, `i001.png…i012.png`", ""]
cur = None
for r in rows:
    if r["beat"] != cur:
        cur = r["beat"]; out += ["", f"### {fmt(r['start'])} · “{r['vo']}”", ""]
    if r["type"] in ("3D MAP", "MOTION GFX"):
        out.append(f"**{r['id']}** · {r['type']} · {fmt(r['start'])} · {r['dur']:.1f}s — {r['prompt']} _(Claude बनाएगा)_"); continue
    out += [f"**{r['id']}** · {r['type']} · {fmt(r['start'])} · {r['dur']:.1f}s", "```", r["prompt"], "```"]
open("02_shot_prompts.md", "w").write("\n".join(out) + "\n")
