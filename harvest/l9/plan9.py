"""L9 v2 arm motion with cuRobo v0.8.0 (Apache-2.0; spec §12.5). cuRobo <= v0.7.8 is NC and never imported here.

Pure part (tested on the laptop):
  resample()        joint waypoints -> per-control-tick joint targets with max |dq| <= DQ_MAX (0.04 rad) under a
                    human-like timing profile (min-jerk bell / two-phase reach, motion9 styles)
  scene_cuboids()   furniture parts / object boxes (world) -> a cuRobo scene dict in the planner base frame
Pod part (cuRobo, torch): Planner9 = MotionPlanner of one (profile, arm) config:
  grasp()  pre-grasp approach (collision-aware) + straight approach along the tool z + lift (plan_grasp)
  pose()   collision-aware pose-to-pose (carry, pre-place), optionally with the held object attached
  line()   short straight move (place descent, retreat) = plan_pose with the target object's collision off
Frames: the planner works in its base link frame; callers pass world poses and the base link's world pose. The tool
frame is the grasp frame G of grasp9 (z_G = -approach), so plan_grasp's approach offset is +standoff along tool z."""
from __future__ import annotations

import math

import numpy as np

DQ_MAX = 0.04
CUROBO_MIN = (0, 8, 0)


def _profile(s: np.ndarray, kind: str, split: float) -> np.ndarray:
    if kind == "two_phase":  # fast transport then a slow final approach (motion9.two_phase)
        from .motion9 import two_phase
        return np.array([two_phase(float(v), split, 0.5) for v in s])
    return 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5  # min-jerk


PEAK = {"minjerk": 1.875, "two_phase": 2.6}


def resample(Q, dq_max: float = DQ_MAX, kind: str = "minjerk", split: float = 0.7, min_steps: int = 2,
             slow: float = 1.0) -> np.ndarray:
    """Dense joint waypoints (N, dof) -> (M, dof) targets, consecutive max-abs step <= dq_max, ends exact.
    The path is parametrised by cumulative L-inf joint distance and timed by the profile (slow >= 1 stretches)."""
    Q = np.asarray(Q, float)
    if len(Q) < 2:
        return Q.copy()
    seg = np.abs(np.diff(Q, axis=0)).max(1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    L = float(cum[-1])
    if L < 1e-9:
        return Q[[0, -1]]
    n = max(min_steps, int(math.ceil(L * PEAK.get(kind, 2.6) * 1.05 * slow / dq_max)))
    for _ in range(8):
        s = _profile(np.linspace(0.0, 1.0, n + 1), kind, split)
        d = s * L
        out = np.stack([np.interp(d, cum, Q[:, j]) for j in range(Q.shape[1])], 1)
        if np.abs(np.diff(out, axis=0)).max() <= dq_max + 1e-9:
            return out
        n = int(n * 1.25) + 1
    return out


def max_step(Q) -> float:
    Q = np.asarray(Q, float)
    return float(np.abs(np.diff(Q, axis=0)).max()) if len(Q) > 1 else 0.0


def _yaw_q(yaw: float) -> list:
    return [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]


def inv_T(T):
    R, t = T[:3, :3], T[:3, 3]
    out = np.eye(4)
    out[:3, :3], out[:3, 3] = R.T, -R.T @ t
    return out


def scene_cuboids(parts: list, boxes: dict, T_world_base, pad: float = 0.0) -> dict:
    """cuRobo scene dict {"cuboid": {name: {dims, pose[x y z qw qx qy qz]}}} in the base frame.
    parts: world furniture parts (prim cuboid, pos centre, size, yaw); boxes: {name: (centre, size, quat_wxyz)}."""
    from .grasp9 import mat_quat, qmat
    Tb = inv_T(np.asarray(T_world_base, float))
    out = {}

    def add(name, c, size, R):
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, c
        B = Tb @ T
        out[name] = {"dims": [float(v) + 2 * pad for v in size],
                     "pose": [*(float(v) for v in B[:3, 3]), *(float(v) for v in mat_quat(B[:3, :3]))]}
    for p in parts:
        if p.get("prim", "cuboid") != "cuboid" or p.get("role") in ("room_wall",):
            continue
        add(f"part_{p['id']}", np.asarray(p["pos"], float), p["size"], qmat(_yaw_q(float(p.get("yaw", 0.0)))))
    for k, (c, size, q) in boxes.items():
        add(k, np.asarray(c, float), size, qmat(q))
    return {"cuboid": out}


# ---------------------------------------------------------------------------------------------- pod (cuRobo)
class Planner9:
    """One cuRobo MotionPlanner per (profile, arm) config (robot yml from curobo9 / L9v2-ROBOT)."""

    def __init__(self, robot_cfg, device: str = "cuda:0", collision_cache: int = 64):
        import curobo
        v = tuple(int(x) for x in str(curobo.__version__).split(".")[:3])
        if v < CUROBO_MIN:
            raise RuntimeError(f"cuRobo {curobo.__version__} < 0.8.0 (NC licence): refused")
        from curobo.motion_planner import MotionPlanner, MotionPlannerCfg
        self.version = str(curobo.__version__)
        cfg = MotionPlannerCfg.create(robot=robot_cfg, scene_model={"cuboid": {"_floor": {
            "dims": [0.1, 0.1, 0.01], "pose": [5.0, 5.0, -5.0, 1, 0, 0, 0]}}},
            collision_cache={"cuboid": collision_cache}, max_goalset=1, num_ik_seeds=32, num_trajopt_seeds=4)
        self.mp = MotionPlanner(cfg)
        self.mp.warmup(enable_graph=True, num_warmup_iterations=3)
        self.torch = __import__("torch")
        self.dev = device
        self.attached = None

    @property
    def joint_names(self):
        return list(self.mp.joint_names)

    def world(self, scene: dict) -> None:
        from curobo._src.geom.types import SceneCfg
        if self.attached:
            self.detach()
        self.mp.update_world(SceneCfg.create(scene))

    def _js(self, q):
        from curobo.types import JointState
        t = self.torch.tensor(np.asarray(q, np.float32)[None], device=self.dev)
        return JointState.from_position(t, joint_names=self.joint_names)

    def _goal(self, T):
        from curobo.types import GoalToolPose
        from .grasp9 import mat_quat
        T = np.asarray(T, float)
        p = self.torch.tensor(T[:3, 3], dtype=self.torch.float32, device=self.dev).view(1, 1, 1, 1, 3)
        q = self.torch.tensor(mat_quat(T[:3, :3]), dtype=self.torch.float32, device=self.dev).view(1, 1, 1, 1, 4)
        return GoalToolPose(tool_frames=self.mp.tool_frames, position=p, quaternion=q)

    @staticmethod
    def _pos(traj) -> np.ndarray | None:
        if traj is None:
            return None
        P = traj.position.reshape(-1, traj.position.shape[-1]).cpu().numpy()
        keep = np.concatenate([[True], np.abs(np.diff(P, axis=0)).max(1) > 1e-6])  # drop padded repeats
        return P[keep]

    def grasp(self, q, T_grasp_base, standoff: float, lift_dz: float) -> dict:
        """-> {ok, status, approach, grasp, lift} joint arrays (approach ends at the pre-grasp)."""
        r = self.mp.plan_grasp(grasp_poses=self._goal(T_grasp_base), current_state=self._js(q),
                               grasp_approach_axis="z", grasp_approach_offset=float(standoff),
                               grasp_approach_in_tool_frame=True, grasp_lift_axis="z",
                               grasp_lift_offset=float(lift_dz), grasp_lift_in_tool_frame=False,
                               plan_approach_to_grasp=True, plan_grasp_to_lift=True)
        ok = r.success is not None and bool(r.success.any())
        return {"ok": ok, "status": str(getattr(r, "status", "")),
                "approach": self._pos(r.approach_interpolated_trajectory) if ok else None,
                "grasp": self._pos(r.grasp_interpolated_trajectory) if ok else None,
                "lift": self._pos(r.lift_interpolated_trajectory) if ok else None}

    def pose(self, q, T_base) -> np.ndarray | None:
        r = self.mp.plan_pose(self._goal(T_base), self._js(q))
        if r is None or not bool(r.success.any()):
            return None
        return self._pos(r.get_interpolated_plan())

    def ik(self, T_base_batch, q_seed=None):
        """Batched reach test: -> (ok (N,), q (N, dof), margin (N,)) for world-collision-aware IK of N tool poses."""
        from curobo.types import GoalToolPose
        from .grasp9 import mat_quat
        Ts = np.asarray(T_base_batch, float)
        n = len(Ts)
        p = self.torch.tensor(Ts[:, :3, 3], dtype=self.torch.float32, device=self.dev).view(n, 1, 1, 1, 3)
        qq = np.stack([mat_quat(T[:3, :3]) for T in Ts])
        q = self.torch.tensor(qq, dtype=self.torch.float32, device=self.dev).view(n, 1, 1, 1, 4)
        g = GoalToolPose(tool_frames=self.mp.tool_frames, position=p, quaternion=q)
        out_ok, out_q = np.zeros(n, bool), np.zeros((n, len(self.joint_names)))
        try:
            r = self.mp.ik_solver.solve_pose(g)
            out_ok = r.success.view(n, -1)[:, 0].cpu().numpy().astype(bool)
            out_q = r.solution.view(n, -1, len(self.joint_names))[:, 0].cpu().numpy()
        except Exception:  # batch size above the solver's: fall back to one by one
            for i in range(n):
                r = self.mp.ik_solver.solve_pose(self._goal(Ts[i]))
                out_ok[i] = bool(r.success.view(-1)[0])
                out_q[i] = r.solution.view(-1, len(self.joint_names))[0].cpu().numpy()
        lo, hi = self._limits()
        margin = np.minimum(out_q - lo, hi - out_q).min(1) / np.maximum((hi - lo).min(), 1e-6)
        return out_ok, out_q, margin

    def _limits(self):
        jl = self.mp.kinematics.get_joint_limits()
        pos = jl.position.cpu().numpy()
        return pos[0], pos[1]

    def attach(self, q, names: list) -> None:
        self.mp.attachment_manager.attach_from_scene(self._js(q), names)
        self.attached = names

    def detach(self) -> None:
        if self.attached:
            self.mp.attachment_manager.detach()
        self.attached = None
