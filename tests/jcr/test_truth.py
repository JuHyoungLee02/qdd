import numpy as np

from harvest.jcr import truth as T


def test_project_inside_ball_keeps_true_point():
    c, mis = T.project_ball([0.41, 0.0, 0.9], [0.40, 0.0, 0.9], 0.03)
    assert np.allclose(c, [0.41, 0.0, 0.9]) and not mis


def test_project_outside_ball_stops_at_boundary_and_flags():
    c, mis = T.project_ball([0.50, 0.0, 0.9], [0.40, 0.0, 0.9], 0.03)
    assert np.allclose(c, [0.43, 0.0, 0.9]) and mis


def _run(p0, c, n=200, **kw):
    p, v = np.asarray(p0, float), np.zeros(3)
    path = [p]
    for _ in range(n):
        P, v = T.smooth_chunk(p, v, c, **kw)
        p = P[0]
        path.append(p)
    return np.array(path)


def test_chunk_shape_and_first_row_is_one_step_ahead():
    P, v = T.smooth_chunk([0.4, 0, 0.9], np.zeros(3), [0.5, 0, 0.9])
    assert P.shape == (T.H, 3)
    assert 0 < np.linalg.norm(P[0] - [0.4, 0, 0.9]) <= T.A_MAX * T.DT * T.DT + 1e-9


def test_chunk_respects_speed_and_accel_limits():
    path = _run([0.4, 0, 0.9], [0.6, -0.1, 0.8])
    v = np.linalg.norm(np.diff(path, axis=0), axis=1) / T.DT
    a = np.abs(np.diff(v)) / T.DT
    assert v.max() <= T.V_MAX + 1e-9
    assert a.max() <= T.A_MAX + 1e-6


def test_chunk_arrives_without_overshoot():
    c = np.array([0.5, 0.0, 0.9])
    path = _run([0.4, 0, 0.9], c)
    assert np.linalg.norm(path[-1] - c) < 1e-4
    assert path[:, 0].max() <= c[0] + 1e-9


def test_chunk_at_goal_is_still():
    P, v = T.smooth_chunk([0.5, 0, 0.9], np.zeros(3), [0.5, 0, 0.9])
    assert np.allclose(P, [0.5, 0, 0.9]) and np.allclose(v, 0)


def test_chunk_stop_decelerates_smoothly():
    P, v = T.smooth_chunk([0.5, 0, 0.9], np.array([0.08, 0, 0]), [0.5, 0, 0.9], stop=True)
    steps = np.linalg.norm(np.diff(np.vstack([[0.5, 0, 0.9], P]), axis=0), axis=1)
    assert steps[0] > 0 and steps[-1] < 1e-9 and np.all(np.diff(steps) <= 1e-12)


def test_grip_event_only_in_allowed_direction_and_at_arrival():
    assert T.grip_event("close", [0.5, 0, 0.9], [0.5, 0, 0.9]) == "close"
    assert T.grip_event("close", [0.5, 0, 0.95], [0.5, 0, 0.9]) == "keep"
    assert T.grip_event(None, [0.5, 0, 0.9], [0.5, 0, 0.9]) == "keep"
    assert T.grip_event("open", [0.5, 0, 0.9], [0.5, 0, 0.9]) == "open"


def test_anomaly_kinds():
    k = T.anomaly_kinds(touched={"o5"}, tgt="o3", holding=False, was_holding=False, grip_cmd_closed=False,
                        tgt_shift_m=0.0, mismatch=False, tgt_z=0.9, table_z=0.8, upright=True)
    assert k == {"unexpected_contact"}
    k = T.anomaly_kinds(touched=set(), tgt="o3", holding=False, was_holding=True, grip_cmd_closed=True,
                        tgt_shift_m=0.03, mismatch=True, tgt_z=0.7, table_z=0.8, upright=False)
    assert k == {"dropped", "target_moved", "cmd_mismatch", "unrecoverable"}
