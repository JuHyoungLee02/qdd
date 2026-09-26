"""E-SR1e part L1 (docs/stage3/prereg_sr1e.md §2.2): contrastive decision guidance (CDG) at evaluation time on an
existing checkpoint, no training (docs/research/lit_sweep_2026-09-26.md §4 L1).

Every Euler step of the flow sampler: v = v(o, d) + (w_eff - 1) * [v(o, d) - v(o, d_self)], d = the condition of
the row (forced / true / edit ...), d_self = the model's own decision (the 'pred' condition of tools/sr0/sr0_eval,
row 1 of every snapshot batch), both at the same x_t. w_eff = 1 + (w - 1) * a with a = the authority proxy of the
snapshot (tools/sr1d/strata.py meta; far a = 1, near a = 0, band in between, unknown -> no a -> w_eff = 1).
The rest is tools/sr1d/sr1d_eval.py unchanged (records, conditions, noise, latency); the latency path (B = 1) runs the
two velocity passes whenever w_eff != 1.
  python tools/sr1e/cdg_eval.py --w 2 -- <tools/sr1d/sr1d_eval.py arguments>
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_HERE, "..", "..")
sys.path.insert(0, ROOT)

STATE = {"w": 1.0, "w_eff": 1.0, "self_idx": 1}


def w_eff(w: float, a) -> float:
    return 1.0 if a is None else 1.0 + (w - 1.0) * float(a)


class TrackMeta(dict):
    """meta[key] (read once per snapshot by sr1d_eval before sampling) sets the snapshot's w_eff."""

    def __getitem__(self, key):
        m = dict.__getitem__(self, key)
        STATE["w_eff"] = w_eff(STATE["w"], m.get("a"))
        return m


def guided_sampler(orig):
    import torch

    @torch.no_grad()
    def sample_actions(expert, cond, steps=10, noise=None):
        w = STATE["w_eff"]
        if w == 1.0:
            return orig(expert, cond, steps, noise)
        enc = expert.encode(cond)
        B = cond["proprio"].shape[0]
        si = STATE["self_idx"] if B > 1 else 0
        enc_s = {k: (v[si:si + 1].expand(B, *v.shape[1:]) if torch.is_tensor(v) else v) for k, v in enc.items()}
        shape = (B, expert.cfg.horizon, expert.cfg.act_dim)
        x = torch.randn(shape, device=cond["proprio"].device) if noise is None else noise.float()
        dt = -1.0 / steps
        for i in range(steps):
            t = torch.full((B,), 1.0 + i * dt, device=x.device)
            v = expert.velocity(enc, x, t)
            vs = expert.velocity(enc_s, x, t)
            x = x + dt * (v + (w - 1.0) * (v - vs))
        return x
    return sample_actions


def main():
    argv = sys.argv[1:]
    cut = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=float, required=True)
    a = ap.parse_args(argv[:cut])
    if a.w < 1.0:
        raise SystemExit("--w >= 1")
    STATE["w"] = a.w
    from harvest.train import stageb_expert as X
    X.sample_actions = guided_sampler(X.sample_actions)
    spec = importlib.util.spec_from_file_location("sr1d_eval", os.path.join(ROOT, "tools", "sr1d", "sr1d_eval.py"))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    orig_read = M.read_meta
    M.read_meta = lambda path: TrackMeta(orig_read(path))
    E0 = M.E0
    names = E0.cond_names(False)
    if names[:2] != ["true", "pred"] and tuple(names[:2]) != ("true", "pred"):
        raise SystemExit(f"condition order changed: {names[:2]}")
    M.main(argv[cut + 1:])


if __name__ == "__main__":
    main()
