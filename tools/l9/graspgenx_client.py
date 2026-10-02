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

import os
import time
import uuid

import numpy as np

QUEUE = os.environ.get("GGX_QUEUE", "/data/harvest/l9v2/graspgenx/queue")


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
