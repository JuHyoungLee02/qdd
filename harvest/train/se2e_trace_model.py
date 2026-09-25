"""Torch side of the OPT-IN auxiliary trajectory targets (training only, nothing generated at run time):
  `trace5@v1`  E-MA1 A factor (se2e_trace; docs/stage3/prereg_ma1.md §3.1): 5 head-image points, 10 outputs
  `a3d@v1`     E-MA1b A3d (se2e_a3d; docs/stage3/prereg_ma1b.md): base-frame future end-effector displacements,
               12 outputs

The existing AuxGeomHead gets the extra regression outputs: its config is saved with n_reg = len(AUX_REG) + n_extra
(and stageb.json "aux_extra" = the version), so a checkpoint reloads with stageb_model.load_heads + as_trace.
TraceAuxHead answers the base StageB.losses with the first len(AUX_REG) outputs (unchanged base aux loss: every S-E2E
base target is masked -> 0), and StageBTrace adds lam_aux * the masked smooth-L1 of ALL outputs against the version's
target vectors (= the trajectory loss, the base targets being masked) on the same backbone hidden states (no
insulation: the gradient reaches the backbone, §58). base_view() = plain StageB with the head answering the base view:
the decision / chunk path is the default one (the aux head is never read there). stageb_model / stageb_data
(prompt-hash files, §71) are not touched.
"""
from __future__ import annotations

import numpy as np
import torch

from . import se2e_a3d as A3
from . import se2e_trace as TR
from . import stageb_data as D
from .stageb_expert import AuxConfig, AuxGeomHead, sample_actions
from .stageb_model import StageB

N_TRACE = 2 * TR.TRACE_POINTS
EXTRA = {TR.AUX_VER: (N_TRACE, TR.trace_aux_vecs), A3.A3D_VER: (A3.N_A3D, A3.a3d_aux_vecs)}


class TraceAuxHead(AuxGeomHead):
    """AuxGeomHead with n_extra extra regression outputs; forward() = the base view, full() = all outputs."""

    n_extra = N_TRACE

    @property
    def n_base(self) -> int:
        return self.cfg.n_reg - self.n_extra

    def full(self, ctx, ctx_mask):
        return AuxGeomHead.forward(self, ctx, ctx_mask)

    def forward(self, ctx, ctx_mask):
        r, c = self.full(ctx, ctx_mask)
        return r[:, :self.n_base], c


class StageBTrace(StageB):
    """StageB + the auxiliary trajectory loss of self.aux_ver (the hidden states of the loss forward are reused)."""

    aux_ver = TR.AUX_VER

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
                raise ValueError(f"{s.get('key')}: trajectory aux runs assume S-E2E rows (no privileged aux targets)")
        self._fw_ctx = None
        total, logs = super().losses(samples, enc, device, vqa, fm_t, fm_noise)
        if self.aux is None or self.lam["aux"] <= 0:
            return total, logs
        ctx, mask = self._fw_ctx
        vecs = EXTRA[self.aux_ver][1]
        r, rm, c, cm = (torch.tensor(np.stack(x), device=device) for x in zip(*[vecs(s) for s in samples]))
        pr, pc = self.aux.full(ctx, mask)
        lr = (torch.nn.functional.smooth_l1_loss(pr, r, reduction="none") * rm).sum() / rm.sum().clamp_min(1.0)
        lc = (torch.nn.functional.binary_cross_entropy_with_logits(pc, c, reduction="none") * cm).sum() \
            / cm.sum().clamp_min(1.0)
        l_tr = lr + lc
        total = total + self.lam["aux"] * l_tr
        logs.update(aux=float(l_tr.detach()), aux_trace=float(lr.detach()), total=float(total.detach()))
        return total, logs


def _set_head(model: StageB, ver: str) -> None:
    if ver not in EXTRA:
        raise ValueError(f"aux version {ver!r}: one of {sorted(EXTRA)}")
    n = EXTRA[ver][0]
    if model.aux is None or model.aux.cfg.n_reg != len(D.AUX_REG) + n:
        raise ValueError(f"aux head without the {ver} outputs")
    model.aux.__class__ = TraceAuxHead
    model.aux.n_extra = n


def as_trace(model: StageB, ver: str = TR.AUX_VER) -> StageB:
    """Class switch of a loaded / built model whose aux head has the `ver` outputs."""
    _set_head(model, ver)
    model.__class__ = StageBTrace
    model.aux_ver = ver
    return model


def base_view(model: StageB, ver: str | None = None) -> StageB:
    """Plain StageB (default losses / decisions / chunks) over a checkpoint with extra aux outputs."""
    ver = ver or getattr(model, "aux_ver", TR.AUX_VER)
    _set_head(model, ver)
    model.__class__ = StageB
    return model


def as_base(model: StageB) -> StageB:
    model.__class__ = StageB
    return model


def with_trace_head(model: StageB, ver: str = TR.AUX_VER) -> StageB:
    """Replace the (new, untrained) aux head by the same architecture with the `ver` extra regression outputs."""
    cfg = model.aux.cfg.to_json()
    cfg["n_reg"] = cfg["n_reg"] + EXTRA[ver][0]
    dev = next(model.aux.parameters()).device
    model.aux = TraceAuxHead(AuxConfig(**cfg)).to(dev)
    return as_trace(model, ver)


@torch.no_grad()
def extra_metrics(model, enc, val, device, seed=0, steps=10):
    """prereg outside-the-rule metrics on the val samples: the aux head's trajectory error (trace5: pixels; a3d: cm,
    per point) and the sampled chunk error (normalized MSE, fixed noise) conditioned on the committed vs the PREDICTED
    (argmax) decision options."""
    from .stagea_loss import item_logprobs
    from .stageb_model import item_images
    was = model.training
    model.eval()
    g = torch.Generator().manual_seed(seed)
    ver = getattr(model, "aux_ver", None) if isinstance(model, StageBTrace) else None
    npt = TR.TRACE_POINTS if ver == TR.AUX_VER else A3.A3D_POINTS - 1
    err, per_pt = [], [[] for _ in range(npt)]
    mse_c, mse_p = [], []
    for s in val:
        if model.shared and hasattr(enc, "p"):
            ctx, mask, lps = model.forward_shared([s], enc, device, grad=False)
            lps = lps[0]
        else:
            ctx, mask = model.contexts([s], enc, device, grad=False)
            lps = [item_logprobs(model.backbone, enc.inputs(it["text"], item_images(it), device),
                                 *enc.trie(it["names"]), enc.end, enc.pad) for it in s["items"]]
        if ver == TR.AUX_VER and s.get("trace5") is not None:
            pr, _ = model.aux.full(ctx, mask)
            uv = pr[0, -N_TRACE:].float().cpu().numpy().reshape(-1, 2) * TR.TRACE_SCALE
            t = np.asarray(s["trace5"]["uv"]).reshape(-1, 2)
            for i, ok in enumerate(s["trace5"]["mask"]):
                if ok:
                    e = float(np.hypot((uv[i, 0] - t[i, 0]) * TR.INTRINSICS["W"],
                                       (uv[i, 1] - t[i, 1]) * TR.INTRINSICS["H"]))
                    err.append(e)
                    per_pt[i].append(e)
        if ver == A3.A3D_VER and s.get("a3d") is not None:
            pr, _ = model.aux.full(ctx, mask)
            d = pr[0, -A3.N_A3D:].float().cpu().numpy().reshape(-1, 3) * A3.A3D_SCALE
            t = np.asarray(s["a3d"]["d"]).reshape(-1, 3)
            for i, ok in enumerate(s["a3d"]["mask"]):
                if ok:
                    e = float(np.linalg.norm(d[i] - t[i]) * 100.0)
                    err.append(e)
                    per_pt[i].append(e)
        a, valid, _ = model.targets([s], device)
        n0 = torch.randn(a.shape, generator=g).to(device)
        pred = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s["items"], lps)}
        m = valid[..., None]
        for dst, smp in ((mse_c, s), (mse_p, {**s, "committed": {**s["committed"], **pred}})):
            z = sample_actions(model.expert, model.cond([smp], ctx, mask, device), steps, n0)
            dst.append(float((((z - a) ** 2) * m).sum() / (m.sum() * a.shape[-1])))
    model.train(was)
    summ = None
    if err:
        summ = {"n_points": len(err), "mean": float(np.mean(err)), "median": float(np.median(err)),
                "per_point_mean": [float(np.mean(x)) if x else None for x in per_pt]}
    return {"n": len(val), "aux_ver": ver, "trace_px": summ if ver == TR.AUX_VER else None,
            "a3d_cm": summ if ver == A3.A3D_VER else None, "chunk_mse_committed": float(np.mean(mse_c)),
            "chunk_mse_predicted": float(np.mean(mse_p))}
