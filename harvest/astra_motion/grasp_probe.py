"""Static grasp-state sub-test (coupling spec §12-§13, user-log 83): does Astra (or the local VLM) wrongly call a
near-miss 'grasped' from the head view, and do the wrist views / the motion overlay help?

snapshots (pod, Isaac): per episode two hard-reset runs driven by the code executor from sim truth:
  true run: TCP to 10 cm above the oracle grasp point -> grasp point [snapshot 'pre': open, fingers around the object,
            not held] -> close [snapshot 'closed' (v2)] -> lift 3 cm [snapshot 'grasped'];
  miss run: the same with the grasp point moved 9 cm toward the robot (-x: the far finger ends ~4 mm in front of the
            object, so in the head view the closed fingers overlap it) -> close -> lift 3 cm [snapshot 'miss'].
  Ground truth = the sim's holding(target) at the snapshot. Raw images of all three cameras + camera models + the last
  3 s TCP trace are saved; overlays are drawn at ask time.
ask (anywhere with network): per snapshot the question GRASP_Q under the pre-registered conditions (views x overlay x
  repeats); rows appended to a JSONL (resumable)."""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np

from . import geometry as G
from . import prompts as PR
from . import schema as SC
from .overlay import annotate, png_bytes

MISS_DX = -0.09
LIFT = 0.03
# (views, overlay, repeats): the view ablation with the overlay on (1 answer each), plus the overlay ablation on all
# three views (2 answers each with and without the overlay; the first 'all3 + overlay' answer is shared)
CONDS = (("head", False, 1), ("head+right", False, 1), ("all3", False, 1), ("all3", True, 1))  # G1 v2 (re-scope)
CONDS_HIGH = (("all3", True, 1),)  # G2: targeted snapshots only (--only)
VIEW_CAMS = {"head": ("head",), "head+right": ("head", "wrist"), "all3": ("head", "wrist_left", "wrist")}
LABEL = {"head": "head camera", "wrist_left": "left wrist camera", "wrist": "right wrist camera"}


def _drive(world, ex, targets, path, limit_s=12.0):
    t0 = world.status()["t"]
    ex.load(targets, t0)
    while ex.busy and world.status()["t"] - t0 < limit_s:
        st = world.status()
        path.append([st["t"], *[float(v) for v in st["tcp"]]])
        cmd, w, _ = ex.tick(st["t"], st["tcp"])
        world.step(cmd, w, ex.goal_quat)


def _save(world, d, name, path, gt, astra_dir):
    from PIL import Image
    o = world.observe()
    sd = os.path.join(d, name)
    os.makedirs(sd, exist_ok=True)
    for k, im in o.rgb.items():
        Image.fromarray(im).save(os.path.join(sd, f"{k}.png"))
    t = o.t
    meta = {"name": name, "gt": gt, "tcp": np.asarray(o.tcp, float).tolist(), "grip_w": o.grip_w,
            "cams": {k: c.to_json() for k, c in o.cams.items()},
            "trace": [p[1:] for p in path if p[0] >= t - 3.0], "astra_dir": list(astra_dir)}
    with open(os.path.join(sd, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    return meta


def snapshots(world, episodes, out: str) -> list:
    from .executor import MotionExec, Target
    from .harness import GRASP_BELOW_TOP_M, obj_height
    rows = []
    for seed, task in episodes:
        for run in ("true", "miss"):
            world.reset(seed, task)
            info = world.task_info()
            st = world.status()
            tg = info["tgt"]
            c = np.asarray(st["obj"][tg], float)
            g = np.array([c[0], c[1], world.table_z + obj_height(tg) - GRASP_BELOW_TOP_M])
            g = g + ([MISS_DX, 0, 0] if run == "miss" else [0, 0, 0])
            ex = MotionExec(world.dt, world.table_z, st["tcp"], world.w_open, world.w_close, quat0=world.quat0)
            path: list = []
            _drive(world, ex, [Target(g + [0, 0, 0.10], "keep"), Target(g, "keep")], path)
            d = os.path.join(out, f"s{seed}_{task}")
            base = {"seed": seed, "task": task, "tgt": tg, "instruction": info["instruction"]}
            if run == "true":
                s = world.status()
                rows.append(_save(world, d, "pre", path, dict(base, holding=bool(s["pred"].get(f"holding({tg})")),
                                                              state="pre"), (0, 0, -0.05)))
            _drive(world, ex, [Target(g, "close")], path)
            if run == "true":  # closed on the object, not lifted yet (balances the truth split: v2)
                s = world.status()
                rows.append(_save(world, d, "closed", path, dict(base, holding=bool(s["pred"].get(f"holding({tg})")),
                                                                 state="closed", grip_w=s["grip_w"]), (0, 0, -0.01)))
            _drive(world, ex, [Target(g + [0, 0, LIFT], "keep")], path)
            s = world.status()
            name = "grasped" if run == "true" else "miss"
            rows.append(_save(world, d, name, path, dict(base, holding=bool(s["pred"].get(f"holding({tg})")),
                                                         state=name, grip_w=s["grip_w"]), (0, 0, LIFT)))
            print("SNAP " + json.dumps({"ep": f"s{seed}_{task}", "name": name, "holding": rows[-1]["gt"]["holding"],
                                        "grip_mm": round(s["grip_w"] * 1e3, 1)}), flush=True)
    return rows


def images(sd: str, meta: dict, views: str, overlay: bool) -> list:
    from PIL import Image
    out = []
    for k in VIEW_CAMS[views]:
        im = np.asarray(Image.open(os.path.join(sd, f"{k}.png")).convert("RGB"))
        if overlay:
            cam = G.Cam.from_json(meta["cams"][k])
            tcp = np.asarray(meta["tcp"], float)
            ad = np.asarray(meta["astra_dir"], float)
            im = annotate(im, cam, tcp, trace=None if k == "wrist" else [np.asarray(p) for p in meta["trace"]],
                          astra_dir=ad, wrist_inset=(k == "wrist"))
        out.append((LABEL[k], png_bytes(im)))
    return out


def ask(model, root: str, out_jsonl: str, conds=CONDS, only: list | None = None) -> None:
    done = set()
    if os.path.exists(out_jsonl):
        for line in open(out_jsonl):
            r = json.loads(line)
            done.add((r["snap"], r["views"], r["overlay"], r["rep"], r["model"]))
    snaps = sorted(os.path.join(dp, n) for dp in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, dp))
                   for n in ("pre", "closed", "grasped", "miss") if os.path.isdir(os.path.join(root, dp, n)))
    for sd in snaps:
        sd_full = os.path.join(root, sd) if not os.path.isabs(sd) else sd
        meta = json.load(open(os.path.join(sd_full, "meta.json")))
        tgt_name = PR.OBJ_NAME[meta["gt"]["tgt"]]
        key = os.path.relpath(sd_full, root).replace("\\", "/")
        if only is not None and key not in only:
            continue
        for views, overlay, reps in conds:
            for r in range(reps):
                if (key, views, overlay, r, model.name) in done:
                    continue
                text = PR.GRASP_Q.format(views=PR.GRASP_VIEWS[views], tgt_name=tgt_name)
                rep = model.ask(text, images(sd_full, meta, views, overlay),
                                {"kind": "grasp", "snap": key, "views": views, "overlay": overlay, "rep": r})
                p, err = (None, [f"api:{rep.error}"]) if (rep.error and not rep.text) else SC.validate("G", rep.text)
                row = {"snap": key, "state": meta["gt"]["state"], "gt_holding": meta["gt"]["holding"],
                       "views": views, "overlay": overlay, "rep": r, "model": model.name, "valid": p is not None,
                       "errors": err[:4], "answer": p, "raw": (rep.text or "")[:600],
                       "latency_s": round(rep.latency_s, 3), "usage": rep.usage, "cost_usd": round(rep.cost_usd, 6),
                       "prompt_id": PR.PROMPT_ID, "prompt_sha": hashlib.sha256(text.encode()).hexdigest()[:12]}
                with open(out_jsonl, "a") as f:
                    f.write(json.dumps(row) + "\n")
                print("GRASP " + json.dumps({k: row[k] for k in ("snap", "views", "overlay", "rep", "gt_holding")}
                                            | {"ans": (p or {}).get("grasp_state"), "cost": row["cost_usd"]}),
                      flush=True)


def score(rows: list) -> dict:
    """Per (model, views, overlay): false 'grasped' rate (answer grasped when not held), missed 'grasped' rate
    (answer not grasped / uncertain when held), uncertain rate, invalid rate, and repeat agreement."""
    out = {}
    for r in rows:
        k = f"{r['model']}|{r['views']}|{'overlay' if r['overlay'] else 'raw'}"
        out.setdefault(k, []).append(r)
    res = {}
    for k, rs in out.items():
        neg = [r for r in rs if not r["gt_holding"]]
        pos = [r for r in rs if r["gt_holding"]]
        ans = lambda r: (r["answer"] or {}).get("grasp_state")  # noqa: E731
        by_snap = {}
        for r in rs:
            by_snap.setdefault(r["snap"], []).append(ans(r))
        pairs = [v for v in by_snap.values() if len(v) >= 2]
        res[k] = {"n": len(rs), "invalid": sum(not r["valid"] for r in rs),
                  "false_grasped": f"{sum(ans(r) == 'grasped' for r in neg)}/{len(neg)}",
                  "missed_grasped": f"{sum(ans(r) != 'grasped' for r in pos)}/{len(pos)}",
                  "uncertain": sum(ans(r) == "uncertain" for r in rs),
                  "miss_false_grasped": f"{sum(ans(r) == 'grasped' for r in neg if r['state'] == 'miss')}/"
                                        f"{sum(r['state'] == 'miss' for r in neg)}",
                  "repeat_agree": f"{sum(len(set(v)) == 1 for v in pairs)}/{len(pairs)}" if pairs else None,
                  "cost_usd": round(sum(r["cost_usd"] for r in rs), 4)}
    return res
