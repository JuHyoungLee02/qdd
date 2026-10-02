"""L9 common executor (L9_COMMON_EXEC=1): the R1 / G1 executor fixes for every robot, robot data only."""
import json
import os

import numpy as np

from harvest.l9 import robot9 as R9
from harvest.l9 import rt9
from tools.l9 import track_lag

PROFILES = ("ffw_sg2", "franka_mast", "r1pro", "g1")


def test_default_off():
    assert os.environ.get("L9_COMMON_EXEC") != "1"
    assert rt9.COMMON is False


def test_switches_off_are_the_robot_tables():
    for tab in (rt9.REVERSE_APPROACH, rt9.GRASP_LINKS_CHECK, rt9.PLACE_CHECK, rt9.LIFT_SKIP):
        for p in PROFILES:
            assert rt9.on(tab, p, common=False) == bool(tab.get(p))
            assert rt9.on(tab, p, common=True) is True


def test_carry_range():
    for p in PROFILES:
        assert rt9.carry_range(p, common=False) == R9.V2_CARRY_CLEAR.get(p)
        assert rt9.carry_range(p, common=True) == R9.CARRY_CLEAR_RANGE


def test_carry_range_from_env_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(R9, "ENV_PROFILE_DIR", str(tmp_path))
    (tmp_path / "g1.json").write_text(json.dumps({"carry_clear_m": [0.03, 0.06]}))
    (tmp_path / "r1pro.json").write_text(json.dumps({"carry_clear_m": [0.2, 0.1]}))  # invalid -> common range
    assert R9.carry_clear_range("g1") == (0.03, 0.06)
    assert R9.carry_clear_range("r1pro") == R9.CARRY_CLEAR_RANGE
    assert R9.carry_clear_range("ffw_sg2") == R9.CARRY_CLEAR_RANGE


def test_cmd_dq_from_measured_overshoot(monkeypatch):
    for p in PROFILES:
        assert rt9.cmd_dq(p, common=False) == rt9.CMD_DQ_BY.get(p, rt9.CMD_DQ)
    monkeypatch.setattr(R9, "TRACK_OVERSHOOT", {"r1pro": 1.47, "ffw_sg2": 1.1, "g1": 0.9})
    assert rt9.cmd_dq("r1pro", common=True) == 0.027  # 0.04 / 1.47 = 0.0272
    assert rt9.cmd_dq("ffw_sg2", common=True) == rt9.CMD_DQ  # 0.04 / 1.1 > the default: never above it
    assert rt9.cmd_dq("g1", common=True) == rt9.CMD_DQ
    assert rt9.cmd_dq("franka_mast", common=True) == rt9.CMD_DQ  # not measured
    for p, r in R9.TRACK_OVERSHOOT.items():  # the cap keeps the measured step under the gate
        assert R9.cmd_dq_cap(p, rt9.CMD_DQ) * max(r, 1.0) <= R9.STEP_GATE + 1e-9


def test_measured_overshoot_data_is_sane():
    for p, r in R9.TRACK_OVERSHOOT.items():
        assert p in PROFILES and 0.5 < float(r) < 3.0


def test_locks_from_sim():
    cfg = {"robot_cfg": {"kinematics": {"lock_joints": {"l1": 0.0, "l2": 0.5, "f": 0.05}}}}
    out, ch = rt9.locks_from_sim(cfg, ["l1", "l2", "x"], np.array([0.2, 0.5, 9.0]))
    assert out["robot_cfg"]["kinematics"]["lock_joints"] == {"l1": 0.2, "l2": 0.5, "f": 0.05}
    assert ch == {"l1": (0.0, 0.2)}
    assert cfg["robot_cfg"]["kinematics"]["lock_joints"]["l1"] == 0.0  # input untouched


class _Pl:
    def __init__(self, qr):
        self.qr = qr

    def ready_ik(self, T):
        return None if self.qr is None else (self.qr, 0.3)

    def cspace(self, q0, qg):
        return np.linspace(q0, qg, 5)


def _rt(qr, q0):
    rt = object.__new__(rt9.Runtime)
    rt.profile, rt.style, rt.timeline = "franka_mast", None, {}
    rt.planner = _Pl(qr)
    rt.q_lo, rt.q_hi = -np.ones(7) * 3, np.ones(7) * 3
    rt.refresh_world = lambda *a, **k: None
    rt.to_base = lambda T: T
    rt.arm_q = lambda: np.asarray(q0, float)
    return rt


def test_ready_path():
    q0, qr = np.zeros(7), np.full(7, 0.5)
    Q, m = _rt(qr, q0).ready_path([0.4, 0, 1.0], [1, 0, 0, 0])
    assert m == 0.3 and np.allclose(Q[-1], qr) and np.allclose(Q[0], q0, atol=0.04)
    assert np.abs(np.diff(Q, axis=0)).max() <= rt9.CMD_DQ + 1e-9
    Q, m = _rt(None, q0).ready_path([0.4, 0, 1.0], [1, 0, 0, 0])
    assert Q is None and m is None
    Q, _ = _rt(q0.copy(), q0).ready_path([0.4, 0, 1.0], [1, 0, 0, 0])  # already there: hold
    assert Q.shape == (1, 7)


def test_track_lag(tmp_path):
    for i, (robot, dq, ok) in enumerate([("r1pro", 0.050, True), ("r1pro", 0.030, True), ("r1pro", 0.09, False),
                                         ("ffw_sg2", 0.030, True)]):
        d = tmp_path / f"e{i}"
        d.mkdir()
        (d / "meta.json").write_text(json.dumps({"robot": robot, "max_dq_rad": dq, "success": ok,
                                                 "motion_version": "l9v2-1"}))
    s = track_lag.scan([str(tmp_path)])
    assert sorted(s) == ["ffw_sg2", "r1pro"] and len(s["r1pro"]) == 2
    r = track_lag.summarize(s["r1pro"], 0.034, q=1.0)
    assert r["overshoot"] == round(0.050 / 0.034, 3) and r["suggested_cap"] == 0.027 and r["over_gate"] == 1
    assert track_lag.summarize(s["ffw_sg2"], 0.034)["suggested_cap"] == 0.034


def test_isaac_env_allowlist():
    sh = open(os.path.join(os.path.dirname(__file__), "..", "..", "tools", "l9", "isaac.sh"), encoding="utf-8").read()
    assert "L9_COMMON_EXEC=$L9_COMMON_EXEC" in sh
