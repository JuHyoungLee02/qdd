"""E-NOV0 feature extraction (docs/stage3/prereg_nov0.md §2-§3). No training; the E-MA2 C0 checkpoint's own
decide pass (StageB.forward_shared, batched, as training / E-SR0) with a forward hook on the vision tower:
  dec   LLM last-layer hidden state at the decision position = the last token of the context prompt (system + images
        + state + generation prompt; every question row continues from it), 2560
  mean  LLM last-layer hidden states averaged over the context prompt tokens, 2560
  vis   vision tower (SigLIP2-L, frozen) last block output, patch mean of the head image ; patch mean over the wrist
        image(s), 2 x 1024
eval split only: predicted option per question (argmax of the option log-probs), correct = pred in the label's
target set, margin = top-1 minus top-2 log-prob, and the expert chunk conditioned on the predicted decisions (flow
noise seed * 1_000_003 + eval index, Euler 10, as ma2eval / E-SR0 'pred') with its normalized MSE to the recorded
action over valid steps.
  R2:    python tools/nov0/nov0_extract.py --data r2 --pool P --ckpt DIR --out-dir D --sets mem,cal,eval \
             [--n-mem 2500 --n-cal 500 --batch 8 --limit N]
  S-E2E: python tools/nov0/nov0_extract.py --data se2e --se2e-root R --ckpt DIR --out-dir D --sets se2e
  batch check (dry run): ... --sets eval --limit 8 --batch-check
Outputs <out-dir>/<set>.npz (ids, dec, mean, vis float32) + <set>.meta.jsonl (+ summary line), selection.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

import nov0_lib as L  # noqa: E402


def build_parser():
    from harvest.train import stageb_train as TR
    ap = TR.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    p = sub.choices["predict"]
    next(x for x in p._actions if x.dest == "out").required = False  # outputs go to --out-dir
    p.add_argument("--out-dir", required=True)
    p.add_argument("--sets", required=True, help="mem,cal,eval (R2) | se2e")
    p.add_argument("--n-mem", type=int, default=2500, help="memory snapshots per (variant, task)")
    p.add_argument("--n-cal", type=int, default=500, help="calibration snapshots per (variant, task)")
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--limit", type=int, default=0, help="N evenly spaced of each set (dry run)")
    p.add_argument("--batch-check", action="store_true", help="dry run: batch 1 vs --batch features, then exit")
    p.add_argument("--noise-ref", default="",
                   help="json {'ids'} (E-MA2 eval set): flow-noise index of an eval id = its position in that list "
                        "(E-SR0 / ma2eval numbering, G1 compares the same draws); other eval ids = len(list) + their "
                        "position in the sorted eval split")
    p.add_argument("--only-ref", action="store_true", help="dry run: eval = only the --noise-ref ids")
    return ap


class VisHook:
    """Captures the vision tower's last block output and grid of the latest forward."""

    def __init__(self, visual):
        self.h = self.thw = None
        self.handle = visual.register_forward_hook(self, with_kwargs=True)

    def __call__(self, mod, args, kwargs, output):
        self.h = output.last_hidden_state.detach().float().cpu().numpy()
        thw = kwargs.get("grid_thw", args[1] if len(args) > 1 else None)
        self.thw = thw.detach().cpu().numpy()


def _margin(lp: dict) -> float:
    v = sorted((float(x) for x in lp.values()), reverse=True)
    return float(v[0] - v[1]) if len(v) > 1 else 99.0


def features(m, enc, batch, dev, hook):
    """(dec [B, D], mean [B, D], vis [B, 2Dv], ctx, mask, lps) of one batch."""
    import torch
    with torch.no_grad():
        ctx, mask, lps = m.forward_shared(batch, enc, dev, grad=False)
    n = mask.sum(1).tolist()
    dec = np.stack([ctx[i, n[i] - 1].float().cpu().numpy() for i in range(len(batch))])
    mean = np.stack([ctx[i, :n[i]].float().mean(0).cpu().numpy() for i in range(len(batch))])
    counts = [int(np.prod(t)) for t in hook.thw]
    vis = L.pool_vis(hook.h, counts, [len(s["context"]["images"]) for s in batch])
    return dec, mean, vis, ctx, mask, lps


def load_r2(a):
    from harvest.train import stageb_data as D
    from harvest.train.r2_ma2 import sample_id
    samples, _ = D.load_for_training("r2", pool=a.pool, rows=a.rows, state=a.state, wrist=not a.no_wrist)
    by, dup = {}, 0
    for s in samples:
        sid = sample_id(s["context"]["images"][0][1])
        if sid in by:
            dup += 1
            continue
        by[sid] = s
    return by, dup


def main(argv=None):
    import torch

    from harvest.train import stageb_train as TR
    from harvest.train.prefix_share import _parts
    from harvest.train.stageb_expert import sample_actions
    from harvest.train.stageb_model import load_heads
    a = build_parser().parse_args(["predict"] + (argv if argv is not None else sys.argv[1:]))
    os.makedirs(a.out_dir, exist_ok=True)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    sets = [x for x in a.sets.split(",") if x]
    t0 = time.time()
    if a.data == "r2":
        by, dup = load_r2(a)
        recs = [{"id": i, "split": s["split"]} for i, s in by.items()]
        sel = L.select(recs, a.n_mem, a.n_cal, seed=0)
        info = {k: {"n": len(v), "sha": hashlib.sha256(json.dumps(v).encode()).hexdigest()[:12]} for k, v in sel.items()}
        json.dump({"n_mem_per": a.n_mem, "n_cal_per": a.n_cal, "n_loaded": len(by), "n_dup": dup, **info, **sel},
                  open(os.path.join(a.out_dir, "selection.json"), "w"))
        print(json.dumps({"event": "selection", "n_loaded": len(by), "n_dup": dup, **info,
                          "load_s": round(time.time() - t0, 1)}), flush=True)
        todo = {s: [(i, by[i]) for i in sel[s]] for s in sets}
        noise_idx = {i: n for n, i in enumerate(sel["eval"])}
        if a.noise_ref:
            ref_ids = json.load(open(a.noise_ref))["ids"]
            noise_idx = L.noise_index(ref_ids, sel["eval"])
            if a.only_ref:
                todo["eval"] = [(i, by[i]) for i in ref_ids]
    else:
        _, _, _, va = TR._load_data(a)
        val = TR.val_subset(va, 0, 0, 0)
        todo = {"se2e": [(s["key"], s) for s in val]}
    bb, proc, _ = TR.load_backbone("qwen", a.model, dev, adapter=os.path.join(a.ckpt, "adapter"))
    m = TR.aux_model(a, load_heads(a.ckpt, bb, dev).eval(), new=False)
    m.shared = True
    m, enc = TR.temporal_model(a, m, proc)
    hook = VisHook(_parts(m.backbone)[0].visual)
    H, A = m.expert.cfg.horizon, m.expert.cfg.act_dim
    if a.batch_check:
        snaps = [s for _, s in todo[sets[0]][:a.limit or 8]]
        one = [features(m, enc, [s], dev, hook)[:3] for s in snaps]
        many = features(m, enc, snaps, dev, hook)[:3]
        res = {}
        for j, name in enumerate(("dec", "mean", "vis")):
            X1, X8 = np.stack([o[j][0] for o in one]), many[j]
            cos = (X1 * X8).sum(1) / (np.linalg.norm(X1, axis=1) * np.linalg.norm(X8, axis=1))
            res[name] = {"min_cos": float(cos.min()), "max_rel": float(np.abs(X1 - X8).max() / np.abs(X1).max())}
        print(json.dumps({"event": "batch_check", "n": len(snaps), **res}), flush=True)
        json.dump(res, open(os.path.join(a.out_dir, "batch_check.json"), "w"))
        return
    for sname in sets:
        items = todo[sname]
        if a.limit and a.limit < len(items):  # dry run: evenly spaced over the sorted set (every stratum)
            items = [items[i * len(items) // a.limit] for i in range(a.limit)]
        ids, F = [], {"dec": [], "mean": [], "vis": []}
        meta_f = open(os.path.join(a.out_dir, f"{sname}.meta.jsonl"), "w", encoding="utf-8")
        ts = time.time()
        for b0 in range(0, len(items), a.batch):
            chunk = items[b0:b0 + a.batch]
            batch = [s for _, s in chunk]
            dec, mean, vis, ctx, mask, lps = features(m, enc, batch, dev, hook)
            for name, X in (("dec", dec), ("mean", mean), ("vis", vis)):
                F[name].append(X.astype(np.float32))
            mses = [None] * len(batch)
            preds_all = []
            for s, lp in zip(batch, lps):
                preds_all.append({it["question"]: max(d, key=lambda n: float(d[n])) for it, d in zip(s["items"], lp)})
            if sname == "eval":
                nidx = [noise_idx[sid] for sid, _ in chunk]
                noise = torch.cat([torch.randn(1, H, A, generator=torch.Generator().manual_seed(
                    a.seed * 1_000_003 + n)) for n in nidx]).to(dev)
                s3 = [{**s, "committed": {**s["committed"], **p}} for s, p in zip(batch, preds_all)]
                with torch.no_grad():
                    z = sample_actions(m.expert, m.cond(s3, ctx, mask, dev), a.steps, noise)
                    tgt, valid, _ = m.targets(batch, dev)
                    vm = valid[..., None]
                    mse = ((((z - tgt) ** 2) * vm).sum((1, 2)) / (vm.sum((1, 2)) * A)).float().cpu().numpy()
                mses = [float(x) for x in mse]
            for j, ((sid, s), lp, p) in enumerate(zip(chunk, lps, preds_all)):
                rec = {"id": sid, "set": sname}
                if a.data == "r2":
                    rec.update(L.parse_id(sid), part=sname)
                else:
                    rec.update(ep=sid.rsplit("_k", 1)[0], kind=sid.split("_ep")[0])
                rec["preds"] = p
                rec["correct"] = {it["question"]: p[it["question"]] in (it.get("target") or []) for it in s["items"]}
                rec["margin"] = {it["question"]: round(_margin(d), 5) for it, d in zip(s["items"], lp)}
                if mses[j] is not None:
                    rec["mse"] = round(mses[j], 7)
                meta_f.write(json.dumps(rec) + "\n")
                ids.append(sid)
            done = b0 + len(chunk)
            if done % (a.batch * 125) < a.batch or done == len(items):
                print(json.dumps({"event": "progress", "set": sname, "done": done, "n": len(items),
                                  "s_per_snap": round((time.time() - ts) / done, 4)}), flush=True)
        meta_f.write(json.dumps({"event": "summary", "set": sname, "n": len(ids), "ckpt": a.ckpt,
                                 "seconds": round(time.time() - ts, 1)}) + "\n")
        meta_f.close()
        np.savez(os.path.join(a.out_dir, f"{sname}.npz"), ids=np.array(ids),
                 **{k: np.concatenate(v) for k, v in F.items()})
    hook.handle.remove()


if __name__ == "__main__":
    main()
