import numpy as np
import pytest

from harvest.perception.aux_labels import AUX_PREDS, aux_labels, aux_names, aux_vector

HE = {"o3": [0.032, 0.032, 0.0475], "o5": [0.09, 0.07, 0.0075]}


def _state(present=("o3", "o5"), pred=None):
    objs = {"o3": {"pos": [0.43, -0.38, 0.0475], "he": HE["o3"]}, "o5": {"pos": [0.48, -0.17, 0.0075], "he": HE["o5"]}}
    pred = pred if pred is not None else {"gripper_open": True, "holding(o3)": False, "near(o3,o5)": None}
    return {"present": list(present),
            "obs": {"pred": pred, "raw": {"objs": objs, "grip": {"pos": [0.33, -0.25, 0.24], "w": 0.107}}}}


def test_aux_labels_deltas_and_pairs():
    a = aux_labels(_state())
    assert a["objects"]["o3"]["delta_m"] == pytest.approx([0.10, -0.13, -0.1925])
    assert a["objects"]["o3"]["dist_m"] == pytest.approx(float(np.linalg.norm([0.10, -0.13, -0.1925])))
    assert a["pairs"]["o3-o5"]["delta_m"] == pytest.approx([-0.05, -0.21, 0.04])
    assert a["gripper"]["width_m"] == pytest.approx(0.107)
    assert a["pred"]["gripper_open"] is True and a["pred"]["near(o3,o5)"] is None


def test_aux_vector_fixed_order_and_mask():
    v, m = aux_vector(_state())
    names = aux_names()
    assert len(v) == len(m) == len(names)
    i = names.index("o3.dx")
    assert v[i] == pytest.approx(0.10) and m[i] == 1
    j = names.index("pred.near(o3,o5)")
    assert m[j] == 0 and v[j] == 0  # unknown predicate -> masked
    k = names.index("pred.gripper_open")
    assert v[k] == 1 and m[k] == 1
    assert names.index("pred." + AUX_PREDS[0]) > names.index("o3-o5.dist")


def test_aux_vector_masks_absent_object():
    v, m = aux_vector(_state(present=("o3",)))
    names = aux_names()
    for n in ("o5.dx", "o5.dist", "o3-o5.dx"):
        assert m[names.index(n)] == 0 and v[names.index(n)] == 0
    assert m[names.index("o3.dz")] == 1
