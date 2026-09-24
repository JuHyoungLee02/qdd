import numpy as np

from harvest.sim.labeler import best_set
from harvest.sim.oracle_state import to_table_frame
from harvest.sim.planner import success_from_history

OK = {"on(o3,o5)": True, "holding(o3)": False, "upright(o3)": True}
BAD = dict(OK, **{"upright(o3)": False})


def test_table_frame_origin():
    assert np.allclose(to_table_frame(np.array([0.5, 0.1, 0.80]), table_top_z=0.75), [0.5, 0.1, 0.05])


def test_success_needs_one_second_continuous():
    hist = [(i * 0.05, OK) for i in range(15)] + [(0.75, BAD)] + [(0.8 + i * 0.05, OK) for i in range(21)]
    assert success_from_history(hist) is True
    assert success_from_history([(i * 0.05, OK) for i in range(15)]) is False


def test_success_rejects_unknown_values():
    unk = dict(OK, **{"on(o3,o5)": None})
    assert success_from_history([(i * 0.05, unk) for i in range(40)]) is False


def test_best_set_ties():
    assert best_set({"a": 1.0, "b": 1.0 - 1e-9, "c": 0.4}) == {"a", "b"}
    assert best_set({"a": 0.2}) == {"a"}
