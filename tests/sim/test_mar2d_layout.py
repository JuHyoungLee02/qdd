"""MolmoAct R2 data (plan 2026-09-26-molmoact-r2-data Task 1): two-target pair layout (M4), multi-path DR keep-out,
and the default layout / randomization path pinned byte-identical (digest computed before the change)."""
import hashlib
import json
import math
import types

import numpy as np
import pytest

from harvest.sim import tasks as T
from harvest.sim.randomize import load_pools, placement_ok, sample_randomization
from harvest.sim.scene import OBJ_GEOM, WS_X, WS_Y

# computed with the code before this change (D:\tools\scratch_qdd\mar2d\baseline_digest.py, 2026-09-26 05:0x UTC)
DEFAULT_DIGEST = "1aa6be6c4a02280c9fda483c2820bbfffe48ab461a9ce1726e9b12ffd4d3bfd9"
SEEDS = list(range(0, 30)) + [10000, 10001, 10599, 10600, 10999, 11000, 12000]


def test_default_layout_digest_unchanged():
    h = hashlib.sha256()
    for seed in SEEDS:
        for task in T.TASK_IDS:
            lay = T.task_layout(seed, task)
            h.update(json.dumps({k: [round(float(x), 12) for x in v] for k, v in sorted(lay.items())}).encode())
            for variant in ("standard", "dr"):
                m = sample_randomization(seed, variant, lay, path=(T.TASKS[task].target, T.TASKS[task].place))
                h.update(json.dumps(m, sort_keys=True).encode())
    assert h.hexdigest() == DEFAULT_DIGEST


def _fr(k):
    return OBJ_GEOM[k]["footprint_r"]


@pytest.mark.parametrize("seed", list(range(11000, 11200)))
def test_pair_layout_rules(seed):
    lay = T.pair_layout(seed)
    assert {"o3", "o8", "o5"} <= set(lay)
    assert set(lay) <= {"o3", "o8", "o5", "o9"}
    for k in ("o3", "o8", "o5"):
        x, y, _ = lay[k]
        lo = WS_X[0] + (0.02 if k == "o5" else 0.0)
        assert lo <= x <= WS_X[1] + 1e-12
        assert WS_Y[0] <= y <= WS_Y[1] + 1e-12
    for k in ("o3", "o8"):
        assert math.dist(lay[k][:2], lay["o5"][:2]) >= max(0.16, _fr(k) + _fr("o5") + 0.03) - 1e-12
    assert math.dist(lay["o3"][:2], lay["o8"][:2]) >= T.PAIR_MIN_SEP_M - 1e-12
    assert T.pair_image_sep_px(lay) >= T.PAIR_MIN_PX - 1e-9
    if "o9" in lay:
        for k in ("o3", "o8", "o5"):
            assert math.dist(lay["o9"][:2], lay[k][:2]) >= _fr("o9") + _fr(k) + 0.02 - 1e-12


def test_pair_layout_deterministic_and_not_a_task_layout():
    assert T.pair_layout(11001) == T.pair_layout(11001)
    assert T.pair_layout(11001) != T.pair_layout(11002)
    for task in T.TASK_IDS:
        assert T.pair_layout(11001) != T.task_layout(11001, task)


def test_pair_tasks_share_place_and_differ_in_target():
    a, b = (T.TASKS[t] for t in T.PAIR_TASKS)
    assert a.place == b.place == "o5" and {a.target, b.target} == {"o3", "o8"}
    assert T.PAIR_PATHS == tuple((T.TASKS[t].target, T.TASKS[t].place) for t in T.PAIR_TASKS)


def test_layout_for_routes_and_refuses():
    assert T.layout_for(11001, "mug_tray", "task") == T.task_layout(11001, "mug_tray")
    assert T.layout_for(11001, "bottle_tray", "pair") == T.pair_layout(11001)
    with pytest.raises(ValueError):
        T.layout_for(11001, "mug_marker", "pair")  # the marker task is not a pair task
    with pytest.raises(ValueError):
        T.layout_for(11001, "mug_tray", "triple")


def test_layout_paths():
    assert T.layout_paths("bottle_tray", "task") == ("o8", "o5")
    assert T.layout_paths("bottle_tray", "pair") == T.PAIR_PATHS


def test_placement_ok_multi_path():
    pools = load_pools()
    c = pools["common"]
    lay = T.pair_layout(11003)
    rng = np.random.default_rng(0)
    n_diff = 0
    for _ in range(3000):
        xy = (float(rng.uniform(*c["place_x"])), float(rng.uniform(*c["place_y"])))
        r = 0.04
        one = placement_ok(xy, r, lay, [], c, ("o3", "o5"))
        one_b = placement_ok(xy, r, lay, [], c, ("o8", "o5"))
        both = placement_ok(xy, r, lay, [], c, T.PAIR_PATHS)
        assert both == (one and one_b)
        n_diff += int(one != both)
    assert n_diff > 0  # the second path actually removes positions


def test_pair_randomization_same_for_both_tasks():
    for seed in (11001, 11002, 11020):
        fake = types.SimpleNamespace(variant="dr")
        from harvest.sim.scene import Env
        Env.set_seed(fake, seed, "mug_tray", layout="pair")
        a = (fake.layout, fake.randomization)
        Env.set_seed(fake, seed, "bottle_tray", layout="pair")
        b = (fake.layout, fake.randomization)
        assert a == b
        assert fake.task == "bottle_tray" and fake.layout_mode == "pair"


def test_set_seed_default_unchanged():
    from harvest.sim.scene import Env
    fake = types.SimpleNamespace(variant="dr")
    Env.set_seed(fake, 11001, "bottle_tray")
    assert fake.layout == T.task_layout(11001, "bottle_tray")
    assert fake.randomization == sample_randomization(11001, "dr", fake.layout, path=("o8", "o5"))
    assert fake.layout_mode == "task"
