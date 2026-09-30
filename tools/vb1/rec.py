"""E-VB1 re-collection with VLA frames (docs/stage3/prereg_vb1.md change 1; pod, Isaac).
One process = one group of tools/vb1/eps.py (one collect job): the world is rebuilt exactly as for E-M35CL
(harvest.teach_pt.run_closed_l8s.build_world), then every episode of the group is collected again with the same
collector call as the L8S production run (harvest.teach_l8d.collect.collect_episode; same seed, task, style, p,
max_perturb, call / motion limits). While the episode runs, every even 20 Hz control tick (10 Hz) records
  head RGB (half resolution) + right-wrist RGB, JPEG q90                    -> vla/head/NNNN.jpg, vla/wrist/NNNN.jpg
  state  = right-arm joints 7 (measured) + gripper width (measured) + lift + head 2      -> vla/vla.npz 'state'
  action = this tick's right-arm joint command 7 (_qcmd: before the gravity offset, after ARM_DQ / ARM_BAND)
           + the gripper width command                                                  -> vla/vla.npz 'action'
The decision-time call images of the collector (calls/) are deleted afterwards (not used, large).
rec.json = new result + the original episode's success / calls + scene reproduction (clutter ids, instruction).
Between episodes the process exits 3 when this card is wanted (L9 GPU_WANTED names it, or the lane's yield file).
python -m tools.vb1.rec --group g0001 --card 7a2a:1 --lane a [--yield-file F]"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import time

import numpy as np

EVERY = 2  # 20 Hz control ticks -> 10 Hz samples
ARM_NAMES = [f"arm_r_joint{k}" for k in range(1, 8)]
STATE_NAMES = ARM_NAMES + ["gripper_width", "lift_joint", "head_joint1", "head_joint2"]
ACTION_NAMES = ARM_NAMES + ["gripper_width"]


def _jpeg(a: np.ndarray, half: bool) -> bytes:
    from PIL import Image
    im = Image.fromarray(np.asarray(a)[..., :3])
    if half:
        im = im.resize((im.width // 2, im.height // 2), Image.BILINEAR)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=90)
    return b.getvalue()


class Rec:
    """Per-episode 10 Hz recorder hung on the world (world.step / world.reset wrappers)."""

    def __init__(self, world):
        self.w = world
        names = list(world.env.robot.joint_names)
        self.arm = [int(i) for i in world.env.arm_ids]
        got = [names[i] for i in self.arm]
        if got != ARM_NAMES:
            raise RuntimeError(f"arm ids are not the right arm joints 1-7: {got}")
        self.i_lift = names.index("lift_joint")
        self.i_head = [names.index("head_joint1"), names.index("head_joint2")]
        self.on = False
        self.clear()

    def clear(self):
        self.tick, self.S, self.A, self.T, self.head, self.wrist = 0, [], [], [], [], []

    def capture(self):
        env = self.w.env
        env.env.sim.render()
        for n in ("cam_head", "cam_wrist_right"):
            env.scene[n].update(0.0, force_recompute=True)
        q = env.robot.data.joint_pos[0].cpu().numpy()
        self.S.append(np.concatenate([q[self.arm], [env.gripper_width()], [q[self.i_lift]], q[self.i_head]])
                      .astype(np.float32))
        self.T.append(float(env.sim_time))
        self.head.append(_jpeg(env.camera_rgb("cam_head"), True))
        self.wrist.append(_jpeg(env.camera_rgb("cam_wrist_right"), False))

    def act(self, width: float):
        qc = np.asarray(self.w._qcmd, np.float32)
        self.A.append(np.concatenate([qc, [np.float32(width)]]))

    def save(self, od: str) -> int:
        n = min(len(self.S), len(self.A))
        vd = os.path.join(od, "vla")
        shutil.rmtree(vd, ignore_errors=True)
        for cam, frames in (("head", self.head), ("wrist", self.wrist)):
            os.makedirs(os.path.join(vd, cam))
            for k in range(n):
                with open(os.path.join(vd, cam, f"{k:04d}.jpg"), "wb") as f:
                    f.write(frames[k])
        np.savez_compressed(os.path.join(vd, "vla.npz"), state=np.asarray(self.S[:n]), action=np.asarray(self.A[:n]),
                            t=np.asarray(self.T[:n]), state_names=np.asarray(STATE_NAMES),
                            action_names=np.asarray(ACTION_NAMES), every=EVERY, dt=float(self.w.dt))
        return n


def install(world) -> Rec:
    rec = Rec(world)
    world._vb1 = rec
    orig_step, orig_reset = world.step, world.reset

    def step(cmd_pos, width, quat=None):
        if not rec.on:
            return orig_step(cmd_pos, width, quat)
        k = rec.tick
        rec.tick += 1
        if k % EVERY == 0:
            rec.capture()
        orig_step(cmd_pos, width, quat)
        if k % EVERY == 0:
            rec.act(width)

    def reset(*a, **kw):
        rec.on = False  # the arm pre-roll to ARM_START inside the reset is not recorded (= joints.npz)
        rec.clear()
        orig_reset(*a, **kw)
        rec.on = True

    world.step, world.reset = step, reset
    return rec


def claim(od: str, owner: str) -> bool:
    if any(os.path.exists(os.path.join(od, n)) for n in ("rec.json", "skip.json", "error.json")):
        return False
    os.makedirs(od, exist_ok=True)
    c = os.path.join(od, "claim")
    try:
        os.mkdir(c)
    except FileExistsError:
        if time.time() - os.path.getmtime(c) < 3600:
            return False
        try:
            os.rename(c, f"{c}.stale.{int(time.time())}")
            os.mkdir(c)
        except OSError:
            return False
    open(os.path.join(c, "owner"), "w").write(owner)
    for n in os.listdir(od):  # a killed earlier try leaves partial files
        if n != "claim" and not n.startswith("claim.stale"):
            p = os.path.join(od, n)
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True)
    ap.add_argument("--card", required=True, help="<pod>:<gpu>, e.g. 7a2a:1 or x2:1")
    ap.add_argument("--lane", required=True)
    ap.add_argument("--yield-file", default="")
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.teach_l8d.collect import collect_episode
        from harvest.teach_l8d.fx import SkipScene
        from harvest.teach_l8d.spec import check_seed
        from harvest.teach_pt.run_closed_l8s import build_world, job_args, repro_check
        from tools.vb1 import eps as E
        from tools.vb1.card import L9_WANTED, card_wanted
        job = next(g["job"] for g in E._groups() if g["id"] == a.group)
        eps = E._eps(a.group)
        j = job_args(job)
        for e in eps:
            check_seed(e["seed"], j.split, True)
        world = build_world(j)
        rec = install(world)
        print("WORLD " + json.dumps({"group": a.group, "furniture": j.furniture, "n": len(eps), "card": a.card}),
              flush=True)
        owner = f"{a.lane} {a.card} pid={os.getpid()}"
        for e in eps:
            why = (a.yield_file if a.yield_file and os.path.exists(a.yield_file) else None) or \
                (L9_WANTED if card_wanted(a.card) else None)
            if why:
                print("YIELD " + why, flush=True)
                code = 3
                break
            od = E.ep_out(e)
            if not claim(od, owner):
                continue
            t0 = time.perf_counter()
            try:
                meta = collect_episode(world, e["seed"], e["task"], j.variant, e["split"], od, e["p"],
                                       e["max_perturb"], a.stop_calls, a.stop_motion, e["style"])
            except SkipScene as ex:
                json.dump({"reason": str(ex)}, open(os.path.join(od, "skip.json"), "w"))
                print("SKIP " + json.dumps({"seed": e["seed"], "task": e["task"], "why": str(ex)}), flush=True)
                continue
            except Exception as ex:  # noqa: BLE001 -- one bad episode must not end the lane
                import traceback
                json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]},
                          open(os.path.join(od, "error.json"), "w"))
                print("EP_ERROR " + json.dumps({"seed": e["seed"], "task": e["task"], "err": repr(ex)}), flush=True)
                continue
            n = rec.save(od)
            rec.on = False
            shutil.rmtree(os.path.join(od, "calls"), ignore_errors=True)
            row = {"group": a.group, "seed": e["seed"], "task": e["task"], "vdir": e["vdir"], "sel": e["sel"],
                   "success": bool(meta.get("success")), "end_reason": meta.get("end_reason"),
                   "n_calls": meta.get("n_calls"), "sim_t": meta.get("sim_t"),
                   "orig_success": e["orig_success"], "orig_n_calls": e["orig_n_calls"],
                   "repro": repro_check(world, e["src"]), "n_frames": n, "max_dq_rad": meta.get("max_dq_rad"),
                   "wall_s": round(time.perf_counter() - t0, 1), "card": a.card, "src": e["src"]}
            json.dump(row, open(os.path.join(od, "rec.json"), "w"))
            print("EP " + json.dumps({k: row[k] for k in ("seed", "task", "success", "orig_success", "n_calls",
                                                          "n_frames", "wall_s")}), flush=True)
        else:
            print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)  # SimulationApp.close() hangs in this chroot (astra_solo.run)


if __name__ == "__main__":
    main()
