"""L8-X licensed mesh objects (pure): canonical <-> root pose, registration, tasks, layouts, labels."""
import json
import math
import os

import numpy as np
import pytest

from harvest.sim import objv as OV
from harvest.sim import scene as S
from harvest.sim import tasks as T

TABLE = os.path.join(os.path.dirname(S.__file__), "assets_x", "objects_objv.json")


@pytest.fixture(scope="module")
def rows():
    return json.load(open(TABLE))["objects"]


def test_canonical_roundtrip(rows):
    k = sorted(rows)[0]
    g = OV.geom(rows[k])
    for yaw in (0.0, 0.7, math.pi / 2, -2.0):
        c = np.array([0.45, -0.2, 0.85 + g["height"] / 2])
        qc = OV.yaw_q(yaw)
        r, qr = OV.root_from_canonical(g, c, qc)
        c2, qc2 = OV.canonical_from_root(g, r, qr)
        assert np.allclose(c, c2, atol=1e-9) and np.allclose(np.abs(np.dot(qc, qc2)), 1.0, atol=1e-9)
    # upright root z = bottom + root_above_bottom (the table's definition)
    r, _ = OV.root_from_canonical(g, [0.4, -0.2, 0.85 + g["height"] / 2], (1, 0, 0, 0))
    assert r[2] == pytest.approx(0.85 + g["root_above_bottom"], abs=1e-9)


def test_mesh_rest_contacts(rows):
    from harvest.predicates import Obj
    from harvest.sim.oracle_state import mesh_rest_contacts
    k = sorted(OV.eligible(rows, "train"))[0]
    OV.register({k: rows[k]})
    h = S.OBJ_GEOM[k]["height"]
    tray = Obj("o5", np.array([0.47, -0.30, 0.0075]), np.array([1.0, 0, 0, 0]), np.array(S.OBJ_GEOM["o5"]["half_extents"]))
    on = Obj(k, np.array([0.48, -0.31, 0.015 + h / 2 + 0.002]), np.array([1.0, 0, 0, 0]),
             np.array(S.OBJ_GEOM[k]["half_extents"]))
    assert mesh_rest_contacts(k, {"o5": tray, k: on}) == {frozenset({k, "o5"})}
    off = Obj(k, np.array([0.70, -0.31, 0.015 + h / 2]), np.array([1.0, 0, 0, 0]), on.half_extents)
    assert not mesh_rest_contacts(k, {"o5": tray, k: off})
    high = Obj(k, np.array([0.48, -0.31, 0.05 + h / 2]), np.array([1.0, 0, 0, 0]), on.half_extents)
    assert not mesh_rest_contacts(k, {"o5": tray, k: high})


def test_register_tasks_and_eligibility(rows):
    el = OV.eligible(rows, "train")
    assert el and all(r["stable_upright"] for r in el.values()) and all(r["split"] == "train" for r in el.values())
    assert not set(el) & set(OV.eligible(rows, "ood_o"))
    # prereg change 8: the gate held 0/9 objects under 7 cm and the 2 cm / 8.9 cm wide ones -> pre-filter
    assert all(r["height"] >= OV.MIN_H - 1e-9 and OV.MIN_GRASP_W <= r["grasp_width"] <= OV.MAX_GRASP_W + 1e-9
               for r in el.values())
    assert "objv_056e01405bac" not in el and "objv_01994d08f483" not in el and "objv_0503854981b4" in el
    ids = OV.register({k: rows[k] for k in sorted(el)[:3]})
    from harvest.astra_motion.prompts import OBJ_DESC, OBJ_NAME
    for k in ids:
        assert S.OBJ_GEOM[k]["shape"] == "mesh" and k in S.OBJV_IDS and k in OBJ_NAME and k in OBJ_DESC
        assert T.close_width(k) == pytest.approx(max(0.0, S.OBJ_GEOM[k]["grasp_width"] - T.GRIP_SQUEEZE_M))
    tids = T.register_objv_tasks(ids, {k: OV.prompt_name(rows[k]) for k in ids})
    assert len(tids) == 2 * len(ids) and len(set(T.X_TASK_CODE[t] for t in tids)) == len(tids)
    ws = ((0.37, 0.52), (-0.40, -0.06))
    for t in tids:
        s = T.TASKS[t]
        for seed in range(31900, 31905):
            lay = T.task_layout(seed, t, ws=ws)
            x, y, yaw = lay[s.target]
            assert ws[0][0] <= x <= ws[0][1] and ws[1][0] <= y <= ws[1][1]
            g = S.OBJ_GEOM[s.target]
            assert abs(yaw - OV.grasp_yaw_of(g)) <= math.radians(10) + 1e-9
    # the primitive tasks' layouts do not change when objects are registered
    assert T.task_layout(30001, "mug_bin", ws=ws) == T.x_task_layout(30001, "mug_bin", ws)
