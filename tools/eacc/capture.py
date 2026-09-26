"""E-ACC bench capture (pod, Isaac cyclo rootfs, GPU 0; docs/stage3/prereg_eacc.md §2). One Isaac process runs the
fixed episode plan (bench.plan) with the R2 oracle planner as the stand-in policy (hard reset per episode, canon §78;
harvest/* is used read-only through IsaacWorld). Per episode: one snapshot (three raw camera PNGs + camera models +
tip + pad gap + holding) and the whole path (t, tip, phase, pad gap, holding) up to t_snap + bench.AFTER_S, plus the
oracle geometry (target / place poses -> pre-grasp point, grasp point, place centre) and the capture checks.
Resumable: an episode with meta.json or skip.json is not run again.
usage (inside ir_run.sh): /isaac-sim/python.sh tools/eacc/capture.py --out /data/harvest/out/eacc/bench [--only id,..]"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench as B  # noqa: E402

CAM_NAME = {"head": "cam_head", "wrist_left": "cam_wrist_left", "wrist": "cam_wrist_right"}
T_MAX = 75.0


def drift_planner_cls():
    from harvest.sim import planner as PL

    class DriftPlanner(PL.OraclePlanner):
        """The oracle planner at bench.SPEED x its TCP speeds; optionally with the goal of one phase moved (goal_fn)
        and that phase frozen (never left, no timeout): the policy heads for the wrong spot and stalls there. With
        freeze None it is the on-plan stand-in policy."""
        freeze, goal_fn = None, None

        def _goal(self):
            g, v = super()._goal()
            if self.phase == self.freeze and self.goal_fn is not None:
                g = np.asarray(self.goal_fn(g), float)
            return g, v * B.SPEED

        def step(self):
            orig, fr = PL.next_phase, self.freeze

            def nf(phase, s):
                return phase if phase == fr else orig(phase, s)
            PL.next_phase = nf
            try:
                return super().step()
            finally:
                PL.next_phase = orig
    return DriftPlanner


def _r(v, n=4):
    return [round(float(x), n) for x in v]


def run_episode(world, ep: dict, out_root: str) -> dict:
    from harvest.astra_motion.harness import obj_height
    d = os.path.join(out_root, ep["id"])
    world.reset(ep["seed"], ep["task"])
    env = world.env
    info = world.task_info()
    tgt, place = info["tgt"], info["place"]
    z0 = world.table_z
    st0 = world.status()
    c = np.asarray(st0["obj"][tgt], float)
    h = obj_height(tgt)
    pre = np.array([c[0], c[1], z0 + h + B.APPROACH_ABOVE_TOP_M])
    gp = np.array([c[0], c[1], z0 + h - B.GRASP_BELOW_TOP_M])
    place_xy = np.asarray(env.object_pose(place)[0], float)[:2]
    kind = ep["kind"]
    wrong, delta = None, None
    pl = drift_planner_cls()(env)
    if kind != "on":
        if kind == "off_b":
            w = np.asarray(env.object_pose(B.WRONG_OBJ[ep["task"]])[0], float)
            wrong = np.array([w[0], w[1], pre[2]])
            pl.freeze, pl.goal_fn = "approach", (lambda g, w=wrong: w)
        else:
            base = pre if kind == "off_a" else np.array([place_xy[0], place_xy[1], z0 + B.CARRY_TCP_Z])
            delta = B.delta_for(ep["id"], ep["seed"])
            for k in range(4):
                dk = B.rotate(delta, k)
                if B.in_box(base + dk):
                    delta = dk
                    break
            wrong = base + np.asarray(delta)
            pl.freeze = "approach" if kind == "off_a" else "carry"
            pl.goal_fn = (lambda g, w=wrong: w)
    world.pl = pl
    path, snap, seg_start = [], None, None
    tip0 = np.asarray(world.status()["tcp"], float)
    while True:
        world._st = None
        s = world.status()
        t, ph = s["t"], pl.phase
        tip = np.asarray(s["tcp"], float)
        holding = bool(s["pred"].get(f"holding({tgt})"))
        path.append({"t": round(t, 3), "tip": _r(tip), "phase": ph, "grip_w": round(float(s["grip_w"]), 4),
                     "holding": holding})
        if snap is None:
            take = False
            if kind == "on":
                take = ph == ep["phase"] and t - pl.t_phase0 >= B.SNAP_AT[ph] - 1e-9
            elif ph == pl.freeze:
                if seg_start is None:
                    seg_start = tip.copy()
                full = float(np.linalg.norm(wrong - seg_start))
                take = full > 0.03 and float(np.linalg.norm(tip - seg_start)) >= B.OFF_FRAC * full
            if take:
                o = world.observe()
                os.makedirs(d, exist_ok=True)
                from PIL import Image
                for k, im in o.rgb.items():
                    Image.fromarray(im).save(os.path.join(d, f"{CAM_NAME[k]}.png"))
                snap = {"t_snap": round(t, 3), "tip": _r(o.tcp), "grip_w": round(float(o.grip_w), 4),
                        "holding": holding, "cams": {CAM_NAME[k]: cm.to_json() for k, cm in o.cams.items()}}
        if snap is not None and t >= snap["t_snap"] + B.AFTER_S:
            break
        if t >= T_MAX or ph == "fail" or (snap is None and ph == "done" and ep.get("phase") != "done"):
            break
        q = pl.step()
        env.step(q)
    base_meta = {"id": ep["id"], "kind": kind, "seed": ep["seed"], "task": ep["task"], "on_phase": ep.get("phase"),
                 "instruction": info["instruction"], "tgt": tgt, "place": place, "table_z": round(z0, 4),
                 "delta": None if delta is None else _r(delta), "wrong_goal": None if wrong is None else _r(wrong),
                 "oracle": {"target_c": _r(c), "pregrasp": _r(pre), "grasp_point": _r(gp), "place_xy": _r(place_xy)}}
    if snap is None:
        os.makedirs(d, exist_ok=True)
        rec = dict(base_meta, reason="no_snapshot", last_phase=path[-1]["phase"], t_end=path[-1]["t"])
        json.dump(rec, open(os.path.join(d, "skip.json"), "w"), indent=1)
        return {"id": ep["id"], "ok": False, "reason": "no_snapshot"}
    meta = dict(base_meta, **snap, path=path, tip_start=_r(tip0))
    meta["checks"] = checks(meta)
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"))
    return {"id": ep["id"], "ok": meta["checks"]["ok"], **{k: v for k, v in meta["checks"].items() if k != "ok"}}


def checks(meta: dict) -> dict:
    """Capture checks (prereg §2.3) -- a snapshot enters a set only if ok."""
    t = meta["t_snap"]
    ra = B.at(meta["path"], t + B.L_ARR)
    out = {"phase_snap": B.at(meta["path"], t)["phase"], "phase_arr": ra["phase"], "path_end": meta["path"][-1]["t"]}
    ok = out["path_end"] >= t + B.L_ARR - 1e-6 or out["phase_arr"] == "done"
    if meta["kind"] == "on":
        ok = ok and out["phase_snap"] == meta["on_phase"] and "fail" not in B.phases_between(meta["path"], t, t + B.L_ARR)
    else:
        tip_s, tip_a = np.asarray(meta["tip"]), np.asarray(ra["tip"])
        w = np.asarray(meta["wrong_goal"])
        out["arr_to_wrong_m"] = round(float(np.linalg.norm(tip_a - w)), 4)
        out["send_to_sub_m"] = round(float(np.linalg.norm(B.subgoal(meta, tip_s) - tip_s)), 4)
        out["arr_to_sub_m"] = round(float(np.linalg.norm(B.subgoal(meta, tip_a) - tip_a)), 4)
        hold_ok = all(r["holding"] for r in meta["path"] if t <= r["t"] <= t + B.L_ARR) if meta["kind"] == "off_c" \
            else not any(r["holding"] for r in meta["path"] if r["t"] <= t + B.L_ARR)
        out["holding_ok"] = hold_ok
        ok = ok and out["arr_to_wrong_m"] <= 0.02 and out["send_to_sub_m"] >= 0.05 and out["arr_to_sub_m"] >= 0.05 \
            and hold_ok
    out["ok"] = bool(ok)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/data/harvest/out/eacc/bench")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import IsaacWorld
        world = IsaacWorld()
        only = set(a.only.split(",")) if a.only else None
        for ep in B.plan():
            if only and ep["id"] not in only:
                continue
            d = os.path.join(a.out, ep["id"])
            if os.path.exists(os.path.join(d, "meta.json")) or os.path.exists(os.path.join(d, "skip.json")):
                continue
            print("EP " + json.dumps(run_episode(world, ep, a.out)), flush=True)
        print("CAPTURE_DONE", flush=True)
    except BaseException:  # noqa: BLE001 - print, then leave without SimulationApp.close()
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
