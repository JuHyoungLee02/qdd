"""E-SIM1 (docs/stage3/prereg_sim1.md): SimplerEnv WidowX + Bridge visual-matching episodes as a qdd world. Same as
harvest.sim0.world.SimWorld except the robot facts (tools/sim0/widowx_geom.py) and the standard octo_bridge.sh setup:
robot widowx, control 5 Hz / sim 500 Hz, arm_pd_ee_target_delta_pose_align2_gripper_pd_joint_pos (the arm delta is
applied to the previous TARGET -> the world sends reference - last reference, rotation delta 0 = the start
orientation; gripper absolute +1 open / -1 close), camera 3rd_view_camera (fixed to the robot base_link, 640x480; the
real-eval overlay), max steps 60 (eggplant 120), object episodes 0-23. Pad gap = finger-link distance x 0.107 / 0.0736
(fully open reads the trained 10.7 cm)."""
from __future__ import annotations

import os

import numpy as np

from .world import ROOT, SimWorld, pose7_to_Rt

CONTROL_W = "arm_pd_ee_target_delta_pose_align2_gripper_pd_joint_pos"
BRIDGE = {
    "spoon": dict(env="PutSpoonOnTableClothInScene-v0", scene="bridge_table_1_v1",
                  overlay="ManiSkill2_real2sim/data/real_inpainting/bridge_real_eval_1.png", robot_xy=(0.147, 0.028),
                  max_steps=60),
    "carrot": dict(env="PutCarrotOnPlateInScene-v0", scene="bridge_table_1_v1",
                   overlay="ManiSkill2_real2sim/data/real_inpainting/bridge_real_eval_1.png", robot_xy=(0.147, 0.028),
                   max_steps=60),
    "stack": dict(env="StackGreenCubeOnYellowCubeBakedTexInScene-v0", scene="bridge_table_1_v1",
                  overlay="ManiSkill2_real2sim/data/real_inpainting/bridge_real_eval_1.png", robot_xy=(0.147, 0.028),
                  max_steps=60),
    "eggplant": dict(env="PutEggplantInBasketScene-v0", scene="bridge_table_1_v2",
                     overlay="ManiSkill2_real2sim/data/real_inpainting/bridge_sink.png", robot_xy=(0.127, 0.06),
                     max_steps=120),
}
OPEN_FINGER_M = 0.0736
GAP_SCALE_W = 0.107 / OPEN_FINGER_M


def episodes() -> list:
    return [{"task": t, "episode": e} for t in BRIDGE for e in range(24)]


def ep_name(e: dict) -> str:
    return f"{e['task']}_e{e['episode']:02d}"


def make_env(e: dict):
    from simpler_env.utils.env.env_builder import build_maniskill2_env
    s = BRIDGE[e["task"]]
    env = build_maniskill2_env(s["env"], obs_mode="rgbd", robot="widowx", sim_freq=500, control_mode=CONTROL_W,
                               control_freq=5, max_episode_steps=s["max_steps"], scene_name=s["scene"],
                               camera_cfgs={"add_segmentation": True}, rgb_overlay_path=os.path.join(ROOT, s["overlay"]))
    opts = {"robot_init_options": {"init_xy": np.array(s["robot_xy"]), "init_rot_quat": np.array([0, 0, 0, 1.0])},
            "obj_init_options": {"episode_id": e["episode"]}}
    return env, opts, s["max_steps"]


class BridgeWorld(SimWorld):
    CAM = "3rd_view_camera"

    def __init__(self, e: dict):
        self.e = e
        self.env, self.opts, self.max_steps = make_env(e)
        self.dt = 1.0 / 5.0
        self.w_close = 0.0
        self.table_z = None
        self.done = False
        self.quat0 = (1.0, 0.0, 0.0, 0.0)

    def reset(self, seed=None, task=None) -> None:
        super().reset(seed, task)
        _, self.target = self.tcp_Rt()  # the controller's target starts at the TCP

    def _gap(self) -> float:
        ls = {l.name: l for l in self.env.unwrapped.agent.robot.get_links()}
        d = np.linalg.norm(ls["left_finger_link"].pose.p - ls["right_finger_link"].pose.p)
        return float(d) * GAP_SCALE_W

    def action_of(self, cmd_b, width: float) -> np.ndarray:
        dp = np.asarray(cmd_b, float) - self.target
        self.target = np.asarray(cmd_b, float).copy()
        g = -1.0 if width < (self.w_open + self.w_close) / 2.0 else 1.0
        return np.concatenate([dp, np.zeros(3), [g]])

__all__ = ["BridgeWorld", "episodes", "ep_name", "make_env", "pose7_to_Rt"]
