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


def decor_parts(mesh: dict, vseed: int, furniture: list, room: bool, arm: str | None = None) -> list:
    """1-2 mesh furniture pieces beside the task furniture (background: chairs, shelves, side tables ...), facing
    the robot, outside the robot keep-out box, inside the room's clear zone when a room is used; with `arm` (L9 v2)
    also 0-3 tabletop pieces (rows kind "tabletop": Poly Haven props / plants / lamps ...) on top parts away from
    the arm band. Pure."""
    from . import scene9 as S9
    if not mesh:
        return []
    floor_mesh = {k: r for k, r in mesh.items() if r.get("kind") != "tabletop"}
    top = tabletop_parts({k: r for k, r in mesh.items() if r.get("kind") == "tabletop"}, vseed, furniture, arm) \
        if arm is not None else []
    mesh = floor_mesh
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
    return out + top


TOP_DECOR_N = (0, 3)
TOP_DECOR_MAX = (0.35, 0.35, 0.45)  # footprint x / y, height (m) of a tabletop piece


def tabletop_parts(mesh: dict, vseed: int, furniture: list, arm: str) -> list:
    """0-3 render-only tabletop pieces on cuboid top parts (world frame), outside the arm's band (|y - y_arm| > 0.28
    or x > 0.72: the task objects and the arm stay inside it), not overlapping other parts above the top. Pure."""
    from . import arm as AR
    if not mesh:
        return []
    rng = np.random.default_rng([int(vseed), 919])
    yb = AR.side(arm) * -0.23
    tops = [p for p in furniture if p.get("usd") is None and p.get("role") in ("top", "fixture") and p["size"][0] >= 0.2
            and p["size"][1] >= 0.2 and not p.get("pitch")]
    names = sorted(k for k, r in mesh.items() if all(v <= m for v, m in zip(r["collider_size"], TOP_DECOR_MAX)))
    out = []
    for _ in range(int(rng.integers(TOP_DECOR_N[0], TOP_DECOR_N[1] + 1)) * 6):
        if len(out) >= TOP_DECOR_N[1] or not tops or not names:
            break
        p = tops[int(rng.integers(len(tops)))]
        a = names[int(rng.integers(len(names)))]
        if any(o["asset"] == a for o in out):
            continue
        sx, sy, sz = mesh[a]["collider_size"]
        yaw = float(rng.uniform(-math.pi, math.pi))
        dx = abs(math.cos(yaw)) * sx + abs(math.sin(yaw)) * sy
        dy = abs(math.sin(yaw)) * sx + abs(math.cos(yaw)) * sy
        (bx0, bx1), (by0, by1) = _world_box(p)
        if bx1 - bx0 < dx + 0.04 or by1 - by0 < dy + 0.04:
            continue
        x, y = rng.uniform(bx0 + dx / 2 + 0.02, bx1 - dx / 2 - 0.02), rng.uniform(by0 + dy / 2 + 0.02, by1 - dy / 2 - 0.02)
        if not (x - dx / 2 > 0.72 or abs(y - yb) - dy / 2 > 0.28):
            continue
        ztop = p["pos"][2] + p["size"][2] / 2
        clash = False
        for q in furniture + out:
            if q is p:
                continue
            (qx0, qx1), (qy0, qy1) = _world_box(q)
            qz0 = q["pos"][2] - q["size"][2] / 2
            qz1 = q["pos"][2] + q["size"][2] / 2
            if qz1 > ztop + 0.002 and qz0 < ztop + sz and qx0 < x + dx / 2 + 0.02 and qx1 > x - dx / 2 - 0.02 \
                    and qy0 < y + dy / 2 + 0.02 and qy1 > y - dy / 2 - 0.02:
                clash = True
                break
        if clash:
            continue
        r = mesh[a]
        out.append({"id": a, "usd": r["dst"], "asset": a, "prim": "mesh", "size": [dx, dy, sz],
                    "pos": [x, y, ztop + sz / 2], "base_pos": [x, y, ztop], "yaw": yaw, "role": "decor_top",
                    "category": r.get("category"), "license": r.get("license"), "source": r.get("source")})
    return out


def _world_box(p: dict) -> tuple:
    """World xy AABB of a part (cuboid / mesh with yaw)."""
    yaw = float(p.get("yaw", 0.0))
    sx, sy = p["size"][0], p["size"][1]
    dx = abs(math.cos(yaw)) * sx + abs(math.sin(yaw)) * sy
    dy = abs(math.sin(yaw)) * sx + abs(math.cos(yaw)) * sy
    return (p["pos"][0] - dx / 2, p["pos"][0] + dx / 2), (p["pos"][1] - dy / 2, p["pos"][1] + dy / 2)


MATERIAL_ROLE = {"room_wall": "wall", "wall": "wall", "mat": "fabric", "sofa": "fabric", "chair": "furniture",
                 "ground": "floor"}  # other part roles: furniture (props: furniture or fabric by the draw)


def material_pool(cat: dict, role: str, split: str, setting: str | None = None) -> list:
    """Sorted material ids of a role / split (materials.split_of); floors by setting: "outdoor" = ground-like
    floors (v1 Poly Haven floors not tagged indoor + v2 outdoor floors), else indoor floors."""
    from ..sim.assets_x import materials as M
    ids = []
    for k, r in cat.items():
        if r["role"] != role or M.split_of(k) != split:
            continue
        if role == "floor" and setting is not None:
            out = r.get("setting") == "outdoor" or (r.get("setting") is None and not r.get("indoor", True))
            if out != (setting == "outdoor"):
                continue
        ids.append(k)
    return sorted(ids)


def make_world9(arm: str, pool: dict, rooms: dict | None = None, split: str = "train", mesh: dict | None = None,
                robot: str = "ffw_sg2", hcam: str | None = None):
    """robot: robot9 profile ("ffw_sg2" = the AI Worker, unchanged; "franka_mast"). hcam (spec §9.3, E-HCAM8):
    None = the standard head camera every episode (unchanged); "coin" = hcam9.coin(seed) picks std / rand per seed;
    "rand" / "hold" = every episode. The Franka mast camera is drawn per episode whatever hcam says."""
    from ..astra_motion.world_isaac import CAMS, KEYS, NO_RENDER, PRE_RENDER, IsaacWorld, WORLD_CONV_TO_OPTICAL
    from ..sim import scene as SC
    from ..sim.assets_x import isaac as FX
    from . import hcam9 as HC
    from . import robot9 as R9

    A.check_arm(arm)
    if robot not in R9.PROFILES:
        raise ValueError(f"robot {robot!r}")
    if hcam not in (None, "coin", "rand", "hold"):
        raise ValueError(f"hcam {hcam!r}")
    franka = robot == "franka_mast"
    if franka and arm != "right":
        raise NotImplementedError("franka_mast: right-arm rows only (spec §9.2)")
    cams = R9.CAMERAS if franka else CAMS
    keys = {"cam_head": "head", "cam_wrist_right": "wrist", "cam_wrist_left": "wrist_left"}
    register_l9_ids()
    ids = register_pool(pool)
    if mesh is not None:  # L9 v2: Poly Haven tabletop pieces join the process's mesh slots (render only)
        from . import assets9 as A9
        k = int(hashlib.sha256("|".join(sorted(mesh)).encode()).hexdigest()[:6], 16)
        mesh = {**mesh, **A9.tabletop_for(k, split=split)}
    undo = FX.without_table(mesh, rooms)

    class World9(IsaacWorld):
        def __init__(self):
            from ..sim.scene import GRIP_MAX_W, make_env
            try:
                self.env = make_env(0, headless=True, cameras=cams, depth=True, render_interval=NO_RENDER,
                                    variant="drf", objset="x", arm=arm, **({"robot": robot} if franka else {}))
            finally:
                undo()
            env = self.env
            self.arm, self.pool_ids = arm, ids
            env.present_ids = tuple(env.present_ids) + SPOT_IDS + SURF_IDS  # Env.reset rebuilds present from these
            self.dt, self.w_open = float(env.step_dt), float(R9.GRIP_MAX_W if franka else GRIP_MAX_W)
            self.robot_profile, self.hcam_mode, self.cam_names = robot, hcam, cams
            self.joint_prefixes = ("panda_joint", "panda_finger") if franka else None
            self._mounts, self._K = {}, {}  # per-episode camera mounts / intrinsics written to the stage
            self.head_cam = None
            self.table_z = float(env.table_top_z)
            self._st, self.last_obs, self.furniture_scene, self.clutter_scene = None, None, None, None
            self.ep, self.scene9, self.light = None, None, None
            if not franka:
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
            here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9")
            tab = json.load(open(os.path.join(here, "materials_l9.json")))
            raw = dict(tab["materials"])
            if os.path.exists(os.path.join(here, "materials_l9v2.json")):  # L9 v2: absolute file paths
                raw.update(json.load(open(os.path.join(here, "materials_l9v2.json")))["materials"])
            cat = {k: r for k, r in M.usable(raw).items() if material_ok(k, r)}
            # outdoor ground (picnic / potting families): the ground-like floors usable() drops
            cat.update({k: r for k, r in raw.items() if r.get("complete") and r["role"] == "floor" and k not in cat
                        and (r.get("setting") == "outdoor" or not r.get("indoor", True))})
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
            self._pools = {}
            return self._mats

        def _retexture(self, seed: int, parts: list) -> dict:
            """One material per used slot by role (furniture / wall / fabric / floor) + the L9 v2 appearance draw
            (vary9.material_look: UV scale, diffuse tint) -> {slot: material id}; self.mat_looks = the draws."""
            import omni.usd
            from pxr import Gf, Sdf, UsdShade

            from ..sim.assets_x import materials as M
            cat, paths, _ = self._materials()
            stage = omni.usd.get_context().get_stage()
            used, looks = {}, {}
            for i, mid in enumerate(self.material_ids(seed, parts)):
                lk = V.material_look(seed, i, self._role_of(parts[i], seed, i))
                M.retexture(stage, paths[i], cat[mid], root=MAT_ROOT, uv_scale=(lk["uv"], lk["uv"]))
                sh = UsdShade.Shader.Get(stage, paths[i] + "/diff")
                if sh:
                    inp = sh.GetInput("scale") or sh.CreateInput("scale", Sdf.ValueTypeNames.Float4)
                    inp.Set(Gf.Vec4f(*[float(c) for c in lk["tint"]], 1.0))
                used[i], looks[i] = mid, lk
            self.mat_looks = looks
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
            if family in S9.OUTDOOR:  # L9 v2: outdoor families have no room (outdoor HDRI + ground slab)
                return None
            if not rooms or not S9.in_zone([p for p in parts if p["role"] not in ("room_wall", "ground")], 0.0):
                return None
            want = S9.ROOM_KINDS.get(family, ())
            names = sorted(rooms)
            pref = [n for n in names if any(w in str(rooms[n].get("kind", "")) for w in want)] or names
            h = int(hashlib.sha256(f"l9-room:{int(vseed)}".encode()).hexdigest()[:8], 16)
            return pref[h % len(pref)]

        def hdr_name(self, vseed: int, family: str | None = None) -> str:
            """Seeded HDRI; outdoor families (scene9.OUTDOOR) draw from the outdoor HDRIs only."""
            from . import scene9 as S9
            cat, _, hdrs = self._materials()
            if family in S9.OUTDOOR:
                hdrs = [h for h in hdrs if cat[h].get("setting") == "outdoor"] or hdrs
            return hdrs[int(hashlib.sha256(f"l9-hdr:{int(vseed)}".encode()).hexdigest()[:8], 16) % len(hdrs)]

        def _role_of(self, p: dict, vseed: int, i: int) -> str:
            r = MATERIAL_ROLE.get(p.get("role"))
            if r is None and p.get("role") == "prop":
                r = "fabric" if (int(vseed) * 131 + i) % 3 == 0 else "furniture"
            return r or "furniture"

        def material_ids(self, vseed: int, parts: list) -> list:
            """One material per used slot: the part's role (MATERIAL_ROLE), the ground slab by its setting
            (outdoor ground / indoor floor), seeded by (visual seed, slot)."""
            cat, paths, _ = self._materials()
            out = []
            for i, p in enumerate(parts):
                if i not in paths:
                    continue
                role = self._role_of(p, vseed, i)
                setting = p.get("setting", "indoor") if role == "floor" else None
                key = (role, setting)
                if key not in self._pools:
                    self._pools[key] = material_pool(cat, role, split, setting) or material_pool(cat, "furniture", split)
                ids = self._pools[key]
                h = int(hashlib.sha256(f"{role}:{int(vseed) * 131 + i}".encode()).hexdigest()[:8], 16)
                out.append(ids[h % len(ids)])
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
            decor = decor_parts(mesh, seed, parts, room is not None, arm=arm)
            FX.author_scene(env, {"furniture": parts + decor, "walls": [], "room": None}, mesh, None)
            self._pitch_parts(parts)
            mats = self._retexture(seed, parts)
            if room is None:
                from ..teach_l8d.xart import hide_ground_grid
                hide_ground_grid()
            tz = float(ep["table_z"])
            if franka:  # base on the stand: main work surface - U[0, 0.12] m (spec §9.2), no lift / neck
                self._place_base(seed, tz)
                head = {"tilt": None, "pan": None, "random": False}
            else:
                # lift + head (cfg.init_state too: the hard reset re-reads it, P131)
                li = rob.joint_names.index("lift_joint")
                env.lift = float(sc["lift"])
                look = V.look_of(ep, sc)  # L9 v2: high / low places tilt the gaze up / down
                head = dict(self._head0 or V.head_pose(seed)) if look == "std" else V.head_pose(seed, 0, look)
                for jn, v in (("lift_joint", env.lift), ("head_joint1", head["tilt"]), ("head_joint2", head["pan"])):
                    if jn in rob.joint_names:
                        rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                        rob.cfg.init_state.joint_pos[jn] = v
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
            if franka:
                self._check_base()
            else:
                fx.check_lift(env.lift, float(rob.data.joint_pos[0, li]))  # SkipScene past 4 cm (P131)
            perturb(env, "P0", seed)
            self._apply_head_cam(seed, tz, 0)  # std (no stage write when already std) / drawn geometry
            for _ in range(PRE_RENDER):
                env.env.sim.render()
            self.iso = self._auto_exposure()
            # head: every episode moves the neck; redraw while a task object / destination leaves the view
            att = 0
            while not self._head_sees() and att < V.HEAD_TRIES:
                att += 1
                if not franka:
                    head = V.head_pose(seed, att, V.look_of(ep, sc)) if att < V.HEAD_TRIES else V.head_default()
                    for jn, v in (("head_joint1", head["tilt"]), ("head_joint2", head["pan"])):
                        rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                        rob.cfg.init_state.joint_pos[jn] = v
                    env.reset()
                    perturb(env, "P0", seed)
                self._apply_head_cam(seed, tz, att)
                for _ in range(PRE_RENDER):
                    env.env.sim.render()
            self.head = head
            self.pl = OraclePlanner(env)
            if franka:
                self.pl.w_open = self.w_open
                self.pl.cmd_w = min(float(self.pl.cmd_w), self.w_open)
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
                                    "robot": robot, "head_cam": self.head_cam, "base": getattr(self, "base", None),
                                    "surface": nodes[ep["main"]]["kind"],
                                    "decor": [{"asset": mesh[p["asset"]].get("name0", p["asset"]),
                                               "category": p.get("category"), "role": p.get("role")} for p in decor],
                                    "env_axes": self._env_axes(sc, room, mats, decor, head)}
            self.clutter_scene = {"n": len(ep.get("clutter", {})), "ids": sorted(ep.get("clutter", {}))}

        def _pitch_parts(self, parts: list) -> None:
            """L9 v2 inclined boards: cuboid parts with a "pitch" (rad, about the part's own y axis after its yaw)
            get that orientation on their slot prim (collider + visual; physical from the next hard reset)."""
            import omni.usd

            from ..sim.randomize import _set_pose
            stage = omni.usd.get_context().get_stage()
            cub = [p for p in parts if p.get("usd") is None]
            for i, p in enumerate(cub[:FX.N_SLOTS]):
                if not p.get("pitch"):
                    continue
                cy, sy = math.cos(p.get("yaw", 0.0) / 2), math.sin(p.get("yaw", 0.0) / 2)
                cp, sp = math.cos(p["pitch"] / 2), math.sin(p["pitch"] / 2)
                q = (cy * cp, -sy * sp, cy * sp, sy * cp)  # q_yaw(z) * q_pitch(y), wxyz
                _set_pose(stage.GetPrimAtPath(FX._slot_path(i)), tuple(p["pos"]), q)

        def _env_axes(self, sc: dict, room, mats: dict, decor: list, head: dict) -> dict:
            """Spec §12.11 principle 7: the environment axis values of the episode (reduced-diversity subsets are cut
            from meta): family / layout / density / props / fixtures / place classes / room kind / materials (+ UV,
            tint) / HDRI setting / light family / decor / head look."""
            from . import scene9 as S9
            cat = self._materials()[0]
            pr = sc.get("params") or {}
            return {"family": sc["family"], "rule": sc["rule"], "density": pr.get("density"), "props": pr.get("props"),
                    "fixtures": pr.get("fixtures"), "n_parts": len(sc.get("parts_s") or []),
                    "place_classes": sorted({n.get("place_class", "desk") for n in sc["nodes"]}),
                    "node_kinds": sorted({n["kind"] for n in sc["nodes"]}),
                    "room_kind": None if room is None else room.get("kind"), "outdoor": sc["family"] in S9.OUTDOOR,
                    "material_roles": {str(i): cat[m]["role"] for i, m in mats.items()},
                    "material_looks": getattr(self, "mat_looks", {}), "hdr_setting": cat.get(self.hdr, {}).get("setting"),
                    "light_family": self.light_family, "decor_n": sum(p.get("role") == "decor" for p in decor),
                    "decor_top_n": sum(p.get("role") == "decor_top" for p in decor), "head_look": head.get("look", "std"),
                    "split": split}

        # ------------------------------------------------------------------ robot base (Franka) / head camera
        def _place_base(self, seed: int, tz: float) -> None:
            """Franka: base origin over the AI Worker right shoulder's xy, top = tz - U[0, 0.12] m; the stand box
            under it. Written to the default root state, cfg.init_state and the USD (the hard reset rebuilds from
            USD)."""
            import omni.usd
            import torch

            from ..sim.randomize import _set_pose
            rng = np.random.default_rng([int(seed), 991])
            z = float(tz - rng.uniform(*R9.BASE_DROP))
            pos = (R9.BASE_X, R9.BASE_Y_RIGHT, z)
            rob = self.env.robot
            rob.data.default_root_state[0, :3] = torch.tensor(pos, dtype=rob.data.default_root_state.dtype,
                                                              device=rob.data.default_root_state.device)
            rob.cfg.init_state.pos = pos
            stage = omni.usd.get_context().get_stage()
            _set_pose(stage.GetPrimAtPath("/World/envs/env_0/Robot"), pos, (1.0, 0.0, 0.0, 0.0))
            _set_pose(stage.GetPrimAtPath("/World/envs/env_0/Stand"), (pos[0], pos[1], z - 1.0), (1.0, 0.0, 0.0, 0.0))
            self.base = {"pos": [round(v, 4) for v in pos], "drop_m": round(tz - z, 4), "stand_xy_m": R9.STAND_XY}

        def _check_base(self, tol: float = 0.01) -> None:
            from ..teach_l8d.fx import SkipScene
            got = self.env.robot.data.root_pos_w[0].cpu().numpy() - self.env.scene.env_origins[0].cpu().numpy()
            err = float(np.linalg.norm(got - np.asarray(self.base["pos"])))
            self.base["measured"] = [round(float(v), 4) for v in got]
            if err > tol:
                raise SkipScene(f"franka base {err * 1e3:.0f} mm off its pose")

        def _cam_prim(self, name: str) -> str:
            if franka:
                return f"/World/envs/env_0/Robot/{R9.CAM_SPECS[name]['parent']}/{name}"
            from ..sim.scene import load_realcam
            return f"/World/envs/env_0/Robot/ffw_sg2_follower/{load_realcam().CAMERA_SPECS[name]['prim']}"

        def _parent_pose(self, name: str):
            rob = self.env.robot
            par = R9.CAM_SPECS[name]["parent"] if franka else self._realcam().CAMERA_SPECS[name]["parent"]
            bi = rob.body_names.index(par)
            return (rob.data.body_pos_w[0, bi].cpu().numpy().astype(float),  # as world_isaac.camera_pose (env 0)
                    rob.data.body_quat_w[0, bi].cpu().numpy().astype(float))

        def _realcam(self):
            from ..sim.scene import load_realcam
            return load_realcam()

        def _default_mount(self, name: str) -> list:
            return R9.mount_of(name) if franka else list(self._realcam().mount_transform(name))

        def _write_mount(self, name: str, mount) -> None:
            """Camera prim local pose (parent link frame) = mount [t, q world convention]; no write if unchanged."""
            mount = [float(v) for v in mount]
            cur = self._mounts.get(name) or self._default_mount(name)
            if np.allclose(np.asarray(cur, float), np.asarray(mount, float), atol=1e-9):
                return  # unchanged (a std episode after std episodes writes nothing)
            import omni.usd
            import torch
            from isaaclab.utils.math import convert_camera_frame_orientation_convention

            from ..sim.randomize import _set_pose
            q = convert_camera_frame_orientation_convention(torch.tensor([mount[3:]], dtype=torch.float32),
                                                            origin="world", target="opengl")[0].tolist()
            _set_pose(omni.usd.get_context().get_stage().GetPrimAtPath(self._cam_prim(name)), tuple(mount[:3]), tuple(q))
            self._mounts[name] = mount

        def _write_K(self, name: str, hfov: float) -> None:
            cam = self.env.scene[name]
            H, W = cam.image_shape
            if abs(self._K.get(name, -1.0) - hfov) < 1e-6:
                return
            import torch
            K = HC.K_of(hfov, W, H)
            spec = R9.CAM_SPECS[name] if franka else None
            ap = R9.H_APERTURE if franka else self._realcam().H_APERTURE
            f0 = (HC.fx_from_hfov(spec["hfov"], W) if franka else float(self._realcam().CAMERA_SPECS[name]["fx"])) * ap / W
            cam.set_intrinsic_matrices(torch.tensor(K[None], dtype=torch.float32), focal_length=f0)
            self._K[name] = float(hfov)

        def _apply_head_cam(self, seed: int, tz: float, attempt: int) -> None:
            """The episode's head camera: Franka = mast draw (attempt 0..TRIES-1, then the default mast); AI Worker =
            std (the robot's camera) or a drawn geometry (hcam rand / hold / coin), redrawn with the neck attempts,
            std after HEAD_TRIES. Records self.head_cam (meta head_cam)."""
            if franka:
                last = attempt >= HC.TRIES
                d = HC.draw_mast(seed, attempt, default=last)
                R, t = HC.mast_pose(self.base["pos"], tz, d)
                pp, pq = self._parent_pose("cam_head")
                pos, q = HC.mount_of(pp, pq, t, R)
                self._write_mount("cam_head", [*pos, *q])
                self._write_K("cam_head", d["hfov"])
                self._write_mount("cam_wrist_right", R9.mount_of("cam_wrist_right"))
            else:
                mode = self.hcam_mode
                mode = HC.coin(seed) if mode == "coin" else (mode or "std")
                if attempt >= V.HEAD_TRIES:
                    mode = "std"
                std = list(self._realcam().mount_transform("cam_head"))
                if mode == "std":
                    d = HC.std_ffw()
                    self._write_mount("cam_head", std)
                    if "cam_head" in self._K:  # only after a drawn episode changed it
                        self._write_K("cam_head", HC.STD_HFOV)
                else:
                    pp, pq = self._parent_pose("cam_head")
                    Rp = HC.quat_to_R(pq)
                    R0 = Rp @ HC.quat_to_R(std[3:])
                    t0 = pp + Rp @ np.asarray(std[:3])
                    h0 = float(t0[2] - tz)
                    d = (HC.draw_hold_ffw if mode == "hold" else HC.draw_ffw)(seed, h0, attempt)
                    R, t = HC.ffw_pose(R0, t0, d)
                    pos, q = HC.mount_of(pp, pq, t, R)
                    self._write_mount("cam_head", [*pos, *q])
                    self._write_K("cam_head", d["hfov"])
            cam = self._cam("cam_head", "head")
            Rwc = np.asarray(cam.R, float) @ WORLD_CONV_TO_OPTICAL.T
            m = self._mounts.get("cam_head") or self._default_mount("cam_head")
            self.head_cam = {"mode": d["mode"], "robot": robot,
                             "parent": R9.CAM_SPECS["cam_head"]["parent"] if franka else "head_link2",
                             "model": R9.CAM_SPECS["cam_head"]["model"] if franka else "Stereolabs ZED Mini (left)",
                             "mount_pos": [round(v, 5) for v in m[:3]], "mount_quat": [round(v, 6) for v in m[3:]],
                             **HC.realized(Rwc, cam.t, tz), "hfov_deg": round(HC.hfov_from_fx(cam.fx, cam.W), 2),
                             "W": cam.W, "H": cam.H, "fx": round(cam.fx, 3), "fy": round(cam.fy, 3),
                             "cx": round(cam.cx, 3), "cy": round(cam.cy, 3), "draw": d, "redraws": int(attempt)}

        def _cam(self, name: str, label: str):
            """= IsaacWorld._cam with this episode's mount (written above) instead of the copied default."""
            from ..astra_motion import geometry as G
            d = self.env.scene[name].data
            K = d.intrinsic_matrices[0].cpu().numpy()
            H, W = d.output["rgb"].shape[1:3]
            m = self._mounts.get(name) or self._default_mount(name)
            pp, pq = self._parent_pose(name)
            Rb = G.quat_to_R(pq)
            R = Rb @ G.quat_to_R(np.asarray(m[3:], float)) @ WORLD_CONV_TO_OPTICAL
            t = pp + Rb @ np.asarray(m[:3], float)
            return G.Cam(label, int(W), int(H), float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2]), R, t)

        def _render(self):
            self.env.env.sim.render()
            for n in cams:
                self.env.scene[n].update(0.0, force_recompute=True)

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
            h = self.hdr_name(seed, self.scene9["family"] if self.scene9 else None)
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
            if not franka:
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
            jp = "panda_joint" if franka else A.joint_prefix(arm)
            return {"tcp": [round(float(v), 4) for v in self.status()["tcp"]],
                    "q_arm": [round(float(v), 4) for v, n in zip(self.env.robot.data.joint_pos[0].cpu().numpy(),
                                                                 self.env.robot.joint_names) if n.startswith(jp)]}

        def step(self, cmd_pos, width: float, quat=None) -> None:
            from ..teach_l8d.xart import l8s_step_band
            m = getattr(self, "motion", None)
            if m and float(m.get("elbow", 0)) > 0 and not franka:  # the null-space posture is the AI Worker's
                self._step_elbow(cmd_pos, width, quat, float(m["elbow"]))
            else:
                l8s_step_band(self, cmd_pos, width, quat)
            self._log_step()

        def _step_elbow(self, cmd_pos, width, quat, gain):
            """= xart.l8s_step_band (ARM_DQ / ARM_BAND clamps) with a null-space pull towards a comfortable posture
            added to the unclamped IK target (spec §10 elbow; motion9.nullspace_pull)."""
            from ..sim.planner import W_MAX, _slerp_step
            from ..teach_l8d.clutter_x import ARM_BAND, ARM_DQ
            from .motion9 import Q_MID, nullspace_pull
            goal = self.pl.goal_quat if quat is None else np.asarray(quat, float)
            self.cmd_quat = _slerp_step(self.cmd_quat, goal, W_MAX * self.dt)
            env = self.env
            rob, ids = env.robot, env.arm_ids
            g = self.pl._gravity_offset()[0].cpu().numpy()
            qd = self.pl._ik(np.asarray(cmd_pos, float), self.cmd_quat, 10.0) - g
            qm = rob.data.joint_pos[0, ids].cpu().numpy()
            J = rob.root_physx_view.get_jacobians()[0, env.ee_idx - 1, :, :][:, ids].cpu().numpy()
            qmid = Q_MID if arm == "right" else A.mirror_q(Q_MID)
            qd = qd + nullspace_pull(J, qm, qmid, gain)
            if getattr(self, "_qcmd", None) is None:
                self._qcmd = qm.copy()
            self._qcmd = np.clip(self._qcmd + np.clip(qd - self._qcmd, -ARM_DQ, ARM_DQ), qm - ARM_BAND, qm + ARM_BAND)
            env.step(np.concatenate([self._qcmd + g, [float(width)]]).astype(np.float32))
            self._st = None
            if hasattr(self, "_jlog"):
                self._jlog.append(rob.data.joint_pos[0].cpu().numpy().copy())

        def _log_step(self):
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
            if franka:
                from ..astra_motion.harness import Obs
                self._render()
                st = self.status()
                obs = Obs(st["t"], {keys[n]: self.env.camera_rgb(n) for n in cams}, None,
                          {keys[n]: self._cam(n, keys[n]) for n in cams}, st["tcp"], st["grip_w"])
                if depth:
                    obs.depth = {"head": self.env.camera_depth("cam_head").copy()}
                self.last_obs = obs
                return obs
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
