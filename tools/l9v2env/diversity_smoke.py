"""L9 v2 diversity of render-smoke frames (spec §12.3 G4 v2, §12.11 principle 2): SigLIP metrics of tools/l9/
diversity.py (pair_dist, pair_dup, nn_dup, nn_sim_median, eff_clusters) on the head f0 PNGs of each named set, equal
sample sizes, + per-axis entropy (bits) and distinct counts from the frames_*.jsonl records.
usage (pod venv with torch + transformers): python tools/l9v2env/diversity_smoke.py --set v1=DIR --set v2=DIR
       [--set prod=GLOB_ROOT:ring] --out report.json [--n 400] [--device cuda]
A set "NAME=ROOT:ring" takes calls/c000/img1_head_ring.png of the episodes under ROOT (production data)."""
import argparse
import glob
import json
import math
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.l9 import diversity as D  # noqa: E402

AXES = ("family", "rule", "room", "hdr", "light", "materials", "decor", "head_look", "density", "fixtures", "place")


def images(spec: str, n: int, seed: int = 0) -> list:
    root, _, kind = spec.partition(":")
    if kind == "ring":
        ps = [p for _, p in D.firsts(root, 10 ** 9, seed, "l9")]
    else:
        ps = sorted(glob.glob(os.path.join(root, "*_head.png")))
    random.Random(seed).shuffle(ps)
    return ps[:n]


def entropy(c: Counter) -> float:
    t = sum(c.values())
    return round(-sum(v / t * math.log2(v / t) for v in c.values() if v), 3) if t else 0.0


def axes(root: str) -> dict:
    cs = {a: Counter() for a in AXES}
    for f in glob.glob(os.path.join(root, "frames_*.jsonl")):
        for ln in open(f):
            r = json.loads(ln)
            if not r.get("ok"):
                continue
            ax = r.get("env_axes") or {}
            cs["family"][r["row"]["family"]] += 1
            cs["rule"][r["row"]["family"] + "/" + r["row"]["rule"]] += 1
            cs["room"][str((r.get("room") or {}).get("name"))] += 1
            cs["hdr"][str(r.get("hdr"))] += 1
            cs["light"][str(r.get("light"))] += 1
            for m in (r.get("materials") or {}).values():
                cs["materials"][m] += 1
            for d in r.get("decor") or []:
                cs["decor"][d.get("asset")] += 1
            cs["head_look"][str((r.get("head") or {}).get("look", "std"))] += 1
            cs["density"][str(ax.get("density"))] += 1
            for x in ax.get("fixtures") or []:
                cs["fixtures"][x] += 1
            for x in ax.get("place_classes") or []:
                cs["place"][x] += 1
    return {a: {"distinct": len(c), "entropy_bits": entropy(c)} for a, c in cs.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    sets = dict(s.split("=", 1) for s in a.set)
    paths = {k: images(v, a.n) for k, v in sets.items()}
    n = min(len(p) for p in paths.values())
    rep = {"n": n}
    for k, ps in paths.items():
        E = D.embed(ps[:n], a.device)
        rep[k] = D.metrics(E, k=min(50, max(2, n // 8)))
        if not sets[k].endswith(":ring"):
            rep[k + "_axes"] = axes(sets[k])
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
