import json, math, re
from prompts_data import BIBLE, V, I, M
T = json.load(open("audio/timeline.json")); P = json.load(open("shots_plan.json"))
VSTYLE = ("Style: cinematic photoreal historical epic, ancient India (4th-3rd century BCE), moody cinematic palette, warm light "
          "against deep shadows, soft haze, subtle film grain. Avoid: text, letters, logos, subtitles, watermarks, modern objects, extra limbs, distorted faces. "
          "Aspect ratio 16:9, {d} seconds.")
ISTYLE = ("Cinematic photoreal still image, ancient India (4th-3rd century BCE), dramatic chiaroscuro lighting, moody warm-and-teal palette, "
          "rich detail, shallow depth of field, 16:9 aspect ratio. No text, no letters, no logos, no watermark.")
sub = lambda s: re.sub(r"\{(\w+)\}", lambda m: BIBLE[m.group(1)], s)
fmt = lambda t: f"{int(t//60)}:{t%60:04.1f}"
errs = []; rows = []; vi = ii = mi = 0
for p in P:
    b, typ, n = p["beat"], p["type"], p["n"]
    vo = " ".join(T[i]["text"] for i in range(p["s"], p["e"] + 1))
    src = {"V": V, "I": I, "M": M}[typ].get(b)
    if src is None: errs.append(f"beat {b} {typ} missing"); continue
    if typ == "M":
        mi += 1; rows.append(dict(id=f"m{mi:02d}", type="MAP", beat=b, start=p["start"], dur=p["dur"], vo=vo, prompt=src)); continue
    if len(src) != n: errs.append(f"beat {b} {typ} needs {n}, has {len(src)}")
    seg = p["dur"] / len(src)
    for k, txt in enumerate(src):
        st = p["start"] + k * seg
        if typ == "V":
            vi += 1; gen = max(5, min(8, math.ceil(seg)))
            rows.append(dict(id=f"v{vi:03d}", type="VIDEO", beat=b, start=round(st, 2), dur=round(seg, 2), vo=vo,
                             prompt=sub(txt) + " " + VSTYLE.format(d=gen)))
        else:
            ii += 1
            rows.append(dict(id=f"i{ii:03d}", type="IMAGE", beat=b, start=round(st, 2), dur=round(seg, 2), vo=vo,
                             prompt=sub(txt) + ". " + ISTYLE))
print("errors:", errs or "none"); print("videos", vi, "images", ii, "maps", mi)
assert max(r["dur"] for r in rows if r["type"] == "IMAGE") <= 2.5
json.dump(rows, open("shots.json", "w"), ensure_ascii=False, indent=1)
# markdown deliverable
out = ["# मौर्य साम्राज्य — शॉट लिस्ट और प्रॉम्प्ट्स (ऑडियो 13:04.7 के अनुसार)", "",
       f"**कुल:** {vi} वीडियो क्लिप · {ii} इमेज (हर इमेज ≤ 2.5 सेकंड) · {mi} 3D मैप (ये मैं बनाऊँगा — प्रॉम्प्ट नहीं चाहिए)", "",
       "**फ़ाइल नाम:** वीडियो `v001.mp4 … v%03d.mp4`, इमेज `i001.png … i%03d.png` — इसी नाम से सेव करके भेजें।" % (vi, ii), "",
       "**वीडियो:** हर क्लिप 5–8 सेकंड में बनाएँ (Veo 8s / Kling 5s ठीक है) — मैं टाइमिंग के हिसाब से काटूँगा। **इमेज:** 16:9, 1920×1080 या बड़ी।", "",
       "**कैरेक्टर बाइबल** (हर प्रॉम्प्ट में पहले से जोड़ा हुआ है — एक जैसा चेहरा रखने के लिए पहले हर किरदार की एक रेफ़रेंस इमेज बनाकर image-to-video इस्तेमाल करें):", ""]
for k, v in BIBLE.items(): out.append(f"- **{k}** — {v}")
out += ["", "---", ""]
cur = None
for r in rows:
    if r["beat"] != cur:
        cur = r["beat"]; out += ["", f"### बीट {cur} · {fmt(r['start'])} · “{r['vo']}”", ""]
    if r["type"] == "MAP":
        out.append(f"**{r['id']}** · 3D MAP · {fmt(r['start'])} · {r['dur']:.1f}s — _{r['prompt']}_ (Claude बनाएगा)"); continue
    out.append(f"**{r['id']}** · {r['type']} · {fmt(r['start'])} · {r['dur']:.1f}s")
    out += ["```", r["prompt"], "```"]
open("02_shot_prompts.md", "w").write("\n".join(out) + "\n")
