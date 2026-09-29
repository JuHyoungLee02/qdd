"""Post-hoc diagnostics for E-M4b-meas (NOT verdict inputs; e_m4b_meas.md "사후 분석"): where the P channel's
false alarms come from, and critic variants without the weakest P rule.

  python -m harvest.m4b.diag --out diag.json
"""
from __future__ import annotations

import argparse
import collections
import json

import numpy as np

from . import analyze as A
from . import prules as PR
from . import spec as FS


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fi", default="/data/harvest/m4b/fidev")
    ap.add_argument("--v1h", default="/data/harvest/m4b/v1h/logits.jsonl")
    ap.add_argument("--out", default="/data/harvest/m4b/diag.json")
    a = ap.parse_args(argv)
    from .data import fi_episodes
    eps = fi_episodes(a.fi, with_lines=False)
    fsn = [s for e in eps for s in e["snaps"]]
    cal = [s for s in fsn if s["split"] == "fi_cal"]
    keys = ("width", "grip_tau", "tcp_z", "tau_res")
    par = PR.fit({k: np.array([s[k] for s in cal]) for k in keys},
                 {p: np.array([bool(s["truth"][p]) for s in cal]) for p in FS.ROBOT})
    fe = {k: np.array([s[k] for s in fsn]) for k in keys}
    hr, sc = PR.apply(fe, par), PR.scores(fe, par)
    hard = {s["key"]: {p: float(hr[p][i]) for p in FS.ROBOT} for i, s in enumerate(fsn)}
    soft = {s["key"]: {p: float(sc[p][i]) for p in FS.ROBOT} for i, s in enumerate(fsn)}
    out = {"P_params": par}
    # (a) hard-rule violations on eval non-failure successes, by predicate and phase (2-tick persistence)
    nf = [e for e in eps if e["split"] == "fi_eval" and e["cond"] not in FS.FAILURES and e["success"]]
    by = collections.Counter()
    eps_by = collections.defaultdict(set)
    for e in nf:
        for p in FS.ROBOT:
            v = [A.viol_prob(s["phase"], hard[s["key"]], {p}) for s in e["snaps"]]
            per = A.M.persist(v, 2)
            for s, x in zip(e["snaps"], per):
                if x >= 1.0:
                    by[(p, s["phase"])] += 1
                    eps_by[p].add(e["ep"])
    out["hard_nonfail_viol_snaps_by_pred_phase"] = {f"{p}|{ph}": n for (p, ph), n in by.items()}
    out["hard_nonfail_eps_by_pred"] = {p: len(v) for p, v in eps_by.items()}
    # truth vs rule at those snapshots (is the TRUTH also violated there? = expectation-table transients)
    tv = collections.Counter()
    for e in nf:
        for s in e["snaps"]:
            for v in FS.violations(s["phase"], s["truth"]):
                tv[(v, s["phase"])] += 1
    out["truth_nonfail_viol_by_pred_phase"] = {f"{p}|{ph}": n for (p, ph), n in tv.items()}
    # (b) critic variants
    probs_h = None
    if a.v1h:
        lg = {}
        for x in open(a.v1h):
            r = json.loads(x)
            lg[r["key"]] = dict(zip(FS.PREDS, r["logits"]))
        is_cal = lambda s: s["split"] == "fi_cal"  # noqa: E731
        T = A.temperatures(lg, fsn, is_cal, FS.PREDS)
        probs_h = A.calibrated(lg, T)
    cal_e = lambda e: e["split"] == "fi_cal"  # noqa: E731
    ev_e = lambda e: e["split"] == "fi_eval"  # noqa: E731
    R3 = {"gripper_open", "holding_t", "lifted_holding"}
    W = set(FS.WORLD)
    cfg = {"P_no_stall": [("p", soft, R3)], "P_stall_only": [("p", soft, {"contact_stall"})]}
    if probs_h:
        cfg["V1h+P_no_stall"] = [("p", soft, R3), ("v", probs_h, W)]
        cfg["V1h+P(stall from V1h)"] = [("p", soft, R3), ("v", probs_h, W | {"contact_stall"})]
        cfg["V1h_robot_only"] = [("v", probs_h, set(FS.ROBOT))]
    out["critic_variants"] = {}
    for n, ch in cfg.items():
        r = A.critic(eps, ch, cal_e, ev_e)
        out["critic_variants"][n] = {k: v for k, v in r.items() if k not in ("false_alarm_eps",)}
    json.dump(out, open(a.out, "w"), indent=1, default=lambda o: None)
    print(json.dumps({k: v for k, v in out.items() if k != "critic_variants"}, indent=1))
    for n, r in out["critic_variants"].items():
        print(n, json.dumps({k: r[k] for k in ("fwer", "recall", "recall_by_type", "thr")}))


if __name__ == "__main__":
    main()
