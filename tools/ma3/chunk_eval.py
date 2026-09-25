"""E-MA3 (docs/stage3/prereg_ma3.md): per-snapshot expert chunk errors + decision item records of one checkpoint.

`evaluate_records` is stageb_train.evaluate() with per-sample records: the SAME fixed-noise generator draws in the
same order (t, fm noise, sampling noise per snapshot), so its summary equals evaluate()'s bit for bit (pod test) and
the item records equal `stageb_train predict`'s. Per snapshot it also samples the chunk conditioned on the PREDICTED
(argmax) decisions with the same sampling noise (no extra draws; as se2e_trace_model.extra_metrics).
Output jsonl: 'item' records (as predict), 'chunk' records {key, mse_n, mae_q, fm, mse_pred}, one 'summary'.
Works for default and kvcond@v1 checkpoints (se2e_kvcond.load_heads_kv).
  python tools/ma3/chunk_eval.py --ckpt DIR --out JSONL [stageb_train predict data options]
"""
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from harvest.train import se2e_kvcond as K  # noqa: E402
from harvest.train import stageb_train as TR  # noqa: E402
from harvest.train.stageb_expert import sample_actions, sample_time  # noqa: E402


@torch.no_grad()
def evaluate_records(model, enc, val, device, seed=0, steps=10):
    """(summary = stageb_train.evaluate() output, item records, chunk records)."""
    was = model.training
    model.eval()
    g = torch.Generator().manual_seed(seed)
    fm, aux, dec, acc, mse_n, mae_q = [], [], [], [], [], []
    items, chunks = [], []
    for s in val:
        a, valid, _ = model.targets([s], device)
        t = sample_time(1, device, g)
        noise = torch.randn(a.shape, generator=g).to(device)
        _, logs = model.losses([s], enc, device, fm_t=t, fm_noise=noise)
        fm.append(logs["fm"])
        if "aux" in logs:
            aux.append(logs["aux"])
        fw = model.last_fw if model.shared and hasattr(enc, "p") else None
        if fw is None:
            raise SystemExit("chunk_eval: the shared (R3) path only")
        pred = {}
        if "dec" in logs:
            dec.append(logs["dec"])
            for it, lp in zip(s["items"], fw[2][0]):
                p = max(lp, key=lambda n: float(lp[n]))
                acc.append(p in it["target"])
                pred[it["question"]] = p
                items.append({"key": s["key"], "question": it["question"], "target": list(it["target"]),
                              "pred": p, "correct": acc[-1], "lp": {n: float(v) for n, v in lp.items()}})
        n0 = torch.randn(a.shape, generator=g).to(device)
        ctx, mask = fw[0], fw[1]
        z = sample_actions(model.expert, model.cond([s], ctx, mask, device), steps, n0)
        m = valid[..., None]
        mse_n.append(float((((z - a) ** 2) * m).sum() / (m.sum() * a.shape[-1])))
        act = model.norm.action(z[0].cpu().numpy(), s["action_script"], s.get("arm", "right"))
        ex = np.asarray(s["action_exec"], np.float32)
        vv = np.asarray(s["valid"]) > 0
        mae_q.append(float(np.abs(act[vv, :7] - ex[vv, :7]).mean()))
        zp = sample_actions(model.expert, model.cond([{**s, "committed": {**s["committed"], **pred}}], ctx, mask,
                                                      device), steps, n0)
        chunks.append({"key": s["key"], "mse_n": mse_n[-1], "mae_q": mae_q[-1], "fm": logs["fm"],
                       "mse_pred": float((((zp - a) ** 2) * m).sum() / (m.sum() * a.shape[-1]))})
    model.train(was)
    mean = lambda x: float(np.mean(x)) if x else None  # noqa: E731
    summ = {"fm": mean(fm), "aux": mean(aux), "dec": mean(dec), "dec_acc": mean(acc), "sample_mse_norm": mean(mse_n),
            "sample_mae_arm_rad": mean(mae_q), "n": len(val)}
    return summ, items, chunks


def main(argv=None):
    ap = K.build_parser()
    a = ap.parse_args(["predict"] + (argv if argv is not None else sys.argv[1:]))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _, _, _, va = TR._load_data(a)
    val = TR.val_subset(va, a.max_val, a.val_per_kind, a.val_seed)
    bb, proc, _ = TR.load_backbone("qwen", a.model, device, adapter=os.path.join(a.ckpt, "adapter"))
    m = K.load_heads_kv(a.ckpt, bb, device).eval()
    m.shared = not a.no_share
    m, enc = TR.temporal_model(a, m, proc)
    summ, items, chunks = evaluate_records(m, enc, val, device, a.seed)
    write = TR._writer(a.out)
    for r in items:
        write({"event": "item", **r})
    for r in chunks:
        write({"event": "chunk", **r})
    write({"event": "summary", "ckpt": a.ckpt, "val_keys_sha": TR._sha([s["key"] for s in val]),
           "expert_cond": "kvcond@v1" if isinstance(m, K.StageBKV) else "none",
           "chunk_mse_pred": float(np.mean([c["mse_pred"] for c in chunks])), **summ})


if __name__ == "__main__":
    main()
