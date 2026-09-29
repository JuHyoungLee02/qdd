"""Bake opened copies of THOR articulated fixtures (articulated tasks A / B / C, user-log 182 / 185; pod, Isaac):
an open drawer (A), a fridge with its door open 90 deg (B), a box with its flaps open (C).

Per asset (several per process, spaced): spawn the ORIGINAL articulated USD (fixed root, identity orientation, high
above the floor), read every body's physics pose at the rest state, write the chosen joints' open values
(prismatic / revolute: OPEN_SHARE x the limit on the side with the larger magnitude; a fridge door at most 90 deg),
step, read the poses again. The body motion D = W1 W0^-1 is carried into the USD asset frame (A = W0 M^-1 of the
root body) and written as the moved bodies' local transforms into a flattened copy <name>_open.usda next to the
source; usd_import.make_static then gives the static opened copy (joints off, colliders static, Y-up fix, bottom
centre at the origin) and inspect() its support surfaces (drawer inside, fridge shelves, box floor).
Output <out>/opened.json {asset: {src, joints: {name: q}, open (flat), dst (static), surfaces, sizes}}.
usage: python -m tools.l8x_assets.bake_open --spec SPEC.json --out DIR
  SPEC: {asset: {"usd": path, "joints": [joint names] | "all", "max_rev_deg": 90 | null}}"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

SPACING = 4.0
Z0 = 6.0
OPEN_SHARE = 0.9
HOLD_K, HOLD_D = 0.0, 1000.0  # damped only (a stiff drive held the drawers at 0); one raw physics step after the write
STEPS = 1


def _mat(pos, q):
    w, x, y, z = (float(v) for v in q)
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, np.asarray(pos, float)
    return M


def _usd_world(stage):
    """{prim name: 4x4 column-convention world matrix} of every prim of a USD stage."""
    from pxr import UsdGeom
    xc = UsdGeom.XformCache()
    out = {}
    for p in stage.Traverse():  # first (outermost) prim of a name: THOR bodies have a same-named Mesh child
        if p.IsA(UsdGeom.Xformable):
            out.setdefault(p.GetName(), (np.array(xc.GetLocalToWorldTransform(p)).T, str(p.GetPath())))
    return out


def write_open(src: str, moved: dict, dst_flat: str) -> None:
    """Flattened copy of src with the moved bodies' new asset-frame world matrices {name: M'} as local transforms."""
    from pxr import Gf, Usd, UsdGeom
    layer = Usd.Stage.Open(src).Flatten()
    tmp = dst_flat + ".tmp.usda"
    layer.Export(tmp)
    st = Usd.Stage.Open(tmp)
    xc = UsdGeom.XformCache()
    for name, M in moved.items():
        prim = next(p for p in st.Traverse() if p.GetName() == name)
        parent = np.array(xc.GetLocalToWorldTransform(prim.GetParent())).T
        local = np.linalg.inv(parent) @ M
        xf = UsdGeom.Xformable(prim)
        xf.ClearXformOpOrder()
        xf.AddTransformOp().Set(Gf.Matrix4d(local.T.tolist()))
    st.GetRootLayer().Export(dst_flat)
    os.remove(tmp)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.assets_x import usd_import as UI
        spec = json.load(open(a.spec))
        names = sorted(spec)
        orig = SC._build_cfg

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.actuators import ImplicitActuatorCfg
            from isaaclab.assets import ArticulationCfg
            cfg, layout = orig(*x, **k)
            for i, n in enumerate(names):
                setattr(cfg.scene, f"art{i}", ArticulationCfg(
                    prim_path="{ENV_REGEX_NS}/ART%d" % i,
                    spawn=sim_utils.UsdFileCfg(
                        usd_path=spec[n]["usd"], mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
                        articulation_props=sim_utils.ArticulationRootPropertiesCfg(fix_root_link=True)),
                    init_state=ArticulationCfg.InitialStateCfg(pos=(SPACING * (i + 1), 8.0, Z0)),
                    actuators={"j": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=HOLD_K, damping=HOLD_D)}))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        env.reset(settle_s=0.2)
        from pxr import Usd
        T = env.torch
        hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
        out = {}
        os.makedirs(a.out, exist_ok=True)
        for i, n in enumerate(names):
            try:
                art = env.scene[f"art{i}"]
                bn, jn = list(art.body_names), list(art.joint_names)
                W0 = {b: _mat(art.data.body_pos_w[0, k].cpu().numpy(), art.data.body_quat_w[0, k].cpu().numpy())
                      for k, b in enumerate(bn)}
                lim = art.data.soft_joint_pos_limits[0].cpu().numpy()
                want = jn if spec[n]["joints"] == "all" else spec[n]["joints"]
                q = art.data.joint_pos[0].clone()
                chosen = {}
                for j in want:
                    k = jn.index(j)
                    lo, hi = float(lim[k, 0]), float(lim[k, 1])
                    v = OPEN_SHARE * (hi if abs(hi) >= abs(lo) else lo)
                    cap = spec[n].get("max_rev_deg")
                    if cap and abs(v) > math.radians(cap) and abs(hi - lo) > 0.5:  # revolute cap (fridge 90 deg)
                        v = math.copysign(math.radians(cap), v)
                    q[k] = v
                    chosen[j] = round(v, 4)
                art.write_joint_state_to_sim(q.unsqueeze(0), T.zeros_like(q).unsqueeze(0))
                art.set_joint_position_target(q.unsqueeze(0))
                for _ in range(STEPS):
                    art.set_joint_position_target(q.unsqueeze(0))  # raw sim steps: no env step / reset events
                    art.write_data_to_sim()
                    env.env.sim.step(render=False)
                    art.update(env.env.sim.get_physics_dt())
                W1 = {b: _mat(art.data.body_pos_w[0, k].cpu().numpy(), art.data.body_quat_w[0, k].cpu().numpy())
                      for k, b in enumerate(bn)}
                got = {j: round(float(art.data.joint_pos[0, jn.index(j)]), 4) for j in chosen}
                st = Usd.Stage.Open(spec[n]["usd"])
                U = _usd_world(st)
                root = bn[0]
                A = W0[root] @ np.linalg.inv(U[root][0])
                moved = {}
                for b in bn:
                    D = W1[b] @ np.linalg.inv(W0[b])
                    if np.abs(D - np.eye(4)).max() > 1e-4 and b in U:
                        moved[b] = np.linalg.inv(A) @ D @ A @ U[b][0]
                flat = os.path.splitext(spec[n]["usd"])[0] + "_open.usda"
                write_open(spec[n]["usd"], moved, flat)
                s = UI.make_static(flat, mode="thor")
                ins = UI.inspect(s["dst"])
                out[n] = dict(src=spec[n]["usd"], joints=chosen, joints_measured=got, moved=sorted(moved), open=flat,
                              **s, **ins)
                print("OPEN " + json.dumps({"asset": n, "joints": got, "moved": len(moved),
                                            "surfaces": len(ins["surfaces"])}), flush=True)
            except Exception as e:  # noqa: BLE001
                out[n] = {"error": f"{type(e).__name__}: {e}"[:300]}
                print("OPEN_ERR", n, out[n]["error"], flush=True)
        json.dump(out, open(os.path.join(a.out, "opened.json"), "w"), indent=1)
        print("OPEN_DONE", sum("error" not in r for r in out.values()), "/", len(out), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
