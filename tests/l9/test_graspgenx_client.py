import numpy as np

from tools.l9.graspgenx_client import P_TO_GRASPGENX, base_to_tcp


def test_p_to_graspgenx_is_self_inverse_and_orthogonal():
    P = P_TO_GRASPGENX
    assert np.allclose(P @ P, np.eye(3))
    assert np.allclose(P @ P.T, np.eye(3))
    assert np.isclose(np.linalg.det(P), 1.0)


def test_base_to_tcp_identity_rotation_case():
    # R_ggx = P => R_base_world = P @ P = I (base_link axis-aligned with world).
    R_ggx = P_TO_GRASPGENX
    t_ggx = np.array([0.0, 0.0, 0.21])  # base_link 21cm from the object along world z
    tcp_in_base_xyz = [0.0, 0.0, -0.16711]  # ffw_sg2_right
    R_tcp, t_tcp = base_to_tcp(R_ggx, t_ggx, tcp_in_base_xyz)
    assert np.allclose(R_tcp, np.eye(3))
    assert np.allclose(t_tcp, [0.0, 0.0, 0.21 - 0.16711])  # ~4.3cm, matches the 2026-10-02 pod verification


def test_base_to_tcp_zero_offset_is_identity_translation():
    R_ggx = np.eye(3)
    t_ggx = np.array([1.0, 2.0, 3.0])
    R_tcp, t_tcp = base_to_tcp(R_ggx, t_ggx, [0.0, 0.0, 0.0])
    assert np.allclose(t_tcp, t_ggx)
