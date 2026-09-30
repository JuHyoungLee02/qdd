"""E-VB1 closed loop: pi0.5 alone on L8S / OOD-O worlds (docs/stage3/prereg_vb1.md change 1; pod, Isaac).
One process = one group of tools/vb1/evalq.py (one collect job): the world is rebuilt as for E-M35CL
(run_closed_l8s.build_world), each episode is reset with the same seed / task (furniture, clutter, head pose, arm
pre-roll to ARM_START = the collector's reset), then the policy runs alone:
  every even 20 Hz tick (10 Hz): head (half resolution) + right-wrist JPEG q90 and the state 11 (= tools/vb1/rec.py);
  a new 50-step chunk every REPLAN samples (1 s); the odd tick takes the mean of this and the next chunk row;
  the joint command goes through the collector's limits (ARM_DQ per tick from the previous command, ARM_BAND around
  the measured joints) plus the gravity offset, the gripper width is clipped to [0, open width].
End: success (harness Monitor: on(target, place), released, upright for 1 s = E-M35CL), off_table, or 120 s of
simulated motion (= the collector's / E-M35CL's motion budget). Result = Monitor summary + end reason + counts.
Every episode writes a 10 fps head | right-wrist video (jpg frames kept + H.264 mp4) and one index line.
python -m tools.vb1.closed --group G --ckpt 20000 --server http://ip:port --card 7a2a:1 --lane a [--yield-file F]"""
from __future__ import annotations

import argparse
import io
import json
import os
import time
import urllib.request

import numpy as np

REPLAN = 10
EVERY = 2
MOTION_S = 120.0
ROOT = "/data/harvest/out/vb1/eval"
VID = "/data/harvest/videos/vb1"


def ask(url: str, head: bytes, wrist: bytes, state, task: str, timeout: float = 120.0) -> np.ndarray:
    b = io.BytesIO()
    np.savez(b, head=np.frombuffer(head, np.uint8), wrist=np.frombuffer(wrist, np.uint8),
             state=np.asarray(state, np.float32), task=np.array(task))
    req = urllib.request.Request(url.rstrip("/") + "/act", data=b.getvalue(),
                                 headers={"Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        z = np.load(io.BytesIO(r.read()))
        return np.asarray(z["action"], np.float32)


def run_episode(world, rec, url: str, seed: int, task: str, vid_dir: str) -> dict:
    from PIL import Image

    from harvest.astra_motion.harness import Monitor
    from harvest.teach_l8d.clutter_x import ARM_BAND, ARM_DQ
    world.reset(seed, task)
    rec.on = False  # the recorder hooks stay off: this loop drives env.step itself
    info = world.task_info()
    mon = Monitor(world, info)
    t0 = float(world.status()["t"])
    env, arm = world.env, rec.arm
    if getattr(world, "_qcmd", None) is None:
        world._qcmd = env.robot.data.joint_pos[0, arm].cpu().numpy().copy()
    chunk, ci, nq, tick, nv, jumps, end = None, 0, 0, 0, 0, 0, None
    a_now = a_next = None
    q_prev = env.robot.data.joint_pos[0, arm].cpu().numpy().copy()
    t_wall = time.perf_counter()
    while True:
        st = world.status()
        mon.update(st)
        if mon.success:
            end = "success"
        elif mon.off_table:
            end = "off_table"
        elif float(st["t"]) - t0 >= MOTION_S:
            end = "motion_limit"
        if end:
            break
        if tick % EVERY == 0:
            rec.clear()
            rec.capture()
            head, wrist, state = rec.head[0], rec.wrist[0], rec.S[0]
            h = np.asarray(Image.open(io.BytesIO(head)))
            w = np.asarray(Image.open(io.BytesIO(wrist)).resize((int(424 * h.shape[0] / 240), h.shape[0])))
            Image.fromarray(np.concatenate([h, w], 1)).save(os.path.join(vid_dir, f"f{nv:05d}.jpg"), quality=85)
            nv += 1
            if chunk is None or ci >= REPLAN:
                chunk, ci = ask(url, head, wrist, state, info["instruction"]), 0
                nq += 1
            a_now, a_next = chunk[ci], chunk[min(ci + 1, len(chunk) - 1)]
            ci += 1
            a = a_now
        else:
            a = 0.5 * (a_now + a_next)
        g = world.pl._gravity_offset()[0].cpu().numpy()
        qm = env.robot.data.joint_pos[0, arm].cpu().numpy()
        world._qcmd = world._qcmd + np.clip(a[:7] - world._qcmd, -ARM_DQ, ARM_DQ)
        world._qcmd = np.clip(world._qcmd, qm - ARM_BAND, qm + ARM_BAND)
        width = float(np.clip(a[7], 0.0, world.w_open))
        env.step(np.concatenate([world._qcmd + g, [width]]).astype(np.float32))
        world._st = None
        q = env.robot.data.joint_pos[0, arm].cpu().numpy()
        jumps += int(np.abs(q - q_prev).max() > 0.04)
        q_prev = q
        tick += 1
    return {**mon.summary(), "end_reason": end, "sim_t": round(float(world.status()["t"]) - t0, 2),
            "n_queries": nq, "n_ticks": tick, "n_frames": nv, "joint_jump_ticks": jumps,
            "wall_s": round(time.perf_counter() - t_wall, 1), "instruction": info["instruction"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--server", required=True)
    ap.add_argument("--card", required=True)
    ap.add_argument("--lane", required=True)
    ap.add_argument("--yield-file", default="")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.harness import _jsonable
        from harvest.teach_l8d.fx import SkipScene
        from harvest.teach_pt.run_closed_l8s import build_world, claim, job_args, make_mp4, repro_check
        from tools.vb1 import evalq as Q
        from tools.vb1.card import L9_WANTED, card_wanted
        from tools.vb1.rec import install
        g = Q.group(a.group)
        j = job_args(g["job"])
        world = build_world(j)
        rec = install(world)
        print("WORLD " + json.dumps({"group": a.group, "set": g["set"], "n": len(g["eps"]), "ckpt": a.ckpt}),
              flush=True)
        owner = f"{a.lane} {a.card} pid={os.getpid()}"
        for e in g["eps"]:
            why = (a.yield_file if a.yield_file and os.path.exists(a.yield_file) else None) or \
                (L9_WANTED if card_wanted(a.card) else None)
            if why:
                print("YIELD " + why, flush=True)
                code = 3
                break
            if Q.served_ckpt() != a.ckpt:
                print("CKPT_CHANGED", flush=True)
                break
            name = f"{e['task']}_s{e['seed']}"
            od = Q.ep_dir(a.ckpt, g["set"], name)
            if not claim(od, owner):
                continue
            vd = os.path.join(od, "frames10")
            os.makedirs(vd, exist_ok=True)
            try:
                res = run_episode(world, rec, a.server, e["seed"], e["task"], vd)
            except SkipScene as ex:
                json.dump({"reason": str(ex)}, open(os.path.join(od, "skip.json"), "w"))
                continue
            except (OSError, ConnectionError) as ex:  # server gone (switch / restart): not a policy failure
                os.rename(od, f"{od}.srv_err.{int(time.time())}")
                print("EP_SRV_ERR " + json.dumps({"seed": e["seed"], "err": repr(ex)}), flush=True)
                break
            except Exception as ex:  # noqa: BLE001
                import traceback
                json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]},
                          open(os.path.join(od, "error.json"), "w"))
                print("EP_ERROR " + json.dumps({"seed": e["seed"], "task": e["task"], "err": repr(ex)}), flush=True)
                continue
            mp4 = os.path.join(VID, a.ckpt, g["set"], name + ".mp4")
            ok = make_mp4(vd, mp4)
            row = {"ckpt": a.ckpt, "set": g["set"], "seed": e["seed"], "task": e["task"],
                   "truth_success": e.get("truth_success"), "success": bool(res.get("success")),
                   "end_reason": res["end_reason"], "fail_stage": res.get("fail_stage"), "sim_t": res["sim_t"],
                   "n_queries": res["n_queries"], "joint_jump_ticks": res["joint_jump_ticks"],
                   "repro": repro_check(world, e["dir"]), "mp4": mp4 if ok else None, "frames": vd,
                   "wall_s": res["wall_s"], "src": e["dir"]}
            json.dump(res, open(os.path.join(od, "result.json"), "w"), default=_jsonable)
            json.dump(row, open(os.path.join(od, "cl.json"), "w"))
            os.makedirs(VID, exist_ok=True)
            with open(os.path.join(VID, "index.jsonl"), "a") as f:
                f.write(json.dumps(row) + "\n")
            print("EP " + json.dumps({k: row[k] for k in ("set", "seed", "task", "success", "end_reason", "sim_t",
                                                          "wall_s")}), flush=True)
        else:
            print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
