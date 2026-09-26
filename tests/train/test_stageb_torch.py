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
    l_ver = m.verify_loss(ss[:3], ctx, mask, dev)  # §61/§64 verification head also reaches the backbone
    assert sum(float(g.abs().sum()) for g in _grads(l_ver, bb)) > 0
    # full joint loss: backbone gradient == gradient of (dec + 0.5 aux + 0.1 verify) alone
    g = torch.Generator().manual_seed(2)
    a, _, _ = m.targets(ss[:3], dev)
    t, noise = E.sample_time(3, dev, g), torch.randn(a.shape, generator=g)
    total, logs = m.losses(ss[:3], enc, dev, fm_t=t, fm_noise=noise)
    g_total = _grads(total, bb)
    ctx, mask = m.contexts(ss[:3], enc, dev, grad=True)
    l_aux2, _ = E.aux_loss(m.aux, ctx, mask, r, rm, c, cm)
    g_ref = _grads(m.decision_loss(ss[:3], enc, dev) + 0.5 * l_aux2 + 0.1 * m.verify_loss(ss[:3], ctx, mask, dev), bb)
    for x, y in zip(g_total, g_ref):
        assert torch.allclose(x, y, atol=1e-6)
    assert {"fm", "aux", "dec", "ver", "total"} <= set(logs)


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
        ctx, mask = m.contexts(ss[:1], enc, dev, grad=False)
        with torch.no_grad():
            v1, v2 = m.verify_logits(ctx, mask), m2.verify_logits(ctx, mask)
        assert v1.shape == (1, len(D.VERIFY_PREDS)) and torch.equal(v1, v2)


def test_masked_proprio_is_zeroed_with_a_mask_channel_and_never_reaches_the_expert():
    """canon §63 (3): a masked key (S-E2E tau) is zero in the expert input, its mask channel is 0, and its recorded
    value cannot change the condition; no loss term reads proprio."""
    enc, dev = MockEncoder(), torch.device("cpu")
    m, ss = _model()
    assert m.expert.cfg.proprio_dim == D.PROPRIO_IN_DIM
    s = dict(ss[0], proprio_mask={"q": 1, "qd": 1, "tau": 0, "grip": 1})
    s_big = dict(s, proprio=dict(s["proprio"], tau=[999.0] * 7))
    ctx, mask = m.contexts([s], enc, dev, grad=False)
    p = m.cond([s], ctx, mask, dev)["proprio"][0]
    assert p.shape == (D.PROPRIO_IN_DIM,) and torch.all(p[14:21] == 0)
    assert p[D.PROPRIO_DIM:].tolist() == [1.0, 1.0, 0.0, 1.0]
    assert torch.equal(m.cond([s_big], ctx, mask, dev)["proprio"], m.cond([s], ctx, mask, dev)["proprio"])
    u_big = dict(ss[0], proprio=dict(ss[0]["proprio"], tau=[999.0] * 7))  # unmasked: tau is an input
    assert not torch.equal(m.cond([u_big], ctx, mask, dev)["proprio"], m.cond([ss[0]], ctx, mask, dev)["proprio"])
    _, logs = m.losses([s], enc, dev)
    assert not any("proprio" in k or "tau" in k for k in logs)


def test_pre_s63_expert_without_mask_channel_keeps_its_23_d_condition():
    enc, dev = MockEncoder(), torch.device("cpu")
    m, ss = _model()
    m.expert = E.ActionExpert(E.ExpertConfig(**{**m.expert.cfg.to_json(), "proprio_dim": D.PROPRIO_DIM}))
    ctx, mask = m.contexts(ss[:1], enc, dev, grad=False)
    assert m.cond(ss[:1], ctx, mask, dev)["proprio"].shape == (1, D.PROPRIO_DIM)
    assert m.predict(ss[0], enc, dev).shape == (15, 8)


def test_per_arm_statistics_are_used_for_each_samples_arm():
    """canon §63 (1): targets / conditions of a left-arm sample use the left-arm statistics."""
    enc, dev = MockEncoder(), torch.device("cpu")
    m, ss = _model()
    left = []
    for s in ss:
        a = (np.asarray(s["action_exec"]) - 2.0).tolist()
        left.append(dict(s, arm="left", action_exec=a, action_script=a,
                         proprio=dict(s["proprio"], q=(np.asarray(s["proprio"]["q"]) - 2.0).tolist())))
    m.norm = D.ActionNorm.fit(ss + left, "absolute")
    a, _, _ = m.targets(left[:1], dev)
    ref, _ = m.norm.target(left[0]["action_exec"], left[0]["action_script"], arm="left")
    assert np.allclose(a[0].numpy(), ref) and abs(float(a[0, :, 0].mean())) < 3.0
    ctx, mask = m.contexts(left[:1], enc, dev, grad=False)
    p = m.cond(left[:1], ctx, mask, dev)["proprio"][0, :D.PROPRIO_DIM].numpy()
    assert np.allclose(p, m.norm.proprio(left[0]["proprio"], arm="left"), atol=1e-6)
    noise = torch.randn(1, 15, 8, generator=torch.Generator().manual_seed(1))
    with torch.no_grad():
        z = E.sample_actions(m.expert, m.cond(left[:1], ctx, mask, dev), 10, noise)[0].numpy()
    out = m.predict(left[0], enc, dev, noise=noise)
    assert np.allclose(out, m.norm.action(z, arm="left"), atol=1e-5)  # decoded with the left statistics
    assert not np.allclose(out, m.norm.action(z, arm="right"), atol=1e-2)


def test_verify_preds_are_the_m4b_test_predicates():
    from harvest.m4b import spec as FS
    assert D.VERIFY_PREDS == FS.PREDS


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


# ---------------------------------------------------------------------------------- S-E2E trainer items (§69 N2, N3)
def _src_samples():
    return ([{"key": f"RB1_ep{e}_k{k}"} for e in range(30) for k in (0, 5)]
            + [{"key": f"RB2_ep{e}_k{k}"} for e in range(6) for k in (0, 5)])


def test_stratified_val_takes_n_per_source_seeded_and_order_free():
    va = _src_samples()
    a = T.stratified_val(list(va), 5, seed=0)
    assert sorted(T.source_of(s) for s in a) == ["RB1"] * 5 + ["RB2"] * 5  # --max-val first-N would be RB1 only
    assert a == T.stratified_val(list(reversed(va)), 5, seed=0)  # input order does not matter
    assert a != T.stratified_val(list(va), 5, seed=1)
    few = T.stratified_val(list(va), 20, seed=0)  # a source with fewer samples than n gives all of them
    assert sum(T.source_of(s) == "RB2" for s in few) == 12 and sum(T.source_of(s) == "RB1" for s in few) == 20
    assert T.stratified_val(list(va), 0, seed=0) == va  # 0 = the whole validation split


def test_val_subset_options_first_n_or_stratified_not_both():
    va = _src_samples()
    assert T.val_subset(va, 0, 0, 0) == va
    assert T.val_subset(va, 4, 0, 0) == va[:4]  # old --max-val (first N) kept for the earlier smokes
    assert T.val_subset(va, 0, 3, 7) == T.stratified_val(va, 3, 7)
    with pytest.raises(SystemExit):
        T.val_subset(va, 4, 3, 0)


def _loop(m, tr, va, **kw):
    recs = []
    hist = T.train_loop(m, MockEncoder(), tr, va, torch.device("cpu"), batch=3, lr=3e-3, lr_heads=2e-3,
                        log=recs.append, **kw)
    return hist, recs


def _strip(recs, kind="train"):
    return [{k: v for k, v in r.items() if k not in ("elapsed_s", "utc")} for r in recs if r["event"] == kind]


def test_checkpoint_cadence_eval_cadence_and_stop_at():
    import copy
    torch.manual_seed(0)
    ss = D.synthetic_rows(16, seed=0)
    tr, va = D.split_samples(ss)
    m = M.new_model(MockBackbone(0), tr, HID, expert_kw=EK, aux_kw=AK)
    saved = []
    hist, _ = _loop(m, tr, va, steps=10, eval_every=4, save_every=4,
                    save=lambda step, st: saved.append((step, copy.deepcopy(st))))
    assert [h["step"] for h in hist if h["event"] == "eval"] == [0, 4, 8, 10]
    assert [s for s, _ in saved] == [4, 8, 10]  # every save_every steps and the last step
    assert saved[0][1]["step"] == 4 and {"opt", "sched", "py_rng", "torch_rng", "order"} <= set(saved[0][1])
    tr_steps = [h for h in hist if h["event"] == "train"]
    assert all(len(h["idx"]) == 3 for h in tr_steps)  # the batch indices are logged (data-order check)
    m2 = M.new_model(MockBackbone(0), tr, HID, expert_kw=EK, aux_kw=AK)
    hist2, _ = _loop(m2, tr, va, steps=10, eval_every=4, stop_at=6)
    assert [h["step"] for h in hist2 if h["event"] == "train"][-1] == 6  # stops early, schedule of 10 steps


def test_resume_from_a_mid_checkpoint_reproduces_the_next_steps_exactly():
    import copy
    torch.manual_seed(0)
    ss = D.synthetic_rows(16, seed=0)
    tr, va = D.split_samples(ss)
    m = M.new_model(MockBackbone(0), tr, HID, expert_kw=EK, aux_kw=AK)
    saved = {}

    def save(step, st):
        saved[step] = (copy.deepcopy(m.state_dict()), copy.deepcopy(st))
    _, recs = _loop(m, tr, va, steps=12, eval_every=6, save_every=6, save=save, seed=3)
    weights, st = saved[6]
    torch.manual_seed(99)  # a fresh model with other initial weights: everything must come from the checkpoint
    m2 = M.new_model(MockBackbone(5), tr, HID, expert_kw=EK, aux_kw=AK)
    m2.load_state_dict(weights)
    _, recs2 = _loop(m2, tr, va, steps=12, eval_every=6, save_every=6, save=lambda *x: None, seed=3, resume=st)
    assert _strip(recs2) == [r for r in _strip(recs) if r["step"] > 6]  # losses, grad norm, lr, batch: identical
    assert _strip(recs2, "eval") == [r for r in _strip(recs, "eval") if r["step"] > 6]  # no step-0 eval again
    assert recs2[0]["event"] == "resume" and recs2[0]["step"] == 6


def test_resume_refuses_a_changed_training_setting():
    # segment_dropout is declared explicitly (matching the current default) so this fixture isolates lr/seed, not
    # the SAVED_BEFORE back-compat resolution covered separately below.
    base = {"lr": 1e-4, "batch": 8, "seed": 0, "val_per_kind": 150, "run": "a", "stop_at": 0, "segment_dropout": 0.3}
    T.check_resume_args(base, {**base, "run": "b", "stop_at": 50})  # run name / stop point may differ
    with pytest.raises(SystemExit):
        T.check_resume_args(base, {**base, "lr": 2e-4})
    with pytest.raises(SystemExit):
        T.check_resume_args(base, {**base, "seed": 1})


def test_resume_of_an_old_checkpoint_without_segment_dropout_key_needs_the_pre_existing_value():
    """A checkpoint saved before --segment-dropout existed has no segment_dropout key in its saved args
    (SAVED_BEFORE = 0.0, ser-A-min-3 fix round 1). Resuming it with the new parser default (0.3) is a real change
    in the training trajectory and must be refused; resuming with --segment-dropout 0.0 reproduces the old run."""
    old_saved = {"lr": 1e-4, "batch": 8, "seed": 0, "val_per_kind": 150, "run": "a", "stop_at": 0}
    with pytest.raises(SystemExit):
        T.check_resume_args(old_saved, {**old_saved, "run": "b", "segment_dropout": 0.3})
    T.check_resume_args(old_saved, {**old_saved, "run": "b", "segment_dropout": 0.0})


# ---------------------------------------------------------------------------------- S-E2E diagnostics (prereg_se2e_diag)
def _lrs(schedule, warmup_steps, steps=12):
    torch.manual_seed(0)
    ss = D.synthetic_rows(16, seed=0)
    tr, va = D.split_samples(ss)
    m = M.new_model(MockBackbone(0), tr, HID, expert_kw=EK, aux_kw=AK)
    hist, _ = _loop(m, tr, va, steps=steps, eval_every=steps, schedule=schedule, warmup_steps=warmup_steps)
    return [h["lr_heads"] for h in hist if h["event"] == "train"]


def test_default_schedule_is_the_old_warmup_cosine_exactly():
    lrs = _lrs("cosine", 0)
    w, total, base = max(1, math.ceil(0.03 * 12)), 12, 2e-3
    old = lambda s: (s + 1) / w if s < w else 0.5 * (1 + math.cos(math.pi * min(1.0, (s - w) / max(1, total - w))))  # noqa: E731
    assert lrs == [base * old(s) for s in range(1, 13)]


def test_constant_schedule_warms_up_then_stays_flat():
    lrs = _lrs("constant", 4)
    assert lrs[:3] == pytest.approx([2e-3 * k / 4 for k in (2, 3, 4)])  # scheduler already stepped once at step 1
    assert lrs[3:] == [2e-3] * 9


def test_train_subset_is_stratified_seeded_and_order_free():
    tr = _src_samples()
    a = T.train_subset(list(tr), 4, seed=0)
    assert sorted(T.source_of(s) for s in a) == ["RB1"] * 4 + ["RB2"] * 4
    assert a == T.train_subset(list(reversed(tr)), 4, seed=0)
    assert a != T.train_subset(list(tr), 4, seed=1)
    assert T.train_subset(tr, 0, seed=0) is tr  # 0 = the whole train split (default)


def test_extra_eval_sets_are_evaluated_at_the_eval_cadence():
    torch.manual_seed(0)
    ss = D.synthetic_rows(16, seed=0)
    tr, va = D.split_samples(ss)
    m = M.new_model(MockBackbone(0), tr, HID, expert_kw=EK, aux_kw=AK)
    hist, _ = _loop(m, tr, va, steps=6, eval_every=3, extra_evals={"train_subset": tr[:4]})
    ex = [h for h in hist if h["event"] == "eval_train_subset"]
    assert [h["step"] for h in ex] == [0, 3, 6] and all(h["n"] == 4 for h in ex)
    assert [h["step"] for h in hist if h["event"] == "eval"] == [0, 3, 6]


def test_evaluate_records_per_item_predictions_without_changing_the_metrics():
    torch.manual_seed(0)
    m, ss = _model(n=6)
    enc, dev = MockEncoder(), torch.device("cpu")
    ref = T.evaluate(m, enc, ss, dev, seed=0)
    recs = []
    ev = T.evaluate(m, enc, ss, dev, seed=0, records=recs)
    assert ev == ref
    assert len(recs) == sum(len(s["items"]) for s in ss)
    r = recs[0]
    assert {"key", "question", "target", "pred", "lp", "correct"} <= set(r)
    assert r["pred"] == max(r["lp"], key=r["lp"].get) and r["correct"] == (r["pred"] in r["target"])
    assert np.mean([x["correct"] for x in recs]) == pytest.approx(ev["dec_acc"])


def test_parser_defaults_keep_the_s_e2e_behaviour():
    a = T.build_parser().parse_args(["train", "--run", "x"])
    assert (a.init_weights, a.train_subset, a.lr_schedule, a.warmup_steps, a.eval_train_subset) == \
        ("", 0, "cosine", 0, False)
    p = T.build_parser().parse_args(["predict", "--ckpt", "c", "--out", "o.jsonl"])
    assert p.cmd == "predict"
    assert (a.train_fraction, a.eval_train_per_kind) == (0.0, 0)


def test_train_fraction_keeps_the_source_mix_is_nested_and_order_free():
    tr = [{"key": f"RB1_ep{e}_k{k}"} for e in range(40) for k in (0, 5)] + \
        [{"key": f"RB2_ep{e}_k{k}"} for e in range(10) for k in (0, 5)]  # 80 RB1, 20 RB2
    q = T.train_fraction(list(tr), 0.25, seed=0)
    assert sorted(T.source_of(s) for s in q) == ["RB1"] * 20 + ["RB2"] * 5  # same fraction of every source
    h = T.train_fraction(list(tr), 0.5, seed=0)
    assert {s["key"] for s in q} < {s["key"] for s in h}  # 25 % inside 50 % (same seed)
    assert q == T.train_fraction(list(reversed(tr)), 0.25, seed=0)
    assert {s["key"] for s in q} != {s["key"] for s in T.train_fraction(list(tr), 0.25, seed=1)}
    assert T.train_fraction(tr, 0.0, seed=0) is tr  # 0 = off
