"""(pod, cuRobo v0.8.0, no rendering) autotune stage 1: offline feasibility sweep with batched cuRobo IK only.

Input = robots/<profile>.json, the ONLY hand-written part: URDF, root height (or a stand/lift range), the hand
descriptor (fingertip links + opposition, harvest/l9/assets9/grippers/hands9.json format), the robot's real cameras
(parent link, mount, HFOV, size, optional pitch joint / pitch offset range) and optional lift/torso joints with limits
(null = the URDF limits). Everything else is measured here:

  for every body config (grid over the given body joints) x surface height x work point (x, y) x TCP height above
  the surface (grasp / lift / carry / ready levels) x hand orientation (yaws over the hand's own symmetry period x
  tilts): cuRobo IK success (self-collision on, empty world), plus "target inside the robot's own head camera"
  for every camera pitch option.

Generalizes r1b probe2/probe3/varfeas (R1 torso closed form -> any body joints by URDF FK; ZED view -> any camera)
and the G1 team's reach / visibility gates. Cost control (no new algorithm): IK is run once per unique base-frame
target (positions snapped to `--snap` m, base rotations grouped to 0.05 rad), targets beyond the arm's FK-sampled
reach radius are marked unreachable without IK.

usage: sweep.py <robots/profile.json> <out dir> [--arms right,left] [--seeds 8] [--batch 2048] [--selftest]
-> <out>/<profile>_<arm>.npz per arm + <out>/<profile>_meta.json; ranges via make_profile.py.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "l9", "v2robot"))
import geom as G  # noqa: E402

XS = np.round(np.arange(0.10, 0.901, 0.05), 3)  # world x of work points (m, robot root frame, forward)
YS = np.round(np.arange(-0.55, 0.151, 0.05), 3)  # right-arm convention (negative = the arm's own side)
LEVELS = np.array([0.04, 0.09, 0.14, 0.19, 0.24, 0.29])  # TCP height above the surface (grasp = first)
SURFACES = np.round(np.arange(0.40, 1.101, 0.05), 3)
OBJ_Z = 0.03  # visibility point above the surface (a small object's centre)


def load_robot(fn: str) -> dict:
    r = json.load(open(fn))
    for k in ("profile", "urdf", "arms", "cameras"):
        if k not in r:
            raise ValueError(f"{fn}: missing {k!r}")
    return r


def body_configs(r: dict, u) -> list:
    """Body joint grid (URDF limits where the input gives null) + the optional virtual stand range."""
    joints = {}
    for j, lim in (r.get("body_joints") or {}).items():
        joints[j] = list(lim) if lim else [u.joints[j]["lower"], u.joints[j]["upper"]]
    if r.get("root_z_rel_surface"):
        joints["root_z_rel_surface"] = list(r["root_z_rel_surface"])
    return G.body_grid(joints, int(r.get("body_n", 5)))


def reach_radius(u, base: str, tool: str, arm_joints: list, n: int = 3000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    lo = np.array([u.joints[j]["lower"] for j in arm_joints])
    hi = np.array([u.joints[j]["upper"] for j in arm_joints])
    best = 0.0
    for _ in range(n):
        q = dict(zip(arm_joints, rng.uniform(lo, hi)))
        best = max(best, float(np.linalg.norm(u.T_rel(tool, base, q)[:3, 3])))
    return best


def camera_world(r: dict, u, cam: str, q: dict, T_wr: np.ndarray, pitch_opt: float) -> dict:
    c = r["cameras"][cam]
    from harvest.l9 import hcam9 as HC
    qq = dict(q)
    Rm = HC.quat_to_R(c["quat"])
    if c.get("pitch_joint"):
        qq[c["pitch_joint"]] = pitch_opt
    elif c.get("pitch_offset_deg"):
        Rm = Rm @ G.rot_y(math.radians(pitch_opt))  # about the camera's own left axis: + = further down
    T = T_wr @ u.T_root(c["parent"], qq)
    return {"R": T[:3, :3] @ Rm, "t": T[:3, :3] @ np.asarray(c["pos"], float) + T[:3, 3], "hfov": c["hfov"],
            "width": c["width"], "height": c["height"]}


def body_points(r: dict, u, per_link: int = 400) -> dict:
    """{link: N x 3 collision-mesh points in the link frame} of every body link that is NOT part of an arm (arm links =
    the first arm joint's child and its descendants, for every arm). Visual meshes when a link has no collision."""
    import trimesh
    from harvest.l9 import curobo9 as C9
    arm_links = set()
    for a in r["arms"]:
        ch = u.joints[C9.arm_joints(r["profile"], a)[0]]["child"]
        arm_links |= {ch, *u.descendants(ch)}
    out = {}
    for link in u.links:
        if link in arm_links:
            continue
        gs = u.geoms(link, "collision") or u.geoms(link, "visual")
        pts = []
        for fn, sc, Tg, prim in gs:
            if fn is None or not os.path.exists(fn):
                continue
            m = trimesh.load(fn, force="mesh", process=False)
            v = np.asarray(m.vertices, float) * np.asarray(sc, float)
            if len(v) > per_link:
                v = v[np.random.default_rng(0).choice(len(v), per_link, replace=False)]
            pts.append((Tg[:3, :3] @ v.T).T + Tg[:3, 3])
        if pts:
            out[link] = np.concatenate(pts)
    return out


def body_front_x(u, pts: dict, q: dict, rz: float, surface_z: float, above: float = 0.02) -> float:
    """Most forward x (root frame) of the non-arm body below surface + `above` with the root at height rz; -9 if none."""
    best = -9.0
    for link, P in pts.items():
        T = u.T_root(link, q)
        W = (T[:3, :3] @ P.T).T + T[:3, 3]
        m = W[:, 2] + rz <= surface_z + above
        if m.any():
            best = max(best, float(W[m, 0].max()))
    return best


def pitch_options(c: dict) -> list:
    if c.get("pitch_joint"):
        lo, hi = c["pitch_range"]
        return [float(v) for v in np.linspace(lo, hi, int(c.get("pitch_n", 7)))]
    if c.get("pitch_offset_deg"):
        lo, hi = c["pitch_offset_deg"]
        return [float(v) for v in np.arange(lo, hi + 1e-6, 5.0)]
    return [0.0]


class IK:
    def __init__(self, profile: str, arm: str, seeds: int, batch: int):
        import torch
        from harvest.l9 import curobo9 as C9
        self.torch, self.B = torch, batch
        self.ik = C9.make_ik(profile, arm, num_seeds=seeds, max_batch_size=batch)
        self.tf = C9.tool_frame(profile, arm)

    def solve(self, P: np.ndarray, Rm: np.ndarray = None, Q: np.ndarray = None) -> np.ndarray:
        """P (N, 3) + rotations Rm (N, 3, 3) or quaternions Q (N, 4, wxyz) in the config base frame -> success."""
        from curobo.types import GoalToolPose, Pose
        from harvest.l9.grasp9 import mat_quat
        out = np.zeros(len(P), bool)
        if Q is None:
            Q = np.stack([mat_quat(R) for R in Rm]) if len(P) else np.zeros((0, 4))
        for s0 in range(0, len(P), self.B):
            m = min(self.B, len(P) - s0)
            p, q = P[s0:s0 + m], Q[s0:s0 + m]
            if m < self.B:
                p = np.concatenate([p, np.repeat(p[-1:], self.B - m, 0)])
                q = np.concatenate([q, np.repeat(q[-1:], self.B - m, 0)])
            g = GoalToolPose.from_poses({self.tf: Pose(
                position=self.torch.tensor(p, device="cuda", dtype=self.torch.float32),
                quaternion=self.torch.tensor(q, device="cuda", dtype=self.torch.float32))}, num_goalset=1)
            r = self.ik.solve_pose(g)
            out[s0:s0 + m] = r.success.reshape(self.B, -1)[:m, 0].cpu().numpy().astype(bool)
            if (s0 // self.B) % 200 == 199:
                print(f"  ik {s0 + m}/{len(P)}", flush=True)
        return out


def selftest(u, profile, arm, ik: IK, base, tool, arm_joints, n=512):
    """FK-generated poses must come back reachable (catches tool/base frame mismatches)."""
    rng = np.random.default_rng(1)
    lo = np.array([u.joints[j]["lower"] for j in arm_joints])
    hi = np.array([u.joints[j]["upper"] for j in arm_joints])
    Ts = [u.T_rel(tool, base, dict(zip(arm_joints, rng.uniform(lo, hi)))) for _ in range(n)]
    ok = ik.solve(np.stack([T[:3, 3] for T in Ts]), np.stack([T[:3, :3] for T in Ts]))
    return float(ok.mean())


def sweep_arm(r: dict, arm: str, out: str, seeds: int, batch: int, snap: float, do_selftest: bool,
              shard=(0, 1), vis_only: bool = False) -> dict:
    from urdf_fk import Urdf
    from harvest.l9 import curobo9 as C9
    prof = r["profile"]
    u = Urdf(r["urdf"])
    base, tool, aj = C9.base_link(prof, arm), C9.tool_frame(prof, arm), C9.arm_joints(prof, arm)
    t0 = time.time()
    ik = None if vis_only else IK(prof, arm, seeds, batch)
    st = selftest(u, prof, arm, ik, base, tool, aj) if do_selftest and ik else None
    print(f"[{prof}/{arm}] selftest FK->IK success {st}", flush=True)
    rad = reach_radius(u, base, tool, aj) + 0.03
    cfgs = body_configs(r, u)
    sgn = -1.0 if arm == "left" else 1.0  # mirror y for the left arm
    hand = r["arms"][arm]["hand"]
    ori = G.orientations(hand, int(r.get("yaw_step", 30)))
    Rw = np.stack([G.grasp_R(math.radians(o["tilt_deg"]), sgn * math.radians(o["yaw_deg"]),
                             sgn * math.radians(o["tdir_deg"])) for o in ori])
    cam = r.get("head_camera", "cam_head")
    popts = pitch_options(r["cameras"][cam])
    C, S, X, Y, H, O, P = len(cfgs), len(SURFACES), len(XS), len(YS), len(LEVELS), len(ori), len(popts)
    reach = np.zeros((C, S, X, Y, H, O), bool)
    vis = np.zeros((C, S, X, Y, P), bool)
    cam_pitch = np.zeros((C, S, P))
    lean, mount_z, mount_x = np.zeros(C), np.zeros((C, S)), np.zeros(C)
    body_q0 = {j: 0.0 for j in cfgs[0] if j != "root_z_rel_surface"}
    T0 = u.T_root(base, body_q0)
    gx, gy, gl = np.meshgrid(XS, YS * sgn, LEVELS, indexing="ij")
    # per config: base pose (world) for every surface
    groups = {}
    poses = []
    for c, q in enumerate(cfgs):
        qb = {k: v for k, v in q.items() if k != "root_z_rel_surface"}
        Tb = u.T_root(base, qb)
        lean[c] = G.lean_rad(Tb, T0)
        row = []
        for s, sz in enumerate(SURFACES):
            rz = (sz + q["root_z_rel_surface"]) if "root_z_rel_surface" in q else float(r.get("root_z", 0.0))
            Twr = np.eye(4)
            Twr[2, 3] = rz
            Twb = Twr @ Tb
            mount_z[c, s] = Twb[2, 3]
            row.append((Twr, Twb))
        mount_x[c] = row[0][1][0, 3]
        poses.append(row)
        key = tuple(np.round(np.array(G.rot_euler(Tb[:3, :3])) / 0.05).astype(int))
        groups.setdefault(key, []).append(c)
    # visibility (numpy)
    for c, q in enumerate(cfgs):
        qb = {k: v for k, v in q.items() if k != "root_z_rel_surface"}
        for s, sz in enumerate(SURFACES):
            Twr = poses[c][s][0]
            Pw = np.stack([gx[..., 0].ravel(), gy[..., 0].ravel(), np.full(X * Y, sz + OBJ_Z)], -1)
            for p, po in enumerate(popts):
                cw = camera_world(r, u, cam, qb, Twr, po)
                vis[c, s, :, :, p] = G.visible(cw, Pw, margin=0.05).reshape(X, Y)
                cam_pitch[c, s, p] = G.cam_pitch_deg(cw["R"])
    # body clearance (L9 runtime P131: a torso posture that pushes into the furniture is not held)
    bpts = body_points(r, u)
    bfx = np.full((C, S), -9.0)
    for c, q in enumerate(cfgs):
        qb = {k: v for k, v in q.items() if k != "root_z_rel_surface"}
        for s, sz in enumerate(SURFACES):
            bfx[c, s] = body_front_x(u, bpts, qb, float(poses[c][s][0][2, 3]), float(sz))
    sfx = "" if shard[1] == 1 else f".s{shard[0]}of{shard[1]}"
    if vis_only:  # recompute camera visibility / pitch only, keep the stored IK results
        old = np.load(os.path.join(out, f"{prof}_{arm}{sfx}.npz"))
        reach = old["reach"]
        groups = {}
    vis_any = vis.any(-1)  # IK only where the robot's own camera sees the point (score = coverage x visible)
    from harvest.l9.grasp9 import mat_quat
    n_ik = 0
    reqP, reqQ, book = [], [], []  # every group's unique in-reach base-frame targets x orientations, solved at once
    for gi, (key, members) in enumerate(groups.items()):
        if gi % shard[1] != shard[0]:
            continue
        Rrep = poses[members[0]][0][1][:3, :3]
        Qo = np.stack([mat_quat(Rrep.T @ Rw[o]) for o in range(O)])  # base-frame tool rotations
        allP, where = [], []
        for c in members:
            for s, sz in enumerate(SURFACES):
                m = np.broadcast_to(vis_any[c, s][:, :, None], (X, Y, H)).ravel()
                if not m.any():
                    continue
                Twb = poses[c][s][1]
                Pw = np.stack([gx.ravel(), gy.ravel(), sz + gl.ravel()], -1)[m]
                allP.append((Pw - Twb[:3, 3]) @ Twb[:3, :3])
                where.append((c, s, m))
        if not allP:
            continue
        keys = np.round(np.concatenate(allP) / snap).astype(np.int64)
        uk, inv = np.unique(keys, axis=0, return_inverse=True)
        up = uk * snap
        idx = np.nonzero(np.linalg.norm(up, axis=1) <= rad)[0]
        reqP.append(np.repeat(up[idx], O, 0))
        reqQ.append(np.tile(Qo, (len(idx), 1)))
        book.append((where, inv.ravel(), len(uk), idx))
        n_ik += len(idx) * O
    print(f"[{prof}/{arm}] shard {shard} groups {len(book)}/{len(groups)} ik {n_ik} t {time.time() - t0:.0f}s", flush=True)
    ok = ik.solve(np.concatenate(reqP), Q=np.concatenate(reqQ)) if n_ik else np.zeros(0, bool)
    o0 = 0
    for where, inv, nu, idx in book:
        res = np.zeros((nu, O), bool)
        res[idx] = ok[o0:o0 + len(idx) * O].reshape(len(idx), O)
        o0 += len(idx) * O
        i0 = 0
        for c, s, m in where:
            k = int(m.sum())
            flat = reach[c, s].reshape(-1, O)
            flat[m] = res[inv[i0:i0 + k]]
            reach[c, s] = flat.reshape(X, Y, H, O)
            i0 += k
    print(f"[{prof}/{arm}] ik done t {time.time() - t0:.0f}s", flush=True)
    if vis_only:
        mo = json.load(open(os.path.join(out, f"{prof}_{arm}{sfx}_meta.json")))
        n_ik, st = mo["n_ik"], mo["selftest_success"]
    meta = {"profile": prof, "arm": arm, "configs": cfgs, "orients": ori, "pitch_options": popts,
            "selftest_success": st, "reach_radius_m": rad, "n_ik": n_ik, "n_groups": len(groups),
            "seconds": round(time.time() - t0, 1), "seeds": seeds, "snap_m": snap, "shard": list(shard)}
    np.savez_compressed(os.path.join(out, f"{prof}_{arm}{sfx}.npz"), reach=reach, vis=vis, cam_pitch=cam_pitch, xs=XS,
                        ys=YS, levels=LEVELS, surfaces=SURFACES, lean=lean, mount_z=mount_z, mount_x=mount_x,
                        body_front_x=bfx)
    json.dump(meta, open(os.path.join(out, f"{prof}_{arm}{sfx}_meta.json"), "w"), indent=1)
    print(f"[{prof}/{arm}] done {meta['seconds']}s ik {n_ik} reach {reach.mean():.3f} vis {vis.mean():.3f}", flush=True)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("robot")
    ap.add_argument("out")
    ap.add_argument("--arms", default=None)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--snap", type=float, default=0.03)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--vis-only", action="store_true", help="recompute visibility / camera pitch, keep IK")
    ap.add_argument("--shard", default="0/1", help="k/n: only rotation groups g with g %% n == k (merge: merge.py)")
    a = ap.parse_args()
    r = load_robot(a.robot)
    os.makedirs(a.out, exist_ok=True)
    for arm in (a.arms.split(",") if a.arms else list(r["arms"])):
        sweep_arm(r, arm, a.out, a.seeds, a.batch, a.snap, a.selftest, tuple(int(v) for v in a.shard.split("/")),
                  a.vis_only)


if __name__ == "__main__":
    main()
