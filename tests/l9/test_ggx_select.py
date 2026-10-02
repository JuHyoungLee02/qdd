import numpy as np

from harvest.l9 import ggx_cache as GC
from harvest.l9 import grasp9 as G


def _box(hx=0.03, hy=0.02, hz=0.05):
    V = np.array([[sx * hx, sy * hy, sz * hz + hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float)
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6],
                  [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, F


def test_seat_recentres_on_contacts():
    V, F = _box()
    R = G.frame_of(np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    C = GC.candidates(V, F, "franka", [(R, np.array([-0.15, 0.01, 0.05]))], [0.7])
    assert len(C["w"]) == 1 and abs(C["w"][0] - 0.04) < 1e-6
    assert abs(C["T"][0, 1, 3]) < 1e-6 and C["score"][0] == 0.7


def test_select_ggx_prior_is_soft_and_ok_is_hard():
    fam = np.array(["top", "side", "side"])
    part = np.array(["body", "body", "body"])
    order = (("top", "body"), ("side", "body"))
    ok = np.array([True, True, False])
    rd, mg = np.zeros(3), np.zeros(3)
    # high GGX score beats the natural first choice (soft prior)
    i, step, rk, _ = G.select_ggx(fam, part, rd, mg, ok, order, np.array([0.1, 0.9, 1.0]), np.full(3, np.nan))
    assert i == 1 and step == 1 and rk == 1
    # equal GGX: the natural prior decides; an invalid candidate is never chosen
    i, step, _, _ = G.select_ggx(fam, part, rd, mg, ok, order, np.array([0.5, 0.5, 5.0]), np.full(3, np.nan))
    assert i == 0 and step == 0
    i, step, _, _ = G.select_ggx(fam, part, rd, mg, ok, order, np.zeros(3), np.full(3, np.nan), instructed="side")
    assert i == 1 and step == 2
