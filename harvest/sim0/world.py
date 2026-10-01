"""E-SIM0 (docs/stage3/prereg_sim0.md): a SimplerEnv Google Robot visual-matching episode as a qdd world (the
astra_motion.harness protocol used by the E-CL15 / E-LIB0 episode classes).

Environment construction = simpler_env.evaluation.maniskill2_evaluator.run_maniskill2_eval_single_episode with the
standard rt1_*_visual_matching.sh arguments (obs_mode rgbd + segmentation, control 3 Hz, sim 513 Hz, the standard
control mode, scene, real-image overlay, robot init pose, object init xy / episode id, URDF None).
Robot frame = the robot base (agent.base_pose). Head camera = overhead_camera (on link_camera), from camera_param
(intrinsic_cv, extrinsic_cv); its depth (m) with the robot's own pixels (segmentation of the robot links) set invalid.
No wrist camera on this robot: image 2 is a blank grey image (the episode states it in the prompt).
Control: arm EE delta pose in the base frame (frame ee_align: delta position + base-frame rotation vector, metres /
radians, unnormalised), the executor's TCP reference minus the TCP; rotation back to the start orientation (about 20 deg
from straight down; fingers close along base x); gripper +1 close / -1 open (target delta, held every step).
Pad gap = distance of the two finger-nail links x GAP_SCALE (the trained scale: fully open reads 10.7 cm).
Success = the env's `success` at a control step (the episode stops there; prereg §3)."""
from __future__ import annotations

import math

import numpy as np

from ..astra_motion.geometry import Cam
from ..astra_motion.harness import Obs

ROOT = "/data/harvest/simpler/SimplerEnv"
CONTROL = ("arm_pd_ee_delta_pose_align_interpolate_by_planner_gripper_pd_joint_target_delta_pos_interpolate_by_planner")
COKE = dict(env="GraspSingleOpenedCokeCanInScene-v0", scene="google_pick_coke_can_1_v4",
            overlay="ManiSkill2_real2sim/data/real_inpainting/google_coke_can_real_eval_1.png",
            robot_xy=(0.35, 0.20), rpy=(0.0, 0.0, 0.0), max_steps=80)
NEAR = dict(env="MoveNearGoogleBakedTexInScene-v0", scene="google_pick_coke_can_1_v4",
            overlay="ManiSkill2_real2sim/data/real_inpainting/google_move_near_real_eval_1.png",
            robot_xy=(0.35, 0.21), rpy=(0.0, 0.0, -0.09), max_steps=80)
COKE_OPTS = ("lr_switch", "upright", "laid_vertically")
COKE_X, COKE_Y = np.linspace(-0.35, -0.12, 5), np.linspace(-0.02, 0.42, 5)
OPEN_NAIL_M = 0.218  # nail-link distance fully open (tools/sim0/robot_geom.py)
GAP_SCALE = 0.107 / OPEN_NAIL_M
HEAD_W, HEAD_H, WRIST_PX, VID_W = 640, 512, 256, 320
ROBOT_LINK_PREFIX = ("link_",)


def episodes() -> list:
    """The pilot list (prereg §3): coke 3 orientations x 5 x 5 positions, move near episodes 0-59."""
    out = [{"task": "coke", "opt": o, "i": i, "j": j} for o in COKE_OPTS for i in range(5) for j in range(5)]
    return out + [{"task": "near", "episode": e} for e in range(60)]


def ep_name(e: dict) -> str:
    return f"coke_{e['opt']}_x{e['i']}y{e['j']}" if e["task"] == "coke" else f"near_e{e['episode']:02d}"


def make_env(e: dict):
    """The standard evaluator's env + reset options for episode spec e -> (env, reset options, max steps)."""
    import os

    import sapien.core as sapien
    from simpler_env.utils.env.env_builder import build_maniskill2_env
    from transforms3d.euler import euler2quat
    spec = COKE if e["task"] == "coke" else NEAR
    extra = {"urdf_version": None}
    if e["task"] == "coke":
        extra[e["opt"]] = True
    env = build_maniskill2_env(spec["env"], obs_mode="rgbd", robot="google_robot_static", sim_freq=513,
                               control_mode=CONTROL, control_freq=3, max_episode_steps=spec["max_steps"],
                               scene_name=spec["scene"], camera_cfgs={"add_segmentation": True},
                               rgb_overlay_path=os.path.join(ROOT, spec["overlay"]), **extra)
    quat = (sapien.Pose(q=euler2quat(*spec["rpy"])) * sapien.Pose(q=[0, 0, 0, 1])).q
    opts = {"robot_init_options": {"init_xy": np.array(spec["robot_xy"]), "init_rot_quat": quat}}
    if e["task"] == "coke":
        opts["obj_init_options"] = {"init_xy": np.array([COKE_X[e["i"]], COKE_Y[e["j"]]])}
    else:
        opts["obj_init_options"] = {"episode_id": e["episode"]}
    return env, opts, spec["max_steps"]


def pose7_to_Rt(p7):
    """[x, y, z, qw, qx, qy, qz] -> (R, t)."""
    w, x, y, z = (float(v) for v in p7[3:7])
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    return R, np.asarray(p7[:3], float)


def rotvec(R: np.ndarray) -> np.ndarray:
    from scipy.spatial.transform import Rotation
    return Rotation.from_matrix(R).as_rotvec()


class SimWorld:
    CAM = "overhead_camera"

    def __init__(self, e: dict):
        self.e = e
        self.env, self.opts, self.max_steps = make_env(e)
        self.dt = 1.0 / 3.0
        self.w_close = 0.0
        self.table_z = None
        self.done = False
        self.quat0 = (1.0, 0.0, 0.0, 0.0)

    # ------------------------------------------------------------------ frames
    def _base_Rt(self):
        bp = np.asarray(self.obs["agent"]["base_pose"], float)  # [x, y, z, qw, qx, qy, qz] (sapien order)
        return pose7_to_Rt(bp)

    def to_base(self, p_w):
        R, t = self._base_Rt()
        return R.T @ (np.asarray(p_w, float) - t)

    def tcp_Rt(self):
        R, t = pose7_to_Rt(np.asarray(self.obs["extra"]["tcp_pose"], float))
        Rb, tb = self._base_Rt()
        return Rb.T @ R, Rb.T @ (t - tb)

    def head_cam(self) -> Cam:
        cp = self.obs["camera_param"][self.CAM]
        K, E = np.asarray(cp["intrinsic_cv"], float), np.asarray(cp["extrinsic_cv"], float)
        Rcw, tcw = E[:3, :3], E[:3, 3]
        Rwc, pw = Rcw.T, -Rcw.T @ tcw
        Rb, tb = self._base_Rt()
        H, W = self.obs["image"][self.CAM]["rgb"].shape[:2]
        return Cam(name=self.CAM, W=W, H=H, fx=K[0, 0], fy=K[1, 1], cx=K[0, 2], cy=K[1, 2], R=Rb.T @ Rwc,
                   t=Rb.T @ (pw - tb))

    def _robot_ids(self):
        if not hasattr(self, "_rid"):
            u = self.env.unwrapped
            self._rid = np.array([l.get_id() for l in u.agent.robot.get_links()], int)
        return self._rid

    # ------------------------------------------------------------------ protocol
    def reset(self, seed=None, task=None) -> None:
        self.obs, _ = self.env.reset(options=self.opts)
        self.instruction = self.env.get_language_instruction()
        self.t, self.done, self.success_any = 0.0, False, False
        Rc, _ = self.tcp_Rt()
        self.R_goal = Rc  # the start orientation is kept (a straight-down target makes the controller's IK fail: G0 debug)
        self.w_open = float(self._gap())
        self.cmd_width = self.w_open
        if self.table_z is None:
            self.table_z = self._measure_table()

    @staticmethod
    def _down(Rc: np.ndarray) -> np.ndarray:
        """Target TCP rotation: the local axis now most aligned with -z (approach) -> -z exactly; the local axis
        most aligned with base x (closing direction) -> +-x (sign kept); third axis by the right-hand rule."""
        a = int(np.argmin(Rc[2]))  # column most pointing down
        rest = [k for k in range(3) if k != a]
        c = max(rest, key=lambda k: abs(Rc[0, k]))
        R = np.zeros((3, 3))
        R[:, a] = [0, 0, -1]
        R[:, c] = [np.sign(Rc[0, c]) or 1.0, 0, 0]
        o = [k for k in range(3) if k not in (a, c)][0]
        R[:, o] = np.cross(R[:, (o + 1) % 3], R[:, (o + 2) % 3])
        return R

    def _gap(self) -> float:
        u = self.env.unwrapped
        ls = {l.name: l for l in u.agent.robot.get_links()}
        d = np.linalg.norm(ls["link_finger_nail_left"].pose.p - ls["link_finger_nail_right"].pose.p)
        return float(d) * GAP_SCALE

    def _measure_table(self) -> float:
        from ..astra_solo import resolve as RS
        o = self.observe(depth=True)
        z = RS.depth_points(o.cams["head"], o.depth["head"])[..., 2]
        z = z[np.isfinite(z) & (z < self.status()["tcp"][2])]
        h, e = np.histogram(z, bins=np.arange(z.min(), z.max() + 0.005, 0.005))
        k = int(np.argmax(h))
        return float((e[k] + e[k + 1]) / 2)

    def task_info(self) -> dict:
        return {"tgt": "o3", "place": "o5", "present": ["o3", "o5"], "instruction": self.instruction}

    def status(self) -> dict:
        _, t = self.tcp_Rt()
        return {"t": self.t, "tcp": t, "grip_w": self._gap(), "obj": {}, "pred": {}}

    def observe(self, depth: bool = False) -> Obs:
        im = self.obs["image"][self.CAM]
        rgb = np.ascontiguousarray(im["rgb"][..., :3]).astype(np.uint8)
        d = None
        if depth:
            dep = np.asarray(im["depth"], float)[..., 0]
            seg = np.asarray(im["Segmentation"])[..., 1]
            dep = np.where(np.isin(seg, self._robot_ids()) | (dep <= 0), np.nan, dep)
            d = {"head": dep.astype(np.float32)}
        wrist = np.full((WRIST_PX, WRIST_PX, 3), 128, np.uint8)
        st = self.status()
        cam = self.head_cam()
        wcam = Cam(name="none", W=WRIST_PX, H=WRIST_PX, fx=1.0, fy=1.0, cx=0.0, cy=0.0, R=np.eye(3), t=st["tcp"])
        return Obs(t=self.t, rgb={"head": rgb, "wrist": wrist}, depth=d, cams={"head": cam, "wrist": wcam},
                   tcp=st["tcp"], grip_w=st["grip_w"])

    def frame(self) -> dict:
        rgb = np.ascontiguousarray(self.obs["image"][self.CAM]["rgb"][..., :3]).astype(np.uint8)
        return {"head": rgb, "wrist": None}

    def action_of(self, cmd_b, width: float) -> np.ndarray:
        Rc, tc = self.tcp_Rt()
        dp = np.asarray(cmd_b, float) - tc
        dr = rotvec(self.R_goal @ Rc.T)
        n = np.linalg.norm(dr)
        if n > 0.5:  # per 1/3 s step
            dr = dr / n * 0.5
        g = 1.0 if width < (self.w_open + self.w_close) / 2.0 else -1.0
        return np.concatenate([dp, dr, [g]])

    def step(self, cmd_b, width: float, quat=None) -> None:
        self.cmd_width = float(width)
        self.obs, _r, done, _trunc, info = self.env.step(self.action_of(cmd_b, width))
        self.done = self.done or bool(info.get("success", done))
        self.t += self.dt

    def holding(self) -> bool:
        return self.cmd_width < self.w_open - 1e-6 and self._gap() > self.w_close + 0.005

    def objects_of_interest(self) -> list:
        return []

    def object_names(self) -> list:
        return []

    def obj_pos(self, name):
        return None

    def close(self) -> None:
        try:
            self.env.close()
        except Exception:  # noqa: BLE001
            pass
