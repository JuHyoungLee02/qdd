"""E-SR1d evaluation on the S-E2E val split (docs/stage3/prereg_sr1d.md §3): tools/sr0/sr0_eval.py (imported, not
modified; the model's own decide -> chunk path, Euler 10, noise seed * 1_000_003 + index) + the E-SR1c plausible-edit
conditions (tools/sr1c/sr1c_eval.edit_conditions, imported) + the authority-proxy stratum of every snapshot
(tools/sr1d/strata.py meta) and the extra records of the near-contact / whole-range rules.

Per condition record [dx, dy, dz, g0, g1, mse, dzmin] (FK displacement of the chunk, gripper openness of the first /
last target, normalized MSE vs the recorded chunk, min over the chunk of FK z(target_i) - FK z(target_0)).
Per snapshot: stratum / a / d / contact / holding / alt strata (proxy, hindsight), ee_z (measured end effector z at
k) and floor_z (episode floor), true_end_err (|FK(true chunk last) - FK(recorded last)|, m), grip_rec [first, last]
(recorded openness), edits {theta: [e_x, e_y, sector, mag]}.
  python tools/sr1d/sr1d_eval.py --data se2e --se2e-root R --se2e-t-root R --motion-line se2e-motion@v1 \
      --motion-bins B --val-per-kind 0 --val-seed 0 --seed 0 --ckpt DIR --meta META --out JSONL [--latency 50]
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel.split("/")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E0 = _load("sr0_eval", "tools/sr0/sr0_eval.py")
E1 = _load("sr1c_eval", "tools/sr1c/sr1c_eval.py")
META_KEYS = ("stratum", "a", "d", "contact", "holding", "alt", "floor_z")


def build_parser():
    ap = E0.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    p = sub.choices["predict"]
    p.add_argument("--meta", required=True, help="tools/sr1d/strata.py meta.jsonl")
    p.add_argument("--latency", type=int, default=0, help="also time the chunk path on the first N snapshots")
    return ap


def read_meta(path: str) -> dict:
    out = {}
    for x in open(path, encoding="utf-8"):
        m = json.loads(x)
        out[m["key"]] = m
    return out


def main(argv=None):
    import torch

    from harvest.train import stageb_train as TR
    from harvest.train.se2e_data import fk_ee, load_arm_chain
    from harvest.train.stageb_expert import sample_actions
    from harvest.train.stageb_model import load_heads
    a = build_parser().parse_args(["predict"] + (argv if argv is not None else sys.argv[1:]))
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    meta = read_meta(a.meta)
    snaps = E0.snapshots(a)
    if a.limit:
        snaps = snaps[:a.limit]
    bb, proc, _ = TR.load_backbone("qwen", a.model, dev, adapter=os.path.join(a.ckpt, "adapter"))
    m = TR.aux_model(a, load_heads(a.ckpt, bb, dev).eval(), new=False)
    m.shared = True
    m, enc = TR.temporal_model(a, m, proc)
    E0.check_vocab(m.vocabs["dec"].to_json(), m.vocabs["phase"].to_json(), False)
    chains = {}
    H, Ad = m.expert.cfg.horizon, m.expert.cfg.act_dim
    write = TR._writer(a.out)
    n_skip, lat = 0, []
    for i, (sid, s) in enumerate(snaps):
        arm = s.get("arm", "right")
        if arm not in chains:
            chains[arm] = load_arm_chain(a.urdf, arm)
        fk = lambda q: fk_ee(chains[arm], q)  # noqa: E731
        labels = {q: s["committed"].get(q) for q in s["committed"]}
        if any(labels.get(q) is None for q in E0.JOY):
            n_skip += 1
            write({"event": "skip", "i": i, "id": sid, "key": s["key"], "labels": labels})
            continue
        mt = meta[s["key"]]
        ex = np.asarray(s["action_exec"], float)
        dgt = fk(ex[-1, :7]) - fk(ex[0, :7])
        g = torch.Generator().manual_seed(a.seed * 1_000_003 + i)
        noise = torch.randn(1, H, Ad, generator=g).to(dev)
        with torch.no_grad():
            ctx, mask, lps = m.forward_shared([s], enc, dev, grad=False)
            preds = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s["items"], lps[0])}
            cs = E0.condition_set(labels, preds, False)
            es = E1.edit_conditions(labels, dgt)
            allc = [(n, c, p) for n, c, p in cs] + [(n, c, p) for n, c, p, _ in es]
            batch = [{**s, "committed": c, **({"phase_id": p} if p else {})} for _, c, p in allc]
            B = len(batch)
            cond = m.cond(batch, ctx.repeat(B, 1, 1), mask.repeat(B, 1), dev)
            z = sample_actions(m.expert, cond, a.steps, noise.repeat(B, 1, 1))
            tgt, valid, _ = m.targets([s], dev)
            vm = valid[..., None]
            mse = ((((z - tgt) ** 2) * vm).sum((1, 2)) / (vm.sum() * Ad)).float().cpu().numpy()
        zc = z.float().cpu().numpy()
        rec, true_end_err = {}, None
        for j, (n, _, _) in enumerate(allc):
            act = m.norm.action(zc[j], s["action_script"], arm)
            P = fk(act[:, :7])
            d = P[-1] - P[0]
            rec[n] = [round(float(v), 7) for v in d] + [round(float(act[0, 7]), 5), round(float(act[-1, 7]), 5),
                                                         round(float(mse[j]), 7),
                                                         round(float((P[:, 2] - P[0, 2]).min()), 7)]
            if n == "true":
                true_end_err = float(np.linalg.norm(P[-1] - fk(ex[-1, :7])))
        write({"event": "snap", "i": i, "id": sid, "key": s["key"], "arm": arm, "labels": labels, "preds": preds,
               "disp_gt": [round(float(x), 7) for x in dgt], "c": rec, **{k: mt[k] for k in META_KEYS},
               "ee_z": mt["ee"][2], "true_end_err": round(true_end_err, 7),
               "grip_rec": [round(float(ex[0, 7]), 5), round(float(ex[-1, 7]), 5)],
               "edits": {n: info for n, _, _, info in es}})
        if i < a.latency:
            lat += E1.time_chunk(m, s, ctx, mask, noise, a.steps, dev)
    summ = {"event": "summary", "ckpt": a.ckpt, "data": a.data, "n": len(snaps) - n_skip, "n_skip": n_skip,
            "n_loaded": len(snaps), "conds": E0.cond_names(False), "edits": list(E1.EDIT_DEG), "steps": a.steps,
            "seed": a.seed, "keys_sha": TR._sha([k for k, _ in snaps]), "meta": a.meta}
    if lat:
        ls = sorted(lat)
        summ["latency_ms"] = {"n": len(ls), "p50": round(1e3 * ls[len(ls) // 2], 3),
                              "p95": round(1e3 * ls[int(0.95 * (len(ls) - 1))], 3)}
    write(summ)


if __name__ == "__main__":
    main()
