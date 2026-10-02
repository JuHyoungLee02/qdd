"""L9v2-R1: the measured R1 Pro top-down band (assets9/reach_v2/r1pro_band_l080.json) lookup (pure)."""
import numpy as np

from harvest.l9 import r1_band as RB


def test_band_column_and_mirror():
    # reach_lean / ready_grid 10-03: at lean 0.8 the column 0.60 m ahead reaches 0.2 m below torso_link4; points close
    # to the torso and far above it do not
    P = np.array([[0.60, -0.15, -0.20], [0.15, -0.15, 0.05], [0.85, -0.15, -0.55]])
    r = RB.ok_points("right", P)
    assert r[0] and not r[1] and not r[2]
    Pl = P.copy()
    Pl[:, 1] *= -1
    assert (RB.ok_points("left", Pl) == r).all()


def test_outside_grid_is_false():
    assert not RB.ok_points("right", [[2.0, 0.0, 0.0]])[0]
