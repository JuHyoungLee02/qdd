"""Loop break (docs/stage3/prereg_main35_closed2.md; diagnosis results/m35cl_stagecap_diag.md fix 1): repeats are
compared on the executed (post-clip) target and the settled TCP, 2-cycles (above <-> lift) count, a stall gets one
adapter sentence in the history slot, the same command is then not re-executed, and a stall that goes on ends the
episode with 'stall' (not the call cap). Genuine convergence and progress after the hint must not trigger."""
import json

import numpy as np

from harvest.teach_strip8 import boost as B
from harvest.teach_strip8 import stall as S

TZ = 0.85  # table z


def call(height, target, tcp, holding=False, grip_w=0.08, kind="other", gripper="keep", mode="point"):
    return S.Call(mode=mode, height=height, gripper=gripper,
                  target=None if target is None else S.executed_target(target, TZ),
                  tcp=np.asarray(tcp, float), holding=holding, grip_w=grip_w, kind=kind)


def test_post_clip_repeat_is_caught_where_pre_clip_misses():
    """'above' on a look-alike at y=+0.31 (outside the box y<=0.10): the arm stops at the clipped y=0.10. The raw goals
    jitter by 2-4 cm, the old LoopGuard (raw goal vs TCP) never counts; the executed targets are one point."""
    raw = [[0.45, 0.31, 1.00], [0.45, 0.28, 1.00], [0.45, 0.33, 1.00], [0.45, 0.30, 1.00]]
    tcp = [0.45, 0.10, 1.00]
    old = B.LoopGuard()
    cmd = {"mode": "point", "point_2d": [100, 500], "height": "above", "gripper": "keep"}
    for g in raw:
        assert old.check(cmd, g, tcp, holding=False) is None
        old.done(g)
    assert old.count == 0
    g = S.StallGuard()
    acts = [g.observe(call("above", r, tcp, kind="blocked"))["action"] for r in raw[:3]]
    assert acts == [None, None, "hint"]  # 3 calls with the same result -> one hint
    assert g.period == 1 and g.hinted
    assert "3 calls in a row" in g.hint_text() and "BLOCKED" in g.hint_text()
    nxt = call("above", raw[3], tcp, kind="blocked")
    assert g.would_repeat(nxt)  # the 4th identical command is not re-executed


def test_two_cycle_above_lift():
    """ep0.5 place failure: holding over the tray, 'above' <-> 'lift' forever (each call moves, the pair does not)."""
    g = S.StallGuard()
    above, lift = [0.40, -0.20, 1.05], [0.40, -0.20, 1.20]
    seq = [("above", above), ("lift", lift), ("above", above), ("lift", lift)]
    acts = [g.observe(call(h, t, t, holding=True, grip_w=0.064, kind="reach"))["action"] for h, t in seq]
    assert acts == [None, None, None, "hint"]
    assert g.period == 2 and "alternated" in g.hint_text()
    assert g.would_repeat(call("above", above, above, holding=True, grip_w=0.064))
    assert not g.would_repeat(call("place", above, above, holding=True, grip_w=0.064, gripper="open"))
    # the old guard counted consecutive 'above' only: a lift in between always reset it
    old = B.LoopGuard()
    for h, t in seq * 2:
        cmd = {"mode": "point", "point_2d": [1, 1], "height": h, "gripper": "keep"}
        assert old.check(cmd, t, t, holding=True) is None
        old.done(t if h == "above" else None)


def test_stall_ends_after_n_more_calls():
    g = S.StallGuard(n_end=3)
    tcp = [0.45, 0.10, 1.00]
    for _ in range(3):
        a = g.observe(call("above", [0.45, 0.31, 1.0], tcp, kind="blocked"))["action"]
    assert a == "hint"
    for k in range(3):
        c = call("above", [0.45, 0.30, 1.0], tcp, kind="blocked")
        assert g.would_repeat(c)
        a = g.skip(c)["action"]
        assert a == ("end" if k == 2 else "still")


def test_genuine_convergence_does_not_trigger():
    """The same 'above' target, the TCP closing in each call (>= 10 mm moved or >= 5 mm nearer): no hint ever."""
    g = S.StallGuard()
    tgt = [0.40, -0.30, 1.00]
    for d in (0.060, 0.045, 0.032, 0.024, 0.017, 0.011, 0.005):  # 6-15 mm steps, error shrinking
        a = g.observe(call("above", tgt, [0.40 - d, -0.30, 1.00], kind="blocked" if d > 0.015 else "reach"))
        assert a["action"] is None and a["period"] == 0
    # reached and re-asked once (the LoopGuard's case), then a new intent: no hint
    g2 = S.StallGuard()
    for h in ("above", "above", "grasp"):
        assert g2.observe(call(h, tgt, tgt, kind="reach", gripper="close" if h == "grasp" else "keep"))["action"] \
            is None


def test_progress_after_hint_resets():
    g = S.StallGuard(n_end=2)
    tcp = [0.45, 0.10, 1.00]
    for _ in range(3):
        a = g.observe(call("above", [0.45, 0.31, 1.0], tcp, kind="blocked"))["action"]
    assert a == "hint"
    # the planner reads the hint and points at the right object: the arm moves 40 cm -> reset, no end
    a = g.observe(call("above", [0.45, -0.30, 1.0], [0.45, -0.30, 1.0], kind="reach"))
    assert a["action"] is None and not g.hinted and g.streak == 0
    assert not g.would_repeat(call("above", [0.45, -0.30, 1.0], [0.45, -0.30, 1.0]))
    # a new stall needs the full count again (no carried-over end)
    for k in range(2):
        a = g.observe(call("grasp", [0.45, -0.30, 0.9], [0.45, -0.30, 0.93], kind="blocked", gripper="close"))
        assert a["action"] is None
    assert g.observe(call("grasp", [0.45, -0.30, 0.9], [0.45, -0.30, 0.93], kind="blocked",
                          gripper="close"))["action"] == "hint"


def test_gripper_change_is_progress():
    g = S.StallGuard()
    t = [0.40, -0.30, 0.95]
    g.observe(call("grasp", t, t, kind="reach", gripper="close"))
    g.observe(call("grasp", t, t, kind="reach", gripper="close", grip_w=0.064, holding=True))  # it grasped
    a = g.observe(call("grasp", t, t, kind="reach", gripper="close", grip_w=0.064, holding=True))
    assert a["action"] is None and g.streak == 1  # only 2 unchanged so far


def test_rewrite_history_line():
    line = "4: point at (100, 500), height above, gripper keep -> done; TCP now (0.450, 0.100, 1.000), pad gap 8.0 cm"
    s = S.skip_line(line, "not executed: X")
    assert s == ("4: point at (100, 500), height above, gripper keep -> not executed: X; TCP now (0.450, 0.100, "
                 "1.000), pad gap 8.0 cm")
    h = S.hint_line("3: a -> BLOCKED: stopped 40 mm; TCP now (1, 2, 3), pad gap 8.0 cm", "NO CHANGE: y")
    assert h == "3: a -> BLOCKED: stopped 40 mm; NO CHANGE: y; TCP now (1, 2, 3), pad gap 8.0 cm"


def _stuck_model(w):
    """Every call the same 'above' on a spot outside the workspace box (y = +0.30): clipped, the arm never gets there."""
    from harvest.astra_motion import geometry as G
    from harvest.astra_motion.truth import Rep
    from harvest.astra_solo import resolve as RS
    from harvest.astra_solo.pt_truth import ASSESS

    class Stuck:
        name = "stuck"

        def __init__(self):
            self.ep, self.n = None, 0

        def ask(self, text, images, meta):
            self.n += 1
            u, v, _ = G.project(self.ep.head, np.array([0.45, 0.30, w.table_z + 0.02]))
            c = {"mode": "point", "point_2d": RS.to_scaled(u, v, self.ep.head.W, self.ep.head.H), "height": "above",
                 "gripper": "keep"}
            return Rep(json.dumps({"assessment": ASSESS, "command": c, "reason": "stuck"}))
    return Stuck()


def test_episode_stall_end_and_off_unchanged():
    from astra_solo.test_pt_episode import PadWorld

    Ep = S.with_loop_break(B.LimitEpisode)
    out = {}
    for lb in (False, True):
        w = PadWorld()
        m = _stuck_model(w)
        ep = Ep(w, m, 3, "mug_tray", None, fix_loop=True, mem_points=True, stop_calls=12, loop_break=lb)
        m.ep = ep
        out[lb] = (ep.run(), m.n)
    off, on = out[False][0], out[True][0]
    assert off["end_reason"] == "stage_cap_calls" and "stall" not in off
    assert on["end_reason"] == "stall" and out[True][1] < out[False][1]
    h = on["history"]
    assert any("NO CHANGE" in x for x in h) and any("not executed" in x for x in h)
    assert on["stall"]["hints"] == [3] and on["stall"]["skips"] and on["stall"]["end_call"] == 6
    # loop_break=False is the plain LimitEpisode (same history as the unwrapped class)
    w = PadWorld()
    m = _stuck_model(w)
    ep = B.LimitEpisode(w, m, 3, "mug_tray", None, fix_loop=True, mem_points=True, stop_calls=12)
    m.ep = ep
    assert ep.run()["history"] == off["history"]


def test_runner_episode_class_has_the_switch():
    from harvest.teach_pt import run_closed_l8s as R
    Ep = R.episode_class()
    assert issubclass(Ep, B.LimitEpisode) and "loop_break" in Ep.__mro__[1].__init__.__code__.co_varnames
