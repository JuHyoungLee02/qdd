"""Torch side of the OPT-IN E-MA1 A factor `aux: trace5@v1` (se2e_trace; docs/stage3/prereg_ma1.md §3.1).

The existing AuxGeomHead gets 10 more regression outputs (the 5 trace points (u, v) in TRACE_SCALE units): its config
is saved with n_reg = len(AUX_REG) + 10, so a checkpoint reloads with stageb_model.load_heads + as_trace. TraceAuxHead
answers the base StageB.losses with the first len(AUX_REG) outputs (unchanged base aux loss: every S-E2E base target is
masked -> 0), and StageBTrace adds lam_aux * the masked smooth-L1 of ALL outputs against trace_aux_vecs (= the trace
loss, the base targets being masked) on the same backbone hidden states (no insulation: the gradient reaches the
backbone, §58). stageb_model / stageb_data (prompt-hash files, §71) are not touched; nothing is generated at run time.
"""
from __future__ import annotations

import numpy as np
import torch

from . import se2e_trace as TR
from . import stageb_data as D
from .stageb_expert import AuxConfig, AuxGeomHead, sample_actions
from .stageb_model import StageB

N_TRACE = 2 * TR.TRACE_POINTS


class TraceAuxHead(AuxGeomHead):
    """AuxGeomHead with N_TRACE extra regression outputs; forward() = the base view, full() = all outputs."""

    @property
    def n_base(self) -> int:
        return self.cfg.n_reg - N_TRACE

    def full(self, ctx, ctx_mask):
        return AuxGeomHead.forward(self, ctx, ctx_mask)

    def forward(self, ctx, ctx_mask):
        r, c = self.full(ctx, ctx_mask)
        return r[:, :self.n_base], c


class StageBTrace(StageB):
    """StageB + the trace5 auxiliary loss (the hidden states of the loss forward are reused)."""

    def forward_shared(self, samples, enc, device, grad=True):
        out = super().forward_shared(samples, enc, device, grad)
        self._fw_ctx = out[:2]
        return out

    def contexts(self, samples, enc, device, grad=True):
        out = super().contexts(samples, enc, device, grad)
        self._fw_ctx = out
        return out

    def losses(self, samples, enc, device, vqa=None, fm_t=None, fm_noise=None):
        for s in samples:
            a = s.get("aux") or {}
            if any(v is not None for v in (a.get("reg") or {}).values()) or \
                    any(v is not None for v in (a.get("cls") or {}).values()):
                raise ValueError(f"{s.get('key')}: trace5 runs assume S-E2E rows (no privileged aux targets)")
        self._fw_ctx = None
        total, logs = super().losses(samples, enc, device, vqa, fm_t, fm_noise)
        if self.aux is None or self.lam["aux"] <= 0:
            return total, logs
        ctx, mask = self._fw_ctx
        r, rm, c, cm = (torch.tensor(np.stack(x), device=device) for x in
                        zip(*[TR.trace_aux_vecs(s) for s in samples]))
        pr, pc = self.aux.full(ctx, mask)
        lr = (torch.nn.functional.smooth_l1_loss(pr, r, reduction="none") * rm).sum() / rm.sum().clamp_min(1.0)
        lc = (torch.nn.functional.binary_cross_entropy_with_logits(pc, c, reduction="none") * cm).sum() \
            / cm.sum().clamp_min(1.0)
        l_tr = lr + lc
        total = total + self.lam["aux"] * l_tr
        logs.update(aux=float(l_tr.detach()), aux_trace=float(lr.detach()), total=float(total.detach()))
        return total, logs


def as_trace(model: StageB) -> StageB:
    """Class switch of a loaded / built model whose aux head has the trace outputs."""
    if model.aux is None or model.aux.cfg.n_reg != len(D.AUX_REG) + N_TRACE:
        raise ValueError("aux head without the trace5 outputs")
    model.aux.__class__ = TraceAuxHead
    model.__class__ = StageBTrace
    return model


def as_base(model: StageB) -> StageB:
    model.__class__ = StageB
    return model


def with_trace_head(model: StageB) -> StageB:
    """Replace the (new, untrained) aux head by the same architecture with N_TRACE more regression outputs."""
    cfg = model.aux.cfg.to_json()
    cfg["n_reg"] = cfg["n_reg"] + N_TRACE
    dev = next(model.aux.parameters()).device
    model.aux = TraceAuxHead(AuxConfig(**cfg)).to(dev)
    return as_trace(model)


@torch.no_grad()
def extra_metrics(model, enc, val, device, seed=0, steps=10):
    """prereg §5 outside-the-rule metrics on the val samples: trace5 pixel error of the aux head (trace models only)
    and the sampled chunk error (normalized MSE, fixed noise) conditioned on the committed vs the PREDICTED (argmax)
    decision options."""
    from .stagea_loss import item_logprobs
    from .stageb_model import item_images
    was = model.training
    model.eval()
    g = torch.Generator().manual_seed(seed)
    tr = isinstance(model, StageBTrace)
    px, per_pt = [], [[] for _ in range(TR.TRACE_POINTS)]
    mse_c, mse_p = [], []
    for s in val:
        if model.shared and hasattr(enc, "p"):
            ctx, mask, lps = model.forward_shared([s], enc, device, grad=False)
            lps = lps[0]
        else:
            ctx, mask = model.contexts([s], enc, device, grad=False)
            lps = [item_logprobs(model.backbone, enc.inputs(it["text"], item_images(it), device),
                                 *enc.trie(it["names"]), enc.end, enc.pad) for it in s["items"]]
        if tr and s.get("trace5") is not None:
            pr, _ = model.aux.full(ctx, mask)
            uv = pr[0, -N_TRACE:].float().cpu().numpy().reshape(-1, 2) * TR.TRACE_SCALE
            t = np.asarray(s["trace5"]["uv"]).reshape(-1, 2)
            for i, ok in enumerate(s["trace5"]["mask"]):
                if ok:
                    e = float(np.hypot((uv[i, 0] - t[i, 0]) * TR.INTRINSICS["W"],
                                       (uv[i, 1] - t[i, 1]) * TR.INTRINSICS["H"]))
                    px.append(e)
                    per_pt[i].append(e)
        a, valid, _ = model.targets([s], device)
        n0 = torch.randn(a.shape, generator=g).to(device)
        pred = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s["items"], lps)}
        m = valid[..., None]
        for dst, smp in ((mse_c, s), (mse_p, {**s, "committed": {**s["committed"], **pred}})):
            z = sample_actions(model.expert, model.cond([smp], ctx, mask, device), steps, n0)
            dst.append(float((((z - a) ** 2) * m).sum() / (m.sum() * a.shape[-1])))
    model.train(was)
    trace = None
    if tr and px:
        trace = {"n_points": len(px), "mean": float(np.mean(px)), "median": float(np.median(px)),
                 "per_point_mean": [float(np.mean(x)) if x else None for x in per_pt]}
    return {"n": len(val), "trace_px": trace, "chunk_mse_committed": float(np.mean(mse_c)),
            "chunk_mse_predicted": float(np.mean(mse_p))}
