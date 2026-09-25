"""E-Astra-motion episode harness (pure; the world is injected). Probe scope (user decision, 2026-09-26): Astra does not
represent targets in space; it looks at the three cameras and gives GPT-as-Policy-style commands (continue / edit /
stop) with an assessment (task_progress, execution / intent status, evidence, confidence).

World protocol (world_isaac.IsaacWorld on the pod, tests/astra_motion/fakeworld.FakeWorld locally):
  dt, table_z, w_open, w_close, quat0 (start gripper orientation), last_obs
  reset(seed, task); task_info() -> {instruction, tgt, place, present}
  observe() -> Obs (head, wrist_left, wrist rendered now); frame() -> {head, wrist, wrist_cam} RGB for videos
  step(cmd_pos, width, quat) -> one control tick (IK / physics are the world's)
  status() -> {t, tcp, grip_w, pred, obj {id: centre}, gripper_contacts set}
  run_oracle(on_tick) -> dict (upper reference)
Modes: S (synchronous: the robot waits for each answer; immediate executor), S-stream-F0 / S-stream-F1 (serial stream,
canon §84 supplement 2 / spec §16: one call in flight, the next request is sent with the newest images as soon as the
answer arrives or times out; the robot keeps moving; smooth executor; F0 fresh requests, F1 flow-anchored diff +
2-answer confirmation); references oracle, nomodel. replay(): re-run a stream episode's logged answers open-loop through
either executor (jerk study).
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass

import numpy as np

from . import geometry as G
from . import prompts as PR
from . import schema as SC
from .executor import MotionExec, SmoothExec, Target
from .overlay import annotate, png_bytes

N_SYNC = 30  # S: call sites per episode
LIMIT_S = 60.0
GRACE_S = 3.0
KNOCK_M = 0.02
VIDEO_EVERY = 4
GRASP_BELOW_TOP_M = 0.018  # = sim.planner.GRASP_BELOW_TOP_M (oracle grasp point: 1.8 cm below the object top)
SUCCESS_HOLD_S = 1.0  # = config.CFG.success_hold_s
MODEL_MODES = ("S", "S-stream-F0", "S-stream-F1")
REF_MODES = ("oracle", "nomodel")
STREAM_WINDOW0 = 3.0  # s: first validity window / "predicted at arrival" horizon (then the recent answer ages)
STREAM_WINDOW = (1.0, 8.0)  # clamp of the window (median of the last 3 answer ages)
STREAM_TIMEOUT_S = 20.0  # sim s without an answer -> give up waiting (the call still costs) and send the next
STAG_MAX_S = 90.0  # s of execution after the first send
STAG_MAX_CALLS = 30
STAG_RT = 1.0  # sim seconds per wall second (1 = real time; tests use more)
SMOOTH_DECAY_S = 0.5
AGREE_COS = math.cos(math.radians(35.0))  # same direction (flip / consensus / F1 confirmation)


def obj_height(k: str) -> float:
    from ..sim.scene import OBJ_GEOM
    g = OBJ_GEOM[k]
    return float(g["height"] if "height" in g else g["size"][2])


@dataclass
class Obs:
    t: float
    rgb: dict
    depth: dict | None
    cams: dict
    tcp: np.ndarray
    grip_w: float


def _success_now(pred, tgt, place) -> bool:
    return pred.get(f"on({tgt},{place})") is True and pred.get(f"holding({tgt})") is False and \
        pred.get(f"upright({tgt})") is True


class Monitor:
    """Per-tick bookkeeping: success (1 s hold, = planner.success_from_history), grasp / lift, collisions, path."""

    def __init__(self, world, info):
        st = world.status()
        self.tgt, self.place, self.table_z = info["tgt"], info["place"], world.table_z
        self.start = {k: np.asarray(v, float).copy() for k, v in st["obj"].items()}
        self.t_ok = None
        self.success = False
        self.ever_hold = self.ever_lift = self.tipped = self.off_table = False
        self.max_lift_mm = 0.0
        self.touched: set = set()
        self.closes: list = []
        self.path: list = []
        self.hold_changes: list = []
        self._hold = False
        self.n = 0
        self.last = st

    def update(self, st):
        self.last, self.n = st, self.n + 1
        pred, t = st["pred"], st["t"]
        if _success_now(pred, self.tgt, self.place):
            self.t_ok = t if self.t_ok is None else self.t_ok
            if t - self.t_ok >= SUCCESS_HOLD_S - 1e-9:
                self.success = True
        else:
            self.t_ok = None
        hold = pred.get(f"holding({self.tgt})") is True
        if hold != self._hold:
            self.hold_changes.append(round(t, 3))
            self._hold = hold
        self.ever_hold |= hold
        if hold and pred.get(f"lifted({self.tgt})") is True:
            self.ever_lift = True
        tp = np.asarray(st["obj"][self.tgt], float)
        self.max_lift_mm = max(self.max_lift_mm, (tp[2] - self.start[self.tgt][2]) * 1e3)
        if pred.get(f"upright({self.tgt})") is False and not hold:
            self.tipped = True
        if tp[2] < self.table_z - 0.05:
            self.off_table = True
        self.touched |= set(st.get("gripper_contacts", set())) - {self.tgt}
        self.path.append([round(float(t), 3)] + [round(float(v), 5) for v in st["tcp"]])

    def on_close(self, t, tcp):
        tp = np.asarray(self.last["obj"][self.tgt], float)
        gp = np.array([tp[0], tp[1], self.table_z + obj_height(self.tgt) - GRASP_BELOW_TOP_M])
        tcp = np.asarray(tcp, float)
        self.closes.append({"t": round(t, 3), "tcp": np.round(tcp, 4).tolist(), "oracle_gp": np.round(gp, 4).tolist(),
                            "err_mm": round(float(np.linalg.norm(tcp - gp)) * 1e3, 1),
                            "err_xy_mm": round(float(np.linalg.norm((tcp - gp)[:2])) * 1e3, 1),
                            "dz_mm": round(float(tcp[2] - gp[2]) * 1e3, 1),
                            "above_top": bool(tcp[2] > self.table_z + obj_height(self.tgt) + 0.005)})

    def summary(self) -> dict:
        moved = {k: round(float(np.linalg.norm((np.asarray(self.last["obj"][k]) - v)[:2])) * 1e3, 1)
                 for k, v in self.start.items() if k != self.tgt}
        knocked = sorted(k for k, d in moved.items() if d > KNOCK_M * 1e3)
        if self.success:
            stage = None
        elif not self.ever_hold:
            c = self.closes[0] if self.closes else None
            stage = "approach" if (c is None or c["err_xy_mm"] > 20.0 or c["above_top"]) else "grasp"
        elif not self.ever_lift:
            stage = "lift"
        else:
            stage = "place"
        return {"success": self.success, "grasp_lift": self.ever_lift, "ever_hold": self.ever_hold,
                "fail_stage": stage, "max_lift_mm": round(self.max_lift_mm, 1), "first_close": self.closes[0]
                if self.closes else None, "n_close": len(self.closes), "gripper_touched_other": sorted(self.touched),
                "knocked": knocked, "moved_mm": moved, "tipped": self.tipped, "off_table": self.off_table,
                "collision": bool(self.touched or knocked or self.tipped), "tcp_path": self.path,
                "hold_changes": self.hold_changes, **motion_stats(self.path)}


def motion_stats(path) -> dict:
    """Max TCP speed (m/s) and jerk (m/s^3, RMS and max) from the per-tick [t, x, y, z] path."""
    P = np.asarray(path, float)
    if len(P) < 5:
        return {"max_speed": None, "jerk_rms": None, "jerk_max": None}
    dt = float(np.median(np.diff(P[:, 0])))
    x = P[:, 1:]
    v = np.diff(x, axis=0) / dt
    j = np.diff(x, n=3, axis=0) / dt ** 3
    jn = np.linalg.norm(j, axis=1)
    return {"max_speed": round(float(np.linalg.norm(v, axis=1).max()), 4),
            "jerk_rms": round(float(np.sqrt((jn ** 2).mean())), 2), "jerk_max": round(float(jn.max()), 2)}


def _kind(c):
    if c is None:
        return "hold", None, "keep"
    if c["decision"] == "stop":
        return "stop", None, "keep"
    e = c["edit"]
    dp = np.asarray(e["delta_position_cm"], float)
    return ("move" if np.linalg.norm(dp) > 1e-6 else "still"), dp, e["gripper"]


def same_command(a: dict | None, b: dict | None) -> bool:
    """Two effective commands agree: same kind (move / still / stop / hold), same gripper action, and (both moving)
    movement directions within 35 deg."""
    ka, da, ga = _kind(a)
    kb, db, gb = _kind(b)
    if ka != kb or ga != gb:
        return False
    if ka == "move":
        return float(da @ db / (np.linalg.norm(da) * np.linalg.norm(db))) >= AGREE_COS
    return True


def opposite(a: dict | None, b: dict | None) -> bool:
    """Direction flip: both move and the directions are more than 90 deg apart."""
    ka, da, _ = _kind(a)
    kb, db, _ = _kind(b)
    return ka == kb == "move" and float(da @ db) < 0


class Episode:
    def __init__(self, world, mode, model, seed, task, out_dir=None, video=False, n_sync=N_SYNC, limit_s=LIMIT_S):
        self.w, self.mode, self.model, self.seed, self.task = world, mode, model, seed, task
        self.out_dir, self.video, self.n_sync, self.limit_s = out_dir, video, n_sync, limit_s
        self.calls: list = []
        self.events: list = []
        self.marks: list = []
        self.frames: list = []
        self.end_reason = None
        self.extra: dict = {}
        self.last_motion = None  # the last committed edit (continue repeats it)
        self.committed = None  # the last committed command (F1 flow)
        self.n_uncertain_continue = 0
        self.proprio_conflicts: list = []

    # ------------------------------------------------------------------ model calls
    def _save_call(self, idx, kind, attempt, text, images, reply):
        if not self.out_dir:
            return
        d = os.path.join(self.out_dir, "calls", f"c{idx:03d}_{kind}_a{attempt}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "prompt.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(d, "reply.txt"), "w", encoding="utf-8") as f:
            f.write(reply or "")
        for j, (label, png) in enumerate(images):
            with open(os.path.join(d, f"img{j + 1}_{label.replace(' ', '_')}.png"), "wb") as f:
                f.write(png)

    def _record(self, idx, kind, attempt, rep, parsed, err, st=None):
        rec = {"call": idx, "kind": kind, "attempt": attempt, "valid": parsed is not None, "errors": err[:8],
               "latency_s": round(rep.latency_s, 3), "first_token_s": round(rep.first_token_s, 3),
               "usage": rep.usage, "cost_usd": round(rep.cost_usd, 6), "api_error": rep.error,
               "model_field": rep.model_field, "t_sim": round(self.w.status()["t"], 3)}
        if parsed is not None:
            rec["parsed"] = parsed
            a = parsed.get("assessment") or {}
            if a.get("claims") and st is not None:  # proprio cross-check of wrist-verified claims (spec §12)
                gw = st["grip_w"]
                if any(k in " ".join(a["claims"]).lower() for k in ("grasp", "hold", "held", "lift", "pick")) and \
                        (gw >= self.w.w_open - 0.005 or gw <= self.w.w_close + 0.002):
                    self.proprio_conflicts.append({"call": idx, "claims": a["claims"], "pad_gap_mm": round(gw * 1e3, 1)})
        self.calls.append(rec)
        return rec

    def _ask(self, text, images, kind, schema_mode):
        """Synchronous call + at most one repair call. Returns the parsed output or None."""
        err: list = []
        for attempt in range(2):
            t = text if attempt == 0 else text + PR.REPAIR.format(errors="; ".join(err[:6]))
            idx = len(self.calls)
            st = self.w.status()
            rep = self.model.ask(t, images, self._meta(kind, idx, attempt))
            parsed, err = (None, [f"api:{rep.error}"]) if (rep.error and not rep.text) else \
                SC.validate(schema_mode, rep.text)
            self._record(idx, kind, attempt, rep, parsed, err, st)
            self._save_call(idx, kind, attempt, t, images, rep.text)
            if parsed is not None:
                return parsed
        return None

    def _meta(self, kind, idx, attempt=0, **kw):
        st = self.w.status()
        return {"seed": self.seed, "task": self.task, "mode": self.mode, "kind": kind, "call": idx,
                "attempt": attempt, "prompt_id": PR.PROMPT_ID, "tcp": np.asarray(st["tcp"], float).tolist(),
                "committed": self.committed, "last_motion": self.last_motion, **kw}

    def _exec_dir(self):
        ex = self.ex
        if isinstance(ex, SmoothExec):
            v = ex.v if np.linalg.norm(ex.v) > 1e-9 else ex.v_tgt
            return v if np.linalg.norm(v) > 1e-9 else None
        tg = ex.cur if ex.cur is not None else (ex.queue[0] if ex.queue else None)
        return None if tg is None else tg.pos - ex.cmd

    def _images(self, obs):
        """Head / left wrist / right wrist (spec §12) with rulers, TCP marker and the §13 motion overlay (last 3 s TCP
        trace, executor direction, last Astra offset); on the right wrist view the directions go to a corner inset."""
        ad = np.asarray(self.last_motion["delta_position_cm"], float) / 100 if self.last_motion else None
        ed = self._exec_dir()
        tr = [p[1:] for p in self.mon.path if p[0] >= obs.t - 3.0]
        kw = dict(trace=tr, exec_dir=ed, astra_dir=ad)
        return [("head camera", png_bytes(annotate(obs.rgb["head"], obs.cams["head"], obs.tcp, **kw))),
                ("left wrist camera", png_bytes(annotate(obs.rgb["wrist_left"], obs.cams["wrist_left"], obs.tcp,
                                                         **kw))),
                ("right wrist camera", png_bytes(annotate(obs.rgb["wrist"], obs.cams["wrist"], obs.tcp,
                                                          wrist_inset=True, exec_dir=ed, astra_dir=ad)))]

    def _text(self, obs, block: str, dyn: str = "") -> str:
        """[static][interface block][NOW][per-call information] -- the cacheable prefix first."""
        yaw = math.degrees(G.yaw_between(self.ex.goal_quat, self.ex.quat0))
        return (PR.static(self.info, obs.cams["head"], obs.cams["wrist_left"], self.w.table_z) + "\n" + block + "\n"
                + PR.dynamic(obs.cams["wrist"], obs.tcp, yaw, obs.grip_w, self.w.w_close) + dyn)

    # ------------------------------------------------------------------ commands -> executor
    def _effective(self, p: dict, last_motion) -> dict | None:
        """The command an S-cmd answer means: uncertain / low confidence -> continue (coupling spec §11); continue ->
        repeat the last committed motion (gripper keep), or hold when there is none."""
        dec = p["decision"]
        if SC.is_uncertain(p) and dec != "continue":
            self.n_uncertain_continue += 1
            dec = "continue"
        if dec == "stop":
            return {"decision": "stop"}
        if dec == "continue":
            return {"decision": "edit", "edit": dict(last_motion, gripper="keep")} if last_motion else None
        return {"decision": "edit", "edit": dict(p["edit"])}

    def _commit(self, eff: dict | None, t: float, tcp, scale: float = 1.0, flip: bool = False,
                window: float | None = None) -> str:
        """Execute an effective command from the measured TCP. Immediate executor: a straight move by the delta, then
        the gripper action. Smooth executor: a ramp over the window (scale, flip). Returns hold / stop / move."""
        if eff is None:
            return "hold"
        if eff["decision"] == "stop":
            return "stop"
        e = eff["edit"]
        if any(abs(v) > 1e-9 for v in e["delta_position_cm"]) or any(abs(v) > 1e-9 for v in e["delta_rotation_rad"]):
            self.last_motion = {"delta_position_cm": list(e["delta_position_cm"]),
                                "delta_rotation_rad": list(e["delta_rotation_rad"]), "gripper": "keep"}
        self.committed = {"decision": "edit", "edit": dict(e)}
        self.ex.rotate(np.asarray(e["delta_rotation_rad"], float) * (scale if isinstance(self.ex, SmoothExec) else 1))
        dp = np.asarray(e["delta_position_cm"], float) / 100.0
        if isinstance(self.ex, SmoothExec):
            self.ex.apply(dp, e["gripper"], t, scale, flip, window)
            self.marks = [(np.asarray(tcp, float) + scale * dp, "cmd")]
        else:
            tgt = Target(self.ex.base(tcp) + dp, e["gripper"], f"m{len(self.events)}")
            self.marks = [(tgt.pos, "cmd")]
            self.events += self.ex.load([tgt], t)
        return "move"

    # ------------------------------------------------------------------ simulation
    def _tick(self):
        st = self.w.status()
        cmd, width, ev = self.ex.tick(st["t"], st["tcp"])
        for e in ev:
            self.events.append(e)
            if e["event"] == "close":
                self.mon.on_close(st["t"], st["tcp"])
        self.w.step(cmd, width, self.ex.goal_quat)
        self._video_tick()

    def _check(self) -> str | None:
        st = self.w.status()
        self.mon.update(st)
        if self.mon.success:
            return "success"
        if self.mon.off_table:
            return "off_table"
        if st["t"] >= self.limit_s:
            return "time_limit"
        return None

    def _run(self) -> str:
        while self.ex.busy:
            r = self._check()
            if r:
                return r
            self._tick()
        return "idle"

    def _grace(self) -> str:
        t0 = self.w.status()["t"]
        while True:
            r = self._check()
            if r in ("success", "off_table"):
                return r
            if self.w.status()["t"] - t0 >= GRACE_S:
                return "grace_end"
            self._tick()

    def _video_tick(self):
        if not self.video:
            return
        self._vt = getattr(self, "_vt", -1) + 1
        if self._vt % VIDEO_EVERY:
            return
        fr = self.w.frame()
        st = self.w.status()
        h = annotate(fr["head"], self._cams["head"], st["tcp"], rulers=False, marks=self.marks)
        wr = annotate(fr["wrist"], fr.get("wrist_cam") or self._cams["wrist"], st["tcp"], rulers=False)
        from PIL import Image, ImageDraw
        hh = h.shape[0]
        wr = np.asarray(Image.fromarray(wr).resize((int(wr.shape[1] * hh / wr.shape[0]), hh)))
        im = Image.fromarray(np.concatenate([h, wr], 1))
        ImageDraw.Draw(im).text((4, 4), f"{self.mode} {getattr(self.model, 'name', '')} s{self.seed} {self.task} "
                                         f"t={st['t']:.1f}s", fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))
        self.frames.append(np.asarray(im))

    # ------------------------------------------------------------------ modes
    def _setup(self, smooth: bool):
        w = self.w
        w.reset(self.seed, self.task)
        self.info = w.task_info()
        self.mon = Monitor(w, self.info)
        st = w.status()
        self.ex = (SmoothExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, window=STREAM_WINDOW0,
                              decay_s=SMOOTH_DECAY_S, quat0=w.quat0) if smooth else
                   MotionExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, quat0=w.quat0))

    def run(self) -> dict:
        self._setup(smooth=self.mode.startswith("S-stream"))
        if self.mode.startswith("S-stream"):  # the stream runs up to STAG_MAX_S after its first send
            self.limit_s = max(self.limit_s, STAG_MAX_S + GRACE_S + 1.0)
        self._cams = self.w.observe().cams
        wall0 = time.perf_counter()
        if self.mode == "oracle":
            def on_tick(s, phase, _prev=[None]):
                self.mon.update(s)
                if phase == "close" and _prev[0] != "close":
                    self.mon.on_close(s["t"], s["tcp"])
                _prev[0] = phase
                self._video_tick()
            self.extra["oracle"] = self.w.run_oracle(on_tick)
            self.end_reason = "success" if self.mon.success else "oracle_end"
        elif self.mode == "nomodel":
            self._nomodel()
        elif self.mode == "S":
            self._s_sync()
        elif self.mode in ("S-stream-F0", "S-stream-F1"):
            self._stagger(self.mode[-2:])
        else:
            raise ValueError(self.mode)
        res = self._result(time.perf_counter() - wall0)
        self._save(res)
        return res

    def _nomodel(self):
        """Lower reference: the same executor straight to the (ideally detected) object centres."""
        st, tz, info = self.w.status(), self.w.table_z, self.info
        c = np.asarray(st["obj"][info["tgt"]], float)
        pc = np.asarray(st["obj"][info["place"]], float)
        h = obj_height(info["tgt"])
        place_top = tz + (obj_height(info["place"]) if info["place"] != "o11" else 0.0)
        tg = [Target(c + [0, 0, h / 2 + 0.10], "keep", "n0"), Target(c.copy(), "close", "n1"),
              Target(np.array([c[0], c[1], tz + 0.20]), "keep", "n2"),
              Target(np.array([pc[0], pc[1], tz + 0.20]), "keep", "n3"),
              Target(np.array([pc[0], pc[1], place_top + h / 2 + 0.01]), "open", "n4"),
              Target(np.array([pc[0], pc[1], place_top + h / 2 + 0.11]), "keep", "n5")]
        self.marks = [(t.pos, t.tag) for t in tg]
        self.events += self.ex.load(tg, st["t"])
        r = self._run()
        self.end_reason = r if r != "idle" else self._grace()

    def _s_sync(self):
        """S: call -> execute the command (the robot waits for each answer) -> call ... up to n_sync call sites."""
        hist = []
        r = "idle"
        for i in range(1, self.n_sync + 1):
            obs = self.w.observe()
            self._cams = obs.cams
            text = self._text(obs, PR.S_SYNC, PR.s_sync_dyn(i, self.n_sync, hist))
            p = self._ask(text, self._images(obs), f"s{i}", "S-cmd")
            if p is None:
                self.end_reason = "schema"
                return
            st = self.w.status()
            eff = self._effective(p, self.last_motion)
            done = self._commit(eff, st["t"], st["tcp"])
            if done == "stop":
                hist.append(f"{i}: stop")
                r = "stop"
                break
            n_ev = len(self.events)
            r = self._run() if done == "move" else "idle"
            if done == "hold":  # continue with nothing to repeat: hold still 0.5 s
                for _ in range(int(round(0.5 / self.w.dt))):
                    r2 = self._check()
                    if r2:
                        r = r2
                        break
                    self._tick()
            st = self.w.status()
            evs = self.events[n_ev:]
            note = (" [clipped to the workspace]" if any(e["event"] == "clipped" for e in evs) else "") + \
                (" [blocked: target not reached]" if any(e["event"] == "timeout" for e in evs) else "") + \
                "".join(f" [stopped {e['err_mm']:.0f} mm short of the target]" for e in evs
                        if e["event"] == "settled")
            unc = " [treated as continue: uncertain / low confidence]" if (SC.is_uncertain(p) and
                                                                           p["decision"] != "continue") else ""
            hist.append(f"{i}: {PR.describe_cmd(eff) if eff else 'hold'}{unc} -> TCP ({st['tcp'][0]:.3f}, "
                        f"{st['tcp'][1]:.3f}, {st['tcp'][2]:.3f}) m, pad gap {st['grip_w'] * 100:.1f} cm{note}")
            if r in ("success", "off_table", "time_limit"):
                break
        self.extra["s_history"] = hist
        self.end_reason = r if r in ("success", "off_table", "time_limit") else self._grace()

    # ------------------------------------------------------------------ serial stream (user-log 83, 86)
    def _predict(self, horizon: float) -> dict:
        import copy
        ex = copy.deepcopy(self.ex)
        t = self.w.status()["t"]
        for i in range(int(round(horizon / ex.dt))):
            ex.tick(t + i * ex.dt, ex.cmd)
        return {"tcp": ex.cmd.copy(), "width": ex.width, "busy": ex.busy}

    def _recent(self, t: float) -> str:
        ev = [f"{e['event']} at t={e['t']:.1f}" for e in self.events if e["t"] >= t - 3.0 and
              e["event"] in ("close", "open", "gripper_done", "clipped")]
        h = [p for (tt, p) in self._tcp_hist if tt >= t - 3.0]
        d = (np.asarray(h[-1]) - np.asarray(h[0])) * 100 if len(h) >= 2 else np.zeros(3)
        return f"TCP moved ({d[0]:+.1f}, {d[1]:+.1f}, {d[2]:+.1f}) cm; events: " + ("; ".join(ev) if ev else "none")

    def _apply_answer(self, a: dict, eff, t, tcp, prev_eff, window=None) -> str:
        """Smooth application: scale 1.0 when the answer agrees with the previous executed answer, else 0.5; a flip
        (opposite direction) resets the ramp first."""
        scale = 1.0 if (prev_eff is not None and same_command(eff, prev_eff)) else 0.5
        flip = opposite(eff, prev_eff)
        a.update(scale=scale, flip=flip, applied_cmd=eff, window=window)
        return self._commit(eff, t, tcp, scale, flip, window)

    def _stagger(self, style: str):
        """Serial stream: one call in flight; the next request (newest images) is sent when the answer arrives or
        after STREAM_TIMEOUT_S; the sim is paced to the wall clock (STAG_RT x real time) and the robot never waits.
        The smooth executor's validity window = the expected time to the next answer (median of the last 3 answer
        ages, first STREAM_WINDOW0, clamped to STREAM_WINDOW). F0 (fresh): the request has only the current observation and
        the task; its (effective) command is applied on arrival. F1 (flow-anchored): the request also carries the
        committed command, task_progress, recent motion and the predicted state at arrival; keep = repeat the
        committed command, revise = a new command applied only when the next arriving answer confirms it (also
        revise, same gripper, direction within 35 deg; the later command is applied)."""
        from concurrent.futures import ThreadPoolExecutor
        w = self.w
        self._tcp_hist = []
        answers, inflight, pending = [], [], None
        prev_eff = None
        tp_now = {"verified_completed": [], "currently_attempting": "start", "remaining": []}
        t0 = w.status()["t"]
        wall0 = time.perf_counter()
        sites = 0
        r = None
        pool = ThreadPoolExecutor(max_workers=4)
        ages: list = []
        abandoned: list = []
        try:
            while True:
                st = w.status()
                t = st["t"]
                self._tcp_hist.append((t, np.asarray(st["tcp"], float).copy()))
                self._tcp_hist = [x for x in self._tcp_hist if x[0] >= t - 3.5]
                r = self._check()
                if r:
                    break
                if t - t0 >= STAG_MAX_S:
                    r = "stream_time_limit"
                    break
                # ---- send
                for f in [x for x in inflight if t - x["send_t"] > STREAM_TIMEOUT_S]:
                    inflight.remove(f)  # gave up waiting: still billed, recorded when it lands
                    abandoned.append(f)
                    answers.append({"site": f["site"], "send_t": round(f["send_t"], 3), "arr_t": None,
                                    "valid": False, "errors": ["timeout"], "status": "timed_out"})
                window = float(np.clip(np.median(ages[-3:]), *STREAM_WINDOW)) if ages else STREAM_WINDOW0
                if not inflight and sites < STAG_MAX_CALLS:
                    o = w.observe()
                    self._cams = o.cams
                    if style == "F0":
                        text = self._text(o, PR.ST_F0)
                    else:
                        pr = self._predict(window)
                        pred = (f"TCP ({pr['tcp'][0]:.3f}, {pr['tcp'][1]:.3f}, {pr['tcp'][2]:.3f}) m, pad gap "
                                f"{pr['width'] * 100:.1f} cm, " + ("still moving" if pr["busy"] else "holding still"))
                        text = self._text(o, PR.ST_F1, PR.st_f1_dyn(PR.describe_cmd(self.committed), tp_now,
                                                                      self._recent(t), pred, window))
                    sites += 1
                    ims = self._images(o)
                    fut = pool.submit(self.model.ask, text, ims, self._meta("st", len(self.calls), style=style,
                                                                            site=sites))
                    inflight.append({"fut": fut, "send_t": t, "site": sites, "committed": self.committed,
                                     "last_motion": self.last_motion, "text": text, "ims": ims, "st": st})
                # ---- receive (arrival order)
                for f in [x for x in inflight if x["fut"].done()]:
                    inflight.remove(f)
                    rep = f["fut"].result()  # re-raises BudgetStop
                    p, err = (None, [f"api:{rep.error}"]) if (rep.error and not rep.text) else \
                        SC.validate("S-cmd" if style == "F0" else "S-diff", rep.text)
                    idx = len(self.calls)
                    self._record(idx, "st", 0, rep, p, err, f["st"])
                    self._save_call(idx, f"st{f['site']:03d}", 0, f["text"], f["ims"] if f["site"] <= 3 else [],
                                    rep.text)
                    a = {"site": f["site"], "send_t": round(f["send_t"], 3), "arr_t": round(t, 3),
                         "age_s": round(t - f["send_t"], 3), "latency_s": round(rep.latency_s, 3),
                         "valid": p is not None, "errors": err[:4], "tokens_in": (rep.usage or {}).get("input_tokens"),
                         "tokens_out": (rep.usage or {}).get("output_tokens"), "cost_usd": round(rep.cost_usd, 6)}
                    ages.append(t - f["send_t"])
                    answers.append(a)
                    if p is None:
                        a["status"] = "invalid"
                        continue
                    asm = p["assessment"]
                    a["assessment"] = {k: asm[k] for k in ("execution_status", "intent_status", "confidence")}
                    a["uncertain"] = SC.is_uncertain(p)
                    tp_now = asm["task_progress"]
                    if style == "F0":
                        eff = self._effective(p, f["last_motion"])
                        a.update(decision=p["decision"], effective=eff)
                        done = self._apply_answer(a, eff, t, st["tcp"], prev_eff, window)
                        prev_eff, a["status"] = eff, "applied"
                        if done == "stop":
                            r = "stop"
                    else:
                        a["decision"], a["evidence"] = p["decision"], p["evidence"][:200]
                        if p["decision"] == "revise" and a["uncertain"]:
                            self.n_uncertain_continue += 1  # uncertain revision -> keep (spec §11)
                            a["decision_effective"] = "keep"
                        if p["decision"] == "keep" or a["uncertain"]:
                            eff = f["committed"]
                            a["effective"] = eff
                            if pending is not None:
                                pending["status"] = "unconfirmed"
                            pending = None
                            if self.committed is not None:
                                keep = {"decision": "edit", "edit": dict(self.committed["edit"], gripper="keep")}
                                self._apply_answer(a, keep, t, st["tcp"], prev_eff, window)
                                prev_eff = keep
                            a["status"] = "keep"
                        else:
                            c = p["command"]
                            eff = c if c["decision"] == "stop" else {"decision": "edit", "edit": c["edit"]}
                            a["effective"] = eff
                            if pending is not None and same_command(pending["effective"], eff):
                                a2 = dict(a)
                                done = self._apply_answer(a2, eff, t, st["tcp"], pending["effective"], window)
                                a.update(scale=a2.get("scale"), flip=a2.get("flip"), applied_cmd=eff, window=window)
                                prev_eff = eff
                                pending["status"], a["status"] = "confirmed", "applied"
                                pending = None
                                if done == "stop":
                                    r = "stop"
                            else:
                                if pending is not None:
                                    pending["status"] = "unconfirmed"
                                a["status"] = "pending"
                                pending = a
                if r == "stop":
                    break
                self._tick()
                lag = (w.status()["t"] - t0) / STAG_RT - (time.perf_counter() - wall0)
                if lag > 0:
                    time.sleep(lag)
        finally:
            for f in inflight + abandoned:  # already paid: wait so the ledger records them; never applied
                try:
                    rep = f["fut"].result()
                except Exception:  # noqa: BLE001 - BudgetStop / network; the caller sees the first one
                    continue
                self._record(len(self.calls), "st_after_end", 0, rep, None, ["arrived after the end"])
            pool.shutdown(wait=True)
        if r == "stop":
            r = self._grace()
        exec_s = w.status()["t"] - t0
        self.extra["stream"] = {"style": style, "answers": answers, "exec_sim_s": round(exec_s, 2),
                                 "wall_s": round(time.perf_counter() - wall0, 2),
                                 "rtf": round(exec_s / max(time.perf_counter() - wall0, 1e-6), 3), "sites": sites,
                                 "t0": round(t0, 3),
                                 "gripper_events": [e["t"] for e in self.events if e["event"] == "gripper_done"]}
        self.end_reason = r

    # ------------------------------------------------------------------ result
    def _result(self, wall_s) -> dict:
        m = self.mon.summary()
        calls = self.calls
        lat = [c["latency_s"] for c in calls if not c["api_error"]]
        conf = [((c.get("parsed") or {}).get("assessment") or {}).get("confidence") for c in calls]
        res = {"seed": self.seed, "task": self.task, "mode": self.mode, "model": getattr(self.model, "name", None),
               "prompt_id": PR.PROMPT_ID, "end_reason": self.end_reason, **m,
               "n_calls": len(calls), "n_repair": sum(c["attempt"] for c in calls),
               "n_invalid": sum(not c["valid"] for c in calls if c["kind"] != "st_after_end"),
               "schema_fail_end": self.end_reason == "schema",
               "latency_s": lat, "cost_usd": round(sum(c["cost_usd"] for c in calls), 6),
               "tokens_in": sum(int((c["usage"] or {}).get("input_tokens") or 0) for c in calls),
               "tokens_cached": sum(int(((c["usage"] or {}).get("input_tokens_details") or {}).get("cached_tokens")
                                        or 0) for c in calls),
               "tokens_out": sum(int((c["usage"] or {}).get("output_tokens") or 0) for c in calls),
               "tokens_reasoning": sum(int(((c["usage"] or {}).get("output_tokens_details") or {})
                                           .get("reasoning_tokens") or 0) for c in calls),
               "decisions": {d: sum(1 for c in calls if (c.get("parsed") or {}).get("decision") == d)
                             for d in ("continue", "edit", "stop", "keep", "revise")},
               "confidence": {k: conf.count(k) for k in ("low", "medium", "high")},
               "n_uncertain_continue": self.n_uncertain_continue, "proprio_conflicts": self.proprio_conflicts,
               "n_clipped": sum(e["event"] == "clipped" for e in self.events),
               "n_timeout": sum(e["event"] == "timeout" for e in self.events),
               "events": self.events, "calls": calls, "sim_t": round(self.w.status()["t"], 2),
               "wall_s": round(wall_s, 1), **self.extra}
        return res

    def _save(self, res):
        if not self.out_dir:
            return
        os.makedirs(self.out_dir, exist_ok=True)
        with open(os.path.join(self.out_dir, "result.json"), "w") as f:
            json.dump(res, f, indent=1, default=_jsonable)
        if self.frames:
            fd = os.path.join(self.out_dir, "frames")
            os.makedirs(fd, exist_ok=True)
            from PIL import Image
            for i, fr in enumerate(self.frames):
                Image.fromarray(fr).save(os.path.join(fd, f"f{i:04d}.jpg"), quality=85)
            try:
                import imageio
                imageio.mimwrite(os.path.join(self.out_dir, "video.mp4"), self.frames, fps=20 / VIDEO_EVERY,
                                 macro_block_size=8)
            except Exception as e:  # noqa: BLE001 - frames stay on disk; the mp4 is a convenience
                res["video_error"] = repr(e)[:200]


def _jsonable(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def run_episode(world, mode, model, seed, task, out_dir=None, video=False, n_sync=N_SYNC) -> dict:
    return Episode(world, mode, model, seed, task, out_dir, video, n_sync).run()


def replay(world, res: dict, executor: str) -> dict:
    """Open-loop replay of a stream episode's logged answers (no model calls): reset the same seed / task, apply
    each executed answer's effective command at its logged arrival time through the chosen executor ('smooth' = the
    live rule with its logged scale / flip, 'immediate' = a straight 8 cm/s move by the delta, replacing the running
    one) and return the TCP motion statistics. Hard-reset determinism makes the smooth replay reproduce the live run
    until the scene reacts differently (it is open loop), so compare motion statistics, not success."""
    ep = Episode(world, res["mode"], None, res["seed"], res["task"])
    ep._setup(smooth=executor == "smooth")
    sg = res["stream"]
    todo = sorted([a for a in sg["answers"] if "applied_cmd" in a], key=lambda a: (a["arr_t"], a["site"]))
    t_end = sg["t0"] + sg["exec_sim_s"]
    while True:
        st = world.status()
        t = st["t"]
        ep.mon.update(st)
        while todo and todo[0]["arr_t"] <= t + 1e-9:
            a = todo.pop(0)
            eff = a["applied_cmd"]
            ep._commit(eff, t, st["tcp"], a.get("scale", 1.0) if executor == "smooth" else 1.0,
                       bool(a.get("flip")) if executor == "smooth" else False, a.get("window"))
        if t >= t_end or ep.mon.off_table:
            break
        ep._tick()
    m = ep.mon.summary()
    return {"executor": executor, "success_open_loop": m["success"], "max_speed": m["max_speed"],
            "jerk_rms": m["jerk_rms"], "jerk_max": m["jerk_max"], "tcp_path": m["tcp_path"]}
