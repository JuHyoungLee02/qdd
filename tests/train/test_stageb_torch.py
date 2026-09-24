"""Stage-B model on a mocked causal backbone (CPU torch): KI gradient insulation, flow matching, sampling,
save/load, joint loop. The real Qwen3-VL architecture is covered by test_stageb_qwen.py (pod)."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from harvest.clients.jevl import option_trie  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_expert as E  # noqa: E402
from harvest.train import stageb_model as M  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402

V, HID = 97, 16
EK = {"width": 32, "depth": 2, "heads": 4}
AK = {"width": 32, "heads": 4, "queries": 2}


class MockBackbone(torch.nn.Module):
    """Causal stand-in: hidden_t = tanh(cumsum(emb @ W)); the 'image' adds a learned bias per image count."""

    def __init__(self, seed=0):
        super().__init__()
        g = torch.Generator().manual_seed(seed)
        self.emb = torch.nn.Parameter(torch.randn(V, HID, generator=g) * 0.5)
        self.w = torch.nn.Parameter(torch.randn(HID, HID, generator=g) * 0.3)
        self.img = torch.nn.Parameter(torch.randn(HID, generator=g) * 0.1)
        self.head = torch.nn.Parameter(torch.randn(HID, V, generator=g))

    def forward(self, input_ids, attention_mask=None, logits_to_keep=0, output_hidden_states=False, n_img=None, **kw):
        h0 = self.emb[input_ids]
        if n_img is not None:
            h0 = h0 + n_img[:, None, None].float() * self.img
        h = torch.tanh(torch.cumsum(h0 @ self.w, 1) / 4)
        logits = h @ self.head
        if logits_to_keep:
            logits = logits[:, -logits_to_keep:]
        return SimpleNamespace(logits=logits, hidden_states=(h0, h))


class MockEncoder:
    end, pad = V - 1, 0

    def __init__(self):
        self._t = {}

    def ids(self, text):
        return [1 + ord(c) % (V - 3) for c in text]

    def trie(self, names):
        if tuple(names) not in self._t:
            tok = {n: self.ids(n) for n in names}
            self._t[tuple(names)] = (tok, option_trie(tok, self.end))
        return self._t[tuple(names)]

    def inputs(self, text, images, device):
        ids = self.ids(text[-60:]) + [V - 2]
        return {"input_ids": torch.tensor([ids], device=device),
                "attention_mask": torch.ones(1, len(ids), dtype=torch.long, device=device),
                "n_img": torch.tensor([len(images or [])], device=device)}


def _model(ki="stop", mode="absolute", n=10, lam=None, seed=0):
    torch.manual_seed(seed)
    ss = D.synthetic_rows(n, seed=seed)
    return M.new_model(MockBackbone(seed), ss, HID, mode=mode, ki=ki, expert_kw=EK, aux_kw=AK, lam=lam), ss


def _grads(loss, params):
    gs = torch.autograd.grad(loss, params, allow_unused=True, retain_graph=True)
    return [torch.zeros_like(p) if g is None else g for g, p in zip(gs, params)]


def test_ki_stop_gives_exactly_zero_backbone_gradient_from_the_expert_loss():
    enc, dev = MockEncoder(), torch.device("cpu")
    res = {}
    for ki in ("stop", "none", "scale:0.5"):
        m, ss = _model(ki)
        bb = list(m.backbone.parameters())
        ctx, mask = m.contexts(ss[:3], enc, dev, grad=True)
        a, valid, _ = m.targets(ss[:3], dev)
        g = torch.Generator().manual_seed(1)
        t, noise = E.sample_time(3, dev, g), torch.randn(a.shape, generator=g)
        l_fm = E.fm_loss(m.expert, m.cond(ss[:3], ctx, mask, dev), a, valid, t=t, noise=noise)
        res[ki] = _grads(l_fm, bb)
        assert sum(float(x.abs().sum()) for x in _grads(l_fm, list(m.expert.parameters()))) > 0
    assert all(float(g.abs().max()) == 0.0 for g in res["stop"])  # exactly zero, not just small
    assert sum(float(g.abs().sum()) for g in res["none"]) > 1e-6  # the test can see a leak
    for g5, g1 in zip(res["scale:0.5"], res["none"]):
        assert torch.allclose(g5, 0.5 * g1, atol=1e-7)


def test_aux_and_decision_losses_reach_the_backbone_and_expert_adds_nothing_under_ki():
    enc, dev = MockEncoder(), torch.device("cpu")
    m, ss = _model("stop", lam={"dec": 1.0, "act": 1.0, "aux": 0.5})
    bb = list(m.backbone.parameters())
    ctx, mask = m.contexts(ss[:3], enc, dev, grad=True)
    r, rm, c, cm = (torch.tensor(np.stack(x)) for x in zip(*[D.aux_vecs(s["aux"]) for s in ss[:3]]))
    l_aux, _ = E.aux_loss(m.aux, ctx, mask, r, rm, c, cm)
    assert sum(float(g.abs().sum()) for g in _grads(l_aux, bb)) > 0
    l_dec = m.decision_loss(ss[:3], enc, dev)
    assert sum(float(g.abs().sum()) for g in _grads(l_dec, bb)) > 0
    # full joint loss: backbone gradient == gradient of (dec + 0.5 aux) alone
    g = torch.Generator().manual_seed(2)
    a, _, _ = m.targets(ss[:3], dev)
    t, noise = E.sample_time(3, dev, g), torch.randn(a.shape, generator=g)
    total, logs = m.losses(ss[:3], enc, dev, fm_t=t, fm_noise=noise)
    g_total = _grads(total, bb)
    ctx, mask = m.contexts(ss[:3], enc, dev, grad=True)
    l_aux2, _ = E.aux_loss(m.aux, ctx, mask, r, rm, c, cm)
    g_ref = _grads(m.decision_loss(ss[:3], enc, dev) + 0.5 * l_aux2, bb)
    for x, y in zip(g_total, g_ref):
        assert torch.allclose(x, y, atol=1e-6)
    assert {"fm", "aux", "dec", "total"} <= set(logs)


def test_insulate_keeps_forward_values():
    x = torch.randn(2, 3, requires_grad=True)
    for ki in ("stop", "none", "scale:0.25"):
        assert torch.equal(E.insulate(x, ki), x)
    with pytest.raises(ValueError):
        E.insulate(x, "half")


def test_euler_sampler_integrates_the_exact_linear_path_to_the_data():
    a_true = torch.randn(2, 15, 8)

    class Exact(torch.nn.Module):  # the true conditional velocity of x_t = t n + (1 - t) a is (x_t - a) / t
        cfg = SimpleNamespace(horizon=15, act_dim=8)

        def encode(self, cond):
            return {}

        def velocity(self, enc, x, t):
            return (x - a_true) / t[:, None, None]
    out = E.sample_actions(Exact(), {"proprio": torch.zeros(2, 23)}, steps=10, noise=torch.randn(2, 15, 8))
    assert torch.allclose(out, a_true, atol=1e-5)


def test_time_sampling_range_and_fm_target_sign():
    t = E.sample_time(1000, "cpu", torch.Generator().manual_seed(0))
    assert float(t.min()) >= 0.001 and float(t.max()) <= 1.0 and 0.55 < float(t.mean()) < 0.65  # Beta(1.5,1) 0.6


def test_flow_matching_learns_and_sampling_approaches_targets():
    torch.manual_seed(0)
    cfg = E.ExpertConfig(ctx_dim=HID, horizon=15, proprio_dim=23, dec_vocab=8, skill_vocab=4, phase_vocab=4,
                         width=64, depth=2, heads=4)
    ex = E.ActionExpert(cfg)
    B = 8
    prop = torch.randn(B, 23)
    a = torch.tanh(prop[:, :8])[:, None].expand(B, 15, 8).contiguous() * torch.linspace(0.2, 1, 15)[None, :, None]
    cond = {"ctx": torch.randn(B, 5, HID), "ctx_mask": torch.ones(B, 5, dtype=torch.long), "proprio": prop,
            "skill": torch.ones(B, dtype=torch.long), "phase": torch.ones(B, dtype=torch.long),
            "dec": torch.zeros(B, 5, dtype=torch.long)}
    valid = torch.ones(B, 15)
    opt = torch.optim.Adam(ex.parameters(), 2e-3)
    g = torch.Generator().manual_seed(0)
    fixed = (E.sample_time(B, "cpu", g), torch.randn(B, 15, 8, generator=g))
    l0 = float(E.fm_loss(ex, cond, a, valid, *fixed))
    for _ in range(300):
        loss = E.fm_loss(ex, cond, a, valid)
        opt.zero_grad()
        loss.backward()
        opt.step()
    l1 = float(E.fm_loss(ex, cond, a, valid, *fixed))
    assert l1 < 0.5 * l0
    z = E.sample_actions(ex, cond, 10, torch.randn(B, 15, 8, generator=g))
    base = float(((torch.randn(B, 15, 8, generator=g) - a) ** 2).mean())
    assert float(((z - a) ** 2).mean()) < 0.25 * base


def test_padding_steps_do_not_contribute_to_the_fm_loss():
    cfg = E.ExpertConfig(ctx_dim=HID, horizon=15, proprio_dim=23, dec_vocab=8, skill_vocab=4, phase_vocab=4, **EK)
    ex = E.ActionExpert(cfg)
    cond = {"ctx": torch.randn(1, 4, HID), "ctx_mask": torch.ones(1, 4, dtype=torch.long), "proprio": torch.randn(1, 23),
            "skill": torch.ones(1, dtype=torch.long), "phase": torch.ones(1, dtype=torch.long),
            "dec": torch.zeros(1, 5, dtype=torch.long)}
    a = torch.randn(1, 15, 8)
    valid = torch.tensor([[1.0] * 11 + [0.0] * 4])
    t, n = torch.tensor([0.5]), torch.randn(1, 15, 8)
    x_t = t * n + (1 - t) * a
    v = ex(cond, x_t, t)
    l_ref = (((v - (n - a)) ** 2)[:, :11]).mean()
    assert torch.allclose(E.fm_loss(ex, cond, a, valid, t, n), l_ref, atol=1e-6)


def test_save_load_heads_round_trip_and_predict_equal(tmp_path):
    enc, dev = MockEncoder(), torch.device("cpu")
    for mode in ("absolute", "residual"):
        m, ss = _model(mode=mode)
        m.eval()
        noise = torch.randn(1, 15, 8)
        p1 = m.predict(ss[0], enc, dev, noise=noise)
        m.save_heads(str(tmp_path / mode))
        m2 = M.load_heads(str(tmp_path / mode), m.backbone).eval()
        assert np.array_equal(p1, m2.predict(ss[0], enc, dev, noise=noise))
        assert m2.norm.to_json() == m.norm.to_json() and m2.ki == "stop"
        assert m2.vocabs["dec"].ids == m.vocabs["dec"].ids


def test_residual_mode_output_stays_within_xi_of_the_scripted_chunk():
    enc, dev = MockEncoder(), torch.device("cpu")
    m, ss = _model(mode="residual")
    assert m.expert.cfg.residual
    with torch.no_grad():  # push the output layer to saturate
        m.expert.out.bias.fill_(50.0)
    act = m.predict(ss[0], enc, dev)
    d = np.abs(act - np.asarray(ss[0]["action_script"], np.float32))
    assert (d <= m.norm.xi[None] + 1e-6).all() and np.allclose(d, m.norm.xi[None], atol=1e-6)


def test_vqa_retention_loss_is_answer_token_nll():
    enc, dev = MockEncoder(), torch.device("cpu")
    m, _ = _model(lam={"vqa": 1.0})
    x = {"text": "what color is the mug?", "images": [], "answer": "red"}
    l = m.vqa_loss([x], enc, dev)
    inp = enc.inputs(x["text"], [], dev)
    ids = enc.ids("red") + [enc.end]
    full = torch.cat([inp["input_ids"], torch.tensor([ids])], 1)
    lg = m.backbone(full).logits[0]
    P = inp["input_ids"].shape[1]
    ref = -np.mean([float(torch.log_softmax(lg[P - 1 + d], -1)[ids[d]]) for d in range(len(ids))])
    assert math.isclose(float(l), ref, rel_tol=1e-5)


def test_joint_train_loop_decreases_losses_on_synthetic_data():
    enc, dev = MockEncoder(), torch.device("cpu")
    torch.manual_seed(0)
    ss = D.synthetic_rows(24, seed=0)
    tr, va = D.split_samples(ss)
    m = M.new_model(MockBackbone(0), tr, HID, expert_kw={"width": 64, "depth": 2, "heads": 4}, aux_kw=AK)
    hist = T.train_loop(m, enc, tr, va, dev, steps=60, batch=4, lr=3e-3, lr_heads=2e-3, eval_every=60,
                        log=lambda r: None)
    ev = [h for h in hist if h["event"] == "eval"]
    assert ev[-1]["fm"] < ev[0]["fm"] and ev[-1]["dec"] < ev[0]["dec"]
    tl = [h["total"] for h in hist if h["event"] == "train"]
    assert np.mean(tl[-10:]) < np.mean(tl[:10])
    ki = T.ki_check(m, enc, tr[:2], dev)
    assert ki["backbone_grad_norm_from_fm"] == 0.0 and ki["backbone_grad_norm_from_aux"] > 0
    assert ki["expert_grad_norm_from_fm"] > 0
