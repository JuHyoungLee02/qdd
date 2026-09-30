"""Split an L9 build output into validation chunk tables, and merge the Isaac settle results back (pure).
  split  python -m tools.l9.assets.chunks split BUILD.json OUTDIR [--size 300]   -> OUTDIR/c0000.json ...
  merge  python -m tools.l9.assets.chunks merge BUILD.json VALDIR OUT.json
         VALDIR/c*/objects_check.json (validate_objects) -> per row stable / stable_upright / settle, like
         objects_objv.json (stable rule: |bottom - top| <= 5 mm, tilt <= 10 deg, drift <= 2 cm)."""
from __future__ import annotations

import glob
import json
import os
import sys

STABLE_RULE = "Isaac settle 2 s on a table: |bottom - table top| <= 5 mm, tilt <= 10 deg, drift <= 2 cm"


def split(build: str, outdir: str, size: int = 300):
    d = json.load(open(build))
    ks = sorted(d["objects"])
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for i in range(0, len(ks), size):
        json.dump({"objects": {k: d["objects"][k] for k in ks[i:i + size]}},
                  open(os.path.join(outdir, f"c{i // size:04d}.json"), "w"))
        n += 1
    print("chunks", n, "rows", len(ks))


def merge(build: str, valdir: str, out: str):
    d = json.load(open(build))
    res = {}
    for f in sorted(glob.glob(os.path.join(valdir, "c*", "objects_check.json"))):
        res.update(json.load(open(f)))
    n_ok = 0
    for k, o in d["objects"].items():
        r = res.get(k)
        if r is None:
            o["stable"] = o["stable_upright"] = None
            continue
        o["stable"] = o["stable_upright"] = bool(r["stable"])
        o["settle"] = {q: r[q] for q in ("dz_mm", "drift_mm", "tilt_deg")}
        n_ok += o["stable"]
    for c in d.get("containers", {}).values():
        o = d["objects"].get(c.get("object_id"))
        c["object_stable"] = None if o is None else o.get("stable")
    d["stable_rule"] = STABLE_RULE
    json.dump(d, open(out, "w"))
    print("merged", len(res), "stable", n_ok, "of", len(d["objects"]))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "split":
        split(a[1], a[2], int(a[4]) if len(a) > 4 and a[3] == "--size" else 300)
    else:
        merge(a[1], a[2], a[3])
