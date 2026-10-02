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
    names = sorted(k for k in mesh if not any(p.get("asset") == k for p in furniture))  # not the task piece
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


HINT_GROUPS = {  # scene9 mat_hint -> material groups (ambientCG displayCategory / Poly Haven first category, lower case,
    # no spaces); fewer than 5 ids -> the role pool
    "wood": {"wood", "planks", "paintedwood", "bamboo", "chipboard", "cork", "wicker", "woodsiding"},
    "paint": {"paintedwood", "paintedmetal", "paintedplaster", "plastic", "wood", "planks"},
    "metal": {"metal", "metalplates", "sheetmetal", "diamondplate", "corrugatedsteel", "paintedmetal", "rust",
              "metalwalkway"},
    "stone": {"marble", "granite", "onyx", "terrazzo", "travertine", "tiles", "concrete"},
    "plastic": {"plastic", "porcelain", "paintedmetal", "rubber", "glazedterracotta"},
    "paper": {"cardboard", "paper", "leather", "fabric", "plastic", "wicker"},
}


def hint_pool(cat: dict, hint: str, split: str) -> list:
    from ..sim.assets_x import materials as M
    want = HINT_GROUPS.get(hint, set())
    return sorted(k for k, r in cat.items() if r["role"] != "env" and M.split_of(k) == split
                  and str(r.get("group", "")).lower().replace(" ", "") in want and r.get("setting") != "outdoor")


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
                robot: str = "ffw_sg2", hcam: str | None = None, ext: dict | None = None, dual: bool = False):
    """robot: robot9 profile ("ffw_sg2" = the AI Worker, unchanged; "franka_mast"). hcam (spec §9.3, E-HCAM8):
    None = the standard head camera every episode (unchanged); "coin" = hcam9.coin(seed) picks std / rand per seed;
    "rand" / "hold" = every episode. The Franka mast camera is drawn per episode whatever hcam says.
    ext (user 10-02, ext9): None = no external camera (unchanged); {"p": share, "n": 1 | 2} = 1-2 world-fixed
    external cameras rendered with the head at every call of the episodes whose ext9.coin is on (they render
    in every episode: switching their render products off breaks them; only paired episodes save them).
    dual (L9 bimanual, 2026-10-02, opt-in -- default False keeps every existing single-arm call byte-identical):
    forwarded to sim.scene.make_env(dual=True). `arm` still names env.primary (the stepped arm's 8-D target);
    the other arm's targets go through world.env.set_arm2_target after world.env.use_arm(other) (sim.scene.SimEnv
    dual support, b2b8946). World9 itself needs no further change: use_arm / set_arm2_target / other_arm live on
    env and are reachable as world.env.*."""
    from ..astra_motion.world_isaac import CAMS, KEYS, NO_RENDER, PRE_RENDER, IsaacWorld, WORLD_CONV_TO_OPTICAL
    from ..sim import scene as SC
    from ..sim.assets_x import isaac as FX
    from . import hcam9 as HC
    from . import robot9 as R9

    A.check_arm(arm)
    if robot not in R9.PROFILES and robot not in R9.V2_PROFILES:
        raise ValueError(f"robot {robot!r}")
    if hcam not in (None, "coin", "rand", "hold"):
        raise ValueError(f"hcam {hcam!r}")
    franka = robot == "franka_mast"
    v2r = robot in R9.V2_PROFILES  # L9 v2 R1 Pro / G1 (robot9.V2): either arm, its own head + used-arm wrist camera
    if franka and arm != "right":
        raise NotImplementedError("franka_mast: right-arm rows only (spec §9.2)")
    other = "left" if arm == "right" else "right"
    # v2 dual-arm robots render both wrists (user 10-02, 4-slot schema): the used arm's is "wrist", the other one
    # "wrist_left" (the AI Worker naming after its left-arm swap: "wrist_left" = the other wrist), saved per call
    cams = R9.CAMERAS if franka else (("cam_head", A.wrist_camera(arm), A.wrist_camera(other)) if v2r else CAMS)
    keys = {"cam_head": "head", "cam_wrist_right": "wrist", "cam_wrist_left": "wrist_left"}
    if v2r:
        keys = {"cam_head": "head", A.wrist_camera(arm): "wrist", A.wrist_camera(other): "wrist_left"}
    register_l9_ids()
    ids = register_pool(pool)
    if mesh is not None:  # L9 v2: Poly Haven tabletop pieces join the process's mesh slots (render only)
        from . import assets9 as A9
        k = int(hashlib.sha256("|".join(sorted(mesh)).encode()).hexdigest()[:6], 16)
        mesh = {**mesh, **A9.tabletop_for(k, split=split)}
        from . import scene9 as S9
        S9.MESH_POOL = {n: r for n, r in mesh.items() if r.get("surfaces")}  # mesh_furniture draws loaded pieces only
    undo = FX.without_table(mesh, rooms)
    from . import ext9 as E9
    ext_names = tuple(f"cam_ext{i}" for i in range(int(ext.get("n", 1)))) if ext else ()
    timing = bool(ext_names) or os.environ.get("IR_L9_EXT_TIMING") == "1"  # per-call render ms (ext9 cost)

    class World9(IsaacWorld):
        def __init__(self):
            from ..sim.scene import GRIP_MAX_W, _ensure_app, make_env
            if ext_names:
                _ensure_app(True, True)  # the Isaac Lab sim modules (camera cfgs) import only inside the app
            xc = {"extra_cameras": self._ext_cfgs()} if ext_names else {}
            try:
                self.env = make_env(0, headless=True, cameras=cams, depth=True, render_interval=NO_RENDER,
                                    variant="drf", objset="x", arm=arm, **({"robot": robot} if franka or v2r else {}),
                                    **({"dual": True} if dual else {}), **xc)
            finally:
                undo()
            env = self.env
            self.dual = bool(dual)
            # (the external render products always render: switching their HydraTexture updates off and on again
            # leaves the annotators empty, smoke 10-02)
            self.ext_cams, self._ext_now, self._ext_pairs, self._ext_K = None, None, [], {}
            self._ext_ms = {"render": [], "capture": [], "save": []}
            self.arm, self.pool_ids = arm, ids
            env.present_ids = tuple(env.present_ids) + SPOT_IDS + SURF_IDS  # Env.reset rebuilds present from these
            self.dt, self.w_open = float(env.step_dt), float(R9.GRIP_MAX_W if franka else (
                R9.V2[robot]["grip_max_w"] if v2r else GRIP_MAX_W))
            self.robot_profile, self.hcam_mode, self.cam_names = robot, hcam, cams
            self.joint_prefixes = ("panda_joint", "panda_finger") if franka else None
            if v2r:  # collect.py max_dq over the used arm's joints / fingers (str.startswith takes a tuple)
                self.joint_prefixes = ((f"{arm}_arm_joint",), f"{arm}_gripper_finger") if robot == "r1pro" else (
                    (f"{arm}_shoulder", f"{arm}_elbow", f"{arm}_wrist"), f"{arm}_hand")
            self._mounts, self._K = {}, {}  # per-episode camera mounts / intrinsics written to the stage
            self.head_cam = None
            self.table_z = float(env.table_top_z)
            self._st, self.last_obs, self.furniture_scene, self.clutter_scene = None, None, None, None
            self.ep, self.scene9, self.light = None, None, None
            if not franka and not v2r:
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
            if name is None and not rooms:
                return None
            names = sorted(rooms or {})
            stage = omni.usd.get_context().get_stage()
            for j, rn in enumerate(names):  # no room: every room parked (smoke 2026-10-02: the previous episode's
                # room stayed in place under an outdoor scene)
                prim = stage.GetPrimAtPath(f"/World/envs/env_0/FR_{rn}")
                if rn == name:
                    r = rooms[rn]
                    _set_pose(prim, (r["pos"][0], r["pos"][1], r["pos"][2] + 0.001), yaw_quat(r["yaw"]))
                else:
                    _set_pose(prim, (ROOM_PARK[0] - 12.0 * j, ROOM_PARK[1], ROOM_PARK[2]), (1.0, 0.0, 0.0, 0.0))
            if name is None:
                return None
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
                h = p.get("mat_hint")
                if h in HINT_GROUPS and role != "fabric":  # L9 v2: the part's palette kind (metal / stone / ...)
                    if ("hint", h) not in self._pools:
                        self._pools[("hint", h)] = hint_pool(cat, h, split)
                    if len(self._pools[("hint", h)]) >= 5:
                        ids = self._pools[("hint", h)]
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
            row_seed = int(seed)  # the episode seed (ext9 coin)
            if timing:
                self._ext_ms = {"render": [], "capture": [], "save": []}
            if ext_names:
                self.ext_cams = None
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
            elif v2r:  # R1 Pro torso squat / G1 standing for this surface (robot9 rules), no neck
                self._place_v2(tz)
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
            elif v2r:
                self._check_v2()
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
                if not franka and not v2r:
                    head = V.head_pose(seed, att, V.look_of(ep, sc)) if att < V.HEAD_TRIES else V.head_default()
                    for jn, v in (("head_joint1", head["tilt"]), ("head_joint2", head["pan"])):
                        rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                        rob.cfg.init_state.joint_pos[jn] = v
                    env.reset()
                    perturb(env, "P0", seed)
                self._apply_head_cam(seed, tz, att)
                for _ in range(PRE_RENDER):
                    env.env.sim.render()
            if not self._head_sees():  # redraws exhausted and still not visible: never ask the VLM to point
                from ..teach_l8d.fx import SkipScene  # at something off-screen (owner order 10-02)
                raise SkipScene("head: target/place out of view")
            self.head = head
            self.pl = OraclePlanner(env)
            if franka or v2r:
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
            if ext_names:
                self._apply_ext(row_seed, tz, parts + decor, room is not None)

        # ------------------------------------------------------------------ external cameras (ext9, user 10-02)
        def _ext_cfgs(self) -> dict:
            """World-fixed pinhole cameras under the env (parked below the floor until a paired episode)."""
            import isaaclab.sim as sim_utils
            from isaaclab.sensors import CameraCfg
            ap = 20.955
            f = HC.fx_from_hfov(70.0, E9.W) * ap / E9.W
            return {n: CameraCfg(prim_path=f"{{ENV_REGEX_NS}}/{n.replace('cam_', 'Cam_')}", update_period=0.0,
                                 height=E9.H, width=E9.W, data_types=["rgb", "distance_to_image_plane"],
                                 update_latest_camera_pose=True,
                                 spawn=sim_utils.PinholeCameraCfg(focal_length=f, focus_distance=200.0,
                                                                  horizontal_aperture=ap, clipping_range=(0.05, 30.0)),
                                 offset=CameraCfg.OffsetCfg(pos=(-3.0, 3.0 + i, -5.0), rot=(1.0, 0.0, 0.0, 0.0),
                                                            convention="world"))
                    for i, n in enumerate(ext_names)}

        def _ext_write(self, name: str, d: dict) -> None:
            import omni.usd
            import torch
            from isaaclab.utils.math import convert_camera_frame_orientation_convention

            from ..sim.randomize import _set_pose
            R, t, K = E9.pose_of(d)
            q = convert_camera_frame_orientation_convention(torch.tensor([HC.R_to_quat(R)], dtype=torch.float32),
                                                            origin="world", target="opengl")[0].tolist()
            path = f"/World/envs/env_0/{name.replace('cam_', 'Cam_')}"
            _set_pose(omni.usd.get_context().get_stage().GetPrimAtPath(path), tuple(float(v) for v in t), tuple(q))
            if abs(self._ext_K.get(name, -1.0) - d["hfov"]) > 1e-6:
                cam = self.env.scene[name]
                f0 = HC.fx_from_hfov(70.0, E9.W) * 20.955 / E9.W
                cam.set_intrinsic_matrices(torch.tensor(K[None], dtype=torch.float32), focal_length=f0)
                self._ext_K[name] = float(d["hfov"])

        def _ext_ctx(self, tz: float, parts: list, in_room: bool):
            from . import scene9 as S9
            org = self.env.scene.env_origins[0].cpu().numpy()
            ws = []
            for a, p, _ in self.ep["steps"]:
                for k in (a, p):
                    ws.append(np.asarray(self.env.object_pose(k)[0], float) - org)
            head = self._cam("cam_head", "head")
            robot_pts = [np.asarray(head.t, float), np.asarray(self.status()["tcp"], float)]
            boxes = [{"pos": p["pos"], "size": p["size"], "yaw": 0.0 if p.get("role") == "decor" else p.get("yaw", 0.0)}
                     for p in parts if p.get("size") is not None]
            zone = None
            if in_room:
                (x0, x1), (y0, y1) = S9.ZONE
                zone = ((x0 + 0.05, x1 - 0.05), (y0 + 0.05, y1 - 0.05))
            ws = E9.must_see(ws)
            return E9.Ctx(look_ws=np.mean(ws, axis=0), robot_pts=robot_pts, ws_pts=ws, boxes=boxes, zone=zone,
                          surface_z=tz)

        def _apply_ext(self, seed: int, tz: float, parts: list, in_room: bool) -> None:
            """Paired episode (ext9.coin): draw each camera's pose, render, check the rendered depth (nothing right in
            front, no hidden must-see point), redraw up to ext9.TRIES; cameras without a valid pose are left out.
            Other episodes: nothing written or recorded."""
            from ..astra_motion.world_isaac import PRE_RENDER
            self._ext_now, self._ext_pairs = None, []
            if not E9.coin(seed, float(ext.get("p", E9.P_DEFAULT))):
                self.ext_cams = None
                return
            import time
            t0 = time.perf_counter()
            ctx = self._ext_ctx(tz, parts, in_room)
            n = E9.n_cams(seed, len(ext_names))
            got, tries = [], []
            for i, name in enumerate(ext_names[:n]):
                rec = None
                for att in range(E9.TRIES):
                    d = E9.draw(seed, att, ctx, cam=i, avoid=[g["pose_draw"] for g in got])
                    if d is None:
                        tries.append({"cam": i, "attempt": att, "why": "no_pose"})
                        continue
                    try:
                        self._ext_write(name, d)
                        for _ in range(PRE_RENDER):
                            self.env.env.sim.render()
                        cam = self.env.scene[name]
                        cam.update(0.0, force_recompute=True)
                        depth = cam.data.output["distance_to_image_plane"][0, ..., 0].cpu().numpy()
                        R, t, K = E9.pose_of(d)
                        ok, why = E9.depth_ok(depth, R, t, K, ctx.ws_pts + ctx.robot_pts)
                    except Exception as ex:  # noqa: BLE001  (an external camera never stops the episode)
                        ok, why = False, f"error: {type(ex).__name__}: {str(ex)[:160]}"
                        print("EXT " + why, flush=True)
                    tries.append({"cam": i, "attempt": att, "why": why})
                    if ok:
                        rec = dict(E9.record(name, d), scene_name=name)
                        break
                if rec is not None:
                    got.append(rec)
            self.ext_cams = got
            self.ext_info = {"version": E9.VERSION, "p": float(ext.get("p", E9.P_DEFAULT)), "coin": True,
                             "n_drawn": n, "n_ok": len(got), "tries": tries,
                             "setup_s": round(time.perf_counter() - t0, 3),
                             "ctx": {"ws_pts": [[round(float(v), 3) for v in p] for p in ctx.ws_pts],
                                     "robot_pts": [[round(float(v), 3) for v in p] for p in ctx.robot_pts],
                                     "boxes": [{k: [round(float(v), 3) for v in b[k]] if k != "yaw"
                                                else round(float(b[k]), 4) for k in ("pos", "size", "yaw")}
                                               for b in ctx.boxes],
                                     "zone": ctx.zone}}

        def _ext_capture(self) -> None:
            """After the head render of a call: the external cameras' images of the same render."""
            if not self.ext_cams:
                return
            import time
            t0 = time.perf_counter()
            now = {}
            try:
                for rec in self.ext_cams:
                    cam = self.env.scene[rec["scene_name"]]
                    cam.update(0.0, force_recompute=True)
                    out = cam.data.output
                    now[rec["name"]] = (out["rgb"][0, ..., :3].cpu().numpy().astype(np.uint8),
                                        out["distance_to_image_plane"][0, ..., 0].cpu().numpy().astype(np.float32))
            except Exception as ex:  # noqa: BLE001  (stop pairing this episode, keep the head data)
                print(f"EXT capture error: {type(ex).__name__}: {str(ex)[:160]}", flush=True)
                self.ext_info["capture_error"] = f"{type(ex).__name__}: {str(ex)[:160]}"
                self.ext_cams, now = [], None
            self._ext_now = now
            self._ext_ms["capture"].append((time.perf_counter() - t0) * 1e3)

        def other_wrist_save(self, call_dir: str) -> None:
            """The other arm's wrist image (user 10-02: dual-arm robots keep both wrists; 4-slot schema, views9):
            img3_wrist_other.png + cams.json "wrist_other" (its record, arm). AI Worker renders both wrists already
            (obs "wrist_left" holds the other one); single-wrist worlds: no-op."""
            import json

            from ..astra_solo.overlay import png_bytes
            obs = getattr(self, "last_obs", None)
            if obs is None or "wrist_left" not in (obs.rgb or {}) or "wrist_left" not in (obs.cams or {}):
                return
            with open(os.path.join(call_dir, "img3_wrist_other.png"), "wb") as f:
                f.write(png_bytes(np.asarray(obs.rgb["wrist_left"])))
            cj = os.path.join(call_dir, "cams.json")
            cams_j = json.load(open(cj)) if os.path.exists(cj) else {}
            c = obs.cams["wrist_left"]
            cams_j["wrist_other"] = dict(c.to_json() if hasattr(c, "to_json") else dict(c),
                                         arm="right" if arm == "left" else "left")
            with open(cj, "w") as f:
                json.dump(cams_j, f)

        def ext_save(self, call_dir: str, idx: int) -> None:
            """Episode-writer hook (pt_episode._save_call, attempt 0, after cams.json): img1_external<k>.png,
            external<k>_depth.npz (uint16 mm, ext9.load_depth) and external_cams.json entries "external<k>" with the pair
            id, all in the third-person tree (tp9.tp_dir, user 10-02). No-op unless paired."""
            self.other_wrist_save(call_dir)
            if not self.ext_cams or not self._ext_now:
                return
            import json
            import time

            from ..astra_solo.overlay import png_bytes
            t0 = time.perf_counter()
            from . import tp9
            pair = f"{os.path.basename(os.path.dirname(os.path.dirname(call_dir)))}/c{int(idx):03d}"
            for k, rec in enumerate(self.ext_cams):
                rgb, depth = self._ext_now[rec["name"]]
                r = dict({x: v for x, v in rec.items() if x != "scene_name"}, pair=pair)
                gc = getattr(getattr(self, "rt", None), "choice", None)  # v2: this call's grasp (format v2 `rot`)
                if gc is not None:
                    r["grasp_rot"] = E9.grasp_rot(rec, gc.c1, gc.c2)
                # third-person views go to their own tree (tp9): the ego call dir / cams.json stay head + wrist
                tp9.write(call_dir, k, png_bytes(rgb),
                          lambda path, d=depth: np.savez_compressed(path, depth_mm=E9.depth_to_mm(d)), r)
            self._ext_pairs.append(int(idx))
            self._ext_now = None
            self._ext_ms["save"].append((time.perf_counter() - t0) * 1e3)

        def ext_timing(self) -> dict:
            """Per-episode timing (IR_L9_EXT_TIMING=1 log lines; isaac.sh passes only IR_* / CUDA_* variables):
            calls' render ms, external capture / save ms."""
            v = self._ext_ms
            return {"paired": bool(self.ext_cams), "n_ext": len(self.ext_cams or []), "n_render": len(v["render"]),
                    **{f"{k}_ms": (round(float(np.mean(x)), 2) if x else None) for k, x in v.items()},
                    **{f"{k}_ms_sum": round(float(np.sum(x)), 1) for k, x in v.items()},
                    "setup_s": (getattr(self, "ext_info", None) or {}).get("setup_s") if self.ext_cams else None}

        def ext_meta(self) -> dict:
            """meta keys of a paired episode ({} otherwise: unpaired episodes are byte-identical)."""
            if self.ext_cams is None:
                return {}
            ms = {k: (round(float(np.mean(v)), 2) if v else None) for k, v in self._ext_ms.items()}
            return {"external": dict(self.ext_info, pairs=list(self._ext_pairs), ms=ms,
                                     n_render=len(self._ext_ms["render"])),
                    "external_cams": [{"name": r["name"], "K": r["K"], "R": r["R"], "t": r["t"], "W": r["W"],
                                       "H": r["H"], "pose_draw": r["pose_draw"]} for r in self.ext_cams]}

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

        def _place_v2(self, tz: float) -> None:
            """R1 Pro / G1: body joints for the work surface (robot9.v2_body_joints: R1 torso squat, G1 straight) +
            the used arm's ready pose + open fingers, written to the default joint state and cfg.init_state (the hard
            reset re-reads it, P131); root pose = robot9.v2_root_pos. G1 skips surfaces it cannot work at."""
            import torch

            from ..teach_l8d.fx import SkipScene
            if robot == "g1" and not R9.g1_surface_ok(tz):
                raise SkipScene(f"g1: surface {tz:.2f} m outside its standing reach band")
            if robot == "r1pro" and not R9.r1_surface_ok(tz):
                raise SkipScene(f"r1pro: surface {tz:.2f} m above its torso reach (L9v2-DIAG 8)")
            rob = self.env.robot
            joints = R9.v2_init_joints(robot, arm, tz)
            for jn, v in joints.items():
                rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = float(v)
                rob.cfg.init_state.joint_pos[jn] = float(v)
            pos = R9.v2_root_pos(robot)
            rob.data.default_root_state[0, :3] = torch.tensor(pos, dtype=rob.data.default_root_state.dtype,
                                                              device=rob.data.default_root_state.device)
            rob.cfg.init_state.pos = pos
            body = R9.v2_body_joints(robot, tz)
            self.base = {"pos": [round(v, 4) for v in pos], "body_joints": {k: round(v, 4) for k, v in body.items()},
                         "surface_z": round(tz, 4)}

        def _check_v2(self, tol: float = 0.05) -> None:  # 0.03 skipped a scene on 0.030 (contact sag, 10-02)
            from ..teach_l8d.fx import SkipScene
            rob = self.env.robot
            got = {k: float(rob.data.joint_pos[0, rob.joint_names.index(k)]) for k in self.base["body_joints"]}
            err = max((abs(got[k] - v) for k, v in self.base["body_joints"].items()), default=0.0)
            self.base["body_measured"] = {k: round(v, 4) for k, v in got.items()}
            if err > tol:
                raise SkipScene(f"{robot} body joints {err:.3f} rad off (P131)")

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
            if v2r:
                return f"/World/envs/env_0/Robot/{R9.V2[robot]['cameras'][name]['parent']}/{name}"
            from ..sim.scene import load_realcam
            return f"/World/envs/env_0/Robot/ffw_sg2_follower/{load_realcam().CAMERA_SPECS[name]['prim']}"

        def _parent_pose(self, name: str):
            rob = self.env.robot
            par = R9.CAM_SPECS[name]["parent"] if franka else (R9.V2[robot]["cameras"][name]["parent"] if v2r else
                                                                  self._realcam().CAMERA_SPECS[name]["parent"])
            bi = rob.body_names.index(par)
            return (rob.data.body_pos_w[0, bi].cpu().numpy().astype(float),  # as world_isaac.camera_pose (env 0)
                    rob.data.body_quat_w[0, bi].cpu().numpy().astype(float))

        def _realcam(self):
            from ..sim.scene import load_realcam
            return load_realcam()

        def _default_mount(self, name: str) -> list:
            if v2r:
                p, q = R9.v2_mount(robot, name)
                return [*p, *q]
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
            spec = R9.CAM_SPECS[name] if franka else (R9.V2[robot]["cameras"][name] if v2r else None)
            ap = R9.H_APERTURE if franka or v2r else self._realcam().H_APERTURE
            f0 = (HC.fx_from_hfov(spec["hfov"], W) if franka or v2r else
                  float(self._realcam().CAMERA_SPECS[name]["fx"])) * ap / W
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
                std = self._default_mount("cam_head") if v2r else list(self._realcam().mount_transform("cam_head"))
                std_hfov = float(R9.V2[robot]["cameras"]["cam_head"]["hfov"]) if v2r else HC.STD_HFOV
                if mode == "std":
                    d = dict(HC.std_ffw(), hfov=round(std_hfov, 2))
                    self._write_mount("cam_head", std)
                    if "cam_head" in self._K:  # only after a drawn episode changed it
                        self._write_K("cam_head", std_hfov)
                    if v2r:  # the used arm's wrist camera (its default mount; nothing written when unchanged)
                        self._write_mount(A.wrist_camera(arm), self._default_mount(A.wrist_camera(arm)))
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
                             "parent": R9.CAM_SPECS["cam_head"]["parent"] if franka else (
                                 R9.V2[robot]["cameras"]["cam_head"]["parent"] if v2r else "head_link2"),
                             "model": R9.CAM_SPECS["cam_head"]["model"] if franka else (
                                 R9.V2[robot]["cameras"]["cam_head"]["model"] if v2r else "Stereolabs ZED Mini (left)"),
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
            if timing:  # render time per call (ext9 cost measurement)
                import time
                t0 = time.perf_counter()
            self.env.env.sim.render()
            for n in cams:
                self.env.scene[n].update(0.0, force_recompute=True)
            if timing:
                self._ext_ms["render"].append((time.perf_counter() - t0) * 1e3)

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
            if not franka and not v2r:
                set_arm_inertia(self.env.robot, A.LEFT_HEAD_INERTIA)  # right (change 27) + left + head (later_problems 11)
            # (no PhysX joint velocity cap: L8S defines _arm_vel_limit but never calls it -- change 25's command
            # rate limit replaced it; with the cap the L9 gate froze the arm mid-carry, diag 2026-10-01)
            s = A.arm_start(arm)
            goal = np.array([s[0], s[1], tz + s[2]])
            if v2r:  # L9v2-DIAG 2: R1 Pro / G1 start at V2_READY (cuRobo-chosen ready pose); chasing the AI Worker
                # start TCP pinned R1's q4 at its limit with the TCP 0.5-0.8 m over the table: hold the ready pose
                goal = np.asarray(self.status()["tcp"], float)
                steps = 0
            ready = self._ready_start(goal) if os.environ.get("L9_COMMON_EXEC") == "1" else None
            if ready is not None and ready.get("ok"):
                steps = 0  # L9 common executor: started at the ready branch, no Cartesian chase
            for _ in range(steps):
                if np.linalg.norm(np.asarray(self.status()["tcp"], float) - goal) < 0.01:
                    break
                self.step(goal, self.w_open, None)
            for _ in range(10):
                self.step(goal, self.w_open, None)
            if v2r:  # arm joints by index (G1 names share no prefix)
                out = {"tcp": [round(float(v), 4) for v in self.status()["tcp"]],
                       "q_arm": [round(float(v), 4) for v in self.env.arm_q()]}
            else:
                jp = "panda_joint" if franka else A.joint_prefix(arm)
                out = {"tcp": [round(float(v), 4) for v in self.status()["tcp"]],
                       "q_arm": [round(float(v), 4) for v, n in zip(self.env.robot.data.joint_pos[0].cpu().numpy(),
                                                                    self.env.robot.joint_names) if n.startswith(jp)]}
            if ready is not None:
                out["ready"] = ready
            return out

        def _ready_start(self, goal) -> dict | None:
            """L9 common executor (audit 8 + 11): move the used arm to the largest joint-margin IK branch of the ready
            TCP (goal; orientation = the start grasp orientation, or the held ready-pose orientation of a robot
            that starts at its ready joints) with a planned joint path (rt9.Runtime.ready_path), then hold it.
            None without a runtime; {'ok': False} keeps the old chase."""
            rt = getattr(self, "rt", None)
            if rt is None or not hasattr(rt, "ready_path"):
                return None
            quat = np.asarray(self.pl.tcp_pose()[1], float) if v2r else np.asarray(self.pl.goal_quat, float)
            try:
                Q, margin = rt.ready_path(np.asarray(goal, float), quat)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": str(e)[:160]}
            if Q is None:
                return {"ok": False, "margin": None if margin is None else round(float(margin), 4)}
            for q in Q:
                rt.q_target = np.asarray(q, float)
                self.step(goal, self.w_open, None)
            return {"ok": True, "margin": round(float(margin), 4), "n": int(len(Q))}

        def step(self, cmd_pos, width: float, quat=None) -> None:
            from ..teach_l8d.xart import l8s_step_band
            m = getattr(self, "motion", None)
            if m and float(m.get("elbow", 0)) > 0 and not franka and not v2r:  # the null-space posture is the AI Worker's
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
            obs = self._observe(depth)
            self._ext_capture()  # paired episodes: the external views of the same render
            return obs

        def _observe(self, depth: bool = False):
            if franka or v2r:
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
