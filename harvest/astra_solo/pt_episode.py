"""Point-then-act and no-depth episodes of E-PT (prereg_pt.md; canon §97 보충 2): the synchronous astra-solo Episode
with another request / schema / command resolution, everything else (executor, monitor, grace, limits, API guards,
per-call saving, sparse video frames) inherited from episode.Episode unchanged. iface:
  pt      astra-solo-pt@v1: v2 overlay image; `point` -> TCP target from the head z-depth + calibration (resolve.py)
  nd-xyz  nd-xyz@v1: ring-only head image, no table height; v2 eef / edit / gripper / stop
  nd-est  nd-est@v1: as nd-xyz, the answer starts with the model's own estimates
  nd-pt   nd-pt@v1: ring-only image, estimates + `point` with the model's own top_z (nd.resolve_est, no depth)
Per call (attempt 0) it saves cams.json and, when the world renders depth, head_depth.npz (float32 z-depth); with
save_v2=True prompt_v2.txt (the astra-solo@v2 request of the same state) and with save_nd=True the three ND requests
(prompt_nd-xyz@v1.txt ...) and img1_head_ring.png -- every arm is compared on byte-identical states.
grip offset (place / above while holding) = TCP height above the table plane (pt: measured from depth; nd-pt: the
model's latest table_z estimate) when a close ends with the pads stopped on something (pad gap > w_close + 5 mm)."""
from __future__ import annotations

import json
import os
import time

import numpy as np

from ..astra_motion.harness import Monitor
from . import nd as ND
from . import nd_prompts as NP
from . import prompts as V2P
from . import pt_prompts as PT
from . import pt_schema as PS
from . import resolve as RS
from .episode import MAX_INVALID_RUN, Episode, outcome
from .executor import MinJerkExec
from .overlay import head_overlay, png_bytes

HOLD_GAP_M = 0.005
IFACES = {"pt": PT.VERSION, "nd-xyz": "nd-xyz@v1", "nd-est": "nd-est@v1", "nd-pt": "nd-pt@v1"}


class PtEpisode(Episode):
    def __init__(self, world, model, seed, task, out_dir=None, allow_eef=False, save_v2=False, save_depth=True,
                 coords="n1000", iface="pt", save_nd=False, **kw):
        super().__init__(world, model, seed, task, out_dir, **kw)
        if iface not in IFACES:
            raise ValueError(iface)
        self.allow_eef, self.save_v2, self.save_depth, self.coords = allow_eef, save_v2, save_depth, coords
        self.iface, self.save_nd = iface, save_nd
        self.version = IFACES[iface]
        self.prompt_id = PT.PROMPT_ID if iface == "pt" else NP.PROMPT_IDS[self.version]
        self.grip_offset = None
        self.plane = None
        self.est_table = None
        self.depth = self.head = self.cams = self.v2_text = None
        self.nd_texts, self.ring_png = {}, None
        self.last_res = None

    # ------------------------------------------------------------------ model
    def _validate(self, text):
        if self.iface == "pt":
            return PS.validate(text, allow_eef=self.allow_eef)
        return ND.validate(text, self.version, allow_eef=self.allow_eef)

    def _ask(self, text, images, i):
        err: list = []
        for attempt in range(2):
            t = text if attempt == 0 else text + PT.REPAIR.format(errors="; ".join(err[:6]))
            idx = len(self.calls)
            truth = self._truth()
            rep = self.model.ask(t, images, {"seed": self.seed, "task": self.task, "call": idx, "site": i,
                                             "attempt": attempt, "prompt_id": self.prompt_id})
            parsed, err = (None, [f"api:{rep.error}"]) if (rep.error and not rep.text) else self._validate(rep.text)
            if parsed is not None and self.coords == "px":
                c = parsed["command"]
                if c.get("point_2d") is not None:  # pixel wording: back to the 0-1000 scale
                    c["point_2d_px"] = list(c["point_2d"])
                    c["point_2d"] = [c["point_2d"][0] / self.head.W * RS.SCALE,
                                     c["point_2d"][1] / self.head.H * RS.SCALE]
            if parsed is not None and (parsed.get("estimates") or {}).get("table_z") is not None:
                self.est_table = parsed["estimates"]["table_z"]
            rec = {"call": idx, "site": i, "attempt": attempt, "valid": parsed is not None, "errors": err[:8],
                   "latency_s": round(rep.latency_s, 3), "usage": rep.usage, "cost_usd": round(rep.cost_usd, 6),
                   "api_error": rep.error, "model_field": rep.model_field, "t_sim": round(self._t(), 3),
                   "truth": truth, "phase_truth": self.phase_of(truth, self.mon.ever_hold)}
            if parsed is not None:
                rec["parsed"] = parsed
            self.calls.append(rec)
            self._save_call(idx, t, images if (self.save_images and (attempt == 0)) else [], rep.text)
            self._api_guard(rep)
            if parsed is not None:
                return parsed, rec
        return None, rec

    def _save_call(self, idx, text, images, reply):
        super()._save_call(idx, text, images, reply)
        if not (self.out_dir and images):
            return
        d = os.path.join(self.out_dir, "calls", f"c{idx:03d}")
        if self.save_depth and self.depth is not None:
            np.savez_compressed(os.path.join(d, "head_depth.npz"), depth=np.asarray(self.depth, np.float32))
        if self.cams is not None:
            with open(os.path.join(d, "cams.json"), "w") as f:
                json.dump({k: c.to_json() for k, c in self.cams.items()}, f)
        if self.save_v2 and self.v2_text is not None:
            with open(os.path.join(d, "prompt_v2.txt"), "w", encoding="utf-8") as f:
                f.write(self.v2_text)
        for v, t in self.nd_texts.items():
            with open(os.path.join(d, f"prompt_{v}.txt"), "w", encoding="utf-8") as f:
                f.write(t)
        if self.save_nd and self.ring_png is not None:
            with open(os.path.join(d, "img1_head_ring.png"), "wb") as f:
                f.write(self.ring_png)

    # ------------------------------------------------------------------ point -> target
    def holding(self, st) -> bool:
        """Robot self-measurement only: the gripper was commanded closed and its pads stopped on something."""
        return self.ex.width < self.w.w_open - 1e-6 and float(st["grip_w"]) > self.w.w_close + HOLD_GAP_M

    def _plane_now(self):
        if self.iface == "nd-pt":
            return self.est_table if self.est_table is not None else self.w.table_z
        return self.plane if self.plane is not None else self.w.table_z

    def resolve(self, cmd: dict, st: dict) -> dict:
        hold = self.holding(st)
        if self.iface == "nd-pt":
            g, info = ND.resolve_est(self.head, cmd, self._plane_now(), st["tcp"], hold, self.grip_offset)
            return dict(info, holding=hold, est_table_z=self._plane_now(),
                        grip_offset=None if self.grip_offset is None else round(self.grip_offset, 4))
        plane = self._plane_now()
        res = None
        if cmd["height"] != "lift":
            res = RS.resolve_point(self.head, self.depth, self.w.table_z, cmd["point_2d"])
            plane = res["plane"]
        if res is not None and res["kind"] == "none":
            return {"kind": "none", "goal": None, "holding": hold}
        goal, notes = RS.target_of(cmd["height"], res, plane, st["tcp"], hold, self.grip_offset)
        return dict(res or {}, goal=[round(float(v), 4) for v in goal], holding=hold, notes=notes,
                    grip_offset=None if self.grip_offset is None else round(self.grip_offset, 4))

    def _execute(self, cmd) -> list:
        if cmd["mode"] != "point":
            self.last_res = None
            return super()._execute(cmd)
        st = self.w.status()
        self.last_res = self.resolve(cmd, st)
        if self.last_res.get("goal") is None:  # the ray misses: nothing to do (reported in the history)
            return [{"t": round(st["t"], 3), "event": "point_unresolved"}]
        return self.ex.go_to(self.last_res["goal"], cmd["gripper"], st["t"])

    def _score(self, cmd, truth, phase):
        if cmd and cmd["mode"] == "point" and phase != "after" and self.last_res and self.last_res.get("goal"):
            goal = np.asarray(self.last_res["goal"], float)
            ref = np.asarray(truth["tgt_xyz"] if phase == "approach" else truth["place_xyz"], float)
            return {"xy_err_mm": round(float(np.linalg.norm(goal[:2] - ref[:2])) * 1e3, 1),
                    "goal": np.round(goal, 4).tolist()}
        return super()._score(cmd, truth, phase)

    def _grip_update(self, evs: list) -> None:
        """After a close, remember how high the TCP was above the plane if the pads stopped on something."""
        st = self.w.status()
        for e in evs:
            if e["event"] == "close" and float(st["grip_w"]) > self.w.w_close + HOLD_GAP_M:
                self.grip_offset = float(e["tcp"][2]) - self._plane_now()

    # ------------------------------------------------------------------ request
    def _request(self, obs, i, statics):
        """-> (text asked, images asked); also prepares the side requests / ring image to save."""
        w = self.w
        nowt = PT.now(obs.cams["wrist"], obs.tcp, obs.grip_w, i, self.max_calls, self._t(), self.motion_limit_s,
                      self.history)
        head_ovl, drawn = head_overlay(obs.rgb["head"], obs.cams["head"], w.table_z, obs.tcp)
        ring, rdrawn = ND.ring_overlay(obs.rgb["head"], obs.cams["head"], obs.tcp)
        self.drawn = drawn
        note = ""
        if "tcp" not in drawn:  # the legend describes only what is drawn (pitfall P89)
            note = "\nNOTE: the TCP is outside the head image this time: no ring and no drop line are drawn."
        elif "drop" not in drawn:
            note = ("\nNOTE: the table point below the TCP is outside the head image this time: the drop line "
                    "leaves the image and its dot is not visible.")
        nd_note = "" if "tcp" in rdrawn else "\nNOTE: the TCP is outside the head image this time: no ring is drawn."
        wrist = (PT.IMAGE_LABELS[1], png_bytes(obs.rgb["wrist"]))
        ovl_ims = [(PT.IMAGE_LABELS[0], png_bytes(head_ovl)), wrist]
        ring_ims = [(PT.IMAGE_LABELS[0], png_bytes(ring)), wrist]
        self.ring_png = ring_ims[0][1] if self.save_nd else None
        pt_text = statics["pt"] + nowt + PT.ANSWER + note
        if self.coords == "px":
            pt_text = PT.px_variant(pt_text, self.head.W, self.head.H)
        self.v2_text = statics["v2"] + nowt + V2P.ANSWER + note if self.save_v2 else None
        nd = {v: statics[v] + nowt + NP.ANSWERS[v] + nd_note for v in NP.VERSIONS}
        self.nd_texts = nd if self.save_nd else {}
        if self.iface == "pt":
            return pt_text, ovl_ims
        return nd[self.version], ring_ims

    # ------------------------------------------------------------------ episode (= Episode.run with the E-PT request)
    def run(self) -> dict:
        w = self.w
        w.reset(self.seed, self.task)
        self.info = w.task_info()
        self.mon = Monitor(w, self.info)
        st = w.status()
        self.t0 = float(st["t"])
        self.ex = MinJerkExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, quat0=w.quat0)
        wall0 = time.perf_counter()
        statics = None
        inv_run, r = 0, None
        for i in range(1, self.max_calls + 1):
            r = self._check()
            if r:
                break
            if self.stop_calls is not None and i > self.stop_calls:
                r = "stage_cap_calls"
                break
            obs = w.observe(depth=True)
            self.depth = (obs.depth or {}).get("head")
            if self.depth is None and (self.iface == "pt" or self.save_nd or self.save_v2):
                raise RuntimeError("this E-PT episode needs the head depth (world built with depth=True)")
            self.cams, self.head = dict(obs.cams), obs.cams["head"]
            if self.depth is not None:
                self.plane = RS.table_plane(RS.depth_points(self.head, self.depth), w.table_z)
            if statics is None:
                statics = {"pt": PT.static(self.info, self.head, w.table_z, w.w_close),
                           "v2": V2P.static(self.info, self.head, w.table_z, w.w_close),
                           **{v: NP.static(self.info, self.head, w.w_close, v) for v in NP.VERSIONS}}
            text, ims = self._request(obs, i, statics)
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
            if self.last_res is not None:
                rec["resolved"] = self.last_res
            rec["score"] = self._score(cmd, rec["truth"], rec["phase_truth"])
            r = self._run()
            st = w.status()
            evs = self.events[n_ev:]
            self._grip_update(evs)
            res = "; ".join(outcome(e) for e in evs if e["event"] in ("clipped", "reach", "settled", "timeout"))
            if any(e["event"] == "point_unresolved" for e in evs):
                res = "the point does not lead to a target: nothing moved"
            res = res or "done"
            tcp = st["tcp"]
            desc = PT.describe(cmd, self.last_res)
            if self.iface.startswith("nd") and self.last_res and self.last_res.get("goal") is not None:
                g = self.last_res["goal"]  # no-depth arms: no measured object top in the history
                desc = (f"point at ({cmd['point_2d'][0]:.0f}, {cmd['point_2d'][1]:.0f}) in image 1 with top_z "
                        f"{cmd['top_z']:.3f}, " if cmd.get("point_2d") is not None else "point, ") + \
                    f"height {cmd['height']}, gripper {cmd['gripper']} [target ({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f})]"
            self.history.append(f"{i}: {desc} -> {res}; TCP now ({tcp[0]:.3f}, {tcp[1]:.3f}, {tcp[2]:.3f}), "
                                f"pad gap {st['grip_w'] * 100:.1f} cm")
            if r:
                break
        else:
            r = self._grace() or "call_limit"
        self.end_reason = r
        return self._result(time.perf_counter() - wall0)

    def _images(self, obs):  # not used by run() (kept for the parent's interface)
        return self._request(obs, 0, None)[1]

    def _save(self, res):
        res["prompt_id"] = self.prompt_id
        res["prompt_version"] = self.version + ("+px" if self.coords == "px" else "")
        modes = PS.MODES if self.iface in ("pt", "nd-pt") else ("eef", "edit", "gripper", "stop")
        res["modes"] = {k: sum(1 for c in self.calls if ((c.get("parsed") or {}).get("command") or {}).get("mode") == k)
                        for k in modes + (("eef",) if self.allow_eef and "eef" not in modes else ())}
        res["n_point_unresolved"] = sum(e["event"] == "point_unresolved" for e in self.events)
        res["interface"] = self.iface
        super()._save(res)


def run_pt_episode(world, model, seed, task, out_dir=None, **kw) -> dict:
    return PtEpisode(world, model, seed, task, out_dir, **kw).run()
