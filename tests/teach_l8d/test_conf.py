"""Confuser scenes (prereg_l8d change 10, STRIP8 D round 2): same-colour, different-shape distractors next to the
target; the OOD-O small red cup o14 never appears; new TRAIN seed block 36000-37999."""
import math

import pytest

from harvest.sim import scene as SC
from harvest.sim import tasks as T
from harvest.teach_l8d import dataset as D
from harvest.teach_l8d import spec as S


def test_confuser_objects_share_the_target_colour_and_differ_from_o14():
    for tgt, pool in T.CONF_POOL.items():
        assert pool and "o14" not in pool
        for k in pool:
            g = SC.OBJ_GEOM[k]
            assert g["color"] == SC.OBJ_GEOM[tgt]["color"] and k in SC.X_RIGID and k in SC.PARK_XY
            if g["shape"] == "cylinder":  # clearly unlike the small red cup (r 2.5 cm, h 7.5 cm)
                assert abs(g["radius"] - 0.025) >= 0.007 or abs(g["height"] - 0.075) >= 0.03
    from harvest.astra_motion.prompts import OBJ_DESC, OBJ_NAME
    for k in {k for p in T.CONF_POOL.values() for k in p}:
        assert k in OBJ_NAME and k in OBJ_DESC


def test_conf_tasks_mirror_their_base_and_append_layout_streams():
    assert set(S.CONF_TASKS) == set(T.CONF_TASKS)
    for t, base in T.CONF_TASKS.items():
        b, c = T.TASKS[base], T.TASKS[t]
        assert (c.target, c.place, c.instruction) == (b.target, b.place, b.instruction)
        assert t in T.X_TASKS and c.target in T.CONF_POOL
    codes = [T.X_TASK_CODE[t] for t in T.X_TASK_IDS]
    assert codes == list(range(100, 100 + len(codes)))
    assert T.X_TASK_IDS[-len(T.CONF_TASKS):] == tuple(T.CONF_TASKS)  # appended: older streams unchanged


@pytest.mark.parametrize("task", sorted(T.CONF_TASKS))
def test_conf_layouts_place_one_or_two_confusers_clear_of_target_and_place(task):
    s = T.TASKS[task]
    pool = T.CONF_POOL[s.target]
    seen = set()
    for seed in range(36000, 36040):
        lay = T.x_task_layout(seed, task, ws=((0.37, 0.52), (-0.40, -0.06)))
        conf = [k for k in lay if k in pool]
        assert 1 <= len(conf) <= min(2, len(pool)) and "o14" not in lay
        seen.update(conf)
        m, p = lay[s.target], lay[s.place]
        for k in conf:
            q = lay[k]
            assert 0.08 - 1e-9 <= math.dist(q[:2], m[:2]) <= 0.16 + 1e-9
            assert math.dist(q[:2], p[:2]) >= T._fr(k) + T._fr(s.place) + 0.04 - 1e-9
            for j, v in lay.items():
                if j != k and j not in SC.X_VISUAL_ONLY and j != "o11":
                    assert math.dist(q[:2], v[:2]) >= T._fr(k) + T._fr(j) + 0.02 - 1e-9, (seed, k, j)
    assert seen == set(pool) or len(pool) > 2


def test_seed_block_and_train_rows():
    assert S.check_seed(36000, "train") == 36000 and S.check_seed(37999, "train") == 37999
    with pytest.raises(ValueError):
        S.check_seed(38000, "train")
    assert S.is_train_seed(30000) and S.is_train_seed(36123) and not S.is_train_seed(34900)
    D.check_row({"seed": 36010, "variant": "drx", "task": "cf_mug_tray"}, "train")
    with pytest.raises(ValueError):
        D.check_row({"seed": 34900, "variant": "drx", "task": "cf_mug_tray"}, "train")


def test_bundle_groups():
    ok = S.bundle_task_ok
    assert ok("mug_tray", ["all"]) and ok("ov_tray__objv_0100598f46bd", ["all"]) and ok("mug_to_upper", ["all"])
    assert ok("clear_to_bin", ["all"]) and not ok("cf_mug_tray", ["all"]) and ok("cf_mug_tray", ["conf"])
    assert not ok("smallcup_tray", ["all"]) and not ok("bluemug_bin", ["all"]) and not ok("ov_tray__x", ["phase1"])
