"""L9 v2 production grasp cache: GraspGenX (GGX) candidates next to the analytic antipodal ones (grasp9).

Offline / privileged (L9_PRINCIPLES.md §2): the GGX request gets a cloud sampled from the object MESH, object frame.
Each GGX pose is converted base_link -> our TCP frame (tools/l9/graspgenx_client.base_to_tcp, verified 10-02) and
then re-seated on the mesh: the closing line through the GGX TCP (a few depths along the approach) is ray-cast on
the mesh, the entry/exit hits become the contacts c1/c2, the pose is centred between them (grasp9 convention:
T = frame_of(a, c) at the contact midpoint). The same support-clearance and swept-volume checks as
grasp9.sample_grasps then apply, so a GGX candidate is held to exactly the analytic candidates' rules; the sim
lift/shake test (tools/l9/grasp_test.py) runs on them unchanged.

Selection side (grasp9.select_ggx): `ggx_support` gives every candidate a GGX score -- its own confidence for a GGX
candidate, the best confidence of the GGX poses next to it for an analytic one (same contact-centre cell and
approach / closing axes within 25 deg), 0 when GGX proposed nothing there."""
from __future__ import annotations

import math

import numpy as np

from . import grasp9 as G

DEPTHS = (0.0, -0.01, 0.01, -0.02, 0.02)  # metres along the approach, tried in order
MAX_SHIFT = 0.02  # the contact midpoint may move at most this far from the GGX TCP along the closing axis
NEAR_M, NEAR_COS = 0.015, math.cos(math.radians(25.0))


def seat(V, F, grip: str, R_tcp: np.ndarray, t_tcp: np.ndarray, rng, pts=None, sz=None):
    """One GGX TCP pose (object frame) -> grasp9 candidate dict entry or None."""
    gr = G.gripper(grip)
    wmax = gr["max_open"] - G.OPEN_MARGIN
    a = -R_tcp[:, 2] / max(np.linalg.norm(R_tcp[:, 2]), 1e-9)
    if a[2] > G.BELOW_Z:
        return None
    c = R_tcp[:, 1] - a * float(R_tcp[:, 1] @ a)
    c = c / max(np.linalg.norm(c), 1e-9)
    s0 = wmax / 2 + 0.02
    for d in DEPTHS:
        o = t_tcp + a * d - c * s0
        ts = G.ray_hits(o[None], c[None], V, F)[0]
        ts = ts[ts <= 2 * s0]
        if len(ts) < 2:
            continue
        w = float(ts[1] - ts[0])
        if not (G.W_MIN <= w <= wmax) or ts[0] < 0.005 or abs((ts[0] + ts[1]) / 2 - s0) > MAX_SHIFT:
            continue
        if len(ts) > 2 and ts[2] - ts[1] < gr["finger_t"]:
            continue
        p, q = o + c * ts[0], o + c * ts[1]
        m = (p + q) / 2
        R = G.frame_of(a, c)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, m
        open_w = min(w + rng.uniform(*G.PRE_OPEN), gr["max_open"])
        if sz is not None and G._lowest(T, G.boxes(gr, open_w)) < sz + G.SUPPORT_CLEAR:
            return None
        if pts is not None and G.hits_boxes((pts - m) @ R, G.boxes(gr, max(open_w, w + 0.002), G.STANDOFF)):
            return None
        return {"T": T, "c1": p, "c2": q, "w": w, "a": a, "pre_open": open_w}
    return None


def candidates(V, F, grip: str, poses_tcp, scores, seed: int = 0) -> dict:
    """poses_tcp: [(R_tcp, t_tcp)] object frame, scores: GGX confidences -> grasp9-format dict (score = GGX conf)."""
    V, F = np.asarray(V, float), np.asarray(F, int)
    rng = np.random.default_rng(seed + 13)
    S, _, _ = G.sample_surface(V, F, 6000, np.random.default_rng(seed + 11))
    pts = G.downsample(np.concatenate([V, S]), 0.003)
    sz = float(V[:, 2].min())
    out = {k: [] for k in ("T", "c1", "c2", "w", "a", "pre_open", "score")}
    for (R, t), s in zip(poses_tcp, scores):
        e = seat(V, F, grip, np.asarray(R, float), np.asarray(t, float), rng, pts=pts, sz=sz)
        if e is None:
            continue
        for k in e:
            out[k].append(e[k])
        out["score"].append(float(s))
    K = len(out["w"])
    return {"T": np.asarray(out["T"]).reshape(K, 4, 4), "c1": np.asarray(out["c1"]).reshape(K, 3),
            "c2": np.asarray(out["c2"]).reshape(K, 3), "w": np.asarray(out["w"], float),
            "a": np.asarray(out["a"]).reshape(K, 3), "pre_open": np.asarray(out["pre_open"], float),
            "score": np.asarray(out["score"], float)}


def ggx_support(C: dict, Gx: dict) -> np.ndarray:
    """Per candidate of C (object frame): best GGX confidence among the GGX poses `Gx` in the same neighbourhood
    (contact midpoint within NEAR_M, approach and closing axes within 25 deg, closing axis sign-free); 0 if none."""
    K = len(C["w"])
    out = np.zeros(K)
    if K == 0 or not len(Gx.get("w", [])):
        return out
    m = (C["c1"] + C["c2"]) / 2
    mg = (Gx["c1"] + Gx["c2"]) / 2
    cc = (C["c2"] - C["c1"]) / np.maximum(C["w"], 1e-9)[:, None]
    cg = (Gx["c2"] - Gx["c1"]) / np.maximum(Gx["w"], 1e-9)[:, None]
    for i in range(K):
        near = (np.linalg.norm(mg - m[i], axis=1) < NEAR_M) & (Gx["a"] @ C["a"][i] > NEAR_COS) & \
               (np.abs(cg @ cc[i]) > NEAR_COS)
        if near.any():
            out[i] = float(Gx["score"][near].max())
    return out
