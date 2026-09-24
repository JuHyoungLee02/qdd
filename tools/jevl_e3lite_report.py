"""E3-lite summary (docs/stage3/results/e3lite.md prereg): per-condition A + episode-cluster CI, secondary metrics,
paired differences for decision rules (1)-(5), sensitivity without the ill-posed questions, latency.

usage: python jevl_e3lite_report.py DIR     (DIR = /data/harvest/e3lite: acc_*.jsonl, lat_*.jsonl, ub.json)
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

from harvest.analysis.stats import auroc, cluster_mean_ci, ece

D = sys.argv[1]
QS = ["dir_xy", "dir_z", "mag_coarse", "target", "phase", "progress"]
MODELS = {"4B": "Qwen3-VL-4B-Instruct", "8B": "Qwen3-VL-8B-Instruct"}
ub = json.load(open(f"{D}/ub.json"))
ILL = [q for q in ("dir_xy", "dir_z", "mag_coarse") if ub["UB"][q] < 0.95]
WELL = [q for q in QS if q not in ILL]

rows = {}
for f in sorted(glob.glob(f"{D}/acc_*.jsonl")):
    rs = [json.loads(x) for x in open(f, encoding="utf-8")]
    if not rs:
        continue
    m = [k for k, v in MODELS.items() if v == rs[0]["model"]][0]
    rows[(m, rs[0]["S"], rs[0]["inp"], rs[0]["order"])] = {(r["snap"], r["qid"]): r for r in rs}
conds = sorted(rows, key=lambda c: (c[0], c[3], c[2], c[1]))
common = set.intersection(*(set(v) for v in rows.values()))
common = sorted(common)
q_of = lambda k: k[1].split(".")[-1]
print(f"conditions {len(conds)}, common items {len(common)}, snapshots {len({k[0] for k in common})}; "
      f"ill-posed (UB<0.95): {ILL}")
name = lambda c: f"{c[0]} {c[1]} {'text+image' if c[2] == 'img' else 'text'} {c[3]}"


def keys_for(qs):
    return [k for k in common if q_of(k) in qs]


def acc_ci(c, qs=QS):
    by = defaultdict(list)
    for k in keys_for(qs):
        r = rows[c][k]
        by[(r["kind"], r["seed"])].append(int(r["correct"]))
    v = [x for xs in by.values() for x in xs]
    return float(np.mean(v)), cluster_mean_ci(by)


def diff(a, b, qs=QS):
    by = defaultdict(list)
    for k in keys_for(qs):
        ra, rb = rows[a][k], rows[b][k]
        by[(ra["kind"], ra["seed"])].append(int(ra["correct"]) - int(rb["correct"]))
    v = [x for xs in by.values() for x in xs]
    return float(np.mean(v)), cluster_mean_ci(by)


def majority(qs=QS):
    ok = []
    ref = rows[conds[0]]
    for q in qs:
        ks = [k for k in common if q_of(k) == q]
        vals = [ref[k]["oracle"] for k in ks]
        top = max(set(vals), key=vals.count)
        ok += [v == top for v in vals]
    return float(np.mean(ok))


fmt = lambda x, ci: f"{x:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]"
fmtd = lambda x, ci: f"{x:+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}]"
MAJ, MAJW = majority(), majority(WELL)
print(f"\nmajority baseline: 6 questions {MAJ:.4f}; well-posed {WELL} {MAJW:.4f}")
print("\n| condition | A (6q) [95% CI] | A well-posed [CI] | ECE | AUROC | NE | first-pos chosen / oracle | "
      "input tok (median) | errors |\n|---|---|---|---|---|---|---|---|---|")
A = {}
for c in conds:
    rs = [rows[c][k] for k in common]
    ok = [r["correct"] for r in rs]
    p = [r["p_chosen"] if r["p_chosen"] is not None else 0.0 for r in rs]
    a, ci = acc_ci(c)
    aw, ciw = acc_ci(c, WELL)
    A[c] = (a, ci, aw, ciw)
    au = auroc(p, ok)
    first = np.mean([r["key"] == r["first"] for r in rs])
    ofirst = np.mean([r["oracle"] == r["first"] for r in rs])
    tok = np.median([r["input_tokens"] for r in rs if r["input_tokens"] is not None])
    print(f"| {name(c)} | {fmt(a, ci)} | {fmt(aw, ciw)} | {ece(p, ok):.3f} | {au:.3f} | "
          f"{np.mean([r['ne'] for r in rs]):.4f} | {first:.3f} / {ofirst:.3f} | {tok:.0f} | "
          f"{sum(r['error'] is not None for r in rs)} |")

print("\n| condition | " + " | ".join(QS) + " |\n|---|" + "---|" * len(QS))
for c in conds:
    print(f"| {name(c)} | " + " | ".join(f"{np.mean([rows[c][k]['correct'] for k in keys_for([q])]):.3f}"
                                          for q in QS) + " |")
print(f"| UB (code rule, S1 numbers) | " + " | ".join(f"{ub['UB'][q]:.3f}" for q in QS) + " |")
print(f"| UB-raw (unrounded, diagnostic) | " + " | ".join(f"{ub['UB_raw'][q]:.3f}" for q in QS) + " |")
print(f"| majority | " + " | ".join(f"{ub['majority'][q]:.3f}" for q in QS) + " |")

print("\nfirst-position rate per question (chosen / oracle):")
print("| condition | " + " | ".join(QS) + " |\n|---|" + "---|" * len(QS))
for c in conds:
    cells = []
    for q in QS:
        rs = [rows[c][k] for k in keys_for([q])]
        cells.append(f"{np.mean([r['key'] == r['first'] for r in rs]):.2f}/{np.mean([r['oracle'] == r['first'] for r in rs]):.2f}")
    print(f"| {name(c)} | " + " | ".join(cells) + " |")


def decide(qs, label):
    print(f"\n### decisions ({label}: {qs})")
    Ai = lambda c: acc_ci(c, qs)[0]
    base = ("4B", "S0", "img", "fixed")
    have = lambda c: c in rows
    # (1)
    cand = [c for c in (("4B", s, "img", "fixed") for s in ("S0", "S1", "S2")) if have(c)]
    best = max(cand, key=Ai)
    gains = {c[1]: diff(c, base, qs) for c in cand if c != base}
    for s, (d, ci) in gains.items():
        print(f"(1) 4B text+image fixed {s} - S0: {fmtd(d, ci)}")
    pick = "S0"
    if best[1] != "S0" and gains[best[1]][1][0] > 0:
        pick = best[1]
        if pick == "S2" and ("4B", "S1", "img", "fixed") in rows:
            d, ci = diff(("4B", "S2", "img", "fixed"), ("4B", "S1", "img", "fixed"), qs)
            print(f"    S2 - S1: {fmtd(d, ci)}")
            if ci[0] <= 0 and gains["S1"][1][0] > 0:
                pick = "S1"
    print(f"(1) -> representation {pick} (best by A: {best[1]} {Ai(best):.4f})")
    # (2)
    c4, c8 = ("4B", pick, "img", "fixed"), ("8B", pick, "img", "fixed")
    model = "4B"
    if have(c8):
        d, ci = diff(c8, c4, qs)
        p95 = LAT.get(("8B", pick, "image"), (None, None))[1]
        print(f"(2) 8B - 4B at {pick} text+image fixed: {fmtd(d, ci)}; 8B N=4 p95 {p95}")
        if ci[0] > 0 and p95 is not None and p95 <= 0.33:
            model = "8B"
    print(f"(2) -> model {model}")
    # (3)
    ci_, ct_ = (model, pick, "img", "fixed"), (model, pick, "txt", "fixed")
    d, ci = diff(ci_, ct_, qs)
    img = ci[0] > 0
    print(f"(3) text+image - text ({model} {pick} fixed): {fmtd(d, ci)} -> "
          f"{'keep head image' if img else 'image adds nothing at this state'}")
    # (4)
    inp = "img" if img else "txt"
    d, ci = diff((model, pick, inp, "rot"), (model, pick, inp, "fixed"), qs)
    mand = abs(d) > 0.02 and (ci[0] > 0 or ci[1] < 0)
    print(f"(4) rotated - fixed ({model} {pick} {inp}): {fmtd(d, ci)} -> "
          f"{'C3 rotation mandatory' if mand else 'rotation not mandatory'}")
    for c in conds:
        if c[3] == "fixed" and (c[0], c[1], c[2], "rot") in rows:
            dd, cc = diff((c[0], c[1], c[2], "rot"), c, qs)
            print(f"    order effect {c[0]} {c[1]} {c[2]}: {fmtd(dd, cc)}")
    # (5)
    bestc = max(conds, key=Ai)
    a, ci = acc_ci(bestc, qs)
    maj = majority(qs)
    print(f"(5) best condition {name(bestc)} A {fmt(a, ci)} vs majority {maj:.4f} -> "
          f"{'Jev-L insufficient on this task' if a < maj else 'above majority'}"
          f"{' (CI includes majority)' if ci[0] <= maj <= ci[1] else ''}")
    # extra paired diffs used in the text
    for m in ("4B", "8B"):
        for inp2 in ("img", "txt"):
            for s in ("S1", "S2"):
                a2, b2 = (m, s, inp2, "fixed"), (m, "S0", inp2, "fixed")
                if have(a2) and have(b2):
                    d, ci = diff(a2, b2, qs)
                    print(f"    {m} {inp2} fixed {s} - S0: {fmtd(d, ci)}")
        for s in ("S0", "S1", "S2"):
            a2, b2 = (m, s, "img", "fixed"), (m, s, "txt", "fixed")
            if have(a2) and have(b2):
                d, ci = diff(a2, b2, qs)
                print(f"    {m} {s} fixed image - text: {fmtd(d, ci)}")
    for s in ("S0", "S1", "S2"):
        for inp2 in ("img", "txt"):
            a2, b2 = ("8B", s, inp2, "fixed"), ("4B", s, inp2, "fixed")
            if have(a2) and have(b2):
                d, ci = diff(a2, b2, qs)
                print(f"    8B - 4B {s} {inp2} fixed: {fmtd(d, ci)}")


LAT = {}
print("\n| model | state | mode | N | p50 | p95 | fail | input tok median | load1 median |\n|---|---|---|---|---|---|---|---|---|")
for f in sorted(glob.glob(f"{D}/lat_*.jsonl")):
    by = defaultdict(list)
    for x in open(f, encoding="utf-8"):
        r = json.loads(x)
        by[(r["model"], r["S"], r["mode"], r["N"])].append(r)
    for (mm, S, mode, n), rs in sorted(by.items()):
        lat = np.array([r["lat"] if r["lat"] is not None else np.inf for r in rs])
        p50, p95 = float(np.quantile(lat, 0.5)), float(np.quantile(lat, 0.95))
        m = [k for k, v in MODELS.items() if v == mm][0]
        LAT[(m, S, mode)] = (p50, p95)
        print(f"| {m} | {S} | {mode} | {n} | {p50:.3f} | {p95:.3f} | {sum(r['lat'] is None for r in rs)}/{len(rs)} | "
              f"{np.median([r['input_tokens'] for r in rs if r['input_tokens']]):.0f} | "
              f"{np.median([r['load1'] for r in rs]):.0f} |")

decide(QS, "pre-registered, 6 questions")
decide(WELL, "sensitivity, well-posed questions only")
