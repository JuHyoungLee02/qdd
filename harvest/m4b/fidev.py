"""FI-DEV generator (Isaac, pod only): DEV seeds 0-29 x 9 conditions (nominal, 5 failure injections, 3 harmless
deviations), run by the BLIND scripted policy (no failure checks, harvest.m4b.spec.next_phase_blind), recorded on the
0.33 s snapshot grid in the pool format plus the measurement fields of E-M4b-meas:

  <out>/<cond>/ep<seed>.jsonl / .npz / .meta.json / img/   cli_pool.write_episode (head + right wrist JPEG q90, native)
  <out>/<cond>/ep<seed>.r1.npz   renderer depth (f16) + camera poses of both cameras (the R1 / V0 input, gen_dev format)
  <out>/<cond>/ep<seed>.fi.json  condition, injection params, t_inject, onset, per-snapshot truth / phase / flags
  <out>/<cond>/ep<seed>.fi.npz   20 Hz stream: t, phase id, arm q / qd / q_target / applied_torque / gravity torque,
                                 gripper width / applied torque, TCP and commanded TCP (table frame), truth (-1 = None)

  IR_ROOT=cyclo ./ir_run.sh env ... /isaac-sim/python.sh -m harvest.m4b.fidev --seeds 0-9 --conds all --out DIR
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import time

import numpy as np

from ..sim import snapshot as SN
from . import spec as FS

PHASE_IDS = {p: i for i, p in enumerate(("approach", "descend", "close", "lift", "carry", "place_descend", "open",
                                         "retreat", "done"))}
HEAD, WRIST = "cam_head", "cam_wrist_right"


def _tf(v):
    return -1 if v is None else int(bool(v))


def make_blind_planner(env, cond: str, par: dict):
    from ..sim.planner import (PLACE_CLEAR_M, OraclePlanner, _slerp_step, W_MAX, REACH_TOL_M, REACH_TOL_FAST_M)
    from ..sim.oracle_state import to_table_frame

    class BlindPlanner(OraclePlanner):
        def __init__(self, env_):
            super().__init__(env_)
            self.cond, self.par = cond, par
            self.t_inject = None
            self.inj_events = []
            self.knocked = False
            self.head_default = None

        def mark(self, what):
            if self.t_inject is None:
                self.t_inject = self.env.sim_time
                self.inj_events.append({"t": round(self.env.sim_time, 4), "what": what, "phase": self.phase})

        def _goal(self):
            goal, v = super()._goal()
            ph, c, p = self.phase, self.cond, self.par
            t_in = self.env.sim_time - self.t_phase0
            if ph == "place_descend":  # blind: aim from the grasp belief, not the live mug pose
                tray = self.env.object_pose("o5")[0]
                gz = (self.grasp_rel or [0.0, 0.0, -(self.mug_h / 2 - 0.018)])[2]
                goal = np.array([tray[0], tray[1], tray[2] + self.tray_h / 2 + PLACE_CLEAR_M + self.mug_h / 2 - gz])
            if c in ("F1_grasp_miss", "F5_stall") and ph == "descend":
                goal[:2] += np.asarray(p["offset_xy"])
                self.mark("descend_offset")
            if c == "F4_place_off" and ph in ("carry", "place_descend"):
                goal[:2] += np.asarray(p["offset_xy"])
                self.mark("place_offset")
            if c == "H3_self_correct" and ph == "carry" and p["t_after_carry"] <= t_in < p["t_after_carry"] + p["dur"]:
                goal[:2] += np.asarray(p["offset_xy"])
                self.mark("detour")
            return goal, v

        def step(self):
            env, t = self.env, self.env.sim_time
            if not self.pred:
                self.observe()
            p = self.pred
            hold_now = p.get("holding(o3)") is True
            self._not_hold = 0 if hold_now else self._not_hold + 1
            mug = self.objs["o3"]
            goal, _ = self._goal()
            tcp, _ = self.tcp_pose()
            tol = REACH_TOL_M if self.phase in ("descend", "place_descend") else REACH_TOL_FAST_M
            sig = dict(reached=bool(np.linalg.norm(goal - tcp) < tol and np.linalg.norm(goal - self.cmd_pos) < 1e-4),
                       t_in_phase=t - self.t_phase0, holding=hold_now,
                       lift_h=float(mug.pos[2] - mug.half_extents[2]),
                       contact_under=p.get("in_contact(o3,o5)") is True)
            new = FS.next_phase_blind(self.phase, sig)
            if new != self.phase:
                if self.phase == "close":
                    self.grasp_rel = (self._mug() - tcp).tolist()
                if new == "retreat":
                    self.retreat_z = tcp[2] + 0.10
                if new == "carry":
                    env.carry_start_xy = self._mug()[:2].copy()
                self.phase, self.t_phase0 = new, t
                self.phase_log.append((t, new))
            t_in = t - self.t_phase0
            goal, v = self._goal()
            d = goal - self.cmd_pos
            n = float(np.linalg.norm(d))
            stp = v * env.step_dt
            self.cmd_pos = goal if n <= stp else self.cmd_pos + d * (stp / n)
            self.cmd_quat = _slerp_step(self.cmd_quat, self.goal_quat, W_MAX * env.step_dt)
            if self.phase in ("close", "lift", "carry", "place_descend"):
                self.cmd_w = self.w_close
            else:
                self.cmd_w = self.w_open
            c, par_ = self.cond, self.par
            if c == "F2_slip_lift" and self.phase in ("lift", "carry", "place_descend"):
                t_lift = next((a for a, b in self.phase_log if b == "lift"), None)
                if t_lift is not None and t - t_lift >= par_["t_after_lift"]:
                    self.mark("grip_loosen")
                    f = min(1.0, (t - t_lift - par_["t_after_lift"]) / par_["ramp_s"])
                    self.cmd_w = self.w_close + f * (par_["w_slip"] - self.w_close)
            if c == "F3_knock_carry" and self.phase == "carry" and not self.knocked and t_in >= par_["t_after_carry"]:
                self.knocked = True
                self.mark("knock")
                self._knock(par_)
            if c == "H1_cam_shake":
                self._shake(t)
            self.history.append((t, to_table_frame(self.cmd_pos, env.table_top_z), self.cmd_w, self.phase))
            q_des = self._ik(self.cmd_pos, self.cmd_quat)
            return np.concatenate([q_des, [self.cmd_w]]).astype(np.float32)

        def _knock(self, par_):
            torch = self.torch
            env = self.env
            a = np.asarray(getattr(env, "carry_start_xy", self._mug()[:2]), float)
            b = env.object_pose("o5")[0][:2]
            u = b - a
            u = u / max(np.linalg.norm(u), 1e-6)
            nrm = np.array([-u[1], u[0]]) * par_["sign"]
            vel = torch.tensor([[nrm[0] * par_["v_lat"], nrm[1] * par_["v_lat"], -par_["v_down"], 0.0, 0.0, 0.0]],
                               dtype=torch.float32, device=env.env.device)
            env.objects["o3"].write_root_velocity_to_sim(vel)

        def _shake(self, t):
            env, par_ = self.env, self.par
            rob = env.robot
            ids = [rob.joint_names.index(n) for n in ("head_joint1", "head_joint2")]
            if self.head_default is None:
                self.head_default = rob.data.default_joint_pos[0, ids].clone()
            t_lift = next((a for a, b in self.phase_log if b == "lift"), None)
            on = t_lift is not None and 0.0 <= t - t_lift - par_["t_after_lift"] < par_["dur"]
            tgt = self.head_default.clone()
            if on:
                self.mark("head_shake")
                s = par_["amp"] * math.sin(2 * math.pi * par_["hz"] * (t - t_lift - par_["t_after_lift"]))
                tgt = tgt + s
            rob.set_joint_position_target(tgt[None], joint_ids=ids)

    return BlindPlanner(env)


def occlude(img: np.ndarray, frac: float, side: str) -> np.ndarray:
    """H2: grey vertical band over `frac` of the image width (left or right side)."""
    out = img.copy()
    w = img.shape[1]
    k = int(round(frac * w))
    if side == "left":
        out[:, :k] = 128
    else:
        out[:, w - k:] = 128
    return out


def run_fi_episode(env, seed: int, cond: str, cams, rc, body, limit_s: float = 60.0, done_grace_s: float = 3.0):
    from ..config import CFG
    from ..perception.geom import cam_pose
    from ..sim.oracle_state import oracle_objects, to_table_frame
    from ..sim.perturb import apply_pending, perturb
    from ..sim.planner import FAIL_STAGE, mug_tray_metrics, randomization_meta, success_from_history

    FS.check_fi_seed(seed)
    kind = FS.seed_kind(seed)
    par = FS.inject_params(seed, cond)
    if env.seed != seed:
        env.set_seed(seed)
    q = env.reset()
    perturb(env, kind, seed)
    pl = make_blind_planner(env, cond, par)
    hist, events, snaps = [], [], []
    stream = {k: [] for k in ("t", "phase", "q", "qd", "q_target", "tau", "tau_grav", "width", "grip_tau", "tcp",
                              "cmd", "truth")}
    prev, pstream = {}, []
    res = {"seed": seed, "kind": kind, "cond": cond, "params": par, "success": False, "stage": None, "info": {},
           "fail_t": None}
    st = {"k": 0}
    ext = {"k": []}
    for n in cams:
        for f in ("depth", "campos", "camR"):
            ext[f"{f}_{n}"] = []
    fi_snaps = []
    t_wall = time.perf_counter()
    rob = env.robot
    ids = env.arm_ids

    def truth_now(pred, grip, contacts):
        gc = {next(iter(c - {"gripper"})) for c in contacts if "gripper" in c and len(c) == 2}
        return FS.truth(pred, FS.contact_open(grip.width_m, gc))

    def take(q_now, boundary):
        t = env.sim_time
        objs, grip, contacts, support = oracle_objects(env)
        ps = copy.deepcopy(pl.ps)
        pred = ps.update(objs, grip, contacts, support)
        obs = {"pred": pred, "near_hyst": [[a, b, bool(v)] for (a, b), v in sorted(ps._near.items())],
               "raw": SN.obs_to_json(objs, grip, contacts, support)}
        s = SN.save_state(env, planner=pl, obs=obs, action=q_now)
        imgs = SN.capture(env, cams)
        occ = False
        if cond == "H2_occlusion":
            t_carry = next((a for a, b in pl.phase_log if b == "carry"), None)
            if t_carry is not None and 0.0 <= t - t_carry - par["t_after_carry"] < par["dur"]:
                imgs[HEAD] = occlude(imgs[HEAD], par["frac"], par["side"])
                occ = True
                pl.mark("occlusion")
        h = pl.history
        moving = len(h) >= 2 and float(np.linalg.norm(np.asarray(h[-1][1]) - np.asarray(h[-2][1]))) > 1e-4
        rec = {"k": st["k"], "t": round(t, 6), "boundary": boundary, "phase": pl.phase,
               "t_in_phase": round(t - pl.t_phase0, 4), "pred": pred, "support": support,
               "present": list(env.present), "tcp": grip.pos.tolist(), "arm_moving": bool(moving),
               "ambiguous_predicates": SN.ambiguous_predicates({i: o.pos for i, o in objs.items()}),
               "changes": [c for c in pstream if c[0] >= t - 3.0] + SN.pred_changes(prev, pred, t),
               "obj_pos": {i: o.pos.tolist() for i, o in objs.items()}, "imgs": imgs}
        snaps.append((rec, s))
        rd = rob.data
        ext["k"].append(st["k"])
        for n in cams:
            ext[f"depth_{n}"].append(env.camera_depth(n).astype(np.float16))
            lp = rd.body_pos_w[0, body[n]].cpu().numpy().astype(float)
            lq = rd.body_quat_w[0, body[n]].cpu().numpy().astype(float)
            p_, R_ = cam_pose(lp, lq, rc.mount_transform(n))
            ext[f"campos_{n}"].append(p_)
            ext[f"camR_{n}"].append(R_)
        tr = truth_now(pred, grip, contacts)
        tcp_t = to_table_frame(pl.tcp_pose()[0], env.table_top_z)
        fi_snaps.append({"k": st["k"], "t": round(t, 6), "phase": pl.phase, "t_in_phase": round(t - pl.t_phase0, 4),
                         "truth": tr, "occluded": occ, "width": float(grip.width_m), "grip_tau": float(grip.effort),
                         "tcp": tcp_t.tolist(), "cmd": to_table_frame(pl.cmd_pos, env.table_top_z).tolist(),
                         "q": rd.joint_pos[0, ids].cpu().numpy().tolist(),
                         "tau": rd.applied_torque[0, ids].cpu().numpy().tolist()})
        st["k"] += 1

    while True:
        t = env.sim_time
        sub = int(round(t / SN.PHYS_DT))
        if sub == SN.snap_sub(st["k"]):
            take(q, True)
        pred = pl.observe()
        pstream += SN.pred_changes(prev, pred, t)
        prev = pred
        hist.append((t, pred))
        # 20 Hz stream (before this step's command)
        rd = rob.data
        stream["t"].append(t)
        stream["phase"].append(PHASE_IDS.get(pl.phase, -1))
        stream["q"].append(rd.joint_pos[0, ids].cpu().numpy())
        stream["qd"].append(rd.joint_vel[0, ids].cpu().numpy())
        stream["q_target"].append(rd.joint_pos_target[0, ids].cpu().numpy())
        stream["tau"].append(rd.applied_torque[0, ids].cpu().numpy())
        stream["tau_grav"].append(rob.root_physx_view.get_gravity_compensation_forces()[0, ids].cpu().numpy())
        stream["width"].append(env.gripper_width())
        stream["grip_tau"].append(env.gripper_effort())
        stream["tcp"].append(to_table_frame(pl.tcp_pose()[0], env.table_top_z))
        stream["cmd"].append(to_table_frame(pl.cmd_pos, env.table_top_z))
        tr = truth_now(pred, pl.grip, pl.contacts)
        stream["truth"].append([_tf(tr[p]) for p in FS.PREDS])
        if pl.objs["o3"].pos[2] < -0.05 and res.get("off_table_t") is None:
            res["off_table_t"] = t  # FI-DEV keeps running (the blind policy does not know; >= 2 s after onset)
        if success_from_history(hist):
            res["success"] = True
            break
        if pl.phase == "done":
            res.setdefault("t_done", t)
            if t - res["t_done"] > done_grace_s:
                res.update(stage="release", info={"reason": "no_success_after_done"})
                break
        if t >= limit_s:
            res.update(stage=FAIL_STAGE.get(pl.phase, "release"), info={"reason": "time_limit", "phase": pl.phase})
            break
        q = pl.step()
        ev = apply_pending(env, t, pl.near_target, pl.phase)
        if ev:
            events.append(ev)
        for n in SN.chunks_to(sub, SN.snap_sub(st["k"])):
            SN.step_partial(env, q, n)
            if n < SN.DECIM and int(round(env.sim_time / SN.PHYS_DT)) == SN.snap_sub(st["k"]):
                take(q, False)
    res["sim_time_s"] = round(env.sim_time, 3)
    res["wall_s"] = round(time.perf_counter() - t_wall, 2)
    res["events"] = events
    res["phases"] = [(round(a, 3), b) for a, b in pl.phase_log]
    res.update(mug_tray_metrics(env))
    randomization_meta(env, res)
    res["planner"] = pl
    res["snaps"] = snaps
    times = [x["t"] for x in fi_snaps]
    t_inj = pl.t_inject
    ons = None
    if cond in FS.FAILURES and t_inj is not None:
        ons = FS.onset(times, [x["phase"] for x in fi_snaps], [x["truth"] for x in fi_snaps], t_inj)
    fi = {"seed": seed, "kind": kind, "cond": cond, "split": FS.seed_split(seed), "fold": FS.cal_fold(seed),
          "params": par, "t_inject": t_inj, "inj_events": pl.inj_events, "onset": ons,
          "success": res["success"], "stage": res["stage"], "info": res["info"], "sim_time_s": res["sim_time_s"],
          "phases": res["phases"], "p_events": events, "snaps": fi_snaps}
    return res, fi, ext, stream


def effort_limits(env):
    r = env.robot
    for name in ("joint_effort_limits", "joint_effort_limit"):
        v = getattr(r.data, name, None)
        if v is not None:
            return v[0].cpu().numpy().tolist()
    return r.root_physx_view.get_dof_max_forces()[0].cpu().numpy().tolist()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-29")
    ap.add_argument("--conds", default="all")
    ap.add_argument("--out", default="/data/harvest/m4b/fidev")
    a = ap.parse_args(argv)
    assert a.out.startswith("/data/harvest/"), "every file under /data/harvest"
    lo, _, hi = a.seeds.partition("-")
    seeds = [FS.check_fi_seed(s) for s in range(int(lo), int(hi or lo) + 1)]
    conds = FS.CONDITIONS if a.conds == "all" else tuple(a.conds.split(","))
    for c in conds:
        if c not in FS.CONDITIONS:
            raise SystemExit(f"unknown condition {c}")

    from ..cli_pool import write_episode
    from ..sim.scene import RECORD_CAMERAS, load_realcam, make_env

    cams = tuple(RECORD_CAMERAS)
    rc = load_realcam()
    env = None
    for s in seeds:
        for c in conds:
            d = f"{a.out}/{c}"
            os.makedirs(d, exist_ok=True)
            if os.path.exists(f"{d}/ep{s}.fi.json"):
                continue
            if env is None:
                env = make_env(s, headless=True, cameras=cams, depth=True)
                body = {n: env.robot.body_names.index(rc.CAMERA_SPECS[n]["parent"]) for n in cams}
                json.dump({"effort_limits": effort_limits(env), "joint_names": env.robot.joint_names,
                           "arm_ids": env.arm_ids, "grip_id": env.grip_id},
                          open(f"{a.out}/robot_meta.json", "w"), indent=1)
            res, fi, ext, stream = run_fi_episode(env, s, c, cams, rc, body)
            meta = write_episode(res, d, cams)
            np.savez_compressed(f"{d}/ep{s}.r1.npz", **{k: np.asarray(v) for k, v in ext.items()})
            np.savez_compressed(f"{d}/ep{s}.fi.npz", **{k: np.asarray(v) for k, v in stream.items()})
            with open(f"{d}/ep{s}.fi.json", "w") as f:
                json.dump(SN._jsonable(fi), f)
            print("EP " + json.dumps({"seed": s, "cond": c, "kind": fi["kind"], "success": fi["success"],
                                      "t_inject": fi["t_inject"], "onset": fi["onset"],
                                      "sim_time_s": fi["sim_time_s"], "wall_s": meta["wall_s"],
                                      "n": len(fi["snaps"])}), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
