"""E-STRIP8 comparison and verdict (prereg_strip8.md §4-5). Per arm: the evaluate.py summary (valid JSON, gripper
action accuracy, approach xy median / p90, approach 3D, grasp z) and snapshot-paired bootstrap differences between
arms on the same states (scores.jsonl ids).
python -m harvest.teach_strip8.compare --set dev --arm s-full=<eval dir> --arm s-min=<eval dir> ... [--ref s-full]
-> JSON on stdout (per-arm summary, paired differences of every arm against --ref for approach_xy_mm and
approach_3d_mm)."""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

MARGIN_MM = 5.0
N_BOOT = 10000


def load_scores(d: str, only=None) -> dict:
    """scores by id; only = substrings (e.g. ["tz0.82", "tz0.88"]): keep ids containing any of them."""
    sc = {s["id"]: s for s in (json.loads(x) for x in open(os.path.join(d, "scores.jsonl")))}
    return {k: v for k, v in sc.items() if not only or any(o in k for o in only)}


def summary_of(sc: dict) -> dict:
    """evaluate.summarize-shaped summary recomputed from scores (for a subset of the states)."""
    from ..teach_pt import metrics as M
    s = list(sc.values())
    return {"control_all": M.summarize(s), "control_first_call": M.summarize([x for x in s if x["call"] == 0]),
            "by_step": {k: M.summarize([x for x in s if x["step"] == k]) for k in sorted({x["step"] for x in s})}}


def paired(a: dict, b: dict, key: str, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Mean of (a - b) over snapshots where both have `key`, percentile bootstrap 95 % CI (resampling snapshots)."""
    ids = sorted(set(a) & set(b))
    both = [i for i in ids if a[i].get(key) is not None and b[i].get(key) is not None]
    d = np.array([a[i][key] - b[i][key] for i in both], float)
    out = {"key": key, "n_common": len(ids), "n_pairs": len(both), "n_unpaired": len(ids) - len(both)}
    if not len(d):
        return dict(out, mean_diff=None, median_diff=None, ci95=None)
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(1)
    return dict(out, mean_diff=round(float(d.mean()), 3), median_diff=round(float(np.median(d)), 3),
                ci95=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)])


def dev_noninferior(arm: dict, full: dict) -> bool:
    """DEV: approach xy median <= S-full + 5 mm, valid JSON >= 0.95, gripper action accuracy >= S-full - 0.05."""
    return (arm["xy_med"] <= full["xy_med"] + MARGIN_MM and arm["valid"] >= 0.95
            and arm["action"] >= full["action"] - 0.05)


def ood_call(ci) -> str:
    """OOD-H approach 3D, paired CI of (arm - reference) mean: upper < 0 BETTER; upper < +5 mm NONINFERIOR;
    lower > +5 mm WORSE; else INCONCLUSIVE."""
    lo, hi = ci
    if hi < 0:
        return "BETTER"
    if hi < MARGIN_MM:
        return "NONINFERIOR"
    if lo > MARGIN_MM:
        return "WORSE"
    return "INCONCLUSIVE"


def brief(summary: dict) -> dict:
    c = summary["control_all"]
    return {"valid": c.get("valid_rate"), "action": c.get("action_acc"), "xy_med": c.get("approach_xy_median_mm"),
            "xy_p90": c.get("approach_xy_p90_mm"), "a3d_med": c.get("approach_3d_median_mm"),
            "a3d_p90": c.get("approach_3d_p90_mm"), "grasp_absz_med": c.get("grasp_absz_median_mm"),
            "grasp_le15": c.get("grasp_absz_le15_share"), "move": c.get("approach_move_share"),
            "carry_xy_med": c.get("carry_xy_median_mm"), "n": c.get("n"),
            "first_xy_med": summary["control_first_call"].get("approach_xy_median_mm"),
            "above_xy_med": summary["by_step"].get("above_target", {}).get("approach_xy_median_mm"),
            "latency_p50": summary.get("latency_s_p50")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--arm", action="append", required=True, help="name=eval dir")
    ap.add_argument("--ref", default="s-full")
    ap.add_argument("--only", default="", help="comma-separated id substrings (e.g. tz0.82,tz0.88)")
    a = ap.parse_args(argv)
    only = [o for o in a.only.split(",") if o]
    arms = dict(x.split("=", 1) for x in a.arm)
    out = {"set": a.set, "only": only, "arms": {}, "paired_vs_" + a.ref: {}}
    sc = {}
    for k, d in arms.items():
        sc[k] = load_scores(d, only)
        out["arms"][k] = brief(dict(summary_of(sc[k]), latency_s_p50=json.load(
            open(os.path.join(d, "summary.json"))).get("latency_s_p50")))
    if a.ref in sc:
        for k in sc:
            if k != a.ref:
                out["paired_vs_" + a.ref][k] = {m: paired(sc[k], sc[a.ref], m)
                                                 for m in ("approach_xy_mm", "approach_3d_mm")}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
