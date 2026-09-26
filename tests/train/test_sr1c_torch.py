"""E-SR1c (prereg_sr1c): authority-gated joystick adaLN expert, its checkpoint marker, the authority condition, and the
branch-mixing flow-matching loss (torch needed: pod / torch environments)."""
import json
import os

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from harvest.train import sr1c as S  # noqa: E402
from harvest.train import sr1c_film as F  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train.stageb_expert import (ActionExpert, AuxConfig, AuxGeomHead, ExpertConfig, fm_loss,  # noqa: E402
                                         sample_actions)

CFG = dict(ctx_dim=16, horizon=4, proprio_dim=5, n_questions=5, dec_vocab=20, width=32, depth=2, heads=4)


def _pair(seed=0, rank=8):
    torch.manual_seed(seed)
    base = ActionExpert(ExpertConfig(**CFG)).eval()
    ada = F.AdaLNExpert(ExpertConfig(**CFG), rank=rank).eval()
    missing, unexpected = ada.load_state_dict(base.state_dict(), strict=False)
    assert not unexpected and all(k.startswith(("joy_mlp", "mod_down", "mod_up")) for k in missing)
    return base, ada


def _cond(B=3, auth=1.0, seed=0):
    g = torch.Generator().manual_seed(seed)
    return {"ctx": torch.randn(B, 6, 16, generator=g), "ctx_mask": torch.ones(B, 6, dtype=torch.long),
            "proprio": torch.randn(B, 5, generator=g), "skill": torch.tensor([1] * B), "phase": torch.tensor([2] * B),
            "dec": torch.randint(1, 20, (B, 5), generator=g), "auth": torch.full((B,), float(auth))}


def test_zero_init_and_zero_authority_equal_the_baseline_expert_exactly():
    base, ada = _pair()
    c = _cond()
    noise = torch.randn(3, 4, 8, generator=torch.Generator().manual_seed(1))
    assert torch.equal(sample_actions(ada, c, 5, noise), sample_actions(base, {k: v for k, v in c.items()
                                                                                  if k != "auth"}, 5, noise))
    with torch.no_grad():
        for up in ada.mod_up:
            up.weight.normal_(0, 0.5)
    c0 = _cond(auth=0.0)
    assert torch.equal(sample_actions(ada, c0, 5, noise), sample_actions(base, c0, 5, noise))
    z1 = sample_actions(ada, _cond(auth=1.0), 5, noise)
    assert not torch.allclose(z1, sample_actions(base, c0, 5, noise))
    zh = sample_actions(ada, _cond(auth=0.5), 5, noise)
    assert not torch.allclose(zh, z1)


def test_only_the_joystick_slots_modulate():
    base, ada = _pair()
    with torch.no_grad():
        for up in ada.mod_up:
            up.weight.normal_(0, 0.5)
    c = _cond()
    enc1 = ada.encode(c)
    c2 = {**c, "dec": c["dec"].clone()}
    c2["dec"][:, 3:] = 1  # target / phase slots change: modulation unchanged
    enc2 = ada.encode(c2)
    for m1, m2 in zip(enc1["mods"], enc2["mods"]):
        assert torch.equal(m1, m2)
    c3 = {**c, "dec": c["dec"].clone()}
    c3["dec"][:, 0] = (c3["dec"][:, 0] % 19) + 1
    assert not torch.equal(ada.encode(c3)["mods"][0], enc1["mods"][0])


def test_missing_authority_is_refused():
    _, ada = _pair()
    c = _cond()
    del c["auth"]
    with pytest.raises(KeyError):
        ada.encode(c)


def test_extra_parameters_at_full_size():
    cfg = ExpertConfig()  # width 768, depth 8
    n0 = sum(p.numel() for p in ActionExpert(cfg).parameters())
    n1 = sum(p.numel() for p in F.AdaLNExpert(cfg, rank=64).parameters())
    extra = n1 - n0
    assert 4.0e6 < extra < 5.0e6  # shared 768x768 + 8 x (768 -> 64 -> 9 x 768), research doc D3 design value


def test_fm_loss_gradient_reaches_the_modulation_only_with_authority():
    _, ada = _pair()
    ada.train()
    a = torch.randn(3, 4, 8)
    for auth, expect in ((0.0, False), (1.0, True)):
        ada.zero_grad(set_to_none=True)
        fm_loss(ada, _cond(auth=auth), a, torch.ones(3, 4)).backward()
        g = ada.mod_up[0].weight.grad
        assert (g is not None and float(g.abs().sum()) > 0) == expect


class _Aux(torch.nn.Module):
    """Aux head stub: predicts g2tgt_dist from ctx[:, 0, 0] (m)."""

    def forward(self, ctx, mask):
        B = ctx.shape[0]
        reg = torch.zeros(B, len(D.AUX_REG))
        reg[:, D.AUX_REG.index("g2tgt_dist")] = ctx[:, 0, 0] / D.AUX_REG_SCALE
        return reg, torch.full((B, len(D.AUX_CLS)), -5.0)


class _M:
    def __init__(self):
        self.aux = _Aux()
        self.training = True

    def cond(self, samples, ctx, mask, device):
        return {"ctx": ctx, "dec": torch.ones(len(samples), 5, dtype=torch.long)}


def test_authority_condition_from_the_aux_head_and_the_phase():
    m = _M()
    F.install_authority(m)
    ctx = torch.zeros(4, 3, 2)
    ctx[:, 0, 0] = torch.tensor([0.20, 0.075, 0.03, 0.20])
    ss = [{"phase_id": "approach"}] * 3 + [{"phase_id": "descend"}]
    c = m.cond(ss, ctx, torch.ones(4, 3), "cpu")
    assert torch.allclose(c["auth"], torch.tensor([1.0, 0.5, 0.0, 0.0]))
    assert m.last_auth == pytest.approx([1.0, 0.5, 0.0, 0.0])


def test_head_config_marker_and_baseline_loader_refuses(tmp_path):
    from harvest.train.stageb_model import StageB, load_heads
    _, ada = _pair()
    norm = D.ActionNorm()
    vocabs = {"dec": D.Vocab(["dir_xy=plus_x"]), "skill": D.Vocab(["pick"]), "phase": D.Vocab(["approach"])}
    m = StageB(torch.nn.Identity(), ada, AuxGeomHead(AuxConfig(ctx_dim=16, width=16, heads=2, n_reg=11, n_cls=7)),
               norm, vocabs)
    F.mark_heads(m, rank=8)
    m.save_heads(str(tmp_path))
    cfg = json.load(open(os.path.join(tmp_path, "stageb.json")))
    assert cfg["expert_cond"] == F.DEC_COND and cfg["adaln_rank"] == 8
    with pytest.raises(RuntimeError):
        load_heads(str(tmp_path), torch.nn.Identity())
    m2 = F.load_heads_sr1c(str(tmp_path), torch.nn.Identity())
    assert isinstance(m2.expert, F.AdaLNExpert)
    for (k1, v1), (k2, v2) in zip(ada.state_dict().items(), m2.expert.state_dict().items()):
        assert k1 == k2 and torch.equal(v1, v2)
    assert hasattr(m2, "last_auth")  # the authority condition is installed on load


def test_load_heads_sr1c_passes_a_plain_checkpoint_through(tmp_path):
    from harvest.train.stageb_model import StageB
    torch.manual_seed(0)
    e = ActionExpert(ExpertConfig(**CFG))
    vocabs = {"dec": D.Vocab(["dir_xy=plus_x"]), "skill": D.Vocab(["pick"]), "phase": D.Vocab(["approach"])}
    StageB(torch.nn.Identity(), e, None, D.ActionNorm(), vocabs).save_heads(str(tmp_path))
    m = F.load_heads_sr1c(str(tmp_path), torch.nn.Identity())
    assert type(m.expert) is ActionExpert and not hasattr(m, "last_auth")


class _LossModel:
    """Stand-in for StageB.losses: records lam['act'] at call time and returns total = lam_act * fm (fm = 2.0)."""

    def __init__(self):
        self.training = True
        self.lam = {"act": 1.0}
        self.seen = []
        self.expert = None

    def losses(self, samples, enc, device, vqa=None, fm_t=None, fm_noise=None):
        self.seen.append((len(samples), self.lam["act"]))
        return torch.tensor(2.0) * self.lam["act"], {"fm": 2.0, "total": 2.0 * self.lam["act"]}


def test_branch_mixing_weights_and_counts(monkeypatch):
    m = _LossModel()
    branches = [{"key": f"b{i}"} for i in range(10)]
    calls = []

    def fm_branch(model, bs, enc, device):
        calls.append([b["key"] for b in bs])
        return torch.tensor(4.0)
    S.with_branches(m, branches, frac=0.5, seed=0, fm_branch=fm_branch)
    total, logs = m.losses([{}] * 8, None, "cpu")
    assert m.seen == [(8, 0.5)] and m.lam["act"] == 1.0  # real part at weight 1 - frac, lam restored
    assert len(calls[0]) == 8  # 50 %: as many branch samples as real samples
    assert float(total) == pytest.approx(0.5 * 2.0 + 0.5 * 4.0)
    assert logs["fm_branch"] == pytest.approx(4.0) and logs["n_branch"] == 8
    m.training = False  # evaluation: the plain loss
    total, logs = m.losses([{}] * 8, None, "cpu")
    assert m.seen[-1] == (8, 1.0) and "fm_branch" not in logs
    # the draw is seeded and independent of the torch RNG
    m2 = _LossModel()
    calls2 = []
    S.with_branches(m2, branches, frac=0.5, seed=0, fm_branch=lambda mm, bs, e, d: calls2.append(
        [b["key"] for b in bs]) or torch.tensor(4.0))
    torch.manual_seed(123)
    m2.losses([{}] * 8, None, "cpu")
    assert calls2[0] == calls[0]


def test_frac_three_quarters_gives_three_branch_samples_per_real():
    m = _LossModel()
    calls = []
    S.with_branches(m, [{"key": "b"}] * 5, frac=0.75, seed=0,
                    fm_branch=lambda mm, bs, e, d: calls.append(len(bs)) or torch.tensor(0.0))
    m.losses([{}] * 4, None, "cpu")
    assert calls == [12] and m.seen == [(4, 0.25)]
