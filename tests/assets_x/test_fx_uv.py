"""UV render cube of the furniture cuboid slots (b4 textures; pure part of harvest.sim.assets_x.isaac)."""
import numpy as np

from harvest.sim.assets_x import isaac as I


def test_faces_point_outwards_and_cover_the_unit_cube():
    P, N, _ = I._cube_faces()
    P, N = np.asarray(P), np.asarray(N)
    assert P.shape == (24, 3) and np.allclose(np.abs(P), 0.5)
    for f in range(6):
        q = P[4 * f:4 * f + 4]
        n = np.cross(q[1] - q[0], q[2] - q[1])
        assert np.allclose(n / np.linalg.norm(n), N[4 * f])  # counter-clockwise seen from outside
        assert np.allclose(q.mean(0), 0.5 * N[4 * f])


def test_box_uv_is_in_metres_of_the_part():
    st = np.asarray(I.box_uv((2.0, 0.5, 0.04)))
    assert st.shape == (24, 2) and st.min() >= 0
    top = st[16:20]  # +z face: x (2 m) and y (0.5 m)
    assert np.isclose(top[:, 0].max(), 2.0) and np.isclose(top[:, 1].max(), 0.5)
    assert np.isclose(st.max(), 2.0)
