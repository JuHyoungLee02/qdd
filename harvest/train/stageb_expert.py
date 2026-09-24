"""Stage-B heads on top of the Qwen3-VL backbone: flow-matching action expert + auxiliary geometry head.

ActionExpert (pi0-style, minimal): a small transformer over [condition tokens | H action tokens].
  condition tokens = proprio (1) + skill (1) + phase (1) + committed decision tokens (one per DecCall question,
  learned embeddings of "question=option name"); action token = MLP([W x_t ; time embedding]) (+ the scripted
  chunk in residual mode) + position. Every block: self-attention over all tokens, cross-attention to the
  projected backbone hidden states of the context prompt (images + state text), MLP.
  Backbone conditioning = cross-attention to ONE layer's hidden-state sequence (default the last), not pi0.5's
  per-layer shared KV: the simplest form that keeps what KI needs (the expert reads backbone features, gradients
  stopped at that boundary) and works with any HF backbone without touching its attention code.
Flow matching (openpi convention): x_t = t * noise + (1 - t) * a, target velocity u = noise - a,
  t ~ 0.001 + 0.999 * Beta(1.5, 1); sampling integrates dx/dt = v from t = 1 (noise) to 0 in `steps` Euler steps.
Knowledge insulation (KI, 2505.23705): the expert sees `insulate(ctx)`: "stop" = ctx.detach() (default),
  "none" = full gradient (ablation), "scale:<g>" = gradient multiplied by g (InternVLA-M1-style ablation, D26 §4.2).
AuxGeomHead: attention pooling (learned queries) over the backbone hidden states -> regression + binary logits of
  privileged geometry; its gradient DOES reach the backbone (the model must learn geometry from the images, §58).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
from torch import nn
import torch.nn.functional as F


@dataclass
class ExpertConfig:
    ctx_dim: int = 2560  # Qwen3-VL-4B text hidden size
    act_dim: int = 8
    horizon: int = 15
    proprio_dim: int = 23
    n_questions: int = 5
    dec_vocab: int = 64
    skill_vocab: int = 32
    phase_vocab: int = 32
    width: int = 768
    depth: int = 8
    heads: int = 12
    mlp_ratio: int = 4
    residual: bool = False  # residual mode: the scripted chunk is an extra input
    dropout: float = 0.0

    def to_json(self):
        return asdict(self)


@dataclass
class AuxConfig:
    ctx_dim: int = 2560
    width: int = 512
    queries: int = 4
    heads: int = 8
    n_reg: int = 11
    n_cls: int = 7

    def to_json(self):
        return asdict(self)


def insulate(ctx: torch.Tensor, ki: str) -> torch.Tensor:
    if ki == "stop":
        return ctx.detach()
    if ki == "none":
        return ctx
    if ki.startswith("scale:"):
        g = float(ki[6:])
        return ctx * g + ctx.detach() * (1.0 - g)  # forward value unchanged, gradient scaled by g
    raise ValueError(f"ki must be stop | none | scale:<g>, got {ki!r}")


def time_embedding(t: torch.Tensor, dim: int, max_period: float = 4.0, min_period: float = 4e-3) -> torch.Tensor:
    """Sinusoidal embedding of t in [0, 1] (openpi posemb_sincos periods)."""
    half = dim // 2
    frac = torch.linspace(0.0, 1.0, half, device=t.device, dtype=torch.float32)
    period = min_period * (max_period / min_period) ** frac
    ang = t.float()[:, None] * (2 * math.pi / period)[None]
    return torch.cat([ang.sin(), ang.cos()], -1)


class Block(nn.Module):
    def __init__(self, w, heads, mlp_ratio, dropout):
        super().__init__()
        self.n1, self.n2, self.n3 = nn.LayerNorm(w), nn.LayerNorm(w), nn.LayerNorm(w)
        self.sa = nn.MultiheadAttention(w, heads, dropout=dropout, batch_first=True)
        self.ca = nn.MultiheadAttention(w, heads, dropout=dropout, batch_first=True)
        self.mlp = nn.Sequential(nn.Linear(w, w * mlp_ratio), nn.GELU(approximate="tanh"),
                                 nn.Linear(w * mlp_ratio, w))

    def forward(self, x, ctx, ctx_pad):
        h = self.n1(x)
        x = x + self.sa(h, h, h, need_weights=False)[0]
        h = self.n2(x)
        x = x + self.ca(h, ctx, ctx, key_padding_mask=ctx_pad, need_weights=False)[0]
        return x + self.mlp(self.n3(x))


class ActionExpert(nn.Module):
    def __init__(self, cfg: ExpertConfig):
        super().__init__()
        self.cfg = c = cfg
        w = c.width
        self.ctx_norm = nn.LayerNorm(c.ctx_dim)
        self.ctx_proj = nn.Linear(c.ctx_dim, w)
        self.proprio = nn.Linear(c.proprio_dim, w)
        self.skill = nn.Embedding(c.skill_vocab, w)
        self.phase = nn.Embedding(c.phase_vocab, w)
        self.dec = nn.Embedding(c.dec_vocab, w)
        self.dec_slot = nn.Parameter(torch.zeros(c.n_questions, w))
        self.act_in = nn.Linear(c.act_dim * (2 if c.residual else 1), w)
        self.act_mlp = nn.Sequential(nn.Linear(2 * w, w), nn.SiLU(), nn.Linear(w, w))
        self.pos = nn.Parameter(torch.zeros(c.horizon, w))
        nn.init.normal_(self.pos, std=0.02)
        nn.init.normal_(self.dec_slot, std=0.02)
        self.blocks = nn.ModuleList(Block(w, c.heads, c.mlp_ratio, c.dropout) for _ in range(c.depth))
        self.out_norm = nn.LayerNorm(w)
        self.out = nn.Linear(w, c.act_dim)

    def encode(self, cond: dict) -> dict:
        """Everything that does not depend on (x_t, t): computed once per chunk, reused by every Euler step.
        cond: ctx [B,T,ctx_dim] (already insulated), ctx_mask [B,T] (1 = real token), proprio [B,P], skill [B],
        phase [B], dec [B,Q] (long), script [B,H,8] (residual mode)."""
        ctx = self.ctx_proj(self.ctx_norm(cond["ctx"].float()))
        ctok = torch.cat([self.proprio(cond["proprio"].float())[:, None], self.skill(cond["skill"])[:, None],
                          self.phase(cond["phase"])[:, None], self.dec(cond["dec"]) + self.dec_slot[None]], 1)
        return {"ctx": ctx, "pad": cond["ctx_mask"] == 0, "ctok": ctok, "script": cond.get("script")}

    def velocity(self, enc: dict, x_t: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        a = x_t.float()
        if self.cfg.residual:
            a = torch.cat([a, enc["script"].float()], -1)
        te = time_embedding(t, self.cfg.width)[:, None].expand(-1, a.shape[1], -1)
        tok = self.act_mlp(torch.cat([self.act_in(a), te], -1)) + self.pos[None, :a.shape[1]]
        n = enc["ctok"].shape[1]
        x = torch.cat([enc["ctok"], tok], 1)
        for b in self.blocks:
            x = b(x, enc["ctx"], enc["pad"])
        return self.out(self.out_norm(x[:, n:]))

    def forward(self, cond, x_t, t):
        return self.velocity(self.encode(cond), x_t, t)


def sample_time(n: int, device, generator=None) -> torch.Tensor:
    b = torch.distributions.Beta(torch.tensor(1.5), torch.tensor(1.0))
    if generator is not None:  # Beta has no generator argument: inverse CDF of Beta(1.5, 1) = u^(1/1.5)
        u = torch.rand(n, generator=generator)
        return (0.001 + 0.999 * u.pow(1 / 1.5)).to(device)
    return (0.001 + 0.999 * b.sample((n,))).to(device)


def fm_loss(expert: ActionExpert, cond: dict, a: torch.Tensor, valid: torch.Tensor, t=None, noise=None):
    """Conditional flow-matching loss; a = normalized target chunk [B,H,D], valid [B,H] (0 = padding)."""
    B = a.shape[0]
    t = sample_time(B, a.device) if t is None else t
    noise = torch.randn_like(a) if noise is None else noise
    x_t = t[:, None, None] * noise + (1 - t[:, None, None]) * a
    v = expert(cond, x_t, t)
    m = valid.float()[..., None]
    return (((v - (noise - a)) ** 2) * m).sum() / (m.sum() * a.shape[-1]).clamp_min(1.0)


@torch.no_grad()
def sample_actions(expert: ActionExpert, cond: dict, steps: int = 10, noise=None) -> torch.Tensor:
    """Euler integration t = 1 -> 0; returns the normalized chunk [B,H,D]."""
    enc = expert.encode(cond)
    B = cond["proprio"].shape[0]
    shape = (B, expert.cfg.horizon, expert.cfg.act_dim)
    x = torch.randn(shape, device=cond["proprio"].device) if noise is None else noise.float()
    dt = -1.0 / steps
    for i in range(steps):
        t = torch.full((B,), 1.0 + i * dt, device=x.device)
        x = x + dt * expert.velocity(enc, x, t)
    return x


class AuxGeomHead(nn.Module):
    def __init__(self, cfg: AuxConfig):
        super().__init__()
        self.cfg = c = cfg
        self.norm = nn.LayerNorm(c.ctx_dim)
        self.proj = nn.Linear(c.ctx_dim, c.width)
        self.q = nn.Parameter(torch.randn(c.queries, c.width) * 0.02)
        self.att = nn.MultiheadAttention(c.width, c.heads, batch_first=True)
        self.mlp = nn.Sequential(nn.Linear(c.queries * c.width, c.width), nn.GELU(approximate="tanh"),
                                 nn.Linear(c.width, c.n_reg + c.n_cls))

    def forward(self, ctx, ctx_mask):
        h = self.proj(self.norm(ctx.float()))
        q = self.q[None].expand(h.shape[0], -1, -1)
        p = self.att(q, h, h, key_padding_mask=ctx_mask == 0, need_weights=False)[0]
        o = self.mlp(p.flatten(1))
        return o[:, :self.cfg.n_reg], o[:, self.cfg.n_reg:]


def aux_loss(head: AuxGeomHead, ctx, ctx_mask, reg, reg_m, cls, cls_m):
    """Smooth-L1 on the scaled regression targets + BCE on predicates, both masked (null labels ignored)."""
    pr, pc = head(ctx, ctx_mask)
    lr = (F.smooth_l1_loss(pr, reg, reduction="none") * reg_m).sum() / reg_m.sum().clamp_min(1.0)
    lc = (F.binary_cross_entropy_with_logits(pc, cls, reduction="none") * cls_m).sum() / cls_m.sum().clamp_min(1.0)
    return lr + lc, {"aux_reg": float(lr.detach()), "aux_cls": float(lc.detach())}


def n_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())
