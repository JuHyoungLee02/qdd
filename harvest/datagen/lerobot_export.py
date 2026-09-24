"""R2 -> LeRobot v2.1 converter (codebase_version "v2.1", the format of the ROBOTIS AI Worker datasets, §63).

  python -m harvest.datagen.lerobot_export export --src R2_OUT --dst LEROBOT_ROOT [--include-invalid] [--codec libx264]
  python -m harvest.datagen.lerobot_export verify --dst LEROBOT_ROOT [--src R2_OUT]

Needs numpy, pyarrow, av (PyAV) and PIL (pod: venv_e3st). Layout written (same as ROBOTIS / lerobot 0.3.x):
  meta/info.json, meta/tasks.jsonl, meta/episodes.jsonl, meta/episodes_stats.jsonl, meta/r2_episodes.jsonl (ours:
  episode_index -> variant / task / kind / seed / source folder)
  data/chunk-000/episode_000000.parquet
  videos/chunk-000/observation.images.cam_head/episode_000000.mp4 (+ cam_wrist_right)
One LeRobot episode = one R2 episode (valid ones only by default). Frames are the 30 Hz ticks; `timestamp` =
frame_index / 30 exactly (what LeRobot syncs video frames on), the true sim time of the tick (off by 0 / +-3.3 ms,
timing.py) is the extra column `sim_time`. Columns: observation.state [q 7 + gripper width m], observation.velocity
[qd 7 + width rate], observation.effort [arm applied torque 7 + gripper joint torque], action [8] = action_exec (the
terminal frame repeats the last action, next.done = 1), action_script [8], phase_id, skill_id, decision.
Videos: re-encoded from the recorded JPEG q90 frames (libx264 yuv420p, g 2 like lerobot, crf 18), pts = frame_index.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from fractions import Fraction

import numpy as np

FPS = 30
CHUNK = 1000
CAMS = {"observation.images.cam_head": ("cam_head", 376, 672),
        "observation.images.cam_wrist_right": ("cam_wrist_right", 240, 424)}
JOINTS = [f"arm_r_joint{i}" for i in range(1, 8)]
PHASES = ("approach", "descend", "close", "lift", "carry", "place_descend", "open", "retreat", "done", "fail")
SKILLS = ("pick", "place")


def features(codec: str) -> dict:
    f = {"timestamp": {"dtype": "float32", "shape": [1], "names": None},
         "frame_index": {"dtype": "int64", "shape": [1], "names": None},
         "episode_index": {"dtype": "int64", "shape": [1], "names": None},
         "index": {"dtype": "int64", "shape": [1], "names": None},
         "task_index": {"dtype": "int64", "shape": [1], "names": None}}
    for key, (_, h, w) in CAMS.items():
        f[key] = {"dtype": "video", "names": ["height", "width", "channels"], "shape": [h, w, 3],
                  "info": {"video.height": h, "video.width": w, "video.channels": 3, "video.codec": codec,
                           "video.pix_fmt": "yuv420p", "video.fps": FPS, "video.is_depth_map": False,
                           "has_audio": False}}
    f["observation.state"] = {"dtype": "float32", "shape": [8], "names": JOINTS + ["gripper_r_width_m"]}
    f["observation.velocity"] = {"dtype": "float32", "shape": [8], "names": [j + "_vel" for j in JOINTS] +
                                 ["gripper_r_width_rate"]}
    f["observation.effort"] = {"dtype": "float32", "shape": [8], "names": [j + "_applied_torque" for j in JOINTS] +
                               ["gripper_r_joint1_applied_torque"]}
    f["action"] = {"dtype": "float32", "shape": [8], "names": JOINTS + ["gripper_r_width_m"]}
    f["action_script"] = {"dtype": "float32", "shape": [8], "names": JOINTS + ["gripper_r_width_m"]}
    f["sim_time"] = {"dtype": "float32", "shape": [1], "names": None}
    f["phase_id"] = {"dtype": "int64", "shape": [1], "names": None}
    f["skill_id"] = {"dtype": "int64", "shape": [1], "names": None}
    f["decision"] = {"dtype": "int64", "shape": [1], "names": None}
    f["next.done"] = {"dtype": "bool", "shape": [1], "names": None}
    return f


def episode_arrays(folder: str, seed: int) -> dict:
    """Per-frame arrays of one R2 episode in LeRobot column order (pure numpy)."""
    z = np.load(f"{folder}/ep{seed}.npz")
    lines = [json.loads(x) for x in open(f"{folder}/ep{seed}.jsonl", encoding="utf-8")]
    n = len(lines)
    grip = np.asarray(z["grip"], np.float32)
    st = np.concatenate([z["q"], grip[:, :1]], 1).astype(np.float32)
    vel = np.concatenate([z["qd"], grip[:, 1:2]], 1).astype(np.float32)
    eff = np.concatenate([z["tau"], np.asarray(z["grip_tau"], np.float32).reshape(-1, 1)], 1).astype(np.float32)
    act = np.asarray(z["action"], np.float32)
    phase = np.array([PHASES.index(ln["phase"]) if ln["phase"] in PHASES else -1 for ln in lines], np.int64)
    skill = np.array([0 if ln["phase"] in PHASES[:4] else 1 for ln in lines], np.int64)
    dec = np.array([int(bool(ln["decision"])) for ln in lines], np.int64)
    done = np.zeros(n, bool)
    done[-1] = True
    return {"n": n, "observation.state": st, "observation.velocity": vel, "observation.effort": eff, "action": act,
            "action_script": act.copy(), "sim_time": np.asarray(z["t"], np.float32), "phase_id": phase,
            "skill_id": skill, "decision": dec, "next.done": done, "lines": lines}


def _stats(a: np.ndarray) -> dict:
    a = np.asarray(a)
    x = a.reshape(len(a), -1).astype(np.float64)
    return {"min": x.min(0).tolist(), "max": x.max(0).tolist(), "mean": x.mean(0).tolist(), "std": x.std(0).tolist(),
            "count": [int(len(a))]}


def _img_stats(frames) -> dict:
    """lerobot image stats: per channel over sampled frames, values in [0, 1], shape (3, 1, 1)."""
    x = np.stack(frames).astype(np.float64) / 255.0  # [n, h, w, 3]
    ch = x.reshape(-1, 3)
    wrap = lambda v: [[[float(c)]] for c in v]  # noqa: E731
    return {"min": wrap(ch.min(0)), "max": wrap(ch.max(0)), "mean": wrap(ch.mean(0)), "std": wrap(ch.std(0)),
            "count": [len(frames)]}


def _encode(paths, dst, codec, h, w, crf=18):
    import av
    from PIL import Image
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with av.open(dst, "w") as out:
        s = out.add_stream(codec, rate=FPS)
        s.width, s.height, s.pix_fmt = w, h, "yuv420p"
        s.time_base = Fraction(1, FPS)
        s.options = {"g": "2", "crf": str(crf)}
        for i, p in enumerate(paths):
            fr = av.VideoFrame.from_ndarray(np.asarray(Image.open(p).convert("RGB")), format="rgb24")
            fr.pts = i
            for pkt in s.encode(fr):
                out.mux(pkt)
        for pkt in s.encode():
            out.mux(pkt)


def _write_parquet(cols: dict, feats: dict, dst: str):
    import pyarrow as pa
    import pyarrow.parquet as pq
    arrays, names = [], []
    for k, v in cols.items():
        f = feats[k]
        if f["shape"] == [1]:
            t = {"float32": pa.float32(), "int64": pa.int64(), "bool": pa.bool_()}[f["dtype"]]
            arrays.append(pa.array(np.asarray(v).reshape(-1), type=t))
        else:
            flat = pa.array(np.asarray(v, np.float32).reshape(-1), type=pa.float32())
            arrays.append(pa.FixedSizeListArray.from_arrays(flat, f["shape"][0]))
        names.append(k)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    pq.write_table(pa.Table.from_arrays(arrays, names=names), dst)


def export(src: str, dst: str, include_invalid: bool = False, codec: str = "libx264") -> dict:
    feats = features(codec)
    metas = []
    for mp in sorted(glob.glob(f"{src}/*/*/*/ep*.meta.json")):
        m = json.load(open(mp, encoding="utf-8"))
        if include_invalid or m.get("valid_for_training"):
            metas.append((m["variant"], m["task"], m["kind"], int(m["seed"]), os.path.dirname(mp), m))
    metas.sort(key=lambda x: x[:4])
    tasks, ep_rows, st_rows, r2_rows = {}, [], [], []
    index = 0
    os.makedirs(f"{dst}/meta", exist_ok=True)
    for ei, (v, task, kind, seed, folder, m) in enumerate(metas):
        A = episode_arrays(folder, seed)
        n, lines = A["n"], A["lines"]
        ti = tasks.setdefault(m["instruction"], len(tasks))
        chunk = ei // CHUNK
        cols = {"timestamp": np.arange(n, dtype=np.float32) / FPS, "frame_index": np.arange(n),
                "episode_index": np.full(n, ei), "index": np.arange(index, index + n), "task_index": np.full(n, ti)}
        for k in ("observation.state", "observation.velocity", "observation.effort", "action", "action_script",
                  "sim_time", "phase_id", "skill_id", "decision", "next.done"):
            cols[k] = A[k]
        _write_parquet(cols, feats, f"{dst}/data/chunk-{chunk:03d}/episode_{ei:06d}.parquet")
        stats = {k: _stats(np.asarray(c).reshape(n, -1)) for k, c in cols.items()}
        from PIL import Image
        for key, (cam, h, w) in CAMS.items():
            paths = [os.path.join(folder, ln["images"][cam]) for ln in lines]
            _encode(paths, f"{dst}/videos/chunk-{chunk:03d}/{key}/episode_{ei:06d}.mp4", codec, h, w)
            pick = paths[:: max(1, n // 20)]
            stats[key] = _img_stats([np.asarray(Image.open(p).convert("RGB")) for p in pick])
        ep_rows.append({"episode_index": ei, "tasks": [m["instruction"]], "length": n})
        st_rows.append({"episode_index": ei, "stats": stats})
        r2_rows.append({"episode_index": ei, "variant": v, "task": task, "kind": kind, "seed": seed,
                        "src": os.path.relpath(folder, src), "success": m["success"],
                        "valid_for_training": m.get("valid_for_training")})
        index += n
    info = {"codebase_version": "v2.1", "robot_type": "ffw_sg2", "total_episodes": len(metas),
            "total_frames": index, "total_tasks": len(tasks), "total_videos": len(metas) * len(CAMS),
            "total_chunks": (len(metas) + CHUNK - 1) // CHUNK, "chunks_size": CHUNK, "fps": FPS,
            "splits": {"train": f"0:{len(metas)}"},
            "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
            "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4",
            "features": feats}
    with open(f"{dst}/meta/info.json", "w") as f:
        json.dump(info, f, indent=4)
    for name, rows in (("tasks", [{"task_index": i, "task": t} for t, i in sorted(tasks.items(), key=lambda x: x[1])]),
                       ("episodes", ep_rows), ("episodes_stats", st_rows), ("r2_episodes", r2_rows)):
        with open(f"{dst}/meta/{name}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    out = {"episodes": len(metas), "frames": index, "tasks": len(tasks), "bytes": _du(dst)}
    print("EXPORT " + json.dumps(out), flush=True)
    return out


def _du(root):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs)


def verify(dst: str, src: str | None = None) -> dict:
    """Read the export back (1) with pyarrow + PyAV: row counts, timestamps = k/30, video frame count and pts,
    decoded frame vs the source JPEG (PSNR), action equal to the R2 npz; (2) with lerobot's LeRobotDataset when
    importable (the real consumer)."""
    import av
    import pyarrow.parquet as pq
    info = json.load(open(f"{dst}/meta/info.json"))
    r2 = [json.loads(x) for x in open(f"{dst}/meta/r2_episodes.jsonl")]
    rep = {"episodes": info["total_episodes"], "checked": 0, "errors": [], "psnr_min_db": None}
    psnrs = []
    for e in r2:
        ei = e["episode_index"]
        t = pq.read_table(f"{dst}/data/chunk-{ei // CHUNK:03d}/episode_{ei:06d}.parquet").to_pydict()
        n = len(t["frame_index"])
        if not np.allclose(t["timestamp"], np.arange(n) / FPS, atol=1e-6):
            rep["errors"].append(f"ep{ei}: timestamps")
        for key, (cam, h, w) in CAMS.items():
            with av.open(f"{dst}/videos/chunk-{ei // CHUNK:03d}/{key}/episode_{ei:06d}.mp4") as c:
                fr = list(c.decode(video=0))
            tdev = max(abs(float(f.time) - i / FPS) for i, f in enumerate(fr)) if fr else 1.0
            if len(fr) != n or tdev > 1e-4 or (fr[0].height, fr[0].width) != (h, w):  # lerobot tolerance_s 1e-4
                rep["errors"].append(f"ep{ei} {key}: {len(fr)} frames, time dev {tdev:.2e} s, size")
            if src:
                from PIL import Image
                lines = [json.loads(x) for x in open(f"{src}/{e['src']}/ep{e['seed']}.jsonl")]
                for k in (0, n // 2, n - 1):
                    a = np.asarray(Image.open(f"{src}/{e['src']}/{lines[k]['images'][cam]}").convert("RGB"), float)
                    b = fr[k].to_ndarray(format="rgb24").astype(float)
                    psnrs.append(10 * np.log10(255 ** 2 / max(((a - b) ** 2).mean(), 1e-9)))
        if src:
            z = np.load(f"{src}/{e['src']}/ep{e['seed']}.npz")
            if not np.array_equal(np.asarray(t["action"], np.float32), np.asarray(z["action"], np.float32)):
                rep["errors"].append(f"ep{ei}: action differs from the R2 npz")
        rep["checked"] += 1
    if psnrs:
        rep["psnr_min_db"] = round(float(min(psnrs)), 2)
    try:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
    except Exception as ex:  # noqa: BLE001
        try:
            from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
        except Exception:  # noqa: BLE001
            rep["lerobot"] = f"not importable ({type(ex).__name__}: {ex})"
            LeRobotDataset = None
    if LeRobotDataset is not None:
        import lerobot
        ds = LeRobotDataset("qdd/r2_dev", root=dst, video_backend="pyav")
        items = [ds[i] for i in (0, len(ds) // 2, len(ds) - 1)]
        lr = {"version": getattr(lerobot, "__version__", "?"), "num_frames": ds.num_frames,
              "num_episodes": ds.num_episodes, "fps": ds.fps,
              "item_keys": sorted(items[0].keys()),
              "image_shape": list(items[0]["observation.images.cam_head"].shape),
              "wrist_shape": list(items[0]["observation.images.cam_wrist_right"].shape),
              "task0": items[0].get("task")}
        z0 = np.asarray(pq.read_table(f"{dst}/data/chunk-000/episode_000000.parquet").to_pydict()["action"][0])
        lr["action0_equal"] = bool(np.allclose(items[0]["action"].numpy(), z0))
        rep["lerobot"] = lr
    rep["pass"] = not rep["errors"] and (rep["psnr_min_db"] is None or rep["psnr_min_db"] >= 30)
    print("VERIFY " + json.dumps(rep), flush=True)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["export", "verify"])
    ap.add_argument("--src")
    ap.add_argument("--dst", required=True)
    ap.add_argument("--include-invalid", action="store_true")
    ap.add_argument("--codec", default="libx264")
    a = ap.parse_args(argv)
    if a.mode == "export":
        export(a.src, a.dst, a.include_invalid, a.codec)
    else:
        verify(a.dst, a.src)


if __name__ == "__main__":
    main()
