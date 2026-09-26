"""E-TEACH-35B per-epoch table + best-epoch rule (prereg_teach_35b.md §7). Reads the eval summaries written by
tools/teach_35b/eval_epoch.sh and the 8-L8 baselines; prints a markdown table and one JSON line (BEST ...).
usage: python epoch_table.py [<teach_35b eval dir>] [<8-L8 DEV305 eval dir>] [<E-PT eval dir>]"""
import json
import os
import sys

E = sys.argv[1] if len(sys.argv) > 1 else "/data/harvest/out/teach_35b/eval"
L8 = sys.argv[2] if len(sys.argv) > 2 else "/data/harvest/out/teach_l8/eval_ft"
PT = sys.argv[3] if len(sys.argv) > 3 else "/data/harvest/out/teach_pt/eval"


def load(p):
    f = os.path.join(p, "summary.json")
    return json.load(open(f)) if os.path.exists(f) else None


def row(name, d305, dev, ood):
    c = d305["control_all"]
    at = d305["by_step"].get("above_target", {})
    fc = d305["control_first_call"]
    aux = d305.get("aux", {})
    r = {"arm": name, "n": c["n"], "valid": c["valid_rate"], "act": c["action_acc"],
         "xy_med": c["approach_xy_median_mm"], "xy_p90": c["approach_xy_p90_mm"],
         "ep_med": c["approach_episode_median_of_medians_mm"], "above_xy": at.get("approach_xy_median_mm"),
         "first_xy": fc["approach_xy_median_mm"], "carry_xy": c["carry_xy_median_mm"],
         "aux_tgt": (aux.get("tgt") or {}).get("xy_median_mm"), "lat_p50_batch8": d305.get("latency_s_p50")}
    if dev:
        r["dev_3d"] = dev["control_all"].get("approach_3d_median_mm")
        r["dev_n"] = dev["control_all"]["n"]
    if ood:
        o = ood["control_all"]
        r.update(ood_n=o["n"], ood_valid=o["valid_rate"], ood_xy=o["approach_xy_median_mm"],
                 ood_3d=o.get("approach_3d_median_mm"), ood_absz=o.get("grasp_absz_median_mm"),
                 ood_act=o["action_acc"])
    return r


rows = [row("8-L8 ep2", load(L8), load(os.path.join(PT, "dev_l8xyz")), load(os.path.join(PT, "ood_h_l8xyz")))]
eps = []
for k in range(1, 9):
    d = load(os.path.join(E, f"dev305_ep{k}"))
    if d:
        rows.append(row(f"35B ep{k}", d, load(os.path.join(E, f"dev_ep{k}")), load(os.path.join(E, f"ood_h_ep{k}"))))
        eps.append((k, rows[-1]))
cols = ["arm", "n", "valid", "act", "xy_med", "xy_p90", "ep_med", "above_xy", "first_xy", "carry_xy", "aux_tgt",
        "dev_3d", "ood_n", "ood_valid", "ood_xy", "ood_3d", "ood_absz", "ood_act", "lat_p50_batch8"]
print("| " + " | ".join(cols) + " |")
print("|" + "---|" * len(cols))
for r in rows:
    print("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")

cand = [(k, r) for k, r in eps if r["valid"] >= 0.95 and r["xy_med"] is not None]
best = None
if cand:
    m = min(r["xy_med"] for _, r in cand)
    g = max(r["act"] for _, r in cand)
    ok = [k for k, r in cand if r["xy_med"] <= m + 1.0 and r["act"] >= g - 0.01]
    best = min(ok) if ok else min(cand, key=lambda kr: (kr[1]["xy_med"], kr[0]))[0]
    b = dict(eps)[best]
    signs = {}
    for k, r in eps:
        if k > best:
            signs[k] = {"overtrain": r["xy_med"] >= b["xy_med"] + 2.0 or r["act"] <= b["act"] - 0.02,
                        "ood_overfit": (r.get("ood_3d") is not None and b.get("ood_3d") is not None
                                        and r["ood_3d"] >= 1.2 * b["ood_3d"])}
    print("BEST " + json.dumps({"best_epoch": best, "m_star": m, "g_star": g, "within_tol": ok, "later_signs": signs}))
else:
    print("BEST " + json.dumps({"best_epoch": None}))
