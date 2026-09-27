"""boost2 DAgger collector: the learner's answer (asked with the d-min request + ring head image) is executed, the row
keeps the truth label; an invalid learner answer executes the truth (fallback); rows / meta / scene are written."""
import json

from harvest.astra_motion.truth import Rep
from harvest.astra_solo.pt_truth import PtTruth
from harvest.teach_strip8 import dagger as D

from astra_solo.test_pt_episode import PadWorld


class Learner:
    """Answers like the pt truth (valid point commands); records what it was asked."""

    def __init__(self, world, garbage_every=0):
        self.t, self.asked, self.k, self.g, self.ep = PtTruth(world), [], 0, garbage_every, None

    def ask(self, text, images, meta):
        self.t.ep = self.ep
        self.asked.append((text, images))
        self.k += 1
        if self.g and self.k % self.g == 0:
            return Rep("not json")
        return self.t.ask(text, images, meta)


def _run(tmp_path, g):
    w = PadWorld()
    lm = Learner(w, g)
    import harvest.teach_strip8.dagger as mod
    orig = mod.collect_episode

    meta = orig(w, 30001, "mug_tray", "standard", "train", str(tmp_path / f"e{g}"), lm, stop_calls=20)
    return meta, lm


def test_learner_drives_and_truth_labels(tmp_path, monkeypatch):
    import harvest.teach_l8d.collect as XC
    monkeypatch.setattr(XC, "scene_record", lambda *a, **k: {"table_z": 0.85, "distractors": {"n": 0}})
    meta, lm = _run(tmp_path, 0)
    assert meta["n_model"] > 0 and meta["n_fallback"] == 0 and meta["success"]
    text, ims = lm.asked[0]
    assert "POINT, THEN ACT" in text and "Table top surface" not in text and "WHITE GRID" not in text
    assert ims[0][1][:4] == b"\x89PNG" and len(ims) == 2
    rows = [json.loads(x) for x in open(tmp_path / "e0" / "labels.jsonl")]
    assert all(r["exec_kind"] == "model" for r in rows if r.get("answer"))
    assert all(json.loads(r["answer"])["command"]["mode"] in ("eef", "gripper", "stop", "edit") for r in rows if r.get("answer"))
    meta2, _ = _run(tmp_path, 3)
    assert meta2["n_fallback"] > 0
