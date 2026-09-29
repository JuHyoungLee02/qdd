"""Split the boost1b plan (boost1b_plan.txt lines '<combos> <vdir> <eps...>') into two lane plans by combo:
lane A = tray + lift arms, lane B = head arms + regression (none:none, pts:none). Output lines '<combos> <eps...>'.
usage: python b1b_split.py <plan> <out A> <out B>"""
import sys

plan, oa, ob = sys.argv[1:4]
A, B = [], []
for ln in open(plan):
    p = ln.split()
    if len(p) < 3:
        continue
    combos, eps = p[0].split(","), p[2:]
    a = [c for c in combos if c.split(":")[1] in ("tray", "lift")]
    b = [c for c in combos if c not in a]
    if a:
        A.append(",".join(a) + " " + " ".join(eps))
    if b:
        B.append(",".join(b) + " " + " ".join(eps))
open(oa, "w").write("\n".join(A) + "\n")
open(ob, "w").write("\n".join(B) + "\n")
print(len(A), len(B))
