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
                        tgt_shift_m=0.03, mismatch=True, tgt_z=0.7, table_z=0.8, upright=False, pads_empty=True)
    assert k == {"dropped", "target_moved", "cmd_mismatch", "unrecoverable"}


def test_holding_flicker_with_object_between_pads_is_not_dropped():
    k = T.anomaly_kinds(touched=set(), tgt="o3", holding=False, was_holding=True, grip_cmd_closed=True,
                        tgt_shift_m=0.0, mismatch=False, tgt_z=0.9, table_z=0.8, upright=True, pads_empty=False)
    assert "dropped" not in k


def test_prio_floor_and_shapes():
    assert abs(T.prio_w(1.0, "gauss", 0.03, 0.2) - 0.2) < 1e-9
    assert abs(T.prio_w(0.0, "gauss", 0.03, 0.2, 0.7) - 0.7) < 1e-9
    assert T.prio_w(0.03, "p4", 0.03, 0.0) == 0.5


def roll(p_true, g, prm, mode="B", n=80, lower=False, kappa=0.9):
    x, v, age = np.array([0.40, 0.0, 0.95]), np.zeros(3), 0.0
    for _ in range(n):
        R = T.mode_chunk(mode, x, v, p_true, g, kappa=kappa, age=age, lower=lower, prm=prm)
        x, v, age = R[3], (R[3] - R[2]) / T.DT, age + 4 * T.DT
    return x


def test_w_max_one_freezes_the_destination():
    g = np.array([0.45, 0.0, 0.93])
    e = roll(g + [0.01, 0, 0], g, dict(T.PRIO, w_max=1.0))
    assert np.linalg.norm(e - g) < 1e-3  # the literal w(0) = 1: no correction at all (change 3 note)


def test_default_blend_corrects_partly_and_lower_corrects_more():
    g = np.array([0.45, 0.0, 0.93])
    p = g + [0.01, 0, 0]
    e = roll(p, g, T.PRIO)
    e2 = roll(p, g, T.PRIO, lower=True)
    assert 0.001 < np.linalg.norm(e - g) < 0.009
    assert np.linalg.norm(e2 - g) > np.linalg.norm(e - g)


def test_blend_rows_limits_and_residual_bound():
    g = np.array([0.45, 0.0, 0.93])
    x0 = np.array([0.40, 0.0, 0.95])
    jr = T.smooth_chunk(x0, np.zeros(3), g + [0.0, 0.2, 0.0])[0]  # JCR wants to go far sideways
    prm = dict(T.PRIO, A=0.02, eps=0.005, t_ramp=0.5)
    R = T.blend_rows(x0, np.zeros(3), jr, g, prm, age=0.0)
    ra = T.blend_rows(x0, np.zeros(3), np.repeat(x0[None], T.H, 0), g, dict(prm, w_min=1.0, w_max=1.0), age=0.0)
    steps = np.diff(np.vstack([x0, R]), axis=0) / T.DT
    assert np.linalg.norm(steps, axis=1).max() <= T.V_BLEND + 1e-9
    for k in range(T.H):
        a_eff = prm["eps"] + (prm["A"] - prm["eps"]) * min(1.0, (k + 1) * T.DT / prm["t_ramp"])
        assert np.linalg.norm(R[k] - ra[k]) <= a_eff + 1e-6


def test_carry_stage_keeps_less_priority():
    rho_n, wm_n = T.stage_prio(T.PRIO, 0.9)
    rho_c, wm_c = T.stage_prio(T.PRIO, 0.3)
    assert wm_c < wm_n and rho_c < rho_n


def test_low_sideways_move_goes_over_the_target_first():
    path = _run([0.40, 0.0, 0.93], [0.46, 0.0, 0.93], n=400)
    far = np.linalg.norm(path[:, :2] - [0.46, 0.0], axis=1) > T.CLEAR_XY_M
    assert np.all(path[far, 2] >= 0.93 - 1e-9)
    assert path[far, 2].max() > 0.93 + 0.03
    assert np.linalg.norm(path[-1] - [0.46, 0.0, 0.93]) < 1e-4
