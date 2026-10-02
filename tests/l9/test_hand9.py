"""Generic gripper layer (harvest/l9/hand9.py): gap table, empty close, any-finger holding for 2- and 3-finger
synthetic hands, derived frame, torso check."""
import json
import os

import numpy as np
import pytest

from harvest.l9 import hand9 as H


def _slab(y0, y1, z0=-0.03, z1=0.01, x=0.01, n=7):
    """A box of points (frame G) spanning y0..y1."""
    g = np.meshgrid(np.linspace(-x, x, n), np.linspace(y0, y1, n), np.linspace(z0, z1, n), indexing="ij")
    return np.stack([a.ravel() for a in g], 1)


def _two_finger(w, t=0.01):
    """Parallel pads with an inner gap w along y_G."""
    return {"A": _slab(-w / 2 - t, -w / 2), "B": _slab(w / 2, w / 2 + t)}


def _three_finger(w, t=0.01):
    """Thumb on -y, index and middle on +y side by side (x offset): the gap is thumb <-> {index, middle}."""
    return {"T": _slab(-w / 2 - t, -w / 2), "I": _slab(w / 2, w / 2 + t) + [0.006, 0, 0],
            "M": _slab(w / 2 + 0.004, w / 2 + t) + [-0.006, 0, 0]}


OPP2 = [[["A"], ["B"]]]
OPP3 = [[["T"], ["I", "M"]]]


@pytest.mark.parametrize("w", [0.0, 0.012, 0.05, 0.09])
def test_two_finger_gap_is_inner_slot(w):
    assert H.hand_gap(_two_finger(w), OPP2) == pytest.approx(w, abs=1e-9)


def test_three_finger_gap_ignores_same_side_spacing():
    # index vs middle sit side by side on the same side: their spacing is NOT the pinch gap
    g = _three_finger(0.03)
    assert H.hand_gap(g, OPP3) == pytest.approx(0.03, abs=1e-9)


def test_overlap_is_negative_and_window_limits():
    g = {"A": _slab(-0.01, 0.005), "B": _slab(-0.005, 0.01)}
    assert H.hand_gap(g, OPP2) < 0
    far = {"A": _slab(-0.06, -0.05, z0=-0.2, z1=-0.1), "B": _slab(0.05, 0.06, z0=-0.2, z1=-0.1)}
    assert np.isnan(H.hand_gap(far, OPP2))  # never inside the TCP-plane window


def test_curled_tip_ahead_of_tcp_narrows_gap():
    # the G1 lesson: a fingertip curling into the span 10 mm ahead of the TCP plane binds the gap
    g = _two_finger(0.06)
    g["B"] = np.concatenate([g["B"], _slab(0.01, 0.02, z0=-0.015, z1=-0.008)])
    assert H.hand_gap(g, OPP2) == pytest.approx(0.04, abs=1e-9)  # -0.03 (A face) .. +0.01 (tip)


def test_rekey_collapses_closed_and_keeps_path_order():
    rows = [{"a": 1.0}, {"a": 0.8}, {"a": 0.5}, {"a": 0.2}, {"a": 0.0}]
    k, g = H.rekey(rows, [-0.01, 0.001, 0.02, 0.05, float("nan")])
    assert g == [0.0, 0.02, 0.05] and k == [0, 2, 3]  # closed row = the first (most closed) path row
    k, g = H.rekey(rows, [0.0, 0.03, 0.025, 0.05, 0.06])  # a dip along the path is skipped, never re-ordered
    assert k == [0, 1, 3, 4] and g == [0.0, 0.03, 0.05, 0.06]
    with pytest.raises(ValueError):
        H.rekey(rows, [0.0, 0.0, 0.0, 0.0, float("nan")])


def _table():
    return H.GapTable({"name": "t", "joints": ["j1", "j2"], "q": [[1.1, 1.1], [0.5, 0.5], [0.0, 0.0]],
                       "gap_m": [0.0, 0.05, 0.10]})


def test_gap_table_roundtrip_and_projection():
    t = _table()
    assert t.max_gap == 0.10 and t.closed_gap == 0.0
    q = t.joints_for_gap(0.075)
    assert q["j1"] == pytest.approx(0.25)
    assert t.gap_of_q(q) == pytest.approx(0.075)
    assert t.gap_of_q({"j1": 0.25, "j2": 0.30}) == pytest.approx(0.0725, abs=1e-6)  # off-path q: projected
    assert t.joints_for_gap(-1)["j1"] == 1.1 and t.joints_for_gap(1)["j1"] == 0.0
    with pytest.raises(ValueError):
        H.GapTable({"joints": ["j"], "q": [[0.0], [1.0]], "gap_m": [0.02, 0.02]})


@pytest.mark.parametrize("closed", [0.0, 0.004])
def test_empty_close_from_measured_gap(closed):
    assert H.close_verdict(closed + 0.002, 0.03, closed) == "EMPTY"
    assert H.close_verdict(0.032, 0.03, closed) == "CONTACT"
    assert H.close_verdict(0.07, 0.03, closed) == "WIDE"
    # a fingertip touching something else while the gap says CONTACT: no tip touches the target -> EMPTY
    assert H.close_verdict(0.032, 0.03, closed, touched={"o9"}, target="o3") == "EMPTY"
    assert H.close_verdict(0.032, 0.03, closed, touched={"o3"}, target="o3") == "CONTACT"


@pytest.mark.parametrize("n_fingers", [2, 3])
def test_holding_any_finger_max_effort(n_fingers):
    f = np.zeros(n_fingers)
    e = np.zeros(n_fingers + 2)
    assert not H.holding(f, e)
    f[-1] = 3.0  # only the LAST finger touches
    e[-1] = 1.5  # only the LAST joint carries effort (a single-joint reading of joint 0 would miss it)
    assert H.holding(f, e)
    assert not H.holding(f, np.full_like(e, 0.2))  # touching without squeezing
    t = _table()
    assert not H.holding(f, e, gap=0.099, tbl=t)  # fully open: not holding
    assert H.holding(f, e, gap=0.04, tbl=t)


def test_derived_frame_matches_G_for_a_parallel_gripper():
    c_closed = {"A": np.array([0.0, -0.001, 0.0]), "B": np.array([0.0, 0.001, 0.0])}
    c_open = {"A": np.array([0.0, -0.04, 0.0]), "B": np.array([0.0, 0.04, 0.0])}
    palm = _slab(-0.04, 0.04, z0=0.03, z1=0.05)  # palm behind the pads (+z_G = towards the wrist)
    fr = H.derived_frame(c_closed, c_open, OPP2, palm, z_open=[(-0.01, 0.01), (-0.01, 0.01)])
    chk = H.frame_check(fr)
    assert chk["ok"] and chk["closing_err_deg"] < 1 and chk["approach_err_deg"] < 1
    bad = dict(fr, closing=np.array([1.0, 0.0, 0.0]))  # closing axis along x_G: wrong frame
    assert not H.frame_check(bad)["ok"]


def test_torso_check():
    ok = [{"lift": [0.1] * 5}, {"lift": [0.3] * 5}]
    assert H.torso_check(ok, {"lift": (0.0, 0.4)}, min_spread=0.1)["ok"]
    moved = [{"lift": [0.1, 0.1, 0.15]}]
    assert not H.torso_check(moved)["ok"]
    assert not H.torso_check(ok, {"lift": (0.0, 0.2)})["ok"]  # outside the range
    assert not H.torso_check([{"lift": [0.1]}, {"lift": [0.1]}], {"lift": (0.0, 0.4)}, min_spread=0.1)["ok"]


def test_flag_off_returns_no_table(monkeypatch):
    monkeypatch.delenv("L9_GRIP_LAYER", raising=False)
    assert H.active_table("franka_mast", "right") is None


def test_descriptors_cover_every_gripper_json():
    d = H.descriptors()
    assert set(H.GRIPPER_JSON.values()) <= set(d)
    for name, h in d.items():
        tips = set(h["tips"])
        for A, B in h["opposition"]:
            assert set(A) <= tips and set(B) <= tips and not set(A) & set(B)


def test_committed_gap_tables_are_valid():
    for name in set(H.GRIPPER_JSON.values()):
        p = os.path.join(H.GAP_DIR, f"{name}.json")
        if not os.path.exists(p):
            continue
        t = H.table(name)
        assert 0.0 <= t.closed_gap < 0.005 and t.max_gap > 0.03
        assert len(json.load(open(p))["contacts_G"]) == len(t.gap)


def test_frame_check_flags_tcp_off_the_pads():
    fr = {"tcp": np.zeros(3), "closing": np.array([0.0, 1.0, 0.0]), "approach": np.array([0.0, 0.0, -1.0]),
          "z_pads": np.array([-0.04, -0.02])}  # pads 20-40 mm ahead of the TCP plane
    assert not H.frame_check(fr)["tcp_plane_on_pads"]
    fr["z_pads"] = np.array([-0.03, 0.002])
    assert H.frame_check(fr)["ok"]


def test_contact_patch_is_inner_face_centre():
    P = _slab(0.02, 0.03, z0=-0.03, z1=0.01)
    c, (z0, z1) = H.contact_patch(P, toward=np.array([0.0, -0.05, -0.01]))
    assert c[1] == pytest.approx(0.02, abs=1e-3) and c[2] == pytest.approx(-0.01) and (z0, z1) == pytest.approx((-0.03, 0.01))


def test_close_verdict_uses_tcp_plane_gap_for_contact():
    # rotating fingers (AI Worker): the binding free gap reads narrower than the TCP-plane gap on the object
    assert H.close_verdict(0.035, 0.054, 0.002, gap_tcp=0.055) == "CONTACT"
    assert H.close_verdict(0.035, 0.054, 0.002) == "WIDE"


@pytest.mark.parametrize("hand", ["two", "three"])
def test_pinched_needs_both_sides(hand):
    if hand == "two":
        meta = {"method": {"chains": {"l2": ["l1", "l2"], "r2": ["r1", "r2"]}, "opposition": [[["l2"], ["r2"]]]}}
        one, both = {"l1": 2.0, "r1": 0.0}, {"l1": 2.0, "r2": 1.0}
    else:
        meta = {"method": {"chains": {"th": ["th0", "th"], "ix": ["ix0", "ix"], "md": ["md0", "md"]},
                           "opposition": [[["th"], ["ix", "md"]]]}}
        one, both = {"ix": 3.0, "md": 3.0, "th": 0.1}, {"md0": 3.0, "th0": 1.0}
    t = H.GapTable(dict(_table().meta, **meta))
    assert not H.pinched(one, t) and H.pinched(both, t)


def test_spec_r4_grip_tag(monkeypatch):
    from harvest.l9 import specgate9 as S
    assert S.spec_for("ffw_sg2", False) == S.SPEC and S.spec_for("franka_mast", False) == S.SPEC_FRANKA_R1
    assert S.spec_for("g1", True) == "L9v2-spec-final-r4-grip"
    assert S.spec_for("franka_mast", True) == "L9v2-spec-final-r1-r4-grip"
    assert {S.spec_family(S.spec_for(r, g)) for r in ("ffw_sg2", "franka_mast") for g in (0, 1)} == {S.SPEC}


def test_exec_offsets_interpolate_contact_mid_and_front():
    meta = {"method": {"opposition": [[["a"], ["b"]]]},
            "contacts_G": [{"a": [0.016, -0.001, -0.01], "b": [0.016, 0.001, -0.01]},
                           {"a": [0.0, -0.03, 0.0], "b": [0.0, 0.03, 0.0]},
                           {"a": [0.0, -0.05, 0.0], "b": [0.0, 0.05, 0.0]}],
            "tip_front_G": [-0.04, -0.03, -0.02]}
    t = H.GapTable(dict(_table().meta, **meta))
    o = t.exec_offsets(0.025)
    assert o["contact_mid"] == pytest.approx([0.008, 0.0, -0.005]) and o["tip_front"] == pytest.approx(-0.035)
    assert H.GapTable(_table().meta).exec_offsets(0.02) == {}
