"""Scripted low-level executor: straight-line minimum-jerk moves to absolute TCP targets, then the gripper action."""
import numpy as np

from harvest.astra_solo.executor import MinJerkExec

TZ = 0.85


def run(ex, tcp_follows=True, t_max=20.0):
    t, tcp, evs, cmds = 0.0, ex.cmd.copy(), [], []
    while ex.busy and t < t_max:
        cmd, w, ev = ex.tick(t, tcp)
        evs += ev
        cmds.append(cmd.copy())
        if tcp_follows:
            tcp = cmd.copy()
        t += ex.dt
    return t, np.array(cmds), evs


def test_reaches_target_with_zero_end_velocity():
    ex = MinJerkExec(0.05, TZ, [0.35, -0.25, TZ + 0.25], 0.107, 0.05)
    ex.go_to([0.45, -0.20, TZ + 0.12], "keep", 0.0)
    t, c, ev = run(ex)
    assert np.allclose(c[-1], [0.45, -0.20, TZ + 0.12], atol=1e-6)
    v = np.linalg.norm(np.diff(c, axis=0), axis=1) / 0.05
    assert v[0] < 0.02 and v[-1] < 0.02 and v.max() <= 1.9 * 0.08 + 1e-6  # min-jerk peak = 1.875 x average
    assert any(e["event"] == "reach" for e in ev)


def test_target_outside_the_box_is_clipped_and_reported():
    ex = MinJerkExec(0.05, TZ, [0.35, -0.25, TZ + 0.25], 0.107, 0.05)
    ev = ex.go_to([0.90, -0.20, TZ - 0.10], "keep", 0.0)
    assert ev and ev[0]["event"] == "clipped"
    _, c, _ = run(ex)
    assert c[-1][0] <= 0.65 + 1e-9 and c[-1][2] >= TZ + 0.025 - 1e-9


def test_gripper_acts_after_arrival():
    ex = MinJerkExec(0.05, TZ, [0.35, -0.25, TZ + 0.25], 0.107, 0.05)
    ex.go_to([0.40, -0.25, TZ + 0.20], "close", 0.0)
    _, _, ev = run(ex)
    kinds = [e["event"] for e in ev]
    assert kinds.index("reach") < kinds.index("close") < kinds.index("gripper_done")
    assert ex.width == 0.05


def test_relative_edit_starts_from_the_commanded_reference():
    ex = MinJerkExec(0.05, TZ, [0.35, -0.25, TZ + 0.25], 0.107, 0.05)
    ex.go_to([0.40, -0.25, TZ + 0.20], "keep", 0.0)
    run(ex)
    lagging = np.array([0.40, -0.25, TZ + 0.19])  # the arm sags 1 cm under load
    ex.move_by([0.0, 0.05, 0.0], "keep", 5.0, lagging)
    assert np.allclose(ex.target, [0.40, -0.20, TZ + 0.20])


def test_blocked_arm_ends_as_timeout():
    ex = MinJerkExec(0.05, TZ, [0.35, -0.25, TZ + 0.25], 0.107, 0.05)
    ex.go_to([0.35, -0.25, TZ + 0.05], "keep", 0.0)
    _, _, ev = run(ex, tcp_follows=False)
    assert ev[-1]["event"] == "timeout"
