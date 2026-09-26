"""tools/xemb/track.py: the shared point-tracking front-end (one cache per episode, reused by T0 / T1 / T3):
seed choice from noisy detections, fusing several tracks of one part, gripper events, cache round trip."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import track as TK  # noqa: E402


def test_seeds_are_spread_and_agree_with_neighbours():
    T = 60
    u = np.c_[np.linspace(100, 300, T), np.full(T, 150.0)]
    u[5] = [600, 10]  # a wild detection is never a seed
    u[40:45] = np.nan
    s = TK.seeds(u, n=3)
    assert len(s) == 3 and 5 not in s
    assert max(s) - min(s) >= T // 3
    assert all(np.isfinite(u[k]).all() for k in s)


def test_fuse_takes_the_median_of_visible_tracks():
    tr = np.zeros((4, 3, 2))
    tr[:, 0] = [10, 10]
    tr[:, 1] = [12, 10]
    tr[:, 2] = [200, 200]  # one track drifted
    vis = np.ones((4, 3), bool)
    vis[:, 2] = False
    f, n = TK.fuse(tr, vis)
    assert np.allclose(f, [[11, 10]] * 4) and (n == 2).all()


def test_fuse_all_invisible_gives_nan():
    tr = np.zeros((2, 2, 2))
    vis = np.zeros((2, 2), bool)
    f, n = TK.fuse(tr, vis)
    assert np.isnan(f).all() and (n == 0).all()


def test_events_from_gripper_joint():
    g = np.array([0.1, 0.1, 0.8, 0.9, 0.9, 0.2, 0.1])
    ev = TK.events(g, closed_thr=0.5)
    assert ev == {"close": [2], "open": [5]}


def test_cache_roundtrip(tmp_path):
    p = tmp_path / "ep.npz"
    c = {"names": ["grip_left", "grip_right"], "tracks": np.random.rand(5, 2, 2), "vis": np.ones((5, 2), bool),
         "fused": {"grip_left": np.random.rand(5, 2)}, "events": {"left": {"close": [1], "open": [3]}}, "meta": {"a": 1}}
    TK.save(str(p), c)
    d = TK.load(str(p))
    assert d["names"] == c["names"] and np.allclose(d["tracks"], c["tracks"])
    assert d["events"]["left"]["close"] == [1] and d["meta"]["a"] == 1
    assert np.allclose(d["fused"]["grip_left"], c["fused"]["grip_left"])
