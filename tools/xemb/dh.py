"""D / H depth-track rows from open data with metric head depth + calibration (user-log 156: final 35B small run compares
D vs H on ready depth data only). One state -> two rows over the same images (RGB + encoded depth, astra-solo-h depth
encoding 0.25-1.60 m grey, near = bright):
  D  answer {"point_2d": [x, y] (0-1000 in image 1), "height": "grasp"}          the code converts point + depth -> xyz
  H  answer {"point_2d", "height", "position_m": [x, y, z]} (robot base frame)   xyz used when there is no depth
Header lines 'source:' / 'frame:' and the camera line (K, pose in the base frame) as in fmt.
Converter: back-project the depth at the point (median of a 5 x 5 patch) -> base frame; its error against the GT target
is the gate (a row is written only when the converter lands within CONV_TOL_M of the GT target)."""
from __future__ import annotations

import json

import numpy as np

from . import fmt as F

CONV_TOL_M = 0.05
D_LO, D_HI = 0.25, 1.60


def encode_depth(depth):
    """= harvest.astra_solo.hybrid.encode_depth at scale 1 (kept local: no harvest import on the pod code path)."""
    z = np.asarray(depth, float)
    ok = np.isfinite(z) & (z >= D_LO) & (z <= D_HI)
    return np.where(ok, np.rint(1 + 254 * (D_HI - np.where(ok, z, D_HI)) / (D_HI - D_LO)), 0).astype(np.uint8)


def converter(K, T_base_cam, depth, uv, r=2):
    """Point + depth -> base-frame xyz (None when no valid depth at the point)."""
    H, W = depth.shape
    u, v = int(round(uv[0])), int(round(uv[1]))
    if not (0 <= u < W and 0 <= v < H):
        return None
    patch = depth[max(0, v - r):v + r + 1, max(0, u - r):u + r + 1]
    patch = patch[np.isfinite(patch) & (patch > 0.05)]
    if not len(patch):
        return None
    z = float(np.median(patch))
    pc = np.array([(uv[0] - K[0, 2]) * z / K[0, 0], (uv[1] - K[1, 2]) * z / K[1, 1], z])
    T = np.asarray(T_base_cam, float)
    return T[:3, :3] @ pc + T[:3, 3]


_ASK = {"grasp": "where the gripper should grasp it", "above": "that the gripper should move above",
        "place": "where the held object should be put down", "lift": "that the gripper should lift"}


def rows(robot, W, H, K, T_base_cam, uv, xyz_base, name, images, rid, intent="grasp"):
    """images: [rgb] (D only, no depth: h is None) or [rgb, encoded depth png] (D and H)."""
    cams = [{"name": "head camera", "W": W, "H": H, "K": np.asarray(K).tolist(), "T_base_cam": np.asarray(T_base_cam).tolist()}]
    depth = len(images) > 1
    head = F.header(robot, f"base_{robot['name']}") + "CAMERAS\n" + F._cam_line(0, cams[0]) + "\n"
    if depth:
        head += "- Image 2: head depth (grey, 0.25-1.60 m, near = bright, black = no depth).\n"
        head += "depth: sensor (head, metric, gray 0.25-1.60 m, near=bright)\n"
    q = (f"Point to the {name} in image 1 {_ASK[intent]} (0-1000, x right, y down) and give the height intent")
    p = [int(round(uv[0] * 1000 / W)), int(round(uv[1] * 1000 / H))]
    x = [round(float(v), 3) for v in xyz_base]
    d = {"id": rid + "_D", "kind": "qa_xemb", "qa_kind": "dh_point", "track": "D", "source": robot["source"],
         "frame": f"base_{robot['name']}", "images": list(images[:1]) if not depth else list(images), "coords": "n1000",
         "prompt": head + q + ".\nReturn JSON only.", "answer": json.dumps({"point_2d": p, "height": intent})}
    if not depth:
        return d, None
    h = dict(d, id=rid + "_H", track="H", qa_kind="dh_point_xyz",
             prompt=head + q + ", and the TCP target position_m in metres in the robot base frame.\nReturn JSON only.",
             answer=json.dumps({"point_2d": p, "height": intent, "position_m": x}))
    return d, h
