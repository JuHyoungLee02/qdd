"""E-LIB0 arms B (pi0.5 base) and R (pi0.5-LIBERO, reference) (docs/stage3/prereg_lib0.md §1): openpi's
examples/libero/main.py (Physical-Intelligence/openpi, Apache-2.0) episode loop unchanged -- the same env construction
(harvest.lib0.world.make_env / start_episode = openpi _get_libero_env + the 10 wait steps), the same preprocessing
(180 deg rotation, resize_with_pad 224, uint8), state = eef pos + axis-angle + gripper qpos, replan every 5 steps,
the suite's max_steps, success = done. Added only: the per-infer round-trip latency, the episode wall clock, and a
10 fps agentview | wrist video in the true camera orientation (from the 256 px observations).
One process = one (suite, task): the env is built once, episodes k in order (as main.py). Python 3.10 venv (venv_libero)."""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import time

import numpy as np

REPLAN = 5
RESIZE = 224


def quat2axisangle(quat):
    """openpi main.py _quat2axisangle (copied from robosuite transform_utils)."""
    quat = np.array(quat, float)
    if quat[3] > 1.0:
        quat[3] = 1.0
    elif quat[3] < -1.0:
        quat[3] = -1.0
    den = np.sqrt(1.0 - quat[3] * quat[3])
    if math.isclose(den, 0.0):
        return np.zeros(3)
    return (quat[:3] * 2.0 * math.acos(quat[3])) / den


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--task", type=int, required=True)
    ap.add_argument("--ks", default="0,1,2,3,4")
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--arm", required=True, help="B (pi05_base) | R (pi05_libero)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--stop-files", default="")
    a = ap.parse_args(argv)
    import imageio
    from openpi_client import image_tools
    from openpi_client import websocket_client_policy as wcp

    from ..teach_pt.run_closed_l8s import claim, yield_reason
    from .world import DUMMY, MAX_STEPS, WAIT_STEPS, make_env, start_episode, task_of
    stops = [f for f in a.stop_files.split(",") if f]
    task, bddl, inits, _ = task_of(a.suite, a.task)
    env = make_env(bddl)
    client = wcp.WebsocketClientPolicy(a.host, a.port)
    max_steps = MAX_STEPS[a.suite]
    print("WORLD " + json.dumps({"suite": a.suite, "task": a.task, "language": task.language, "arm": a.arm}), flush=True)
    code = 0
    for k in [int(x) for x in a.ks.split(",")]:
        why = yield_reason(stops)
        if why:
            print("YIELD " + why, flush=True)
            code = 3
            break
        name = f"t{a.task:02d}_k{k}"
        od = os.path.join(a.out, a.arm, a.suite, name)
        if not claim(od, f"pid={os.getpid()}"):
            continue
        t0 = time.perf_counter()
        obs, done = start_episode(env, inits[k])
        plan = collections.deque()
        lat, frames, err, steps = [], [], None, 0
        t = WAIT_STEPS
        try:
            while t < max_steps + WAIT_STEPS and not done:
                img = np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])
                wimg = np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1])
                if (t - WAIT_STEPS) % 2 == 0:  # video: true camera orientation (vertical flip only)
                    frames.append(np.concatenate([obs["agentview_image"][::-1], obs["robot0_eye_in_hand_image"][::-1]], 1))
                img = image_tools.convert_to_uint8(image_tools.resize_with_pad(img, RESIZE, RESIZE))
                wimg = image_tools.convert_to_uint8(image_tools.resize_with_pad(wimg, RESIZE, RESIZE))
                if not plan:
                    el = {"observation/image": img, "observation/wrist_image": wimg,
                          "observation/state": np.concatenate((obs["robot0_eef_pos"], quat2axisangle(obs["robot0_eef_quat"]),
                                                               obs["robot0_gripper_qpos"])),
                          "prompt": str(task.language)}
                    q0 = time.perf_counter()
                    chunk = client.infer(el)["actions"]
                    lat.append(round(time.perf_counter() - q0, 4))
                    assert len(chunk) >= REPLAN
                    plan.extend(chunk[:REPLAN])
                action = plan.popleft()
                obs, _r, done, _i = env.step(action.tolist())
                steps += 1
                if done:
                    break
                t += 1
        except Exception as ex:  # noqa: BLE001 -- openpi main.py: log and end the episode
            err = repr(ex)
            print("EP_EXC " + json.dumps({"k": k, "err": err}), flush=True)
        if err is not None and ("ConnectionClosed" in err or "Connection" in err):  # server gone: not a model failure
            os.rename(od, f"{od}.srv_err.{int(time.time())}")
            continue
        mp4 = os.path.join(a.vid_root, a.arm, a.suite, name + ".mp4")
        os.makedirs(os.path.dirname(mp4), exist_ok=True)
        try:
            imageio.mimwrite(mp4, frames, fps=10)
        except Exception:  # noqa: BLE001
            mp4 = None
        row = {"arm": a.arm, "suite": a.suite, "task": a.task, "k": k, "language": task.language,
               "success": bool(done), "steps": steps, "t_success": round(steps * 0.05, 2) if done else None,
               "end_reason": "success" if done else ("exception" if err else "max_steps"), "error": err,
               "n_infer": len(lat), "latency_s": lat, "wall_s": round(time.perf_counter() - t0, 1), "mp4": mp4,
               "n_frames": len(frames)}
        json.dump(row, open(os.path.join(od, "row.json"), "w"))
        json.dump(row, open(os.path.join(od, "result.json"), "w"))
        with open(os.path.join(a.vid_root, a.arm, "index.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")
        print("EP " + json.dumps({x: row[x] for x in ("suite", "task", "k", "success", "steps", "wall_s")}), flush=True)
    env.close()
    print("RUN_DONE", flush=True)
    os._exit(code)


if __name__ == "__main__":
    main()
