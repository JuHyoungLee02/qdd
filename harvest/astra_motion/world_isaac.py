"""Isaac world for the probe (pod only; IR_ROOT=cyclo ir_run.sh). Uses harvest.sim read-only: make_env with the default
hard_reset=True (canon §78: every episode depends only on its seed) and all three real-robot cameras (head ZED Mini left
eye, left and right wrist D405; canon §43/§47, coupling spec §12), and OraclePlanner only as a helper for IK (DLS +
joint-step clamp + gravity offset), the TCP pose, the top-down grasp orientation and the oracle predicates.

Camera poses: Isaac Lab's camera pos_w / quat_w_* are read from USD, which physics (Fabric) does not update here -- at
reset they showed the head camera level and the wrist camera under the table while the renders were correct (sanity
2026-09-25, docs/stage3/prereg_astra_motion.md §0). So a camera pose = the LIVE parent-link body pose x the copied mount
transform (FFW_SG2_REAL_cameras.mount_transform); tests/astra_motion/test_camera_pose.py.
"""
from __future__ import annotations

import numpy as np

from . import geometry as G
from .harness import Obs

CAMS = ("cam_head", "cam_wrist_left", "cam_wrist_right")
KEYS = {"cam_head": "head", "cam_wrist_left": "wrist_left", "cam_wrist_right": "wrist"}
NO_RENDER = 10 ** 9  # = datagen.gen.NO_RENDER: the env never renders by itself
PRE_RENDER = 8  # = datagen.gen.PRE_RENDER (renderer warm-up after reset)
WORLD_CONV_TO_OPTICAL = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
# columns = optical x (right) = -Y, optical y (down) = -Z, optical z (forward) = +X of Isaac's "world" camera
# convention (+X forward, +Z up) -- the same matrix as Isaac's quat_w_ros for an identity quat_w_world


def camera_pose(robot, realcam, name: str):
    """(R_base_from_optical, t) of a camera: parent link body pose (live PhysX / Fabric data) composed with the
    mount transform of FFW_SG2_REAL_cameras (camera in its parent link, world convention)."""
    spec = realcam.CAMERA_SPECS[name]
    bi = robot.body_names.index(spec["parent"])
    p = robot.data.body_pos_w[0, bi].cpu().numpy().astype(float)
    q = robot.data.body_quat_w[0, bi].cpu().numpy().astype(float)
    m = realcam.mount_transform(name)
    Rb = G.quat_to_R(q)
    return Rb @ G.quat_to_R(m[3:]) @ WORLD_CONV_TO_OPTICAL, p + Rb @ np.asarray(m[:3], float)


class IsaacWorld:
    def __init__(self):
        from ..sim.scene import GRIP_MAX_W, make_env
        self.env = make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        self.dt = float(self.env.step_dt)
        self.table_z = float(self.env.table_top_z)
        self.w_open = float(GRIP_MAX_W)
        self._st = None
        self.last_obs = None

    # ------------------------------------------------------------------ episode
    def reset(self, seed: int, task: str) -> None:
        from ..sim.perturb import perturb
        from ..sim.planner import OraclePlanner
        env = self.env
        env.set_seed(seed, task)
        env.reset()
        perturb(env, "P0", seed)  # P0 = no perturbation (arms nothing)
        for _ in range(PRE_RENDER):
            env.env.sim.render()
        self.pl = OraclePlanner(env)
        self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
        self.quat0 = np.asarray(self.pl.goal_quat, float)  # top-down, the oracle's grasp yaw
        self.w_close = float(self.pl.w_close)
        self._st = None

    def task_info(self) -> dict:
        from ..sim.tasks import TASKS
        s = TASKS[self.env.task]
        return {"instruction": s.instruction, "tgt": s.target, "place": s.place, "present": list(self.env.present)}

    # ------------------------------------------------------------------ cameras
    def _cam(self, name: str, label: str) -> G.Cam:
        from ..sim.scene import load_realcam
        d = self.env.scene[name].data
        K = d.intrinsic_matrices[0].cpu().numpy()
        H, W = d.output["rgb"].shape[1:3]
        R, t = camera_pose(self.env.robot, load_realcam(), name)
        return G.Cam(label, int(W), int(H), float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2]), R, t)

    def _render(self):
        self.env.env.sim.render()
        for n in CAMS:
            self.env.scene[n].update(0.0, force_recompute=True)

    def observe(self, depth: bool = False) -> Obs:
        self._render()
        cams = {KEYS[n]: self._cam(n, KEYS[n]) for n in CAMS}
        rgb = {KEYS[n]: self.env.camera_rgb(n) for n in CAMS}
        st = self.status()
        self.last_obs = Obs(st["t"], rgb, None, cams, st["tcp"], st["grip_w"])
        return self.last_obs

    def frame(self) -> dict:
        self._render()
        return {"head": self.env.camera_rgb("cam_head"), "wrist": self.env.camera_rgb("cam_wrist_right"),
                "wrist_cam": self._cam("cam_wrist_right", "wrist")}

    # ------------------------------------------------------------------ control
    def step(self, cmd_pos, width: float, quat=None) -> None:
        from ..sim.planner import MAX_DQ_RAD, W_MAX, _slerp_step
        goal = self.pl.goal_quat if quat is None else np.asarray(quat, float)
        self.cmd_quat = _slerp_step(self.cmd_quat, goal, W_MAX * self.dt)
        q = self.pl._ik(np.asarray(cmd_pos, float), self.cmd_quat, MAX_DQ_RAD)
        self.env.step(np.concatenate([q, [float(width)]]).astype(np.float32))
        self._st = None

    def _status_from(self, pl) -> dict:
        env = self.env
        pl.observe()
        touched = set()
        for c in pl.contacts:
            if "gripper" in c:
                touched |= set(c) - {"gripper"}
        return {"t": round(float(env.sim_time), 6), "tcp": pl.tcp_pose()[0], "grip_w": float(env.gripper_width()),
                "pred": dict(pl.pred), "obj": {k: env.object_pose(k)[0].copy() for k in env.present},
                "gripper_contacts": touched}

    def status(self) -> dict:
        if self._st is None:
            self._st = self._status_from(self.pl)
        return self._st

    def run_oracle(self, on_tick) -> dict:
        from ..sim.planner import run_episode

        def cb(env, pl):
            on_tick(self._status_from(pl), pl.phase)
        res = run_episode(self.env, "P0", self.env.seed, on_step=cb)
        res.pop("planner", None)
        self._st = None
        return {k: v for k, v in res.items() if k in ("success", "stage", "info", "phases", "grasp_rel_mm",
                                                      "sim_time_s", "tgt_place_xy_mm")}
