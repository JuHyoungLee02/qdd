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
VISUAL_ONLY = ("o11",)
PRESENT_IDS = ("o3", "o5", "o8", "o9", "o11")  # objects in play when the layout has them (o10 joins after P2 fires)
for _g in OBJ_GEOM.values():
    if _g["shape"] in ("cylinder", "marker"):
        _g["half_extents"] = (_g["radius"], _g["radius"], _g["height"] / 2)
    else:
        _g["half_extents"] = tuple(s / 2 for s in _g["size"])
    _g["footprint_r"] = float(math.hypot(_g["half_extents"][0], _g["half_extents"][1])) if _g["shape"] == "cuboid" \
        else _g["radius"]

# right-arm top-down workspace (world xy), measured reach margin from the shoulder at (-0.02, -0.23, 1.33)
WS_X = (0.36, 0.48)
WS_Y = (-0.40, -0.06)
DISTRACTOR_X = (0.34, 0.56)
DISTRACTOR_Y = (-0.46, 0.08)
PARK_XY = {"o8": (-3.0, 3.0), "o9": (-3.3, 3.0), "o10": (-3.6, 3.0),  # parked behind the robot (out of the head view)
           "o11": (-3.0, -3.0)}

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
                           "gripper_r_rh_p12_rn_r2")}
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


def joint_to_width(q: float) -> float:
    return float(np.interp(q, _GQ, _GW))


def width_to_joint(w: float) -> float:
    return float(np.interp(w, _GW[::-1], _GQ[::-1]))


def sample_layout(seed: int) -> dict:
    """Initial placement from the seed: {obj_id: (x, y, yaw)} in world xy (table frame xy is the same)."""
    rng = np.random.default_rng([int(seed), 11])
    fr = {k: g["footprint_r"] for k, g in OBJ_GEOM.items()}
    for _ in range(10000):
        t = (rng.uniform(WS_X[0] + 0.02, WS_X[1]), rng.uniform(WS_Y[0] + 0.03, WS_Y[1] - 0.03), 0.0)
        m = (rng.uniform(*WS_X), rng.uniform(*WS_Y), 0.0)
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
        _APP = AppLauncher(headless=headless, device="cuda:0", enable_cameras=cameras).app
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


def _object_reset_pose(k: str, layout: dict):
    g = OBJ_GEOM[k]
    if k in layout:
        x, y, yaw = layout[k]
        return (x, y, TABLE_TOP_Z + g["half_extents"][2] + 0.001), yaw_quat(yaw)
    x, y = PARK_XY.get(k, (-2.4 - 0.3 * len(k), 2.4))
    return (x, y, g["half_extents"][2] + 0.001), yaw_quat(0.0)


def _place_layout_event(env, env_ids):
    """Reset event: put every object at its layout pose (or parked), zero velocity. Runs once per reset.
    Also sets the PD targets of the joints outside the action (left arm, head, lift) to their defaults; without
    this they are driven to 0 (Isaac Lab leaves joint_pos_target at 0 for joints no action term owns)."""
    import torch
    rob = env.scene["robot"]
    rob.set_joint_position_target(rob.data.default_joint_pos[env_ids], env_ids=env_ids)
    for k in ("o3", "o5", "o8", "o9", "o10"):
        pos, quat = _object_reset_pose(k, _LAYOUT["layout"])
        o = env.scene[k]
        p = torch.tensor([[*pos, *quat]], dtype=torch.float32, device=env.device)
        p[:, :3] += env.scene.env_origins[env_ids]
        o.write_root_pose_to_sim(p, env_ids=env_ids)
        o.write_root_velocity_to_sim(torch.zeros((len(env_ids), 6), device=env.device), env_ids=env_ids)
    if _LAYOUT.get("rand"):  # variant random / dr: this seed's tabletop distractors (randomize.py)
        from .randomize import write_distractor_poses
        write_distractor_poses(env, env_ids, _LAYOUT["rand"])


def _build_cfg(seed: int, cameras, arm: str, depth: bool, sim_device: str = "cpu", variant: str = "standard",
               decimation: int = 5, render_interval: int | None = None, task: str = "mug_tray"):
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

    if arm != "right":
        raise NotImplementedError("single right arm only (T11)")
    from .tasks import task_layout
    layout = task_layout(seed, task)  # mug_tray = sample_layout(seed)
    robot_prefix = "{ENV_REGEX_NS}/Robot/ffw_sg2_follower"
    finger_paths = [f"{robot_prefix}/right_gripper/{b}" for b in FINGER_BODIES[arm]]
    obj_ids = ["o3", "o5", "o8", "o9", "o10"]

    def obj_cfg(k):
        g = OBJ_GEOM[k]
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
        else:
            spawn = sim_utils.CuboidCfg(size=g["size"], **common)
        x, y, yaw = layout.get(k, (*PARK_XY.get(k, (-3.9, 3.0)), 0.0))
        z = (TABLE_TOP_Z if k in layout else 0.0) + g["half_extents"][2] + 0.001
        return RigidObjectCfg(prim_path="{ENV_REGEX_NS}/" + k.upper(), spawn=spawn,
                              init_state=RigidObjectCfg.InitialStateCfg(pos=(x, y, z), rot=yaw_quat(yaw)))

    def contact_cfg(k):
        others = [f"{{ENV_REGEX_NS}}/{j.upper()}" for j in obj_ids if j != k]
        return ContactSensorCfg(prim_path="{ENV_REGEX_NS}/" + k.upper(), update_period=0.0, history_length=0,
                                filter_prim_paths_expr=finger_paths + others)

    robot = _robot_cfg()
    robot = robot.replace(init_state=robot.init_state.replace(joint_pos={**robot.init_state.joint_pos, **INIT_JOINTS}))

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
            init_state=AssetBaseCfg.InitialStateCfg(pos=(*TABLE_CENTER_XY, TABLE_TOP_Z - TABLE_SIZE[2] / 2))),
    }
    for k in obj_ids:
        scene_attrs[k] = obj_cfg(k)
        scene_attrs[f"contact_{k}"] = contact_cfg(k)
    if variant != "standard":  # random / dr: one parked rigid body per pool distractor (their own colliders only)
        from .randomize import distractor_scene_cfgs, randomized_table_cfg
        scene_attrs.update(distractor_scene_cfgs(variant))
        scene_attrs["table"] = randomized_table_cfg(scene_attrs["table"])  # same table + own material (visual)
    mk = OBJ_GEOM["o11"]  # R2 visual-only task marker (no collider / rigid body): parked, moved at reset (USD pose)
    scene_attrs["marker"] = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Marker",
        spawn=sim_utils.CylinderCfg(radius=mk["radius"], height=mk["height"], axis="Z",
                                    visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=mk["color"])),
        init_state=AssetBaseCfg.InitialStateCfg(pos=(*PARK_XY["o11"], mk["height"] / 2)))
    for n, c in _default_camera_cfgs(cameras, depth).items():
        scene_attrs[n] = c
    @configclass
    class QddSceneCfg(InteractiveSceneCfg):
        pass

    scene_cfg = QddSceneCfg(num_envs=1, env_spacing=4.0, replicate_physics=False)
    for k, v in scene_attrs.items():  # instance attributes: InteractiveScene reads cfg.__dict__ in this order
        setattr(scene_cfg, k, v)

    arm_joints, gj = ARM_JOINTS[arm], GRIP_JOINT[arm]

    @configclass
    class ActionsCfg:
        arm_action = mdp.JointPositionActionCfg(asset_name="robot", joint_names=arm_joints, scale=1.0,
                                                use_default_offset=False, preserve_order=True)
        gripper_action = mdp.JointPositionActionCfg(asset_name="robot", joint_names=GRIP_ALL[arm], scale=1.0,
                                                    preserve_order=True,
                                                    use_default_offset=False)

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


def _measure_finger_offsets(arm: str):
    """(pad centre, fingertip) distance from the link7 origin along the gripper axis (link7 -z), from the USD's
    authored (zero-joint) pose: finger link2 world bounds expressed in the link7 frame."""
    import omni.usd
    from pxr import Gf, Usd, UsdGeom

    stage = omni.usd.get_context().get_stage()
    root = "/World/envs/env_0/Robot/ffw_sg2_follower"
    T7 = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(f"{root}/{EE_BODY[arm]}"))
    inv = T7.GetInverse()
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    zs = []
    for b in FINGER_BODIES[arm][1::2]:  # l2, r2
        rng = bb.ComputeWorldBound(stage.GetPrimAtPath(f"{root}/right_gripper/{b}")).ComputeAlignedRange()
        lo, hi = rng.GetMin(), rng.GetMax()
        for cx in (lo[0], hi[0]):
            for cy in (lo[1], hi[1]):
                for cz in (lo[2], hi[2]):
                    zs.append(inv.Transform(Gf.Vec3d(cx, cy, cz))[2])
    tip, base = -min(zs), -max(zs)
    return float((tip + base) / 2), float(tip)


class Env:
    """Thin wrapper over an Isaac Lab ManagerBasedRLEnv. step() takes 7 arm joint targets + gripper width (m)."""

    def __init__(self, seed: int, headless=True, cameras=DEFAULT_CAMERAS, arm="right", depth=True, sim_device="cpu",
                 variant="standard", decimation: int = 5, render_interval: int | None = None, task: str = "mug_tray"):
        from . import randomize
        from .tasks import check_task
        self.variant = randomize.check_variant(variant)
        self.task = check_task(task)
        cameras = tuple(cameras or ())
        _ensure_app(headless, bool(cameras))
        import torch
        from isaaclab.envs import ManagerBasedRLEnv

        self.torch = torch
        self.seed, self.arm, self.cameras = int(seed), arm, cameras
        cfg, self.layout = _build_cfg(seed, cameras, arm, depth, sim_device, variant, decimation, render_interval,
                                      task)
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
        self.objects = {k: self.scene[k] for k in ("o3", "o5", "o8", "o9", "o10")}
        self.contact = {k: self.scene[f"contact_{k}"] for k in self.objects}
        self.present = [k for k in PRESENT_IDS if k in self.layout]  # o10 joins after P2 fires
        jn = self.robot.joint_names
        self.arm_ids = [jn.index(n) for n in ARM_JOINTS[arm]]
        self.grip_id = jn.index(GRIP_JOINT[arm])
        self.ee_idx = self.robot.body_names.index(EE_BODY[arm])
        self.finger_idx = [self.robot.body_names.index(b) for b in FINGER_BODIES[arm]]
        self.step_dt = float(self.env.step_dt)
        self._steps = 0
        self.perturb_state = None
        self.table_top_z = TABLE_TOP_Z
        self.tcp_offset, self.tip_offset = _measure_finger_offsets(arm)
        if self.variant != "standard":
            randomize.setup_visuals(self)
            self.rand_mesh_fit = dict(randomize.MESH_FIT)


    # ---- time / stepping
    @property
    def sim_time(self) -> float:
        return self._steps * self.step_dt

    def task_path(self):
        from .tasks import TASKS
        return TASKS[self.task].target, TASKS[self.task].place

    def set_seed(self, seed: int, task: str = "mug_tray"):
        """Reuse this env for another seed (and task, R2): new layout, applied by the next reset() (one write at
        reset). Callers that do not name a task get the original mug -> tray task (pool / labeler / prefix)."""
        from .randomize import sample_randomization
        from .tasks import check_task, task_layout
        self.seed, self.task = int(seed), check_task(task)
        self.layout = task_layout(seed, self.task)
        _LAYOUT["layout"] = self.layout
        self.randomization = sample_randomization(seed, self.variant, self.layout, path=self.task_path())
        _LAYOUT["rand"] = self.randomization

    def _place_marker(self):
        """Visual-only marker o11: USD pose (no physics prim), on the table when the layout has it, else parked."""
        import omni.usd

        from .randomize import _set_pose
        prim = omni.usd.get_context().get_stage().GetPrimAtPath("/World/envs/env_0/Marker")
        if prim.IsValid():
            _set_pose(prim, tuple(float(v) for v in self._marker_pos()))

    def _marker_pos(self) -> np.ndarray:
        g = OBJ_GEOM["o11"]
        if "o11" in self.layout:
            x, y = self.layout["o11"][:2]
            return np.array([x, y, TABLE_TOP_Z + g["height"] / 2])
        return np.array([*PARK_XY["o11"], g["height"] / 2])

    def reset(self, settle_s: float = 1.0):
        """Reset once (write default state once), then let objects settle with the arm holding its pose."""
        _LAYOUT["layout"] = self.layout
        _LAYOUT["rand"] = self.randomization
        if self.variant != "standard":
            from .randomize import apply_visuals
            apply_visuals(self, self.randomization)
        self._place_marker()
        self.present = [k for k in PRESENT_IDS if k in self.layout]
        self.perturb_state = None
        if hasattr(self, "carry_start_xy"):
            del self.carry_start_xy
        self.env.reset(seed=self.seed)
        self._steps = 0
        q = self.robot.data.joint_pos[0]
        hold = np.concatenate([q[self.arm_ids].cpu().numpy(), [GRIP_MAX_W]])
        for _ in range(int(round(settle_s / self.step_dt))):
            self.step(hold)
        if self.variant != "standard":  # distractor offset from its sampled pose after settling (spawn check)
            from .randomize import distractor_positions, distractor_report
            self.rand_settle = distractor_report(self)
            self.rand_settle_pos = distractor_positions(self)
        self._steps = 0  # episode clock starts after settling
        return hold

    def step(self, q_target: np.ndarray) -> None:
        q_target = np.asarray(q_target, dtype=np.float32)
        g = width_to_joint(float(q_target[7]))
        a = np.concatenate([q_target[:7], [g, g, g, g]]).astype(np.float32)
        self.env.step(self.torch.as_tensor(a, device=self.env.device).unsqueeze(0))
        self._steps += 1

    # ---- robot readouts (world frame)
    def arm_q(self) -> np.ndarray:
        return self.robot.data.joint_pos[0, self.arm_ids].cpu().numpy()

    def ee_pose(self):
        d = self.robot.data
        return d.body_pos_w[0, self.ee_idx].cpu().numpy(), d.body_quat_w[0, self.ee_idx].cpu().numpy()

    def finger_mid(self) -> np.ndarray:
        p = self.robot.data.body_pos_w[0, self.finger_idx[1]] + self.robot.data.body_pos_w[0, self.finger_idx[3]]
        return (p / 2).cpu().numpy()

    def gripper_width(self) -> float:
        """Measured pad gap: finger link2 origin distance minus the pad inset (not the joint1 map)."""
        d = self.robot.data.body_pos_w[0, self.finger_idx[1]] - self.robot.data.body_pos_w[0, self.finger_idx[3]]
        return max(float(d.norm()) - PAD_INSET_M, 0.0)

    def gripper_effort(self) -> float:
        return float(self.robot.data.applied_torque[0, self.grip_id].abs())

    def object_pose(self, k):
        if k in VISUAL_ONLY:  # the marker is not a physics body: its pose is the layout pose
            return self._marker_pos(), np.array([1.0, 0.0, 0.0, 0.0])
        d = self.objects[k].data
        return d.root_pos_w[0].cpu().numpy(), d.root_quat_w[0].cpu().numpy()

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


def make_env(seed: int, headless: bool = True, cameras=DEFAULT_CAMERAS, arm: str = "right", depth: bool = True,
             sim_device: str = "cpu", variant: str = "standard", decimation: int = 5,
             render_interval: int | None = None, task: str = "mug_tray") -> Env:
    """cameras: names from KNOWN_CAMERAS (real robot cameras); () for no rendering.
    task: tasks.TASK_IDS (R2); the default is the original mug -> tray task with the standard layout.
    sim_device: 'cpu' (PhysX on CPU, default, canon §48) or 'cuda' (GPU PhysX, the v1 setting).
    variant: 'standard' (today's scene, unchanged), 'random' (5 axes from the TEST pool, evaluation only) or 'dr'
    (5 axes from the disjoint TRAIN pool, training-time domain randomization); randomize.py, canon §34/§52.
    decimation: physics substeps (10 ms) per env step, 5 = the 20 Hz pool/label setting; the closed-loop runtime (R5,
    D23 §3) uses 1 (100 Hz). render_interval: physics substeps per render (default = decimation)."""
    return Env(seed, headless=headless, cameras=cameras, arm=arm, depth=depth, sim_device=sim_device, variant=variant,
               decimation=decimation, render_interval=render_interval, task=task)
