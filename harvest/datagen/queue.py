"""File-lock work queue for the R2 generator (pure; POSIX / Lustre-safe O_CREAT|O_EXCL).

An item = (variant, task, kind, seed). Several processes walk the same item list; a process takes an item only if
it creates `<out>/_queue/<item>.lock` exclusively and the item is not done (its ep<seed>.meta.json exists). A lock
older than stale_s whose item is not done (a crashed worker) may be taken over. Resumable: done items are skipped.
"""
from __future__ import annotations

import json
import os
import socket
import time


def item_name(variant: str, task: str, kind: str, seed: int) -> str:
    return f"{variant}.{task}.{kind}.{int(seed)}"


def ep_folder(out: str, variant: str, task: str, kind: str) -> str:
    return f"{out}/{variant}/{task}/{kind}"


def is_done(out: str, variant: str, task: str, kind: str, seed: int) -> bool:
    return os.path.exists(f"{ep_folder(out, variant, task, kind)}/ep{int(seed)}.meta.json")


def plan(variants, tasks, kinds, seeds) -> list:
    """Seed-major order: all (task, kind) of one seed before the next seed (a partial run stays balanced)."""
    return [(v, t, k, s) for s in seeds for v in variants for t in tasks for k in kinds]


def _lock(out: str, item: str) -> str:
    return f"{out}/_queue/{item}.lock"


def claim(out: str, item: tuple, stale_s: float | None = None, now: float | None = None) -> bool:
    v, t, k, s = item
    if is_done(out, v, t, k, s):
        return False
    os.makedirs(f"{out}/_queue", exist_ok=True)
    p = _lock(out, item_name(*item))
    for attempt in range(2):
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            if attempt == 0 and stale_s is not None and (now or time.time()) - os.path.getmtime(p) > stale_s:
                try:
                    os.remove(p)  # crashed worker: take the item over
                except FileNotFoundError:
                    pass
                continue
            return False
        with os.fdopen(fd, "w") as f:
            json.dump({"pid": os.getpid(), "host": socket.gethostname(), "t": time.time()}, f)
        if is_done(out, v, t, k, s):  # finished between the check and the lock
            os.remove(p)
            return False
        return True
    return False


def release(out: str, item: tuple) -> None:
    try:
        os.remove(_lock(out, item_name(*item)))
    except FileNotFoundError:
        pass


def status(out: str, items) -> dict:
    done = sum(is_done(out, *it) for it in items)
    locked = sum(os.path.exists(_lock(out, item_name(*it))) and not is_done(out, *it) for it in items)
    return {"items": len(items), "done": done, "in_progress": locked, "todo": len(items) - done - locked}
