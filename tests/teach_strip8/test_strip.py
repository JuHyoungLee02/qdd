"""E-STRIP8 request stripping (prereg_strip8.md §1-2): removing the table-height line and the grid / drop-line overlay
from an astra-solo@v2 request gives the E-PT nd-xyz@v1 request of the same state byte for byte; the minimal request
also has no object sizes and no grasp / place recipes, and keeps the task and the robot's own information; the
privileged-information dropout draws are deterministic and have the registered rates; the minimal closed-loop episode
asks the minimal request."""
import json

import numpy as np
import pytest

from harvest.astra_motion.prompts import OBJ_DESC
from harvest.astra_solo import nd_prompts as NP
from harvest.astra_solo.pt_episode import PtEpisode
from harvest.astra_solo.pt_truth import NdTruth, PtTruth
from harvest.teach_strip8 import strip as S

from astra_solo.test_pt_episode import PadWorld


@pytest.fixture(scope="module")
def calls(tmp_path_factory):
    d = tmp_path_factory.mktemp("strip8")
    w = PadWorld()
    m = PtTruth(w)
    ep = PtEpisode(w, m, 3, "mug_tray", str(d / "ep"), save_v2=True, save_nd=True)
    m.ep = ep
    ep.run()
    out = []
    for c in sorted((d / "ep" / "calls").iterdir()):
        if (c / "prompt_v2.txt").exists():
            out.append(((c / "prompt_v2.txt").read_text(encoding="utf-8"),
                        (c / "prompt_nd-xyz@v1.txt").read_text(encoding="utf-8")))
    assert len(out) >= 4
    return out


def test_table_and_overlay_give_nd_xyz_bytes(calls):
    for v2, nd in calls:
        assert S.strip(v2, {"table", "overlay"}) == nd


def test_minimal_has_no_scene_or_recipe_information(calls):
    for v2, nd in calls:
        t = S.minimal(v2)
        for bad in ("Table top surface", "0.850", "WHITE GRID", "DROP LINE", "Grasping an upright", "table + h",
                    "Putting a held object down", "lift before moving sideways", "name: shape", "diameter", "cm high"):
            assert bad not in t, bad
        for desc in OBJ_DESC.values():
            assert desc not in t
        for keep in ("TASK:", "Fully open pad gap 10.7 cm", "White ring", "CAMERAS", "Image 1: head camera",
                     "TCP at (", "The code keeps the TCP inside x", "- red mug (the object to move)",
                     "- blue tray (where to put it)", "Moves are straight lines.", "Return JSON only"):
            assert keep in t, keep
        assert S.minimal(nd) == t  # the same minimal request from the nd-xyz text
        assert S.strip(t, S.FIELDS) == t  # idempotent


def test_each_field_changes_only_its_part(calls):
    v2 = calls[0][0]
    assert S.strip(v2, set()) == v2
    for f in S.FIELDS:
        t = S.strip(v2, {f})
        assert t != v2 and (len(t) < len(v2) or f == "table")  # the nd table sentence is longer than v2's
        assert t.split("NOW\n", 1)[1] == v2.split("NOW\n", 1)[1] or f == "overlay"
    with pytest.raises(ValueError):
        S.strip(v2, {"nonsense"})
    with pytest.raises(ValueError):
        S.strip("no request here", {"table"})


def test_drop_draws_are_deterministic_with_registered_rates():
    rng = np.random.default_rng(0)
    draws = [S.sample_drops(rng) for _ in range(20000)]
    again = [S.sample_drops(np.random.default_rng(0)) for _ in range(1)]
    assert again[0] == draws[0]
    p_all = np.mean([d == frozenset(S.FIELDS) for d in draws])
    p_none = np.mean([len(d) == 0 for d in draws])
    assert abs(p_all - (0.3 + 0.7 / 16)) < 0.015 and abs(p_none - 0.7 / 16) < 0.01
    for f in S.FIELDS:
        assert abs(np.mean([f in d for d in draws]) - 0.65) < 0.015


def test_minimal_episode_asks_the_minimal_request(tmp_path):
    from harvest.teach_strip8.episode import StripEpisode
    w = PadWorld()
    m = NdTruth(w, "nd-xyz")
    ep = StripEpisode(w, m, 3, "mug_tray", str(tmp_path / "e"))
    m.ep = ep
    res = ep.run()
    assert res["success"], res["end_reason"]
    assert res["prompt_version"] == S.VERSION and res["interface"] == "s-min"
    t = (tmp_path / "e" / "calls" / "c000" / "prompt.txt").read_text(encoding="utf-8")
    assert t == S.minimal(t) and "Grasping an upright" not in t and "Table top surface" not in t
    assert json.load(open(tmp_path / "e" / "result.json"))["prompt_id"] == S.PROMPT_ID


def test_runner_factory_picks_the_interface(tmp_path):
    from harvest.astra_solo.episode import Episode
    from harvest.teach_strip8.episode import StripEpisode
    from harvest.teach_strip8.run_closed import make_episode
    w = PadWorld()
    assert isinstance(make_episode("s-min", w, None, 0, out_dir=None), StripEpisode)
    e = make_episode("v2", w, None, 0, out_dir=None)
    assert isinstance(e, Episode) and not isinstance(e, StripEpisode)
    with pytest.raises(ValueError):
        make_episode("pt", w, None, 0, out_dir=None)
