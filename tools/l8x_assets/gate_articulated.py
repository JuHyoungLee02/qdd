"""Articulated fixture gate (user-log 176; pod, Isaac): THOR assets with their original joints (MolmoSpaces
objects_thor, CC BY 4.0), several per process, each spawned as a fixed-root articulation facing the robot (Y-up fix +
yaw -90 deg, as gate_drawer / furniture MESH_YAW), bodies 1 kg, joints damped (no stiffness).
  spawn    every movable joint stays within 5 mm / 3 deg of its start for 2 s, the root does not move
  actuate  per movable joint (up to MAX_J): a force (prismatic, FORCE N) or torque (revolute, TORQUE N m) about the
           joint axis on its moving body for 1 s (revolute 2 s), both signs; ok = moved >= 60 % of the range or
           >= 10 cm / 45 deg
  handle   handle-like bodies (handle / knob / button / switch / lever in the name) on or equal to the moving body
           (fixed-joint chain): world collider bbox after the spawn -> height, smallest cross size, the gap behind the
           handle to the moving part's front face and its protrusion (front = -x, towards the robot);
           graspable = height 0.35-1.35 m (floor piece, lift + reach) and (bar: cross 8-45 mm, gap >= 25 mm |
           knob / lever: protrusion >= 15 mm, cross 8-60 mm)
  pass     spawn ok and at least one joint that actuates with a graspable handle on its moving part
Output <out>/articulated_gate.json {asset: record}; ART lines per asset.
usage: python -m tools.l8x_assets.gate_articulated --out DIR --assets a.usda,b.usda,..."""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

SPACING = 3.0
MAX_J = 6
FORCE, TORQUE = 20.0, 3.0
HANDLE_WORDS = ("handle", "knob", "button", "switch", "lever", "dial")


def joints_of(usd: str) -> tuple:
    """({movable joint: {type, b0, b1, lower, upper, axis_b0, axis_b1}}, [(a, b) fixed pairs]) from the USD."""
    from pxr import Usd
    st = Usd.Stage.Open(usd)
    mov, fixed = {}, []
    for p in st.Traverse():
        t = p.GetTypeName()
        b0 = p.GetRelationship("physics:body0").GetTargets() if p.GetRelationship("physics:body0") else []
        b1 = p.GetRelationship("physics:body1").GetTargets() if p.GetRelationship("physics:body1") else []
        n0, n1 = (str(b0[0].name) if b0 else None), (str(b1[0].name) if b1 else None)
        if t == "PhysicsFixedJoint":
            fixed.append((n0, n1))
        elif t in ("PhysicsPrismaticJoint", "PhysicsRevoluteJoint"):
            ax = str(p.GetAttribute("physics:axis").Get() or "X")
            e = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}[ax]
            axes = []
            for s in ("0", "1"):
                q = p.GetAttribute(f"physics:localRot{s}").Get()
                axes.append([float(v) for v in (_qrot((q.GetReal(), *q.GetImaginary()), e) if q is not None else e)])
            mov[p.GetName()] = {"type": "prismatic" if "Prismatic" in t else "revolute", "b0": n0, "b1": n1,
                                "lower": p.GetAttribute("physics:lowerLimit").Get(),
                                "upper": p.GetAttribute("physics:upperLimit").Get(),
                                "axis_b0": axes[0], "axis_b1": axes[1]}
    count: dict = {}
    for j in mov.values():
        for b in (j["b0"], j["b1"]):
            count[b] = count.get(b, 0) + 1
    fixed_to = {}
    for a_, b_ in fixed:
        fixed_to.setdefault(a_, set()).add(b_)
        fixed_to.setdefault(b_, set()).add(a_)
    for j in mov.values():
        side = "1" if (count.get(j["b0"], 0) >= count.get(j["b1"], 0) and len(mov) > 1) or j["b0"] is None else "0"
        if j["b1"] is None:
            side = "0"
        j["moving"], j["axis_moving"] = j["b" + side], j["axis_b" + side]
        group, todo = {j["moving"]}, [j["moving"]]
        while todo:  # the moving part = its body + everything fixed-jointed to it
            for c in fixed_to.get(todo.pop(), ()):
                if c not in group and count.get(c, 0) == 0:
                    group.add(c)
                    todo.append(c)
        j["group"] = sorted(g for g in group if g)
    return mov, fixed


def _qrot(q, v):
    w, x, y, z = (float(c) for c in q)
    u = np.array([x, y, z])
    v = np.asarray(v, float)
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--assets", required=True)
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.objv import qmul
        usds = a.assets.split(",")
        names = [os.path.splitext(os.path.basename(u))[0] for u in usds]
        orig = SC._build_cfg
        rot = qmul((math.cos(-math.pi / 4), 0.0, 0.0, math.sin(-math.pi / 4)), (0.7071068, 0.7071068, 0.0, 0.0))

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.actuators import ImplicitActuatorCfg
            from isaaclab.assets import ArticulationCfg
            cfg, layout = orig(*x, **k)
            for i, (n, u) in enumerate(zip(names, usds)):
                setattr(cfg.scene, "art_" + n, ArticulationCfg(
                    prim_path="{ENV_REGEX_NS}/ART_" + n,
                    spawn=sim_utils.UsdFileCfg(
                        usd_path=u, mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
                        articulation_props=sim_utils.ArticulationRootPropertiesCfg(fix_root_link=True)),
                    init_state=ArticulationCfg.InitialStateCfg(pos=(2.0 + SPACING * i, 4.0, 0.0), rot=rot),
                    actuators={"all": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=0.0, damping=5.0)}))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        jinfo = {n: joints_of(u)[0] for n, u in zip(names, usds)}
        env.reset(settle_s=0.2)
        import omni.usd
        from pxr import Usd, UsdGeom
        stage = omni.usd.get_context().get_stage()
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy", "guide"])

        def bbox(n, body):
            root = stage.GetPrimAtPath(f"/World/envs/env_0/ART_{n}")
            for p in Usd.PrimRange(root):
                if p.GetName() == body:
                    r = cache.ComputeWorldBound(p).ComputeAlignedRange()
                    return None if r.IsEmpty() else (np.array(r.GetMin()), np.array(r.GetMax()))
            return None

        T, dev = env.torch, env.env.device
        hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
        res = {}
        os.makedirs(a.out, exist_ok=True)
        for n in names:
            art = env.scene["art_" + n]
            jn, bn = list(art.joint_names), list(art.body_names)
            mov = {j: jinfo[n][j] for j in jn if j in jinfo[n]}
            root0 = art.data.root_pos_w[0].cpu().numpy().copy()
            # handle geometry at the spawn pose (USD matches physics before any root move)
            hand = {}
            rb = cache.ComputeWorldBound(stage.GetPrimAtPath(f"/World/envs/env_0/ART_{n}")).ComputeAlignedRange()
            floor_z = float(rb.GetMin()[2])
            for j, m in mov.items():
                body = bbox(n, m["moving"])
                for b in m["group"]:
                    if not any(w in b.lower() for w in HANDLE_WORDS):
                        continue
                    hb = bbox(n, b)
                    if hb is None:
                        continue
                    lo, hi = hb
                    size = hi - lo
                    cross = float(sorted(size)[1]) if b != m["moving"] else float(min(size))
                    gap = prot = None
                    if body is not None and b != m["moving"]:
                        gap = float(body[0][0] - hi[0])  # moving part's front face - handle back
                        prot = float(body[0][0] - lo[0])
                    else:
                        prot = float(size[0])
                    z = float((lo[2] + hi[2]) / 2) - floor_z  # above the piece bottom (it stands on the floor)
                    knob = b == m["moving"] or any(w in b.lower() for w in HANDLE_WORDS[1:])
                    ok_h = 0.35 <= z <= 1.35
                    if knob:
                        ok = ok_h and prot is not None and prot >= 0.015 and 0.008 <= cross <= 0.06
                    else:
                        ok = ok_h and gap is not None and gap >= 0.025 and 0.008 <= float(min(size)) <= 0.045
                    hand.setdefault(j, []).append({"body": b, "z": round(z, 3),
                                                  "size": [round(float(v), 3) for v in size],
                                                  "gap": None if gap is None else round(gap, 3),
                                                  "protrusion": None if prot is None else round(prot, 3),
                                                  "kind": "knob" if knob else "bar", "graspable": bool(ok)})
            q0 = art.data.joint_pos[0].cpu().numpy().copy()
            for _ in range(40):
                env.step(hold)
            q1 = art.data.joint_pos[0].cpu().numpy()
            drift = {}
            for j, m in mov.items():
                d = abs(float(q1[jn.index(j)] - q0[jn.index(j)]))
                drift[j] = round(d * (1e3 if m["type"] == "prismatic" else 180 / math.pi), 1)
            root_move = float(np.linalg.norm(art.data.root_pos_w[0].cpu().numpy() - root0))
            spawn_ok = root_move <= 0.005 and all(v <= (5.0 if mov[j]["type"] == "prismatic" else 3.0)
                                                  for j, v in drift.items())
            acts = []
            for j, m in list(mov.items())[:MAX_J]:
                bi = bn.index(m["moving"]) if m["moving"] in bn else None
                if bi is None:
                    continue
                lo_, hi_ = (float(v) for v in (m["lower"] or 0.0, m["upper"] or 0.0))
                rng = (hi_ - lo_) if m["type"] == "prismatic" else math.radians(hi_ - lo_)
                best = 0.0
                for sign in (1.0, -1.0):
                    env.reset(settle_s=0.1)
                    f = T.zeros((1, len(bn), 3), device=dev)
                    tq = T.zeros_like(f)
                    vec = T.tensor([sign * c for c in m["axis_moving"]], device=dev)
                    if m["type"] == "prismatic":
                        f[0, bi, :] = FORCE * vec
                    else:
                        tq[0, bi, :] = TORQUE * vec
                    art.set_external_force_and_torque(f, tq)
                    qa = float(art.data.joint_pos[0, jn.index(j)])
                    for _ in range(20 if m["type"] == "prismatic" else 40):  # 1 s / 2 s
                        env.step(hold)
                    qb = float(art.data.joint_pos[0, jn.index(j)])
                    art.set_external_force_and_torque(T.zeros_like(f), T.zeros_like(f))
                    best = max(best, abs(qb - qa))
                need = min(0.6 * abs(rng), 0.10 if m["type"] == "prismatic" else math.radians(45)) if rng else 1e9
                acts.append({"joint": j, "type": m["type"], "moving": m["moving"], "range": round(rng, 4),
                             "moved": round(best, 4), "ok": bool(best >= need - 1e-6 and rng > 0),
                             "handles": hand.get(j, [])})
            good = [x for x in acts if x["ok"] and any(h["graspable"] for h in x["handles"])]
            r = {"usd": usds[names.index(n)], "n_joints": len(mov), "spawn_drift": drift,
                 "root_move_mm": round(root_move * 1e3, 1), "spawn_ok": bool(spawn_ok), "joints": acts,
                 "n_good": len(good), "pass": bool(spawn_ok and good)}
            res[n] = r
            print("ART " + json.dumps({"asset": n, "pass": r["pass"], "spawn_ok": r["spawn_ok"], "n_good": len(good),
                                       "acts": [(x["joint"], x["ok"], sum(h["graspable"] for h in x["handles"]))
                                                for x in acts]}), flush=True)
            p = os.path.join(a.out, "articulated_gate.json")
            old = json.load(open(p)) if os.path.exists(p) else {}
            old.update({n: r})
            json.dump(old, open(p, "w"), indent=1)
        print("ART_DONE", sum(r["pass"] for r in res.values()), "/", len(res), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
