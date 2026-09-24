"""Pure parts of harvest.sim.tasks (R2 multi-task registry, no Isaac)."""
import math

import numpy as np
import pytest

from harvest.sim import tasks as T
from harvest.sim.perturb import p2_spawn_xy
from harvest.sim.scene import OBJ_GEOM, WS_X, WS_Y, sample_layout

DEV = range(30)
NEW = [t for t in T.TASK_IDS if t != "mug_tray"]


def test_registry_has_mug_tray_and_two_more_tasks_with_distinct_goals():
    assert T.TASK_IDS[0] == "mug_tray" and len(T.TASK_IDS) >= 3
    assert T.TASKS["mug_tray"].target == "o3" and T.TASKS["mug_tray"].place == "o5"
    assert T.TASKS["mug_tray"].instruction == "Put the red mug on the blue tray."
    assert len({(T.TASKS[t].target, T.TASKS[t].place) for t in T.TASK_IDS}) == len(T.TASK_IDS)
    assert len({T.TASKS[t].instruction for t in T.TASKS}) == len(T.TASKS)
    assert not set(T.EXPERIMENTAL_TASKS) & set(T.TASK_IDS)
    for t in T.TASKS:
        s = T.TASKS[t]
        assert s.target in OBJ_GEOM and s.place in OBJ_GEOM and s.instruction.endswith(".")
        assert s.target in s.stage_text["S1"] and s.place in s.stage_text["S2"]


def test_check_task_refuses_unknown():
    with pytest.raises(ValueError):
        T.check_task("pour_water")
    assert T.check_task("bottle_tray") == "bottle_tray"


@pytest.mark.parametrize("seed", DEV)
def test_mug_tray_layout_is_the_standard_layout(seed):
    assert T.task_layout(seed, "mug_tray") == sample_layout(seed)


@pytest.mark.parametrize("task", NEW)
@pytest.mark.parametrize("seed", DEV)
def test_new_task_layouts(task, seed):
    s = T.TASKS[task]
    L = T.task_layout(seed, task)
    assert L == T.task_layout(seed, task)  # deterministic
    assert s.target in L and s.place in L and "o3" in L  # the mug stays on the table as a distractor
    assert "o10" not in L  # P2 object stays parked
    for k in (s.target, s.place):  # both reachable (top-down workspace of the right arm)
        x, y = L[k][:2]
        assert WS_X[0] - 1e-9 <= x <= WS_X[1] + 1e-9 and WS_Y[0] - 1e-9 <= y <= WS_Y[1] + 1e-9
    assert math.dist(L[s.target][:2], L[s.place][:2]) >= 0.16
    for k in L:
        if k in (s.target, s.place):
            continue
        assert math.dist(L[k][:2], L[s.target][:2]) >= 0.10  # finger room around the target
        assert math.dist(L[k][:2], L[s.place][:2]) >= OBJ_GEOM[k]["footprint_r"] + OBJ_GEOM[s.place]["footprint_r"] + 0.04
    keys = list(L)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            assert math.dist(L[a][:2], L[b][:2]) >= OBJ_GEOM[a]["footprint_r"] + OBJ_GEOM[b]["footprint_r"] + 0.02


def test_new_task_layouts_differ_from_standard_and_between_seeds():
    for t in NEW:
        assert T.task_layout(3, t) != T.task_layout(4, t)
        assert T.task_layout(3, t) != sample_layout(3)


@pytest.mark.parametrize("task", T.TASK_IDS)
@pytest.mark.parametrize("seed", DEV)
def test_p2_spot_exists_beside_the_carry_path(task, seed):
    s = T.TASKS[task]
    L = T.task_layout(seed, task)
    obst = {k: (np.array(v[:2]), OBJ_GEOM[k]["footprint_r"]) for k, v in L.items()}
    xy = p2_spawn_xy(seed, L[s.target][:2], L[s.place][:2], obst, OBJ_GEOM["o10"]["footprint_r"])
    assert np.all(np.isfinite(xy))


@pytest.mark.parametrize("task", NEW)
def test_dr_distractors_keep_out_of_the_task_path(task):
    from harvest.sim.perturb import P2_LATERAL_M
    from harvest.sim.randomize import _seg_dist, load_pools, sample_randomization
    s = T.TASKS[task]
    c = load_pools()["common"]
    for seed in DEV:
        L = T.task_layout(seed, task)
        m = sample_randomization(seed, "dr", L, path=(s.target, s.place))
        for d in m["distractors"]:
            band = P2_LATERAL_M[1] + OBJ_GEOM["o10"]["footprint_r"] + d["footprint_r"] + c["keepout_margin_m"]
            assert _seg_dist(d["xy"], L[s.target][:2], L[s.place][:2]) >= band - 1e-9
            for k, p in L.items():
                assert math.dist(d["xy"], p[:2]) >= OBJ_GEOM[k]["footprint_r"] + d["footprint_r"] - 1e-9


def test_box_yaw_is_graspable_and_grasp_yaw_aligns_with_a_face():
    for seed in DEV:
        yaw = T.task_layout(seed, "box_marker")["o9"][2]
        g = T.grasp_yaw("o9", yaw)
        assert abs(g - T.TOP_DOWN_YAW) <= math.radians(T.BOX_YAW_DEV_DEG) + 1e-9
        # closing axis (gripper yaw - pi/2) is parallel to a box face normal: difference is a multiple of pi/2
        r = (g - math.pi / 2 - yaw) / (math.pi / 2)
        assert abs(r - round(r)) < 1e-9
    assert T.grasp_yaw("o3", 1.234) == T.TOP_DOWN_YAW  # cylinders: the planner's default yaw
    assert T.grasp_yaw("o9", math.radians(100)) == pytest.approx(math.pi / 2 + math.radians(10))
    assert T.grasp_yaw("o9", math.radians(-170)) == pytest.approx(math.pi / 2 + math.radians(10))


def test_close_width_squeezes_the_grasped_dimension():
    assert T.close_width("o3") == pytest.approx(2 * 0.032 - 0.014)
    assert T.close_width("o8") == pytest.approx(2 * 0.025 - 0.014)
    assert T.close_width("o9") == pytest.approx(0.05 - 0.014)


def test_success_now_generalizes_the_mug_rule():
    ok = {"on(o8,o5)": True, "holding(o8)": False, "upright(o8)": True}
    assert T.success_now(ok, "o8", "o5")
    assert not T.success_now({**ok, "holding(o8)": None}, "o8", "o5")  # unknown never counts
    assert not T.success_now({**ok, "upright(o8)": False}, "o8", "o5")
    assert not T.success_now(ok, "o3", "o5")


def test_marker_virtual_contact():
    pos = {"o9": np.array([0.40, -0.20, 0.035]), "o11": np.array([0.41, -0.21, 0.001])}
    bottom = {"o9": 0.0, "o11": 0.0}
    assert T.marker_contacts(pos, bottom, "o11") == {frozenset({"o9", "o11"})}
    far = {**pos, "o9": np.array([0.40, -0.26, 0.035])}  # 5.1 cm off the marker centre
    assert T.marker_contacts(far, bottom, "o11") == set()
    assert T.marker_contacts(pos, {**bottom, "o9": 0.01}, "o11") == set()  # lowest point 1 cm above the table


def test_lowest_point_of_a_tilted_mug_is_its_rim():
    up = (1.0, 0.0, 0.0, 0.0)
    assert T.lowest_z("o3", [0.4, -0.2, 0.0475], up) == pytest.approx(0.0)
    th = math.radians(20)
    q = (math.cos(th / 2), math.sin(th / 2), 0.0, 0.0)  # 20 deg about x
    z = 0.0475 * math.cos(th) + 0.032 * math.sin(th)  # centre height when the rim touches
    assert T.lowest_z("o3", [0.4, -0.2, z], q) == pytest.approx(0.0, abs=1e-12)
    assert z - 0.0475 > 0.004  # the untilted "bottom" would read > 4 mm above the table (DEV mug_marker seeds 1, 3)
    assert T.lowest_z("o9", [0, 0, 0.035], up) == pytest.approx(0.0)


def test_stage_texts_and_names():
    s = T.TASKS["box_marker"]
    assert s.stage_text == {"S1": "pick up box o9", "S2": "place box o9 on marker o11"}
    st = T.stages(s)
    assert st["S1"]["exit"] == "holding(o9) lifted(o9)" and st["S2"]["exit"] == "on(o9,o11)"
    assert st["S2"]["invariants"] == ["holding(o9)"]
    assert T.stages(T.TASKS["mug_tray"]) == {
        "S1": {"text": "pick up mug o3", "exit": "holding(o3) lifted(o3)", "invariants": []},
        "S2": {"text": "place mug o3 on tray o5", "exit": "on(o3,o5)", "invariants": ["holding(o3)"]}}
