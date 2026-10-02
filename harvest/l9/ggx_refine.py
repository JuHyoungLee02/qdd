"""live9.refine() hook, backed by the shared GraspGenX batch server (tools/l9/graspgenx_client.py; server on
juhyoung-q-fe08 GPU1/4/5 shared with the G1 Dex3-1 integration, rt9._load_ggx). GraspGenX weights: NVIDIA Open
Model License, internal use, licence cleared 2026-10-02.

Conversion pipeline (mirrors the G1 mesh integration's verified base_link -> TCP correction, tools/l9/
graspgenx_client.base_to_tcp + graspgenx_gripper_cfg's P_TO_GRASPGENX permutation): the observed cloud is sent
object-centred (mean-subtracted around the commanded point, graspgenx_client's own convention), each returned pose
is converted base_link -> our TCP frame, then its translation is corrected by ray-casting the verified approach
axis onto the OBSERVED CLOUD itself (we have no mesh here, unlike the G1 integration -- same idea: no hardcoded
offset, snap to whatever surface is actually seen along that axis).

live9.choose_live does NOT trust this blindly: every candidate this module returns is re-validated (approach
family, rot_img window, support clearance, collision) by the same check the antipodal path applies to its own
candidates -- see live9.sample_grasps_cloud's filters, reused here via `filter_candidates`."""
from __future__ import annotations

import json
import os

import numpy as np

from . import grasp9 as G

NUM_GRASPS = 64
TIMEOUT_S = 20.0
STANDOFF_PROBE = 0.12  # ray-cast origin: this far back along the approach from the raw GraspGenX pose


def gripper_asset(grip: str, arm: str) -> str:
    """The arm-specific asset (e.g. 'ffw_sg2_left') when it exists, else grasp9.JSON_NAME's single default
    (franka_hand has no left/right variant)."""
    cand = f"{grip}_{arm}"
    if os.path.exists(os.path.join(G.DIR, cand + ".json")):
        return cand
    return G.JSON_NAME.get(grip, grip)


def _tcp_in_base(name: str) -> tuple:
    p = os.path.join(G.DIR, name + ".json")
    j = json.load(open(p, encoding="utf-8"))
    t = j.get("tcp_in_base", {})
    return tuple(t.get("xyz", (0.0, 0.0, 0.0))), tuple(t.get("rpy", (0.0, 0.0, 0.0)))


def _nearest_on_cloud(P: np.ndarray, origin: np.ndarray, direction: np.ndarray, max_t: float = 0.2, tol: float = 0.03):
    """Nearest cloud point to the ray (origin + t*direction, 0 < t <= max_t) within `tol` of the ray -- the
    ray-cast-onto-the-observed-surface correction (G1's mesh version used the object's own mesh; there is none
    here, so the cloud itself stands in). None when nothing in the cloud lies near that ray."""
    if len(P) == 0:
        return None
    rel = P - origin
    t = rel @ direction
    lat = np.linalg.norm(rel - t[:, None] * direction, axis=1)
    m = (t > 0) & (t <= max_t) & (lat < tol)
    if not m.any():
        return None
    i = np.argmin(np.where(m, lat, np.inf))
    return P[i]


def make_refiner(arm: str, num_grasps: int = NUM_GRASPS, timeout_s: float = TIMEOUT_S):
    """A live9.set_refiner-compatible callable bound to `arm` (the refine() hook signature carries no arm
    parameter; the caller -- rtlive9.LiveRuntime -- knows its own arm and binds it here at install time)."""
    def refine(cloud: np.ndarray, point3d, approach: str, rot: int, gripper: str):
        from tools.l9.graspgenx_client import base_to_tcp, request_grasps
        if len(cloud) < 10:
            return None
        name = gripper_asset(gripper, arm)
        xyz, rpy = _tcp_in_base(name)
        centre = np.asarray(point3d, float)
        pts = (np.asarray(cloud, float) - centre).astype(np.float32)
        grasps, scores, status = request_grasps(pts, gripper=name, num_grasps=num_grasps, timeout_s=timeout_s)
        if status != "ok" or not len(grasps):
            return None
        gr = G.gripper(gripper)
        T_l, c1, c2, w_l, a_l, pre, sc = [], [], [], [], [], [], []
        for Tg, s in zip(grasps, scores):
            R_ggx, t_ggx = np.asarray(Tg[:3, :3], float), np.asarray(Tg[:3, 3], float)
            R_tcp, t_tcp = base_to_tcp(R_ggx, t_ggx, xyz, rpy)
            t_world = t_tcp + centre
            a = -R_tcp[:, 2] / max(np.linalg.norm(R_tcp[:, 2]), 1e-9)
            surf = _nearest_on_cloud(np.asarray(cloud, float), t_world - a * STANDOFF_PROBE, a)
            m = surf if surf is not None else t_world
            c = R_tcp[:, 1] / max(np.linalg.norm(R_tcp[:, 1]), 1e-9)
            T = np.eye(4)
            T[:3, :3], T[:3, 3] = R_tcp, m
            T_l.append(T)
            c1.append(m - 0.02 * c)
            c2.append(m + 0.02 * c)
            w_l.append(0.04)
            a_l.append(a)
            pre.append(min(gr["max_open"], 0.06))
            sc.append(float(s))
        K = len(T_l)
        return {"T": np.asarray(T_l).reshape(K, 4, 4), "c1": np.asarray(c1).reshape(K, 3),
                "c2": np.asarray(c2).reshape(K, 3), "w": np.asarray(w_l), "a": np.asarray(a_l).reshape(K, 3),
                "score": np.asarray(sc), "pre_open": np.asarray(pre), "gripper": gr,
                "source": np.array(["graspgenx"] * K)}
    return refine
