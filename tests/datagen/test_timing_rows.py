"""R2 data generator, pure parts: the 30 Hz tick grid on 10 ms physics, chunks, rows (R4 contract), aux, verify."""
import math

import numpy as np
import pytest

from harvest.datagen import rows as R
from harvest.datagen import timing as TM
from harvest.train.stageb_data import AUX_CLS, AUX_REG, check_row


# ------------------------------------------------------------------------------------------ timing
def test_tick_grid_is_30hz_on_10ms_substeps():
    subs = [TM.tick_sub(k) for k in range(31)]
    assert subs[:7] == [0, 3, 7, 10, 13, 17, 20] and subs[30] == 100
    holds = [TM.hold_substeps(k) for k in range(300)]
    assert set(holds) == {3, 4} and sum(holds) == 1000  # 300 ticks = exactly 10 s
    err = [abs(TM.tick_time(k) - k / 30) for k in range(3000)]
    assert max(err) == pytest.approx(1 / 300, abs=1e-12)  # |t_k - k/30| <= 3.33 ms, 0 every 3rd tick
    assert all(TM.tick_time(3 * j) == pytest.approx(j / 10, abs=1e-12) for j in range(100))


def test_decision_frames_every_10_ticks():
    assert [k for k in range(35) if TM.is_decision(k)] == [0, 10, 20, 30]
    dts = [TM.tick_time(10 * (j + 1)) - TM.tick_time(10 * j) for j in range(30)]
    assert min(dts) == pytest.approx(0.33) and max(dts) == pytest.approx(0.34)
    assert np.mean(dts) == pytest.approx(1 / 3, abs=1e-3)


def test_chunk_pads_with_the_last_action_and_masks():
    acts = np.arange(5 * 8, dtype=np.float32).reshape(5, 8)
    a, v = TM.chunk(acts, 0, 3)
    assert np.array_equal(a, acts[:3]) and v == [1, 1, 1]
    a, v = TM.chunk(acts, 3, 4)
    assert np.array_equal(a[:2], acts[3:5]) and np.array_equal(a[2], acts[4]) and np.array_equal(a[3], acts[4])
    assert v == [1, 1, 0, 0]
    with pytest.raises(ValueError):
        TM.chunk(acts, 5, 4)  # no real first step


# ------------------------------------------------------------------------------------------ rows
def _state(tgt="o8", place="o5", grip=(0.40, -0.30, 0.20), tpos=(0.42, -0.30, 0.05), ppos=(0.46, -0.12, 0.0075),
           pred=None):
    pred = pred or {"gripper_open": True, f"holding({tgt})": False, f"lifted({tgt})": False,
                    f"upright({tgt})": True, f"near({tgt},{place})": False, f"in_contact({tgt},{place})": False,
                    f"on({tgt},{place})": False, f"above({tgt},{place})": False}
    objs = {tgt: {"pos": list(tpos), "he": [0.025, 0.025, 0.05]}, place: {"pos": list(ppos), "he": [0.09, 0.07, 0.0075]}}
    return {"present": [tgt, place], "obs": {"pred": pred, "raw": {"objs": objs, "grip": {"pos": list(grip), "w": 0.1}}}}


def test_aux_row_maps_aux_labels_to_the_r4_names():
    st = _state()
    aux = R.aux_row(st, "o8", "o5", goal_delta=[0.02, 0.0, -0.05])
    assert set(aux["reg"]) == set(AUX_REG) and set(aux["cls"]) == set(AUX_CLS)
    assert aux["reg"]["g2tgt_dx"] == pytest.approx(0.02) and aux["reg"]["g2tgt_dz"] == pytest.approx(-0.15)
    assert aux["reg"]["g2tgt_dist"] == pytest.approx(math.hypot(0.02, 0.15))
    assert aux["reg"]["g2goal_dz"] == pytest.approx(-0.05) and aux["reg"]["g2goal_dist"] == pytest.approx(math.hypot(0.02, 0.05))
    assert aux["reg"]["tgt2place_dy"] == pytest.approx(-0.18)
    assert aux["cls"] == {"gripper_open": 1, "holding_tgt": 0, "lifted_tgt": 0, "upright_tgt": 1,
                          "near_tgt_place": 0, "contact_tgt_place": 0, "on_tgt_place": 0}


def test_aux_row_masks_unknown_and_absent():
    st = _state(pred={"gripper_open": True, "holding(o8)": None})
    del st["obs"]["raw"]["objs"]["o5"]
    st["present"] = ["o8"]
    aux = R.aux_row(st, "o8", "o5", goal_delta=None)
    assert aux["reg"]["tgt2place_dx"] is None and aux["reg"]["g2goal_dist"] is None
    assert aux["cls"]["holding_tgt"] is None and aux["cls"]["on_tgt_place"] is None


def test_truth9_and_verify_expected_after():
    pred = {"on(o8,o5)": False, "in_contact(o8,o5)": False, "lifted(o8)": True, "near(o8,o5)": False,
            "above(o8,o5)": False, "gripper_open": False, "holding(o8)": True}
    tr = R.truth9(pred, "o8", "o5", contact_open=False)
    assert tr == {"on_tp": False, "contact_tp": False, "lifted_t": True, "near_tp": False, "above_tp": False,
                  "gripper_open": False, "holding_t": True, "lifted_holding": True, "contact_stall": False}
    v = R.verify_prev_step("carry", 10, tr)
    assert v["k0"] == 10 and v["phase"] == "carry" and v["violations"] == []
    assert ["holding_t", True] in v["expected_after"] and v["holds"]["lifted_t"] is True
    dropped = {**tr, "holding_t": False, "lifted_holding": False}
    v = R.verify_prev_step("carry", 10, dropped)
    assert set(v["violations"]) == {"holding_t", "lifted_holding"} and v["holds"]["holding_t"] is False
    v = R.verify_prev_step("place_descend", 0, {**tr, "above_tp": None, "contact_tp": False})
    assert v["holds"]["above_tp|contact_tp"] is None  # unknown never contradicts


def test_skill_of_phase():
    assert [R.skill_of(p) for p in ("approach", "descend", "close", "lift")] == ["pick"] * 4
    assert [R.skill_of(p) for p in ("carry", "place_descend", "open", "retreat", "done")] == ["place"] * 5


def test_stageb_row_passes_the_r4_contract_at_30hz():
    acts = np.zeros((40, 8), np.float32)
    acts[:, 7] = 0.1
    pro = {"q": [0.0] * 7, "qd": [0.0] * 7, "tau": [0.1] * 7, "grip": [0.107, 0.0]}
    st = _state()
    row = R.stageb_row(seed=3, kind="P0", k=30, task="bottle_tray", phase="approach", proprio=pro, actions=acts,
                       H=15, aux=R.aux_row(st, "o8", "o5", [0.0, 0.0, 0.0]))
    check_row(row, hz=30)
    assert row["hz"] == 30 and row["H"] == 15 and row["arm"] == "right" and row["valid"][-1] == 0
    assert row["skill_id"] == "pick" and row["phase_id"] == "approach" and row["task"] == "bottle_tray"
    assert row["action_exec"] == row["action_script"]
    with pytest.raises(ValueError):
        check_row(row, hz=10)
