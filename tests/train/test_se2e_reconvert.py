"""tools/se2e_convert.py reconvert (canon §83): rows re-derived with the causal velocity keep every other field of
the old conversion (images, labels, actions) and gain the motion-line source (se2e_temporal.hist_fields)."""
import copy
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import se2e_convert as C  # noqa: E402

from harvest.train import se2e_data as S  # noqa: E402

from .test_se2e_data import _chain, _episode  # noqa: E402


def _old_and_new():
    st, act = _episode()
    ch = {"right": _chain(), "left": _chain()}
    new = S.episode_rows(st, act, 10, ch, 7, "RB1", "sort", stride=5)
    old = json.loads(json.dumps(new))
    for r in old:  # the old conversion: central-difference velocity, filtered image refs, rotation flag
        r["proprio"]["qd"] = [v + 1.0 for v in r["proprio"]["qd"]]
        r["proprio"]["grip"][1] += 1.0
        r["images"] = {"cam_head": f"img/RB1/ep000007/k{r['k']:04d}_cam_head.jpg"}
        r["img_rotate_cw"] = ["cam_wrist_left", "cam_wrist_right"]
    return st, old, new


def test_merge_takes_the_new_velocity_and_keeps_the_rest():
    st, old, new = _old_and_new()
    out = C.merge_reconverted(old, new)
    assert [r["k"] for r in out] == [r["k"] for r in old]
    for o, n, r in zip(old, new, out):
        assert r["proprio"]["qd"] == n["proprio"]["qd"] and r["proprio"]["grip"][1] == n["proprio"]["grip"][1]
        assert r["proprio"]["grip"][0] == o["proprio"]["grip"][0]
        assert r["images"] == o["images"] and r["img_rotate_cw"] == o["img_rotate_cw"]
        rest = {k: v for k, v in r.items() if k != "proprio"}
        assert rest == {k: v for k, v in o.items() if k != "proprio"}


def test_merge_refuses_any_other_changed_field():
    _, old, new = _old_and_new()
    bad = copy.deepcopy(new)
    bad[2]["ee_delta"][0] += 1e-3
    with pytest.raises(ValueError, match="ee_delta"):
        C.merge_reconverted(old, bad)
    bad = copy.deepcopy(new)
    bad[1]["proprio"]["grip"][0] += 0.1  # the gripper VALUE is not a velocity field
    with pytest.raises(ValueError, match="proprio"):
        C.merge_reconverted(old, bad)
    with pytest.raises(ValueError, match="frames"):
        C.merge_reconverted(old, new[:-1])


def test_hist_rows_carry_the_same_causal_velocity_as_proprio():
    st, old, new = _old_and_new()
    out = C.merge_reconverted(old, new, state=st, fps=10, names=S.FEATURE_NAMES_16, kind="RB1")
    for r in out:
        assert r["motion_src"]["qd_bwd"] == r["proprio"]["qd"]
        assert r["motion_src"]["grip_rate_bwd"] == r["proprio"]["grip"][1]
        assert r["k_prev"] == max(0, r["k"] - 3)
        assert set(r["images_prev"]) == set(r["images"])
        assert r["images_prev"]["cam_head"] == f"img_prev/RB1/ep000007/k{r['k_prev']:04d}_cam_head.jpg"
    np.testing.assert_allclose(out[0]["proprio"]["qd"], 0.0)  # episode start
