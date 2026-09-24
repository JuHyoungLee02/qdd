"""T13 snapshot pool (E §1.5, §2A.3). Isaac parts run on the pod only (python.sh -m harvest.cli_pool ...).

  restore-test --seed 0 [--points 10] --out DIR      DEV seed: restore drift at 10 snapshot points (Step 1)
  pool --seeds 2000-2039 --out DIR --confirm-pool     POOL episodes (seed-determined P0/P1/P2), images + state
  check --out DIR                                     counts, intervals, oversampling, ambiguity, split

Seeds: only DEV 0-29 and POOL 2000-2119 (snapshot.check_seed); TEST / TEST-P5 are refused before anything runs.
Per POOL episode: ep<seed>.npz (full sim state of every continuous snapshot), ep<seed>.jsonl (one line per
continuous snapshot: text state, oracle answers, ambiguous, decision / oversample flags, weights, image paths,
FSM + observation state), img/ep<seed>/k###_<cam>.jpg (672x376 head, wrist; JPEG q90), ep<seed>.meta.json.
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import time

import numpy as np

from .sim import snapshot as S


def _seeds(spec: str):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    for s in out:
        S.check_seed(s)
    return out


def _utc():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


# ------------------------------------------------------------------------------------ one episode (Isaac)
def run_snapshot_episode(env, seed: int, kind: str, cams=(), on_snapshot=None, limit_s: float = 60.0,
                         done_grace_s: float = 3.0) -> dict:
    """run_episode (planner.py) with continuous snapshots on the exact 0.33 s grid. on_snapshot(env, pl, rec, s,
    imgs) may restore state; it returns True when the planner must use the snapshot observation next (the
    sensors are stale after a write)."""
    from .config import CFG
    from .sim.oracle_state import oracle_objects
    from .sim.perturb import apply_pending, perturb
    from .sim.planner import FAIL_STAGE, SUCCESS_KEYS, OraclePlanner, mug_tray_metrics, success_from_history

    S.check_seed(seed)
    if env.seed != seed:
        env.set_seed(seed)
    q = env.reset()
    perturb(env, kind, seed)
    pl = OraclePlanner(env)
    hist, events, snaps, stream = [], [], [], []
    prev = {}
    res = {"seed": seed, "kind": kind, "success": False, "stage": None, "info": {}, "fail_t": None}
    st = {"k": 0, "skip_obs": None}
    t_wall = time.perf_counter()

    def take(q_now, boundary):
        t = env.sim_time
        objs, grip, contacts, support = oracle_objects(env)
        ps = copy.deepcopy(pl.ps)
        pred = ps.update(objs, grip, contacts, support)
        obs = {"pred": pred, "near_hyst": [[a, b, bool(v)] for (a, b), v in sorted(ps._near.items())],
               "raw": S.obs_to_json(objs, grip, contacts, support)}
        s = S.save_state(env, planner=pl, obs=obs, action=q_now)
        imgs = S.capture(env, cams) if cams else {}
        h = pl.history
        moving = len(h) >= 2 and float(np.linalg.norm(np.asarray(h[-1][1]) - np.asarray(h[-2][1]))) > 1e-4
        rec = {"k": st["k"], "t": round(t, 6), "boundary": boundary, "phase": pl.phase,
               "t_in_phase": round(t - pl.t_phase0, 4), "pred": pred, "support": support,
               "present": list(env.present), "tcp": grip.pos.tolist(), "arm_moving": bool(moving),
               "ambiguous_predicates": S.ambiguous_predicates({i: o.pos for i, o in objs.items()}),
               "changes": [c for c in stream if c[0] >= t - 3.0] + S.pred_changes(prev, pred, t),
               "obj_pos": {i: o.pos.tolist() for i, o in objs.items()}}
        snaps.append((rec, s))
        st["k"] += 1
        if on_snapshot and on_snapshot(env, pl, rec, s, imgs):
            st["skip_obs"] = obs
        elif imgs:
            rec["imgs"] = imgs

    while True:
        t = env.sim_time
        sub = int(round(t / S.PHYS_DT))
        if sub == S.snap_sub(st["k"]):
            take(q, True)
        if st["skip_obs"] is not None:  # a restore happened at this boundary: use the snapshot observation
            o = st["skip_obs"]
            pl.pred, pl.ps._near = dict(o["pred"]), {(a, b): v for a, b, v in o["near_hyst"]}
            pl.objs, pl.grip, pl.contacts, pl.support = S.obs_from_json(o["raw"])
            pl.near_target = bool(np.linalg.norm(pl.grip.pos - pl.objs["o3"].pos) < CFG.near_in_m)
            pred, st["skip_obs"] = pl.pred, None
        else:
            pred = pl.observe()
        stream += S.pred_changes(prev, pred, t)
        prev = pred
        hist.append((t, pred))
        if pl.objs["o3"].pos[2] < -0.05:
            res.update(stage=FAIL_STAGE.get(pl.phase, "release"), info={"reason": "off_table", "phase": pl.phase},
                       fail_t=t)
            break
        if success_from_history(hist):
            res["success"] = True
            break
        if pl.phase == "fail":
            res.update(stage=pl.fail_stage, info=pl.fail_info, fail_t=pl.phase_log[-1][0])
            break
        if pl.phase == "done":
            res.setdefault("t_done", t)
            if t - res["t_done"] > done_grace_s:
                res.update(stage="release", info={"reason": "no_success_after_done",
                                                  **{k: pred.get(k) for k in SUCCESS_KEYS}})
                break
        if t >= limit_s:
            res.update(stage=FAIL_STAGE.get(pl.phase, "release"), info={"reason": "time_limit", "phase": pl.phase})
            break
        q = pl.step()
        ev = apply_pending(env, t, pl.near_target, pl.phase)
        if ev:
            events.append(ev)
        for n in S.chunks_to(sub, S.snap_sub(st["k"])):
            S.step_partial(env, q, n)
            if n < S.DECIM and int(round(env.sim_time / S.PHYS_DT)) == S.snap_sub(st["k"]):
                take(q, False)  # mid-step: the rest of this env step refreshes the sensors
    res["sim_time_s"] = round(env.sim_time, 3)
    res["wall_s"] = round(time.perf_counter() - t_wall, 2)
    res["events"] = events
    res["phases"] = [(round(a, 3), b) for a, b in pl.phase_log]
    res.update(mug_tray_metrics(env))
    res["planner"] = pl
    res["snaps"] = snaps
    return res


def attach_oracle(res: dict) -> None:
    """Oracle answers for every continuous snapshot k that has a full step [t_k, t_k + T_c] in the history."""
    from .config import CFG
    from .sim.planner import decision_points
    pl = res["planner"]
    dps = decision_points(pl)
    ts = np.array([h[0] for h in pl.history])
    P = np.array([np.asarray(h[1], float) for h in pl.history])

    def phase_at(t):
        j = int(np.searchsorted(ts, t + 1e-9, side="right")) - 1
        return pl.history[max(j, 0)][3]

    def pos(t):
        return np.array([np.interp(t, ts, P[:, i]) for i in range(3)])

    for rec, s in res["snaps"]:
        k = rec["k"]
        if k >= len(dps):
            rec["oracle"] = None
            continue
        t, ds, a = dps[k]
        assert abs(t - rec["t"]) < 1e-6, (t, rec["t"])
        ph0, ph1 = phase_at(t), phase_at(t + CFG.T_c)
        tgt = S.oracle_target(ph0)
        pred = rec["pred"]
        raw_c = [set(c) for c in s["obs"]["raw"]["contacts"]]
        contact = bool(pred.get("holding(o3)")) or {"gripper", tgt} in raw_c
        dist_t = float(np.linalg.norm(np.asarray(rec["tcp"]) - np.asarray(rec["obj_pos"].get(tgt, rec["tcp"]))))
        near_contact = ph0 in S.NEAR_CONTACT_PHASES or dist_t <= CFG.near_in_m
        d = pos(t + CFG.T_c) - pos(t)
        fine = "done" if ph1 != ph0 else S.fine_axis(d)
        dist_ids = ("o8", "o9", "o10")
        forb = (pred.get("upright(o3)") is False) or any(
            (("gripper" in c) or ("o3" in c)) and bool(c & set(dist_ids)) for c in raw_c)
        sid = S.stage_of(ph0)
        stage_done = bool(pred.get("holding(o3)") and pred.get("lifted(o3)")) if sid == "S1" else \
            bool(pred.get("on(o3,o5)"))
        rec["ds_id"] = ds
        rec["oracle"] = dict(a, target=tgt, phase_choice=S.oracle_phase_choice(ph0, ph1), fine_dir=fine,
                             near_contact=bool(near_contact), fine_mag=0.01 if contact else 0.02,
                             progress=S.oracle_progress(t, res["fail_t"], res["events"]),
                             stage=sid, stage_done=stage_done, forbidden=bool(forb),
                             cmd_disp_m=[round(float(v), 5) for v in d])


# --------------------------------------------------------------------------------------- restore test
def restore_test(seed: int, n_points: int, out: str, frames: bool):
    """Step 1 of T13: at n_points snapshots of DEV seed `seed` (P0) — hold the saved target 0.5 s on the original
    state (reference), restore once, hold again, compare object positions; then restore once more and continue the
    episode. The whole episode is compared with a plain run of the same seed. Head-camera frames at the snapshot,
    after the restore and after both 0.5 s holds are compared pixel-wise (memory rule: verify with frames)."""
    from .sim.scene import make_env
    if seed not in S.DEV_SEEDS:
        raise SystemExit("restore-test: DEV seeds only")
    os.makedirs(out, exist_ok=True)
    cams = ("cam_head",)
    env = make_env(seed, headless=True, cameras=cams, depth=False)
    # plain reference run (no restores)
    plain = run_snapshot_episode(env, seed, "P0")
    plain_pos = {r["k"]: r["obj_pos"] for r, _ in plain["snaps"]}
    K = len(plain["snaps"])
    picks = [int(x) for x in np.linspace(2, K - 4, n_points).round()]
    rows, sheets = [], []

    snap_states, snap_imgs = {}, {}

    def on_snap(env_, pl, rec, s, imgs):
        k = rec["k"]
        snap_states[k], snap_imgs[k] = s, imgs["cam_head"]
        if k not in picks:
            return False
        sub = int(round(rec["t"] / S.PHYS_DT))
        first = (S.DECIM - sub % S.DECIM) or S.DECIM
        img0 = imgs["cam_head"]
        ref = S.hold_trace(env_, s["action"], 0.5, first_chunk=first)
        img_ref = S.capture(env_, cams)["cam_head"]
        S.restore_state(env_, s)
        img_rs = S.capture(env_, cams)["cam_head"]  # right after the write, before any physics step
        tr = S.hold_trace(env_, s["action"], 0.5, first_chunk=first)
        img_rs_end = S.capture(env_, cams)["cam_head"]
        dev_ref = max(max(float(np.linalg.norm(a[o] - b[o])) for o in a) for (_, a), (_, b) in zip(tr, ref))
        per_obj = {o: round(max(float(np.linalg.norm(a[o] - b[o])) for (_, a), (_, b) in zip(tr, ref)) * 1e3, 4)
                   for o in env_.present}
        rest = [o for o in env_.present if float(np.linalg.norm(s["obj_vel"][o][:3])) < 0.01]
        settle = {o: round(max(float(np.linalg.norm(a[o] - s["obj_pose"][o][:3])) for _, a in tr) * 1e3, 4)
                  for o in rest}
        row = {"k": k, "t": rec["t"], "phase": rec["phase"], "boundary": rec["boundary"],
               "holding": rec["pred"].get("holding(o3)"),
               "restore_drift_vs_ref_mm": round(dev_ref * 1e3, 4), "per_object_vs_ref_mm": per_obj,
               "rest_objects_settle_mm": settle,
               "moving_objects": [o for o in env_.present if o not in rest],
               "img_diff_at_restore": round(float(np.abs(img_rs.astype(int) - img0.astype(int)).mean()), 3),
               "img_diff_after_hold": round(float(np.abs(img_rs_end.astype(int) - img_ref.astype(int)).mean()), 3),
               "img_maxdiff_after_hold": int(np.abs(img_rs_end.astype(int) - img_ref.astype(int)).max())}
        # image-state sync (frames, not numbers only): (a) a second render of the same state must not move the
        # mug (a one-frame annotator lag would), (b) writing the state 0.33 s earlier must move it in the image.
        c0, n0 = red_centroid(img0)
        img_again = S.capture(env_, cams)["cam_head"]  # state = restored snapshot + 0.5 s hold; baseline pair
        img_again2 = S.capture(env_, cams)["cam_head"]
        row["render_noise_mean"] = round(float(np.abs(img_again.astype(int) - img_again2.astype(int)).mean()), 3)
        row["mug_centroid_repeat_px"] = _px(red_centroid(img_again)[0], red_centroid(img_again2)[0])
        prev_s = snap_states.get(k - 1)
        if prev_s is not None:
            S.restore_state(env_, prev_s)
            cp, _ = red_centroid(S.capture(env_, cams)["cam_head"])
            row["mug_px_shift_after_writing_prev_state"] = _px(cp, c0)
            row["mug_px_shift_prev_snapshot_image"] = _px(red_centroid(snap_imgs[k - 1])[0], c0)
        row["mug_centroid"], row["mug_red_px"] = c0, n0
        rows.append(row)
        print("RT " + json.dumps(row), flush=True)
        if len(sheets) < 3 and (rec["phase"] in ("close", "lift", "carry") or not sheets):
            sheets.append((k, rec["phase"], img0, img_rs, img_ref, img_rs_end))
        S.restore_state(env_, s)  # continue the episode from the snapshot
        return rec["boundary"]

    tested = run_snapshot_episode(env, seed, "P0", cams=cams, on_snapshot=on_snap)
    div = []
    for r, _ in tested["snaps"]:
        if r["k"] in plain_pos:
            div.append(max(float(np.linalg.norm(np.asarray(r["obj_pos"][o]) - np.asarray(plain_pos[r["k"]][o])))
                           for o in r["obj_pos"]))
    summ = {"seed": seed, "points": len(rows), "utc": _utc(),
            "max_restore_drift_vs_ref_mm": max(r["restore_drift_vs_ref_mm"] for r in rows),
            "max_rest_settle_mm": max([v for r in rows for v in r["rest_objects_settle_mm"].values()] or [0.0]),
            "plain": {k: plain[k] for k in ("success", "sim_time_s", "mug_tray_xy_mm", "wall_s")},
            "with_restores": {k: tested[k] for k in ("success", "sim_time_s", "mug_tray_xy_mm", "wall_s")},
            "episode_obj_divergence_max_mm": round(max(div) * 1e3, 3) if div else None,
            "episode_obj_divergence_at_last_mm": round(div[-1] * 1e3, 3) if div else None,
            "n_snapshots": len(tested["snaps"]),
            "intervals": S.interval_stats([r["t"] for r, _ in tested["snaps"]]),
            "rtf_plain": round(plain["sim_time_s"] / max(plain["wall_s"], 1e-6), 3)}
    print("RT_SUMMARY " + json.dumps(summ), flush=True)
    with open(f"{out}/restore_test_seed{seed}.json", "w") as f:
        json.dump({"summary": summ, "points": rows}, f, indent=1)
    if frames and sheets:
        _save_sheet(sheets, f"{out}/restore_frames_seed{seed}.png")


def red_centroid(img):
    """Pixel centroid of the red mug (renders light red: R high, G and B well below R)."""
    x = img.astype(int)
    m = (x[..., 0] > 150) & (x[..., 0] - x[..., 1] > 70) & (x[..., 0] - x[..., 2] > 70)
    if m.sum() < 30:
        return None, int(m.sum())
    vs, us = np.nonzero(m)
    return [round(float(us.mean()), 2), round(float(vs.mean()), 2)], int(m.sum())


def _px(a, b):
    return None if a is None or b is None else round(float(np.hypot(a[0] - b[0], a[1] - b[1])), 2)


def _save_sheet(sheets, path):
    from PIL import Image, ImageDraw
    w, h = 336, 188
    names = ("snapshot", "restored (t)", "orig +0.5 s hold", "restored +0.5 s hold")
    sheet = Image.new("RGB", (w * 4, h * len(sheets)))
    for r, (k, ph, *ims) in enumerate(sheets):
        for c, im in enumerate(ims):
            x = Image.fromarray(im).resize((w, h))
            ImageDraw.Draw(x).text((5, 5), f"k{k} {ph}: {names[c]}", fill=(255, 255, 0))
            sheet.paste(x, (c * w, r * h))
    sheet.save(path, optimize=True)


# -------------------------------------------------------------------------------------------- pool
def write_episode(res: dict, out: str, cams) -> dict:
    from PIL import Image

    from .sim.planner import PHASE_TIMEOUT_S
    from .sim.snapshot import pack_states, pool_split, select_decision, text_state
    seed = res["seed"]
    attach_oracle(res)
    cands = [i for i, (r, _) in enumerate(res["snaps"]) if r["oracle"] is not None]
    sel = select_decision([bool(res["snaps"][i][0]["ambiguous_predicates"]) for i in cands],
                          rng=np.random.default_rng([seed, 29]))
    chosen = {cands[i]: (o, w) for i, o, w in sel}
    img_dir = f"{out}/img/ep{seed}"
    os.makedirs(img_dir, exist_ok=True)
    states = [s for _, s in res["snaps"]]
    obj_ids = list(states[0]["obj_pose"])
    arrays, js = pack_states(states, obj_ids)
    np.savez_compressed(f"{out}/ep{seed}.npz", **arrays)
    split = pool_split(seed)
    with open(f"{out}/ep{seed}.jsonl", "w") as f:
        for i, ((rec, s), j) in enumerate(zip(res["snaps"], js)):
            paths = {}
            for cam, im in rec.pop("imgs", {}).items():
                p = f"{img_dir}/k{rec['k']:03d}_{cam}.jpg"
                Image.fromarray(im).save(p, quality=90)
                paths[cam] = os.path.relpath(p, out)
            ch = [(tc, p, a, b) for tc, p, a, b in rec["changes"]]
            txt = text_state(rec["t"], rec["phase"], rec["t_in_phase"], PHASE_TIMEOUT_S.get(rec["phase"], 60.0),
                             rec["pred"], rec["present"], rec["support"], bool(rec["pred"].get("gripper_open")),
                             bool(rec["pred"].get("holding(o3)")), rec["arm_moving"], ch)
            ov, w = chosen.get(i, (False, 0.0))
            line = {"seed": seed, "kind": res["kind"], "split": split, "k": rec["k"], "t": rec["t"],
                    "ds_id": rec.get("ds_id"), "decision": i in chosen, "oversampled": bool(ov),
                    "w_natural": round(float(w), 6) if i in chosen else None,
                    "w_oversample": 1.0 if i in chosen else None,
                    "ambiguous": bool(rec["ambiguous_predicates"]), "ambiguous_predicates": rec["ambiguous_predicates"],
                    "phase": rec["phase"], "boundary_step": rec["boundary"], "text_state": txt,
                    "oracle": rec["oracle"], "pred": rec["pred"], "images": paths, "state": j}
            f.write(json.dumps(S._jsonable(line)) + "\n")
    meta = {k: v for k, v in res.items() if k not in ("planner", "snaps")}
    meta.update(split=split, n_snapshots=len(res["snaps"]), n_candidates=len(cands), utc=_utc(), cams=list(cams))
    with open(f"{out}/ep{seed}.meta.json", "w") as f:
        json.dump(S._jsonable(meta), f, indent=1)
    return meta


def pool(seeds, out: str):
    from .sim import scene
    from .sim.scene import make_env
    os.makedirs(out, exist_ok=True)
    cams = tuple(getattr(scene, "RECORD_CAMERAS", ("cam_head",)))
    env = None
    for s in seeds:
        if os.path.exists(f"{out}/ep{s}.meta.json"):
            continue  # resumable
        kind = S.pool_kind(s)
        if env is None:
            env = make_env(s, headless=True, cameras=cams, depth=False)
        res = run_snapshot_episode(env, s, kind, cams=cams)
        meta = write_episode(res, out, cams)
        print("EP " + json.dumps({k: meta[k] for k in ("seed", "kind", "split", "success", "stage", "sim_time_s",
                                                       "wall_s", "n_snapshots")}), flush=True)


def check(out: str) -> dict:
    eps = sorted(glob.glob(f"{out}/ep*.jsonl"))
    n_dec = n_ov = n_amb_all = n_all = n_amb_dec = 0
    iv, splits, kinds, succ, missing_img = [], {}, {}, 0, 0
    for p in eps:
        lines = [json.loads(x) for x in open(p)]
        seed = lines[0]["seed"]
        meta = json.load(open(p.replace(".jsonl", ".meta.json")))
        succ += bool(meta["success"])
        sp = {x["split"] for x in lines}
        assert len(sp) == 1, f"ep{seed}: mixed split {sp}"
        splits[sp.pop()] = splits.get(lines[0]["split"], 0) + 1
        kinds[lines[0]["kind"]] = kinds.get(lines[0]["kind"], 0) + 1
        t = [x["t"] for x in lines]
        d = np.diff(t)
        iv += d.tolist()
        orc = [x for x in lines if x["oracle"] is not None]
        n_all += len(orc)
        n_amb_all += sum(x["ambiguous"] for x in orc)
        dec = [x for x in lines if x["decision"]]
        n_dec += len(dec)
        n_ov += sum(x["oversampled"] for x in dec)
        n_amb_dec += sum(x["ambiguous"] for x in dec)
        for x in lines:
            for rel in x["images"].values():
                missing_img += not os.path.exists(f"{out}/{rel}")
    iv = np.array(iv) if iv else np.zeros(1)
    r = {"episodes": len(eps), "success": succ, "decision_snapshots": n_dec,
         "oversampled_frac": round(n_ov / max(n_dec, 1), 4),
         "ambiguous_frac_decision": round(n_amb_dec / max(n_dec, 1), 4),
         "ambiguous_frac_natural": round(n_amb_all / max(n_all, 1), 4), "continuous_with_oracle": n_all,
         "interval_mean": round(float(iv.mean()), 6), "interval_min": round(float(iv.min()), 6),
         "interval_max": round(float(iv.max()), 6), "splits": splits, "kinds": kinds, "missing_images": missing_img}
    r["pass"] = {"n1200": n_dec == 1200, "interval_033": bool(abs(iv - 0.33).max() <= 0.01),
                 "oversample_30pm2": abs(r["oversampled_frac"] - 0.30) <= 0.02}
    print("CHECK " + json.dumps(r), flush=True)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["restore-test", "pool", "check"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seeds", default="")
    ap.add_argument("--points", type=int, default=10)
    ap.add_argument("--out", default="/data/juhyoung_qdd/data/pool")
    ap.add_argument("--frames", action="store_true")
    ap.add_argument("--confirm-pool", action="store_true", help="POOL generation is gated until the scene is final")
    a = ap.parse_args()
    if a.mode == "check":
        check(a.out)
        return
    if a.mode == "restore-test":
        restore_test(a.seed, a.points, a.out, a.frames)
    else:
        seeds = _seeds(a.seeds)
        if any(s in S.POOL_SEEDS for s in seeds) and not a.confirm_pool:
            raise SystemExit("POOL generation needs --confirm-pool (on hold until the robot config port is done)")
        pool(seeds, a.out)
    os._exit(0)  # SimulationApp.close() hangs in this chroot; results are already flushed


if __name__ == "__main__":
    main()
