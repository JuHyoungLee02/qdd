"""tools/ma1/g0.py judge (prereg_ma1 §2) on synthetic frames / reference points."""
import importlib.util
import pathlib

import numpy as np

from harvest.train import se2e_trace as TR

spec = importlib.util.spec_from_file_location("g0", pathlib.Path(__file__).parents[1] / "tools/ma1/g0.py")
g0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g0)

_ts = importlib.util.spec_from_file_location("ts", pathlib.Path(__file__).parent / "train" / "test_se2e_trace.py")
_tsm = importlib.util.module_from_spec(_ts)
_ts.loader.exec_module(_tsm)
HEAD = _tsm.HEAD_URDF
CAM_T = _tsm.CAM0


def _frames(n_per=30):
    rng = np.random.default_rng(0)
    out = []
    for kind in ("RB1", "RB2"):
        for arm in ("left", "right"):
            for i in range(n_per):
                ee = CAM_T + [rng.uniform(0.3, 0.7), rng.uniform(-0.3, 0.3), rng.uniform(-0.6, -0.3)]
                out.append({"key": f"{kind}_ep{i}_{arm}", "kind": kind, "arm": arm, "ee": ee.tolist(),
                            "q_head": [0.5492, 0.0], "cal": i < n_per // 2})
    return out


def _points(frames, corr=None, noise=0.0, drop=()):
    chain = TR.load_head_chain(HEAD)
    rng = np.random.default_rng(1)
    out = []
    for f in frames:
        uv, _ = TR.project(TR.head_camera(chain, f["q_head"]), np.array([f["ee"]]), corr=corr)
        p = (uv[0] + rng.normal(0, noise, 2)).tolist()
        out.append({"key": f["key"], "point": None if f["key"] in drop else p})
    return out


def test_nominal_pass():
    fr = _frames()
    v = g0.judge(fr, _points(fr, noise=3.0), HEAD)
    assert v["result"] == "pass_nominal" and v["pass"] and v["camera"]["corr"] is None
    assert v["nominal"]["all"]["n"] == 120 and v["nominal"]["all"]["median"] < 12
    assert set(v["nominal"]) >= {"all", "RB1", "RB2"}


def test_pnp_rescues_an_extrinsic_offset():
    fr = _frames()
    corr = {"RB1": np.array([0.0, 0.08, 0.0, 0.02, 0.0, 0.0]), "RB2": np.array([0.05, 0.0, 0.0, 0.0, 0.03, 0.0])}
    pts = []
    for kind in ("RB1", "RB2"):
        sub = [f for f in fr if f["kind"] == kind]
        pts += _points(sub, corr=corr[kind], noise=2.0)
    v = g0.judge(fr, pts, HEAD)
    assert not TR.g0_pass(v["nominal"]["all"])
    assert v["result"] == "pass_pnp" and v["pass"]
    assert v["pnp"]["test"]["all"]["n"] == 60 and v["pnp"]["cal_n"] == {"RB1": 30, "RB2": 30}
    assert set(v["camera"]["corr"]) == {"RB1", "RB2"}


def test_failures_excluded_and_counted():
    fr = _frames()
    drop = {f["key"] for f in fr[:10]}
    v = g0.judge(fr, _points(fr, noise=1.0, drop=drop), HEAD)
    assert v["reference_failures"] == 10 and v["human_fallback"] == 0 and v["nominal"]["all"]["n"] == 110


def test_insufficient_references():
    fr = _frames()
    drop = {f["key"] for f in fr[:31]}
    v = g0.judge(fr, _points(fr, drop=drop), HEAD)
    assert v["result"] == "insufficient_references" and not v["pass"] and v["next"] == "R2"


def test_hopeless_fails_to_r2():
    fr = _frames()
    rng = np.random.default_rng(3)
    pts = [{"key": f["key"], "point": [float(rng.uniform(0, 672)), float(rng.uniform(0, 376))]} for f in fr]
    v = g0.judge(fr, pts, HEAD)
    assert v["result"] == "fail" and not v["pass"] and v["next"] == "R2"
