"""Head-view table grid (robot-frame coordinates drawn ON the table plane from camera calibration only) and the TCP
drop line (TCP -> the table point straight below it)."""
import numpy as np

from harvest.astra_motion import geometry as G
from harvest.astra_solo import overlay as O

from astra_motion.fakeworld import HEAD, TZ


def test_grid_is_drawn_on_the_table_plane():
    img = np.full((HEAD.H, HEAD.W, 3), 60, np.uint8)
    out, drawn = O.head_overlay(img, HEAD, TZ, tcp=np.array([0.40, -0.25, TZ + 0.20]))
    assert out.shape == img.shape and out.dtype == np.uint8
    u, v, _ = G.project(HEAD, [0.40, -0.20, TZ])  # a grid crossing
    assert out[int(v), int(u)].astype(int).sum() > img[int(v), int(u)].astype(int).sum()
    assert set(drawn) == {"grid", "tcp", "drop"}


def test_grid_lines_cover_the_workspace():
    xs, ys = O.grid_values()
    assert min(xs) <= 0.30 and max(xs) >= 0.60 and min(ys) <= -0.45 and max(ys) >= 0.05
    assert all(abs(round(x * 100) - x * 100) < 1e-9 for x in xs)  # whole centimetres


def test_labels_are_explicit_metres():
    assert O.label("x", 0.40) == "x=0.40" and O.label("y", -0.20) == "y=-0.20" and O.label("y", 0.10) == "y=+0.10"


def test_no_tcp_elements_when_tcp_is_missing():
    img = np.zeros((HEAD.H, HEAD.W, 3), np.uint8)
    _, drawn = O.head_overlay(img, HEAD, TZ, tcp=None)
    assert drawn == ["grid"]
