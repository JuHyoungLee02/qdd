"""Simulator ground truth → predicate inputs (harvest.predicates).

Frame convention: table-top frame, table surface at z = 0 (x, y unchanged from the world frame).
Isaac-dependent functions import Isaac lazily so this module loads without Isaac.
"""
import numpy as np

CONTACT_FORCE_N = 0.1  # |F| above this counts as a contact (sim noise floor is ~1e-3 N)
TABLE_TOL_M = 0.004  # object bottom within 4 mm of the table surface -> supported by the table


def to_table_frame(p_world: np.ndarray, table_top_z: float) -> np.ndarray:
    p = np.asarray(p_world, dtype=float).copy()
    p[2] -= table_top_z
    return p


def support_from_contacts(pos: dict, half_z: dict, contacts: set, table_tol: float = TABLE_TOL_M) -> dict:
    """support[a] = the highest object in contact with a whose centre is lower than a's; else "table" when a's
    bottom is on the table surface; else None (in the air, e.g. held). Table frame positions."""
    sup = {}
    for a, pa in pos.items():
        below = [b for b in pos if b != a and frozenset({a, b}) in contacts and pos[b][2] < pa[2]]
        if below:
            sup[a] = max(below, key=lambda b: pos[b][2])
        elif pa[2] - half_z[a] <= table_tol:
            sup[a] = "table"
        else:
            sup[a] = None
    return sup


REST_TOL_M = 0.006  # mesh object bottom within 6 mm of another object's top (convex-hull colliders sit a few mm off)


def container_contains(j: str, b, xy, bottom_z: float) -> bool:
    """L8S container j (objv.register_containers) holds a point: xy inside its opening box and the object's bottom
    between inner floor - 1 cm and the rim (into) or within 1.5 cm of the top (onto). b: container Obj (canonical
    centre, quat); the boxes are relative to the USD root = centre - R(yaw) centre_from_root_xy."""
    import math

    from .scene import OBJ_GEOM
    g = OBJ_GEOM[j]
    q = b.quat_wxyz
    yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
    dx, dy = float(xy[0] - b.pos[0]), float(xy[1] - b.pos[1])
    c, s = math.cos(-yaw), math.sin(-yaw)
    rx = c * dx - s * dy + g["centre_from_root_xy"][0]
    ry = s * dx + c * dy + g["centre_from_root_xy"][1]
    (x0, x1), (y0, y1) = g["opening_box"]
    if not (x0 <= rx <= x1 and y0 <= ry <= y1):
        return False
    base = b.pos[2] - g["half_extents"][2]
    floor = base + g["inner_floor_z"]
    if g["place_kind"] == "onto":
        return abs(bottom_z - floor) <= 0.015
    return floor - 0.01 <= bottom_z <= base + g["rim_z"]


def mesh_rest_contacts(k: str, objs: dict, tol: float = REST_TOL_M) -> set:
    """{k, j} when mesh object k rests on object j: k's lowest point within tol of j's top face and k's centre inside
    j's upright box in xy (table frame positions; boxes as OBJ_GEOM half extents, j assumed upright)."""
    from .scene import OBJ_GEOM, SUPPORT_TOP
    from .tasks import lowest_z
    a = objs[k]
    bot = lowest_z(k, a.pos, a.quat_wxyz)
    out = set()
    for j, b in objs.items():
        if j == k or OBJ_GEOM[j]["shape"] in ("marker", "surface"):
            continue
        if OBJ_GEOM[j].get("place_kind"):  # L8S container (pilot 2: bowls' curved floors failed the flat-top rule)
            if container_contains(j, b, a.pos[:2], bot):
                out.add(frozenset({k, j}))
            continue
        he = OBJ_GEOM[j]["half_extents"]
        top = b.pos[2] - he[2] + SUPPORT_TOP.get(j, 2 * he[2])
        if abs(bot - top) <= tol and abs(a.pos[0] - b.pos[0]) <= he[0] and abs(a.pos[1] - b.pos[1]) <= he[1]:
            out.add(frozenset({k, j}))
    return out


def oracle_objects(env):
    """(objs, gripper, contacts, support) for PredicateState.update, table frame (z = 0 at the table top).

    contacts: frozensets of ids from the per-object contact sensors (filtered against the four finger links and
    the other objects; any finger link -> "gripper"). Only objects in play (env.present) are reported.
    """
    from ..predicates import Gripper, Obj
    from .scene import FINGER_BODIES, OBJ_GEOM, VISUAL_ONLY, X_VISUAL_ONLY
    from .tasks import lowest_z, marker_contacts, surface_contacts

    z0 = env.table_top_z
    objs, half_z = {}, {}
    for k in env.present:
        p, q = env.object_pose(k)
        he = np.array(OBJ_GEOM[k]["half_extents"])
        objs[k] = Obj(id=k, pos=to_table_frame(p, z0), quat_wxyz=q, half_extents=he)
        half_z[k] = he[2]
    all_ids = list(getattr(env, "obj_ids", ["o3", "o5", "o8", "o9", "o10"]))  # = the contact filter order (scene)
    n_f = len(getattr(env, "finger_bodies", None) or FINGER_BODIES[env.arm])  # L9 profile: its finger links
    f0, f1 = getattr(env, "finger_slice", (0, n_f))  # dual (L9 bimanual): this arm's fingers among both arms'
    n_all = getattr(env, "n_finger_filters", n_f)
    contacts = set()
    for k in env.present:
        if k in VISUAL_ONLY or k in X_VISUAL_ONLY:  # marker / L8-X spots: no sensor; virtual contacts
            pos = {j: o.pos for j, o in objs.items()}
            bottom = {j: lowest_z(j, o.pos, o.quat_wxyz) for j, o in objs.items()}
            if OBJ_GEOM[k]["shape"] == "surface":  # L8-X furniture surface as the place object
                contacts |= surface_contacts(pos, bottom, k, OBJ_GEOM[k]["half_extents"][:2])
            else:
                contacts |= marker_contacts(pos, bottom, k)
            continue
        if OBJ_GEOM[k].get("kinematic"):  # L8S container: no sensor; objects resting in it are found from their side
            continue
        fm = env.contact[k].data.force_matrix_w  # (1, 1, n_filters, 3); filters = fingers + other objects
        mag = fm[0, 0].norm(dim=-1).cpu().numpy()
        if (mag[f0:f1] > CONTACT_FORCE_N).any():
            contacts.add(frozenset({"gripper", k}))
        others = [j for j in all_ids if j != k and not OBJ_GEOM[j].get("kinematic")]  # = the sensor filter order
        for j, m in zip(others, mag[n_all:]):
            if m > CONTACT_FORCE_N and j in env.present:
                contacts.add(frozenset({k, j}))
        if OBJ_GEOM[k]["shape"] == "mesh":  # L8-X mesh objects report finger contacts but not object contacts
            # (nested rigid body of the physics USD, debug_objv_contact): resting on another object = geometric
            contacts |= mesh_rest_contacts(k, objs)
    tcp = to_table_frame(env.finger_mid(), z0)
    t = env.gap_table() if hasattr(env, "gap_table") else None  # L9 grip layer (opt-in), None = unchanged
    if t is not None:
        from ..l9.hand9 import OPEN_TOL
        grip = Gripper(width_m=env.gripper_width(), effort=env.gripper_effort(), pos=tcp, open_m=t.max_gap - OPEN_TOL)
    else:
        grip = Gripper(width_m=env.gripper_width(), effort=env.gripper_effort(), pos=tcp)
    support = support_from_contacts({k: o.pos for k, o in objs.items()}, half_z, contacts)
    return objs, grip, contacts, support
