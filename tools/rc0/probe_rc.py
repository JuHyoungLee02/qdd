"""E-RC0 setup probe (no model): one RoboCasa365 target task via the official gym env (split target, seed 7): obs keys,
raw env facts (robot root body, eef site, gripper joints, cameras, controller config), step timing, an arm-delta test
(+x for 5 steps) to read the controller frame/scale. usage: probe_rc.py <task> <out dir>"""
import json
import os
import sys
import time

import gymnasium as gym
import numpy as np
import robocasa  # noqa: F401
import robocasa.wrappers.gym_wrapper  # noqa: F401  (registers robocasa/<task>)
from robocasa.utils.env_utils import convert_action

task, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
t0 = time.time()
env = gym.make(f"robocasa/{task}", split="target", seed=7)
obs, info = env.reset()
print("make+reset s", round(time.time() - t0, 1), "lang", obs["annotation.human.task_description"])
print("obs", {k: np.shape(v) for k, v in obs.items() if not isinstance(v, str)})
raw = env.unwrapped.env
rob = raw.robots[0]
print("robot", type(rob).__name__, "root body", rob.robot_model.root_body, "prefix", rob.robot_model.naming_prefix)
cc = rob.composite_controller
print("composite", type(cc).__name__, {k: (type(c).__name__, getattr(c, "input_ref_frame", None),
                                            np.round(getattr(c, "output_max", np.zeros(1)), 3).tolist()) for k, c in cc.part_controllers.items()})
m = raw.sim.model
print("cameras", [m.camera_id2name(i) for i in range(m.ncam)][:20])
print("sites with grip", [m.site_id2name(i) for i in range(m.nsite) if "grip" in (m.site_id2name(i) or "")][:10])
print("gripper joints", [m.joint_id2name(i) for i in range(m.njnt) if "gripper" in (m.joint_id2name(i) or "") or "finger" in (m.joint_id2name(i) or "")])
o = raw._get_observations(force_update=True)
print("raw obs keys", [k for k in o if "eef" in k or "gripper" in k or "base" in k])
print("eef", np.round(o.get("robot0_eef_pos"), 4).tolist() if "robot0_eef_pos" in o else None,
      "base_to_eef", np.round(o.get("robot0_base_to_eef_pos"), 4).tolist() if "robot0_base_to_eef_pos" in o else None)
a = np.zeros(12)
a[11] = 0.0
p0 = np.array(raw._get_observations(force_update=True)["robot0_base_to_eef_pos"])
t1 = time.time()
for i in range(5):
    a[0] = 1.0
    obs, r, d, tr, info = env.step(convert_action(a))
print("step s", round((time.time() - t1) / 5, 3))
p1 = np.array(raw._get_observations(force_update=True)["robot0_base_to_eef_pos"])
print("base_to_eef delta after 5x(+1,0,0)", np.round(p1 - p0, 4).tolist())
print("success", info.get("success"))
