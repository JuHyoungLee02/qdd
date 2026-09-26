"""AIWorkerEmbodiment.camera_models() (Astra-VLA coupling plan Task 8 Step 6): the live camera-model adapter that
reuses the E-Astra-motion probe's camera_pose (P40, world_isaac.py) and feeds obs["cams"] for harvest/couple/overlay.py.

(An earlier revision of this file also covered a since-removed AIWorkerEmbodiment.ee_sim() -- controller ruling O1
proposed exposing kin.tcp_pose() as "the simulator's own EE/TCP position" comparable to R2's/MolmoAct's "tcp" label
and the URDF-FK residual G-fk measured; review ruling O1b found kin.tcp_pose() is actually the PAD-CENTRE TCP the
planner/IK targets, a different point from env.finger_mid() (R2's "tcp", what G-fk actually compared FK against;
the two differ ~7.8 mm, docs/stage3/results/r5_closed_loop.md), so ee_sim added no information kin didn't already
provide and was removed along with its tests; see harvest/runtime/aiworker.py's docstrings for the corrected facts.)

No Isaac needed: harvest.runtime.aiworker imports cleanly stand-alone (all Isaac-only calls are lazy, inside
methods), so this stubs env/robot/K on a bare AIWorkerEmbodiment via object.__new__ and monkeypatches the three
lazily-imported functions (camera_pose, load_realcam, camera_table)."""
import numpy as np

from harvest.runtime.aiworker import AIWorkerEmbodiment, _camera_model_dict


def test_camera_model_dict_shape_and_types():
    R = np.eye(3) * 2.0  # any array-like, incl. non-float / non-list, must round-trip through asarray
    t = [1, 2, 3]
    K = np.array([[100, 0, 80], [0, 100, 60], [0, 0, 1]])
    d = _camera_model_dict(R, t, K, 160, 120)
    assert set(d) == {"K", "R", "t", "W", "H"}
    assert d["K"] == K.tolist() and d["R"] == R.tolist() and d["t"] == [1.0, 2.0, 3.0]
    assert d["W"] == 160 and d["H"] == 120 and isinstance(d["W"], int) and isinstance(d["H"], int)


class _StubRobot:
    pass


def _make_embodiment(cameras=("cam_head", "cam_wrist_right")):
    e = object.__new__(AIWorkerEmbodiment)
    e.cameras = cameras
    e.env = type("E", (), {"robot": _StubRobot()})()
    e.K = {n: np.array([[100.0, 0, 80], [0, 100.0, 60], [0, 0, 1]]) for n in cameras}
    return e


def test_camera_models_shape_matches_cams_obs_contract(monkeypatch):
    e = _make_embodiment()
    poses = {"cam_head": (np.eye(3), np.array([0.0, 0.0, 1.2])),
             "cam_wrist_right": (np.diag([1.0, -1.0, -1.0]), np.array([0.3, -0.1, 0.9]))}
    rows = {"cam_head": {"name": "cam_head", "width": 672, "height": 376},
            "cam_wrist_right": {"name": "cam_wrist_right", "width": 424, "height": 240}}

    def fake_camera_pose(robot, realcam, name):
        assert robot is e.env.robot and realcam == "REALCAM"
        return poses[name]

    monkeypatch.setattr("harvest.astra_motion.world_isaac.camera_pose", fake_camera_pose)
    monkeypatch.setattr("harvest.sim.scene.load_realcam", lambda: "REALCAM")
    monkeypatch.setattr("harvest.sim.scene.camera_table", lambda: list(rows.values()))

    out = e.camera_models()
    assert set(out) == {"cam_head", "cam_wrist_right"}
    for n in out:
        assert set(out[n]) == {"K", "R", "t", "W", "H"}
        assert out[n]["W"] == rows[n]["width"] and out[n]["H"] == rows[n]["height"]
        assert out[n]["R"] == poses[n][0].tolist() and out[n]["t"] == poses[n][1].tolist()
        assert out[n]["K"] == e.K[n].tolist()


def test_camera_models_is_not_evaluated_eagerly_in_obs_extra(monkeypatch):
    """Only the callable is stored in extra (evaluated when an Astra request goes out, not on every _obs call)."""
    calls = []

    def fake_camera_pose(robot, realcam, name):
        calls.append(name)
        return np.eye(3), np.zeros(3)

    e = _make_embodiment(cameras=("cam_head",))
    monkeypatch.setattr("harvest.astra_motion.world_isaac.camera_pose", fake_camera_pose)
    monkeypatch.setattr("harvest.sim.scene.load_realcam", lambda: "REALCAM")
    monkeypatch.setattr("harvest.sim.scene.camera_table", lambda: [{"name": "cam_head", "width": 1, "height": 1}])

    extra = {"cams": e.camera_models}
    assert calls == []  # storing the bound method must not call it
    out = extra["cams"]()
    assert calls == ["cam_head"] and set(out) == {"cam_head"}
