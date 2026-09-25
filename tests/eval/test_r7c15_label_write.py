"""R7 cycle 15 N10 / N3.

N10: the label WRITER (`cli_label.label_snapshot`) must not turn a missing per-outcome replay distance into 0.0 (= a
bit-identical, trusted row, canon §78 (1)); a row whose outcomes do not all carry a number records None, which the
readers treat as untrusted (canon §80 [Claude decision] (1)).
N3: the two trust counters report which questions they count — `load_truth` (e05 / rd / calib) only the five stage-A
QUESTIONS, stage A `OutcomeLabels` every row of the label files (fine_dir included)."""
import json

import pytest

from harvest import cli_label as C
from harvest.eval import common
from harvest.train.stagea_data import replay_bit_identical

from .test_r7c14_label_trust import _line, _row

ORACLE = {"dir_xy": "plus_x", "dir_z": "down", "mag_coarse": "m2", "target": "o3", "phase_choice": "carry",
          "near_contact": False}


class FakeLab:
    """labeler stand-in: every option succeeds; replay fields per option from `rep` (a missing key = no field)."""

    def __init__(self, rep):
        self.rep = rep

    def label(self, snap, q, keys):
        outs = {}
        for i, k in enumerate(keys):
            o = {"success": True, "fail": False, "t_success": 1.0, "t_fail": None, "phase": "carry", "dist_m": 0.1,
                 "d_start": 0.3, "checkpoints": {}}
            o.update(self.rep(i))
            outs[k] = o
        return {"best": set(outs), "scores": {k: 1.0 for k in outs}, "outcomes": outs}


def _rows(rep):
    snap = {"key": "ep2000_k3", "state": {}, "oracle": ORACLE, "replay": {"seed": 2000, "kind": "P0", "k": 3}}
    return C.label_snapshot(FakeLab(rep), snap, ("o3", "o5"))


def _all(v):
    return lambda i: {"replay_maxabs": v, "replay_obj_mm": v, "replay_jpos_rad": v}


def test_all_outcomes_bit_identical_row_is_zero_and_trusted():
    rows = _rows(_all(0.0))
    assert rows and all(r["replay_maxabs"] == 0.0 and replay_bit_identical(r) for r in rows)
    assert all(r["replay_obj_mm"] == 0.0 and r["replay_jpos_rad"] == 0.0 for r in rows)


def test_row_keeps_the_largest_outcome_distance():
    rows = _rows(lambda i: {"replay_maxabs": 0.3 if i == 1 else 0.0, "replay_obj_mm": 2.0 if i == 1 else 0.0,
                            "replay_jpos_rad": 0.0})
    assert all(r["replay_maxabs"] == 0.3 and r["replay_obj_mm"] == 2.0 for r in rows)
    assert not any(replay_bit_identical(r) for r in rows)


@pytest.mark.parametrize("missing", ["absent", "null"])
def test_an_outcome_without_a_replay_distance_makes_the_row_untrusted(missing):
    def rep(i):
        if i == 0:
            return {} if missing == "absent" else {"replay_maxabs": None, "replay_obj_mm": None,
                                                    "replay_jpos_rad": None}
        return {"replay_maxabs": 0.0, "replay_obj_mm": 0.0, "replay_jpos_rad": 0.0}
    rows = _rows(rep)
    assert rows
    for r in rows:
        assert r["replay_maxabs"] is None and r["replay_obj_mm"] is None and r["replay_jpos_rad"] is None
        assert not replay_bit_identical(r)
        json.dumps(r)  # null in the jsonl


def test_rows_without_replay_distances_are_excluded_by_the_readers(tmp_path):
    rows = _rows(lambda i: {})
    for r in rows:
        r.update(seed=2000, kind="P0", k=3)
    (tmp_path / "ep2000.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    stats = {}
    assert common.load_truth([{"kind": "P0", "seed": 2000}], "outcome:plan", [str(tmp_path)], stats=stats) == {}
    assert stats["rows_kept"] == 0 and stats["rows_excluded_replay_not_bit_identical"] == len(common.QUESTIONS)


# ------------------------------------------------------------------------------------------ N3: counted questions
def _label_rows(seed, k):
    """One snapshot's rows: the five QUESTIONS bit-identical, fine_dir (near contact) not bit-identical."""
    return [_row(q, seed, k, 0.2 if q == "fine_dir" else 0.0) for q in list(common.QUESTIONS) + ["fine_dir"]]


def test_load_truth_reports_its_question_set_and_skips_fine_dir(tmp_path):
    (tmp_path / "ep2001.jsonl").write_text("".join(json.dumps(r) + "\n" for r in _label_rows(2001, 3)))
    stats = {}
    t = common.load_truth([{"kind": "P0", "seed": 2001}], "outcome:plan", [str(tmp_path)], stats=stats)
    assert set(t[("P0", 2001, 3)]) == set(common.QUESTIONS)
    # the untrusted fine_dir row is outside the question set: neither kept nor excluded
    assert stats == {"rule": "plan", "rows_kept": 5, "rows_excluded_replay_not_bit_identical": 0,
                     "questions": list(common.QUESTIONS)}


def test_stagea_reports_that_it_counts_every_label_row(tmp_path):
    from types import SimpleNamespace

    from harvest.train import stagea_train as T
    (tmp_path / "labels").mkdir()
    (tmp_path / "ep2001.jsonl").write_text(json.dumps(_line(2001, 3)) + "\n")
    (tmp_path / "labels" / "ep2001.jsonl").write_text("".join(json.dumps(r) + "\n" for r in _label_rows(2001, 3)))
    (tmp_path / "labels" / "ep2001.jsonl.done").write_text("{}")
    a = SimpleNamespace(dev_val_seeds="", pool=str(tmp_path), state="S0", partial=False, step_cm=0.1,
                        target_source="outcome", rule="plan", labels_v2="", cameras="H")
    stats = {}
    T._items(a, stats)
    assert stats["rows_kept"] == 5 and stats["rows_excluded_replay_not_bit_identical"] == 1  # fine_dir counted
    assert stats["questions"] == T.STAGEA_TRUST_QUESTIONS
