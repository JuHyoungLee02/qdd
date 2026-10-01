"""E-SIM0 setup probe (no model): make one SimplerEnv Google Robot env, reset, print obs keys / camera params / the
controller, save the head image. usage: probe_simpler.py <task> <out dir>"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

import simpler_env
from simpler_env.utils.env.observation_utils import get_image_from_maniskill2_obs_dict

task, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
t0 = time.time()
env = simpler_env.make(task)
obs, info = env.reset()
print("make+reset s", round(time.time() - t0, 1), "instruction", env.get_language_instruction())
print("obs keys", list(obs.keys()), {k: list(v.keys()) for k, v in obs.items() if isinstance(v, dict)})
for cam, d in obs.get("image", {}).items():
    print(cam, {k: np.asarray(v).shape for k, v in d.items()})
print("camera_param", json.dumps({c: {k: np.round(np.asarray(v), 4).tolist() for k, v in d.items()}
                                  for c, d in obs.get("camera_param", {}).items()})[:1500])
def sh(d):
    return {k: (sh(v) if isinstance(v, dict) else np.round(np.asarray(v, float), 4).tolist()) for k, v in d.items()}
print("agent", sh(obs.get("agent", {})))
print("extra", sh(obs.get("extra", {})))
print("control_mode", getattr(env.unwrapped, "_control_mode", None), "action_space", env.action_space)
img = get_image_from_maniskill2_obs_dict(env, obs)
Image.fromarray(img).save(os.path.join(out, f"probe_{task}.png"))
t1 = time.time()
for _ in range(10):
    obs, r, done, trunc, info = env.step(np.zeros(env.action_space.shape))
print("step s", round((time.time() - t1) / 10, 3), "info", {k: v for k, v in info.items() if not isinstance(v, np.ndarray)})
