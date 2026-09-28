"""D round 2 code fixes (prereg_dround2.md): (d) DescendGuard - not holding, above the pointed object (xy within 2 cm)
and not descending for 2 calls while the intent is not grasp -> grasp + close at the same point; (a) point recheck -
before the grasp, a crop around the pointed pixel is shown to the same model ("is this the <target>?"); a 'no' re-asks
the command once with a note."""
import json

import numpy as np

from harvest.astra_motion.truth import Rep
from harvest.astra_solo.pt_truth import PtTruth
from harvest.teach_strip8 import boost as B

from astra_solo.test_pt_episode import PadWorld


def test_descend_guard_rule():
    D = B.DescendGuard(n=2)
    res = {"kind": "object", "xy": [0.40, -0.30], "top": 0.945}
    cmd = {"mode": "point", "point_2d": [500, 500], "height": "lift", "gripper": "keep"}
    tcp = [0.401, -0.301, 1.05]
    assert D.check(cmd, res, tcp, holding=False) is None
    assert D.check(cmd, res, tcp, holding=False) == {"height": "grasp", "gripper": "close"}
    assert D.check(cmd, res, tcp, holding=False) is None  # reset after a switch
    D2 = B.DescendGuard(n=2)
    assert D2.check(cmd, res, tcp, holding=False) is None
    assert D2.check(cmd, res, [0.401, -0.301, 1.0], holding=False) is None  # it descended 5 cm: reset
    assert D2.check(dict(cmd, height="grasp"), res, tcp, holding=False) is None
    assert D2.check(cmd, res, [0.47, -0.30, 1.05], holding=False) is None  # not above the object
    assert D2.check(cmd, dict(res, kind="table"), tcp, holding=False) is None
    assert D2.check(cmd, res, tcp, holding=True) is None


class Lifter(PtTruth):
    """The truth, except that every grasp is asked as 'above' (it never descends; the LoopGuard is off here)."""

    def ask(self, text, images, meta):
        d = json.loads(super().ask(text, images, meta).text)
        c = d["command"]
        if c.get("mode") == "point" and c.get("height") == "grasp":
            d["command"] = dict(c, height="above", gripper="keep")
        return Rep(json.dumps(d))


def test_descend_guard_in_episode():
    out = {}
    for fd in (False, True):
        w = PadWorld()
        m = Lifter(w)
        ep = B.BoostEpisode(w, m, 3, "mug_tray", None, fix_descend=fd, stop_calls=14)
        m.ep = ep
        out[fd] = ep.run()
    assert not out[False]["success"] and out[True]["success"]
    assert any(s.get("guard") == "descend" for s in out[True]["boost"]["switches"])


class Recheck(PtTruth):
    """Pointing: the first answer of every call points at a wrong pixel; the verifier says 'no' for that pixel."""

    def __init__(self, w):
        super().__init__(w)
        self.k, self.asked_verify = 0, 0

    def ask(self, text, images, meta):
        if "Is the marked point on the" in text:
            self.asked_verify += 1
            return Rep(json.dumps({"yes": False}))
        rep = super().ask(text, images, meta)
        d = json.loads(rep.text)
        c = d["command"]
        if ("NOTE: your point" not in text and c.get("mode") == "point" and c.get("point_2d") and c["height"] != "lift"
                and not self.ep.holding(self.w.status())):
            d["command"] = dict(c, point_2d=[5, 5])  # a corner of the image: nothing there
        return Rep(json.dumps(d))


def test_point_recheck_reasks_once():
    w = PadWorld()
    m = Recheck(w)
    ep = B.BoostEpisode(w, m, 3, "mug_tray", None, fix_loop=True, recheck=True, stop_calls=14)
    m.ep = ep
    res = ep.run()
    assert m.asked_verify > 0
    assert res["boost"]["rechecks"] and all(r["answer"] is False for r in res["boost"]["rechecks"])
    assert res["success"], res["end_reason"]


def test_crop_marks_point():
    from harvest.astra_solo.overlay import png_bytes
    img = np.full((376, 672, 3), 100, np.uint8)
    crop = B.crop_png(png_bytes(img), [500, 500], half=64)
    from PIL import Image
    import io
    c = np.asarray(Image.open(io.BytesIO(crop)).convert("RGB"))
    assert c.shape[0] == c.shape[1] >= 128 and (c != 100).any()
