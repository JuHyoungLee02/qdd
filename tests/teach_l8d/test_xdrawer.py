"""L8-X drawer truth plan and judge (pure; prereg_l8x_tasks 2.4)."""
import numpy as np

from harvest.teach_l8d import xdrawer as XD

W_OPEN = 0.107


def run(h0=(0.52, -0.22, 0.90), u=(-1.0, 0.0, 0.0), n=200, stick=True, clear_z=1.05):
    """Toy world: the TCP goes to each command; a closed gripper on the handle drags the handle (drawer) along u."""
    tcp, w, q = np.array([0.34, -0.25, 1.10]), W_OPEN, 0.0
    h0, u = np.asarray(h0, float), np.asarray(u, float)
    info = {"pull_dir": u, "open_target": 0.20, "clear_z": clear_z}
    low_off = 0
    steps = []
    for _ in range(n):
        h = h0 + u * q
        step, cmd = XD.plan_drawer({"tcp": tcp, "grip_w": w, "handle": h, "joint": q}, info, W_OPEN)
        steps.append(step)
        assert not (cmd["mode"] == "eef" and cmd.get("gripper") == "close"), "closing while moving (change 9)"
        if cmd["mode"] == "stop":
            break
        if cmd.get("gripper") == "close":
            w = 0.01  # closed on a ~1 cm bar
        elif cmd.get("gripper") == "open":
            w = cmd.get("width_m", W_OPEN)
        if cmd["mode"] == "eef":
            new = np.array(cmd["position_m"], float)
            if step == "pull" and stick:
                q = max(q, float((new - h0) @ u))
            if np.linalg.norm(new[:2] - h[:2]) > XD.NEAR_XY and new[2] < clear_z - 0.03 and step != "retreat":
                low_off += 1
            tcp = new
    assert low_off == 0, "approach dipped below the clear height away from the handle"
    return steps, q, w


def test_plan_opens_the_drawer_and_releases():
    steps, q, w = run()
    assert steps[-1] == "done" and q >= 0.2 - XD.OPEN_TOL and w == XD.PRESHAPE_W
    assert [s for s in XD.STEPS if s in steps] == list(XD.STEPS)
    assert XD.success_drawer(q, w, W_OPEN, 0.0) and not XD.success_drawer(0.1, w, W_OPEN, 0.0)
    assert not XD.success_drawer(q, 0.01, W_OPEN, 0.0) and not XD.success_drawer(q, w, W_OPEN, 0.05)


def test_slipping_handle_reopens_and_regrasps():
    steps, q, _ = run(stick=False, n=60)  # the drawer never follows: the plan keeps pulling from the handle
    assert "pull" in steps and q == 0.0


def test_list_and_ids():
    js = {"Dresser_1": {"handles": [{"prim": "Dresser_1_drawer_1_handle_PrimitiveCollider_2", "ok": True, "top_z": 0.8, "size": [0.01, 0.3, 0.01],
                                     "standoff_m": 0.03},
                                    {"prim": "Dresser_1_drawer_1_handle_PrimitiveCollider_3", "ok": True, "top_z": 0.8, "size": [0.01, 0.3, 0.01],
                                     "standoff_m": 0.03},
                                    {"prim": "Dresser_1_drawer_3_handle_PrimitiveCollider_1", "ok": True,
                                     "top_z": 0.7, "standoff_m": 0.015},  # too close to the front (change 7)
                                    {"prim": "Dresser_1_drawer_2_handle_PrimitiveCollider_1", "ok": False,
                                     "top_z": 0.6}]}}
    lst = XD.drawer_list(js)
    assert lst == [("Dresser_1", "Dresser_1_drawer_1_handle", 0.8)]
    assert XD.task_id(*lst[0][:2]) == "dr__Dresser_1__Dresser_1_drawer_1_handle"
    assert XD.gate_pick(lst, 35390) == lst[0]
    assert XD.texts("pull")[0] == "pull the drawer open"


def test_front_plan_opens_the_drawer():
    """change 10: front grasp; the TCP never goes past the grasp point towards the piece (+x here)."""
    h0, u = np.array([0.50, -0.22, 0.94]), np.array([-1.0, 0.0, 0.0])
    tcp, w, q, steps = np.array([0.34, -0.25, 1.17]), W_OPEN, 0.0, []
    for _ in range(200):
        h = h0 + u * q
        step, cmd = XD.plan_drawer_front({"tcp": tcp, "grip_w": w, "handle": h, "joint": q},
                                         {"pull_dir": u, "open_target": 0.20}, W_OPEN)
        steps.append(step)
        assert not (cmd["mode"] == "eef" and cmd.get("gripper") == "close")
        if cmd["mode"] == "stop":
            break
        if cmd.get("gripper") == "close":
            w = 0.01
        elif cmd.get("gripper") == "open":
            w = cmd.get("width_m", W_OPEN)
        if cmd["mode"] == "eef":
            assert cmd["orient"] == "front"
            new = np.array(cmd["position_m"], float)
            assert float((new - h) @ u) >= XD.FRONT_GRASP - 1e-3  # never deeper than the grasp point
            if step == "pull":
                q = max(q, float((new - h0) @ u) - XD.FRONT_GRASP)
            tcp = new
    assert steps[-1] == "done" and q >= 0.2 - XD.OPEN_TOL
    assert [s for s in XD.STEPS_FRONT if s in steps] == list(XD.STEPS_FRONT)


def test_front_plan_seats_before_closing_and_keeps_a_released_drawer_done():
    """change 14: a TCP stopped 9 mm short / 9 mm low re-inserts past the grasp point; a released drawer that drifted
    back from 0.20 to 0.19 m is done (not re-grasped)."""
    h, u = np.array([0.52, -0.17, 0.94]), [-1.0, 0.0, 0.0]
    g = h + np.array(u) * XD.FRONT_GRASP
    info = {"pull_dir": u, "open_target": 0.20}
    st = {"tcp": g + np.array([-0.009, 0.0, -0.009]), "grip_w": XD.FRONT_W, "handle": h, "joint": 0.0}
    step, cmd = XD.plan_drawer_front(st, info, 0.107)
    assert step == "insert" and cmd["position_m"][0] > g[0] and cmd["position_m"][2] > g[2]
    st = dict(st, tcp=g + np.array([-0.003, 0.0, 0.002]))
    assert XD.plan_drawer_front(st, info, 0.107)[0] == "close"
    st = {"tcp": g + np.array([-0.2, 0.0, 0.0]), "grip_w": XD.FRONT_W, "handle": h - np.array([0.19, 0, 0]),
          "joint": 0.19}
    assert XD.plan_drawer_front(st, info, 0.107)[0] in ("retreat", "done")
