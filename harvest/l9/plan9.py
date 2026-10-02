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
import os

import numpy as np

DQ_MAX = 0.04
# (IK seeds, trajopt seeds, plan attempts); L9_CUROBO="ik,trajopt,attempts" overrides (speed A/B, 10-02 profile:
# cuRobo was 47 % of the lane wall time)
SEEDS = tuple(int(x) for x in os.environ.get("L9_CUROBO", "64,12,8").split(","))
IK_BATCH = 128
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

    def __init__(self, robot_cfg, device: str = "cuda:0", collision_cache: int = 64, self_collision: bool = True):
        import curobo
        v = tuple(int(x) for x in str(curobo.__version__).split(".")[:3])
        if v < CUROBO_MIN:
            raise RuntimeError(f"cuRobo {curobo.__version__} < 0.8.0 (NC licence): refused")
        from curobo.motion_planner import MotionPlanner, MotionPlannerCfg
        self.version = str(curobo.__version__)
        import copy
        self._robot_cfg = copy.deepcopy(robot_cfg)
        cp = (lambda: copy.deepcopy(self._robot_cfg)) if isinstance(robot_cfg, dict) else (lambda: robot_cfg)
        cfg = MotionPlannerCfg.create(robot=cp(), scene_model={"cuboid": {"_floor": {
            "dims": [0.1, 0.1, 0.01], "pose": [5.0, 5.0, -5.0, 1, 0, 0, 0]}}},
            collision_cache={"cuboid": collision_cache}, max_goalset=1, num_ik_seeds=SEEDS[0], num_trajopt_seeds=SEEDS[1],
            self_collision_check=self_collision)
        self.mp = MotionPlanner(cfg)

        self.mp.warmup(enable_graph=True, num_warmup_iterations=3)
        from curobo.inverse_kinematics import InverseKinematics, InverseKinematicsCfg
        self.ikb = InverseKinematics(InverseKinematicsCfg.create(  # batched reach checks (candidate filtering)
            robot=cp(), scene_model={"cuboid": {"_floor": {"dims": [0.1, 0.1, 0.01],
                                                               "pose": [5.0, 5.0, -5.0, 1, 0, 0, 0]}}},
            num_seeds=int(os.environ.get("L9_IK_SEEDS_CANDIDATE", "16")), self_collision_check=True,
            max_batch_size=IK_BATCH, collision_cache={"cuboid": collision_cache}))
        self.torch = __import__("torch")
        self.dev = device
        self.attached = None
        self._planned = list(self.mp.joint_names)

    @property
    def joint_names(self):
        return list(self.mp.joint_names)

    def world(self, scene: dict) -> None:
        from curobo._src.geom.types import SceneCfg
        if self.attached:
            self.detach()
        sc = SceneCfg.create(scene)
        self.mp.update_world(sc)
        self.ikb.update_world(sc)
        if getattr(self, "mpc", None) is not None:
            self.mpc.update_world(sc)
        if getattr(self, "ikr", None) is not None:
            self.ikr.update_world(sc)
        self._scene = scene  # start_hits() checks the start state against these cuboids

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

    def _pos(self, traj) -> np.ndarray | None:
        if traj is None:
            return None
        P = traj.position.reshape(-1, traj.position.shape[-1]).cpu().numpy()
        names = list(getattr(traj, "joint_names", None) or [])
        if names and P.shape[1] != len(names):
            names = []
        if names:  # interpolated plans may carry the locked joints too (fingers): keep the planned ones, in order
            P = P[:, [names.index(n) for n in self._planned]]
        else:
            P = P[:, :len(self._planned)]
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

    def pose(self, q, T_base, escape: bool = True) -> np.ndarray | None:
        """Collision-aware pose-to-pose. A start state inside the padded world (+ activation distance) makes cuRobo
        refuse every attempt ('Start or End state in collision'; L9v2-DIAG 1: the preroll pose touches shelf decor,
        the arm rests on an object it just placed): then a short straight TCP escape (3 / 6 / 10 cm up, back along
        the tool z, towards the base, down, sideways) to a collision-free state and the plan from there."""
        r = self.mp.plan_pose(self._goal(T_base), self._js(q), max_attempts=SEEDS[2])
        if r is not None and bool(r.success.any()):
            return self._pos(r.get_interpolated_plan())
        if os.environ.get("L9_IK_SEED") == "1" and not self.attached and not self.start_hits(q):
            # H4 (every robot, opt-in): plan_pose's own IK misses a goal that the batched world-collision IK (the
            # candidate filter) solves -- hand that IK solution to a joint-space plan instead of giving up
            ok, qi, _ = self.ik(np.asarray(T_base, float)[None], contact_links_off=False)
            if bool(ok[0]):
                Q = self.cspace(q, qi[0])
                if Q is not None:
                    self.n_ik_seed = getattr(self, "n_ik_seed", 0) + 1
                    return Q
        if not escape or not self.start_hits(q):
            return None
        E = self.escape(q)
        if E is None:
            return None
        r = self.mp.plan_pose(self._goal(T_base), self._js(E[-1]), max_attempts=SEEDS[2])
        if r is None or not bool(r.success.any()):
            return None
        self.n_escape = getattr(self, "n_escape", 0) + 1
        return np.concatenate([E, self._pos(r.get_interpolated_plan())[1:]])

    def start_hits(self, q, act: float = 0.012) -> list:
        """[(cuboid, penetration m)] of joint state q vs the current world: robot collision spheres + the 1 cm
        activation distance (+ 2 mm). Non-empty = cuRobo refuses q as a start state."""
        from .grasp9 import qmat
        st = self.mp.compute_kinematics(self._js(q))
        S = st.robot_spheres.reshape(-1, 4).cpu().numpy()
        S = S[S[:, 3] > 0]
        out = []
        for k, v in (getattr(self, "_scene", None) or {}).get("cuboid", {}).items():
            c, R, h = np.asarray(v["pose"][:3], float), qmat(v["pose"][3:]), np.asarray(v["dims"], float) / 2
            d = np.linalg.norm(np.maximum(np.abs((S[:, :3] - c) @ R) - h, 0.0), axis=1)
            pen = S[:, 3] + act - d
            if (pen > 0).any():
                out.append((k, float(pen.max())))
        return out

    def tool_T(self, q) -> np.ndarray:
        from .grasp9 import qmat
        st = self.mp.compute_kinematics(self._js(q))
        T = np.eye(4)
        T[:3, :3] = qmat(st.tool_poses.quaternion.reshape(-1, 4)[0].cpu().numpy())
        T[:3, 3] = st.tool_poses.position.reshape(-1, 3)[0].cpu().numpy()
        return T

    def escape(self, q, steps=(0.03, 0.06, 0.10)):
        """(N, dof) straight TCP move from q to the first collision-free state (start_hits == []), or None."""
        T0 = self.tool_T(q)
        dirs = [np.array([0, 0, 1.0]), T0[:3, 2], np.array([-1.0, 0, 0]), np.array([0, 0, -1.0]),
                np.array([0, 1.0, 0]), np.array([0, -1.0, 0])]
        for st in steps:
            for d in dirs:
                T1 = T0.copy()
                T1[:3, 3] = T0[:3, 3] + st * d / np.linalg.norm(d)
                Q = self.line(q, T0, T1, check=False)
                if Q is not None and not self.start_hits(Q[-1]):
                    return Q
        return None

    def ik(self, T_base_batch, contact_links_off: bool = True):
        """Batched reach test: -> (ok (N,), q (N, dof), margin (N,)) for world-collision-aware IK of N tool poses.
        The gripper contact links are not collision-checked (grasp9 already checked the gripper against the object
        and the support; plan_grasp does the same)."""
        from curobo.types import GoalToolPose, Pose
        from .grasp9 import mat_quat
        Ts = np.asarray(T_base_batch, float)
        n, dof = len(Ts), len(self.joint_names)
        out_ok, out_q = np.zeros(n, bool), np.zeros((n, dof))
        links = list(self.ikb.kinematics.config.kinematics_config.grasp_contact_link_names or [])             if contact_links_off else []
        for l in links:
            self.ikb.kinematics.config.kinematics_config.disable_link_spheres(l)
        try:
            for s0 in range(0, n, IK_BATCH):
                T = Ts[s0:s0 + IK_BATCH]
                m = len(T)
                pad = np.concatenate([T, np.repeat(T[-1:], IK_BATCH - m, 0)]) if m < IK_BATCH else T
                pos = self.torch.tensor(pad[:, :3, 3], dtype=self.torch.float32, device=self.dev)
                qq = self.torch.tensor(np.stack([mat_quat(t[:3, :3]) for t in pad]), dtype=self.torch.float32,
                                       device=self.dev)
                g = GoalToolPose.from_poses({self.ikb.tool_frames[0]: Pose(position=pos, quaternion=qq)},
                                            num_goalset=1)
                r = self.ikb.solve_pose(g)
                out_ok[s0:s0 + m] = r.success.reshape(IK_BATCH, -1)[:m, 0].cpu().numpy().astype(bool)
                out_q[s0:s0 + m] = r.solution.reshape(IK_BATCH, -1, dof)[:m, 0].cpu().numpy()
        finally:
            for l in links:
                self.ikb.kinematics.config.kinematics_config.enable_link_spheres(l)
        lo, hi = self._limits()
        margin = np.minimum(out_q - lo, hi - out_q).min(1) / np.maximum((hi - lo).min(), 1e-6)
        return out_ok, out_q, margin

    def line(self, q0, T0_base, T1_base, step_m: float = 0.01, check: bool = True):
        """Straight tool move (short place descents, retreats, lifts) when plan_pose refuses near contact: IK per
        waypoint (no world collision, self-collision on), each seeded with the previous solution. -> (N, dof) or
        None when a waypoint has no solution or a joint jumps > 0.15 rad between waypoints."""
        from curobo.inverse_kinematics import InverseKinematics, InverseKinematicsCfg
        from curobo.types import GoalToolPose, JointState, Pose
        from .grasp9 import mat_quat
        if getattr(self, "ikl", None) is None:
            self.ikl = InverseKinematics(InverseKinematicsCfg.create(
                robot=__import__("copy").deepcopy(self._robot_cfg), scene_model={"cuboid": {"_floor": {"dims": [0.1, 0.1, 0.01],
                                                                          "pose": [5.0, 5.0, -5.0, 1, 0, 0, 0]}}},
                num_seeds=1, self_collision_check=True, max_batch_size=1))  # 1 seed = the previous waypoint: no branch jumps
        T0, T1 = np.asarray(T0_base, float), np.asarray(T1_base, float)
        n = max(2, int(np.ceil(np.linalg.norm(T1[:3, 3] - T0[:3, 3]) / step_m)) + 1)
        q = np.asarray(q0, float)
        out = [q]
        q0q, q1q = mat_quat(T0[:3, :3]), mat_quat(T1[:3, :3])
        if float(np.dot(q0q, q1q)) < 0:
            q1q = -q1q
        for s in np.linspace(0, 1, n)[1:]:
            p = T0[:3, 3] + s * (T1[:3, 3] - T0[:3, 3])
            qq = (1 - s) * q0q + s * q1q
            qq = qq / np.linalg.norm(qq)
            pos = self.torch.tensor(p[None], dtype=self.torch.float32, device=self.dev)
            qt = self.torch.tensor(qq[None], dtype=self.torch.float32, device=self.dev)
            g = GoalToolPose.from_poses({self.ikl.tool_frames[0]: Pose(position=pos, quaternion=qt)}, num_goalset=1)
            cs = JointState.from_position(self.torch.tensor(q[None], dtype=self.torch.float32, device=self.dev),
                                          joint_names=self.joint_names)
            try:
                r = self.ikl.solve_pose(g, current_state=cs)
            except TypeError:
                r = self.ikl.solve_pose(g)
            if not bool(r.success.reshape(-1)[0]):
                return None
            qn = r.solution.reshape(-1, len(self.joint_names))[0].cpu().numpy()
            if np.abs(qn - q).max() > 0.15:
                return None
            out.append(qn)
            q = qn
        out = np.asarray(out)
        if check and getattr(self, "_scene", None):  # the IK has no world: reject a line through the loaded
            for qq in out[1::2]:  # world (pilot 10-02: straight lifts / retreats knocked neighbours 7-23 cm away)
                if self.start_hits(qq, act=0.0):
                    self.n_line_reject = getattr(self, "n_line_reject", 0) + 1
                    return None
        return out

    def reverse_approach(self, T_grasp_base, T_pre_base, step_m: float = 0.008, n_branches: int = 8):
        """Straight approach found from the GRASP end (L9v2-R1): IK branches of the grasp pose (world as loaded,
        self-collision on), best joint-limit margin first, each walked back to the pre-grasp with plan9.line.
        A forward walk from the transit's pre-grasp configuration often hits a joint limit on the way down (R1 Pro
        elbow joint4, replay 10-03), although another branch of the same grasp pose has a clean straight line.
        -> (N, dof) pre-grasp -> grasp joint path, or None."""
        T = np.asarray(T_grasp_base, float)
        P, order = self._branches(T, n_branches)
        self.last_reverse = {"n_ik": int(len(order))}
        for i in order:
            Q = self.line(P[i], T, T_pre_base, step_m)
            if Q is not None:
                self.n_reverse = getattr(self, "n_reverse", 0) + 1
                return Q[::-1].copy()
        return None

    def ready_ik(self, T_base, n_branches: int = 32):
        """L9 common executor (#8): the IK branch of a ready TCP pose with the largest joint-limit margin (world as
        loaded, self-collision on) -- the branch search of reverse_approach, for every robot.
        -> (q (dof,), margin rad) or None."""
        P, order = self._branches(np.asarray(T_base, float), n_branches)
        if not len(order):
            return None
        lo, hi = self._limits()
        q = P[order[0]]
        return q.copy(), float(np.minimum(q - lo, hi - q).min())

    def _branches(self, T, n_branches: int):
        """IK branches of one tool pose (ikr: 32 seeds, self-collision, world as loaded) -> (P (n, dof) planned
        joints, indices of the successful ones sorted by joint-limit margin, best first)."""
        from curobo.inverse_kinematics import InverseKinematics, InverseKinematicsCfg
        from curobo.types import GoalToolPose, Pose
        from .grasp9 import mat_quat
        if getattr(self, "ikr", None) is None:
            import copy
            self.ikr = InverseKinematics(InverseKinematicsCfg.create(
                robot=copy.deepcopy(self._robot_cfg), scene_model={"cuboid": {"_floor": {
                    "dims": [0.1, 0.1, 0.01], "pose": [5.0, 5.0, -5.0, 1, 0, 0, 0]}}},
                num_seeds=32, self_collision_check=True, max_batch_size=1, collision_cache={"cuboid": 64}))
            if getattr(self, "_scene", None):
                from curobo._src.geom.types import SceneCfg
                self.ikr.update_world(SceneCfg.create(self._scene))
        g = GoalToolPose.from_poses({self.ikr.tool_frames[0]: Pose(
            position=self.torch.tensor(T[:3, 3][None], dtype=self.torch.float32, device=self.dev),
            quaternion=self.torch.tensor(mat_quat(T[:3, :3])[None], dtype=self.torch.float32, device=self.dev))},
            num_goalset=1)
        r = self.ikr.solve_pose(g, return_seeds=n_branches)
        ok = r.success.reshape(-1).cpu().numpy().astype(bool)
        names = list(r.js_solution.joint_names)
        P = r.js_solution.position.reshape(len(ok), -1).cpu().numpy()
        P = P[:, [names.index(n) for n in self._planned]]
        lo, hi = self._limits()
        order = sorted(np.flatnonzero(ok), key=lambda i: -float(np.minimum(P[i] - lo, hi - P[i]).min()))
        return P, order

    def cspace(self, q, q_goal):
        """Collision-aware joint-space plan q -> q_goal (world as loaded). -> (N, dof) or None. Its own MotionPlanner:
        the pose planner's CUDA graphs are built for pose goals and cuRobo 0.8 cannot reset them for a joint goal
        ('CUDA graph reset is not available', offline test 10-03)."""
        from curobo.types import JointState
        if getattr(self, "mpc", None) is None:
            import copy
            from curobo.motion_planner import MotionPlanner, MotionPlannerCfg
            from curobo._src.geom.types import SceneCfg
            self.mpc = MotionPlanner(MotionPlannerCfg.create(
                robot=copy.deepcopy(self._robot_cfg), scene_model={"cuboid": {"_floor": {
                    "dims": [0.1, 0.1, 0.01], "pose": [5.0, 5.0, -5.0, 1, 0, 0, 0]}}},
                collision_cache={"cuboid": 64}, max_goalset=1, num_ik_seeds=SEEDS[0], num_trajopt_seeds=SEEDS[1],
                self_collision_check=True))
            if getattr(self, "_scene", None):
                self.mpc.update_world(SceneCfg.create(self._scene))
        g = JointState.from_position(self.torch.tensor(np.asarray(q_goal, np.float32)[None], device=self.dev),
                                     joint_names=self.joint_names)
        r = self.mpc.plan_cspace(g, self._js(q), max_attempts=SEEDS[2])
        if r is None or not bool(r.success.any()):
            return None
        return self._pos(r.get_interpolated_plan())
    def _limits(self):
        jl = self.mp.kinematics.get_joint_limits()
        pos = jl.position.cpu().numpy()
        return pos[0], pos[1]

    def _managers(self):
        """cuRobo 0.8.0: MotionPlanner.attachment_manager raises AttributeError (TrajOptSolver has no such attribute;
        the manager lives on each solver's core). Attach on every solver that plans (IK + trajopt)."""
        out = []
        for s in (self.mp.ik_solver, self.mp.trajopt_solver):
            m = getattr(getattr(s, "core", s), "attachment_manager", None)
            if m is not None and all(m is not o for o in out):
                out.append(m)
        return out

    ATTACH_SPHERES = (16, 12, 8)  # the yml's extra_collision_spheres {attached_object: 16}

    def attach(self, q, names: list) -> bool:
        """Attach the held objects on every solver. Automatic sphere fitting gave 26 spheres for a large object and
        raised ('only 16 sphere slots'), which killed the whole job (pilot 10-02): fit at most 16, then fewer; if no
        fit works, plan without the attachment (False) instead of crashing."""
        fit = os.environ.get("L9_ATTACH_FIT", "voxel")  # MORPHIT (Adam fit) took 6 s per attach = 28 % of a lane's
        # wall (10-02 A/B timing); the held objects are boxes: the voxel fit (bbox grid + SDF) covers them
        for n in self.ATTACH_SPHERES:
            try:
                for m in self._managers():
                    import inspect
                    ft = type(inspect.signature(m.attach_from_scene).parameters["sphere_fit_type"].default)
                    m.attach_from_scene(self._js(q), names, num_spheres=n, sphere_fit_type=ft(fit))
                self.attached = names
                return True
            except (ValueError, RuntimeError):
                for m in self._managers():  # undo the managers that did attach
                    try:
                        m.detach()
                    except Exception:
                        pass
                self.attached = None
        return False

    def detach(self) -> None:
        if self.attached:
            for m in self._managers():
                m.detach()
        self.attached = None
