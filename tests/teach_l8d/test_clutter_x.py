"""b3 cluttered table scenes (prereg_l8d change 11): real objects (helper objects_real.json) scattered on the table
around the task layout by clutter.sample_clutter, clear of the workspace box and of every layout object."""
import math

from harvest.teach_l8d import clutter_x as CX

WS = ((0.37, 0.52), (-0.40, -0.06))


def test_pool_is_train_only_short_stable_and_per_bucket():
    rows = CX.load_real()
    p1 = CX.pool_for(rows, "drx|0.840", n=30)
    assert len(p1) == 30 and p1 == CX.pool_for(rows, "drx|0.840", n=30)
    assert p1 != CX.pool_for(rows, "standard|0.900", n=30)
    for k, r in p1.items():
        assert r["split"] == "train" and r.get("stable") and r["height"] <= CX.MAX_H + 1e-9
    assert not set(CX.pool_for(rows, "x", n=30, exclude={next(iter(p1))})) & {next(iter(p1))}


def test_add_clutter_keeps_the_task_area_free():
    rows = CX.load_real()
    pool = CX.pool_for(rows, "drx|0.840", n=30)
    lay = {"o3": (0.45, -0.20, 0.0), "o5": (0.40, -0.33, 0.0), "o9": (0.50, 0.02, 0.3)}
    fr = {"o3": 0.032, "o5": 0.114, "o9": 0.036}
    n_tot = 0
    for seed in range(36300, 36320):
        out, placed = CX.add_clutter(dict(lay), seed, pool, WS, fr)
        assert {k: out[k] for k in lay} == lay and set(out) - set(lay) == {p["id"] for p in placed}
        n_tot += len(placed)
        for p in placed:
            r = pool[p["id"]]["footprint_r"]
            (x0, x1), (y0, y1) = CX.TABLE_BOX
            assert x0 + r <= p["x"] <= x1 - r and y0 + r <= p["y"] <= y1 - r
            assert not (WS[0][0] - CX.MARGIN - r < p["x"] < WS[0][1] + CX.MARGIN + r
                        and WS[1][0] - CX.MARGIN - r < p["y"] < WS[1][1] + CX.MARGIN + r)
            for k, v in lay.items():
                assert math.dist((p["x"], p["y"]), v[:2]) >= r + fr[k] + 0.02 - 1e-9
    assert n_tot >= 20 * 3  # a few objects per scene on average


def test_clutter_plan_and_dir():
    from harvest.teach_l8d.run_collect import select_plan, vdir
    plan = [{"seed": 1, "split": "train", "variant": "drx", "table_z": 0.84, "task": "mug_tray", "objset": "x"},
            {"seed": 2, "split": "train", "variant": "drx", "table_z": 0.84, "task": "mug_tray", "objset": "x", "clutter": True}]
    assert [e["seed"] for e in select_plan(plan, "drx", 0.84, "train", "x")] == [1]
    assert [e["seed"] for e in select_plan(plan, "drx", 0.84, "train", "x", clutter=True)] == [2]
    assert vdir("drx", 0.84, None, None, True) == "drx_tz0.840_cl" and vdir("drx", 0.84, None) == "drx_tz0.840"


def test_real_object_tasks_register():
    from harvest.sim import objv as OV
    from harvest.sim import tasks as T
    rows = CX.load_real()
    k = sorted(k for k, r in rows.items() if r["split"] == "train" and r.get("task_target_ok"))[0]
    assert k in OV.register_for_tasks([f"ov_tray__{k}"]) and T.TASKS[f"ov_tray__{k}"].target == k


class _Env:
    def __init__(self, quat):
        self.quat = quat

    def object_pose(self, k):
        return [0.0, 0.0, 0.0], self.quat


def _tilted(deg):
    a = math.radians(deg) / 2
    return [math.cos(a), math.sin(a), 0.0, 0.0]  # about x


def test_occlusion_ignores_the_container_itself():
    """L8S change 28 (audit 4 item 3): a sample hidden only by the destination container (its rim / wall / handle)
    is not counted; anything else in front still is."""
    import numpy as np

    from harvest.astra_motion import geometry as G
    cam = G.Cam("c", 100, 100, 100.0, 100.0, 50.0, 50.0, np.diag([1.0, -1.0, -1.0]), np.array([0.0, 0.0, 1.0]))
    depth = np.full((100, 100), 0.4)  # something 0.4 m below the camera (world z 0.6) in front of the top at z 0.1
    box = ((0.0, 0.0, 0.6), (0.2, 0.2, 0.05), 0.0)
    assert CX.occlusion(cam, depth, (0.0, 0.0), 0.02, 0.1) == 1.0
    assert CX.occlusion(cam, depth, (0.0, 0.0), 0.02, 0.1, ignore=[box]) == 0.0
    far = ((0.0, 0.0, 0.3), (0.2, 0.2, 0.05), 0.0)  # a box elsewhere does not excuse the occluder
    assert CX.occlusion(cam, depth, (0.0, 0.0), 0.02, 0.1, ignore=[far]) == 1.0


def test_container_boxes_only_for_env_containers(monkeypatch):
    """A place that is not an env body (ring V peg, place_kind 'around') or not a container gives no box."""
    from harvest.sim import scene as SC

    class _E:
        objects = {}

        def object_pose(self, k):
            raise KeyError(k)
    monkeypatch.setitem(SC.OBJ_GEOM, "_t_peg", {"shape": "cuboid", "size": [0.04, 0.04, 0.002],
                                                "place_kind": "around"})
    monkeypatch.setitem(SC.OBJ_GEOM, "_t_cup", {"shape": "cuboid", "size": [0.1, 0.1, 0.1],
                                                "half_extents": [0.05] * 3, "place_kind": "into"})
    assert CX.container_boxes(_E(), "_t_peg") == [] and CX.container_boxes(_E(), "_t_cup") == []
    assert CX.container_boxes(None, "_t_cup") == []


def test_upright_rule_by_shape():
    """L8S change 28 (audit 4): rolling objects need no upright pose; an object in a container may lean <= 60 deg;
    everything else keeps the 30 deg predicate."""
    rows = CX.load_real()
    roll = next(k for k, r in rows.items() if r.get("noun") in CX.ROLLING)
    plain = next(k for k, r in rows.items() if r.get("noun") not in CX.ROLLING and r.get("sphericity", 0) < 0.6)
    st = lambda k, v: {"pred": {f"upright({k})": v}, "obj": {}}  # noqa: E731
    assert CX.upright_rule(st(roll, False), _Env(_tilted(90)), {"tgt": roll, "place": "o5"}, into=False)[
        "pred"][f"upright({roll})"] is True
    assert CX.upright_rule(st(plain, False), _Env(_tilted(45)), {"tgt": plain, "place": "c"}, into=True)[
        "pred"][f"upright({plain})"] is True
    assert CX.upright_rule(st(plain, False), _Env(_tilted(75)), {"tgt": plain, "place": "c"}, into=True)[
        "pred"][f"upright({plain})"] is False
    assert CX.upright_rule(st(plain, False), _Env(_tilted(45)), {"tgt": plain, "place": "o5"}, into=False)[
        "pred"][f"upright({plain})"] is False
    assert CX.upright_rule(st(plain, True), _Env(_tilted(10)), {"tgt": plain, "place": "o5"}, into=False)[
        "pred"][f"upright({plain})"] is True
