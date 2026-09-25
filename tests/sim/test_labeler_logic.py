import numpy as np
import pytest

from harvest.jevcall import DIR_XY, DIR_Z, MAG
from harvest.sim import labeler as L
from harvest.sim.planner import MAG_BINS
from harvest.sim.snapshot import PHASE_ORDER

ORA = {"dir_xy": "plus_x", "dir_z": "down", "mag_coarse": "medium", "target": "o3", "fine_mag": 0.01}


def test_best_set_ties_tolerance():
    assert L.best_set({"a": 1.0, "b": 1.0, "c": 0.4}) == {"a", "b"}
    assert L.best_set({"a": 1.0, "b": 1.0 - 2e-6}) == {"a"}


def test_option_keys_match_jevcall_keys():
    ne = "NONE_ESCALATE"
    assert set(L.option_keys("dir_xy")) == {o.key for o in DIR_XY} - {ne}
    assert set(L.option_keys("dir_z")) == {o.key for o in DIR_Z} - {ne}
    assert set(L.option_keys("mag_coarse")) == {o.key for o in MAG} - {ne}
    assert L.MAG_M == dict(MAG_BINS)
    assert L.option_keys("target", ["o5", "o10", "o3"]) == ["o3", "o5", "o10"]


def test_displacement_code_table():
    assert np.allclose(L.displacement("plus_x", "none_z", "large"), [0.04, 0, 0])
    d = L.displacement("plus_x_minus_y", "up", "xlarge")
    assert np.isclose(np.linalg.norm(d), 0.08) and d[0] > 0 > d[1] and d[2] > 0
    assert not L.displacement("none_xy", "none_z", "xlarge").any()


def test_exec_spec_shares_oracle_rollout_across_questions():
    a = L.exec_spec("dir_xy", "plus_x", ORA)
    assert a == L.exec_spec("dir_z", "down", ORA) == L.exec_spec("mag_coarse", "medium", ORA)
    assert L.exec_spec("target", "o3", ORA) == L.exec_spec("phase", "continue", ORA) == ("plan",)
    assert L.exec_spec("target", "o5", ORA) == ("target", "o5")
    assert L.exec_spec("phase", "hold", ORA) == L.exec_spec("fine_dir", "hold", ORA) == ("hold",)
    assert L.exec_spec("fine_dir", "done", ORA) == L.exec_spec("phase", "next", ORA) == ("next",)
    assert L.exec_spec("fine_dir", "minus_z", ORA) == ("disp", 0.0, 0.0, -0.01)
    hold = dict(ORA, dir_xy="none_xy", dir_z="none_z")
    assert {L.exec_spec("mag_coarse", m, hold) for m in L.MAG_M} == {("hold",)}
    with pytest.raises(ValueError):
        L.exec_spec("dir_xy", "NONE_ESCALATE", ORA)


def test_score_outcome_order():
    ok = L.score_outcome({"success": True, "fail": False}, PHASE_ORDER)
    fail = L.score_outcome({"success": False, "fail": True, "phase": "fail", "dist_m": 0}, PHASE_ORDER)
    far = L.score_outcome({"success": False, "fail": False, "phase": "carry", "dist_m": 0.2}, PHASE_ORDER)
    near = L.score_outcome({"success": False, "fail": False, "phase": "carry", "dist_m": 0.05}, PHASE_ORDER)
    later = L.score_outcome({"success": False, "fail": False, "phase": "place_descend", "dist_m": 0.29},
                            PHASE_ORDER)
    done = L.score_outcome({"success": False, "fail": False, "phase": "done", "dist_m": 0.0}, PHASE_ORDER)
    assert ok == 1.0 and fail == 0.0
    assert 0 < far < near < later < done < 1.0


class _O:
    def __init__(self, key):
        self.key = key


def test_label_uses_option_key_and_skips_none_escalate():
    class Fake(L.Labeler):
        def __init__(self):
            self.cache, self.n_rollouts, self.sim_s = {}, 0, 0.0

        def _rollout(self, state, spec):
            self.n_rollouts += 1
            good = spec in (("plan",), L.exec_spec("dir_xy", "plus_x", ORA))
            return {"success": good, "fail": False, "phase": "carry", "dist_m": 0.1}

    lab = Fake()
    snap = {"key": "ep0_k1", "state": None, "oracle": ORA}
    opts = [_O(k) for k in L.option_keys("dir_xy")] + [_O("NONE_ESCALATE")]
    r = lab.label(snap, "dir_xy", opts)
    assert r["best"] == {"plus_x"} and "NONE_ESCALATE" not in r["scores"]
    n = lab.n_rollouts
    r2 = lab.label(snap, "dir_z", [_O(k) for k in L.option_keys("dir_z")])
    assert r2["best"] == {"down"} and lab.n_rollouts == n + 2  # oracle rollout reused from the cache


# ---- prereg_labeler.md candidate rules
PH = PHASE_ORDER


def _o(success=False, fail=False, t=None, phase="carry", dist=0.1, cps=None):
    return {"success": success, "fail": fail, "t_success": t, "phase": phase, "dist_m": dist, "d_start": 0.3,
            "checkpoints": cps or {}}


def test_rule_plan_all_successes_tie():
    outs = {"a": _o(True, t=4.0), "b": _o(True, t=5.0), "c": _o(fail=True)}
    assert L.rule_best(outs, "plan", PH) == {"a", "b"}


def test_rule_time_tau():
    outs = {"a": _o(True, t=4.0), "b": _o(True, t=4.3), "c": _o(True, t=4.6), "d": _o(fail=True)}
    assert L.rule_best(outs, "time0.33", PH) == {"a", "b"}
    assert L.rule_best(outs, "time0.66", PH) == {"a", "b", "c"}
    none_ok = {"a": _o(phase="carry", dist=0.1), "b": _o(phase="carry", dist=0.2)}
    assert L.rule_best(none_ok, "time0.33", PH) == {"a"}  # no success: D-plan progress


def test_rule_short_progress_veto_and_early_success():
    cp = lambda ph, d: {"1": {"phase": ph, "dist_m": d, "d_start": 0.2}}
    outs = {"a": _o(True, t=8.0, cps=cp("carry", 0.05)), "b": _o(True, t=8.0, cps=cp("carry", 0.10)),
            "c": _o(fail=True, cps=cp("place_descend", 0.0)), "d": _o(True, t=8.0, cps=cp("lift", 0.0))}
    assert L.rule_best(outs, "short1", PH) == {"a"}  # c is further but fails later: veto
    outs["e"] = _o(True, t=0.9, cps={})
    assert L.rule_best(outs, "short1", PH) == {"e"}
    # close/open hold still: d_start ~0 must not blow up
    z = {"x": _o(cps={"2": {"phase": "close", "dist_m": 0.001, "d_start": 0.0}})}
    assert L.rule_best(z, "short2", PH) == {"x"}


def test_select_rule_prereg():
    st = {"plan": (0.99, 0.05), "time0.33": (0.93, 0.40), "time0.66": (0.95, 0.39), "short3": (0.91, 0.41),
          "short2": (0.85, 0.60), "short1": (0.70, 0.70)}
    assert L.select_rule(st) == "time0.66"  # eligible max 0.41; within 0.02: time0.33/0.66/short3 -> D-time, larger tau
    st["short3"] = (0.91, 0.45)
    assert L.select_rule(st) == "short3"
    assert L.select_rule({"plan": (0.5, 0.1)}) is None
    assert L.select_rule({"plan": (0.95, 0.10), "short1": (0.95, 0.12)}) == "plan"


# ---- replay restore (docs/stage3/results/pool_replay_debug.md): the rerun depends on what the process ran before
# (hidden PhysX order state), so a replay is checked against the stored snapshot and, when it is not bit-exact,
# run again after another pre-replay history instead of branching from a wrong state.
def _rstate(off):
    raw = {"objs": {"o3": {"pos": [0.4, -0.2, 0.8], "quat": [1, 0, 0, 0], "he": [0.04, 0.04, 0.05]}},
           "grip": {"w": 0.1, "effort": 0.0, "pos": [0.4, -0.2, 0.9]}, "contacts": [], "support": {}}
    return {"joint_pos": np.zeros(3) + off, "joint_vel": np.zeros(3),
            "obj_pose": {"o3": np.array([0.4 + off, -0.2, 0.8, 1, 0, 0, 0])}, "obj_vel": {"o3": np.zeros(6)},
            "obs": {"pred": {}, "near_hyst": [], "raw": raw}}


class _RPL:
    class ps:  # noqa: N801 (planner predicate state stand-in)
        _near = {}


class _RLab(L.Labeler):
    def __init__(self):
        self.env, self.cache, self.n_rollouts, self.sim_s = object(), {}, 0, 0.0

    def _branch(self, pl, spec):
        return {"success": True, "fail": False}


def _fake_replays(monkeypatch, offsets):
    """Replays whose state at every snapshot is off by offsets[i] (m) on the i-th replay; None = the replay ends
    before snapshot k (a diverged run that finished early)."""
    import harvest.cli_pool as CP
    calls, it = [], iter(offsets)

    def prefix(env):
        calls.append("prefix")

    def run(env, seed, kind, cams=(), on_snapshot=None, **kw):
        calls.append(("run", seed, kind, on_snapshot is not None))
        if on_snapshot is None:
            return {}
        off = next(it)
        for k in range(4 if off is not None else 1):
            on_snapshot(env, _RPL(), {"k": k}, _rstate(off or 0.0), {})
        return {}

    monkeypatch.setattr(CP, "canonical_prefix", prefix)
    monkeypatch.setattr(CP, "run_snapshot_episode", run)
    return calls


_RSNAP = {"key": "ep2052_k2", "state": _rstate(0.0), "oracle": ORA, "replay": {"seed": 2052, "kind": "P0", "k": 2}}


def test_replay_exact_on_first_try_costs_one_prefix(monkeypatch):
    calls = _fake_replays(monkeypatch, [0.0])
    out = _RLab()._replay_rollout(_RSNAP, ("plan",))
    assert out["success"] and out["replay_maxabs"] == 0.0 and out["replay_attempts"] == 1
    assert calls == ["prefix", ("run", 2052, "P0", True)]


def test_replay_mismatch_is_retried_after_another_history(monkeypatch):
    from harvest.sim.snapshot import pool_kind
    calls = _fake_replays(monkeypatch, [0.02, None, 0.0])  # off by 2 cm, then ends before k, then exact
    out = _RLab()._replay_rollout(_RSNAP, ("plan",))
    assert out["success"] and out["replay_maxabs"] == 0.0 and out["replay_obj_mm"] == 0.0
    assert out["replay_attempts"] == 3
    # the 2nd try first re-runs the pool generator's own history: the previous POOL seed complete, then the prefix
    assert calls[2:6] == ["prefix", ("run", 2051, pool_kind(2051), False), "prefix", ("run", 2052, "P0", True)]


def test_replay_fourth_try_runs_the_seed_itself_complete_first(monkeypatch):
    calls = _fake_replays(monkeypatch, [0.02, 0.02, 0.02, 0.0])
    out = _RLab()._replay_rollout(_RSNAP, ("plan",))
    assert out["replay_attempts"] == 4 and out["replay_maxabs"] == 0.0
    # 4th try history: prefix, the same seed complete (no snapshot hook), prefix, then the replay itself
    assert calls[-4:] == ["prefix", ("run", 2052, "P0", False), "prefix", ("run", 2052, "P0", True)]


def test_replay_mismatch_on_every_try_is_reported_not_hidden(monkeypatch):
    n = len(L.REPLAY_HISTORIES)
    _fake_replays(monkeypatch, [0.02] * n)
    out = _RLab()._replay_rollout(_RSNAP, ("plan",))
    assert out["replay_attempts"] == n and out["success"]  # branched from the last try, mismatch kept in the row
    assert out["replay_obj_mm"] == pytest.approx(20.0)


def test_replay_never_reaching_k_still_raises(monkeypatch):
    _fake_replays(monkeypatch, [None] * len(L.REPLAY_HISTORIES))
    with pytest.raises(RuntimeError, match="never reached"):
        _RLab()._replay_rollout(_RSNAP, ("plan",))
