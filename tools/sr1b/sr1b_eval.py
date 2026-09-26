"""E-SR1b evaluation (docs/stage3/prereg_sr1b.md): the E-SR0 joystick-adherence evaluation (tools/sr0/sr0_eval.py:
same snapshots, same condition set, same fixed flow noise per snapshot, same records) with the chunk sampled under
decision classifier-free guidance at every weight w of --cfg-w (harvest.train.sr1b.sample_actions_cfg; null = the
--null-slots decision ids set to 0, the dropout token). w = 1 is the plain sr0 path (bit-identical sampling).
One sr0-format jsonl per w, <out>_w<w>.jsonl, so tools/sr0/sr0_verdict.py's metric functions read it unchanged;
each 'snap' record also carries the decision-item targets (decision accuracy), w, the near-contact flag and distance
(harvest.train.sr1b.near_snap = runtime.core.near_contact from the row's aux geometry; strata, distance CFG), the phase
and the recorded chunk's first / last gripper openness (grip_gt; gripper timing).
Reusable for later arms (E-SR1c): --null-slots, --cfg-w.
  python tools/sr1b/sr1b_eval.py --data r2 --pool P --rows ROWS --eval-set JSON --grip --seed 0 --ckpt DIR \
      --cfg-w 1,1.5,2,3,5,8 --out PREFIX
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))

import numpy as np  # noqa: E402

import sr0_eval as E0  # noqa: E402
from harvest.train import sr1b as S  # noqa: E402


def out_path(prefix: str, w: float) -> str:
    return f"{prefix}_w{S.w_tag(w)}.jsonl"


def build_parser():
    ap = E0.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    p = sub.choices["predict"]
    p.add_argument("--cfg-w", default="1", help="guidance grid, 1 first (e.g. 1,1.5,2,3,5,8)")
    p.add_argument("--null-slots", default=",".join(S.JOY), help="decision slots zeroed for the null condition")
    return ap


def main(argv=None):
    import torch

    from harvest.train import stageb_train as TR
    from harvest.train.se2e_data import fk_ee, load_arm_chain
    from harvest.train.stageb_model import load_heads
    a = build_parser().parse_args(["predict"] + (argv if argv is not None else sys.argv[1:]))
    ws, slots = S.parse_ws(a.cfg_w), S.slot_indices(a.null_slots)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    snaps = E0.snapshots(a)
    if a.limit:
        snaps = snaps[:a.limit]
    bb, proc, _ = TR.load_backbone("qwen", a.model, dev, adapter=os.path.join(a.ckpt, "adapter"))
    m = TR.aux_model(a, load_heads(a.ckpt, bb, dev).eval(), new=False)
    m.shared = True
    m, enc = TR.temporal_model(a, m, proc)
    E0.check_vocab(m.vocabs["dec"].to_json(), m.vocabs["phase"].to_json(), a.grip)
    chains = {}
    H, A = m.expert.cfg.horizon, m.expert.cfg.act_dim
    names = E0.cond_names(a.grip)
    for w in ws:
        if os.path.exists(out_path(a.out, w)):
            os.remove(out_path(a.out, w))
    writes = {w: TR._writer(out_path(a.out, w)) for w in ws}
    n_skip = 0
    for i, (sid, s) in enumerate(snaps):
        arm = s.get("arm", "right")
        if arm not in chains:
            chains[arm] = load_arm_chain(a.urdf, arm)
        fk = lambda q: fk_ee(chains[arm], q)  # noqa: E731
        labels = {q: s["committed"].get(q) for q in s["committed"]}
        if any(labels.get(q) is None for q in E0.JOY):
            n_skip += 1
            for w in ws:
                writes[w]({"event": "skip", "i": i, "id": sid, "key": s["key"], "labels": labels})
            continue
        g = torch.Generator().manual_seed(a.seed * 1_000_003 + i)
        noise = torch.randn(1, H, A, generator=g).to(dev)
        zs = {}
        with torch.no_grad():
            ctx, mask, lps = m.forward_shared([s], enc, dev, grad=False)
            preds = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s["items"], lps[0])}
            cs = E0.condition_set(labels, preds, a.grip)
            batch = [{**s, "committed": c, **({"phase_id": p} if p else {})} for _, c, p in cs]
            B = len(batch)
            cond = m.cond(batch, ctx.repeat(B, 1, 1), mask.repeat(B, 1), dev)
            tgt, valid, _ = m.targets([s], dev)
            vm = valid[..., None]
            for w in ws:
                z = S.sample_actions_cfg(m.expert, cond, w, a.steps, noise.repeat(B, 1, 1), slots)
                mse = ((((z - tgt) ** 2) * vm).sum((1, 2)) / (vm.sum() * A)).float().cpu().numpy()
                zs[w] = (z.float().cpu().numpy(), mse)
        ex = np.asarray(s["action_exec"], float)
        dgt = [round(float(v), 7) for v in fk(ex[-1, :7]) - fk(ex[0, :7])]
        targets = {it["question"]: list(it["target"]) for it in s["items"]}
        near, dist = S.near_snap(s.get("aux"), s.get("phase_id"))
        extra = {"near": near, "dist_m": None if dist is None else round(dist, 5), "phase_id": s.get("phase_id"),
                 "grip_gt": [round(float(ex[0, 7]), 5), round(float(ex[-1, 7]), 5)]}
        for w in ws:
            zc, mse = zs[w]
            rec = {}
            for j, (n, _, _) in enumerate(cs):
                act = m.norm.action(zc[j], s["action_script"], arm)
                d = fk(act[-1, :7]) - fk(act[0, :7])
                rec[n] = [round(float(v), 7) for v in d] + [round(float(act[0, 7]), 5), round(float(act[-1, 7]), 5),
                                                             round(float(mse[j]), 7)]
            writes[w]({"event": "snap", "i": i, "id": sid, "key": s["key"], "arm": arm, "labels": labels,
                       "preds": preds, "targets": targets, "disp_gt": dgt, "c": rec, "w": w, **extra})
    for w in ws:
        writes[w]({"event": "summary", "ckpt": a.ckpt, "data": a.data, "n": len(snaps) - n_skip, "n_skip": n_skip,
                   "n_loaded": len(snaps), "grip": a.grip, "conds": names, "steps": a.steps, "seed": a.seed,
                   "keys_sha": TR._sha([k for k, _ in snaps]), "w": w, "cfg_w": list(ws),
                   "null_slots": [S.QUESTIONS[j] for j in slots]})


if __name__ == "__main__":
    main()
