"""S-E2E pre-registered criteria (docs/stage3/prereg_se2e.md §4) from the run logs. Prints one JSON.
usage: python se2e_verdict.py <out_root> <runA> <runB> <total> <mid> [<drivers_dir>]
  <out_root>/<run>/log.jsonl                 main run (train / eval / ckpt / save_load records)
  <out_root>/<run>/evalck.jsonl              evalck of ckpt/step_<mid> against the log (--step mid)
  <out_root>/<run>_resume/log.jsonl          resume from ckpt/step_<mid>, --stop-at mid + 50
  <drivers_dir>/driver_A.out, driver_B.out   run_seed.sh output with "main rc=", "evalck rc=", "resume rc=" lines
                                             (criterion (a) "rc 0"; runA -> A, runB -> B)
Committed to the repo before the results were read (R7 cycle 13 N3). Thresholds are the pre-registered ones; "<=" uses
the canon §74 comparison tolerance CMP_EPS = 1e-12 (relative, as harvest.analysis.stats.at_most) so a value equal to
the threshold up to float rounding passes.
"""
import json
import math
import os
import re
import sys

root, runs, total, mid = sys.argv[1], sys.argv[2:4], int(sys.argv[4]), int(sys.argv[5])
drivers = sys.argv[6] if len(sys.argv) > 6 else None
K = 50
DEC_S, DEC_F, FM_S, FM_F, MSE_S = 0.70, 0.80, 0.80, 0.90, 0.80
REL_MED, REL_MAX = 1e-2, 5e-2
CMP_EPS = 1e-12


def le(a, b):
    return a <= b + CMP_EPS * max(1.0, abs(b))


def driver_rc(tag):
    """rc values printed by run_seed.sh for main / evalck / resume; None when the file or a line is missing."""
    p = os.path.join(drivers, f"driver_{tag}.out") if drivers else None
    txt = open(p).read() if p and os.path.exists(p) else ""
    out = {}
    for k in ("main", "evalck", "resume"):
        m = re.findall(rf"{k} rc=(-?\d+)", txt)
        out[k] = int(m[-1]) if m else None
    return out


def load(p):
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


def verdict(run):
    log = load(os.path.join(root, run, "log.jsonl"))
    tr = [r for r in log if r["event"] == "train"]
    ev = [r for r in log if r["event"] == "eval"]
    out = {"run": run}
    steps = [r["step"] for r in tr]
    finite = all(math.isfinite(r[k]) for r in tr for k in ("fm", "dec", "total", "grad_norm"))
    finite &= all(math.isfinite(r[k]) for r in ev for k in ("fm", "dec", "sample_mse_norm"))
    ck = [r["step"] for r in log if r["event"] == "ckpt"]
    out["a"] = {"train_steps_1_to_total": steps == list(range(1, total + 1)), "finite": finite,
                "final_eval": bool(ev) and ev[-1]["step"] == total, "final_ckpt": total in ck,
                "last_saved": os.path.exists(os.path.join(root, run, "last", "heads.pt"))}
    if drivers is not None:
        rc = driver_rc("A" if run == runs[0] else "B")
        out["a"]["rc_all_zero"] = all(v == 0 for v in rc.values())
    out["a"]["pass"] = all(out["a"].values())
    if drivers is not None:
        out["a"]["rc"] = rc
    e0, eN = ev[0], ev[-1]
    last3 = ev[-3:]
    sm = {k: sum(r[k] for r in last3) / 3 for k in ("dec", "fm", "sample_mse_norm")}
    out["b"] = {"eval_steps": [r["step"] for r in ev], "last3_steps": [r["step"] for r in last3],
                "dec0": e0["dec"], "dec_final": eN["dec"], "dec_last3": sm["dec"],
                "fm0": e0["fm"], "fm_final": eN["fm"], "fm_last3": sm["fm"],
                "mse0": e0["sample_mse_norm"], "mse_final": eN["sample_mse_norm"], "mse_last3": sm["sample_mse_norm"],
                "b1": le(sm["dec"], DEC_S * e0["dec"]) and le(eN["dec"], DEC_F * e0["dec"]),
                "b2": le(sm["fm"], FM_S * e0["fm"]) and le(eN["fm"], FM_F * e0["fm"]),
                "b3": le(sm["sample_mse_norm"], MSE_S * e0["sample_mse_norm"])}
    out["b"]["pass"] = out["b"]["b1"] and out["b"]["b2"] and out["b"]["b3"]
    sl = [r for r in log if r["event"] == "save_load"]
    ec = load(os.path.join(root, run, "evalck.jsonl"))
    ec = [r for r in ec if r.get("step") == mid]
    out["c"] = {"final_max_abs_action_diff": sl[-1]["max_abs_action_diff"] if sl else None,
                "final_eval_equal": sl[-1]["eval_equal"] if sl else None,
                "mid_step": mid, "mid_equal": ec[-1]["equal"] if ec else None,
                "mid_max_abs_diff": ec[-1]["max_abs_diff"] if ec else None}
    out["c"]["pass"] = (bool(sl) and sl[-1]["max_abs_action_diff"] == 0.0 and sl[-1]["eval_equal"] is True
                        and bool(ec) and ec[-1]["equal"] is True)
    rs = [r for r in load(os.path.join(root, run + "_resume", "log.jsonl")) if r["event"] == "train"]
    orig = {r["step"]: r for r in tr}
    keys = ("fm", "dec", "total", "grad_norm", "lr_heads", "idx")
    same = [all(r[k] == orig[r["step"]][k] for k in keys) for r in rs]
    rel = sorted(abs(r["total"] - orig[r["step"]]["total"]) / abs(orig[r["step"]]["total"]) for r in rs[1:])
    first = rs[0] if rs else None
    e = {"steps": [rs[0]["step"], rs[-1]["step"]] if rs else None, "n": len(rs),
         "bit_identical_steps": sum(same), "bit_identical_all": bool(rs) and all(same),
         "idx_lr_identical_all": bool(rs) and all(r["idx"] == orig[r["step"]]["idx"]
                                                  and r["lr_heads"] == orig[r["step"]]["lr_heads"] for r in rs),
         "first_step_losses_identical": bool(first) and all(first[k] == orig[first["step"]][k]
                                                            for k in ("fm", "dec", "total")),
         "rel_total_median": rel[len(rel) // 2] if rel else None, "rel_total_max": rel[-1] if rel else None}
    tol = (e["n"] == K and e["idx_lr_identical_all"] and e["first_step_losses_identical"] and rel
           and le(e["rel_total_median"], REL_MED) and le(e["rel_total_max"], REL_MAX))
    e["grade"] = "bit" if e["n"] == K and e["bit_identical_all"] else ("tolerance" if tol else "fail")
    e["pass"] = e["grade"] != "fail"
    out["e"] = e
    return out


res = [verdict(r) for r in runs]
print(json.dumps({"runs": res, "d_both_seeds_abc": all(r["a"]["pass"] and r["b"]["pass"] and r["c"]["pass"]
                                                       for r in res),
                  "e_resume": [r["e"]["grade"] for r in res]}, indent=1))
