import math

import numpy as np
import pytest

from harvest.l9 import reach9 as R9
from harvest.l9 import scene9 as S


@pytest.fixture(scope="module")
def rm():
    return R9.load_default()


def test_40_layouts_over_8_families():
    assert len(S.FAMILIES) >= 8 and all(len(r) >= 5 for _, r in S.FAMILIES.values())
    assert len(S.all_rules()) >= 40


@pytest.mark.parametrize("arm", ["right", "left"])
def test_every_rule_samples(rm, arm):
    for f, r in S.all_rules():
        for seed in range(3):
            sc = S.sample(f, r, seed, arm, rm)
            assert len(sc["furniture"]) == len(sc["parts_s"]) <= S.N_SLOTS
            assert not S.keep_out_hits(sc["parts_s"], sc["yaw"])
            assert abs(sc["robot_pose"]["yaw"]) <= math.radians(20) + 1e-9
            assert S.DIST[0] <= sc["robot_pose"]["distance"] <= S.DIST[1]
            assert S.usable_nodes(sc), (f, r, seed)
            for n in S.usable_nodes(sc):
                pts = S.usable(n, sc, rm, sc["lift"])
                sgn = 1 if arm == "right" else -1
                assert np.all(sgn * pts[:, 1] <= 0.07)  # the arm's side of the robot


def test_frames_roundtrip():
    p = np.array([0.4, -0.2])
    assert np.allclose(S.s_of(S.world_of(p, 0.3), 0.3), p)


def test_deterministic(rm):
    a = S.sample("dining", "seats4", 5, "right", rm)
    b = S.sample("dining", "seats4", 5, "right", rm)
    assert a["furniture"] == b["furniture"] and a["lift"] == b["lift"]
    c = S.sample("dining", "seats4", 6, "right", rm)
    assert c["furniture"] != a["furniture"]


def test_bad_rule():
    with pytest.raises(ValueError):
        S.sample("dining", "nope", 0, "right")
