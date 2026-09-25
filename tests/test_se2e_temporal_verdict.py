"""tools/se2e/temporal_verdict.py (prereg_se2e_temporal §6) on synthetic predictions."""
import json
import math
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "se2e", "temporal_verdict.py")
CELLS = ("single+none", "video2+none", "single+motion", "video2+motion")


def _write(tmp, acc_all, trans_extra, p95):
    """20 snapshots x 3 questions; the first 10 snapshots are transitions. acc_all[cell] = fraction correct on the
    steady snapshots, trans_extra[cell] = the same on transition snapshots."""
    flags = {f"RB1_ep{i}_k0": {"transition": i < 10, "per_q": {q: i < 10 for q in ("dir_xy", "dir_z", "mag_coarse")}}
             for i in range(20)}
    tp = tmp / "trans.json"
    tp.write_text(json.dumps({"meta": {}, "flags": flags}))
    pred = []
    for c in CELLS:
        p = tmp / f"{c}.jsonl"
        recs = []
        for i in range(20):
            frac = trans_extra[c] if i < 10 else acc_all[c]
            for j, q in enumerate(("dir_xy", "dir_z", "mag_coarse")):
                ok = (i * 3 + j) % 10 < round(frac * 10)
                lp = {"a": math.log(0.7), "b": math.log(0.3)} if ok else {"a": math.log(0.3), "b": math.log(0.7)}
                recs.append({"event": "item", "key": f"RB1_ep{i}_k0", "question": q, "target": ["a"],
                             "pred": "a" if ok else "b", "correct": ok, "lp": lp})
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        pred.append(f"{c}={p}")
    lp_ = tmp / "lat.json"
    lp_.write_text(json.dumps({"formats": {c: {"full_p95": p95[c]} for c in CELLS}}))
    return pred, tp, lp_


def _run(tmp, *args):
    pred, tp, lp = _write(tmp, *args)
    out = tmp / "v.json"
    subprocess.run([sys.executable, TOOL, "--pred", *pred, "--trans", str(tp), "--lat", str(lp), "--out", str(out)],
                   check=True, capture_output=True)
    return json.load(open(out))


def test_video_adopted_motion_rejected_by_transition_drop(tmp_path):
    steady = {"single+none": 0.7, "video2+none": 0.8, "single+motion": 1.0, "video2+motion": 1.0}
    trans = {"single+none": 0.6, "video2+none": 0.7, "single+motion": 0.4, "video2+motion": 0.5}
    lat = {"single+none": 0.30, "video2+none": 0.31, "single+motion": 0.30, "video2+motion": 0.31}
    v = _run(tmp_path, steady, trans, lat)
    assert v["verdict"]["V"]["adopt"] is True
    assert abs(v["main_effects_acc"]["transition"]["V"] - 0.1) < 1e-9
    assert v["verdict"]["M"]["c1_gain"] is True and v["verdict"]["M"]["c2_transition"] is False
    assert v["verdict"]["M"]["adopt"] is False
    assert abs(v["interaction_acc"]["all"]) < 1e-9 or v["interaction_acc"]["all"] is not None


def test_latency_rule(tmp_path):
    steady = {"single+none": 0.6, "video2+none": 0.8, "single+motion": 0.6, "video2+motion": 0.8}
    trans = dict(steady)
    lat = {"single+none": 0.30, "video2+none": 0.34, "single+motion": 0.30, "video2+motion": 0.34}
    v = _run(tmp_path, steady, trans, lat)
    assert v["verdict"]["V"]["c1_gain"] and v["verdict"]["V"]["c2_transition"]
    assert v["verdict"]["V"]["c3_latency"] is False and v["verdict"]["V"]["adopt"] is False  # +13 % > 10 %
    assert v["verdict"]["M"]["adopt"] is False  # no gain
