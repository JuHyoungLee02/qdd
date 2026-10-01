"""L9 Isaac world (pod): an IsaacWorld for one arm with the L8S render rules (FX slot furniture, room backgrounds,
Poly Haven / ambientCG materials, CC0 HDRI dome, auto exposure, raised head limit, L8S arm command with the per-step
joint log) and the L9 layers: scene9 furniture + nodes, task9 episodes, vary9 light families / head pose.

World9.prepare(ep) is called before each episode by collect9 (it holds the scene, the episode spec and the light /
head draw); reset(seed, task) then builds that episode exactly like L8DWorld._reset_furniture does for L8S (hard
reset from the USD poses, lift in cfg.init_state, measured lift checked, P0, exposure, head in-view redraw)."""
from __future__ import annotations

import hashlib
import math
import os

import numpy as np

from . import arm as A
from . import vary9 as V

N_SPOTS, N_SURF, N_SUPP = 6, 3, 12
SPOT_IDS = tuple(f"s9_{i}" for i in range(N_SPOTS))
SURF_IDS = tuple(f"v9_{i}" for i in range(N_SURF))
SUPP_IDS = tuple(f"b9_{i}" for i in range(N_SUPP))
L9_TASK = "l9_task"  # the registered task id of the current episode (re-registered per episode)
MAT_ROOT = "/data/harvest/assets_l9/materials"


def register_l9_ids() -> None:
    """Invisible L9 place / support ids (spots, virtual surfaces, supports) in scene.OBJ_GEOM and the visual-only /
    virtual-place tuples (L9 processes only; module attributes are rebound, the L8 definitions are unchanged)."""
    from ..astra_motion import prompts as P
    from ..sim import scene as SC
    for i, k in enumerate(SPOT_IDS):
        SC.OBJ_GEOM[k] = dict(shape="marker", radius=0.04, height=0.002, invisible=True, half_extents=(0.04, 0.04, 0.001),
                              footprint_r=0.04)
        SC.PARK_XY[k] = (-3.0 - 0.2 * i, -3.6)
        P.OBJ_NAME[k], P.OBJ_DESC[k] = "target spot", "an unmarked spot on the surface"
    for i, k in enumerate(SURF_IDS):
        SC.OBJ_GEOM[k] = dict(shape="surface", size=(0.10, 0.10, 0.002), invisible=True,
                              half_extents=(0.05, 0.05, 0.001), footprint_r=0.07)
        SC.PARK_XY[k] = (-3.0 - 0.2 * i, -3.9)
    for i, k in enumerate(SUPP_IDS):
        SC.OBJ_GEOM[k] = dict(shape="surface", size=(0.02, 0.02, 0.002), invisible=True,
                              half_extents=(0.01, 0.01, 0.001), footprint_r=0.01)
        SC.PARK_XY[k] = (-3.0 - 0.2 * i, -4.2)
    new = tuple(k for k in SPOT_IDS + SURF_IDS + SUPP_IDS if k not in SC.X_VISUAL_ONLY)
    SC.X_VISUAL_ONLY = tuple(SC.X_VISUAL_ONLY) + new
    SC.VIRTUAL_PLACES = tuple(SC.VIRTUAL_PLACES) + tuple(k for k in SURF_IDS + SUPP_IDS if k not in SC.VIRTUAL_PLACES)


def register_pool(pool: dict) -> list:
    """Pool objects as scene bodies (before make_env): targets / clutter as objv mesh rigid bodies, containers as
    kinematic containers (with the L9 spawn scale)."""
    from ..sim import objv as OV
    from ..sim import scene as SC
    rig = {k: r for k, r in pool.items() if r["role9"] != "container"}
    con = {k: r for k, r in pool.items() if r["role9"] == "container"}
    ids = OV.register(rig) if rig else []
    if con:
        ids += OV.register_containers(con)
        for k, r in con.items():
            if r.get("spawn_scale"):
                SC.OBJ_GEOM[k]["spawn_scale"] = tuple(r["spawn_scale"])
            # L9 rows: inside.inner_floor_z is measured from the container's BOTTOM and the USD root sits at its
            # centre (root_above_bottom = h / 2), so register_containers' "inner_floor_z - root_above_bottom" (right
            # for L8S rows, root at the bottom) put the place surface h / 2 too low (pilot G1: releases pressed into
            # bowls, objects started inside containers tipped). SUPPORT_TOP is "above the bottom".
            SC.SUPPORT_TOP[k] = float(r["inside"]["inner_floor_z"])
    return sorted(ids)


def decor_parts(mesh: dict, vseed: int, furniture: list, room: bool) -> list:
    """1-2 mesh furniture pieces beside the task furniture (background: chairs, shelves, side tables ...), facing
    the robot, outside the robot keep-out box, inside the room's clear zone when a room is used. Pure."""
    from . import scene9 as S9
    if not mesh:
        return []
    rng = np.random.default_rng([int(vseed), 917])
    boxes = S9.aabb_world([p for p in furniture if p.get("role") != "room_wall"], 0.0)
    (fx0, fx1) = (min(b[0][0] for b in boxes), max(b[0][1] for b in boxes)) if boxes else (0.3, 1.0)
    (fy0, fy1) = (min(b[1][0] for b in boxes), max(b[1][1] for b in boxes)) if boxes else (-0.5, 0.5)
    names = sorted(mesh)
    out = []
    (zx0, zx1), (zy0, zy1) = S9.ZONE if room else ((-0.5, 2.5), (-2.0, 2.0))

    def dims(r):
        sx, sy, sz = r["collider_size"]
        yaw = float(r.get("yaw", -math.pi / 2))
        return abs(math.sin(yaw)) * sy + abs(math.cos(yaw)) * sx, abs(math.sin(yaw)) * sx + abs(math.cos(yaw)) * sy, sz, yaw

    for side in rng.permutation([-1, 1])[: int(rng.integers(1, 3))]:
        slack = (zy1 - fy1 - 0.05) if side > 0 else (fy0 - zy0 - 0.05)
        fit = [n for n in names if dims(mesh[n])[1] <= slack and dims(mesh[n])[0] <= zx1 - 0.2
               and not any(p["asset"] == n for p in out)]
        if not fit:
            continue
        a = fit[int(rng.integers(len(fit)))]
        r = mesh[a]
        dx, dy, sz, yaw = dims(r)
        y = (fy1 + 0.05 + dy / 2) if side > 0 else (fy0 - 0.05 - dy / 2)
        x = float(np.clip(fx0 + dx / 2 + rng.uniform(0.0, 0.3), 0.20 + dx / 2, zx1 - dx / 2))
        lo, hi = (x - dx / 2, y - dy / 2), (x + dx / 2, y + dy / 2)
        if lo[0] < 0.15 and hi[1] > -0.45 and lo[1] < 0.45:  # robot keep-out (x < 0.15, |y| < 0.45)
            continue
        if not (zx0 <= lo[0] and hi[0] <= zx1 and zy0 <= lo[1] and hi[1] <= zy1):
            continue
        out.append({"id": a, "usd": r["dst"], "asset": a, "prim": "mesh", "size": [dx, dy, sz],
                    "pos": [x, y, sz / 2], "base_pos": [x, y, 0.0], "yaw": yaw, "role": "decor",
                    "category": r.get("category"), "license": r.get("license"), "source": r.get("source")})
    return out


def make_world9(arm: str, pool: dict, rooms: dict | None = None, split: str = "train", mesh: dict | None = None):
    from ..astra_motion.world_isaac import CAMS, KEYS, NO_RENDER, PRE_RENDER, IsaacWorld
    from ..sim import scene as SC
    from ..sim.assets_x import isaac as FX

    A.check_arm(arm)
    register_l9_ids()
    ids = register_pool(pool)
    undo = FX.without_table(mesh, rooms)

    class World9(IsaacWorld):
        def __init__(self):
            from ..sim.scene import GRIP_MAX_W, make_env
            try:
                self.env = make_env(0, headless=True, cameras=CAMS, depth=True, render_interval=NO_RENDER,
                                    variant="drf", objset="x", arm=arm)
            finally:
                undo()
            env = self.env
            self.arm, self.pool_ids = arm, ids
            env.present_ids = tuple(env.present_ids) + SPOT_IDS + SURF_IDS  # Env.reset rebuilds present from these
            self.dt, self.w_open = float(env.step_dt), float(GRIP_MAX_W)
            self.table_z = float(env.table_top_z)
            self._st, self.last_obs, self.furniture_scene, self.clutter_scene = None, None, None, None
            self.ep, self.scene9, self.light = None, None, None
            self._head_limit()

        # ------------------------------------------------------------------ setup helpers
        def _head_limit(self, upper_deg: float = 57.0):
            import omni.usd
            from pxr import Usd
            stage = omni.usd.get_context().get_stage()
            for p in Usd.PrimRange(stage.GetPrimAtPath("/World/envs/env_0/Robot")):
                if p.GetName() == "head_joint1":
                    a = p.GetAttribute("physics:upperLimit")
                    if a and a.Get() is not None and a.Get() < upper_deg:
                        a.Set(upper_deg)

        def _arm_vel_limit(self):
            import torch

            from ..teach_l8d.clutter_x import ARM_VMAX_STEP
            rob = self.env.robot
            jp = A.joint_prefix(arm)
            ids_ = [i for i, n in enumerate(rob.joint_names) if n.startswith(jp)]
            fn = getattr(rob, "write_joint_velocity_limit_to_sim", None)
            if fn is not None:
                fn(torch.full((1, len(ids_)), ARM_VMAX_STEP / float(self.dt), device=rob.device), joint_ids=ids_)

        def _materials(self):
            if hasattr(self, "_mats"):
                return self._mats
            import omni.usd

            from ..sim.assets_x import materials as M
            from ..teach_l8d.clutter_x import material_ok
            stage = omni.usd.get_context().get_stage()
            import json
            tab = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "materials_l9.json")))
            cat = {k: r for k, r in M.usable(tab["materials"]).items() if material_ok(k, r)}
            paths = {}
            first = M.pick(cat, "furniture", 0)
            for i in range(FX.N_SLOTS):
                prim = stage.GetPrimAtPath(FX._slot_path(i))
                if not prim.IsValid():
                    continue
                mp = f"/World/Looks/l9_{i}"
                M.bind(prim, M.author(stage, mp, first, root=MAT_ROOT))
                paths[i] = mp
            hdrs = sorted(k for k, r in cat.items() if r["role"] == "env" and M.split_of(k) == split)
            self._mats = (cat, paths, hdrs)
            return self._mats

        def _retexture(self, seed: int, parts: list) -> dict:
            """One material per used slot by role (furniture / wall / fabric) -> {slot: material id}."""
            import omni.usd

            from ..sim.assets_x import materials as M
            cat, paths, _ = self._materials()
            stage = omni.usd.get_context().get_stage()
            used = {}
            for i, mid in enumerate(self.material_ids(seed, parts)):
                M.retexture(stage, paths[i], cat[mid], root=MAT_ROOT)
                used[i] = mid
            return used

        def _place_room(self, seed: int, parts: list, family: str):
            import omni.usd

            from ..sim.assets_x.isaac import ROOM_PARK, yaw_quat
            from ..sim.randomize import _set_pose
            name = self.room_name(seed, family, parts)
            if name is None:
                return None
            names = sorted(rooms)
            stage = omni.usd.get_context().get_stage()
            for j, rn in enumerate(names):
                prim = stage.GetPrimAtPath(f"/World/envs/env_0/FR_{rn}")
                if rn == name:
                    r = rooms[rn]
                    _set_pose(prim, (r["pos"][0], r["pos"][1], r["pos"][2] + 0.001), yaw_quat(r["yaw"]))
                else:
                    _set_pose(prim, (ROOM_PARK[0] - 12.0 * j, ROOM_PARK[1], ROOM_PARK[2]), (1.0, 0.0, 0.0, 0.0))
            r = rooms[name]
            return {"name": r.get("name0", name), "kind": r.get("kind"), "license": r.get("license"), "source": r.get("source")}

        # ------------------------------------------------------------------ episode
        def prepare(self, scene: dict, ep: dict, light_family: str, head: dict | None = None, vseed: int | None = None):
            """The next episode: scene, task9 episode, light family, head pose and the visual seed (room / HDRI /
            materials are drawn from vseed, the same draw collect9 hashed for the combination ledger)."""
            self.scene9, self.ep, self.light_family = scene, ep, light_family
            self._head0, self.vseed = head, vseed

        def room_name(self, vseed: int, family: str, parts: list):
            from . import scene9 as S9
            if not rooms or not S9.in_zone([p for p in parts if p["role"] != "room_wall"], 0.0):
                return None
            want = S9.ROOM_KINDS.get(family, ())
            names = sorted(rooms)
            pref = [n for n in names if any(w in str(rooms[n].get("kind", "")) for w in want)] or names
            h = int(hashlib.sha256(f"l9-room:{int(vseed)}".encode()).hexdigest()[:8], 16)
            return pref[h % len(pref)]

        def hdr_name(self, vseed: int) -> str:
            hdrs = self._materials()[2]
            return hdrs[int(hashlib.sha256(f"l9-hdr:{int(vseed)}".encode()).hexdigest()[:8], 16) % len(hdrs)]

        def material_ids(self, vseed: int, parts: list) -> list:
            from ..sim.assets_x import materials as M
            cat, paths, _ = self._materials()
            out = []
            for i, p in enumerate(parts):
                if i not in paths:
                    continue
                role = {"room_wall": "wall", "wall": "wall", "mat": "fabric", "sofa": "fabric",
                        "chair": "furniture"}.get(p.get("role"), "furniture")
                try:
                    rec = M.pick(cat, role, int(vseed) * 131 + i, split)
                except ValueError:
                    rec = M.pick(cat, "furniture", int(vseed) * 131 + i, split)
                out.append(rec["id"])
            return out

        def reset(self, seed, task=L9_TASK):
            from ..sim import scene as SC
            from ..sim.perturb import perturb
            from ..sim.planner import OraclePlanner
            from ..teach_l8d import fx
            from . import scene9 as S9
            from . import task9 as T9
            env, sc, ep = self.env, self.scene9, self.ep
            rob = env.robot
            seed = int(self.vseed if getattr(self, "vseed", None) is not None else seed)  # the drawn visual seed
            parts = [p for p in sc["furniture"]]
            room = self._place_room(seed, parts, sc["family"])
            if room is not None:
                parts = [p for p in parts if p["role"] != "room_wall"]
            decor = decor_parts(mesh, seed, parts, room is not None)
            FX.author_scene(env, {"furniture": parts + decor, "walls": [], "room": None}, mesh, None)
            mats = self._retexture(seed, parts)
            if room is None:
                from ..teach_l8d.xart import hide_ground_grid
                hide_ground_grid()
            # lift + head (cfg.init_state too: the hard reset re-reads it, P131)
            li = rob.joint_names.index("lift_joint")
            env.lift = float(sc["lift"])
            head = dict(self._head0 or V.head_pose(seed))
            for jn, v in (("lift_joint", env.lift), ("head_joint1", head["tilt"]), ("head_joint2", head["pan"])):
                if jn in rob.joint_names:
                    rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                    rob.cfg.init_state.joint_pos[jn] = v
            tz = float(ep["table_z"])
            env.table_top_z, self.table_z = tz, tz
            SC._LAYOUT["table_z"] = tz
            # layout: objects (+ supports on other heights), spots, surfaces
            lay, sup_i = {}, 0
            nodes = {n["id"]: n for n in sc["nodes"]}
            for k, o in ep["objects"].items():
                yaw = self._obj_yaw(k)
                if o.get("support"):
                    lay[k] = (o["xy"][0], o["xy"][1], yaw, o["support"])
                    continue
                top = nodes[o["node"]]["top_z"]
                if abs(top - tz) > 1e-4:
                    b = SUPP_IDS[sup_i]
                    sup_i += 1
                    SC.SUPPORT_TOP[b] = top - tz
                    lay[b] = (o["xy"][0], o["xy"][1], 0.0)
                    lay[k] = (o["xy"][0], o["xy"][1], yaw, b)
                else:
                    lay[k] = (o["xy"][0], o["xy"][1], yaw)
            for k, s in ep["spots"].items():
                lay[k] = (s["xy"][0], s["xy"][1], 0.0)
                SC.OBJ_GEOM[k]["rule_text"] = s["rule_text"]
            from ..astra_motion import prompts as P
            for k, s in ep["surfaces"].items():
                h = float(s["half"])
                env.set_virtual_surface(k, float(s["top"]), ((s["xy"][0] - h, s["xy"][0] + h),
                                                             (s["xy"][1] - h, s["xy"][1] + h)))
                lay[k] = (s["xy"][0], s["xy"][1], 0.0)
                SC.OBJ_GEOM[k]["rule_text"] = s["rule_text"]
                P.OBJ_NAME[k] = s.get("label") or s["name"]
                P.OBJ_DESC[k] = f"a {s['name']} of the furniture"
            for k in list(ep.get("clutter", {})):
                c = ep["clutter"][k]
                top = nodes[c["node"]]["top_z"]
                if abs(top - tz) > 1e-4 and sup_i < N_SUPP:
                    b = SUPP_IDS[sup_i]
                    sup_i += 1
                    SC.SUPPORT_TOP[b] = top - tz
                    lay[b] = (c["xy"][0], c["xy"][1], 0.0)
                    lay[k] = (c["xy"][0], c["xy"][1], float(c.get("yaw", 0.0)), b)
                elif abs(top - tz) <= 1e-4:
                    lay[k] = (c["xy"][0], c["xy"][1], float(c.get("yaw", 0.0)))
            env.layout = lay
            SC._LAYOUT["layout"] = lay
            SC._LAYOUT["rand"] = None
            env.task = task
            # lighting (drf structure + the L9 family) and the HDRI
            self._visuals(seed, tz)
            env.reset()
            fx.check_lift(env.lift, float(rob.data.joint_pos[0, li]))  # SkipScene past 4 cm (P131)
            perturb(env, "P0", seed)
            for _ in range(PRE_RENDER):
                env.env.sim.render()
            self.iso = self._auto_exposure()
            # head: every episode moves the neck; redraw while a task object / destination leaves the view
            att = 0
            while not self._head_sees() and att < V.HEAD_TRIES:
                att += 1
                head = V.head_pose(seed, att) if att < V.HEAD_TRIES else V.head_default()
                for jn, v in (("head_joint1", head["tilt"]), ("head_joint2", head["pan"])):
                    rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                    rob.cfg.init_state.joint_pos[jn] = v
                env.reset()
                perturb(env, "P0", seed)
                for _ in range(PRE_RENDER):
                    env.env.sim.render()
            self.head = head
            self.pl = OraclePlanner(env)
            if arm == "left":  # mirrored top-down grasp orientation (fingers still close along world x)
                q = np.asarray(self.pl.goal_quat, float)
                yaw = 2.0 * math.atan2(q[3], q[0])
                self.pl.goal_quat = np.array(A.yaw_quat(A.goal_yaw(arm, yaw)))
            self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
            self.quat0 = np.asarray(self.pl.goal_quat, float)
            self.w_close = float(self.pl.w_close)
            self._qcmd = None
            arm_start = self._preroll_arm(tz)
            self._jlog, self._blog, self._alog, self._tlog = [], [], [], []
            self._st = None
            self.furniture_scene = {"kind": f"l9_{sc['family']}", "family": sc["family"], "rule": sc["rule"],
                                    "robot_pose": sc["robot_pose"], "lift": sc["lift"], "room": room,
                                    "materials": mats, "hdr": self.hdr, "light_family": self.light_family,
                                    "head": head, "iso": self.iso, "arm_start": arm_start, "params": sc.get("params"),
                                    "surface": nodes[ep["main"]]["kind"],
                                    "decor": [{"asset": mesh[p["asset"]].get("name0", p["asset"]),
                                               "category": p.get("category")} for p in decor]}
            self.clutter_scene = {"n": len(ep.get("clutter", {})), "ids": sorted(ep.get("clutter", {}))}

        def _obj_yaw(self, k):
            from ..sim import objv as OV
            from ..sim import scene as SC
            g = SC.OBJ_GEOM[k]
            if g.get("kinematic"):
                h = int(hashlib.sha256(f"l9-yaw:{k}".encode()).hexdigest()[:4], 16) / 65535.0
                return float((h - 0.5) * math.pi)
            return float(OV.grasp_yaw_of(g))

        def _visuals(self, seed, tz):
            from ..sim import randomize as R
            from ..sim.assets_x import materials as M
            cat, _, hdrs = self._materials()
            # (make_env variant drf already ran randomize.setup_visuals: dome, key / fill lights)
            h = self.hdr_name(seed)
            m = R.sample_randomization(seed, "drf", self.env.layout)
            m["distractors"] = []
            if m.get("hdr"):
                m["hdr"]["file"] = os.path.join(MAT_ROOT, cat[h]["files"]["hdr"])
                m["hdr"]["name"] = h
            common = R.load_pools(R.pools_path("drf"))["common"]
            target = (0.46, A.side(arm) * -0.23, tz)
            m = V.light_meta(m, self.light_family, seed, target, common)
            self.env.randomization = m  # applied by Env.reset (variant drf)
            self.hdr = h

        def _auto_exposure(self):
            from ..teach_l8d.xart import auto_exposure
            return auto_exposure(self)

        def _head_sees(self, margin: float = 0.05) -> bool:
            from ..astra_motion import geometry as G
            cam = self._cam("cam_head", "head")
            pts = []
            for a, p, _ in self.ep["steps"]:
                for k in (a, p):
                    pos = np.asarray(self.env.object_pose(k)[0], float) - self.env.scene.env_origins[0].cpu().numpy()
                    pts.append(pos)
            for p in pts:
                u, v, z = G.project(cam, p)
                if not (z > 0 and margin * cam.W <= u <= (1 - margin) * cam.W and margin * cam.H <= v <= (1 - margin) * cam.H):
                    return False
            return True

        def _preroll_arm(self, tz, steps: int = 200) -> dict:
            from ..teach_l8d.clutter_x import set_arm_inertia
            set_arm_inertia(self.env.robot, A.LEFT_HEAD_INERTIA)  # right (change 27) + left + head (later_problems 11)
            # (no PhysX joint velocity cap: L8S defines _arm_vel_limit but never calls it -- change 25's command
            # rate limit replaced it; with the cap the L9 gate froze the arm mid-carry, diag 2026-10-01)
            s = A.arm_start(arm)
            goal = np.array([s[0], s[1], tz + s[2]])
            for _ in range(steps):
                if np.linalg.norm(np.asarray(self.status()["tcp"], float) - goal) < 0.01:
                    break
                self.step(goal, self.w_open, None)
            for _ in range(10):
                self.step(goal, self.w_open, None)
            jp = A.joint_prefix(arm)
            return {"tcp": [round(float(v), 4) for v in self.status()["tcp"]],
                    "q_arm": [round(float(v), 4) for v, n in zip(self.env.robot.data.joint_pos[0].cpu().numpy(),
                                                                 self.env.robot.joint_names) if n.startswith(jp)]}

        def step(self, cmd_pos, width: float, quat=None) -> None:
            from ..teach_l8d.xart import l8s_step_band
            l8s_step_band(self, cmd_pos, width, quat)
            if not hasattr(self, "_tlog"):
                return
            d, ids_ = self.env.robot.data, self.env.arm_ids
            self._tlog.append(np.concatenate([d.joint_pos_target[0, ids_].cpu().numpy(), d.applied_torque[0, ids_].cpu().numpy(),
                                              d.computed_torque[0, ids_].cpu().numpy(), d.joint_vel[0, ids_].cpu().numpy()]).astype(np.float32))
            w, x, y, z = (float(v) for v in d.root_quat_w[0].cpu().numpy())
            self._blog.append([*(float(v) for v in d.root_pos_w[0].cpu().numpy()),
                               math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))])

        # ------------------------------------------------------------------ observation (the used arm's wrist)
        def observe(self, depth: bool = False):
            obs = IsaacWorld.observe(self)
            if arm == "left":  # "wrist" = the used arm's wrist camera (the right one moves to "wrist_other")
                obs.rgb["wrist"], obs.rgb["wrist_left"] = obs.rgb["wrist_left"], obs.rgb["wrist"]
                obs.cams["wrist"], obs.cams["wrist_left"] = obs.cams["wrist_left"], obs.cams["wrist"]
            if depth:
                obs.depth = {"head": self.env.camera_depth("cam_head").copy()}
            self.last_obs = obs
            return obs

        def frame(self) -> dict:
            self._render()
            w = A.wrist_camera(arm)
            return {"head": self.env.camera_rgb("cam_head"), "wrist": self.env.camera_rgb(w),
                    "wrist_cam": self._cam(w, "wrist")}

        # ------------------------------------------------------------------ task info / status
        def _status_from(self, pl):
            st = IsaacWorld._status_from(self, pl)
            from ..sim.scene import OBJ_GEOM
            from ..predicates import _tilt_deg
            from ..teach_l8d.clutter_x import ROLLING, UPRIGHT_INTO_DEG
            info = self.task_info()
            tgt = info["tgt"]
            key = f"upright({tgt})"
            if key not in st["pred"]:
                return st
            row = OBJ_GEOM.get(tgt, {})
            name = str(row.get("name", ""))
            if any(w in name.split() for w in ROLLING):
                new = True
            elif OBJ_GEOM.get(info["place"], {}).get("place_kind") == "into":
                new = _tilt_deg(np.asarray(self.env.object_pose(tgt)[1], float)) <= UPRIGHT_INTO_DEG
            else:
                return st
            return st if st["pred"][key] is new else dict(st, pred={**st["pred"], key: new})

        def task_info(self):
            from ..sim.tasks import X_STEPS
            from ..teach_l8d.xlabels import x_info
            return self.step_info(0) if self.env.task in X_STEPS else x_info(self.env, IsaacWorld.task_info(self))

        def step_info(self, k: int):
            from ..sim.tasks import X_STEPS
            from ..teach_l8d.multistep import step_info
            from ..teach_l8d.xlabels import x_info
            return x_info(self.env, step_info(IsaacWorld.task_info(self), X_STEPS[self.env.task], k))

    return World9()
