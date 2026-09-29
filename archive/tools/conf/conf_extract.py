"""E-CONF extraction (docs/stage3/prereg_conf.md §2-§3). No training: an existing checkpoint's own decide pass
(StageB.forward_shared, batched, as E-NOV0) -> per question the option log-probs, the prediction (argmax) and the
label target set; then the expert chunk conditioned on the predicted decisions (as runtime decide -> chunk) with
1 + K flow-noise draws: the primary draw (E-NOV0 / E-SR0 noise numbering) gives the normalized chunk MSE to the
recorded action over valid steps, all 1 + K draws give the flow dispersion (conf_lib.dispersion).
  R2 cal  (E-NOV0 eval split, val):  --data r2 --pool <ma2 views> --set cal --noise-ref <E-MA2 eval_set.json>
  R2 test (never-trained episodes):  --data r2 --pool <conf views> --set test --noise-offset 100000
  S-E2E   (val split):               --data se2e --se2e-root R [motion-line args] --set se2e
  common: --ckpt DIR --out JSONL [--batch 8 --k-extra 4 --steps 10 --latency 200 --limit N]
One json line per snapshot (conf_lib record) + a summary line; with --latency N the first N snapshots also time the
chunk path for one snapshot with 1 draw and with 1 + K draws (GPU synchronised, 3 repeats each, median).
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nov0"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

import conf_lib as L  # noqa: E402
import nov0_lib as N  # noqa: E402

HZ = {"r2": 30, "se2e": 10}


def build_parser():
    from harvest.train import stageb_train as TR
    ap = TR.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    p = sub.choices["predict"]
    p.add_argument("--set", required=True, choices=("cal", "test", "se2e"))
    p.add_argument("--k-extra", type=int, default=4)
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--latency", type=int, default=0)
    p.add_argument("--limit", type=int, default=0, help="dry run: N evenly spaced snapshots")
    p.add_argument("--noise-ref", default="", help="cal: E-MA2 eval_set.json (E-NOV0 noise numbering)")
    p.add_argument("--noise-offset", type=int, default=100000, help="test: noise index = offset + position")
    return ap


def snapshots(a):
    """[(id, sample, noise index)] in a fixed order."""
    from harvest.train import stageb_data as D
    from harvest.train import stageb_train as TR
    if a.data == "se2e":
        _, _, _, va = TR._load_data(a)
        val = TR.val_subset(va, 0, 0, 0)
        return [(s["key"], s, i) for i, s in enumerate(val)]
    from harvest.train.r2_ma2 import sample_id
    samples, _ = D.load_for_training("r2", pool=a.pool, rows=a.rows, state=a.state, wrist=not a.no_wrist)
    by = {}
    for s in samples:
        sid = sample_id(s["context"]["images"][0][1])
        if sid in by:
            raise SystemExit(f"duplicate snapshot id {sid}")
        by[sid] = s
    if a.set == "cal":
        ids = sorted(i for i, s in by.items() if s["split"] == "val")
        nidx = N.noise_index(json.load(open(a.noise_ref))["ids"], ids)
    else:
        ids = sorted(by)
        nidx = {i: a.noise_offset + n for n, i in enumerate(ids)}
    return [(i, by[i], nidx[i]) for i in ids]


def meta_of(sid, a):
    if a.data == "r2":
        d = N.parse_id(sid)
        return {"ep": d["ep"], "t": d["k"] / HZ["r2"], "variant": d["variant"], "task": d["task"], "kind": d["kind"],
                "seed": d["seed"]}
    ep, k = sid.rsplit("_k", 1)
    return {"ep": ep, "t": int(k) / HZ["se2e"], "kind": sid.split("_ep")[0]}


def _sync(dev):
    import torch
    if dev.type == "cuda":
        torch.cuda.synchronize(dev)


def time_chunk(m, s, ctx, mask, noises, steps, dev):
    """(seconds with 1 draw, seconds with len(noises) draws) of cond + Euler sampling for one snapshot."""
    import torch

    from harvest.train.stageb_expert import sample_actions
    out = []
    for n in (1, len(noises)):
        ts = []
        for _ in range(3):
            _sync(dev)
            t0 = time.perf_counter()
            with torch.no_grad():
                cond = m.cond([s] * n, ctx.repeat(n, 1, 1), mask.repeat(n, 1), dev)
                sample_actions(m.expert, cond, steps, noises[:n])
            _sync(dev)
            ts.append(time.perf_counter() - t0)
        out.append(sorted(ts)[1])
    return out


def main(argv=None):
    import torch

    from harvest.train import stageb_train as TR
    from harvest.train.sr1c_film import load_heads_sr1c
    from harvest.train.stageb_expert import sample_actions
    a = build_parser().parse_args(["predict"] + (argv if argv is not None else sys.argv[1:]))
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    t_load = time.time()
    snaps = snapshots(a)
    n_all = len(snaps)
    if a.limit and a.limit < len(snaps):
        snaps = [snaps[i * len(snaps) // a.limit] for i in range(a.limit)]
    print(json.dumps({"event": "loaded", "n": n_all, "n_run": len(snaps), "s": round(time.time() - t_load, 1)}),
          flush=True)
    bb, proc, _ = TR.load_backbone("qwen", a.model, dev, adapter=os.path.join(a.ckpt, "adapter"))
    m = TR.aux_model(a, load_heads_sr1c(a.ckpt, bb, dev).eval(), new=False)
    m.shared = True
    m, enc = TR.temporal_model(a, m, proc)
    H, A = m.expert.cfg.horizon, m.expert.cfg.act_dim
    S = 1 + a.k_extra
    fo = open(a.out, "w", encoding="utf-8")
    ts, lat = time.time(), []
    for b0 in range(0, len(snaps), a.batch):
        chunk = snaps[b0:b0 + a.batch]
        batch = [s for _, s, _ in chunk]
        with torch.no_grad():
            ctx, mask, lps = m.forward_shared(batch, enc, dev, grad=False)
        preds = [{it["question"]: max(d, key=lambda n: float(d[n])) for it, d in zip(s["items"], lp)}
                 for s, lp in zip(batch, lps)]
        s3 = [{**s, "committed": {**s["committed"], **p}} for s, p in zip(batch, preds)]
        noises = [torch.cat([torch.randn(1, H, A, generator=torch.Generator().manual_seed(x))
                             for x in L.noise_seeds(n, a.k_extra)]) for _, _, n in chunk]
        with torch.no_grad():
            rep = [x for x in s3 for _ in range(S)]
            cond = m.cond(rep, ctx.repeat_interleave(S, 0), mask.repeat_interleave(S, 0), dev)
            z = sample_actions(m.expert, cond, a.steps, torch.cat(noises).to(dev))
            tgt, valid, _ = m.targets(batch, dev)
            z = z.view(len(batch), S, H, A)
            vm = valid[:, None, :, None]
            mse = ((((z - tgt[:, None]) ** 2) * vm).sum((2, 3)) / (vm.sum((2, 3)) * A)).float().cpu().numpy()
            zc, vc = z.float().cpu().numpy(), valid.cpu().numpy()
        for j, (sid, s, n) in enumerate(chunk):
            rec = {"id": sid, "nidx": n, **meta_of(sid, a), "mse": round(float(mse[j, 0]), 7),
                   "mse_k": [round(float(x), 7) for x in mse[j, 1:]], "disp": float(L.dispersion(zc[j], vc[j] > 0)),
                   "q": {it["question"]: {"lp": {k: round(float(v), 5) for k, v in d.items()},
                                          "target": list(it.get("target") or []), "pred": preds[j][it["question"]]}
                         for it, d in zip(s["items"], lps[j])}}
            fo.write(json.dumps(rec) + "\n")
            if len(lat) < a.latency:
                nz = noises[j].to(dev)
                lat.append(time_chunk(m, s3[j], ctx[j:j + 1], mask[j:j + 1], nz, a.steps, dev))
        done = b0 + len(chunk)
        if done % (a.batch * 125) < a.batch or done == len(snaps):
            print(json.dumps({"event": "progress", "done": done, "n": len(snaps),
                              "s_per_snap": round((time.time() - ts) / done, 4)}), flush=True)
    summ = {"event": "summary", "set": a.set, "ckpt": a.ckpt, "data": a.data, "n": len(snaps), "n_loaded": n_all,
            "k_extra": a.k_extra, "steps": a.steps, "seconds": round(time.time() - ts, 1)}
    if lat:
        t1 = sorted(x[0] for x in lat)
        tk = sorted(x[1] for x in lat)
        dd = sorted(x[1] - x[0] for x in lat)
        q = lambda v, p: round(1e3 * v[int(p * (len(v) - 1))], 3)  # noqa: E731
        summ["latency_ms"] = {"n": len(lat), "one_p50": q(t1, 0.5), "one_p95": q(t1, 0.95), "k_p50": q(tk, 0.5),
                              "k_p95": q(tk, 0.95), "added_p50": q(dd, 0.5), "added_p95": q(dd, 0.95)}
    fo.write(json.dumps(summ) + "\n")
    fo.close()
    print(json.dumps(summ), flush=True)


if __name__ == "__main__":
    main()
