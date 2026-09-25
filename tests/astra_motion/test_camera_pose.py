"""Camera pose from the live parent-link pose x the copied mount transform (world_isaac.camera_pose), no Isaac."""
import math

import numpy as np

from harvest.astra_motion import geometry as G
from harvest.astra_motion import world_isaac as WI
from harvest.sim.scene import load_realcam


class _T:
    def __init__(self, a):
        self.a = np.asarray(a, float)

    def __getitem__(self, i):
        return _T(self.a[i])

    def cpu(self):
        return self

    def numpy(self):
        return self.a


class _Robot:
    def __init__(self, names, pos, quat):
        self.body_names = names

        class D:
            pass
        self.data = D()
        self.data.body_pos_w = _T([pos])
        self.data.body_quat_w = _T([quat])


def test_world_to_optical_matches_isaac_ros_of_identity():
    assert np.allclose(WI.WORLD_CONV_TO_OPTICAL, G.quat_to_R((0.5, -0.5, 0.5, -0.5)))  # Isaac quat_w_ros (dump)


def test_head_camera_pitched_link():
    rc = load_realcam()
    pitch = 0.69  # link pitched down about its y axis
    q = (math.cos(pitch / 2), 0.0, math.sin(pitch / 2), 0.0)
    rob = _Robot(["base", "head_link2"], [[0, 0, 0], [0.1, 0.0, 1.5]], [[1, 0, 0, 0], q])
    R, t = WI.camera_pose(rob, rc, "cam_head")
    z = R[:, 2]  # optical axis: forward and down by the pitch
    assert abs(math.degrees(math.asin(-z[2])) - math.degrees(pitch)) < 1e-6 and z[0] > 0
    assert abs(R[:, 0] @ [0, -1, 0] - 1) < 1e-9  # image right = robot right (-y)
    off = np.asarray(rc.mount_transform("cam_head")[:3])
    assert np.allclose(t, np.array([0.1, 0.0, 1.5]) + G.quat_to_R(q) @ off)
    assert abs(np.linalg.det(R) - 1) < 1e-9
