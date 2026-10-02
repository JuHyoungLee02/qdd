"""(pure numpy; r1pro/g1 need one trimesh-free URDF FK call, plain python3, no Isaac) Self-check 7: is scene
PLACEMENT validated against the new robot's OWN reach map + OWN head camera, or still against the AI Worker's
(reach9.load_default(), the only `rm` scene9.sample()/collect9.draw() use unless a robot has its own hook)?

Why (L9 owner request via main, 10-03, after the G1 fix 2311383): `scene9.sample` / `collect9.draw` place every
robot's objects with the AI Worker's reach probe + head camera (`reach9.load_default()`) unless a robot-specific
hook exists. For G1 that put targets where ITS OWN torso D435 does not look: offline replay of 80 plan rows -> only
~30/80 visible in G1's own camera (commit 2311383). G1's own fix (`harvest.l9.g1reach9.G1Reach` + a small
`reach9.py`/`collect9.py` dispatch hook, opt-in `L9V2_G1_REACH=1`) lives on the G1 team's own branch (worktree
`wt_l9g1`), **not yet on dev** -- this script does NOT depend on it or touch reach9.py/collect9.py/scene9.py at all
(tool side only, per the task's constraint): it calls `scene9.sample`/`scene9.node_points` (read-only, existing
functions) and does its own reach+visibility check directly against a generic `ProfileReach`, instead of routing
through `reach9.reach_points` (which on current dev still assumes a plain `ReachModel` and has no hook to dispatch
on `rm.reach_xy`). It is the generic, tool-side version of the same idea (any new robot gets this gate
automatically, without needing a bespoke `<robot>reach9.py` + a human noticing late).

Method (no new algorithm, same idea as g1reach9.G1Reach, generalized):
  1. Build `ProfileReach(profile, arm)`: the SAME `assets9/reach_v2/<profile>_<arm>.json` cuRobo map
     (`harvest.l9.g1reach9._ok_base`'s grid lookup, generalized to any profile) + the profile's own head camera,
     placed in the SAME scene-origin convention `robot9.v2_root_pos`/`BASE_X`/`BASE_Y_RIGHT` + a representative
     table height already use (robot9 constants only; no new placement rule).
  2. Draw N scenes with `scene9.sample(..., rm=reach9.load_default())` -- the CURRENT default for any robot without
     its own hook (what AI Worker-style placement gives everyone today).
  3. For every drawn scene, re-check every node's points under the profile's OWN reach map + camera (bypassing
     `scene9.usable`'s own-parts-occlusion check, `blocked_s`, since wiring that in would mean touching reach9.py --
     a comparative reach/visibility signal, not a pixel-exact occlusion check) -- this answers "if this new robot
     used today's default placement unmodified, what fraction would actually be reachable and in ITS OWN camera
     view?" -- vs the AIW rate the scene was drawn to satisfy (already in `scene["usable_n"]`). A projected-radius
     floor (`--obj-radius-m`, default 0.03 m, a representative small-object half-width) also requires the object
     not shrink to a sub-pixel speck.

usage: scene_reach.py <profile> <arm> <family> <rule> <n_seeds> [--seed0 0] [--table-z 0.75] [--obj-radius-m 0.03]
                      [--margin-frac 0.05] [--min-radius-px 6] [--out out.json]
Franka needs no URDF (its head camera is already given directly in the config base link, panda_link0). R1 Pro / G1
need their prepared URDF (`/data/harvest/assets_l9v2/robots/<robot>/<robot>_l9v2.urdf`, `--urdf` to override).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.join(HERE, "..", "..")
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _urdf_fk():
    sys.path.insert(0, os.path.join(HERE, "..", "l9", "v2robot"))
    from urdf_fk import Urdf  # noqa: E402
    return Urdf


# ---------------------------------------------------------------------------------------------- reach (generalizes
# harvest.l9.g1reach9._ok_base to any profile/arm; same reach_v2 json format for all 4 robots)
class ProfileReach:
    """ReachModel stand-in for `reach9.reach_points`/`visible_points` (duck-typed: `reach_xy`, `cam`, `margin_px`,
    `at_lift`) -- the SAME interface `harvest.l9.g1reach9.G1Reach` uses, built generically from this profile's own
    `assets9/reach_v2/<profile>_<arm>.json` map and head camera."""

    def __init__(self, profile: str, arm: str, cam: dict | None, margin_px: float, assets9: str):
        self.profile, self.arm = profile, arm
        self.map = json.load(open(os.path.join(assets9, "reach_v2", f"{profile}_{arm}.json")))
        self.base_pos, self.base_R = None, None  # set by base_world_pose()
        self.cam = cam  # {"R","t","fx","fy","cx","cy","W","H"} in WORLD (scene-origin) frame, or None
        self.margin_px = margin_px

    def at_lift(self, lift: float) -> "ProfileReach":
        return self  # this profile's reach_v2 map has no lift axis (cuRobo grid is lift-invariant by base frame)

    def reach_xy(self, arm: str, X, Y, top, z_need=(0.07, 0.24)) -> np.ndarray:
        X, Y = np.asarray(X, float).ravel(), np.asarray(Y, float).ravel()
        ok = np.ones(X.shape, bool)
        for dz in z_need:
            P = np.stack([X, Y, np.full(X.shape, float(top) + dz)], -1)
            Pb = (P - self.base_pos) @ self.base_R  # world -> this profile's config-base-link frame
            g = self.map["grid"]
            idx, inside = [], np.ones(len(P), bool)
            for k, ax in enumerate("xyz"):
                i = np.rint((Pb[:, k] - g[ax]["lo"]) / g[ax]["step"]).astype(int)
                inside &= (i >= 0) & (i < g[ax]["n"])
                idx.append(np.clip(i, 0, g[ax]["n"] - 1))
            flat = (idx[0] * g["y"]["n"] + idx[1]) * g["z"]["n"] + idx[2]
            cell_ok = np.zeros(len(P), bool)
            for c in ("top", "oblique"):
                s = np.frombuffer(self.map["ok"][c].encode(), np.uint8) == ord("1")
                cell_ok |= s[flat]
            ok &= cell_ok & inside
        return ok


# ---------------------------------------------------------------------------------------------- world placement
# (robot9 constants only: no new base/camera placement rule, just read where each profile already sits)
def base_world_pose(profile: str, table_z: float, urdf: str | None) -> tuple:
    """-> (R [3x3], t [3]) of this profile's cuRobo CONFIG base link in the scene-origin (world) frame scene9 uses
    ("the robot stands at the origin facing +x", scene9.py's own docstring)."""
    from harvest.l9 import robot9 as R9
    if profile == "franka_mast":
        return np.eye(3), np.array([R9.BASE_X, R9.BASE_Y_RIGHT, 0.80])  # config base = panda_link0 = the root itself
    Urdf = _urdf_fk()
    robot = "r1pro" if profile == "r1pro" else "g1"
    root = np.asarray(R9.v2_root_pos(robot), float)
    u = Urdf(urdf or f"/data/harvest/assets_l9v2/robots/{robot}/{robot}_l9v2.urdf")
    body_q = R9.v2_body_joints(robot, table_z)
    base_link = "torso_link4" if robot == "r1pro" else "torso_link"
    T = u.T_root(base_link, body_q)
    return T[:3, :3], T[:3, 3] + root


def camera_world(profile: str, arm: str, base_R: np.ndarray, base_t: np.ndarray, urdf: str | None) -> dict | None:
    """-> reach9-style {"R","t","fx","fy","cx","cy","W","H"} in WORLD frame, or None (no camera modelled). R's
    columns = (right, down, forward) -- reach9.visible_points' convention -- converted from hcam9's "columns =
    camera +X forward, +Y left, +Z up" convention the V2 camera mounts and the AI Worker/Franka ones share
    (harvest/l9/hcam9.py docstring; same conversion `g1reach9.G1Reach` already uses, generalized)."""
    from harvest.l9 import hcam9 as HC
    from harvest.l9 import robot9 as R9
    if profile == "franka_mast":
        pos, quat = R9.head_mount_default()  # already given directly in panda_link0 == the config base link
        R_parent_base, t_parent_base = np.eye(3), np.zeros(3)
        s = R9.CAM_SPECS["cam_head"]
        W, H, hfov = s["width"], s["height"], s["hfov"]
    else:
        robot = "r1pro" if profile == "r1pro" else "g1"
        c = R9.V2[robot]["cameras"]["cam_head"]
        pos, quat = c["pos"], c["quat"]
        Urdf = _urdf_fk()
        u = Urdf(urdf or f"/data/harvest/assets_l9v2/robots/{robot}/{robot}_l9v2.urdf")
        base_link = "torso_link4" if robot == "r1pro" else "torso_link"
        T = u.T_rel(c["parent"], base_link, {})
        R_parent_base, t_parent_base = T[:3, :3], T[:3, 3]
        W, H, hfov = c["width"], c["height"], c["hfov"]
    R_cam_parent = HC.quat_to_R(quat)  # cols = fwd, left, up (parent-link frame)
    R_cam_base = R_parent_base @ R_cam_parent
    t_cam_base = t_parent_base + R_parent_base @ np.asarray(pos, float)
    R_cam_world, t_cam_world = base_R @ R_cam_base, base_t + base_R @ t_cam_base
    right, down, fwd = -R_cam_world[:, 1], -R_cam_world[:, 2], R_cam_world[:, 0]
    fx = (W / 2) / math.tan(math.radians(hfov) / 2)
    return {"R": np.column_stack([right, down, fwd]), "t": t_cam_world, "fx": fx, "fy": fx, "cx": W / 2, "cy": H / 2,
           "W": W, "H": H}


def build_profile_reach(profile: str, arm: str, table_z: float, margin_frac: float, urdf: str | None) -> "ProfileReach":
    here = os.path.join(HERE, "..", "..", "harvest", "l9", "assets9")
    base_R, base_t = base_world_pose(profile, table_z, urdf)
    cam = camera_world(profile, arm, base_R, base_t, urdf)
    margin_px = margin_frac * cam["W"]
    pr = ProfileReach(profile, arm, cam, margin_px, here)
    pr.base_pos, pr.base_R = base_t, base_R
    return pr


# ---------------------------------------------------------------------------------------------- comparison
def visible_with_radius(rm, X, Y, z, h, obj_radius_m: float, min_radius_px: float) -> np.ndarray:
    from harvest.l9 import reach9 as R9
    ok = R9.visible_points(rm, X, Y, z, h=h)
    if rm.cam is None:
        return ok
    c = rm.cam
    P = np.stack([np.asarray(X, float).ravel(), np.asarray(Y, float).ravel(), np.full(len(np.ravel(X)), z)], -1)
    depth = np.maximum(((P - c["t"]) @ c["R"])[:, 2], 1e-6)
    radius_px = c["fx"] * obj_radius_m / depth
    return ok & (radius_px >= min_radius_px)


def run(profile: str, arm: str, family: str, rule: str, seeds: list, table_z: float, obj_radius_m: float,
       margin_frac: float, min_radius_px: float, urdf: str | None) -> dict:
    from harvest.l9 import reach9 as R9
    from harvest.l9 import scene9 as S9
    aiw = R9.load_default()
    own = build_profile_reach(profile, arm, table_z, margin_frac, urdf)
    per_seed = []
    for sd in seeds:
        try:
            sc = S9.sample(family, rule, int(sd), arm, aiw)
        except RuntimeError as e:
            per_seed.append({"seed": int(sd), "error": str(e)})
            continue
        n_aiw = sum(1 for n in sc["nodes"] if sc["usable_n"].get(n["id"], 0) >= 4)
        n_own = 0
        for n in sc["nodes"]:
            # scene9.usable()'s own-parts-occlusion check (blocked_s) is skipped here (tool side only -- current
            # dev reach9.py has no rm-type dispatch hook yet (unmerged G1 branch 2311383), so this check calls
            # `own.reach_xy` directly instead of scene9.usable()/reach9.reach_points, which assume a plain
            # ReachModel). A comparative visibility/reach signal, not a pixel-exact occlusion check.
            W, _ = S9.node_points(n, sc["yaw"])
            if len(W) == 0 or n.get("covered_above") is not None or n.get("fixture") in S9.FRONT_FIXTURES:
                continue
            reach_ok = own.reach_xy(arm, W[:, 0], W[:, 1], n["top_z"])
            vis_ok = visible_with_radius(own, W[:, 0], W[:, 1], n["top_z"], 0.10, obj_radius_m, min_radius_px)
            if (reach_ok & vis_ok).sum() >= 4:
                n_own += 1
        per_seed.append({"seed": int(sd), "n_nodes": len(sc["nodes"]), "n_usable_under_aiw": n_aiw,
                         "n_usable_under_own_camera": n_own})
    ok_rows = [r for r in per_seed if "error" not in r]
    rate_aiw = float(np.mean([r["n_usable_under_aiw"] / max(r["n_nodes"], 1) for r in ok_rows])) if ok_rows else None
    rate_own = float(np.mean([r["n_usable_under_own_camera"] / max(r["n_nodes"], 1) for r in ok_rows])) if ok_rows else None
    return {"profile": profile, "arm": arm, "family": family, "rule": rule, "n_seeds": len(seeds),
           "n_draw_errors": len(seeds) - len(ok_rows), "rate_usable_under_aiw_default": rate_aiw,
           "rate_usable_under_own_camera": rate_own,
           "gap": (rate_aiw - rate_own) if (rate_aiw is not None and rate_own is not None) else None,
           "per_seed": per_seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("arm")
    ap.add_argument("family")
    ap.add_argument("rule")
    ap.add_argument("n_seeds", type=int)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--table-z", type=float, default=0.75)
    ap.add_argument("--obj-radius-m", type=float, default=0.03)
    ap.add_argument("--margin-frac", type=float, default=0.05)
    ap.add_argument("--min-radius-px", type=float, default=6.0)
    ap.add_argument("--urdf", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    seeds = list(range(a.seed0, a.seed0 + a.n_seeds))
    out = run(a.profile, a.arm, a.family, a.rule, seeds, a.table_z, a.obj_radius_m, a.margin_frac, a.min_radius_px,
             a.urdf)
    print(json.dumps({k: v for k, v in out.items() if k != "per_seed"}, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
