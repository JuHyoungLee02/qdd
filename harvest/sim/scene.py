"""T11 sim scene: AI Worker FFW-SG2 (fixed base), right arm only, table + red mug / blue tray (E §1.4, canon §37-§38).

Pure parts (layout sampling, gripper width <-> joint map, geometry) import without Isaac and are unit-tested
locally. Everything that touches Isaac is imported lazily inside functions (pod only).

Frames: world x = robot forward, y = robot left, z = up; robot root is fixed at the world origin.
The "table frame" (harvest.predicates) is world x, y and z - TABLE_TOP_Z.
Cameras: only the AI Worker model's default cameras as defined by cyclo_lab (user instruction 2026-09-24:
no ZED_M twin, no extra stereo pair). See docs/stage3/results/scene_bringup.md for the camera table.
"""
from __future__ import annotations

import math

import numpy as np

CYCLO_LAB_SRC = "/data/juhyoung_qdd/cyclo_lab/source/cyclo_lab"  # official ROBOTIS-GIT/cyclo_lab clone (f4c0470)

SCENE_SPEC = {
    "instruction": "Put the red mug on the blue tray.",
    "target": "o3",  # mug red
    "place": "o5",  # tray blue
    "distractors": ("o8", "o9"),  # 0-2 per seed
    "p2_object": "o10",  # DEV perturbation P2 only: parked off-table until it "appears"
    "names": {"o3": "mug red", "o5": "tray blue", "o8": "bottle green", "o9": "box yellow", "o10": "box purple"},
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
}
for _g in OBJ_GEOM.values():
    if _g["shape"] == "cylinder":
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
PARK_XY = {"o8": (-3.0, 3.0), "o9": (-3.3, 3.0), "o10": (-3.6, 3.0)}  # parked behind the robot (out of the head view)

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
# initial robot pose: cyclo_lab SG2 pick-place default (set_default_joint_pose), head pitched further down
# (head_joint1 upper limit 0.695) so the table workspace is inside the default head camera.
INIT_JOINTS = {"arm_l_joint1": 0.75, "arm_l_joint4": -2.30, "arm_r_joint1": 0.75, "arm_r_joint4": -2.30,
               "head_joint1": 0.69, "lift_joint": -0.0993}


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


# ----------------------------------------------------------------------------------------------------------
# Isaac part (pod only)
# ----------------------------------------------------------------------------------------------------------
_APP = None
DEFAULT_CAMERAS = ("cam_head",)
KNOWN_CAMERAS = ("cam_head", "right_wrist_cam")


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
    """cyclo_lab's own camera definitions, unchanged except the optional renderer depth annotator.

    cam_head: FFW-SG2 pick-place task (config/ffw_sg2/joint_pos_env_cfg.py), the only camera cyclo_lab defines
    for SG2. right_wrist_cam: FFW-BG2 pick-place task (config/ffw_bg2/joint_pos_env_cfg.py) on the D405 mount
    frame camera_r_link, which the SG2 USD also has; same offset/intrinsics, only the robot prefix differs.
    """
    out = {}
    for n in names:
        if n not in KNOWN_CAMERAS:
            raise ValueError(f"camera {n!r}: only the model's default cameras {KNOWN_CAMERAS}")
        if n == "cam_head":
            from cyclo_lab.manager_based.manipulation.pick_place.config.ffw_sg2.joint_pos_env_cfg import (
                FFWSG2PickPlaceEnvCfg,
            )
            c = FFWSG2PickPlaceEnvCfg().scene.cam_head
        else:
            from cyclo_lab.manager_based.manipulation.pick_place.config.ffw_bg2.joint_pos_env_cfg import (
                PickPlaceFFWBG2EnvCfg,
            )
            c = PickPlaceFFWBG2EnvCfg().scene.right_wrist_cam
            c = c.replace(prim_path=c.prim_path.replace("ffw_bg2_follower/right_arm/", "ffw_sg2_follower/"))
        if depth and "distance_to_image_plane" not in c.data_types:
            c = c.replace(data_types=list(c.data_types) + ["distance_to_image_plane"])
        out[n] = c
    return out


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


def _build_cfg(seed: int, cameras, arm: str, depth: bool):
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

    from cyclo_lab.assets.robots.FFW_SG2 import FFW_SG2_CFG

    if arm != "right":
        raise NotImplementedError("single right arm only (T11)")
    layout = sample_layout(seed)
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

    robot = FFW_SG2_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
    robot = robot.replace(init_state=robot.init_state.replace(joint_pos={**robot.init_state.joint_pos, **INIT_JOINTS}))
    # RH-P12-RN: cyclo_lab drives only joint1 stiffly (100) and the other three finger joints with stiffness 2,
    # so under a grasp load the fingers go asymmetric (measured seed 2: joints [0.88, 1.10, 0.16, 0.40], the mug
    # was shoved 28 mm and the arm with it). We command all four joints to the same target (as cyclo_lab's own
    # BG2 BinaryJointPositionAction does: close_command_expr "gripper_r_joint.*") and give the slave joints the
    # master's gains. Real gains get re-fit from step responses later (canon §37 [가정]).
    acts = dict(robot.actuators)
    acts["gripper_slave"] = acts["gripper_slave"].replace(stiffness=acts["gripper_master"].stiffness,
                                                          damping=acts["gripper_master"].damping,
                                                          velocity_limit_sim=acts["gripper_master"].velocity_limit_sim)
    robot = robot.replace(actuators=acts)

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
            self.decimation = 5  # canon §37: sim.dt 0.01, decimation 5 -> 20 Hz env step
            self.sim.dt = 0.01
            self.sim.render_interval = self.decimation
            self.episode_length_s = 120.0
            self.sim.physx.bounce_threshold_velocity = 0.01
            self.sim.physx.friction_correlation_distance = 0.00625
            self.viewer.eye = (1.6, -1.2, 1.7)
            self.viewer.lookat = (0.4, -0.2, 0.8)

    cfg = EnvCfg()
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

    def __init__(self, seed: int, headless=True, cameras=DEFAULT_CAMERAS, arm="right", depth=True):
        cameras = tuple(cameras or ())
        _ensure_app(headless, bool(cameras))
        import torch
        from isaaclab.envs import ManagerBasedRLEnv

        self.torch = torch
        self.seed, self.arm, self.cameras = int(seed), arm, cameras
        cfg, self.layout = _build_cfg(seed, cameras, arm, depth)
        _LAYOUT["layout"] = self.layout
        self.env = ManagerBasedRLEnv(cfg=cfg)
        self.scene = self.env.scene
        self.robot = self.scene["robot"]
        self.objects = {k: self.scene[k] for k in ("o3", "o5", "o8", "o9", "o10")}
        self.contact = {k: self.scene[f"contact_{k}"] for k in self.objects}
        self.present = [k for k in ("o3", "o5", "o8", "o9") if k in self.layout]  # o10 joins after P2 fires
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


    # ---- time / stepping
    @property
    def sim_time(self) -> float:
        return self._steps * self.step_dt

    def set_seed(self, seed: int):
        """Reuse this env for another seed: new layout, applied by the next reset() (one write at reset)."""
        self.seed = int(seed)
        self.layout = sample_layout(seed)
        _LAYOUT["layout"] = self.layout

    def reset(self, settle_s: float = 1.0):
        """Reset once (write default state once), then let objects settle with the arm holding its pose."""
        _LAYOUT["layout"] = self.layout
        self.present = [k for k in ("o3", "o5", "o8", "o9") if k in self.layout]
        self.perturb_state = None
        if hasattr(self, "carry_start_xy"):
            del self.carry_start_xy
        self.env.reset(seed=self.seed)
        self._steps = 0
        q = self.robot.data.joint_pos[0]
        hold = np.concatenate([q[self.arm_ids].cpu().numpy(), [GRIP_MAX_W]])
        for _ in range(int(round(settle_s / self.step_dt))):
            self.step(hold)
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


def make_env(seed: int, headless: bool = True, cameras=DEFAULT_CAMERAS, arm: str = "right", depth: bool = True) -> Env:
    """cameras: names of the AI Worker model's default cameras only (KNOWN_CAMERAS); () for no rendering."""
    return Env(seed, headless=headless, cameras=cameras, arm=arm, depth=depth)
