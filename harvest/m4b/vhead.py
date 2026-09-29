"""V1h: verification head on the frozen stage-A backbone (pod, venv_train, GPU 2).

  python -m harvest.m4b.vhead extract --fi ROOT --pool DIR --out FEATDIR [--model MERGED]
  python -m harvest.m4b.vhead train   --fi ROOT --pool DIR --feat FEATDIR --out RUNDIR
  python -m harvest.m4b.vhead latency --fi ROOT --feat FEATDIR --run RUNDIR [--model MERGED]

extract: one context forward per snapshot (D27: system -> head -> right wrist -> IMG state), last-layer hidden states
[T, 2560] saved in fp16 per episode (<feat>/<ep key with / -> _>.pt, {snapshot key: tensor}).
train: AuxGeomHead architecture (queries 4, width 512, heads 8) with the 9 test-predicate logits (BCE, None masked);
3-fold cross-fit over FI-DEV calibration seeds ({0-4},{5-9},{10-14}); training set of fold f = POOL fit + FI cal
seeds outside f. Writes logits.jsonl: key, fold-out logits (cal: out-of-fold head; others: mean of the 3 heads).
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from . import spec as FS

MERGED = "/data/harvest/ckpt/stageA/sftA_pool_v1/merged"
PREDS = FS.PREDS


def _fname(ep):
    return ep.replace("/", "_") + ".pt"


def load_all(fi_root, pool_dir, with_lines=True):
    from .data import fi_episodes, pool_snaps
    eps = fi_episodes(fi_root, with_lines=with_lines)
    snaps = [s for e in eps for s in e["snaps"]] + (pool_snaps(pool_dir) if pool_dir else [])
    return eps, snaps


def cmd_extract(a):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    from ..train.stageb_model import HFEncoder
    _, snaps = load_all(a.fi, a.pool)
    os.makedirs(a.out, exist_ok=True)
    by_ep = {}
    for s in snaps:
        by_ep.setdefault(s["ep"], []).append(s)
    dev = torch.device("cuda")
    proc = AutoProcessor.from_pretrained(a.model)
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, attn_implementation="sdpa").to(dev)
    model.eval()
    enc = HFEncoder(proc)
    t0, n = time.time(), 0
    for ep, ss in by_ep.items():
        f = os.path.join(a.out, _fname(ep))
        if os.path.exists(f):
            continue
        out = {}
        with torch.no_grad():
            for s in ss:
                x = enc.inputs(s["ctx"], s["images"], dev)
                h = model(**x, output_hidden_states=True, logits_to_keep=1).hidden_states[-1][0]
                out[s["key"]] = h.to(torch.float16).cpu()
                n += 1
        torch.save(out, f + ".tmp")
        os.replace(f + ".tmp", f)
        print(json.dumps({"ep": ep, "n": len(ss), "total": n, "s": round(time.time() - t0, 1),
                          "T": int(next(iter(out.values())).shape[0])}), flush=True)


def _labels(s):
    y = np.array([0.0 if s["truth"].get(p) is None else float(s["truth"][p]) for p in PREDS], np.float32)
    m = np.array([s["truth"].get(p) is not None for p in PREDS], np.float32)
    return y, m


def _batch(feats, idx, dev):
    import torch
    hs = [feats[i] for i in idx]
    T = max(h.shape[0] for h in hs)
    x = torch.zeros(len(hs), T, hs[0].shape[1], dtype=torch.float16)
    m = torch.zeros(len(hs), T, dtype=torch.long)
    for j, h in enumerate(hs):
        x[j, :h.shape[0]] = h
        m[j, :h.shape[0]] = 1
    return x.to(dev), m.to(dev)


def make_head(ctx_dim=2560):
    from ..train.stageb_expert import AuxConfig, AuxGeomHead
    return AuxGeomHead(AuxConfig(ctx_dim=ctx_dim, width=512, queries=4, heads=8, n_reg=0, n_cls=len(PREDS)))


def train_head(feats, Y, M, idx, dev, epochs=8, lr=3e-4, wd=0.01, bs=64, seed=0, log=print):
    import torch
    import torch.nn.functional as F
    torch.manual_seed(seed)
    head = make_head(feats[0].shape[1]).to(dev)
    opt = torch.optim.AdamW(head.parameters(), lr=lr, weight_decay=wd)
    rng = np.random.default_rng(seed)
    Yt, Mt = torch.tensor(Y), torch.tensor(M)
    step = 0
    for ep in range(epochs):
        order = rng.permutation(idx)
        tot, nb = 0.0, 0
        for b in range(0, len(order), bs):
            bi = order[b:b + bs]
            x, m = _batch(feats, bi, dev)
            _, lg = head(x, m)
            y, mk = Yt[bi].to(dev), Mt[bi].to(dev)
            loss = (F.binary_cross_entropy_with_logits(lg, y, reduction="none") * mk).sum() / mk.sum().clamp_min(1)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            tot += float(loss)
            nb += 1
            step += 1
        log({"epoch": ep, "loss": round(tot / max(nb, 1), 5), "steps": step})
    return head


def predict(head, feats, idx, dev, bs=64):
    import torch
    out = np.zeros((len(idx), len(PREDS)), np.float32)
    head.eval()
    with torch.no_grad():
        for b in range(0, len(idx), bs):
            bi = idx[b:b + bs]
            x, m = _batch(feats, bi, dev)
            out[b:b + len(bi)] = head(x, m)[1].float().cpu().numpy()
    return out


def cmd_train(a):
    import torch
    _, snaps = load_all(a.fi, a.pool, with_lines=False)
    feats, keep = [], []
    cache = {}
    for i, s in enumerate(snaps):
        f = os.path.join(a.feat, _fname(s["ep"]))
        if f not in cache:
            cache.clear()
            cache[f] = torch.load(f, weights_only=True) if os.path.exists(f) else {}
        h = cache[f].get(s["key"])
        if h is None:
            continue
        feats.append(h)
        keep.append(s)
    snaps = keep
    Y, M = map(np.stack, zip(*[_labels(s) for s in snaps]))
    os.makedirs(a.out, exist_ok=True)
    log_f = open(os.path.join(a.out, "log.jsonl"), "w")

    def log(r):
        log_f.write(json.dumps(r) + "\n")
        log_f.flush()
        print(json.dumps(r), flush=True)
    dev = torch.device("cuda")
    split = np.array([s["split"] for s in snaps])
    fold = np.array([-1 if s["fold"] is None else s["fold"] for s in snaps])
    log({"n": len(snaps), **{k: int((split == k).sum()) for k in ("pool_fit", "pool_eval", "fi_cal", "fi_eval")}})
    logits = np.zeros((len(snaps), len(PREDS)), np.float32)
    other = np.where(split != "fi_cal")[0]
    acc_other = np.zeros((len(other), len(PREDS)), np.float32)
    for f in range(3):
        tr = np.where((split == "pool_fit") | ((split == "fi_cal") & (fold != f)))[0]
        log({"fold": f, "train": int(len(tr))})
        head = train_head(feats, Y, M, tr, dev, log=lambda r: log({"fold": f, **r}))
        torch.save(head.state_dict(), os.path.join(a.out, f"head_fold{f}.pt"))
        oof = np.where((split == "fi_cal") & (fold == f))[0]
        logits[oof] = predict(head, feats, oof, dev)
        acc_other += predict(head, feats, other, dev) / 3.0
    logits[other] = acc_other
    with open(os.path.join(a.out, "logits.jsonl"), "w") as fo:
        for s, lg in zip(snaps, logits):
            fo.write(json.dumps({"key": s["key"], "logits": [round(float(v), 5) for v in lg]}) + "\n")
    log({"done": True})


def cmd_latency(a):
    """Added latency of the head on top of the context forward (batch 1, CUDA sync), plus the forward itself."""
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    from ..train.stageb_model import HFEncoder
    eps, _ = load_all(a.fi, None)
    ss = [s for e in eps if e["split"] == "fi_eval" for s in e["snaps"]][:a.n]
    dev = torch.device("cuda")
    proc = AutoProcessor.from_pretrained(a.model)
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, attn_implementation="sdpa").to(dev)
    model.eval()
    heads = []
    for f in range(3):
        h = make_head().to(dev)
        h.load_state_dict(torch.load(os.path.join(a.run, f"head_fold{f}.pt"), weights_only=True))
        heads.append(h.eval())
    enc = HFEncoder(proc)

    def sync():
        torch.cuda.synchronize()
    fw, hd, hd1 = [], [], []
    with torch.no_grad():
        for i, s in enumerate(ss):
            x = enc.inputs(s["ctx"], s["images"], dev)
            sync()
            t0 = time.perf_counter()
            hsd = model(**x, output_hidden_states=True, logits_to_keep=1).hidden_states[-1]
            sync()
            t1 = time.perf_counter()
            m = torch.ones(1, hsd.shape[1], dtype=torch.long, device=dev)
            h16 = hsd.to(torch.float16)
            _ = [h(h16, m)[1] for h in heads]
            sync()
            t2 = time.perf_counter()
            _ = heads[0](h16, m)[1]
            sync()
            t3 = time.perf_counter()
            if i >= 5:
                fw.append(t1 - t0)
                hd.append(t2 - t1)
                hd1.append(t3 - t2)
    q = lambda v, p: float(np.quantile(v, p) * 1e3)  # noqa: E731
    r = {"n": len(fw), "forward_ms": {"p50": q(fw, 0.5), "p95": q(fw, 0.95)},
         "head3_ms": {"p50": q(hd, 0.5), "p95": q(hd, 0.95)}, "head1_ms": {"p50": q(hd1, 0.5), "p95": q(hd1, 0.95)},
         "gpu": torch.cuda.get_device_name(0)}
    json.dump(r, open(os.path.join(a.run, "latency.json"), "w"), indent=1)
    print(json.dumps(r))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "train", "latency"])
    ap.add_argument("--fi", default="/data/harvest/m4b/fidev")
    ap.add_argument("--pool", default="/data/harvest/data/pool")
    ap.add_argument("--out", default="")
    ap.add_argument("--feat", default="/data/harvest/m4b/feat_v1h")
    ap.add_argument("--run", default="/data/harvest/m4b/v1h")
    ap.add_argument("--model", default=MERGED)
    ap.add_argument("--n", type=int, default=205)
    a = ap.parse_args(argv)
    {"extract": cmd_extract, "train": cmd_train, "latency": cmd_latency}[a.cmd](a)


if __name__ == "__main__":
    main()
