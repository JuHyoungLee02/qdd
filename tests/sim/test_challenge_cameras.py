"""v2 scene cameras = humanoid-challenge-env FFW_SG2_REAL_cameras.py, copied verbatim (no Isaac needed)."""
import hashlib
import math

import pytest

from harvest.sim.scene import (
    CHALLENGE_SCRIPTS, DEFAULT_CAMERAS, KNOWN_CAMERAS, RECORD_CAMERAS, _sim_device, camera_table, load_realcam,
)

# sha256 of the copied files at kairobahq/humanoid-challenge-env@523ea8e8ebcd (see third_party/.../NOTICE.md)
SHA = {
    "FFW_SG2_REAL_cameras.py": "5b71adc52bd6c22a78964de78c0b86e5ff2196ace784690a37ae7404234e478f",
    "taskC/taskC_ffw_sg2.py": "a5a6bbef929b47f36e324cb0472c595d4ec44eddea2997157432f34440a62462",
}


@pytest.mark.parametrize("rel", sorted(SHA))
def test_copied_files_unmodified(rel):
    assert hashlib.sha256((CHALLENGE_SCRIPTS / rel).read_bytes()).hexdigest() == SHA[rel]


def test_default_and_recorded_cameras():
    assert KNOWN_CAMERAS == ("cam_head", "cam_wrist_left", "cam_wrist_right")
    assert DEFAULT_CAMERAS == ("cam_head", "cam_wrist_left", "cam_wrist_right")
    assert RECORD_CAMERAS == ("cam_head", "cam_wrist_right")


def test_fx_from_hfov():
    rc = load_realcam()
    assert rc._fx_from_hfov(424, 87.0) == pytest.approx(223.40, abs=0.01)
    assert rc._fx_from_hfov(672, 2 * math.degrees(math.atan(336 / 367.0))) == pytest.approx(367.0)


def test_camera_table_values():
    t = {r["name"]: r for r in camera_table()}
    h, w = t["cam_head"], t["cam_wrist_right"]
    assert (h["width"], h["height"], h["fx"], h["parent"]) == (672, 376, 367.0, "head_link2")
    assert h["hfov_deg"] == pytest.approx(84.95, abs=0.01) and h["vfov_deg"] == pytest.approx(54.25, abs=0.01)
    assert (w["width"], w["height"], w["parent"]) == (424, 240, "arm_r_link7")
    assert w["fx"] == pytest.approx(223.40, abs=0.01) and w["hfov_deg"] == pytest.approx(87.0)
    assert w["vfov_deg"] == pytest.approx(56.49, abs=0.01)
    assert h["clip_m"] == (0.1, 100.0) and w["clip_m"] == (0.03, 100.0)


def test_mount_transforms():
    rc = load_realcam()
    head = rc.mount_transform("cam_head")
    assert head == pytest.approx([0.0238122, 0.0249820, -0.0109594, 1.0, 0.0, 0.0, 0.0])
    r, l = rc.mount_transform("cam_wrist_right"), rc.mount_transform("cam_wrist_left")
    assert r == pytest.approx(l)  # same numbers on both arms (URDF, not mirrored)
    assert math.fsum(v * v for v in r[3:]) == pytest.approx(1.0)
    # independent check: URDF R = Ry(1.66678943569) Rx(-pi/2) applied to camera_link's (0.01085, 0.009, 0.021)
    import numpy as np
    a, b = -np.pi / 2, 1.66678943569
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    t = np.array([0.108236, -0.021, -0.062552]) + Ry @ Rx @ np.array([0.01085, 0.009, 0.021])
    assert r[:3] == pytest.approx(t.tolist(), abs=1e-9)
    w, x, y, z = r[3:]  # quaternion -> matrix equals Ry Rx
    Rq = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                   [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                   [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    assert np.allclose(Rq, Ry @ Rx, atol=1e-9)


def test_sim_device_choice():
    assert _sim_device("cpu") == "cpu"
    assert _sim_device("cuda") == "cuda:0" and _sim_device("cuda:0") == "cuda:0"
    with pytest.raises(ValueError):
        _sim_device("cuda:2")
