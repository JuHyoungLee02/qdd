import pytest

from harvest.train import stagea_data as D
from harvest.train import stagea_train as T


def test_source_factory_specs():
    assert T.source_factory("py:harvest.train.stagea_data:FnSource", "", False) is D.FnSource  # resolves any callable
    assert callable(T.source_factory("outcome", "plan", False))
    assert callable(T.source_factory("labels_v2", "", False))
    assert T._seedset("24-26,3") == {24, 25, 26, 3}
    with pytest.raises(SystemExit):
        T.source_factory("outcome", "", False)  # outcome labels need the prereg rule
    with pytest.raises(SystemExit):
        T.source_factory("oracle", "plan", False)  # no oracle source exists


def test_select_val_is_deterministic_and_order_free():
    va = [{"key": f"ep{i}_k0", "question": q} for i in range(10) for q in ("a", "b")]
    a = T.select_val(list(va), 5, 0)
    b = T.select_val(list(reversed(va)), 5, 0)
    assert a == b and len(a) == 5
    assert T.select_val(va, 0, 0) == va
