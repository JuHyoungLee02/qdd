"""Wall-time split of an L9 run (L9_TIMING=1; cProfile cannot see past the Kit app launch): physics sub-steps, rendering,
the cuRobo planner (IPC to its process), the episode writer, the rest. Wraps the callables in place; report() -> dict."""
from __future__ import annotations

import time

T: dict = {}


def _wrap(obj, name: str, key: str) -> None:
    f = getattr(obj, name, None)
    if f is None or getattr(f, "_timed", False):
        return

    def g(*a, **k):
        t0 = time.perf_counter()
        try:
            return f(*a, **k)
        finally:
            T[key] = T.get(key, 0.0) + time.perf_counter() - t0
            T[key + "_n"] = T.get(key + "_n", 0) + 1
    g._timed = True
    setattr(obj, name, g)


def install(world) -> None:
    env = world.env.env  # ManagerBasedRLEnv
    _wrap(env.sim, "step", "physics")
    _wrap(env.sim, "render", "render")
    _wrap(env, "step", "env_step")
    _wrap(world.env, "camera_rgb", "camera_read")
    _wrap(world.env, "camera_depth", "camera_read")
    rt = getattr(world, "rt", None)
    if rt is not None:
        _wrap(type(rt.planner), "_call", "curobo")
        for m in ("pose", "ik", "line", "world", "attach", "detach", "grasp"):
            _wrap(type(rt.planner), m, f"curobo_{m}")
    from ..astra_solo import pt_episode as PE
    _wrap(PE.PtEpisode if hasattr(PE, "PtEpisode") else PE, "_save_call", "write")
    T["t0"] = time.perf_counter()


def report() -> dict:
    out = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in T.items() if k != "t0"}
    out["wall"] = round(time.perf_counter() - T.get("t0", time.perf_counter()), 1)
    return out
