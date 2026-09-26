"""MolmoAct R2 data (plan 2026-09-26-molmoact-r2-data Task 2): waypoint geometry for path-diversified episodes (M3)."""
import math

import numpy as np
import pytest

from harvest.sim import tasks as T
from harvest.sim import waypoint as W

TZ = 0.85


def test_offsets_range_sign_and_determinism():
    signs = set()
    for seed in range(10001, 10200):
        for task in T.TASK_IDS:
            o = W.sample_offsets(seed, task)
            assert set(o) == {"approach", "carry"}
            for v in o.values():
                assert W.WP_OFFSET_M[0] <= abs(v) <= W.WP_OFFSET_M[1]
                signs.add(v > 0)
            assert o == W.sample_offsets(seed, task)
    assert signs == {True, False}
    assert W.sample_offsets(10001, "mug_tray") != W.sample_offsets(10002, "mug_tray")
    assert W.sample_offsets(10001, "mug_tray") != W.sample_offsets(10001, "bottle_tray")


def test_waypoint_is_perpendicular_midpoint_offset():
    s = np.array([0.34, -0.25, TZ + 0.25])
    g = np.array([0.44, -0.12, TZ + 0.195])
    wp = W.waypoint(s, g, 0.06, TZ)
    mid = (s + g) / 2
    d = (g - s)[:2] / np.linalg.norm((g - s)[:2])
    off = wp[:2] - mid[:2]
    assert abs(float(np.dot(off, d))) < 1e-12
    assert math.isclose(float(np.linalg.norm(off)), 0.06, abs_tol=1e-12)
    assert math.isclose(wp[2], mid[2], abs_tol=1e-12)
    # sign: +offset = left of the travel direction (counter-clockwise normal)
    assert float(d[0] * off[1] - d[1] * off[0]) > 0


def test_waypoint_safe_box_flips_then_clips():
    s = np.array([0.34, -0.25, TZ + 0.25])
    g = np.array([0.34, -0.05, TZ + 0.20])  # travel +y: +offset points to -x (x 0.34 - 0.09 = 0.25 < 0.30) -> flipped
    wp = W.waypoint(s, g, 0.09, TZ)
    assert math.isclose(wp[0], 0.34 + 0.09, abs_tol=1e-12)
    for s2, g2, off in ((np.array([0.50, -0.30, TZ + 0.2]), np.array([0.50, -0.10, TZ + 0.2]), 0.09),
                        (np.array([0.40, 0.00, TZ + 0.2]), np.array([0.49, 0.01, TZ + 0.2]), 0.09)):
        wp = W.waypoint(s2, g2, off, TZ)
        assert W.SAFE_X[0] <= wp[0] <= W.SAFE_X[1] and W.SAFE_Y[0] <= wp[1] <= W.SAFE_Y[1]
    low = W.waypoint(np.array([0.34, -0.25, TZ + 0.10]), np.array([0.44, -0.10, TZ + 0.10]), 0.05, TZ)
    assert low[2] >= TZ + W.MIN_Z_TABLE - 1e-12


def test_waypoint_none_for_short_moves():
    s = np.array([0.40, -0.20, TZ + 0.2])
    assert W.waypoint(s, s + [0.005, 0.0, 0.0], 0.06, TZ) is None


def test_wp_goal_never_reached_at_waypoint():
    wp = np.array([0.40, -0.20, TZ + 0.22])
    real = np.array([0.45, -0.10, TZ + 0.195])
    g, passed = W.wp_goal(wp, wp + [0.0, W.WP_PASS_R + 1e-4, 0.0], real)
    assert passed is False and np.array_equal(g, wp)
    g, passed = W.wp_goal(wp, wp + [0.0, W.WP_PASS_R - 1e-4, 0.0], real)
    assert passed is True and np.array_equal(g, real)
    g, passed = W.wp_goal(None, wp, real)
    assert passed is True and np.array_equal(g, real)


class _Base:
    """Planner stand-in: phase, cmd_pos, env.table_top_z and a _goal() like OraclePlanner's."""

    def __init__(self):
        self.env = type("E", (), {"table_top_z": TZ, "sim_time": 0.0})()
        self.phase = "approach"
        self.cmd_pos = np.array([0.34, -0.25, TZ + 0.25])
        self.goals = {"approach": np.array([0.44, -0.12, TZ + 0.195]), "descend": np.array([0.44, -0.12, TZ + 0.06]),
                      "carry": np.array([0.40, -0.35, TZ + 0.20])}

    def _goal(self):
        return self.goals[self.phase].copy(), 0.2


def test_mixin_routes_through_waypoint_then_goal_and_logs():
    P = W.waypoint_mixin(_Base)
    p = P()
    p.setup_waypoints({"approach": 0.06, "carry": -0.07})
    g0, _ = p._goal()
    wp = p.wp_state["approach"]["wp"]
    assert np.allclose(g0, wp) and not np.allclose(g0, p.goals["approach"])
    p.cmd_pos = wp + [0.0, 0.0, 0.01]  # inside the pass radius
    g1, _ = p._goal()
    assert np.allclose(g1, p.goals["approach"]) and p.wp_state["approach"]["passed"]
    p.phase = "descend"
    g2, _ = p._goal()
    assert np.allclose(g2, p.goals["descend"]) and "descend" not in p.wp_state
    p.phase, p.cmd_pos = "carry", np.array([0.44, -0.12, TZ + 0.20])
    g3, _ = p._goal()
    assert np.allclose(g3, p.wp_state["carry"]["wp"])
    log = p.waypoint_log()
    assert set(log) == {"approach", "carry"} and log["approach"]["passed"] and not log["carry"]["passed"]
    assert log["carry"]["offset_m"] == -0.07


def test_mixin_is_a_subclass_and_base_is_untouched():
    P = W.waypoint_mixin(_Base)
    assert issubclass(P, _Base) and not hasattr(_Base, "setup_waypoints")
    with pytest.raises(AttributeError):
        _Base().wp_state
