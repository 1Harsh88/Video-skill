import json, re, difflib
asr = json.load(open("audio/asr_words.json"))
text = open("audio/vo_text.txt").read()
# sentences: split on danda / ? / ! / newline
sents = [s.strip() for s in re.split(r"(?<=[।?!])\s+|\n+", text) if s.strip()]
norm = lambda w: re.sub(r"[^ऀ-ॿa-zA-Z]", "", w).replace("़", "")
sw = []  # (sentence index, word)
for i, s in enumerate(sents):
    for w in s.split():
        n = norm(w)
        if n: sw.append((i, n))
aw = [norm(w[2]) for w in asr]
sm = difflib.SequenceMatcher(None, [w for _, w in sw], aw, autojunk=False)
m = {}
for a, b, size in sm.get_matching_blocks():
    for k in range(size): m[a + k] = b + k
# per sentence: first/last matched word times; interpolate gaps
out = []
for i, s in enumerate(sents):
    idx = [k for k, (si, _) in enumerate(sw) if si == i]
    hits = [m[k] for k in idx if k in m]
    out.append({"i": i, "text": s, "start": asr[hits[0]][0] if hits else None, "end": asr[hits[-1]][1] if hits else None, "cov": round(len(hits) / max(1, len(idx)), 2)})
for k, o in enumerate(out):  # fill missing
    if o["start"] is None:
        o["start"] = out[k - 1]["end"] if k else 0.0
    if o["end"] is None:
        nxt = next((x["start"] for x in out[k + 1:] if x["start"] is not None), 784.6)
        o["end"] = nxt
json.dump(out, open("audio/sentences.json", "w"), ensure_ascii=False, indent=1)
low = [o for o in out if o["cov"] < 0.5]
print(len(out), "sentences; low coverage:", len(low))
for o in out[:6] + out[-4:]: print(round(o["start"],1), round(o["end"],1), o["cov"], o["text"][:50])
