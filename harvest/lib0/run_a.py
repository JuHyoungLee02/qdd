"""E-LIB0 arm A (docs/stage3/prereg_lib0.md §2): the main 35B (no LIBERO training) driving a LIBERO Franka through the
E-CL15 episode class (with_loop_break(LimitEpisode): d-min request, mem_points, fix_loop LoopGuard, loop break
stall_n 3, 30 calls / 120 s motion) on harvest.lib0.world.LiberoWorld.

LIBERO-specific pieces only (everything else is the E-CL15 code path, unchanged):
  * the workspace box (code-filled prompt slot + executor clip) = BOX_X / BOX_Y, patched into astra_motion.executor
    BEFORE the prompt modules are imported (they copy SAFE_X / SAFE_Y at import)
  * resolve.robot_mask (the L8S 10.5 cm height rule) -> off: the world removes the robot's own pixels from the depth by
    segmentation
  * the Monitor -> LibMonitor (success = LIBERO done; holding = robot self-measurement)
  * the TASK / Success / OBJECTS block of the request -> the LIBERO task (lib_block); every other line as trained
  * no object truth in _truth / _score (LIBERO objects are not L8S ids); video = agentview | wrist at 10 fps
One process = one (suite, task): the env is built once and episodes k run in order (as openpi main.py)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

import numpy as np

BOX_X, BOX_Y = (0.15, 0.85), (-0.40, 0.40)  # prereg change 1 (fixed before any model run: tools/lib0/box.py, 40 tasks)
VID_EVERY = 2  # 20 Hz control -> 10 fps
SUCCESS_LINE = "Success = what the TASK sentence asks is done (the simulator checks it). Then answer stop."
OBJ_HEAD = "OBJECTS (other objects on the table are obstacles, do not touch them)"


# E-LIB0b (prereg_lib0.md change 2): adapter only, no training. Franka facts (tools/lib0/franka_geom.py, franka_mesh.py):
# fingers close along base y; pads 1.7 cm (+1.2 / -0.5 cm about the TCP = grip_site); fingertips 1.0 cm below the TCP;
# hand body from 3.0 cm above the TCP. z floor = fingertip + the trained clearance (AI Worker: 2.5 - 2.25 = 0.25 cm).
DZ_B = (0.012, 0.40)
TEXT_B = (
    ("You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) at a table, in simulation.",
     "You control a robot arm (Franka Emika Panda) at a table, in simulation."),
    ("its two fingers close along the robot x axis. TCP = the point midway between the finger pads. The pads are 4.5 cm "
     "long (from 2.25 cm above to 2.25 cm below the TCP); the gripper body starts 2.5 cm above the TCP.",
     "its two fingers close along the robot y axis. TCP = the point midway between the finger pads. The pads are 1.7 cm "
     "long (from 1.2 cm above to 0.5 cm below the TCP); the fingertips end 1.0 cm below the TCP; the gripper body starts "
     "3.0 cm above the TCP."),
    ("then apply gripper: close (0.6 s), open (0.5 s) or keep.",
     "then apply gripper: close or open (the code waits until the fingers stop moving, at most 10 s) or keep."),
)
GRIP_MAX_S = 10.0  # change 2 (2b): the robosuite Panda gripper ramps its target 0.01 per step -> wait until it settles
GRIP_STILL_M, GRIP_STILL_TICKS = 3e-4, 5


def settle_exec(base, world):
    """MinJerkExec whose open / close waits (trained 0.5 / 0.6 s) last until the pad gap stops changing (< 0.3 mm per
    tick for 5 ticks), at least the trained time, at most GRIP_MAX_S (E-LIB0b change 2b)."""

    class SettleGrip(base):
        def _act(self, action, t, tcp):
            self._w0, self._gl, self._still = t, None, 0
            return super()._act(action, t, tcp)

        def tick(self, t, tcp):
            if self.wait_until is not None:
                g = world._gap()
                self._still = self._still + 1 if (self._gl is not None and abs(g - self._gl) < GRIP_STILL_M) else 0
                self._gl = g
                if t >= self.wait_until - 1e-9 and self._still < GRIP_STILL_TICKS and t < self._w0 + GRIP_MAX_S:
                    return self.cmd.copy(), self.width, []
            return super().tick(t, tcp)
    return SettleGrip


def patch_box(fix_b: bool = False):
    from ..astra_motion import executor as EX
    EX.SAFE_X, EX.SAFE_Y = BOX_X, BOX_Y
    if fix_b:
        EX.SAFE_DZ = DZ_B


def text_b(text: str) -> str:
    for old, new in TEXT_B:
        if text.count(old) != 1:
            raise ValueError(f"E-LIB0b: fixed sentence not found once: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def lib_block(world) -> str:
    """TASK / Success / OBJECTS lines of the request for this LIBERO task (objects of interest = 'task object',
    the other objects and fixtures = 'obstacle'; names from the BDDL without index / underscores)."""
    from .world import obj_name
    ooi = world.objects_of_interest()
    rest = [n for n in world.object_names() if n not in ooi]
    lines = [f"- {obj_name(n)} (task object)" for n in ooi] + [f"- {obj_name(n)} (obstacle)" for n in rest]
    return f"TASK: {world.task.language}\n{SUCCESS_LINE}\n{OBJ_HEAD}\n" + "\n".join(lines) + "\n"


def swap_block(text: str, block: str) -> str:
    a, b = text.index("TASK: "), text.index("\nNOW\n")
    return text[:a] + block + text[b:]


class LibMonitor:
    """The harness Monitor's interface for a LIBERO world: success = the env's done (LIBERO _check_success at any
    control step, as openpi); holding / closes from the robot's own measurement; off_table from the sim (monitor only)."""

    def __init__(self, world, info):
        self.w = world
        self.success = self.off_table = self.ever_hold = False
        self.closes, self.path = [], []
        self.ooi = world.objects_of_interest()
        self.n = 0

    def update(self, st):
        self.n += 1
        if self.w.done:
            self.success = True
        self.ever_hold |= self.w.holding()
        self.path.append([round(float(st["t"]), 3)] + [round(float(v), 5) for v in st["tcp"]])
        if self.n % 10 == 0:
            for k in self.ooi:
                p = self.w.obj_pos(k)
                if p is not None and p[2] < self.w.table_z - 0.05:
                    self.off_table = True

    def on_close(self, t, tcp):
        self.closes.append({"t": round(float(t), 3), "tcp": np.round(np.asarray(tcp, float), 4).tolist()})

    def summary(self) -> dict:
        stage = None if self.success else ("approach" if not self.closes else
                                           ("grasp" if not self.ever_hold else "after_grasp"))
        return {"success": self.success, "ever_hold": self.ever_hold, "fail_stage": stage, "n_close": len(self.closes),
                "first_close": self.closes[0] if self.closes else None, "off_table": self.off_table,
                "tcp_path": self.path[::5]}


def episode_class():
    from PIL import Image

    from ..teach_strip8.boost import LimitEpisode
    from ..teach_strip8.stall import with_loop_break

    class LibEpisode(with_loop_break(LimitEpisode)):
        vid_dir = None
        block = None
        fix_b = False
        fix_c = False  # E-LIB0c (prereg change 3): rim grasp for hollow objects (harvest.lib0.rim)

        def resolve(self, cmd: dict, st: dict) -> dict:
            res = super().resolve(cmd, st)
            if not (self.fix_c and cmd.get("height") == "grasp" and res.get("kind") == "object"
                    and res.get("goal") is not None and cmd.get("point_2d") is not None and self.depth is not None):
                return res
            from .rim import region_points, rim_of
            P, _plane, _r = region_points(self.head, self.depth, self.w.table_z, cmd["point_2d"], tcp=st["tcp"])
            v = rim_of(P, st["tcp"])
            self.rim_log = getattr(self, "rim_log", []) + [dict(v, call=len(self.calls))]
            if not v["hollow"]:
                return res
            return dict(res, goal=[float(v["xy"][0]), float(v["xy"][1]), float(v["z"])], goal_centre=res["goal"],
                        rim=True)

        def _save(self, res):
            res["rim"] = getattr(self, "rim_log", [])
            super()._save(res)

        def _truth(self) -> dict:
            st = self.w.status()
            return {"tgt_xyz": None, "place_xyz": None, "holding": self.w.holding(),
                    "tcp": np.round(np.asarray(st["tcp"], float), 4).tolist(), "grip_w": round(float(st["grip_w"]), 4)}

        def _score(self, cmd, truth, phase):
            return None

        def make_exec(self, st):
            ex = super().make_exec(st)
            if self.fix_b:
                ex.__class__ = settle_exec(type(ex), self.w)
            return ex

        def _request(self, obs, i, statics):
            text, ims = super()._request(obs, i, statics)
            text = swap_block(text, self.block)
            return (text_b(text) if self.fix_b else text), ims

        def _tick(self):
            super()._tick()
            if not self.vid_dir:
                return
            self._v = getattr(self, "_v", -1) + 1
            if self._v % VID_EVERY:
                return
            fr = self.w.frame()
            n = getattr(self, "_nv", 0)
            Image.fromarray(np.concatenate([fr["head"], fr["wrist"]], 1)).save(
                os.path.join(self.vid_dir, f"f{n:05d}.jpg"), quality=85)
            self._nv = n + 1
    return LibEpisode


def make_mp4(frames_dir: str, out: str) -> bool:
    import imageio_ffmpeg
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", "10", "-i",
                        os.path.join(frames_dir, "f%05d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p", out],
                       capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--task", type=int, required=True)
    ap.add_argument("--ks", default="0,1,2,3,4", help="standard init-state indices")
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--arm", default="A")
    ap.add_argument("--stop-files", default="")
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    ap.add_argument("--fix-b", action="store_true", help="E-LIB0b adapter fixes (prereg change 2)")
    ap.add_argument("--fix-c", action="store_true", help="E-LIB0c: + rim grasp for hollow objects (change 3)")
    a = ap.parse_args(argv)
    a.fix_b = a.fix_b or a.fix_c
    patch_box(a.fix_b)
    from ..astra_solo import pt_episode as PE
    from ..astra_solo import resolve as RS
    from ..astra_solo.models import LocalVLM
    from ..teach_pt.run_closed_l8s import ErrCount, claim, yield_reason
    from .world import GAP_SCALE_B, MAX_STEPS, W_CLOSE_B, LiberoWorld
    RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
    PE.Monitor = LibMonitor
    code = 0
    stops = [f for f in a.stop_files.split(",") if f]
    world = LiberoWorld(a.suite, a.task)
    if a.fix_b:
        world.gap_scale, world.w_close = GAP_SCALE_B, W_CLOSE_B * GAP_SCALE_B
    print("WORLD " + json.dumps({"suite": a.suite, "task": a.task, "language": world.task.language,
                                 "ooi": world.objects_of_interest()}), flush=True)
    model = ErrCount(LocalVLM(a.qwen_url, a.qwen_name, "q35_lib0"))
    Ep = episode_class()
    budget_s = MAX_STEPS[a.suite] * world.dt
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
        vd = os.path.join(od, "frames10")
        os.makedirs(vd, exist_ok=True)
        t0 = time.perf_counter()
        model.errors = 0
        try:
            ep = Ep(world, model, k, "libero", od, video=False, variant="libero", stop_calls=a.stop_calls,
                    stop_motion_s=a.stop_motion, mem_points=True, fix_loop=True, loop_break=True, stall_n=3,
                    corrupt=None)
            ep.vid_dir = vd
            ep.fix_b, ep.fix_c = a.fix_b, a.fix_c
            world.table_z = None  # re-measured at this episode's reset
            ep.block = lib_block(world)
            res = ep.run()
        except Exception as ex:  # noqa: BLE001 -- one bad episode must not end the lane
            import traceback
            json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]}, open(os.path.join(od, "error.json"), "w"))
            print("EP_ERROR " + json.dumps({"k": k, "err": repr(ex)}), flush=True)
            continue
        if model.errors:
            os.rename(od, f"{od}.srv_err.{int(time.time())}")
            print("EP_SRV_ERR " + json.dumps({"k": k, "n": model.errors}), flush=True)
            continue
        mp4 = os.path.join(a.vid_root, a.arm, a.suite, name + ".mp4")
        ok = make_mp4(vd, mp4)
        lat = res.get("latency_s") or []
        row = {"arm": a.arm, "fix_b": a.fix_b, "fix_c": a.fix_c, "suite": a.suite, "task": a.task, "k": k, "language": world.task.language,
               "success": bool(res.get("success")), "t_success": res.get("t_success"),
               "success_in_budget": bool(res.get("success")) and res.get("t_success") is not None
               and float(res["t_success"]) <= budget_s + 1e-9, "budget_s": budget_s,
               "end_reason": res.get("end_reason"), "fail_stage": res.get("fail_stage"), "n_calls": res.get("n_calls"),
               "n_invalid": res.get("n_invalid"), "latency_s": lat, "sim_t": res.get("sim_t"),
               "wall_s": round(time.perf_counter() - t0, 1), "table_z": world.table_z, "mp4": mp4 if ok else None,
               "n_frames": getattr(ep, "_nv", 0), "result": os.path.join(od, "result.json")}
        json.dump(row, open(os.path.join(od, "row.json"), "w"))
        with open(os.path.join(a.vid_root, a.arm, "index.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")
        print("EP " + json.dumps({x: row[x] for x in ("suite", "task", "k", "success", "end_reason", "n_calls",
                                                      "wall_s")}), flush=True)
    world.close()
    print("RUN_DONE", flush=True)
    os._exit(code)


if __name__ == "__main__":
    main()
