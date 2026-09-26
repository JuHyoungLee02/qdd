"""tools/rb3/rb3_lib.py: release frame (require_grasp), head-image yellow rule, overlap fingerprints."""
import importlib.util
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
_spec = importlib.util.spec_from_file_location("rb3_lib", os.path.join(ROOT, "tools", "rb3", "rb3_lib.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

NAMES16 = [f"arm_l_joint{i}" for i in range(1, 8)] + ["gripper_l_joint1"] + \
          [f"arm_r_joint{i}" for i in range(1, 8)] + ["gripper_r_joint1"]
NAMES19 = NAMES16 + ["head_joint1", "head_joint2", "lift_joint"]


def test_releases_need_a_grasp_inside_the_episode():
    g = [1.0, 1.0, 0.1, 0.1, 0.9, 0.9, 0.9, 0.2, 0.2]  # closed at start -> opening to grasp, then grasp + release
    assert L.releases(g) == [7]
    assert L.releases([0.0] * 5) == []
    assert L.releases([0, 1, 0, 1, 0]) == [2, 4]


def test_first_release_earliest_arm():
    st = np.zeros((12, 16))
    st[2:6, 7] = 1.0  # left: grasp 2, release 6
    st[1:4, 15] = 1.0  # right: grasp 1, release 4
    assert L.first_release(st, NAMES16) == (4, "right")
    assert L.first_release(np.zeros((5, 16)), NAMES16) == (None, None)


def test_yellow_low_counts_only_the_lower_40_percent():
    im = np.zeros((10, 10, 3), np.uint8)
    im[:6] = (230, 200, 20)  # yellow in the upper 60 % only
    assert L.yellow_low(im) == 0.0
    im[8:] = (230, 200, 20)  # 2 of the 4 lower rows
    assert L.yellow_low(im) == 0.5
    im[8:] = (230, 200, 160)  # not yellow (blue too high)
    assert L.yellow_low(im) == 0.0
    assert L.release_flag(10, 0.02) and not L.release_flag(10, 0.019) and not L.release_flag(None, 0.5)


def test_head_down_and_no_grasp():
    assert L.head_down(0.02) and not L.head_down(0.01) and not L.head_down(None)
    st = np.zeros((10, 16))
    st[:, 7] = 0.45
    assert L.exclude_reason(st, NAMES16) == "no_grasp"
    st[4, 15] = 0.51
    assert L.exclude_reason(st, NAMES16) is None


def test_fingerprints():
    rng = np.random.default_rng(0)
    x19 = rng.normal(size=(30, 19)).astype(np.float32)
    a = L.arm16(x19, NAMES19)
    assert a.shape == (30, 16)
    np.testing.assert_array_equal(a[:, 15], x19[:, 15])
    assert L.exact_hash(a) == L.exact_hash(a.copy()) and L.exact_hash(a) != L.exact_hash(a + 1e-6)
    g = np.round(a.astype(np.float64), 3)  # on the 1e-3 grid: float noise below the rounding step is ignored
    assert L.round_hash(g) == L.round_hash(g + 1e-5) and L.round_hash(g) != L.round_hash(g + 2e-3)
    fa = np.stack([L.traj_fp(a), L.traj_fp(a * 2)])
    fb = np.stack([L.traj_fp(a * 2 + 1e-4), L.traj_fp(a)])
    idx, dist = L.nearest(fa, fb)
    assert idx == [1, 0] and dist[0] == 0.0 and dist[1] < 2e-4
