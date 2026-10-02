import types

import numpy as np

from harvest.l9 import rt9


def test_with_flips_turns_about_approach_and_keeps_originals():
    T = np.tile(np.eye(4), (2, 1, 1))
    T[1, :3, 3] = [0.1, 0.0, 0.0]
    C = {"T": T, "c1": np.array([[0, -0.01, 0], [0.1, -0.02, 0]]), "c2": np.array([[0, 0.01, 0], [0.1, 0.02, 0]]),
         "w": np.array([0.02, 0.04]), "a": np.array([[0, 0, -1.0], [0, 0, -1.0]]), "score": np.array([0.5, 0.4]),
         "pre_open": np.array([0.04, 0.06]), "test_ok": np.array([True, False]),
         "source": np.array(["analytic", "analytic"]), "tested": True}
    me = types.SimpleNamespace(_cand={})
    out = rt9.Runtime._with_flips(me, "obj", C)
    assert len(out["w"]) == 4 and np.allclose(out["T"][:2], T)
    R = out["T"][2, :3, :3]
    assert np.allclose(R[:, 2], T[0, :3, 2]) and np.allclose(R[:, 1], -T[0, :3, 1]) and np.isclose(np.linalg.det(R), 1)
    assert np.allclose(out["c1"][2], C["c2"][0]) and list(out["test_ok"]) == [True, False, True, False]
    assert out["source"][3] == "analytic_flip" and out["tested"] is True
    assert rt9.Runtime._with_flips(me, "obj", C) is out  # cached
