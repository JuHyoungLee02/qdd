"""E-SIM0 arm A (docs/stage3/prereg_sim0.md §2): the main 35B through the E-LIB0c episode class (E-CL15 executor path:
d-min request, mem_points, LoopGuard, loop break, 30 calls / 120 s, rim grasp for hollow objects, gripper settles) on
harvest.sim0.world.SimWorld, with the Google Robot facts in the fixed prompt sentences (prereg change 1) and the
no-wrist note. Also the G0 scripted check (--g0: sim truth for the can position, prereg §5; no model).
One process = a list of episodes (each builds its own env: the standard evaluator does the same)."""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

BOX_X, BOX_Y, DZ = (0.35, 0.90), (-0.45, 0.45), (0.005, 0.40)  # prereg change 1 (tools/sim0/robot_geom.py, scenes)
TEXT_G = (
    ("- It points straight down; its two fingers", "- It points almost straight down (tilted about 20 degrees); its two fingers"),
    ("You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) at a table, in simulation.",
     "You control a robot arm (Google Robot) at a table, in simulation."),
    ("its two fingers close along the robot x axis. TCP = the point midway between the finger pads. The pads are 4.5 cm "
     "long (from 2.25 cm above to 2.25 cm below the TCP); the gripper body starts 2.5 cm above the TCP.",
     "its two fingers close along the robot x axis. TCP = the point where the two fingertips meet when closed. The "
     "fingers are about 11 cm long and swing in from above as they close; the lowest finger point is at the TCP; the "
     "gripper body starts 15 cm above the TCP."),
    ("then apply gripper: close (0.6 s), open (0.5 s) or keep.",
     "then apply gripper: close or open (the code waits until the fingers stop moving, at most 10 s) or keep."),
)
WRIST_NOTE = "\nNOTE: this robot has no wrist camera: image 2 is blank."
VID_EVERY = 1  # 3 Hz control -> 3 fps video


# E-SIM1 (prereg_sim1.md): SimplerEnv WidowX + Bridge facts (tools/sim0/widowx_geom.py)
BOX_W = ((0.15, 0.55), (-0.30, 0.30), (0.005, 0.40))
TEXT_W = (
    ("You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) at a table, in simulation.",
     "You control a robot arm (WidowX 250) at a table, in simulation."),
    ("its two fingers close along the robot x axis. TCP = the point midway between the finger pads. The pads are 4.5 cm "
     "long (from 2.25 cm above to 2.25 cm below the TCP); the gripper body starts 2.5 cm above the TCP.",
     "its two fingers close along the robot y axis. TCP = the point midway between the fingertips. The fingers reach "
     "about 3 cm above the TCP; the gripper body starts 3 cm above the TCP."),
    ("then apply gripper: close (0.6 s), open (0.5 s) or keep.",
     "then apply gripper: close or open (the code waits until the fingers stop moving, at most 10 s) or keep."),
)
BENCH = "gr"


def patch():
    from ..astra_motion import executor as EX
    if BENCH == "bridge":
        EX.SAFE_X, EX.SAFE_Y, EX.SAFE_DZ = BOX_W
    else:
        EX.SAFE_X, EX.SAFE_Y, EX.SAFE_DZ = BOX_X, BOX_Y, DZ
    from ..lib0 import rim
    rim.OPEN_M = 0.15  # Google Robot open fingertip span (tools/sim0/robot_geom.py), minus a little


def text_g(text: str) -> str:
    for old, new in (TEXT_W if BENCH == "bridge" else TEXT_G):
        if text.count(old) != 1:
            raise ValueError(f"E-SIM0: fixed sentence not found once: {old[:60]!r}")
        text = text.replace(old, new)
    import re
    text, n = re.subn(r"- Right wrist camera \(image 2\): [^\n]*", "- Right wrist camera (image 2): none (blank image).",
                      text, count=1)
    if n != 1:
        raise ValueError("E-SIM0: wrist line not found")
    return text + WRIST_NOTE


def episode_class():
    from PIL import Image

    from ..lib0.run_a import episode_class as lib_class
    from ..lib0.run_a import settle_exec

    Base = lib_class()

    class SimEpisode(Base):
        fix_b, fix_c = False, False  # change 2: no grasp-location rule (user 10-02 02시: current model as is)

        def _request(self, obs, i, statics):
            text, ims = super()._request(obs, i, statics)
            return text_g(text), ims

        def make_exec(self, st):
            ex = super().make_exec(st)
            ex.__class__ = settle_exec(type(ex), self.w)
            return ex

        def _tick(self):
            super(Base, self)._tick()  # skip the lib0 two-camera video
            if not self.vid_dir:
                return
            self._v = getattr(self, "_v", -1) + 1
            if self._v % VID_EVERY:
                return
            n = getattr(self, "_nv", 0)
            Image.fromarray(self.w.frame()["head"]).save(os.path.join(self.vid_dir, f"f{n:05d}.jpg"), quality=85)
            self._nv = n + 1
    return SimEpisode


def block_of(world) -> str:
    """TASK / Success / OBJECTS for the episode: the scene's actors except the arena; an actor whose name words appear
    in the instruction = 'task object', the rest 'obstacle' (names: actor names without index / underscores)."""
    from ..lib0.run_a import OBJ_HEAD, SUCCESS_LINE
    from ..lib0.world import obj_name
    names = [a.name for a in world.env.unwrapped._scene.get_all_actors() if a.name not in ("arena", "ground", "")]
    ins = world.instruction.lower()
    lines = []
    for n in names:
        nm = obj_name(n).replace("baked ", "").replace(" v2", "")
        role = "task object" if any(w in ins for w in nm.lower().split() if len(w) > 3) else "obstacle"
        lines.append(f"- {nm} ({role})")
    return f"TASK: {world.instruction}\n{SUCCESS_LINE}\n{OBJ_HEAD}\n" + "\n".join(lines) + "\n"


def make_mp4(frames_dir: str, out: str, fps: int = 3) -> bool:
    import subprocess

    import imageio_ffmpeg
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                        os.path.join(frames_dir, "f%05d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf",
                        "pad=ceil(iw/2)*2:ceil(ih/2)*2", out], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


def g0(world) -> dict:
    """Scripted check (sim truth of the can): above the can 8 cm, down to its top - 2 cm, close, lift 10 cm."""
    from ..lib0.run_a import settle_exec  # noqa: F401
    from ..astra_solo.executor import MinJerkExec
    from ..astra_motion.geometry import pixel_of
    from ..astra_solo import resolve as RS
    u = world.env.unwrapped
    src = getattr(u, "obj", None) or getattr(u, "episode_source_obj", None)
    p = world.to_base(src.pose.p)
    st = world.status()
    o = world.observe(depth=True)  # G1: the resolver on the can's projected centre vs the sim truth
    iu, iv, ins = pixel_of(o.cams["head"], p)
    g1 = None
    if ins:
        r = RS.resolve_point(o.cams["head"], o.depth["head"], world.table_z,
                             [(iu + 0.5) / o.cams["head"].W * 1000, (iv + 0.5) / o.cams["head"].H * 1000], tcp=st["tcp"])
        g1 = None if r.get("xy") is None else round(float(np.linalg.norm(np.asarray(r["xy"]) - p[:2])) * 1e3, 1)
    ex = MinJerkExec(world.dt, world.table_z, st["tcp"], world.w_open, world.w_close)
    top = p[2] + 0.06  # upright can: centre + half height
    plan = [([p[0], p[1], top + 0.08], "keep"), ([p[0], p[1], top - 0.03], "close"), ([p[0], p[1], top + 0.10], "keep")]
    for goal, g in plan:
        ex.go_to(goal, g, world.t)
        for _ in range(60):
            if not ex.busy:
                break
            cmd, w, _ = ex.tick(world.t, world.status()["tcp"])
            world.step(cmd, w)
    return {"can_base": np.round(p, 4).tolist(), "g1_xy_err_mm": g1, "table_z": round(world.table_z, 4),
            "success": world.done, "tcp": np.round(world.status()["tcp"], 4).tolist(),
            "gap": round(world._gap(), 4)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps", required=True, help="comma list of episode names (world.ep_name)")
    ap.add_argument("--qwen-url", default=None)
    ap.add_argument("--qwen-name", default="lib0_ep2_5")
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--arm", default="A")
    ap.add_argument("--stop-files", default="")
    ap.add_argument("--g0", action="store_true")
    ap.add_argument("--bench", default="gr", choices=("gr", "bridge"))
    a = ap.parse_args(argv)
    global BENCH
    BENCH = a.bench
    patch()
    from ..astra_solo import pt_episode as PE
    from ..astra_solo import resolve as RS
    from ..lib0.run_a import LibMonitor
    from ..teach_pt.run_closed_l8s import ErrCount, claim, yield_reason
    if a.bench == "bridge":
        from .bridge import BridgeWorld as SimWorld
        from .bridge import ep_name, episodes
    else:
        from .world import SimWorld, ep_name, episodes
    RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
    PE.Monitor = LibMonitor
    want = set(a.eps.split(","))
    specs = [e for e in episodes() if ep_name(e) in want]
    stops = [f for f in a.stop_files.split(",") if f]
    model = None
    if not a.g0:
        from ..astra_solo.models import LocalVLM
        model = ErrCount(LocalVLM(a.qwen_url, a.qwen_name, "q35_sim0"))
    code = 0
    for e in specs:
        if yield_reason(stops):
            code = 3
            break
        name = ep_name(e)
        od = os.path.join(a.out, a.arm, name)
        if not claim(od, f"pid={os.getpid()}"):
            continue
        t0 = time.perf_counter()
        world = SimWorld(e)
        try:
            if a.g0:
                world.reset()
                r = g0(world)
                json.dump(dict(r, name=name), open(os.path.join(od, "result.json"), "w"))
                print("G0 " + json.dumps(dict(r, name=name)), flush=True)
                world.close()
                continue
            vd = os.path.join(od, "frames")
            os.makedirs(vd, exist_ok=True)
            Ep = episode_class()
            model.errors = 0
            world.reset()
            ep = Ep(world, model, 0, "simpler", od, video=False, variant="simpler", stop_calls=30, stop_motion_s=120.0,
                    mem_points=True, fix_loop=True, loop_break=True, stall_n=3, corrupt=None)
            ep.vid_dir = vd
            ep.block = block_of(world)
            world.reset = lambda *a_, **k_: None  # already reset (the episode's run() calls reset again)
            res = ep.run()
        except Exception as ex:  # noqa: BLE001
            import traceback
            json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]}, open(os.path.join(od, "error.json"), "w"))
            print("EP_ERROR " + json.dumps({"ep": name, "err": repr(ex)}), flush=True)
            world.close()
            continue
        if model.errors:
            os.rename(od, f"{od}.srv_err.{int(time.time())}")
            world.close()
            continue
        mp4 = os.path.join(a.vid_root, a.arm, name + ".mp4")
        ok = make_mp4(vd, mp4)
        budget_s = world.max_steps * world.dt
        row = {"arm": a.arm, "ep": name, "task": e["task"], "instruction": world.instruction,
               "success": bool(res.get("success")), "t_success": res.get("t_success"),
               "success_in_budget": bool(res.get("success")) and res.get("t_success") is not None
               and float(res["t_success"]) <= budget_s + 1e-9, "budget_s": budget_s,
               "end_reason": res.get("end_reason"), "fail_stage": res.get("fail_stage"), "n_calls": res.get("n_calls"),
               "n_invalid": res.get("n_invalid"), "latency_s": res.get("latency_s") or [], "sim_t": res.get("sim_t"),
               "wall_s": round(time.perf_counter() - t0, 1), "table_z": world.table_z, "mp4": mp4 if ok else None,
               "result": os.path.join(od, "result.json")}
        json.dump(row, open(os.path.join(od, "row.json"), "w"))
        with open(os.path.join(a.vid_root, a.arm + "_index.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")
        print("EP " + json.dumps({x: row[x] for x in ("ep", "success", "end_reason", "n_calls", "wall_s")}), flush=True)
        world.close()
    print("RUN_DONE", flush=True)
    os._exit(code)


if __name__ == "__main__":
    main()
