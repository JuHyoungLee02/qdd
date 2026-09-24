"""labels_v2 (docs/stage3/results/labels_v2.md prereg): write v2 labels next to the DEV snapshots and measure
the S1-text code-rule gate, label distributions, agreement with the old oracle and with the outcome-based labels.

usage (pod, CPU only):
  python labels_v2_eval.py --dev /data/harvest/data/jsel_dev --selfcheck /data/harvest/data/pool_selfcheck \
      --out /data/harvest/labels_v2/eval_step1.json [--step-cm 1] [--write]
--write: /data/harvest/data/jsel_dev/{P0,P1,P2}.labels_v2.jsonl (one row per snapshot line; originals untouched).

POOL mode (stageA_sft.md step 1): --pool /data/harvest/data/pool --out JSON --step-cm 0.1 [--write]
  labels for every pool line -> <pool>.labels_v2.jsonl (stagea_data.labels_v2_path; outside the folder so the
  ep*.jsonl globs are unaffected). The pool `oracle` field is dropped on read (never used: no progress, no
  old-oracle agreement). Gate = the S1-text code rule on all lines and on the decision snapshots.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harvest.e3lite import state_text  # noqa: E402
from harvest.labels_v2 import (ALIGN_XY_M, DEADBAND_M, MAG_EDGES_M, QUESTIONS, _obs, code_rule_v2,  # noqa: E402
                               labels)
from harvest.sim.snapshot import stage_of  # noqa: E402

GATED = ("dir_xy", "dir_z", "mag_coarse", "target", "phase_choice")
OUTCOME_Q = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
             "phase_choice": "phase"}


def lines(dev):
    for kind in ("P0", "P1", "P2"):
        ps = [p for p in glob.glob(f"{dev}/{kind}/ep*.jsonl") if re.fullmatch(r"ep\d+\.jsonl", os.path.basename(p))]
        for p in sorted(ps, key=lambda x: int(os.path.basename(x)[2:-6])):
            for x in open(p, encoding="utf-8"):
                yield kind, json.loads(x)


def pool_lines(pool):
    """Pool lines without the `oracle` field (canon §52-§54: never a target, never read here)."""
    ps = [p for p in glob.glob(f"{pool}/ep*.jsonl") if re.fullmatch(r"ep\d+\.jsonl", os.path.basename(p))]
    for p in sorted(ps, key=lambda x: int(os.path.basename(x)[2:-6])):
        for x in open(p, encoding="utf-8"):
            ln = json.loads(x)
            ln.pop("oracle", None)
            yield ln


def pool_label_rows(lines):
    rows = []
    for ln in lines:
        lab = labels(ln)
        lab.pop("progress", None)  # labels_v2 progress = the old oracle value; not defined on the pool
        rows.append({"seed": ln["seed"], "kind": ln["kind"], "k": ln["k"], "t": ln["t"], "ds_id": ln.get("ds_id"),
                     "split": ln.get("split"), "decision": bool(ln.get("decision")), "planner_phase": ln["phase"],
                     "stage": stage_of(ln["phase"]), "labels_v2": lab})
    return rows


def write_rows(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def pool_main(a):
    from harvest.train.stagea_data import labels_v2_path
    lines = list(pool_lines(a.pool))
    rows = pool_label_rows(lines)
    qs = GATED + ("motion_phase",)
    res = {"n_lines": len(rows), "step_cm": a.step_cm, "n_episodes": len({(r["seed"], r["kind"]) for r in rows})}
    mism = []
    for subset, pick in (("all", lambda r: True), ("decision", lambda r: r["decision"])):
        sel = [(ln, r) for ln, r in zip(lines, rows) if pick(r)]
        ok = defaultdict(list)
        for ln, r in sel:
            rule = code_rule_v2(state_text(ln, "S1", step_cm=a.step_cm))
            for q in qs:
                ok[q].append(rule[q] == r["labels_v2"][q])
                if subset == "all" and rule[q] != r["labels_v2"][q] and q in GATED:
                    mism.append({"snap": f"{ln['kind']}_s{ln['seed']}_k{ln['k']}", "q": q, "label": r["labels_v2"][q],
                                 "rule": rule[q], "M": r["labels_v2"]["motion_phase"], "M_rule": rule["motion_phase"],
                                 "delta_m": r["labels_v2"]["delta_m"], "decision": r["decision"],
                                 "cause": cause(ln, r["labels_v2"], rule, q, a.step_cm / 100)})
        gate = {q: round(float(np.mean(v)), 4) for q, v in ok.items()}
        res[f"gate_{subset}"] = {"n": len(sel), **gate}
        res[f"gate_pass_{subset}"] = {q: gate[q] >= 0.95 for q in GATED}
    res["mismatch_causes"] = {q: dict(Counter(m["cause"] for m in mism if m["q"] == q)) for q in GATED}
    for subset, pick in (("all", lambda r: True), ("decision_fit", lambda r: r["decision"] and r["split"] == "fit"),
                         ("decision_eval", lambda r: r["decision"] and r["split"] == "eval")):
        sel = [r for r in rows if pick(r)]
        d = {q: dict(Counter(r["labels_v2"][q] for r in sel).most_common()) for q in qs}
        maj = {q: round(max(v.values()) / len(sel), 4) for q, v in d.items()}
        res[f"dist_{subset}"] = {"n": len(sel), "dist": d, "majority": maj,
                                 "majority_mean_gated": round(float(np.mean([maj[q] for q in GATED])), 4)}
    res["split_episodes"] = dict(Counter(r["split"] for r in rows if r["k"] == 0))
    res["decision_per_split"] = dict(Counter(r["split"] for r in rows if r["decision"]))
    if a.write:
        res["labels_file"] = labels_v2_path(a.pool)
        write_rows(rows, res["labels_file"])
    json.dump(res, open(a.out, "w"), indent=1)
    with open(a.out.replace(".json", "_mismatch.jsonl"), "w") as f:
        for m in mism:
            f.write(json.dumps(m) + "\n")
    print(json.dumps({k: v for k, v in res.items() if not k.startswith("dist")}, indent=1))


def cause(line, lab, rule, q, step_m):
    """Why the S1-text rule differs from the label: the nearest threshold to the true value within one print step."""
    if rule["motion_phase"] != lab["motion_phase"]:
        g, rel, _, _ = _obs(line["state"])
        o = "o3" if lab["motion_phase"] in ("approach", "grasp") else "o5"
        h = float(np.hypot(*rel[o][:2])) if o in rel else float("nan")
        return "align_1.5cm" if abs(h - ALIGN_XY_M) <= 1.5 * step_m else "motion_other"
    d = np.asarray(lab["delta_m"])
    if q == "dir_xy":
        near = min(abs(abs(d[0]) - DEADBAND_M), abs(abs(d[1]) - DEADBAND_M))
        return "deadband_1cm" if near <= 1.5 * step_m else "other"
    if q == "dir_z":
        return "deadband_1cm" if abs(abs(d[2]) - DEADBAND_M) <= 1.5 * step_m else "other"
    if q == "mag_coarse":
        n = float(np.linalg.norm(d))
        return "mag_edge" if min(abs(n - e) for e in MAG_EDGES_M) <= 2 * step_m else "other"
    if q == "phase_choice":
        if (lab["dir_xy"], lab["dir_z"]) != (rule["dir_xy"], rule["dir_z"]):
            return "reached_via_deadband"
        return "facts_other"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="")
    ap.add_argument("--pool", default="", help="POOL mode (see module doc)")
    ap.add_argument("--selfcheck", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--step-cm", type=float, default=1)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    step_m = a.step_cm / 100
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    if a.pool:
        return pool_main(a)

    rows, files = [], defaultdict(list)
    for kind, ln in lines(a.dev):
        lab = labels(ln)
        files[kind].append({"seed": ln["seed"], "kind": kind, "k": ln["k"], "t": ln["t"], "ds_id": ln.get("ds_id"),
                            "planner_phase": ln["phase"], "stage": stage_of(ln["phase"]), "labels_v2": lab})
        if ln["oracle"] is None:
            continue
        rule = code_rule_v2(state_text(ln, "S1", step_cm=a.step_cm))
        rows.append((kind, ln, lab, rule))
    if a.write:
        for kind, rs in files.items():
            with open(f"{a.dev}/{kind}.labels_v2.jsonl", "w") as f:
                for r in rs:
                    f.write(json.dumps(r) + "\n")

    out = {"n_lines": sum(len(v) for v in files.values()), "n_snap": len(rows), "step_cm": a.step_cm}
    # gate
    gate, causes, mism = {}, {}, []
    for q in QUESTIONS:
        ok = [r[3][q] == r[2][q] for r in rows]
        gate[q] = round(float(np.mean(ok)), 4)
        c = Counter()
        for (kind, ln, lab, rule), o in zip(rows, ok):
            if not o and q in GATED:
                cz = cause(ln, lab, rule, q, step_m)
                c[cz] += 1
                mism.append({"snap": f"{kind}_s{ln['seed']}_k{ln['k']}", "q": q, "label": lab[q], "rule": rule[q],
                             "M": lab["motion_phase"], "M_rule": rule["motion_phase"], "delta_m": lab["delta_m"],
                             "cause": cz})
        causes[q] = dict(c)
    gate["motion_phase"] = round(float(np.mean([r[3]["motion_phase"] == r[2]["motion_phase"] for r in rows])), 4)
    out["gate"], out["gate_pass"] = gate, {q: gate[q] >= 0.95 for q in GATED}
    out["mismatch_causes"] = causes
    # distributions, old-oracle agreement
    dist, conf, agree, maj = {}, {}, {}, {}
    for q in QUESTIONS + ("motion_phase",):
        c = Counter(r[2][q] for r in rows)
        dist[q] = dict(c.most_common())
        maj[q] = round(c.most_common(1)[0][1] / len(rows), 4)
        if q in QUESTIONS:
            agree[q] = round(float(np.mean([r[1]["oracle"][q] == r[2][q] for r in rows])), 4)
            conf[q] = {f"{o}->{n}": v for (o, n), v in Counter((r[1]["oracle"][q], r[2][q]) for r in rows).most_common()}
    out["dist"], out["majority"], out["agree_old"], out["confusion_old_to_new"] = dist, maj, agree, conf
    out["majority_pooled_gated"] = round(float(np.mean([maj[q] for q in GATED])), 4)
    out["M_vs_planner_phase"] = {f"{p}->{m}": v for (p, m), v in
                                 Counter((r[1]["phase"], r[2]["motion_phase"]) for r in rows).most_common()}
    # outcome-based labels (T14 self-check), matched by (seed, kind, k) with the same planner phase and t
    if a.selfcheck:
        snap = {(ln["seed"], kind, ln["k"]): (ln, lab) for kind, ln, lab, _ in rows}
        by = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))  # rule -> q -> [n, new in best, old in best]
        n_rows = n_match = n_phase_mismatch = 0
        size, matched = defaultdict(list), set()
        for p in sorted(glob.glob(f"{a.selfcheck}/dev*_P*.jsonl")):
            for x in open(p):
                try:
                    r = json.loads(x)
                except json.JSONDecodeError:  # a file still being written by the self-check run
                    continue
                n_rows += 1
                key = (r["seed"], r["kind"], r["k"])
                qn = {v: k for k, v in OUTCOME_Q.items()}.get(r["question"])
                if key not in snap or qn is None:
                    continue
                ln, lab = snap[key]
                if ln["phase"] != r["phase"] or abs(ln["t"] - r["t"]) > 1e-6:
                    n_phase_mismatch += 1
                    continue
                n_match += 1
                matched.add(key)
                for ru, best in r["best_by_rule"].items():
                    b = by[ru][qn]
                    b[0] += 1
                    b[1] += lab[qn] in best
                    b[2] += ln["oracle"][qn] in best
                    size[(ru, qn)].append(len(best) / r["n_options"])
        out["outcome"] = {"n_rows": n_rows, "n_matched_rows": n_match, "n_phase_or_t_mismatch": n_phase_mismatch,
                          "n_snap": len(matched),
                          "by_rule": {ru: {q: {"n": v[0], "new_in_best": round(v[1] / v[0], 4),
                                               "old_in_best": round(v[2] / v[0], 4),
                                               "best_frac_of_options": round(float(np.mean(size[(ru, q)])), 4)}
                                           for q, v in d.items()} for ru, d in by.items()}}
    json.dump(out, open(a.out, "w"), indent=1)
    with open(a.out.replace(".json", "_mismatch.jsonl"), "w") as f:
        for m in mism:
            f.write(json.dumps(m) + "\n")
    print(json.dumps({k: out[k] for k in ("n_lines", "n_snap", "step_cm", "gate", "gate_pass", "mismatch_causes",
                                          "majority", "agree_old")}, indent=1))


if __name__ == "__main__":
    main()
