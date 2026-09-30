"""Sim-truth executor of JCR data episodes (docs/stage3/jcr_design.md §4, §0-2). Drop-in for astra_solo MinJerkExec
(go_to / move_by / grip / busy / tick -> (commanded TCP, gripper width, events), goal_quat, target, cmd, width): the
world's IK (joint step <= 0.04 rad per tick, gravity offset) turns the commanded TCP into joints, exactly as for OX.

Every command: goal_cmd = the command as RECEIVED (upper-like noise already added by the recorder, clipped to the
workspace box), goal_true0 = what the noise-free command resolves to, ref object = the object the command is about
(approach: target, carry: place). Each tick c* = project_ball(goal_true0 moved with the ref object, goal_cmd, R_GOAL);
every DS_TICKS ticks the truth chunk (truth.smooth_chunk, H rows) is re-planned from the commanded TCP and its rows are
played -- the chunk is the label of that sample, and the rows played are exactly its first rows (labels == executed).
Arrival as MinJerkExec: reach < 8 mm of c*, settled (commanded TCP at c* and the TCP still for 4 ticks), timeout
(time budget); then the command's gripper action. Unrecoverable anomaly -> stop chunk (decelerate, hold).
Command realism (NOW.md §1-0c): delay (the command takes effect delay_s after issue; the previous one runs meanwhile),
pre-issue (a keep-gripper move releases the episode loop within PRE_M of c*, so the next command arrives before
arrival), mid-move swap (goal_cmd redrawn at swap_t)."""
from __future__ import annotations

import numpy as np

from ..astra_motion.executor import CLOSE_WAIT_S, OPEN_WAIT_S, SETTLE_M_PER_TICK, SETTLE_TICKS, clip_box
from . import truth as T

DS_TICKS = 4  # 0.2 s at 20 Hz: one decision step = one sample
PRE_M = 0.03
V_BUDGET = 0.04  # m/s for the time budget (= couple_joy.vla_exec.V_MIN)
T_MIN, EXTRA_S = 2.0, 4.0
BLOCKED_M = 0.03


class TruthExec:
    def __init__(self, dt, table_z, tcp0, w_open, w_close, quat0, state_fn, tgt="o3", place="o5",
                 r_goal: float = T.R_GOAL):
        self.dt, self.table_z = float(dt), float(table_z)
        self.r_goal = float(r_goal)  # 0 = a scripted executor (c* = the received command; the OXe arm)
        self.w_open, self.w_close, self.width = float(w_open), float(w_close), float(w_open)
        self.goal_quat = np.asarray(quat0, float)
        self.state_fn, self.tgt, self.place = state_fn, tgt, place
        self.cmd = np.asarray(tcp0, float).copy()
        self.target = self.cmd.copy()
        self.v = np.zeros(3)
        self.seg = None
        self.pending = None
        self.pending_grip = None
        self.wait_until = self.wait_action = None
        self.next_meta = {}
        self.plan = None  # (P, row)
        self.k = 0
        self._still = 0
        self._last_tcp = None
        self.was_holding = False
        self.slip_until, self.slip_m = -1.0, 0.0
        self.stage = None
        self.samples, self.log_events = [], []

    # ------------------------------------------------------------------ MinJerkExec API
    @property
    def busy(self) -> bool:
        s = self.seg is not None and not self.seg.get("released")
        return bool(s or self.pending is not None or self.wait_until is not None or self.pending_grip is not None)

    def go_to(self, pos, grip: str, t: float) -> list:
        m, self.next_meta = self.next_meta, {}
        q, c = clip_box(pos, self.table_z)
        ev = [{"t": round(t, 3), "event": "clipped", "want": np.round(np.asarray(pos, float), 4).tolist(),
               "got": np.round(q, 4).tolist()}] if c else []
        gt = np.asarray(m.get("goal_true", q), float)
        seg = {"goal_cmd": q, "goal_true0": gt, "grip": grip, "role": m.get("role", "lift"), "t_issue": float(t),
               "t_act": float(t) + float(m.get("delay_s", 0.0)), "pre": bool(m.get("pre", False)) and grip == "keep",
               "swap_t": m.get("swap_t"), "swap_dxyz": m.get("swap_dxyz"), "src": m.get("src", "truth"),
               "noise": m.get("noise")}
        self.target = q.copy()
        if seg["t_act"] <= t + 1e-9:
            self._activate(seg, t)
        else:
            self.pending = seg
        return ev

    def move_by(self, delta, grip: str, t: float, tcp) -> list:
        tcp = np.asarray(tcp, float)
        base = self.target if np.linalg.norm(self.target - tcp) <= 0.03 else tcp
        return self.go_to(base + np.asarray(delta, float), grip, t)

    def grip(self, action: str, t: float) -> None:
        self.pending_grip = (action, t)

    # ------------------------------------------------------------------ internals
    def _activate(self, seg, t):
        st = self.state_fn()
        ref = self.tgt if seg["role"] == "approach" else (self.place if seg["role"] == "carry" else None)
        seg["ref"] = ref
        seg["ref0"] = None if ref is None else np.asarray(st["obj"][ref], float).copy()
        seg["t_act"] = float(t)
        d = float(np.linalg.norm(seg["goal_cmd"] - np.asarray(st["tcp"], float)))
        seg["T"] = max(d / V_BUDGET, T_MIN) + EXTRA_S
        seg["p_start"] = self.cmd.copy()
        self.seg, self.pending = seg, None
        self.plan = None  # re-plan now
        self._still = 0
        self.log_events.append({"t": round(t, 3), "event": "cmd_active", "role": seg["role"], "grip": seg["grip"],
                                "src": seg["src"], "delay_s": round(seg["t_act"] - seg["t_issue"], 3)})

    def _act(self, action, t, tcp):
        self.width = self.w_close if action == "close" else self.w_open
        if action == "open":
            self.was_holding = False
        self.wait_until, self.wait_action = t + (CLOSE_WAIT_S if action == "close" else OPEN_WAIT_S), action
        self.v = np.zeros(3)
        self.plan = None
        return [{"t": round(t, 3), "event": action, "tcp": np.round(np.asarray(tcp, float), 4).tolist()}]

    def c_star(self, st):
        s = self.seg
        gt = s["goal_true0"]
        if s["ref"] is not None:
            held = bool(st.get("holding"))
            if not (s["ref"] == self.tgt and held):
                gt = gt + (np.asarray(st["obj"][s["ref"]], float) - s["ref0"])
        c, mis = T.project_ball(gt, s["goal_cmd"], self.r_goal)
        if self.r_goal == 0.0:
            mis = False
        return c, mis, gt

    def _width_out(self, t):
        return self.width + (self.slip_m if t < self.slip_until else 0.0)

    def tick(self, t: float, tcp):
        tcp = np.asarray(tcp, float)
        ev = []
        if self.pending is not None and t >= self.pending["t_act"] - 1e-9:
            self._activate(self.pending, t)
        if self.wait_until is not None:
            if t >= self.wait_until - 1e-9:
                ev.append({"t": round(t, 3), "event": "gripper_done", "action": self.wait_action})
                self.wait_until = self.wait_action = None
            self.k += 1
            return self.cmd.copy(), self._width_out(t), ev
        if self.pending_grip is not None:
            a, _ = self.pending_grip
            self.pending_grip = None
            self.k += 1
            return self.cmd.copy(), self._width_out(t), self._act(a, t, tcp)
        if self.seg is None:
            self.k += 1
            self.v = np.zeros(3)
            return self.cmd.copy(), self._width_out(t), ev
        s = self.seg
        if s.get("swap_t") is not None and t >= s["swap_t"] and not s.get("swapped"):
            s["goal_cmd"], _ = clip_box(s["goal_true0"] + np.asarray(s["swap_dxyz"], float), self.table_z)
            s["swapped"] = True
            self.target = s["goal_cmd"].copy()
            self.plan = None
            ev.append({"t": round(t, 3), "event": "swap"})
        st = self.state_fn()
        c, mis, gt = self.c_star(st)
        hold = bool(st.get("holding"))
        shift = 0.0 if s["ref"] != self.tgt else float(np.linalg.norm(
            np.asarray(st["obj"][self.tgt], float)[:2] - s["ref0"][:2]))
        an = T.anomaly_kinds(st.get("touched", set()), self.tgt, hold, self.was_holding, self.width < self.w_open - 0.02,
                             shift, mis, float(np.asarray(st["obj"][self.tgt])[2]), self.table_z,
                             bool(st.get("upright", True)),
                             pads_empty=float(st.get("grip_w", 1.0)) < self.w_close + T.PAD_EMPTY_M)
        self.was_holding = self.was_holding or hold
        stop = "unrecoverable" in an
        if self.plan is None or self.plan[1] >= DS_TICKS:
            P, _ = T.smooth_chunk(self.cmd, self.v, c, stop=stop)
            self.plan = [P, 0]
            self.samples.append({"k": self.k, "t": round(t, 4), "tcp": tcp.tolist(), "p_cmd": self.cmd.tolist(),
                                 "v": self.v.tolist(), "chunk": P.tolist(), "c_star": c.tolist(),
                                 "goal_cmd": s["goal_cmd"].tolist(), "goal_true": gt.tolist(), "r_goal": T.R_GOAL,
                                 "seg_start": s["p_start"].tolist(),
                                 "allow": s["grip"] if s["grip"] in ("open", "close") else None,
                                 "cmd_age": round(t - s["t_issue"], 3), "cmd_src": s["src"], "role": s["role"],
                                 "stop": stop, "anomaly": sorted(an), "touched": sorted(st.get("touched", ())),
                                 "holding": hold, "grip_w": float(st.get("grip_w", self.width)),
                                 "width_cmd": self._width_out(t), "stage": self.stage})
        P, row = self.plan
        new = P[row]
        self.v = (new - self.cmd) / self.dt
        self.cmd = new.copy()
        self.plan[1] += 1
        err = float(np.linalg.norm(tcp - c))
        moved = float(np.linalg.norm(tcp - self._last_tcp)) if self._last_tcp is not None else 1.0
        self._last_tcp = tcp.copy()
        at_cmd = float(np.linalg.norm(self.cmd - c)) < 1e-6
        self._still = self._still + 1 if (at_cmd and moved < SETTLE_M_PER_TICK) else 0
        if s["pre"] and not s.get("released") and err < PRE_M:
            s["released"] = True
            ev.append({"t": round(t, 3), "event": "pre_issue"})
        kind = None
        if err < T.REACH_M:
            kind = "reach"
        elif self._still >= SETTLE_TICKS:
            kind = "settled" if err <= BLOCKED_M else "timeout"
        elif t > s["t_act"] + s["T"]:
            kind = "timeout"
        if kind is not None:
            ev.append({"t": round(t, 3), "event": kind, "err_mm": round(err * 1e3, 1)})
            self.seg = None
            if s["grip"] in ("open", "close"):
                ev += self._act(s["grip"], t, tcp)
        self.k += 1
        return self.cmd.copy(), self._width_out(t), ev
