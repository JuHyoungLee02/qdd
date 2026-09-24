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
