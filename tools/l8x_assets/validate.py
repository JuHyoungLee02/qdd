"""L8X-assets validation (pod, Isaac; one process runs many scenes -- furniture is re-authored per scene and built
at each hard reset). Per (kind, seed):
  spawn    robot arm joints after the settle vs the default pose (a furniture part hitting the robot moves them)
  surfaces drop a mug (o3) and a box (o9) 5 mm above the centre of each surface's placement region (or the surface
           centre), 2 s: settled z vs top + half height (support height check), xy drift, tilt
  reach    TCP to (region centre, top + 0.15) then top + 0.08, 5 mm steps, settled error (mm); arm error > 8 mm = fail
  view     head camera frame with every surface box projected (green = usable region, red = not, yellow = region)
  video    head camera frames of the whole sequence -> mp4 (cv2)
usage: python -m tools.l8x_assets.validate --out DIR --reach reach_base.json [--kinds a,b] [--seeds 0,1]
       [--mesh-table thor_furniture.json --mesh-kinds thor_counter,...]"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

DROP_TICKS = 40
HOLD_TICKS = 25
STEP_M = 0.005
PARK = {"o3": (-2.0, 2.0, 0.10), "o5": (-2.3, 2.0, 0.10), "o8": (-2.6, 2.0, 0.10), "o9": (-2.9, 2.0, 0.10),
        "o10": (-3.2, 2.0, 0.10)}


def _r(v, n=4):
    return round(float(v), n)


class Runner:
    def __init__(self, mesh_assets=None):
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim.assets_x.isaac import without_table
        from harvest.sim.scene import GRIP_MAX_W, make_env
        self.undo = without_table(mesh_assets)
        self.env = make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        self.mesh_assets = mesh_assets or {}
        self.w = float(GRIP_MAX_W)
        self.frames = []

    # -------------------------------------------------------------- helpers
    def head(self):
        from harvest.astra_motion.world_isaac import camera_pose
        from harvest.sim.scene import load_realcam
        env = self.env
        env.env.sim.render()
        for n in ("cam_head",):
            env.scene[n].update(0.0, force_recompute=True)
        d = env.scene["cam_head"].data
        K = d.intrinsic_matrices[0].cpu().numpy()
        R, t = camera_pose(env.robot, load_realcam(), "cam_head")
        img = env.camera_rgb("cam_head").copy()
        return img, {"fx": float(K[0, 0]), "fy": float(K[1, 1]), "cx": float(K[0, 2]), "cy": float(K[1, 2]),
                     "W": int(img.shape[1]), "H": int(img.shape[0]), "R": R, "t": t}

    def grab(self, every=1):
        if len(self.frames) % 1 == 0:
            self.frames.append(self.head()[0])

    def tcp(self):
        return np.asarray(self.pl.tcp_pose()[0], float)

    def step(self, p):
        from harvest.sim.planner import MAX_DQ_RAD, W_MAX, _slerp_step
        self.cmd_quat = _slerp_step(self.cmd_quat, self.pl.goal_quat, W_MAX * self.env.step_dt)
        q = self.pl._ik(np.asarray(p, float), self.cmd_quat, MAX_DQ_RAD)
        self.env.step(np.concatenate([q, [self.w]]).astype(np.float32))

    def move(self, p, rec=True):
        p = np.asarray(p, float)
        cur = self.tcp()
        n = max(1, int(np.ceil(np.linalg.norm(p - cur) / STEP_M)))
        for j in range(1, n + 1):
            self.step(cur + (p - cur) * j / n)
            if rec and j % 4 == 0:
                self.grab()
        for k in range(HOLD_TICKS):
            self.step(p)
        if rec:
            self.grab()
        return float(np.linalg.norm(self.tcp() - p) * 1e3)

    def hold(self, n, rec=True):
        p = self.tcp()
        for k in range(n):
            self.step(p)
            if rec and k % 4 == 0:
                self.grab()

    # -------------------------------------------------------------- one scene
    def run(self, sc, out_dir):
        from harvest.sim import scene as SC
        from harvest.sim.assets_x.isaac import author_scene
        from harvest.sim.planner import OraclePlanner
        env = self.env
        self.frames = []
        used = author_scene(env, sc, self.mesh_assets)
        li = env.robot.joint_names.index("lift_joint")
        lift = sc.get("lift")
        env.robot.data.default_joint_pos[0, li] = float(SC.INIT_JOINTS["lift_joint"] if lift is None else lift)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        t0 = time.time()
        env.reset(settle_s=1.0)
        q0 = np.asarray(SC.INIT_R_ARM, float)
        dq = float(np.abs(env.arm_q() - q0).max())
        bp = env.robot.data.body_pos_w[0].cpu().numpy()
        names = env.robot.body_names
        self.pl = OraclePlanner(env)
        self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
        for k in PARK:
            env.write_object_pose(k, PARK[k])
        self.hold(5, rec=False)
        img, cam = self.head()
        regions = {p["surface"]: p for p in sc["placement_regions"]}
        res = {"kind": sc["kind"], "seed": sc["seed"], "params": sc["params"], "slots": used, "lift": lift,
               "lift_measured": _r(float(env.robot.data.joint_pos[0, li])),
               "spawn": _spawn_check(dq, bp, names, sc), "surfaces": [], "reset_s": _r(time.time() - t0, 1)}
        _overlay(img, cam, sc, regions, os.path.join(out_dir, "head_overlay.png"))
        _save(img, os.path.join(out_dir, "head.png"))
        for s in sc["surfaces"][:6]:
            reg = regions.get(s["id"], {})
            box = reg.get("region") or s["xy_box"]
            cx, cy = (box[0][0] + box[0][1]) / 2, (box[1][0] + box[1][1]) / 2
            r = {"id": s["id"], "kind": s["kind"], "top_z": s["top_z"], "usable": reg.get("region") is not None,
                 "reason": reg.get("reason"), "visible_centre": bool(_inside(cam, [cx, cy, s["top_z"]]))}
            r["ray"] = _raycast_down([cx, cy, s["top_z"] + 0.30])  # PhysX: what is really under the centre
            if r["ray"]["hit"]:
                r["ray"]["dz_mm"] = _r((r["ray"]["z"] - s["top_z"]) * 1e3, 1)
            drops = {}
            tight = s.get("clearance") is not None and s["clearance"] < 0.12  # inside a drawer: no drop
            for k, h, dxy in ((() if tight else (("o3", 0.095, (0.0, -0.035)), ("o9", 0.07, (0.0, 0.035))))):
                x, y = cx + dxy[0], cy + dxy[1]
                env.write_object_pose(k, (x, y, s["top_z"] + h / 2 + 0.005))
                drops[k] = (x, y, h)
            self.hold(DROP_TICKS)
            r["drop"] = {}
            for k, (x, y, h) in drops.items():
                p, q = env.object_pose(k)
                tilt = float(np.degrees(2 * np.arccos(min(1.0, abs(float(q[0]))))))
                r["drop"][k] = {"dz_mm": _r((p[2] - (s["top_z"] + h / 2)) * 1e3, 1),
                                "dxy_mm": _r(np.hypot(p[0] - x, p[1] - y) * 1e3, 1), "tilt_deg": _r(tilt, 1),
                                "ok": bool(abs(p[2] - (s["top_z"] + h / 2)) < 0.005 and tilt < 5.0)}
                env.write_object_pose(k, PARK[k])
            if r["usable"]:
                above = self.move([cx, cy, s["top_z"] + 0.15])
                low = self.move([cx, cy, s["top_z"] + 0.08])
                back = self.move([cx, cy, s["top_z"] + 0.15])
                r["reach"] = {"above_mm": _r(above, 1), "low_mm": _r(low, 1), "back_mm": _r(back, 1),
                              "ok": bool(max(above, low) <= 8.0)}
            res["surfaces"].append(r)
        self.move([0.34, -0.25, 1.10], rec=False)
        _video(self.frames, os.path.join(out_dir, "head.mp4"))
        _contact_sheet(self.frames, os.path.join(out_dir, "sheet.png"))
        with open(os.path.join(out_dir, "result.json"), "w") as f:
            json.dump(res, f, indent=1)
        with open(os.path.join(out_dir, "scene.json"), "w") as f:
            json.dump(sc, f, indent=1)
        return res


def _spawn_check(dq, bp, names, sc):
    """Robot bodies in front of the torso (x > 0.15) that sit on / inside a furniture part's box after the settle:
    a body within 1.5 cm of or below a part's top inside its xy footprint = the robot rests on the furniture."""
    hits = []
    for p in list(sc["furniture"]) + list(sc["walls"]):
        c, s = np.asarray(p["pos"], float), np.asarray(p["size"], float)
        lo, hi = c - s / 2, c + s / 2
        for i, n in enumerate(names):
            x, y, z = bp[i]
            if x > 0.15 and lo[0] - 0.01 <= x <= hi[0] + 0.01 and lo[1] - 0.01 <= y <= hi[1] + 0.01 \
                    and lo[2] - 0.01 <= z <= hi[2] + 0.015:
                hits.append(f"{n}@{p['id']}")
    return {"arm_dq_max_rad": _r(dq), "robot_in_furniture": hits[:8], "ok": not hits}


def _raycast_down(origin, dist=2.0):
    from omni.physx import get_physx_scene_query_interface
    h = get_physx_scene_query_interface().raycast_closest(tuple(float(v) for v in origin), (0.0, 0.0, -1.0), dist)
    if not h or not h.get("hit"):
        return {"hit": False}
    return {"hit": True, "z": _r(h["position"][2]), "collider": str(h.get("collision", ""))[-80:]}


def _contact_sheet(frames, path, n=8):
    import cv2
    if not frames:
        return
    idx = np.linspace(0, len(frames) - 1, min(n, len(frames))).astype(int)
    tiles = [cv2.resize(np.ascontiguousarray(frames[i][:, :, ::-1]), (336, 188)) for i in idx]
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.concatenate(tiles[k:k + 4], 1) for k in range(0, len(tiles), 4)]
    cv2.imwrite(path, np.concatenate(rows, 0))


def _proj(cam, P):
    P = np.atleast_2d(np.asarray(P, float))
    Pc = (P - np.asarray(cam["t"])) @ np.asarray(cam["R"])
    z = np.maximum(Pc[:, 2], 1e-6)
    return np.stack([cam["cx"] + cam["fx"] * Pc[:, 0] / z, cam["cy"] + cam["fy"] * Pc[:, 1] / z], 1), Pc[:, 2] > 0


def _inside(cam, P):
    uv, ok = _proj(cam, P)
    return bool(ok.all() and 0 <= uv[0, 0] < cam["W"] and 0 <= uv[0, 1] < cam["H"])


def _save(img, path):
    import cv2
    cv2.imwrite(path, np.ascontiguousarray(img[:, :, ::-1]))


def _overlay(img, cam, sc, regions, path):
    import cv2
    o = np.ascontiguousarray(img[:, :, ::-1].copy())

    def poly(box, z, col, th):
        (x0, x1), (y0, y1) = box
        uv, ok = _proj(cam, [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]])
        if ok.all():
            cv2.polylines(o, [uv.astype(np.int32).reshape(-1, 1, 2)], True, col, th)
    for s in sc["surfaces"]:
        reg = regions.get(s["id"], {})
        poly(s["xy_box"], s["top_z"], (0, 200, 0) if reg.get("region") else (0, 0, 220), 1)
        if reg.get("region"):
            poly(reg["region"], s["top_z"], (0, 220, 255), 2)
    cv2.putText(o, f"{sc['kind']} s{sc['seed']}", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imwrite(path, o)


def _video(frames, path, fps=10):
    import cv2
    if not frames:
        return
    H, W = frames[0].shape[:2]
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    for f in frames:
        vw.write(np.ascontiguousarray(f[:, :, ::-1]))
    vw.release()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--reach", required=True)
    ap.add_argument("--kinds", default=None)
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--mesh-table", default=None)
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.sim.assets_x import furniture as FU
        from harvest.sim.assets_x.reach import ReachModel
        rm = ReachModel.load(a.reach)
        mesh_assets = None
        if a.mesh_table:
            with open(a.mesh_table) as f:
                mesh_assets = json.load(f)["assets"]
        kinds = a.kinds.split(",") if a.kinds else list(FU.KINDS) + (list(FU.mesh_kinds(mesh_assets))
                                                                   if mesh_assets else [])
        seeds = [int(s) for s in a.seeds.split(",")]
        scenes = [FU.sample_scene(k, s, reach=rm, mesh_assets=mesh_assets) for k in kinds for s in seeds]
        used = {p["asset"] for sc in scenes for p in sc["furniture"] if p.get("asset")}
        run = Runner({n: v for n, v in (mesh_assets or {}).items() if n in used})  # load only the pieces used
        summ = []
        for sc in scenes:
            kind, seed = sc["kind"], sc["seed"]
            if True:
                d = os.path.join(a.out, f"{kind}_s{seed}")
                os.makedirs(d, exist_ok=True)
                r = run.run(sc, d)
                summ.append(r)
                print("SCENE " + json.dumps({"kind": kind, "seed": seed, "spawn": r["spawn"],
                                             "surfaces": [{k: v for k, v in s.items() if k != "drop"} | {
                                                 "drop_ok": all(x["ok"] for x in s["drop"].values())}
                                                 for s in r["surfaces"]]}), flush=True)
        with open(os.path.join(a.out, "summary.json"), "w") as f:
            json.dump(summ, f, indent=1)
        print("VALIDATE_DONE", len(summ), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
