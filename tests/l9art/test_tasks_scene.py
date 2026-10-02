import numpy as np
import pytest

from harvest.l9art import fixtures as FX
from harvest.l9art import scene_art as SA
from harvest.l9art import skills as SK
from harvest.l9art import tasks as TK

OBJS = {"o1": {"name": "red box", "fp": (0.06, 0.05), "h": 0.06}, "o2": {"name": "toy", "fp": (0.05, 0.05), "h": 0.08}}


def test_defs_count_and_skills():
    assert 16 <= len(TK.DEFS) <= 20
    for d in TK.DEFS.values():
        for kind, _, _ in d["stages"]:
            assert TK.STAGE_SKILL[kind] in TK.SKILLS
        assert "g1" not in d["robots"]


@pytest.mark.parametrize("did", sorted(TK.DEFS))
def test_instantiate_and_build(did):
    d = TK.DEFS[did]
    ok = 0
    for s in range(30):
        spec = FX.sample(d["family"], s) if d["family"] != "none" else None
        try:
            prog = TK.instantiate(did, spec, s, "red box")
        except ValueError:
            continue
        for st in prog["stages"]:
            if st["kind"] in ("pull", "push", "rotate"):
                assert st["goal"] is not None
        for arm in ("right", "left"):
            try:
                b = SA.build(s, "ffw_sg2", arm, spec, prog, OBJS)
            except ValueError:
                continue
            assert b["ep"]["objects"] and -0.5 <= b["sc"]["lift"] <= 0.0
            if spec is not None:
                (x0, x1), (y0, y1) = SA.fixture_aabb(spec, b["fixture"]["T"])
                assert x0 > 0.2
        ok += 1
    assert ok >= 5, did


def test_handle_grasp_frames():
    gr = {"max_open": 0.107, "pad_len": 0.045, "finger_w": 0.022}
    rng = np.random.default_rng(0)
    for fam in ("drawer", "door", "slide", "knob"):
        sp = FX.sample(fam, 4)
        ln = next(iter(sp["handles"]))
        hf = FX.handle_frame(sp, ln, SA.T_WF(0.55, -0.2, 0.75, 0.1))
        g = SK.handle_grasp(hf, gr, SK.grasp_draw(rng))
        R = g["T"][:3, :3]
        assert np.allclose(R.T @ R, np.eye(3), atol=1e-9)
        assert np.dot(-R[:, 2], -np.asarray(hf["fn"])) > 0.8  # approaching into the part
        assert np.linalg.norm(g["T_pre"][:3, 3] - g["T"][:3, 3]) > 0.07
        if "bar" in hf:
            assert abs(np.dot(R[:, 1], hf["bar"])) < 0.25  # pads close across the bar
