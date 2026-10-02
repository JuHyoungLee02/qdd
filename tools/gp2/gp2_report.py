"""E-GP2 early pilot report (prereg_gp2 §5-§6; pure, pod venv python, PYTHONPATH = code dir).
Per model (<run>_q<steps> / <run>_final): on the held-out L9 v2 grasp rows (truth_eval.jsonl) approach-family accuracy,
rotation-bin exact / within +-1 bin (circular over the 12 bins) / mean circular bin error, each against the run's
own label (arm a: rot_bin_img, arm b: rot_bin_base; an invalid or missing answer counts as wrong, error 6); point
error = approach 3D error (harvest.teach_pt.metrics scores) on the same rows and on all held-out approach rows;
final models also the L8-X 7 sets (median, > 20 mm rate). Paired bootstrap (rows, 10,000 draws, seed 0) for
b-a_s0, b-a_s2 and the A/A pair a_s2-a_s0; decision of prereg §6.
usage: python tools/gp2/gp2_report.py <gp2 out dir> [--out report.json]"""
import glob
import json
import os
import sys

import numpy as np

FAIL_MM = 20.0
REPS = 10000


def parse(text):
    from harvest.astra_motion.schema import SchemaError, extract_json
    try:
        d = extract_json(text or "")
    except (SchemaError, ValueError, TypeError):
        return None
    c = d.get("command") if isinstance(d, dict) else None
    return c if isinstance(c, dict) else None


def circ(a, b):
    d = abs(int(a) - int(b)) % 12
    return min(d, 12 - d)


def per_row(out, model, arm, truth):
    key = "rot_bin_img" if arm == "a" else "rot_bin_base"
    d = os.path.join(out, "eval", model, f"l9_eval_{arm}")
    rep = {}
    for x in open(os.path.join(d, "replies.jsonl")):
        r = json.loads(x)
        rep[r["id"]] = r["text"]
    sc = {}
    for x in open(os.path.join(d, "scores.jsonl")):
        s = json.loads(x)
        if s.get("approach_row"):
            v = s.get("approach_3d_mm")
            sc[s["id"]] = float("inf") if (v is None or not s.get("valid")) else float(v)
    rows = {}
    for t in truth:
        if t["id"] not in rep:
            continue
        c = parse(rep[t["id"]]) or {}
        fam_ok = c.get("approach") == t["family"]
        rot = c.get("rot")
        ok_rot = isinstance(rot, int) and 0 <= rot <= 11
        e = circ(rot, t[key]) if ok_rot else 6
        rows[t["id"]] = {"fam": float(fam_ok), "rot_exact": float(e == 0), "rot_pm1": float(e <= 1), "rot_err": float(e),
                         "pt_mm": sc.get(t["id"], float("inf")), "family": t["family"], "robot": t.get("robot"),
                         "instructed": t.get("instructed")}
    allpt = list(sc.values())
    return rows, allpt


def summ(rows):
    if not rows:
        return {}
    v = list(rows.values())
    pt = np.array([r["pt_mm"] for r in v])
    return {"n": len(v), "fam_acc": round(float(np.mean([r["fam"] for r in v])), 4),
            "rot_exact": round(float(np.mean([r["rot_exact"] for r in v])), 4),
            "rot_pm1": round(float(np.mean([r["rot_pm1"] for r in v])), 4),
            "rot_err_bins": round(float(np.mean([r["rot_err"] for r in v])), 3),
            "pt_median_mm": round(float(np.median(np.where(np.isfinite(pt), pt, 1e9))), 2),
            "pt_fail20": round(float(np.mean(pt > FAIL_MM)), 4)}


def by(rows, k):
    out = {}
    for v in sorted({r[k] for r in rows.values()}, key=str):
        out[str(v)] = summ({i: r for i, r in rows.items() if r[k] == v})
    return out


def lx_sets(out, model):
    res = {}
    for f in sorted(glob.glob(os.path.join(out, "eval", model, "x_*_d-min_clean", "scores.jsonl"))):
        sc = {}
        for x in open(f):
            s = json.loads(x)
            if s.get("approach_row"):
                v = s.get("approach_3d_mm")
                sc[s["id"]] = float("inf") if (v is None or not s.get("valid")) else float(v)
        res[os.path.basename(os.path.dirname(f))] = sc
    return res


def boot(x, y, stat, reps=REPS, seed=0):
    """paired bootstrap over shared ids of stat(y) - stat(x): (diff, lo, hi)."""
    ids = sorted(set(x) & set(y))
    if len(ids) < 20:
        return None
    a, b = np.array([x[i] for i in ids]), np.array([y[i] for i in ids])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ids), size=(reps, len(ids)))
    d = np.array([stat(b[k]) - stat(a[k]) for k in idx])
    return [round(float(stat(b) - stat(a)), 4), round(float(np.percentile(d, 2.5)), 4),
            round(float(np.percentile(d, 97.5)), 4)]


def main():
    a = sys.argv[1:]
    out = a[0]
    truth = [json.loads(x) for x in open(os.path.join(out, "data", "truth_eval.jsonl"))]
    steps = int(open(os.path.join(out, "steps_a.txt")).read())
    runs = {"a_s0": "a", "b_s0": "b", "a_s2": "a"}
    rep = {"steps": steps, "truth_rows": len(truth), "models": {}}
    R = {}
    for run, arm in runs.items():
        for tag in (f"q{steps // 4}", f"q{steps // 2}", "final"):
            m = f"{run}_{tag}"
            if not os.path.exists(os.path.join(out, "eval", m, f"l9_eval_{arm}", "scores.jsonl")):
                continue
            rows, allpt = per_row(out, m, arm, truth)
            R[m] = rows
            ap = np.array(allpt)
            e = {"grasp": summ(rows), "by_family": by(rows, "family"), "by_robot": by(rows, "robot"),
                 "all_approach_rows": {"n": len(ap), "median_mm": round(float(np.median(np.where(np.isfinite(ap), ap, 1e9))), 2)
                                       if len(ap) else None, "fail20": round(float(np.mean(ap > FAIL_MM)), 4) if len(ap) else None}}
            if tag == "final":
                lx = lx_sets(out, m)
                e["l8x"] = {k: {"n": len(v), "median_mm": round(float(np.median(np.where(np.isfinite(list(v.values())),
                                                                                          list(v.values()), 1e9))), 2),
                                "fail20": round(float(np.mean(np.array(list(v.values())) > FAIL_MM)), 4)}
                            for k, v in lx.items()}
                R[m + "_l8x"] = lx
            rep["models"][m] = e
    mean = np.mean
    fail = lambda v: np.mean(v > FAIL_MM)  # noqa: E731
    med = lambda v: np.median(np.where(np.isfinite(v), v, 1e4))  # noqa: E731
    cmp = {}
    for tag in (f"q{steps // 4}", f"q{steps // 2}", "final"):
        for lab, (x, y) in {"AA_a_s2-a_s0": ("a_s0", "a_s2"), "b_s0-a_s0": ("a_s0", "b_s0"),
                            "b_s0-a_s2": ("a_s2", "b_s0")}.items():
            mx, my = f"{x}_{tag}", f"{y}_{tag}"
            if mx not in R or my not in R:
                continue
            c = {}
            for k in ("rot_pm1", "rot_exact", "fam"):
                c[k] = boot({i: r[k] for i, r in R[mx].items()}, {i: r[k] for i, r in R[my].items()}, mean)
            c["rot_err_bins"] = boot({i: r["rot_err"] for i, r in R[mx].items()},
                                     {i: r["rot_err"] for i, r in R[my].items()}, mean)
            px, py = ({i: r["pt_mm"] for i, r in R[m].items()} for m in (mx, my))
            c["pt_median_mm"] = boot(px, py, med)
            c["pt_fail20"] = boot(px, py, fail)
            if tag == "final" and mx + "_l8x" in R and my + "_l8x" in R:
                c["l8x"] = {s: {"median_mm": boot(R[mx + "_l8x"][s], R[my + "_l8x"].get(s, {}), med, reps=2000),
                                "fail20": boot(R[mx + "_l8x"][s], R[my + "_l8x"].get(s, {}), fail, reps=2000)}
                            for s in R[mx + "_l8x"]}
            cmp[f"{lab}@{tag}"] = c
    rep["compare"] = cmp
    rep["decision"] = decide(cmp, f"final")
    s = json.dumps(rep, indent=1)
    if "--out" in a:
        open(a[a.index("--out") + 1], "w").write(s)
    print(s)


def decide(cmp, tag):
    """prereg_gp2 §6 (fixed before results)."""
    aa = cmp.get(f"AA_a_s2-a_s0@{tag}")
    b0, b2 = cmp.get(f"b_s0-a_s0@{tag}"), cmp.get(f"b_s0-a_s2@{tag}")
    if not (aa and b0 and b2) or not aa.get("rot_pm1") or not b0.get("rot_pm1") or not b2.get("rot_pm1"):
        return {"result": "INCOMPLETE"}
    m = max(0.03, (aa["rot_pm1"][2] - aa["rot_pm1"][1]) / 2, abs(aa["rot_pm1"][0]))
    nf = max(0.03, (aa["fam"][2] - aa["fam"][1]) / 2, abs(aa["fam"][0]))
    np_ = max(0.02, (aa["pt_fail20"][2] - aa["pt_fail20"][1]) / 2, abs(aa["pt_fail20"][0]))

    def ni(c):  # b not worse than that a run: family accuracy, point > 20 mm rate, L8-X > 20 mm rates
        ok = c["fam"][1] >= -nf and c["pt_fail20"][2] <= np_
        for s, v in (c.get("l8x") or {}).items():
            aav = ((aa.get("l8x") or {}).get(s) or {}).get("fail20")
            ml = max(0.02, (aav[2] - aav[1]) / 2) if aav else 0.02
            ok = ok and v["fail20"] is not None and v["fail20"][2] <= ml
        return ok
    win_b = all(c["rot_pm1"][0] >= m and c["rot_pm1"][1] > 0 for c in (b0, b2))
    win_a = all(c["rot_pm1"][0] <= -m and c["rot_pm1"][2] < 0 for c in (b0, b2))
    if win_b and ni(b0) and ni(b2):
        r = "B_BETTER"
    elif win_b:
        r = "B_BETTER_BUT_NI_FAIL"
    elif win_a:
        r = "A_BETTER"
    else:
        r = "SAME"
    return {"result": r, "margin_rot_pm1": round(m, 4), "margin_fam": round(nf, 4), "margin_pt_fail20": round(np_, 4),
            "keep": "b (base frame)" if r == "B_BETTER" else "a (image frame)",
            "note": "early pilot: re-run at 7,500 L9 v2 episodes before the format is frozen"}


if __name__ == "__main__":
    main()
