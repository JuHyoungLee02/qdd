"""E-SR1d (prereg_sr1d): the gripper-event authority proxy and the kinematic branch chunk / validity checks of
harvest/train/sr1d_kin.py."""
import numpy as np

from harvest.train import sr1c_branch as B
from harvest.train import sr1d_kin as K


def test_events_are_the_first_frames_of_new_closed_or_open_states():
    g = [0.1, 0.1, 0.8, 1.0, 1.0, 0.3, 0.1]
    assert K.gripper_events(g) == [(2, "close"), (5, "open")]
    assert K.gripper_events([0.1] * 5) == []


def test_contact_mask_marks_moving_gripper_and_event_windows():
    g = np.array([0.1] * 10 + [1.0] * 10)
    m = K.contact_mask(g, K.gripper_events(g), win=2)
    assert m[8:13].all() and not m[:8].any() and not m[13:].any()
    slow = np.linspace(0.1, 0.2, 20)  # 0.05 / s < GRIP_MOVE
    assert not K.contact_mask(slow, []).any()


def test_event_distance_uses_previous_and_next_event_points():
    ee = np.zeros((10, 3))
    ee[:, 0] = np.arange(10) * 0.05
    ev = [(2, "close"), (8, "open")]
    assert K.event_distance(ee, ev, 5) == 0.15  # |ee5 - ee2| = 0.15, |ee5 - ee8| = 0.15
    assert abs(K.event_distance(ee, ev, 7) - 0.05) < 1e-12
    assert K.event_distance(ee, [], 3) is None


def test_authority_proxy_contact_near_band_far_unknown():
    assert K.authority_proxy(0.5, True) == 0.0
    assert K.authority_proxy(0.04, False) == 0.0
    assert abs(K.authority_proxy(0.075, False) - 0.5) < 1e-12
    assert K.authority_proxy(0.2, False) == 1.0
    assert K.authority_proxy(None, False) is None
    assert K.stratum(None) == "unknown" and K.stratum(1.0) == "far"


def test_grasp_height_is_the_close_event_height_while_closed():
    g = [0.1, 0.9, 0.9, 0.1]
    ee = np.array([[0, 0, 0.3], [0, 0, 0.1], [0, 0, 0.2], [0, 0, 0.25]])
    assert K.grasp_height(g, ee, 2) == 0.1
    assert K.grasp_height(g, ee, 3) is None


def _fixture():
    import importlib.util
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_sr1c_branch.py")
    spec = importlib.util.spec_from_file_location("_sr1c_branch_fixture", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


URDF = _fixture().URDF  # ffw_bg2_rev4_follower right arm chain + limits (E-SR1c test fixture)


def _chain():
    from harvest.train.se2e_data import load_arm_chain
    return load_arm_chain(URDF, "right")


def test_ik_chunk_moves_straight_along_the_forced_direction():
    chain = _chain()
    lim = B.joint_limits(URDF, "right")
    q0 = np.array([0.4, -0.3, 0.1, -1.6, -0.1, -0.1, 0.05])
    u = B.direction("plus_y", "none_z")
    Q, info = K.ik_chunk(chain, lim, q0, 0.04 * u, np.full(7, 0.2), H=5)
    p, _ = B.fk_pose(chain, Q)
    assert info["ok"] and K.dir_err_deg(p[-1] - p[0], u) < 1.0


def test_ik_chunk_respects_the_per_joint_step_cap():
    chain = _chain()
    lim = B.joint_limits(URDF, "right")
    q0 = np.array([0.4, -0.3, 0.1, -1.6, -0.1, -0.1, 0.05])
    cap = np.full(7, 0.001)
    Q, info = K.ik_chunk(chain, lim, q0, 0.08 * B.direction("plus_x", "none_z"), cap, H=5)
    assert np.all(np.abs(np.diff(Q, axis=0)) <= cap + 1e-12) and not info["ok"]


def test_dir_err():
    assert K.dir_err_deg([1, 0, 0], [1, 0, 0]) == 0.0
    assert abs(K.dir_err_deg([0, 1, 0], [1, 0, 0]) - 90.0) < 1e-9


def test_validity_checks_in_order():
    path = np.array([[0.4, -0.2, -0.3], [0.41, -0.2, -0.3], [0.42, -0.2, -0.3]])
    env = ([0.1, -0.6, -0.5], [0.7, 0.0, -0.1])
    other = np.array([[0.4, 0.2, -0.3]] * 3)
    kw = dict(env_lo=env[0], env_hi=env[1], other_path=other, speed_max=0.03, end_dist=0.2)
    assert K.validity(path, -0.4, None, **kw) is None
    assert K.validity(path, -0.29, None, **kw) == "table"
    assert K.validity(path, -0.4, -0.29, **kw) == "held_table"
    assert K.validity(path + [0, 0.3, 0], -0.4, None, **{**kw, "other_path": None}) == "envelope"
    assert K.validity(path, -0.4, None, **{**kw, "other_path": path + [0, 0.05, 0]}) == "other_arm"
    assert K.validity(path, -0.4, None, **{**kw, "speed_max": 0.005}) == "speed"
    assert K.validity(path, -0.4, None, **{**kw, "end_dist": 0.03}) == "near_end"


def test_cap_disp():
    d, s = K.cap_disp(np.array([0.1, 0, 0]), 0.05)
    assert np.allclose(d, [0.05, 0, 0]) and s == 0.5
    d, s = K.cap_disp(np.array([0.01, 0, 0]), 0.05)
    assert s == 1.0
