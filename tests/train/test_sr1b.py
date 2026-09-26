"""E-SR1b (prereg_sr1b): hindsight relabel bins, relabel of the expert's committed decisions, dropout row draw and
the prompt marker (pure parts of harvest/train/sr1b.py; no torch)."""
import importlib.util
import math
import os

import numpy as np

from harvest.train import sr1b as S

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location("sr0_eval", os.path.join(ROOT, "tools", "sr0", "sr0_eval.py"))
E0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E0)


def _xy(deg, r=0.01):
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def test_sector_xy_is_the_nearest_of_eight_directions():
    assert S.DIR_XY8 == E0.DIR_XY8
    for k, d in enumerate(S.DIR_XY8):
        for off in (-22.0, 0.0, 22.0):
            assert S.sector_xy(*_xy(45 * k + off)) == d
        u = E0.unit_xy(d)
        dx, dy = _xy(45 * k + 22.0)
        assert (dx * u[0] + dy * u[1]) / math.hypot(dx, dy) > 0.9  # the bin is a hit under the sr0 metric


def test_sector_xy_none_below_the_minimum():
    assert S.sector_xy(S.XY_MIN_M - 1e-6, 0.0) == "none_xy"
    assert S.sector_xy(0.0, 0.0) == "none_xy"
    assert S.sector_xy(S.XY_MIN_M, 0.0) == "plus_x"
    assert S.sector_xy(-S.XY_MIN_M * 0.8, -S.XY_MIN_M * 0.8) == "minus_x_minus_y"


def test_z_bin():
    assert S.z_bin(S.Z_MIN_M) == "up" and S.z_bin(-S.Z_MIN_M) == "down"
    assert S.z_bin(S.Z_MIN_M - 1e-6) == "none_z" and S.z_bin(-S.Z_MIN_M + 1e-6) == "none_z"


def _sample(first, last, arm="right", committed=None, mid=(0.5, 0.5, 0.5)):
    ex = np.zeros((15, 8))
    ex[0, :3], ex[-1, :3] = first, last
    ex[1:-1, :3] = mid
    c = committed if committed is not None else {"dir_xy": "plus_y", "dir_z": "up", "mag_coarse": "large",
                                                "target": "o3", "phase": "reach"}
    return {"key": "P0_ep1_k3", "arm": arm, "action_exec": ex.tolist(), "committed": c,
            "items": [{"question": "dir_xy", "target": ["plus_y"]}]}


FK = {"right": lambda q: np.asarray(q, float)[..., :3], "left": lambda q: -np.asarray(q, float)[..., :3]}


def test_relabel_changes_only_the_committed_directions():
    s = _sample([0, 0, 0], [0.01, -0.01, -0.003])
    old = {**s["committed"]}
    (n,), st = S.relabel([s], FK)
    assert n["committed"] == {**old, "dir_xy": "plus_x_minus_y", "dir_z": "down"}
    assert s["committed"] == old  # input not modified
    assert n["items"] is s["items"] and n["action_exec"] is s["action_exec"]  # decision targets unchanged
    assert st["n"] == 1 and st["changed_xy"] == 1 and st["changed_z"] == 1 and st["missing"] == 0
    assert st["xy"]["plus_x_minus_y"] == 1 and st["z"]["down"] == 1


def test_relabel_uses_first_and_last_chunk_rows_per_arm():
    a = _sample([0.1, 0.1, 0.1], [0.1, 0.1, 0.1])  # middle rows far away: ignored -> none
    b = _sample([0, 0, 0], [0.01, 0, 0], arm="left")  # left FK is mirrored in this fake -> minus_x
    (na, nb), st = S.relabel([a, b], FK)
    assert na["committed"]["dir_xy"] == "none_xy" and na["committed"]["dir_z"] == "none_z"
    assert nb["committed"]["dir_xy"] == "minus_x"
    assert st["n"] == 2


def test_relabel_leaves_samples_without_committed_directions():
    s = _sample([0, 0, 0], [0.01, 0, 0], committed={"target": "o3"})
    (n,), st = S.relabel([s], FK)
    assert n is s and st["missing"] == 1 and st["changed_xy"] == 0


def test_drop_rows_rate_and_determinism():
    r1, r2 = np.random.default_rng(S.drop_seed(0)), np.random.default_rng(S.drop_seed(0))
    x = np.concatenate([S.drop_rows(8, 0.3, r1) for _ in range(5000)])
    y = np.concatenate([S.drop_rows(8, 0.3, r2) for _ in range(5000)])
    assert np.array_equal(x, y) and abs(x.mean() - 0.3) < 0.01
    assert not S.drop_rows(8, 0.0, np.random.default_rng(1)).any()
    assert S.drop_seed(0) != S.drop_seed(1)


def test_joystick_slots_follow_the_question_order():
    from harvest.train import stageb_data as D
    assert S.QUESTIONS == D.QUESTIONS
    assert [D.QUESTIONS[i] for i in S.JOY_SLOTS] == list(S.JOY) == ["dir_xy", "dir_z", "mag_coarse"]


def test_mark_prompt_config():
    cfg = {"camera": ["x"], "ma2": "ma2@v1", "sha": "old"}
    a = S.mark_prompt_config(cfg, 0.3, False)
    b = S.mark_prompt_config(cfg, 0.3, True)
    c = S.mark_prompt_config(cfg, 0.2, False)
    assert a["sr1b"] == S.SR1B_VER and a["sr1b_drop"] == 0.3 and a["sr1b_relabel"] is False
    assert a["camera"] == ["x"] and a["ma2"] == "ma2@v1" and "harvest/train/sr1b.py" in a["sr1b_files_sha"]
    assert len({a["sha"], b["sha"], c["sha"], "old"}) == 4 and cfg["sha"] == "old"


def test_parse_ws_and_out_path():
    assert S.parse_ws("1,1.5,2,3,5,8") == (1.0, 1.5, 2.0, 3.0, 5.0, 8.0)
    assert S.w_tag(1.0) == "1" and S.w_tag(1.5) == "1.5" and S.w_tag(8.0) == "8"
    for bad in ("1.5,2", "1,1", "1,-2", "", "1,x"):
        try:
            S.parse_ws(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def _aux(g2t, t2p, contact=0):
    return {"reg": {"g2tgt_dx": g2t[0], "g2tgt_dy": g2t[1], "g2tgt_dz": g2t[2],
                    "g2tgt_dist": float(np.linalg.norm(g2t)), "tgt2place_dx": t2p[0], "tgt2place_dy": t2p[1],
                    "tgt2place_dz": t2p[2]}, "cls": {"contact_tgt_place": contact}}


def test_near_contact_snapshot_definition():
    from harvest.config import CFG
    from harvest.datagen.rows import PICK_PHASES
    assert S.NEAR_M == CFG.near_in_m and S.PICK_PHASES == PICK_PHASES
    far_obj = _aux([0.2, 0, 0], [0.0, 0.0, 0.0])
    assert S.near_snap(_aux([0.03, 0.03, 0.0], [0.3, 0, 0]), "descend") == (True, pytest_approx(0.0424264))
    assert S.near_snap(far_obj, "approach")[0] is False
    # place stage: gripper -> place = g2tgt - tgt2place (o3 - g) - (o3 - o5) = o5 - g
    assert S.near_snap(_aux([0.0, 0.0, -0.02], [0.0, 0.0, 0.01]), "place_descend") == (True, pytest_approx(0.03))
    assert S.near_snap(_aux([0.0, 0.0, -0.02], [0.2, 0.0, 0.1]), "carry")[0] is False
    assert S.near_snap(_aux([0.0, 0.0, -0.02], [0.2, 0.0, 0.1], contact=1), "open")[0] is True
    assert S.near_snap({"reg": {"g2tgt_dist": None}, "cls": {}}, "approach") == (None, None)
    assert S.near_snap({"reg": {"g2tgt_dx": 0.0, "g2tgt_dy": 0.0, "g2tgt_dz": 0.0}, "cls": {}}, "carry") == (None, None)


def pytest_approx(v):
    import pytest
    return pytest.approx(v, abs=1e-6)


def test_slot_indices():
    assert S.slot_indices("dir_xy,dir_z,mag_coarse") == (0, 1, 2)
    assert S.slot_indices("dir_xy") == (0,)
    for bad in ("", "dir_q", "dir_xy,dir_xy"):
        try:
            S.slot_indices(bad)
        except ValueError:
            continue
        raise AssertionError(bad)
