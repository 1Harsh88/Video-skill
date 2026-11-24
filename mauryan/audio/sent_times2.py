import json
S = json.load(open("audio/sentences.json"))
sil = [tuple(map(float, l.split())) for l in open("audio/silences.txt") if len(l.split()) == 2]
TOTAL = 784.67
L = [len(s["text"]) for s in S]
cum = [0]
for l in L: cum.append(cum[-1] + l)
anch = [(0, 0.0)] + [(i, s["start"]) for i, s in enumerate(S) if s["cov"] >= 0.5] + [(len(S), TOTAL)]
# enforce monotonic anchors
clean = []
for i, t in anch:
    if not clean or (t > clean[-1][1] and i > clean[-1][0]): clean.append((i, t))
starts = []
for i in range(len(S)):
    a = max(x for x in clean if x[0] <= i); b = min(x for x in clean if x[0] >= i)
    if a[0] == b[0]: t = a[1]
    else: t = a[1] + (b[1] - a[1]) * (cum[i] - cum[a[0]]) / (cum[b[0]] - cum[a[0]])
    # snap to the end of the nearest silence within 1.5 s
    near = [e for s0, e in sil if abs(e - t) < 1.5]
    if near: t = min(near, key=lambda e: abs(e - t))
    starts.append(round(t, 2))
for i in range(1, len(starts)):
    if starts[i] <= starts[i - 1]: starts[i] = starts[i - 1] + 0.5
out = []
for i, s in enumerate(S):
    end = starts[i + 1] if i + 1 < len(S) else TOTAL
    out.append({"i": i, "start": starts[i], "end": round(end, 2), "text": s["text"]})
json.dump(out, open("audio/timeline.json", "w"), ensure_ascii=False, indent=1)
for o in out: print(f'{o["i"]:3d} {o["start"]:6.1f} {o["end"]-o["start"]:5.1f}  {o["text"][:60]}')
