"""E-SR1c verdict (docs/stage3/prereg_sr1c.md §4): stratified metrics and the fixed rule of tools/sr1c/sr1c_verdict.py."""
import importlib.util
import math
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sr1c_verdict", os.path.join(ROOT, "tools", "sr1c", "sr1c_verdict.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

DIRS = ("plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
        "plus_x_minus_y")
UNIT = {"plus_x": (1, 0), "plus_x_plus_y": (1, 1), "plus_y": (0, 1), "minus_x_plus_y": (-1, 1), "minus_x": (-1, 0),
        "minus_x_minus_y": (-1, -1), "minus_y": (0, -1), "plus_x_minus_y": (1, -1), "none_xy": (0, 0)}


def _v(name, n=0.01):
    u = np.asarray(UNIT[name], float)
    return (u / np.linalg.norm(u) * n) if np.linalg.norm(u) else u


def snap(i, stratum="far", follow=True, task="mug_tray", label="plus_x", mse=0.02, end_err=0.004, grip=0.5,
         pen=False, preds_ok=True, edits_follow=True):
    """A synthetic sr1c_eval 'snap' record: follow=True -> every xy:d chunk moves along d; else along +x."""
    c = {}
    for d in DIRS + ("none_xy",):
        v = _v(d) if follow else _v("plus_x")
        c[f"xy:{d}"] = [v[0], v[1], 0.0, 1.0, 1.0, mse, -0.05 if pen else 0.0]
    for z, dz in (("up", 0.005), ("down", -0.005), ("none_z", 0.0)):
        c[f"z:{z}"] = [0.01, 0.0, dz, 1.0, 1.0, mse, min(dz, 0.0)]
    for k, m in enumerate(("tiny", "small", "medium", "large", "xlarge")):
        c[f"mag:{m}"] = [0.002 * (k + 1), 0.0, 0.0, 1.0, 1.0, mse, 0.0]
    tv = _v(label)
    c["true"] = [tv[0], tv[1], 0.0, 1.0, 1.0, mse, 0.0]
    c["pred"] = list(c["true"])
    c["flip"] = [-tv[0], -tv[1], 0.0, 1.0, 1.0, mse * 2, 0.0]
    c["pid:close"] = [0, 0, 0, 1.0, 0.5 - grip / 2, mse, 0.0]
    c["pid:open"] = [0, 0, 0, 1.0, 0.5 + grip / 2, mse, 0.0]
    edits = {}
    for th in (30, -30, 45, -45, 90, -90, 180):
        t = math.radians(th)
        e = [0.02 * math.cos(t), 0.02 * math.sin(t)]
        edits[f"edit:{th}"] = [e[0], e[1], "plus_x", "medium"]
        v = e if edits_follow else [0.02, 0.0]
        c[f"edit:{th}"] = [v[0], v[1], 0.0, 1.0, 1.0, mse, 0.0]
    labels = {"dir_xy": label, "dir_z": "none_z", "mag_coarse": "medium", "target": "o3", "phase": "continue"}
    preds = dict(labels) if preds_ok else {**labels, "target": "o5", "phase": "hold"}
    a = {"far": 1.0, "near": 0.0, "band": 0.5}[stratum]
    return {"event": "snap", "i": i, "id": f"dr/{task}/P0/ep{10000 + i}/k10", "key": f"P0_ep{10000 + i}_k10",
            "labels": labels, "preds": preds, "disp_gt": [0.02, 0.0, 0.0], "c": c, "a_priv": a, "stratum": stratum,
            "a_hat": a, "dist_priv": 0.2 if stratum == "far" else 0.03, "dist_hat": 0.2 if stratum == "far" else 0.03,
            "phase": "approach", "auth_model": None, "tcp_z": 0.03 if pen else 0.2, "true_end_err": end_err,
            "edits": edits}


def run(n_far=10, n_near=10, **kw):
    far_kw = {k: v for k, v in kw.items() if k in ("follow", "edits_follow")}
    near_kw = {k: v for k, v in kw.items() if k not in ("follow", "edits_follow")}
    return [V.snap_stats(snap(i, "far", **far_kw)) for i in range(n_far)] + \
        [V.snap_stats(snap(100 + i, "near", **near_kw)) for i in range(n_near)]


def test_far_adherence_edits_and_strata():
    s = V.summarize(run(follow=True))
    assert s["far"]["a_xy"] == 1.0 and s["far"]["n_snap"] == 10 and s["near"]["n_snap"] == 10
    assert s["far"]["edit"]["45"] == 1.0 and s["far"]["edit"]["180"] == 1.0
    s = V.summarize(run(follow=False, edits_follow=False))
    assert s["far"]["a_xy"] == pytest.approx(2 / 7)  # only plus_x_plus_y and plus_x_minus_y within 60 deg of +x
    assert s["far"]["edit"]["30"] == 1.0 and s["far"]["edit"]["90"] == 0.0 and s["far"]["edit"]["180"] == 0.0
    assert s["far"]["edit_plausible"] == pytest.approx(1.0) and s["far"]["edit_stress"] == 0.0


def test_near_non_inferiority_metrics():
    s = V.summarize(run(mse=0.03, end_err=0.006, grip=0.05, preds_ok=False))
    n = s["near"]
    assert n["mse_true"] == pytest.approx(0.03) and n["end_err_median"] == pytest.approx(0.006)
    assert n["grip_hit"] == 0.0 and n["acc_target_phase"] == 0.0 and n["true_rate"] == 1.0


def test_penetration_proxy_and_decision_accuracy():
    s = V.summarize(run(pen=True))
    assert s["all"]["pen_rate"] == pytest.approx(0.5)  # the near snapshots (tcp 3 cm, chunk dips 5 cm)
    assert s["all"]["dec_acc"] == 1.0


def _metrics(a_far, mse=0.02, end=0.004, grip=0.95, acc_tp=0.99, true_near=0.9, true_all=0.92, pen=0.0, acc=0.94,
             p95=30.0, a_z=0.9, rho=0.6):
    return {"far": {"a_xy": a_far, "a_z": a_z, "rho_mean": rho, "n_snap": 379},
            "near": {"mse_true": mse, "end_err_median": end, "grip_hit": grip, "acc_target_phase": acc_tp,
                     "true_rate": true_near, "n_snap": 821},
            "all": {"true_rate": true_all, "pen_rate": pen, "dec_acc": acc}, "latency_p95_ms": p95}


def test_rule_adopt_near_bleed_and_boundary():
    c0 = _metrics(0.40)
    ok = V.arm_check(_metrics(0.85), c0)
    assert ok["adopt"] and ok["grade"] == "FULL" and not ok["near_bleed"] and not ok["boundary"]
    xy = V.arm_check(_metrics(0.85, a_z=0.7), c0)
    assert xy["adopt"] and xy["grade"] == "XY"
    bleed = V.arm_check(_metrics(0.90, mse=0.02 * 1.06), c0)
    assert not bleed["adopt"] and bleed["near_bleed"] and bleed["fails"] == ["N1"]
    assert V.arm_check(_metrics(0.90, end=0.004 * 1.11), c0)["fails"] == ["N2"]
    assert V.arm_check(_metrics(0.90, grip=0.95 - 0.021), c0)["fails"] == ["N3"]
    assert V.arm_check(_metrics(0.90, acc_tp=0.99 - 0.011), c0)["fails"] == ["N4"]
    assert V.arm_check(_metrics(0.90, true_near=0.9 - 0.021), c0)["fails"] == ["N5"]
    assert V.arm_check(_metrics(0.90, true_all=0.899), c0)["fails"] == ["i"]
    assert V.arm_check(_metrics(0.90, pen=0.021), c0)["fails"] == ["ii"]
    assert V.arm_check(_metrics(0.90, acc=0.94 - 0.011), c0)["fails"] == ["iii"]
    assert V.arm_check(_metrics(0.90, p95=40.001), c0)["fails"] == ["iv"]
    # exact boundaries pass (CMP_EPS)
    edge = V.arm_check(_metrics(0.80, mse=0.02 * 1.05, end=0.004 * 1.10, grip=0.93, acc_tp=0.98, true_near=0.88,
                                true_all=0.90, pen=0.02, acc=0.93, p95=40.0), c0)
    assert edge["adopt"], edge["fails"]
    assert V.arm_check(_metrics(0.799), c0)["fails"] == ["far"]
    assert V.arm_check(_metrics(0.78), c0)["boundary"] and V.arm_check(_metrics(0.83), c0)["boundary"]
    assert not V.arm_check(_metrics(0.831), c0)["boundary"]


def test_rule_choice_between_arms():
    c0 = _metrics(0.40)
    a1, a2 = V.arm_check(_metrics(0.86), c0), V.arm_check(_metrics(0.90), c0)
    assert V.choose(a1, a2, diff=0.04, diff_lo=0.01)["verdict"] == "ADOPT_C2"
    assert V.choose(a1, a2, diff=0.04, diff_lo=-0.001)["verdict"] == "ADOPT_C1"  # CI touches 0: simpler arm
    assert V.choose(a1, a2, diff=0.029, diff_lo=0.01)["verdict"] == "ADOPT_C1"
    no = V.arm_check(_metrics(0.5), c0)
    assert V.choose(no, a2, 0.4, 0.3)["verdict"] == "ADOPT_C2"
    assert V.choose(a1, no, -0.4, -0.5)["verdict"] == "ADOPT_C1"
    assert V.choose(no, no, 0.0, 0.0)["verdict"] == "RUN_S"
    b = V.arm_check(_metrics(0.81), c0)
    assert V.choose(b, no, 0, 0)["verdict"] == "NEED_SEED1"


def test_rule_structural_fallback():
    c0 = _metrics(0.40)
    c0["far"]["end_err_median"] = 0.010
    s = _metrics(0.995)
    s["far"]["end_err_median"] = 0.0115
    assert V.struct_check(s, c0)["verdict"] == "STRUCT"
    s["far"]["end_err_median"] = 0.0116
    assert V.struct_check(s, c0)["verdict"] == "NONE"
    s = _metrics(0.98)
    s["far"]["end_err_median"] = 0.01
    assert V.struct_check(s, c0)["verdict"] == "S_BUG"


def _write(path, snaps, p95=30.0, n=None):
    import json
    with open(path, "w") as f:
        for s in snaps:
            f.write(json.dumps(s) + "\n")
        f.write(json.dumps({"event": "summary", "n": len(snaps) if n is None else n, "keys_sha": "x",
                            "latency_ms": {"p95": p95}}) + "\n")


def test_cli_end_to_end_and_input_checks(tmp_path):
    import json
    far0 = [snap(i, "far", follow=False) for i in range(6)]
    far1 = [snap(i, "far", follow=True) for i in range(6)]
    near = [snap(100 + i, "near") for i in range(6)]
    _write(tmp_path / "c0.jsonl", far0 + near)
    _write(tmp_path / "c1.jsonl", far1 + near)
    _write(tmp_path / "c2.jsonl", far1 + near)
    V.main(["--c0", str(tmp_path / "c0.jsonl"), "--c1", str(tmp_path / "c1.jsonl"), "--c2", str(tmp_path / "c2.jsonl"),
            "--n", "12", "--boot", "50", "--out", str(tmp_path / "v.json")])
    r = json.load(open(tmp_path / "v.json"))
    assert r["arms"]["c1"]["adopt"] and r["choice"]["verdict"] == "ADOPT_C1"  # equal arms: the simpler one
    assert r["summary"]["c0"]["far"]["a_xy"] == pytest.approx(2 / 7)
    _write(tmp_path / "bad.jsonl", far1 + near, n=13)
    with pytest.raises(SystemExit):
        V.main(["--c0", str(tmp_path / "c0.jsonl"), "--c1", str(tmp_path / "bad.jsonl"), "--n", "12",
                "--out", str(tmp_path / "v2.json")])
    dup = far1 + near[:-1] + [snap(100, "near")]
    _write(tmp_path / "dup.jsonl", dup)
    with pytest.raises(SystemExit):
        V.main(["--c0", str(tmp_path / "c0.jsonl"), "--c1", str(tmp_path / "dup.jsonl"), "--n", "12",
                "--out", str(tmp_path / "v3.json")])


def test_seed_average():
    a = _metrics(0.78)
    b = _metrics(0.84)
    m = V.average([a, b])
    assert m["far"]["a_xy"] == pytest.approx(0.81) and m["near"]["mse_true"] == pytest.approx(0.02)
