"""E-SR1c arm C2: authority-gated joystick adaLN-Zero modulation of the action expert (docs/stage3/prereg_sr1c.md;
research doc decision_adherence_0p8_2026-09-26.md §2 D3 `adaln@v1`). OPT-IN: the baseline expert / loader are not
modified (stageb_expert.py, stageb_model.py untouched; a C2 checkpoint is refused by stageb_model.load_heads).

  e_joy = sum over the joystick slots (dir_xy, dir_z, mag_coarse) of (dec embedding + slot embedding)  [the expert's
          own tables; target / phase stay plain condition tokens]
  h     = SiLU(Linear(w, w)(e_joy))                                   shared
  m_b   = a * Up_b(Down_b(h)),  Down: w -> rank, Up: rank -> 9 w (zero init)   per block b
        = (gamma1, beta1, alpha1, gamma2, beta2, alpha2, gamma3, beta3, alpha3)
  block: x += (1 + alpha1) * SA(LN1(x) (1 + gamma1) + beta1); the same for cross-attention (2) and the MLP (3)
a = the authority (cond["auth"], sr1c_authority.estimated from the aux head + the expert's phase input -- training,
evaluation and runtime use the same estimate). a = 0 or zero-initialized Up -> numerically the baseline block.
"""
from __future__ import annotations

import json
import os

import torch
from torch import nn

from .stageb_expert import ActionExpert, ExpertConfig

DEC_COND = "adaln@v1"
JOY_SLOTS = (0, 1, 2)  # dir_xy, dir_z, mag_coarse in stageb_data.QUESTIONS
RANK = 64


class AdaLNExpert(ActionExpert):
    def __init__(self, cfg: ExpertConfig, rank: int = RANK):
        super().__init__(cfg)
        w = cfg.width
        self.rank = rank
        self.joy_mlp = nn.Sequential(nn.Linear(w, w), nn.SiLU())
        self.mod_down = nn.ModuleList(nn.Linear(w, rank) for _ in range(cfg.depth))
        self.mod_up = nn.ModuleList(nn.Linear(rank, 9 * w) for _ in range(cfg.depth))
        for up in self.mod_up:
            nn.init.zeros_(up.weight)
            nn.init.zeros_(up.bias)

    def encode(self, cond: dict) -> dict:
        enc = super().encode(cond)
        auth = cond["auth"]  # KeyError without an authority: a C2 expert never runs ungated
        ids = cond["dec"][:, list(JOY_SLOTS)]
        e = (self.dec(ids) + self.dec_slot[list(JOY_SLOTS)][None]).sum(1)
        h = self.joy_mlp(e)
        a = auth.float().to(h.device)[:, None]
        B, w = h.shape
        enc["mods"] = [(up(dn(h)) * a).view(B, 9, w) for dn, up in zip(self.mod_down, self.mod_up)]
        return enc

    def velocity(self, enc: dict, x_t: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        from .stageb_expert import time_embedding
        a = x_t.float()
        if self.cfg.residual:
            a = torch.cat([a, enc["script"].float()], -1)
        te = time_embedding(t, self.cfg.width)[:, None].expand(-1, a.shape[1], -1)
        tok = self.act_mlp(torch.cat([self.act_in(a), te], -1)) + self.pos[None, :a.shape[1]]
        n = enc["ctok"].shape[1]
        x = torch.cat([enc["ctok"], tok], 1)
        for b, m in zip(self.blocks, enc["mods"]):
            g1, b1, a1, g2, b2, a2, g3, b3, a3 = (v[:, None] for v in m.unbind(1))
            h = b.n1(x) * (1 + g1) + b1
            x = x + (1 + a1) * b.sa(h, h, h, need_weights=False)[0]
            h = b.n2(x) * (1 + g2) + b2
            x = x + (1 + a2) * b.ca(h, enc["ctx"], enc["ctx"], key_padding_mask=enc["pad"], need_weights=False)[0]
            x = x + (1 + a3) * b.mlp(b.n3(x) * (1 + g3) + b3)
        return self.out(self.out_norm(x[:, n:]))


def swap_expert(model, rank: int = RANK):
    """Replace model.expert by an AdaLNExpert holding the same base weights (modulation zero-initialized)."""
    base = model.expert
    ada = AdaLNExpert(base.cfg, rank=rank)
    missing, unexpected = ada.load_state_dict(base.state_dict(), strict=False)
    if unexpected or not all(k.startswith(("joy_mlp", "mod_down", "mod_up")) for k in missing):
        raise RuntimeError(f"adaLN swap: missing {missing}, unexpected {unexpected}")
    model.expert = ada.to(next(base.parameters()).device)
    return model


def install_authority(model):
    """cond(...) also returns 'auth' [B] = sr1c_authority.estimated(aux head outputs on ctx, sample phase_id);
    model.last_auth = the last batch's values (logging / evaluation)."""
    from . import sr1c_authority as A
    base = model.cond

    def cond(samples, ctx, mask, device):
        c = base(samples, ctx, mask, device)
        with torch.no_grad():
            reg, cls = model.aux(ctx.detach(), mask)
        reg, cls = reg.float().cpu().numpy(), cls.float().cpu().numpy()
        a = [A.estimated(reg[i], cls[i], s["phase_id"]) for i, s in enumerate(samples)]
        model.last_auth = a
        c["auth"] = torch.tensor(a, dtype=torch.float32, device=c["dec"].device)
        return c
    model.cond = cond
    model.last_auth = None
    return model


def mark_heads(model, rank: int = RANK):
    base = model.head_config

    def head_config():
        return {**base(), "expert_cond": DEC_COND, "adaln_rank": rank}
    model.head_config = head_config
    return model


def load_heads_sr1c(out_dir, backbone, device="cpu"):
    """stageb_model.load_heads for both kinds: a plain checkpoint -> the baseline StageB unchanged; an adaln@v1
    checkpoint -> AdaLNExpert + the authority condition installed."""
    from . import stageb_data as D
    from .stageb_model import StageB, build_heads, load_heads
    cfg = json.load(open(os.path.join(out_dir, "stageb.json")))
    if cfg.get("expert_cond") is None:
        return load_heads(out_dir, backbone, device)
    if cfg["expert_cond"] != DEC_COND:
        raise ValueError(f"expert_cond {cfg['expert_cond']!r}")
    _, a, v = build_heads(cfg)
    e = AdaLNExpert(ExpertConfig(**cfg["expert"]), rank=int(cfg["adaln_rank"]))
    sd = torch.load(os.path.join(out_dir, "heads.pt"), map_location="cpu", weights_only=True)
    e.load_state_dict({k[7:]: x for k, x in sd.items() if k.startswith("expert.")})
    if a is not None:
        a.load_state_dict({k[4:]: x for k, x in sd.items() if k.startswith("aux.")})
    if v is not None:
        v.load_state_dict({k[7:]: x for k, x in sd.items() if k.startswith("verify.")})
    vocabs = {k: D.Vocab.from_json(x) for k, x in cfg["vocabs"].items()}
    m = StageB(backbone, e, a, D.ActionNorm.from_json(cfg["norm"]), vocabs, cfg["ki"], cfg["layer"], cfg["lam"],
               verify=v).to(device)
    mark_heads(m, int(cfg["adaln_rank"]))
    return install_authority(m)
