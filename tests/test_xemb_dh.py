import json

import numpy as np

from tools.xemb.dh import converter, encode_depth, rows


def test_converter_inverts_projection():
    K = np.array([[300.0, 0, 128], [0, 300.0, 128], [0, 0, 1]])
    T = np.eye(4)
    T[:3, 3] = [0.1, 0.2, 0.3]
    depth = np.full((256, 256), 0.8)
    p_cam = np.array([0.05, -0.02, 0.8])
    uv = K @ p_cam / p_cam[2]
    xb = converter(K, T, depth, uv[:2])
    assert np.allclose(xb, p_cam + [0.1, 0.2, 0.3], atol=1e-6)


def test_encode_depth_range():
    g = encode_depth(np.array([[0.25, 1.60, 2.0, np.nan]]))
    assert g[0, 0] == 255 and g[0, 1] == 1 and g[0, 2] == 0 and g[0, 3] == 0


def test_rows_answers():
    robot = {"name": "panda", "source": "maniskill/panda"}
    d, h = rows(robot, 256, 256, np.eye(3), np.eye(4), [128, 64], [0.1, 0.2, 0.3], "red cube", ["a", "b"], "r")
    assert json.loads(d["answer"]) == {"point_2d": [500, 250], "height": "grasp"}
    assert json.loads(h["answer"])["position_m"] == [0.1, 0.2, 0.3]
    assert "frame: base_panda" in d["prompt"] and "position_m" not in d["answer"]
