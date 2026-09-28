"""E-VIEW8 builds (prereg_view8.md): open point rows split by viewpoint (user-log 169-170).
  A0 = base + open head-view rows (no third-person, no wide-angle gopro)
  A1 = A0 + third-person object / place points (MolmoBot Franka zed2 / droid shoulder, view=third, obj/place_point)
  A2 = A1 + third-person own-gripper points (view=third, ee_point)
  A3 = A1 + extra third-person object points (RH20T / DROID, files given later)
Additive (the base rows are the same in every arm, each open row once), steps = round(1632 x rows / base rows).
Only the training copies are read for the MolmoBot Franka rows (obj_pixel_train.jsonl, records_verified_train.jsonl:
the wide-angle rows are removed there, operation T 753c9a1). G rows are split off, then guarded.
usage: python view8_build.py main <out dir> <base d-min jsonl>
       python view8_build.py a3   <out dir> <base d-min jsonl> <third-person obj jsonl> [...]"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xemb import gsplit as GS  # noqa: E402

X = "/data/harvest/out/xemb_proto/points"
PK = "/data/harvest/out/xemb"
HEAD_FILES = [f"{X}/{s}/records_verified.jsonl" for s in ("behavior", "molmobot_rby1", "rb2", "rb3", "maniskill")] + [
    f"{PK}/dh_pack/dh_D.jsonl", f"{PK}/dist8_packs/t1t4_pixel.jsonl"]  # dh_D / t1t4: head cameras, no view tag
MIXED_FILES = [f"{PK}/dist8_packs/obj_pixel_train.jsonl", f"{X}/molmobot_franka/records_verified_train.jsonl"]
BASE_STEPS = 1632


def _rows(p):
    return [json.loads(x) for x in open(p, encoding="utf-8")]


def view_of(r, f):
    v = r.get("view")
    if v is None and f in HEAD_FILES:
        return "head"
    return v


def classify(files):
    """-> {cell: [rows]} with cell in head / third_obj / third_ee / other; one row per id, G rows dropped."""
    seen, cells, counts = set(), {"head": [], "third_obj": [], "third_ee": [], "other": []}, {}
    for f in files:
        rs = _rows(f)
        rs, g = GS.split(rs)
        counts[f] = {"rows": len(rs) + len(g), "g_dropped": len(g)}
        for r in rs:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            v, q = view_of(r, f), r.get("qa_kind", "qa")
            if v == "head":
                c = "head"
            elif v == "third" and q in ("obj_point", "place_point"):
                c = "third_obj"
            elif v == "third" and q == "ee_point":
                c = "third_ee"
            else:
                c = "other"
            cells[c].append(dict(r, kind="aux", aux_kind="open_" + q))
    for c, rs in cells.items():
        if c != "other":
            GS.guard(rs, "view8 " + c)
    return cells, counts


def write(out, name, base, rows):
    lines = base + [json.dumps(r) for r in rows]
    order = np.random.default_rng([8, len(lines)]).permutation(len(lines))
    with open(os.path.join(out, f"train_{name}.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for i in order:
            f.write(lines[int(i)] + "\n")
    steps = int(round(BASE_STEPS * len(lines) / len(base)))
    with open(os.path.join(out, "steps.txt"), "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{name} {steps}\n")
    return {"base": len(base), "open": len(rows), "total": len(lines), "steps": steps}


def main(out, base_p):
    os.makedirs(out, exist_ok=True)
    base = open(base_p, encoding="utf-8").read().splitlines()
    cells, counts = classify(HEAD_FILES + MIXED_FILES)
    res = {"files": counts, "cells": {c: len(v) for c, v in cells.items()}}
    a0 = cells["head"]
    a1 = a0 + cells["third_obj"]
    a2 = a1 + cells["third_ee"]
    for name, rows in (("A0", a0), ("A1", a1), ("A2", a2)):
        res[name] = write(out, name, base, rows)
    json.dump(res, open(os.path.join(out, "build.counts.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "files"}))


def a3(out, base_p, extra):
    base = open(base_p, encoding="utf-8").read().splitlines()
    cells, _ = classify(HEAD_FILES + MIXED_FILES)
    ex, excounts = classify(extra)
    known = {r["id"] for r in cells["head"] + cells["third_obj"]}
    add = [r for r in ex["third_obj"] if r["id"] not in known]
    res = write(out, "A3", base, cells["head"] + cells["third_obj"] + add)
    res.update(extra_files=excounts, extra_cells={c: len(v) for c, v in ex.items()}, extra_added=len(add))
    json.dump(res, open(os.path.join(out, "build_a3.counts.json"), "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    if sys.argv[1] == "main":
        main(sys.argv[2], sys.argv[3])
    else:
        a3(sys.argv[2], sys.argv[3], sys.argv[4:])
