"""L8-X multi-step (pure parts): prompt patch (a separate version), step infos, layouts, offsets in the labels."""
import numpy as np
import pytest

from harvest.astra_solo import nd_prompts as NP
from harvest.astra_solo import prompts as V2P
from harvest.astra_solo import pt_prompts as PT
from harvest.sim import tasks as T
from harvest.teach_l8d import multistep as M
from harvest.teach_l8d import xlabels as X

from astra_motion.fakeworld import HEAD, TZ


def _info(task, k=0):
    base = {"instruction": T.TASKS[task].instruction, "present": sorted({o for s in T.X_STEPS[task] for o in s[:2]})}
    return M.step_info(base, T.X_STEPS[task], k)


@pytest.mark.parametrize("task", sorted(T.X_STEPS))
def test_patch_every_interface(task):
    steps = T.X_STEPS[task]
    info = _info(task)
    texts = {"v2": V2P.static(info, HEAD, TZ, 0.05), "pt": PT.static(info, HEAD, TZ, 0.05),
             **{v: NP.static(info, HEAD, 0.05, v) for v in NP.VERSIONS}}
    for v, t in texts.items():
        m = M.patch_static(t, info, steps)
        assert M.success_line_single(info) not in m and M.success_line_multi(steps) in m, v
        assert "(the object to move first)" in m and "(the object to move second)" in m, v
        assert ("(where to put them)" in m) == (len({s[1] for s in steps}) == 1), v
        assert T.TASKS[task].instruction in m
        # nothing else changes: same lines except the success line and the role suffixes
        a, b = t.split("\n"), m.split("\n")
        assert len(a) == len(b)
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        assert all(b[i].startswith("Success =") or b[i].startswith("- ") for i in diff)


@pytest.mark.parametrize("task", sorted(T.X_STEPS))
def test_minimal_format_from_the_patched_v2(task):
    from harvest.teach_strip8 import strip as ST
    info = _info(task)
    m = M.patch_static(V2P.static(info, HEAD, TZ, 0.05), info, T.X_STEPS[task])
    s = ST.minimal(m + V2P.ANSWER)
    assert M.success_line_multi(T.X_STEPS[task]) in s and "Table top surface" not in s
    assert "(the object to move second)" in s and "diameter" not in s


def test_old_prompts_untouched():
    assert V2P.PROMPT_ID and M.PROMPT_ID_M != V2P.PROMPT_ID
    assert len(M.PROMPT_ID_M) == 12


def test_step_infos_and_offsets():
    info1 = _info("clear_to_bin", 1)
    assert info1["tgt"] == "o8" and info1["place"] == "o15" and info1["step_idx"] == 1
    assert info1["place_xy_offset"] == [0.0, -0.035]
    assert "place_xy_offset" not in _info("mug_tray_bottle_marker", 1)
    st = {"tcp": np.array([0.45, -0.20, TZ + 0.40]), "grip_w": 0.06, "pred": {"holding(o8)": True},
          "obj": {"o8": np.array([0.45, -0.20, TZ + 0.40 - 0.082 + 0.05]), "o15": np.array([0.44, -0.30, TZ + 0.025])}}
    step, cmd = X.plan(st, dict(info1, sup_tgt=TZ, sup_place=TZ, place_top=TZ + 0.008), TZ, 0.107)
    assert step == "carry_over" and cmd["position_m"][:2] == [0.44, round(-0.30 - 0.035, 3)]


@pytest.mark.parametrize("task", sorted(T.X_STEPS))
def test_multi_layouts_are_clear(task):
    ws = ((0.37, 0.52), (-0.40, -0.06))
    for seed in range(30000, 30020):
        lay = T.task_layout(seed, task, ws=ws)
        ids = {o for s in T.X_STEPS[task] for o in s[:2]}
        assert ids <= set(lay)
        for k in ids:
            x, y = lay[k][:2]
            assert ws[0][0] - 1e-9 <= x <= ws[0][1] and ws[1][0] <= y <= ws[1][1]
