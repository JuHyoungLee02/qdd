"""L8-D per-height workspace (docs/stage3/prereg_l8d.md): layouts take an optional workspace box ws = ((x0, x1),
(y0, y1)); ws None is the old path byte for byte."""
import pytest

from harvest.sim import scene as S
from harvest.sim import tasks as T

WS = ((0.40, 0.49), (-0.38, -0.08))


@pytest.mark.parametrize("seed", [0, 5, 17, 30003])
def test_default_ws_is_unchanged(seed):
    assert S.sample_layout(seed) == S.sample_layout(seed, ws=None)
    assert S.sample_layout(seed) == S.sample_layout(seed, ws=(S.WS_X, S.WS_Y))
    for t in T.TASK_IDS:
        assert T.task_layout(seed, t) == T.task_layout(seed, t, ws=None) == T.task_layout(seed, t, ws=(S.WS_X, S.WS_Y))
        assert T.layout_for(seed, t) == T.layout_for(seed, t, ws=None)


@pytest.mark.parametrize("seed", range(30000, 30040))
def test_ws_bounds_target_and_place(seed):
    for t in T.TASK_IDS:
        lay = T.task_layout(seed, t, ws=WS)
        s = T.TASKS[t]
        for k in (s.target, s.place):
            x, y = lay[k][:2]
            assert WS[0][0] <= x <= WS[0][1] and WS[1][0] <= y <= WS[1][1], (t, k, x, y)


def test_ws_must_be_valid():
    with pytest.raises(ValueError):
        S.check_ws(((0.5, 0.4), (-0.3, -0.1)))
    with pytest.raises(ValueError):
        S.check_ws(((0.40, 0.44), (-0.3, -0.1)))  # narrower than 8 cm
    assert S.check_ws(None) is None
