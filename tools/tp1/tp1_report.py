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


def load(out, model, labels, sub="l9_eval"):
    """labels: {id: label command} for the ids to score; empty/None -> load every control row's own label from
    <out>/data/<sub>.jsonl (change 7: e.g. the l9_eval_tpdir subset, whose ids are not in the off-arm labels dict)."""
    d = os.path.join(out, "eval", model, sub)
    if not os.path.exists(os.path.join(d, "scores.jsonl")):
        return {}
    if not labels:
        dp = os.path.join(out, "data", f"{sub}.jsonl")
        labels = {}
        if os.path.exists(dp):
            for x in open(dp, encoding="utf-8"):
                r = json.loads(x)
                if r.get("kind", "control") != "control" or r.get("label_missing"):
                    continue
                labels[r["id"]] = json.loads(r["answer"]).get("command") or {}
    rep = {json.loads(x)["id"]: json.loads(x)["text"] for x in open(os.path.join(d, "replies.jsonl"))}
    px = {}
    for x in open(os.path.join(d, "scores.jsonl")):
        s = json.loads(x)
        v = s.get("point_px")
        px[s["id"]] = float(v) if (s.get("valid") and v is not None) else float("inf")
    rows = {}
    for i in labels:
        lab = labels.get(i)
        if i not in rep:
            continue
        # change 7 (bug fix 10-03): a row whose LABEL is not a point command (mode keep/close/edit, no point_2d) has
        # no target pixel -- metrics.score leaves point_px None for it, same as a prediction that missed. Only rows
        # whose label HAS a point_2d go into the px aggregate (n, median, fail20); those where the prediction still
        # produced no matching point count as inf (a real failure), not excluded.
        label_has_point = bool(lab) and lab.get("point_2d") is not None
        c = parse(rep[i])
        r = {"px": px.get(i, float("inf")) if label_has_point else None, "has_px_label": label_has_point,
             "schema_fail": float(c is None)}
        if lab and lab.get("approach"):
            r["fam"] = float((c or {}).get("approach") == lab["approach"])
            rot = (c or {}).get("rot")
            r["rot_pm1"] = float(isinstance(rot, int) and isinstance(lab.get("rot"), int) and circ(rot, lab["rot"]) <= 1)
        rows[i] = r
    return rows


def persp(out, model):
    """change 3: perspective hold-out items -> {id: {"ok": 0/1, "kind", "stratum"}}; P ok = the predicted point is
    nearer the true robot-frame spot than the opposite-direction spot; Q / Y ok = exact label."""
    from harvest.astra_motion.schema import SchemaError, extract_json
    items = {json.loads(x)["id"]: json.loads(x) for x in open(os.path.join(out, "data", "persp_eval.jsonl"))}
    rp = os.path.join(out, "eval", model, "persp", "replies.jsonl")
    if not os.path.exists(rp):
        return {}
    res = {}
    for x in open(rp):
        r = json.loads(x)
        it = items.get(r["id"])
        if it is None:
            continue
        try:
            d = extract_json(r["text"] or "")
        except (SchemaError, ValueError, TypeError):
            d = {}
        t, ok = it["truth"], 0.0
        if it["aux_kind"] == "P":
            p = d.get("point_2d") if isinstance(d, dict) else None
            if isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p):
                u, v = p[0] / 1000 * t["W"], p[1] / 1000 * t["H"]
                ok = float(np.hypot(u - t["px"][0], v - t["px"][1]) < np.hypot(u - t["px_opp"][0], v - t["px_opp"][1]))
        elif it["aux_kind"] == "Q":
            ok = float(isinstance(d, dict) and d.get("relation") == t["relation"])
        else:
            ok = float(isinstance(d, dict) and d.get("camera_facing") == t["camera_facing"])
        res[r["id"]] = {"ok": ok, "kind": it["aux_kind"], "stratum": it["stratum"]}
    return res


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
    return {i: r[k] for i, r in rows.items() if r.get(k) is not None}


def main():
    a = sys.argv[1:]
    out = a[0]
    # change 6 (user 10-03): the primary set is l9_test = the HOLDOUT_FROZEN definitions (+ eval_ood when it has
    # episodes); --subset all = every held-out definition of this build (secondary)
    subset = a[a.index("--subset") + 1] if "--subset" in a else "l9test"
    from harvest.l9.alloc9 import HOLDOUT_FROZEN
    labels = {}
    for x in open(os.path.join(out, "data", "l9_eval_off.jsonl")):
        r = json.loads(x)
        if r.get("kind", "control") != "control" or r.get("label_missing"):
            continue
        if subset == "l9test" and r.get("task_def") not in HOLDOUT_FROZEN:
            continue
        labels[r["id"]] = (json.loads(r["answer"]).get("command") or {})
    steps = {k: int(open(os.path.join(out, f"steps_{k}.txt")).read()) for k in ("off", "on", "onaux")
             if os.path.exists(os.path.join(out, f"steps_{k}.txt"))}
    runs = {"off_s0": "off", "on_s0": "on", "off_s1": "off", "onaux_s0": "onaux"}  # onaux: change 3
    rep, R = {"subset": subset, "l8x_note": "old-convention (L8 labels), secondary", "steps": steps, "label_rows": len(labels), "grasp_label_rows": sum(1 for v in labels.values() if v.get("approach")),
              "models": {}}, {}
    for run, arm in runs.items():
        if arm not in steps:
            continue
        for tag in (f"q{steps[arm] // 4}", f"q{steps[arm] // 2}", "final"):
            m = f"{run}_{tag}"
            if not os.path.exists(os.path.join(out, "eval", m, "EVAL_DONE")):
                continue
            key = {f"q{steps[arm] // 4}": "25", f"q{steps[arm] // 2}": "50", "final": "final"}[tag]
            rows = load(out, m, labels)
            R[(run, key)] = rows
            pz = persp(out, m)
            R[(run, key, "persp")] = pz
            prim = [z["ok"] for z in pz.values() if z["stratum"] != "head_std" and z["kind"] in "PQ"]
            pxv = col(rows, "px")  # change 7: only rows whose LABEL is a point command
            v = np.array(list(pxv.values())) if pxv else np.array([np.inf])
            e = {"persp": {f"{st}/{k}": round(mean(np.array([z["ok"] for z in pz.values()
                                                            if z["stratum"] == st and z["kind"] == k])), 4)
                           for st in ("head_std", "head_tilt", "third_person") for k in ("P", "Q", "Y")
                           if any(z["stratum"] == st and z["kind"] == k for z in pz.values())},
                 "persp_primary": round(mean(np.array(prim)), 4) if prim else None,
                 "n": len(rows), "n_point_label": len(pxv), "px_median": round(med(v), 2), "px_fail20": round(fail_px(v), 4),
                 "schema_fail": round(mean(np.array([r["schema_fail"] for r in rows.values()])), 4),
                 "fam_acc": round(mean(np.array(list(col(rows, "fam").values()))), 4) if col(rows, "fam") else None,
                 "rot_pm1": round(mean(np.array(list(col(rows, "rot_pm1").values()))), 4) if col(rows, "rot_pm1") else None}
            if tag == "final":
                tq = load(out, m, {}, "l9_eval_tpdir")
                tpxv = col(tq, "px")
                tv = np.array(list(tpxv.values())) if tpxv else np.array([np.inf])
                e["tpdir"] = {"n": len(tq), "n_point_label": len(tpxv), "px_median": round(med(tv), 2),
                             "px_fail20": round(fail_px(tv), 4)}
                L = lx(out, m)
                R[(run, "l8x")] = L
                e["l8x"] = {s: {"n": len(d), "median_mm": round(med(np.array(list(d.values()))), 2),
                                "fail20": round(fail_mm(np.array(list(d.values()))), 4)} for s, d in L.items()}
            rep["models"][m] = e
    cmp = {}
    for tag in ("25", "50", "final"):
        for lab, (x, y) in {"AA_off_s1-off_s0": ("off_s0", "off_s1"), "on_s0-off_s0": ("off_s0", "on_s0"),
                            "on_s0-off_s1": ("off_s1", "on_s0"), "onaux_s0-on_s0": ("on_s0", "onaux_s0")}.items():
            if (x, tag) not in R or (y, tag) not in R:
                continue
            rx, ry = R[(x, tag)], R[(y, tag)]
            c = {"px_median": boot(col(rx, "px"), col(ry, "px"), med), "px_fail20": boot(col(rx, "px"), col(ry, "px"), fail_px),
                 "fam_acc": boot(col(rx, "fam"), col(ry, "fam"), mean), "rot_pm1": boot(col(rx, "rot_pm1"), col(ry, "rot_pm1"), mean)}
            zx, zy = R.get((x, tag, "persp"), {}), R.get((y, tag, "persp"), {})
            c["persp_primary"] = boot({i: v["ok"] for i, v in zx.items() if v["stratum"] != "head_std" and v["kind"] in "PQ"},
                                      {i: v["ok"] for i, v in zy.items() if v["stratum"] != "head_std" and v["kind"] in "PQ"}, mean)
            c["persp_all"] = boot({i: v["ok"] for i, v in zx.items()}, {i: v["ok"] for i, v in zy.items()}, mean)
            if tag == "final" and (x, "l8x") in R and (y, "l8x") in R:
                c["l8x_fail20"] = {s: boot(R[(x, "l8x")][s], R[(y, "l8x")].get(s, {}), fail_mm, reps=2000) for s in R[(x, "l8x")]}
            cmp[f"{lab}@{tag}"] = c
    rep["compare"] = cmp
    rep["decision"] = decide(cmp)
    rep["decision_aux"] = decide_aux(cmp)
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
        return ok  # change 6: L8-X (old convention) is reported, not judged
    if ni(c0) and ni(c1):
        better = all(c["px_fail20"][0] <= -mf and c["px_fail20"][2] < 0 for c in (c0, c1))
        r = "ON_BETTER" if better else "ON_NONINF"
    else:
        r = "ON_WORSE"
    return {"result": r, "margin_px_fail20": round(mf, 4), "margin_px_median": round(mm_, 2), "margin_fam": round(mfam, 4),
            "margin_l8x": {s: round(v, 4) for s, v in ml.items()},
            "note": "early pilot: re-run at 7,500 L9 v2 episodes"}


def decide_aux(cmp):
    """prereg_tp1 change 3: arm 4 (onaux_s0) against on_s0 -- primary = perspective accuracy (third-person + tilted
    head strata, P and Q); ego non-inferiority as in §5 (margins from the off A/A pair)."""
    aa, c = cmp.get("AA_off_s1-off_s0@final"), cmp.get("onaux_s0-on_s0@final")
    if not (aa and c and c.get("persp_primary")):
        return {"result": "INCOMPLETE"}

    def m(k, floor):
        v = aa.get(k)
        return floor if not v else max(floor, (v[2] - v[1]) / 2, abs(v[0]))
    mp, mf, mm_, mfam = m("persp_primary", 0.03), m("px_fail20", 0.02), m("px_median", 3.0), m("fam_acc", 0.03)
    ego_ok = c["px_fail20"][2] <= mf and c["px_median"][2] <= mm_ and (c["fam_acc"] is None or c["fam_acc"][1] >= -mfam)
    p = c["persp_primary"]
    r = "AUX_WORSE" if not ego_ok else ("AUX_BETTER" if (p[0] >= mp and p[1] > 0) else "AUX_SAME")
    return {"result": r, "margin_persp": round(mp, 4), "persp_primary_diff": p}


if __name__ == "__main__":
    main()
