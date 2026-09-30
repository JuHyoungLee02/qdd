"""E-M35CL closed loop on L8S furniture scenes (docs/stage3/prereg_main35_closed.md; pod, Isaac, report only).
One process = one collect job (the L8S / OOD-O render command line, --job): the world and the clutter pool are rebuilt
exactly as harvest.teach_l8d.run_collect built them for that job (same plan rows -> same registered objects, pool and
look-alikes), then each listed episode (seed, task) is re-run with a local vLLM model through the boost1b executor
(LimitEpisode, d-min, mem_points + fix_loop = the f35_d limits configuration), once per condition:
  none | light:<level> (limits.LIGHT_LEVELS on every head observation) | head:<tilt deg>:<pan deg> (head pose offset
  from the L8S default 0.785 / 0 for every episode; the in-view redraw halves it, then the default).
Episodes are claimed with mkdir (several lanes share one list); between episodes the process exits when a yield file
exists (L9 GPU_WANTED, exit 3) or the served checkpoint changed (exit 0). Every episode writes a 10 fps head | left
wrist | right wrist video (jpg frames kept + H.264 mp4) and one index line.
python -m harvest.teach_pt.run_closed_l8s --job "<run_collect args>" --episodes FILE --conds none --ckpt f35d
  --qwen-url http://host:port --qwen-name m35cl_f35d --out /data/harvest/out/main35_closed/res
  --vid-root /data/harvest/videos/main35_closed [--current FILE] [--yield-files a,b]"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time

STALE_S = 3600  # a claim without a result after this long is taken over (a killed lane)
VID_EVERY = 2  # control ticks at 20 Hz -> 10 fps
FFMPEG_FALLBACK = "/isaac-sim/kit/python/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"


def parse_cond(cond: str) -> dict:
    """none | light:<level> | head:<tilt deg>:<pan deg> -> {kind, ...}."""
    p = cond.split(":")
    if p[0] == "none" and len(p) == 1:
        return {"kind": "none"}
    if p[0] == "light" and len(p) == 2:
        return {"kind": "light", "level": p[1]}
    if p[0] == "head" and len(p) == 3:
        return {"kind": "head", "tilt_deg": float(p[1]), "pan_deg": float(p[2])}
    raise ValueError(f"bad condition {cond!r}")


def cond_dir(cond: str) -> str:
    return cond.replace(":", "_").replace("+", "p").replace("-", "m")


def yield_reason(files) -> str | None:
    for f in files:
        if f and os.path.exists(f):
            return f
    return None


def claim(od: str, owner: str, now: float | None = None) -> bool:
    """True when this process owns episode dir od (mkdir od/claim); a finished episode is never claimed; a stale
    claim (no result after STALE_S) is moved aside atomically and taken over."""
    if done(od):
        return False
    os.makedirs(od, exist_ok=True)
    c = os.path.join(od, "claim")
    try:
        os.mkdir(c)
    except FileExistsError:
        now = time.time() if now is None else now
        if now - os.path.getmtime(c) < STALE_S:
            return False
        try:
            os.rename(c, f"{c}.stale.{os.getpid()}.{int(now)}")
            os.mkdir(c)
        except OSError:
            return False
    with open(os.path.join(c, "owner"), "w") as f:
        f.write(owner)
    return True


def done(od: str) -> bool:
    return any(os.path.exists(os.path.join(od, n)) for n in ("result.json", "skip.json", "error.json"))


def served(current: str):
    """The checkpoint named in the served-checkpoint file, None when there is none (no server)."""
    try:
        t = open(current).read().split()
    except OSError:
        return None
    return t[0] if len(t) == 3 else None


def server_error(err) -> bool:
    """A transport / server-side error (LocalVLM stores it in reply.error and the episode goes on)."""
    e = str(err or "")
    return bool(e) and (not e.startswith("http_") or e.startswith(("http_5", "http_404")))


class ErrCount:
    def __init__(self, m):
        self.m, self.errors = m, 0

    def ask(self, *a, **k):
        r = self.m.ask(*a, **k)
        if server_error(getattr(r, "error", None)):
            self.errors += 1
        return r

    def __getattr__(self, k):
        return getattr(self.m, k)


def job_args(job: str):
    ap = argparse.ArgumentParser()
    for k in ("--split", "--variant", "--ws-x", "--furniture", "--objset", "--plan"):
        ap.add_argument(k, default=None)
    ap.add_argument("--table-z", type=float, required=True)
    ap.add_argument("--lift", type=float, default=None)
    ap.add_argument("--rooms", action="store_true")
    ap.add_argument("--clutter", type=int, default=0)
    ap.add_argument("--confirm-ood", action="store_true")
    ap.add_argument("--reach", default="/data/harvest/out/teach_l8d/gate/reach_base.json")
    j, _ = ap.parse_known_args(shlex.split(job))
    return j


def build_world(j):
    """= harvest.teach_l8d.run_collect.main's world / pool construction for this job (its plan rows)."""
    from ..teach_l8d import spec as S
    from ..teach_l8d.run_collect import make_world, select_plan
    x0, x1 = (float(v) for v in j.ws_x.split(","))
    ws = S.ws_of((x0, x1))
    eps = select_plan(json.load(open(j.plan)), j.variant, j.table_z, j.split, j.objset, j.lift, j.furniture,
                      bool(j.clutter))
    from ..sim.objv import register_for_tasks
    if j.variant == "drf":
        from ..sim.tasks import use_shape_names
        use_shape_names()
    register_for_tasks([e["task"] for e in eps])
    pool = None
    if j.clutter:
        from ..sim.objv import register
        from ..teach_l8d.clutter_x import confuser_ids, load_real, pool_for
        key = f"{j.variant}|{j.table_z:.3f}|{j.lift}" + (f"|{j.furniture}" if j.furniture else "")
        rows_real = load_real()
        pool = pool_for(rows_real, key, n=j.clutter, n_base=12 if j.furniture else 0)
        if j.furniture:
            from ..sim.tasks import TASKS as _T
            for e in eps:
                t = _T.get(e["task"])
                if t is not None and t.target in rows_real:
                    pool.update({k: rows_real[k] for k in confuser_ids(rows_real, t.target)})
        register(pool)
    sp = "ood" if j.split == "ood_s" else "train"
    return make_world(j.variant, j.table_z, ws, j.lift, j.objset, j.furniture, j.reach, sp, sp if j.rooms else None,
                      pool)


def head_patch(cx, c: dict):
    """Replace clutter_x.head_pose (looked up at every reset) by the fixed offset; -> restore function."""
    import math
    orig = cx.head_pose

    def fixed(seed, attempt=0):
        sc = 0.5 ** int(attempt)
        return {"tilt": round(cx.HEAD_TILT0 + math.radians(c["tilt_deg"]) * sc, 4),
                "pan": round(math.radians(c["pan_deg"]) * sc, 4), "random": True, "attempt": int(attempt),
                "cl_variant": True}
    cx.head_pose = fixed

    def restore():
        cx.head_pose = orig
    return restore


def episode_class():
    import numpy as np
    from PIL import Image

    from ..teach_strip8.boost import LimitEpisode

    class CLEpisode(LimitEpisode):
        """LimitEpisode + a 10 fps three-camera frame dump (head | left wrist | right wrist) to vid_dir."""
        vid_dir = None

        def _tick(self):
            super()._tick()
            if not self.vid_dir:
                return
            self._v10 = getattr(self, "_v10", -1) + 1
            if self._v10 % VID_EVERY:
                return
            fr = self.w.frame()
            h, wr = fr["head"], fr["wrist"]
            wl = self.w.env.camera_rgb("cam_wrist_left")
            hh = h.shape[0]
            parts = [h] + [np.asarray(Image.fromarray(x).resize((int(x.shape[1] * hh / x.shape[0]), hh)))
                           for x in (wl, wr)]
            n = getattr(self, "_nv", 0)
            Image.fromarray(np.concatenate(parts, 1)).save(os.path.join(self.vid_dir, f"f{n:05d}.jpg"), quality=85)
            self._nv = n + 1
    return CLEpisode


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return FFMPEG_FALLBACK


def make_mp4(frames_dir: str, out: str) -> bool:
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(20 // VID_EVERY), "-i",
                        os.path.join(frames_dir, "f%05d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf",
                        "pad=ceil(iw/2)*2:ceil(ih/2)*2", out], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)


def repro_check(world, ep_dir: str) -> dict:
    """The rebuilt scene against the render's scene.json (clutter ids, instruction)."""
    try:
        s = json.load(open(os.path.join(ep_dir, "scene.json")))
    except OSError:
        return {"scene_json": False}
    import ast
    cl = s.get("clutter")
    if isinstance(cl, str):
        cl = ast.literal_eval(cl)
    ours = getattr(world, "clutter_scene", None) or {}
    info = {}
    try:
        info = world.task_info()
    except Exception:  # noqa: BLE001
        pass
    return {"clutter_match": (cl or {}).get("ids") == ours.get("ids"),
            "instruction_match": s.get("instruction") == info.get("instruction"),
            "head": (getattr(world, "furniture_scene", None) or {}).get("head")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--episodes", required=True, help="JSON [{set, dir, seed, task}] (one job)")
    ap.add_argument("--conds", default="none")
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--current", default=None, help="the served-checkpoint file; exit when it names another")
    ap.add_argument("--yield-files", default="")
    ap.add_argument("--owner", default="")
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    a = ap.parse_args(argv)
    code = 0
    yf = [f for f in a.yield_files.split(",") if f]
    try:
        from ..astra_solo.models import LocalVLM
        from ..sim.tasks import X_STEPS
        from ..teach_l8d import clutter_x as CX
        from ..teach_l8d.fx import SkipScene
        from ..teach_l8d.spec import check_seed
        j = job_args(a.job)
        eps = json.load(open(a.episodes))
        for e in eps:
            check_seed(e["seed"], j.split, True)
        world = build_world(j)
        print("WORLD " + json.dumps({"furniture": j.furniture, "plan": j.plan, "n": len(eps), "ckpt": a.ckpt}),
              flush=True)
        model = ErrCount(LocalVLM(a.qwen_url, a.qwen_name, "qwen8b"))
        Ep = episode_class()
        owner = f"{a.owner} pid={os.getpid()}"
        for cond in a.conds.split(","):
            c = parse_cond(cond)
            restore = head_patch(CX, c) if c["kind"] == "head" else (lambda: None)
            try:
                for e in eps:
                    why = yield_reason(yf)
                    if why:
                        print("YIELD " + why, flush=True)
                        code = 3
                        raise StopIteration
                    if a.current and served(a.current) != a.ckpt:  # switched or the server yielded
                        print("CKPT_CHANGED", flush=True)
                        raise StopIteration
                    name = f"{e['task']}_s{e['seed']}"
                    od = os.path.join(a.out, a.ckpt, cond_dir(cond), e["set"], name)
                    if e["task"] in X_STEPS or not claim(od, owner):
                        continue
                    vd = os.path.join(od, "frames10")
                    os.makedirs(vd, exist_ok=True)
                    t0 = time.perf_counter()
                    kw = dict(video=False, variant=j.variant, stop_calls=a.stop_calls, stop_motion_s=a.stop_motion,
                              mem_points=True, fix_loop=True,
                              corrupt=("light", c["level"]) if c["kind"] == "light" else None)
                    model.errors = 0
                    try:
                        ep = Ep(world, model, e["seed"], e["task"], od, **kw)
                        ep.vid_dir = vd
                        res = ep.run()
                    except SkipScene as ex:
                        json.dump({"reason": str(ex)}, open(os.path.join(od, "skip.json"), "w"))
                        print("SKIP " + json.dumps({"seed": e["seed"], "task": e["task"], "why": str(ex)}),
                              flush=True)
                        continue
                    except Exception as ex:  # noqa: BLE001 -- one bad episode must not end the lane
                        import traceback
                        json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]},
                                  open(os.path.join(od, "error.json"), "w"))
                        print("EP_ERROR " + json.dumps({"seed": e["seed"], "task": e["task"], "err": repr(ex)}),
                              flush=True)
                        continue
                    if model.errors:  # the server went away (yield / restart): not a model failure -> retry later
                        os.rename(od, f"{od}.srv_err.{int(time.time())}")
                        print("EP_SRV_ERR " + json.dumps({"seed": e["seed"], "task": e["task"], "n": model.errors}),
                              flush=True)
                        continue
                    rep = repro_check(world, e["dir"])
                    mp4 = os.path.join(a.vid_root, a.ckpt, e["set"], cond_dir(cond), name + ".mp4")
                    ok = make_mp4(vd, mp4)
                    row = {"ckpt": a.ckpt, "cond": cond, "set": e["set"], "seed": e["seed"], "task": e["task"],
                           "success": bool(res.get("success")), "fail_stage": res.get("fail_stage"),
                           "end_reason": res.get("end_reason"), "n_calls": res.get("n_calls"),
                           "sim_t": res.get("sim_t"), "wall_s": round(time.perf_counter() - t0, 1),
                           "repro": rep, "mp4": mp4 if ok else None, "n_frames": getattr(ep, "_nv", 0),
                           "frames": vd, "result": os.path.join(od, "result.json"), "src": e["dir"]}
                    json.dump(row, open(os.path.join(od, "cl.json"), "w"))
                    os.makedirs(a.vid_root, exist_ok=True)
                    with open(os.path.join(a.vid_root, "index.jsonl"), "a") as f:
                        f.write(json.dumps(row) + "\n")
                    print("EP " + json.dumps({k: row[k] for k in ("ckpt", "cond", "set", "seed", "task", "success",
                                                                  "end_reason", "n_calls", "wall_s")}), flush=True)
            finally:
                restore()
        print("RUN_DONE", flush=True)
    except StopIteration:
        pass
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
