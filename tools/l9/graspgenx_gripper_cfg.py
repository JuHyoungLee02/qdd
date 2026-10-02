"""Generic converter: our ``harvest/l9/assets9/grippers/<name>.json`` TCP-frame finger
boxes -> GraspGenX's ``SweepVolumeParams`` (base-link frame, +Z=approach, +X=closing axis).

Pure, no torch/graspgenx import -- safe to run on the laptop or the pod. Used by the
GraspGenX batch wrapper (``tools/l9/graspgenx_gripper_cfg.py``'s own dict output is fed
into ``graspgenx.serving.types.SweepVolumeParams(**cfg)`` on the pod side, where that
import is available).

Frame conventions (see any ``assets9/grippers/*.json``'s own ``"frame"`` field):
  - Ours (TCP frame G): origin = pad centre, z = -approach, y = closing axis, x = y cross z.
  - tcp_in_base: xyz + rpy (URDF-style extrinsic X-Y-Z Euler, <origin rpy="r p y">) that
    maps a point in frame G into the gripper's base_link frame.
  - GraspGenX sweep-volume base frame: +Z = approach axis, +X = closing direction.
    Permutation from base_link-frame (ours, after tcp_in_base) to GraspGenX axes:
    P = [[0,1,0],[1,0,0],[0,0,-1]]  (ours (x,y,z) -> graspgenx (y,x,-z)); det(P)=+1.
    (ours y = closing axis -> graspgenx x = closing axis; ours -z = approach -> graspgenx
    +z = approach, i.e. graspgenx_z = -ours_z.)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

P_TO_GRASPGENX = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, -1.0))


def _mat_vec(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def _rpy_to_matrix(rpy):
    """Extrinsic X-Y-Z Euler (URDF <origin rpy="r p y"> convention): R = Rz(yaw) @ Ry(pitch) @ Rx(roll)."""
    r, p, y = rpy
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    rx = ((1, 0, 0), (0, cr, -sr), (0, sr, cr))
    ry = ((cp, 0, sp), (0, 1, 0), (-sp, 0, cp))
    rz = ((cy, -sy, 0), (sy, cy, 0), (0, 0, 1))

    def matmul(a, b):
        return tuple(
            tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
            for i in range(3)
        )

    return matmul(matmul(rz, ry), rx)


def _union_box(boxes):
    """boxes: list of {"center":[x,y,z], "size":[sx,sy,sz]} in the same frame.
    Returns (center, size) of the axis-aligned box enclosing all of them."""
    lo = [math.inf, math.inf, math.inf]
    hi = [-math.inf, -math.inf, -math.inf]
    for b in boxes:
        c, s = b["center"], b["size"]
        for k in range(3):
            lo[k] = min(lo[k], c[k] - s[k] / 2.0)
            hi[k] = max(hi[k], c[k] + s[k] / 2.0)
    center = tuple((lo[k] + hi[k]) / 2.0 for k in range(3))
    size = tuple(hi[k] - lo[k] for k in range(3))
    return center, size


def _pick_entries(by_width):
    """open = max-width entry; mid = the entry closest to half the open width (prefers
    an existing by_width row over interpolating, since GraspGenX just needs a plausible
    partially-closed sweep volume, not an exact mid state)."""
    entries = sorted(by_width, key=lambda e: e["width"])
    open_e = entries[-1]
    half = open_e["width"] / 2.0
    mid_e = min(entries, key=lambda e: abs(e["width"] - half))
    return open_e, mid_e


def sweep_volume_params_dict(gripper_json_path: str | Path) -> dict:
    """Returns a plain dict with the SweepVolumeParams fields (extents_open, offset_open,
    extents_mid, offset_mid, gripper_type, fingertip_depth) -- construct the real
    ``graspgenx.serving.types.SweepVolumeParams`` from this dict where that import exists.
    Only 2-finger (parallel_2f) grippers are supported here; a 3-finger hand (e.g. G1
    Dex3-1) needs its own converter (different gripper_type, no single closing axis)."""
    data = json.loads(Path(gripper_json_path).read_text())
    boxes = data["boxes"]
    n_fingers = len(boxes["by_width"][0]["fingers"])
    if n_fingers != 2:
        raise ValueError(
            f"{gripper_json_path}: {n_fingers}-finger gripper, this converter only "
            "supports 2-finger (parallel_2f) grippers; write a dedicated converter."
        )
    open_e, mid_e = _pick_entries(boxes["by_width"])

    rot = _rpy_to_matrix(tuple(data["tcp_in_base"]["rpy"]))
    xyz = tuple(data["tcp_in_base"]["xyz"])

    def to_graspgenx(entry):
        c_tcp, size = _union_box(entry["fingers"])
        c_base = tuple(_mat_vec(rot, c_tcp)[k] + xyz[k] for k in range(3))
        # size is extent along each of OUR base-frame axes (rotation by rpy=0 in all
        # observed assets does not change axis-aligned extents; a future non-zero-rpy
        # asset would need true OBB handling here, not just axis-permuted AABB extents).
        c_gx = _mat_vec(P_TO_GRASPGENX, c_base)
        extents_gx = tuple(abs(x) for x in _mat_vec(P_TO_GRASPGENX, size))
        return list(extents_gx), list(c_gx), c_base, size

    extents_open, offset_open, c_base_open, size_open = to_graspgenx(open_e)
    extents_mid, offset_mid, _, _ = to_graspgenx(mid_e)

    # fingertip_depth: distance from the gripper origin to the far edge of the OPEN
    # sweep volume along the approach axis (our base-frame z, before permutation).
    fingertip_depth = abs(c_base_open[2]) + size_open[2] / 2.0

    return {
        "extents_open": extents_open,
        "offset_open": offset_open,
        "extents_mid": extents_mid,
        "offset_mid": offset_mid,
        "gripper_type": 0,  # parallel_2f
        "fingertip_depth": fingertip_depth,
        "_source": str(gripper_json_path),
        "_open_width_m": open_e["width"],
        "_mid_width_m": mid_e["width"],
    }


if __name__ == "__main__":
    import sys

    for p in sys.argv[1:]:
        cfg = sweep_volume_params_dict(p)
        print(json.dumps(cfg, indent=2))
