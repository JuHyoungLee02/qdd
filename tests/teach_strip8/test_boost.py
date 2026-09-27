"""boost1 (prereg_boost1.md): (a) while holding, point targets are resolved on the depth frame remembered just before
the grasp (the held object cannot occlude the place target there); (b) an 'above' point repeated at the same spot after
the arm already reached it is turned into the next intent (holding -> place + open, else grasp + close). Both off =
the E-DIST8 d-min episode unchanged."""
import numpy as np

from harvest.teach_strip8 import boost as B


def test_loop_switch_rule():
    L = B.LoopGuard(n=2, tol=0.015)
    cmd = {"mode": "point", "point_2d": [500, 500], "height": "above", "gripper": "keep"}
    g = [0.40, -0.30, 1.00]
    assert L.check(cmd, g, tcp=[0.2, 0.0, 1.1], holding=False) is None  # first above, far away
    L.done(g)
    assert L.check(cmd, g, tcp=[0.401, -0.301, 1.0], holding=False) is None  # reached once: count 1
    L.done(g)
    sw = L.check(cmd, g, tcp=[0.40, -0.30, 1.0], holding=False)  # reached again: switch
    assert sw == {"height": "grasp", "gripper": "close"}
    L.done(g)
    assert L.check(cmd, g, tcp=[0.40, -0.30, 1.0], holding=True) is None  # count reset after a switch
    L2 = B.LoopGuard(n=2, tol=0.015)
    for _ in range(2):
        assert L2.check(cmd, g, tcp=g, holding=True) is None
        L2.done(g)
    assert L2.check(cmd, g, tcp=g, holding=True) == {"height": "place", "gripper": "open"}
    L3 = B.LoopGuard(n=2, tol=0.015)
    L3.check(cmd, g, tcp=g, holding=False)
    L3.done(g)
    L3.check(dict(cmd, height="grasp"), g, tcp=g, holding=False)  # another intent resets
    L3.done(g)
    assert L3.check(cmd, g, tcp=g, holding=False) is None
    L4 = B.LoopGuard(n=2, tol=0.015)
    L4.check(cmd, g, tcp=g, holding=False)
    L4.done(g)
    g2 = [0.45, -0.30, 1.00]  # moved 5 cm: a new spot
    assert L4.check(cmd, g2, tcp=g, holding=False) is None


def test_episode_truth_and_loop(tmp_path):
    import json

    from harvest.astra_motion.truth import Rep
    from harvest.astra_solo.pt_truth import PtTruth

    from astra_solo.test_pt_episode import A, PadWorld
    for fm, fl in ((False, False), (True, True)):
        w = PadWorld()
        m = PtTruth(w)
        ep = B.BoostEpisode(w, m, 3, "mug_tray", str(tmp_path / f"t{fm}"), fix_mem=fm, fix_loop=fl)
        m.ep = ep
        res = ep.run()
        assert res["success"], (fm, res["end_reason"], res["history"])
        assert res["boost"]["fix_mem"] == fm and (res["boost"]["n_memory_resolves"] > 0) == fm

    class Looper(PtTruth):
        """The truth, except that every grasp is asked as 'above' (the intent loop)."""

        def ask(self, text, images, meta):
            rep = super().ask(text, images, meta)
            d = json.loads(rep.text)
            c = d["command"]
            if c.get("mode") == "point" and c.get("height") == "grasp":
                d["command"] = dict(c, height="above", gripper="keep")
            return Rep(json.dumps(d))

    out = {}
    for fl in (False, True):
        w = PadWorld()
        m = Looper(w)
        ep = B.BoostEpisode(w, m, 3, "mug_tray", None, fix_loop=fl, stop_calls=12)
        m.ep = ep
        out[fl] = ep.run()
    assert not out[False]["success"] and out[True]["success"]
    assert out[True]["boost"]["switches"][0]["switch"] == {"height": "grasp", "gripper": "close"}
    assert A  # the shared assessment block is importable (fixture module)


def test_memory_frame_choice():
    M = B.PlaceMemory()
    d0, d1 = np.zeros((2, 2)), np.ones((2, 2))
    M.update(d0, tcp=[0.3, 0.0, 1.0], plane=0.85, holding=False)
    M.update(d1, tcp=[0.4, 0.0, 0.9], plane=0.85, holding=False)
    assert M.frame(holding=False, live=d1)[0] is d1  # not holding: the live frame
    M.update(np.full((2, 2), 7.0), tcp=[0.4, 0.0, 1.0], plane=0.85, holding=True)  # holding: memory not overwritten
    depth, tcp, used = M.frame(holding=True, live=np.full((2, 2), 7.0))
    assert depth is d1 and tcp == [0.4, 0.0, 0.9] and used
    assert B.PlaceMemory().frame(holding=True, live=d0) == (d0, None, False)  # nothing remembered: live
