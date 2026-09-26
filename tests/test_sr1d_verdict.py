"""E-SR1d verdict (docs/stage3/prereg_sr1d.md §4): the fixed rule of tools/sr1d/sr1d_verdict.py on synthetic runs."""
import importlib.util
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sr1d_verdict", os.path.join(ROOT, "tools", "sr1d", "sr1d_verdict.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

DIRS = ("plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
        "plus_x_minus_y")
UNIT = {"plus_x": (1, 0), "plus_x_plus_y": (1, 1), "plus_y": (0, 1), "minus_x_plus_y": (-1, 1), "minus_x": (-1, 0),
        "minus_x_minus_y": (-1, -1), "minus_y": (0, -1), "plus_x_minus_y": (1, -1), "none_xy": (0, 0)}
MAGS = ("tiny", "small", "medium", "large", "xlarge")


def _v(name, n=0.01):
    u = np.asarray(UNIT[name], float)
    return (u / np.linalg.norm(u) * n) if np.linalg.norm(u) else u


def snap(i, stratum="far", follow=True, mse=0.02, contact=False, grip_follow=True):
    c = {}
    for d in DIRS + ("none_xy",):
        v = _v(d) if follow else _v("plus_x")
        c[f"xy:{d}"] = [v[0], v[1], 0.0, 1.0, 1.0, mse, -0.001]
    for z, s in (("up", 1), ("down", -1), ("none_z", 0)):
        c[f"z:{z}"] = [0.01, 0, s * 0.01 if follow else 0.01, 1.0, 1.0, mse, -0.001]
    for j, m in enumerate(MAGS):
        c[f"mag:{m}"] = [0.002 * (j + 1) if follow else 0.01, 0, 0, 1.0, 1.0, mse, -0.001]
    g1 = 0.0 if grip_follow else 1.0
    c["true"] = [0.01, 0, 0, 1.0, g1, mse, -0.001]
    c["pred"] = c["true"]
    c["flip"] = [-0.01, 0, 0, 1.0, 1.0, mse, -0.001]
    c["edit:30"] = [0.01, 0, 0, 1.0, 1.0, mse, 0.0]
    return {"event": "snap", "i": i, "id": f"RB1_ep{i}_k0", "key": f"RB1_ep{i}_k0", "arm": "right",
            "labels": {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"},
            "preds": {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"}, "disp_gt": [0.01, 0, 0],
            "c": c, "stratum": stratum, "a": 1.0, "d": 0.2, "contact": contact, "holding": False, "alt": {},
            "floor_z": -0.45, "ee_z": -0.3, "true_end_err": 0.01, "grip_rec": [1.0, 0.0],
            "edits": {"edit:30": [0.01, 0.0, "plus_x", "small"]}}


def write(tmp, name, recs, lat=30.0):
    p = os.path.join(tmp, name)
    with open(p, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
        f.write(json.dumps({"event": "summary", "n": len(recs), "latency_ms": {"p95": lat}}) + "\n")
    return p


def run(tmp, c1_follow=True, c1_near_mse=0.02, c1_lat=30.0):
    def recs(follow, near_mse):
        return [snap(i, "far", follow) for i in range(6)] + [snap(6 + i, "near", False, near_mse, True)
                                                              for i in range(4)]
    c0 = [write(tmp, f"c0_{s}.jsonl", recs(False, 0.02)) for s in (1, 2)]
    c1 = [write(tmp, f"c1_{s}.jsonl", recs(c1_follow, c1_near_mse), c1_lat) for s in (1, 2)]
    out = os.path.join(tmp, "v.json")
    V.main(["--c0", *c0, "--c1", *c1, "--n", "10", "--boot", "50", "--out", out])
    return json.load(open(out))


def test_follow_is_adopted_full(tmp_path):
    r = run(str(tmp_path))
    assert r["rule"]["verdict"] == "ADOPT" and r["rule"]["grade"] == "FULL"
    assert r["avg"]["c0"]["primary"]["a_xy"] < 0.5


def test_ignore_is_not_reached(tmp_path):
    assert run(str(tmp_path), c1_follow=False)["rule"]["verdict"] == "NOT_REACHED"


def test_near_mse_worse_is_near_bleed(tmp_path):
    r = run(str(tmp_path), c1_near_mse=0.03)
    assert r["rule"]["verdict"] == "NEAR_BLEED" and r["rule"]["fails"] == ["N1"]


def test_latency_worse_is_not_adopted(tmp_path):
    r = run(str(tmp_path), c1_lat=45.0)
    assert r["rule"]["verdict"] == "NOT_ADOPTED" and r["rule"]["fails"] == ["iv"]


def test_all_mode_uses_every_snapshot_and_contact_as_near(tmp_path):
    t = str(tmp_path)
    c0 = [write(t, f"a0_{s}.jsonl", [snap(i, "far", False) for i in range(6)]
                + [snap(6 + i, "unknown", False, contact=True) for i in range(4)]) for s in (1, 2)]
    c1 = [write(t, f"a1_{s}.jsonl", [snap(i, "far", True) for i in range(6)]
                + [snap(6 + i, "unknown", True, contact=True) for i in range(4)]) for s in (1, 2)]
    out = os.path.join(t, "v.json")
    V.main(["--c0", *c0, "--c1", *c1, "--mode", "all", "--n", "10", "--boot", "20", "--out", out])
    r = json.load(open(out))
    assert r["avg"]["c1"]["primary"]["n_snap"] == 10 and r["avg"]["c1"]["near"]["n_snap"] == 4
