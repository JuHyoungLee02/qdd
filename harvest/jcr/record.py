"""JCR stage-1 data recorder (docs/stage3/jcr_design.md §0-§0-2, §4, §5; prereg_jcr1.md change 1). Pod only (Isaac).

One Isaac process = one scene variant of the E-Couple world (SoloWorld mug_tray, head depth on) on R2_TRAIN layout
seeds (10000-59999; the evaluation's DEV 0-19, CAL and TEST are refused). Per episode:
  commander = the sim-truth planner through the point interface (PtTruth: point + height intent -> the shared resolve
              code -> xyz), exactly the commands OX executed; the command source of the episode (disturb.plan_episode)
              is 'truth' (clean) or 'upper' (the resolved xyz goal + an empirical main-35B error, gripper-intent error,
              call-latency delay, mid-move swaps, pre-issued next commands; upper.py)
  executor  = TruthExec (exec_truth.py): follows the RECEIVED command inside the envelope toward the truth point;
              its per-0.2 s truth chunks are the labels (== the rows it executed)
  disturbances (normal >= half): push / shake / obstacle / slip (disturb.py), applied from privileged state
Written to <out>/<variant>/s<seed>/: result.json (the episode's own record + calls/ with the commander prompts and
images -- reusable for the upper's progress / failure-detection training), ep.json (plan, outcome, failure cause,
disturbance events, G-br tracking stats), ticks.jsonl (20 Hz privileged state, contacts, anomalies, stage),
samples.jsonl (one per 0.2 s decision: inputs + labels), img/k<k>_{head,wrist}.jpg at sample ticks, and a 10 fps
head | wrist mp4 under --vid-root.
python -m harvest.jcr.record --variant standard --seeds 10000-10019 --out /data/harvest/out/jcr/d0
  --vid-root /data/harvest/videos/jcr_d0 --dist /data/harvest/out/jcr/upper_err_dist.json [--scale 0.5]
  [--yield-files a,b] [--owner lane]"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from . import disturb as D
from . import truth as T
from . import upper as U

TRAIN_SEEDS = range(10000, 60000)  # = datagen.gen.R2_TRAIN_SEEDS
VID_EVERY = 2
RECOVER_S = 3.0  # RaC: samples later than this after a disturbance, in a failed episode, are the 'tail' (dropped)
UNREC_END_S = 1.0


def seed_list(spec: str) -> list:
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    bad = [s for s in out if s not in TRAIN_SEEDS]
    if bad:
        raise SystemExit(f"R2_TRAIN seeds {TRAIN_SEEDS.start}-{TRAIN_SEEDS.stop - 1} only (DEV / CAL / TEST never): {bad[:5]}")
    return out


def classes():
    from ..astra_solo.pt_episode import PtEpisode
    from ..astra_solo.pt_truth import PtTruth
    from .exec_truth import TruthExec

    class StepTruth(PtTruth):
        """PtTruth that remembers the truth step it answered (the stage field of the record)."""
        last_step = None

        def ask(self, text, images, meta):
            rep = super().ask(text, images, meta)
            try:
                self.last_step = json.loads(rep.text)["reason"].split(" ", 1)[1]
            except Exception:  # noqa: BLE001
                self.last_step = None
            return rep

    class JcrRecEpisode(PtEpisode):
        plan = dist = rng = None
        img_dir = vid_dir = None

        # ---------------------------------------------------------------- privileged state
        def _priv(self) -> dict:
            st = self.w.status()
            tg = self.info["tgt"]
            return {"t": float(st["t"]), "tcp": np.asarray(st["tcp"], float), "obj": st["obj"],
                    "holding": st["pred"].get(f"holding({tg})") is True,
                    "upright": st["pred"].get(f"upright({tg})") is not False,
                    "touched": set(st.get("gripper_contacts", set())), "grip_w": float(st["grip_w"])}

        def make_exec(self, st):
            w = self.w
            self._ntick, self._nv, self.ticks, self.dist_events = 0, 0, [], []
            self._dstate = {e["kind"]: {"done": False} for e in self.plan["events"]}
            self._unrec_t = None
            ex = TruthExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, w.quat0, self._priv,
                           tgt=self.info["tgt"], place=self.info["place"])
            return ex

        # ---------------------------------------------------------------- commands
        def _role(self, cmd, hold: bool) -> str:
            h = cmd.get("height")
            if h == "lift" or cmd["mode"] == "edit":
                return "lift"
            return "carry" if hold else "approach"

        def _noise(self, role, height, grip, scale):
            if self.plan["src"] == "truth":
                return {"dxyz": [0.0, 0.0, 0.0], "grip": grip, "intent_err": False, "delay_s": 0.0}
            return U.sample_cmd_noise(self.rng, self.dist, role, height, grip, scale)

        def _meta(self, role, noise, goal_true, t):
            m = {"goal_true": goal_true, "role": role, "delay_s": noise["delay_s"], "src": self.plan["src"],
                 "noise": noise}
            if self.rng.uniform() < self.plan["p_swap"]:
                sw = U.sample_cmd_noise(self.rng, self.dist, role, "grasp", "keep", self.plan["scale"])
                m["swap_t"] = t + noise["delay_s"] + float(self.rng.uniform(0.5, 1.5))
                m["swap_dxyz"] = sw["dxyz"]
            m["pre"] = bool(self.rng.uniform() < self.plan["p_pre"])
            return m

        def _execute(self, cmd) -> list:
            st = self.w.status()
            hold = st["pred"].get(f"holding({self.info['tgt']})") is True
            t = float(st["t"])
            if cmd["mode"] == "point":
                res = self.resolve(cmd, st)
                self.last_res = res
                if res.get("goal") is None:
                    return [{"t": round(t, 3), "event": "point_unresolved"}]
                role = self._role(cmd, hold)
                gt = np.asarray(res["goal"], float)
                n = self._noise(role, cmd["height"], cmd["gripper"], self.plan["scale"])
                goal = gt + np.asarray(n["dxyz"], float)
                self.ex.next_meta = self._meta(role, n, gt, t)
                self.ex.stage = self.model.last_step
                self.cmd_log.append({"t": round(t, 3), "stage": self.model.last_step, "cmd": cmd, "role": role,
                                     "goal_true": gt.round(4).tolist(), "goal_cmd": goal.round(4).tolist(),
                                     "noise": n, "swap_t": self.ex.next_meta.get("swap_t"),
                                     "pre": self.ex.next_meta["pre"]})
                return self.ex.go_to(goal, n["grip"], t)
            if cmd["mode"] == "edit":
                n = self._noise("lift", "lift", cmd.get("gripper", "keep"), self.plan["scale"])
                self.ex.next_meta = {"role": "lift", "delay_s": n["delay_s"], "src": self.plan["src"], "noise": n,
                                     "pre": False}
                self.ex.stage = self.model.last_step
                self.cmd_log.append({"t": round(t, 3), "stage": self.model.last_step, "cmd": cmd, "role": "lift",
                                     "noise": n})
            else:
                self.cmd_log.append({"t": round(t, 3), "stage": self.model.last_step, "cmd": cmd})
            self.last_res = None
            return super(PtEpisode, self)._execute(cmd)

        # ---------------------------------------------------------------- disturbances
        def _disturb(self, t):
            env, tg = self.w.env, self.info["tgt"]
            p = self._priv()
            tcp, tp = p["tcp"], np.asarray(p["obj"][tg], float)
            for e in self.plan["events"]:
                s = self._dstate[e["kind"]]
                if s["done"]:
                    continue
                k = e["kind"]
                if k == "push" and not p["holding"] and np.linalg.norm(tcp[:2] - tp[:2]) < e["near_m"]:
                    pos, q = env.object_pose(tg)
                    env.write_object_pose(tg, (pos[0] + e["dxy"][0], pos[1] + e["dxy"][1], pos[2]), tuple(q))
                    s["done"] = True
                    self.dist_events.append({"t": round(t, 3), "kind": k, "dxy": e["dxy"]})
                elif k == "shake":
                    seg = self.ex.seg
                    armed = seg is not None and seg["grip"] == "close" and not p["holding"] and \
                        np.linalg.norm(tcp - self.ex.c_star(p)[0]) < 0.02
                    if s.get("n", 0) == 0 and not armed:
                        continue
                    if t >= s.get("next_t", -1):
                        pos, q = env.object_pose(tg)
                        d = self.rng.uniform(-e["amp_m"], e["amp_m"], size=2)
                        env.write_object_pose(tg, (pos[0] + d[0], pos[1] + d[1], pos[2]), tuple(q))
                        s["n"] = s.get("n", 0) + 1
                        s["next_t"] = t + e["every_s"]
                        self.dist_events.append({"t": round(t, 3), "kind": k, "dxy": d.round(4).tolist()})
                        s["done"] = s["n"] >= e["n"]
                elif k == "obstacle" and p["holding"] and tp[2] > self.mon.start[tg][2] + 0.05:
                    self._obstacle(t)
                    s["done"] = True
                elif k == "slip" and p["holding"]:
                    s.setdefault("t_hold", t)
                    if t - s["t_hold"] >= e["after_lift_s"]:
                        self.ex.slip_until, self.ex.slip_m = t + e["dur_s"], e["open_m"]
                        s["done"] = True
                        self.dist_events.append({"t": round(t, 3), "kind": k, "open_m": e["open_m"],
                                                 "dur_s": e["dur_s"]})
            self.w._st = None

        def _obstacle(self, t):
            from ..sim.perturb import p2_spawn_xy
            from ..sim.scene import OBJ_GEOM, SCENE_SPEC, TABLE_TOP_Z
            env = self.w.env
            k = SCENE_SPEC["p2_object"]
            if k in env.present:
                return
            g = OBJ_GEOM[k]
            mug, _ = env.object_pose(self.info["tgt"])
            tray, _ = env.object_pose(self.info["place"])
            obst = {j: (env.object_pose(j)[0][:2], OBJ_GEOM[j]["footprint_r"]) for j in env.present}
            xy = p2_spawn_xy(int(self.seed), mug[:2], tray[:2], obst, g["footprint_r"])
            z = TABLE_TOP_Z + g["half_extents"][2] + 0.001
            env.write_object_pose(k, (xy[0], xy[1], z))
            env.present.append(k)
            self.dist_events.append({"t": round(t, 3), "kind": "obstacle", "obj": k, "xy": np.round(xy, 4).tolist()})

        # ---------------------------------------------------------------- tick / record
        def _will_sample(self, t) -> bool:
            ex = self.ex
            if ex.wait_until is not None or ex.pending_grip is not None:
                return False
            if ex.pending is not None and t >= ex.pending["t_act"] - 1e-9:
                return True
            return ex.seg is not None and (ex.plan is None or ex.plan[1] >= 4)

        def _tick(self):
            from PIL import Image
            st = self.w.status()
            t = float(st["t"])
            self._disturb(t)
            samp = self._will_sample(t)
            vid = self._ntick % VID_EVERY == 0
            fr = self.w.frame() if (samp or vid) else None
            n0 = len(self.ex.samples)
            super()._tick()
            if len(self.ex.samples) > n0 and fr is not None:
                s = self.ex.samples[-1]
                for cam, key in (("head", "head"), ("wrist", "wrist")):
                    Image.fromarray(np.asarray(fr[key])[..., :3].astype(np.uint8)).save(
                        os.path.join(self.img_dir, f"k{s['k']:05d}_{cam}.jpg"), quality=90)
                s["img"] = f"k{s['k']:05d}"
                s["q"] = np.asarray(self.w.env.arm_q(), float).round(5).tolist()
                s["effort"] = self._effort()
            if vid and fr is not None and self.vid_dir:
                h, wr = np.asarray(fr["head"])[..., :3], np.asarray(fr["wrist"])[..., :3]
                if wr.shape[0] != h.shape[0]:
                    wr = np.asarray(Image.fromarray(wr).resize((int(wr.shape[1] * h.shape[0] / wr.shape[0]),
                                                                h.shape[0])))
                Image.fromarray(np.concatenate([h, wr], 1).astype(np.uint8)).save(
                    os.path.join(self.vid_dir, f"f{self._nv:05d}.jpg"), quality=85)
                self._nv += 1
            p = self._priv()
            contacts = sorted("|".join(sorted(c)) for c in getattr(self.w.pl, "contacts", set()))
            an = self.ex.samples[-1]["anomaly"] if self.ex.samples else []
            self.ticks.append({"k": self._ntick, "t": round(p["t"], 4), "tcp": p["tcp"].round(5).tolist(),
                               "cmd": np.round(self.ex.cmd, 5).tolist(), "q": np.round(self.w.env.arm_q(), 5).tolist(),
                               "grip_w": round(p["grip_w"], 5), "width_cmd": round(self.ex._width_out(t), 5),
                               "effort": self._effort(), "holding": p["holding"], "upright": p["upright"],
                               "touched": sorted(p["touched"]), "contacts": contacts,
                               "obj": {k: np.round(v, 5).tolist() for k, v in p["obj"].items()},
                               "busy": self.ex.busy, "stage": self.ex.stage, "anomaly": an})
            if "unrecoverable" in an:
                self._unrec_t = t if self._unrec_t is None else self._unrec_t
            else:
                self._unrec_t = None
            self._ntick += 1

        def _effort(self) -> float:
            env = self.w.env
            return round(float(env.robot.data.applied_torque[0, env.grip_id]), 4)

        def _check(self):
            r = super()._check()
            if r:
                return r
            if self._unrec_t is not None and self._t() + self.t0 - self._unrec_t >= UNREC_END_S:
                return "unrecoverable"
            return None

    return StepTruth, JcrRecEpisode


def finalize(ep, res: dict, od: str) -> dict:
    """Post-hoc labels on the samples (gripper event row, contact, window) and the episode record."""
    ex = ep.ex
    dt = ex.dt
    grips = [(e["t"], e["event"]) for e in ep.events if e["event"] in ("close", "open")]
    t_dist = [e["t"] for e in ep.dist_events]
    ok = bool(res.get("success"))
    tick_t = np.array([x["t"] for x in ep.ticks]) if ep.ticks else np.zeros(0)
    tcp = np.array([x["tcp"] for x in ep.ticks]) if ep.ticks else np.zeros((0, 3))
    gbr = []
    for s in ex.samples:
        s["grip_event"], s["grip_row"] = "keep", None
        for tg, a in grips:
            r = int(round((tg - s["t"]) / dt))
            if 0 <= r < T.H:
                s["grip_event"], s["grip_row"] = a, r
                break
        s["contact"] = ep.info["tgt"] in s["touched"]
        prev = [td for td in t_dist if td <= s["t"]]
        if prev and s["t"] - prev[-1] < RECOVER_S:
            s["window"] = "recover"
        elif prev and not ok:
            s["window"] = "tail"
        else:
            s["window"] = "normal"
        if len(tick_t):  # G-br (online): the chunk's planned TCP displacement over one decision step (4 rows) vs the
            # measured TCP displacement over the same 4 ticks (displacements: the load sag / IK lag offset cancels)
            j0 = int(np.searchsorted(tick_t, s["t"] - 1e-6))
            j = int(np.searchsorted(tick_t, s["t"] + 4 * dt - 1e-6))
            if j < len(tick_t):
                e = float(np.linalg.norm((tcp[j] - tcp[j0]) - (np.asarray(s["chunk"][3]) - np.asarray(s["p_cmd"])))) * 1e3
                s["gbr_mm"] = round(e, 2)
                gbr.append(e)
    fail = None
    if not ok:
        fail = res.get("end_reason")
        if res.get("fail_stage"):
            fail = f"{res.get('fail_stage')}:{fail}"
    an_all = sorted({a for s in ex.samples for a in s["anomaly"]})
    rec = {"seed": ep.seed, "variant": ep.variant, "plan": ep.plan, "success": ok, "end_reason": res.get("end_reason"),
           "fail_stage": res.get("fail_stage"), "failure": fail, "grasp_lift": res.get("grasp_lift"),
           "n_calls": res.get("n_calls"), "sim_t": res.get("sim_t"), "disturb_events": ep.dist_events,
           "anomalies": an_all, "t_first_anomaly": next((s["t"] for s in ex.samples if s["anomaly"]), None),
           "n_samples": len(ex.samples), "windows": {w: sum(s["window"] == w for s in ex.samples)
                                                      for w in ("normal", "recover", "tail")},
           "gbr_mm": {"n": len(gbr), "p50": round(float(np.median(gbr)), 2) if gbr else None,
                      "p90": round(float(np.percentile(gbr, 90)), 2) if gbr else None},
           "exec_events": ex.log_events, "events": ep.events}
    with open(os.path.join(od, "samples.jsonl"), "w") as f:
        for s in ex.samples:
            f.write(json.dumps(s) + "\n")
    with open(os.path.join(od, "ticks.jsonl"), "w") as f:
        for x in ep.ticks:
            f.write(json.dumps(x) + "\n")
    with open(os.path.join(od, "cmds.jsonl"), "w") as f:
        for c in ep.cmd_log:
            f.write(json.dumps(c, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)) + "\n")
    with open(os.path.join(od, "ep.json"), "w") as f:
        json.dump(rec, f, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="standard", choices=["standard", "dr"])
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--dist", required=True)
    ap.add_argument("--scale", type=float, default=0.75)
    ap.add_argument("--yield-files", default="")
    ap.add_argument("--owner", default="")
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    a = ap.parse_args(argv)
    yf = [f for f in a.yield_files.split(",") if f]
    code = 0
    try:
        from ..astra_solo.world import SoloWorld
        from ..teach_pt.run_closed_l8s import claim, make_mp4, yield_reason
        StepTruth, Ep = classes()
        dist = U.load_dist(a.dist)
        world = SoloWorld(a.variant, depth=True)
        print("WORLD " + json.dumps({"variant": a.variant, "dt": world.dt, "dist": dist.get("sha256"),
                                     "scale": a.scale}), flush=True)
        if abs(world.dt - T.DT) > 1e-6:
            raise SystemExit(f"world dt {world.dt} != truth DT {T.DT}")
        owner = f"{a.owner} pid={os.getpid()}"
        for s in seed_list(a.seeds):
            why = yield_reason(yf)
            if why:
                print("YIELD " + why, flush=True)
                code = 3
                break
            od = os.path.join(a.out, a.variant, f"s{s}")
            if os.path.exists(os.path.join(od, "ep.json")) or not claim(od, owner):
                continue
            m = StepTruth(world)
            ep = Ep(world, m, s, "mug_tray", out_dir=od, video=False, variant=a.variant, iface="pt",
                    stop_calls=a.stop_calls, stop_motion_s=a.stop_motion)
            m.ep = ep
            ep.plan = D.plan_episode(s, a.scale)
            ep.dist = dist
            ep.rng = np.random.default_rng(ep.plan["rng_seed"])
            ep.cmd_log = []
            ep.img_dir = os.path.join(od, "img")
            ep.vid_dir = os.path.join(od, "frames10")
            os.makedirs(ep.img_dir, exist_ok=True)
            os.makedirs(ep.vid_dir, exist_ok=True)
            t0 = time.perf_counter()
            try:
                res = ep.run()
                rec = finalize(ep, res, od)
            except Exception as ex:  # noqa: BLE001 -- one bad episode must not end the lane
                import traceback
                json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]},
                          open(os.path.join(od, "error.json"), "w"))
                print("EP_ERROR " + json.dumps({"seed": s, "err": repr(ex)}), flush=True)
                continue
            mp4 = os.path.join(a.vid_root, a.variant, f"s{s}.mp4")
            ok = make_mp4(ep.vid_dir, mp4)
            if ok:  # the per-sample head / wrist frames in img/ are the kept originals; the composite is the video
                for fn in os.listdir(ep.vid_dir):
                    os.remove(os.path.join(ep.vid_dir, fn))
                os.rmdir(ep.vid_dir)
            os.makedirs(a.vid_root, exist_ok=True)
            with open(os.path.join(a.vid_root, "index.jsonl"), "a") as f:
                f.write(json.dumps({"seed": s, "variant": a.variant, "success": rec["success"],
                                    "failure": rec["failure"], "normal": ep.plan["normal"], "src": ep.plan["src"],
                                    "mp4": mp4 if ok else None}) + "\n")
            print("EP " + json.dumps({"seed": s, "success": rec["success"], "failure": rec["failure"],
                                      "normal": ep.plan["normal"], "src": ep.plan["src"],
                                      "dist": [e["kind"] for e in ep.dist_events], "n_samples": rec["n_samples"],
                                      "gbr": rec["gbr_mm"], "anom": rec["anomalies"],
                                      "wall_s": round(time.perf_counter() - t0, 1)}), flush=True)
        else:
            print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
