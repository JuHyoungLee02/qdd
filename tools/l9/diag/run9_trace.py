"""L9 v2 diagnosis: harvest.l9.run9 with a per-step truth trace (pod, Isaac). Same arguments as run9.
  python -m tools.l9.diag.run9_trace --plan P --job J --out O --v2 --p 0 --video-seeds ...
env DIAG_TRACE_DIR (default <out>/../trace): <dir>/<seed>.jsonl, one line every DIAG_TRACE_EVERY (default 2) control
steps: t, truth step label (rt.last_label), TCP position, measured pad gap, commanded width, the current target's
position + quaternion + tilt from upright (deg), its z speed, and the arm joints. env DIAG_VIDEO_EVERY (default 5 =
unchanged) sets the episode video frame interval (astra_solo.episode.VIDEO_EVERY).
Nothing else changes: the wrapper only reads state after each world.step."""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np


def tilt_deg(q) -> float:
    w, x, y, z = (float(v) for v in q)
    zz = 1 - 2 * (x * x + y * y)  # world z of the body z axis
    return math.degrees(math.acos(max(-1.0, min(1.0, zz))))


def main():
    from harvest.astra_solo import episode as E
    E.VIDEO_EVERY = int(os.environ.get("DIAG_VIDEO_EVERY", "5"))
    from harvest.l9 import rt9
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/data/harvest/l9v2/diag/trace_out"
    tdir = os.environ.get("DIAG_TRACE_DIR") or os.path.join(os.path.dirname(os.path.abspath(out)), "trace")
    os.makedirs(tdir, exist_ok=True)
    every = int(os.environ.get("DIAG_TRACE_EVERY", "2"))
    orig_install = rt9.install

    def install(world, *a, **k):
        rt = orig_install(world, *a, **k)
        step0, reset0 = world.step, world.reset
        st = {"n": 0, "f": None, "seed": None}

        def reset(seed, task=None):
            r = reset0(seed, task) if task is not None else reset0(seed)
            if st["f"]:
                st["f"].close()
            st["seed"], st["n"] = seed, 0
            st["f"] = open(os.path.join(tdir, f"{seed}.jsonl"), "w")
            return r

        def step(cmd_pos, width, quat=None):
            step0(cmd_pos, width, quat)
            st["n"] += 1
            if st["f"] is None or st["n"] % every:
                return
            try:
                env = world.env
                tg = (rt.choice_key or (None,))[0]
                stt = getattr(env, "sim_time", None)
                stt = stt() if callable(stt) else stt
                rec = {"i": st["n"], "t": round(float(stt), 3) if stt is not None else None,
                       "step": (rt.last_label or (None,))[0],
                       "tcp": np.round(np.asarray(world.pl.tcp_pose()[0], float), 4).tolist(),
                       "tq": np.round(np.asarray(world.pl.tcp_pose()[1], float), 4).tolist(),
                       "gap": round(float(env.gripper_width()), 4), "w_cmd": round(float(width), 4)}
                if tg is not None:
                    p, q = env.object_pose(tg)
                    rec.update(tgt=tg, p=np.round(np.asarray(p, float), 4).tolist(),
                               q=np.round(np.asarray(q, float), 4).tolist(), tilt=round(tilt_deg(q), 1))
                    try:
                        rec["vz"] = round(float(env.objects[tg].data.root_lin_vel_w[0, 2]), 3)
                    except Exception:  # noqa: BLE001
                        pass
                rec["q"] = np.round(rt.arm_q(), 3).tolist()
                st["f"].write(json.dumps(rec) + "\n")
            except Exception as e:  # noqa: BLE001
                st["f"].write(json.dumps({"i": st["n"], "err": f"{type(e).__name__}: {e}"}) + "\n")

        world.step = step
        world.reset = reset
        return rt

    rt9.install = install
    from harvest.l9 import run9
    run9.main()


if __name__ == "__main__":
    main()
