"""Synthetic episode folders in the pool / DEV snapshot format (no Isaac, no images of substance)."""
import json
import os

import pytest


def make_line(seed, kind, k):
    x = 0.30 + 0.01 * k
    raw = {"grip": {"pos": [x, -0.10, 0.25 - 0.005 * k], "w": 0.107, "effort": 0.0},
           "objs": {"o3": {"pos": [0.42, -0.30, 0.05], "quat": [1, 0, 0, 0], "he": [0.03, 0.03, 0.05]},
                    "o5": {"pos": [0.45, 0.10, 0.01], "quat": [1, 0, 0, 0], "he": [0.1, 0.1, 0.01]}},
           "contacts": [], "support": {}}
    return {"seed": seed, "kind": kind, "k": k, "t": round(0.33 * k, 2), "ds_id": f"ds{k}", "phase": "approach",
            "decision": k % 3 == 0,
            "text_state": (f"t_state: f{k} (t={0.33 * k:.2f}s)  contract: c1  stage: S1 \"pick up mug o3\"\n"
                           "robot: gripper=open arm=moving\nfacts: gripper_open=yes holding(o3)=no lifted(o3)=no "
                           "upright(o3)=yes upright(o5)=yes"),
            "state": {"present": ["o3", "o5"], "obs": {"raw": raw}}, "oracle": {"dir_xy": "SECRET"},
            "images": {"cam_head": f"img/ep{seed}/k{k:03d}_cam_head.jpg",
                       "cam_wrist_right": f"img/ep{seed}/k{k:03d}_cam_wrist_right.jpg"}}


def write_episodes(d, seeds, kind="P0", n_k=8, events=None):
    os.makedirs(d, exist_ok=True)
    lab = []
    for s in seeds:
        os.makedirs(os.path.join(d, "img", f"ep{s}"), exist_ok=True)
        with open(os.path.join(d, f"ep{s}.jsonl"), "w", encoding="utf-8") as f:
            for k in range(n_k):
                ln = make_line(s, kind, k)
                f.write(json.dumps(ln) + "\n")
                for cam in ("cam_head", "cam_wrist_right"):
                    open(os.path.join(d, ln["images"][cam]), "wb").write(b"\xff\xd8jpg")
                lab.append({"seed": s, "kind": kind, "k": k, "labels_v2": {
                    "dir_xy": "plus_x_minus_y", "dir_z": "down", "mag_coarse": "xlarge", "target": "o3",
                    "phase_choice": "continue"}})
        json.dump({"seed": s, "kind": kind, "success": True, "events": events or []},
                  open(os.path.join(d, f"ep{s}.meta.json"), "w"))
    with open(d.rstrip("/\\") + ".labels_v2.jsonl", "a", encoding="utf-8") as f:
        for r in lab:
            f.write(json.dumps(r) + "\n")


@pytest.fixture
def dev_dirs(tmp_path):
    root = tmp_path / "jsel_dev"
    write_episodes(str(root / "P0"), [0, 1, 2], "P0")
    write_episodes(str(root / "P1"), [0, 1], "P1", events=[{"kind": "P1", "t": 0.9}])
    return {"P0": str(root / "P0"), "P1": str(root / "P1"), "root": str(root)}
