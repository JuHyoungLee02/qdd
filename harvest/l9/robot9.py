"""L9 robot profiles (spec §9.1). A profile names the robot, its arm / gripper joints and links, gripper geometry, the
width <-> joint map, the initial pose, the cameras (parent link, mount, intrinsics), the base placement rule and the
prompt wording. "ffw_sg2" = the existing AI Worker path (make_env(robot=None), nothing here is used); "franka_mast" =
Franka Emika Panda (franka_description, Apache-2.0) on a stand with a head camera mast fixed to its base link.

Pure except the functions marked "pod" (Isaac Lab imports inside)."""
from __future__ import annotations

import math
import os
import re

import numpy as np

from . import hcam9 as HC

PROFILES = ("ffw_sg2", "franka_mast")
DEFAULT = "ffw_sg2"

# ---------------------------------------------------------------------------------------------- Franka
# Isaac Sim 5.1 ships franka_description (franka_ros, package.xml <license>Apache 2.0</license>) with its URDF
# importer; paths are inside the Isaac chroot (tools/l9/isaac.sh -> ir_run.sh IR_ROOT=cyclo).
FRANKA_SRC = "/isaac-sim/exts/isaacsim.asset.importer.urdf/data/urdf/robots/franka_description"
FRANKA_DIR = "/data/harvest/assets_l9r/franka"
FRANKA_URDF = "panda_l9r.urdf"
ARM = tuple(f"panda_joint{i}" for i in range(1, 8))
FINGERS = ("panda_finger_joint1", "panda_finger_joint2")
EE_BODY = "panda_ee"  # added frame on panda_hand, z up when the hand points down (= AI Worker link7 convention)
FINGER_BODIES = ("panda_leftfinger", "panda_rightfinger")
GRIP_MAX_W = 0.08  # Franka Hand max opening
FINGER_Q_MAX = 0.04
# a top-down start (Franka "ready" pose, TCP ~0.3 m ahead of the base)
INIT_Q = (0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785)
BASE_Y_RIGHT = -0.23  # base under the AI Worker right shoulder's xy (scene.py WS comment: shoulder at (-0.02, -0.23))
BASE_X = 0.0
BASE_DROP = (0.0, 0.12)  # base top = main work surface - U[0, 0.12] m (the AI Worker lift rule's analogue)
STAND_XY = 0.20  # stand box under the base (m)
# drive: Isaac Lab FRANKA_PANDA_HIGH_PD_CFG gains with gravity ON (our planner adds the PhysX gravity-compensation
# offset / stiffness to the joint target, harvest.sim.planner._gravity_offset, like for the AI Worker)
ARM_KP, ARM_KD = 400.0, 80.0
EFFORT_SHOULDER, EFFORT_FOREARM = 87.0, 12.0
FINGER_KP, FINGER_KD, FINGER_EFFORT = 2.0e3, 1.0e2, 70.0  # Franka Hand continuous grasp force 70 N
# wrist camera: D405 (as the AI Worker wrists, 424 x 240, hfov 87) beside the hand looking at the finger tips
WRIST_POS = (0.09, 0.0, 0.0)  # in panda_hand (z = towards the fingers, y = finger axis); 5.5 cm saw the hand body (smoke 4)
WRIST_LOOK_AT = (0.0, 0.0, 0.12)
WRIST_W, WRIST_H, WRIST_HFOV = 424, 240, 87.0
HEAD_CLIP, WRIST_CLIP = (0.1, 100.0), (0.03, 100.0)
H_APERTURE = 20.955  # = FFW_SG2_REAL_cameras.H_APERTURE (only focal / aperture matters)
# TCP / pad geometry for the prompt (Franka Hand fingertip pads; refined by the pod probe tools/l9r/probe_franka.py)
PAD_LEN_M, BODY_ABOVE_TCP_M = 0.020, 0.036


def franka_width_to_joint(w: float) -> float:
    """Pad gap (m) -> each finger's prismatic joint (the two fingers move symmetrically, gap = 2 q)."""
    return float(np.clip(float(w) / 2.0, 0.0, FINGER_Q_MAX))


def franka_joint_to_width(q: float) -> float:
    return float(2.0 * np.clip(float(q), 0.0, FINGER_Q_MAX))


def franka_urdf_text(src: str, mesh_root: str) -> str:
    """The bundled panda_arm_hand.urdf with absolute mesh paths, an inertial on the empty panda_link8 (fixed joints
    are kept as links: merge_fixed_joints=False) and the panda_ee frame: fixed to panda_hand, rotated pi about x, so
    its z axis points away from the fingers (the AI Worker arm_r_link7 convention the planner assumes: TCP on the
    body's -z axis, top-down grasp = a pure yaw quaternion, fingers closing along body y at yaw 0)."""
    if "<robot" not in src or "panda_hand" not in src:
        raise ValueError("not the panda arm + hand URDF")
    out = src.replace("package://franka_description", mesh_root.rstrip("/"))
    tiny = ('<inertial><origin rpy="0 0 0" xyz="0 0 0"/><mass value="0.01"/>'
            '<inertia ixx="1e-5" ixy="0" ixz="0" iyy="1e-5" iyz="0" izz="1e-5"/></inertial>')
    out, n = re.subn(r'<link name="panda_link8"\s*/>', f'<link name="panda_link8">{tiny}</link>', out)
    if n != 1:
        raise ValueError("panda_link8 not found as an empty link")
    # the importer keeps <mimic> as a PhysX mimic constraint even with convert_mimic_joints_to_normal_joints (probe2:
    # finger 2 held at -q1 against its drive, pad gap 9 mm when 80 mm was commanded): both fingers are driven instead
    out = re.sub(r"\s*<mimic[^>]*/>", "", out)
    ee = (f'  <link name="{EE_BODY}">{tiny}</link>\n'
          f'  <joint name="{EE_BODY}_joint" type="fixed"><parent link="panda_hand"/><child link="{EE_BODY}"/>'
          f'<origin rpy="{math.pi:.9f} 0 0" xyz="0 0 0"/></joint>\n</robot>')
    i = out.rindex("</robot>")
    return out[:i] + ee + out[i + len("</robot>"):]


def ensure_franka_urdf(src_dir: str = FRANKA_SRC, dst_dir: str = FRANKA_DIR) -> str:
    """(pod) Write the modified URDF once, named by its content hash (a changed URDF gets its own converted USD);
    -> its path."""
    import hashlib
    os.makedirs(dst_dir, exist_ok=True)
    txt = franka_urdf_text(open(os.path.join(src_dir, "robots", "panda_arm_hand.urdf")).read(), src_dir)
    dst = os.path.join(dst_dir, FRANKA_URDF.replace(".urdf", f"_{hashlib.sha256(txt.encode()).hexdigest()[:8]}.urdf"))
    if not os.path.exists(dst) or open(dst).read() != txt:
        tmp = dst + f".tmp{os.getpid()}"
        open(tmp, "w").write(txt)
        os.replace(tmp, dst)
    return dst


def franka_robot_cfg():
    """(pod) ArticulationCfg: the URDF converted once to a USD under FRANKA_DIR/usd, fixed base, contact reporting
    on (object sensors filter the finger links), mimic finger joint driven as a normal joint."""
    import isaaclab.sim as sim_utils
    from isaaclab.actuators import ImplicitActuatorCfg
    from isaaclab.assets.articulation import ArticulationCfg
    from isaaclab.sim.converters import UrdfConverterCfg
    path = ensure_franka_urdf()
    spawn = sim_utils.UrdfFileCfg(
        asset_path=path, usd_dir=os.path.join(FRANKA_DIR, "usd_" + os.path.basename(path)[:-5]), force_usd_conversion=False,
        fix_base=True,
        merge_fixed_joints=False, convert_mimic_joints_to_normal_joints=True, make_instanceable=False,
        joint_drive=UrdfConverterCfg.JointDriveCfg(gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(
            stiffness=ARM_KP, damping=ARM_KD)),
        activate_contact_sensors=True,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False, max_depenetration_velocity=5.0),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False, solver_position_iteration_count=32, solver_velocity_iteration_count=1,  # DIAG 4
            fix_root_link=True))
    return ArticulationCfg(
        prim_path="{ENV_REGEX_NS}/Robot", spawn=spawn,
        init_state=ArticulationCfg.InitialStateCfg(pos=(BASE_X, BASE_Y_RIGHT, 0.80),
                                                   joint_pos={**dict(zip(ARM, INIT_Q)), "panda_finger_joint.*": 0.04}),
        actuators={
            "panda_shoulder": ImplicitActuatorCfg(joint_names_expr=["panda_joint[1-4]"],
                                                  effort_limit_sim=EFFORT_SHOULDER, stiffness=ARM_KP, damping=ARM_KD),
            "panda_forearm": ImplicitActuatorCfg(joint_names_expr=["panda_joint[5-7]"],
                                                 effort_limit_sim=EFFORT_FOREARM, stiffness=ARM_KP, damping=ARM_KD),
            "panda_hand": ImplicitActuatorCfg(joint_names_expr=["panda_finger_joint.*"],
                                              effort_limit_sim=FINGER_EFFORT, stiffness=FINGER_KP, damping=FINGER_KD)},
        soft_joint_pos_limit_factor=1.0)


def wrist_mount() -> tuple:
    """(pos, world-convention quat) of the wrist camera in panda_hand: optical axis from WRIST_POS to WRIST_LOOK_AT,
    camera 'up' (+Z) = the hand's +x side (away from the look-at point's side), no roll otherwise."""
    p = np.asarray(WRIST_POS, float)
    f = np.asarray(WRIST_LOOK_AT, float) - p
    f = f / np.linalg.norm(f)
    up = np.array([1.0, 0.0, 0.0])
    z = up - f * float(up @ f)
    z = z / np.linalg.norm(z)
    y = np.cross(z, f)
    return tuple(float(v) for v in p), HC.R_to_quat(np.column_stack([f, y, z]))


def head_mount_default() -> tuple:
    """(pos, quat) of the mast camera in panda_link0 for the default draw at a surface 0.06 m above the base."""
    d = HC.draw_mast(0, default=True)
    R, t = HC.mast_pose((0.0, 0.0, 0.0), 0.06, d)
    return tuple(float(v) for v in t), HC.R_to_quat(R)


CAM_SPECS = {  # Franka cameras (parent link, size, hfov, clip); mounts: head = per episode (hcam9), wrist = wrist_mount
    "cam_head": {"parent": "panda_link0", "width": HC.W, "height": HC.H, "hfov": HC.D435_HFOV, "clip": HEAD_CLIP,
                 "model": "Intel RealSense D435 colour (69 x 42 deg) rendered 672x376, on a mast fixed to panda_link0"},
    "cam_wrist_right": {"parent": "panda_hand", "width": WRIST_W, "height": WRIST_H, "hfov": WRIST_HFOV,
                        "clip": WRIST_CLIP, "model": "Intel RealSense D405 (87 deg) on panda_hand"},
}
CAMERAS = ("cam_head", "cam_wrist_right")


def mount_of(name: str) -> list:
    """[tx, ty, tz, qw, qx, qy, qz] (FFW_SG2_REAL_cameras.mount_transform format) of a Franka camera's default."""
    p, q = head_mount_default() if name == "cam_head" else wrist_mount()
    return [*p, *q]


def franka_camera_cfgs(names, depth: bool) -> dict:
    """(pod) CameraCfg per name (scene key = name), prims under the parent link of the URDF articulation."""
    import isaaclab.sim as sim_utils
    from isaaclab.sensors import CameraCfg
    out = {}
    for n in names:
        if n not in CAM_SPECS:
            raise ValueError(f"camera {n!r}: Franka profile has {tuple(CAM_SPECS)}")
        s = CAM_SPECS[n]
        m = mount_of(n)
        fx = HC.fx_from_hfov(s["hfov"], s["width"])
        out[n] = CameraCfg(
            prim_path=f"{{ENV_REGEX_NS}}/Robot/{s['parent']}/{n}", update_period=0.0, height=s["height"],
            width=s["width"], data_types=["rgb", "distance_to_image_plane"] if depth else ["rgb"],
            update_latest_camera_pose=True,
            spawn=sim_utils.PinholeCameraCfg(focal_length=fx * H_APERTURE / s["width"], focus_distance=200.0,
                                             horizontal_aperture=H_APERTURE, clipping_range=s["clip"]),
            offset=CameraCfg.OffsetCfg(pos=tuple(m[:3]), rot=tuple(m[3:]), convention="world"))
    return out


# ---------------------------------------------------------------------------------------------- L9 v2: R1 Pro, G1
# spec §12.2. These profiles are NOT in PROFILES yet (world9 / scene.py treat every non-Franka profile as the AI
# Worker): the owner adds them to the executor; V2_PROFILES lists them. Assets: the prepared URDFs of
# tools/l9/v2robot/robots_v2.py (TCP links "<arm>_l9_tcp" = the cuRobo tool frame = grasp frame G), converted
# once to USD by Isaac Lab's UrdfConverter under V2_ROOT/<robot>/usd_<hash>.
V2_PROFILES = ("r1pro", "g1")
V2_ROOT = "/data/harvest/assets_l9v2/robots"
_D405 = {"width": 424, "height": 240, "hfov": 87.0}  # = the AI Worker / Franka wrist cameras (D405)


def _rpy_R(r: float, p: float, y: float) -> np.ndarray:
    return HC.axis_angle_R((0, 0, 1), y) @ HC.axis_angle_R((0, 1, 0), p) @ HC.axis_angle_R((1, 0, 0), r)


def _look_mount(pos, look_at, up) -> tuple:
    """(pos, world-convention quat) of a camera at pos (parent frame) whose optical axis (+X) points at look_at and
    whose +Z is as close as possible to `up`."""
    p = np.asarray(pos, float)
    f = np.asarray(look_at, float) - p
    f /= np.linalg.norm(f)
    u = np.asarray(up, float)
    z = u - f * float(u @ f)
    z /= np.linalg.norm(z)
    return tuple(float(v) for v in p), HC.R_to_quat(np.column_stack([f, np.cross(z, f), z]))


# Galaxea R1 Pro (GalaxeaManipSim galaxea_sim/robots/r1_pro.py, Apache-2.0, abe7f51): SAPIEN cameras use the same
# x-forward / y-left / z-up convention as our "world" camera mounts, so their local poses are taken as they are.
# head: zed_link, quat [1, 1, -1, 1] / 2, fovx 100.837 fovy 68.998 deg (1280 x 720); wrist: <arm>_realsense_link,
# rpy(-10 deg, 0, -90 deg) * quat [0.5, 0.5, -0.5, 0.5], fovx 55.70 (right) / 54.39 (left) deg at 320 x 240.
R1_HEAD_HFOV = 100.837
R1_WRIST = {"right": 55.703, "left": 54.393}


def _r1_wrist_quat() -> tuple:
    R = _rpy_R(math.radians(-10.0), 0.0, -math.pi / 2) @ HC.quat_to_R((0.5, 0.5, -0.5, 0.5))
    return HC.R_to_quat(R)


V2 = {
    "r1pro": {
        "name": "Galaxea R1 Pro", "urdf": f"{V2_ROOT}/r1pro/r1pro_l9v2.urdf",
        "licence": "Apache-2.0 (OpenGalaxea/GalaxeaManipSim galaxea_sim/assets/r1_pro/robot.urdf, abe7f51)",
        "root_link": "base_link", "base_z": 0.0,  # base_link origin on the floor (GalaxeaManipSim robot_origin 0)
        "torso": ("torso_joint1", "torso_joint2", "torso_joint3", "torso_joint4"),
        "arms": {s: {"joints": tuple(f"{s}_arm_joint{i}" for i in range(1, 8)),
                     "fingers": (f"{s}_gripper_finger_joint1", f"{s}_gripper_finger_joint2"),
                     "ee": f"{s}_gripper_link", "tcp": f"{s}_l9_tcp",
                     "finger_bodies": (f"{s}_gripper_finger_link1", f"{s}_gripper_finger_link2")}
                 for s in ("right", "left")},
        "grip_max_w": 0.0999, "finger_q_max": 0.05,  # w = 2 q (grippers/r1pro_*.json, FK of the finger faces)
        "pad_len_m": 0.070, "finger_depth_m": 0.035,
        # drives: GalaxeaManipSim joint_stiffness 1000 / damping 200 (all joints, SAPIEN); gripper effort 100 N
        # (URDF limit). Gravity off on the robot like the Franka high-PD profile.
        "kp": 1000.0, "kd": 200.0, "finger_kp": 2.0e3, "finger_kd": 1.0e2, "finger_effort": 100.0,
        "cameras": {"cam_head": {"parent": "zed_link", "pos": (0.0, 0.0, 0.0), "quat": (0.5, 0.5, -0.5, 0.5),
                                 "width": HC.W, "height": HC.H, "hfov": R1_HEAD_HFOV,
                                 "model": "ZED on torso_link4 (GalaxeaManipSim head camera, 100.8 x 69.0 deg)"},
                    **{f"cam_wrist_{s}": {"parent": f"{s}_realsense_link", "pos": (0.0, 0.0, 0.0),
                                          "quat": _r1_wrist_quat(), "width": 320, "height": 240,
                                          "hfov": R1_WRIST[s],
                                          "model": "RealSense on the gripper (GalaxeaManipSim wrist camera)"}
                       for s in ("right", "left")}},
    },
    "g1": {
        "name": "Unitree G1 (29 DoF, Dex3-1 hands)", "urdf": f"{V2_ROOT}/g1/g1_l9v2.urdf",
        "licence": "BSD-3-Clause (unitreerobotics/unitree_ros g1_description via cuRobo v0.8.0 content)",
        "root_link": "pelvis", "base_z": 0.793,  # [hypothesis] pelvis height standing with straight legs; smoke
        "torso": ("waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint"),
        "arms": {s: {"joints": tuple(f"{s}_{n}_joint" for n in ("shoulder_pitch", "shoulder_roll", "shoulder_yaw",
                                                                 "elbow", "wrist_roll", "wrist_pitch", "wrist_yaw")),
                     "fingers": tuple(f"{s}_hand_{j}_joint" for j in ("thumb_0", "thumb_1", "thumb_2", "index_0",
                                                                     "index_1", "middle_0", "middle_1")),
                     "ee": f"{s}_hand_palm_link", "tcp": f"{s}_l9_tcp",
                     "finger_bodies": (f"{s}_hand_thumb_2_link", f"{s}_hand_index_1_link")}
                 for s in ("right", "left")},
        "grip_max_w": 0.1131, "grip_min_w": 0.0215,  # Dex3-1 thumb-index pinch band (tools/l9/v2robot/hands_v2.py)
        "pad_len_m": 0.015, "finger_depth_m": 0.0345,
        # [hypothesis] drives; URDF hand joint effort 2.45 N m. Legs + waist are held at 0 by the body drives.
        "kp": 400.0, "kd": 80.0, "finger_kp": 20.0, "finger_kd": 1.0, "finger_effort": 2.45,
        "cameras": {"cam_head": {"parent": "d435_link", "pos": (0.0, 0.0, 0.0), "quat": (1.0, 0.0, 0.0, 0.0),
                                 "width": HC.W, "height": HC.H, "hfov": HC.D435_HFOV,
                                 "model": "Intel RealSense D435 on torso_link (unitree_ros d435_joint, 47.6 deg down)"},
                    # no official wrist camera (spec §9.2: wrist mount): a D405 on the palm looking at the pinch; 9 cm
                    # above the index finger the hand filled half the frame (smoke 10-02) -> 13 cm, 3 cm back
                    **{f"cam_wrist_{s}": {"parent": f"{s}_hand_palm_link",
                                          "look": ((-0.03, 0.0, 0.13 if s == "right" else -0.13),
                                                   (0.074, 0.056 if s == "right" else -0.056, 0.014),
                                                   (-1.0, 0.0, 0.0)),
                                          **_D405, "model": "D405 on a wrist mount above the index finger [hypothesis]"}
                       for s in ("right", "left")}},
    },
}


R1_LEAN = 0.80  # rad, torso_link4 pitched forward [hypothesis, smoke 10-02]: upright the ZED looks 20 deg down and the
# table filled only the bottom rows; 0.40 still put objects at x 0.40 on the bottom edge (r1_posture.py: v 349 of 376);
# 0.80 gives a 66 deg view with objects at x 0.4-0.6 at rows 195-280
R1_T4_ABOVE = 0.36  # torso_link4 origin above the work surface: the cuRobo top-down sweep (lean 0.80, world-aligned)
# reaches x 0.1-0.6 m ahead of torso_link4 at 0.33-0.40 m below it (grasps) and 0.5-0.7 m ahead at 0.1-0.3 m below


def r1_torso_q(p1: float, p2: float, lean: float = R1_LEAN) -> tuple:
    """R1 Pro torso from link pitches: torso_link1 pitch p1 (hip), torso_link2 pitch p2, torso_link3/4 pitch `lean`
    (all forward-positive about y): joint1 = p1, joint2 = p2 - p1, joint3 = p2 - lean (axis -y), joint4 (yaw) = 0."""
    return (float(p1), float(p2 - p1), float(p2 - lean), 0.0)


def r1_torso_for_surface(surface_z: float, lean: float = R1_LEAN) -> tuple:
    """Torso pitches putting torso_link4 R1_T4_ABOVE over the surface with joint3 straight above the hip joint
    (x of joint3 = that of joint1, so the reach band stays in front of the base): grid search over p1 in [0, 1],
    p2 in [-1.0, 0.5] (joint3 limit -1.83: p2 >= -1.03 at lean 0.8). Joint3 = 0.34265 + 0.4 cos p1 + 0.3 cos p2 above
    base_link, torso_link4 0.09962 further along the leaned axis (URDF origins). Surfaces above ~0.75 m leave the
    torso at its top (p1 = p2 = 0). -> (joint values, height error m)."""
    p1 = np.linspace(0.0, 1.0, 101)[:, None]
    p2 = np.linspace(-1.0, 0.5, 151)[None, :]
    z = 0.34265 + 0.4 * np.cos(p1) + 0.3 * np.cos(p2) + 0.09962 * math.cos(lean)
    x = 0.4 * np.sin(p1) + 0.3 * np.sin(p2)
    cost = (z - (float(surface_z) + R1_T4_ABOVE)) ** 2 + 4.0 * x ** 2
    i, j = np.unravel_index(int(np.argmin(cost)), cost.shape)
    err = float(z[i, j] - (float(surface_z) + R1_T4_ABOVE))
    return r1_torso_q(float(p1[i, 0]), float(p2[0, j]), lean), err


def v2_width_to_joints(profile: str, arm: str, w: float) -> dict:
    """Finger joint targets for a pad gap w (m). R1 Pro: both prismatic fingers q = w / 2. G1: the Dex3-1 pinch
    table (assets9/grippers/g1_<arm>.json width_to_joint.q_by_joint), clipped to its usable band."""
    a = V2[profile]["arms"][arm]
    if profile == "r1pro":
        q = float(np.clip(float(w) / 2.0, 0.0, V2[profile]["finger_q_max"]))
        return {j: q for j in a["fingers"]}
    t = _g1_table(arm)
    return {j: float(np.interp(w, t["width_m"], t["q_by_joint"][j])) for j in a["fingers"]}


_G1_TABLE = {}


def _g1_table(arm: str) -> dict:
    if arm not in _G1_TABLE:
        import json
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "grippers", f"g1_{arm}.json")
        _G1_TABLE[arm] = json.load(open(p))["width_to_joint"]
    return _G1_TABLE[arm]


# start arm poses (7 values, V2 arms[arm].joints order). STOW = the unused arm; READY = the used arm before the
# preroll, from tools/l9/v2robot/ready_pose.py (cuRobo IK, top-down TCP 0.20 m over a surface in front of the arm).
V2_STOW = {"r1pro": {"right": (0.0,) * 7, "left": (0.0,) * 7},  # R1: arms hang at 0
           # G1: at 0 the forearms point forward over the table (smoke 10-02) -> upper arm out, elbow open [hypothesis]
           # elbow -0.9 lifted the forearm to the face (smoke 2): +1.4 lets it hang
           "g1": {"right": (0.2, -0.25, 0.0, 1.4, 0.0, 0.0, 0.0), "left": (0.2, 0.25, 0.0, 1.4, 0.0, 0.0, 0.0)}}
V2_READY = {  # ready_pose.py 10-02: R1 TCP (0.542, -+0.20, 0.169) in torso_link4 (leaned 0.80; world 0.50 ahead, 0.27 below),
    # world top-down yaw +-pi/2;
    # G1 (0.30, -+0.20, 0) in torso_link,
    # yaw -pi/2 (the right-arm reach sweep found top-down only at that yaw for x 0.1-0.4)
    "r1pro": {"right": (0.87431, -3.07854, -0.2803, -1.58941, -1.51053, 0.2809, -0.10471),
              "left": (0.87437, 3.07831, 0.28057, -1.58942, 1.51029, 0.28117, 0.10469)},
    "g1": {"right": (-0.30265, -0.76872, 0.61976, -0.1309, -0.88791, 0.69321, 0.59968),
           "left": (-0.20483, 0.01847, 0.32992, -0.08547, 1.68825, -0.23174, -0.83459)}}


def v2_joints_to_width(profile: str, arm: str, q) -> float:
    """Measured pad gap from the finger joint values (order = V2 arms[arm].fingers). R1 Pro: q1 + q2 (each finger
    moves w / 2); G1: the width of the nearest row of the pinch table (joint-space distance)."""
    q = np.asarray(q, float)
    if profile == "r1pro":
        return float(max(q[0] + q[1], 0.0))
    t = _g1_table(arm)
    Q = np.array([t["q_by_joint"][j] for j in V2[profile]["arms"][arm]["fingers"]]).T
    return float(t["width_m"][int(np.argmin(np.linalg.norm(Q - q[None], axis=1)))])


def v2_contact_bodies(profile: str, arm: str) -> tuple:
    """Finger bodies the object contact sensors filter on (G1: thumb, index and middle distal links)."""
    a = V2[profile]["arms"][arm]
    if profile == "g1":
        return (f"{arm}_hand_thumb_2_link", f"{arm}_hand_index_1_link", f"{arm}_hand_middle_1_link")
    return tuple(a["finger_bodies"])


# per-episode body placement (spec §9.1 base placement rule), root pose in the env frame
V2_BASE_X = {"r1pro": -0.05, "g1": -0.02}  # [hypothesis] root x so the arm bases sit where the AI Worker shoulders do
G1_SHOULDER_ABOVE = (0.30, 0.55)  # [hypothesis] usable G1 shoulder height over the work surface (no squat model)
# gripper body (housing / palm) above the TCP along the approach: R1 Pro finger root 0.008 m below gripper_link,
# TCP 0.0433 below it -> 0.035; G1 palm origin 0.088 behind the pinch point along the approach, palm 0.02 thick
# [hypothesis: 0.04]
V2_BODY_ABOVE_TCP = {"r1pro": 0.035, "g1": 0.040}


def v2_body_joints(profile: str, table_z: float) -> dict:
    """Joints that put the robot at the work surface: R1 Pro torso (r1_torso_for_surface); G1 standing straight
    (waist + legs 0)."""
    if profile == "r1pro":
        return dict(zip(V2["r1pro"]["torso"], r1_torso_for_surface(table_z)[0]))
    return {j: 0.0 for j in V2["g1"]["torso"]}


def v2_root_pos(profile: str) -> tuple:
    return (V2_BASE_X[profile], 0.0, V2[profile]["base_z"])


def r1_surface_ok(table_z: float) -> bool:
    """R1 Pro works a surface only where its torso reaches the planned height (torso_link4 R1_T4_ABOVE over it, within
    2 cm): its top (1.112 m) caps it at surfaces of ~0.77 m. Above that the ready TCP ended 1.5-12 cm over or even under
    the surface and every episode died at the start (L9v2-DIAG 8: 0/6, z - table -0.049..+0.118)."""
    return r1_torso_for_surface(table_z)[1] >= -0.02


def g1_surface_ok(table_z: float) -> bool:
    """G1 stands straight: its shoulders (pelvis 0.793 + 0.044 + 0.248 m) must be 0.30-0.55 m over the surface."""
    s = V2["g1"]["base_z"] + 0.044 + 0.248 - float(table_z)
    return G1_SHOULDER_ABOVE[0] <= s <= G1_SHOULDER_ABOVE[1]


def v2_init_joints(profile: str, arm: str, table_z: float, ready: dict | None = None) -> dict:
    """Start joints: body for the surface, the used arm at its ready pose (V2_READY, inside the limits by >= 0.03),
    the other arm at its stow pose, every finger open."""
    out = v2_body_joints(profile, table_z)
    for s, a in V2[profile]["arms"].items():
        q = (ready or V2_READY[profile]).get(s) if s == arm else V2_STOW[profile].get(s)
        if q:
            out.update(dict(zip(a["joints"], q)))
        if profile == "r1pro":
            out.update(v2_width_to_joints(profile, s, V2["r1pro"]["grip_max_w"]))
        else:
            out.update(v2_width_to_joints(profile, s, V2["g1"]["grip_max_w"]))
    return out


def v2_mount(profile: str, cam: str) -> tuple:
    c = V2[profile]["cameras"][cam]
    if "look" in c:
        return _look_mount(*c["look"])
    return tuple(c["pos"]), tuple(c["quat"])


def v2_robot_cfg(profile: str, init_joints: dict | None = None):
    """(pod) ArticulationCfg of an L9 v2 robot: its prepared URDF converted once (hash-named USD dir), fixed root,
    gravity off, contact sensors on, no self-collision (cuRobo plans self-collision free), drives from V2."""
    import hashlib

    import isaaclab.sim as sim_utils
    from isaaclab.actuators import ImplicitActuatorCfg
    from isaaclab.assets.articulation import ArticulationCfg
    from isaaclab.sim.converters import UrdfConverterCfg
    s = V2[profile]
    h = hashlib.sha256(open(s["urdf"], "rb").read()).hexdigest()[:8]
    spawn = sim_utils.UrdfFileCfg(
        asset_path=s["urdf"], usd_dir=os.path.join(os.path.dirname(s["urdf"]), f"usd_{h}"), force_usd_conversion=False,
        fix_base=True, merge_fixed_joints=False, convert_mimic_joints_to_normal_joints=True, make_instanceable=False,
        joint_drive=UrdfConverterCfg.JointDriveCfg(gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(
            stiffness=s["kp"], damping=s["kd"])),
        activate_contact_sensors=True,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=True, max_depenetration_velocity=5.0),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False, solver_position_iteration_count=32, solver_velocity_iteration_count=1,  # DIAG 4
            fix_root_link=True))
    fingers = [j for a in s["arms"].values() for j in a["fingers"]]
    return ArticulationCfg(
        prim_path="{ENV_REGEX_NS}/Robot", spawn=spawn,
        init_state=ArticulationCfg.InitialStateCfg(pos=(0.0, 0.0, s["base_z"]), joint_pos=dict(init_joints or {})),
        actuators={
            "body": ImplicitActuatorCfg(joint_names_expr=[f"^(?!({'|'.join(fingers)})$).*"], stiffness=s["kp"],
                                        damping=s["kd"]),
            "fingers": ImplicitActuatorCfg(joint_names_expr=fingers, effort_limit_sim=s["finger_effort"],
                                           stiffness=s["finger_kp"], damping=s["finger_kd"])},
        soft_joint_pos_limit_factor=1.0)


def v2_camera_cfgs(profile: str, names, depth: bool = False) -> dict:
    """(pod) CameraCfg per camera name (scene key = name), prims under the parent link of the URDF articulation."""
    import isaaclab.sim as sim_utils
    from isaaclab.sensors import CameraCfg
    out = {}
    for n in names:
        c = V2[profile]["cameras"][n]
        pos, quat = v2_mount(profile, n)
        fx = HC.fx_from_hfov(c["hfov"], c["width"])
        out[n] = CameraCfg(
            prim_path=f"{{ENV_REGEX_NS}}/Robot/{c['parent']}/{n}", update_period=0.0, height=c["height"],
            width=c["width"], data_types=["rgb", "distance_to_image_plane"] if depth else ["rgb"],
            update_latest_camera_pose=True,
            spawn=sim_utils.PinholeCameraCfg(focal_length=fx * H_APERTURE / c["width"], focus_distance=200.0,
                                             horizontal_aperture=H_APERTURE,
                                             clipping_range=WRIST_CLIP if "wrist" in n else HEAD_CLIP),
            offset=CameraCfg.OffsetCfg(pos=tuple(pos), rot=tuple(quat), convention="world"))
    return out


# ---------------------------------------------------------------------------------------------- prompts
_FFW_ROBOT = "the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2)"
_FFW_PADS = ("The pads are 4.5 cm long (from 2.25 cm above to 2.25 cm below the TCP); the gripper body starts 2.5 cm "
             "above the TCP. Fully open pad gap 10.7 cm")


def prompt_swaps(name: str) -> list:
    """(old, new) text pairs turning the AI Worker request wording into the profile's (robot, gripper, head camera
    mount). Image labels ('right wrist camera') and the hand field stay (the arm stands where the AI Worker's right
    arm works)."""
    if name == DEFAULT:
        return []
    if name in V2_PROFILES:  # L9 v2: robot name + gripper geometry (gripper json facts); head camera wording kept
        s = V2[name]
        p = s["pad_len_m"] * 100
        gripper = ("a parallel gripper" if name == "r1pro" else
                   "a three-finger hand (Unitree Dex3-1) used as a thumb-index pinch")
        robot_txt = ("the right arm of a wheeled humanoid robot (Galaxea R1 Pro)" if name == "r1pro" else
                     "the right arm of a humanoid robot (Unitree G1)")
        tail = (f" ({gripper}); it cannot close on things thinner than {s['grip_min_w'] * 100:.1f} cm"
                if "grip_min_w" in s else f" ({gripper})")
        return [(_FFW_ROBOT, robot_txt),
                (_FFW_PADS, f"The pads are {p:.1f} cm long (from {p / 2:.1f} cm above to {p / 2:.1f} cm below the TCP); "
                            f"the gripper body starts {V2_BODY_ABOVE_TCP[name] * 100:.1f} cm above the TCP. Fully open "
                            f"pad gap {s['grip_max_w'] * 100:.1f} cm{tail}")]
    if name != "franka_mast":
        raise ValueError(name)
    h = PAD_LEN_M * 100 / 2
    return [(_FFW_ROBOT, "a robot arm (Franka Emika Panda) on a fixed stand"),
            (_FFW_PADS, f"The pads are {PAD_LEN_M * 100:.1f} cm long (from {h:.1f} cm above to {h:.1f} cm below the "
                        f"TCP); the gripper body starts {BODY_ABOVE_TCP_M * 100:.1f} cm above the TCP. Fully open pad "
                        f"gap {GRIP_MAX_W * 100:.1f} cm"),
            ("head camera, fixed on the robot head,", "head camera, fixed on a mast on the robot's stand,"),
            ("head camera (fixed on the robot head)", "head camera (fixed on a mast on the robot's stand)"),
            ("origin at the robot base", "origin on the floor next to the robot's stand")]


def swap_text(text: str, name: str) -> str:
    for a, b in prompt_swaps(name):
        text = text.replace(a, b)
    return text


PROMPT_MODULES = ("harvest.astra_solo.prompts", "harvest.astra_solo.pt_prompts", "harvest.astra_solo.nd_prompts",
                  "harvest.astra_motion.prompts")


def apply_prompts(name: str) -> list:
    """Process-level: rebind STATIC of the request modules with the profile wording (the AI Worker text stays for
    name == ffw_sg2). -> modules changed. Every swap must hit the v2 / pt STATIC once (wording drift guard)."""
    import importlib
    if name == DEFAULT:
        return []
    done = []
    for m in PROMPT_MODULES:
        mod = importlib.import_module(m)
        s = getattr(mod, "STATIC", None)
        if isinstance(s, str):
            new = swap_text(s, name)
            if new != s:
                mod.STATIC = new
                done.append(m)
    from ..astra_solo import prompts as V2
    from ..astra_solo import pt_prompts as PT
    for a, b in prompt_swaps(name)[:3]:
        if a in V2.STATIC or a in PT.STATIC:
            raise RuntimeError(f"prompt swap not applied: {a[:40]}")
    return done
