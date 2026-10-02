"""T11 sim scene: AI Worker FFW-SG2 (fixed base), right arm only, table + red mug / blue tray (E §1.4, canon §37-§38).

Pure parts (layout sampling, gripper width <-> joint map, geometry) import without Isaac and are unit-tested
locally. Everything that touches Isaac is imported lazily inside functions (pod only).

Frames: world x = robot forward, y = robot left, z = up; robot root is fixed at the world origin.
The "table frame" (harvest.predicates) is world x, y and z - TABLE_TOP_Z.
v2 (2026-09-24, user instruction "우손목캠 있음 ... 로봇 설정 그대로 가져와서 복사해서 써보자"): robot and cameras are
copied verbatim from kairobahq/humanoid-challenge-env (third_party/humanoid_challenge_env, see NOTICE.md):
robot = taskC_ffw_sg2.FFW_SG2_MOBILE_CFG with ONE deviation (base fixed, canon §38), cameras =
FFW_SG2_REAL_cameras.camera_cfg (head ZED Mini left 672x376, wrists D405 424x240). The v1 scene (cyclo_lab
FFW_SG2_CFG + cam_head, slave-gripper gain change) is described in docs/stage3/results/scene_bringup.md.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np

# official ROBOTIS-GIT/cyclo_lab at 42dcd8256651 (the commit FFW_SG2_REAL_cameras.py pins as "CL"); a git worktree of
# our f4c0470 clone. FFW_SG2.py / FFW_SG2.usd blobs are identical at both commits (checked: 004ee05 / 08a5bd5).
CYCLO_LAB_SRC = "/data/harvest/cyclo_lab_42dcd82/source/cyclo_lab"
CHALLENGE_SCRIPTS = Path(__file__).resolve().parents[2] / "third_party" / "humanoid_challenge_env" / "scripts"

SCENE_SPEC = {
    "instruction": "Put the red mug on the blue tray.",
    "target": "o3",  # mug red
    "place": "o5",  # tray blue
    "distractors": ("o8", "o9"),  # 0-2 per seed
    "p2_object": "o10",  # DEV perturbation P2 only: parked off-table until it "appears"
    "names": {"o3": "mug red", "o5": "tray blue", "o8": "bottle green", "o9": "box yellow", "o10": "box purple",
              "o11": "marker magenta"},
}

TABLE_TOP_Z = 0.85  # world z of the table surface (table frame z = 0). Chosen so that the default head camera
# (pitch at its 0.695 rad limit) sees x >= ~0.35 m on the table while the right arm still reaches top-down to
# x ~0.50 m (at 0.76 m the visible and reachable bands barely overlapped: x 0.385-0.47).
TABLE_CENTER_XY = (0.50, -0.10)
TABLE_SIZE = (0.70, 1.00, 0.04)

# primitive shapes; mass kg, friction (static, dynamic). footprint_r = xy bounding radius (layout clearance)
OBJ_GEOM = {
    "o3": dict(shape="cylinder", radius=0.032, height=0.095, mass=0.20, friction=(1.0, 1.0), color=(0.80, 0.08, 0.08)),
    "o5": dict(shape="cuboid", size=(0.18, 0.14, 0.015), mass=0.40, friction=(0.8, 0.8), color=(0.10, 0.25, 0.85)),
    "o8": dict(shape="cylinder", radius=0.025, height=0.10, mass=0.15, friction=(0.8, 0.8), color=(0.10, 0.65, 0.20)),
    "o9": dict(shape="cuboid", size=(0.05, 0.05, 0.07), mass=0.10, friction=(0.8, 0.8), color=(0.90, 0.80, 0.10)),
    "o10": dict(shape="cuboid", size=(0.06, 0.05, 0.08), mass=0.10, friction=(0.8, 0.8), color=(0.55, 0.20, 0.70)),
    # R2 (task box_marker): flat VISUAL-ONLY target marker (no collider, no rigid body, no contact sensor); parked
    # behind the robot unless a task layout puts it on the table. Its "contact" is virtual (tasks.marker_contacts).
    # magenta: orange (1.0, 0.45, 0) rendered yellow in the bright standard scene (= the yellow box o9), DEV frames
    "o11": dict(shape="marker", radius=0.05, height=0.002, color=(0.85, 0.0, 0.65)),
}
# L8-X objects (docs/research/l8x_env_suite_design_2026-09-27.md): only in an env made with objset="x" (make_env);
# the default env, its bodies, sensors and layouts are unchanged.
X_OBJ_GEOM = {
    "o12": dict(shape="cuboid", size=(0.12, 0.12, 0.08), mass=2.0, friction=(1.0, 1.0), color=(0.85, 0.85, 0.80)),
    "o13": dict(shape="cylinder", radius=0.032, height=0.095, mass=0.20, friction=(1.0, 1.0),
                color=(0.15, 0.35, 0.95)),  # blue mug = the red mug's twin (colour attribute)
    "o14": dict(shape="cylinder", radius=0.025, height=0.075, mass=0.12, friction=(1.0, 1.0),
                color=(0.80, 0.08, 0.08)),  # small red cup (size attribute vs the red mug)
    # open box (floor + 4 walls, one rigid body): place-into container; support_top = floor top
    "o15": dict(shape="openbox", size=(0.16, 0.16, 0.05), wall=0.008, mass=1.0, friction=(0.8, 0.8),
                color=(0.50, 0.50, 0.50)),
    # invisible relational spots (no prim, no collider): 10 cm left / right (+y / -y) of the bottle o8
    "o17": dict(shape="marker", radius=0.04, height=0.002, invisible=True),
    "o18": dict(shape="marker", radius=0.04, height=0.002, invisible=True),
    # a furniture surface as a place target (static collider, no sensor): its box / top are set per episode
    # (Env.set_virtual_surface); contact = the object's bottom on its top inside its box (tasks.surface_contacts)
    "o19": dict(shape="surface", size=(0.10, 0.10, 0.002), invisible=True),
    "o20": dict(shape="surface", size=(0.10, 0.10, 0.002), invisible=True),  # a furniture container's floor
    # confusers (prereg_l8d change 10): the target's exact colour, another shape / size (never like the OOD-O cup o14)
    "o21": dict(shape="cuboid", size=(0.07, 0.05, 0.06), mass=0.20, friction=(1.0, 1.0), color=(0.80, 0.08, 0.08)),
    "o22": dict(shape="cylinder", radius=0.04, height=0.02, mass=0.10, friction=(1.0, 1.0), color=(0.80, 0.08, 0.08)),
    "o23": dict(shape="cylinder", radius=0.018, height=0.12, mass=0.10, friction=(1.0, 1.0), color=(0.80, 0.08, 0.08)),
    "o24": dict(shape="cylinder", radius=0.035, height=0.055, mass=0.10, friction=(1.0, 1.0), color=(0.10, 0.65, 0.20)),
    "o25": dict(shape="cuboid", size=(0.06, 0.06, 0.05), mass=0.20, friction=(1.0, 1.0), color=(0.10, 0.65, 0.20)),
    "o26": dict(shape="cuboid", size=(0.07, 0.05, 0.06), mass=0.20, friction=(1.0, 1.0), color=(0.15, 0.35, 0.95)),
    # relational spots of change 18 (invisible, no collider): in front of / behind the bottle, between bottle and box
    "o27": dict(shape="marker", radius=0.04, height=0.002, invisible=True),
    "o28": dict(shape="marker", radius=0.04, height=0.002, invisible=True),
    "o29": dict(shape="marker", radius=0.04, height=0.002, invisible=True),
}
X_RIGID = ("o12", "o13", "o14", "o15", "o21", "o22", "o23", "o24", "o25", "o26")
X_VISUAL_ONLY = ("o17", "o18", "o19", "o20", "o27", "o28", "o29")
VIRTUAL_PLACES = ("o19", "o20")  # furniture surfaces as place objects (set per episode, Env.set_virtual_surface)
SUPPORT_TOP = {"o15": 0.008}  # place surface above the object's bottom when it is not its top (bin floor)
OBJ_GEOM.update(X_OBJ_GEOM)
VISUAL_ONLY = ("o11",)
PRESENT_IDS = ("o3", "o5", "o8", "o9", "o11")  # objects in play when the layout has them (o10 joins after P2 fires)
X_PRESENT_IDS = PRESENT_IDS + X_RIGID + X_VISUAL_ONLY
OBJV_IDS: list = []  # L8-X licensed mesh objects registered in this process (harvest.sim.objv.register)
for _g in OBJ_GEOM.values():
    if _g["shape"] in ("cylinder", "marker"):
        _g["half_extents"] = (_g["radius"], _g["radius"], _g["height"] / 2)
    else:
        _g["half_extents"] = tuple(s / 2 for s in _g["size"])
    _g["footprint_r"] = float(math.hypot(_g["half_extents"][0], _g["half_extents"][1])) \
        if _g["shape"] in ("cuboid", "openbox", "surface") else _g["radius"]

# right-arm top-down workspace (world xy), measured reach margin from the shoulder at (-0.02, -0.23, 1.33)
WS_X = (0.36, 0.48)
WS_Y = (-0.40, -0.06)
DISTRACTOR_X = (0.34, 0.56)
DISTRACTOR_Y = (-0.46, 0.08)
PARK_XY = {"o8": (-3.0, 3.0), "o9": (-3.3, 3.0), "o10": (-3.6, 3.0),  # parked behind the robot (out of the head view)
           "o11": (-3.0, -3.0),
           "o12": (-3.0, 4.2), "o13": (-3.3, 4.2), "o14": (-3.6, 4.2), "o15": (-3.9, 4.2),  # L8-X objects
           "o21": (-3.0, 4.6), "o22": (-3.3, 4.6), "o23": (-3.6, 4.6), "o24": (-3.9, 4.6), "o25": (-4.2, 4.6),
           "o26": (-4.5, 4.6)}  # confusers

# RH-P12-RN: gripper_r_joint1 (0 = open, 1.1 = closed; joints 2-4 mimic). Inner pad gap measured in sim
# (probe2, 2026-09-24): finger link2 origin distance minus 7.7 mm (pad inner faces from the USD bbox).
_GQ = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 1.1])
_GW = np.array([0.1147, 0.1014, 0.0847, 0.0653, 0.0439, 0.0327, 0.0214, 0.0100]) - 0.0077
GRIP_MAX_W = float(_GW[0])  # 107.0 mm (spec 107.6 mm)
GRIP_Q_CLOSED = 1.1

ARM_JOINTS = {"right": [f"arm_r_joint{i}" for i in range(1, 8)], "left": [f"arm_l_joint{i}" for i in range(1, 8)]}
GRIP_JOINT = {"right": "gripper_r_joint1", "left": "gripper_l_joint1"}
GRIP_ALL = {"right": [f"gripper_r_joint{i}" for i in range(1, 5)], "left": [f"gripper_l_joint{i}" for i in range(1, 5)]}
PAD_INSET_M = 0.0077  # finger link2 origin -> pad inner face (USD bbox), per finger pair
EE_BODY = {"right": "arm_r_link7", "left": "arm_l_link7"}
FINGER_BODIES = {"right": ("gripper_r_rh_p12_rn_l1", "gripper_r_rh_p12_rn_l2", "gripper_r_rh_p12_rn_r1",
                           "gripper_r_rh_p12_rn_r2"),
                 "left": ("gripper_l_rh_p12_rn_l1", "gripper_l_rh_p12_rn_l2", "gripper_l_rh_p12_rn_r1",
                          "gripper_l_rh_p12_rn_r2")}  # L9 (arm="left", opt-in)
GRIPPER_PRIM = {"right": "right_gripper", "left": "left_gripper"}  # sub-prim of the robot USD holding the fingers
# initial robot pose. v1: cyclo_lab SG2 pick-place default (set_default_joint_pose: arm_?_joint1 0.75, joint4 -2.30,
# lift -0.0993) with the head pitched to 0.69 so the table workspace is inside the head camera.
# v2 (challenge-env robot): the RIGHT arm starts top-down above the workspace instead (INIT_R_ARM). From the cyclo
# pose the approach IK folded the elbow until the restored arm_r_link6 collider hit arm_r_link1 (134-201 N) and the
# swinging arm knocked the mug over (P0 seeds 1-4), and a joint-space move from that pose dips the fingertips to the
# table (-13..+61 mm over x > 0.30 for 4 candidate targets). v1 only worked because link6 had no collider.
INIT_R_ARM = (-1.0511, -1.0975, 1.2281, -2.3934, 0.4838, 1.2356, 1.80)  # TCP (0.34, -0.25, table + 0.25), yaw pi/2
# (IK gave joint7 = 1.8201, its upper limit 1.820; 1.80 keeps the default inside the limits)
INIT_JOINTS = {"arm_l_joint1": 0.75, "arm_l_joint4": -2.30, "head_joint1": 0.69, "lift_joint": -0.0993,
               **{f"arm_r_joint{i + 1}": v for i, v in enumerate(INIT_R_ARM)}}


def init_joints(arm: str = "right") -> dict:
    """Initial joints of an env acting with `arm`: "right" = INIT_JOINTS (unchanged); "left" (L9) = the left arm at the
    mirrored INIT_R_ARM start, the right arm in the cyclo idle pose (harvest.l9.arm)."""
    from ..l9.arm import init_joints as _ij
    return _ij(arm, INIT_JOINTS)


def joint_to_width(q: float) -> float:
    return float(np.interp(q, _GQ, _GW))


def width_to_joint(w: float) -> float:
    return float(np.interp(w, _GW[::-1], _GQ[::-1]))


WS_MIN_W = 0.08  # L8-D gate G-H: a table height's workspace (view x reach) must be >= 8 cm wide in x


def _check_objset(task: str, objset) -> None:
    from .tasks import X_TASKS
    if task in X_TASKS and objset != "x":
        raise ValueError(f"task {task!r} is an L8-X task: make_env(objset='x')")


def check_ws(ws):
    """ws = ((x0, x1), (y0, y1)) workspace box (L8-D per-height box, docs/stage3/prereg_l8d.md) or None (WS_X/WS_Y)."""
    if ws is None:
        return None
    (x0, x1), (y0, y1) = ws
    if not (x1 - x0 >= WS_MIN_W - 1e-9 and y1 - y0 >= 0.08):
        raise ValueError(f"workspace {ws}: x width >= {WS_MIN_W} m and y width >= 0.08 m")
    return (float(x0), float(x1)), (float(y0), float(y1))


def sample_layout(seed: int, ws=None) -> dict:
    """Initial placement from the seed: {obj_id: (x, y, yaw)} in world xy (table frame xy is the same).
    ws: optional workspace box (check_ws) for target and place; None = WS_X / WS_Y (unchanged)."""
    wx, wy = check_ws(ws) or (WS_X, WS_Y)
    rng = np.random.default_rng([int(seed), 11])
    fr = {k: g["footprint_r"] for k, g in OBJ_GEOM.items()}
    for _ in range(10000):
        t = (rng.uniform(wx[0] + 0.02, wx[1]), rng.uniform(wy[0] + 0.03, wy[1] - 0.03), 0.0)
        m = (rng.uniform(*wx), rng.uniform(*wy), 0.0)
        if math.dist(t[:2], m[:2]) >= max(0.16, fr["o3"] + fr["o5"] + 0.03):
            break
    else:  # pragma: no cover
        raise RuntimeError("layout")
    out = {"o3": m, "o5": t}
    n = int(rng.integers(0, 3))
    for k in SCENE_SPEC["distractors"][:n]:
        for _ in range(10000):
            p = (rng.uniform(*DISTRACTOR_X), rng.uniform(*DISTRACTOR_Y), float(rng.uniform(-math.pi, math.pi)))
            ok = math.dist(p[:2], m[:2]) >= 0.10 and all(
                math.dist(p[:2], q[:2]) >= fr[k] + fr[j] + 0.02 for j, q in out.items())
            if ok:
                out[k] = p
                break
    return out


def yaw_quat(yaw: float) -> tuple:
    return (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))


_MODS = {}


def _load_challenge(name: str, rel: str):
    """Import a copied humanoid-challenge-env file by path (as the challenge scripts do with _by_path)."""
    if name not in _MODS:
        spec = importlib.util.spec_from_file_location(name, CHALLENGE_SCRIPTS / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS[name] = mod
    return _MODS[name]


def load_realcam():
    """FFW_SG2_REAL_cameras (its data part imports without Isaac)."""
    return _load_challenge("FFW_SG2_REAL_cameras", "FFW_SG2_REAL_cameras.py")


KNOWN_CAMERAS = ("cam_head", "cam_wrist_left", "cam_wrist_right")  # = FFW_SG2_REAL_cameras.CAMERA_NAMES
DEFAULT_CAMERAS = KNOWN_CAMERAS  # the real robot's three cameras are present in the scene
RECORD_CAMERAS = ("cam_head", "cam_wrist_right")  # what we record (one arm = right)


def camera_table():
    """One row per camera from the copied spec: resolution, fx, FOV, parent link, mount [t, q], clipping."""
    rc = load_realcam()
    rows = []
    for n in rc.CAMERA_NAMES:
        s = rc.CAMERA_SPECS[n]
        hf, vf = rc.fov_deg(n)
        rows.append(dict(name=n, model=s["model"], width=s["width"], height=s["height"], fx=s["fx"],
                         hfov_deg=hf, vfov_deg=vf, focal_length=rc.focal_length(n), parent=s["parent"],
                         prim=s["prim"], mount=rc.mount_transform(n), clip_m=tuple(s["clipping_range"])))
    return rows


# ----------------------------------------------------------------------------------------------------------
# Isaac part (pod only)
# ----------------------------------------------------------------------------------------------------------
_APP = None


def _sim_device(name: str) -> str:
    """Physics device for SimulationCfg.device: 'cpu' (default, canon §48) or 'cuda' (-> cuda:0; GPU 0 only)."""
    if name == "cpu":
        return "cpu"
    if name in ("cuda", "cuda:0"):
        return "cuda:0"
    raise ValueError(f"sim_device {name!r}: 'cpu' or 'cuda'")


def _ensure_app(headless: bool, cameras: bool):
    global _APP
    if _APP is None:
        import sys
        if CYCLO_LAB_SRC not in sys.path:
            sys.path.insert(0, CYCLO_LAB_SRC)
        from isaaclab.app import AppLauncher
        import os
        kw = {}
        kt, pt = os.environ.get("L9_KIT_THREADS"), os.environ.get("L9_PHYSX_THREADS")
        if kt or pt:  # L9 lanes (10-02): many Isaac processes per pod were CPU-throttled; cap the worker threads
            a = [f"--/plugins/carb.tasking.plugin/threadCount={int(kt)}"] if kt else []
            if pt:
                a += [f"--/persistent/physics/numThreads={int(pt)}", f"--/physics/numThreads={int(pt)}"]
            kw["kit_args"] = " ".join(a)
        _APP = AppLauncher(headless=headless, device="cuda:0", enable_cameras=cameras, **kw).app
    return _APP


def _default_camera_cfgs(names, depth: bool):
    """FFW_SG2_REAL_cameras.camera_cfg as copied; the only override is the renderer depth annotator."""
    rc = load_realcam()
    out = {}
    for n in names:
        if n not in KNOWN_CAMERAS:
            raise ValueError(f"camera {n!r}: only the real robot's cameras {KNOWN_CAMERAS}")
        out[n] = rc.camera_cfg(n, data_types=["rgb", "distance_to_image_plane"]) if depth else rc.camera_cfg(n)
    return out


def _robot_cfg():
    """taskC_ffw_sg2.FFW_SG2_MOBILE_CFG verbatim except fix_root_link (False -> True): canon §38 fixes the base.
    Everything else (USD, gains incl. grippers, gravity on, spawn function: jaw friction 2.0/1.8, collider restore
    and filters, head pitch limit 45 deg, swerve actuators) is the copied file's."""
    ffw = _load_challenge("taskC_ffw_sg2", "taskC/taskC_ffw_sg2.py")
    robot = ffw.FFW_SG2_MOBILE_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
    ap = robot.spawn.articulation_props.replace(fix_root_link=True)  # re-enables the USD world FixedJoint
    return robot.replace(spawn=robot.spawn.replace(articulation_props=ap))


_LAYOUT = {"layout": {}}  # current seed's layout, read by the reset event (module global: cfgs get deep-copied)
# "table_z" (set by Env): the table top of the current env; TABLE_TOP_Z unless make_env(table_z=...) (E-PT OOD-H)


def base_z(k: str, layout: dict, table_z: float) -> float:
    """World z of k's bottom at reset: the table, or (L8-X layout entry (x, y, yaw, support)) the support's top."""
    e = layout[k]
    if len(e) > 3 and e[3]:
        s = e[3]
        return base_z(s, layout, table_z) + SUPPORT_TOP.get(s, 2 * OBJ_GEOM[s]["half_extents"][2])
    return table_z


def _object_reset_pose(k: str, layout: dict):
    g = OBJ_GEOM[k]
    if k in layout:
        x, y, yaw = layout[k][:3]
        z0 = _LAYOUT.get("table_z", TABLE_TOP_Z)
        if len(layout[k]) > 3:  # L8-X: standing on another object
            z0 = base_z(k, layout, z0)
        pos, q = (x, y, z0 + g["half_extents"][2] + 0.001), yaw_quat(yaw)
    else:
        x, y = PARK_XY.get(k, (-2.4 - 0.3 * len(k), 2.4))
        pos, q = (x, y, g["half_extents"][2] + 0.001), yaw_quat(0.0)
    if g["shape"] == "mesh":  # L8-X licensed mesh object: canonical (bbox centre, upright) -> its USD root pose
        from .objv import root_from_canonical
        r, rq = root_from_canonical(g, pos, q)
        return tuple(float(v) for v in r), tuple(float(v) for v in rq)
    return pos, q


def _place_layout_event(env, env_ids):
    """Reset event: put every object at its layout pose (or parked), zero velocity. Runs once per reset.
    Also sets the PD targets of the joints outside the action (left arm, head, lift) to their defaults; without
    this they are driven to 0 (Isaac Lab leaves joint_pos_target at 0 for joints no action term owns)."""
    import torch
    rob = env.scene["robot"]
    rob.set_joint_position_target(rob.data.default_joint_pos[env_ids], env_ids=env_ids)
    for k in _LAYOUT.get("obj_ids", ("o3", "o5", "o8", "o9", "o10")):  # + L8-X objects when objset="x"
        pos, quat = _object_reset_pose(k, _LAYOUT["layout"])
        o = env.scene[k]
        p = torch.tensor([[*pos, *quat]], dtype=torch.float32, device=env.device)
        p[:, :3] += env.scene.env_origins[env_ids]
        o.write_root_pose_to_sim(p, env_ids=env_ids)
        if not OBJ_GEOM[k].get("kinematic"):  # L8S containers are kinematic: a velocity write is a PhysX error
            o.write_root_velocity_to_sim(torch.zeros((len(env_ids), 6), device=env.device), env_ids=env_ids)
    if _LAYOUT.get("rand"):  # variant random / dr: this seed's tabletop distractors (randomize.py)
        from .randomize import write_distractor_poses
        write_distractor_poses(env, env_ids, _LAYOUT["rand"])


def _build_cfg(seed: int, cameras, arm: str, depth: bool, sim_device: str = "cpu", variant: str = "standard",
               decimation: int = 5, render_interval: int | None = None, task: str = "mug_tray",
               table_z: float = TABLE_TOP_Z, ws=None, lift: float | None = None, objset: str | None = None,
               robot: str | None = None, extra_cameras: dict | None = None, dual: bool = False):
    import isaaclab.envs.mdp as mdp
    import isaaclab.sim as sim_utils
    from isaaclab.assets import AssetBaseCfg, RigidObjectCfg
    from isaaclab.envs import ManagerBasedRLEnvCfg
    from isaaclab.managers import EventTermCfg as EventTerm
    from isaaclab.managers import ObservationGroupCfg as ObsGroup
    from isaaclab.managers import ObservationTermCfg as ObsTerm
    from isaaclab.managers import SceneEntityCfg
    from isaaclab.managers import TerminationTermCfg as DoneTerm
    from isaaclab.scene import InteractiveSceneCfg
    from isaaclab.sensors import ContactSensorCfg
    from isaaclab.utils import configclass

    if arm not in ("right", "left"):  # L9: arm="left" (opt-in); every L8 caller passes the default "right"
        raise NotImplementedError(f"arm {arm!r}")
    if robot is not None:  # L9 spec §9.1 (opt-in robot profile; None = the AI Worker, unchanged)
        from ..l9 import robot9 as R9
        if not (robot == "franka_mast" and arm == "right") and robot not in R9.V2_PROFILES:
            raise NotImplementedError(f"robot {robot!r} arm {arm!r}")
    v2r = robot in ("r1pro", "g1")  # L9 v2 profiles (robot9.V2): R1 Pro / G1, either arm
    from .tasks import task_layout
    layout = task_layout(seed, task, ws=ws)  # mug_tray = sample_layout(seed)
    robot_prefix = "{ENV_REGEX_NS}/Robot/ffw_sg2_follower"
    finger_paths = [f"{robot_prefix}/{GRIPPER_PRIM[arm]}/{b}" for b in FINGER_BODIES[arm]]
    if robot is not None:
        bodies = R9.v2_contact_bodies(robot, arm) if v2r else R9.FINGER_BODIES
        finger_paths = [f"{{ENV_REGEX_NS}}/Robot/{b}" for b in bodies]
    other = "left" if arm == "right" else "right"
    if dual:  # L9 bimanual: the other arm's finger links join the contact filters (after the used arm's)
        if robot is None:
            finger_paths = finger_paths + [f"{robot_prefix}/{GRIPPER_PRIM[other]}/{b}" for b in FINGER_BODIES[other]]
        elif v2r:
            finger_paths = finger_paths + [f"{{ENV_REGEX_NS}}/Robot/{b}" for b in R9.v2_contact_bodies(robot, other)]
        else:
            raise NotImplementedError(f"dual: robot {robot!r} has one arm")
    obj_ids = ["o3", "o5", "o8", "o9", "o10"] + (list(X_RIGID) + list(OBJV_IDS) if objset == "x" else [])

    def obj_cfg(k):
        g = OBJ_GEOM[k]
        if g["shape"] == "mesh":  # L8-X licensed mesh (own convex-hull colliders in its physics USD)
            spawn = sim_utils.UsdFileCfg(usd_path=g["usd"],
                                         rigid_props=sim_utils.RigidBodyPropertiesCfg(max_depenetration_velocity=1.0),
                                         mass_props=sim_utils.MassPropertiesCfg(mass=g["mass"]),
                                         activate_contact_sensors=True,
                                         **({"scale": tuple(g["spawn_scale"])} if g.get("spawn_scale") else {}),  # L9 opt-in
                                         **_collider_spawn(k, g))  # L9 v2 opt-in (L9V2_COLLIDERS / row collider)
            pos, rot = _object_reset_pose(k, layout)
            return RigidObjectCfg(prim_path="{ENV_REGEX_NS}/" + k.upper(), spawn=spawn,
                                  init_state=RigidObjectCfg.InitialStateCfg(pos=pos, rot=rot))
        common = dict(
            rigid_props=sim_utils.RigidBodyPropertiesCfg(max_depenetration_velocity=1.0),
            mass_props=sim_utils.MassPropertiesCfg(mass=g["mass"]),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.004, rest_offset=0.0),
            physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=g["friction"][0],
                                                            dynamic_friction=g["friction"][1], restitution=0.0),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=g["color"]),
            activate_contact_sensors=True,
        )
        if g["shape"] == "cylinder":
            spawn = sim_utils.CylinderCfg(radius=g["radius"], height=g["height"], axis="Z", **common)
        elif g["shape"] == "openbox":  # L8-X container: floor + 4 walls in one rigid body (spawn_open_box)
            spawn = sim_utils.CuboidCfg(size=g["size"], func=spawn_open_box, **common)
        else:
            spawn = sim_utils.CuboidCfg(size=g["size"], **common)
        x, y, yaw = layout.get(k, (*PARK_XY.get(k, (-3.9, 3.0)), 0.0))[:3]
        z = (table_z if k in layout else 0.0) + g["half_extents"][2] + 0.001
        if k in layout and len(layout[k]) > 3:  # L8-X: standing on another object
            z = base_z(k, layout, table_z) + g["half_extents"][2] + 0.001
        return RigidObjectCfg(prim_path="{ENV_REGEX_NS}/" + k.upper(), spawn=spawn,
                              init_state=RigidObjectCfg.InitialStateCfg(pos=(x, y, z), rot=yaw_quat(yaw)))

    def body_path(k):  # the rigid body prim (L8-X mesh objects keep it under their USD root)
        g = OBJ_GEOM[k]
        return "{ENV_REGEX_NS}/" + k.upper() + ("/" + g["body_rel"] if g.get("body_rel") else "")

    def contact_cfg(k):
        others = [body_path(j) for j in obj_ids if j != k and not OBJ_GEOM[j].get("kinematic")]  # L8S containers: no sensor
        return ContactSensorCfg(prim_path=body_path(k), update_period=0.0, history_length=0,
                                filter_prim_paths_expr=finger_paths + others)

    if v2r:
        robot_name, robot = robot, R9.v2_robot_cfg(robot, R9.v2_init_joints(robot, arm, table_z))
        robot = robot.replace(init_state=robot.init_state.replace(pos=R9.v2_root_pos(robot_name)))
    elif robot is not None:
        robot_name, robot = robot, R9.franka_robot_cfg()
    else:
        robot_name = None
        robot = _robot_cfg()
        base = INIT_JOINTS if arm == "right" else init_joints(arm)  # L9 left arm: mirrored start, right arm stowed
        joints = dict(base) if lift is None else {**base, "lift_joint": float(lift)}  # L8-D lift flag
        robot = robot.replace(init_state=robot.init_state.replace(joint_pos={**robot.init_state.joint_pos, **joints}))

    scene_attrs = {
        "robot": robot,
        "plane": AssetBaseCfg(prim_path="/World/GroundPlane", spawn=sim_utils.GroundPlaneCfg()),
        "light": AssetBaseCfg(prim_path="/World/light", spawn=sim_utils.DomeLightCfg(color=(0.9, 0.9, 0.9),
                                                                                     intensity=2500.0)),
        "table": AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Table",
            spawn=sim_utils.CuboidCfg(
                size=TABLE_SIZE, collision_props=sim_utils.CollisionPropertiesCfg(),
                physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=0.6, dynamic_friction=0.6),
                visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.55, 0.45, 0.35))),
            init_state=AssetBaseCfg.InitialStateCfg(pos=(*TABLE_CENTER_XY, table_z - TABLE_SIZE[2] / 2))),
    }
    for k in obj_ids:
        scene_attrs[k] = obj_cfg(k)
        if not OBJ_GEOM[k].get("kinematic"):  # kinematic containers: no contact reporter (rest contacts are geometric)
            scene_attrs[f"contact_{k}"] = contact_cfg(k)
    if variant not in ("standard", "drf"):  # random / dr: one parked rigid body per pool distractor (own colliders)
        from .randomize import distractor_scene_cfgs, randomized_table_cfg
        scene_attrs.update(distractor_scene_cfgs(variant))
        scene_attrs["table"] = randomized_table_cfg(scene_attrs["table"])  # same table + own material (visual)
    mk = OBJ_GEOM["o11"]  # R2 visual-only task marker (no collider / rigid body): parked, moved at reset (USD pose)
    scene_attrs["marker"] = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Marker",
        spawn=sim_utils.CylinderCfg(radius=mk["radius"], height=mk["height"], axis="Z",
                                    visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=mk["color"])),
        init_state=AssetBaseCfg.InitialStateCfg(pos=(*PARK_XY["o11"], mk["height"] / 2)))
    if v2r:  # L9 v2 profile cameras (robot9.V2), no stand
        for n, c in R9.v2_camera_cfgs(robot_name, cameras, depth).items():
            scene_attrs[n] = c
    elif robot_name is not None:  # profile cameras + the stand under the arm base (static collider, moved per episode)
        for n, c in R9.franka_camera_cfgs(cameras, depth).items():
            scene_attrs[n] = c
        scene_attrs["stand"] = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Stand",
            spawn=sim_utils.CuboidCfg(size=(R9.STAND_XY, R9.STAND_XY, 2.0), collision_props=sim_utils.CollisionPropertiesCfg(),
                                      visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.25, 0.25, 0.27))),
            init_state=AssetBaseCfg.InitialStateCfg(pos=(R9.BASE_X, R9.BASE_Y_RIGHT, 0.80 - 1.0)))
    else:
        for n, c in _default_camera_cfgs(cameras, depth).items():
            scene_attrs[n] = c
    for n, c in (extra_cameras or {}).items():  # L9 v2 world-fixed external cameras (ext9); None = unchanged
        scene_attrs[n] = c
    @configclass
    class QddSceneCfg(InteractiveSceneCfg):
        pass

    scene_cfg = QddSceneCfg(num_envs=1, env_spacing=4.0, replicate_physics=False)
    for k, v in scene_attrs.items():  # instance attributes: InteractiveScene reads cfg.__dict__ in this order
        setattr(scene_cfg, k, v)

    arm_joints, gj = ARM_JOINTS[arm], GRIP_JOINT[arm]
    grip_all = GRIP_ALL[arm]
    if v2r:
        arm_joints, grip_all = list(R9.V2[robot_name]["arms"][arm]["joints"]), list(R9.V2[robot_name]["arms"][arm]["fingers"])
    elif robot_name is not None:
        arm_joints, grip_all = list(R9.ARM), list(R9.FINGERS)

    @configclass
    class ActionsCfg:
        arm_action = mdp.JointPositionActionCfg(asset_name="robot", joint_names=arm_joints, scale=1.0,
                                                use_default_offset=False, preserve_order=True)
        gripper_action = mdp.JointPositionActionCfg(asset_name="robot", joint_names=grip_all, scale=1.0,
                                                    preserve_order=True,
                                                    use_default_offset=False)
    if dual:  # L9 bimanual: the other arm + gripper after the used arm's (action = [arm, grip, arm2, grip2])
        if v2r:
            arm2, grip2 = list(R9.V2[robot_name]["arms"][other]["joints"]), list(R9.V2[robot_name]["arms"][other]["fingers"])
        else:
            arm2, grip2 = ARM_JOINTS[other], GRIP_ALL[other]

        @configclass
        class ActionsCfg(ActionsCfg):  # noqa: F811
            arm2_action = mdp.JointPositionActionCfg(asset_name="robot", joint_names=arm2, scale=1.0,
                                                     use_default_offset=False, preserve_order=True)
            gripper2_action = mdp.JointPositionActionCfg(asset_name="robot", joint_names=grip2, scale=1.0,
                                                         preserve_order=True, use_default_offset=False)

    @configclass
    class ObsCfg:
        @configclass
        class Policy(ObsGroup):
            joint_pos = ObsTerm(func=mdp.joint_pos, params={"asset_cfg": SceneEntityCfg("robot")})

            def __post_init__(self):
                self.enable_corruption = False
                self.concatenate_terms = True
        policy: Policy = Policy()

    @configclass
    class EventCfg:
        reset_all = EventTerm(func=mdp.reset_scene_to_default, mode="reset")
        place_layout = EventTerm(func=_place_layout_event, mode="reset")

    @configclass
    class TermCfg:
        time_out = DoneTerm(func=mdp.time_out, time_out=True)

    @configclass
    class EnvCfg(ManagerBasedRLEnvCfg):
        observations = ObsCfg()
        actions = ActionsCfg()
        events = EventCfg()
        terminations = TermCfg()
        rewards = None
        commands = None
        curriculum = None

        def __post_init__(self):
            self.decimation = decimation  # canon §37: sim.dt 0.01, decimation 5 -> 20 Hz env step (R5: 1 -> 100 Hz)
            self.sim.dt = 0.01
            self.sim.render_interval = render_interval or self.decimation
            self.episode_length_s = 120.0
            self.sim.physx.bounce_threshold_velocity = 0.01
            self.sim.physx.friction_correlation_distance = 0.00625
            self.viewer.eye = (1.6, -1.2, 1.7)
            self.viewer.lookat = (0.4, -0.2, 0.8)

    cfg = EnvCfg()
    cfg.sim.device = _sim_device(sim_device)  # physics device; rendering stays on the GPU (AppLauncher cuda:0)
    cfg.scene = scene_cfg
    return cfg, layout


def _measure_finger_offsets(arm: str, robot: str | None = None):
    """(pad centre, fingertip) distance from the link7 origin along the gripper axis (link7 -z), from the USD's
    authored (zero-joint) pose: finger link2 world bounds expressed in the link7 frame.
    robot (L9 profile, opt-in): its EE frame and finger links; the pad centre = half the profile's pad above the tip."""
    import omni.usd
    from pxr import Gf, Usd, UsdGeom

    stage = omni.usd.get_context().get_stage()
    root = "/World/envs/env_0/Robot/ffw_sg2_follower"
    ee, fingers = f"{root}/{EE_BODY[arm]}", [f"{root}/{GRIPPER_PRIM[arm]}/{b}" for b in FINGER_BODIES[arm][1::2]]
    if robot is not None:
        from ..l9 import robot9 as R9
        root = "/World/envs/env_0/Robot"
        ee, fingers = f"{root}/{R9.EE_BODY}", [f"{root}/{b}" for b in R9.FINGER_BODIES]
    T7 = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(ee))
    inv = T7.GetInverse()
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    zs = []
    for path in fingers:  # l2, r2
        rng = bb.ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
        lo, hi = rng.GetMin(), rng.GetMax()
        for cx in (lo[0], hi[0]):
            for cy in (lo[1], hi[1]):
                for cz in (lo[2], hi[2]):
                    zs.append(inv.Transform(Gf.Vec3d(cx, cy, cz))[2])
    tip, base = -min(zs), -max(zs)
    if robot is not None:
        return float(tip - R9.PAD_LEN_M / 2), float(tip)
    return float((tip + base) / 2), float(tip)


class Env:
    """Thin wrapper over an Isaac Lab ManagerBasedRLEnv. step() takes 7 arm joint targets + gripper width (m)."""

    hard_reset = True  # every reset() recreates the PhysX scene first (physx_hard_reset.md)

    def __init__(self, seed: int, headless=True, cameras=DEFAULT_CAMERAS, arm="right", depth=True, sim_device="cpu",
                 variant="standard", decimation: int = 5, render_interval: int | None = None, task: str = "mug_tray",
                 hard_reset: bool = True, table_z: float | None = None, ws=None, lift: float | None = None,
                 objset: str | None = None, robot: str | None = None, extra_cameras: dict | None = None,
                 dual: bool = False):
        from . import randomize
        from .tasks import check_task
        if objset not in (None, "x"):
            raise ValueError(f"objset {objset!r}: None or 'x'")
        self.objset = objset  # L8-X objects (o12-o15 rigid, o17 / o18 invisible spots) only with "x"
        self.obj_ids = ["o3", "o5", "o8", "o9", "o10"] + (list(X_RIGID) + list(OBJV_IDS) if objset == "x" else [])
        self.present_ids = X_PRESENT_IDS + tuple(OBJV_IDS) if objset == "x" else PRESENT_IDS
        _LAYOUT["obj_ids"] = tuple(self.obj_ids)
        self.ws = check_ws(ws)  # L8-D per-height workspace box (None = WS_X / WS_Y)
        self.lift = None if lift is None else float(lift)  # L8-D lift flag (None = INIT_JOINTS lift, default)
        self.hard_reset = bool(hard_reset)
        self.variant = randomize.check_variant(variant)
        self.task = check_task(task)
        _check_objset(self.task, objset)
        cameras = tuple(cameras or ())
        _ensure_app(headless, bool(cameras))
        import torch
        from isaaclab.envs import ManagerBasedRLEnv

        self.torch = torch
        self.seed, self.arm, self.cameras = int(seed), arm, cameras
        tz = TABLE_TOP_Z if table_z is None else float(table_z)
        _LAYOUT["table_z"] = tz  # randomize.write_distractor_poses reads it (distractors stand on this table)
        self.robot_name = robot  # L9 profile (None = the AI Worker)
        ext = {"extra_cameras": dict(extra_cameras)} if extra_cameras else {}
        self.dual = bool(dual)
        cfg, self.layout = _build_cfg(seed, cameras, arm, depth, sim_device, variant, decimation, render_interval,
                                      task, tz, self.ws, self.lift, objset, **({"robot": robot} if robot else {}),
                                      **ext, **({"dual": True} if dual else {}))
        if ext:  # the hard reset keeps every camera's render product (callbacks muted for self.cameras)
            self.cameras = cameras + tuple(extra_cameras)
        self.sim_device = cfg.sim.device
        _LAYOUT["layout"] = self.layout
        self.randomization = randomize.sample_randomization(seed, variant, self.layout, path=self.task_path())
        _LAYOUT["rand"] = self.randomization
        self.rand_settle = None
        self.env = ManagerBasedRLEnv(cfg=cfg)
        self.scene = self.env.scene
        self.robot = self.scene["robot"]
        if not self.robot.is_fixed_base:  # canon §38 (the one deviation from the copied FFW_SG2_MOBILE_CFG)
            raise RuntimeError("robot base is not fixed")
        self.objects = {k: self.scene[k] for k in self.obj_ids}
        self.contact = {k: self.scene[f"contact_{k}"] for k in self.objects if not OBJ_GEOM[k].get("kinematic")}
        self.present = [k for k in self.present_ids if k in self.layout]  # o10 joins after P2 fires
        jn = self.robot.joint_names
        if robot is None:
            self.arm_ids = [jn.index(n) for n in ARM_JOINTS[arm]]
            self.grip_id = jn.index(GRIP_JOINT[arm])
            self.ee_idx = self.robot.body_names.index(EE_BODY[arm])
            self.finger_idx = [self.robot.body_names.index(b) for b in FINGER_BODIES[arm]]
        elif robot in ("r1pro", "g1"):  # L9 v2 profile: EE = the TCP link (pad centre, grasp frame G), offset 0
            from ..l9 import robot9 as R9
            a = R9.V2[robot]["arms"][arm]
            self.arm_ids = [jn.index(n) for n in a["joints"]]
            self.grip_ids = [jn.index(n) for n in a["fingers"]]
            self.grip_id = self.grip_ids[0]
            self.ee_idx = self.robot.body_names.index(a["tcp"])
            self.finger_bodies = tuple(a["finger_bodies"])
            self.finger_idx = [self.robot.body_names.index(b) for b in self.finger_bodies]
            self.pad_pair, self.pad_inset = (0, 1), 0.0
        else:  # L9 profile: its joints / links; finger_mid and gripper_width read pad_pair / pad_inset
            from ..l9 import robot9 as R9
            self.arm_ids = [jn.index(n) for n in R9.ARM]
            self.grip_id = jn.index(R9.FINGERS[0])
            self.ee_idx = self.robot.body_names.index(R9.EE_BODY)
            self.finger_idx = [self.robot.body_names.index(b) for b in R9.FINGER_BODIES]
            self.finger_bodies = R9.FINGER_BODIES
            self.pad_pair, self.pad_inset = (0, 1), 0.0
        self.step_dt = float(self.env.step_dt)
        self._steps = 0
        self.perturb_state = None
        self.table_top_z = tz
        if robot in ("r1pro", "g1"):  # the EE body is the TCP itself; tip = the gripper json's finger depth
            from ..l9 import robot9 as R9
            self.tcp_offset, self.tip_offset = 0.0, float(R9.V2[robot]["finger_depth_m"])
        else:
            self.tcp_offset, self.tip_offset = _measure_finger_offsets(arm, robot) if robot else _measure_finger_offsets(arm)
        self.finger_slice, self.n_finger_filters = (0, len(self.finger_idx)), len(self.finger_idx)
        self.primary = arm
        if self.dual:
            self._setup_dual(robot)
        if self.variant != "standard":
            randomize.setup_visuals(self)
            self.rand_mesh_fit = dict(randomize.MESH_FIT)

    # ---- L9 bimanual: per-arm readout contexts (use_arm) + the other arm's targets in every step
    _CTX = ("arm", "arm_ids", "grip_id", "grip_ids", "ee_idx", "finger_idx", "finger_bodies", "pad_pair", "pad_inset",
            "tcp_offset", "tip_offset", "finger_slice")

    def _setup_dual(self, robot):
        jn, bn = self.robot.joint_names, self.robot.body_names
        p = self.primary
        o = "left" if p == "right" else "right"
        self._ctx = {p: {k: getattr(self, k) for k in self._CTX if hasattr(self, k)}}
        c = {"arm": o}
        if robot is None:
            c.update(arm_ids=[jn.index(n) for n in ARM_JOINTS[o]], grip_id=jn.index(GRIP_JOINT[o]),
                     ee_idx=bn.index(EE_BODY[o]), finger_idx=[bn.index(b) for b in FINGER_BODIES[o]])
            c["tcp_offset"], c["tip_offset"] = _measure_finger_offsets(o)
        else:
            from ..l9 import robot9 as R9
            a = R9.V2[robot]["arms"][o]
            c.update(arm_ids=[jn.index(n) for n in a["joints"]], grip_ids=[jn.index(n) for n in a["fingers"]],
                     ee_idx=bn.index(a["tcp"]), finger_bodies=tuple(a["finger_bodies"]), pad_pair=(0, 1),
                     pad_inset=0.0, tcp_offset=0.0, tip_offset=float(R9.V2[robot]["finger_depth_m"]))
            c["grip_id"] = c["grip_ids"][0]
            c["finger_idx"] = [bn.index(b) for b in c["finger_bodies"]]
        n1 = self.finger_slice[1]
        if robot is None:
            nf2 = len(FINGER_BODIES[o])
        else:
            from ..l9 import robot9 as R9
            nf2 = len(R9.v2_contact_bodies(robot, o))
            self.finger_slice = (0, len(R9.v2_contact_bodies(robot, p)))
            self._ctx[p]["finger_slice"] = self.finger_slice
            n1 = self.finger_slice[1]
        c["finger_slice"] = (n1, n1 + nf2)
        self.n_finger_filters = n1 + nf2
        self._ctx[o] = c
        q = self.robot.data.joint_pos[0, c["arm_ids"]].cpu().numpy().astype(np.float32)
        self.arm2_target = (q, None)  # (joint targets, width or None = the current finger joints)

    def use_arm(self, arm: str) -> None:
        """Readouts (arm_q, ee_pose, finger_mid, gripper_width, contacts) of `arm` from now on (dual only)."""
        for k, v in self._ctx[arm].items():
            setattr(self, k, v)

    def other_arm(self) -> str:
        return "left" if self.primary == "right" else "right"


    # ---- time / stepping
    @property
    def sim_time(self) -> float:
        return self._steps * self.step_dt

    def task_path(self):
        from .tasks import TASKS
        return TASKS[self.task].target, TASKS[self.task].place

    def set_seed(self, seed: int, task: str = "mug_tray", layout: str = "task"):
        """Reuse this env for another seed (and task, R2): new layout, applied by the next reset() (one write at
        reset). Callers that do not name a task get the original mug -> tray task (pool / labeler / prefix).
        layout 'pair' (MolmoAct M4, explicit option): tasks.pair_layout, one scene for both tasks.PAIR_TASKS."""
        from .randomize import sample_randomization
        from .tasks import check_task, layout_for, layout_paths
        self.seed, self.task = int(seed), check_task(task)
        _check_objset(self.task, getattr(self, "objset", None))
        self.layout = layout_for(seed, self.task, layout, ws=getattr(self, "ws", None))
        self.layout_mode = layout
        _LAYOUT["layout"] = self.layout
        self.randomization = sample_randomization(seed, self.variant, self.layout,
                                                  path=layout_paths(self.task, layout))
        _LAYOUT["rand"] = self.randomization

    def _place_marker(self):
        """Visual-only marker o11: USD pose (no physics prim), on the table when the layout has it, else parked."""
        import omni.usd

        from .randomize import _set_pose
        prim = omni.usd.get_context().get_stage().GetPrimAtPath("/World/envs/env_0/Marker")
        if prim.IsValid():
            _set_pose(prim, tuple(float(v) for v in self._marker_pos()))

    def _marker_pos(self, k: str = "o11") -> np.ndarray:
        g = OBJ_GEOM[k]
        h = g.get("height", 2 * g["half_extents"][2])
        if k in self.layout:
            x, y = self.layout[k][:2]
            top = getattr(self, "virtual_top", {}).get(k, self.table_top_z)  # o19: the furniture surface top
            return np.array([x, y, top + h / 2 if k not in VIRTUAL_PLACES else top - h / 2])
        return np.array([*PARK_XY.get(k, (-3.0, -3.3)), h / 2])

    def set_virtual_surface(self, k: str, top_z: float, xy_box) -> None:
        """L8-X: a furniture surface (static collider) as the place object k ('o19'): its top and box for this
        episode (OBJ_GEOM half extents follow the box; the layout entry is its centre)."""
        (x0, x1), (y0, y1) = xy_box
        g = OBJ_GEOM[k]
        g["size"] = (float(x1 - x0), float(y1 - y0), 0.002)
        g["half_extents"] = (g["size"][0] / 2, g["size"][1] / 2, 0.001)
        g["footprint_r"] = float(math.hypot(g["half_extents"][0], g["half_extents"][1]))
        if not hasattr(self, "virtual_top"):
            self.virtual_top = {}
        self.virtual_top[k] = float(top_z)

    def _recreate_physx_scene(self):
        """Timeline stop/play (SimulationContext.reset(soft=False)): a new PhysX scene, so no episode starts from
        PhysX-internal state (contact pairs / islands / solver order) left by earlier runs in this process -- that
        state made one seed replay into one of a few discrete trajectories (pool_replay_debug.md). On PLAY Isaac Lab
        re-creates the PhysX views of every asset and sensor (same Python objects). Cameras are left as they are: they
        hold no PhysX handle, and their re-init would add a new render product per episode.
        The new scene is built from the USD poses, which are the make_env seed's layout; so while stopped the objects
        get this seed's reset poses (what make_env(seed) authors) -- else a process made with another seed builds a
        different scene (DEV 11 after make_env(5): o8 on the table instead of parked, mug 10 mm off; physx_hard_reset.md).
        """
        sim = self.env.sim
        cams = [self.scene[n] for n in self.cameras]
        for c in cams:
            c._invalidate_initialize_callback = c._initialize_callback = _no_callback
        sim._disable_app_control_on_stop_handle = True  # Isaac Lab otherwise waits for PLAY inside the STOP event
        try:
            sim.stop()
            for k in self.objects:
                _author_usd_pose(f"/World/envs/env_0/{k.upper()}", *_object_reset_pose(k, self.layout))
            sim.reset(soft=False)
        finally:
            sim._disable_app_control_on_stop_handle = False
            for c in cams:
                del c._invalidate_initialize_callback, c._initialize_callback
        self.env._sim_step_counter = 0  # render_interval phase counted from the episode start

    def reset(self, settle_s: float = 1.0):
        """Reset once (write default state once), then let objects settle with the arm holding its pose.
        With hard_reset (default) the PhysX scene is recreated first, so the episode depends only on the seed."""
        _LAYOUT["layout"] = self.layout
        _LAYOUT["rand"] = self.randomization
        if self.hard_reset:
            self._recreate_physx_scene()
        if self.variant != "standard":
            from .randomize import apply_visuals
            apply_visuals(self, self.randomization)
        self._place_marker()
        self.present = [k for k in getattr(self, "present_ids", PRESENT_IDS) if k in self.layout]
        self.perturb_state = None
        if hasattr(self, "carry_start_xy"):
            del self.carry_start_xy
        self.env.reset(seed=self.seed)
        self._steps = 0
        q = self.robot.data.joint_pos[0]
        hold = np.concatenate([q[self.arm_ids].cpu().numpy(), [self.grip_max_w]])
        for _ in range(int(round(settle_s / self.step_dt))):
            self.step(hold)
        if self.variant != "standard":  # distractor offset from its sampled pose after settling (spawn check)
            from .randomize import distractor_positions, distractor_report
            self.rand_settle = distractor_report(self)
            self.rand_settle_pos = distractor_positions(self)
        self._steps = 0  # episode clock starts after settling
        return hold

    # ---- L9 generic grip layer (harvest/l9/hand9.py; opt-in L9_GRIP_LAYER=1, unset: gap_table() is None and every
    # caller below keeps its old path): opening <-> finger joints and the width readout through the gripper's
    # measured free-gap table, effort = the max over ALL finger joints (never one joint)
    def gap_table(self, arm: str | None = None):
        from ..l9 import hand9 as H
        return H.active_table(getattr(self, "robot_name", None), arm or self.arm)

    def _finger_order(self, arm: str) -> list:
        """This robot's finger joints of `arm` in its action order."""
        rn = getattr(self, "robot_name", None)
        from ..l9 import robot9 as R9
        if rn in R9.V2_PROFILES:
            return list(R9.V2[rn]["arms"][arm]["fingers"])
        return list(R9.FINGERS) if rn is not None else list(GRIP_ALL[arm])

    def _gl_fingers(self, t, w: float, arm: str) -> list:
        m = t.joints_for_gap(w)
        return [m[j] for j in self._finger_order(arm)]

    def _gl_ids(self, t) -> list:
        c = self.__dict__.setdefault("_gl_idx", {})
        if t.name not in c:
            jn = self.robot.joint_names
            c[t.name] = [jn.index(j) for j in t.joints]
        return c[t.name]

    def gripper_tcp_gap(self) -> float | None:
        """(grip layer) the measured gap in the TCP plane (contact-width reading); None when the layer is off."""
        t = self.gap_table()
        if t is None:
            return None
        return t.tcp_gap_of_q(self.robot.data.joint_pos[0, self._gl_ids(t)].cpu().numpy())

    def finger_forces(self, k: str) -> dict | None:
        """(grip layer) contact force magnitude of object k on each finger contact body (this arm), None when the
        layer is off or k has no contact sensor."""
        if self.gap_table() is None or k not in getattr(self, "contact", {}):
            return None
        fb = getattr(self, "finger_bodies", None) or FINGER_BODIES[self.arm]  # = the sensor filter order (oracle_state)
        f0, f1 = getattr(self, "finger_slice", (0, len(fb)))
        mag = self.contact[k].data.force_matrix_w[0, 0].norm(dim=-1).cpu().numpy()
        return {b: float(m) for b, m in zip(fb, mag[f0:f1])}

    @property
    def grip_max_w(self) -> float:
        t = self.gap_table()
        if t is not None:
            return t.max_gap
        if getattr(self, "robot_name", None) is None:
            return GRIP_MAX_W
        from ..l9 import robot9 as R9
        if self.robot_name in R9.V2_PROFILES:
            return float(R9.V2[self.robot_name]["grip_max_w"])
        return R9.GRIP_MAX_W

    def step(self, q_target: np.ndarray) -> None:
        q_target = np.asarray(q_target, dtype=np.float32)
        if getattr(self, "dual", False) and self.arm != self.primary:
            raise RuntimeError("dual: step() takes the primary arm's targets; use_arm(primary) first")
        t = self.gap_table()
        if t is not None:  # grip layer: the opening is a measured free gap -> finger joints by the gap table
            n = len(self.arm_ids)
            a = np.concatenate([q_target[:n], self._gl_fingers(t, float(q_target[n]), self.arm)]).astype(np.float32)
        elif getattr(self, "robot_name", None) in ("r1pro", "g1"):  # L9 v2: arm joints + the profile's width map
            from ..l9 import robot9 as R9
            n = len(self.arm_ids)
            w = R9.v2_width_to_joints(self.robot_name, self.arm, float(q_target[n]))
            g = [w[j] for j in R9.V2[self.robot_name]["arms"][self.arm]["fingers"]]
            a = np.concatenate([q_target[:n], g]).astype(np.float32)
        elif getattr(self, "robot_name", None) is not None:  # L9 profile: two symmetric prismatic fingers
            from ..l9 import robot9 as R9
            g = R9.franka_width_to_joint(float(q_target[7]))
            a = np.concatenate([q_target[:7], [g, g]]).astype(np.float32)
        else:
            g = width_to_joint(float(q_target[7]))
            a = np.concatenate([q_target[:7], [g, g, g, g]]).astype(np.float32)
        if getattr(self, "dual", False):
            a = np.concatenate([a, self._arm2_action()]).astype(np.float32)
        self.env.step(self.torch.as_tensor(a, device=self.env.device).unsqueeze(0))
        self._steps += 1

    def _arm2_action(self) -> np.ndarray:
        """The other arm's action part (joint targets + its finger joints for the held width)."""
        o = self.other_arm()
        c = self._ctx[o]
        q, w = self.arm2_target
        t = self.gap_table(o) if w is not None else None
        if t is not None:  # grip layer
            g = self._gl_fingers(t, float(w), o)
        elif getattr(self, "robot_name", None) in ("r1pro", "g1"):
            from ..l9 import robot9 as R9
            ids = c["grip_ids"]
            if w is None:
                g = self.robot.data.joint_pos[0, ids].cpu().numpy()
            else:
                m = R9.v2_width_to_joints(self.robot_name, o, float(w))
                g = [m[j] for j in R9.V2[self.robot_name]["arms"][o]["fingers"]]
        else:
            if w is None:
                g = [float(self.robot.data.joint_pos[0, c["grip_id"]])] * 4
            else:
                g = [width_to_joint(float(w))] * 4
        return np.concatenate([np.asarray(q, np.float32), np.asarray(g, np.float32)])

    def set_arm2_target(self, q, width=None) -> None:
        """Joint targets (and gripper width; None = keep the fingers where they are) of the other arm (dual)."""
        self.arm2_target = (np.asarray(q, np.float32), None if width is None else float(width))

    # ---- robot readouts (world frame)
    def arm_q(self) -> np.ndarray:
        return self.robot.data.joint_pos[0, self.arm_ids].cpu().numpy()

    def ee_pose(self):
        d = self.robot.data
        return d.body_pos_w[0, self.ee_idx].cpu().numpy(), d.body_quat_w[0, self.ee_idx].cpu().numpy()

    def finger_mid(self) -> np.ndarray:
        if getattr(self, "robot_name", None) is not None:  # L9 profile: the TCP (pad centre) on the EE frame's -z
            from .planner import _quat_rot
            p, q = self.ee_pose()
            return p + _quat_rot(q, (0.0, 0.0, -self.tcp_offset))
        a, b = getattr(self, "pad_pair", (1, 3))
        p = self.robot.data.body_pos_w[0, self.finger_idx[a]] + self.robot.data.body_pos_w[0, self.finger_idx[b]]
        return (p / 2).cpu().numpy()

    def gripper_width(self) -> float:
        """Measured pad gap: finger link2 origin distance minus the pad inset (not the joint1 map)."""
        t = self.gap_table()
        if t is not None:  # grip layer: the measured free gap of the current finger joints
            return t.gap_of_q(self.robot.data.joint_pos[0, self._gl_ids(t)].cpu().numpy())
        if getattr(self, "robot_name", None) in ("r1pro", "g1"):  # L9 v2: from the measured finger joints
            from ..l9 import robot9 as R9
            q = self.robot.data.joint_pos[0, self.grip_ids].cpu().numpy()
            return R9.v2_joints_to_width(self.robot_name, self.arm, q)
        a, b = getattr(self, "pad_pair", (1, 3))
        d = self.robot.data.body_pos_w[0, self.finger_idx[a]] - self.robot.data.body_pos_w[0, self.finger_idx[b]]
        return max(float(d.norm()) - getattr(self, "pad_inset", PAD_INSET_M), 0.0)

    def gripper_effort(self) -> float:
        t = self.gap_table()
        if t is not None:  # grip layer: the largest torque over ALL finger joints (g1b H1: one joint read ~0)
            return float(self.robot.data.applied_torque[0, self._gl_ids(t)].abs().max())
        if getattr(self, "robot_name", None) == "g1":  # g1b H1: grip_id = thumb_0, whose target never moves (its torque
            # stays ~0 while the other six joints squeeze at the 2.45 N m cap): the largest finger torque instead
            return float(self.robot.data.applied_torque[0, self.grip_ids].abs().max())
        return float(self.robot.data.applied_torque[0, self.grip_id].abs())

    def object_pose(self, k):
        if k in VISUAL_ONLY or k in X_VISUAL_ONLY:  # the marker is not a physics body: its pose is the layout pose
            return self._marker_pos(k), np.array([1.0, 0.0, 0.0, 0.0])
        d = self.objects[k].data
        p, q = d.root_pos_w[0].cpu().numpy(), d.root_quat_w[0].cpu().numpy()
        if OBJ_GEOM[k]["shape"] == "mesh":  # L8-X mesh: USD root -> canonical (bbox centre, upright = identity)
            from .objv import canonical_from_root
            c, qc = canonical_from_root(OBJ_GEOM[k], p, q)
            return c, np.asarray(qc, float)
        return p, q

    def object_vel(self, k) -> float:
        return float(self.objects[k].data.root_lin_vel_w[0].norm())

    def write_object_pose(self, k, pos_w, quat_wxyz=(1.0, 0.0, 0.0, 0.0)):
        """One-shot pose write (perturbations only; never call every step)."""
        t = self.torch
        pose = t.tensor([[*pos_w, *quat_wxyz]], dtype=t.float32, device=self.env.device)
        self.objects[k].write_root_pose_to_sim(pose)
        self.objects[k].write_root_velocity_to_sim(t.zeros((1, 6), device=self.env.device))

    # ---- cameras
    def camera_rgb(self, name="cam_head") -> np.ndarray:
        return self.scene[name].data.output["rgb"][0, ..., :3].cpu().numpy().astype(np.uint8)

    def camera_depth(self, name="cam_head") -> np.ndarray:
        return self.scene[name].data.output["distance_to_image_plane"][0, ..., 0].cpu().numpy()

    def close(self):
        self.env.close()


def _no_callback(event):
    pass


# ---------------------------------------------------------------------------------------------- L9 v2 colliders
# Opt-in collider override of mesh objects (harvest/l9/gtest9.apply_collider, docs/book P167): a catalog row with
# collider = 'sdf' (OBJ_GEOM 'collider'), or, with the environment variable L9V2_COLLIDERS = 1 (or a json path), the
# objects listed in /data/harvest/l9v2/collider_override.json get their render meshes as SDF colliders. Without
# either, the spawn config is exactly the v1 one.
COLLIDER_MAP = "/data/harvest/l9v2/collider_override.json"
_COLLIDERS = {}  # prim name (K.upper()) -> mode, read by spawn_usd_collider
_COLLIDER_MAP = {}


def _collider_spawn(k: str, g: dict) -> dict:
    import os
    mode = g.get("collider")
    env = os.environ.get("L9V2_COLLIDERS", "")
    if not mode and env and env != "0":
        path = env if env.endswith(".json") else COLLIDER_MAP
        if path not in _COLLIDER_MAP:
            import json
            _COLLIDER_MAP[path] = json.load(open(path)).get("objects", {}) if os.path.exists(path) else {}
        mode = _COLLIDER_MAP[path].get(k)
    if not mode or mode == "none":
        return {}
    _COLLIDERS[k.upper()] = mode
    return {"func": spawn_usd_collider}


def spawn_usd_collider(prim_path, cfg, translation=None, orientation=None, **kwargs):
    """The Isaac Lab USD spawner, then gtest9.apply_collider on every spawned copy (mode from _COLLIDERS by the
    prim name)."""
    import omni.usd
    from isaaclab.sim.spawners.from_files import spawn_from_usd
    from isaaclab.sim.utils import find_matching_prim_paths

    from ..l9.gtest9 import apply_collider
    prim = spawn_from_usd(prim_path, cfg, translation=translation, orientation=orientation, **kwargs)
    stage = omni.usd.get_context().get_stage()
    mode = _COLLIDERS[prim_path.rsplit("/", 1)[-1]]
    for path in find_matching_prim_paths(prim_path):
        n = apply_collider(stage, path, mode)
        print(f"[l9v2 collider] {path} {mode} render meshes {n}", flush=True)
    return prim


def spawn_open_box(prim_path, cfg, translation=None, orientation=None, **kwargs):
    """L8-X container (OBJ_GEOM shape "openbox", size (x, y, h), wall t): one rigid body = the Isaac Lab cuboid
    spawner for the floor (t thick, bottom at -h/2 of the body origin; rigid body, mass, contact report, materials)
    + four wall cubes (colliders, same materials) as extra children of its geometry prim."""
    import omni.usd
    from isaaclab.sim import schemas
    from isaaclab.sim.spawners.shapes import spawn_cuboid
    from isaaclab.sim.utils import bind_physics_material, bind_visual_material
    from pxr import Gf, UsdGeom, UsdPhysics

    from .randomize import _set_pose
    path = prim_path.replace("env_.*", "env_0")
    sx, sy, h = (float(v) for v in cfg.size)
    t = float(OBJ_GEOM["o15"]["wall"])
    prim = spawn_cuboid(path, cfg.replace(size=(sx, sy, t)), translation=translation, orientation=orientation,
                        **kwargs)
    stage = omni.usd.get_context().get_stage()
    _set_pose(stage.GetPrimAtPath(path + "/geometry/mesh"), (0.0, 0.0, -h / 2 + t / 2))
    geo = path + "/geometry"
    vis = cfg.visual_material_path if cfg.visual_material_path.startswith("/") else f"{geo}/{cfg.visual_material_path}"
    phy = cfg.physics_material_path if cfg.physics_material_path.startswith("/") else \
        f"{geo}/{cfg.physics_material_path}"
    walls = [((0.0, sy / 2 - t / 2), (sx, t)), ((0.0, -sy / 2 + t / 2), (sx, t)),
             ((sx / 2 - t / 2, 0.0), (t, sy - 2 * t)), ((-sx / 2 + t / 2, 0.0), (t, sy - 2 * t))]
    for i, ((cx, cy), (lx, ly)) in enumerate(walls):
        p = f"{geo}/wall{i}"
        cube = UsdGeom.Cube.Define(stage, p)
        cube.GetSizeAttr().Set(1.0)
        xf = UsdGeom.Xformable(cube)
        xf.AddTranslateOp().Set(Gf.Vec3d(cx, cy, t / 2))  # from the floor top to the rim (z -h/2 + t .. h/2)
        xf.AddScaleOp().Set(Gf.Vec3f(lx, ly, h - t))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        if cfg.collision_props is not None:
            schemas.define_collision_properties(p, cfg.collision_props)
        if cfg.visual_material is not None:
            bind_visual_material(p, vis)
        if cfg.physics_material is not None:
            bind_physics_material(p, phy)
    return prim


def _author_usd_pose(path: str, pos, quat_wxyz) -> None:
    """USD pose of a prim under /World/envs/env_0 (env-local, like _object_reset_pose); only while stopped."""
    import omni.usd

    from .randomize import _set_pose
    _set_pose(omni.usd.get_context().get_stage().GetPrimAtPath(path), tuple(pos), tuple(quat_wxyz))


def make_env(seed: int, headless: bool = True, cameras=DEFAULT_CAMERAS, arm: str = "right", depth: bool = True,
             sim_device: str = "cpu", variant: str = "standard", decimation: int = 5,
             render_interval: int | None = None, task: str = "mug_tray", hard_reset: bool = True,
             table_z: float | None = None, ws=None, lift: float | None = None,
             objset: str | None = None, robot: str | None = None, extra_cameras: dict | None = None,
             dual: bool = False) -> Env:
    """cameras: names from KNOWN_CAMERAS (real robot cameras); () for no rendering.
    task: tasks.TASK_IDS (R2); the default is the original mug -> tray task with the standard layout.
    sim_device: 'cpu' (PhysX on CPU, default, canon §48) or 'cuda' (GPU PhysX, the v1 setting).
    variant: 'standard' (today's scene, unchanged), 'random' (5 axes from the TEST pool, evaluation only) or 'dr'
    (5 axes from the disjoint TRAIN pool, training-time domain randomization); randomize.py, canon §34/§52.
    decimation: physics substeps (10 ms) per env step, 5 = the 20 Hz pool/label setting; the closed-loop runtime (R5,
    D23 §3) uses 1 (100 Hz). render_interval: physics substeps per render (default = decimation).
    hard_reset: True (default) = every reset() recreates the PhysX scene, so an episode depends only on its seed
    (physx_hard_reset.md); False = the old soft reset, only for replaying episodes recorded before (history-dependent,
    pool_replay_debug.md).
    table_z: None (default) = TABLE_TOP_Z 0.85 (every path unchanged); a float moves the table and the objects
    standing on it (E-PT OOD-H, docs/stage3/prereg_pt.md; any variant since L8-D: pool distractors stand on it too).
    ws: None (default) = WS_X / WS_Y; a box ((x0, x1), (y0, y1)) for the task layouts (L8-D per-height box, gate G-H).
    lift: None (default) = INIT_JOINTS lift_joint; a float = the lift joint's start / hold position (L8-D lift flag,
    default off, docs/stage3/prereg_l8d.md). The head pitch is never changed.
    objset: None (default) = the five objects o3-o10; "x" = + the L8-X objects (X_OBJ_GEOM: stand, blue mug, small
    cup, open bin, invisible relational spots; docs/research/l8x_env_suite_design_2026-09-27.md)."""
    kw = {} if ws is None and lift is None and objset is None else {"ws": ws, "lift": lift, "objset": objset}
    if robot is not None:  # L9 robot profile (spec §9.1); None = the AI Worker (unchanged)
        kw = {"ws": ws, "lift": lift, "objset": objset, "robot": robot}
    if extra_cameras:  # {scene name: CameraCfg} world-fixed extra cameras (L9 v2 ext9); None / {} = unchanged
        kw = dict({"ws": ws, "lift": lift, "objset": objset}, **kw, extra_cameras=extra_cameras)
    if dual:  # L9 bimanual (opt-in; default False = every existing call unchanged): forward to Env(dual=True)
        kw = dict({"ws": ws, "lift": lift, "objset": objset}, **kw, dual=True)
    return Env(seed, headless=headless, cameras=cameras, arm=arm, depth=depth, sim_device=sim_device, variant=variant,
               decimation=decimation, render_interval=render_interval, task=task, hard_reset=hard_reset,
               table_z=table_z, **kw)
