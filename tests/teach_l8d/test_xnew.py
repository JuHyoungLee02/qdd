"""L8-X new tasks (prereg_l8x_tasks.md): registration, eligibility, name gate, push truth plan, judges (pure)."""
import copy

import numpy as np

from harvest.sim import objv
from harvest.sim import scene as SC
from harvest.sim import tasks as T
from harvest.teach_l8d import xnew as XN


def row(k, name, h=0.08, w=0.05, L=0.07, top=None, noun="cup", colour=None, split="train", circ=0.95, box=0.3):
    return {"uid": k, "name": name, "task_name": name, "noun": noun, "colour": colour,
            "name_check": {"claimed": noun, "noun": noun, "renamed": False, "reasons": []},
            "task_target_ok": True, "pose": "upright", "split": split, "height": h, "grasp_width": w, "length": L,
            "half_extents": [w / 2, L / 2, h / 2], "footprint_r": float(np.hypot(w, L) / 2), "circularity": circ,
            "boxiness": box, "sphericity": 0.2, "usd_physics": f"/x/{k}.usda", "body_rel": "",
            "spawn_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "root_above_bottom": 0.0, "centre_from_root_xy": [0.0, 0.0],
            "mass": 0.2, "category": noun, "license": "CC BY 4.0", "top_surface": top}


ROWS = {"gso_cup": row("gso_cup", "red cup", w=0.06, colour="red"),
        "gso_box": row("gso_box", "white box", h=0.05, w=0.12, L=0.16, noun="box", colour="white", circ=0.6, box=0.9,
                       top={"top_z": 0.05, "box": [[-0.055, 0.055], [-0.075, 0.075]], "area": 0.0165}),
        "gso_toy": dict(row("gso_toy", "toy", noun="object"), task_target_ok=False),
        "gso_ood": row("gso_ood", "blue can", w=0.06, split="ood_o", noun="can", colour="blue")}


def test_eligibility_and_frozen_lists():
    assert XN.target_ok(ROWS["gso_cup"]) and not XN.target_ok(ROWS["gso_ood"])
    assert XN.base_ok(ROWS["gso_box"], ROWS["gso_cup"]) and not XN.base_ok(ROWS["gso_cup"], ROWS["gso_box"])
    assert XN.stack_pairs(ROWS) == [("gso_cup", "gso_box"), ("gso_cup", "o12")]
    egg = dict(ROWS["gso_cup"], noun="egg")
    assert XN.target_ok(egg) and not XN.stack_top_ok(egg)
    assert XN.instruction(XN.stack_task_id("gso_cup", "o12"), ROWS, 0) == "Put the red cup on the white stand."
    assert XN.name_gate(XN.stack_task_id("gso_cup", "o12"), ROWS) is None
    assert "gso_cup" in XN.push_objects(ROWS) and "gso_ood" not in XN.push_objects(ROWS)
    assert XN.push_objects(ROWS, "ood_o") == ["gso_ood", "o14"]  # + the held-out small red cup


def test_register_new_tasks_and_objv_body_rel():
    t1, t2 = XN.stack_task_id("gso_cup", "gso_box"), XN.push_task_id("gso_cup")
    ids = XN.register_new_tasks([t1, t2, "mug_tray"], ROWS)
    assert ids == ["gso_box", "gso_cup"]
    assert T.TASKS[t1].target == "gso_cup" and T.TASKS[t1].place == "gso_box"
    assert T.TASKS[t1].instruction == "Put the red cup on the white box."
    assert T.TASKS[t2].place == XN.MARKER and 7000 <= T.X_TASK_CODE[t2] < 7900 and 6000 <= T.X_TASK_CODE[t1] < 6900
    assert SC.OBJ_GEOM["gso_cup"]["body_rel"] == ""  # the row's body_rel (GSO: the root is the rigid body)
    code = dict(T.X_TASK_CODE)
    XN.register_new_tasks([t1, t2], ROWS)
    assert T.X_TASK_CODE == code  # idempotent
    g = objv.geom({**{k: v for k, v in ROWS["gso_cup"].items() if k != "body_rel"}, "uid": "abc"})
    assert g["body_rel"] == "Geometry/obja_abc"  # default (Objaverse rows) unchanged


def test_texts_and_ood_phrasings():
    t = XN.stack_task_id("gso_cup", "gso_box")
    idx = {XN.text_index(t, s) for s in range(200)}
    assert idx.isdisjoint(XN.STACK_OOD_TEXTS) and len(idx) > 6
    assert {XN.text_index(t, s, ood=True) for s in range(50)} <= set(XN.STACK_OOD_TEXTS)
    assert XN.instruction(XN.push_task_id("gso_cup"), ROWS, 0) == "Push the red cup onto the magenta marker."


def test_name_gate():
    assert XN.name_gate(XN.stack_task_id("gso_cup", "gso_box"), ROWS) is None
    assert "no checked noun" in XN.name_gate(XN.push_task_id("gso_toy"), ROWS)
    assert "also called" in XN.name_gate(XN.push_task_id("gso_cup"), ROWS, present_names=["red cup"])
    bad = copy.deepcopy(ROWS)
    bad["gso_cup"]["task_name"] = "green cup"
    assert "colour" in XN.name_gate(XN.push_task_id("gso_cup"), bad)


def _sim_push(start_obj, marker, n=80):
    """Toy world: the TCP goes to each command; a low TCP moving through the object's disc pushes the centre along."""
    XN.register_new_tasks([XN.push_task_id("gso_cup")], ROWS)
    r = SC.OBJ_GEOM["gso_cup"]["footprint_r"]
    obj, tcp, grip = np.array(start_obj, float), np.array([0.34, -0.25, 1.10]), 0.107
    info = {"tgt": "gso_cup", "place": XN.MARKER, "sup_tgt": 0.85}
    steps = []
    for _ in range(n):
        st = {"tcp": tcp, "grip_w": grip, "obj": {"gso_cup": obj.copy(), XN.MARKER: np.array(marker, float)},
              "pred": {"on(gso_cup,o11)": bool(np.linalg.norm(obj[:2] - marker[:2]) <= 0.04),
                       "upright(gso_cup)": True, "holding(gso_cup)": False}}
        step, cmd = XN.plan_push(st, info, 0.85, 0.107)
        steps.append(step)
        if cmd is None or cmd["mode"] == "stop":
            break
        new = np.array(cmd["position_m"], float)
        if cmd["gripper"] == "close":
            grip = 0.033  # the executor closes to the object's close width, not shut (gate 35211: stuck at 3.3 cm)
        if new[2] <= 0.85 + 0.07:  # low: push the object if the path enters its disc
            d = new[:2] - obj[:2]
            if np.linalg.norm(d) < r:
                u = (new[:2] - tcp[:2]) / max(np.linalg.norm(new[:2] - tcp[:2]), 1e-9)
                obj[:2] = new[:2] + u * r
        tcp = new
    return steps, obj


def test_push_plan_reaches_the_marker():
    for start, mk in (([0.40, -0.30, 0.89], [0.40, -0.16, 0.851]), ([0.38, -0.20, 0.89], [0.50, -0.20, 0.851])):
        steps, obj = _sim_push(start, np.array(mk))
        assert steps[-1] == "done", steps
        assert np.linalg.norm(obj[:2] - np.array(mk[:2])) <= XN.PUSH_DONE_R + 1e-6
        assert {"above_start", "lower_behind", "push", "lift_away"} <= set(steps)


def test_judges():
    rows = [{"gt": {"place": [0.4, -0.2, 0.9], "tgt": [0.4, -0.3, 0.89]}},
            {"gt": {"place": [0.41, -0.2, 0.9], "tgt": [0.45, -0.3, 0.89]}}]
    assert XN.success_stack(rows) and XN.success_push(rows)
    rows[1]["gt"]["place"] = [0.45, -0.2, 0.9]
    rows[1]["gt"]["tgt"] = [0.45, -0.3, 0.95]  # lifted 6 cm: carried, not pushed
    assert not XN.success_stack(rows) and not XN.success_push(rows)
    assert XN.texts("push", "red cup", "magenta marker")[0] == "push the red cup onto the magenta marker"


def test_hooks_push_plan_layout_and_label():
    from harvest.teach_l8d import xlabels as XL
    t = XN.push_task_id("gso_cup")
    XN.register_new_tasks([t], ROWS)
    ws = ((0.36, 0.54), (-0.40, -0.06))
    for s in range(30):
        lay = T.x_task_layout(35210 + s, t, ws)
        m, p = np.array(lay["gso_cup"][:2]), np.array(lay[XN.MARKER][:2])
        d = p - m
        assert 0.10 - 1e-9 <= np.linalg.norm(d) <= 0.18 + 1e-9 and d[0] >= -1e-9 and d[1] >= -1e-9  # +x / +y
        assert ws[0][0] + 0.03 - 1e-9 <= p[0] <= ws[0][1] + 1e-9 and ws[1][0] + 0.03 - 1e-9 <= p[1] <= ws[1][1] - 0.03 + 1e-9
    st = {"tcp": np.array([0.34, -0.25, 1.1]), "grip_w": 0.107,
          "obj": {"gso_cup": np.array([0.40, -0.30, 0.89]), XN.MARKER: np.array([0.40, -0.16, 0.851])},
          "pred": {"on(gso_cup,o11)": False, "upright(gso_cup)": True, "holding(gso_cup)": False}}
    info = {"tgt": "gso_cup", "place": XN.MARKER, "kind": "push", "sup_tgt": 0.85, "present": ["gso_cup"]}
    assert XL.plan(st, info, 0.85, 0.107) == XN.plan_push(st, info, 0.85, 0.107)
    lab = XL.label(st, info, 0.85, 0.107, first=True)
    assert lab["step"] == "above_start" and "behind the red cup" in lab["answer"]


def test_gate_seeds_cover_the_new_task_gates():
    from harvest.teach_l8d import spec as S
    assert S.check_seed(35205, "gate") == 35205 and S.check_seed(35000, "gate") == 35000


def test_push_filter_excludes_tall_narrow_objects():
    tall = dict(ROWS["gso_cup"], height=0.095, grasp_width=0.047)  # the gate-2 bottles (tipped)
    assert not XN.push_ok(tall) and XN.push_ok(ROWS["gso_cup"])


def test_primitive_push_objects():
    assert {"o3", "o9", "o12", "o13"} <= set(XN.push_objects(ROWS)) and "o14" not in XN.push_objects(ROWS)
    assert XN.push_objects(ROWS, "ood_o") == ["gso_ood", "o14"] or XN.push_objects(ROWS, "ood_o")[-1] == "o14"
    t = XN.push_task_id("o9")
    XN.register_new_tasks([t], ROWS)
    assert T.TASKS[t].instruction == "Push the yellow box onto the magenta marker." and XN.name_gate(t, ROWS) is None


def test_parse_ids_ending_with_underscore():
    assert XN.parse("st__gso_Lavender_Snake_Tieks_Snake_Print_Ballet___o12") == \
        ("st", ["gso_Lavender_Snake_Tieks_Snake_Print_Ballet_", "o12"])
    assert XN.parse("st__a__b") == ("st", ["a", "b"]) and XN.parse("pu__gso_x_") == ("pu", ["gso_x_"])
