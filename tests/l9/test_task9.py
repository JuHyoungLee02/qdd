from collections import Counter

import numpy as np
import pytest

from harvest.l9 import assets9 as A9
from harvest.l9 import collect9 as C9
from harvest.l9 import reach9 as R9
from harvest.l9 import scene9 as S9
from harvest.l9 import task9 as T9


@pytest.fixture(scope="module")
def rm():
    return R9.load_default()


def test_definition_counts():
    c = T9.definition_count()
    assert len(T9.DEFS) >= 75 and len(c) == 9 and all(v >= 8 for v in c.values())
    for d in T9.DEFS.values():
        assert len(d.templates) >= 5, d.id
        assert T9.dep_order(d.objs)  # no cyclic constraints
        for a, dst in d.steps:
            assert a in d.objs and (dst in d.objs or dst in d.dst), (d.id, dst)


def test_licences_and_pools():
    cat = A9.catalog()
    assert len(cat) > 3000
    assert all(A9.licence_ok(r["license"]) for r in cat.values())
    assert not A9.licence_ok("CC BY-NC 4.0") and not A9.licence_ok("CC BY-ND 4.0") and A9.licence_ok("CC0 1.0")
    p0, p1 = A9.pool_for(0), A9.pool_for(1)
    assert p0 == A9.pool_for(0) and set(p0) != set(p1)
    b = Counter(A9.bucket_of(r) for r in p0.values())
    assert b[("container", "wide")] >= 3 and b[("target", "slender")] >= 3
    assert all(r["footprint_r"] <= A9.CONTAINER_R_MAX[T9.kind_of(r)] + 1e-6 for r in p0.values() if r["role9"] == "container")


def test_instantiate_objects_clear_and_named(rm):
    d = T9.DEFS["line2_y"]
    got = 0
    for s in range(12):
        sc = S9.sample("workbench", "crates", s, ("right", "left")[s % 2], rm)
        ep = T9.instantiate(d, sc, A9.pool_for(s), s, rm, tries=20)
        if ep is None:
            continue
        got += 1
        xy = [np.asarray(o["xy"]) for o in ep["objects"].values()]
        fr = [o["fr"] for o in ep["objects"].values()]
        for i in range(len(xy)):
            for j in range(i + 1, len(xy)):
                assert np.hypot(*(xy[i] - xy[j])) >= fr[i] + fr[j] + 0.02 - 1e-6
        for k in ep["roles"].values():
            assert ep["names"][k] in ep["instruction"].lower()
        assert len(ep["steps"]) == 2 and all(p.startswith("s9_") for _, p, _ in ep["steps"])
    assert got >= 3


def test_unfit_scene_returns_none(rm):
    sc = S9.sample("dining", "seats2", 0, "right", rm)
    assert T9.instantiate(T9.DEFS["sort_cubbies"], sc, A9.pool_for(0), 0, rm, tries=3) is None


def test_draw_combo_hash_unique(rm, tmp_path):
    from harvest.l9.vary9 import ComboLedger
    led = ComboLedger(str(tmp_path / "l.txt"))
    row = {"seed": 900001, "arm": "left", "family": "workbench", "rule": "crates", "def": "in_wide"}
    sc, ep, light, head, h, sd = C9.draw(row, A9.pool_for(3), rm, led)
    led.add(h)
    sc2, ep2, _, _, h2, sd2 = C9.draw(row, A9.pool_for(3), rm, led)  # the same row: the used combination is redrawn
    assert h2 != h and sd2 != sd


def test_container_support_top_from_bottom():
    from harvest.l9 import world9 as W
    from harvest.sim import scene as SC
    c = A9.containers()
    k = sorted(c)[0]
    W.register_pool({k: c[k]})
    assert SC.SUPPORT_TOP[k] == pytest.approx(c[k]["inside"]["inner_floor_z"])
    assert 0.0 <= SC.SUPPORT_TOP[k] <= c[k]["height"]
