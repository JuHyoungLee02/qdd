"""E-RC0 arm A: the main 35B through the E-LIB0b episode class (E-CL15 path + Panda facts + gripper settle, no grasp
rule) on harvest.rc0.world.RcWorld. One process = one task: the env is built once (seed 7) and episodes k = 0..n-1 are
its successive resets (as the official loop). usage: run_a.py --task T --n 3 --qwen-url U --out O --vid-root V"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

BOX = ((0.15, 0.85), (-0.45, 0.45), (0.012, 0.40))  # base frame; prereg change 1 (Panda reach on the Omron base)


def block(world) -> str:
    from ..lib0.run_a import OBJ_HEAD, SUCCESS_LINE
    from ..lib0.world import obj_name
    ins = world.instruction.lower()
    lines = []
    for n in world.object_names():
        nm = obj_name(n)
        role = "task object" if any(w in ins for w in nm.lower().split() if len(w) > 3) else "obstacle"
        lines.append(f"- {nm} ({role})")
    return f"TASK: {world.instruction}\n{SUCCESS_LINE}\n{OBJ_HEAD}\n" + "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", default="lib0_ep2_5")
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--stop-files", default="")
    a = ap.parse_args(argv)
    from ..astra_motion import executor as EX
    EX.SAFE_X, EX.SAFE_Y, EX.SAFE_DZ = BOX
    from ..astra_solo import pt_episode as PE
    from ..astra_solo import resolve as RS
    from ..astra_solo.models import LocalVLM
    from ..lib0.run_a import LibMonitor, episode_class, make_mp4
    from ..teach_pt.run_closed_l8s import ErrCount, claim, yield_reason
    from .world import RcWorld, task_horizon
    RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
    PE.Monitor = LibMonitor
    stops = [f for f in a.stop_files.split(",") if f]
    world = RcWorld(a.task)
    model = ErrCount(LocalVLM(a.qwen_url, a.qwen_name, "q35_rc0"))
    Ep = episode_class()
    budget_s = task_horizon(a.task) * world.dt
    for k in range(a.n):
        if yield_reason(stops):
            break
        od = os.path.join(a.out, "A", a.task, f"k{k}")
        world.reset()  # the k-th reset of the seed-7 env, whether or not this episode is (re)claimed
        if not claim(od, f"pid={os.getpid()}"):
            continue
        vd = os.path.join(od, "frames10")
        os.makedirs(vd, exist_ok=True)
        t0 = time.perf_counter()
        model.errors = 0
        reset0 = world.reset
        world.reset = lambda *x, **y: None  # already reset for this episode
        try:
            ep = Ep(world, model, k, "robocasa", od, video=False, variant="robocasa", stop_calls=30, stop_motion_s=120.0,
                    mem_points=True, fix_loop=True, loop_break=True, stall_n=3, corrupt=None)
            ep.vid_dir, ep.fix_b, ep.fix_c = vd, True, False
            ep.block = block(world)
            res = ep.run()
        except Exception as ex:  # noqa: BLE001
            import traceback
            json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]}, open(os.path.join(od, "error.json"), "w"))
            print("EP_ERROR " + json.dumps({"k": k, "err": repr(ex)}), flush=True)
            world.reset = reset0
            continue
        world.reset = reset0
        if model.errors:
            os.rename(od, f"{od}.srv_err.{int(time.time())}")
            continue
        mp4 = os.path.join(a.vid_root, "A", a.task, f"k{k}.mp4")
        ok = make_mp4(vd, mp4)
        row = {"arm": "A", "task": a.task, "k": k, "instruction": world.instruction, "success": bool(res.get("success")),
               "t_success": res.get("t_success"), "success_in_budget": bool(res.get("success"))
               and res.get("t_success") is not None and float(res["t_success"]) <= budget_s + 1e-9,
               "end_reason": res.get("end_reason"), "fail_stage": res.get("fail_stage"), "n_calls": res.get("n_calls"),
               "latency_s": res.get("latency_s") or [], "wall_s": round(time.perf_counter() - t0, 1),
               "mp4": mp4 if ok else None, "result": os.path.join(od, "result.json")}
        json.dump(row, open(os.path.join(od, "row.json"), "w"))
        print("EP " + json.dumps({x: row[x] for x in ("task", "k", "success", "end_reason", "n_calls", "wall_s")}), flush=True)
    world.close()
    print("RUN_DONE", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
