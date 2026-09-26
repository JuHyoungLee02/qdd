"""Executor = scripted skill S + residual-R hook (canon §34-§35, §51; M6 §4.1), 100 Hz, pure (IK injected).

The skill computes its own sub-goal from the perceived state every tick (the labels_v2 sub-phase geometry: the same
functions that define the decision answers, applied to the current measurement) and turns the COMMITTED typed
decisions of the current decision step into a bounded motion (canon §35 "구간 제한": the chosen direction d-hat and
cm-bin are kept by a code projection):
  - dir_xy / dir_z: each axis may move only with the sign the decision chose; an axis the decision calls "none" may
    only close a gap inside the 1 cm dead band (labels_v2 DEADBAND_M);
  - mag_coarse: the TCP travel inside one decision step is capped at the bin's upper edge (xlarge: speed limit only);
  - target: the motion must be about the object the decision names (mug o3 for approach/grasp/lift, tray o5 for
    carry/place), otherwise no motion;
  - phase: hold -> no motion; next -> the irreversible gripper events (close / open) and the S1 -> S2 stage switch,
    each also gated by a code safety predicate (M6 dp.release rule "M4 확정 + 코드 안전 술어");
  - missing / NONE_ESCALATE decision -> keep the last command (no motion = hold + slow down, never a stop).
Because the goal is recomputed from fresh measurements, stale decisions can freeze an axis but never drive it past
the goal. The (b) check of M4 compares the measured TCP with the commanded reference at the end of each step.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..labels_v2 import DEADBAND_M, MAG_EDGES_M, _delta, _motion, gripper_state
from ..sim.planner import CLOSE_WAIT_S, GRASP_BELOW_TOP_M, OPEN_WAIT_S, TOP_DOWN_YAW, W_MAX, _slerp_step

GRIP_MAX_W = 0.107  # scene.GRIP_MAX_W (107.0 mm); scene imports Isaac lazily but keep this module import-light
MUG_R, SQUEEZE = 0.032, 0.014  # scene OBJ_GEOM o3 radius, planner GRIP_SQUEEZE_M
V = {"approach": 0.20, "descend": 0.06, "close": 0.0, "lift": 0.08, "carry": 0.20, "place_descend": 0.06,
     "open": 0.0, "retreat": 0.20, "done": 0.0}  # planner V_FAST / V_SLOW / V_LIFT per phase
MAG_CAP = dict(zip(("tiny", "small", "medium", "large"), MAG_EDGES_M))  # xlarge: no cap beyond the speed
_XY_SIGN = {"plus_x": (1, 0), "plus_x_plus_y": (1, 1), "plus_y": (0, 1), "minus_x_plus_y": (-1, 1),
            "minus_x": (-1, 0), "minus_x_minus_y": (-1, -1), "minus_y": (0, -1), "plus_x_minus_y": (1, -1),
            "none_xy": (0, 0)}
_Z_SIGN = {"up": 1, "down": -1, "none_z": 0}
MOTION_OBJ = {"approach": "o3", "grasp": "o3", "lift": "o3", "carry": "o5", "place": "o5"}
OK_M, LAG_M = 0.015, 0.04  # (b) residual thresholds, TCP command vs measured at the step end [가정]
WS_X, WS_Y, WS_Z = (0.25, 0.65), (-0.50, 0.10), (0.03, 0.35)  # safety box (world x/y, z above the table)
GRASP_FLOOR_M = 0.003  # TCP grasp floor below the planner's grasp height
HOLD_DEBOUNCE_S = 0.15  # planner.HOLD_DEBOUNCE = 3 control steps at 20 Hz (datagen: 5 at 30 Hz)


def constraint(dec: dict):
    """(signs (sx, sy, sz), cap_m) from the step's decisions, or None when motion is not allowed."""
    xy, z = _XY_SIGN.get(dec.get("dir_xy")), _Z_SIGN.get(dec.get("dir_z"))
    if xy is None or z is None or dec.get("phase") in (None, "hold", "NONE_ESCALATE"):
        return None
    m = dec.get("mag_coarse")
    if m is None or m == "NONE_ESCALATE":
        return None
    return (xy[0], xy[1], z), MAG_CAP.get(m, math.inf)


def project(err, signs, deadband: float = DEADBAND_M) -> np.ndarray:
    """Keep each axis of err only where it agrees with the decided sign; a 'none' axis only inside the dead band."""
    out = np.zeros(3)
    for i, s in enumerate(signs):
        e = float(err[i])
        if s == 0:
            out[i] = e if abs(e) < deadband else 0.0
        elif np.sign(e) == s:
            out[i] = e
    return out


def rel_from_raw(raw: dict):
    """(g, rel {obj: centre - g}, mug half-height, tray half-height) from the M1 observation (table frame)."""
    g = np.asarray(raw["grip"]["pos"], float)
    rel = {k: np.asarray(o["pos"], float) - g for k, o in raw["objs"].items()}
    hm = raw["objs"].get("o3", {}).get("he", [0, 0, 0.0475])[2]
    hr = raw["objs"].get("o5", {}).get("he", [0, 0, 0.0075])[2]
    return g, rel, hm, hr


@dataclass
class SkillCmd:
    pos_w: np.ndarray
    quat_w: np.ndarray
    width: float
    events: list = field(default_factory=list)
    motion: str = ""
    allowed: bool = False


class PickPlaceSkill:
    """Mug -> tray pick-and-place skill S (one contract, stages S1 pick / S2 place, snapshot.STAGES)."""

    def __init__(self, dt: float = 0.01, max_retries: int = 2):
        self.dt, self.max_retries = dt, max_retries
        self.w_open, self.w_close = GRIP_MAX_W, max(0.0, 2 * MUG_R - SQUEEZE)
        self.stage_gate = "self"  # "astra" (E-M8c K3, Gemini faithful): stage ends only on Astra's instruction
        self.goal_quat = np.array([math.cos(TOP_DOWN_YAW / 2), 0, 0, math.sin(TOP_DOWN_YAW / 2)])
        self.irrev_gate = None  # couple.driver irrev_allowed(kind, t): two-layer gate (spec §5); None = off
        self.speed_scale = 1.0  # couple slow down (spec §7, info_request slow_down)

    def reset(self, t: float, tcp_pos_w, tcp_quat_w) -> None:
        self.phase, self.stage, self.t_phase0 = "approach", "S1", t
        self.cmd_pos, self.cmd_quat = np.asarray(tcp_pos_w, float).copy(), np.asarray(tcp_quat_w, float).copy()
        self.cmd_w = self.w_open
        self.dec: dict = {}
        self.cap_left = math.inf
        self.moved = 0.0  # motion commanded in the current step (redecide keeps the step's budget)
        self.wait_until = None
        self.retries = 0
        self.pending_outcome = None  # CONTRADICT from an expected_after check in this step
        self.events: list = []
        self._t_hold = None  # last tick with holding(o3) measured true (debounce)
        self.bias = np.zeros(3)  # sum of the Astra offset translations applied by nudge (plan Task 19 fix F19 I2)

    # ------------------------------------------------------------------ decisions
    def begin_slot(self, ds: int, dec: dict) -> None:
        self.ds, self.dec = ds, dict(dec)
        c = constraint(self.dec)
        self.cap_left = c[1] if c else 0.0
        self.moved = 0.0

    def redecide(self, dec: dict) -> None:
        """C2 VLM Stream (M4 §5 :332, canon §74): a newer answer, or the 5 s timeout ({} -> default action = no
        decided motion, as for any empty step), replaces the running step's decisions at this tick. The step keeps
        one option-magnitude budget: the new option's cap minus what this step already moved."""
        self.dec = dict(dec)
        c = constraint(self.dec)
        self.cap_left = max(0.0, c[1] - self.moved) if c else 0.0

    def irreversible(self, question: str, choice: str) -> bool:
        """M6 effect field: 'next' where it fires close / open."""
        return question == "phase" and choice == "next" and self.phase in ("approach", "descend", "place_descend")

    def _set_phase(self, p: str, t: float, why: str = "") -> None:
        if p != self.phase:
            self.events.append({"t": round(t, 3), "event": "phase", "from": self.phase, "to": p, "why": why})
            self.phase, self.t_phase0 = p, t

    # ------------------------------------------------------------------ tick
    def tick(self, t: float, raw: dict, pred: dict, tcp_pos_w, table_z: float) -> SkillCmd:
        tcp_pos_w = np.asarray(tcp_pos_w, float)
        g, rel, hm, hr = rel_from_raw(raw)  # the labels' geometry (finger-link midpoint), consistent with decisions
        # holding debounce (the planner's HOLD_DEBOUNCE, 0.15 s): a one-tick dropout of the gripper applied torque
        # (DEV seed 1: ~20 -> 0.02 N m for 10 ms, pads still on the mug) is not an object loss (pre-R7 fix 3)
        if pred.get("holding(o3)"):
            self._t_hold = t
        elif self._t_hold is not None and t - self._t_hold < HOLD_DEBOUNCE_S - 1e-9:
            pred = {**pred, "holding(o3)": True}
        gs = gripper_state(pred)
        if self.wait_until is not None:
            if t < self.wait_until - 1e-9:
                return self._cmd(t, "wait", False)
            self.wait_until = None
            if self.phase == "close":
                if pred.get("holding(o3)"):
                    self._set_phase("lift", t, "holding")
                else:
                    self.pending_outcome = "CONTRADICT"  # expected_after holding(o3) is false (T1 predicate)
                    self.cmd_w, self.retries = self.w_open, self.retries + 1
                    self.events.append({"t": round(t, 3), "event": "grasp_miss", "retry": self.retries})
                    self._set_phase("approach", t, "grasp_miss")
            elif self.phase == "open":
                if pred.get("holding(o3)"):
                    self.pending_outcome = "CONTRADICT"
                self._set_phase("retreat", t, "released")
        if gs == "closed_empty" and self.cmd_w < self.w_open:  # grasp lost outside a wait: re-open, pick again
            self.pending_outcome = "CONTRADICT"
            self.cmd_w, self.stage, self.retries = self.w_open, "S1", self.retries + 1
            self.events.append({"t": round(t, 3), "event": "object_lost", "retry": self.retries})
            self._set_phase("approach", t, "object_lost")
            self.wait_until = t + OPEN_WAIT_S
            return self._cmd(t, "wait", False)
        M = _motion(self.stage, gs, rel) if {"o3", "o5"} <= set(rel) else "wait"
        d = _delta(M, float(g[2]), rel, hm, hr) if M != "wait" else np.zeros(3)
        if M != "wait":  # the sub-goal shifted by the Astra offset so far (F19 I2: else the skill pulls it back)
            d = d + self.bias
        floor_z = None
        if M == "grasp":  # code safety floor: TCP not below the planner's grasp height - 3 mm (R5 smokes: the
            # finger-mid goal alone sank the gripper body onto the rim; the pool's grasps sat 7.8 mm above the goal)
            floor_z = table_z + float(g[2] + rel["o3"][2]) + hm - GRASP_BELOW_TOP_M - GRASP_FLOOR_M
        at_floor = floor_z is not None and tcp_pos_w[2] <= floor_z + 0.002
        reached = bool(np.all(np.abs(d[:2]) < DEADBAND_M) and (abs(d[2]) < DEADBAND_M or at_floor))
        self._label(M, gs, t)
        ph = self.dec.get("phase")
        # gripper events and stage switch: decision 'next' + code safety predicate
        if ph == "next":
            if (self.stage == "S1" and gs == "open" and M == "grasp" and reached and self.retries <= self.max_retries
                    and self._gate("close", t)):
                self.cmd_w, self.wait_until = self.w_close, t + CLOSE_WAIT_S
                self._set_phase("close", t, "next+reached")
                return self._cmd(t, "close", False)
            if (self.stage == "S1" and pred.get("holding(o3)") and pred.get("lifted(o3)")
                    and self.stage_gate == "self" and self._gate("stage", t)):
                self.stage = "S2"
                self._set_phase("carry", t, "next+exit_S1")
            elif (self.stage == "S2" and gs == "closed_holding" and M == "place"
                  and (pred.get("in_contact(o3,o5)") or reached) and self._gate("release", t)):
                self.cmd_w, self.wait_until = self.w_open, t + OPEN_WAIT_S
                self._set_phase("open", t, "next+placed")
                return self._cmd(t, "open", False)
            elif self.stage == "S2" and gs == "open" and M == "retreat" and reached and self.stage_gate == "self":
                self._set_phase("done", t, "next+retreated")
        # bounded motion toward the sub-goal
        c = constraint(self.dec)
        want = MOTION_OBJ.get(M)
        allowed = c is not None and M != "wait" and self.phase != "done" and (want is None or
                                                                              self.dec.get("target") == want)
        if allowed:
            goal_w = tcp_pos_w + d  # the sub-goal in TCP space: measured TCP + remaining displacement (fresh)
            step_dir = project(goal_w - self.cmd_pos, c[0])
            n = float(np.linalg.norm(step_dir))
            step = min(V.get(self.phase, 0.06) * self.speed_scale * self.dt, n, self.cap_left)
            if step > 0:
                self.cmd_pos = self.cmd_pos + step_dir * (step / n)
                self.cap_left -= step
                self.moved += step
            z_lo = max(table_z + WS_Z[0], floor_z if floor_z is not None else -np.inf)
            self.cmd_pos = np.array([np.clip(self.cmd_pos[0], *WS_X), np.clip(self.cmd_pos[1], *WS_Y),
                                     np.clip(self.cmd_pos[2], z_lo, table_z + WS_Z[1])])
        return self._cmd(t, M, allowed)

    def _gate(self, kind: str, t: float) -> bool:
        return self.irrev_gate is None or bool(self.irrev_gate(kind, t))

    def nudge(self, step6, table_z: float):
        """One tick of the Astra offset (couple.offset): the reference itself moves (the skill goes on from the shifted
        point and M4 (b) compares the measured TCP with it); rotation turns cmd_quat (the skill slerps it back). The
        clipped translation also accumulates in self.bias, which shifts the skill's sub-goal (tick: d + bias) so the
        skill does not pull the reference back to its object-derived goal (plan Task 19 fix F19 I2; zeroed by reset
        and reanchor)."""
        from ..couple.geom import quat_from_rotvec, quat_mul
        s = np.asarray(step6, float)
        p = self.cmd_pos + s[:3]
        old = self.cmd_pos
        self.cmd_pos = np.array([np.clip(p[0], *WS_X), np.clip(p[1], *WS_Y),
                                 np.clip(p[2], table_z + WS_Z[0], table_z + WS_Z[1])])
        self.bias = self.bias + (self.cmd_pos - old)  # the clipped translation, kept in the sub-goal (tick)
        if np.any(s[3:]):
            self.cmd_quat = quat_mul(quat_from_rotvec(s[3:]), self.cmd_quat)
        return self.cmd_pos.copy(), self.cmd_quat.copy()

    def astra_advance(self, decision: str, t: float, pred: dict) -> str:
        """E-M8c K3 (Gemini streaming faithful variant): Astra's run_instruction / reset end the current step, applied
        only when the code safety predicate of that transition holds (M6 rule: decision + code safety predicate).
        Returns applied | rejected | noop."""
        if decision == "run_instruction":
            if self.stage == "S1" and pred.get("holding(o3)") and pred.get("lifted(o3)"):
                self.stage = "S2"
                self._set_phase("carry", t, "astra_run_instruction")
                return "applied"
            return "rejected"
        if decision == "reset":
            if self.stage == "S2" and gripper_state(pred) == "open" and self.phase == "retreat":
                self._set_phase("done", t, "astra_reset")
                return "applied"
            return "rejected"
        return "noop"

    def _label(self, M: str, gs: str, t: float) -> None:
        """Prompt phase name (planner vocabulary) from the sub-phase, outside waits and the done state."""
        if self.phase in ("close", "open", "done"):
            return
        if self.stage == "S1":
            p = {"approach": "approach", "grasp": "descend", "lift": "lift"}.get(M, self.phase)
        else:
            p = {"carry": "carry", "place": "place_descend", "retreat": "retreat"}.get(M, self.phase)
        self._set_phase(p, t, "subphase")

    def _cmd(self, t: float, motion: str, allowed: bool) -> SkillCmd:
        self.cmd_quat = _slerp_step(self.cmd_quat, self.goal_quat, W_MAX * self.dt)
        ev, self.events = self.events, []
        return SkillCmd(self.cmd_pos.copy(), self.cmd_quat.copy(), float(self.cmd_w), ev, motion, allowed)

    # ------------------------------------------------------------------ (b)
    def reanchor(self, tcp_pos_w) -> None:
        """After an M4 DEVIATE / CONTRADICT the reference ref(t) is re-planned from the measured TCP (M5 replans;
        00-interfaces §3): the command stops chasing a point the arm was pushed away from."""
        self.cmd_pos = np.asarray(tcp_pos_w, float).copy()
        self.bias = np.zeros(3)
        self.events.append({"event": "reanchor", "cmd": [round(float(v), 4) for v in self.cmd_pos]})

    def step_outcome(self, tcp_pos_w) -> tuple[str, float]:
        """M4 (b) for the step that just ended: residual of the measured TCP against the commanded reference."""
        r = float(np.linalg.norm(np.asarray(tcp_pos_w, float) - self.cmd_pos))
        if self.pending_outcome:
            out, self.pending_outcome = self.pending_outcome, None
            return out, r
        return ("OK" if r <= OK_M else "LAG" if r <= LAG_M else "DEVIATE"), r


def residual_hook_zero(ctx: dict) -> np.ndarray:
    """Residual-R hook (canon §35): bounded joint correction on top of S near contact. No-op until R is trained."""
    return np.zeros(7)


def apply_residual(q7, hook, ctx: dict, near: bool, r_max: float = 0.02) -> np.ndarray:
    """Add the hook's correction only in the near/contact zone, clipped to +-r_max rad (interval-bounded R)."""
    q7 = np.asarray(q7, float)
    if not near or hook is None:
        return q7
    return q7 + np.clip(np.asarray(hook(ctx), float), -r_max, r_max)
