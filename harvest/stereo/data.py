"""E3-ST data loading: ROBOTIS LeRobot v2.1 head stereo pairs (cam_head = left, cam_head_right = right).

Only the episodes fetched by the E3-ST download script are expected under `root`
(layout mirrors the HF repo: videos/chunk-000/observation.images.<key>/episode_XXXXXX.mp4).
Requires PyAV (`av`) at call time.
"""
from __future__ import annotations

import json
import os
from typing import Iterator

import numpy as np

DEFAULT_ROOT = os.environ.get("E3ST_DATA", "/data/juhyoung_qdd/data/e3st")
LEFT_KEY = "observation.images.cam_head"
RIGHT_KEY = "observation.images.cam_head_right"


def _repo_dir(repo: str, root: str) -> str:
    name = repo.split("/")[-1]
    return os.path.join(root, name)


def video_path(repo: str, episode: int, key: str, root: str = DEFAULT_ROOT, chunk_size: int = 1000) -> str:
    return os.path.join(
        _repo_dir(repo, root), "videos", f"chunk-{episode // chunk_size:03d}", key, f"episode_{episode:06d}.mp4"
    )


def fps(repo: str, root: str = DEFAULT_ROOT) -> float:
    with open(os.path.join(_repo_dir(repo, root), "meta", "info.json"), encoding="utf-8") as f:
        return float(json.load(f)["fps"])


def _frames(path: str) -> Iterator[np.ndarray]:
    import av  # local import: only needed on the pod

    with av.open(path) as c:
        for fr in c.decode(video=0):
            yield fr.to_ndarray(format="rgb24")


def load_pairs(repo: str, episode: int, max_frames: int, root: str = DEFAULT_ROOT) -> Iterator[tuple]:
    """Yield (t_seconds, left_rgb HxWx3 uint8, right_rgb HxWx3 uint8) for the first `max_frames` frames.

    Stops at the shorter of the two streams (frame counts are checked by the caller via the count).
    """
    hz = fps(repo, root)
    left = _frames(video_path(repo, episode, LEFT_KEY, root))
    right = _frames(video_path(repo, episode, RIGHT_KEY, root))
    for i, (l, r) in enumerate(zip(left, right)):
        if i >= max_frames:
            break
        yield i / hz, l, r
