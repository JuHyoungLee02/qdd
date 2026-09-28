"""prereg_limits.md change 3 table: before / after pairs of the noise fix. Per arm pair: success, grasp+lift, memory drops,
carry-phase 'above' target jump between consecutive 'above' calls (median, mm), LoopGuard switches, held-object pixels
excluded (median). usage: python nf_table.py <limits out root> <reg episode list file>"""
import json
import os
import sys

import numpy as np

ROOT, REG = sys.argv[1], sys.argv[2]
reg = {"s{1}_{0}".format(*os.path.basename(e).rsplit("_s", 1)) for line in open(REG) for e in line.split()}


def load(arm_dir, keep=None):
    out = {}
    for dp, _, fs in os.walk(arm_dir):
        if "result.json" in fs and (keep is None or os.path.basename(dp) in keep):
            out[os.path.relpath(dp, arm_dir)] = json.load(open(os.path.join(dp, "result.json")))
    return out


def mech(r):
    b = r.get("boost") or {}
    drops = sum(1 for m in b.get("mem_checks", []) if not m.get("kept", True))
    held = [m["n_held_px"] for m in b.get("mem_checks", []) if "n_held_px" in m]
    goals = [(c.get("resolved") or {}).get("goal") for c in r["calls"]
             if c.get("phase_truth") == "carry" and ((c.get("parsed") or {}).get("command") or {}).get("height") == "above"]
    goals = [g for g in goals if g]
    jumps = [np.linalg.norm(np.subtract(a, b_)) * 1e3 for a, b_ in zip(goals, goals[1:])]
    return drops, jumps, len(b.get("switches", [])), held


def med(x):
    return None if not x else round(float(np.median(x)), 1)


def row(name, before, after):
    ks = sorted(set(before) & set(after))
    s0 = sum(bool(before[k]["success"]) for k in ks)
    s1 = sum(bool(after[k]["success"]) for k in ks)
    g0 = sum(bool(before[k].get("grasp_lift")) for k in ks)
    g1 = sum(bool(after[k].get("grasp_lift")) for k in ks)
    m0 = [mech(before[k]) for k in ks]
    m1 = [mech(after[k]) for k in ks]
    j0 = [j for m in m0 for j in m[1]]
    j1 = [j for m in m1 for j in m[1]]
    h1 = [h for m in m1 for h in m[3]]
    print(f"{name}: n={len(ks)} success {s0}->{s1} grasp_lift {g0}->{g1} | mem_drops {sum(m[0] for m in m0)}->"
          f"{sum(m[0] for m in m1)} | carry above jump med mm {med(j0)}->"
          f"{med(j1)} | switches {sum(m[2] for m in m0)}->{sum(m[2] for m in m1)} | "
          f"held px med {med(h1)}")
    for k in ks:
        a, b = before[k], after[k]
        if bool(a["success"]) != bool(b["success"]):
            print(f"   {k}: {a['success']}/{a.get('end_reason')} -> {b['success']}/{b.get('end_reason')}")
    return s0, s1, g0, g1


n1 = row("noise 1x", load(f"{ROOT}/map/noise_1"), load(f"{ROOT}/map/noise_1_nf"))
n2 = row("noise 2x", load(f"{ROOT}/map/noise_2"), load(f"{ROOT}/map/noise_2_nf"))
rg = row("reg none", load(f"{ROOT}/v2/none", reg), load(f"{ROOT}/v2/none_nf", reg))
gain = (n1[1] + n2[1]) - (n1[0] + n2[0])
reg_ok = rg[1] >= rg[0] - 1 and rg[3] >= rg[2] - 1
verdict = ("ADOPT" if gain >= 2 and reg_ok else
           "PARTIAL" if gain == 1 or (gain >= 2 and not reg_ok) else "NOT_ADOPT")
print(f"noise gain {gain:+d}, regression ok {reg_ok} -> {verdict}")
