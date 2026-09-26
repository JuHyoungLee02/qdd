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


def make_world(variant: str, table_z: float, ws, lift, objset=None, furniture=None, reach_path=None):
    from ..astra_motion.world_isaac import CAMS, NO_RENDER, PRE_RENDER, IsaacWorld
    from ..astra_solo.world import SoloWorld
    from ..sim.scene import GRIP_MAX_W, make_env
    from .xlabels import x_info
    if furniture is not None:  # L8-X furniture: no L8 table, furniture slots (helper L8X-assets, 85a37da)
        from ..sim.assets_x import isaac as FX
        FX.without_table(None)

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

        def reset(self, seed, task="mug_tray"):
            if furniture is None:
                IsaacWorld.reset(self, seed, task)
                return
            self._reset_furniture(seed, task)

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
            sc = FU.sample_scene(furniture, seed, reach=self._rm)
            surf, region = fx.choose_surface(sc)
            env.ws = fx.ws_from_region(region)
            tz = float(surf["top_z"])
            env.table_top_z, self.table_z = tz, tz
            SC._LAYOUT["table_z"] = tz
            env.lift = float(sc["lift"])
            rob = env.robot
            li = rob.joint_names.index("lift_joint")
            rob.data.default_joint_pos[0, li] = env.lift
            FX.author_scene(env, sc)
            env.set_seed(seed, task)
            keep = {TASKS[task].target, TASKS[task].place} | {o for st in X_STEPS.get(task, ()) for o in st[:2]}
            lay, dropped = fx.filter_layout(env.layout, surf, keep)
            env.layout = lay
            SC._LAYOUT["layout"] = lay
            self.furniture_scene = fx.summary(sc, surf, region, dropped)
            env.reset()
            perturb(env, "P0", seed)
            for _ in range(PRE_RENDER):
                env.env.sim.render()
            self.pl = OraclePlanner(env)
            self.cmd_quat = np.asarray(self.pl.cmd_quat, float)
            self.quat0 = np.asarray(self.pl.goal_quat, float)
            self.w_close = float(self.pl.w_close)
            self._st = None

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


def vdir(variant: str, table_z: float, lift, furniture=None) -> str:
    return (f"{variant}_tz{float(table_z):.3f}" + ("" if lift is None else f"_lift{float(lift):+.3f}")
            if furniture is None else f"{variant}_fx_{furniture}")


def select_plan(plan: list, variant: str, table_z: float, split: str, objset=None, lift=None, furniture=None) -> list:
    """The plan rows this process runs: same split, variant, objset, lift and table height (or furniture kind)."""
    out = []
    for e in plan:
        if e["variant"] != variant or e.get("split", "train") != split or (e.get("objset") or None) != objset:
            continue
        if furniture is not None:
            if e.get("furniture") != furniture:
                continue
        elif e.get("furniture") is not None or abs(e["table_z"] - table_z) > 1e-6 or \
                (e.get("lift") is not None and (lift is None or abs(e["lift"] - lift) > 1e-6)):
            continue
        out.append(e)
    return out


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
            eps = select_plan(json.load(open(a.plan)), a.variant, a.table_z, a.split, a.objset, a.lift, a.furniture)
        else:
            eps = [{"seed": s, "task": a.task or S.task_of(s)} for s in parse_seeds(a.seeds)]
        for e in eps:
            S.check_seed(e["seed"], a.split, a.confirm_ood)
            if a.task:
                e["task"] = a.task
        vids = {int(v) for v in a.video_seeds.split(",") if v.strip()}
        if a.furniture and a.variant != "standard":
            raise ValueError("furniture scenes: variant standard only (the drx table material / pool distractors "
                             "assume the L8 table)")
        world = make_world(a.variant, a.table_z, ws, a.lift, a.objset, a.furniture, a.reach)
        lim = None
        if a.lift is not None:
            rob = world.env.robot
            i = rob.joint_names.index("lift_joint")
            lim = [round(float(v), 4) for v in rob.data.soft_joint_pos_limits[0, i].cpu().numpy()]
        print("WORLD " + json.dumps({"table_z": world.table_z, "variant": a.variant, "ws": ws, "lift": a.lift,
                                     "lift_limits": lim, "n": len(eps)}), flush=True)
        for e in eps:
            s, task = e["seed"], e["task"]
            od = os.path.join(a.out, a.split, vdir(a.variant, a.table_z, a.lift, a.furniture), f"{task}_s{s}")
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
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)  # SimulationApp.close() hangs in this chroot (astra_solo.run)


if __name__ == "__main__":
    main()
