import json
from collections import Counter
from types import SimpleNamespace

import numpy as np
import pytest

from harvest.predicates import Gripper, Obj, PredicateState
from harvest.sim import snapshot as S


# ---- seeds
@pytest.mark.parametrize("seed", [1000, 1149, 1300, 1329, 500, 30, 1999, 2120])
def test_test_and_other_seeds_refused(seed):
    with pytest.raises(ValueError):
        S.check_seed(seed)


def test_pool_kinds_balanced_seeded_and_dev_only():
    kinds = [S.pool_kind(s) for s in S.POOL_SEEDS]
    assert Counter(kinds) == {"P0": 40, "P1": 40, "P2": 40}
    assert kinds == [S.pool_kind(s) for s in S.POOL_SEEDS]  # deterministic
    assert set(kinds) <= {"P0", "P1", "P2"}
    assert kinds[:6] != ["P0", "P1", "P2", "P0", "P1", "P2"]  # not a trivial cycle


def test_pool_split_episode_level_balanced():
    sp = {s: S.pool_split(s) for s in S.POOL_SEEDS}
    assert Counter(sp.values()) == {"fit": 60, "eval": 60}
    for k in S.POOL_KINDS:
        assert Counter(v for s, v in sp.items() if S.pool_kind(s) == k) == {"fit": 20, "eval": 20}
    assert S.pool_split(3) == "dev"


# ---- grid
def test_snapshot_grid_is_exact_033():
    t = [S.snap_sub(k) * S.PHYS_DT for k in range(40)]
    st = S.interval_stats(t)
    assert abs(st["mean"] - 0.33) < 1e-9 and abs(st["min"] - 0.33) < 1e-9 and abs(st["max"] - 0.33) < 1e-9


def test_chunks_hit_target_exactly():
    sub, k, hits = 0, 1, []
    while k < 30:
        for n in S.chunks_to(sub, S.snap_sub(k)):
            sub += n
            if sub == S.snap_sub(k):
                hits.append(sub)
                k += 1
        assert sub % S.DECIM == 0  # every env step still ends on the 50 ms grid
    assert hits == [S.snap_sub(i) for i in range(1, 30)]


def test_chunks_no_split_on_boundary():
    assert S.chunks_to(160, 165) == [5]
    assert S.chunks_to(160, 163) == [3, 2]
    assert S.chunks_to(160, 200) == [5]


# ---- ambiguity / sampling
def test_ambiguous_only_inside_near_band():
    p = {"o3": [0, 0, 0], "o5": [0.055, 0, 0], "o8": [0.3, 0, 0]}
    assert S.ambiguous_predicates(p) == ["near(o3,o5)", "near(o5,o3)"]
    assert S.ambiguous_predicates({"o3": [0, 0, 0], "o5": [0.049, 0, 0]}) == []
    assert S.ambiguous_predicates({"o3": [0, 0, 0], "o5": [0.061, 0, 0]}) == []


def test_select_decision_30pct_and_weights():
    rng = np.random.default_rng(1)
    amb = [i % 4 == 0 for i in range(36)]  # 9 boundary of 36
    sel = S.select_decision(amb, rng=rng)
    assert len(sel) == 10 and len({i for i, _, _ in sel}) == 10
    assert sum(o for _, o, _ in sel) == 3
    assert all(amb[i] == o for i, o, _ in sel)
    assert abs(sum(w for _, _, w in sel) - 10) < 1e-9
    # natural boundary share recovered by the weights: 9/36
    wb = sum(w for _, o, w in sel if o)
    assert abs(wb / 10 - 9 / 36) < 1e-9


def test_select_decision_tops_up_when_boundary_short():
    sel = S.select_decision([False] * 35 + [True], rng=np.random.default_rng(0))
    assert sum(o for _, o, _ in sel) == 1 and len(sel) == 10
    sel = S.select_decision([True] * 32 + [False] * 4, rng=np.random.default_rng(0))
    assert sum(o for _, o, _ in sel) == 6 and len(sel) == 10


# ---- oracle labels
def test_oracle_target_phase_fine_progress():
    assert S.oracle_target("descend") == "o3" and S.oracle_target("carry") == "o5"
    assert S.oracle_phase_choice("lift", "carry") == "next"
    assert S.oracle_phase_choice("lift", "lift") == "continue"
    assert S.fine_axis([0.001, 0.0, -0.02]) == "minus_z"
    assert S.fine_axis([0.001, 0.0, 0.001]) == "hold"
    assert S.oracle_progress(5.0, 4.0, []) == "failure"
    assert S.oracle_progress(5.0, None, [{"t": 4.5}]) == "allowed_change"
    assert S.oracle_progress(6.0, None, [{"t": 4.5}]) == "valid_progress"
    assert S.next_phase_name("open") == "retreat" and S.next_phase_name("done") is None


def test_text_state_minimal_format():
    pred = {"holding(o3)": True, "upright(o3)": True, "upright(o5)": True, "on(o3,o5)": False,
            "lifted(o3)": True, "near(o3,o5)": True, "gripper_open": False}
    s = S.text_state(6.6, "carry", 0.4, 6.0, pred, ["o3", "o5"], {"o3": None, "o5": "table"}, False, True, True,
                     [(6.4, "near(o3,o5)", False, True), (1.0, "lifted(o3)", False, True)])
    lines = s.split("\n")
    assert lines[0] == 't_state: f132 (t=6.60s)  contract: c1  stage: S2 "place mug o3 on tray o5"'
    assert lines[1] == "robot: gripper=closed_holding(o3) arm=moving"
    assert "  o3 mug red | held_by_gripper | upright" in lines
    assert "  o5 tray blue | on(table) | upright" in lines
    assert "on(o3,o5)=no" in s  # named in the stage exit although false
    assert s.endswith("changes (last 3s): -0.2s near(o3,o5): no->yes")


# ---- planner / observation round trip
def _fake_planner():
    ps = PredicateState()
    objs = {"o3": Obj("o3", np.array([0.4, -0.2, 0.05]), np.array([1.0, 0, 0, 0]), np.array([0.03, 0.03, 0.05]))}
    grip = Gripper(0.05, 3.0, np.array([0.4, -0.2, 0.06]))
    ps.update(objs, grip, {frozenset({"gripper", "o3"})}, {"o3": "table"})
    return SimpleNamespace(phase="lift", t_phase0=4.2, cmd_w=0.052, _not_hold=1, fail_stage=None, retreat_z=None,
                           near_target=True, cmd_pos=np.array([0.4, -0.2, 0.9]), cmd_quat=np.array([0.7, 0, 0, 0.7]),
                           grasp_rel=[0.0, -0.009, -0.046], fail_info={}, ps=ps, pred={"holding(o3)": True},
                           objs=objs, grip=grip, contacts={frozenset({"gripper", "o3"})}, phase_log=[(0.0, "approach")],
                           history=[1, 2])


def test_planner_state_round_trip_is_json():
    a = _fake_planner()
    d = json.loads(json.dumps(S.planner_state(a)))
    b = _fake_planner()
    b.phase, b.cmd_pos, b._not_hold, b.ps._near = "approach", np.zeros(3), 0, {}
    S.apply_planner_state(b, d)
    assert b.phase == "lift" and b._not_hold == 1 and np.allclose(b.cmd_pos, a.cmd_pos)
    assert b.ps._near == a.ps._near and b.contacts == a.contacts
    assert np.allclose(b.objs["o3"].pos, a.objs["o3"].pos) and b.grip.width_m == a.grip.width_m
    assert b.history == []


def _fake_state(i):
    rng = np.random.default_rng(i)
    return {"t": 0.33 * i, "steps": 6.6 * i, "episode_length_buf": 7 * i, "present": ["o3", "o5"], "seed": 2000,
            "carry_start_xy": None, "perturb": {"kind": "P1", "seed": 2000, "fired": False, "t_carry": None,
                                                "event": None},
            **{k: rng.normal(size=30).astype(np.float32) for k in S.ROBOT_ARRAYS},
            "obj_pose": {o: rng.normal(size=7).astype(np.float32) for o in ("o3", "o5", "o8")},
            "obj_vel": {o: rng.normal(size=6).astype(np.float32) for o in ("o3", "o5", "o8")},
            "action": rng.normal(size=8).astype(np.float32),
            "rng_np": np.random.RandomState(i).get_state(), "rng_torch": rng.integers(0, 255, 5056).astype(np.uint8),
            "planner": {"phase": "lift"}, "obs": {"pred": {"a": True}}}


def test_pack_unpack_round_trip(tmp_path):
    st = [_fake_state(i) for i in range(4)]
    arrays, js = S.pack_states(st, ["o3", "o5", "o8"])
    np.savez_compressed(tmp_path / "x.npz", **arrays)
    back = np.load(tmp_path / "x.npz")
    js = json.loads(json.dumps(js))
    for i, s in enumerate(st):
        u = S.unpack_state(back, i, js[i])
        for k in S.ROBOT_ARRAYS + ("action", "rng_torch"):
            assert np.array_equal(u[k], s[k])
        for o in ("o3", "o5", "o8"):
            assert np.array_equal(u["obj_pose"][o], s["obj_pose"][o])
        r = np.random.RandomState()
        r.set_state(u["rng_np"])
        assert r.randint(1 << 30) == np.random.RandomState(i).randint(1 << 30)
        assert u["t"] == s["t"] and u["planner"] == s["planner"] and u["perturb"] == s["perturb"]
