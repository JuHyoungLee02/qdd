"""E-MA1 A factor (prereg_ma1 §3.1) on the mocked causal backbone (CPU torch): trace head sizing, the trace5 aux loss
added to the stage-B loss, gradient to the backbone, save / load, the extra (outside-the-rule) metrics."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from harvest.train import se2e_trace as TR  # noqa: E402
from harvest.train import se2e_trace_model as TM  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_expert as E  # noqa: E402
from harvest.train import stageb_model as M  # noqa: E402

from .test_stageb_torch import AK, EK, HID, MockBackbone, MockEncoder  # noqa: E402


def _samples(n=6, seed=0):
    ss = D.synthetic_rows(n, seed=seed)
    rng = np.random.default_rng(seed)
    for s in ss:
        s["aux"] = {"reg": {}, "cls": {}}  # S-E2E rows: no privileged geometry
        s["trace5"] = {"uv": rng.uniform(0, 1, 10).tolist(), "mask": [1, 1, 0, 1, 1]}
    return ss


def _model(seed=0, lam=None):
    torch.manual_seed(seed)
    ss = _samples(seed=seed)
    m = M.new_model(MockBackbone(seed), ss, HID, expert_kw=EK, aux_kw=AK, lam=lam)
    return TM.with_trace_head(m), ss


def test_trace_head_sizes_and_base_view():
    m, ss = _model()
    assert isinstance(m, TM.StageBTrace) and isinstance(m.aux, TM.TraceAuxHead)
    assert m.aux.cfg.n_reg == len(D.AUX_REG) + 10 and m.aux.cfg.n_cls == len(D.AUX_CLS)
    ctx, mask = torch.randn(2, 5, HID), torch.ones(2, 5, dtype=torch.long)
    r, c = m.aux(ctx, mask)
    rf, cf = m.aux.full(ctx, mask)
    assert r.shape == (2, len(D.AUX_REG)) and rf.shape == (2, len(D.AUX_REG) + 10)
    assert torch.equal(rf[:, :len(D.AUX_REG)], r) and torch.equal(c, cf)


def test_loss_adds_lambda_times_masked_trace_loss():
    m, ss = _model()
    enc, dev = MockEncoder(), torch.device("cpu")
    g = torch.Generator().manual_seed(0)
    t = E.sample_time(len(ss), dev, g)
    a, _, _ = m.targets(ss, dev)
    noise = torch.randn(a.shape, generator=g)
    total, logs = m.losses(ss, enc, dev, fm_t=t, fm_noise=noise)
    with torch.no_grad():
        ctx, mask = m.contexts(ss, enc, dev, grad=False)
        r, rm, c, cm = (torch.tensor(np.stack(x)) for x in zip(*[TR.trace_aux_vecs(s) for s in ss]))
        pr, _ = m.aux.full(ctx, mask)
        want = (torch.nn.functional.smooth_l1_loss(pr, r, reduction="none") * rm).sum() / rm.sum()
    assert logs["aux_trace"] == pytest.approx(float(want), rel=1e-5)
    base = M.StageB.losses(TM.as_base(m), ss, enc, dev, fm_t=t, fm_noise=noise)[0]
    TM.as_trace(m)
    assert float(total.detach()) == pytest.approx(float(base.detach()) + 0.1 * float(want), rel=1e-5)
    assert logs["aux"] == pytest.approx(float(want), rel=1e-5)


def test_trace_loss_reaches_the_backbone():
    m, ss = _model(lam={"dec": 0.0, "act": 0.0, "ver": 0.0})
    enc, dev = MockEncoder(), torch.device("cpu")
    total, _ = m.losses(ss, enc, dev)
    bb = [p for p in m.backbone.parameters()]
    gs = torch.autograd.grad(total, bb, allow_unused=True)
    assert sum(float((g ** 2).sum()) for g in gs if g is not None) > 0


def test_refuses_rows_with_privileged_aux_targets():
    m, ss = _model()
    ss[0]["aux"] = {"reg": {D.AUX_REG[0]: 0.1}, "cls": {}}
    with pytest.raises(ValueError):
        m.losses(ss, MockEncoder(), torch.device("cpu"))


def test_save_load_roundtrip(tmp_path):
    m, ss = _model()
    m.save_heads(str(tmp_path))
    m2 = TM.as_trace(M.load_heads(str(tmp_path), m.backbone))
    ctx, mask = torch.randn(1, 4, HID), torch.ones(1, 4, dtype=torch.long)
    assert torch.equal(m.aux.full(ctx, mask)[0], m2.aux.full(ctx, mask)[0])
    assert isinstance(m2, TM.StageBTrace)


def test_extra_metrics_trace_error_and_predicted_decision_chunk():
    m, ss = _model()
    ev = TM.extra_metrics(m, MockEncoder(), ss, torch.device("cpu"), seed=0)
    assert ev["n"] == len(ss)
    assert ev["trace_px"]["n_points"] == 4 * len(ss) and ev["trace_px"]["mean"] > 0
    assert len(ev["trace_px"]["per_point_mean"]) == 5
    assert ev["chunk_mse_committed"] > 0 and ev["chunk_mse_predicted"] > 0
    ev2 = TM.extra_metrics(TM.as_base(m), MockEncoder(), ss, torch.device("cpu"), seed=0)
    assert ev2["trace_px"] is None and ev2["chunk_mse_committed"] == pytest.approx(ev["chunk_mse_committed"])
