# beat grouping: (first_sentence, last_sentence, type)  V=video clip(s) max 8s each, I=images max 2.5s each, M=3D map (rendered by Claude)
import json, math
T = json.load(open("audio/timeline.json"))
BEATS = [
 (0,0,"V"),(1,1,"V"),(2,3,"V"),(4,4,"I"),(5,5,"V"),(6,6,"I"),
 (7,7,"M"),(8,9,"M"),(10,10,"I"),(11,11,"V"),(12,12,"I"),(13,13,"V"),
 (14,14,"M"),(15,15,"V"),(16,16,"M"),(17,17,"M"),(18,18,"I"),(19,19,"V"),(20,21,"V"),(22,22,"V"),
 (23,25,"I"),(26,26,"V"),(27,28,"V"),(29,29,"I"),(30,30,"I"),(31,32,"V"),(33,33,"I"),(34,35,"V"),(36,36,"I"),
 (37,40,"M"),(41,41,"M"),(42,42,"V"),(43,43,"V"),(44,45,"V"),
 (46,46,"M"),(47,47,"V"),(48,49,"I"),(50,50,"M"),(51,51,"V"),(52,52,"I"),(53,53,"I"),(54,54,"V"),(55,55,"M"),
 (56,56,"V"),(57,57,"V"),(58,58,"I"),(59,59,"V"),(60,60,"I"),(61,61,"V"),(62,62,"I"),
 (63,63,"I"),(64,64,"V"),(65,65,"M"),(66,66,"I"),(67,67,"V"),(68,68,"I"),(69,70,"I"),
 (71,71,"M"),(72,74,"V"),(75,75,"V"),(76,76,"I"),(77,77,"V"),(78,78,"I"),
 (79,79,"M"),(80,80,"I"),(81,82,"M"),(83,84,"I"),(85,85,"I"),(86,86,"I"),(87,87,"M"),(88,88,"V"),(89,89,"V"),(90,90,"I"),(91,91,"I"),
 (92,92,"M"),(93,95,"V"),(96,96,"V"),(97,97,"I"),(98,98,"V"),(99,99,"I"),(100,101,"V"),(102,102,"I"),(103,103,"I"),(104,104,"V"),
 (105,105,"V"),(106,106,"I"),(107,108,"V"),(109,110,"V"),(111,111,"I"),(112,112,"I"),(113,113,"V"),
 (114,114,"I"),(115,116,"I"),(117,117,"V"),(118,118,"I"),(119,119,"M"),(120,120,"I"),(121,121,"V"),
 (122,122,"V"),(123,123,"V"),(124,125,"I"),(126,126,"M"),(127,127,"V"),(128,128,"V"),(129,130,"M"),
 (131,131,"V"),(132,132,"V"),(133,133,"I"),(134,134,"I"),(135,135,"I"),(136,137,"I"),(138,139,"V"),
]
# sanity: contiguous coverage
cov = [i for a,b,_ in BEATS for i in range(a,b+1)]
assert cov == list(range(len(T))), "beats must cover every sentence once in order"
plan = []
for k,(a,b,t) in enumerate(BEATS):
    s, e = T[a]["start"], T[b]["end"]
    d = e - s
    n = math.ceil(d/9.0) if t=="V" else (math.ceil(d/2.5) if t=="I" else 1)
    plan.append(dict(beat=k+1, s=a, e=b, type=t, start=round(s,2), end=round(e,2), dur=round(d,2), n=n))
json.dump(plan, open("shots_plan.json","w"), indent=1)
from collections import Counter
c = Counter(); tot = Counter()
for p in plan: c[p["type"]] += p["n"]; tot[p["type"]] += p["dur"]
print("prompts needed:", dict(c), "seconds:", {k: round(v) for k,v in tot.items()})
for p in plan: print(p["beat"], p["type"], p["n"], p["dur"], T[p["s"]]["text"][:40])
