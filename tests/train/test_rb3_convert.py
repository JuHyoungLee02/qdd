"""RB3 (Dongkkka/ffw_bg2_rev4_pickup_obj_1127_total2) in tools/se2e_convert.py: opt-in kind; the RB1 / RB2 default
conversion stays byte-identical (golden sha of the rows made by the converter before RB3 was added, 1ef9f2c)."""
import hashlib
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import se2e_convert as C  # noqa: E402

from harvest.train import se2e_data as S  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402

from .test_se2e_data import URDF  # noqa: E402

# both arms: the right chain of test_se2e_data.URDF + the same chain named for the left arm, mirrored in y
URDF2 = URDF.replace("</robot>", "") + URDF.split('<robot name="t">')[1].replace("arm_r_", "arm_l_").replace(
    "end_effector_r_", "end_effector_l_").replace("gripper_r_", "gripper_l_").replace('child link="r', 'child link="l') \
    .replace('parent link="r', 'parent link="l').replace('link="g"', 'link="gl"').replace("0 -0.1045 0", "0 0.1045 0") \
    .replace("0 -0.123 0", "0 0.123 0")

INFO = {"chunks_size": 1000, "fps": 10,
        "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
        "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"}


def _fake_pq(ep, D_, T=47):
    rng = np.random.default_rng(1000 + ep + D_)
    st = np.cumsum(rng.normal(0, 0.03, (T, D_)), 0)
    st[:, 7] = st[:, 15] = 0.0
    st[10:30, 7] = 1.0  # left gripper closes 1.0-3.0 s
    act = st + rng.normal(0, 0.01, st.shape)
    t = {"task_index": [0] * T, "timestamp": [round(i / 10, 6) for i in range(T)]}
    return t, st.astype(np.float32).astype(np.float64), act.astype(np.float32).astype(np.float64)


def _rows(monkeypatch, kind, D_, ep=3, **kw):
    monkeypatch.setattr(C, "_read_pq", lambda path: _fake_pq(ep, D_))
    names = S.FEATURE_NAMES_19 if D_ == 19 else S.FEATURE_NAMES_16
    info = {**INFO, "features": {"observation.state": {"names": names}}}
    return C._convert_ep(("/nonexistent", info, {0: "sort the bottles"}, kind, ep, "/nonexistent", URDF2, 5, False),
                         **kw)


def _sha(rows):
    return hashlib.sha256("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows).encode()).hexdigest()


# rows of the pre-RB3 converter (1ef9f2c) on the fake episodes above
GOLDEN = {("RB1", 16): "06a4486ffc6dfc4ba7f0d5b7aee03f048858348010099adae409933761eabe24",
          ("RB2", 19): "ba9b4b63ef774b9a571f99759fd4a6d30a42d749e6e67a24dfd25291af0ba58e"}


@pytest.mark.parametrize("kind,D_", [("RB1", 16), ("RB2", 19)])
def test_rb1_rb2_rows_byte_identical_to_the_pre_rb3_converter(monkeypatch, kind, D_):
    assert _sha(_rows(monkeypatch, kind, D_)) == GOLDEN[(kind, D_)]


def test_default_kinds_are_rb1_rb2_only():
    assert C.DATASETS == {"RB1": "Task_0001_CoffeeClassification_lerobot", "RB2": "Task_0002_OrderPicking_lerobot"}
    assert C.selected("") == C.DATASETS
    assert C.selected("RB1,RB2") == C.DATASETS
    assert C.selected("RB3") == {"RB3": "ffw_bg2_rev4_pickup_obj_1127_total2"}
    with pytest.raises(SystemExit):
        C.selected("RB9")


def test_rb3_rows_no_rotation_grip_unit_and_episode_flags(monkeypatch):
    flags = {3: {"release_visible": True, "release_frame": 30, "head_down_f0": True, "exclude": None,
                 "task_text": "sort the bottles"}}
    rows = _rows(monkeypatch, "RB3", 16, flags=flags)
    assert rows and all(r["kind"] == "RB3" and r["img_rotate_cw"] == [] for r in rows)
    assert all(r["grip_unit"] == C.GRIP_UNIT["RB3"] and D.grip_source(r) == C.GRIP_UNIT["RB3"] for r in rows)
    assert all(r["release_visible"] is True and r["release_frame"] == 30 and r["head_down_f0"] is True for r in rows)
    assert all("exclude" not in r for r in rows)
    assert all(r["split"] == S.split_of("RB3", 3) for r in rows)
    # everything else equals the RB1 path on the same 16-D episode (same episode_rows)
    base = _rows(monkeypatch, "RB1", 16)
    drop = ("kind", "img_rotate_cw", "grip_unit", "release_visible", "release_frame", "head_down_f0", "split",
            "images")
    for a, b in zip(rows, base):
        assert {k: v for k, v in a.items() if k not in drop} == {k: v for k, v in b.items() if k not in drop}


def test_rb3_task_text_from_episode_flags(monkeypatch):
    """RB3's parquet task_index is wrong for 58 merged episodes (13, 14 are not in tasks.jsonl) -> the task text comes
    from meta/episodes.jsonl through the episode flags (required for RB3)."""
    f = {3: {"release_visible": False, "release_frame": None, "head_down_f0": True, "task_text": "pick the box"}}
    assert {r["task"] for r in _rows(monkeypatch, "RB3", 16, flags=f)} == {"pick the box"}
    assert {r["task"] for r in _rows(monkeypatch, "RB1", 16)} == {"sort the bottles"}
    with pytest.raises(KeyError):
        _rows(monkeypatch, "RB3", 16, flags={3: {"release_visible": False, "release_frame": None, "head_down_f0": 1}})


def test_flag_exclusions():
    flags = {1: {"exclude": None}, 2: {"exclude": "no_grasp"}, 3: {"exclude": None}}
    assert C.flag_excluded(flags) == [2]
    assert C.flag_excluded(None) == []


def test_rb3_needs_its_episode_flag(monkeypatch):
    with pytest.raises(KeyError):
        _rows(monkeypatch, "RB3", 16, flags={})


def test_hist_option_adds_causal_motion_source(monkeypatch):
    t, st, _ = _fake_pq(3, 16)
    rows = _rows(monkeypatch, "RB3", 16, flags={3: {"release_visible": False, "release_frame": None,
                                                    "head_down_f0": False, "task_text": "t"}}, hist=True)
    for r in rows:
        assert r["proprio"]["qd"] == r["motion_src"]["qd_bwd"]  # row velocity = motion source (causal, §83)
        assert r["proprio"]["grip"][1] == r["motion_src"]["grip_rate_bwd"]
        assert r["k_prev"] == max(0, r["k"] - 3)
    assert rows[0]["proprio"]["qd"] == [0.0] * 7
