"""Monitor.summary: an earlier step's target (carried on purpose) is never "knocked" (R1 2-step bug, 10-03)."""
import numpy as np

from harvest.astra_motion.harness import Monitor


class _W:
    table_z = 0.8

    def __init__(self, obj):
        self.obj = obj

    def status(self):
        return {"obj": self.obj, "pred": {}, "t": 0.0}


def test_earlier_target_not_knocked():
    w = _W({"a": [0.5, 0.0, 0.8], "b": [0.5, 0.2, 0.8], "c": [0.6, 0.1, 0.8]})
    m = Monitor(w, {"tgt": "a", "place": "p"})
    m.done_tgts.add("a")
    m.tgt = "b"  # step 2 (multistep._check)
    m.last = {"obj": {"a": [0.3, 0.0, 0.8], "b": [0.3, 0.2, 0.8], "c": [0.7, 0.1, 0.8]}}
    s = m.summary()
    assert s["knocked"] == ["c"] and "a" not in s["moved_mm"]
