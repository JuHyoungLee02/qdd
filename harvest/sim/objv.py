"""L8-X licensed mesh objects (b2; helper L8X-assets table harvest/sim/assets_x/objects_objv.json: MolmoSpaces
Objaverse subset, CC0 / CC BY / CC BY-SA, attribution per object) as task objects.

Canonical frame: every other module sees a mesh object like a primitive one -- its pose = the centre of its
upright bounding box and a quaternion that is identity when it stands as authored upright (the table's
spawn_quat_wxyz, a +90 deg x rotation for the Y-up geometry, is factored out). The rigid body's USD root is
somewhere else (root_above_bottom above its bottom, centre_from_root_xy from its centre in xy), so the scene converts
at spawn / reset (root_from_canonical) and at every read (canonical_from_root).

register(rows): OBJ_GEOM entries (shape "mesh", half_extents / height / footprint_r / grasp_width from the table),
parking spots and prompt names / descriptions; only the objects a process uses (each is a rigid body prim). The
objects' narrow horizontal side is turned to world x at layout time (grasp_yaw_of) so the fingers (closing along
world x) close on grasp_width. Pure (numpy)."""
from __future__ import annotations

import math

import numpy as np

PARK0 = (-4.5, -4.0)


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def qinv(q):
    w, x, y, z = q
    return (w, -x, -y, -z)


def qrot(q, v):
    """Rotate vector v by unit quaternion q (w, x, y, z)."""
    p = qmul(qmul(q, (0.0, *v)), qinv(q))
    return np.array(p[1:], float)


def yaw_q(yaw: float):
    return (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))


def _offset(g) -> np.ndarray:
    """Root -> bbox centre in the canonical (upright) frame."""
    cx, cy = g["centre_from_root_xy"]
    return np.array([cx, cy, g["height"] / 2 - g["root_above_bottom"]], float)


def root_from_canonical(g, centre, quat_c):
    """(root position, root quaternion) of a mesh object whose canonical pose is (centre, quat_c)."""
    q = qmul(tuple(quat_c), tuple(g["spawn_quat_wxyz"]))
    return np.asarray(centre, float) - qrot(tuple(quat_c), _offset(g)), q


def canonical_from_root(g, root, quat_root):
    qc = qmul(tuple(quat_root), qinv(tuple(g["spawn_quat_wxyz"])))
    n = math.sqrt(sum(v * v for v in qc))
    qc = tuple(v / n for v in qc)
    return np.asarray(root, float) + qrot(qc, _offset(g)), qc


def grasp_yaw_of(g) -> float:
    """Layout yaw that turns the object's narrow horizontal side to world x (the fingers close along x)."""
    hx, hy = g["half_extents"][:2]
    return math.pi / 2 if hy < hx else 0.0


def geom(row: dict) -> dict:
    he = [float(v) for v in row["half_extents"]]
    return {"shape": "mesh", "usd": row["usd_physics"], "body_rel": f"Geometry/obja_{row['uid']}",
            "spawn_quat_wxyz": [float(v) for v in row["spawn_quat_wxyz"]],
            "root_above_bottom": float(row["root_above_bottom"]),
            "centre_from_root_xy": [float(v) for v in row["centre_from_root_xy"]],
            "half_extents": tuple(he), "size": (2 * he[0], 2 * he[1], float(row["height"])), "height": float(row["height"]), "footprint_r": float(row["footprint_r"]),
            "grasp_width": float(row["grasp_width"]), "mass": float(row.get("mass", 0.3)),
            "friction": tuple(row.get("friction", (0.8, 0.8))), "name": row["name"], "category": row["category"],
            "split": row["split"], "license": row["license"], "attribution": row.get("attribution")}


def prompt_name(row: dict) -> str:
    return " ".join(str(row["name"]).lower().split())


def prompt_desc(g: dict) -> str:
    L, W = sorted((2 * g["half_extents"][0], 2 * g["half_extents"][1]), reverse=True)
    return f"object about {L * 100:.1f} x {W * 100:.1f} cm, {g['height'] * 100:.1f} cm high"


def register(rows: dict) -> list:
    """rows: {id: table row}. Adds the objects to scene.OBJ_GEOM / PARK_XY / scene.OBJV_IDS and the prompt tables;
    returns the ids (sorted). Idempotent."""
    from ..astra_motion import prompts as P
    from . import scene as S
    ids = sorted(rows)
    for i, k in enumerate(ids):
        g = geom(rows[k])
        S.OBJ_GEOM[k] = g
        S.PARK_XY[k] = (PARK0[0] - 0.35 * i, PARK0[1])
        P.OBJ_NAME[k] = prompt_name(rows[k])
        P.OBJ_DESC[k] = prompt_desc(g)
    S.OBJV_IDS[:] = sorted(set(S.OBJV_IDS) | set(ids))
    return ids


TABLE = "assets_x/objects_objv.json"  # under harvest/sim


def load_rows(path: str | None = None) -> dict:
    import json
    import os
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), TABLE)
    return json.load(open(p))["objects"]


def register_for_tasks(tasks, rows: dict | None = None) -> list:
    """Register the mesh objects (and their ov_* tasks) that the given task names use ('ov_<kind>__<id>');
    -> the ids. Used by the runner (before make_env) and by the dataset builder (prompt names / sizes)."""
    from .tasks import register_objv_tasks
    ids = sorted({t.split("__", 1)[1] for t in tasks if str(t).startswith("ov_")})
    if not ids:
        return []
    rows = rows or load_rows()
    register({k: rows[k] for k in ids})
    register_objv_tasks(ids, {k: prompt_name(rows[k]) for k in ids})
    return ids


MIN_H, MAX_H = 0.07, 0.10  # prereg_l8d change 8: the truth held 0/9 gated objects under 7 cm (3/5 at 8 cm)
MIN_GRASP_W, MAX_GRASP_W = 0.025, 0.085  # ... and failed the 2.0 cm and 8.9 cm wide ones (pads stop at ~8.5 cm)


def eligible(rows: dict, split: str = "train", need_stable: bool = True) -> dict:
    """Objects usable as targets: the split, the helper's stable flag (Isaac drop test), height MIN_H-MAX_H and a
    grasp width MIN_GRASP_W-MAX_GRASP_W; the Objaverse gate (>= 2/3 clean truth) filters further."""
    return {k: r for k, r in rows.items() if r["split"] == split and (r.get("stable_upright") is True or not need_stable)
            and MIN_H - 1e-9 <= r["height"] <= MAX_H + 1e-9
            and MIN_GRASP_W - 1e-9 <= r["grasp_width"] <= MAX_GRASP_W + 1e-9}
