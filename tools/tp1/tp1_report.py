"""E-TP1 report (prereg_tp1 §4-§5; pod venv python, PYTHONPATH = code dir).
Per model (<run>_q<steps> / <run>_final; runs off_s0, on_s0, off_s1): on the held-out L9 v2 ego rows the point pixel
error to the label point (scores point_px; invalid / missing = inf), median and > 20 px rate; on rows whose label has an
approach: family accuracy and rot within +-1 bin; answer schema failures; final models the L8-X 7 sets (3D median,
> 20 mm). Paired bootstrap (rows, 10,000 / L8-X 2,000, seed 0): A/A off_s1-off_s0 and on_s0-off_s0, on_s0-off_s1.
usage: python tools/tp1/tp1_report.py <tp1 out dir> [--out report.json]"""
import glob
import json
import os
import sys

import numpy as np

PX, MM = 20.0, 20.0


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


def load(out, model, arm, labels):
    d = os.path.join(out, "eval", model, f"l9_eval_{arm}")
    rep = {json.loads(x)["id"]: json.loads(x)["text"] for x in open(os.path.join(d, "replies.jsonl"))}
    px = {}
    for x in open(os.path.join(d, "scores.jsonl")):
        s = json.loads(x)
        v = s.get("point_px")
        px[s["id"]] = float(v) if (s.get("valid") and v is not None) else float("inf")
    rows = {}
    for i, lab in labels.items():
        if i not in rep:
            continue
        c = parse(rep[i])
        r = {"px": px.get(i, float("inf")), "schema_fail": float(c is None)}
        if lab.get("approach"):
            r["fam"] = float((c or {}).get("approach") == lab["approach"])
            rot = (c or {}).get("rot")
            r["rot_pm1"] = float(isinstance(rot, int) and isinstance(lab.get("rot"), int) and circ(rot, lab["rot"]) <= 1)
        rows[i] = r
    return rows


def lx(out, model):
    res = {}
    for f in sorted(glob.glob(os.path.join(out, "eval", model, "x_*_d-min_clean", "scores.jsonl"))):
        sc = {}
        for x in open(f):
            s = json.loads(x)
            if s.get("approach_row"):
                v = s.get("approach_3d_mm")
                sc[s["id"]] = float("inf") if (v is None or not s.get("valid")) else float(v)
        res[os.path.basename(os.path.dirname(f))[2:-12]] = sc
    return res


med = lambda v: float(np.median(np.where(np.isfinite(v), v, 1e4)))  # noqa: E731
fail_px = lambda v: float(np.mean(v > PX))  # noqa: E731
fail_mm = lambda v: float(np.mean(v > MM))  # noqa: E731
mean = lambda v: float(np.mean(v))  # noqa: E731


def boot(x, y, stat, reps=10000, seed=0):
    ids = sorted(set(x) & set(y))
    if len(ids) < 20:
        return None
    a, b = np.array([x[i] for i in ids], float), np.array([y[i] for i in ids], float)
    idx = np.random.default_rng(seed).integers(0, len(ids), size=(reps, len(ids)))
    d = np.array([stat(b[k]) - stat(a[k]) for k in idx])
    return [round(stat(b) - stat(a), 4), round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]


def col(rows, k):
    return {i: r[k] for i, r in rows.items() if k in r}


def main():
    a = sys.argv[1:]
    out = a[0]
    labels = {}
    for x in open(os.path.join(out, "data", "l9_eval_off.jsonl")):
        r = json.loads(x)
        if r.get("kind", "control") != "control" or r.get("label_missing"):
            continue
        labels[r["id"]] = (json.loads(r["answer"]).get("command") or {})
    steps = {k: int(open(os.path.join(out, f"steps_{k}.txt")).read()) for k in ("off", "on")}
    runs = {"off_s0": "off", "on_s0": "on", "off_s1": "off"}
    rep, R = {"steps": steps, "label_rows": len(labels), "grasp_label_rows": sum(1 for v in labels.values() if v.get("approach")),
              "models": {}}, {}
    for run, arm in runs.items():
        for tag in (f"q{steps[arm] // 4}", f"q{steps[arm] // 2}", "final"):
            m = f"{run}_{tag}"
            if not os.path.exists(os.path.join(out, "eval", m, f"l9_eval_{arm}", "scores.jsonl")):
                continue
            rows = load(out, m, arm, labels)
            R[(run, {f"q{steps[arm] // 4}": "25", f"q{steps[arm] // 2}": "50", "final": "final"}[tag])] = rows
            v = np.array([r["px"] for r in rows.values()])
            e = {"n": len(rows), "px_median": round(med(v), 2), "px_fail20": round(fail_px(v), 4),
                 "schema_fail": round(mean(np.array([r["schema_fail"] for r in rows.values()])), 4),
                 "fam_acc": round(mean(np.array(list(col(rows, "fam").values()))), 4) if col(rows, "fam") else None,
                 "rot_pm1": round(mean(np.array(list(col(rows, "rot_pm1").values()))), 4) if col(rows, "rot_pm1") else None}
            if tag == "final":
                L = lx(out, m)
                R[(run, "l8x")] = L
                e["l8x"] = {s: {"n": len(d), "median_mm": round(med(np.array(list(d.values()))), 2),
                                "fail20": round(fail_mm(np.array(list(d.values()))), 4)} for s, d in L.items()}
            rep["models"][m] = e
    cmp = {}
    for tag in ("25", "50", "final"):
        for lab, (x, y) in {"AA_off_s1-off_s0": ("off_s0", "off_s1"), "on_s0-off_s0": ("off_s0", "on_s0"),
                            "on_s0-off_s1": ("off_s1", "on_s0")}.items():
            if (x, tag) not in R or (y, tag) not in R:
                continue
            rx, ry = R[(x, tag)], R[(y, tag)]
            c = {"px_median": boot(col(rx, "px"), col(ry, "px"), med), "px_fail20": boot(col(rx, "px"), col(ry, "px"), fail_px),
                 "fam_acc": boot(col(rx, "fam"), col(ry, "fam"), mean), "rot_pm1": boot(col(rx, "rot_pm1"), col(ry, "rot_pm1"), mean)}
            if tag == "final" and (x, "l8x") in R and (y, "l8x") in R:
                c["l8x_fail20"] = {s: boot(R[(x, "l8x")][s], R[(y, "l8x")].get(s, {}), fail_mm, reps=2000) for s in R[(x, "l8x")]}
            cmp[f"{lab}@{tag}"] = c
    rep["compare"] = cmp
    rep["decision"] = decide(cmp)
    s = json.dumps(rep, indent=1)
    if "--out" in a:
        open(a[a.index("--out") + 1], "w").write(s)
    print(s)


def decide(cmp):
    """prereg_tp1 §5 (fixed before results)."""
    aa, c0, c1 = cmp.get("AA_off_s1-off_s0@final"), cmp.get("on_s0-off_s0@final"), cmp.get("on_s0-off_s1@final")
    if not (aa and c0 and c1):
        return {"result": "INCOMPLETE"}

    def m(k, floor, d=aa):
        v = d.get(k)
        return floor if not v else max(floor, (v[2] - v[1]) / 2, abs(v[0]))
    mf, mm_, mfam = m("px_fail20", 0.02), m("px_median", 3.0), m("fam_acc", 0.03)
    ml = {s: max(0.02, (v[2] - v[1]) / 2, abs(v[0])) if v else 0.02 for s, v in (aa.get("l8x_fail20") or {}).items()}

    def ni(c):
        ok = c["px_fail20"][2] <= mf and c["px_median"][2] <= mm_ and (c["fam_acc"] is None or c["fam_acc"][1] >= -mfam)
        for s, v in (c.get("l8x_fail20") or {}).items():
            ok = ok and v is not None and v[2] <= ml.get(s, 0.02)
        return ok
    if ni(c0) and ni(c1):
        better = all(c["px_fail20"][0] <= -mf and c["px_fail20"][2] < 0 for c in (c0, c1))
        r = "ON_BETTER" if better else "ON_NONINF"
    else:
        r = "ON_WORSE"
    return {"result": r, "margin_px_fail20": round(mf, 4), "margin_px_median": round(mm_, 2), "margin_fam": round(mfam, 4),
            "margin_l8x": {s: round(v, 4) for s, v in ml.items()},
            "note": "early pilot: re-run at 7,500 L9 v2 episodes"}


if __name__ == "__main__":
    main()
