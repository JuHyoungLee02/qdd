"""tools/se2e/motion_confirm_verdict.py (prereg_se2e_motion_confirm): pooled 2-seed motion effect on synthetic
predictions. Rule: confirmed iff pooled overall effect >= +0.015 AND its 95 % snapshot-cluster bootstrap lower bound
> 0 AND pooled transition effect >= -0.01."""
import json
import math
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "se2e", "motion_confirm_verdict.py")
RUNS = ("none_s1", "motion_s1", "none_s2", "motion_s2")
N = 200  # snapshots; the first half are transitions


def _write(tmp, steady, trans):
    """steady[run] / trans[run] = fraction of correct items on steady / transition snapshots."""
    flags = {f"RB1_ep{i}_k0": {"transition": i < N // 2, "per_q": {q: i < N // 2 for q in ("dir_xy", "dir_z",
                                                                                            "mag_coarse")}}
             for i in range(N)}
    tp = tmp / "trans.json"
    tp.write_text(json.dumps({"meta": {}, "flags": flags}))
    pred = []
    for c in RUNS:
        p = tmp / f"{c}.jsonl"
        recs = []
        for i in range(N):
            frac = trans[c] if i < N // 2 else steady[c]
            for j, q in enumerate(("dir_xy", "dir_z", "mag_coarse")):
                ok = (i * 3 + j) % 20 < round(frac * 20)
                lp = {"a": math.log(0.7), "b": math.log(0.3)} if ok else {"a": math.log(0.3), "b": math.log(0.7)}
                recs.append({"event": "item", "key": f"RB1_ep{i}_k0", "question": q, "target": ["a"],
                             "pred": "a" if ok else "b", "correct": ok, "lp": lp})
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        pred.append(f"{c}={p}")
    return pred, tp


def _run(tmp, steady, trans):
    pred, tp = _write(tmp, steady, trans)
    out = tmp / "v.json"
    subprocess.run([sys.executable, TOOL, "--pred", *pred, "--trans", str(tp), "--out", str(out)],
                   check=True, capture_output=True)
    return json.load(open(out))


def test_confirmed_when_both_seeds_gain(tmp_path):
    base = {"none_s1": 0.60, "motion_s1": 0.70, "none_s2": 0.60, "motion_s2": 0.70}
    v = _run(tmp_path, base, base)
    assert abs(v["pooled_effect"]["all"] - 0.10) < 1e-9
    assert v["bootstrap_95"]["all"][0] > 0 and v["verdict"]["confirmed"] is True
    assert abs(v["per_seed_effect"]["s1"]["all"] - 0.10) < 1e-9 and abs(v["seed_spread"]["all"]) < 1e-9


def test_small_gain_is_not_confirmed(tmp_path):
    st = {"none_s1": 0.60, "motion_s1": 0.60, "none_s2": 0.60, "motion_s2": 0.65}  # pooled +0.025 on steady only
    tr = {"none_s1": 0.60, "motion_s1": 0.60, "none_s2": 0.60, "motion_s2": 0.60}
    v = _run(tmp_path, st, tr)
    assert abs(v["pooled_effect"]["all"] - 0.0125) < 1e-9  # < 0.015
    assert v["verdict"]["c_point"] is False and v["verdict"]["confirmed"] is False
    assert abs(v["seed_spread"]["all"] - 0.025) < 1e-9  # |effect s2 - effect s1|


def test_transition_drop_blocks(tmp_path):
    st = {"none_s1": 0.50, "motion_s1": 0.80, "none_s2": 0.50, "motion_s2": 0.80}
    tr = {"none_s1": 0.70, "motion_s1": 0.65, "none_s2": 0.70, "motion_s2": 0.65}
    v = _run(tmp_path, st, tr)
    assert v["verdict"]["c_point"] is True and v["verdict"]["c_lower"] is True
    assert v["verdict"]["c_transition"] is False and v["verdict"]["confirmed"] is False
