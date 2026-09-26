"""Track-H rows (harvest.teach_pt.hybrid_data) on the fake world: depth-mode split of the training rows, the depth
image only when depth is on, the H truth scoring ~0 through the runtime selector (PT branch with depth, xyz branch
without), D-noisy rows pointing at a stereo-noise copy, and the H request = the R request apart from the tag / form."""
import json

import numpy as np
import pytest

from harvest.astra_solo import hybrid as HY
from harvest.teach_pt import collect as C
from harvest.teach_pt import hybrid_data as HD
from harvest.teach_pt import metrics as M

from astra_solo.test_pt_episode import PadWorld


@pytest.fixture(scope="module")
def roots(tmp_path_factory):
    root = tmp_path_factory.mktemp("pth")
    w = PadWorld()
    C.collect_episode(w, 3, "mug_tray", "standard", str(root / "dev" / "standard" / "mug_tray_s3"), p=0.35)
    C.collect_episode(w, 20100, "mug_tray", "standard", str(root / "train" / "standard" / "mug_tray_s20100"), p=0.35)
    return root


def _rows(p):
    return [json.loads(x) for x in open(p)]


def test_eval_modes_and_scores(roots):
    out = roots / "data"
    out.mkdir(exist_ok=True)
    for mode in ("on", "noisy", "off"):
        HD.build_h(str(roots / "dev"), str(out), "dev", mode)
        rows = _rows(out / f"dev_h_{mode}.jsonl")
        assert rows and all(r["h_mode"] == {"on": "clean", "noisy": "noisy", "off": "off"}[mode] for r in rows)
        assert all(len(r["images"]) == (2 if mode == "off" else 3) for r in rows)
        t = open(rows[0]["prompt_path"], encoding="utf-8").read()
        assert (HY.TAG_ON in t) == (mode != "off") and "position_m" in t
        sc = [M.score(r, r["answer"], "h") for r in rows]
        assert all(s["valid"] and s["action_ok"] for s in sc)
        summ = M.summarize(sc)
        if mode == "on":
            assert summ["h_fallback_rate"] < 0.5 and summ["approach_xy_median_mm"] < 10
        if mode == "off":
            assert summ["h_branches"]["pt"] == 0 and summ["approach_xy_median_mm"] < 2
    noisy = _rows(out / "dev_h_noisy.jsonl")
    assert all("depth_zed_mini" in r["depth_path"] for r in noisy)
    HD.build_pt_noisy(str(roots / "dev"), str(out), "dev")
    pn = _rows(out / "dev_pt_noisy.jsonl")
    assert pn and all(r["depth_noise"] == "zed_mini" and np.load(r["depth_path"])["depth"].shape == (376, 672)
                      for r in pn)


def test_train_mode_mix(roots):
    out = roots / "data"
    out.mkdir(exist_ok=True)
    c = HD.build_h(str(roots / "train"), str(out), "train", "train")
    assert c["aux_rows"] == c["states"] and set(c["depth_modes"]) <= {"off", "noisy", "clean"}
    with pytest.raises(ValueError):
        HD.build_h(str(roots / "dev"), str(out), "dev", "train")
