"""L9 left / right arm constants (pure). The FFW-SG2 is mirror-symmetric about the robot's xz plane (ROBOTIS
ai_worker ffw_description/mujoco/ffw_sg2/ffw_sg2.xml, checked 2026-09-30): joints 1, 4, 6 turn about y (pitch, same
sign on both arms), joints 2, 7 about x and 3, 5 about z (their mirror image has the opposite sign; the joint ranges
agree: arm_r_joint2 [-3.14, 0] vs arm_l_joint2 [0, 3.14], joint7 [-1.8201, 1.5804] vs [-1.5804, 1.8201]).
So a left-arm pose = the right-arm pose with q2, q3, q5, q7 negated, reaching the y-mirrored point."""
from __future__ import annotations

import math

ARMS = ("right", "left")
MIRROR_SIGN = (1, -1, -1, 1, -1, 1, -1)
INIT_R_ARM = (-1.0511, -1.0975, 1.2281, -2.3934, 0.4838, 1.2356, 1.80)  # = scene.INIT_R_ARM
STOW = {"joint1": 0.75, "joint4": -2.30}  # the cyclo idle pose (= scene.INIT_JOINTS arm_l_*), mirrored = same values
ARM_START_R = (0.34, -0.25, 0.25)  # = clutter_x.ARM_START (TCP above the work surface)

# principal inertias (kg m^2, COM frame) of the left arm and head links, ffw_sg2.xml (later_problems 11; the robot USD
# gives every such link a 1e-6 placeholder, change 27 fixed the right arm only)
LEFT_HEAD_INERTIA = {
    "arm_l_link1": (0.00336559, 0.00296956, 0.00240308), "arm_l_link2": (0.0108884, 0.0107203, 0.00242441),
    "arm_l_link3": (0.0034081, 0.00290979, 0.00183363), "arm_l_link4": (0.00633449, 0.00629266, 0.00142827),
    "arm_l_link5": (0.00188568, 0.00172688, 0.00124772), "arm_l_link6": (0.00161927, 0.00141848, 0.000538247),
    "arm_l_link7": (0.000452453, 0.000416075, 0.0001032),
    "head_link1": (1.77151e-05, 1.63207e-05, 6.86142e-06), "head_link2": (0.00134009, 0.000890252, 0.000762966)}


def check_arm(arm: str) -> str:
    if arm not in ARMS:
        raise ValueError(f"arm {arm!r}: one of {ARMS}")
    return arm


def mirror_q(q) -> tuple:
    """Right-arm joint vector <-> left-arm joint vector (the mirror is its own inverse)."""
    return tuple(float(s * v) for s, v in zip(MIRROR_SIGN, q))


INIT_L_ARM = mirror_q(INIT_R_ARM)


def joint_prefix(arm: str) -> str:
    return {"right": "arm_r_joint", "left": "arm_l_joint"}[check_arm(arm)]


def finger_prefix(arm: str) -> str:
    return {"right": "gripper_r", "left": "gripper_l"}[check_arm(arm)]


def wrist_camera(arm: str) -> str:
    return {"right": "cam_wrist_right", "left": "cam_wrist_left"}[check_arm(arm)]


def side(arm: str) -> int:
    """+1 for the right arm (works at y < 0), -1 for the left (y > 0): y_arm = side * y_right."""
    return 1 if check_arm(arm) == "right" else -1


def mirror_y(p, arm: str):
    """A right-arm frame point (x, y[, z]) for this arm (y negated for the left arm)."""
    p = list(p)
    p[1] = -p[1] if check_arm(arm) == "left" else p[1]
    return tuple(p)


def arm_start(arm: str) -> tuple:
    return mirror_y(ARM_START_R, arm)


def goal_yaw(arm: str, yaw: float) -> float:
    """Top-down grasp yaw for this arm: the mirror of a yaw rotation is the opposite yaw (fingers still close along
    world x)."""
    return float(yaw) if check_arm(arm) == "right" else -float(yaw)


def yaw_quat(yaw: float) -> tuple:
    return (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))


def init_joints(arm: str, base: dict) -> dict:
    """Initial joint dict for an env acting with `arm`: right = `base` (scene.INIT_JOINTS, unchanged); left = the
    active left arm at the mirrored start pose and the right arm stowed (the cyclo idle pose)."""
    if check_arm(arm) == "right":
        return dict(base)
    out = {k: v for k, v in base.items() if not k.startswith(("arm_r_joint", "arm_l_joint"))}
    out.update({f"arm_l_joint{i + 1}": v for i, v in enumerate(INIT_L_ARM)})
    out.update({"arm_r_joint1": STOW["joint1"], "arm_r_joint4": STOW["joint4"]})
    return out


def apply_arm_workspace(arm: str) -> list:
    """Process-level (one arm per Isaac process): the executor's safety box and the behaviour policy's reach-limit
    corner for this arm. Right = unchanged. Left = y mirrored: astra_motion.executor.SAFE_Y (-0.50, 0.10) ->
    (-0.10, 0.50) rebound in every loaded module that imported it by name (prompts, overlay, nd_prompts, behavior),
    teach_l8.behavior.REACH_CORNER_Y mirrored. Import-time copies are why this runs before and after the imports
    (call it at process start and again after the world is built). -> modules rebound."""
    import sys

    from ..astra_motion import executor as EX
    from ..teach_l8 import behavior as BH
    if check_arm(arm) == "right":
        return []
    r_y = (-0.50, 0.10)
    l_y = (-r_y[1], -r_y[0])
    EX.SAFE_Y = l_y
    BH.REACH_CORNER_Y = (0.42, 0.50)
    done = []
    for name, mod in list(sys.modules.items()):
        if name.startswith("harvest.") and getattr(mod, "SAFE_Y", None) in (r_y, l_y) and mod is not EX:
            mod.SAFE_Y = l_y
            done.append(name)
    return sorted(done)
