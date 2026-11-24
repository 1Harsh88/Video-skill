import json, math
P = json.load(open("shots_plan.json")); T = json.load(open("audio/timeline.json"))
NEW={1:'V',2:'V',3:'V',4:'I',5:'V',6:'G',7:'M',8:'M',9:'M',10:'V',11:'G',12:'V',13:'M',14:'V',15:'M',16:'M',17:'G',18:'V',19:'V',20:'V',21:'V',22:'V',23:'V',24:'I',25:'V',26:'V',27:'I',28:'V',29:'V',30:'M',31:'M',32:'V',33:'V',34:'V',35:'M',36:'V',37:'G',38:'M',39:'V',40:'V',41:'M',42:'V',43:'M',44:'V',45:'V',46:'M',47:'V',48:'G',49:'V',50:'G',51:'V',52:'V',53:'M',54:'I',55:'V',56:'V',57:'G',58:'M',59:'V',60:'V',61:'I',62:'V',63:'G',64:'M',65:'G',66:'M',67:'V',68:'V',69:'I',70:'M',71:'V',72:'V',73:'V',74:'V',75:'M',76:'M',77:'V',78:'I',79:'V',80:'I',81:'V',82:'G',83:'V',84:'V',85:'V',86:'V',87:'V',88:'V',89:'G',90:'V',91:'V',92:'I',93:'V',94:'V',95:'V',96:'M',97:'G',98:'V',99:'V',100:'V',101:'G',102:'M',103:'V',104:'V',105:'M',106:'V',107:'V',108:'G',109:'M',110:'V',111:'V',112:'V'}
BUMP = {111, 95, 47}   # +1 clip to reach exactly 100
plan = []
for p in P:
    t = NEW[p["beat"]]; d = p["dur"]
    if t == "V": n = max(1, round(d / 5.0), math.ceil(d / 8)) + (1 if p["beat"] in BUMP else 0)
    elif t == "I": n = math.ceil(d / 2.5)
    else: n = max(1, math.ceil(d / 6.5))
    q = dict(p); q["type"] = t; q["n"] = n; plan.append(q)
json.dump(plan, open("shots_plan2.json", "w"), indent=1)
from collections import Counter
c = Counter()
for q in plan: c[q["type"]] += q["n"]
print(dict(c))
if __name__ == "__main__":
    import sys
    if "--list" in sys.argv:
        for q in plan: print(q["beat"], q["type"], q["n"], q["dur"], "|", " ".join(T[i]["text"] for i in range(q["s"], q["e"] + 1))[:90])
