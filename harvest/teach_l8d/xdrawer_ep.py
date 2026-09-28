"""L8-X drawer episodes for the runner (prereg_l8x_tasks 2.4, change 12): dr__<piece>__<handle> tasks only.

DrawerEpisode = the synchronous astra-solo loop of astra_solo.episode.Episode (observe -> ask -> execute completely
with the min-jerk executor -> measured history), with the drawer truth plan (xdrawer.plan_drawer_front) as the
behaviour policy (DART-style offsets on approach moves with probability p, at most max_perturb per episode; the label
is always the truth), the +x2 request (xdrawer_prompt) and the drawer judge (xdrawer.success_drawer). Per call it saves
the request as prompt_v2.txt and prompt_nd-xyz@v1.txt (the same stripped text), the ring-only head image under both
head file names, the wrist image, cams.json and head_depth.npz; per episode labels.jsonl / scene.json / meta.json /
result.json in the teach_l8d layout (build b3d with format nd-xyz, aux off: the rows have no object pixels).

World protocol (DrawerWorld on the pod; a fake world in the tests): reset(seed, task) -> spec dict (instruction words,
open_target, pull_dir), status() -> {t, tcp, grip_w, handle, joint, root}, observe(depth) -> Obs, frame(), step(pos,
width, quat), dt, table_z (the executor's box base = handle z - 0.15), w_open, w_close, quats {"down", "front"}.
Nothing here changes the existing runner paths: run_collect calls run_drawer only when every task is dr__."""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np

from ..astra_solo.episode import VIDEO_EVERY, outcome
from ..astra_solo.executor import MinJerkExec
from . import xdrawer as XD
from . import xdrawer_prompt as XP

SCENE_SCHEMA = "qdd.l8d.scene/v1"
PERTURB_STEPS = ("front_of_handle", "insert", "retreat")
PERTURB_M = (0.01, 0.03)  # offset length range of a behaviour perturbation (y / z, across the approach line)
MAX_CALLS, MOTION_LIMIT_S = 40, 180.0  # the prompt's stated limits (= astra_solo.episode)
HANDLE_X, HANDLE_Y = (0.50, 0.54), (-0.28, -0.16)  # change 12: seeded handle position (retreat stays in x >= 0.25)
LIFT_JITTER = 0.02
REL_Z = 0.95


def _l(v):
    return [round(float(x), 4) for x in np.asarray(v, float)]


def layout_of(seed: int) -> dict:
    """Seeded handle position and lift offset of an episode (pure)."""
    r = np.random.default_rng([int(seed), 12, 7])
    return {"handle_xy": [float(r.uniform(*HANDLE_X)), float(r.uniform(*HANDLE_Y))],
            "lift_dz": float(r.uniform(-LIFT_JITTER, LIFT_JITTER))}


class DrawerEpisode:
    def __init__(self, world, seed: int, task: str, out_dir: str | None, p: float, max_perturb: int, rng,
                 stop_calls: int | None = 30, stop_motion_s: float | None = 120.0, video: bool = False):
        self.w, self.seed, self.task, self.out_dir = world, int(seed), task, out_dir
        self.p, self.max_perturb, self.rng = p, max_perturb, rng
        self.stop_calls, self.stop_motion_s, self.video = stop_calls, stop_motion_s, video
        self.rows, self.history, self.events, self.frames = [], [], [], []
        self.n_pert = 0
        self.end_reason = None

    def _t(self):
        return float(self.w.status()["t"]) - self.t0

    def _tick(self):
        st = self.w.status()
        pos, width, ev = self.ex.tick(st["t"], st["tcp"])
        self.events += ev
        self.w.step(pos, width, self.ex.goal_quat)
        self._vt = getattr(self, "_vt", -1) + 1
        if self.video and self._vt % VIDEO_EVERY == 0:
            fr = self.w.frame()
            self.frames.append((fr["head"], fr["wrist"]))

    def _execute(self, cmd: dict, t: float, tcp) -> list:
        m = cmd["mode"]
        if m == "eef":
            if cmd.get("orient"):
                self.orient = cmd["orient"]
                self.ex.goal_quat = np.asarray(self.w.quats[self.orient], float)
            return self.ex.go_to(cmd["position_m"], cmd["gripper"], t)
        if cmd.get("gripper") == "open" and cmd.get("width_m") is not None:
            self.ex.w_open = float(cmd["width_m"])
        self.ex.grip(cmd["gripper"], t)
        return []

    def _perturbed(self, step: str, cmd: dict):
        if cmd["mode"] != "eef" or step not in PERTURB_STEPS or self.n_pert >= self.max_perturb or \
                self.rng.random() >= self.p:
            return cmd, "clean"
        a = self.rng.uniform(0, 2 * math.pi)
        d = self.rng.uniform(*PERTURB_M)
        off = np.array([0.0, d * math.cos(a), d * math.sin(a)])
        self.n_pert += 1
        return dict(cmd, position_m=_l(np.asarray(cmd["position_m"], float) + off)), "perturb_xyz"

    def _save_call(self, idx: int, text: str, obs, ring_png: bytes):
        from ..astra_solo.overlay import png_bytes
        from ..teach_l8.dataset import IMAGE_FILES
        d = os.path.join(self.out_dir, "calls", f"c{idx:03d}")
        os.makedirs(d, exist_ok=True)
        for name in ("prompt.txt", "prompt_v2.txt", "prompt_nd-xyz@v1.txt"):
            with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        for name in (IMAGE_FILES[0], "img1_head_ring.png"):
            with open(os.path.join(d, name), "wb") as f:
                f.write(ring_png)
        with open(os.path.join(d, IMAGE_FILES[1]), "wb") as f:
            f.write(png_bytes(obs.rgb["wrist"]))
        with open(os.path.join(d, "cams.json"), "w") as f:
            json.dump({k: c.to_json() for k, c in obs.cams.items()}, f)
        if obs.depth and obs.depth.get("head") is not None:
            np.savez_compressed(os.path.join(d, "head_depth.npz"), depth=np.asarray(obs.depth["head"], np.float32))

    def run(self) -> dict:
        from ..astra_solo import nd as ND
        from ..astra_solo.overlay import png_bytes
        from ..teach_l8 import labels as L
        w = self.w
        spec = w.reset(self.seed, self.task)
        self.spec = spec
        st = w.status()
        self.t0, root0 = float(st["t"]), np.asarray(st["root"], float).copy()
        self.orient = "down"
        self.ex = MinJerkExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, quat0=w.quats["down"])
        info = {"pull_dir": spec["pull_dir"], "open_target": spec["open_target"]}
        wall0 = time.perf_counter()
        static, prev_kind, prev_failed, prev_cmd, r, stopped = None, "start", False, None, None, False
        for i in range(1, MAX_CALLS + 1):
            if self.stop_calls is not None and i > self.stop_calls:
                r = "stage_cap_calls"
                break
            if self._t() >= MOTION_LIMIT_S or (self.stop_motion_s is not None and self._t() >= self.stop_motion_s):
                r = "stage_cap_motion"
                break
            obs = w.observe(depth=True)
            st = w.status()
            if static is None:
                static = XP.static(spec["words"], obs.cams["head"], spec["open_target"])
            ring, drawn = ND.ring_overlay(obs.rgb["head"], obs.cams["head"], obs.tcp)
            text = static + XP.now(obs.cams["wrist"], obs.tcp, obs.grip_w, self.orient, i, MAX_CALLS, self._t(),
                                   MOTION_LIMIT_S, self.history) + XP.ANSWER + ("" if "tcp" in drawn else XP.NOTE_TCP)
            step, cmd = XD.plan_drawer_front(st, info, w.w_open)
            last = self.history[-1] if self.history else ""
            ans = XP.answer(step, cmd, st, spec["words"], not self.history, last, prev_failed, float(st["joint"]))
            drop = "stuck" if L.stuck(last, prev_cmd, cmd) else None
            ex_cmd, kind = (cmd, "clean") if cmd["mode"] == "stop" else self._perturbed(step, cmd)
            idx = len(self.rows)
            self.rows.append({"call": idx, "site": i, "prev_kind": prev_kind, "drop": drop, "step": step,
                              "phase": step, "status": json.loads(ans)["assessment"]["execution_status"],
                              "answer": ans, "pt_answer": None, "ndest_answer": None, "ndpt_answer": None,
                              "exec_kind": kind, "orient": self.orient, "tgt": "handle", "place": "drawer",
                              "gt": {"tcp": _l(st["tcp"]), "grip_w": round(float(st["grip_w"]), 4),
                                     "handle": _l(st["handle"]), "joint": round(float(st["joint"]), 4)},
                              "prompt_id": XP.PROMPT_ID, "prompt_version": XP.VERSION})
            if self.out_dir:
                self._save_call(idx, text, obs, png_bytes(ring))
            prev_kind, prev_failed, prev_cmd = kind, self.rows[-1]["status"] == "failed", ex_cmd
            if cmd["mode"] == "stop":
                self.history.append(f"{i}: stop")
                r, stopped = "stop", True
                break
            n_ev = len(self.events)
            self.events += self._execute(ex_cmd, st["t"], st["tcp"])
            while self.ex.busy:
                if self._t() >= MOTION_LIMIT_S:
                    break
                self._tick()
            st = w.status()
            res = "; ".join(outcome(e) for e in self.events[n_ev:]
                            if e["event"] in ("clipped", "reach", "settled", "timeout")) or "done"
            t = st["tcp"]
            self.history.append(f"{i}: {XP.describe(ex_cmd)} -> {res}; TCP now ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}), "
                                f"gripper {self.orient}, pad gap {st['grip_w'] * 100:.1f} cm")
        else:
            r = "call_limit"
        self.end_reason = r
        st = w.status()
        move = float(np.linalg.norm(np.asarray(st["root"], float) - root0))
        ok = XD.success_drawer(float(st["joint"]), float(st["grip_w"]), w.w_open, move, spec["open_target"])
        self.judge = {"joint_end": round(float(st["joint"]), 4), "open_target": spec["open_target"],
                      "grip_end": round(float(st["grip_w"]), 4), "root_move_m": round(move, 4), "stopped": stopped,
                      "success": bool(ok and stopped)}
        return {"success": bool(ok and stopped), "end_reason": r, "n_calls": len(self.rows),
                "sim_t": round(self._t(), 2), "wall_s": round(time.perf_counter() - wall0, 1),
                "history": self.history, "events": self.events, "judge": self.judge}


def collect_drawer_episode(world, seed: int, task: str, variant: str, split: str, out_dir: str, p: float,
                           max_perturb: int = 4, stop_calls: int | None = 30, stop_motion_s: float | None = 120.0,
                           style: str = "", video: bool = False) -> dict:
    """= collect.collect_episode for a dr__ task (same rng stream rule, the same output files)."""
    from ..teach_l8 import collect as LC
    rng = np.random.default_rng([int(seed), 8, LC.VARIANT_CODE.get(variant, 9)])
    ep = DrawerEpisode(world, seed, task, out_dir, p, max_perturb, rng, stop_calls, stop_motion_s, video)
    res = ep.run()
    os.makedirs(out_dir, exist_ok=True)
    sp = ep.spec
    scene = {"schema": SCENE_SCHEMA, "seed": seed, "split": split, "task": task, "variant": variant, "style": style,
             "instruction": sp["words"]["instruction"], "table_z": round(float(world.table_z), 5),
             "lift": sp.get("lift"), "lift_joint_measured": sp.get("lift_measured"), "ws": None, "layout": {},
             "randomization": None, "rand_settle": None, "steps": None, "clutter": None, "surface": "drawer",
             "furniture": {"piece": sp["piece"], "handle": sp["handle"], "handle_xyz": sp.get("handle_xyz"),
                           "open_target": sp["open_target"], "pull_dir": _l(sp["pull_dir"]), "layout": sp.get("layout")},
             "distractors": {"n": 0, "layout_objects": [], "pool_distractors": []}}
    with open(os.path.join(out_dir, "scene.json"), "w") as f:
        json.dump(scene, f)
    with open(os.path.join(out_dir, "labels.jsonl"), "w") as f:
        for r in ep.rows:
            f.write(json.dumps(dict(r, seed=seed, task=task, variant=variant, table_z=scene["table_z"],
                                    n_distractors=0)) + "\n")
    with open(os.path.join(out_dir, "result.json"), "w") as f:
        json.dump(dict(res, seed=seed, task=task, prompt_id=XP.PROMPT_ID, prompt_version=XP.VERSION), f, indent=1)
    if ep.frames:
        from PIL import Image
        fd = os.path.join(out_dir, "frames")
        os.makedirs(fd, exist_ok=True)
        for k, (h, wr) in enumerate(ep.frames):
            hh = h.shape[0]
            wr2 = np.asarray(Image.fromarray(wr).resize((int(wr.shape[1] * hh / wr.shape[0]), hh)))
            Image.fromarray(np.concatenate([h, wr2], 1)).save(os.path.join(fd, f"f{k:04d}.jpg"), quality=85)
    meta = {"seed": seed, "split": split, "task": task, "variant": variant, "table_z": scene["table_z"],
            "lift": scene["lift"], "n_distractors": 0, "p": p, "max_perturb": max_perturb, "style": style,
            "success": res["success"], "end_reason": res["end_reason"], "n_calls": res["n_calls"],
            "n_rows": len(ep.rows), "n_perturb": ep.n_pert, "sim_t": res["sim_t"], "wall_s": res["wall_s"],
            "n_pt_labels": 0, "judge": ep.judge, "prompt_id": XP.PROMPT_ID, "prompt_version": XP.VERSION}
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta


# ============================================================================ Isaac (pod)
U_THOR = "/data/harvest/assets_x/molmospaces/objects_thor/usd"


def usd_of(piece: str) -> str:
    pkg = "thor_Dresser" if piece.startswith("Dresser") else "thor_Desk" if piece.startswith("Desk") else \
        "thor_" + "_".join(piece.split("_")[:3]) if piece.startswith("Side_Table") else "thor_" + piece
    return f"{U_THOR}/{pkg}/{piece}/{piece}.usda"


def make_drawer_world(piece: str, handles: dict):
    """One articulated THOR piece per process (= tools/l8x_assets/gate_drawer.py, gate 6 ff577d8): fixed root, drawer
    links 1 kg, damped; Y-up fix + yaw -90 deg (front towards the robot). handles: {handle body: words dict}. The
    bar centres are measured once before any root move (USD poses go stale after one), in each handle body's frame."""
    from ..astra_motion.world_isaac import CAMS, NO_RENDER, IsaacWorld
    from ..sim import scene as SC
    from ..sim.objv import qinv, qmul, qrot
    from tools.l8x_assets.gate_drawer import drawer_joint_of, joints_all

    usd = usd_of(piece)
    orig = SC._build_cfg
    q0 = (0.7071068, 0.7071068, 0.0, 0.0)
    qz = (math.cos(-math.pi / 4), 0.0, 0.0, math.sin(-math.pi / 4))
    rot = qmul(qz, q0)

    def patched(*x, **k):
        import isaaclab.sim as sim_utils
        from isaaclab.actuators import ImplicitActuatorCfg
        from isaaclab.assets import ArticulationCfg
        cfg, layout = orig(*x, **k)
        cfg.scene.table = None
        cfg.scene.art = ArticulationCfg(
            prim_path="{ENV_REGEX_NS}/ART",
            spawn=sim_utils.UsdFileCfg(usd_path=usd, mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
                                       articulation_props=sim_utils.ArticulationRootPropertiesCfg(fix_root_link=True)),
            init_state=ArticulationCfg.InitialStateCfg(pos=(1.2, 0.0, 0.0), rot=rot),
            actuators={"drawers": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=0.0, damping=20.0)})
        return cfg, layout

    class DrawerWorld(IsaacWorld):
        def __init__(self):
            from ..sim.scene import GRIP_MAX_W, make_env
            SC._build_cfg = patched
            try:
                self.env = make_env(0, headless=True, cameras=CAMS, depth=True, render_interval=NO_RENDER)
            finally:
                SC._build_cfg = orig
            env = self.env
            self.dt, self.w_open, self.w_close = float(env.step_dt), float(GRIP_MAX_W), 0.0
            self._st, self.last_obs = None, None
            env.layout = {}
            SC._LAYOUT["layout"] = {}
            for k in ("o3", "o5", "o8", "o9", "o10"):
                SC._LAYOUT["layout"].pop(k, None)
            env.reset(settle_s=0.2)
            self.art = env.scene["art"]
            bn, jn = list(self.art.body_names), list(self.art.joint_names)
            import omni.usd
            from pxr import Usd, UsdGeom
            stage = omni.usd.get_context().get_stage()
            root = stage.GetPrimAtPath("/World/envs/env_0/ART")
            cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy", "guide"])

            def rng_of(p):
                g = cache.ComputeWorldBound(p).ComputeAlignedRange()
                return None if g.IsEmpty() else (np.array(g.GetMin()), np.array(g.GetMax()))
            plo, phi = rng_of(root)
            joints = joints_all(usd)
            self.h = {}
            for hb, words in handles.items():
                hp = next(p for p in Usd.PrimRange(root) if p.GetName() == hb)
                best = None
                for p in Usd.PrimRange(hp):  # the grasp bar = the handle body's longest collider (change 8)
                    if "Collider" in p.GetName():
                        b = rng_of(p)
                        if b is not None and (best is None or (b[1] - b[0]).max() > (best[1] - best[0]).max()):
                            best = b
                hc = (best[0] + best[1]) / 2
                hi_ = bn.index(hb)
                bq = self.art.data.body_quat_w[0, hi_].cpu().numpy()
                jname = drawer_joint_of(joints, hb)
                ji = jn.index(jname)
                upper = float(self.art.data.soft_joint_pos_limits[0, ji, 1])
                self.h[hb] = {"words": words, "hc": hc, "bi": hi_, "ji": ji, "joint": jname,
                              "hoff": qrot(qinv(tuple(bq)), hc - self.art.data.body_pos_w[0, hi_].cpu().numpy()),
                              "open_target": min(XD.OPEN_TARGET, round(0.9 * upper, 3))}
            self.p0 = self.art.data.default_root_state[0, :3].cpu().numpy().copy()
            self.plo_z = float(plo[2])
            fq = qmul((math.cos(-math.pi / 4), 0.0, math.sin(-math.pi / 4), 0.0),
                      (math.cos(math.pi / 4), 0.0, 0.0, math.sin(math.pi / 4)))
            self.quats = {"down": None, "front": np.asarray(fq, float)}
            self.cur = None

        def reset(self, seed, task="dr"):
            from ..astra_motion.world_isaac import PRE_RENDER
            from ..sim.planner import OraclePlanner
            env = self.env
            hb = task.split("__")[2]
            h = self.h[hb]
            lay = layout_of(seed)
            hc = h["hc"]
            newp = self.p0 + np.array([lay["handle_xy"][0] - hc[0], lay["handle_xy"][1] - hc[1], -self.plo_z])
            self.art.data.default_root_state[0, :3] = env.torch.tensor(newp, device=env.env.device)
            self.art.cfg.init_state.pos = tuple(float(v) for v in newp)
            hz = float(hc[2] - self.plo_z)
            lift = float(np.clip(SC.INIT_JOINTS["lift_joint"] + (hz - REL_Z) + lay["lift_dz"], -0.5, 0.0))
            rob = env.robot
            li = rob.joint_names.index("lift_joint")
            rob.cfg.init_state.joint_pos["lift_joint"] = lift
            rob.data.default_joint_pos[0, li] = lift
            env.reset(settle_s=0.5)
            for _ in range(PRE_RENDER):
                env.env.sim.render()
            self.pl = OraclePlanner(env)
            self.quats["down"] = np.asarray(self.pl.goal_quat, float)
            self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
            self.quat0 = self.quats["down"]
            self.cur = h
            self._st = None
            st = self.status()
            self.table_z = float(st["handle"][2]) - 0.15  # executor box: handle - 12.5 cm .. + 25 cm
            words = dict(h["words"])
            return {"words": words, "open_target": h["open_target"], "pull_dir": [-1.0, 0.0, 0.0], "piece": piece,
                    "handle": hb, "handle_xyz": _l(st["handle"]), "lift": lift, "layout": lay,
                    "lift_measured": round(float(rob.data.joint_pos[0, li]), 4)}

        def status(self):
            if self._st is None:
                env, h, a = self.env, self.cur, self.art
                self._st = {"t": round(float(env.sim_time), 6), "tcp": self.pl.tcp_pose()[0],
                            "grip_w": float(env.gripper_width()),
                            "handle": a.data.body_pos_w[0, h["bi"]].cpu().numpy()
                            + qrot(tuple(a.data.body_quat_w[0, h["bi"]].cpu().numpy()), h["hoff"]),
                            "joint": float(a.data.joint_pos[0, h["ji"]]),
                            "root": a.data.root_pos_w[0].cpu().numpy().copy()}
            return self._st

        def observe(self, depth: bool = False):
            obs = IsaacWorld.observe(self)
            if depth:
                obs.depth = {"head": self.env.camera_depth("cam_head").copy()}
            return obs

    return DrawerWorld()


def is_drawer_run(eps: list) -> bool:
    """The runner's dr__ switch: a non-empty episode list of dr__ tasks only (a mix is refused)."""
    dr = [str(e["task"]).startswith("dr__") for e in eps]
    if any(dr) and not all(dr):
        raise ValueError("dr__ tasks cannot share a process with other tasks")
    return bool(dr) and all(dr)


def run_drawer(a, eps: list, vids: set) -> None:
    """run_collect's dr__ path: every episode of this process must be on one piece (one Isaac scene per piece;
    --piece picks it from a plan with several)."""
    from ..teach_l8.run_collect import style_of
    from . import spec as S
    if not a.drawer_list:
        raise ValueError("dr__ tasks need --drawer-list")
    drawer_list = json.load(open(a.drawer_list))
    if a.piece:
        eps = [e for e in eps if e["task"].split("__")[1] == a.piece]
    a.video_ids = vids
    pieces = {e["task"].split("__")[1] for e in eps}
    if len(pieces) != 1:
        raise ValueError(f"dr__ episodes of one process must share one piece, got {sorted(pieces)}")
    piece = pieces.pop()
    rows = {r["task"]: r for r in drawer_list["tasks"]}
    handles = {}
    for e in eps:
        r = rows[e["task"]]
        handles[r["handle_body"]] = r
    same = [r for r in drawer_list["tasks"] if r["piece"] == piece]
    same.sort(key=lambda r: -float(r["handle_y"]))
    words = {r["handle_body"]: (same.index(r), len(same)) for r in same}
    world = make_drawer_world(piece, {hb: None for hb in handles})
    print("WORLD " + json.dumps({"piece": piece, "handles": sorted(handles), "n": len(eps)}), flush=True)
    for e in eps:
        s, task = e["seed"], e["task"]
        hb = task.split("__")[2]
        rank, n = words[hb]
        world.h[hb]["words"] = XP.instruction(piece, rank, n, s)
        od = os.path.join(a.out, a.split, f"{a.variant}_dr_{piece}", f"{task}_s{s}")
        if os.path.exists(os.path.join(od, "meta.json")):
            continue
        style = "clean" if a.clean else style_of(s, S.CLEAN_SHARE)
        t0 = time.perf_counter()
        meta = collect_drawer_episode(world, s, task, a.variant, a.split, od, 0.0 if style == "clean" else a.p,
                                      a.max_perturb, a.stop_calls, a.stop_motion, style, video=s in a.video_ids)
        print("EP " + json.dumps(dict(meta, wall_total_s=round(time.perf_counter() - t0, 1))), flush=True)
    print("RUN_DONE", flush=True)
