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
WRIST_POS = (0.055, 0.0, 0.03)  # in panda_hand (z = towards the fingers, y = finger axis)
WRIST_LOOK_AT = (0.0, 0.0, 0.105)
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
            enabled_self_collisions=False, solver_position_iteration_count=8, solver_velocity_iteration_count=0,
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
