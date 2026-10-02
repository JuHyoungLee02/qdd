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
SNAP = (0.02, 0.015, 0.025, 0.01, 0.03, 0.035, 0.04, 0.005)  # TCP below the snapped surface entry, in order
MAX_SHIFT = 0.03  # the contact midpoint may move at most this far from the GGX TCP along the closing axis
NEAR_M, NEAR_COS = 0.015, math.cos(math.radians(25.0))


def pair(ts, s0: float, wmax: float, ft: float):
    """Contact pair on one closing line (hit distances ts from the open finger start): entry i / exit k with finger
    room on both outer sides (no surface within ft before i / after k), width in range, the start outside; the pair
    whose midpoint is nearest the GGX TCP (s0) -> (t_i, t_k) or a reject reason."""
    if len(ts) < 2:
        return "nohit"
    best, last = None, "width"
    for i in range(len(ts)):
        if ts[i] < 0.005 or (i > 0 and ts[i] - ts[i - 1] < ft):
            continue
        for k in range(i + 1, len(ts)):
            w = ts[k] - ts[i]
            if w > wmax:
                break
            if w < G.W_MIN or (k + 1 < len(ts) and ts[k + 1] - ts[k] < ft):
                continue
            d = abs((ts[i] + ts[k]) / 2 - s0)
            if d > MAX_SHIFT:
                last = "shift"
                continue
            if best is None or d < best[0]:
                best = (d, ts[i], ts[k])
    return last if best is None else (best[1], best[2])


def seat(V, F, grip: str, R_tcp: np.ndarray, t_tcp: np.ndarray, rng, pts=None, sz=None, why=None):
    """One GGX TCP pose (object frame) -> grasp9 candidate dict entry or None (`why`: Counter of reject reasons).
    TCP depths tried: GGX's own (DEPTHS around it), then snapped to the mesh along the approach (SNAP below the
    first surface the approach line through the GGX TCP enters) -- GGX's base->TCP depth is only verified for the
    AIW gripper, so every gripper also gets the surface-snapped depths (the G1 integration's ray-cast idea)."""
    gr = G.gripper(grip)
    wmax = gr["max_open"] - G.OPEN_MARGIN
    a = -R_tcp[:, 2] / max(np.linalg.norm(R_tcp[:, 2]), 1e-9)
    why = why if why is not None else {}
    if a[2] > G.BELOW_Z:
        why["below"] = why.get("below", 0) + 1
        return None
    c = R_tcp[:, 1] - a * float(R_tcp[:, 1] @ a)
    c = c / max(np.linalg.norm(c), 1e-9)
    s0 = wmax / 2 + 0.02
    tops = [t_tcp + a * d for d in DEPTHS]
    h = G.ray_hits((t_tcp - a * 0.4)[None], a[None], V, F)[0]
    if len(h):
        e = t_tcp - a * 0.4 + a * float(h[0])
        tops += [e + a * d for d in SNAP]
    last = "nohit"
    for tc in tops:
        o = tc - c * s0
        ts = G.ray_hits(o[None], c[None], V, F)[0]
        ts = ts[ts <= 2 * s0]
        pr = pair(ts, s0, wmax, gr["finger_t"])
        if isinstance(pr, str):
            last = pr
            continue
        t0_, t1_ = pr
        w = float(t1_ - t0_)
        p, q = o + c * t0_, o + c * t1_
        m = (p + q) / 2
        R = G.frame_of(a, c)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, m
        open_w = min(w + rng.uniform(*G.PRE_OPEN), gr["max_open"])
        if sz is not None and G._lowest(T, G.boxes(gr, open_w)) < sz + G.SUPPORT_CLEAR:
            last = "support"
            continue
        if pts is not None and G.hits_boxes((pts - m) @ R, G.boxes(gr, max(open_w, w + 0.002), G.STANDOFF)):
            last = "collision"
            continue
        why["ok"] = why.get("ok", 0) + 1
        return {"T": T, "c1": p, "c2": q, "w": w, "a": a, "pre_open": open_w}
    why[last] = why.get(last, 0) + 1
    return None


def candidates(V, F, grip: str, poses_tcp, scores, seed: int = 0, why=None) -> dict:
    """poses_tcp: [(R_tcp, t_tcp)] object frame, scores: GGX confidences -> grasp9-format dict (score = GGX conf)."""
    V, F = np.asarray(V, float), np.asarray(F, int)
    rng = np.random.default_rng(seed + 13)
    S, _, _ = G.sample_surface(V, F, 6000, np.random.default_rng(seed + 11))
    pts = G.downsample(np.concatenate([V, S]), 0.003)
    sz = float(V[:, 2].min())
    out = {k: [] for k in ("T", "c1", "c2", "w", "a", "pre_open", "score")}
    for (R, t), s in zip(poses_tcp, scores):
        e = seat(V, F, grip, np.asarray(R, float), np.asarray(t, float), rng, pts=pts, sz=sz, why=why)
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
