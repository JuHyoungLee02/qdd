"""Pure client for the shared GraspGenX file-queue server (``graspgenx_serve.py`` on
fe08 GPU 1/4/5). No torch/graspgenx import here -- safe to import from inside the Isaac
process (GPU0) or any other consumer. Talks over a shared filesystem queue directory
(both processes must see the same path, e.g. both running on pod fe08 under /data).

Usage:
    from tools.l9.graspgenx_client import request_grasps
    grasps, scores, status = request_grasps(points_Nx3, gripper="ffw_sg2_right",
                                             num_grasps=64, timeout_s=30.0)

``points`` should be object-centered (mean-subtracted) or in whatever frame the caller
wants grasp poses returned in -- the server does not know about object pose, it only
samples grasps in the frame of the points it is given. The caller re-applies the
object's world pose to the returned 4x4 grasp poses itself.
"""
from __future__ import annotations

import math
import os
import time
import uuid

import numpy as np

QUEUE = os.environ.get("GGX_QUEUE", "/data/harvest/l9v2/graspgenx/queue")

# ours (x,y,z) -> graspgenx (y,x,-z); P@P == I (verified: applying the permutation twice
# is the identity), P is orthogonal (det=+1), so P is its own inverse AND its own transpose.
P_TO_GRASPGENX = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0]])


def _rpy_to_matrix(rpy):
    """Extrinsic X-Y-Z Euler (URDF <origin rpy="r p y"> convention)."""
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = (
        math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y),
    )
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def base_to_tcp(R_ggx, t_ggx, tcp_in_base_xyz, tcp_in_base_rpy=(0.0, 0.0, 0.0)):
    """A GraspGenX grasp pose (R_ggx, t_ggx) is for the gripper's BASE_LINK origin, in
    GraspGenX's own axis convention (ours (x,y,z) permuted to graspgenx (y,x,-z)) -- NOT
    the TCP/pad-contact pose our own planning stack (rt9.Runtime.choose() etc) expects.
    Verified 2026-10-02 against the live server (ffw_sg2_right, synthetic 6cm cube):
    raw base_link origin sat 21.0cm from the object center; after this correction, 4.3cm
    (cube half-size 3.0cm) with approach-axis alignment dot=0.989.

    tcp_in_base_xyz/rpy: from the gripper's own assets9/grippers/<name>.json "tcp_in_base".
    Returns (R_tcp_world, t_tcp_world)."""
    R_base_world = R_ggx @ P_TO_GRASPGENX  # P is self-inverse, so this undoes our axis permutation
    t_base_world = t_ggx  # P only permutes axes about the origin -- translation is unaffected
    R_tcp_in_base = _rpy_to_matrix(tuple(tcp_in_base_rpy))
    R_tcp_world = R_base_world @ R_tcp_in_base
    t_tcp_world = R_base_world @ np.asarray(tcp_in_base_xyz, dtype=float) + t_base_world
    return R_tcp_world, t_tcp_world


def request_grasps(
    points: np.ndarray,
    gripper: str,
    num_grasps: int = 200,
    threshold: float = -1.0,
    collision_boxes=None,  # list of (center_xyz, size_xyz), same frame as `points`
    timeout_s: float = 60.0,
    poll_s: float = 0.2,
):
    """Returns (grasps (M,4,4) float32, scores (M,) float32, status str).
    On timeout or a server-side error, returns (empty, empty, status_message) --
    callers must check `status == "ok"` before trusting a non-empty result and must
    also handle the ok-but-zero-candidates case (status == "ok", M == 0)."""
    os.makedirs(QUEUE, exist_ok=True)
    rid = uuid.uuid4().hex
    req_path = os.path.join(QUEUE, f"req_{rid}.npz")
    tmp_path = req_path + ".tmp"
    kw = dict(
        points=np.asarray(points, dtype=np.float32),
        gripper=np.frombuffer(gripper.encode("utf-8").ljust(64, b"\x00"), dtype=np.uint8),
        num_grasps=np.int64(num_grasps),
        threshold=np.float32(threshold),
    )
    if collision_boxes:
        kw["collision_boxes_center"] = np.asarray(
            [c for c, _ in collision_boxes], dtype=np.float32
        )
        kw["collision_boxes_size"] = np.asarray(
            [s for _, s in collision_boxes], dtype=np.float32
        )
    # np.savez(path, ...) auto-appends ".npz" unless path already ends with it -- since
    # tmp_path ends in ".npz.tmp", pass an open file handle instead to avoid that.
    with open(tmp_path, "wb") as f:
        np.savez(f, **kw)
    os.replace(tmp_path, req_path)

    resp_path = os.path.join(QUEUE, f"resp_{rid}.npz")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if os.path.exists(resp_path):
            try:
                d = np.load(resp_path, allow_pickle=False)
                grasps = d["grasps"]
                scores = d["scores"]
                status = str(d["status"])
            finally:
                try:
                    os.remove(resp_path)
                except OSError:
                    pass
            return grasps, scores, status
        time.sleep(poll_s)
    return (
        np.zeros((0, 4, 4), np.float32),
        np.zeros((0,), np.float32),
        f"timeout after {timeout_s}s (request {rid} never answered)",
    )
