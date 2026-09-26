"""E-CONF held-out R2 views (docs/stage3/prereg_conf.md §3). CPU only; reads /data/harvest/r2/train (never writes).

R2_TRAIN episodes with valid_for_training False (the planner run ended in a failed outcome, mostly the bottle tipping
after release) were never in any stage-B training set (every checkpoint trains on valid episodes) and never in E-NOV0
(eval split = valid episodes). At most --cap episodes per (variant, task), seeded. Output = the stage-B loader layout
(as tools/ma2/build_ma2.py views): <dst>/view/<v>/<t>/<k>/ep<seed>.jsonl (decision lines), img -> source img/,
sibling <k>.stageb.jsonl (decision rows) and <k>.labels_v2.jsonl; <dst>/heldout.json.
  python tools/conf/conf_build.py --src /data/harvest/r2/train --dst /data/harvest/data/conf --cap 100
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import conf_lib as L  # noqa: E402


def episodes(src: str) -> list:
    out = []
    for mp in sorted(glob.glob(os.path.join(src, "*", "*", "P*", "ep*.meta.json"))):
        rel = os.path.relpath(mp, src).replace("\\", "/").split("/")
        meta = json.load(open(mp))
        out.append({"variant": rel[0], "task": rel[1], "kind": rel[2], "seed": int(meta["seed"]),
                    "valid": bool(meta.get("valid_for_training"))})
    return out


def _jl(path):
    return [json.loads(x) for x in open(path, encoding="utf-8")]


def build(src: str, dst: str, cap: int, seed: int = 0, link=os.symlink) -> dict:
    eps = episodes(src)
    sel = L.select_heldout(eps, cap, seed)
    by = {}
    for v, t, k, s in sel:
        by.setdefault((v, t, k), []).append(s)
    mismatch, n_snap = 0, 0
    for (v, t, k), seeds in sorted(by.items()):
        fo = os.path.join(src, v, t, k)
        V = os.path.join(dst, "view", v, t, k)
        os.makedirs(V, exist_ok=True)
        if not os.path.lexists(os.path.join(V, "img")):
            link(os.path.join(fo, "img"), os.path.join(V, "img"))
        with open(V + ".stageb.jsonl", "w", encoding="utf-8") as fr, \
                open(V + ".labels_v2.jsonl", "w", encoding="utf-8") as fl:
            for s in sorted(seeds):
                lines = _jl(os.path.join(fo, f"ep{s}.jsonl"))
                last = max(x["k"] for x in lines)
                dec = [x for x in lines if x["decision"]]
                with open(os.path.join(V, f"ep{s}.jsonl"), "w", encoding="utf-8") as f:
                    for x in dec:
                        f.write(json.dumps(x) + "\n")
                rows = [r for r in _jl(os.path.join(fo, "rows", f"ep{s}.stageb.jsonl")) if r["decision"]]
                labs = _jl(os.path.join(fo, "rows", f"ep{s}.labels_v2.jsonl"))
                ks = [x["k"] for x in dec if x["k"] < last]
                if not (len(ks) == len(rows) == len(labs) - (len(dec) - len(ks))):
                    mismatch += 1
                n_snap += len(rows)
                for r in rows:
                    fr.write(json.dumps(r) + "\n")
                for x in labs:
                    fl.write(json.dumps(x) + "\n")
    unseen = [list(x) for x in sel if L.layout_unseen(x, eps)]
    per = {}
    for v, t, _, _ in sel:
        per[f"{v}/{t}"] = per.get(f"{v}/{t}", 0) + 1
    info = {"src": src, "cap": cap, "seed": seed, "n_episodes_all": len(eps),
            "n_invalid": sum(not e["valid"] for e in eps), "n_episodes": len(sel), "per_cell": per,
            "n_rows": n_snap, "mismatch": mismatch, "selected": [list(x) for x in sel], "layout_unseen": unseen,
            "sha": hashlib.sha256(json.dumps([list(x) for x in sel]).encode()).hexdigest()[:12]}
    json.dump(info, open(os.path.join(dst, "heldout.json"), "w"), indent=1)
    return info


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--cap", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    info = build(a.src, a.dst, a.cap, a.seed)
    print(json.dumps({k: v for k, v in info.items() if k not in ("selected", "layout_unseen")}
                     | {"n_layout_unseen": len(info["layout_unseen"])}))


if __name__ == "__main__":
    main()
