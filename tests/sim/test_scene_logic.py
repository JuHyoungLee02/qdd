"""Pure parts of harvest.sim.scene / oracle_state (no Isaac)."""
import numpy as np
import pytest

from harvest.sim.oracle_state import support_from_contacts
from harvest.sim.scene import (
    GRIP_MAX_W, OBJ_GEOM, SCENE_SPEC, joint_to_width, sample_layout, width_to_joint,
)

DEV = range(30)


def test_spec_ids_and_instruction():
    assert SCENE_SPEC["target"] == "o3" and SCENE_SPEC["place"] == "o5"
    assert SCENE_SPEC["distractors"] == ("o8", "o9")
    assert SCENE_SPEC["instruction"] == "Put the red mug on the blue tray."


def test_layout_deterministic_per_seed():
    assert sample_layout(3) == sample_layout(3)
    assert sample_layout(3) != sample_layout(4)


@pytest.mark.parametrize("seed", DEV)
def test_layout_constraints(seed):
    L = sample_layout(seed)
    assert {"o3", "o5"} <= set(L)
    ds = [k for k in L if k in ("o8", "o9")]
    assert 0 <= len(ds) <= 2
    m, t = np.array(L["o3"][:2]), np.array(L["o5"][:2])
    assert np.linalg.norm(m - t) >= 0.16  # something to carry
    for k in ds:  # fingers need room around the mug (grasp axis = y)
        assert np.linalg.norm(np.array(L[k][:2]) - m) >= 0.10
    keys = list(L)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ra, rb = OBJ_GEOM[a]["footprint_r"], OBJ_GEOM[b]["footprint_r"]
            assert np.linalg.norm(np.array(L[a][:2]) - np.array(L[b][:2])) >= ra + rb + 0.02


def test_layout_varies_distractor_count_over_dev():
    counts = {sum(k in sample_layout(s) for k in ("o8", "o9")) for s in DEV}
    assert counts == {0, 1, 2}


def test_width_joint_roundtrip_and_monotone():
    assert joint_to_width(0.0) == pytest.approx(GRIP_MAX_W, abs=1e-4)
    ws = [joint_to_width(q) for q in np.linspace(0, 1.1, 12)]
    assert all(a > b for a, b in zip(ws, ws[1:]))
    for w in (0.003, 0.03, 0.064, 0.1):
        assert joint_to_width(width_to_joint(w)) == pytest.approx(w, abs=1e-3)
    assert width_to_joint(1.0) == 0.0 and width_to_joint(0.0) == pytest.approx(1.1)  # 0 = fully closed


def test_support_picks_highest_contact_below():
    pos = {"o3": np.array([0.4, -0.2, 0.06]), "o5": np.array([0.4, -0.2, 0.0075]), "o8": np.array([0.3, 0, 0.06])}
    half_z = {"o3": 0.0475, "o5": 0.0075, "o8": 0.06}
    contacts = {frozenset({"o3", "o5"}), frozenset({"gripper", "o3"})}
    sup = support_from_contacts(pos, half_z, contacts)
    assert sup["o3"] == "o5"
    assert sup["o5"] == "table" and sup["o8"] == "table"


def test_support_none_when_held_in_air():
    pos = {"o3": np.array([0.4, -0.2, 0.15])}
    sup = support_from_contacts(pos, {"o3": 0.0475}, {frozenset({"gripper", "o3"})})
    assert sup["o3"] is None
