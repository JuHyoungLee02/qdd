"""E-RC0 (docs/stage3/prereg_rc0.md): a RoboCasa365 target task as a qdd world (the protocol of the E-LIB0 episode class).

Environment = the official gym env (robocasa/<task>, split target, seed 7: the robocasa-benchmark/openpi eval loop);
the k-th episode is the k-th reset of that env (as the official loop). The arm only: base motion and torso stay 0.
Robot frame = robot0_base (mobile base body). TCP = gripper0_right_grip_site; base-frame TCP from the env's
robot0_base_to_eef_pos. Cameras: head = robot0_agentview_left (on the mobile base), wrist = robot0_eye_in_hand,
rendered by us from the MuJoCo camera (512 / 256 px) with metric depth and the robot's own pixels removed (as E-LIB0).
Control: the composite controller's arm OSC (input frame base, output_max 0.05 m / 0.5 rad per unit): position input =
(reference - TCP) / 0.05, rotation input = error to the start orientation / 0.5, both clipped to [-1, 1]; gripper
close >= 0.5. Pad gap = finger qpos difference x 10.7 / 8 (the trained scale, E-LIB0b). Success = info["success"]."""
from __future__ import annotations

import math

import numpy as np

from ..astra_motion.geometry import Cam
from ..astra_motion.harness import Obs
from ..lib0.world import quat_xyzw_to_R, rotvec_of

HEAD_CAM, WRIST_CAM = "robot0_agentview_left", "robot0_eye_in_hand"
HEAD_PX, WRIST_PX, VID_PX = 512, 256, 256
POS_SCALE, ROT_SCALE = 0.05, 0.5
ROBOT_PREFIX = ("robot0_", "gripper0_", "mobilebase0_")
GAP_SCALE = 10.7 / 8.0
W_CLOSE_REAL = 0.0018  # m, Panda fingers closed on nothing (E-LIB0 measurement, same Panda hand model)


def make_env(task: str):
    import gymnasium as gym
    import robocasa  # noqa: F401
    import robocasa.wrappers.gym_wrapper  # noqa: F401 -- registers robocasa/<task>
    return gym.make(f"robocasa/{task}", split="target", seed=7)


def task_horizon(task: str) -> int:
    from robocasa.utils.dataset_registry_utils import get_task_horizon
    return int(get_task_horizon(task) * 1.5)


class RcWorld:
    def __init__(self, task: str):
        self.task_name = task
        self.env = make_env(task)
        self.raw = self.env.unwrapped.env
        self.dt = 1.0 / float(self.raw.control_freq)
        self.w_close = W_CLOSE_REAL * GAP_SCALE
        self.table_z = None
        self.done = False
        self.quat0 = (1.0, 0.0, 0.0, 0.0)

    @property
    def sim(self):
        return self.raw.sim

    @property
    def robot_geoms(self) -> np.ndarray:
        m = self.sim.model
        return np.array(sorted(i for i in range(m.ngeom) if (m.geom_id2name(i) or "").startswith(ROBOT_PREFIX)), int)

    def _base(self):
        """The mobile base frame the env reports (state.base_position / base_rotation, xyzw): the frame of
        state.end_effector_position_relative and of the arm OSC input (the 'robot0_base' body is a fixed placeholder at
        (10, 10, 0) in RoboCasa: change 1, G1 geometry check)."""
        return quat_xyzw_to_R(self.obs["state.base_rotation"]), np.asarray(self.obs["state.base_position"], float)

    def to_base(self, p_w):
        R, t = self._base()
        return R.T @ (np.asarray(p_w, float) - t)

    def cam(self, name: str, W: int, H: int) -> Cam:
        cid = self.sim.model.camera_name2id(name)
        X = np.array(self.sim.data.cam_xmat[cid]).reshape(3, 3)
        Rw = np.stack([X[:, 0], -X[:, 1], -X[:, 2]], 1)
        Rb, tb = self._base()
        f = 0.5 * H / math.tan(math.radians(float(self.sim.model.cam_fovy[cid])) / 2.0)
        return Cam(name=name, W=W, H=H, fx=f, fy=f, cx=W / 2.0, cy=H / 2.0, R=Rb.T @ Rw,
                   t=Rb.T @ (np.array(self.sim.data.cam_xpos[cid]) - tb))

    def render(self, name, W, H, depth=False, seg=False):
        out = self.sim.render(width=W, height=H, camera_name=name, depth=depth)
        rgb, d = (out if depth else (out, None))
        rgb = np.ascontiguousarray(rgb[::-1])
        if d is not None:
            m = self.sim.model
            ext = float(m.stat.extent)
            near, far = float(m.vis.map.znear) * ext, float(m.vis.map.zfar) * ext
            d = near / (1.0 - np.asarray(d[::-1], float) * (1.0 - near / far))
        s = None
        if seg:
            sg = np.asarray(self.sim.render(width=W, height=H, camera_name=name, segmentation=True))[::-1]
            s = (sg[..., 0] == 5) & np.isin(sg[..., 1], self.robot_geoms)
        return rgb, d, s

    def _raw_obs(self):
        return self.raw._get_observations(force_update=True)

    def reset(self, seed=None, task=None) -> None:
        self.obs, _ = self.env.reset()
        self.instruction = self.obs["annotation.human.task_description"]
        self.t, self.done = 0.0, False
        self.R0 = quat_xyzw_to_R(self.obs["state.end_effector_rotation_relative"])  # base-frame (gym obs; _get_observations(force_update) would re-render every camera)
        self.w_open = float(self._gap())
        self.cmd_width = self.w_open
        self.table_z = self._measure_table()

    def _gap(self) -> float:
        q = np.asarray(self.obs["state.gripper_qpos"], float)
        return float(q[0] - q[1]) * GAP_SCALE

    def _measure_table(self) -> float:
        from ..astra_solo import resolve as RS
        _, d, s = self.render(HEAD_CAM, HEAD_PX, HEAD_PX, depth=True, seg=True)
        d = np.where(s, np.nan, d)
        z = RS.depth_points(self.cam(HEAD_CAM, HEAD_PX, HEAD_PX), d)[..., 2]
        z = z[np.isfinite(z) & (z < self.status()["tcp"][2])]
        h, e = np.histogram(z, bins=np.arange(z.min(), z.max() + 0.005, 0.005))
        k = int(np.argmax(h))
        return float((e[k] + e[k + 1]) / 2)

    def task_info(self) -> dict:
        return {"tgt": "o3", "place": "o5", "present": ["o3", "o5"], "instruction": self.instruction}

    def status(self) -> dict:
        tcp = np.asarray(self.obs["state.end_effector_position_relative"], float)  # = robot0_base_to_eef_pos
        return {"t": self.t, "tcp": tcp, "grip_w": self._gap(), "obj": {}, "pred": {}}

    def observe(self, depth: bool = False) -> Obs:
        head, d, s = self.render(HEAD_CAM, HEAD_PX, HEAD_PX, depth=depth, seg=depth)
        wr, _, _ = self.render(WRIST_CAM, WRIST_PX, WRIST_PX)
        st = self.status()
        dd = {"head": np.where(s, np.nan, d).astype(np.float32)} if depth else None
        return Obs(t=self.t, rgb={"head": head, "wrist": wr}, depth=dd,
                   cams={"head": self.cam(HEAD_CAM, HEAD_PX, HEAD_PX), "wrist": self.cam(WRIST_CAM, WRIST_PX, WRIST_PX)},
                   tcp=st["tcp"], grip_w=st["grip_w"])

    def frame(self) -> dict:
        h, _, _ = self.render(HEAD_CAM, VID_PX, VID_PX)
        w, _, _ = self.render(WRIST_CAM, VID_PX, VID_PX)
        return {"head": h, "wrist": w}

    def step(self, cmd_b, width: float, quat=None) -> None:
        from robocasa.utils.env_utils import convert_action
        self.cmd_width = float(width)
        dp = np.clip((np.asarray(cmd_b, float) - np.asarray(self.obs["state.end_effector_position_relative"], float))
                     / POS_SCALE, -1, 1)
        Rc = quat_xyzw_to_R(self.obs["state.end_effector_rotation_relative"])
        dr = np.clip(rotvec_of(self.R0 @ Rc.T) / ROT_SCALE, -1, 1)  # base-frame rotation error (OSC input frame base)
        a = np.zeros(12)
        a[0:3], a[3:6] = dp, dr
        a[6] = 1.0 if width < (self.w_open + self.w_close) / 2.0 else 0.0
        self.obs, _r, _d, _tr, info = self.env.step(convert_action(a))
        self.done = self.done or bool(info.get("success"))
        self.t += self.dt

    def holding(self) -> bool:
        return self.cmd_width < self.w_open - 1e-6 and self._gap() > self.w_close + 0.005

    def objects_of_interest(self) -> list:
        return []

    def object_names(self) -> list:
        return list(getattr(self.raw, "objects", {}).keys())

    def obj_pos(self, name):
        return None

    def close(self):
        try:
            self.env.close()
        except Exception:  # noqa: BLE001
            pass
