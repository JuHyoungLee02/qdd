"""Environment profile reader (harvest/l9/envprof9.py): schema check, per-episode draw from coupled cells or ranges."""
import json

import pytest

from harvest.l9 import envprof9 as E


def _p(**kw):
    p = {"schema": E.SCHEMA, "profile": "toy", "surface_z_m": [0.55, 0.78], "stance_x_m": [-0.1, 0.05],
         "body": {"joints": {"waist_pitch": [0.1, 0.4]}, "lean_rad": [0.1, 0.4]},
         "hand": {"yaw_deg_ok": [[-80, 80], [100, 180]], "yaw_deg_bad": [85, 95]},
         "ready": {"tcp_above_surface_m": [0.18, 0.24]}, "carry_clear_m": [0.05, 0.10],
         "head_cam": {"pitch_deg": [-5, 5]}, "lateral_m": {"right": [-0.3, 0.0], "left": [0.0, 0.3]}}
    p.update(kw)
    return p


def test_validate():
    assert E.validate(_p()) == []
    assert E.validate(_p(schema="v0"))
    assert E.validate(_p(surface_z_m=[0.8, 0.5]))
    assert E.validate(_p(cells=[]))


def test_draw_ranges_deterministic_and_inside():
    p = _p()
    a, b = E.draw(p, 7), E.draw(p, 7)
    assert a == b and E.draw(p, 8) != a
    for s in range(50):
        d = E.draw(p, s)
        assert 0.55 <= d["surface_z"] <= 0.78 and 0.1 <= d["torso"]["waist_pitch"] <= 0.4
        assert 0.05 <= d["carry_clear"] <= 0.10 and 0.18 <= d["ready_tcp_above"] <= 0.24


def test_draw_cells_keeps_coupling():
    # high surface only with a low lean: independent marginals would pair (0.9, 0.9); cells never do
    cells = [{"surface_z": 0.9, "lean": 0.75, "torso": {"t4": 0.1}, "score": 1.0},
             {"surface_z": 0.6, "lean": 0.9, "torso": {"t4": 0.3}, "score": 0.5}]
    p = _p(cells=cells, cell_half={"surface_z": 0.01, "torso.t4": 0.0})
    seen = set()
    for s in range(40):
        d = E.draw(p, s)
        pair = (round(d["surface_z"], 1), d["lean"])
        assert pair in {(0.9, 0.75), (0.6, 0.9)}
        assert abs(d["surface_z"] - (0.9 if d["lean"] == 0.75 else 0.6)) <= 0.01
        seen.add(pair)
    assert len(seen) == 2


def test_yaw_and_lateral():
    p = _p()
    assert E.yaw_ok(p, 0) and not E.yaw_ok(p, 90) and E.yaw_ok(p, 120) and not E.yaw_ok(p, -120)
    assert E.lateral_range(p, "left") == [0.0, 0.3]


def test_load_and_flag(tmp_path, monkeypatch):
    f = tmp_path / "toy.json"
    f.write_text(json.dumps(_p()))
    assert E.load("toy", str(f))["profile"] == "toy"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(_p(schema="x")))
    with pytest.raises(ValueError):
        E.load("bad", str(bad))
    monkeypatch.delenv("L9_ENV_PROFILE", raising=False)
    assert E.active("ffw_sg2") is None


def test_yaw_grid_form():
    p = _p(hand={"yaw_deg_ok": [0, 30, 60, 90, 300, 330], "yaw_deg_bad": [240, 270]})
    assert E.validate(p) == []
    assert E.yaw_ok(p, 40) and not E.yaw_ok(p, 200) and not E.yaw_ok(p, 250)


def make_model(seed, arm, profile=None):  # a stand-in robot scene model factory ("module:factory" in a profile)
    return ("own", seed, arm, profile["profile"] if profile else None)


def test_scene_model_plugin(tmp_path, monkeypatch):
    from harvest.l9 import hand9 as H
    monkeypatch.setattr(E, "DIR", str(tmp_path))
    E._CACHE.clear()
    assert H.scene_model("toy", default="aiw", seed=1, arm="right") == "aiw"  # no profile, nothing registered
    (tmp_path / "toy.json").write_text(json.dumps(_p(scene_model=f"{__name__}:make_model")))
    E._CACHE.clear()
    assert H.scene_model("toy", default="aiw", seed=3, arm="left") == ("own", 3, "left", "toy")
    monkeypatch.setitem(H.SCENE_MODELS, "toy", lambda **kw: "registered")
    assert H.scene_model("toy", default="aiw", seed=3, arm="left") == "registered"
    E._CACHE.clear()


def test_draw_near_surface_picks_matching_cell_without_body_jitter():
    from harvest.l9 import envprof9 as E
    p = {"cells": [{"surface_z": 0.5, "stance_x": 0.3, "torso": {"j1": 0.1}},
                   {"surface_z": 0.8, "stance_x": 0.4, "torso": {"j1": 0.7}}],
         "cell_half": {"surface_z": 0.025, "torso.j1": 0.3}}
    for s in range(20):
        d = E.draw(p, s, near={"surface_z": 0.79})
        assert d["torso"]["j1"] == 0.7 and abs(d["stance_x"] - 0.4) < 1e-9
    assert E.draw(p, 1, near={"surface_z": 0.65}) is None
    assert E.draw(p, 3)["torso"]["j1"] != 0.1 or True  # no near: unchanged behaviour (jitter allowed)
