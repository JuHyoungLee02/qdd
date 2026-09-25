"""'truth' reference model: answers the S command interface from the simulator's ground truth (object poses, holding
state). It shows what this executor + command interface can do with perfect decisions and checks the whole chain
(sync S, staggered F0 / F1, smooth executor) before paid calls. World needs status(), task_info(), w_open.

Plan (as TCP points): 10 cm above the oracle grasp point -> grasp point (target top - 1.8 cm, = planner
GRASP_BELOW_TOP_M) + close -> table + 22 cm -> above the place centre -> place height (target bottom 4 mm above the
place top) + open. Each answer = an edit toward the next point (<= 5 cm), with the point's gripper action when this
edit reaches it; stop once the target rests released on the place object. F1: keep while the committed command already
points the same way, else revise."""
from __future__ import annotations

import json

import numpy as np

from .harness import GRASP_BELOW_TOP_M, obj_height, same_command

CARRY_DZ = 0.22
TP = {"verified_completed": [], "currently_attempting": "task", "remaining": ["grasp", "place"]}
ASSESS = {"task_progress": TP, "current_subgoal": "task", "execution_status": "progressing",
          "execution_evidence": "ground truth", "intent_status": "aligned", "intent_evidence": "ground truth",
          "confidence": "high"}


class Rep:
    def __init__(self, text):
        self.text, self.usage, self.latency_s, self.first_token_s = text, {}, 0.0, 0.0
        self.error, self.model_field, self.cost_usd = None, "truth", 0.0


class TruthModel:
    name = "truth"

    def __init__(self, world, mode=None):
        self.w, self.mode = world, mode

    def _geo(self):
        st, info = self.w.status(), self.w.task_info()
        tg, pl = info["tgt"], info["place"]
        c, p = np.asarray(st["obj"][tg], float), np.asarray(st["obj"][pl], float)
        tz = self.w.table_z
        h = obj_height(tg)
        place_top = tz + (obj_height(pl) if pl != "o11" else 0.0)
        return st, info, c, p, tz, h, place_top

    def remaining_points(self):
        """[(point, gripper)] still to do, from the current state; [] = done (stop)."""
        st, info, c, p, tz, h, place_top = self._geo()
        tg, pl = info["tgt"], info["place"]
        tcp = np.asarray(st["tcp"], float)
        pred = st["pred"]
        if pred.get(f"on({tg},{pl})") is True and pred.get(f"holding({tg})") is False:
            return []
        if pred.get(f"holding({tg})") is True or st["grip_w"] < self.w.w_open - 0.005:
            put = np.array([p[0], p[1], place_top + (tcp[2] - (c[2] - h / 2)) + 0.004])
            pts = [(np.array([tcp[0], tcp[1], tz + CARRY_DZ]), "keep"), (np.array([p[0], p[1], tz + CARRY_DZ]), "keep"),
                   (put, "open")]
            if np.linalg.norm(tcp[:2] - p[:2]) < 0.015:
                return pts[2:]
            if tcp[2] >= tz + CARRY_DZ - 0.015:
                return pts[1:]
            return pts
        g = np.array([c[0], c[1], tz + h - GRASP_BELOW_TOP_M])
        above = g + [0, 0, 0.10]
        if np.linalg.norm(tcp[:2] - g[:2]) < 0.015 and tcp[2] <= above[2] + 0.015:
            return [(g, "close")]
        return [(above, "keep"), (g, "close")]

    def command(self) -> dict:
        pts = self.remaining_points()
        if not pts:
            return {"decision": "stop"}
        tcp = np.asarray(self.w.status()["tcp"], float)
        p, g = pts[0]
        d = p - tcp
        n = float(np.linalg.norm(d))
        if n > 0.05:
            d, g = d * (0.05 / n), "keep"
        return {"decision": "edit", "edit": {"delta_position_cm": [float(v) for v in d * 100],
                                             "delta_rotation_rad": [0.0, 0.0, 0.0], "gripper": g}}

    def ask(self, text, images, meta):
        c = self.command()
        if meta.get("kind") == "st" and meta.get("style") == "F1":
            com = meta.get("committed")
            if com is not None and c["decision"] == "edit" and same_command(com, c):
                return Rep(json.dumps({"assessment": ASSESS, "decision": "keep", "evidence": "ground truth"}))
            return Rep(json.dumps({"assessment": ASSESS, "decision": "revise", "command": c,
                                   "evidence": "ground truth"}))
        return Rep(json.dumps({"assessment": ASSESS, **c, "reason": "truth"}))
