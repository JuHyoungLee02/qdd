"""JCR model (docs/stage3/jcr_design.md §3 + §0-2): Qwen3-VL-4B backbone (LoRA r32, vision frozen) over the head + active
wrist images and one FIXED short sentence (no state / phase text, §1-1 finding 6), the stage-B flow-matching action
expert (stageb_expert.ActionExpert: cross-attention to the backbone hidden states, KI stop-gradient) conditioned on the
JCR cond vector (features.cond_vec, one token), and a JCR head (attention pooling of the backbone states + the cond
vector, NOT insulated -> LoRA learns contact / anomaly from the images) with the event (keep / close@r / open@r / stop),
contact and anomaly outputs.
Losses: L = L_fm(delta chunk) + LAM_EV * CE(event, events up-weighted) + LAM_C * BCE(contact) + LAM_A * BCE(anomaly,
pos_weight). Every real sample brings K forced-joystick branches (features.branch) that share its backbone pass."""
from __future__ import annotations

import os

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from ..train.stageb_expert import ActionExpert, ExpertConfig, fm_loss, insulate, sample_actions
from . import features as FT
from . import truth as T

TEXT = "Image 1: head camera. Image 2: right wrist camera."
LAM_EV, LAM_C, LAM_A = 0.5, 0.5, 0.25
EV_W = 5.0  # event classes other than keep
ANOM_POS_W = 5.0


class JCRHead(nn.Module):
    def __init__(self, ctx_dim, cond_dim=FT.COND_DIM, width=512, queries=4, heads=8):
        super().__init__()
        self.norm = nn.LayerNorm(ctx_dim)
        self.proj = nn.Linear(ctx_dim, width)
        self.q = nn.Parameter(torch.randn(queries, width) * 0.02)
        self.att = nn.MultiheadAttention(width, heads, batch_first=True)
        self.cond = nn.Sequential(nn.Linear(cond_dim, width), nn.GELU(approximate="tanh"))
        self.mlp = nn.Sequential(nn.Linear((queries + 1) * width, width), nn.GELU(approximate="tanh"),
                                 nn.Linear(width, FT.N_EVENT + 1 + len(FT.ANOM) + 1))

    def forward(self, ctx, ctx_mask, cond):
        h = self.proj(self.norm(ctx.float()))
        q = self.q[None].expand(h.shape[0], -1, -1)
        p = self.att(q, h, h, key_padding_mask=ctx_mask == 0, need_weights=False)[0]
        o = self.mlp(torch.cat([p.flatten(1), self.cond(cond.float())], 1))
        n = FT.N_EVENT
        return o[:, :n], o[:, n], o[:, n + 1:]


class JCR(nn.Module):
    def __init__(self, backbone, ctx_dim, norm: FT.Norm, ki="stop", layer=-1, width=768, depth=8, heads=12):
        super().__init__()
        self.backbone, self.norm, self.ki, self.layer = backbone, norm, ki, layer
        self.ecfg = ExpertConfig(ctx_dim=ctx_dim, act_dim=3, horizon=T.H, proprio_dim=FT.COND_DIM, n_questions=1,
                                 dec_vocab=2, skill_vocab=2, phase_vocab=2, width=width, depth=depth, heads=heads)
        self.expert = ActionExpert(self.ecfg)
        self.head = JCRHead(ctx_dim)

    # ------------------------------------------------------------------ backbone
    def contexts(self, enc, image_sets, device, grad=True):
        hs = []
        for ims in image_sets:
            x = enc.inputs(TEXT, ims, device)
            with torch.set_grad_enabled(grad and torch.is_grad_enabled()):
                out = self.backbone(**x, output_hidden_states=True, logits_to_keep=1)
            hs.append(out.hidden_states[self.layer][0])
        L = max(h.shape[0] for h in hs)
        ctx = hs[0].new_zeros(len(hs), L, hs[0].shape[1])
        mask = torch.zeros(len(hs), L, dtype=torch.long, device=device)
        for i, h in enumerate(hs):
            ctx[i, :h.shape[0]] = h
            mask[i, :h.shape[0]] = 1
        return ctx, mask

    def expert_cond(self, ctx, mask, cond):
        B = cond.shape[0]
        z = torch.zeros(B, dtype=torch.long, device=cond.device)
        return {"ctx": insulate(ctx, self.ki), "ctx_mask": mask, "proprio": cond, "skill": z, "phase": z,
                "dec": z[:, None]}

    # ------------------------------------------------------------------ training
    def losses(self, enc, rows, device):
        """rows: list of (image set, [sample, branch_1, ... branch_K]) -- every group shares one backbone pass."""
        ctx, mask = self.contexts(enc, [r[0] for r in rows], device)
        rep = torch.tensor([len(r[1]) for r in rows], device=device)
        ss = [s for r in rows for s in r[1]]
        ctx, mask = ctx.repeat_interleave(rep, 0), mask.repeat_interleave(rep, 0)
        cond = torch.tensor(np.stack([FT.cond_vec(s) for s in ss]), device=device)
        a = torch.tensor(np.stack([self.norm.z(FT.delta(s)) for s in ss]), device=device)
        valid = torch.ones(a.shape[:2], device=device)
        l_fm = fm_loss(self.expert, self.expert_cond(ctx, mask, cond), a, valid)
        ev_l, c_l, an_l = self.head(ctx, mask, cond)
        ev = torch.tensor([FT.event_class(s) for s in ss], device=device)
        w = torch.full((FT.N_EVENT,), EV_W, device=device)
        w[FT.EV_KEEP] = 1.0
        l_ev = F.cross_entropy(ev_l, ev, weight=w)
        ct = torch.tensor([float(bool(s.get("contact"))) for s in ss], device=device)
        l_c = F.binary_cross_entropy_with_logits(c_l, ct)
        at = torch.tensor(np.stack([FT.anomaly_vec(s) for s in ss]), device=device)
        l_a = F.binary_cross_entropy_with_logits(an_l, at, pos_weight=torch.full_like(at[0], ANOM_POS_W))
        loss = l_fm + LAM_EV * l_ev + LAM_C * l_c + LAM_A * l_a
        return loss, {"fm": float(l_fm), "ev": float(l_ev), "contact": float(l_c), "anom": float(l_a)}

    # ------------------------------------------------------------------ inference
    @torch.no_grad()
    def predict(self, enc, image_set, samples, device, steps=10, seed=0):
        """-> list of dicts (one per sample sharing the image set): delta [H,3] m, event probs, contact p, anomaly p."""
        ctx, mask = self.contexts(enc, [image_set], device, grad=False)
        B = len(samples)
        ctx, mask = ctx.expand(B, -1, -1), mask.expand(B, -1)
        cond = torch.tensor(np.stack([FT.cond_vec(s) for s in samples]), device=device)
        g = torch.Generator(device="cpu").manual_seed(seed)
        noise = torch.randn((B, T.H, 3), generator=g).to(device)
        z = sample_actions(self.expert, self.expert_cond(ctx, mask, cond), steps=steps, noise=noise)
        ev_l, c_l, an_l = self.head(ctx, mask, cond)
        out = []
        for i in range(B):
            out.append({"delta": self.norm.unz(z[i].float().cpu().numpy()).tolist(),
                        "event_p": torch.softmax(ev_l[i].float(), -1).cpu().numpy().tolist(),
                        "contact_p": float(torch.sigmoid(c_l[i].float())),
                        "anomaly_p": torch.sigmoid(an_l[i].float()).cpu().numpy().tolist()})
        return out

    # ------------------------------------------------------------------ save / load
    def heads_state(self):
        return {"expert": self.expert.state_dict(), "head": self.head.state_dict()}

    def save(self, d, extra=None):
        import json
        os.makedirs(d, exist_ok=True)
        self.backbone.save_pretrained(os.path.join(d, "adapter"))
        torch.save(self.heads_state(), os.path.join(d, "heads.pt"))
        with open(os.path.join(d, "jcr.json"), "w") as f:
            json.dump({"expert": self.ecfg.to_json(), "norm": self.norm.to_json(), "ki": self.ki,
                       "layer": self.layer, "text": TEXT, **(extra or {})}, f)


def load(d, model_dir, device, dtype=torch.bfloat16):
    import json

    from ..train.stageb_model import HFEncoder
    from ..train.stageb_train import load_backbone
    cfg = json.load(open(os.path.join(d, "jcr.json")))
    bb, proc, hid = load_backbone("qwen", model_dir, device, adapter=os.path.join(d, "adapter"), dtype=dtype)
    e = cfg["expert"]
    m = JCR(bb, hid, FT.Norm(cfg["norm"]["std"]), cfg["ki"], cfg["layer"], e["width"], e["depth"], e["heads"])
    st = torch.load(os.path.join(d, "heads.pt"), map_location="cpu")
    m.expert.load_state_dict(st["expert"])
    m.head.load_state_dict(st["head"])
    m.expert.to(device), m.head.to(device)
    m.eval()
    return m, HFEncoder(proc, "")
