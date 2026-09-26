"""One synchronous Astra-solo episode (the robot waits for every answer): observe -> ask (one repair call when the
answer is invalid) -> execute the command completely with the scripted executor -> record the measured result ->
ask again, until success, stop, an off-table drop, MAX_INVALID_RUN invalid call sites in a row, the call limit or the
robot-motion time limit (sim seconds of execution; waiting for answers costs no motion time).

World protocol = harvest/astra_motion/harness.py (reset / task_info / observe / frame / step / status, dt, table_z,
w_open, w_close, quat0). Success, grasp / lift and the failure stage come from the probe's Monitor (same predicates as
the closed-loop evaluation: on(target, place) and released and upright for 1 s).
Every call is saved (prompt, images, reply) with its scoring truth (object centres, holding) -- the truth is never put
in the prompt; it scores the commanded target afterwards (per-call accuracy, and the paid effort comparison).
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

from ..astra_motion.harness import GRACE_S, Monitor, _jsonable
from . import prompts as PR
from . import schema as SC
from .executor import MinJerkExec
from .overlay import head_overlay, png_bytes

MAX_CALLS = 40
MOTION_LIMIT_S = 180.0
MAX_INVALID_RUN = 3
VIDEO_EVERY = 5
KRW_PER_USD = 1450.0


def outcome(e: dict) -> str:
    """History wording of an executor event (measured result of a move)."""
    if e["event"] == "clipped":
        g = e["got"]
        return f"target clipped to the workspace at ({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f})"
    if e["event"] == "reach":
        return f"reached the target (error {e['err_mm']:.0f} mm)"
    if e["event"] == "settled":
        return f"stopped {e['err_mm']:.0f} mm short of the target (arm stopped moving)"
    return f"BLOCKED: stopped {e['err_mm']:.0f} mm from the target (contact or out of reach)"


class Episode:
    def __init__(self, world, model, seed, task, out_dir=None, max_calls=MAX_CALLS, motion_limit_s=MOTION_LIMIT_S,
                 video=False, variant="standard", save_images=True):
        self.w, self.model, self.seed, self.task, self.out_dir = world, model, seed, task, out_dir
        self.max_calls, self.motion_limit_s, self.video, self.variant = max_calls, motion_limit_s, video, variant
        self.save_images = save_images
        self.calls, self.events, self.history, self.frames = [], [], [], []
        self.end_reason = None
        self.t_success = None

    # ------------------------------------------------------------------ model
    def _truth(self) -> dict:
        st = self.w.status()
        tg, pl = self.info["tgt"], self.info["place"]
        hold = st["pred"].get(f"holding({tg})") is True
        return {"tgt_xyz": np.round(st["obj"][tg], 4).tolist(), "place_xyz": np.round(st["obj"][pl], 4).tolist(),
                "holding": hold, "tcp": np.round(np.asarray(st["tcp"], float), 4).tolist(),
                "grip_w": round(float(st["grip_w"]), 4)}

    @staticmethod
    def phase_of(truth: dict, ever_hold: bool) -> str:
        return "carry" if truth["holding"] else ("approach" if not ever_hold else "after")

    def _score(self, cmd: dict | None, truth: dict, phase: str) -> dict | None:
        """xy error (mm) of the commanded TCP target to the object that phase is about (approach: the target object,
        carry: the place object). eef = its position; edit = the executor's resulting target."""
        if not cmd or cmd["mode"] not in ("eef", "edit") or phase == "after":
            return None
        goal = np.asarray(cmd["position_m"] if cmd["mode"] == "eef" else self.ex.target, float)
        ref = np.asarray(truth["tgt_xyz"] if phase == "approach" else truth["place_xyz"], float)
        return {"xy_err_mm": round(float(np.linalg.norm(goal[:2] - ref[:2])) * 1e3, 1),
                "goal": np.round(goal, 4).tolist()}

    def _ask(self, text, images, i):
        err: list = []
        for attempt in range(2):
            t = text if attempt == 0 else text + PR.REPAIR.format(errors="; ".join(err[:6]))
            idx = len(self.calls)
            truth = self._truth()
            rep = self.model.ask(t, images, {"seed": self.seed, "task": self.task, "call": idx, "site": i,
                                             "attempt": attempt, "prompt_id": PR.PROMPT_ID})
            parsed, err = (None, [f"api:{rep.error}"]) if (rep.error and not rep.text) else SC.validate(rep.text)
            rec = {"call": idx, "site": i, "attempt": attempt, "valid": parsed is not None, "errors": err[:8],
                   "latency_s": round(rep.latency_s, 3), "usage": rep.usage, "cost_usd": round(rep.cost_usd, 6),
                   "api_error": rep.error, "model_field": rep.model_field, "t_sim": round(self._t(), 3),
                   "truth": truth, "phase_truth": self.phase_of(truth, self.mon.ever_hold)}
            if parsed is not None:
                rec["parsed"] = parsed
            self.calls.append(rec)
            self._save_call(idx, t, images if (self.save_images and (attempt == 0)) else [], rep.text)
            if parsed is not None:
                return parsed, rec
        return None, rec

    def _save_call(self, idx, text, images, reply):
        if not self.out_dir:
            return
        d = os.path.join(self.out_dir, "calls", f"c{idx:03d}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "prompt.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(d, "reply.txt"), "w", encoding="utf-8") as f:
            f.write(reply or "")
        for j, (label, png) in enumerate(images):
            with open(os.path.join(d, f"img{j + 1}_{label.replace(' ', '_')}.png"), "wb") as f:
                f.write(png)

    # ------------------------------------------------------------------ sim
    def _t(self) -> float:
        return float(self.w.status()["t"]) - self.t0

    def _check(self):
        self.mon.update(self.w.status())
        if self.mon.success:
            if self.t_success is None:
                self.t_success = round(self._t(), 3)
            return "success"
        if self.mon.off_table:
            return "off_table"
        if self._t() >= self.motion_limit_s:
            return "motion_limit"
        return None

    def _tick(self):
        st = self.w.status()
        cmd, width, ev = self.ex.tick(st["t"], st["tcp"])
        for e in ev:
            self.events.append(e)
            if e["event"] == "close":
                self.mon.on_close(st["t"], st["tcp"])
        self.w.step(cmd, width, self.ex.goal_quat)
        if self.video:
            self._vt = getattr(self, "_vt", -1) + 1
            if self._vt % VIDEO_EVERY == 0:
                fr = self.w.frame()
                self.frames.append((fr["head"], fr["wrist"]))

    def _run(self):
        while self.ex.busy:
            r = self._check()
            if r:
                return r
            self._tick()
        return None

    def _grace(self):
        t0 = self._t()
        while self._t() - t0 < GRACE_S:
            r = self._check()
            if r in ("success", "off_table"):
                return r
            self._tick()
        return None

    # ------------------------------------------------------------------ episode
    def _images(self, obs):
        head, drawn = head_overlay(obs.rgb["head"], obs.cams["head"], self.w.table_z, obs.tcp)
        self.drawn = drawn
        return [(PR.IMAGE_LABELS[0], png_bytes(head)), (PR.IMAGE_LABELS[1], png_bytes(obs.rgb["wrist"]))]

    def _execute(self, cmd) -> list:
        st = self.w.status()
        m = cmd["mode"]
        if m == "eef":
            return self.ex.go_to(cmd["position_m"], cmd["gripper"], st["t"])
        if m == "edit":
            return self.ex.move_by(cmd["delta_m"], cmd["gripper"], st["t"], st["tcp"])
        self.ex.grip(cmd["gripper"], st["t"])
        return []

    def run(self) -> dict:
        w = self.w
        w.reset(self.seed, self.task)
        self.info = w.task_info()
        self.mon = Monitor(w, self.info)
        st = w.status()
        self.t0 = float(st["t"])
        self.ex = MinJerkExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, quat0=w.quat0)
        wall0 = time.perf_counter()
        head_static = None
        inv_run, r = 0, None
        for i in range(1, self.max_calls + 1):
            r = self._check()
            if r:
                break
            obs = w.observe()
            if head_static is None:
                head_static = PR.static(self.info, obs.cams["head"], w.table_z, w.w_close)
            text = head_static + PR.now(obs.cams["wrist"], obs.tcp, obs.grip_w, i, self.max_calls, self._t(),
                                        self.motion_limit_s, self.history) + PR.ANSWER
            ims = self._images(obs)
            if "tcp" not in self.drawn:  # the legend describes only what is drawn (pitfall P89)
                text += "\nNOTE: the TCP is outside the head image this time: no ring and no drop line are drawn."
            elif "drop" not in self.drawn:
                text += ("\nNOTE: the table point below the TCP is outside the head image this time: the drop line "
                         "leaves the image and its dot is not visible.")
            p, rec = self._ask(text, ims, i)
            if p is None:
                inv_run += 1
                self.history.append(f"{i}: (invalid answer, nothing executed)")
                if inv_run >= MAX_INVALID_RUN:
                    r = "schema"
                    break
                continue
            inv_run = 0
            cmd = p["command"]
            if cmd["mode"] == "stop":
                self.history.append(f"{i}: stop")
                rec["score"] = None
                r = self._grace() or "stop"
                break
            n_ev = len(self.events)
            self.events += self._execute(cmd)
            rec["score"] = self._score(cmd, rec["truth"], rec["phase_truth"])
            r = self._run()
            st = w.status()
            evs = self.events[n_ev:]
            res = "; ".join(outcome(e) for e in evs if e["event"] in ("clipped", "reach", "settled", "timeout"))
            res = res or "done"
            tcp = st["tcp"]
            self.history.append(f"{i}: {PR.describe(cmd)} -> {res}; TCP now ({tcp[0]:.3f}, {tcp[1]:.3f}, "
                                f"{tcp[2]:.3f}), pad gap {st['grip_w'] * 100:.1f} cm")
            if r:
                break
        else:
            r = self._grace() or "call_limit"
        self.end_reason = r
        return self._result(time.perf_counter() - wall0)

    def _result(self, wall_s) -> dict:
        m = self.mon.summary()
        calls = self.calls
        usd = sum(c["cost_usd"] for c in calls)
        res = {"seed": self.seed, "task": self.task, "variant": self.variant, "model": getattr(self.model, "name", None),
               "prompt_id": PR.PROMPT_ID, "prompt_version": PR.VERSION, "end_reason": self.end_reason, **m,
               "t_success": self.t_success, "n_calls": len(calls), "n_sites": len({c["site"] for c in calls}),
               "n_repair": sum(c["attempt"] for c in calls), "n_invalid": sum(not c["valid"] for c in calls),
               "latency_s": [c["latency_s"] for c in calls if not c["api_error"]], "cost_usd": round(usd, 6),
               "cost_krw": round(usd * KRW_PER_USD, 2),
               "tokens_in": sum(int((c["usage"] or {}).get("input_tokens") or 0) for c in calls),
               "tokens_out": sum(int((c["usage"] or {}).get("output_tokens") or 0) for c in calls),
               "tokens_reasoning": sum(int(((c["usage"] or {}).get("output_tokens_details") or {})
                                           .get("reasoning_tokens") or 0) for c in calls),
               "modes": {k: sum(1 for c in calls if ((c.get("parsed") or {}).get("command") or {}).get("mode") == k)
                         for k in SC.MODES},
               "n_clipped": sum(e["event"] == "clipped" for e in self.events),
               "n_blocked": sum(e["event"] == "timeout" for e in self.events),
               "history": self.history, "events": self.events, "calls": calls, "sim_t": round(self._t(), 2),
               "wall_s": round(wall_s, 1)}
        self._save(res)
        return res

    def _save(self, res):
        if not self.out_dir:
            return
        os.makedirs(self.out_dir, exist_ok=True)
        with open(os.path.join(self.out_dir, "result.json"), "w") as f:
            json.dump(res, f, indent=1, default=_jsonable)
        if self.frames:
            from PIL import Image
            fd = os.path.join(self.out_dir, "frames")
            os.makedirs(fd, exist_ok=True)
            for k, (h, wr) in enumerate(self.frames):
                hh = h.shape[0]
                wr2 = np.asarray(Image.fromarray(wr).resize((int(wr.shape[1] * hh / wr.shape[0]), hh)))
                Image.fromarray(np.concatenate([h, wr2], 1)).save(os.path.join(fd, f"f{k:04d}.jpg"), quality=85)


def run_episode(world, model, seed, task, out_dir=None, **kw) -> dict:
    return Episode(world, model, seed, task, out_dir, **kw).run()
