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
            st["seed"], st["n"], st["geom"] = seed, 0, set()
            st["f"] = open(os.path.join(tdir, f"{seed}.jsonl"), "w", buffering=1)
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
                plk = (rt.choice_key or (None, None))[1] if rt.choice_key and len(rt.choice_key) > 1 else None
                if plk is not None:  # objects and spot markers (marker pose = its layout pose on the surface)
                    pp, pq = env.object_pose(plk)
                    rec.update(pl=plk, pp=np.round(np.asarray(pp, float), 4).tolist(),
                               pq=np.round(np.asarray(pq, float), 4).tolist())
                if tg is not None and st.setdefault("geom", set()).isdisjoint({tg, plk}) is not None:
                    from harvest.sim.scene import OBJ_GEOM
                    for k_ in (tg, plk):
                        if k_ is not None and k_ not in st["geom"] and "half_extents" in OBJ_GEOM.get(k_, {}):
                            st["geom"].add(k_)
                            st["f"].write(json.dumps({"geom": k_, "he": list(OBJ_GEOM[k_]["half_extents"])}) + "\n")
                if tg is not None:
                    p, q = env.object_pose(tg)
                    rec.update(tgt=tg, p=np.round(np.asarray(p, float), 4).tolist(),
                               oq=np.round(np.asarray(q, float), 4).tolist(), tilt=round(tilt_deg(q), 1))
                    try:
                        rec["vz"] = round(float(env.objects[tg].data.root_lin_vel_w[0, 2]), 3)
                    except Exception:  # noqa: BLE001
                        pass
                rec["q"] = np.round(rt.arm_q(), 3).tolist()
                try:  # finger bodies (the pad pair the gap is read from) and all finger-like joints
                    a_, b_ = getattr(env, "pad_pair", (0, 1))
                    bp = env.robot.data.body_pos_w[0]
                    rec["fa"] = np.round(bp[env.finger_idx[a_]].cpu().numpy(), 4).tolist()
                    rec["fb"] = np.round(bp[env.finger_idx[b_]].cpu().numpy(), 4).tolist()
                    jn = env.robot.joint_names
                    jp = env.robot.data.joint_pos[0].cpu().numpy()
                    rec["fq"] = {n: round(float(jp[i]), 4) for i, n in enumerate(jn) if "finger" in n or "gripper" in n}
                except Exception:  # noqa: BLE001
                    pass
                st["f"].write(json.dumps(rec) + "\n")
            except Exception as e:  # noqa: BLE001
                st["f"].write(json.dumps({"i": st["n"], "err": f"{type(e).__name__}: {e}"}) + "\n")

        world.step = step
        world.reset = reset
        # failed-motion dumps (DIAG_DUMP_MOTION=1): the last world scene / attach sent to the planner, the start joints
        # and the goal of every motion_for that returned no trajectory (carry, put, retreat ...) ->
        # <trace dir>/motion_<seed>_<k>.json, replay with tools/l9/diag/motion_repro.py
        if os.environ.get("DIAG_DUMP_MOTION", "1") == "1":
            pl = rt.planner
            w0, a0, mf0 = pl.world, pl.attach, rt.motion_for
            mem = {"tries": [], "k": 0}

            def world_(scene):
                mem["tries"].append({"scene": scene, "attach": None})
                return w0(scene)

            def attach_(q, names):
                if mem["tries"]:
                    mem["tries"][-1]["attach"] = {"q": np.asarray(q, float).tolist(), "names": list(names)}
                return a0(q, names)

            def motion_for(pos, grip):
                q0 = rt.plan_start()
                mem["tries"], mem["calls"] = [], []
                out = mf0(pos, grip)
                if out[0] is None and mem["k"] < 40:
                    mem["k"] += 1
                    try:
                        lab = rt.last_label
                        cmd = lab[1] if lab else None
                        quat = (cmd or {}).get("quat_wxyz") or np.asarray(world.pl.tcp_pose()[1], float).tolist()
                        from harvest.l9.rt9 import T_of
                        T = T_of(pos, quat)
                        tg = (rt.choice_key or (None,))[0]
                        json.dump({"what": "motion", "step": lab[0] if lab else None, "note": out[1],
                                   "seed": st["seed"], "q": np.asarray(q0, float).tolist(), "joints": rt.joints,
                                   "T_world_base": rt.T_world_base().tolist(), "tcp_T": T.tolist(),
                                   "tcp_now": rt.tcp_T().tolist(), "tries": mem["tries"], "calls": mem.get("calls", []),
                                   "gc": None if rt.choice is None else {"T": np.asarray(rt.choice.T).tolist(),
                                                                         "pre": np.asarray(rt.choice.pre).tolist(),
                                                                         "family": rt.choice.family},
                                   "tgt": tg, "tgt_pose": [np.asarray(v, float).tolist() for v in
                                                           world.env.object_pose(tg)] if tg else None,
                                   "goal_is_tcp_T": True},
                                  open(os.path.join(tdir, f"motion_{st['seed']}_{mem['k']}.json"), "w"))
                    except Exception as e:  # noqa: BLE001
                        print("DIAG dump error", type(e).__name__, e, flush=True)
                return out

            def wrap(name):
                f0 = getattr(pl, name)

                def f(*args, **kw):
                    out = f0(*args, **kw)
                    try:
                        mem.setdefault("calls", []).append({
                            "fn": name, "world_idx": len(mem["tries"]) - 1, "ok": out is not None,
                            "args": [np.asarray(x, float).tolist() if hasattr(x, "__len__") else x for x in args],
                            "kw": {k: (np.asarray(v, float).tolist() if hasattr(v, "__len__") else v) for k, v in kw.items()}})
                    except Exception:  # noqa: BLE001
                        pass
                    return out
                return f

            pl.line, pl.pose = wrap("line"), wrap("pose")
            pl.world, pl.attach, rt.motion_for = world_, attach_, motion_for
        return rt

    rt9.install = install
    from harvest.l9 import run9
    run9.main()


if __name__ == "__main__":
    main()
