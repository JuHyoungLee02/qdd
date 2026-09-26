"""E-SR1d in-run gates (docs/stage3/prereg_sr1d.md §0.5). Each subcommand prints a JSON line with 'pass' and exits
1 on failure.
  ga    --meta META                         authority proxy: coverage, sensitivity agreement, loaded far val n
  gkin  --stats BRANCH_STATS --strata S     kinematic validity of the generated branches (replaces E-SR1c G-br)
  g0    --log TRAIN_STDOUT --stats BRANCH_STATS  branch join (stdout event) / batch share
  g1    --eval C0_EVAL --sr0 SR0_JSONL      the C0 evaluation path reproduces E-SR0 (same checkpoint)
  g2    --log TRAIN_LOG [--max-s 4444]      loop time and finite losses
  cfg   --log TRAIN_LOG --ref REF_LOG       training args = the reference run's args but the E-SR1d options / names
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))
_spec = importlib.util.spec_from_file_location("sr0_verdict", os.path.join(_HERE, "..", "sr0", "sr0_verdict.py"))
V0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V0)

COVER_MIN, AGREE_MIN, FAR_VAL_MIN = 0.70, 0.95, 300
REJ_MAX, DIR_REJ_MAX, DIR_P99_MAX = 0.50, 0.50, 10.0
CFG_ALLOWED = {"run", "out_root", "sr1d_branch", "sr1d_frac", "sr1d_mode", "overwrite"}
# options added to stageb_train after motion_s1 / s2 were trained (E-MA1b): absent in the reference config, allowed
# only at their off defaults
NEW_OFF = {"aux_extra": "none", "a3d_root": "/data/harvest/data/ma1b/conv"}


def _out(name, ok, **kw):
    print(json.dumps({"gate": name, "pass": bool(ok), **kw}, default=float), flush=True)
    return 0 if ok else 1


def loaded(m: dict) -> bool:
    from harvest.train.se2e_data import needed_cams
    return set(needed_cams(m)) <= set(m.get("has_cams") or [])


def gate_ga(a):
    ms = [json.loads(x) for x in open(a.meta, encoding="utf-8")]
    cover = float(np.mean([m["stratum"] != "unknown" for m in ms]))
    alts = sorted(ms[0]["alt"])
    agree = {n: float(np.mean([(m["stratum"] == "far") == (m["alt"][n] == "far") for m in ms])) for n in alts}
    lv = [m for m in ms if m["split"] == "val" and loaded(m)]
    strata_val = {s: sum(m["stratum"] == s for m in lv) for s in ("far", "band", "near", "unknown")}
    ok = cover >= COVER_MIN and min(agree.values()) >= AGREE_MIN and strata_val["far"] >= FAR_VAL_MIN
    return _out("ga", ok, coverage=cover, agree=agree, val_loaded=len(lv), val_strata=strata_val)


def gate_gkin(a):
    t = json.load(open(a.stats))["total"]
    ds = json.load(open(a.strata))["datasets"]
    spd = min(d["ee_tick_speed_p999"] for d in ds.values())
    cap = min(d["chunk_cap_m"] for d in ds.values())
    checks = {"reject_rate": t["reject_rate"] <= REJ_MAX,
              "reject_by_dir": max(t["reject_rate_by_dir"].values()) <= DIR_REJ_MAX,
              "dir_within_45": t["dir_err_gt45"] == 0,
              "dir_p99": t["dir_err_q"]["99"] <= DIR_P99_MAX,
              "joint_limits": t["jlim_viol"] == 0,
              "joint_speed": t["dq_ratio_q"]["100"] <= 1.0 + 1e-9,
              "ee_speed": t["tick_speed_q"]["100"] <= spd + 1e-9,
              "magnitude": t["mag_q"]["100"] <= cap + 1e-6,
              "branches": t["branches"] > 0}
    return _out("gkin", all(checks.values()), checks=checks, reject_rate=t["reject_rate"],
                rejected=t["rejected"], reject_rate_by_dir=t["reject_rate_by_dir"], dir_err_q=t["dir_err_q"],
                mag_q=t["mag_q"], tick_speed_q=t["tick_speed_q"], dq_ratio_q=t["dq_ratio_q"], ee_speed_p999_min=spd,
                chunk_cap_min=cap, branches=t["branches"], snaps=t["snaps"])


def _log(path):
    out = []
    for x in open(path, encoding="utf-8"):
        if x.startswith("{"):
            try:
                out.append(json.loads(x))
            except json.JSONDecodeError:
                pass
    return out


def gate_g0(a):
    recs = _log(a.log)
    t = json.load(open(a.stats))["total"]
    j = [r for r in recs if r.get("event") == "sr1d_branches"]
    tr = [r for r in recs if r.get("event") == "train"]
    nb = sorted({r.get("n_branch") for r in tr})
    ok = bool(j) and j[-1]["joined"] == t["branches"] and j[-1]["missing"] == 0 and nb == [8] and len(tr) > 0
    return _out("g0", ok, join=j[-1] if j else None, branches=t["branches"], n_branch=nb, steps=len(tr))


def gate_g1(a):
    def snaps(p):
        return [json.loads(x) for x in open(p, encoding="utf-8") if '"event": "snap"' in x]
    e, r = snaps(a.eval), snaps(a.sr0)
    by = {x["key"]: x for x in r}
    diffs = [float(np.linalg.norm(np.asarray(x["c"]["pred"][:3]) - np.asarray(by[x["key"]]["c"]["pred"][:3])))
             for x in e if x["key"] in by]
    a1 = V0.pool([[V0.snap_stats(x, False) for x in e]], range(len(e)))["a_xy"]
    a0 = V0.pool([[V0.snap_stats(x, False) for x in r]], range(len(r)))["a_xy"]
    ok = len(diffs) == len(e) == len(r) and float(np.median(diffs)) <= 1e-3 and abs(a1 - a0) <= 0.005
    return _out("g1", ok, n=len(e), matched=len(diffs), disp_diff_median_m=float(np.median(diffs)) if diffs else None,
                disp_diff_max_m=max(diffs) if diffs else None, a_xy=a1, a_xy_sr0=a0)


def gate_g2(a):
    recs = _log(a.log)
    tr = [r for r in recs if r.get("event") == "train"]
    fin = all(math.isfinite(v) for r in tr for k, v in r.items() if isinstance(v, float))
    el = tr[-1]["elapsed_s"] if tr else None
    ok = bool(tr) and fin and el <= a.max_s
    return _out("g2", ok, steps=len(tr), elapsed_s=el, max_s=a.max_s, finite=fin)


def gate_cfg(a):
    c = next(r for r in _log(a.log) if r.get("event") == "config")["args"]
    r = next(x for x in _log(a.ref) if x.get("event") == "config")["args"]
    diff = sorted(k for k in set(c) | set(r) if c.get(k) != r.get(k) and k not in CFG_ALLOWED
                  and not (k not in r and NEW_OFF.get(k, object()) == c.get(k)))
    return _out("cfg", not diff, diff={k: [c.get(k), r.get(k)] for k in diff})


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ga")
    p.add_argument("--meta", required=True)
    p = sub.add_parser("gkin")
    p.add_argument("--stats", required=True)
    p.add_argument("--strata", required=True)
    p = sub.add_parser("g0")
    p.add_argument("--log", required=True)
    p.add_argument("--stats", required=True)
    p = sub.add_parser("g1")
    p.add_argument("--eval", required=True)
    p.add_argument("--sr0", required=True)
    p = sub.add_parser("g2")
    p.add_argument("--log", required=True)
    p.add_argument("--max-s", type=float, default=4444.0)
    p = sub.add_parser("cfg")
    p.add_argument("--log", required=True)
    p.add_argument("--ref", required=True)
    a = ap.parse_args(argv)
    rc = {"ga": gate_ga, "gkin": gate_gkin, "g0": gate_g0, "g1": gate_g1, "g2": gate_g2, "cfg": gate_cfg}[a.cmd](a)
    sys.exit(rc)


if __name__ == "__main__":
    main()
