"""L8-X truth labels: teach_l8.labels with support-aware heights (docs/research/l8x_env_suite_design_2026-09-27.md
§2). The task info may carry
  sup_tgt    world z of the surface the target stood on when picked (table, or the stand's top)
  sup_place  world z of the surface the place object stands on (table)
  place_top  world z where the held object's bottom goes (tray top, stand top, bin floor, table for spots)
and the plan uses them instead of the single table height:
  grasp z  = sup_tgt + h - 1.8 cm;  approach = + 10 cm;  low / lift-clear test = sup_tgt + h + 3 cm
  carry z  = max(sup_tgt, sup_place) + 22 cm;  put = place_top + (TCP - bottom) + 4 mm.
Without those keys every value equals teach_l8.labels (one table): label() here == labels.label() byte for byte
(tests). Pure."""
from __future__ import annotations

import json

import numpy as np

from ..astra_motion.harness import GRASP_BELOW_TOP_M, obj_height
from ..astra_motion.prompts import OBJ_NAME
from ..teach_l8 import labels as L


def heights(info: dict, table_z: float) -> dict:
    tz_t = float(info.get("sup_tgt", table_z))
    tz_p = float(info.get("sup_place", table_z))
    top = float(info["place_top"]) if "place_top" in info else L.place_top(info["place"], table_z)
    return {"sup_tgt": tz_t, "carry_base": max(tz_t, tz_p), "place_top": top}


def plan(st: dict, info: dict, table_z: float, w_open: float):
    tg, pl = info["tgt"], info["place"]
    H = heights(info, table_z)
    pred = st["pred"]
    tcp = np.asarray(st["tcp"], float)
    c, p = np.asarray(st["obj"][tg], float), np.asarray(st["obj"][pl], float)
    if info.get("place_xy_offset"):  # multi-step: a shared place (bin) gets side-by-side spots
        p = p + np.array([*info["place_xy_offset"], 0.0], float)
    h = obj_height(tg)
    hold = pred.get(f"holding({tg})") is True
    zc = H["carry_base"] + L.CARRY_DZ
    if pred.get(f"on({tg},{pl})") is True and not hold:
        top = c[2] + h / 2
        if tcp[2] < top + L.RETREAT_ABOVE and np.linalg.norm(tcp[:2] - c[:2]) < L.RETREAT_XY:
            return "retreat", {"mode": "eef", "position_m": L._r([tcp[0], tcp[1], tcp[2] + L.ABOVE_DZ]),
                               "gripper": "keep"}
        return "done", {"mode": "stop"}
    if not hold and pred.get(f"upright({tg})") is False:
        return "tipped", None
    if hold:
        put = np.array([p[0], p[1], H["place_top"] + (tcp[2] - (c[2] - h / 2)) + L.PLACE_CLEAR])
        if np.linalg.norm(tcp[:2] - p[:2]) < L.NEAR_XY:
            return "lower_open", {"mode": "eef", "position_m": L._r(put), "gripper": "open"}
        if tcp[2] >= zc - L.NEAR_XY:
            return "carry_over", {"mode": "eef", "position_m": L._r([p[0], p[1], zc]), "gripper": "keep"}
        return "carry_up", {"mode": "eef", "position_m": L._r([tcp[0], tcp[1], zc]), "gripper": "keep"}
    if float(st["grip_w"]) < w_open - L.OPEN_TOL:
        return "reopen", {"mode": "gripper", "gripper": "open"}
    g = np.array([c[0], c[1], H["sup_tgt"] + h - GRASP_BELOW_TOP_M])
    above = g + [0.0, 0.0, L.ABOVE_DZ]
    dxy = float(np.linalg.norm(tcp[:2] - g[:2]))
    if dxy < L.NEAR_XY and tcp[2] <= above[2] + L.NEAR_XY:
        return "descend_close", {"mode": "eef", "position_m": L._r(g), "gripper": "close"}
    if tcp[2] < H["sup_tgt"] + h + L.LOW_MARGIN:
        return "lift_clear", {"mode": "eef", "position_m": L._r([tcp[0], tcp[1], above[2]]), "gripper": "keep"}
    return "above_target", {"mode": "eef", "position_m": L._r(above), "gripper": "keep"}


def label(st: dict, info: dict, table_z: float, w_open: float, first: bool, last_line: str = "",
          prev_failed: bool = False):
    """= teach_l8.labels.label with the support-aware plan."""
    step, cmd = plan(st, info, table_z, w_open)
    if cmd is None:
        return None
    tn, pn = OBJ_NAME.get(info["tgt"], info["tgt"]), OBJ_NAME.get(info["place"], info["place"])
    doing, remaining, done = L._texts(step, tn, pn)
    status = L.status_of(step, first, last_line, prev_failed)
    ans = {"assessment": {"task_progress": {"verified_completed": done, "currently_attempting": doing,
                                            "remaining": remaining},
                          "execution_status": status, "evidence": L.evidence_of(step, st, tn, last_line),
                          "evidence_view": "both", "confidence": "high"},
           "command": cmd, "reason": f"Next: {doing}."}
    return {"step": step, "phase": L.phase_of(step), "command": cmd, "status": status, "answer": json.dumps(ans)}


def x_info(env, info: dict) -> dict:
    """The support heights of an L8-X scene from the env layout (scene.base_z / SUPPORT_TOP); unchanged info for a
    one-table task (no extra keys -> the L8 plan)."""
    from ..sim.scene import OBJ_GEOM, SUPPORT_TOP, X_VISUAL_ONLY, base_z
    from ..sim.tasks import X_TASKS
    if env.task not in X_TASKS:
        return info
    tz, lay = float(env.table_top_z), env.layout
    tg, pl = info["tgt"], info["place"]
    sp = base_z(pl, lay, tz)
    if pl in X_VISUAL_ONLY:
        top = sp
    else:
        top = sp + SUPPORT_TOP.get(pl, 2 * OBJ_GEOM[pl]["half_extents"][2])
    return dict(info, sup_tgt=base_z(tg, lay, tz), sup_place=sp, place_top=top)
