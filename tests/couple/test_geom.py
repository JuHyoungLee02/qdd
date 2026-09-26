import numpy as np

from harvest.couple.geom import quat_from_rotvec, quat_mul


def test_rotvec_and_product():
    q = quat_from_rotvec([0, 0, np.pi / 2])
    np.testing.assert_allclose(q, [np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)], atol=1e-12)
    np.testing.assert_allclose(quat_from_rotvec([0, 0, 0]), [1, 0, 0, 0])
    np.testing.assert_allclose(quat_mul(q, q), [0, 0, 0, 1], atol=1e-12)
