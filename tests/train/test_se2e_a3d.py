"""E-MA1b A3d (docs/stage3/prereg_ma1b.md): future end-effector trajectory in the robot base frame (no camera) --
targets, aux vectors, attaching to samples. Pure numpy."""
import json

import numpy as np
import pytest

from harvest.train import se2e_a3d as A
from harvest.train import se2e_data as S
from harvest.train import stageb_data as D

from .test_se2e_data import _chain, _episode


def test_constants_registered():
    assert A.A3D_VER == "a3d@v1" and A.N_A3D == 12 and A.A3D_SCALE == D.AUX_REG_SCALE == 0.05


def test_target_even_points_relative_to_now():
    T = 50
    ee = np.stack([[0.01 * i, -0.02 * i, 0.005 * i] for i in range(T)])
    g = np.array([0.1] * 20 + [0.9] * 30)  # closes at frame 20
    t = A.a3d_target(ee, g, 4, fps=10)
    assert t["end"] == 20 and t["mask"] == [1, 1, 1, 1] and t["span_s"] == pytest.approx(1.6)
    want = np.stack([ee[k] - ee[4] for k in (8, 12, 16, 20)]).reshape(-1)
    np.testing.assert_allclose(t["d"], want, atol=1e-12)


def test_target_cap_and_episode_end():
    ee = np.cumsum(np.ones((80, 3)) * 0.01, 0)
    g = np.zeros(80)
    assert A.a3d_target(ee, g, 0, 10)["end"] == 30  # 3 s cap
    t = A.a3d_target(ee, g, 70, 10)
    assert t["end"] == 79 and t["mask"] == [1, 1, 1, 1]
    np.testing.assert_allclose(t["d"][-3:], ee[79] - ee[70], atol=1e-12)
    t = A.a3d_target(ee, g, 79, 10)  # last frame: no future -> masked
    assert t["mask"] == [0, 0, 0, 0] and t["d"] == [0.0] * 12


def test_aux_vecs_appends_scaled_masked_displacements():
    s = {"aux": {"reg": {}, "cls": {}}, "a3d": {"d": [0.05, -0.1, 0.0] * 4, "mask": [1, 0, 1, 1]}}
    r, rm, c, cm = A.a3d_aux_vecs(s)
    n = len(D.AUX_REG)
    assert r.shape == (n + 12,) and rm[:n].sum() == 0
    np.testing.assert_allclose(r[n:n + 3], [1.0, -2.0, 0.0])
    assert rm[n:].tolist() == [1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1] and r[n + 3:n + 6].tolist() == [0, 0, 0]
    r2, rm2, _, _ = A.a3d_aux_vecs({"aux": {"reg": {}, "cls": {}}})
    assert rm2.sum() == 0 and r2.shape == (n + 12,)


def test_episode_targets_match_row_labels():
    """The FK / frame indexing agree with the rows' own label displacement (ee_delta = FK(k+3) - FK(k))."""
    st, act = _episode()
    ch = {"right": _chain(), "left": _chain()}
    rows = S.episode_rows(st, act, 10, ch, 3, "RB1", "t", stride=5)
    out = A.episode_targets(rows, st, S.FEATURE_NAMES_16, ch, fps=10)
    assert [o["key"] for o in out] == [f"RB1_ep3_k{r['k']}" for r in rows]
    assert all(o["label_check_m"] < 1e-4 for o in out)
    json.dumps(out)


def test_attach_requires_every_sample(tmp_path):
    p = tmp_path / "RB1.a3d.jsonl"
    p.write_text(json.dumps({"key": "RB1_ep0_k0", "d": [0.0] * 12, "mask": [1] * 4}) + "\n")
    ss = [{"key": "RB1_ep0_k0"}]
    A.attach(ss, str(tmp_path), "RB1")
    assert ss[0]["a3d"]["mask"] == [1] * 4
    with pytest.raises(KeyError):
        A.attach([{"key": "RB1_ep0_k5"}], str(tmp_path), "RB1")
