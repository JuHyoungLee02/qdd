"""E-DEP1 stage 2 closed-loop runner (docs/stage3/prereg_deploy1.md §2 + change 1). Pod only (Isaac).

One Isaac process = one scene variant of the E-Couple world (JcrWorld: SoloWorld mug_tray, head + right wrist
cameras) on the DEV layout seeds 0-19; arms = upper schedules, same seeds:
  S0        ask after the robot is idle (baseline)          S1   ask again as soon as the previous answer landed
  S2x<x>    ask while moving when the expected remaining move time <= x * the running mean upper latency
Upper = the main 35B through the unchanged d-min interface (PtEpisode iface 'd-min': ring head image + right wrist,
the trained request text), served by vLLM; its measured wall latency is applied in SIM time: the request is built from
the scene at t_q, the model is called (the simulator is paused meanwhile) and the answer takes effect at t_q + latency
while the simulator keeps running. Executor = the scripted accel-limited executor (harvest.jcr.exec_truth.TruthExec,
mode 'S': straight to the received command; a new command continues from the current commanded TCP and velocity =
the RTC-style stitch) + the adapter continuation (lift start / small retreat while the upper thinks, NOW.md §1-0e).
Overlap (S1 / S2) only while the in-flight command is a move with gripper keep (its outcome can be written in the
trained 'as if arrived' form: '-> reached the target (error 0 mm); TCP now (goal)'); a gripper action's outcome
(did the pads stop on the object?) is not predictable, so after close / open every schedule waits (change 1).
Stale check when an answer lands (overlap.stale_check): the premise (in-flight move reached, holding unchanged) and
the pointed object's region (head depth at t_q vs now; the destination rides on the object, > 2 cm = dropped).
Per episode: ep.json (success, calls with t_q / latency / mid-motion / stale, wait time, continuity, per-call spatial
error vs the simulator), ticks (10 Hz TCP), 5 fps head | wrist video.
python -m harvest.deploy.runner --arms S0,S1,S2x1.0 --variant standard --seeds 0-19 --url http://x2:8672
  --name q35_dep --out /data/harvest/out/deploy/cl1 --vid-root /data/harvest/videos/deploy_cl1 [--yield-files a,b]"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from . import overlap as O

MAX_CALLS = 40
STOP_CALLS = 30
STOP_MOTION_S = 180.0
VID_EVERY = 4  # 20 Hz ticks -> 5 fps
LAT0 = 2.0


def parse_arm(a: str):
    if a in ("S0", "S1"):
        return a, 1.0
    if a.startswith("S2x"):
        return "S2", float(a[3:])
    raise ValueError(a)


def classes():
    from ..astra_solo import resolve as RS
    from ..astra_solo.episode import outcome
    from ..astra_solo.pt_episode import PtEpisode
    from ..jcr import adapter as AD
    from ..jcr.exec_truth import TruthExec

    class OverlapEpisode(PtEpisode):
        schedule, x = "S0", 1.0
        vid_dir = None

        def make_exec(self, st):
            w = self.w
            self._ntick, self._nv, self.ticks = 0, 0, []

            def priv():
                s = w.status()
                tg = self.info["tgt"]
                return {"t": float(s["t"]), "tcp": np.asarray(s["tcp"], float), "obj": s["obj"],
                        "holding": s["pred"].get(f"holding({tg})") is True,
                        "upright": s["pred"].get(f"upright({tg})") is not False,
                        "touched": set(s.get("gripper_contacts", set())), "grip_w": float(s["grip_w"])}
            return TruthExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, w.quat0, priv, tgt=self.info["tgt"],
                             place=self.info["place"], mode="S", continuation=True)

        # -------------------------------------------------------------- in-flight command bookkeeping
        def _seg_open(self):
            ex = self.ex
            return ex.seg is not None and not ex.seg.get("cont")

        def _t_left(self, st):
            ex = self.ex
            if ex.seg is None or ex.seg.get("cont"):
                return None
            d = float(np.linalg.norm(np.asarray(st["tcp"], float) - ex.seg["goal_cmd"]))
            return d / 0.08 + 0.3

        def _overlap_ok(self):
            """A pre-ask is allowed only during a gripper-keep move answered by the upper (not a continuation)."""
            f = self.inflight
            return f is not None and f["grip"] == "keep" and f["mode"] in ("point", "edit") and not f.get("pre_asked")

        def _provisional(self, st):
            f = self.inflight
            g = f["goal"]
            return (f"{f['site']}: {f['desc']} -> reached the target (error 0 mm); TCP now ({g[0]:.3f}, {g[1]:.3f}, "
                    f"{g[2]:.3f}), pad gap {float(st['grip_w']) * 100:.1f} cm")

        # -------------------------------------------------------------- ask / land
        def _ask_now(self, t, st):
            if self.pending is not None or self.n_sites >= STOP_CALLS:
                return False
            idle = not self.ex.busy and not self._seg_open()
            if idle:
                return True
            if self.schedule == "S0" or not self._overlap_ok():
                return False
            return O.ask_now(self.schedule, self.x, True, False, self._t_left(st), self.lat_est)

        def _submit(self, t, st, statics):
            obs = self.w.observe(depth=True)
            self.depth = (obs.depth or {}).get("head")
            self.cams, self.head = dict(obs.cams), obs.cams["head"]
            self.plane = RS.table_plane(RS.depth_points(self.head, self.depth), self.w.table_z)
            if statics[0] is None:
                from ..astra_solo import nd_prompts as NP
                from ..astra_solo import prompts as V2P
                from ..astra_solo import pt_prompts as PT
                statics[0] = {"pt": PT.static(self.info, self.head, self.w.table_z, self.w.w_close),
                              "v2": V2P.static(self.info, self.head, self.w.table_z, self.w.w_close),
                              **{v: NP.static(self.info, self.head, self.w.w_close, v) for v in NP.VERSIONS}}
            mid = self.ex.busy or self._seg_open()
            self.n_sites += 1
            hist0 = list(self.history)
            if mid:
                self.history.append(self._provisional(st))
                self.inflight["pre_asked"] = True
            text, ims = self._request(obs, self.n_sites, statics[0])
            self.history = hist0
            truth = self._truth()
            rep = self.model.ask(text, ims, {"seed": self.seed, "call": len(self.calls)})
            parsed, err = (None, [f"api:{rep.error}"]) if (rep.error and not rep.text) else self._validate(rep.text)
            lat = float(rep.latency_s or LAT0)
            self.lat_est = 0.7 * self.lat_est + 0.3 * lat
            snap = {"holding": bool(self.holding(st)), "grip_closed": self.ex.width < self.w.w_open - 0.02,
                    "depth": self.depth, "head": self.head, "plane": self.plane, "tcp": np.asarray(st["tcp"], float),
                    "inflight": self.inflight["site"] if (mid and self.inflight) else None, "mid": mid}
            if parsed is not None and (parsed["command"].get("point_2d") is not None):
                snap["region"] = AD.region_points(self.head, self.depth, self.w.table_z,
                                                  parsed["command"]["point_2d"], tcp=st["tcp"])
            rec = {"call": len(self.calls), "site": self.n_sites, "t_q": round(t, 3), "latency_s": round(lat, 3),
                   "mid_motion": bool(mid), "valid": parsed is not None, "errors": err[:4], "truth": truth,
                   "t_sim": round(self._t(), 3), "attempt": 0, "usage": rep.usage, "cost_usd": 0.0,
                   "api_error": rep.error, "model_field": rep.model_field}
            if parsed is not None:
                rec["parsed"] = parsed
            self.calls.append(rec)
            self._save_call(rec["call"], text, ims if self.save_images else [], rep.text)
            self.pending = O.Pending(t, t + lat, parsed, snap)
            self.pending.rec = rec

        def _land(self, t, st):
            p, self.pending = self.pending, None
            rec = p.rec
            if p.answer is None:
                self.inv_run += 1
                rec["outcome"] = "invalid"
                return "schema" if self.inv_run >= 3 else None
            self.inv_run = 0
            cmd = p.answer["command"]
            # stale check: premise of a pre-ask (the in-flight move reached) + object region + holding
            now = {"holding": bool(self.holding(st)), "grip_closed": self.ex.width < self.w.w_open - 0.02}
            if p.snap.get("region") is not None:
                obs = self.w.observe(depth=True)
                d_now = (obs.depth or {}).get("head")
                c = O.region_centroid(p.snap["region"])
                from ..astra_motion import geometry as G
                u, v, z = G.project(obs.cams["head"], c)
                if z > 0 and np.isfinite(u):
                    pt = RS.to_scaled(u, v, obs.cams["head"].W, obs.cams["head"].H)
                    now["region"] = AD.region_points(obs.cams["head"], d_now, self.w.table_z, pt, tcp=st["tcp"])
            keep, why, shift = O.stale_check(p.snap, now)
            if keep and p.snap["mid"]:
                end = self.seg_end.get(p.snap["inflight"])
                if end is not None and end != "reach":
                    keep, why = False, f"premise_{end}"
            rec["stale"] = None if keep else why
            if not keep:
                rec["outcome"] = "dropped"
                self.n_dropped += 1
                return None
            rec["outcome"] = "applied"
            if cmd["mode"] == "stop":
                self._finish_inflight(st, "stopped")
                self.history.append(f"{rec['site']}: stop")
                return "stop"
            self._finish_inflight(st, None)
            if cmd["mode"] == "point":
                save = (self.depth, self.head, self.plane)
                self.depth, self.head, self.plane = p.snap["depth"], p.snap["head"], p.snap["plane"]
                st_q = dict(st, tcp=p.snap["tcp"])
                res = self.resolve(cmd, st_q)
                self.depth, self.head, self.plane = save
                if res.get("goal") is None:
                    self.history.append(f"{rec['site']}: {self._desc(cmd, res)} -> the point does not lead to a target: nothing moved")
                    return None
                goal = np.asarray(res["goal"], float) + (shift if cmd.get("height") in ("above", "grasp") else 0.0)
                rec["resolved"] = dict(res, goal=np.round(goal, 4).tolist(), shift_mm=round(float(np.linalg.norm(shift)) * 1e3, 1))
                rec["score"] = self._score_goal(cmd, goal, st)
                self.ex.next_meta = {"height": cmd["height"], "src": "upper"}
                self.events += self.ex.go_to(goal, cmd["gripper"], t)
                self._open_inflight(rec["site"], cmd, res, goal)
            elif cmd["mode"] == "edit":
                self.ex.next_meta = {"height": "lift", "src": "upper"}
                self.events += self.ex.move_by(cmd["delta_m"], cmd.get("gripper", "keep"), t, st["tcp"])
                self._open_inflight(rec["site"], cmd, None, self.ex.target.copy())
            else:
                self.ex.grip(cmd["gripper"], t)
                self._open_inflight(rec["site"], cmd, None, np.asarray(st["tcp"], float))
            return None

        def _desc(self, cmd, res):
            from ..astra_solo import pt_prompts as PT
            return PT.describe(cmd, res)

        def _open_inflight(self, site, cmd, res, goal):
            self.inflight = {"site": site, "mode": cmd["mode"], "grip": cmd.get("gripper", "keep"),
                             "desc": self._desc(cmd, res) if cmd["mode"] == "point" else self._desc(cmd, None),
                             "goal": np.asarray(goal, float), "n_ev": len(self.events)}

        def _finish_inflight(self, st, forced):
            """Write the in-flight command's history line (its measured result so far) -- the trained format."""
            f = self.inflight
            if f is None:
                return
            evs = self.events[f["n_ev"]:]
            res = "; ".join(outcome(e) for e in evs if e["event"] in ("clipped", "reach", "settled", "timeout"))
            tcp = st["tcp"]
            if not res and not forced:  # a pre-asked answer landed before the move ended: its measured state so far
                err = float(np.linalg.norm(np.asarray(tcp, float) - f["goal"]))
                res = outcome({"event": "reach" if err < 0.008 else "settled", "err_mm": round(err * 1e3, 1)})
            res = res or forced
            self.history.append(f"{f['site']}: {f['desc']} -> {res}; TCP now ({tcp[0]:.3f}, {tcp[1]:.3f}, "
                                f"{tcp[2]:.3f}), pad gap {float(st['grip_w']) * 100:.1f} cm")
            self.inflight = None

        def _score_goal(self, cmd, goal, st):
            if cmd["mode"] != "point" or cmd.get("height") == "lift":
                return None
            ref = st["obj"][self.info["place"] if self.holding(st) else self.info["tgt"]]
            return {"xy_err_mm": round(float(np.linalg.norm(np.asarray(goal[:2]) - np.asarray(ref[:2]))) * 1e3, 1)}

        # -------------------------------------------------------------- loop
        def run(self) -> dict:
            w = self.w
            w.reset(self.seed, self.task)
            self.info = w.task_info()
            from ..astra_motion.harness import Monitor
            self.mon = Monitor(w, self.info)
            st = w.status()
            self.t0 = float(st["t"])
            self.ex = self.make_exec(st)
            self.pending, self.inflight, self.n_sites, self.n_dropped, self.inv_run = None, None, 0, 0, 0
            self.lat_est, self.seg_end = LAT0, {}
            self.no_cmd_s = 0.0
            statics = [None]
            wall0 = time.perf_counter()
            r = None
            while True:
                r = self._check()
                if r:
                    break
                st = w.status()
                t = float(st["t"])
                if self.pending is not None and t >= self.pending.t_due - 1e-9:
                    r = self._land(t, st)
                    if r == "stop":
                        r = self._grace() or "stop"
                        break
                    if r:
                        break
                    st = w.status()
                if self._ask_now(t, st):
                    self._submit(t, st, statics)
                elif self.n_sites >= STOP_CALLS and self.pending is None and not self.ex.busy:
                    r = "stage_cap_calls"
                    break
                if not self.ex.busy and not self._seg_open():
                    self.no_cmd_s += w.dt
                n_ev = len(self.events)
                self._tick_rec()
                for e in self.events[n_ev:]:
                    if e["event"] in ("reach", "settled", "timeout") and self.inflight is not None:
                        self.seg_end[self.inflight["site"]] = e["event"]
                    if e["event"] in ("gripper_done", "reach", "settled", "timeout") and self.inflight is not None \
                            and (self.inflight["grip"] == "keep" or e["event"] == "gripper_done"):
                        self._finish_inflight(w.status(), None)
                self._grip_update(self.events[n_ev:])
            self.end_reason = r
            return self._result(time.perf_counter() - wall0)

        def _tick_rec(self):
            self._ntick += 1
            if self._ntick % 2 == 0:
                s = self.w.status()
                self.ticks.append([round(float(s["t"]), 3)] + np.round(np.asarray(s["tcp"], float), 4).tolist())
            if self.vid_dir and self._ntick % VID_EVERY == 0:
                from PIL import Image
                fr = self.w.frame()
                h, wr = np.asarray(fr["head"])[..., :3], np.asarray(fr["wrist"])[..., :3]
                wr = np.asarray(Image.fromarray(wr).resize((int(wr.shape[1] * h.shape[0] / wr.shape[0]), h.shape[0])))
                Image.fromarray(np.concatenate([h, wr], 1).astype(np.uint8)).save(
                    os.path.join(self.vid_dir, f"f{self._nv:05d}.jpg"), quality=85)
                self._nv += 1
            self._tick()

    return OverlapEpisode


def summarize_ep(ep, res) -> dict:
    calls = ep.calls
    mid = [c for c in calls if c.get("mid_motion")]
    P = np.array([x[1:] for x in ep.ticks]) if ep.ticks else np.zeros((0, 3))
    cont = O.continuity(P, 0.1)
    xy = lambda cs: [c["score"]["xy_err_mm"] for c in cs if c.get("score")]  # noqa: E731
    return {"success": bool(res.get("success")), "end_reason": res.get("end_reason"), "fail_stage": res.get("fail_stage"),
            "sim_t": res.get("sim_t"), "n_calls": len(calls), "n_mid": len(mid), "n_dropped": ep.n_dropped,
            "stale_reasons": [c.get("stale") for c in calls if c.get("stale")], "no_cmd_s": round(ep.no_cmd_s, 2),
            "lat_mean_s": round(float(np.mean([c["latency_s"] for c in calls])), 3) if calls else None,
            "continuity": cont, "xy_rest_mm": xy([c for c in calls if not c.get("mid_motion")]), "xy_mid_mm": xy(mid)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--variant", default="standard", choices=["standard", "dr"])
    ap.add_argument("--seeds", default="0-19")
    ap.add_argument("--url", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--yield-files", default="")
    ap.add_argument("--owner", default="")
    a = ap.parse_args(argv)
    yf = [f for f in a.yield_files.split(",") if f]
    code = 0
    try:
        from ..astra_motion.models import LocalVLM
        from ..jcr.record import make_mp4_fps
        from ..jcr.world import JcrWorld
        from ..teach_pt.run_closed_l8s import claim, yield_reason
        seeds = []
        for part in a.seeds.split(","):
            x, _, y = part.partition("-")
            seeds += list(range(int(x), int(y or x) + 1))
        if any(not 0 <= s <= 19 for s in seeds):
            raise SystemExit("DEV layout seeds 0-19 only")
        Ep = classes()
        vlm = LocalVLM(a.url, a.name, a.name, max_tokens=2000)
        world = JcrWorld(a.variant, depth=True)
        print("WORLD " + json.dumps({"variant": a.variant, "arms": a.arms}), flush=True)
        owner = f"{a.owner} pid={os.getpid()}"
        for s in seeds:
            for arm in a.arms.split(","):
                why = yield_reason(yf)
                if why:
                    print("YIELD " + why, flush=True)
                    code = 3
                    raise StopIteration
                od = os.path.join(a.out, arm, a.variant, f"s{s}")
                if os.path.exists(os.path.join(od, "ep.json")) or not claim(od, owner):
                    continue
                vd = os.path.join(od, "frames")
                os.makedirs(vd, exist_ok=True)
                ep = Ep(world, vlm, s, "mug_tray", out_dir=od, video=False, variant=a.variant, iface="d-min",
                        max_calls=MAX_CALLS, motion_limit_s=STOP_MOTION_S, stop_calls=STOP_CALLS,
                        stop_motion_s=STOP_MOTION_S)
                ep.schedule, ep.x = parse_arm(arm)
                ep.vid_dir = vd
                t0 = time.perf_counter()
                try:
                    res = ep.run()
                except Exception as ex:  # noqa: BLE001
                    import traceback
                    json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]},
                              open(os.path.join(od, "error.json"), "w"))
                    print("EP_ERROR " + json.dumps({"arm": arm, "seed": s, "err": repr(ex)}), flush=True)
                    continue
                row = dict(summarize_ep(ep, res), arm=arm, variant=a.variant, seed=s,
                           wall_s=round(time.perf_counter() - t0, 1))
                mp4 = os.path.join(a.vid_root, arm, a.variant, f"s{s}.mp4")
                row["mp4"] = mp4 if make_mp4_fps(vd, mp4, 5) else None
                if row["mp4"]:
                    for fn in os.listdir(vd):
                        os.remove(os.path.join(vd, fn))
                json.dump(row, open(os.path.join(od, "ep.json"), "w"))
                with open(os.path.join(od, "ticks.json"), "w") as f:
                    json.dump(ep.ticks, f)
                print("EP " + json.dumps({k: row[k] for k in ("arm", "variant", "seed", "success", "end_reason",
                                                              "n_calls", "n_mid", "n_dropped", "no_cmd_s", "wall_s")}),
                      flush=True)
        print("RUN_DONE", flush=True)
    except StopIteration:
        pass
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
