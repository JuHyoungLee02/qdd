"""E-PT offline metrics (prereg_pt.md §4), one scorer for every arm: the reply is validated with the arm's runtime
schema, its command is turned into the TCP goal exactly as the runtime would (xyz: eef position / edit from the
executor base; pt: resolve.py on the saved head depth + camera with the saved robot state; nd-pt: nd.resolve_est
with the reply's own table_z), then compared with the simulator:
  approach_xy_mm   steps above_target / descend_close: goal xy - target centre (= L8's metric)
  carry_xy_mm      steps carry_over / lower_open: goal xy - place centre
  grasp_z_mm       step descend_close: goal z - label goal z (signed; the grasp height -- what a wrong table
                   height breaks)
  approach_3d_mm   steps above_target / descend_close: |goal - label goal| (label = the L8 xyz truth)
  action_ok        gripper action (keep / open / close / stop) = the label's
  point_px         pt / nd-pt, point rows whose label is a point: pixel distance of the reply's point to the label's
                   (px of the 672x376 image)
  est_*            nd-est / nd-pt: |estimate - truth| for table_z (mm), target base xy (mm), target height (mm)."""
from __future__ import annotations

import json

import numpy as np

from ..teach_l8 import metrics as LM

APPROACH_STEPS = LM.APPROACH_STEPS
CARRY_STEPS = LM.CARRY_STEPS


def validate(reply: str, arm: str):
    if arm in ("xyz",):
        from ..astra_solo import schema as SC
        return SC.validate(reply or "")
    if arm == "pt":
        from ..astra_solo import pt_schema as PS
        return PS.validate(reply or "")
    from ..astra_solo import nd as ND
    return ND.validate(reply or "", f"{arm}@v1")


def _cam_depth(row):
    from ..astra_motion.geometry import Cam
    cam = Cam.from_json(json.load(open(row["cams_path"]))["head"])
    depth = np.load(row["depth_path"])["depth"] if row.get("depth_path") else None
    return cam, depth


def goal_of(row: dict, parsed: dict, arm: str, cache: dict | None = None):
    cmd = parsed["command"]
    if cmd["mode"] in ("eef", "edit"):
        g = LM.goal_of(cmd, row["ex_target"], row["gt"]["tcp"])
        return None if g is None else np.asarray(g, float)
    if cmd["mode"] != "point":
        return None
    from ..astra_solo import resolve as RS
    s = row["pt_state"]
    cam, depth = (cache or {}).get("cd") or _cam_depth(row)
    if arm == "pt":
        plane, res = s["plane"], None
        if cmd["height"] != "lift":
            res = RS.resolve_point(cam, depth, s["plane"], cmd["point_2d"], tcp=row["gt"]["tcp"])
            if res["kind"] == "none":
                return None
            plane = res["plane"]
        g, _ = RS.target_of(cmd["height"], res, plane, row["gt"]["tcp"], s["holding"], s["grip_offset"])
        return np.asarray(g, float)
    from ..astra_solo import nd as ND
    est_t = (parsed.get("estimates") or {}).get("table_z", s["plane"])
    g, _ = ND.resolve_est(cam, cmd, est_t, row["gt"]["tcp"], s["holding"], s["grip_offset"])
    return None if g is None else np.asarray(g, float)


def score(row: dict, reply: str, arm: str) -> dict:
    lab_all = json.loads(row["answer"])
    lab = lab_all["command"]
    xyz_lab = json.loads(row["xyz_answer"])["command"] if row.get("xyz_answer") else lab
    parsed, _ = validate(reply, arm)
    out = {"valid": parsed is not None, "action_ok": False, "approach_xy_mm": None, "approach_move": False,
           "carry_xy_mm": None, "grasp_z_mm": None, "approach_3d_mm": None, "point_px": None,
           "approach_row": row["step"] in APPROACH_STEPS, "label_action": LM.action_of(lab), "pred_mode": None}
    if parsed is None:
        return out
    cmd = parsed["command"]
    out["pred_mode"] = cmd["mode"]
    out["action_ok"] = LM.action_of(cmd) == out["label_action"]
    if cmd.get("point_2d") is not None and lab.get("point_2d") is not None:
        cam, _ = _cam_depth(dict(row, depth_path=None))
        dx = (cmd["point_2d"][0] - lab["point_2d"][0]) / 1000 * cam.W
        dy = (cmd["point_2d"][1] - lab["point_2d"][1]) / 1000 * cam.H
        out["point_px"] = round(float(np.hypot(dx, dy)), 1)
    est, est_l = parsed.get("estimates"), lab_all.get("estimates")
    if est and est_l:
        out["est_table_mm"] = round(abs(est["table_z"] - est_l["table_z"]) * 1e3, 1)
        out["est_tgt_xy_mm"] = round(float(np.hypot(*np.subtract(est["target_base_xy"], est_l["target_base_xy"])))
                                     * 1e3, 1)
        out["est_tgt_h_mm"] = round(abs(est["target_height_m"] - est_l["target_height_m"]) * 1e3, 1)
    try:
        g = goal_of(row, parsed, arm)
    except Exception as e:  # noqa: BLE001 - a scorer failure is recorded, never silently a miss
        out["goal_error"] = f"{type(e).__name__}: {e}"[:200]
        g = None
    if g is None:
        return out
    if row["step"] in APPROACH_STEPS:
        out["approach_move"] = True
        out["approach_xy_mm"] = round(float(np.linalg.norm(g[:2] - np.asarray(row["gt"]["tgt"][:2]))) * 1e3, 1)
        if "position_m" in xyz_lab:
            out["approach_3d_mm"] = round(float(np.linalg.norm(g - np.asarray(xyz_lab["position_m"]))) * 1e3, 1)
            if row["step"] == "descend_close":
                out["grasp_z_mm"] = round(float(g[2] - xyz_lab["position_m"][2]) * 1e3, 1)
    if row["step"] in CARRY_STEPS:
        out["carry_xy_mm"] = round(float(np.linalg.norm(g[:2] - np.asarray(row["gt"]["place"][:2]))) * 1e3, 1)
    return out


def _q(v, q):
    return round(float(np.percentile(v, q)), 1) if v else None


def summarize(sc: list) -> dict:
    base = LM.summarize(sc)
    gz = [s["grasp_z_mm"] for s in sc if s.get("grasp_z_mm") is not None]
    a3 = [s["approach_3d_mm"] for s in sc if s.get("approach_3d_mm") is not None]
    px = [s["point_px"] for s in sc if s.get("point_px") is not None]
    base.update({"grasp_z_median_mm": _q(gz, 50), "grasp_absz_median_mm": _q([abs(v) for v in gz], 50),
                 "grasp_absz_le15_share": round(sum(abs(v) <= 15 for v in gz) / len(gz), 4) if gz else None,
                 "n_grasp": len(gz), "approach_3d_median_mm": _q(a3, 50), "approach_3d_p90_mm": _q(a3, 90),
                 "point_px_median": _q(px, 50), "point_px_p90": _q(px, 90), "n_point": len(px),
                 "n_goal_error": sum(1 for s in sc if s.get("goal_error"))})
    for k in ("est_table_mm", "est_tgt_xy_mm", "est_tgt_h_mm"):
        v = [s[k] for s in sc if s.get(k) is not None]
        base[k + "_median"] = _q(v, 50)
    return base


def aux_score(row: dict, reply: str):
    """pt aux: pixel distance (px); xy aux: L8's metric (mm)."""
    from ..astra_motion.schema import SchemaError, extract_json
    t = json.loads(row["answer"])
    if "xy" in t:
        return LM.aux_score(row, reply)
    try:
        p = extract_json(reply or "").get("point_2d")
    except (SchemaError, AttributeError):
        return None
    if not (isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p)):
        return None
    return round(float(np.hypot((p[0] - t["point_2d"][0]) * 0.672, (p[1] - t["point_2d"][1]) * 0.376)), 1)
