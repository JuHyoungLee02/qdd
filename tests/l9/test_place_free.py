"""H2: free_place_xy moves the place point off an object an earlier step put there (pure)."""
import numpy as np

from harvest.l9 import v2plan as VP
from harvest.sim import scene as SC


def test_free_place_moves_off_earlier_object(monkeypatch):
    geom = {"bin": {"half_extents": (0.15, 0.10, 0.05)}, "a": {"half_extents": (0.03, 0.03, 0.04)},
            "b": {"half_extents": (0.03, 0.03, 0.04)}}
    monkeypatch.setattr(SC, "OBJ_GEOM", geom, raising=False)
    st = {"obj": {"bin": [0.5, 0.0, 0.70], "a": [0.5, 0.0, 0.74], "b": [0.3, 0.3, 0.74]}}
    p = np.array([0.5, 0.0, 0.70])
    q = VP.free_place_xy(st, "bin", "b", p)
    r = np.hypot(0.03, 0.03)
    assert np.hypot(q[0] - 0.5, q[1] - 0.0) >= 2 * r + VP.FREE_GAP - 1e-9  # clear of "a"
    assert abs(q[0] - 0.5) <= 0.15 - r + 1e-9 and abs(q[1]) <= 0.10 - r + 1e-9  # inside the bin footprint
    assert q[2] == p[2]


def test_free_place_keeps_point_when_free(monkeypatch):
    geom = {"bin": {"half_extents": (0.15, 0.10, 0.05)}, "b": {"half_extents": (0.03, 0.03, 0.04)}}
    monkeypatch.setattr(SC, "OBJ_GEOM", geom, raising=False)
    st = {"obj": {"bin": [0.5, 0.0, 0.70], "b": [0.3, 0.3, 0.74]}}
    p = np.array([0.5, 0.0, 0.70])
    assert (VP.free_place_xy(st, "bin", "b", p) == p).all()
