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
