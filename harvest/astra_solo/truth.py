"""'truth' reference for the Astra-solo interface: answers each call from simulator ground truth with one eef command to
the next point of the probe's truth plan (harvest/astra_motion/truth.py remaining_points: above the grasp point ->
grasp point + close -> carry height -> above the place -> place height + open), stop when done. It checks the whole
chain (prompt, schema, executor, episode) and gives the interface's ceiling. Never used as a result arm."""
from __future__ import annotations

import json

from ..astra_motion.truth import Rep, TruthModel

ASSESS = {"task_progress": {"verified_completed": [], "currently_attempting": "task", "remaining": []},
          "execution_status": "progressing", "evidence": "ground truth", "evidence_view": "both", "confidence": "high"}


class SoloTruth:
    name = "truth"

    def __init__(self, world):
        self.plan = TruthModel(world)

    def ask(self, text, images, meta):
        pts = self.plan.remaining_points()
        if not pts:
            cmd = {"mode": "stop"}
        else:
            p, g = pts[0]
            cmd = {"mode": "eef", "position_m": [float(v) for v in p], "gripper": g}
        return Rep(json.dumps({"assessment": ASSESS, "command": cmd, "reason": "truth"}))
