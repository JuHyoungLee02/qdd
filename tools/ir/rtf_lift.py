"""Task 10 Step 6: RTF of Isaac-Lift-Cube-Franka-v0 driven through inspect-robots eval
via the stock IsaacSimEmbodiment adapter.

usage: python.sh rtf_lift.py {cam|nocam} [sim_seconds=60]
cam  : AppLauncher(enable_cameras=True) + one 224x224 TiledCamera 'base_rgb' added to the
       Lift scene and to the policy obs group (the stock Lift task has no camera).
Wall time is measured from the first policy.act() to the end of the rollout (boot and env
creation excluded; they are reported separately).
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

MODE = sys.argv[1]
SIM_S = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
OUT = "/data/juhyoung_qdd/ir/rtf"
CAM = MODE == "cam"

t_boot0 = time.perf_counter()
from isaaclab.app import AppLauncher  # noqa: E402

app = AppLauncher(headless=True, device="cuda:0", enable_cameras=CAM).app
t_boot = time.perf_counter() - t_boot0

import gymnasium as gym  # noqa: E402
import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import inspect_robots_isaacsim.embodiment as E  # noqa: E402
from inspect_robots import (  # noqa: E402
    ActionChunk, ObservationSpace, PolicyBase, PolicyInfo, Scene, Task, eval,
)
from inspect_robots.types import Action  # noqa: E402

E._ACTIVE_APP = app  # adapter reuses our launched app (process singleton)
TASK = "Isaac-Lift-Cube-Franka-v0"
emb = E.IsaacSimEmbodiment(TASK, cameras=(("base_rgb", 224, 224, 3),) if CAM else ())

t_env0 = time.perf_counter()
env_cfg = parse_env_cfg(TASK, device="cuda:0", num_envs=1)
env_cfg.episode_length_s = SIM_S + 10.0  # one continuous episode (default 5 s would time out)
E._disable_debug_vis(env_cfg)
if CAM:
    import isaaclab.sim as sim_utils
    from isaaclab.envs import mdp
    from isaaclab.managers import ObservationTermCfg as ObsTerm
    from isaaclab.managers import SceneEntityCfg
    from isaaclab.sensors import TiledCameraCfg

    env_cfg.scene.base_rgb = TiledCameraCfg(
        prim_path="{ENV_REGEX_NS}/base_rgb",
        offset=TiledCameraCfg.OffsetCfg(pos=(1.5, 0.0, 0.7), rot=(0.0, -0.2588, 0.0, 0.9659),
                                        convention="world"),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(focal_length=18.0, clipping_range=(0.05, 10.0)),
        width=224, height=224,
    )
    env_cfg.observations.policy.base_rgb = ObsTerm(
        func=mdp.image, params={"sensor_cfg": SceneEntityCfg("base_rgb"), "data_type": "rgb",
                                "normalize": False})
E._request_named_obs_terms(env_cfg, "policy")
emb._ensure_app()
emb._env = gym.make(TASK, cfg=env_cfg, render_mode="rgb_array")
t_env = time.perf_counter() - t_env0
step_dt = float(emb._env.unwrapped.step_dt)
n_steps = int(round(SIM_S / step_dt))


class Hold(PolicyBase):
    """Zero action = hold Lift default joint pose (use_default_offset), gripper open."""

    info = PolicyInfo(name="hold", action_space=emb.info.action_space,
                      observation_space=ObservationSpace())

    def __init__(self):
        self.t_first = None
        self.n = 0
        self.img_shape = None
        self.saved = False

    def act(self, obs):
        if self.t_first is None:
            self.t_first = time.perf_counter()
        self.n += 1
        if "base_rgb" in obs.images:
            im = obs.images["base_rgb"]
            self.img_shape = tuple(im.shape)
            if not self.saved and self.n == 50:
                np.save(f"{OUT}/frame_{MODE}.npy", im)
                try:
                    from PIL import Image
                    Image.fromarray(np.asarray(im, dtype=np.uint8)).save(f"{OUT}/frame_{MODE}.png")
                except Exception as e:  # noqa: BLE001
                    print("[rtf] PNG save failed:", e)
                self.saved = True
        return ActionChunk(actions=[Action(data=np.array([0.0] * 7 + [1.0], dtype=np.float32))])


pol = Hold()
task = Task(name=f"rtf-lift-{MODE}", scenes=[Scene(id="s0", instruction="lift the cube", init_seed=0)],
            scorer="episode_length", max_steps=n_steps)
log = eval(task, pol, emb, log_dir=f"{OUT}/logs", seed=0)[0]
t_end = time.perf_counter()
wall = t_end - pol.t_first
sim_t = pol.n * step_dt
res = dict(mode=MODE, task=TASK, step_dt=step_dt, steps=pol.n, sim_time_s=sim_t,
           wall_s=round(wall, 2), rtf=round(sim_t / wall, 3), boot_s=round(t_boot, 1),
           env_create_s=round(t_env, 1), img_shape=pol.img_shape, status=str(log.status),
           ms_per_step=round(wall / pol.n * 1e3, 2))
print("RTF_RESULT " + json.dumps(res), flush=True)
with open(f"{OUT}/rtf_{MODE}.json", "w") as f:
    json.dump(res, f)
emb.close()
