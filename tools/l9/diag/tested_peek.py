"""L9 v2 diagnosis: summary of a grasp cache + Isaac test file of one object (pure numpy).
usage: python tools/l9/diag/tested_peek.py <grip> <object id> [--grasps DIR] [--tested DIR]
Prints the keys, pass counts and, per candidate that passed, the planned width vs the gap the test measured."""
import os
import sys

import numpy as np


def main():
    grip, oid = sys.argv[1], sys.argv[2]
    gd = sys.argv[sys.argv.index("--grasps") + 1] if "--grasps" in sys.argv else "/data/harvest/l9v2/grasps"
    td = sys.argv[sys.argv.index("--tested") + 1] if "--tested" in sys.argv else "/data/harvest/l9v2/tested"
    g = dict(np.load(os.path.join(gd, grip, f"{oid}.npz"), allow_pickle=True))
    print("grasps", {k: v.shape for k, v in g.items()})
    tp = os.path.join(td, grip, f"{oid}.npz")
    if not os.path.exists(tp):
        print("no test file")
        return
    t = dict(np.load(tp, allow_pickle=True))
    print("tested", {k: (v.shape, v.dtype.str) for k, v in t.items()})
    for k, v in t.items():
        if v.dtype == bool and v.ndim == 1:
            print(f"  {k}: {int(v.sum())}/{len(v)}")
    gapk = [k for k in t if "gap" in k]
    idx = np.asarray(t.get("idx", np.arange(len(g["w"]))), int)
    p = np.asarray(t.get("pass_shake", t.get("pass", np.zeros(len(idx), bool))), bool)
    if len(p) != len(idx):
        p = p[idx]
    print("  collider", t.get("collider"), "pad_drop", t.get("pad_drop"))
    for k in gapk:
        v = np.asarray(t[k], float)
        if len(v) == len(idx):
            w = g["w"][idx]
            d = v - w
            print(f"  {k}: all n={len(v)} gap-w median {np.nanmedian(d):.4f}; pass n={int(p.sum())} "
                  f"gap-w median {np.nanmedian(d[p]) if p.any() else float('nan'):.4f} "
                  f"gap median {np.nanmedian(v[p]) if p.any() else float('nan'):.4f} w median "
                  f"{np.nanmedian(w[p]) if p.any() else float('nan'):.4f}")
            if "--each" in sys.argv:
                fam = t.get("family", [""] * len(idx))
                for j in range(len(idx)):
                    print(f"    idx {idx[j]} fam {fam[j]} w {w[j]:.4f} {k} {v[j]:.4f} pass {bool(p[j])}")


if __name__ == "__main__":
    main()
