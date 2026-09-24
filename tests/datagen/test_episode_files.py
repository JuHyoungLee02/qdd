"""R2 episode files: finalize -> validate -> merge on a synthetic (Isaac-free) episode, and the lock queue."""
import json
import os

import numpy as np
import pytest

from harvest.datagen import episode as E
from harvest.datagen import queue as Q
from harvest.datagen import validate as V
from harvest.datagen.timing import tick_time
from harvest.train.stageb_data import load_stageb, read_rows

PIL = pytest.importorskip("PIL.Image")


def _fake_episode(folder, seed=3, n=23, task="bottle_tray", kind="P0", success=True):
    """n frames (k = 0..n-1) of a bottle approach: gripper descending toward o8; JPEGs at native size."""
    img_dir = f"{folder}/img/ep{seed}"
    os.makedirs(img_dir, exist_ok=True)
    frames, actions, holds = [], [], []
    tgt, place = "o8", "o5"
    for k in range(n):
        t = tick_time(k)
        g = [0.40, -0.30, 0.25 - 0.003 * k]
        pred = {"gripper_open": True, "holding(o8)": False, "lifted(o8)": False, "upright(o8)": True,
                "near(o8,o5)": False, "in_contact(o8,o5)": False, "on(o8,o5)": False, "above(o8,o5)": False,
                "holding(o3)": False, "upright(o3)": True, "upright(o5)": True}
        raw = {"objs": {"o3": {"pos": [0.5, 0.0, 0.0475], "quat": [1, 0, 0, 0], "he": [0.032, 0.032, 0.0475]},
                        "o5": {"pos": [0.46, -0.12, 0.0075], "quat": [1, 0, 0, 0], "he": [0.09, 0.07, 0.0075]},
                        "o8": {"pos": [0.42, -0.30, 0.05], "quat": [1, 0, 0, 0], "he": [0.025, 0.025, 0.05]}},
               "grip": {"w": 0.107, "effort": 0.0, "pos": g}, "contacts": [], "support": {"o3": "table", "o5": "table",
                                                                                         "o8": "table"}}
        ims = {}
        for cam, (w, h) in V.NATIVE.items():
            p = f"{img_dir}/f{k:04d}_{cam}.jpg"
            PIL.fromarray(np.full((h, w, 3), 80 + k, np.uint8)).save(p, quality=90)
            ims[cam] = os.path.relpath(p, folder).replace("\\", "/")
        frames.append({"k": k, "t": t, "phase": "approach", "t_in_phase": t, "pred": pred, "support": raw["support"],
                       "present": ["o3", "o5", "o8"], "arm_moving": True, "changes": [], "raw": raw, "images": ims,
                       "proprio": {"q": [0.1 * k] * 7, "qd": [0.0] * 7, "tau": [1.0] * 7, "grip": [0.107, 0.0]},
                       "contact_open": False})
        if k < n - 1:
            actions.append([0.1 * k] * 7 + [0.107])
            holds.append(int(round((tick_time(k + 1) - t) / 0.01)))
    stream = {"t": [f["t"] for f in frames], "q": [f["proprio"]["q"] for f in frames],
              "qd": [[0.0] * 7] * n, "tau": [[1.0] * 7] * n, "grip": [[0.107, 0.0]] * n, "grip_tau": [0.0] * n,
              "obj_pose": np.zeros((n, 5, 7)), "obj_ids": ["o3", "o5", "o8", "o9", "o10"]}
    return {"seed": seed, "kind": kind, "task": task, "variant": "dr", "split": "dev", "frames": frames,
            "actions": actions, "hold_n": holds, "stream": stream,
            "meta": {"success": success, "stage": None, "events": []}}


def test_finalize_validate_merge_and_load_stageb(tmp_path):
    folder = str(tmp_path / "dr" / "bottle_tray" / "P0")
    meta = E.finalize(_fake_episode(folder), folder, H=15)
    assert meta["n_frames"] == 23 and meta["n_rows"] == 22 and meta["n_decisions"] == 3  # k 0, 10, 20
    rep = V.validate_episode(folder, 3)
    assert rep["errors"] == [] and rep["valid_for_training"] and rep["images"] == 46
    V.stamp(folder, 3, rep)
    lines = [json.loads(x) for x in open(f"{folder}/ep3.jsonl")]
    assert lines[10]["decision"] and lines[10]["ds_id"] == "ds1" and lines[11]["ds_id"] is None
    assert lines[10]["verify"]["prev_step"]["k0"] == 0 and lines[22]["verify"]["prev_step"]["k0"] == 20
    assert "place bottle o8 on tray o5" not in lines[0]["text_state"] and "pick up bottle o8" in lines[0]["text_state"]
    labs = [json.loads(x) for x in open(f"{folder}/rows/ep3.labels_v2.jsonl")]
    assert labs[0]["labels_v2"]["target"] == "o8" and labs[0]["labels_v2"]["dir_xy"] == "plus_x"
    c = E.merge(folder)
    assert c["episodes"] == 1 and c["rows"] == 22 and c["labels"] == 3
    rows = read_rows(folder + ".stageb.jsonl")
    assert rows[(3, "P0", 21)]["valid"] == [1] + [0] * 14
    samples = load_stageb(folder, dev_val_seeds={3})
    assert len(samples) == 22 and samples[0]["split"] == "val"
    dec = [s for s in samples if s["items"]]
    assert len(dec) == 3 and {it["question"] for it in dec[0]["items"]} == {"dir_xy", "dir_z", "mag_coarse", "target",
                                                                            "phase"}
    tgt = [it for it in dec[0]["items"] if it["question"] == "target"][0]
    assert tgt["target"] == ["o8"] and [lab for lab, _ in samples[0]["context"]["images"]] == [
        "head camera:", "right wrist camera (active arm):"]


def test_validate_flags_missing_images_and_failed_episodes(tmp_path):
    folder = str(tmp_path / "f")
    E.finalize(_fake_episode(folder, success=False), folder)
    os.remove(f"{folder}/img/ep3/f0005_cam_wrist_right.jpg")
    rep = V.validate_episode(folder, 3)
    assert not rep["structural_ok"] and not rep["valid_for_training"]
    assert any("missing cam_wrist_right" in e for e in rep["errors"])
    V.stamp(folder, 3, rep)
    assert E.merge(folder)["skipped_invalid"] == [3]


def test_finalize_refuses_action_count_mismatch(tmp_path):
    ep = _fake_episode(str(tmp_path / "g"), n=5)
    ep["actions"] = ep["actions"][:-1]
    with pytest.raises(ValueError):
        E.finalize(ep, str(tmp_path / "g"))


def test_lerobot_columns_from_an_episode(tmp_path):
    from harvest.datagen import lerobot_export as LX
    folder = str(tmp_path / "lx")
    E.finalize(_fake_episode(folder, n=12), folder)
    A = LX.episode_arrays(folder, 3)
    assert A["n"] == 12 and A["observation.state"].shape == (12, 8) and A["action"].shape == (12, 8)
    assert np.array_equal(A["action"][-1], A["action"][-2])  # terminal frame repeats the last command
    assert A["next.done"].tolist() == [False] * 11 + [True] and A["decision"].tolist()[:11] == [1] + [0] * 9 + [1]
    f = LX.features("libx264")
    assert f["observation.images.cam_head"]["shape"] == [376, 672, 3] and f["action"]["shape"] == [8]
    for k in ("observation.state", "observation.velocity", "observation.effort", "action", "action_script"):
        assert len(f[k]["names"]) == f[k]["shape"][0]
    s = LX._stats(A["observation.state"])
    assert len(s["mean"]) == 8 and s["count"] == [12]


def test_lerobot_export_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    pytest.importorskip("av")
    from harvest.datagen import lerobot_export as LX
    src = tmp_path / "r2"
    folder = str(src / "dr" / "bottle_tray" / "P0")
    E.finalize(_fake_episode(folder, n=12), folder)
    V.stamp(folder, 3, V.validate_episode(folder, 3))
    out = LX.export(str(src), str(tmp_path / "lr"))
    assert out["episodes"] == 1 and out["frames"] == 12
    rep = LX.verify(str(tmp_path / "lr"), str(src))
    assert rep["errors"] == []


def test_queue_claims_once_resumes_and_takes_over_stale_locks(tmp_path):
    out = str(tmp_path / "q")
    items = Q.plan(["dr"], ["mug_tray", "box_marker"], ["P0"], [0, 1])
    assert items[:2] == [("dr", "mug_tray", "P0", 0), ("dr", "box_marker", "P0", 0)]
    it = items[0]
    assert Q.claim(out, it) and not Q.claim(out, it)  # second process loses
    assert not Q.claim(out, it, stale_s=3600)  # fresh lock is not stale
    assert Q.claim(out, it, stale_s=10, now=os.path.getmtime(f"{out}/_queue/{Q.item_name(*it)}.lock") + 60)
    folder = Q.ep_folder(out, *it[:3])
    os.makedirs(folder)
    open(f"{folder}/ep0.meta.json", "w").write("{}")
    Q.release(out, it)
    assert not Q.claim(out, it)  # done items are never taken again
    assert Q.status(out, items) == {"items": 4, "done": 1, "in_progress": 0, "todo": 3}
