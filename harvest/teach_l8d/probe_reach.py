"""Gate G-H reach probe (pod, Isaac, no rendering needed): top-down IK reach of the right arm over a world grid, with
the table lowered out of the way (0.70 m) and every object parked off the table. For each y in spec.GATE_Y and x on a
2 cm grid, the TCP goes up to z 1.20, across, then down the column in 2 cm steps; at each step the target is held
for HOLD_TICKS and the settled TCP error (mm) is recorded -> err[y][x][z]. With --lift the lift joint starts / holds
at that value (the torso moves; the head pitch is unchanged) and the lift joint's soft limits are logged.
Also logs the live head camera (K, R, t) for the view band.
usage: python -m harvest.teach_l8d.probe_reach --out reach.json [--lift 0.0] [--table-z 0.70]"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

XS = [round(0.30 + 0.02 * i, 2) for i in range(17)]  # 0.30 .. 0.62
ZS = [round(1.20 - 0.02 * i, 2) for i in range(24)]  # 1.20 .. 0.74
Z_TOP = 1.20
STEP_M = 0.005
HOLD_TICKS = 25


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--lift", type=float, default=None)
    ap.add_argument("--table-z", type=float, default=0.70)
    ap.add_argument("--zmin", type=float, default=None, help="lowest probed z (default 0.74 + lift shift)")
    a = ap.parse_args(argv)
    code = 0
    try:
        from . import spec as S
        from .run_collect import make_world
        world = make_world("standard", a.table_z, None, a.lift)
        world.reset(0, "mug_tray")
        env = world.env
        for i, k in enumerate(("o3", "o5", "o8", "o9")):
            env.write_object_pose(k, (-2.0 - 0.3 * i, 2.0, 0.10))
        rob = env.robot
        li = rob.joint_names.index("lift_joint")
        lift_now = float(rob.data.joint_pos[0, li])
        lim = [round(float(v), 4) for v in rob.data.soft_joint_pos_limits[0, li].cpu().numpy()]
        shift = 0.0 if a.lift is None else a.lift - (-0.0993)
        zs = [round(z + shift, 3) for z in ZS]
        zmin = a.zmin if a.zmin is not None else 0.74 + shift
        zs = [z for z in zs if z >= zmin - 1e-9]
        w = world.w_open

        def tcp():
            world._st = None
            return np.asarray(world.status()["tcp"], float)

        def move(p):
            p = np.asarray(p, float)
            cur = tcp()
            n = max(1, int(np.ceil(np.linalg.norm(p - cur) / STEP_M)))
            for j in range(1, n + 1):
                world.step(cur + (p - cur) * j / n, w)
            for _ in range(HOLD_TICKS):
                world.step(p, w)
            return float(np.linalg.norm(tcp() - p) * 1e3)

        for _ in range(20):
            world.step(tcp(), w)
        obs = world.observe()
        h = obs.cams["head"]
        head = {"fx": h.fx, "fy": h.fy, "cx": h.cx, "cy": h.cy, "W": h.W, "H": h.H,
                "R": np.asarray(h.R, float).tolist(), "t": np.asarray(h.t, float).tolist()}
        err = []
        for y in S.GATE_Y:
            ey = []
            for x in XS:
                move([tcp()[0], tcp()[1], Z_TOP + shift])
                move([x, y, Z_TOP + shift])
                ey.append([round(move([x, y, z]), 2) for z in zs])
                print("COL " + json.dumps({"y": y, "x": x, "err": ey[-1]}), flush=True)
            err.append(ey)
        out = {"xs": XS, "ys": list(S.GATE_Y), "zs": zs, "err_mm": err, "lift_cmd": a.lift, "lift_start": lift_now,
               "lift_limits": lim, "lift_shift": shift, "table_z_probe": a.table_z, "head_cam": head,
               "hold_ticks": HOLD_TICKS, "step_m": STEP_M}
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(out, f)
        print("PROBE_DONE " + json.dumps({"lift_limits": lim, "lift_start": lift_now, "head_t": head["t"]}), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
