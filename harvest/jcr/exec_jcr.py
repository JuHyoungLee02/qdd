"""JCR closed-loop executor (arms OJ / OJe, prereg_jcr1.md §3): the TruthExec command handling (delay, swap, pre-issue,
clip box) with the MOTION and the GRIPPER TIMING from the JCR model every decision step (0.2 s):
  sample (non-privileged: TCP, received goal, commanded TCP, velocity, envelope, allowed gripper action, command age,
  joints, pad gap, effort) + head / wrist frames -> JCR -> delta chunk, event, contact p, anomaly p.
Authority (code, never the model): rows are pulled into the envelope (within R_PATH of the segment start -> goal
line or within r_goal of the goal), per-row step <= V_CAP * dt; the gripper acts only in the commander-allowed
direction (event close@r / open@r at its row); if the segment has come to rest (JCR asks for no motion for REST_N
decisions inside r_goal + 1 cm of the goal) and the allowed action is not done within GRIP_WAIT_S, the code does it
(grip_fallback, counted). stop -> hold still (anomaly reported). Arrival without privileged state: rest (as above) ->
'settled'; time budget -> 'timeout'.
Every decision also logs the TRUTH chunk / c* of that state (TruthExec rule, privileged) next to the model output:
the rollout is relabelled on the fly (NOW.md §1-0d) and can join the next round's data."""
from __future__ import annotations

import numpy as np

from . import features as FT
from . import truth as T
from .exec_truth import DS_TICKS, TruthExec

R_PATH = 0.04
V_CAP = 0.12
REST_M = 0.003
REST_N = 2
GRIP_WAIT_S = 1.5


def envelope_clip(P, p0, start, goal, r_goal, r_path=R_PATH, v_cap=V_CAP, dt=T.DT):
    """Rows pulled into (ball(goal, r_goal) U tube(start -> goal, r_path)) and step-capped."""
    out, prev = [], np.asarray(p0, float)
    a, b = np.asarray(start, float), np.asarray(goal, float)
    ab = b - a
    L2 = float(ab @ ab)
    for p in np.asarray(P, float):
        if np.linalg.norm(p - b) > r_goal:
            s = 0.0 if L2 < 1e-12 else float(np.clip((p - a) @ ab / L2, 0.0, 1.0))
            n = a + s * ab
            d = float(np.linalg.norm(p - n))
            if d > r_path:
                p = n + (p - n) * (r_path / d)
        st = p - prev
        m = float(np.linalg.norm(st))
        if m > v_cap * dt:
            p = prev + st * (v_cap * dt / m)
        out.append(p)
        prev = p
    return np.array(out)


class JcrExec(TruthExec):
    def __init__(self, *args, client=None, obs_fn=None, seed=0, **kw):
        super().__init__(*args, **kw)
        self.client, self.obs_fn, self.seed = client, obs_fn, int(seed)
        self.rest_n = 0
        self.grip_at = None  # (t_act, action) scheduled by the model
        self.t_rest = None
        self.stats = {"chunks": 0, "errors": 0, "grip_jcr": 0, "grip_fallback": 0, "stop": 0, "lat": []}

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
            from ..astra_motion.executor import clip_box
            s["goal_cmd"], _ = clip_box(s["goal_true0"] + np.asarray(s["swap_dxyz"], float), self.table_z)
            s["swapped"] = True
            self.target = s["goal_cmd"].copy()
            self.plan = None
            ev.append({"t": round(t, 3), "event": "swap"})
        allow = s["grip"] if s["grip"] in ("open", "close") else None
        if self.plan is None or self.plan[1] >= DS_TICKS:
            st = self.state_fn()  # privileged: the truth label of this state only (relabel), never used to act
            c, mis, gt = self.c_star(st)
            hold = bool(st.get("holding"))
            an = T.anomaly_kinds(st.get("touched", set()), self.tgt, hold, self.was_holding,
                                 self.width < self.w_open - 0.02, 0.0 if s["ref"] != self.tgt else float(
                                     np.linalg.norm(np.asarray(st["obj"][self.tgt], float)[:2] - s["ref0"][:2])),
                                 mis, float(np.asarray(st["obj"][self.tgt])[2]), self.table_z,
                                 bool(st.get("upright", True)),
                             pads_empty=float(st.get("grip_w", 1.0)) < self.w_close + T.PAD_EMPTY_M)
            self.was_holding = self.was_holding or hold
            P_truth, _ = T.smooth_chunk(self.cmd, self.v, c, stop="unrecoverable" in an)
            ob = self.obs_fn()
            smp = {"k": self.k, "t": round(t, 4), "tcp": tcp.tolist(), "p_cmd": self.cmd.tolist(),
                   "v": self.v.tolist(), "goal_cmd": s["goal_cmd"].tolist(), "r_goal": T.R_GOAL, "allow": allow,
                   "cmd_age": round(t - s["t_issue"], 3), "q": list(map(float, ob["q"])), "grip_w": ob["grip_w"],
                   "effort": ob["effort"]}
            try:
                o = self.client.act(smp, ob["head"], ob["wrist"], seed=self.seed * 100003 + self.k)
                err = o.get("error")
            except Exception as ex:  # noqa: BLE001
                o, err = None, repr(ex)
            if err or o is None:
                self.stats["errors"] += 1
                P = np.repeat(self.cmd[None], T.H, 0)
                kind, row = "keep", None
                o = {"error": err}
            else:
                self.stats["chunks"] += 1
                self.stats["lat"].append(o.get("latency_s"))
                kind, row = FT.decode_event(int(np.argmax(o["event_p"])))
                P = self.cmd[None] + np.asarray(o["delta"], float)
                if kind == "stop":
                    self.stats["stop"] += 1
                    P = np.repeat(self.cmd[None], T.H, 0)
                P = envelope_clip(P, self.cmd, s["p_start"], s["goal_cmd"], T.R_GOAL)
                if kind in ("close", "open") and kind == allow and self.grip_at is None:
                    self.grip_at = (t + row * self.dt, kind)
            self.plan = [P, 0]
            smp.update(truth_chunk=P_truth.tolist(), c_star=c.tolist(), goal_true=gt.tolist(), anomaly=sorted(an),
                       touched=sorted(st.get("touched", ())), holding=hold, stop=("unrecoverable" in an),
                       seg_start=s["p_start"].tolist(), role=s["role"], cmd_src=s["src"], stage=self.stage,
                       jcr={"delta": o.get("delta"), "event": [kind, row], "contact_p": o.get("contact_p"),
                            "anomaly_p": o.get("anomaly_p"), "error": o.get("error")})
            self.samples.append(smp)
            moving = float(np.linalg.norm(P[-1] - self.cmd)) > REST_M
            near = float(np.linalg.norm(tcp - s["goal_cmd"])) < T.R_GOAL + 0.01
            self.rest_n = 0 if (moving or not near) else self.rest_n + 1
        P, row_i = self.plan
        new = P[row_i]
        self.v = (new - self.cmd) / self.dt
        self.cmd = new.copy()
        self.plan[1] += 1
        if self.grip_at is not None and t >= self.grip_at[0] - 1e-9:
            a = self.grip_at[1]
            self.grip_at = None
            self.stats["grip_jcr"] += 1
            ev.append({"t": round(t, 3), "event": "settled", "err_mm": round(float(np.linalg.norm(
                tcp - s["goal_cmd"])) * 1e3, 1), "by": "jcr"})
            self.seg = None
            return self.cmd.copy(), self._width_out(t), ev + self._act(a, t, tcp)
        if s["pre"] and not s.get("released") and float(np.linalg.norm(tcp - s["goal_cmd"])) < 0.03:
            s["released"] = True
            ev.append({"t": round(t, 3), "event": "pre_issue"})
        kind = None
        if self.rest_n >= REST_N:
            if allow is None:
                kind = "settled"
            else:
                self.t_rest = t if self.t_rest is None else self.t_rest
                if t - self.t_rest >= GRIP_WAIT_S - 1e-9:
                    kind = "settled"
        if kind is None and t > s["t_act"] + s["T"]:
            kind = "timeout"
        if kind is not None:
            ev.append({"t": round(t, 3), "event": kind, "err_mm": round(float(np.linalg.norm(
                tcp - s["goal_cmd"])) * 1e3, 1)})
            self.seg, self.t_rest, self.rest_n, self.grip_at = None, None, 0, None
            if allow is not None:
                self.stats["grip_fallback"] += 1
                ev.append({"t": round(t, 3), "event": "grip_fallback", "action": allow})
                ev += self._act(allow, t, tcp)
        self.k += 1
        return self.cmd.copy(), self._width_out(t), ev
