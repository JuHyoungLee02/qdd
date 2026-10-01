"""E-SIM0 arm B (docs/stage3/prereg_sim0.md §2): openpi pi05_base (no Google Robot training) through the openpi
websocket client, in the standard SimplerEnv evaluator loop (simpler_env.evaluation.maniskill2_evaluator: env, reset
options, max_episode_steps; the episode also stops at the first `success`, prereg §3).
Input (openpi pi05_libero format): image = overhead_camera RGB (openpi resize_with_pad 224), wrist = zeros, state = 8 zeros
(pi05 with discrete_state_input False does not read the state), prompt = the env instruction.
Output: replan every 5 of the 10-step chunk; each 7-d action (fractal / Octo convention, de-normalised by the server
with the Octo fractal statistics) -> env action exactly as SimplerEnv's Octo google_robot wrapper: world_vector x 1.0,
rotation_delta (roll, pitch, yaw) -> axis-angle, open_gripper (1 = open) -> relative gripper with the sticky repeat 15.
Video: the overhead RGB at 3 fps."""
from __future__ import annotations

import argparse
import collections
import json
import os
import time

import numpy as np

REPLAN, RESIZE, STICKY = 5, 224, 15


class GripperConv:
    """simpler_env/policies/octo/octo_model.py google_robot gripper (alternative implementation)."""

    def __init__(self):
        self.prev, self.on, self.rep, self.act = None, False, 0, 0.0

    def __call__(self, open_g: float) -> float:
        rel = 0.0 if self.prev is None else self.prev - open_g
        self.prev = open_g
        if abs(rel) > 0.5 and not self.on:
            self.on, self.act = True, rel
        if self.on:
            self.rep += 1
            rel = self.act
        if self.rep == STICKY:
            self.on, self.rep, self.act = False, 0, 0.0
        return float(rel)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--arm", default="B")
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--stop-files", default="")
    a = ap.parse_args(argv)
    import imageio
    from openpi_client import image_tools
    from openpi_client import websocket_client_policy as wcp
    from transforms3d.euler import euler2axangle

    from ..teach_pt.run_closed_l8s import claim, yield_reason
    from .world import ep_name, episodes, make_env
    want = set(a.eps.split(","))
    stops = [f for f in a.stop_files.split(",") if f]
    client = wcp.WebsocketClientPolicy(a.host, a.port)
    code = 0
    for e in [x for x in episodes() if ep_name(x) in want]:
        if yield_reason(stops):
            code = 3
            break
        name = ep_name(e)
        od = os.path.join(a.out, a.arm, name)
        if not claim(od, f"pid={os.getpid()}"):
            continue
        t0 = time.perf_counter()
        env, opts, max_steps = make_env(e)
        obs, _ = env.reset(options=opts)
        ins = env.get_language_instruction()
        plan, lat, frames, conv = collections.deque(), [], [], GripperConv()
        succ, steps, err = False, 0, None
        try:
            while steps < max_steps and not succ:
                img = np.ascontiguousarray(obs["image"]["overhead_camera"]["rgb"][..., :3]).astype(np.uint8)
                frames.append(img)
                if not plan:
                    el = {"observation/image": image_tools.convert_to_uint8(image_tools.resize_with_pad(img, RESIZE, RESIZE)),
                          "observation/wrist_image": np.zeros((RESIZE, RESIZE, 3), np.uint8),
                          "observation/state": np.zeros(8, np.float32), "prompt": ins}
                    q0 = time.perf_counter()
                    chunk = client.infer(el)["actions"]
                    lat.append(round(time.perf_counter() - q0, 4))
                    plan.extend(chunk[:REPLAN])
                r = np.asarray(plan.popleft(), float)
                ax, ang = euler2axangle(*r[3:6])
                act = np.concatenate([r[:3], np.asarray(ax) * ang, [conv(float(r[6]))]])
                obs, _rw, done, trunc, info = env.step(act)
                steps += 1
                succ = bool(info.get("success", done))
        except Exception as ex:  # noqa: BLE001
            err = repr(ex)
            print("EP_EXC " + json.dumps({"ep": name, "err": err}), flush=True)
        env.close()
        if err is not None and "Connection" in err:
            os.rename(od, f"{od}.srv_err.{int(time.time())}")
            continue
        mp4 = os.path.join(a.vid_root, a.arm, name + ".mp4")
        os.makedirs(os.path.dirname(mp4), exist_ok=True)
        try:
            imageio.mimwrite(mp4, frames, fps=3)
        except Exception:  # noqa: BLE001
            mp4 = None
        row = {"arm": a.arm, "ep": name, "task": e["task"], "instruction": ins, "success": succ, "steps": steps,
               "t_success": round(steps / 3.0, 2) if succ else None,
               "end_reason": "success" if succ else ("exception" if err else "max_steps"), "error": err,
               "n_infer": len(lat), "latency_s": lat, "wall_s": round(time.perf_counter() - t0, 1), "mp4": mp4}
        json.dump(row, open(os.path.join(od, "row.json"), "w"))
        json.dump(row, open(os.path.join(od, "result.json"), "w"))
        with open(os.path.join(a.vid_root, a.arm + "_index.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")
        print("EP " + json.dumps({x: row[x] for x in ("ep", "success", "steps", "wall_s")}), flush=True)
    print("RUN_DONE", flush=True)
    os._exit(code)


if __name__ == "__main__":
    main()
