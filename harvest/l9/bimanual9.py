"""L9 v2 bimanual (spec docs/superpowers/specs/2026-10-02-l9-bimanual.md; research
docs/research/bimanual_datagen_2026-10-02.md). Category A (handover) first, AI Worker first.

Design decision (see the spec note §1): do NOT write a second planner. `rt9.Runtime` is reused unmodified, one
instance per arm, against a dual `sim.scene.SimEnv` (dual=True, b2b8946). The handover zone is a robot-geometry
point (hypothesis, flagged), not a scene node, so it is NOT routed through task9's destination-spot sampler; task9 /
scene9 are only used (unmodified) to draw a valid scene and a start pose for the handed-over object.

Pure layer (this file's top half): no torch / curobo / isaaclab import, unit-tested on the laptop (tests/l9).
Impure layer (bottom half, `HandoverRuntime` / `run_smoke`): pod only, lazy imports."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------------------------- pure: task defs
# category A (research doc table rows 1-12): 6 object groups x 2 directions. `cats` filters the AI Worker object
# catalog the same way task9v2's `T`/`hollow()` dicts do; `giver`/`receiver` are the arm roles.
BIM_A_OBJECTS = {
    "block": ("block",), "can": ("can",), "cup": ("cup", "mug"), "bottle": ("bottle",),
    "bowl": ("bowl",), "box": ("box",),
}
BIM_A_DEFS: dict = {}
for _name, _cats in BIM_A_OBJECTS.items():
    BIM_A_DEFS[f"handover_{_name}_lr"] = {"cats": _cats, "giver": "left", "receiver": "right", "family": "bim_a"}
    BIM_A_DEFS[f"handover_{_name}_rl"] = {"cats": _cats, "giver": "right", "receiver": "left", "family": "bim_a"}
assert len(BIM_A_DEFS) == 12, len(BIM_A_DEFS)

GRIPPERS = ("grasp", "release", "hold")  # research doc §(d): "hold" is new (role=support, contact maintained)
ROLES = ("lead", "support", "independent")

# ---------------------------------------------------------------------------------------------- pure: zone geometry
# [가설] per the research doc §(d).3: a fixed handover-zone point in the robot's own frame (not a scene node), so the
# receiver's label never depends on a dynamic estimate of the giver's future position. AI Worker: WS_X/WS_Y (sim.scene)
# is the measured top-down reach band of ONE arm; the zone sits at the shared midline (y=0, both arms' workspaces are
# mirror images about y, harvest.l9.arm) at the near edge of that band and above the table (an in-air handover, so
# "no floor / table contact" is a meaningful success check, not automatically true).
ZONE_X = 0.38  # m, world frame (within [0.36, 0.48], sim.scene.WS_X)
ZONE_Z_ABOVE_TABLE = 0.20  # m above the table top
# R1 Pro / G1: no measured zone yet (category A ships AI Worker first, owner's plan step 3); same formula, their own
# reach bands (robot9.V2[profile]), marked untested.
ZONE_X_V2 = {"r1pro": 0.45, "g1": 0.30}
ZONE_Z_ABOVE_TABLE_V2 = {"r1pro": 0.22, "g1": 0.18}


def handover_zone_xyz(profile: str, table_z: float) -> np.ndarray:
    if profile in ZONE_X_V2:
        return np.array([ZONE_X_V2[profile], 0.0, table_z + ZONE_Z_ABOVE_TABLE_V2[profile]], float)
    return np.array([ZONE_X, 0.0, table_z + ZONE_Z_ABOVE_TABLE], float)


def final_spot_xyz(zone: np.ndarray, receiver_arm: str, reach: float = 0.14) -> np.ndarray:
    """Where the receiver finally sets the object down: `reach` further into the receiver's own half of the table
    (right arm = -y, left arm = +y; harvest.l9.arm.side), same height band as the zone minus a few cm (object comes
    to rest, not held mid-air)."""
    from .arm import side
    y = zone[1] - side(receiver_arm) * reach  # side(+1)=right (y<0): final spot moves further -y = deeper right
    return np.array([zone[0], y, zone[2] - 0.08], float)


# ---------------------------------------------------------------------------------------------- pure: command schema
def bim_command(arm: str, role: str, position_m, gripper: str, quat_wxyz=None, sync: bool = False, point_px=None,
                 height=None, approach=None, wrist_bin=None) -> dict:
    """The research doc §(d) schema: the existing v2plan per-arm command (mode/position_m/gripper[/quat_wxyz]) plus
    `arm`, `role` (lead|support|independent) and `sync`; `gripper` additionally allows "hold" (role=support: keep the
    current contact, no new grasp attempt)."""
    if role not in ROLES:
        raise ValueError(f"role {role!r}: one of {ROLES}")
    if gripper not in GRIPPERS and gripper != "keep":
        raise ValueError(f"gripper {gripper!r}: one of {GRIPPERS + ('keep',)}")
    cmd = {"mode": "eef", "arm": arm, "role": role, "sync": bool(sync),
           "position_m": [round(float(v), 4) for v in position_m], "gripper": gripper}
    if quat_wxyz is not None:
        cmd["quat_wxyz"] = [round(float(v), 5) for v in quat_wxyz]
    if point_px is not None:
        cmd["point_px"] = list(point_px)
    if height is not None:
        cmd["height"] = height
    if approach is not None:
        cmd["approach"] = approach
    if wrist_bin is not None:
        cmd["wrist_bin"] = int(wrist_bin)
    return cmd


def pair_commands(a: dict, b: dict) -> dict:
    """One call's "commands" list (views9.ARM_NOTE format: one per arm)."""
    return {"commands": [a, b]}


# ---------------------------------------------------------------------------------------------- pure: phase FSM
PHASES = ("giver_pick", "giver_carry", "giver_hold", "receiver_pick", "giver_release", "receiver_carry", "done")


def handover_phase(phase: str, giver_holding: bool, giver_at_zone: bool, receiver_contacted: bool,
                    giver_opened: bool, receiver_at_final: bool) -> str:
    """Next phase (pure state machine, research doc §(c)/(d)): the giver carries to the zone and HOLDS (closed,
    stationary) until the receiver's grip reads CONTACT (both closed at once = the required overlap window); only
    then does the giver open, and only then does the receiver carry on. One phase advances per call; callers re-call
    with the same phase until a condition flips (no-op safe)."""
    if phase not in PHASES:
        raise ValueError(f"phase {phase!r}: one of {PHASES}")
    if phase == "giver_pick":
        return "giver_carry" if giver_holding else phase
    if phase == "giver_carry":
        return "giver_hold" if giver_at_zone else phase
    if phase == "giver_hold":
        return "receiver_pick"  # receiver starts approaching while the giver holds (doc §(d).3: two-stage choreo)
    if phase == "receiver_pick":
        return "giver_release" if receiver_contacted else phase
    if phase == "giver_release":
        return "receiver_carry" if giver_opened else phase
    if phase == "receiver_carry":
        return "done" if receiver_at_final else phase
    return "done"


# ---------------------------------------------------------------------------------------------- pure: success gate
def success_a(final_xy, target_xy, tol: float = 0.03, floor_touched: bool = False, overlap_ticks: int = 0) -> dict:
    """Research doc §(c) category-A gate (xy part only; pose-angle <= 15 deg is checked in sim, not here)."""
    err = float(math.hypot(final_xy[0] - target_xy[0], final_xy[1] - target_xy[1]))
    ok = (err <= tol) and (not floor_touched) and (overlap_ticks >= 1)
    return {"ok": bool(ok), "place_err_m": round(err, 4), "floor_touched": bool(floor_touched),
            "overlap_ticks": int(overlap_ticks)}


# ---------------------------------------------------------------------------------------------- impure: runtime
# Deliberately NOT built on rt9.TrajExec / rt9.Runtime.motion_for: both are tightly coupled to the single-arm step
# name machinery (Runtime.plan / v2plan.plan), which needs a task9-style "place" object in the scene. The handover
# zone is not a scene object (spec note §1), so this orchestrator drives joint trajectories itself -- a self
# contained "trajectory player" per arm -- and reuses only the self-contained pieces of Runtime: `choose()` (grasp
# candidate selection), `_approach_plan()` (pre-grasp transit + straight approach + lift, already its own function),
# `planner.pose()/line()` + `_resample()` for the carry / zone / final moves, and `refresh_world()` for obstacles.
GRAVITY_BOX_HALF = (0.07, 0.07, 0.09)  # m, coarse stand-in for the other arm's hand + forearm end (spec note R1)
SETTLE_TICKS = 30  # ~0.6 s at 20 Hz / dt: gripper close/open settle wait


@dataclass
class _ArmSlot:
    arm: str
    rt: object  # rt9.Runtime
    traj: object = None  # np.ndarray (T, 7) or None (= hold the current q_target)
    traj_i: int = 0
    width: float = 0.0
    held_obj: str | None = None


class HandoverRuntime:
    """Category-A orchestrator: two `rt9.Runtime` (one per arm) against one dual SimEnv, driven by `handover_phase`.
    Not wired into `collect9.run_episode` / `teach_l8d.collect.collect_episode` yet (spec note §3): `run_episode`
    below is a standalone loop for the pilot's smoke episodes, not the production label/build pipeline."""

    def __init__(self, world, profile: str, giver_arm: str, receiver_arm: str, device: str = "cuda:0",
                 allow_untested: bool = False):
        from . import rt9 as RT
        env = world.env
        if not getattr(env, "dual", False):
            raise ValueError("HandoverRuntime needs world.env built with dual=True (world9.make_world9(dual=True))")
        if env.primary not in (giver_arm, receiver_arm):
            raise ValueError(f"env.primary={env.primary!r} must be the giver or the receiver arm")
        self.world, self.profile = world, profile
        env.use_arm(giver_arm)
        giver_rt = RT.Runtime(world, profile, giver_arm, device=device, allow_untested=allow_untested)
        env.use_arm(receiver_arm)
        receiver_rt = RT.Runtime(world, profile, receiver_arm, device=device, allow_untested=allow_untested)
        self.giver = _ArmSlot(giver_arm, giver_rt, width=float(giver_rt.w.w_open))
        self.receiver = _ArmSlot(receiver_arm, receiver_rt, width=float(receiver_rt.w.w_open))
        self.phase = "giver_pick"
        self.overlap_ticks = 0
        self.events = []
        env.use_arm(env.primary)
        self._freeze(self.giver)
        self._freeze(self.receiver)

    def slot_of(self, arm: str) -> "_ArmSlot":
        return self.giver if arm == self.giver.arm else self.receiver

    def other_of(self, slot: "_ArmSlot") -> "_ArmSlot":
        return self.receiver if slot is self.giver else self.giver

    # -------------------------------------------------------------- per-tick stepping
    def _freeze(self, slot: "_ArmSlot") -> None:
        """This arm's target becomes its current measured joints (held stationary)."""
        env = self.world.env
        env.use_arm(slot.arm)
        slot.rt.q_target = env.arm_q().astype(np.float32)
        slot.traj = None

    def _gravity_target(self, slot: "_ArmSlot") -> np.ndarray:
        env = self.world.env
        env.use_arm(slot.arm)  # context-dependent gravity query; the index arrays below are not (rt's own snapshot)
        g = self.world.pl._gravity_offset()[0].cpu().numpy()
        rt = slot.rt
        q = env.robot.data.joint_pos[0, rt.arm_ids].cpu().numpy().copy()
        if rt.q_target is not None:
            for j, sid in enumerate(rt.sim_ids):
                q[rt.arm_ids.index(sid)] = rt.q_target[j]
        return (q + g).astype(np.float32)

    def tick(self) -> None:
        """One physics step. Each slot with a live `traj` advances one waypoint into `rt.q_target` first; a slot
        with `traj=None` keeps stepping its last-frozen `q_target` (held)."""
        for slot in (self.giver, self.receiver):
            if slot.traj is not None:
                if slot.traj_i < len(slot.traj):
                    slot.rt.q_target = slot.traj[slot.traj_i]
                    slot.traj_i += 1
                if slot.traj_i >= len(slot.traj):
                    slot.traj = None  # arrived: hold this last waypoint from now on
        env = self.world.env
        primary = self.slot_of(env.primary)
        other = self.other_of(primary)
        q_other = self._gravity_target(other)
        env.use_arm(other.arm)
        env.set_arm2_target(q_other, other.width)
        q_prim = self._gravity_target(primary)
        env.use_arm(primary.arm)
        env.step(np.concatenate([q_prim, [primary.width]]).astype(np.float32))
        self._update_overlap()

    def run_ticks(self, n: int) -> None:
        for _ in range(n):
            self.tick()

    def _update_overlap(self) -> None:
        env = self.world.env
        env.use_arm(self.giver.arm)
        gw = env.gripper_width()
        env.use_arm(self.receiver.arm)
        rw = env.gripper_width()
        env.use_arm(env.primary)
        if self.phase == "receiver_pick" and gw < 0.01 and rw < 0.01:
            self.overlap_ticks += 1

    # -------------------------------------------------------------- motion primitives (self-contained Runtime bits)
    def other_arm_boxes(self, slot: "_ArmSlot") -> dict:
        """A coarse box around the OTHER arm's current TCP, to pass as `extra_boxes=` into `slot.rt.choose()` /
        `refresh_world()` (rt9.Runtime, extended for this: both now accept `extra_boxes` and merge it in after their
        own obstacle scan, so it survives their internal `refresh_world` calls instead of being overwritten by the
        next one -- spec note R1b). Spec note R1: a box, not the other arm's real links -- no true dual-arm
        self-collision check."""
        env = self.world.env
        other = self.other_of(slot)
        env.use_arm(other.arm)
        p_other, _ = self.world.pl.tcp_pose()
        env.use_arm(slot.arm)
        return {"other_arm": (np.asarray(p_other, float), [2 * h for h in GRAVITY_BOX_HALF],
                              np.array([1.0, 0.0, 0.0, 0.0]))}

    def _grasp(self, slot: "_ArmSlot", obj_key: str) -> dict:
        """Choose + transit + straight approach + lift (rt9.Runtime._approach_plan, self-contained), then close.
        -> {"ok", "status"}."""
        env = self.world.env
        env.use_arm(slot.arm)
        rt = slot.rt
        gc = rt.choose(obj_key, {"tgt": obj_key}, extra_boxes=self.other_arm_boxes(slot))
        if gc is None:
            return {"ok": False, "status": "no valid grasp"}
        r = rt._approach_plan(rt.plan_start(), gc, obj_key, extra_boxes=self.other_arm_boxes(slot))
        if not r["ok"]:
            return {"ok": False, "status": r["status"]}
        slot.traj, slot.traj_i = rt._resample(r["approach"]), 0
        self.run_ticks(len(slot.traj) + 5)
        slot.traj, slot.traj_i = rt._resample(r["grasp"]), 0
        self.run_ticks(len(slot.traj) + 5)
        slot.width = 0.0  # close
        self.run_ticks(SETTLE_TICKS)
        env.use_arm(slot.arm)
        gap = float(env.gripper_width())
        from . import rt9 as RT
        if RT.classify_close(gap, gc.w) == "EMPTY":
            return {"ok": False, "status": f"EMPTY close (gap {gap * 100:.1f} cm)"}
        slot.traj, slot.traj_i = rt._resample(r["lift"]), 0
        self.run_ticks(len(slot.traj) + 5)
        slot.held_obj = obj_key
        return {"ok": True, "status": "ok", "gc": gc}

    def _move_to(self, slot: "_ArmSlot", target_xyz, quat_wxyz=None) -> dict:
        """A straight / planned cuRobo move to a world TCP pose, holding `slot.held_obj` attached if set."""
        from . import rt9 as RT
        env = self.world.env
        env.use_arm(slot.arm)
        rt = slot.rt
        rt.refresh_world(holding=slot.held_obj or None, extra_boxes=self.other_arm_boxes(slot))
        q = env.arm_q() if rt.q_target is None else np.asarray(rt.q_target, float)
        quat = np.asarray(quat_wxyz, float) if quat_wxyz is not None else np.asarray(rt.tcp_T()[:3, :3], float)
        T = RT.T_of(target_xyz, RT.G.mat_quat(quat) if quat.shape == (3, 3) else quat)
        Tb = rt.to_base(T)
        Q = rt.planner.line(q, rt.to_base(rt.tcp_T()), Tb) or rt.planner.pose(q, Tb)
        if Q is None:
            return {"ok": False, "status": "no collision-free path"}
        slot.traj, slot.traj_i = rt._resample(np.asarray(Q, float)), 0
        self.run_ticks(len(slot.traj) + 5)
        return {"ok": True, "status": "ok"}

    def _gripper(self, slot: "_ArmSlot", action: str) -> None:
        slot.width = 0.0 if action == "close" else float(slot.rt.w.w_open)
        self.run_ticks(SETTLE_TICKS)
        if action == "open":
            slot.held_obj = None

    # -------------------------------------------------------------- episode
    def run_episode(self, obj_key: str, table_z: float, final_xy=None, max_phase_ticks: int = 400) -> dict:
        """Category-A smoke episode: giver picks `obj_key`, carries to the handover zone and holds; the receiver
        approaches and closes on it (while the giver holds), the giver opens once the receiver has it, the receiver
        carries to `final_xy` (default: `final_spot_xyz`). Not the production collection loop (spec note §3): no
        labels.jsonl / build9 row here, see tools/l9/bim_smoke.py for that wiring."""
        zone = handover_zone_xyz(self.profile, table_z)
        if final_xy is None:
            final_xy = final_spot_xyz(zone, self.receiver.arm)[:2]
        log = []
        r = self._grasp(self.giver, obj_key)
        log.append({"phase": "giver_pick", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        r = self._move_to(self.giver, zone)
        log.append({"phase": "giver_carry", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        self.phase = "receiver_pick"
        self.overlap_ticks = 0
        r = self._grasp(self.receiver, obj_key)
        log.append({"phase": "receiver_pick", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        self._gripper(self.giver, "open")
        log.append({"phase": "giver_release", "ok": True})
        r = self._move_to(self.giver, np.asarray(zone, float) + np.array([-0.08, 0.0, 0.05]))  # retreat, clear of
        log.append({"phase": "giver_retreat", **r})  # the receiver's incoming carry path
        r = self._move_to(self.receiver, np.array([final_xy[0], final_xy[1], zone[2]]))
        log.append({"phase": "receiver_carry", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        self._gripper(self.receiver, "open")
        env = self.world.env
        env.use_arm(self.receiver.arm)
        final_obj_xy = np.asarray(env.object_pose(obj_key)[0], float)[:2]
        gate = success_a(final_obj_xy, final_xy, overlap_ticks=self.overlap_ticks)
        return {"ok": gate["ok"], "gate": gate, "log": log}


def install_handover(world, profile: str, giver_arm: str, receiver_arm: str, device: str = "cuda:0",
                      allow_untested: bool = False) -> HandoverRuntime:
    return HandoverRuntime(world, profile, giver_arm, receiver_arm, device=device, allow_untested=allow_untested)
