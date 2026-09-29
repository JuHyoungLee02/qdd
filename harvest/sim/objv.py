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
    return {"shape": "mesh", "usd": row["usd_physics"],
            "body_rel": row.get("body_rel", f"Geometry/obja_{row['uid']}"),  # real objects (L8X-assets) give theirs
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
    from ..teach_l8d.xnew import is_new_task, register_new_tasks  # L8-X st__ / pu__ tasks (real objects)
    new = register_new_tasks([t for t in tasks if is_new_task(t)]) if any(is_new_task(t) for t in tasks) else []
    into = [t for t in tasks if str(t).startswith("ov_into__")]
    if into:  # L8S: ov_into__<object>__<container> (containers.json, into / onto)
        from .tasks import register_into_task
        conts = load_containers(usable_only=False)
        cids = sorted({t.rsplit("__", 1)[1] for t in into})
        register_containers({c: conts[c] for c in cids})
        tasks = [t for t in tasks if t not in into] + [f"ov_tray__{t[len('ov_into__'):].rsplit('__', 1)[0]}"
                                                       for t in into]
    ids = sorted({t.split("__", 1)[1] for t in tasks if str(t).startswith("ov_")})
    if not ids:
        return new
    rows = rows or load_rows()
    if any(k not in rows for k in ids):  # b3 real objects (helper objects_real.json, objv-compatible rows)
        from ..teach_l8d.clutter_x import load_real
        rows = {**load_real(), **rows}
    register({k: rows[k] for k in ids})
    register_objv_tasks(ids, {k: prompt_name(rows[k]) for k in ids})
    if into:
        for t in into:
            a, c = t[len("ov_into__"):].rsplit("__", 1)
            register_into_task(t, a, c, prompt_name(rows[a]), prompt_name(conts[c]), conts[c]["inside"]["place_kind"])
        ids = sorted(set(ids) | set(cids))
    return sorted(set(ids) | set(new))


MIN_H, MAX_H = 0.07, 0.10  # prereg_l8d change 8: the truth held 0/9 gated objects under 7 cm (3/5 at 8 cm)
MIN_GRASP_W, MAX_GRASP_W = 0.025, 0.085  # ... and failed the 2.0 cm and 8.9 cm wide ones (pads stop at ~8.5 cm)


def eligible(rows: dict, split: str = "train", need_stable: bool = True) -> dict:
    """Objects usable as targets: the split, the helper's stable flag (Isaac drop test), height MIN_H-MAX_H and a
    grasp width MIN_GRASP_W-MAX_GRASP_W; the Objaverse gate (>= 2/3 clean truth) filters further."""
    return {k: r for k, r in rows.items() if r["split"] == split and (r.get("stable_upright") is True or not need_stable)
            and MIN_H - 1e-9 <= r["height"] <= MAX_H + 1e-9
            and MIN_GRASP_W - 1e-9 <= r["grasp_width"] <= MAX_GRASP_W + 1e-9}


CONTAINERS = "assets_x/containers.json"  # helper L8X-assets 2a8f3e3: into / onto places (kinematic)
RIM_MAX = 0.12  # m above the bottom: the carry height (support + 22 cm, xlabels) clears the rim with the object


def load_containers(path: str | None = None, usable_only: bool = True) -> dict:
    """Container rows (gate_pass, rim <= RIM_MAX) as objv rows (name = noun, split train)."""
    import json
    import os
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), CONTAINERS)
    out = {}
    for k, r in json.load(open(p))["containers"].items():
        i = r["inside"]
        if usable_only and not (r.get("gate_pass") and (i.get("rim_z") or i["inner_floor_z"]) <= RIM_MAX + 1e-9):
            continue
        out[k] = dict(r, name=r.get("name") or r["noun"].replace("_", " "), split=r.get("split") or "train",
                      uid=r.get("uid") or k)
    return out


def register_containers(rows: dict) -> list:
    """Register containers as kinematic mesh objects whose place surface is their inner floor (SUPPORT_TOP)."""
    from . import scene as S
    ids = register(rows)
    for k in ids:
        i = rows[k]["inside"]
        S.OBJ_GEOM[k].update(kinematic=True, place_kind=i["place_kind"], opening=float(i.get("opening_min_side", 0)))
        S.SUPPORT_TOP[k] = float(i["inner_floor_z"]) - float(rows[k].get("root_above_bottom", 0.0))
    return ids


def into_fits(obj: dict, cont: dict) -> bool:
    """The object passes the container's opening with 1 cm each side (2 x footprint_r <= opening - 2 cm)."""
    return 2 * float(obj["footprint_r"]) <= float(cont["inside"].get("opening_min_side", 0)) - 0.02
