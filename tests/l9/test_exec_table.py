import numpy as np

from harvest.l9 import gtest9 as GT
from harvest.l9 import hand9 as H


def test_exec_table_off_by_default(monkeypatch):
    monkeypatch.delenv("L9_EXEC_TABLE", raising=False)
    T = np.eye(4)
    assert np.allclose(GT.exec_pose(T, 0.03, "g1", None, 0.0), T)


def test_exec_table_g1_lateral_and_support(monkeypatch):
    monkeypatch.setenv("L9_EXEC_TABLE", "1")
    t = H.table_for("g1", "right")
    if t is None:
        return
    off = t.exec_offsets(0.03)
    T = np.eye(4)  # top-down? no: identity = approach -z_G = world -z, i.e. top-down
    T[:3, 3] = [0.5, 0.0, 0.80]
    out = GT.exec_pose(T, 0.03, "g1", None, support_z=None)
    cm = off["contact_mid"]
    assert np.allclose(out[:3, 3], [0.5 - cm[0], -cm[1], 0.80])  # contact centre moved onto the planned point
    low_support = 0.80 + float(off["tip_front"]) + 0.02  # surface above the deepest finger point
    out2 = GT.exec_pose(T, 0.03, "g1", None, support_z=low_support)
    assert out2[2, 3] > out[2, 3]  # backed off upward along +z_G
    assert np.allclose(GT.exec_pose(T, 0.03, "ffw_sg2", None, None), T)  # hand-tuned FINGER path untouched
