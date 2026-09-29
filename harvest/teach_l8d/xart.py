"""L8-X articulated put-in tasks A / C (user-log 182 / 185; helper L8X-assets): a real object into the open top
drawer of a gate-passed THOR drawer piece (A) or into a THOR box with its flaps open (C). No new command vocabulary:
the L8-D collection path (collect.collect_episode: PtEpisode + XCollector, xlabels truth plan with support heights,
v2 / ND / pt requests and labels) runs on an ArtWorld that implements the IsaacWorld protocol.

Fixtures are the baked opened static copies (tools/l8x_assets/bake_open.py: joints written open in Isaac, the moved
bodies' poses carried into a static USD; opened.json has their support surfaces in the asset frame). Scene per
process = one fixture (yaw -90 deg: front towards the robot):
  A  the drawer's exposed inside (the uncovered container surface below the top) centred at TARGET_XY; the object
     stands on the piece's top 8-12 cm behind its front edge, same y; executor floor = the drawer floor (lower).
  C  a parametric stand (cuboid, STAND_TOP high) carries the box (its inside centred at C_BOX_XY) and the object
     (C_OBJ_XY); carry height raised over the box rim (sup_place = rim + object height + 3 cm - 22 cm).
Episode (seeded): object from the target list (opening fit), y jitter +-2 cm, lift from the work heights (+-2 cm),
head 0.785 rad (L8S), CC0 HDRI dome (train split), auto exposure (L8S rule: > 10 % saturated -> ISO x 0.6).
Predicates: holding = pads closed on the object (gap > 5 mm, < open - 5 mm) and the object within 6 cm of the
TCP; on(obj, place) = released, object bottom within 1.5 cm of the inside floor, centre inside the inner box;
upright = tilt <= 20 deg. Task id ai__<A|C>__<fixture>__<object>."""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

TARGET_XY = (0.42, -0.22)  # pilot 3: at 0.38 IK diverged; 0.44 -> 0.42 (audit 3): with rooms only Dresser_318_1 fits (2.3 / 2.6 m dressers exceed the 2 m room zone), its top at 0.44 was 8 mm beyond reach
C_BOX_XY, C_OBJ_XY = (0.52, None), (0.42, -0.38)  # pilot 4: y -0.47 was out of reach, (0.58, 0.0) too
C_GAP, C_BOX_Y_MAX = 0.13, 0.02  # C gate 1: at 10 cm the open fingers met the Box_2 wall (approach blocked 5 cm up)
C_GRASP_DEEPER = 0.0  # C gate 2: 2 cm deeper made it worse (3/10, fingertips on the stand -> tipped at the grasp); reverted
STAND_TOP, STAND_SIZE, STAND_CENTRE = 0.65, (0.52, 0.95), (0.52, -0.14)  # flap tops below the start TCP (1.06 m)
TOP_BEHIND = (0.04, 0.06)
MAX_LEN = 0.15  # objects at most 15 cm long (a held shoe hit the furniture while carried)
OBJ_X_MAX = 0.63
BOX_UP, CARRY_DZ, TCP_BELOW_TOP = 0.40, 0.22, 0.018  # executor box height above table_z, xlabels carry, grasp depth
FLOOR_TOL, TILT_UP = 0.015, 20.0
HOLD_GAP = 0.005
LIFT0, REL_TABLE = -0.0993, 0.85
PARK = (-7.0, 7.0, 0.3)
YAW = -math.pi / 2
PLACE_ID = "art_place"
GRIP_MAX = 0.107  # = scene.GRIP_MAX_W


def fixture_hint(rec: dict) -> str:
    return os.path.basename(str(rec.get("src", "?")))


def task_id(kind: str, fixture: str, obj: str) -> str:
    return f"ai__{kind}__{fixture}__{obj}"


def parse(task: str) -> tuple:
    _, kind, fixture, obj = task.split("__", 3)
    return kind, fixture, obj


def target_surface(rec: dict, kind: str):
    """The place surface of an opened fixture (asset frame): A = the largest uncovered container surface below the
    top (the open drawer's exposed inside); C = the largest container surface (the box floor)."""
    S = rec["surfaces"]
    if not S:
        return None
    top = max(s["top_z"] for s in S)
    if kind == "A":
        c = [s for s in S if s["container"] and s["covered_above"] is None and s["top_z"] < top - 0.05]
    else:
        c = [s for s in S if s["container"]]
    return max(c, key=lambda s: s["area"]) if c else None


def top_surface(rec: dict):
    S = [s for s in rec["surfaces"] if s["covered_above"] is None]
    return max(S, key=lambda s: s["top_z"]) if S else None


def to_world(box, pos, yaw=YAW):
    """Asset-frame xy box -> world xy box (yaw a multiple of 90 deg)."""
    c, s = round(math.cos(yaw)), round(math.sin(yaw))
    pts = np.array([[x, y] for x in box[0] for y in box[1]], float)
    w = pts @ np.array([[c, -s], [s, c]], float).T + np.asarray(pos[:2], float)
    return [[float(w[:, 0].min()), float(w[:, 0].max())], [float(w[:, 1].min()), float(w[:, 1].max())]]


def fits(obj: dict, box, margin: float = 0.02) -> bool:
    return 2 * float(obj["footprint_r"]) <= min(box[0][1] - box[0][0], box[1][1] - box[1][0]) - 2 * margin


def layout(kind: str, rec: dict, obj: dict, seed: int) -> dict:
    """Seeded scene layout (pure): fixture base position, place box / floor, object xy / support, work heights."""
    rng = np.random.default_rng([int(seed), 185, 3])
    ts = target_surface(rec, kind)
    if ts is None:
        raise ValueError("no place surface")
    (x0, x1), (y0, y1) = ts["free_box"]
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    jy = float(rng.uniform(-0.02, 0.02))
    if kind == "A":
        tx, ty = TARGET_XY[0], TARGET_XY[1] + jy
        pos = (tx - yc, ty + xc, 0.0)  # yaw -90: world (x, y) = pos + (y_a, -x_a)
        tp = top_surface(rec)
        front = pos[0] + tp["free_box"][1][0]  # the top's front edge (asset y min) in world x
        ox, oy = front + float(rng.uniform(*TOP_BEHIND)), ty
        if ox > OBJ_X_MAX:
            raise ValueError(f"object on the top at x {ox:.3f} beyond reach ({OBJ_X_MAX})")
        obj_z = float(tp["top_z"])
        floor = float(ts["top_z"])
    else:
        half = 0.5 * max(float(rec["collider_size"][0]), float(rec["collider_size"][1]))  # flaps spread
        # the inside centre goes next to the object (box edge 10 cm beside it); too wide a box = out of reach
        tx, ty = C_BOX_XY[0], C_OBJ_XY[1] + jy + C_GAP + half
        if ty > C_BOX_Y_MAX:
            raise ValueError(f"box {fixture_hint(rec)} too wide: centre y {ty:.3f} > {C_BOX_Y_MAX}")
        pos = (tx - yc, ty + xc, STAND_TOP)
        ox, oy = C_OBJ_XY[0], C_OBJ_XY[1] + jy
        obj_z = STAND_TOP
        floor = STAND_TOP + float(ts["top_z"])
    box = to_world(ts["free_box"], pos)
    rim = None if ts.get("rim_z") is None else float(ts["rim_z"]) + pos[2]
    work = min(floor, obj_z)
    h = float(obj["height"])
    if kind == "A":  # executor box: carry (top + 22 cm) <= table_z + 40 cm, drawer placement >= table_z + 2.5 cm
        work = max(work, obj_z + CARRY_DZ - BOX_UP + 0.005)
        if work > floor + h - TCP_BELOW_TOP - 0.025 + 0.004:
            raise ValueError(f"top {obj_z:.3f} too far above the drawer floor {floor:.3f} for the executor box")
    top = pos[2] + float(rec["collider_size"][2]) if kind == "C" else obj_z  # C: the flaps stand above the rim
    carry = (max(top, obj_z) + h + 0.03) if kind == "C" else obj_z + CARRY_DZ
    if carry > work + BOX_UP - 0.005:
        raise ValueError(f"carry height {carry:.3f} above the executor box ({work:.3f} + {BOX_UP})")
    place_tcp = floor + h - TCP_BELOW_TOP + 0.004
    # A: the fingers open along world x inside the drawer (run 4: at 10.7 cm they stopped at 6 cm on the walls of an
    # 11 cm deep drawer and the object stayed held) -> open only to the drawer depth - 3.5 cm
    w_open = GRIP_MAX if kind != "A" else min(GRIP_MAX, (box[0][1] - box[0][0]) - 0.035)
    if float(obj.get("grasp_width", 0.0)) > w_open - 0.02:
        raise ValueError(f"object {obj.get('grasp_width')} m wide > the release width {w_open:.3f} - 2 cm")
    # the lift centres the used TCP band (place .. carry) where L8 works at the default lift (table 0.85 + 7-24 cm);
    # C (pilot 5): the carry over the flaps (table + 37 cm) was out of reach there -> the band top goes to the carry
    mid = 0.5 * (place_tcp + carry) if kind == "A" else carry - 0.085
    lift = float(np.clip(LIFT0 + (mid - (REL_TABLE + 0.155)) + rng.uniform(-0.02, 0.02), -0.5, 0.0))
    return {"pos": [round(v, 4) for v in pos], "place_box": [[round(v, 4) for v in b] for b in box],
            "place_xy": [round((box[0][0] + box[0][1]) / 2, 4), round((box[1][0] + box[1][1]) / 2, 4)],
            "floor": round(floor, 4), "rim": None if rim is None else round(rim, 4), "obj_xy": [round(ox, 4),
                                                                                                 round(oy, 4)],
            "obj_z": round(obj_z, 4), "work_z": round(work, 4), "lift": round(lift, 4), "jy": round(jy, 4),
            "carry_z": round(carry, 4), "w_open": round(w_open, 4)}


def preds(obj_c, obj_bottom, obj_tilt, tcp, grip_w, w_open, lay, reach: float = 0.06, gw: float | None = None) -> dict:
    """The oracle predicates of an articulated put-in episode (pure)."""
    obj_c, tcp = np.asarray(obj_c, float), np.asarray(tcp, float)
    # reach: the object centre can be up to half its length from the TCP (a shoe is held at one end; pilot:
    # 6 cm read a lifted shoe as released and tipped)
    # gw: the object width -- pads more than 8 mm wider than it are not holding it (pilot 8: a release inside a
    # drawer stopped at 6.4 cm on a 5 cm object and read as still held)
    top = w_open - HOLD_GAP if gw is None else min(w_open - HOLD_GAP, gw + 0.008)
    hold = HOLD_GAP < grip_w < top and float(np.linalg.norm(obj_c - tcp)) < reach
    (x0, x1), (y0, y1) = lay["place_box"]
    inside = x0 <= obj_c[0] <= x1 and y0 <= obj_c[1] <= y1
    # L8-D change 19 (into): inside the opening box, bottom from the inside floor - 1 cm up to the rim; after release
    rim = lay.get("rim") if lay.get("rim") is not None else lay["floor"] + 0.10
    on = (not hold) and inside and lay["floor"] - 0.01 <= obj_bottom <= rim
    return {"holding(t)": hold, "on(t,p)": on, "upright(t)": obj_tilt <= TILT_UP,
            "lifted(t)": obj_bottom > lay["obj_z"] + 0.02}


# ============================================================================ Isaac (pod)
def pick_room(rooms: dict, seed: int):
    """L8S rule: every episode has a room. Same pick as furniture.sample_scene (seed rng [seed, 97, 200])."""
    if not rooms:
        return None
    names = sorted(rooms)
    return names[int(np.random.default_rng([int(seed), 97, 200]).integers(len(names)))]


def fixture_aabb(rec: dict, pos) -> tuple:
    """World xy box of a fixture placed at pos with yaw -90 deg (asset x -> world -y): collider centred on the origin."""
    sx, sy = float(rec["collider_size"][0]), float(rec["collider_size"][1])
    return ((pos[0] - sy / 2, pos[0] + sy / 2), (pos[1] - sx / 2, pos[1] + sx / 2))


def in_room_zone(boxes) -> bool:
    """Every xy box inside rooms.ZONE (the clear part of an iTHOR room around the robot: L8S room rule)."""
    from ..sim.assets_x.rooms import ZONE
    (zx0, zx1), (zy0, zy1) = ZONE
    return all(zx0 <= x0 and x1 <= zx1 and zy0 <= y0 and y1 <= zy1 for (x0, x1), (y0, y1) in boxes)


def scene_boxes(kind: str, rec: dict, lay: dict) -> list:
    out = [fixture_aabb(rec, lay["pos"])]
    if kind == "C":
        out.append(((STAND_CENTRE[0] - STAND_SIZE[0] / 2, STAND_CENTRE[0] + STAND_SIZE[0] / 2),
                    (STAND_CENTRE[1] - STAND_SIZE[1] / 2, STAND_CENTRE[1] + STAND_SIZE[1] / 2)))
    return out


def room_cfgs(cfg, rooms: dict | None):
    """Render-only iTHOR rooms, parked (as L8S isaac.slot_cfgs), added to a scene cfg."""
    import isaaclab.sim as sim_utils
    from isaaclab.assets import AssetBaseCfg

    from ..sim.assets_x.isaac import ROOM_PARK
    for j, (rn, r) in enumerate(sorted((rooms or {}).items())):
        setattr(cfg.scene, f"fr_{rn}", AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/FR_" + rn, spawn=sim_utils.UsdFileCfg(usd_path=r["usd"]),
            init_state=AssetBaseCfg.InitialStateCfg(pos=(ROOM_PARK[0] - 12.0 * j, ROOM_PARK[1], ROOM_PARK[2]))))


def place_room(rooms: dict | None, seed: int, boxes: list):
    """A train-split iTHOR room around the scene (same pick as L8S); the scene's xy boxes must lie in rooms.ZONE,
    else ValueError (skipped). The others are parked. USD poses (render only). -> scene room record."""
    import omni.usd

    from ..sim.assets_x.isaac import ROOM_PARK, yaw_quat
    from ..sim.randomize import _set_pose
    name = pick_room(rooms, seed)
    if name is None:
        return None
    if not in_room_zone(boxes):
        raise ValueError(f"scene outside the room zone: {[[[round(v, 3) for v in a] for a in b] for b in boxes]}")
    stage = omni.usd.get_context().get_stage()
    for j, rn in enumerate(sorted(rooms)):
        prim = stage.GetPrimAtPath(f"/World/envs/env_0/FR_{rn}")
        if rn == name:
            r = rooms[rn]
            _set_pose(prim, (r["pos"][0], r["pos"][1], r["pos"][2] + 0.001), yaw_quat(r["yaw"]))
        else:
            _set_pose(prim, (ROOM_PARK[0] - 12.0 * j, ROOM_PARK[1], ROOM_PARK[2]), (1.0, 0.0, 0.0, 0.0))
    r = rooms[name]
    return {"name": name, "usd": r["usd"], "pos": r["pos"], "yaw": r["yaw"], "kind": r.get("kind"),
            "license": r.get("license"), "source": r.get("source")}


def preroll_arm(world, steps: int = 200) -> dict:
    """= L8DWorld._preroll_arm (change 21): right TCP to ARM_START above the work surface (joint steps <= ARM_DQ)."""
    from .clutter_x import ARM_START
    goal = np.array([ARM_START[0], ARM_START[1], float(world.table_z) + ARM_START[2]])
    for _ in range(steps):
        if np.linalg.norm(np.asarray(world.status()["tcp"], float) - goal) < 0.01:
            break
        world.step(goal, world.w_open, None)
    for _ in range(10):
        world.step(goal, world.w_open, None)
    env = world.env
    return {"tcp": [round(float(v), 4) for v in world.status()["tcp"]],
            "q_arm": [round(float(v), 4) for v, n in zip(env.robot.data.joint_pos[0].cpu().numpy(),
                                                         env.robot.joint_names) if n.startswith("arm_r_joint")]}


def l8s_step(world, cmd_pos, width: float, quat=None) -> None:
    """= L8DWorld.step (L8S): arm step ARM_DQ (measured <= 0.04 rad), joint angles logged per step (joints.npz)."""
    from ..sim.planner import W_MAX, _slerp_step
    from .clutter_x import ARM_DQ
    goal = world.pl.goal_quat if quat is None else np.asarray(quat, float)
    world.cmd_quat = _slerp_step(world.cmd_quat, goal, W_MAX * world.dt)
    q = world.pl._ik(np.asarray(cmd_pos, float), world.cmd_quat, ARM_DQ)
    world.env.step(np.concatenate([q, [float(width)]]).astype(np.float32))
    world._st = None
    if hasattr(world, "_jlog"):
        world._jlog.append(world.env.robot.data.joint_pos[0].cpu().numpy().copy())


def make_art_world(kind: str, fixture: str, rec: dict, objs: dict, rooms: dict | None = None):
    from ..astra_motion.world_isaac import CAMS, NO_RENDER, PRE_RENDER, IsaacWorld
    from ..sim import scene as SC
    from ..sim.objv import register_for_tasks
    from tools.l8x_assets.validate_objects import qmul, tilt_deg

    ids = sorted(objs)
    register_for_tasks([f"ov_tray__{k}" for k in ids])  # names / sizes / OBJ_GEOM of the real objects
    orig = SC._build_cfg

    def patched(*x, **k):
        import isaaclab.sim as sim_utils
        from isaaclab.assets import AssetBaseCfg, RigidObjectCfg
        cfg, lay = orig(*x, **k)
        cfg.scene.table = None
        room_cfgs(cfg, rooms)
        cfg.scene.fixture = AssetBaseCfg(prim_path="{ENV_REGEX_NS}/FIXTURE",
                                         spawn=sim_utils.UsdFileCfg(usd_path=rec["dst"]),
                                         init_state=AssetBaseCfg.InitialStateCfg(pos=(PARK[0], -PARK[1], -3.0)))
        if kind == "C":
            cfg.scene.stand = AssetBaseCfg(
                prim_path="{ENV_REGEX_NS}/STAND",
                spawn=sim_utils.CuboidCfg(
                    size=(STAND_SIZE[0], STAND_SIZE[1], STAND_TOP), collision_props=sim_utils.CollisionPropertiesCfg(),
                    visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.55, 0.45, 0.35))),
                init_state=AssetBaseCfg.InitialStateCfg(pos=(STAND_CENTRE[0], STAND_CENTRE[1], STAND_TOP / 2)))
        for i, n in enumerate(ids):
            o = objs[n]
            setattr(cfg.scene, f"ai_{i}", RigidObjectCfg(
                prim_path="{ENV_REGEX_NS}/AI_%d" % i,
                spawn=sim_utils.UsdFileCfg(usd_path=o["usd_physics"],
                                           mass_props=sim_utils.MassPropertiesCfg(mass=o["mass"])),
                init_state=RigidObjectCfg.InitialStateCfg(pos=(PARK[0] - 0.4 * i, PARK[1], PARK[2]),
                                                          rot=tuple(o["spawn_quat_wxyz"]))))
        return cfg, lay

    class ArtWorld(IsaacWorld):
        def __init__(self):
            from ..sim.scene import GRIP_MAX_W, make_env
            SC._build_cfg = patched
            try:
                self.env = make_env(0, headless=True, cameras=CAMS, depth=True, render_interval=NO_RENDER)
            finally:
                SC._build_cfg = orig
            env = self.env
            self.dt, self.w_open = float(env.step_dt), float(GRIP_MAX_W)
            self._st, self.last_obs = None, None
            env.layout = {}
            SC._LAYOUT["layout"] = {}
            self._head_limit()
            self.kind, self.fixture, self.lay, self.obj, self.i_obj = kind, fixture, None, None, None
            self.furniture_scene = None

        def _head_limit(self, upper_deg: float = 57.0):
            import omni.usd
            from pxr import Usd
            stage = omni.usd.get_context().get_stage()
            for p in Usd.PrimRange(stage.GetPrimAtPath("/World/envs/env_0/Robot")):
                if p.GetName() == "head_joint1":
                    a = p.GetAttribute("physics:upperLimit")
                    if a and a.Get() is not None and a.Get() < upper_deg:
                        a.Set(upper_deg)

        def _pose(self, path, pos, yaw):
            import omni.usd

            from ..sim.randomize import _set_pose
            stage = omni.usd.get_context().get_stage()
            _set_pose(stage.GetPrimAtPath(path), tuple(float(v) for v in pos),
                      (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)))

        def reset(self, seed, task):
            from ..sim.perturb import perturb
            from ..sim.planner import OraclePlanner
            from .clutter_x import HEAD_TILT0
            env = self.env
            _, _, oid = parse(task)
            self.obj, self.i_obj = oid, ids.index(oid)
            o = objs[oid]
            lay = layout(kind, rec, o, seed)
            self.lay = lay
            self.w_open = float(lay["w_open"])  # the executor opens to this (A: the drawer depth - 3.5 cm)
            self._pose("/World/envs/env_0/FIXTURE", lay["pos"], YAW)  # applied by the hard reset below
            room = self._room(seed, lay)
            rob = env.robot
            for jn, v in (("lift_joint", lay["lift"]), ("head_joint1", HEAD_TILT0), ("head_joint2", 0.0)):
                if jn in rob.joint_names:
                    rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                    rob.cfg.init_state.joint_pos[jn] = v
            env.table_top_z = self.table_z = float(lay["work_z"])
            SC._LAYOUT["table_z"] = self.table_z
            env.lift = lay["lift"]
            env.task = "mug_tray"  # the OraclePlanner (IK / TCP helper) needs a registered task with scene objects
            env.layout = {oid: (lay["obj_xy"][0], lay["obj_xy"][1], 0.0), PLACE_ID: (*lay["place_xy"], 0.0)}
            env.present = [oid, PLACE_ID]
            env.randomization = None  # set by _dome (drf) after the reset
            self._register_place(lay)
            env.reset(settle_s=0.1)
            for i, n in enumerate(ids):  # the episode's object on its support, the others parked
                ob = env.scene[f"ai_{i}"]
                if n == oid:
                    x, y = lay["obj_xy"]
                    cx, cy = o["centre_from_root_xy"]
                    z = lay["obj_z"] + o["root_above_bottom"] + 0.003
                    p = [x - cx, y - cy, z, *o["spawn_quat_wxyz"]]
                else:
                    p = [PARK[0] - 0.4 * i, PARK[1], PARK[2], *objs[n]["spawn_quat_wxyz"]]
                ob.write_root_pose_to_sim(env.torch.tensor([p], dtype=env.torch.float32, device=env.env.device))
                ob.write_root_velocity_to_sim(env.torch.zeros((1, 6), device=env.env.device))
            self._q0 = tuple(o["spawn_quat_wxyz"])
            hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
            for _ in range(15):
                env.step(hold)
            perturb(env, "P0", seed)
            self._dome(seed)
            self.pl = OraclePlanner(env)
            self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
            self.quat0 = np.asarray(self.pl.goal_quat, float)
            arm_start = self._preroll_arm()  # L8D change 21: the right arm starts out of the head view
            self._jlog = []  # change 20: joints.npz records from here (collect_episode saves world._jlog)
            for _ in range(PRE_RENDER):
                env.env.sim.render()
            self.iso = self._auto_exposure()
            from ..sim.tasks import close_width
            self.w_close = float(close_width(oid))  # object width - 14 mm (L8 squeeze); 0 threw objects (pilots)
            self._st = None
            self.furniture_scene = {"kind": f"art_{kind}", "fixture": fixture, "layout": lay, "iso": self.iso,
                                    "hdr": self.hdr, "room": room, "room_skip": None if room else "no rooms loaded",
                                    "arm_start": arm_start,
                                    "head": {"tilt": HEAD_TILT0, "pan": 0.0}, "surface": "art_" + kind}

        def _room(self, seed, lay):
            return place_room(rooms, seed, scene_boxes(kind, rec, lay))

        def _preroll_arm(self) -> dict:
            return preroll_arm(self)

        def step(self, cmd_pos, width: float, quat=None) -> None:
            l8s_step(self, cmd_pos, width, quat)

        def _register_place(self, lay):
            from ..astra_motion import prompts as P
            (x0, x1), (y0, y1) = lay["place_box"]
            name = {"A": "open drawer", "C": "open box"}[kind]
            SC.OBJ_GEOM[PLACE_ID] = {"shape": "cuboid", "size": [x1 - x0, y1 - y0, 0.002], "height": 0.002,
                                    "footprint_r": 0.5 * min(x1 - x0, y1 - y0), "place_kind": "into"}
            SC.SUPPORT_TOP[PLACE_ID] = 0.0
            P.OBJ_NAME[PLACE_ID], P.OBJ_DESC[PLACE_ID] = name, name

        def _dome(self, seed):
            """L8S lighting: the drf randomization (exposure gain, 1-3 key lights, shadow softness, tint;
            randomize.sample_randomization / apply_visuals) with a CC0 indoor HDRI (train split) on the dome."""
            from ..sim import randomize as R
            from ..sim.assets_x import materials as M
            from .clutter_x import material_ok
            if not hasattr(self, "_hdrs"):
                cat = {k: r for k, r in M.usable(M.load()).items() if material_ok(k, r)}
                self._hdrs = [k for k, r in sorted(cat.items()) if r["role"] == "env" and M.split_of(k) == "train"]
                self._cat = cat
                R.setup_visuals(self.env)
            k = self._hdrs[int(hashlib.sha256(f"art-hdr:{int(seed)}".encode()).hexdigest()[:8], 16) % len(self._hdrs)]
            m = R.sample_randomization(seed, "drf", self.env.layout)
            m["distractors"] = []  # no pool distractors in articulated scenes
            if m.get("hdr"):
                m["hdr"]["file"] = os.path.join(M.ROOT, self._cat[k]["files"]["hdr"])
                m["hdr"]["name"] = k
            R.apply_visuals(self.env, m)
            self.env.randomization = m
            self.hdr = k

        def _auto_exposure(self):
            import carb

            from .clutter_x import DARK_MEAN, ISO0, SAT_MAX
            st = carb.settings.get_settings()
            iso = ISO0 * float(((self.env.randomization or {}).get("lighting") or {}).get("exposure", 1.0))
            for k in range(6):
                st.set("/rtx/post/tonemap/filmIso", iso)
                for _ in range(PRE_RENDER):
                    self.env.env.sim.render()
                self.env.scene["cam_head"].update(0.0, force_recompute=True)  # the frame just rendered
                rgb = self.env.scene["cam_head"].data.output["rgb"][0].cpu().numpy()[..., :3].astype(float)
                sat, mean = float((rgb.max(axis=2) >= 250).mean()), float(rgb.mean())
                if sat > SAT_MAX:
                    iso *= 0.6
                elif mean < DARK_MEAN:
                    iso *= 1.6
                else:
                    return {"iso": round(iso, 2), "sat": round(sat, 4), "mean": round(mean, 1), "tries": k + 1}
            return {"iso": round(iso, 2), "sat": round(sat, 4), "mean": round(mean, 1), "tries": 6,
                    "overexposed": sat > SAT_MAX}

        def task_info(self):
            o, lay = objs[self.obj], self.lay
            name = o["name"]
            text = {"A": f"Put the {name} into the open drawer.", "C": f"Put the {name} into the open box."}[kind]
            info = {"instruction": text, "tgt": self.obj, "place": PLACE_ID, "present": [self.obj, PLACE_ID],
                    "sup_tgt": lay["obj_z"] - (C_GRASP_DEEPER if kind == "C" else 0.0), "place_top": lay["floor"],
                    "sup_place": lay["floor"]}  # C: grasp 2 cm deeper, so the release is 2 cm above the floor
            if kind == "C":  # carry over the flaps / rim with the object hanging below the TCP
                info["sup_place"] = max(lay["floor"], lay["carry_z"] - 0.22)
            return info

        def _status_from(self, pl):
            env = self.env
            d = env.scene[f"ai_{self.i_obj}"].data
            c = d.root_pos_w[0].cpu().numpy().copy()
            q = d.root_quat_w[0].cpu().numpy()
            o = objs[self.obj]
            bottom = float(c[2] - o["root_above_bottom"])
            cen = c + np.array([o["centre_from_root_xy"][0], o["centre_from_root_xy"][1],
                                o["root_above_bottom"] + o["height"] / 2 - o["root_above_bottom"]])
            cen[2] = bottom + o["height"] / 2
            tcp = pl.tcp_pose()[0]
            w = float(env.gripper_width())
            p = preds(cen, bottom, tilt_deg(q, self._q0), tcp, w, self.w_open, self.lay,
                      reach=max(0.06, 0.5 * float(o["length"]) + 0.03), gw=float(o["grasp_width"]))
            pred = {f"holding({self.obj})": p["holding(t)"], f"on({self.obj},{PLACE_ID})": p["on(t,p)"],
                    f"upright({self.obj})": p["upright(t)"], f"lifted({self.obj})": p["lifted(t)"]}
            pl_c = np.array([*self.lay["place_xy"], self.lay["floor"] + 0.001])
            return {"t": round(float(env.sim_time), 6), "tcp": tcp, "grip_w": w, "pred": pred,
                    "obj": {self.obj: cen, PLACE_ID: pl_c}, "gripper_contacts": set()}

        def observe(self, depth: bool = False):
            obs = IsaacWorld.observe(self)
            if depth:
                obs.depth = {"head": self.env.camera_depth("cam_head").copy()}
            return obs

    return ArtWorld()


def run_art(out: str, kind: str, fixture: str, opened: str, objects: str, seeds: list, split: str = "train",
            clean: bool = False, p: float = 0.35, video: set = frozenset()) -> list:
    """One fixture per process: episodes on the given seeds (targets from the objects list that fit the place)."""
    from ..teach_l8.run_collect import style_of
    from . import spec as S
    from .collect import collect_episode
    rec = json.load(open(opened))[fixture]
    rows = json.load(open(objects))
    ts = target_surface(rec, kind)
    box = [[0.0, ts["free_box"][0][1] - ts["free_box"][0][0]], [0.0, ts["free_box"][1][1] - ts["free_box"][1][0]]]
    fit = {k: o for k, o in sorted(rows.items()) if fits(o, box) and float(o["length"]) <= MAX_LEN}
    if not fit:
        raise ValueError(f"{fixture}: no object fits the place ({box})")
    pick = {s: sorted(fit)[int(hashlib.sha256(f"ai:{fixture}:{s}".encode()).hexdigest()[:8], 16) % len(fit)]
            for s in seeds}
    from .fx import rooms_of  # L8S: every episode has a room background (train-split iTHOR rooms, audit 3)
    rooms = rooms_of(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim", "assets_x"),
                     "train")
    world = make_art_world(kind, fixture, rec, {k: fit[k] for k in sorted(set(pick.values()))}, rooms)
    res = []
    for s in seeds:
        task = task_id(kind, fixture, pick[s])
        od = os.path.join(out, split, f"art_{kind}_{fixture}", f"{task}_s{s}")
        if os.path.exists(os.path.join(od, "meta.json")):
            continue
        style = "clean" if clean else style_of(s, S.CLEAN_SHARE)
        try:
            m = collect_episode(world, s, task, "drf", split, od, 0.0 if style == "clean" else p, 4, 40, 120.0,
                                style, video=s in video)
        except ValueError as ex:  # layout not feasible for this object (executor box / fit): recorded, run goes on
            os.makedirs(od, exist_ok=True)
            json.dump({"seed": s, "task": task, "reason": str(ex)}, open(os.path.join(od, "skipped.json"), "w"))
            print("SKIP " + json.dumps({"seed": s, "task": task, "reason": str(ex)}), flush=True)
            continue
        m["art"] = world.furniture_scene
        json.dump(m, open(os.path.join(od, "meta.json"), "w"))
        res.append(m)
        print("EP " + json.dumps({k: m[k] for k in ("seed", "task", "success", "end_reason", "n_calls")}
                                 | {"iso": world.iso}), flush=True)
    return res
