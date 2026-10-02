"""L9 live (no-cache) runtime: a rt9.Runtime subclass that replaces the per-object candidate cache with the live
antipodal search on the observed point cloud (harvest/l9/live9.py), for a command (point_2d, approach family, rot
bin) that stands in for a VLM instruction (user principle 10-02: at execution time there is no per-object saved
grasp list -- the point / direction / rotation the VLM names is refined near itself, in the live depth cloud).
Opt-in (harvest.l9.run9 --live-exec); nothing here edits rt9.py beyond the one additive `runtime_cls` parameter on
rt9.install (default unchanged) that lets this subclass reuse rt9's hook-wiring unchanged. The production path
(rt9.Runtime via plain rt9.install(...)) stays byte-identical.

Command source (env LIVE_CMD_SOURCE, default "cache"):
  cache -- calls rt9.Runtime.choose() first (the real candidate cache) ONLY to read its label (the commanded
           point_2d / approach family / rot bin, gc.meta) as the stand-in "VLM output" (spec: "feed the truth
           labeller's command ... as the VLM output"). The cached candidate's POSE (gc.T) is then discarded --
           the live search below re-derives the grasp from the observed depth and never executes the cached T.
           Needs GRASP_DIR / TESTED_DIR (the object IS in the cache); this mode compares live vs. cached execution
           on identical commands and seeds (the cache-vs-live A/B).
  gt    -- the command comes from scene ground truth only (the target's own centre -> its head-image pixel,
           grasp9.natural_order's first family, rot bin 0) and never calls rt9.Runtime.choose() at all, so the
           object-level cache is never read. Proves step 7: with L9V2_GRASPS / L9V2_TESTED pointed at an empty
           directory, this mode still finds an executable grasp (the no-npz operation test)."""
from __future__ import annotations

import os

import numpy as np

from . import grasp9 as G
from . import live9 as L
from . import rt9 as RT


class LiveRuntime(RT.Runtime):
    cmd_source = os.environ.get("LIVE_CMD_SOURCE", "cache")

    # ------------------------------------------------------------------ the "VLM" command
    def _command(self, k: str, info: dict, extra_boxes):
        if self.cmd_source == "gt":
            return self._command_gt(k)
        return self._command_cache(k, info, extra_boxes)

    def _command_cache(self, k: str, info: dict, extra_boxes):
        """The cache's own label, read-only: gc.T is never used below (RT.Runtime.choose already ran its full
        validity / reach checks to produce this label, exactly as the production path does; we only borrow the
        point / approach / rot_bin_img it put in gc.meta)."""
        gc = RT.Runtime.choose(self, k, info, extra_boxes=extra_boxes)
        if gc is None or gc.meta.get("point") is None:
            return None
        return (gc.meta["point"], gc.family, int(gc.meta.get("rot_bin_img", 0)), gc.meta.get("category", "") or "",
                float(gc.meta.get("obj_h", 0.0)))

    def _command_gt(self, k: str):
        """No cache read anywhere: scene ground truth stands in for the VLM point, grasp9.natural_order (pure
        geometry, no disk) for the approach family, rot bin 0 for the rotation."""
        from ..astra_motion.geometry import project
        from ..astra_solo.resolve import to_scaled
        from ..sim.scene import OBJ_GEOM
        g = OBJ_GEOM.get(k, {})
        c, _ = self.w.env.object_pose(k)
        he = np.asarray(g.get("half_extents", (0.03, 0.03, 0.05)), float)
        cat = f"{g.get('category', '')} {g.get('name', '')}".lower()
        obj_h = 2 * float(he[2])
        order = G.natural_order(cat, obj_h)
        approach = order[0][0] if order else "top"
        obs = getattr(self.w, "last_obs", None)
        cam = obs.cams.get("head") if obs is not None else None
        if cam is None:
            return None
        u, v, z = project(cam, c)
        if not (z > 0):
            return None
        return (to_scaled(u, v, cam.W, cam.H), approach, 0, cat, obj_h)

    # ------------------------------------------------------------------ perception
    def _wrist_depth(self):
        from .arm import wrist_camera
        obs = getattr(self.w, "last_obs", None)
        cam = obs.cams.get("wrist") if obs is not None else None
        if cam is None:
            return None, None
        try:
            depth = self.w.env.camera_depth(wrist_camera(self.arm))
        except Exception:  # noqa: BLE001  (no wrist depth render on this world: head-only crop)
            return cam, None
        return cam, depth

    def _extra_boxes_tuple(self, k: str):
        """Neighbour objects + furniture as (C, H, R) cuboids (grasp9.obb_overlap convention), the same set
        rt9.Runtime._valid builds for its own collision check (duplicated here, not imported, to keep rt9.py
        untouched beyond the one additive install() parameter)."""
        nb = self.obstacle_boxes(exclude=(k,))
        fs = getattr(self.w, "scene9", {}) or {}
        parts = [p for p in fs.get("furniture", []) if "size" in p and "pos" in p and p.get("role") != "room_wall"]
        bl = [(np.asarray(v[0]), np.asarray(v[1]) / 2, G.qmat(v[2])) for v in nb.values()]
        bl += [(np.asarray(p["pos"], float), np.asarray(p["size"], float) / 2,
                G.qmat(G.yaw_quat(float(p.get("yaw", 0.0))))) for p in parts]
        if not bl:
            return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3, 3))
        return np.array([b[0] for b in bl]), np.array([b[1] for b in bl]), np.array([b[2] for b in bl])

    # ------------------------------------------------------------------ the live choice
    def _dbg(self, msg: str) -> None:
        if os.environ.get("LIVE_DEBUG"):
            print(f"LIVE_DEBUG {msg}", flush=True)

    def choose(self, k: str, info: dict, extra_boxes: dict | None = None):
        cmd = self._command(k, info, extra_boxes)
        if cmd is None:
            self._dbg(f"{k}: no command (cache label step found nothing)")
            self.picks.append({"obj": k, "choice_fail": "no VLM-style command for the live executor"})
            return None
        point_2d, approach, rot_bin, category, obj_h = cmd
        obs = getattr(self.w, "last_obs", None)
        if obs is None or not getattr(obs, "depth", None):
            self.w.observe(depth=True)
            obs = self.w.last_obs
        head_cam = obs.cams.get("head")
        head_depth = (obs.depth or {}).get("head") if getattr(obs, "depth", None) else None
        if head_cam is None or head_depth is None:
            self._dbg(f"{k}: no head depth")
            self.picks.append({"obj": k, "choice_fail": "no head depth to back-project the command"})
            return None
        point3d = L.back_project(point_2d, head_cam, head_depth)
        if point3d is None:
            self._dbg(f"{k}: back-projection failed at point_2d={point_2d}")
            self.picks.append({"obj": k, "choice_fail": "back-projection: no valid depth at the commanded point"})
            return None
        wrist_cam, wrist_depth = self._wrist_depth()
        P, V = L.crop_cloud(point3d, head_cam, head_depth, wrist_cam, wrist_depth)
        if len(P) < L.MIN_PTS:
            self._dbg(f"{k}: crop too small ({len(P)} pts) at point3d={point3d} approach={approach} rot={rot_bin}")
            self.picks.append({"obj": k, "choice_fail": f"live crop too small ({len(P)} points)"})
            return None
        P, V = L.downsample_cap(P, L.MAX_CLOUD, seed=int(getattr(self.w, "vseed", 0) or 0), V=V)
        N = L.estimate_normals(P, view_origin=V)
        self.refresh_world(exclude=(k,), extra_boxes=extra_boxes)
        support_z = self._bottom_z(k)
        f_dir = point3d[:2] - self.T_world_base()[:2, 3]
        extra = self._extra_boxes_tuple(k)
        seed = int(getattr(self.w, "vseed", 0) or 0)
        gc = L.choose_live(P, N, self.grip, approach, rot_bin, point3d, support_z, f_dir, cam=head_cam,
                           category=category, obj_h=obj_h, extra_obstacles=extra, seed=seed, k=len(self.picks))
        if gc is None:
            self._dbg(f"{k}: no live candidate in {len(P)} pts, point3d={point3d} approach={approach} rot={rot_bin}")
            self.picks.append({"obj": k, "choice_fail": "no valid live candidate",
                               "live_cmd": {"approach": approach, "rot_bin": int(rot_bin), "n_cloud": int(len(P))}})
            return None
        ok, _, margin = self.planner.ik(self.to_base(gc.T)[None])
        if not bool(ok[0]):
            self._dbg(f"{k}: live candidate found but cuRobo IK rejected it, approach={approach} rot={rot_bin}")
            self.picks.append({"obj": k, "choice_fail": "live candidate unreachable (cuRobo IK)",
                               "live_cmd": {"approach": approach, "rot_bin": int(rot_bin)}})
            return None
        self._exec_pose(gc, support_z)
        gc.meta.update(obj=k, obj_h=round(obj_h, 4), tested=False, n_candidates=int(len(P)), n_valid=1,
                       curobo=self.curobo, grip=self.grip, live_exec=True, live_cmd_source=self.cmd_source)
        self._Cw, self._ok, self._margin = None, np.ones(1, bool), np.asarray([float(margin[0])])
        return gc

    def next_fallback(self, gc):
        """Simplified vs. rt9's cache fallback (no stored candidate array to re-rank): retry the SAME command once
        with the rot window widened to +-2 bins; otherwise give up (there is no list of alternatives to fall back
        to -- the live search only ever looked near the one commanded point)."""
        if getattr(gc, "_live_retried", False):
            return None, "no reachable live grasp of the commanded point (rot window already widened)"
        k = (self.choice_key or (None,))[0]
        if k is None:
            return None, "no reachable live grasp of the commanded point"
        cmd = self._command(k, self.w.task_info(), None)
        if cmd is None:
            return None, "no reachable live grasp of the commanded point"
        point_2d, approach, rot_bin, category, obj_h = cmd
        obs = self.w.last_obs
        head_cam, head_depth = obs.cams.get("head"), (obs.depth or {}).get("head")
        point3d = L.back_project(point_2d, head_cam, head_depth) if head_depth is not None else None
        if point3d is None:
            return None, "no reachable live grasp of the commanded point"
        wrist_cam, wrist_depth = self._wrist_depth()
        P, V = L.crop_cloud(point3d, head_cam, head_depth, wrist_cam, wrist_depth)
        if len(P) < L.MIN_PTS:
            return None, "no reachable live grasp of the commanded point"
        P, V = L.downsample_cap(P, L.MAX_CLOUD, seed=int(getattr(self.w, "vseed", 0) or 0), V=V)
        N = L.estimate_normals(P, view_origin=V)
        support_z = self._bottom_z(k)
        f_dir = point3d[:2] - self.T_world_base()[:2, 3]
        new = L.choose_live(P, N, self.grip, approach, rot_bin, point3d, support_z, f_dir, cam=head_cam,
                            category=category, obj_h=obj_h, extra_obstacles=self._extra_boxes_tuple(k),
                            seed=int(getattr(self.w, "vseed", 0) or 0), k=len(self.picks), rot_win=2)
        if new is None:
            return None, "no reachable live grasp of the commanded point (rot window already widened)"
        ok, _, _ = self.planner.ik(self.to_base(new.T)[None])
        if not bool(ok[0]):
            return None, "no reachable live grasp of the commanded point (rot window already widened)"
        self._exec_pose(new, support_z)
        new._live_retried = True
        new.meta.update({x: gc.meta.get(x) for x in ("obj", "tested", "n_candidates", "curobo", "grip")})
        return new, "live retry: widened the rot window to +-2 bins"


def install(world, profile: str = "ffw_sg2", arm: str = "right", device: str = "cuda:0", allow_untested=False,
           style=None) -> LiveRuntime:
    """Same hook-wiring as rt9.install (unchanged), with LiveRuntime installed instead of rt9.Runtime.
    LIVE_REFINER=ggx installs harvest.l9.ggx_refine's GraspGenX-backed refiner (live9.set_refiner) bound to this
    arm; unset (default) leaves live9's refiner hook empty, so choose_live uses only its own antipodal search --
    the A/B switch between the two is this one env var, no code change."""
    if os.environ.get("LIVE_REFINER") == "ggx":
        from . import ggx_refine as GGX
        L.set_refiner(GGX.make_refiner(arm))
    else:
        L.set_refiner(None)
    return RT.install(world, profile, arm, device=device, allow_untested=allow_untested, style=style,
                      runtime_cls=LiveRuntime)
