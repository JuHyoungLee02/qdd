"""JCR training / offline evaluation (docs/stage3/prereg_jcr1.md; jcr_design.md §0-2, §6, §7). venv_train, one GPU.
  train : python tools/jcr/train.py train --data /data/harvest/out/jcr/d0 [--data ...] --out /data/harvest/ckpt/jcr/jcr1_0
          [--steps 4000 --batch 8 --K 2 --lr 2e-4 --lr-heads 5e-4 --backbone qwen|tiny --max-val 400]
  eval  : python tools/jcr/train.py eval --ckpt DIR --data ... --out DIR/offline.json
Data = harvest.jcr.record episodes (<root>/<variant>/s<seed>/samples.jsonl + img/); samples without images and RaC
'tail' samples are dropped; split by seed (seed % 20 == 0 -> val). Sampling weights: normal episodes >= half of the
mass, and inside disturbed episodes recover : progress = 1 : 1.5 (§0-2). Every step: batch real samples, each with K
forced-joystick branches (features.branch). Offline metrics (val, branches with a fixed seed): joystick compliance
(cos(predicted, truth end displacement) > 0.707) far (> 2 cm) / near, endpoint error, event accuracy + |row error|,
contact F1, anomaly AUROC."""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.jcr import features as FT  # noqa: E402

MODEL_DIR = "/data/harvest/models/Qwen3-VL-4B-Instruct"
RECOVER_SHARE = 1.0 / 2.5  # recover : progress = 1 : 1.5 inside disturbed episodes


def load_data(roots):
    tr, va = [], []
    for root in roots:
        for sp in sorted(glob.glob(os.path.join(root, "*", "s*", "samples.jsonl"))):
            d = os.path.dirname(sp)
            if not os.path.exists(os.path.join(d, "ep.json")):
                continue
            ep = json.load(open(os.path.join(d, "ep.json")))
            normal = bool(ep["plan"]["normal"])
            seed = int(ep["seed"])
            old_rule = ep.get("anom_rule", 1) < 2  # rule 1 flagged 'dropped' on holding-predicate flicker
            for line in open(sp):
                s = json.loads(line)
                if "img" not in s or s.get("window") == "tail":
                    continue
                if old_rule:
                    s["anomaly"] = [k for k in s.get("anomaly", []) if k != "dropped"]
                s["_imgs"] = [["head camera", os.path.join(d, "img", s["img"] + "_head.jpg")],
                              ["right wrist camera", os.path.join(d, "img", s["img"] + "_wrist.jpg")]]
                s["_normal"], s["_seed"] = normal, seed
                (va if seed % 20 == 0 else tr).append(s)
    return tr, va


def weights(ss):
    w = np.ones(len(ss))
    nm = np.array([s["_normal"] for s in ss])
    rc = np.array([s.get("window") == "recover" for s in ss])
    dis = ~nm
    n_rc, n_pg = (dis & rc).sum(), (dis & ~rc).sum()
    if n_rc and n_pg:  # recover share inside disturbed episodes
        w[dis & rc] = RECOVER_SHARE / n_rc
        w[dis & ~rc] = (1 - RECOVER_SHARE) / n_pg
        w[dis] *= dis.sum()
    if nm.any() and dis.any() and w[nm].sum() < w[dis].sum():  # normal >= half of the mass
        w[nm] *= w[dis].sum() / w[nm].sum()
    return w / w.sum()


def make_model(a, tr, device):
    import torch

    from harvest.jcr.model import JCR
    from harvest.train.stageb_model import HFEncoder
    from harvest.train.stageb_train import load_backbone
    dtype = torch.float32 if a.backbone == "tiny" else torch.bfloat16
    bb, proc, hid = load_backbone(a.backbone, MODEL_DIR, device, lora={"r": 32, "alpha": 64, "dropout": 0.05},
                                  dtype=dtype)
    bb.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    bb.enable_input_require_grads()
    m = JCR(bb, hid, FT.Norm.fit(tr))
    m.expert.to(device), m.head.to(device)
    return m, HFEncoder(proc, "")


def cmd_train(a):
    import torch
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    tr, va = load_data(a.data)
    print(json.dumps({"train": len(tr), "val": len(va)}), flush=True)
    device = "cuda"
    m, enc = make_model(a, tr, device)
    heads = list(m.expert.parameters()) + list(m.head.parameters())
    lora = [p for p in m.backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW([{"params": heads, "lr": a.lr_heads}, {"params": lora, "lr": a.lr}], weight_decay=0.0)
    wu = max(1, int(0.03 * a.steps))
    sch = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / wu if s < wu else 0.5 * (1 + math.cos(math.pi * min(1.0, (s - wu) / max(1, a.steps - wu)))))
    w = weights(tr)
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "train.jsonl"), "a")
    t0 = time.time()
    for step in range(a.steps):
        idx = rng.choice(len(tr), size=a.batch, p=w)
        rows = [(tr[i]["_imgs"], [tr[i]] + [FT.branch(tr[i], rng) for _ in range(a.K)]) for i in idx]
        m.train()
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=a.backbone != "tiny"):
            loss, parts = m.losses(enc, rows, device)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(heads + lora, 1.0)
        opt.step()
        sch.step()
        if step % 20 == 0 or step == a.steps - 1:
            rec = {"step": step, "loss": round(float(loss), 5), **{k: round(v, 5) for k, v in parts.items()},
                   "gn": round(float(gn), 3), "s_per_step": round((time.time() - t0) / (step + 1), 3)}
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print("STEP " + json.dumps(rec), flush=True)
        if a.save_every and (step + 1) % a.save_every == 0 and step + 1 < a.steps:
            m.save(os.path.join(a.out, f"step{step + 1}"), {"step": step + 1})
    m.save(os.path.join(a.out, "last"), {"step": a.steps, "data": a.data, "n_train": len(tr), "args": vars(a)})
    if va:
        res = offline_eval(m, enc, va[:a.max_val] if a.max_val else va, device, seed=0)
        json.dump(res, open(os.path.join(a.out, "last", "offline.json"), "w"), indent=1)
        print("OFFLINE " + json.dumps(res), flush=True)
    print("TRAIN_DONE", flush=True)


def offline_eval(m, enc, va, device, seed=0):
    rng = np.random.default_rng(seed + 1)
    m.eval()
    comp = {"far": [], "near": []}
    end_mm, ev_ok, ev_row, cp, ct, ap, at = [], [], [], [], [], [], []
    for s in va:
        grp = [s] + [FT.branch(s, rng) for _ in range(2)]
        outs = m.predict(enc, s["_imgs"], grp, device, seed=seed)
        for g, o in zip(grp, outs):
            pd, td = np.asarray(o["delta"])[-1], FT.delta(g)[-1]
            end_mm.append(float(np.linalg.norm(pd - td)) * 1e3)
            if "branch" in g and np.linalg.norm(td) > 1e-3:
                c = float(np.dot(pd, td) / (np.linalg.norm(pd) * np.linalg.norm(td) + 1e-12))
                comp["far" if g["branch"]["offset_m"] > 0.02 else "near"].append(c > 0.7071)
            ec, pc = FT.event_class(g), int(np.argmax(o["event_p"]))
            k1, r1 = FT.decode_event(ec)
            k2, r2 = FT.decode_event(pc)
            ev_ok.append(k1 == k2)
            if k1 == k2 and r1 is not None and r2 is not None:
                ev_row.append(abs(r1 - r2))
            cp.append(o["contact_p"])
            ct.append(bool(g.get("contact")))
            ap.append(o["anomaly_p"][-1])
            at.append(bool(g.get("anomaly")))
    cp, ct = np.array(cp), np.array(ct)
    tp = int(((cp > 0.5) & ct).sum())
    prec = tp / max(int((cp > 0.5).sum()), 1)
    rec = tp / max(int(ct.sum()), 1)
    return {"n": len(va), "compliance_far": float(np.mean(comp["far"])) if comp["far"] else None,
            "compliance_near": float(np.mean(comp["near"])) if comp["near"] else None,
            "n_far": len(comp["far"]), "n_near": len(comp["near"]),
            "end_err_mm_p50": float(np.median(end_mm)), "end_err_mm_p90": float(np.percentile(end_mm, 90)),
            "event_acc": float(np.mean(ev_ok)), "event_row_err_p50": float(np.median(ev_row)) if ev_row else None,
            "contact_f1": 2 * prec * rec / max(prec + rec, 1e-9), "contact_prec": prec, "contact_rec": rec,
            "anomaly_auroc": auroc(np.array(ap), np.array(at))}


def auroc(p, y):
    if y.all() or not y.any():
        return None
    order = np.argsort(p)
    r = np.empty(len(p))
    r[order] = np.arange(1, len(p) + 1)
    n1 = y.sum()
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)))


def cmd_eval(a):
    from harvest.jcr.model import load
    _, va = load_data(a.data)
    m, enc = load(a.ckpt, MODEL_DIR, "cuda")
    res = offline_eval(m, enc, va[:a.max_val] if a.max_val else va, "cuda")
    json.dump(res, open(a.out, "w"), indent=1)
    print("OFFLINE " + json.dumps(res), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["train", "eval"])
    ap.add_argument("--data", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--K", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lr-heads", type=float, default=5e-4)
    ap.add_argument("--backbone", default="qwen", choices=["qwen", "tiny"])
    ap.add_argument("--max-val", type=int, default=400)
    ap.add_argument("--save-every", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    (cmd_train if a.mode == "train" else cmd_eval)(a)


if __name__ == "__main__":
    main()
