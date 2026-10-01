import math

import numpy as np

from harvest.l9 import grasp9 as G
from harvest.l9 import gtest9 as T
from harvest.sim import objv

TABLE = {"width_m": [0.0023, 0.0137, 0.025, 0.0362, 0.0576, 0.077, 0.0937, 0.107],
         "drive_q": [1.1, 1.0, 0.9, 0.8, 0.6, 0.4, 0.2, 0.0]}
ROW = {"height": 0.12, "root_above_bottom": 0.06, "centre_from_root_xy": [0.01, -0.02],
       "spawn_quat_wxyz": [0.7071068, 0.7071068, 0.0, 0.0]}
TCP = (0.0, 0.0, -0.16711)


def test_euler_roundtrip():
    rng = np.random.default_rng(0)
    for _ in range(200):
        r, p, y = rng.uniform(-3, 3), rng.uniform(-1.5, 1.5), rng.uniform(-3, 3)
        R = T.rot_xyz(r, p, y)
        assert np.allclose(T.rot_xyz(*T.euler_xyz(R)), R, atol=1e-9)


def test_euler_unwrap_near_ref():
    R = T.rot_xyz(0.1, 0.2, math.pi - 0.01)
    r, p, y = T.euler_xyz(T.rot_xyz(0.1, 0.2, -math.pi + 0.02) @ np.eye(3), ref=(0.1, 0.2, math.pi - 0.01))
    assert abs(y - (math.pi + 0.02)) < 1e-9
    assert np.allclose(T.rot_xyz(r, p, y), T.rot_xyz(0.1, 0.2, -math.pi + 0.02))
    assert R.shape == (3, 3)


def test_vjoints_fk_and_no_gimbal_after_yaw():
    rng = np.random.default_rng(1)
    for _ in range(100):
        a = rng.normal(size=3)
        a[2] = -abs(a[2]) * rng.uniform(0, 1)
        a /= np.linalg.norm(a)
        c = np.cross(a, rng.normal(size=3))
        Tobj = T.pose(G.frame_of(a, c), rng.uniform(-0.03, 0.03, 3))
        yaw = T.yaw_for(a)
        assert abs((T.rz(yaw) @ a)[0]) < 1e-9
        centre = np.array([1.0, 2.0, 0.06])
        Tw = T.tcp_world(Tobj, yaw, centre)
        Tb = T.base_from_tcp(Tw, TCP)
        q = T.vjoints(Tb, origin=(1.0, 2.0, 0.0))
        assert abs(q[4]) < 1e-6  # p = 0 at the grasp
        assert np.allclose(T.fk(q, origin=(1.0, 2.0, 0.0)), Tb, atol=1e-9)
        # the TCP lies 16.7 cm along -z_base... i.e. along the approach from the base
        assert np.allclose(Tb[:3, 3] + 0.16711 * (T.rz(yaw) @ a), Tw[:3, 3], atol=1e-9)


def test_backoff_against_approach():
    a = np.array([0.0, 0.6, -0.8])
    Tw = T.pose(G.frame_of(a, [1.0, 0.0, 0.0]), [0.0, 0.0, 0.1])
    Tp = T.backoff(Tw, 0.06)
    assert np.allclose(Tp[:3, 3], Tw[:3, 3] - 0.06 * a)


def test_object_pose_matches_objv():
    c, q, root, qr = T.object_pose(ROW, 0.7, origin=(2.0, 0.0, 0.0))
    assert np.allclose(c, [2.0, 0.0, 0.06])
    c2, q2 = objv.canonical_from_root(ROW, root, qr)
    assert np.allclose(c2, c, atol=1e-9)
    assert np.allclose(np.abs(np.dot(q2, q)), 1.0, atol=1e-9)


def test_shake_and_about_point():
    assert np.allclose(T.shake_rot(0.0, 1.5), np.eye(3))
    angs = []
    for t in np.linspace(0, 1.5, 301):
        R = T.shake_rot(t, 1.5)
        angs.append(math.degrees(math.acos(max(-1, min(1, (np.trace(R) - 1) / 2)))))
    assert max(angs) <= 15.0 + 1e-6 and max(angs) > 14.0
    Tw = T.pose(np.eye(3), [0.3, 0.0, 0.2])
    c = np.array([0.3, 0.0, 0.1])
    Tr = T.about_point(Tw, T.rx(0.3), c)
    assert np.isclose(np.linalg.norm(Tr[:3, 3] - c), 0.1)


def test_width_table_inverse():
    for w in (0.01, 0.05, 0.09):
        assert abs(T.q_to_width(T.width_to_q(w, TABLE), TABLE) - w) < 1e-9
    assert T.width_to_q(0.107, TABLE) == 0.0 and T.width_to_q(0.0, TABLE) == 1.1


def test_pick_covers_groups():
    rng = np.random.default_rng(2)
    a = np.array([[0, 0, -1.0]] * 100 + [[0, 0.7071, -0.7071]] * 100 + [[0, 1.0, 0]] * 100)
    w = rng.uniform(0.005, 0.09, 300)
    s = rng.random(300)
    idx = T.pick(a, w, s, 48)
    assert len(idx) == 48 and len(set(idx)) == 48
    fams = {T.fam_obj(a[i]) for i in idx}
    wcs = {T.width_class(w[i]) for i in idx}
    assert fams == {"top", "oblique", "horizontal"} and wcs == {"narrow", "mid", "wide"}
    assert len(T.pick(a[:10], w[:10], s[:10], 48)) == 10


def test_verdict_rules():
    assert T.gap_class(0.001, 0.05) == "EMPTY"
    assert T.gap_class(0.045, 0.05) == "CONTACT"
    assert T.gap_class(0.07, 0.05) == "WIDE"
    ok = T.verdict(0.1, True, 0.04, 0.1, True, 0.04, 0.004)
    assert ok == {"lift_ok": True, "shake_ok": True}
    assert T.verdict(0.1, True, 0.04, 0.1, True, 0.04, 0.02)["shake_ok"] is False
    assert T.verdict(0.02, True, 0.04, 0.02, True, 0.04, 0.0)["lift_ok"] is False
    assert T.verdict(0.1, True, 0.001, 0.1, True, 0.001, 0.0)["lift_ok"] is False
    assert T.inside([0.0, 0.02, 0.0], 0.026, 0.107, (-0.0274, 0.0152))
    assert not T.inside([0.0, 0.0, 0.08], 0.026, 0.107, (-0.0274, 0.0152))


def test_plan_round_fk_follows_phases():
    rng = np.random.default_rng(3)
    N = 6
    Tw, origins = [], []
    for i in range(N):
        a = np.array([0.0, rng.uniform(0.2, 1.0), -rng.uniform(0.0, 1.0)])
        a /= np.linalg.norm(a)
        Tw.append(T.pose(G.frame_of(a, [1.0, 0.0, 0.0]), [i * 2.0, 0.0, 0.05]))
        origins.append([i * 2.0, 0.0, 0.0])
    Tw, origins = np.asarray(Tw), np.asarray(origins)
    q, st = T.plan_round(Tw, origins, TCP, 0.01)
    assert q.shape == (st["end"], N, 6)
    for i in range(N):
        tcp = lambda k: (T.fk(q[k, i], origins[i]) @ T.pose(np.eye(3), TCP))[:3, 3]
        a = -Tw[i, :3, 2]
        assert np.allclose(tcp(0), Tw[i, :3, 3] - 0.06 * a, atol=1e-9)  # pre-grasp
        assert np.allclose(tcp(st["close"]), Tw[i, :3, 3], atol=1e-9)  # at the grasp
        assert np.allclose(tcp(st["hold"]), Tw[i, :3, 3] + [0, 0, 0.1], atol=1e-9)
        for k in range(st["shake"], st["end"]):  # the shake turns about the lifted TCP
            assert np.allclose(tcp(k), Tw[i, :3, 3] + [0, 0, 0.1], atol=1e-9)
        assert np.abs(np.diff(q[:, i, 3:], axis=0)).max() < 0.05  # no euler jumps


def test_pick_natural_parts_first():
    rng = np.random.default_rng(4)
    a = np.array([[0, 0, -1.0]] * 200 + [[0, 1.0, 0]] * 20)
    w = np.r_[rng.uniform(0.04, 0.05, 200), rng.uniform(0.04, 0.05, 20)]
    part = ["body"] * 200 + ["rim"] * 20
    s = np.r_[np.ones(200), np.zeros(20)]
    idx = T.pick(a, w, s, 10, part=part, prefer={("horizontal", "rim"): 0})
    assert sum(part[i] == "rim" for i in idx) == 5  # two groups alternate, the natural one first


def test_parts_and_natural_rank():
    row = {"category": "bowl", "name": "white bowl", "half_extents": [0.08, 0.08, 0.03], "height": 0.06}
    c1 = np.array([[0.075, 0, 0.02], [0.0, -0.02, 0.0]])
    c2 = np.array([[0.083, 0, 0.02], [0.0, 0.02, 0.0]])
    p = T.parts(row, c1, c2, [0.008, 0.04])
    assert p[0] == "rim"
    r = T.natural_rank(row)
    assert r[("top", "rim")] == 0 and r[("horizontal", "rim")] == 2


def test_exec_pose_backs_off_by_pad_drop():
    a = np.array([0.0, 0.0, -1.0])
    Tg = T.pose(G.frame_of(a, [1.0, 0.0, 0.0]), [0.0, 0.0, 0.05])
    assert T.pad_drop(0.107, "ffw_sg2", TABLE) == 0.0
    d = T.pad_drop(0.025, "ffw_sg2", TABLE)
    assert abs(d - 0.0279) < 1e-9
    Te = T.exec_pose(Tg, 0.025, "ffw_sg2", TABLE)
    assert np.allclose(Te[:3, 3], [0.0, 0.0, 0.05 + d]) and np.allclose(Te[:3, :3], Tg[:3, :3])
    assert T.pad_drop(0.03, "franka", TABLE) == 0.0
    assert T.pad_drop(0.025, "ffw_sg2") == d  # table from assets9/grippers/ffw_sg2_right.json
    assert np.allclose(T.exec_pose(Tg, 0.03, "franka"), Tg)
