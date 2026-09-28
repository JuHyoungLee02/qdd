"""L8-X drawer truth plan and judge (pure; prereg_l8x_tasks 2.4)."""
import numpy as np

from harvest.teach_l8d import xdrawer as XD

W_OPEN = 0.107


def run(h0=(0.52, -0.22, 0.90), u=(-1.0, 0.0, 0.0), n=200, stick=True):
    """Toy world: the TCP goes to each command; a closed gripper on the handle drags the handle (drawer) along u."""
    tcp, w, q = np.array([0.34, -0.25, 1.10]), W_OPEN, 0.0
    h0, u = np.asarray(h0, float), np.asarray(u, float)
    info = {"pull_dir": u, "open_target": 0.20}
    steps = []
    for _ in range(n):
        h = h0 + u * q
        step, cmd = XD.plan_drawer({"tcp": tcp, "grip_w": w, "handle": h, "joint": q}, info, W_OPEN)
        steps.append(step)
        if cmd["mode"] == "stop":
            break
        if cmd.get("gripper") == "close":
            w = 0.02
        elif cmd.get("gripper") == "open":
            w = W_OPEN
        if cmd["mode"] == "eef":
            new = np.array(cmd["position_m"], float)
            if step == "pull" and stick:
                q = max(q, float((new - h0) @ u))
            tcp = new
    return steps, q, w


def test_plan_opens_the_drawer_and_releases():
    steps, q, w = run()
    assert steps[-1] == "done" and q >= 0.2 - XD.OPEN_TOL and w == W_OPEN
    assert [s for s in XD.STEPS if s in steps] == list(XD.STEPS)
    assert XD.success_drawer(q, w, W_OPEN, 0.0) and not XD.success_drawer(0.1, w, W_OPEN, 0.0)
    assert not XD.success_drawer(q, 0.02, W_OPEN, 0.0) and not XD.success_drawer(q, w, W_OPEN, 0.05)


def test_slipping_handle_reopens_and_regrasps():
    steps, q, _ = run(stick=False, n=60)  # the drawer never follows: the plan keeps pulling from the handle
    assert "pull" in steps and q == 0.0


def test_list_and_ids():
    js = {"Dresser_1": {"handles": [{"prim": "Dresser_1_drawer_1_handle_PrimitiveCollider_2", "ok": True, "top_z": 0.8},
                                    {"prim": "Dresser_1_drawer_1_handle_PrimitiveCollider_3", "ok": True, "top_z": 0.8},
                                    {"prim": "Dresser_1_drawer_2_handle_PrimitiveCollider_1", "ok": False,
                                     "top_z": 0.6}]}}
    lst = XD.drawer_list(js)
    assert lst == [("Dresser_1", "Dresser_1_drawer_1_handle", 0.8)]
    assert XD.task_id(*lst[0][:2]) == "dr__Dresser_1__Dresser_1_drawer_1_handle"
    assert XD.gate_pick(lst, 35390) == lst[0]
    assert XD.texts("pull")[0] == "pull the drawer open"
