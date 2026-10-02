import math

import numpy as np

from harvest.astra_motion.geometry import Cam
from harvest.l9 import grasp9 as G
from harvest.l9 import v2plan as P


def _cands():
    """Synthetic candidates around an object at (0.45, -0.2, 0.80): top-centre, top off-centre, oblique, side, front."""
    c = np.array([0.45, -0.2, 0.80])
    A = [np.array([0, 0, -1.0]), np.array([0, 0, -1.0]),
         np.array([math.sin(0.8), 0, -math.cos(0.8)]), np.array([0, 1.0, 0]), np.array([1.0, 0, 0])]
    offs = [np.zeros(3), np.array([0.03, 0, 0]), np.zeros(3), np.zeros(3), np.zeros(3)]
    T, c1, c2 = [], [], []
    for a, o in zip(A, offs):
        cl = np.cross(a, [0.0, 0, 1]) if abs(a[2]) < 0.9 else np.array([1.0, 0, 0])
        cl = cl / np.linalg.norm(cl)
        R = G.frame_of(a, cl)
        t = np.eye(4)
        t[:3, :3], t[:3, 3] = R, c + o
        T.append(t)
        c1.append(c + o - 0.02 * R[:, 1])
        c2.append(c + o + 0.02 * R[:, 1])
    n = len(A)
    return {"T": np.array(T), "c1": np.array(c1), "c2": np.array(c2), "w": np.full(n, 0.04),
            "a": np.array(A), "score": np.ones(n), "pre_open": np.full(n, 0.065),
            "source": np.array(["analytic"] * n)}, c


def _cam():
    # looking down the -z from 0.6 m above the object, optical x = world -y, y = world -x
    R = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, -1.0]])
    return Cam("head", 672, 376, 400.0, 400.0, 336.0, 188.0, R, np.array([0.45, -0.2, 1.4]))


def test_choose_top_centre_then_constraint_and_meta():
    C, c = _cands()
    ok = np.ones(5, bool)
    gc = None
    for seed in range(40):  # find a non-instructed draw
        d = P.draws(seed, 0)
        if not d["instructed"]:
            gc = P.choose(C, ok, np.ones(5), c, (0.0, 0.0), seed, 0)
            break
    assert gc.idx == 0 and gc.rule_step == 0 and gc.family == "top"
    gc2 = P.choose(C, ok, np.ones(5), c, (0.0, 0.0), seed, 0, constraint="blocked_above")
    assert gc2.family in ("front", "side") and gc2.rule_step == 1
    m = gc.meta
    for k in ("label_rule", "rule_step", "approach_reason", "instructed_approach", "ik_ok_by_family", "random_alt_idx",
              "grasp_world", "contacts_world", "width_m", "pre_open_m", "rot_bin_base", "open_bin3", "open_cm_bin"):
        assert k in m


def test_instructed_rate_and_family():
    C, c = _cands()
    ok = np.ones(5, bool)
    inst = [P.choose(C, ok, np.ones(5), c, (0.0, 0.0), s, 0) for s in range(400)]
    rate = sum(g.instructed is not None for g in inst) / len(inst)
    assert 0.14 < rate < 0.26
    assert all(g.family == g.instructed for g in inst if g.instructed)


def test_label_point_and_rot_bin_with_camera():
    C, c = _cands()
    cam = _cam()
    depth = np.full((376, 672), 0.6 - 0.0, float)  # a flat top at the object centre height
    gc = P.choose(C, np.ones(5, bool), np.ones(5), c, (0.0, 0.0), 3, 0, cam=cam, depth=depth, allow_instruct=False)
    m = gc.meta
    assert m["point"] is not None and abs(m["point"][0] - 500) <= 2 and abs(m["point"][1] - 500) <= 2
    assert 0 <= m["rot_bin_img"] <= 11 and len(m["valid_set"]) == 5


def test_single_candidate_choose_keeps_part_and_point():
    """rt9.next_fallback re-chooses one candidate: with parts / camera it must keep the part and the visible point."""
    C, c = _cands()
    i = 2
    sub = {k: (v[[i]] if isinstance(v, np.ndarray) and len(v) == 5 else v) for k, v in C.items()}
    parts = np.array(["body"])
    depth = np.full((376, 672), 0.6, float)
    gc = P.choose(sub, np.ones(1, bool), np.ones(1), c, (0.0, 0.0), 0, 0, allow_instruct=False, cam=_cam(),
                  depth=depth, parts=parts, category="bottle", height=0.2)
    assert gc is not None and gc.meta["part"] == "body" and gc.meta["label_rule"] == "natural_v1"
    assert gc.meta["point"] is not None and gc.meta["category"] == "bottle"


def _st(tcp, quat, grip_w=0.1, hold=False, obj=None, on=False):
    obj = obj or {"o1": [0.45, -0.2, 0.80], "o2": [0.40, -0.35, 0.76]}
    return {"tcp": tcp, "tcp_quat": quat, "grip_w": grip_w, "obj": obj,
            "obj_quat": {k: [1.0, 0, 0, 0] for k in obj},
            "pred": {"holding(o1)": hold, "upright(o1)": True, "on(o1,o2)": on}}


def test_inview_score_true_false():
    """P.inview_score (L9_CARRY_INVIEW): same 'inside with a 5% margin' convention as world9._head_sees."""
    cam = _cam()
    centre_pt = np.array([0.45, -0.2, 0.8])  # straight below the camera: always centred regardless of depth
    far_pt = np.array([0.45, -0.7, 0.8])  # far to the side: projects outside the margin
    assert P.inview_score(cam, [centre_pt]) == 1.0
    assert P.inview_score(cam, [far_pt]) == 0.0
    assert P.inview_score(cam, [centre_pt, far_pt]) == 0.5
    assert P.inview_score(None, [centre_pt]) == 0.0  # no camera (flag off) -> 0, never consulted by carry_over_z
    assert P.inview_score(cam, []) == 0.0


def test_carry_over_z_default_without_cam_or_held():
    """cam=None or T_obj_G=None (flag off / nothing measured yet) must keep today's formula byte-identical."""
    assert P.carry_over_z(0.97, 0.84, (0.40, -0.55), [1, 0, 0, 0], np.eye(4), cam=None) == 0.97
    assert P.carry_over_z(0.97, 0.84, (0.40, -0.55), [1, 0, 0, 0], None, cam=_cam()) == 0.97


def test_carry_over_z_tie_keeps_default():
    """Both candidates equally (in)-view (here: directly under the camera, always centred) -> keep max() (today)."""
    cam = _cam()
    assert P.carry_over_z(0.97, 0.84, (0.45, -0.2), [1, 0, 0, 0], np.eye(4), cam=cam) == 0.97


def test_carry_over_z_prefers_inview_candidate():
    """The higher (default = max) candidate projects outside the head image at this offset; the lower one is
    inside -> carry_over_z switches to it (soft preference, no new constant: both values are already computed by
    the caller)."""
    cam = _cam()
    assert P.carry_over_z(0.97, 0.84, (0.40, -0.55), [1, 0, 0, 0], np.eye(4), cam=cam) == 0.84
    assert P.carry_over_z(0.84, 0.97, (0.40, -0.55), [1, 0, 0, 0], np.eye(4), cam=cam) == 0.84  # order-independent


def test_plan_carry_over_default_matches_legacy_formula(monkeypatch):
    """plan()'s carry_over step without a camera (flag off) must still compute max(zc, put_z + 0.05): the only
    change is additive and opt-in."""
    from harvest.astra_motion import harness
    monkeypatch.setattr(harness, "obj_height", lambda k: 0.10)
    C, c = _cands()
    gc = P.choose(C, np.ones(5, bool), np.ones(5), c, (0.0, 0.0), 5, 0, allow_instruct=False)
    info = {"tgt": "o1", "place": "o2", "sup_tgt": 0.75, "sup_place": 0.71, "place_top": 0.73}
    held = {"T_obj_G": np.eye(4)}
    obj = {"o1": [0.45, -0.2, 0.80], "o2": [0.40, -0.55, 0.71]}
    st = _st([0.0, 0.0, 0.97], list(gc.quat), 0.04, hold=True, obj=obj)
    put_T = P.put_pose([1.0, 0, 0, 0], (0.40, -0.55), 0.73 + 0.05 + gc.place_dz, np.eye(4))
    expected = round(max(0.97, put_T[2, 3] + 0.05), 4)
    s, cmd = P.plan(st, info, 0.75, 0.107, gc, held)
    assert s == "carry_over" and cmd["position_m"][2] == expected


def test_plan_carry_over_prefers_inview_with_camera(monkeypatch):
    """Same scenario, with a head camera (L9_CARRY_INVIEW=1 wiring): the default (zc) candidate is off-frame at
    this place offset, the lower one is in frame -> plan() must return the lower z instead."""
    from harvest.astra_motion import harness
    monkeypatch.setattr(harness, "obj_height", lambda k: 0.10)
    C, c = _cands()
    gc = P.choose(C, np.ones(5, bool), np.ones(5), c, (0.0, 0.0), 5, 0, allow_instruct=False)
    info = {"tgt": "o1", "place": "o2", "sup_tgt": 0.75, "sup_place": 0.71, "place_top": 0.73}
    held = {"T_obj_G": np.eye(4)}
    obj = {"o1": [0.45, -0.2, 0.80], "o2": [0.40, -0.55, 0.71]}
    st = _st([0.0, 0.0, 0.97], list(gc.quat), 0.04, hold=True, obj=obj)
    put_T = P.put_pose([1.0, 0, 0, 0], (0.40, -0.55), 0.73 + 0.05 + gc.place_dz, np.eye(4))
    expected = round(put_T[2, 3] + 0.05, 4)
    s, cmd = P.plan(st, info, 0.75, 0.107, gc, held, cam=_cam())
    assert s == "carry_over" and cmd["position_m"][2] == expected and expected < 0.97 - 0.05


def test_plan_sequence_side_grasp(monkeypatch):
    from harvest.astra_motion import harness
    monkeypatch.setattr(harness, "obj_height", lambda k: 0.10)
    C, c = _cands()
    ok = np.zeros(5, bool)
    ok[3] = True  # side only
    gc = P.choose(C, ok, np.ones(5), c, (0.0, 0.0), 5, 0, allow_instruct=False)
    assert gc.family == "side"
    info = {"tgt": "o1", "place": "o2", "sup_tgt": 0.75, "sup_place": 0.71, "place_top": 0.73}
    q0 = [1.0, 0, 0, 0]
    s, cmd = P.plan(_st([0.3, -0.3, 1.1], q0), info, 0.75, 0.107, gc, None)
    assert s == "above_target" and np.allclose(cmd["position_m"], gc.pre, atol=1e-3)
    s, cmd = P.plan(_st(list(gc.pre), list(gc.quat)), info, 0.75, 0.107, gc, None)
    assert s == "descend_close" and np.allclose(cmd["position_m"], gc.pos, atol=1e-3) and cmd["gripper"] == "close"
    # holding: carry up keeps the held orientation, then over the place, then lower with the measured grip offset
    T_og = np.linalg.inv(np.block([[np.eye(3), c[:, None]], [np.zeros((1, 3)), np.ones((1, 1))]])) @ gc.T
    s, cmd = P.plan(_st(list(gc.pos), list(gc.quat), 0.04, hold=True), info, 0.75, 0.107, gc, {"T_obj_G": T_og})
    assert s == "carry_up" and cmd["quat_wxyz"] == [round(v, 5) for v in gc.quat]
    put_xy = np.array([0.40, -0.35]) + T_og[:2, 3]
    s, cmd = P.plan(_st([put_xy[0], put_xy[1], 1.2], list(gc.quat), 0.04, hold=True), info, 0.75, 0.107, gc,
                    {"T_obj_G": T_og})
    assert s == "lower_open" and cmd["gripper"] == "open"


def test_carry_z_default_and_r1_clearance():
    """L9v2-R1: no carry_clear -> carry_base + CARRY_DZ; with carry_clear the held object's bottom clears carry_base
    by carry_clear (TCP = base + hang + clear), never above the default."""
    import types

    from harvest.l9.v2plan import carry_z
    H = {"carry_base": 0.75}
    gc = types.SimpleNamespace()
    assert carry_z(H, 0.22, gc, [0, 0, 0.80], [0, 0, 0.78], 0.06, True) == 0.75 + 0.22
    gc.carry_clear = 0.07
    # object centre 0.78, height 0.06 -> bottom 0.75; TCP 0.80 -> hang 0.05; z = 0.75 + 0.05 + 0.07
    assert abs(carry_z(H, 0.22, gc, [0, 0, 0.80], [0, 0, 0.78], 0.06, True) - 0.87) < 1e-9
    # a tall hang is capped at the default
    assert carry_z(H, 0.22, gc, [0, 0, 1.10], [0, 0, 0.78], 0.06, True) == 0.75 + 0.22
