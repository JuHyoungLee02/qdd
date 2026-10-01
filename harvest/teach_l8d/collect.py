"""L8-D collection (prereg_l8d.md §2): the E-PT collection path (teach_pt.collect.PtCollector inside a PtEpisode: the
L8 behaviour policy = truth labels + DART-style perturbations, depth on; every call saves the astra-solo@v2 request
(prompt_v2.txt + grid overlay PNG), the three no-grid ND requests (+ ring-only PNG), the point request, head depth and
cameras) so the training format (grid on/off, hand-given info on/off, depth on/off) is chosen at build time.
Per episode it adds scene.json: table height, lift, workspace box, variant, task, layout, randomization (materials,
lights, distractors with the settled offsets) and the distractor count. Pure except the world handed in."""
from __future__ import annotations

import json
import os

import numpy as np

from ..astra_solo.pt_episode import PtEpisode
from ..teach_l8 import collect as LC
from ..teach_pt.collect import PtCollector

SCENE_SCHEMA = "qdd.l8d.scene/v1"


_OCC_MAX = 0.5
_SAT_MAX = 0.10


def _sat(w):
    """Saturated share of this call's head frame (max channel >= 250); None without an RGB head frame."""
    obs = getattr(w, "last_obs", None)
    rgb = getattr(obs, "rgb", None) if obs is not None else None
    if not rgb or "head" not in rgb:
        return None
    a = np.asarray(rgb["head"])[..., :3]
    return round(float((a.max(axis=2) >= 250).mean()), 4)


def _occ(w, st, info, lab):
    """Occluded share of the current step's point object (target while approaching / grasping, else the
    destination) in this call's head frame; None without depth (non-L8S worlds)."""
    obs = getattr(w, "last_obs", None)
    if lab is None or obs is None or not getattr(obs, "depth", None) or "head" not in obs.depth:
        return None
    from ..sim import scene as SC
    from .clutter_x import container_boxes, occlusion
    k = info["tgt"] if lab.get("phase") == "approach" else info["place"]
    own = container_boxes(getattr(w, "env", None), info["place"])  # change 28: the destination is not an occluder
    if k not in st["obj"] or k not in SC.OBJ_GEOM:
        return None
    g = SC.OBJ_GEOM[k]
    he = g.get("half_extents", (g.get("radius", 0.03),) * 3)
    p = np.asarray(st["obj"][k], float)
    top = p[2] + (he[2] if g.get("shape") not in ("marker", "surface") else 0.0)
    return round(occlusion(obs.cams["head"], obs.depth["head"], p[:2], 0.6 * min(he[0], he[1]), top, ignore=own), 3)


class _XLabels(LC.Collector):
    """teach_l8.collect.Collector.ask with the support-aware labels (xlabels.label == labels.label on one table)."""

    def ask(self, text, images, meta):
        from ..astra_motion.truth import Rep
        from ..teach_l8 import behavior as B
        from ..teach_l8 import labels as L
        from . import xlabels as XL
        ep, w = self.ep, self.w
        st, info = w.status(), ep.info
        last = ep.history[-1] if ep.history else ""
        lab = XL.label(st, info, w.table_z, getattr(w, "w_open_label", w.w_open), first=not ep.history, last_line=last,
                       prev_failed=self.prev_failed)
        cams = w.last_obs.cams if getattr(w, "last_obs", None) is not None else {}
        tgt = np.asarray(st["obj"][info["tgt"]], float)
        drop = "tipped" if lab is None else ("not_visible" if cams and not LC.visible(cams, tgt) else None)
        if drop is None and lab["step"] == "done" and st["pred"].get(f"upright({info['tgt']})") is False:
            drop = "tipped"  # change 28 (audit 4): "done" only with the judge's upright (success_now)
        if drop is None and L.stuck(last, self.prev_cmd, lab["command"]):
            drop = "stuck"
        occ = _occ(w, st, info, lab)
        if drop is None and occ is not None and occ >= _OCC_MAX:  # change 20: the step's point is hidden
            drop = "occluded"
        sat = _sat(w)
        if drop is None and sat is not None and sat > _SAT_MAX:  # change 22 (audit 3): exposure on every call
            drop = "overexposed"
        row = {"call": meta["call"], "site": meta["site"], "prev_kind": self.prev_kind, "drop": drop,
               "gt": {"tgt": LC._l(tgt), "place": LC._l(st["obj"][info["place"]]), "tcp": LC._l(st["tcp"]),
                      "grip_w": round(float(st["grip_w"]), 4),
                      "others": {k: LC._l(v) for k, v in st["obj"].items() if k not in (info["tgt"], info["place"])}},
               "ex_target": LC._l(ep.ex.target), "drawn": list(getattr(ep, "drawn", [])),
               "tgt": info["tgt"], "place": info["place"], "occ": occ, "sat": sat}
        if lab is None:
            row.update(step="tipped", phase="tipped", status=None, answer=None, exec_kind="stop")
            self.rows.append(row)
            return Rep(json.dumps({"assessment": LC._stub(), "command": {"mode": "stop"}, "reason": "tipped"}))
        row.update(step=lab["step"], phase=lab["phase"], status=lab["status"], answer=lab["answer"])
        if info.get("kind") == "push":
            row["held"] = st["pred"].get(f"holding({info['tgt']})") is True  # new-task judges (xnew)
        H = XL.heights(info, w.table_z)
        # behaviour perturbations are relative to the pick surface (= the table on one-table tasks)
        c = B.Ctx(state=st, info=info, table_z=H["sup_tgt"], step=lab["step"], label_cmd=lab["command"])
        cmd, kind = B.choose(self.rng, c, self.p if self.n_pert < self.max_perturb else 0.0)
        self.n_pert += kind != "clean"
        row["exec_kind"] = kind
        self.rows.append(row)
        self.prev_kind, self.prev_failed, self.prev_cmd = kind, lab["status"] == "failed", cmd
        a = json.loads(lab["answer"])
        return Rep(json.dumps({"assessment": a["assessment"], "command": cmd, "reason": kind}))


class XCollector(PtCollector, _XLabels):
    """PtCollector (pt / ND labels, pixels, robot-side state) on top of the support-aware L8 collector."""
    name = "l8x_behavior"


def _jl(v):
    if isinstance(v, dict):
        return {str(k): _jl(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jl(x) for x in v]
    if isinstance(v, (np.floating, float)):
        return round(float(v), 5)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.ndarray):
        return _jl(v.tolist())
    return v


def distractor_count(layout: dict, info: dict, randomization: dict | None) -> dict:
    """Obstacles on the table: layout objects other than target / place (the scene's o3 / o5 / o8 / o9) + pool
    distractors actually placed (randomize.sample_randomization)."""
    lay = [k for k in layout if k not in (info["tgt"], info["place"])]
    pool = [d["name"] for d in ((randomization or {}).get("distractors") or [])]
    return {"n": len(lay) + len(pool), "layout_objects": lay, "pool_distractors": pool}


def scene_record(world, seed: int, task: str, variant: str, split: str, style: str) -> dict:
    env = getattr(world, "env", None)  # None in the pure fake world (tests)
    info = world.task_info()
    rand = getattr(env, "randomization", None)
    layout = dict(getattr(env, "layout", None) or {k: None for k in info.get("present", [])})
    lift_q = None
    rob = getattr(env, "robot", None)
    if rob is not None and "lift_joint" in rob.joint_names:
        lift_q = float(rob.data.joint_pos[0, rob.joint_names.index("lift_joint")])
    return _jl({"schema": SCENE_SCHEMA, "seed": seed, "split": split, "task": task, "variant": variant,
                "style": style, "instruction": info["instruction"],
                "table_z": float(getattr(env, "table_top_z", world.table_z)),
                "lift": getattr(env, "lift", None), "lift_joint_measured": lift_q,
                "ws": getattr(env, "ws", None), "layout": layout,
                "randomization": rand, "rand_settle": getattr(env, "rand_settle", None),
                "steps": _steps(task), "furniture": getattr(world, "furniture_scene", None),
                "clutter": getattr(world, "clutter_scene", None),
                "surface": (getattr(world, "furniture_scene", None) or {}).get("kind", "table"),
                "distractors": distractor_count(layout, info, rand)})


def _steps(task: str):
    from ..sim.tasks import X_STEPS
    return [list(s[:2]) for s in X_STEPS[task]] if task in X_STEPS else None


def save_joints(world, out_dir: str, meta: dict) -> None:
    """L8S joints.npz + meta max_dq_rad / max_dq_finger_rad from world._jlog (change 20; change 30: shared with
    the drawer runner). No-op without a joint log."""
    import numpy as np

    jl = getattr(world, "_jlog", None)
    if jl:  # change 20 (audit 2): every physics step's joint angles (jump check <= 0.04 rad / frame)
        q = np.asarray(jl, np.float32)
        bl = getattr(world, "_blog", None) or []
        al = getattr(world, "_alog", None) or []
        tl = getattr(world, "_tlog", None) or []
        world._alog, world._tlog = [], []
        np.savez_compressed(os.path.join(out_dir, "joints.npz"), q=q, base=np.asarray(bl, np.float32),
                            arm_cmd_offset_ik=np.asarray(al, np.float32), arm_ids=np.asarray([int(i) for i in world.env.arm_ids]),
                            arm_target_torque_vel=np.asarray(tl, np.float32),
                            arm_kd_effort=np.asarray([getattr(world.env.robot.data, k)[0, world.env.arm_ids].cpu().numpy()
                                                      for k in ("joint_stiffness", "joint_damping", "joint_effort_limits")
                                                      if hasattr(world.env.robot.data, k)], np.float32),
                            names=np.asarray(world.env.robot.joint_names), dt=float(world.dt))
        world._blog = []

        names = list(world.env.robot.joint_names)
        d = np.abs(np.diff(q, axis=0)) if len(q) > 1 else np.zeros((1, len(names)))
        side = "l" if getattr(world, "arm", "right") == "left" else "r"  # L9 left-arm worlds (opt-in attribute)
        jp, fp = getattr(world, "joint_prefixes", None) or (f"arm_{side}_joint", f"gripper_{side}")  # L9 robot profile
        arm = [i for i, n in enumerate(names) if n.startswith(jp)]
        fing = [i for i, n in enumerate(names) if n.startswith(fp)]
        meta["max_dq_rad"] = round(float(d[:, arm].max()) if arm else float(d.max()), 4)  # the used arm (<= 0.04)
        meta["max_dq_finger_rad"] = round(float(d[:, fing].max()), 4) if fing else None  # fingers: excluded
        world._jlog = []


def collect_episode(world, seed: int, task: str, variant: str, split: str, out_dir: str, p: float,
                    max_perturb: int = 4, stop_calls: int | None = 30, stop_motion_s: float | None = 120.0,
                    style: str = "", video: bool = False) -> dict:
    """= teach_pt.collect.collect_episode (same rng stream, collector, limits) + scene.json and an optional sparse
    video (Episode video=True: head | right wrist jpgs every 5 control ticks)."""
    rng = np.random.default_rng([int(seed), 8, LC.VARIANT_CODE.get(variant, 9)])
    from ..sim.tasks import X_STEPS
    from .multistep import XEpisode
    from . import xnew
    if xnew.is_new_task(task):  # judge-stage name gate + the per-seed phrasing (prereg_l8x_tasks 2.5 / 2.1-2.2)
        import dataclasses

        from ..astra_motion.prompts import OBJ_NAME
        from ..sim import tasks as T
        from .fx import SkipScene
        rows = xnew.load_real_rows()
        others = [OBJ_NAME.get(k, k) for k in ("o3",) + tuple(T.TASKS[task].extras)]
        why = xnew.name_gate(task, rows, others)
        if why:
            raise SkipScene(why)
        txt = xnew.instruction(task, rows, xnew.text_index(task, seed, ood=split.startswith("ood")))
        T.TASKS[task] = T.X_TASKS[task] = dataclasses.replace(T.TASKS[task], instruction=txt)
    coll = XCollector(world, rng, p, max_perturb)
    kw = dict(variant=variant, stop_calls=stop_calls, stop_motion_s=stop_motion_s, allow_eef=True, save_v2=True,
              save_nd=True, video=video)
    if task in X_STEPS:  # multi-step: twice the call / motion budget of the runner (the prompt limits unchanged)
        kw.update(stop_calls=None if stop_calls is None else 2 * stop_calls,
                  stop_motion_s=None if stop_motion_s is None else 2 * stop_motion_s)
        ep = XEpisode(world, coll, seed, task, out_dir, steps=X_STEPS[task], **kw)
    else:
        ep = PtEpisode(world, coll, seed, task, out_dir, **kw)
    coll.ep = ep
    res = ep.run()
    judge = None
    if xnew.is_new_task(task):  # prereg_l8x_tasks 2: the new-task judge on top of success_now
        judge = xnew.success_push(coll.rows) if task.startswith("pu__") else xnew.success_stack(coll.rows)
    os.makedirs(out_dir, exist_ok=True)
    scene = scene_record(world, seed, task, variant, split, style)
    with open(os.path.join(out_dir, "scene.json"), "w") as f:
        json.dump(scene, f)
    with open(os.path.join(out_dir, "labels.jsonl"), "w") as f:
        for r in coll.rows:
            f.write(json.dumps(dict(r, seed=seed, task=task, variant=variant, table_z=scene["table_z"],
                                    n_distractors=scene["distractors"]["n"])) + "\n")
    meta = {"seed": seed, "split": split, "task": task, "variant": variant, "table_z": scene["table_z"],
            "lift": scene["lift"], "n_distractors": scene["distractors"]["n"], "p": p, "max_perturb": max_perturb,
            "style": style, "success": bool(res.get("success")), "end_reason": res.get("end_reason"),
            "n_calls": res["n_calls"], "n_rows": len(coll.rows), "n_perturb": coll.n_pert, "sim_t": res.get("sim_t"),
            "wall_s": res.get("wall_s"), "n_pt_labels": sum(r.get("pt_answer") is not None for r in coll.rows)}
    if judge is not None:  # new tasks only (old tasks: meta byte-identical)
        meta["judge"], meta["success"] = judge, meta["success"] and judge
    save_joints(world, out_dir, meta)
    sats = [r.get("sat") for r in coll.rows if r.get("sat") is not None]
    if sats:  # change 22: the brightest call (every call is checked)
        meta["max_sat"] = max(sats)
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta
