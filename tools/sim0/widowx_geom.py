"""E-SIM1 (SimplerEnv WidowX Bridge) setup: links, TCP (extra.tcp_pose) in the base frame, finger links open / closed,
3rd_view_camera param, controller; no model. usage: widowx_geom.py"""
import json

import numpy as np
from simpler_env.utils.env.env_builder import build_maniskill2_env

env = build_maniskill2_env("PutCarrotOnPlateInScene-v0", obs_mode="rgbd", robot="widowx", sim_freq=500,
                           control_mode="arm_pd_ee_target_delta_pose_align2_gripper_pd_joint_pos", control_freq=5,
                           max_episode_steps=60, scene_name="bridge_table_1_v1", camera_cfgs={"add_segmentation": True},
                           rgb_overlay_path="/data/harvest/simpler/SimplerEnv/ManiSkill2_real2sim/data/real_inpainting/bridge_real_eval_1.png")
obs, _ = env.reset(options={"robot_init_options": {"init_xy": np.array([0.147, 0.028]), "init_rot_quat": np.array([0, 0, 0, 1.0])},
                            "obj_init_options": {"episode_id": 0}})
u = env.unwrapped
rob = u.agent.robot
inv = rob.get_pose().inv()
print("instruction", env.get_language_instruction())
print("base_pose", np.round(obs["agent"]["base_pose"], 4).tolist(), "tcp_pose", np.round(obs["extra"]["tcp_pose"], 4).tolist())
print("joints", [j.name for j in rob.get_active_joints()], "qpos", np.round(obs["agent"]["qpos"], 4).tolist())
print("cams", list(obs["image"].keys()), {k: np.round(np.asarray(v["intrinsic_cv"]), 2).tolist() for k, v in obs["camera_param"].items()})
L = lambda: {l.name: (inv * l.pose).p.round(4).tolist() for l in rob.get_links() if "finger" in l.name or "ee" in l.name or "gripper" in l.name}
print("links open", json.dumps(L()))
for g in (-1.0, 1.0):
    for _ in range(5):
        obs, *_ = env.step(np.array([0, 0, 0, 0, 0, 0, g]))
    print("gripper", g, "qpos", np.round(obs["agent"]["qpos"], 4).tolist(), json.dumps(L()))
print("actors", {a.name: (inv * a.pose).p.round(4).tolist() for a in u._scene.get_all_actors()})
