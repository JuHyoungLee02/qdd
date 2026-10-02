"""Unit tests for harvest.l9art.build_art and tools.l9art.gate_art against a tiny synthetic collect root (no sim,
no real episodes): meta.json / labels.jsonl / calls/cNNN/* built by hand, images are tiny PIL PNGs."""
from __future__ import annotations

import json
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.l9art import build_art as BA  # noqa: E402
from tools.l9art import gate_art as GA  # noqa: E402

CAMS = {"head": {"W": 672, "H": 376, "fx": 400.0, "fy": 400.0, "cx": 336.0, "cy": 188.0,
                 "R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "t": [0.0, 0.0, 1.0]}}


def _answer(cmd: dict) -> str:
    return json.dumps({"assessment": {"task_progress": {"verified_completed": [], "currently_attempting": "x",
                                                         "remaining": []}, "execution_status": "progressing",
                                      "evidence": "e", "evidence_view": "both", "confidence": "high"},
                       "command": cmd, "reason": "r"})


def _write_call(ep_dir: str, call: int):
    d = os.path.join(ep_dir, "calls", f"c{call:03d}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "prompt_v3.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"call {call} prompt\n")
    Image.new("RGB", (8, 8), (10, 20, 30)).save(os.path.join(d, "img1_head_ring.png"))
    Image.new("RGB", (8, 8), (40, 50, 60)).save(os.path.join(d, "img2_right_wrist_camera.png"))
    json.dump(CAMS, open(os.path.join(d, "cams.json"), "w"))
    return d


def make_episode(root: str, did: str, seed: int, arm: str, robot: str, success: bool, split: str = "train",
                  rows=None, skills_v3=None, extra_meta=None) -> str:
    ep_dir = os.path.join(root, split, did, f"{did}_s{seed}_{arm}")
    os.makedirs(ep_dir, exist_ok=True)
    meta = {"robot": robot, "success": success, "end_reason": "stop" if success else "too_many_failures",
            "task_id": did, "skills_v3": skills_v3 or ["pull_axis"], "seed": seed, "max_dq_rad": 0.02,
            "fail_counts": {} if success else {"approach_fail": 1}, "draw": {"u": 0.1, "pitch": 0.2, "yaw": -0.05}}
    if extra_meta:
        meta.update(extra_meta)
    json.dump(meta, open(os.path.join(ep_dir, "meta.json"), "w"))
    rows = rows or default_rows()
    with open(os.path.join(ep_dir, "labels.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            _write_call(ep_dir, r["call"])
            f.write(json.dumps(r) + "\n")
    return ep_dir


def default_rows():
    above = {"mode": "point", "skill": "pull_axis", "point_2d": [500, 300], "height": "above", "gripper": "open",
             "hand": "right", "approach": "front", "rot": 3}
    move = {"mode": "point", "skill": "pull_axis", "point_2d": [500, 300], "point2": [400, 300], "height": "grasp",
            "gripper": "keep", "hand": "right", "axis": "linear", "amount_cm": 10.0}
    return [
        {"call": 1, "stage": 0, "sub": "above", "skill": "pull_axis", "answer": _answer(above), "command": above,
         "joints": {}, "tcp": [0, 0, 0], "grip_w": 0.1, "drop": None},
        {"call": 2, "stage": 0, "sub": "move", "skill": "pull_axis", "answer": _answer(move), "command": move,
         "joints": {}, "tcp": [0, 0, 0], "grip_w": 0.0, "drop": None},
    ]


def make_skipped(root: str, did: str, seed: int, arm: str, robot: str, split: str = "train"):
    ep_dir = os.path.join(root, split, did, f"{did}_s{seed}_{arm}")
    os.makedirs(ep_dir, exist_ok=True)
    json.dump({"row": {"seed": seed, "def": did, "arm": arm, "robot": robot}, "reason": "ValueError: no fitting part"},
              open(os.path.join(ep_dir, "skipped.json"), "w"))


# ------------------------------------------------------------------ build_art
def test_label_missing_of():
    assert BA.label_missing_of({"command": {"mode": "point", "point_2d": None}}) is True
    assert BA.label_missing_of({"sub": "move", "command": {"mode": "point", "point_2d": [1, 1], "point2": None}}) is True
    assert BA.label_missing_of({"sub": "above", "command": {"mode": "point", "point_2d": [1, 1]}}) is False
    assert BA.label_missing_of({"command": {"mode": "gripper", "gripper": "open"}}) is False


def test_build_train_drops_failed_episode_and_missing_label(tmp_path):
    root = str(tmp_path)
    make_episode(root, "drawer_open", 1, "right", "ffw_sg2", True)
    make_episode(root, "drawer_open", 2, "right", "ffw_sg2", False)  # whole episode dropped (train)
    ep_dirs = BA.find_episode_dirs(root, "train")
    assert len(ep_dirs) == 2
    out = str(tmp_path / "out")
    res = BA.build(ep_dirs, out, "train", "train_art", train=True)
    assert res["control_rows"] == 2  # only the successful episode's 2 calls
    rows = [json.loads(ln) for ln in open(res["path"], encoding="utf-8")]
    assert all(not r["label_missing"] for r in rows)
    assert all(r["success"] for r in rows)
    assert {r["gen"] for r in rows} == {"l9art"}
    assert {r["gen_version"] for r in rows} == {"v3"}
    assert {r["source"] for r in rows} == {"l9art/ffw_sg2"}
    assert all(r["camera"].startswith("camera: head") for r in rows)
    assert all(os.path.exists(r["prompt_path"]) for r in rows)
    assert all(os.path.exists(p) for r in rows for p in r["images"])


def test_build_train_drops_label_missing_row(tmp_path):
    root = str(tmp_path)
    bad = {"mode": "point", "skill": "pull_axis", "point_2d": None, "height": "above", "gripper": "open", "hand": "right"}
    rows = default_rows() + [{"call": 3, "stage": 0, "sub": "above", "skill": "pull_axis", "answer": _answer(bad),
                              "command": bad, "joints": {}, "tcp": [0, 0, 0], "grip_w": 0.1, "drop": "not_visible"}]
    make_episode(root, "drawer_open", 1, "right", "ffw_sg2", True, rows=rows)
    out = str(tmp_path / "out")
    res = BA.build(BA.find_episode_dirs(root, "train"), out, "train", "train_art", train=True)
    assert res["control_rows"] == 2
    assert res["label_missing"] == 0


def test_build_eval_keeps_all_rows_flagged(tmp_path):
    root = str(tmp_path)
    bad = {"mode": "point", "skill": "pull_axis", "point_2d": None, "height": "above", "gripper": "open", "hand": "right"}
    rows = default_rows() + [{"call": 3, "stage": 0, "sub": "above", "skill": "pull_axis", "answer": _answer(bad),
                              "command": bad, "joints": {}, "tcp": [0, 0, 0], "grip_w": 0.1, "drop": "not_visible"}]
    make_episode(root, "drawer_open", 1, "right", "ffw_sg2", False, rows=rows)  # failed episode
    out = str(tmp_path / "out")
    res = BA.build(BA.find_episode_dirs(root, "train"), out, "train", "eval_art", train=False)
    assert res["control_rows"] == 3  # eval keeps the failed episode's rows too
    assert res["label_missing"] == 1
    rows_out = [json.loads(ln) for ln in open(res["path"], encoding="utf-8")]
    assert sum(r["label_missing"] for r in rows_out) == 1
    assert all(not r["success"] for r in rows_out)


def test_build_skips_episode_without_labels(tmp_path):
    root = str(tmp_path)
    make_episode(root, "drawer_open", 1, "right", "ffw_sg2", True)
    make_skipped(root, "drawer_open", 2, "right", "ffw_sg2")
    ep_dirs = BA.find_episode_dirs(root, "train")  # skipped.json has no meta.json -> glob finds only 1
    assert len(ep_dirs) == 1
    out = str(tmp_path / "out")
    res = BA.build(ep_dirs, out, "train", "train_art", train=True)
    assert res["control_rows"] == 2
    assert res["episodes"] == 1


def test_check_rows_ok_and_bad(tmp_path):
    root = str(tmp_path)
    make_episode(root, "drawer_open", 1, "right", "ffw_sg2", True)
    out = str(tmp_path / "out")
    res = BA.build(BA.find_episode_dirs(root, "train"), out, "train", "train_art", train=True)
    rows = [json.loads(ln) for ln in open(res["path"], encoding="utf-8")]
    chk = BA.check_rows(rows)
    assert chk["n_errors"] == 0

    broken = [dict(rows[0], prompt_path="/no/such/file.txt")]
    chk2 = BA.check_rows(broken)
    assert chk2["n_errors"] == 1

    bad_skill = json.loads(rows[0]["answer"])
    bad_skill["command"]["skill"] = "not_a_skill"
    broken2 = [dict(rows[0], answer=json.dumps(bad_skill))]
    chk3 = BA.check_rows(broken2)
    assert chk3["n_errors"] == 1


# ------------------------------------------------------------------ gate_art
def test_wilson_bounds():
    p, lo, hi = GA.wilson(0, 0)
    assert (p, lo, hi) == (0.0, 0.0, 1.0)
    p, lo, hi = GA.wilson(10, 10)
    assert p == 1.0 and hi <= 1.0 and lo > 0.5
    p, lo, hi = GA.wilson(5, 10)
    assert p == 0.5 and lo < 0.5 < hi


def test_collect_and_summarize_fail_group(tmp_path):
    root = str(tmp_path)
    make_episode(root, "drawer_open", 1, "right", "ffw_sg2", True)
    make_episode(root, "drawer_open", 2, "right", "ffw_sg2", False)
    make_skipped(root, "drawer_open", 3, "right", "ffw_sg2")
    groups = GA.collect(root, "train")
    key = ("drawer_open", "ffw_sg2")
    assert key in groups
    assert len(groups[key]["episodes"]) == 2
    assert groups[key]["n_skipped"] == 1
    res = GA.summarize(groups, min_succ=0.70)
    s = res["drawer_open|ffw_sg2"]
    assert s["n_episodes"] == 2 and s["n_success"] == 1
    assert s["success_rate"] == 0.5
    assert s["n_skipped"] == 1
    assert s["diversity"]["needs_approach_diversity"] is True
    assert s["diversity"]["n_approach_families"] == 1  # only "front" used in default_rows()
    assert s["verdict"]["pass"] is False
    assert any("usable_rate" in r for r in s["verdict"]["reasons"])
    assert any("approach_families" in r for r in s["verdict"]["reasons"])


def test_summarize_pass_group_no_grasp_requirement(tmp_path):
    root = str(tmp_path)
    press = {"mode": "point", "skill": "press", "point_2d": [500, 300], "height": "grasp", "gripper": "keep",
              "hand": "right"}
    rows = [{"call": 1, "stage": 0, "sub": "above", "skill": "press", "answer": _answer(press), "command": press,
             "joints": {}, "tcp": [0, 0, 0], "grip_w": 0.1, "drop": None}]
    for s in (10, 11, 12):
        make_episode(root, "button_press", s, "right", "franka_mast", True, rows=rows, skills_v3=["press"])
    groups = GA.collect(root, "train")
    res = GA.summarize(groups, min_succ=0.70)
    s = res["button_press|franka_mast"]
    assert s["n_episodes"] == 3 and s["success_rate"] == 1.0
    assert s["diversity"]["needs_approach_diversity"] is False
    assert s["verdict"]["pass"] is True
    assert s["verdict"]["reasons"] == []


def test_to_markdown_has_header_and_rows(tmp_path):
    root = str(tmp_path)
    make_episode(root, "drawer_open", 1, "right", "ffw_sg2", True)
    groups = GA.collect(root, "train")
    res = GA.summarize(groups)
    md = GA.to_markdown(res)
    assert md.startswith("| def |")
    assert "drawer_open" in md and "ffw_sg2" in md


def test_make_sheet(tmp_path):
    root = str(tmp_path)
    ep = make_episode(root, "drawer_open", 1, "right", "ffw_sg2", True)
    groups = GA.collect(root, "train")
    out_png = str(tmp_path / "sheets" / "drawer_open_ffw_sg2.jpg")
    p = GA.make_sheet(groups[("drawer_open", "ffw_sg2")]["episodes"], out_png)
    assert p == out_png
    assert os.path.exists(out_png)


def test_label_presence_share():
    missing_point2 = {"mode": "point", "skill": "pull_axis", "point_2d": [1, 1], "point2": None, "height": "grasp",
                       "gripper": "keep", "hand": "right"}
    rows = [{"call": 2, "stage": 0, "sub": "move", "skill": "pull_axis", "answer": _answer(missing_point2),
             "command": missing_point2, "joints": {}, "tcp": [0, 0, 0], "grip_w": 0.0, "drop": None}]
    stats = GA._group_stats([("x", {"draw": {}, "skills_v3": []}, rows)])
    assert stats["label_presence"]["point2_share"] == 0.0
    assert stats["label_presence"]["point_2d_share"] == 1.0
    assert stats["label_presence"]["overall"] == 0.5  # 1 of 2 required pixels present (point_2d ok, point2 missing)
