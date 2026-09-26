"""`aiworker` Inspect Robots embodiment (P1, canon §42, D23 §3): our v2 scene (sim/scene.py make_env, CPU PhysX,
variant standard / random / dr) as one FFW-SG2 right arm.

- action: joint_pos 8-D = 7 right-arm joint targets (rad, soft joint limits) + gripper pad-gap target (m, 0..107 mm),
  finite bounds, dim_labels, max_step, gripper "continuous"; the embodiment clips every action to the bounds.
- state: exactly one StateSpec field joint_pos (8,) (measured arm joints + measured pad gap) = the proprioceptive
  reference agent / capx require.
- control: sim.dt 0.01, decimation 1 -> control_hz 100; cameras (head ZED Mini left 672x376, right wrist D405 424x240,
  copied challenge-env config) render every `render_interval` physics steps and are put into Observation.images only
  on those steps (new frames); depth / intrinsics are callables in extra (never arrays: TrialRecord keeps extras).
- extra: sim_time, m1 (sim oracle M1 observation, table frame -- the E0 oracle condition; our policy reads it, the
  harness baselines never see it, canon §42 정보 동등), kin (sim kinematics service: TCP pose + DLS IK with the
  static gravity offset of the PD arm, the planner's; a real robot would use its URDF IK -- kin.tcp_pose() is the
  PAD-CENTRE TCP the planner/IK actually targets, env.ee_pose() + env.tcp_offset, NOT env.finger_mid()/R2's own "tcp"
  label -- the two differ by ~7.8 mm, docs/stage3/results/r5_closed_loop.md), table_z, rtf, cams (callable ->
  camera_models(): live camera pose x mount per camera, evaluated only when an Astra request goes out; Astra-VLA
  coupling Task 8, reuses harvest.astra_motion.world_isaac.camera_pose, P40).
- success: planner.success_from_history (on(o3,o5) & not holding(o3) & upright(o3) held 1 s) -> terminated "success";
  mug below the floor -> terminated "off_table". self_paced only when asked (wall clock); the sim uses simlat.
Seeds: DEV (0-29); CAL/TEST only behind HARVEST_ALLOW_SPLIT (check_layout_seed, R6 guard).
"""
from __future__ import annotations

import hashlib
import pathlib
import time

import numpy as np

GRIP_MAX_W = 0.107
DIM_LABELS = tuple(f"arm_r_joint{i}" for i in range(1, 8)) + ("gripper_r_width",)
MAX_STEP = (0.05,) * 7 + (0.02,)  # per 10 ms tick; generous (the planner-grade IK clamps at 0.02 rad)
STATE_UNIT = "rad (7 arm joints) + m (gripper pad gap)"
DEV_SEEDS = range(0, 30)
DOCS = ("AI Worker FFW-SG2, fixed base, RIGHT arm only (left arm, head, lift held at defaults). Action = absolute "
        "joint targets arm_r_joint1..7 (rad, positive = joint axis per the ROBOTIS URDF) + gripper_r_width = target "
        "pad gap in metres (0 = closed, 0.107 = fully open). World frame: +x forward, +y robot left, +z up; table top "
        "at z = 0.85 m in front of the robot. 100 Hz control; head camera 672x376, right wrist camera 424x240.")


def check_layout_seed(ls: int, env=None) -> int:
    """DEV 0-29 always; CAL / TEST / TEST-P5 layout seeds only when HARVEST_ALLOW_SPLIT names that split (set by the
    main session at the pre-registered time, harvest/eval/splits.py); everything else is refused."""
    import os

    from ..eval.splits import ENV, PROTECTED, split_of
    env = os.environ if env is None else env
    s = int(ls)
    if s in DEV_SEEDS:
        return s
    sp = split_of(s)
    if sp in PROTECTED and env.get(ENV) == sp:
        return s
    raise ValueError(f"layout seed {s}: DEV 0-29 only (CAL/TEST need {ENV}=<split>, main session only)")


def clip_action(a, low, high) -> np.ndarray:
    a = np.asarray(a, dtype=float).reshape(-1)
    if a.shape != (8,):
        raise ValueError(f"action shape {a.shape}, expected (8,)")
    return np.clip(a, low, high)


def build_info(low, high, cameras=(("cam_head", 376, 672), ("cam_wrist_right", 240, 424)), self_paced=False,
               environment_id=None, environment_revision=None):
    from inspect_robots import ActionSemantics, Box, EmbodimentInfo, ObservationSpace, StateField, StateSpec
    from inspect_robots.spaces import CameraSpec
    caps = {"seedable", "resettable", "privileged_success", "renderable"} | ({"self_paced"} if self_paced else set())
    return EmbodimentInfo(
        name="aiworker",
        action_space=Box(shape=(8,), low=np.asarray(low, float), high=np.asarray(high, float),
                         semantics=ActionSemantics(control_mode="joint_pos", gripper="continuous",
                                                   dim_labels=DIM_LABELS, max_step=MAX_STEP)),
        observation_space=ObservationSpace(cameras=tuple(CameraSpec(n, h, w) for n, h, w in cameras),
                                           state=StateSpec(fields=(StateField("joint_pos", (8,), STATE_UNIT),))),
        control_hz=100.0, is_simulated=True, capabilities=frozenset(caps), docs=DOCS,
        environment_id=environment_id, environment_revision=environment_revision)


def scene_revision() -> str:
    here = pathlib.Path(__file__).resolve().parents[1] / "sim"
    h = hashlib.sha256()
    for f in ("scene.py", "randomize.py", "planner.py"):
        h.update((here / f).read_bytes())
    return "harvest-sim-" + h.hexdigest()[:12]


def _camera_model_dict(R, t, K, W: int, H: int) -> dict:
    """Pure assembly of one overlay.CamModel-shaped dict (no Isaac): camera_models() is this plus the live Isaac
    pose lookup, factored out so it is testable without a running sim (tests/runtime/test_camera_models.py)."""
    return {"K": np.asarray(K, float).tolist(), "R": np.asarray(R, float).tolist(),
           "t": np.asarray(t, float).tolist(), "W": int(W), "H": int(H)}


class Kinematics:
    """Sim kinematics service: the planner's TCP pose and DLS IK (with the PD gravity-sag offset)."""

    def __init__(self, env):
        from ..sim.planner import OraclePlanner
        self.pl = OraclePlanner(env)

    def tcp_pose(self):
        return self.pl.tcp_pose()

    def ik(self, pos_w, quat_w, max_dq):
        return self.pl._ik(np.asarray(pos_w, float), np.asarray(quat_w, float), max_dq)


class AIWorkerEmbodiment:
    def __init__(self, variant: str = "standard", cameras=("cam_head", "cam_wrist_right"), render_interval: int = 3,
                 self_paced: bool = False, depth: bool = True):
        from ..sim.scene import camera_table, make_env
        self.variant, self.cameras, self.self_paced = variant, tuple(cameras), self_paced
        self.env = make_env(0, cameras=self.cameras, depth=depth, sim_device="cpu", variant=variant, decimation=1,
                            render_interval=render_interval)
        e = self.env
        lim = e.robot.data.soft_joint_pos_limits[0, e.arm_ids].cpu().numpy()
        self.low = np.r_[lim[:, 0], 0.0]
        self.high = np.r_[lim[:, 1], GRIP_MAX_W]
        rows = {r["name"]: r for r in camera_table()}
        cams = tuple((n, rows[n]["height"], rows[n]["width"]) for n in self.cameras)
        self.K = {n: np.array([[rows[n]["fx"], 0, rows[n]["width"] / 2], [0, rows[n]["fx"], rows[n]["height"] / 2],
                               [0, 0, 1.0]]) for n in self.cameras}
        self.info = build_info(self.low, self.high, cams, self_paced,
                               environment_id="isaac-sim-5.1.0-rc.19/isaaclab-2.3.0 (cyclo-lab-2.0.0 rootfs), CPU PhysX",
                               environment_revision=scene_revision())
        self._last = None

    # ------------------------------------------------------------------ protocol
    def reset(self, scene, *, seed=None):
        from ..predicates import PredicateState
        from ..sim.perturb import perturb
        from ..sim.snapshot import capture
        md = dict(scene.metadata or {})
        ls = int(md.get("layout_seed", scene.init_seed))
        check_layout_seed(ls)
        if md.get("variant", "standard") != self.variant:
            raise ValueError(f"scene variant {md.get('variant')} != embodiment variant {self.variant} (one per process)")
        kind = md.get("kind", "P0")
        if kind != "P0":
            raise NotImplementedError("R5: DEV P0 only (P1/P2 need the planner-phase hooks of perturb.apply_pending)")
        e = self.env
        if e.seed != ls:
            e.set_seed(ls)
        e.reset()
        perturb(e, kind, ls)
        self.kin = Kinematics(e)
        self.ps, self.succ, self.n = PredicateState(), [], 0
        self.t_wall0, self._last = time.monotonic(), None
        imgs = capture(e, self.cameras)
        return self._obs(imgs, self._m1())

    def step(self, action):
        from inspect_robots import StepResult

        from ..sim.planner import _success_now, success_from_history
        if self.self_paced:  # wall clock (real robot / RTF >= 1 only)
            now = time.monotonic()
            if self._last is not None and self._last + 0.01 > now:
                time.sleep(self._last + 0.01 - now)
            self._last = time.monotonic()
        e = self.env
        a = clip_action(action.data, self.low, self.high)
        e.step(a)
        self.n += 1
        new = e.env._sim_step_counter % e.env.cfg.sim.render_interval == 0
        imgs = {n: e.camera_rgb(n) for n in self.cameras} if new else {}
        m1 = self._m1()
        from ..sim.snapshot import obs_from_json
        pred = self.ps.update(*obs_from_json(m1["raw"]))
        t = e.sim_time
        self.succ = self.succ + [(t, pred)] if _success_now(pred) else []
        ok = success_from_history(self.succ)
        off = m1["raw"]["objs"]["o3"]["pos"][2] < -0.05
        wall = time.monotonic() - self.t_wall0
        info = {"success": ok, "sim_time": t, "rtf": t / max(wall, 1e-9), "clipped": bool(np.any(a != action.data)),
                **{k: pred.get(k) for k in ("holding(o3)", "on(o3,o5)", "upright(o3)")}}
        return StepResult(observation=self._obs(imgs, m1), terminated=bool(ok or off),
                          termination_reason="success" if ok else ("off_table" if off else None), info=info)

    def close(self):
        self.env.close()

    # ------------------------------------------------------------------ helpers
    def _m1(self):
        from ..sim.oracle_state import oracle_objects
        from ..sim.snapshot import obs_to_json
        return {"raw": obs_to_json(*oracle_objects(self.env)), "present": list(self.env.present)}

    def camera_models(self) -> dict:
        """{cam: {K, R, t, W, H}} now: live parent-link pose x mount (the E-Astra-motion probe's camera_pose; Isaac
        camera pos_w / quat_w do not follow physics, P40). R is world_from_optical; it equals base_from_optical here
        only because this embodiment's robot is fixed-base at the world origin with identity rotation (aiworker
        docstring) -- on a mobile or re-based robot the two would differ and R would need a base-pose correction.
        Evaluated only when an Astra request goes out (couple/overlay.py consumes this dict as obs["cams"], Task 8).

        Frame check (Task 8 Step 6, no conversion applied): camera_pose (harvest/astra_motion/world_isaac.py) reads
        (R, t) straight from robot.data.body_pos_w / body_quat_w -- Isaac's world/PhysX frame. kin.tcp_pose() ->
        OraclePlanner.tcp_pose() -> self.env.ee_pose() (harvest/sim/scene.py Env.ee_pose) returns
        d.body_pos_w[0, self.ee_idx] directly -- the SAME body_pos_w world frame. The robot is fixed-base (aiworker
        docstring), so this is not seed/reset dependent. Since overlay.project() consumes cam.R/cam.t and the tip in
        one common frame, and both camera_pose and kin.tcp_pose already report in body_pos_w, camera_models() passes
        R/t straight through with no extra transform."""
        from ..astra_motion.world_isaac import camera_pose
        from ..sim.scene import camera_table, load_realcam
        rc, rows = load_realcam(), {r["name"]: r for r in camera_table()}
        out = {}
        for n in self.cameras:
            R, t = camera_pose(self.env.robot, rc, n)
            out[n] = _camera_model_dict(R, t, self.K[n], rows[n]["width"], rows[n]["height"])
        return out

    def _obs(self, imgs, m1):
        from inspect_robots import Observation
        e = self.env
        t = e.sim_time
        q = np.r_[e.arm_q(), e.gripper_width()]
        extra = {"sim_time": t, "m1": m1, "kin": self.kin, "table_z": e.table_top_z,
                 "depth": {n: (lambda n=n: e.camera_depth(n)) for n in self.cameras},
                 "intrinsics": {n: (lambda n=n: self.K[n].copy()) for n in self.cameras},
                 "cams": self.camera_models,
                 "rtf": t / max(time.monotonic() - self.t_wall0, 1e-9)}
        return Observation(images=imgs, state={"joint_pos": q}, image_times={n: t for n in imgs}, state_time=t,
                           extra=extra)
