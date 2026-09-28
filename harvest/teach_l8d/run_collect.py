"""L8-D collection runner (pod, Isaac; one process = one variant x one table height [x one lift]):
python -m harvest.teach_l8d.run_collect --split train|gate|ood_h|ood_o|ood_d --variant standard|drx|randx
  --table-z 0.84 --ws-x 0.37,0.49 [--lift -0.0993] --seeds 30000-30099 | --plan plan.json [--confirm-ood] [--clean]
  [--video-seeds 30001,30007] [--out ...]
--plan: a JSON list of episodes (spec.plan_train rows); only rows matching this process's (variant, table_z) run.
Style per seed: 'clean' (p = 0) with probability 0.25 (teach_l8.run_collect.style_of, same as L8) or --clean for all
(gate G-H). Output <out>/<split>/<variant>_tz<z>[_lift<l>]/<task>_s<seed>/ (calls/, result.json, labels.jsonl,
meta.json, scene.json, frames/ for video seeds); finished episodes are skipped (resume)."""
from __future__ import annotations

import argparse
import json
import os
import time

OUT = "/data/harvest/out/teach_l8d/collect"


def make_world(variant: str, table_z: float, ws, lift, objset=None, furniture=None, reach_path=None,
               mesh_split: str = "train", rooms_split: str | None = None, clutter_pool: dict | None = None):
    import os

    from ..astra_motion.world_isaac import CAMS, NO_RENDER, PRE_RENDER, IsaacWorld
    from ..astra_solo.world import SoloWorld
    from ..sim.scene import GRIP_MAX_W, make_env
    from .xlabels import x_info
    mesh = None
    l8s = variant == "drf"  # L8S render rules (changes 17-18): head, exposure, materials, HDRIs, gated pieces
    if furniture is not None:  # L8-X furniture: no L8 table, furniture slots (helper L8X-assets, 85a37da)
        from ..sim.assets_x import isaac as FX
        from . import fx as _fx
        if _fx.is_mesh_kind(furniture):  # licensed mesh pieces (THOR / cyclo_lab): only this kind's pieces
            d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim", "assets_x")
            mesh = _fx.mesh_subset(_fx.load_mesh_assets(d), furniture, mesh_split)
            if l8s:  # L8S (change 17): only the pieces that passed the helper's per-piece gate
                mesh = _fx.passed_pieces(mesh)
            if not mesh:
                raise ValueError(f"no {mesh_split} mesh pieces for {furniture}")
        rooms = None
        if rooms_split:  # iTHOR room backgrounds (render only; helper 5473bb8), this split only
            d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim", "assets_x")
            rooms = _fx.rooms_of(d, rooms_split)
        FX.without_table(mesh, rooms)

    class L8DWorld(SoloWorld):
        """SoloWorld (depth on) with the R2 tasks, one table height, the height's workspace box and the lift flag;
        objset "x" adds the L8-X objects and tasks (task_info then carries the support heights, xlabels)."""

        def __init__(self):  # = SoloWorld.__init__ + ws / lift / objset
            self.variant, self.depth = variant, True
            self.env = make_env(0, headless=True, cameras=CAMS, depth=True, render_interval=NO_RENDER,
                                variant=variant, table_z=float(table_z), ws=ws, lift=lift, objset=objset)
            self.dt = float(self.env.step_dt)
            self.table_z = float(self.env.table_top_z)
            self.w_open = float(GRIP_MAX_W)
            self._st = None
            self.last_obs = None
            if l8s and furniture is not None:  # L8S: head pitch 0.785 (+10 deg) above the URDF's 0.6951
                self._head_limit()

        def _head_limit(self, upper: float = 1.0):
            import torch
            rob = self.env.robot
            if "head_joint1" not in rob.joint_names:
                return
            j = rob.joint_names.index("head_joint1")
            lim = rob.data.soft_joint_pos_limits[0, j].clone() if hasattr(rob.data, "soft_joint_pos_limits") else None
            lo = float(lim[0]) if lim is not None else -0.2317
            limits = torch.tensor([[[lo, upper]]], device=rob.device)
            fn = getattr(rob, "write_joint_position_limit_to_sim", None) or getattr(rob, "write_joint_limits_to_sim")
            fn(limits, joint_ids=[j])

        def reset(self, seed, task="mug_tray"):
            if furniture is None:
                if clutter_pool:  # b3 clutter (change 11): real objects around the task layout, set with the layout
                    env, set_seed = self.env, self.env.set_seed

                    def with_clutter(sd, tk, *a, **k):
                        set_seed(sd, tk, *a, **k)
                        self._apply_clutter(sd, tk)
                    env.set_seed = with_clutter
                    try:
                        IsaacWorld.reset(self, seed, task)
                    finally:
                        del env.set_seed
                    return
                IsaacWorld.reset(self, seed, task)
                return
            self._reset_furniture(seed, task)

        def _apply_clutter(self, seed, task):
            from ..sim import scene as SC
            from ..sim.randomize import sample_randomization
            from ..sim.tasks import layout_paths
            from .clutter_x import add_clutter
            env = self.env
            fr = {k: SC.OBJ_GEOM[k]["footprint_r"] for k in env.layout}
            lay, placed = add_clutter(env.layout, seed, clutter_pool, ws, fr)
            env.layout = SC._LAYOUT["layout"] = lay
            env.randomization = SC._LAYOUT["rand"] = sample_randomization(seed, env.variant, lay,
                                                                          path=layout_paths(task, "task"))
            self.clutter_scene = {"n": len(placed), "ids": [p["id"] for p in placed]}

        def _reset_furniture(self, seed, task):
            """= IsaacWorld.reset with a furniture scene: sample it, work on its best surface (fx.choose_surface),
            author the parts (USD, applied by the hard reset), set the scene's lift as the lift joint default."""
            import numpy as np

            from ..sim import scene as SC
            from ..sim.assets_x import furniture as FU
            from ..sim.assets_x import isaac as FX
            from ..sim.assets_x.reach import ReachModel
            from ..sim.perturb import perturb
            from ..sim.planner import OraclePlanner
            from ..sim.tasks import TASKS, X_STEPS
            from . import fx
            env = self.env
            if not hasattr(self, "_rm"):
                self._rm = ReachModel.load(reach_path)
            from ..sim.tasks import X_FURNITURE_TASKS
            sc = FU.sample_scene(furniture, seed, reach=self._rm, mesh_assets=mesh, split=mesh_split, rooms=rooms)
            upper, vid = None, TASKS[task].place
            if task in X_FURNITURE_TASKS or vid in SC.VIRTUAL_PLACES:  # cross-surface: o19 = a higher surface, o20 = a container's floor
                pick = fx.choose_container if vid == "o20" else fx.choose_two_surfaces
                surf, region, upper, uregion = pick(sc)
                if float(upper["top_z"]) < float(surf["top_z"]) + 0.02 - 0.03:  # executor box: z >= table + 2.5 cm
                    raise fx.SkipScene(f"place surface {upper['id']} lower than the work surface")
                env.set_virtual_surface(vid, float(upper["top_z"]), uregion)
            else:
                surf, region = fx.choose_surface(sc)
            env.ws = fx.ws_from_region(region)
            if l8s and env.ws[0][1] - env.ws[0][0] >= 0.16:  # audit P5: not at the image's bottom edge
                env.ws = ((env.ws[0][0] + 0.04, env.ws[0][1]), env.ws[1])
            tz = float(surf["top_z"])
            env.table_top_z, self.table_z = tz, tz
            SC._LAYOUT["table_z"] = tz
            env.lift = float(sc["lift"])
            rob = env.robot
            li = rob.joint_names.index("lift_joint")
            rob.data.default_joint_pos[0, li] = env.lift
            # the hard reset re-initialises the articulation from cfg.init_state (default_joint_pos alone was reset
            # to the INIT_JOINTS lift: measured -0.125 in every scene, L8X-assets finding): set it there too
            rob.cfg.init_state.joint_pos["lift_joint"] = env.lift
            head = None
            from .clutter_x import HEAD_TILT0
            if l8s:  # L8S change 17: head 0.785 rad (45 deg, the real robot); ~15 % get a small pan / tilt
                from .clutter_x import head_pose
                head = head_pose(seed)
                for jn, v in (("head_joint1", head["tilt"]), ("head_joint2", head["pan"])):
                    if jn in rob.joint_names:
                        rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                        rob.cfg.init_state.joint_pos[jn] = v
            FX.author_scene(env, sc, mesh, rooms)
            if l8s and os.environ.get("L8S_ISO"):  # calibration runs only: the tonemapper's film ISO
                import carb
                carb.settings.get_settings().set("/rtx/post/tonemap/filmIso", float(os.environ["L8S_ISO"]))
            if l8s:
                self._retexture(seed, sc)
            try:
                env.set_seed(seed, task)
            except RuntimeError as ex:  # task_layout found no layout in this box
                raise fx.SkipScene(f"layout: {ex}") from ex
            if l8s and getattr(self, "_hdr", None) and env.randomization.get("hdr"):
                env.randomization["hdr"].update(file=self._hdr, name=os.path.basename(self._hdr))
            from ..sim.tasks import X_BETWEEN, X_REL
            keep = {TASKS[task].target, TASKS[task].place} | {o for st in X_STEPS.get(task, ()) for o in st[:2]}
            if task in X_REL:  # relational placement: keep its reference object (and its spot)
                keep |= {X_REL[task][0], X_REL[task][1]}
            if task in X_BETWEEN:  # between two references: keep both and the spot
                keep |= set(X_BETWEEN[task])
            lay, dropped = fx.filter_layout(env.layout, surf, keep)
            if upper is not None:  # the place surface centre (its region, not the layout box)
                lay[vid] = ((uregion[0][0] + uregion[0][1]) / 2, (uregion[1][0] + uregion[1][1]) / 2, 0.0)
            if clutter_pool:  # b4 (change 12): real clutter on the work surface, clear of the layout
                from .clutter_x import add_clutter
                # realistic scenes: no primitive extras (red mug / bottle / box) besides the task's own objects
                lay = {k: v for k, v in lay.items() if k in keep or k in SC.VIRTUAL_PLACES or k in SC.OBJV_IDS}
                from .clutter_x import add_confusers
                from ..astra_motion.prompts import OBJ_NAME
                fr = {k: SC.OBJ_GEOM[k]["footprint_r"] for k in lay}
                taken = {" ".join(str(OBJ_NAME.get(k, k)).lower().split()) for k in lay}  # audit P2: unique names
                # change 16: ~20 % of episodes get look-alikes of the target (same colour, similar size) near it
                lay, conf = add_confusers(lay, seed, TASKS[task].target, TASKS[task].place, clutter_pool, fr,
                                          surf["xy_box"], taken_names=taken)
                fr = {k: SC.OBJ_GEOM[k]["footprint_r"] for k in lay}
                lay, placed = add_clutter(lay, seed, clutter_pool, env.ws, fr, surface=surf, arrange=True,
                                          taken_names=taken)
                self.clutter_scene = {"n": len(placed), "ids": [p["id"] for p in placed], "confusers": conf,
                                      "arr": {a: sum(p.get("arr") == a for p in placed) for a in ("display", "stack")}}
            env.layout = lay
            SC._LAYOUT["layout"] = lay
            self.furniture_scene = fx.summary(sc, surf, region, dropped)
            self.furniture_scene["room"] = (sc.get("room") or {}).get("name")  # audit P6: record the room
            if head is not None:
                self.furniture_scene["head"] = head
            if upper is not None:
                self.furniture_scene["place_surface"] = {"id": upper["id"], "kind": upper.get("kind"),
                                                         "top_z": upper["top_z"], "region": uregion}
            env.reset()
            fx.check_lift(env.lift, float(rob.data.joint_pos[0, li]))  # SkipScene (skipped.json), job goes on
            perturb(env, "P0", seed)
            for _ in range(PRE_RENDER):
                env.env.sim.render()
            if l8s:  # audit P1: auto exposure (film ISO), an episode still > 10 % saturated is skipped
                self.furniture_scene["iso"] = self._auto_exposure()
            if head is not None and head["random"] and not self._head_sees(lay, task, tz, upper):
                # change 17: a random head pose is used only when the object and its destination stay in view
                for jn, v in (("head_joint1", HEAD_TILT0), ("head_joint2", 0.0)):
                    if jn in rob.joint_names:
                        rob.data.default_joint_pos[0, rob.joint_names.index(jn)] = v
                        rob.cfg.init_state.joint_pos[jn] = v
                head.update(tilt=HEAD_TILT0, pan=0.0, random=False, fallback=True)
                env.reset()
                perturb(env, "P0", seed)
                for _ in range(PRE_RENDER):
                    env.env.sim.render()
            self.pl = OraclePlanner(env)
            self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
            self.quat0 = np.asarray(self.pl.goal_quat, float)
            self.w_close = float(self.pl.w_close)
            self._st = None

        def _materials(self):
            """L8S change 17: one Poly Haven CC0 material per mesh piece and per cuboid slot (bound once, visual
            only); per episode retextured from the train split. -> (catalog, {prim path: material path})."""
            if hasattr(self, "_mats"):
                return self._mats
            import omni.usd

            from ..sim.assets_x import isaac as FX
            from ..sim.assets_x import materials as M
            stage = omni.usd.get_context().get_stage()
            cat = M.usable(M.load())
            first = M.pick(cat, "furniture", 0)
            paths = {}
            prims = [FX._mesh_path(n) for n in sorted(mesh or {})] + [FX._slot_path(i) for i in range(FX.N_SLOTS)]
            for i, p in enumerate(prims):
                prim = stage.GetPrimAtPath(p)
                if not prim.IsValid():
                    continue
                mp = f"/World/Looks/l8s_{i}"
                M.bind(prim, M.author(stage, mp, first))
                paths[p] = mp
            self._mats = (cat, paths, M.hdr_paths(cat, "train"))
            return self._mats

        def _retexture(self, seed, sc):
            import hashlib

            import omni.usd

            from ..sim.assets_x import materials as M
            cat, paths, hdrs = self._materials()
            stage = omni.usd.get_context().get_stage()
            n_furn = sum(1 for p in sc["furniture"] if p.get("usd") is None)
            for j, (p, mp) in enumerate(sorted(paths.items())):
                role = "wall" if "/FX_" in p and int(p.rsplit("_", 1)[1]) >= n_furn else "furniture"
                M.retexture(stage, mp, M.pick(cat, role, int(seed) * 97 + j))
            if hdrs:  # change 17: Poly Haven indoor HDRIs (train split) replace the pool's dome maps
                h = hdrs[int(hashlib.sha256(f"l8s-hdr:{int(seed)}".encode()).hexdigest()[:8], 16) % len(hdrs)]
                self._hdr = h

        def _sat(self):
            import numpy as np
            rgb = self.env.scene["cam_head"].data.output["rgb"][0].cpu().numpy()[..., :3].astype(float)
            return float((rgb.max(axis=2) >= 250).mean()), float(rgb.mean())

        def _auto_exposure(self) -> dict:
            import carb

            from . import fx
            from .clutter_x import DARK_MEAN, ISO0, SAT_MAX
            st = carb.settings.get_settings()
            e = float((self.env.randomization.get("lighting") or {}).get("exposure", 1.0))
            iso = float(os.environ.get("L8S_ISO") or ISO0 * e)
            for k in range(6):
                st.set("/rtx/post/tonemap/filmIso", iso)
                for _ in range(PRE_RENDER):
                    self.env.env.sim.render()
                sat, mean = self._sat()
                if sat > SAT_MAX:
                    iso *= 0.6
                elif mean < DARK_MEAN:
                    iso *= 1.6
                else:
                    return {"iso": round(iso, 2), "sat": round(sat, 4), "mean": round(mean, 1), "tries": k + 1}
            raise fx.SkipScene(f"exposure not fixed: {sat:.3f} saturated, mean {mean:.0f}, ISO {iso:.1f}")

        def _head_sees(self, lay, task, tz, upper, margin: float = 0.05) -> bool:
            """Target and destination project inside the head image (5 % margin) at the current head pose."""
            from ..astra_motion import geometry as G
            from ..sim.tasks import TASKS
            cam = self._cam("cam_head", "head")
            s = TASKS[task]
            pts = [(lay[s.target][0], lay[s.target][1], tz + 0.03)]
            if s.place in lay:
                pz = float(upper["top_z"]) if upper is not None and s.place == "o19" else tz
                pts.append((lay[s.place][0], lay[s.place][1], pz + 0.01))
            for p in pts:
                u, v, z = G.project(cam, p)
                if not (z > 0 and margin * cam.W <= u <= (1 - margin) * cam.W
                        and margin * cam.H <= v <= (1 - margin) * cam.H):
                    return False
            return True

        def task_info(self):
            from ..sim.tasks import X_STEPS
            if self.env.task in X_STEPS:
                return self.step_info(0)
            return x_info(self.env, IsaacWorld.task_info(self))

        def step_info(self, k: int):
            """Multi-step task: step k's info (target / place / offset + support heights)."""
            from ..sim.tasks import X_STEPS
            from .multistep import step_info
            return x_info(self.env, step_info(IsaacWorld.task_info(self), X_STEPS[self.env.task], k))

    return L8DWorld()


def vdir(variant: str, table_z: float, lift, furniture=None, clutter: bool = False) -> str:
    return (f"{variant}_tz{float(table_z):.3f}" + ("" if lift is None else f"_lift{float(lift):+.3f}")
            + ("_cl" if clutter else "") if furniture is None else f"{variant}_fx_{furniture}")


def select_plan(plan: list, variant: str, table_z: float, split: str, objset=None, lift=None, furniture=None,
                clutter: bool = False) -> list:
    """The plan rows this process runs: same split, variant, objset, lift, clutter flag and table height (or
    furniture kind)."""
    out = []
    for e in plan:
        if e["variant"] != variant or e.get("split", "train") != split or (e.get("objset") or None) != objset:
            continue
        if bool(e.get("clutter")) != bool(clutter):
            continue
        if furniture is not None:
            if e.get("furniture") != furniture:
                continue
        elif e.get("furniture") is not None or abs(e["table_z"] - table_z) > 1e-6 or \
                (e.get("lift") is not None and (lift is None or abs(e["lift"] - lift) > 1e-6)):
            continue
        out.append(e)
    return out


class _DrawerDone(Exception):
    """The dr__ path finished (run_drawer printed RUN_DONE)."""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--table-z", type=float, required=True)
    ap.add_argument("--ws-x", required=True, help="x0,x1 of the height's workspace box (gate G-H)")
    ap.add_argument("--lift", type=float, default=None)
    ap.add_argument("--objset", default=None, help="x = L8-X objects and tasks")
    ap.add_argument("--furniture", default=None, help="L8-X furniture kind (harvest.sim.assets_x.furniture.KINDS)")
    ap.add_argument("--reach", default="/data/harvest/out/teach_l8d/gate/reach_base.json")
    ap.add_argument("--rooms", action="store_true", help="iTHOR room backgrounds (furniture scenes)")
    ap.add_argument("--clutter", type=int, default=0, help="b3: pool size of real clutter objects (0 = none)")
    ap.add_argument("--seeds", default=None)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--task", default=None, help="override the per-seed task (gate / OOD sets)")
    ap.add_argument("--confirm-ood", action="store_true")
    ap.add_argument("--clean", action="store_true", help="every episode clean (p = 0): gate G-H")
    ap.add_argument("--video-seeds", default="")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--p", type=float, default=0.35)
    ap.add_argument("--max-perturb", type=int, default=4)
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    ap.add_argument("--drawer-list", default=None, help="dr__ tasks (L8-X drawer, xdrawer_ep): the frozen list")
    ap.add_argument("--piece", default=None, help="dr__ tasks: this process's piece (one articulated scene)")
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..sim import randomize as R
        from ..teach_l8.run_collect import parse_seeds, style_of
        from . import spec as S
        from .collect import collect_episode
        from .fx import SkipScene
        if a.split == "train":
            R.check_train_variant(a.variant)
        if a.variant == "randx" and a.split != "ood_d":
            raise ValueError("variant randx (TEST_X pool) is for split ood_d only")
        x0, x1 = (float(v) for v in a.ws_x.split(","))
        ws = S.ws_of((x0, x1))
        if a.plan:
            eps = select_plan(json.load(open(a.plan)), a.variant, a.table_z, a.split, a.objset, a.lift, a.furniture,
                              bool(a.clutter))
        else:
            eps = [{"seed": s, "task": a.task or S.task_of(s)} for s in parse_seeds(a.seeds)]
        for e in eps:
            S.check_seed(e["seed"], a.split, a.confirm_ood)
            if a.task:
                e["task"] = a.task
        vids = {int(v) for v in a.video_seeds.split(",") if v.strip()}
        from .xdrawer_ep import is_drawer_run
        if is_drawer_run(eps):  # L8-X drawer (prereg_l8x_tasks change 12): its own world / episode, dr__ only
            from .xdrawer_ep import run_drawer
            run_drawer(a, eps, vids)
            raise _DrawerDone
        from ..sim.objv import register_for_tasks  # L8-X mesh objects used by this process (before make_env)
        objv_ids = register_for_tasks([e["task"] for e in eps])
        pool = None
        if a.clutter:  # b3 clutter objects of this process (prims before make_env), change 11
            if a.objset != "x":
                raise ValueError("--clutter: --objset x only")
            from ..sim.objv import register
            from .clutter_x import load_real, pool_for
            key = f"{a.variant}|{a.table_z:.3f}|{a.lift}" + (f"|{a.furniture}" if a.furniture else "")
            rows_real = load_real()
            pool = pool_for(rows_real, key, n=a.clutter, n_base=12 if a.furniture else 0)
            if a.furniture:  # change 16: the look-alikes of this process's real targets join the pool
                from ..sim.tasks import TASKS as _T
                from .clutter_x import confuser_ids
                for e in eps:
                    t = _T.get(e["task"])
                    if t is not None and t.target in rows_real:
                        pool.update({k: rows_real[k] for k in confuser_ids(rows_real, t.target)})
            register(pool)
        if a.furniture and a.variant not in ("standard", "drf"):
            raise ValueError("furniture scenes: variant standard or drf (drx: the table material / pool distractors "
                             "assume the L8 table)")
        if a.variant == "drf" and not a.furniture:
            raise ValueError("variant drf: furniture scenes only (L8 table scenes use drx)")
        world = make_world(a.variant, a.table_z, ws, a.lift, a.objset, a.furniture, a.reach,
                           "ood" if a.split == "ood_s" else "train",
                           ("ood" if a.split == "ood_s" else "train") if a.rooms else None, pool)
        lim = None
        if a.lift is not None:
            rob = world.env.robot
            i = rob.joint_names.index("lift_joint")
            lim = [round(float(v), 4) for v in rob.data.soft_joint_pos_limits[0, i].cpu().numpy()]
        print("WORLD " + json.dumps({"table_z": world.table_z, "variant": a.variant, "ws": ws, "lift": a.lift,
                                     "lift_limits": lim, "n": len(eps)}), flush=True)
        for e in eps:
            s, task = e["seed"], e["task"]
            od = os.path.join(a.out, a.split, vdir(a.variant, a.table_z, a.lift, a.furniture, bool(a.clutter)),
                              f"{task}_s{s}")
            if os.path.exists(os.path.join(od, "meta.json")) or os.path.exists(os.path.join(od, "skipped.json")):
                continue
            style = "clean" if a.clean else style_of(s, S.CLEAN_SHARE)
            t0 = time.perf_counter()
            try:
                meta = collect_episode(world, s, task, a.variant, a.split, od, 0.0 if style == "clean" else a.p,
                                       a.max_perturb, a.stop_calls, a.stop_motion, style, video=s in vids)
            except SkipScene as ex:  # furniture scene without a usable surface for this task
                os.makedirs(od, exist_ok=True)
                json.dump({"seed": s, "task": task, "reason": str(ex)}, open(os.path.join(od, "skipped.json"), "w"))
                print("SKIP " + json.dumps({"seed": s, "task": task, "reason": str(ex)}), flush=True)
                continue
            print("EP " + json.dumps(dict(meta, wall_total_s=round(time.perf_counter() - t0, 1))), flush=True)
        print("RUN_DONE", flush=True)
    except _DrawerDone:
        pass
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)  # SimulationApp.close() hangs in this chroot (astra_solo.run)


if __name__ == "__main__":
    main()
