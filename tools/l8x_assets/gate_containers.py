"""Container gate for the diversified tasks (user-log 178; pod, Isaac).

Each container of containers.json (kinematic, triangle-mesh collider) stands on the floor in its own spot far from
the robot. Per container up to N_TRY candidate objects that fit its opening (2 x footprint_r <= opening_min_side -
2 cm) are dropped ONE AT A TIME from 3 cm above the rim at the opening centre (random yaw), 1.5 s settle, then parked:
  inside  the object's centre within the opening box (+1 cm), its bottom between the inner floor - 1 cm and the rim
"onto" targets (plate, board): dropped 3 cm above the surface; inside = centre over the box, bottom within the
surface +-1.5 cm. Pen holders get pens / pencils standing (long axis vertical, lowered until the tip is 1 cm above
the rim): inside + tilt <= 35 deg from vertical. A container passes with >= 75 % inside; "fits" lists the objects
that stayed inside.
Candidates: objects_real rows that passed the L8-D object gate (--pass-ids) or the rescaled stable rows, stable
products 2.5-8.5 cm wide and <= 15 cm tall, task_items fruit; pens for pen holders.
Output <out>/containers_check.json.
usage: python -m tools.l8x_assets.gate_containers --containers C.json --items I.json --objects O.json
       --products P.json --pass-ids tally.json --out DIR"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os

import numpy as np

N_TRY = 4
SETTLE = 30
SPOT = (3.0, -8.0, 1.0)  # x, y0, dy
PARK = (-6.0, 6.0, 0.3)


def _h(s):
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--containers", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--objects", required=True)
    ap.add_argument("--products", required=True)
    ap.add_argument("--pass-ids", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from tools.l8x_assets.validate_objects import qmat, qmul, tilt_deg

        C = {k: c for k, c in json.load(open(a.containers))["containers"].items() if c.get("place_kind")}
        items = json.load(open(a.items))["objects"]
        objs = json.load(open(a.objects))["objects"]
        prods = json.load(open(a.products))["objects"]
        passed = set(json.load(open(a.pass_ids)).get("pass_ids", []))
        pool = {}
        for k, o in objs.items():
            if (k in passed or (k.startswith("gsor_") and o.get("stable"))) and o.get("usd_physics"):
                pool[k] = o
        for k, o in prods.items():
            if o.get("stable") and 0.025 <= o["grasp_width"] <= 0.085 and o["height"] <= 0.15:
                pool[k] = o
        for k, o in items.items():
            if o.get("role") == "fruit":
                pool[k] = o
        pens = {k: o for k, o in items.items() if o.get("role") == "pen"}
        cand = {}
        for ck, c in C.items():
            ins = c["inside"]
            if c["role"] == "pen_holder":
                cand[ck] = sorted(pens)[:4]
                continue
            fit = [k for k, o in pool.items() if 2 * o["footprint_r"] <= ins["opening_min_side"] - 0.02
                   and o["height"] <= 0.25]
            fit.sort(key=lambda k: _h(f"{ck}:{k}"))
            cand[ck] = fit[:N_TRY]
        used = sorted({k for v in cand.values() for k in v})
        allrows = {**pool, **pens}
        cnames = sorted(C)
        orig = SC._build_cfg

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.assets import RigidObjectCfg
            cfg, layout = orig(*x, **k)
            cfg.scene.table = None
            for i, n in enumerate(cnames):
                c = C[n]
                setattr(cfg.scene, "ct_%d" % i, RigidObjectCfg(
                    prim_path="{ENV_REGEX_NS}/CT_%d" % i, spawn=sim_utils.UsdFileCfg(usd_path=c["usd_physics"]),
                    init_state=RigidObjectCfg.InitialStateCfg(
                        pos=(SPOT[0] - c["origin_from_root"][0], SPOT[1] + i * SPOT[2] - c["origin_from_root"][1],
                             c["root_above_bottom"]), rot=tuple(c["spawn_quat_wxyz"]))))
            for i, n in enumerate(used):
                o = allrows[n]
                setattr(cfg.scene, "it_%d" % i, RigidObjectCfg(
                    prim_path="{ENV_REGEX_NS}/IT_%d" % i,
                    spawn=sim_utils.UsdFileCfg(usd_path=o["usd_physics"],
                                               mass_props=sim_utils.MassPropertiesCfg(mass=o["mass"])),
                    init_state=RigidObjectCfg.InitialStateCfg(pos=(PARK[0] - 0.4 * i, PARK[1], PARK[2]),
                                                              rot=tuple(o["spawn_quat_wxyz"]))))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        env.reset(settle_s=0.3)
        T, dev = env.torch, env.env.device
        hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
        # resume: keep finished containers; the one that was running when a previous run died / timed out (a
        # PhysX hang inside a narrow triangle-mesh holder) is recorded as a failure
        outp, curp = os.path.join(a.out, "containers_check.json"), os.path.join(a.out, "current.txt")
        res = json.load(open(outp)) if os.path.exists(outp) else {}
        if os.path.exists(curp):
            hung = open(curp).read().strip()
            if hung and hung not in res:
                res[hung] = {"role": C[hung]["role"], "n": 0, "inside": 0, "pass": False, "fits": [],
                             "container_drift_mm": None, "trials": [], "hung": True}
        rng = np.random.default_rng(178)
        for ci, ck in enumerate(cnames):
            if ck in res:
                continue
            os.makedirs(a.out, exist_ok=True)
            open(curp, "w").write(ck)
            c, ins = C[ck], C[ck]["inside"]
            base = np.array([SPOT[0], SPOT[1] + ci * SPOT[2], 0.0])
            (ox0, ox1), (oy0, oy1) = ins["opening_box"]
            cen = base + np.array([(ox0 + ox1) / 2, (oy0 + oy1) / 2, 0.0])
            trials = []
            for k in cand[ck]:
                i = used.index(k)
                o = allrows[k]
                yaw = float(rng.uniform(-math.pi, math.pi))
                qy = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
                if c["role"] == "pen_holder":  # stand the pen: rotate its long canonical axis (y) to z
                    q = qmul(qmul(qy, (math.cos(math.pi / 4), math.sin(math.pi / 4), 0.0, 0.0)),
                             tuple(o["spawn_quat_wxyz"]))
                    z = ins["rim_z"] + 0.01 + o["length"] / 2
                else:
                    q = qmul(qy, tuple(o["spawn_quat_wxyz"]))
                    top = ins["rim_z"] if ins["place_kind"] == "into" else ins["inner_floor_z"]
                    z = top + 0.03 + o["root_above_bottom"]
                cx, cy = o["centre_from_root_xy"]
                R = qmat(q)
                off = R @ np.array([cx, cy, 0.0]) if c["role"] != "pen_holder" else np.zeros(3)
                p0 = [float(cen[0] - off[0]), float(cen[1] - off[1]), float(z)]
                env.scene["it_%d" % i].write_root_pose_to_sim(T.tensor([[*p0, *q]], dtype=T.float32, device=dev))
                env.scene["it_%d" % i].write_root_velocity_to_sim(T.zeros((1, 6), device=dev))
                for _ in range(SETTLE):
                    env.step(hold)
                d = env.scene["it_%d" % i].data
                p, qq = d.root_pos_w[0].cpu().numpy(), d.root_quat_w[0].cpu().numpy()
                rel = p - base
                if c["role"] == "pen_holder":
                    inside = bool(ox0 - 0.01 <= rel[0] <= ox1 + 0.01 and oy0 - 0.01 <= rel[1] <= oy1 + 0.01 and
                                  ins["inner_floor_z"] - 0.01 <= rel[2] <= ins["rim_z"] + o["length"] / 2)
                    bot = None
                else:  # object centre and lowest corner of its box (root frame -> world)
                    Rq = qmat(qq)
                    hx, hy, _ = o["half_extents"]
                    ccx, ccy = o["centre_from_root_xy"]
                    zb, zt = -o["root_above_bottom"], -o["root_above_bottom"] + o["height"]
                    cen_w = rel + Rq @ np.array([ccx, ccy, (zb + zt) / 2])
                    corners = np.array([[ccx + sx * hx, ccy + sy * hy, z] for sx in (-1, 1) for sy in (-1, 1)
                                        for z in (zb, zt)])
                    bot = float(rel[2] + (corners @ Rq.T)[:, 2].min())
                    inxy = ox0 - 0.01 <= cen_w[0] <= ox1 + 0.01 and oy0 - 0.01 <= cen_w[1] <= oy1 + 0.01
                    if ins["place_kind"] == "onto":
                        inside = bool(inxy and abs(bot - ins["inner_floor_z"]) <= 0.015)
                    else:
                        inside = bool(inxy and ins["inner_floor_z"] - 0.01 <= bot <= ins["rim_z"])
                r = {"object": k, "inside": inside, "rel": [round(float(v), 3) for v in rel],
                     "bottom": None if bot is None else round(bot, 3)}
                print("TRY", ck[:30], k[:30], r["inside"], r["rel"], r["bottom"], flush=True)
                if c["role"] == "pen_holder":
                    up = qmat(qq) @ (qmat(q).T @ np.array([0.0, 0.0, 1.0]))
                    r["tilt_deg"] = round(math.degrees(math.acos(float(np.clip(abs(up[2]), -1, 1)))), 1)
                    r["inside"] = inside and r["tilt_deg"] <= 35
                trials.append(r)
                env.scene["it_%d" % i].write_root_pose_to_sim(T.tensor(
                    [[PARK[0] - 0.4 * i, PARK[1], PARK[2], *o["spawn_quat_wxyz"]]], dtype=T.float32, device=dev))
                env.scene["it_%d" % i].write_root_velocity_to_sim(T.zeros((1, 6), device=dev))
            dc = env.scene["ct_%d" % ci].data.root_pos_w[0].cpu().numpy()
            k_in = sum(t["inside"] for t in trials)
            res[ck] = {"role": c["role"], "n": len(trials), "inside": k_in,
                       "pass": bool(trials) and k_in >= 0.75 * len(trials), "fits": [t["object"] for t in trials
                                                                                    if t["inside"]],
                       "container_drift_mm": round(float(np.linalg.norm(dc[:2] - (base[:2] - np.array(
                           c["origin_from_root"][:2])))) * 1e3, 1), "trials": trials}
            print("CONT " + json.dumps({k: v for k, v in res[ck].items() if k != "trials"} | {"id": ck}), flush=True)
            os.makedirs(a.out, exist_ok=True)  # partial result after every container
            json.dump(res, open(os.path.join(a.out, "containers_check.json"), "w"), indent=1)
        os.makedirs(a.out, exist_ok=True)
        json.dump(res, open(os.path.join(a.out, "containers_check.json"), "w"), indent=1)
        if os.path.exists(curp):
            os.remove(curp)
        print("CONT_DONE", sum(v["pass"] for v in res.values()), "/", len(res), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
