"""E-TEACH-L8 offline metrics (prereg §4): per control sample
  valid           the runtime validator (astra_solo.schema.validate) accepts the reply (no repair call offline);
  action_ok       the gripper action (keep / open / close / stop; gripper mode = its value) equals the label's;
  approach_xy_mm  approach samples whose label goes to the target (steps above_target / descend_close): xy distance
                  of the reply's commanded TCP goal (eef = position_m, edit = executor base + delta) to the target
                  centre -- the same quantity as the pilot / proxy 'approach target xy error'; None when the reply is
                  not a move (then approach_move is False);
  carry_xy_mm     carry samples (steps carry_over / lower_open): goal xy to the place centre;
  goal_err_mm     3-D distance of the reply goal to the label goal (both moves).
Executor base of an edit = the commanded target when within 3 cm of the TCP, else the TCP (astra_solo.executor)."""
from __future__ import annotations

import json

import numpy as np

from ..astra_motion.schema import SchemaError, extract_json
from ..astra_solo import schema as SC

APPROACH_STEPS = ("above_target", "descend_close")
CARRY_STEPS = ("carry_over", "lower_open")


def action_of(cmd: dict) -> str:
    m = cmd.get("mode")
    if m == "stop":
        return "stop"
    return cmd.get("gripper") or "keep"


def goal_of(cmd: dict, ex_target, tcp):
    if cmd.get("mode") == "eef" and cmd.get("position_m") is not None:
        return np.asarray(cmd["position_m"], float)
    if cmd.get("mode") == "edit" and cmd.get("delta_m") is not None:
        t, p = np.asarray(ex_target, float), np.asarray(tcp, float)
        base = t if np.linalg.norm(t - p) <= 0.03 else p
        return base + np.asarray(cmd["delta_m"], float)
    return None


def score(row: dict, reply: str) -> dict:
    lab = json.loads(row["answer"])["command"]
    parsed, _ = SC.validate(reply or "")
    out = {"valid": parsed is not None, "action_ok": False, "approach_xy_mm": None, "approach_move": False,
           "carry_xy_mm": None, "goal_err_mm": None, "approach_row": row["step"] in APPROACH_STEPS,
           "label_action": action_of(lab), "pred_action": None, "pred_mode": None}
    if parsed is None:
        return out
    cmd = parsed["command"]
    out["pred_action"], out["pred_mode"] = action_of(cmd), cmd["mode"]
    out["action_ok"] = out["pred_action"] == out["label_action"]
    g = goal_of(cmd, row["ex_target"], row["gt"]["tcp"])
    if g is None:
        return out
    if row["step"] in APPROACH_STEPS:
        out["approach_move"] = True
        out["approach_xy_mm"] = round(float(np.linalg.norm(g[:2] - np.asarray(row["gt"]["tgt"][:2]))) * 1e3, 1)
    if row["step"] in CARRY_STEPS:
        out["carry_xy_mm"] = round(float(np.linalg.norm(g[:2] - np.asarray(row["gt"]["place"][:2]))) * 1e3, 1)
    if "position_m" in lab:
        out["goal_err_mm"] = round(float(np.linalg.norm(g - np.asarray(lab["position_m"], float))) * 1e3, 1)
    return out


def _q(v, q):
    return round(float(np.percentile(v, q)), 1) if v else None


def summarize(scores: list) -> dict:
    n = len(scores)
    ap = [s for s in scores if s.get("approach_row")]
    xy = [s["approach_xy_mm"] for s in ap if s["approach_xy_mm"] is not None]
    cx = [s["carry_xy_mm"] for s in scores if s["carry_xy_mm"] is not None]
    by_ep: dict = {}
    for s in ap:
        if s["approach_xy_mm"] is not None:
            by_ep.setdefault(s.get("episode"), []).append(s["approach_xy_mm"])
    ep_med = [float(np.median(v)) for v in by_ep.values()]
    return {"n": n, "valid_rate": round(sum(s["valid"] for s in scores) / n, 4) if n else None,
            "action_acc": round(sum(s["action_ok"] for s in scores) / n, 4) if n else None,
            "n_approach": len(ap), "approach_move_share": round(len(xy) / len(ap), 4) if ap else None,
            "approach_xy_median_mm": _q(xy, 50), "approach_xy_p90_mm": _q(xy, 90),
            "approach_xy_le20_share": round(sum(v <= 20 for v in xy) / len(xy), 4) if xy else None,
            "approach_episode_median_of_medians_mm": _q(ep_med, 50), "n_episodes": len(ep_med),
            "carry_xy_median_mm": _q(cx, 50), "carry_xy_p90_mm": _q(cx, 90), "n_carry": len(cx)}


def aux_score(row: dict, reply: str):
    try:
        d = extract_json(reply or "")
        p = d.get("xy")
        if not (isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p)):
            return None
    except (SchemaError, AttributeError):
        return None
    t = json.loads(row["answer"])["xy"]
    return round(float(np.hypot(p[0] - t[0], p[1] - t[1])) * 1e3, 1)
