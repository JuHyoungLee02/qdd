"""E-LIB0 (docs/stage3/prereg_lib0.md): a LIBERO task as a qdd world (the astra_motion.harness protocol used by the
E-CL15 episode classes: reset / task_info / observe / status / step, dt, table_z, w_open, w_close, quat0).

Environment construction and episode start are openpi's examples/libero/main.py (Apache-2.0): OffScreenRenderEnv with
the 256 px cameras, env.seed(7), reset, set_init_state(standard init state k), 10 dummy steps ([0]*6 + [-1]). Success =
the env's `done` (= LIBERO _check_success()) at any control step, as openpi counts it.

Robot frame = the robosuite robot base body (robot0_base): x forward, y left, z up (the frame the prompt describes).
Cameras (Cam, OpenCV optical axes, base frame): the MuJoCo camera pose (cam_xpos / cam_xmat: x right, y up, looking
along -z) and fovy (square pixels: fx = fy = H / 2 / tan(fovy / 2)). sim.render images are bottom-up -> flipped
vertically (the true camera view). Depth: the z-buffer -> metric optical z (robosuite camera_utils formula); the robot's
own pixels (segmentation of robot0_ / gripper0_ / mount0_ geoms) are set invalid (nan) -- robot self-measurement that
replaces the L8S-only height rule resolve.robot_mask (prereg §2).

Control: the LIBERO default OSC_POSE controller (delta, 20 Hz): position input = (TCP reference - TCP now) / 0.05 m,
orientation input = the rotation error to the start orientation / 0.5 rad, both clipped to [-1, 1]; gripper +1 close,
-1 open (from the executor's commanded width)."""
from __future__ import annotations

import math
import os

import numpy as np

from ..astra_motion.geometry import Cam
from ..astra_motion.harness import Obs

SUITES = ("libero_spatial", "libero_object", "libero_goal", "libero_10")
MAX_STEPS = {"libero_spatial": 220, "libero_object": 280, "libero_goal": 300, "libero_10": 520}  # openpi main.py
WAIT_STEPS = 10
DUMMY = [0.0] * 6 + [-1.0]
ENV_SEED = 7
ENV_RES = 256  # openpi LIBERO_ENV_RESOLUTION
HEAD_CAM, WRIST_CAM = "agentview", "robot0_eye_in_hand"
HEAD_PX, WRIST_PX, VID_PX = 512, 256, 256
POS_SCALE, ROT_SCALE = 0.05, 0.5  # OSC_POSE output_max (robosuite default controller config)
ROBOT_PREFIX = ("robot0_", "gripper0_", "mount0_")
W_CLOSE = 0.0  # Franka fingers closed on nothing: pad gap ~0
# E-LIB0b (prereg_lib0.md change 2, measured with tools/lib0/franka_geom.py / franka_mesh.py)
GAP_SCALE_B = 10.7 / 8.0  # Franka gap (max ~8 cm) -> the trained AI Worker scale (fully open 10.7 cm)
W_CLOSE_B = 0.0018  # m, Franka gap after a close on nothing (measured), before the scale
TABLE_BIN_M = 0.005
HORIZON = 100000  # robosuite time-out (raises past it) moved out of reach for the qdd arm: its own limits end episodes
# (LIBERO step: done = _check_success() only). use_camera_obs=False: the 256 px observations are never used by this arm.


def task_of(suite: str, task_id: int):
    from libero.libero import benchmark, get_libero_path
    ts = benchmark.get_benchmark_dict()[suite]()
    task = ts.get_task(task_id)
    bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
    return task, bddl, ts.get_task_init_states(task_id), ts.n_tasks


def make_env(bddl: str, res: int = ENV_RES, **kw):
    """openpi _get_libero_env (+ optional kwargs, e.g. horizon for the qdd arm)."""
    from libero.libero.envs import OffScreenRenderEnv
    env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=res, camera_widths=res, **kw)
    env.seed(ENV_SEED)
    return env


def start_episode(env, init_state):
    """openpi: reset, set the init state, 10 dummy steps -> (obs, done)."""
    env.reset()
    obs = env.set_init_state(init_state)
    done = False
    for _ in range(WAIT_STEPS):
        obs, _r, done, _i = env.step(DUMMY)
    return obs, done


def quat_xyzw_to_R(q) -> np.ndarray:
    x, y, z, w = (float(v) for v in q)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def rotvec_of(R: np.ndarray) -> np.ndarray:
    """Axis-angle vector of a rotation matrix."""
    c = max(-1.0, min(1.0, (np.trace(R) - 1.0) / 2.0))
    th = math.acos(c)
    if th < 1e-9:
        return np.zeros(3)
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    s = math.sin(th)
    if s < 1e-6:  # ~180 deg: axis from the diagonal
        a = np.sqrt(np.maximum((np.diag(R) + 1.0) / 2.0, 0.0))
        return a / max(np.linalg.norm(a), 1e-12) * th
    return v / (2 * s) * th


def obj_name(bddl_name: str) -> str:
    """'akita_black_bowl_1' -> 'akita black bowl'."""
    parts = bddl_name.split("_")
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    return " ".join(parts)


class LiberoWorld:
    def __init__(self, suite: str, task_id: int, depth: bool = True):
        self.suite, self.task_id = suite, int(task_id)
        self.task, self.bddl, self.init_states, _ = task_of(suite, task_id)
        self.env = make_env(self.bddl, horizon=HORIZON, use_camera_obs=False)  # renders only when observed
        self.dt = 1.0 / float(self.rs.control_freq)
        self.w_close = W_CLOSE
        self.gap_scale = 1.0  # E-LIB0b: every pad gap the code sees / reports x GAP_SCALE_B (the trained scale)
        self.table_z = None
        self.cmd_width = None
        self.done = False

    # ------------------------------------------------------------------ frames
    @property
    def rs(self):  # the robosuite / LIBERO domain env
        return self.env.env

    @property
    def sim(self):  # a hard reset rebuilds the MjSim: never keep it
        return self.env.env.sim

    @property
    def robot_geoms(self) -> np.ndarray:
        m = self.sim.model
        return np.array(sorted(i for i in range(m.ngeom) if (m.geom_id2name(i) or "").startswith(ROBOT_PREFIX)), int)

    def _base(self):
        bid = self.sim.model.body_name2id("robot0_base")
        return np.array(self.sim.data.body_xmat[bid]).reshape(3, 3), np.array(self.sim.data.body_xpos[bid])

    def to_base(self, p_w):
        R, t = self._base()
        return R.T @ (np.asarray(p_w, float) - t)

    def to_world(self, p_b):
        R, t = self._base()
        return R @ np.asarray(p_b, float) + t

    def cam(self, name: str, W: int, H: int) -> Cam:
        cid = self.sim.model.camera_name2id(name)
        X = np.array(self.sim.data.cam_xmat[cid]).reshape(3, 3)
        Rw = np.stack([X[:, 0], -X[:, 1], -X[:, 2]], 1)  # OpenCV axes (right, down, forward) in the world
        Rb, tb = self._base()
        f = 0.5 * H / math.tan(math.radians(float(self.sim.model.cam_fovy[cid])) / 2.0)
        return Cam(name=name, W=W, H=H, fx=f, fy=f, cx=W / 2.0, cy=H / 2.0, R=Rb.T @ Rw,
                   t=Rb.T @ (np.array(self.sim.data.cam_xpos[cid]) - tb))

    def render(self, name: str, W: int, H: int, depth: bool = False, seg: bool = False):
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
            sg = self.sim.render(width=W, height=H, camera_name=name, segmentation=True)
            sg = np.asarray(sg)[::-1]
            s = (sg[..., 0] == 5) & np.isin(sg[..., 1], self.robot_geoms)  # mjOBJ_GEOM = 5
        return rgb, d, s

    # ------------------------------------------------------------------ protocol
    def reset(self, seed: int, task=None) -> None:
        """seed = the standard init-state index k (0..49)."""
        self.k = int(seed)
        self.obs, self.done = start_episode(self.env, self.init_states[self.k])
        self.t = 0.0
        self.R0 = quat_xyzw_to_R(self.obs["robot0_eef_quat"])  # world orientation kept by the executor
        self.w_open = float(self._gap())
        self.cmd_width = self.w_open
        self.quat0 = (1.0, 0.0, 0.0, 0.0)
        if self.table_z is None:
            self.table_z = self._measure_table()

    def _gap(self) -> float:
        q = np.asarray(self.obs["robot0_gripper_qpos"], float)
        return float(q[0] - q[1]) * self.gap_scale

    def _measure_table(self) -> float:
        """Prior table height = the mode (5 mm bins) of the head depth points' heights below the TCP (first frame)."""
        from ..astra_solo import resolve as RS
        _, d, s = self.render(HEAD_CAM, HEAD_PX, HEAD_PX, depth=True, seg=True)
        d = np.where(s, np.nan, d)
        z = RS.depth_points(self.cam(HEAD_CAM, HEAD_PX, HEAD_PX), d)[..., 2]
        z = z[np.isfinite(z) & (z < self.status()["tcp"][2])]
        h, e = np.histogram(z, bins=np.arange(z.min(), z.max() + TABLE_BIN_M, TABLE_BIN_M))
        k = int(np.argmax(h))
        return float((e[k] + e[k + 1]) / 2)

    def task_info(self) -> dict:
        """Dummy L8S ids keep the prompt builders' lookups valid; the LIBERO task block replaces their lines
        (run_a.lib_block)."""
        return {"tgt": "o3", "place": "o5", "present": ["o3", "o5"], "instruction": self.task.language}

    def status(self) -> dict:
        return {"t": self.t, "tcp": self.to_base(self.obs["robot0_eef_pos"]), "grip_w": self._gap(), "obj": {},
                "pred": {}}

    def observe(self, depth: bool = False) -> Obs:
        head_rgb, d, s = self.render(HEAD_CAM, HEAD_PX, HEAD_PX, depth=depth, seg=depth)
        wr, _, _ = self.render(WRIST_CAM, WRIST_PX, WRIST_PX)
        st = self.status()
        dd = {"head": np.where(s, np.nan, d).astype(np.float32)} if depth else None
        return Obs(t=self.t, rgb={"head": head_rgb, "wrist": wr}, depth=dd,
                   cams={"head": self.cam(HEAD_CAM, HEAD_PX, HEAD_PX), "wrist": self.cam(WRIST_CAM, WRIST_PX, WRIST_PX)},
                   tcp=st["tcp"], grip_w=st["grip_w"])

    def frame(self) -> dict:
        h, _, _ = self.render(HEAD_CAM, VID_PX, VID_PX)
        w, _, _ = self.render(WRIST_CAM, VID_PX, VID_PX)
        return {"head": h, "wrist": w}

    def action_of(self, cmd_b, width: float) -> np.ndarray:
        p_w = self.to_world(cmd_b)
        dp = np.clip((p_w - np.asarray(self.obs["robot0_eef_pos"], float)) / POS_SCALE, -1.0, 1.0)
        Rc = quat_xyzw_to_R(self.obs["robot0_eef_quat"])
        dr = np.clip(rotvec_of(self.R0 @ Rc.T) / ROT_SCALE, -1.0, 1.0)
        g = 1.0 if width < (self.w_open + self.w_close) / 2.0 else -1.0
        return np.concatenate([dp, dr, [g]])

    def step(self, cmd_b, width: float, quat=None) -> None:
        self.cmd_width = float(width)
        self.obs, _r, done, _i = self.env.step(self.action_of(cmd_b, width).tolist())
        self.done = self.done or bool(done)
        self.t += self.dt

    def holding(self) -> bool:
        return self.cmd_width < self.w_open - 1e-6 and self._gap() > self.w_close + 0.005

    def objects_of_interest(self) -> list:
        return list(getattr(self.rs, "obj_of_interest", []) or [])

    def object_names(self) -> list:
        """Movable objects and non-table fixtures of the BDDL problem (names as in the BDDL)."""
        names = list(getattr(self.rs, "objects_dict", {}).keys()) + [k for k in getattr(self.rs, "fixtures_dict", {})
                                                                     if "table" not in k]
        return names

    def obj_pos(self, name: str):
        """Sim truth (scoring / checks only, never in the prompt)."""
        try:
            return self.to_base(self.sim.data.body_xpos[self.rs.obj_body_id[name]])
        except Exception:  # noqa: BLE001
            return None

    def close(self) -> None:
        try:
            self.env.close()
        except Exception:  # noqa: BLE001
            pass
