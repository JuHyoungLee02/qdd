"""VLA joystick executor: a drop-in for astra_solo.executor.MinJerkExec (same go_to / move_by / grip / busy API) that
moves the arm with fused-VLA chunks instead of a scripted straight line (docs/stage3/coupling_program.md, NOW.md §1-1).

Every decision step (DS = 0.33 s) the executor reads the robot (frames, 8-D joint_pos), turns 'commander goal -
TCP' into the joystick decision (joy.joystick = the VLA's own training labeler), names the phase from the commander's
intent (joy.vla_phase) and asks the VLA for a chunk (client.chunk = runtime.fused_model.FusedClient). Between steps
the chunk is played (fused_action.chunk_value), each joint target clamped to 0.04 rad per tick (NOW.md §4).
The commander keeps authority over WHERE (goal) and WHAT (gripper intent); the VLA owns HOW (the joint path) and WHEN
the gripper acts inside the allowed direction (joy.grip_gate). If the VLA does not complete the allowed gripper action
within GRIP_WAIT_S of arrival the code completes it (event grip_fallback: an interface / VLA failure signal).
Arrival rules = the scripted executor's where they apply: reach = within REACH_TOL_M; settled = still for STILL_S
within BLOCKED_M; timeout = still for STALL_S farther than BLOCKED_M, or past max(d / V_MIN, T_MIN) + EXTRA_S.
tick_q(t, tcp) -> (7 joint targets, gripper width target, events)."""
from __future__ import annotations

import numpy as np

from ..astra_motion.executor import BLOCKED_M, CLOSE_WAIT_S, OPEN_WAIT_S, REACH_TOL_M, clip_box
from ..runtime.fused_action import chunk_value
from . import joy as J

DS = 0.33
GRIP_WAIT_S = 1.5  # after arrival, the VLA has this long to complete the allowed gripper action
GRIP_DONE_M = 0.005
STILL_M = 0.0005  # TCP motion per tick counted as still
STILL_S = 1.0
STALL_S = 3.0
V_MIN = 0.04  # m/s: the time budget of a move (VLA approach speed was ~0.07 m/s in E-VLA-solo)
T_MIN = 2.0
EXTRA_S = 4.0


class VLAJoyExec:
    joint_mode = True

    def __init__(self, io, client, dt, table_z, tcp0, q0, w0, w_open, w_close, quat0=(1.0, 0.0, 0.0, 0.0),
                 tgt="o3", place="o5", holding_fn=None, ds: float = DS):
        self.io, self.client, self.dt, self.table_z, self.ds = io, client, float(dt), float(table_z), float(ds)
        self.w_open, self.w_close = float(w_open), float(w_close)
        self.tgt, self.place = tgt, place
        self.holding_fn = holding_fn or (lambda: False)
        self.cmd = np.asarray(tcp0, float).copy()
        self.target = self.cmd.copy()
        self.goal_quat = np.asarray(quat0, float)
        self.q_cmd = np.asarray(q0, float)[:7].copy()
        self.width = float(w0)
        self.intent = {"mode": "point", "height": "above", "gripper": "keep"}
        self.phase = "approach"
        self.released = False
        self.seg = None  # (goal, t0, T_budget, grip)
        self.gstage = None  # {"action", "t0", "hold_at_entry"}
        self.wait_until = self.wait_action = None
        self.chunk = None  # (rows, chunk_dt, t_state)
        self.next_ds = -1e9
        self._jp_prev = self._t_prev = None
        self._still_t = 0.0
        self._last_tcp = None
        self.log = []  # one row per decision step
        self.stats = {"chunks": 0, "errors": 0, "grip_vla": 0, "grip_fallback": 0}

    # ------------------------------------------------------------------ MinJerkExec API
    @property
    def busy(self) -> bool:
        return bool(self.seg is not None or self.gstage is not None or self.wait_until is not None)

    def set_intent(self, cmd: dict) -> None:
        self.intent = {k: cmd.get(k) for k in ("mode", "height", "gripper")}

    def go_to(self, pos, grip: str, t: float) -> list:
        q, c = clip_box(pos, self.table_z)
        ev = [{"t": round(t, 3), "event": "clipped", "want": np.round(np.asarray(pos, float), 4).tolist(),
               "got": np.round(q, 4).tolist()}] if c else []
        d = float(np.linalg.norm(q - self.target))
        self.target = q.copy()
        self.seg = (q, float(t), max(d / V_MIN, T_MIN) + EXTRA_S, grip)
        self._still_t = 0.0
        self.next_ds = -1e9  # a new command: ask the VLA at once
        return ev

    def move_by(self, delta, grip: str, t: float, tcp) -> list:
        tcp = np.asarray(tcp, float)
        base = self.target if np.linalg.norm(self.target - tcp) <= 0.03 else tcp
        return self.go_to(base + np.asarray(delta, float), grip, t)

    def grip(self, action: str, t: float) -> None:
        self._enter_grip(action, t)

    # ------------------------------------------------------------------ internals
    def _enter_grip(self, action, t):
        self.gstage = {"action": action, "t0": float(t), "hold_at_entry": bool(self.holding_fn())}
        self.phase = action
        self.next_ds = -1e9

    def _closed_empty(self) -> bool:
        return self.gstage is None and self.width < self.w_open - 0.02 and not self.holding_fn()

    def _request(self, t, tcp) -> list:
        arrived = self.gstage is not None
        hold = bool(self.holding_fn())
        intent = dict(self.intent, gripper=self.gstage["action"]) if arrived else self.intent
        self.phase = J.vla_phase(intent, hold, self.released, arrived)
        goal = self.target
        joy = J.joystick(goal, tcp)
        com = J.committed(self.phase, joy, self.tgt, self.place, self._closed_empty())
        jp = np.asarray(self.io.joint_pos(), float)
        ctx = {"t_state": float(t), "joint_pos": jp, "joint_pos_prev": self._jp_prev,
               "dt_prev": None if self._t_prev is None else float(t) - self._t_prev,
               "images": self.io.frames(), "phase": self.phase, "ctx_text": self.io.ctx_text(self.phase, t)}
        self._jp_prev, self._t_prev = jp.copy(), float(t)
        r = self.client.chunk(ctx, com)
        row = {"t": round(float(t), 3), "phase": self.phase, "dec": com, "goal": np.round(goal, 4).tolist(),
               "tcp": np.round(np.asarray(tcp, float), 4).tolist(),
               "err_mm": round(float(np.linalg.norm(goal - np.asarray(tcp, float))) * 1e3, 1),
               "lat_s": round(float(getattr(r, "latency_s", 0.0) or 0.0), 4), "error": r.error}
        self.log.append(row)
        if r.error is not None or r.chunk is None:
            self.stats["errors"] += 1
            self.chunk = None
            return [{"t": round(float(t), 3), "event": "vla_error", "error": str(r.error)}]
        self.stats["chunks"] += 1
        self.chunk = (np.asarray(r.chunk, float), float(r.chunk_dt), float(t))
        return []

    def _grip_done(self, action) -> bool:
        tgt = self.w_close if action == "close" else self.w_open
        return abs(self.width - tgt) <= GRIP_DONE_M

    def _finish_grip(self, action, t, by) -> list:
        g = self.gstage
        self.gstage = None
        self.stats["grip_vla" if by == "vla" else "grip_fallback"] += 1
        if action == "open" and g and g["hold_at_entry"]:
            self.released = True
        self.wait_until = t + (CLOSE_WAIT_S if action == "close" else OPEN_WAIT_S)
        self.wait_action = action
        ev = [{"t": round(t, 3), "event": "grip_fallback", "action": action}] if by == "code" else []
        return ev + [{"t": round(t, 3), "event": action, "by": by, "tcp": np.round(self.target, 4).tolist()}]

    def tick_q(self, t: float, tcp):
        tcp = np.asarray(tcp, float)
        ev = []
        if self.wait_until is not None:  # after a gripper action: hold still like the scripted executor
            if t >= self.wait_until - 1e-9:
                ev.append({"t": round(t, 3), "event": "gripper_done", "action": self.wait_action})
                self.wait_until = self.wait_action = None
            return self.q_cmd.copy(), self.width, ev
        if self.seg is None and self.gstage is None:
            return self.q_cmd.copy(), self.width, ev
        if t >= self.next_ds - 1e-9:
            ev += self._request(t, tcp)
            self.next_ds = t + self.ds
        if self.chunk is not None:
            rows, cdt, t0 = self.chunk
            a = chunk_value(rows, cdt, t0, t + self.dt)
            self.q_cmd = J.clamp_step(self.q_cmd, a[:7])
            allow = self.gstage["action"] if self.gstage is not None else None
            self.width = J.grip_gate(self.width, float(a[7]), allow, self.w_open, self.w_close)
        if self.gstage is not None:
            act = self.gstage["action"]
            if self._grip_done(act):
                ev += self._finish_grip(act, t, "vla")
            elif t - self.gstage["t0"] >= GRIP_WAIT_S - 1e-9:
                self.width = self.w_close if act == "close" else self.w_open
                ev += self._finish_grip(act, t, "code")
            return self.q_cmd.copy(), self.width, ev
        goal, t0, T, grip = self.seg
        err = float(np.linalg.norm(tcp - goal))
        moved = float(np.linalg.norm(tcp - self._last_tcp)) if self._last_tcp is not None else 1.0
        self._last_tcp = tcp.copy()
        self._still_t = self._still_t + self.dt if moved < STILL_M else 0.0
        kind = None
        if err < REACH_TOL_M:
            kind = "reach"
        elif self._still_t >= STILL_S - 1e-9 and err <= BLOCKED_M:
            kind = "settled"
        elif (self._still_t >= STALL_S - 1e-9) or t > t0 + T:
            kind = "timeout"
        if kind is not None:
            ev.append({"t": round(t, 3), "event": kind, "err_mm": round(err * 1e3, 1)})
            self.seg = None
            if grip in ("open", "close"):
                self._enter_grip(grip, t)
        return self.q_cmd.copy(), self.width, ev

    def summary(self) -> dict:
        lat = [r["lat_s"] for r in self.log if r["error"] is None]
        return dict(self.stats, n_steps=len(self.log),
                    lat_p50_s=float(np.median(lat)) if lat else None,
                    lat_p95_s=float(np.percentile(lat, 95)) if lat else None)
