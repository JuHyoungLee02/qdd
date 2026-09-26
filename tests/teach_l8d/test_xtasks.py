"""L8-X tasks (pure): layouts, prompts, support-aware truth labels (== L8 labels on one table)."""
import json
import math

import numpy as np
import pytest

from harvest.astra_motion.prompts import OBJ_DESC, OBJ_NAME, place_rule
from harvest.sim import scene as S
from harvest.sim import tasks as T
from harvest.teach_l8 import labels as L
from harvest.teach_l8d import xlabels as X

WS = ((0.37, 0.49), (-0.40, -0.06))


def test_registry_and_codes():
    assert set(T.X_TASK_IDS) <= set(T.TASKS) and not set(T.X_TASK_IDS) & set(T.TASK_IDS)
    assert len(set(T.X_TASK_CODE.values())) == len(T.X_TASK_IDS)
    assert not set(T.X_TASK_CODE.values()) & {1000 + v for v in T.TASK_CODE.values()}
    for t in T.X_TASK_IDS:
        s = T.TASKS[t]
        assert s.target in OBJ_NAME and s.place in OBJ_NAME and s.place in OBJ_DESC
        assert place_rule(s.place, OBJ_NAME[s.place])
    assert "o12" not in S.PRESENT_IDS and "o12" in S.X_PRESENT_IDS


def test_default_objects_and_layouts_untouched():
    assert S.PRESENT_IDS == ("o3", "o5", "o8", "o9", "o11") and S.VISUAL_ONLY == ("o11",)
    assert place_rule("o5", "blue tray") == "on the blue tray (resting on it, supported by it)"
    for s in range(5):
        assert all(len(v) == 3 for v in T.task_layout(s, "mug_tray").values())


@pytest.mark.parametrize("task", T.X_TASK_IDS)
def test_x_layouts(task):
    s = T.TASKS[task]
    for seed in range(30000, 30030):
        lay = T.task_layout(seed, task, ws=WS)
        assert lay == T.task_layout(seed, task, ws=WS)
        assert s.target in lay and s.place in lay and "o3" in lay
        for k in (s.target, s.place):
            x, y = lay[k][:2]
            assert WS[0][0] - 1e-9 <= x <= WS[0][1] + 1e-9 and WS[1][0] - 1e-9 <= y <= WS[1][1] + 1e-9, (k, x, y)
        if task == "stand_mug_tray":
            assert lay["o3"][3] == "o12" and lay["o3"][:2] == lay["o12"][:2]
            assert S.base_z("o3", lay, 0.85) == pytest.approx(0.85 + 0.08)
        if task in T.X_CONFUSER:
            d = math.dist(lay[s.target][:2], lay[T.X_CONFUSER[task]][:2])
            assert 0.08 - 1e-9 <= d <= 0.14 + 1e-9
        if task in T.X_REL:
            ref, spot, dy = T.X_REL[task]
            assert lay[spot][1] - lay[ref][1] == pytest.approx(dy) and lay[spot][0] == lay[ref][0]
            assert math.dist(lay["o3"][:2], lay[spot][:2]) >= 0.12


def _state(rng, tz):
    tcp = [rng.uniform(0.3, 0.55), rng.uniform(-0.45, 0.0), tz + rng.uniform(0.02, 0.35)]
    hold = bool(rng.random() < 0.4)
    c = [rng.uniform(0.35, 0.5), rng.uniform(-0.4, -0.06), tz + 0.0475 + (tcp[2] - tz - 0.15 if hold else 0.0)]
    p = [rng.uniform(0.35, 0.5), rng.uniform(-0.4, -0.06), tz + 0.0075]
    if rng.random() < 0.2:
        p[:2] = tcp[:2]
    pred = {"holding(o3)": hold, "upright(o3)": bool(rng.random() < 0.95), "on(o3,o5)": bool(rng.random() < 0.15)}
    return {"tcp": np.array(tcp), "grip_w": float(rng.choice([0.107, 0.064, 0.02])), "pred": pred,
            "obj": {"o3": np.array(c), "o5": np.array(p)}}


def test_xlabels_equal_l8_labels_on_one_table():
    rng = np.random.default_rng(0)
    info = {"tgt": "o3", "place": "o5", "present": ["o3", "o5"]}
    for i in range(3000):
        tz = float(rng.choice([0.85, 0.80, 0.92]))
        st = _state(rng, tz)
        a = L.label(st, info, tz, 0.107, first=i % 7 == 0, last_line="3: BLOCKED" if i % 11 == 0 else "")
        b = X.label(st, info, tz, 0.107, first=i % 7 == 0, last_line="3: BLOCKED" if i % 11 == 0 else "")
        assert a == b
        # explicit keys equal to the one-table values give the same labels
        c = X.label(st, dict(info, sup_tgt=tz, sup_place=tz, place_top=tz + 0.015), tz, 0.107,
                    first=i % 7 == 0, last_line="3: BLOCKED" if i % 11 == 0 else "")
        assert c == a


def test_xlabels_use_the_support_heights():
    tz = 0.85
    info = {"tgt": "o3", "place": "o15", "present": ["o3", "o15"], "sup_tgt": tz + 0.08, "sup_place": tz,
            "place_top": tz + 0.008}
    st = {"tcp": np.array([0.40, -0.20, tz + 0.40]), "grip_w": 0.107, "pred": {},
          "obj": {"o3": np.array([0.40, -0.20, tz + 0.08 + 0.0475]), "o15": np.array([0.45, -0.3, tz + 0.025])}}
    step, cmd = X.plan(st, info, tz, 0.107)
    assert step == "above_target" and cmd["position_m"][2] == pytest.approx(round(tz + 0.08 + 0.095 - 0.018 + 0.10, 3))
    st["tcp"] = np.array([0.40, -0.20, tz + 0.08 + 0.077])
    step, cmd = X.plan(st, info, tz, 0.107)
    assert step == "descend_close" and cmd["position_m"][2] == pytest.approx(round(tz + 0.08 + 0.077, 3))
    st = {"tcp": np.array([0.45, -0.30, tz + 0.40]), "grip_w": 0.064, "pred": {"holding(o3)": True},
          "obj": {"o3": np.array([0.45, -0.30, tz + 0.40 - 0.077 + 0.0475]), "o15": np.array([0.45, -0.3, tz + 0.025])}}
    step, cmd = X.plan(st, info, tz, 0.107)
    assert step == "lower_open"
    bottom = st["obj"]["o3"][2] - 0.0475
    assert cmd["position_m"][2] == pytest.approx(round(tz + 0.008 + (st["tcp"][2] - bottom) + 0.004, 3))
    st["tcp"] = np.array([0.40, -0.20, tz + 0.25])
    st["obj"]["o3"] = np.array([0.40, -0.20, tz + 0.25 - 0.077 + 0.0475])
    step, cmd = X.plan(st, info, tz, 0.107)
    assert step == "carry_up" and cmd["position_m"][2] == pytest.approx(round(tz + 0.08 + 0.22, 3))
