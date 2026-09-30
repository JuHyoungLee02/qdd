import math

import pytest

from harvest.l9 import vary9 as V
from harvest.sim import randomize as R

COMMON = {"light_types": {"sphere": {"base_intensity": 4.6e6, "radius": 0.08}, "disk": {"base_intensity": 1.15e6, "radius": 0.2},
                          "rect": {"base_intensity": 1e6, "width": 0.4, "height": 0.4},
                          "cylinder": {"base_intensity": 1.5e6, "length": 0.6, "radius": 0.04},
                          "distant": {"base_intensity": 3200.0, "angle": 1.0}},
          "light_distance_m": [1.2, 2.0], "key_weight": 0.5, "dome_weight": 0.5}


def _meta():
    return {"hdr": {"name": "h", "file": "f.hdr", "intensity": 1000.0, "intensity_mult": 1.0, "rotation_deg": 0.0},
            "light": {}, "lighting": {}}


def test_ten_plus_families_valid_types():
    assert len(V.LIGHT_FAMILIES) >= 10
    for f in V.LIGHT_FAMILIES.values():
        assert set(f.key_types) <= set(R.LIGHT_TYPES) and f.fills[1] <= 2


def test_light_meta_per_family():
    seen = set()
    for i, fam in enumerate(V.LIGHT_NAMES):
        m = V.light_meta(_meta(), fam, 7, (0.5, -0.1, 0.8), COMMON)
        f = V.LIGHT_FAMILIES[fam]
        assert m["light"]["type"] in f.key_types
        assert f.color_k[0] <= m["light"]["color_temperature_k"] <= f.color_k[1]
        assert len(m["lighting"]["fills"]) <= 2 and m["lighting"]["family"] == fam
        assert len(m["light"]["quat_wxyz"]) == 4
        seen.add(m["light"]["type"])
    assert len(seen) >= 4
    assert _meta()["hdr"]["intensity"] == 1000.0  # input untouched


def test_head_pose_every_episode():
    for s in range(200):
        h = V.head_pose(s)
        assert h["random"] and abs(h["pan"]) <= 0.35
        assert 0.40 <= h["tilt"] <= V.HEAD_TILT_MAX
    assert V.head_pose(3) == V.head_pose(3) and V.head_pose(3, 1) != V.head_pose(3)
    assert V.head_default()["tilt"] == 0.785


def test_unreal_off_by_default():
    assert all(V.unreal_style(s) is None for s in range(100))
    assert any(V.unreal_style(s, p=1.0) for s in range(3))


def test_combo_hash_and_ledger(tmp_path):
    rec = {"room": "r1", "furniture": ["a"], "materials": ["m"], "light_family": "overcast", "hdr": "h",
           "robot_pose": [30, 5], "head_pose": [45, 3]}
    h = V.combo_hash(rec)
    assert h == V.combo_hash(dict(rec))
    for k in V.COMBO_KEYS:
        assert V.combo_hash(dict(rec, **{k: "other"})) != h
    with pytest.raises(KeyError):
        V.combo_hash({"room": 1})
    led = V.ComboLedger(str(tmp_path / "a.txt"))
    assert not led.seen(h)
    led.add(h)
    assert led.seen(h)
    with pytest.raises(ValueError):
        led.add(h)
    led2 = V.ComboLedger(str(tmp_path / "b.txt"), others=[str(tmp_path / "a.txt")])
    assert led2.seen(h)


def test_keep_named_colours():
    names = {"a": "red mug", "b": "cup", "c": "blue bowl"}
    assert V.keep_named_colours("Put the red mug in the blue bowl.", names) == {"a", "c"}


def test_pick_light_family_covers_all():
    assert {V.pick_light_family(s, "dining") for s in range(400)} == set(V.LIGHT_NAMES)
