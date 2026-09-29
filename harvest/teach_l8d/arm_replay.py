"""L8S change 26 diagnosis: replay a recorded right-arm PD target series (joints.npz arm_target_torque_vel) on the
robot alone (seed 0 standard scene, no furniture / clutter, no cameras) and print joint1's per-step change.
--no-self turns the robot's self collisions off (USD PhysxArticulationAPI, re-read by the hard reset).
If the joint1 jump is reproduced here it comes from the robot itself (self contact / drive), not the scene.

  python.sh -m harvest.teach_l8d.arm_replay --npz EP/joints.npz --steps 0-80 [--no-self] --out F.json
"""
from __future__ import annotations

import argparse
import json
import os


def _self_collisions(stage, root: str, on: bool) -> list:
    from pxr import PhysxSchema
    hit = []
    for p in stage.Traverse():
        if str(p.GetPath()).startswith(root) and p.HasAPI(PhysxSchema.PhysxArticulationAPI):
            PhysxSchema.PhysxArticulationAPI(p).CreateEnabledSelfCollisionsAttr(bool(on))
            hit.append(str(p.GetPath()))
    return hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--steps", default="0-80")
    ap.add_argument("--no-self", action="store_true")
    ap.add_argument("--hold", type=int, default=None)
    ap.add_argument("--probe", type=int, default=None)
    ap.add_argument("--effort", type=float, default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import numpy as np

    from ..sim.scene import GRIP_MAX_W, make_env
    z = np.load(a.npz, allow_pickle=True)
    ids = [int(i) for i in z["arm_ids"]]
    names = [str(n) for n in z["names"]]
    q_all, tgt = z["q"], z["arm_target_torque_vel"][:, :len(ids)]
    s0, s1 = (int(v) for v in a.steps.split("-"))
    lift = float(q_all[s0, names.index("lift_joint")])
    env = make_env(0, headless=True, cameras=(), lift=lift)
    roots = []
    if a.no_self:
        import omni.usd
        roots = _self_collisions(omni.usd.get_context().get_stage(), "/World/envs/env_0/Robot", False)
    env.reset(settle_s=0.0)
    rob, torch = env.robot, env.torch
    q0 = rob.data.joint_pos.clone()
    q0[0, ids] = torch.as_tensor(q_all[s0, ids], device=q0.device)
    rob.write_joint_state_to_sim(q0, torch.zeros_like(q0))  # diagnosis only: start at the recorded pose
    for _ in range(10):
        env.step(np.concatenate([q_all[s0, ids], [GRIP_MAX_W]]))
    rows = []
    if a.list:  # joints / constraints of the robot USD: loop joints, mimic joints, tendons (position-level couplings)
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        for p in stage.Traverse():
            path = str(p.GetPath())
            schemas = [str(s) for s in p.GetAppliedSchemas()]
            tn = str(p.GetTypeName())
            odd = [s for s in schemas if "Mimic" in s or "Tendon" in s or "Attachment" in s]
            if "Joint" in tn or odd:
                b0 = p.GetRelationship("physics:body0").GetTargets() if p.GetRelationship("physics:body0") else []
                b1 = p.GetRelationship("physics:body1").GetTargets() if p.GetRelationship("physics:body1") else []
                ex = p.GetAttribute("physics:excludeFromArticulation")
                en = p.GetAttribute("physics:jointEnabled")
                print("ARM_LIST", tn, path.replace("/World/envs/env_0/", ""), [str(x).split("/")[-1] for x in b0],
                      [str(x).split("/")[-1] for x in b1], "exclude", ex.Get() if ex and ex.IsValid() else None,
                      "enabled", en.Get() if en and en.IsValid() else None, odd, flush=True)
                for at in p.GetAttributes():
                    if "mimic" in at.GetName().lower():
                        print("ARM_LIST   attr", at.GetName(), at.Get(), flush=True)
                for rel in p.GetRelationships():
                    if "mimic" in rel.GetName().lower():
                        print("ARM_LIST   rel", rel.GetName(), [str(x) for x in rel.GetTargets()], flush=True)
        import sys
        sys.stdout.flush()
        os._exit(0)
    if a.probe is not None:  # which robot body's colliders push joint1: turn each body's colliders off in turn
        import omni.usd
        from pxr import UsdPhysics
        stage = omni.usd.get_context().get_stage()
        cols = [p for p in stage.Traverse() if str(p.GetPath()).startswith("/World/envs/env_0/Robot")
                and p.HasAPI(UsdPhysics.CollisionAPI)]
        qh = q_all[a.probe, ids]

        def drift():
            env.reset(settle_s=0.0)
            qq = rob.data.joint_pos.clone()
            qq[0, ids] = torch.as_tensor(qh, device=qq.device)
            rob.write_joint_state_to_sim(qq, torch.zeros_like(qq))
            for _ in range(15):
                env.step(np.concatenate([qh, [GRIP_MAX_W]]))
            return float(rob.data.joint_pos[0, ids[0]].cpu().numpy() - qh[0])
        base = drift()
        print("ARM_PROBE base drift", round(base, 3), "colliders", len(cols))
        out = {"probe": a.probe, "base": base, "bodies": {}}
        scene_cols = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI)
                      and not str(p.GetPath()).startswith("/World/envs/env_0/Robot")]
        for tag, group in (("ALL_ROBOT", cols), ("ALL_SCENE", scene_cols)):
            for p in group:
                UsdPhysics.CollisionAPI(p).CreateCollisionEnabledAttr(False)
            out[tag] = round(drift(), 4)
            for p in group:
                UsdPhysics.CollisionAPI(p).CreateCollisionEnabledAttr(True)
            print("ARM_PROBE", tag, len(group), out[tag], flush=True)
        for b in rob.body_names:
            mine = [p for p in cols if f"/{b}/" in str(p.GetPath()) + "/"]
            if not mine:
                continue
            for p in mine:
                UsdPhysics.CollisionAPI(p).CreateCollisionEnabledAttr(False)
            d = drift()
            for p in mine:
                UsdPhysics.CollisionAPI(p).CreateCollisionEnabledAttr(True)
            out["bodies"][b] = round(d, 4)
            print("ARM_PROBE", b, len(mine), round(d, 3), flush=True)
        json.dump(out, open(a.out, "w"), indent=0)
        import sys; sys.stdout.flush(); os._exit(0)
    if a.hold is not None:  # static check: hold the recorded pose at step a.hold; PhysX gravity torque vs drive
        view = rob.root_physx_view
        qh = q_all[a.hold, ids]
        if a.effort is not None:  # diagnosis only: how much joint1 torque holding this pose needs
            rob.write_joint_effort_limit_to_sim(a.effort, joint_ids=[ids[0]])
        q0[0, ids] = torch.as_tensor(qh, device=q0.device)
        rob.write_joint_state_to_sim(q0, torch.zeros_like(q0))
        for k in range(40):
            env.step(np.concatenate([qh, [GRIP_MAX_W]]))
            c = view.get_gravity_compensation_forces()[0, ids].cpu().numpy()
            q = rob.data.joint_pos[0, ids].cpu().numpy()
            rows.append({"t": k, "q": [round(float(v), 4) for v in q], "rec_q": [round(float(v), 4) for v in qh],
                         "tau": [round(float(v), 2) for v in rob.data.applied_torque[0, ids].cpu().numpy()],
                         "grav": [round(float(v), 2) for v in c]})
        print("ARM_HOLD", a.hold, "q-qh", np.round(q - qh, 3).tolist(), "tau", rows[-1]["tau"], "grav", rows[-1]["grav"])
        print("ARM_HOLD limits", np.round(rob.data.joint_pos_limits[0, ids].cpu().numpy(), 3).tolist())
        print("ARM_HOLD physx limits", np.round(view.get_dof_limits()[0, ids].cpu().numpy(), 3).tolist())
        print("ARM_HOLD physx max force", np.round(view.get_dof_max_forces()[0, ids].cpu().numpy(), 1).tolist(),
              "stiff", np.round(view.get_dof_stiffnesses()[0, ids].cpu().numpy(), 1).tolist(),
              "armature", np.round(view.get_dof_armatures()[0, ids].cpu().numpy(), 3).tolist(),
              "friction", np.round(view.get_dof_friction_coefficients()[0, ids].cpu().numpy(), 3).tolist())
        for b in ("arm_base_link", "arm_r_link1", "arm_r_link2", "arm_r_link3", "arm_r_link4", "arm_r_link6",
                  "arm_r_link7", "head_link2"):
            print("ARM_HOLD body", b, np.round(rob.data.body_pos_w[0, rob.body_names.index(b)].cpu().numpy(), 3).tolist())
        mass = rob.root_physx_view.get_masses()[0].cpu().numpy()
        print("ARM_HOLD masses", {n: round(float(m), 2) for n, m in zip(rob.body_names, mass) if float(m) > 0.5})
        json.dump({"hold": a.hold, "rows": rows}, open(a.out, "w"), indent=0)
        import sys; sys.stdout.flush(); os._exit(0)
    for i in range(s0, min(s1, len(tgt))):
        env.step(np.concatenate([tgt[i], [GRIP_MAX_W]]))
        q = rob.data.joint_pos[0, ids].cpu().numpy()
        rows.append({"t": i, "q": [round(float(v), 4) for v in q], "rec_q": [round(float(v), 4) for v in q_all[i + 1, ids]],
                     "tau": [round(float(v), 2) for v in rob.data.applied_torque[0, ids].cpu().numpy()]})
    q = np.asarray([r["q"] for r in rows])
    dq = np.abs(np.diff(q, axis=0)).max(0)
    res = {"npz": a.npz, "no_self": a.no_self, "roots": roots, "lift": lift, "max_dq": dq.round(4).tolist(),
           "rows": rows}
    json.dump(res, open(a.out, "w"), indent=0)
    print("ARM_REPLAY", "no_self" if a.no_self else "self", "max dq per joint", dq.round(3).tolist(), "roots", roots)
    import sys; sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
