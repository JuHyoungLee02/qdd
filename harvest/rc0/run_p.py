"""E-RC0 arm P: the official pi0.5 RoboCasa365 checkpoint through robocasa-benchmark/openpi examples/robocasa/main.py's
eval_env loop (Apache-2.0) unchanged: env robocasa/<task> split target seed 7, horizon = task horizon x 1.5, images
agentview_left / eye_in_hand / agentview_right resize_with_pad 224, state = eef pos rel + eef rot rel + base pos + base
rot + gripper qpos, replan 5, convert_action, success = info["success"] (stop at it). Added: per-infer latency, wall
clock, a 10 fps agentview_left | eye_in_hand video, n trials instead of 50.
usage: run_p.py --task T --n 3 --host H --port P --out O --vid-root V"""
from __future__ import annotations

import argparse
import collections
import json
import os
import time

import numpy as np


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    a = ap.parse_args(argv)
    import imageio
    from openpi_client import image_tools
    from openpi_client import websocket_client_policy as wcp
    from robocasa.utils.env_utils import convert_action

    from ..teach_pt.run_closed_l8s import claim
    from .world import make_env, task_horizon
    env = make_env(a.task)
    client = wcp.WebsocketClientPolicy(a.host, a.port)
    horizon = task_horizon(a.task)
    for k in range(a.n):
        od = os.path.join(a.out, "P", a.task, f"k{k}")
        obs, info = env.reset()
        if not claim(od, f"pid={os.getpid()}"):
            continue
        t0 = time.perf_counter()
        lang = obs["annotation.human.task_description"]
        plan, lat, frames, t, done, err = collections.deque(), [], [], 0, False, None
        rp = lambda x: image_tools.convert_to_uint8(image_tools.resize_with_pad(np.ascontiguousarray(x), 224, 224))  # noqa: E731
        try:
            while t < horizon:
                if t % 2 == 0:
                    frames.append(np.concatenate([obs["video.robot0_agentview_left"], obs["video.robot0_eye_in_hand"]], 1))
                if not plan:
                    state = np.concatenate((obs["state.end_effector_position_relative"],
                                            obs["state.end_effector_rotation_relative"], obs["state.base_position"],
                                            obs["state.base_rotation"], obs["state.gripper_qpos"]), axis=0)
                    q0 = time.perf_counter()
                    chunk = client.infer({"observation/image": rp(obs["video.robot0_agentview_left"]),
                                          "observation/wrist_image": rp(obs["video.robot0_eye_in_hand"]),
                                          "observation/right_image": rp(obs["video.robot0_agentview_right"]),
                                          "observation/state": state, "prompt": lang})["actions"]
                    lat.append(round(time.perf_counter() - q0, 4))
                    plan.extend(chunk[:5])
                obs, _r, _d, _tr, info = env.step(convert_action(np.asarray(plan.popleft())))
                t += 1
                if info["success"]:
                    done = True
                    break
        except Exception as ex:  # noqa: BLE001
            err = repr(ex)
            print("EP_EXC " + json.dumps({"k": k, "err": err}), flush=True)
        mp4 = os.path.join(a.vid_root, "P", a.task, f"k{k}.mp4")
        os.makedirs(os.path.dirname(mp4), exist_ok=True)
        try:
            imageio.mimwrite(mp4, frames, fps=10)
        except Exception:  # noqa: BLE001
            mp4 = None
        row = {"arm": "P", "task": a.task, "k": k, "instruction": lang, "success": done, "steps": t,
               "end_reason": "success" if done else ("exception" if err else "horizon"), "error": err,
               "latency_s": lat, "n_infer": len(lat), "wall_s": round(time.perf_counter() - t0, 1), "mp4": mp4}
        json.dump(row, open(os.path.join(od, "row.json"), "w"))
        print("EP " + json.dumps({x: row[x] for x in ("task", "k", "success", "steps", "wall_s")}), flush=True)
    env.close()
    print("RUN_DONE", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
