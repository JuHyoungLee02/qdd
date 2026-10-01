import numpy as np

from harvest.l9 import grasp9 as G
from harvest.l9 import rt9 as R


def test_classify_close_and_lift():
    assert R.classify_close(0.001, 0.04) == "EMPTY"
    assert R.classify_close(0.036, 0.04) == "CONTACT"
    assert R.classify_close(0.06, 0.04) == "WIDE"
    assert R.classify_lift(0.036, 0.0365, 0.002) == "SUCCESS"
    assert R.classify_lift(0.036, 0.030, 0.002) == "SLIP"
    assert R.classify_lift(0.036, 0.036, 0.02) == "SLIP"


def test_free_opening_clips_to_neighbour():
    gr = G.gripper("ffw_sg2")
    T = np.eye(4)
    T[:3, 3] = [0.5, 0.0, 0.85]  # top-down grasp, fingers close along world y
    w, pre = 0.04, 0.08
    none = (np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3, 3)))
    assert R.free_opening(T, gr, none, w, pre) == pre
    # a low neighbour (top at the TCP height) 3.5 cm from the axis: the 8 cm finger slab hits it
    nb = (np.array([[0.5, 0.035 + 0.05, 0.80]]), np.array([[0.05, 0.05, 0.05]]), np.eye(3)[None])
    got = R.free_opening(T, gr, nb, w, pre)
    assert got is not None and got < pre and got / 2 + gr["finger_t"] <= 0.035 + 1e-6
    # a neighbour hugging the object: nothing fits
    nb2 = (np.array([[0.5, 0.021 + 0.05, 0.80]]), np.array([[0.05, 0.05, 0.05]]), np.eye(3)[None])
    assert R.free_opening(T, gr, nb2, w, pre) is None
