"""E-PT collection -> per-arm datasets -> offline scoring on the fake world: every arm's truth answer scores ~0 error
through the runtime path (pt: depth resolver; nd-pt: own top_z), a wrong point scores its error, seeds are guarded,
and the arms share the same states."""
import json
import os

import numpy as np
import pytest

from harvest.teach_pt import collect as C
from harvest.teach_pt import dataset as DS
from harvest.teach_pt import metrics as M

from astra_solo.test_pt_episode import PadWorld


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("pt")
    w = PadWorld()
    for s in (0, 1):
        C.collect_episode(w, s, "mug_tray", "standard", str(root / "dev" / "standard" / f"mug_tray_s{s}"), p=0.35)
    counts = DS.build(str(root / "dev"), str(root / "data"), "dev", repeats=False)
    return root, counts


def _rows(root, arm):
    return [json.loads(x) for x in open(root / "data" / f"dev_{arm}.jsonl")]


def test_counts_and_same_states(built):
    root, counts = built
    ids = {arm: {r["id"] for r in _rows(root, arm) if r["kind"] == "control"} for arm in DS.ARMS}
    assert ids["xyz"] and ids["nd-xyz"] == ids["xyz"] == ids["nd-est"]
    assert ids["pt"] <= ids["xyz"] and ids["nd-pt"] <= ids["xyz"]
    for arm in DS.ARMS:
        a = counts["arms"][arm]
        assert a["aux_rows"] == a["control_unique"]


def test_truth_answers_score_zero(built):
    root, _ = built
    for arm in DS.ARMS:
        sc = [M.score(r, r["answer"], arm) for r in _rows(root, arm) if r["kind"] == "control"]
        assert all(s["valid"] and s["action_ok"] for s in sc), arm
        xy = [s["approach_xy_mm"] for s in sc if s["approach_xy_mm"] is not None]
        assert xy and max(xy) < 12, (arm, xy)
        gz = [abs(s["grasp_z_mm"]) for s in sc if s.get("grasp_z_mm") is not None]
        assert not gz or max(gz) < 6, (arm, gz)
        summ = M.summarize(sc)
        assert summ["n_goal_error"] == 0


def test_wrong_point_scores_error(built):
    root, _ = built
    r = [x for x in _rows(root, "pt") if x["kind"] == "control" and x["step"] == "above_target"][0]
    a = json.loads(r["answer"])
    a["command"]["point_2d"] = [a["command"]["point_2d"][0] + 150, a["command"]["point_2d"][1]]
    s = M.score(r, json.dumps(a), "pt")
    assert s["valid"] and s["point_px"] > 90 and s["approach_xy_mm"] > 30


def test_aux_truth(built):
    root, _ = built
    for arm in ("pt", "nd-xyz"):
        aux = [r for r in _rows(root, arm) if r["kind"] == "aux"]
        assert all(M.aux_score(r, r["answer"]) == 0 for r in aux)


def test_seed_guards():
    with pytest.raises(ValueError):
        C.check_seed(25, "dev", "standard")
    with pytest.raises(ValueError):
        C.check_seed(20100, "train", "random")
    with pytest.raises(ValueError):
        C.check_seed(3, "ood_h", "standard", 0.85)
    assert C.check_seed(3, "ood_h", "standard", 0.82) == 3
    assert C.check_seed(22, "ood_d", "random") == 22
    with pytest.raises(ValueError):
        C.check_seed(20100, "train", "standard", 0.82)
