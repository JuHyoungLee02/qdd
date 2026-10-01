"""E-POL0 setup probe (no model): one PolaRiS DROID env on the render card -- robot bodies (gripper / finger pads),
TCP candidate, camera intrinsics / poses, observation keys, a differential-IK move test (5 cm up), images saved.
usage (polaris venv, render card): probe_polaris.py <env name> <out dir>"""
import argparse
import json
import os
import sys

from isaaclab.app import AppLauncher

env_name, out = sys.argv[1], sys.argv[2]
p = argparse.ArgumentParser()
a, _ = p.parse_known_args([])
a.enable_cameras, a.headless = True, True
app = AppLauncher(a).app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import polaris.environments  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from polaris.utils import load_eval_initial_conditions  # noqa: E402

os.makedirs(out, exist_ok=True)
cfg = parse_env_cfg(env_name, device="cuda", num_envs=1, use_fabric=True)
from isaaclab.sensors import CameraCfg  # noqa: E402
cams = {k: v for k, v in vars(cfg.scene).items() if isinstance(v, CameraCfg)}
print("camera cfgs", list(cams))
for k, v in cams.items():
    if k != "wrist_cam":
        v.data_types = list(v.data_types) + ["distance_to_image_plane"]
env = gym.make(env_name, cfg=cfg)
ins, ics = load_eval_initial_conditions(env.unwrapped.usd_file)
obs, info = env.reset(object_positions=ics[0])
u = env.unwrapped
rob = u.scene["robot"]
names = list(rob.data.body_names)
bp = rob.data.body_pos_w[0].cpu().numpy()
root = rob.data.root_pos_w[0].cpu().numpy()
print("instruction", ins, "n_ic", len(ics))
print("joints", list(rob.data.joint_names))
print("bodies", {n: np.round(bp[i] - root, 4).tolist() for i, n in enumerate(names)
                 if any(k in n.lower() for k in ("finger", "pad", "robotiq", "base_link", "hand", "link8", "gripper"))})
print("root", np.round(root, 4).tolist(), np.round(rob.data.root_quat_w[0].cpu().numpy(), 4).tolist())
for cam in list(cams):
    c = u.scene[cam]
    print(cam, "K", np.round(c.data.intrinsic_matrices[0].cpu().numpy(), 2).tolist(), "pos", np.round(c.data.pos_w[0].cpu().numpy() - root, 4).tolist(),
          "quat_ros", np.round(c.data.quat_w_ros[0].cpu().numpy(), 4).tolist(), "outputs", list(c.data.output.keys()))
print("obs keys", list(obs.keys()), {k: (list(v.keys()) if isinstance(v, dict) else None) for k, v in obs.items()})
print("info", {k: v for k, v in info.items() if k == "rubric"})
for cam, img in obs["splat"].items():
    Image.fromarray(np.asarray(img).astype(np.uint8)).save(os.path.join(out, f"{env_name}_{cam}.png"))
ext = [k for k in cams if k != "wrist_cam"][0]
d = u.scene[ext].data.output["distance_to_image_plane"][0, ..., 0].cpu().numpy()
print("depth", float(np.nanmin(d)), float(np.nanmax(d)), d.shape)
np.save(os.path.join(out, f"{env_name}_depth.npy"), d)
print("action space", env.action_space)
app.close()
