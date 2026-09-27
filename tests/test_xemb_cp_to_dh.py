import numpy as np

from tools.xemb.cp_to_dh import names_of, parse_cam, project


def test_parse_cam_and_project_roundtrip():
    p = ("- Image 1: head camera, 672x376 px, fx 367.0 fy 367.0 cx 336.0 cy 188.0; at (0.11, 0.02, 0.12) m, looking "
         "along (+0.84, -0.02, -0.54); image right = (-0.01, -1.00, +0.01), image down = (-0.54, -0.00, -0.84).")
    W, H, K, T = parse_cam(p)
    assert (W, H) == (672, 376) and K[0, 0] == 367.0
    x = T[:3, 3] + 0.8 * T[:3, 2]  # a point on the optical axis
    uv = project(K, T, x)
    assert np.allclose(uv, [336.0, 188.0], atol=1.0)


def test_names():
    assert names_of("lower to the red mug and close on it") == ("red mug", "red mug")
    assert names_of("carry the red mug above the blue tray") == ("red mug", "blue tray")
    assert names_of("lower the red mug onto the blue tray and release it") == ("red mug", "blue tray")
    assert names_of("move the TCP above the green bottle") == ("green bottle", "green bottle")
