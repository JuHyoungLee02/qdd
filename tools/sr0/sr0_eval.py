"""E-SR0 joystick adherence (docs/stage3/prereg_sr0.md): does the action expert chunk follow the decision it is
conditioned on? No training: existing checkpoints, the model's own inference path (decide -> chunk, as ma2eval and
runtime): one shared-prefix forward per snapshot (StageB.forward_shared -> context hidden states + predicted
decisions), then the expert (StageB.cond + stageb_expert.sample_actions, Euler 10) under a FIXED set of decision
conditions that differ in one question at a time (condition_set):
  true            committed = the snapshot's labels (training-time teacher forcing)
  pred            the model's argmax decisions
  xy:<d>          dir_xy forced to each of the 9 options (8 directions + none_xy), other questions = labels
  z:<d>           dir_z forced to up / down / none_z
  mag:<m>         mag_coarse forced to tiny / small / medium / large / xlarge
  flip            dir_xy and dir_z reversed (none stays)
  pid:close|open  (R2 only, --grip) the expert's sub-phase token forced to close / open (the typed decision vocabulary
                  has no gripper option; this is the discrete condition that carries the gripper event)
Every condition of a snapshot uses the same flow noise (seed * 1_000_003 + snapshot index, as ma2eval). Per condition
it records the FK fingertip displacement of the chunk (active arm URDF, arm_base_link frame: FK(last chunk target) -
FK(first chunk target), as ma2eval), the gripper openness of the first / last chunk target, and the normalized chunk
MSE against the recorded action (valid steps).
Output jsonl: one 'snap' record per snapshot {key, id, arm, labels, preds, disp_gt, c: {cond: [dx, dy, dz, g0, g1,
mse]}} and one 'summary'.
  S-E2E: python tools/sr0/sr0_eval.py --data se2e --se2e-root R --se2e-t-root R --motion-line se2e-motion@v1 \
             --motion-bins B --val-per-kind 0 --val-seed 0 --seed 0 --ckpt DIR --out JSONL
  R2:    python tools/sr0/sr0_eval.py --data r2 --pool P --rows ROWS --eval-set JSON --grip --seed 0 --ckpt DIR \
             --out JSONL
"""
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

DIR_XY8 = ("plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
           "plus_x_minus_y")
DIR_XY9 = DIR_XY8 + ("none_xy",)
DIR_Z3 = ("up", "down", "none_z")
MAGS = ("tiny", "small", "medium", "large", "xlarge")  # 0.5 / 1 / 2 / 4 / 8 cm (sim.planner.MAG_BINS)
PID_GRIP = ("close", "open")
JOY = ("dir_xy", "dir_z", "mag_coarse")
_SGN = {"plus_x": (1, 0), "plus_x_plus_y": (1, 1), "plus_y": (0, 1), "minus_x_plus_y": (-1, 1), "minus_x": (-1, 0),
        "minus_x_minus_y": (-1, -1), "minus_y": (0, -1), "plus_x_minus_y": (1, -1), "none_xy": (0, 0)}
FLIP_XY = {d: next(k for k, v in _SGN.items() if v == (-s[0], -s[1])) for d, s in _SGN.items()}
FLIP_Z = {"up": "down", "down": "up", "none_z": "none_z"}
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"


def unit_xy(name: str) -> np.ndarray:
    v = np.asarray(_SGN[name], float)
    n = np.linalg.norm(v)
    return v / n if n else v


def cond_names(grip: bool) -> list:
    return (["true", "pred"] + [f"xy:{d}" for d in DIR_XY9] + [f"z:{d}" for d in DIR_Z3]
            + [f"mag:{m}" for m in MAGS] + ["flip"] + ([f"pid:{p}" for p in PID_GRIP] if grip else []))


def condition_set(labels: dict, preds: dict, grip: bool) -> list:
    """[(name, committed decisions, phase_id override or None)] in cond_names order; the inputs are not modified."""
    miss = [q for q in JOY if labels.get(q) is None]
    if miss:
        raise ValueError(f"labels without {miss}")
    base = dict(labels)
    out = [("true", dict(base), None), ("pred", {**base, **preds}, None)]
    out += [(f"xy:{d}", {**base, "dir_xy": d}, None) for d in DIR_XY9]
    out += [(f"z:{d}", {**base, "dir_z": d}, None) for d in DIR_Z3]
    out += [(f"mag:{m}", {**base, "mag_coarse": m}, None) for m in MAGS]
    out.append(("flip", {**base, "dir_xy": FLIP_XY[base["dir_xy"]], "dir_z": FLIP_Z[base["dir_z"]]}, None))
    if grip:
        out += [(f"pid:{p}", dict(base), p) for p in PID_GRIP]
    return out


def check_vocab(dec_names, phase_names, grip: bool) -> None:
    """Every forced value must have its own embedding in the checkpoint (unknown -> id 0 would be silent)."""
    need = [f"dir_xy={d}" for d in DIR_XY9] + [f"dir_z={d}" for d in DIR_Z3] + [f"mag_coarse={m}" for m in MAGS]
    miss = [n for n in need if n not in set(dec_names)]
    if grip:
        miss += [f"phase_id={p}" for p in PID_GRIP if p not in set(phase_names)]
    if miss:
        raise SystemExit(f"checkpoint vocabulary lacks {miss}")


# ------------------------------------------------------------------------------------------ GPU part (pod)
def build_parser():
    from harvest.train import stageb_train as TR
    ap = TR.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    p = sub.choices["predict"]
    p.add_argument("--eval-set", default="", help="R2: json {'ids': [...]} (E-MA2 eval_set.json)")
    p.add_argument("--grip", action="store_true", help="add pid:close / pid:open (R2)")
    p.add_argument("--urdf", default=URDF)
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--limit", type=int, default=0, help="first N snapshots only (dry run)")
    return ap


def snapshots(a):
    """[(id, sample)] in evaluation order: S-E2E = the whole val split (--val-per-kind 0, stageb_train order);
    R2 = the eval-set ids (E-MA2 order) from the eval rows."""
    from harvest.train import stageb_data as D
    from harvest.train import stageb_train as TR
    if a.eval_set:
        from harvest.train.r2_ma2 import sample_id
        ids = json.load(open(a.eval_set))["ids"]
        samples, _ = D.load_for_training(a.data, pool=a.pool, rows=a.rows, state=a.state, wrist=not a.no_wrist)
        by = {}
        for s in samples:
            by.setdefault(sample_id(s["context"]["images"][0][1]), s)
        miss = [i for i in ids if i not in by]
        if miss or len(set(ids)) != len(ids):
            raise SystemExit(f"eval set: {len(miss)} ids not loaded, {len(ids) - len(set(ids))} duplicates")
        return [(i, by[i]) for i in ids]
    _, _, _, va = TR._load_data(a)
    val = TR.val_subset(va, a.max_val, a.val_per_kind, a.val_seed)
    return [(s["key"], s) for s in val]


def main(argv=None):
    import torch

    from harvest.train import stageb_train as TR
    from harvest.train.se2e_data import fk_ee, load_arm_chain
    from harvest.train.stageb_expert import sample_actions
    from harvest.train.stageb_model import load_heads
    a = build_parser().parse_args(["predict"] + (argv if argv is not None else sys.argv[1:]))
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    snaps = snapshots(a)
    if a.limit:
        snaps = snaps[:a.limit]
    bb, proc, _ = TR.load_backbone("qwen", a.model, dev, adapter=os.path.join(a.ckpt, "adapter"))
    m = TR.aux_model(a, load_heads(a.ckpt, bb, dev).eval(), new=False)
    m.shared = True
    m, enc = TR.temporal_model(a, m, proc)
    check_vocab(m.vocabs["dec"].to_json(), m.vocabs["phase"].to_json(), a.grip)
    chains = {}
    H, A = m.expert.cfg.horizon, m.expert.cfg.act_dim
    names = cond_names(a.grip)
    write = TR._writer(a.out)
    n_skip = 0
    for i, (sid, s) in enumerate(snaps):
        arm = s.get("arm", "right")
        if arm not in chains:
            chains[arm] = load_arm_chain(a.urdf, arm)
        fk = lambda q: fk_ee(chains[arm], q)  # noqa: E731
        labels = {q: s["committed"].get(q) for q in s["committed"]}
        if any(labels.get(q) is None for q in JOY):
            n_skip += 1
            write({"event": "skip", "i": i, "id": sid, "key": s["key"], "labels": labels})
            continue
        g = torch.Generator().manual_seed(a.seed * 1_000_003 + i)
        noise = torch.randn(1, H, A, generator=g).to(dev)
        with torch.no_grad():
            ctx, mask, lps = m.forward_shared([s], enc, dev, grad=False)
            preds = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s["items"], lps[0])}
            cs = condition_set(labels, preds, a.grip)
            batch = [{**s, "committed": c, **({"phase_id": p} if p else {})} for _, c, p in cs]
            B = len(batch)
            cond = m.cond(batch, ctx.repeat(B, 1, 1), mask.repeat(B, 1), dev)
            z = sample_actions(m.expert, cond, a.steps, noise.repeat(B, 1, 1))
            tgt, valid, _ = m.targets([s], dev)
            vm = valid[..., None]
            mse = ((((z - tgt) ** 2) * vm).sum((1, 2)) / (vm.sum() * A)).float().cpu().numpy()
        zc = z.float().cpu().numpy()
        rec = {}
        for j, (n, _, _) in enumerate(cs):
            act = m.norm.action(zc[j], s["action_script"], arm)
            d = fk(act[-1, :7]) - fk(act[0, :7])
            rec[n] = [round(float(v), 7) for v in d] + [round(float(act[0, 7]), 5), round(float(act[-1, 7]), 5),
                                                         round(float(mse[j]), 7)]
        ex = np.asarray(s["action_exec"], float)
        dgt = fk(ex[-1, :7]) - fk(ex[0, :7])
        write({"event": "snap", "i": i, "id": sid, "key": s["key"], "arm": arm, "labels": labels, "preds": preds,
               "disp_gt": [round(float(v), 7) for v in dgt], "c": rec})
    write({"event": "summary", "ckpt": a.ckpt, "data": a.data, "n": len(snaps) - n_skip, "n_skip": n_skip,
           "n_loaded": len(snaps), "grip": a.grip, "conds": names, "steps": a.steps, "seed": a.seed,
           "keys_sha": TR._sha([k for k, _ in snaps])})


if __name__ == "__main__":
    main()
