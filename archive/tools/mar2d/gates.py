"""MolmoAct R2 data gates (plan docs/superpowers/plans/2026-09-26-molmoact-r2-data.md), CPU only, read-only on data.

  cmp  --a ROOT_A --b ROOT_B [--items v/t/k/seed,...]   bit comparison of the physics arrays of the same items
       (G-default: re-recorded default episodes vs R2_TRAIN; G-x2: x2 pod vs R2_TRAIN; G-det: fresh process vs pilot)
Outputs JSON to stdout (and --out FILE).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import numpy as np

PHYS = ("t", "q", "qd", "tau", "q_target", "grip", "grip_q", "grip_tau", "tcp", "obj_pose", "action", "action_real",
        "hold_n", "phase_id", "truth")
META_VOLATILE = {"wall_s", "rtf", "timing_s", "prefix_wall_s", "worker", "utc", "validation", "valid_for_training"}


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def items_of(root):
    out = []
    for mp in sorted(glob.glob(f"{root}/*/*/*/ep*.meta.json")):
        v, t, k = mp.replace("\\", "/").split("/")[-4:-1]
        out.append((v, t, k, int(os.path.basename(mp)[2:-10])))
    return out


def cmp_item(a_root, b_root, it):
    v, t, k, s = it
    fa, fb = f"{a_root}/{v}/{t}/{k}/ep{s}", f"{b_root}/{v}/{t}/{k}/ep{s}"
    za, zb = np.load(fa + ".npz"), np.load(fb + ".npz")
    ma, mb = json.load(open(fa + ".meta.json")), json.load(open(fb + ".meta.json"))
    diff = {}
    for n in PHYS:
        if n not in za.files or n not in zb.files:
            diff[n] = "missing"
            continue
        x, y = za[n], zb[n]
        if x.shape != y.shape:
            diff[n] = f"shape {x.shape} vs {y.shape}"
        elif not np.array_equal(x, y):
            diff[n] = float(np.abs(x.astype(float) - y.astype(float)).max())
    keys_a, keys_b = set(ma) - META_VOLATILE, set(mb) - META_VOLATILE
    meta_diff = sorted(k2 for k2 in keys_a & keys_b if ma[k2] != mb[k2] and k2 not in ("randomization",))
    return {"item": f"{v}/{t}/{k}/{s}", "bit_identical": not diff, "array_diffs": diff,
            "meta_keys_equal": keys_a == keys_b, "meta_only_a": sorted(keys_a - keys_b),
            "meta_only_b": sorted(keys_b - keys_a), "meta_value_diffs": meta_diff,
            "n_frames": [int(len(za["t"])), int(len(zb["t"]))], "success": [ma.get("success"), mb.get("success")]}


def cmd_cmp(a):
    its = items_of(a.a) if not a.items else [tuple(x.split("/")[:3]) + (int(x.split("/")[3]),) for x in a.items.split(",")]
    rows = [cmp_item(a.a, a.b, it) for it in its]
    out = {"gate": a.name, "utc": utc(), "a": a.a, "b": a.b, "n": len(rows),
           "bit_identical": sum(r["bit_identical"] for r in rows),
           "meta_keys_equal": sum(r["meta_keys_equal"] for r in rows), "rows": rows}
    out["PASS"] = bool(rows) and out["bit_identical"] == len(rows) and out["meta_keys_equal"] == len(rows)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["cmp"])
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--items", default="")
    ap.add_argument("--name", default="cmp")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    res = {"cmp": cmd_cmp}[a.mode](a)
    s = json.dumps(res, indent=1)
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        open(a.out, "w").write(s)
    print(s)


if __name__ == "__main__":
    main()
