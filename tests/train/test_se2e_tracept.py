"""E-MAR-real factor A (prereg_marr): `trace5-point@v1` pointing-trace aux target -- label -> target conversion,
attachment (RB2 labelled, RB1 masked), run-time registration with undo (default runs unchanged), the aux loss, and
the runtime path: the base view decides / predicts chunks bit-identically (training-only head)."""
import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from harvest.train import se2e_tracept as TP  # noqa: E402
from harvest.train import se2e_trace_model as TM  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_model as M  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402

from .test_stageb_torch import AK, EK, HID, MockBackbone, MockEncoder  # noqa: E402


@pytest.fixture
def installed():
    undo = TP.install()
    yield
    undo()


def test_target_conversion_and_masks():
    t = TP.target([[0, 255], [51, 102]])
    assert t["mask"] == [1, 1, 0, 0, 0]
    assert t["uv"][:4] == [0.0, 1.0, 51 / 255, 102 / 255] and t["uv"][4:] == [0.0] * 6
    assert TP.target(None) is None and TP.target([]) is None
    with pytest.raises(ValueError):
        TP.target([[0, 0]] * 6)
    with pytest.raises(ValueError):
        TP.target([[256, 0]])
    s = {"aux": {"reg": {}, "cls": {}}, "tracept": t}
    r, rm, _, _ = TP.tracept_aux_vecs(s)
    n = len(D.AUX_REG)
    assert r.shape == (n + 10,) and rm[n:].tolist() == [1, 1, 1, 1] + [0] * 6
    assert r[n + 1] == pytest.approx(1.0 / TP.SCALE) and not rm[:n].any()
    r0, rm0, _, _ = TP.tracept_aux_vecs({"aux": {"reg": {}, "cls": {}}, "tracept": None})
    assert not rm0.any() and not r0[n:].any()


def test_attach_labels_rb2_masks_rb1(tmp_path):
    rows = [{"key": "RB2_ep3_k5", "trace255": [[10, 20], [30, 40], [50, 60], [70, 80], [90, 100]]},
            {"key": "RB2_ep3_k9", "trace255": None}]
    (tmp_path / "RB2.tracept.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    ss = [{"key": "RB1_ep0_k0"}, {"key": "RB2_ep3_k5"}, {"key": "RB2_ep3_k9"}]
    c = TP.attach(ss, str(tmp_path))
    assert ss[0]["tracept"] is None and ss[2]["tracept"] is None and ss[1]["tracept"]["mask"] == [1] * 5
    assert c["RB1"] == {"rows": 1, "labelled": 0, "file": None} and c["RB2"]["labelled"] == 1
    with pytest.raises(KeyError):
        TP.attach([{"key": "RB2_ep4_k0"}], str(tmp_path))


def test_import_changes_nothing_and_install_undo():
    before = (T.AUX_CHOICES, T.AUX_FILES, T.attach_aux_targets, T._data, T.RESUME_KEYS, TM.extra_metrics,
              dict(TM.EXTRA))
    a0 = T.build_parser().parse_args(["train", "--run", "a"])
    assert not hasattr(a0, "tracept_root")
    with pytest.raises(SystemExit):
        T.build_parser().parse_args(["train", "--run", "a", "--aux-extra", TP.TRACEPT_VER])
    undo = TP.install()
    try:
        for cmd in (["train", "--run", "a"], ["predict", "--ckpt", "c", "--out", "o"], ["evalck", "--ckpt", "c"]):
            a = T.build_parser().parse_args(cmd + ["--aux-extra", TP.TRACEPT_VER, "--tracept-root", "/x"])
            assert a.aux_extra == TP.TRACEPT_VER and a.tracept_root == "/x"
            assert T.build_parser().parse_args(cmd).aux_extra == "none"
        assert "tracept_root" in T.RESUME_KEYS and TM.EXTRA[TP.TRACEPT_VER][0] == 10
        assert set(TP.FILES) <= set(T.AUX_FILES)
    finally:
        undo()
    after = (T.AUX_CHOICES, T.AUX_FILES, T.attach_aux_targets, T._data, T.RESUME_KEYS, TM.extra_metrics,
             dict(TM.EXTRA))
    assert after == before


def test_prompt_config_marker(installed):
    ss = D.synthetic_rows(4, seed=0)
    for s in ss:
        s["context"]["images"] = [["head camera:", "h.jpg"]]
    base = T.prompt_config_t(ss, "IMG", "D27v1", {"version": "se2e-motion@v1"})
    marked = T.prompt_config_t(ss, "IMG", "D27v1", {"version": "se2e-motion@v1"}, aux=TP.TRACEPT_VER)
    assert "aux" not in base and marked["aux"] == TP.TRACEPT_VER and marked["sha"] != base["sha"]
    assert set(TP.FILES) <= set(marked["files_sha"]) and not set(TP.FILES) & set(base["files_sha"])


def test_attach_aux_targets_dispatch(installed, tmp_path):
    (tmp_path / "RB2.tracept.jsonl").write_text(json.dumps({"key": "RB2_ep3_k5", "trace255": [[1, 2]]}) + "\n")
    a = T.build_parser().parse_args(["train", "--run", "a", "--aux-extra", TP.TRACEPT_VER,
                                     "--tracept-root", str(tmp_path)])
    ss = [{"key": "RB2_ep3_k5"}, {"key": "RB1_ep0_k0"}]
    T.attach_aux_targets(a, ss)
    assert ss[0]["tracept"]["mask"] == [1, 0, 0, 0, 0] and ss[1]["tracept"] is None
    s2 = [{"key": "RB2_ep3_k5"}]
    T.attach_aux_targets(T.build_parser().parse_args(["train", "--run", "a"]), s2)
    assert "tracept" not in s2[0]


def _samples(n=6, seed=0):
    ss = D.synthetic_rows(n, seed=seed)
    rng = np.random.default_rng(seed)
    for i, s in enumerate(ss):
        s["aux"] = {"reg": {}, "cls": {}}
        pts = rng.integers(0, 256, (1 + i % 5, 2)).tolist()
        s["tracept"] = None if i == 1 else TP.target(pts)
    return ss


def _model(seed=0, lam=None):
    torch.manual_seed(seed)
    ss = _samples(seed=seed)
    m = M.new_model(MockBackbone(seed), ss, HID, expert_kw=EK, aux_kw=AK, lam=lam)
    return TM.with_trace_head(m, TP.TRACEPT_VER), ss


def test_head_and_loss(installed):
    m, ss = _model()
    assert m.aux.cfg.n_reg == len(D.AUX_REG) + 10 and m.aux_ver == TP.TRACEPT_VER
    enc, dev = MockEncoder(), torch.device("cpu")
    total, logs = m.losses(ss, enc, dev)
    with torch.no_grad():
        ctx, mask = m.contexts(ss, enc, dev, grad=False)
        r, rm, _, _ = (torch.tensor(np.stack(x)) for x in zip(*[TP.tracept_aux_vecs(s) for s in ss]))
        pr, _ = m.aux.full(ctx, mask)
        want = (torch.nn.functional.smooth_l1_loss(pr, r, reduction="none") * rm).sum() / rm.sum()
    assert logs["aux_trace"] == pytest.approx(float(want), rel=1e-5)
    m2, _ = _model(lam={"dec": 0.0, "act": 0.0, "ver": 0.0})
    tot2, _ = m2.losses(ss, enc, dev)
    gs = torch.autograd.grad(tot2, list(m2.backbone.parameters()), allow_unused=True)
    assert sum(float((g ** 2).sum()) for g in gs if g is not None) > 0  # reaches the backbone (§58)


def test_runtime_path_base_view_identical(installed):
    """Training-only head: the same checkpoint in the trained view and the base (runtime) view gives bit-identical
    decision records and chunks."""
    m, ss = _model()
    enc, dev = MockEncoder(), torch.device("cpu")
    recs_t = []
    ev_t = T.evaluate(m, enc, ss, dev, seed=0, records=recs_t)
    noise = torch.randn(1, m.expert.cfg.horizon, m.expert.cfg.act_dim, generator=torch.Generator().manual_seed(3))
    ch_t = m.predict(ss[0], enc, dev, noise=noise)
    TM.base_view(m, TP.TRACEPT_VER)
    assert type(m) is M.StageB
    recs_b = []
    ev_b = T.evaluate(m, enc, ss, dev, seed=0, records=recs_b)
    ch_b = m.predict(ss[0], enc, dev, noise=noise)
    assert recs_t == recs_b and np.array_equal(ch_t, ch_b)
    assert {k: v for k, v in ev_t.items() if k != "aux"} == {k: v for k, v in ev_b.items() if k != "aux"}


def test_aux_model_and_extra_metrics(installed, tmp_path):
    ss = _samples()
    torch.manual_seed(0)
    m = M.new_model(MockBackbone(0), ss, HID, expert_kw=EK, aux_kw=AK)
    a = T.build_parser().parse_args(["train", "--run", "a", "--aux-extra", TP.TRACEPT_VER])
    m = T.aux_model(a, m, new=True)
    assert isinstance(m, TM.StageBTrace) and m.aux.cfg.n_reg == len(D.AUX_REG) + 10
    m.save_heads(str(tmp_path))
    m2 = T.aux_model(a, M.load_heads(str(tmp_path), m.backbone), new=False)
    ctx, mask = torch.randn(1, 4, HID), torch.ones(1, 4, dtype=torch.long)
    assert torch.equal(m.aux.full(ctx, mask)[0], m2.aux.full(ctx, mask)[0])
    ev = TM.extra_metrics(m, MockEncoder(), ss, torch.device("cpu"), seed=0)
    n_pts = sum(sum(s["tracept"]["mask"]) for s in ss if s["tracept"] is not None)
    assert ev["tracept_px"]["n_points"] == n_pts and ev["tracept_px"]["n_rows"] == len(ss) - 1
    assert ev["tracept_px"]["mean_px"] > 0 and len(ev["tracept_px"]["per_point_mean_px"]) == 5
    assert ev["chunk_mse_committed"] > 0 and ev["trace_px"] is None
