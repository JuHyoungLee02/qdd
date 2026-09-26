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


def oracle_objects(env):
    """(objs, gripper, contacts, support) for PredicateState.update, table frame (z = 0 at the table top).

    contacts: frozensets of ids from the per-object contact sensors (filtered against the four finger links and
    the other objects; any finger link -> "gripper"). Only objects in play (env.present) are reported.
    """
    from ..predicates import Gripper, Obj
    from .scene import FINGER_BODIES, OBJ_GEOM, VISUAL_ONLY, X_VISUAL_ONLY
    from .tasks import lowest_z, marker_contacts

    z0 = env.table_top_z
    objs, half_z = {}, {}
    for k in env.present:
        p, q = env.object_pose(k)
        he = np.array(OBJ_GEOM[k]["half_extents"])
        objs[k] = Obj(id=k, pos=to_table_frame(p, z0), quat_wxyz=q, half_extents=he)
        half_z[k] = he[2]
    all_ids = list(getattr(env, "obj_ids", ["o3", "o5", "o8", "o9", "o10"]))  # = the contact filter order (scene)
    n_f = len(FINGER_BODIES[env.arm])
    contacts = set()
    for k in env.present:
        if k in VISUAL_ONLY or k in X_VISUAL_ONLY:  # marker / L8-X spots: no sensor; virtual contacts
            contacts |= marker_contacts({j: o.pos for j, o in objs.items()},
                                        {j: lowest_z(j, o.pos, o.quat_wxyz) for j, o in objs.items()}, k)
            continue
        fm = env.contact[k].data.force_matrix_w  # (1, 1, n_filters, 3); filters = fingers + other objects
        mag = fm[0, 0].norm(dim=-1).cpu().numpy()
        if (mag[:n_f] > CONTACT_FORCE_N).any():
            contacts.add(frozenset({"gripper", k}))
        others = [j for j in all_ids if j != k]
        for j, m in zip(others, mag[n_f:]):
            if m > CONTACT_FORCE_N and j in env.present:
                contacts.add(frozenset({k, j}))
    tcp = to_table_frame(env.finger_mid(), z0)
    grip = Gripper(width_m=env.gripper_width(), effort=env.gripper_effort(), pos=tcp)
    support = support_from_contacts({k: o.pos for k, o in objs.items()}, half_z, contacts)
    return objs, grip, contacts, support
