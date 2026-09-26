"""E-SR1c evaluation (docs/stage3/prereg_sr1c.md §3): tools/sr0/sr0_eval.py (imported, not modified) + the sr1c
loader (sr1c_film.load_heads_sr1c: plain checkpoints unchanged, adaln@v1 with the estimated authority), the
authority of every snapshot (privileged from the row's aux, estimated from the aux head), plausible-edit conditions
and the extra records of the near-contact / whole-range rules.

Conditions per snapshot = sr0_eval.condition_set (true, pred, xy:<9>, z:<3>, mag:<5>, flip, pid:close|open) +
  edit:<theta> for theta in EDIT_DEG when the recorded chunk moves >= EDIT_MIN_M in xy: the edit vector
  e = rot_z(recorded chunk xy displacement, theta), length clipped to [1, 5] cm (an Astra edit is <= 5 cm);
  committed dir_xy = its 8-sector (labels_v2 dead band not applied: the sector of the angle), mag_coarse =
  labels_v2.mag_label(e), dir_z / target / phase = labels. Adherence to an edit = chunk xy displacement
  >= 0.1 mm and cos(chunk xy, e) > 0.5.
Per condition record [dx, dy, dz, g0, g1, mse, dzmin] (dzmin = min over the chunk of FK z(target_i) - FK z(target_0)).
Per snapshot: a_priv / dist_priv / stratum, a_hat / dist_hat (aux head), auth_model (C2: the gate value used),
tcp_z (measured finger midpoint height above the table at the snapshot, R2 npz), true_end_err (|FK(true chunk last)
- FK(recorded last)|, m), edits {theta: [e_x, e_y, sector, mag]}.
  python tools/sr1c/sr1c_eval.py --data r2 --pool P --rows ROWS --eval-set JSON --grip --seed 0 --ckpt DIR \
      --r2 /data/harvest/r2/train --out JSONL [--latency 50] [--limit N]
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import time

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

_spec = importlib.util.spec_from_file_location("sr0_eval", os.path.join(ROOT, "tools", "sr0", "sr0_eval.py"))
E0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E0)

EDIT_DEG = (30, -30, 45, -45, 90, -90, 180)
EDIT_MIN_M = 0.005
EDIT_LEN_M = (0.01, 0.05)


def sector(dx: float, dy: float) -> str:
    return E0.DIR_XY8[int(round(math.atan2(dy, dx) / (math.pi / 4))) % 8]


def edit_conditions(labels: dict, disp_gt) -> list:
    """[(name, committed, None, info)] of the plausible-edit / stress conditions (empty if the recorded chunk xy
    displacement is below EDIT_MIN_M)."""
    from harvest.labels_v2 import mag_label
    v = np.asarray(disp_gt[:2], float)
    n = float(np.linalg.norm(v))
    if n < EDIT_MIN_M:
        return []
    L = min(max(n, EDIT_LEN_M[0]), EDIT_LEN_M[1])
    out = []
    for th in EDIT_DEG:
        t = math.radians(th)
        e = np.array([math.cos(t) * v[0] - math.sin(t) * v[1], math.sin(t) * v[0] + math.cos(t) * v[1]]) * (L / n)
        c = {**labels, "dir_xy": sector(e[0], e[1]), "mag_coarse": mag_label([e[0], e[1], 0.0])}
        out.append((f"edit:{th}", c, None, [round(float(e[0]), 6), round(float(e[1]), 6), c["dir_xy"],
                                             c["mag_coarse"]]))
    return out


def snap_meta(s: dict) -> dict:
    from harvest.train import sr1c_authority as A
    d, c = A.stage_distance(s["aux"], s["phase_id"])
    a = A.privileged(s["aux"], s["phase_id"])
    return {"a_priv": a, "dist_priv": d, "contact_priv": c, "stratum": A.stratum(a), "phase": s["phase_id"]}


def build_parser():
    ap = E0.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    p = sub.choices["predict"]
    p.add_argument("--r2", default="/data/harvest/r2/train", help="R2 episode npz root (tcp height)")
    p.add_argument("--latency", type=int, default=0, help="also time the chunk path on the first N snapshots")
    return ap


def main(argv=None):
    import torch

    from harvest.train import sr1c_authority as A
    from harvest.train import stageb_train as TR
    from harvest.train.se2e_data import fk_ee, load_arm_chain
    from harvest.train.sr1c_film import load_heads_sr1c
    from harvest.train.stageb_expert import sample_actions
    a = build_parser().parse_args(["predict"] + (argv if argv is not None else sys.argv[1:]))
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    snaps = E0.snapshots(a)
    if a.limit:
        snaps = snaps[:a.limit]
    bb, proc, _ = TR.load_backbone("qwen", a.model, dev, adapter=os.path.join(a.ckpt, "adapter"))
    m = load_heads_sr1c(a.ckpt, bb, dev).eval()
    m.shared = True
    m, enc = TR.temporal_model(a, m, proc)
    E0.check_vocab(m.vocabs["dec"].to_json(), m.vocabs["phase"].to_json(), a.grip)
    gated = hasattr(m, "last_auth")
    chains = {}
    H, Ad = m.expert.cfg.horizon, m.expert.cfg.act_dim
    write = TR._writer(a.out)
    n_skip, lat = 0, []
    npz = {}
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
        ex = np.asarray(s["action_exec"], float)
        dgt = fk(ex[-1, :7]) - fk(ex[0, :7])
        g = torch.Generator().manual_seed(a.seed * 1_000_003 + i)
        noise = torch.randn(1, H, Ad, generator=g).to(dev)
        with torch.no_grad():
            ctx, mask, lps = m.forward_shared([s], enc, dev, grad=False)
            preds = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s["items"], lps[0])}
            cs = E0.condition_set(labels, preds, a.grip)
            es = edit_conditions(labels, dgt)
            allc = [(n, c, p) for n, c, p in cs] + [(n, c, p) for n, c, p, _ in es]
            batch = [{**s, "committed": c, **({"phase_id": p} if p else {})} for _, c, p in allc]
            B = len(batch)
            cond = m.cond(batch, ctx.repeat(B, 1, 1), mask.repeat(B, 1), dev)
            auth_model = list(m.last_auth) if gated else None
            z = sample_actions(m.expert, cond, a.steps, noise.repeat(B, 1, 1))
            tgt, valid, _ = m.targets([s], dev)
            vm = valid[..., None]
            mse = ((((z - tgt) ** 2) * vm).sum((1, 2)) / (vm.sum() * Ad)).float().cpu().numpy()
            reg, cls = m.aux(ctx, mask)
            reg, cls = reg[0].float().cpu().numpy(), cls[0].float().cpu().numpy()
        d_hat, c_hat = A.estimated_distance(reg, cls, s["phase_id"])
        zc = z.float().cpu().numpy()
        rec = {}
        true_end_err = None
        for j, (n, _, _) in enumerate(allc):
            act = m.norm.action(zc[j], s["action_script"], arm)
            P = fk(act[:, :7])
            d = P[-1] - P[0]
            rec[n] = [round(float(v), 7) for v in d] + [round(float(act[0, 7]), 5), round(float(act[-1, 7]), 5),
                                                         round(float(mse[j]), 7),
                                                         round(float((P[:, 2] - P[0, 2]).min()), 7)]
            if n == "true":
                true_end_err = float(np.linalg.norm(P[-1] - fk(ex[-1, :7])))
        v, t_, kd, ep, kk = sid.split("/")
        key = (v, t_, kd, ep)
        if key not in npz:
            npz.clear()
            npz[key] = np.load(os.path.join(a.r2, v, t_, kd, f"{ep}.npz"))["tcp"]
        tcp_z = float(npz[key][int(kk[1:])][2])
        write({"event": "snap", "i": i, "id": sid, "key": s["key"], "arm": arm, "labels": labels, "preds": preds,
               "disp_gt": [round(float(x), 7) for x in dgt], "c": rec, **snap_meta(s),
               "a_hat": A.authority(d_hat, s["phase_id"], c_hat), "dist_hat": round(float(d_hat), 5),
               "contact_hat": bool(c_hat), "auth_model": auth_model[0] if auth_model else None,
               "tcp_z": round(tcp_z, 5), "true_end_err": round(true_end_err, 7),
               "edits": {n: info for n, _, _, info in es}})
        if i < a.latency:
            lat += time_chunk(m, s, ctx, mask, noise, a.steps, dev)
    summ = {"event": "summary", "ckpt": a.ckpt, "data": a.data, "n": len(snaps) - n_skip, "n_skip": n_skip,
            "n_loaded": len(snaps), "grip": a.grip, "conds": E0.cond_names(a.grip), "edits": list(EDIT_DEG),
            "steps": a.steps, "seed": a.seed, "gated": gated, "keys_sha": TR._sha([k for k, _ in snaps])}
    if lat:
        ls = sorted(lat)
        summ["latency_ms"] = {"n": len(ls), "p50": round(1e3 * ls[len(ls) // 2], 3),
                              "p95": round(1e3 * ls[int(0.95 * (len(ls) - 1))], 3)}
    write(summ)


def time_chunk(m, s, ctx, mask, noise, steps, dev, reps=4, warm=3):
    """Seconds of the runtime chunk path for one sample (cond incl. the authority estimate + Euler sampling),
    context precomputed, true decision, CUDA synchronized; `warm` untimed calls first."""
    import torch

    from harvest.train.stageb_expert import sample_actions

    def sync():
        if dev.type == "cuda":
            torch.cuda.synchronize()
    out = []
    with torch.no_grad():
        for r in range(warm + reps):
            sync()
            t0 = time.perf_counter()
            sample_actions(m.expert, m.cond([s], ctx, mask, dev), steps, noise)
            sync()
            if r >= warm:
                out.append(time.perf_counter() - t0)
    return out


if __name__ == "__main__":
    main()
