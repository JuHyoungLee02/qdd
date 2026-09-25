"""E-MA3 (docs/stage3/prereg_ma3.md): OPT-IN per-layer backbone KV conditioning of the action expert, on the real
Qwen3-VL architecture (tiny random init, CPU, fp32) with the real processor. Pod only.

Checks: layer choice; the captured per-layer K / V of the context row are the same in the shared (R3) path and the
per-context path; KI stop (no expert gradient into the backbone) and the KV projections learn; cond() refuses KV of
another forward; save -> reload gives the identical chunk; a kvcond checkpoint does not load as a default one and a
default checkpoint loads unchanged through the kv loader; the CLI wrapper without the option is stageb_train.
"""
import json
import os

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
pytest.importorskip("peft")

MODEL = os.environ.get("STAGEA_BASE", "/data/harvest/models/Qwen3-VL-4B-Instruct")
if not os.path.exists(os.path.join(MODEL, "preprocessor_config.json")):
    pytest.skip("Qwen3-VL processor files not present (pod only)", allow_module_level=True)

from harvest.train import se2e_kvcond as K  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_model as M  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402

REL = 1e-4
EK = {"width": 32, "depth": 2, "heads": 4}
AK = {"width": 32, "heads": 4, "queries": 2}


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    d = tmp_path_factory.mktemp("kv")
    ss = D.synthetic_rows(5, seed=1, img_dir=str(d / "img"))
    bb, proc, hd = T.load_backbone("tiny", MODEL, torch.device("cpu"), lora={"r": 4, "alpha": 8, "dropout": 0.0})
    with torch.no_grad():
        for n, p in bb.named_parameters():
            if "lora_B" in n:
                p.normal_(0, 0.3)
    return bb, M.HFEncoder(proc), hd, ss, d


def _kv_model(env, seed=0):
    bb, enc, hd, ss, _ = env
    torch.manual_seed(seed)
    m = M.new_model(bb, ss, hd, expert_kw=EK, aux_kw=AK)
    return K.with_kvcond(m), enc, ss


def test_kv_layers_spread_over_the_backbone_and_end_at_the_last():
    assert K.kv_layers(36, 8) == [3, 8, 12, 17, 21, 26, 30, 35]
    assert K.kv_layers(2, 2) == [0, 1]
    with pytest.raises(ValueError):
        K.check_layers(K.kv_layers(2, 4), 2)


def test_captured_kv_equal_in_shared_and_per_context_paths(env):
    m, enc, ss = _kv_model(env)
    m.eval()
    batch = ss[:3]
    with torch.no_grad():
        m.shared = True
        c1, k1, _ = m.forward_shared(batch, enc, "cpu", grad=False)
        kv1 = [(k.clone(), v.clone()) for k, v in m._kv[1]]
        m.shared = False
        c0, k0 = m.contexts(batch, enc, "cpu", grad=False)
        kv0 = m._kv[1]
    assert torch.equal(k0, k1)
    assert len(kv0) == len(m.kv_layers) == 2 and kv0[0][0].shape == (3, c0.shape[1], m.expert.kv_dim)
    for (a0, b0), (a1, b1) in zip(kv0, kv1):
        for x, y in ((a0, a1), (b0, b1)):
            x, y = x * k0[..., None], y * k1[..., None]
            assert float((x - y).abs().max()) <= REL * max(1.0, float(x.abs().max()))


def test_cond_refuses_kv_of_another_forward(env):
    m, enc, ss = _kv_model(env)
    with torch.no_grad():
        ctx, mask, _ = m.forward_shared(ss[:2], enc, "cpu", grad=False)
        m.cond(ss[:2], ctx, mask, "cpu")
        with pytest.raises(RuntimeError):
            m.cond(ss[:2], ctx.clone(), mask, "cpu")


def test_ki_stop_and_the_kv_projections_learn(env):
    m, enc, ss = _kv_model(env)
    m.shared = True
    m.train()
    bb = [p for p in m.backbone.parameters() if p.requires_grad]
    ctx, mask, _ = m.forward_shared(ss[:2], enc, "cpu", grad=True)
    a, valid, _ = m.targets(ss[:2], "cpu")
    l_fm = K.fm_loss(m.expert, m.cond(ss[:2], ctx, mask, "cpu"), a, valid)
    g_bb = torch.autograd.grad(l_fm, bb, allow_unused=True, retain_graph=True)
    assert all(g is None or float(g.abs().max()) == 0.0 for g in g_bb)
    g_kv = torch.autograd.grad(l_fm, list(m.expert.kv.parameters()), allow_unused=True)
    assert all(g is not None for g in g_kv) and sum(float(g.abs().sum()) for g in g_kv) > 0
    assert torch.isfinite(l_fm)


def test_losses_train_step_runs_and_logs_fm(env):
    m, enc, ss = _kv_model(env)
    m.shared = True
    tot, logs = m.losses(ss[:2], enc, "cpu")
    tot.backward()
    assert torch.isfinite(tot) and "fm" in logs and "dec" in logs


def test_save_reload_identical_chunk_and_default_loader_refuses(env, tmp_path):
    m, enc, ss = _kv_model(env)
    bb = env[0]
    m.eval()
    m.save_heads(str(tmp_path), {"x": 1})
    cfg = json.load(open(tmp_path / "stageb.json"))
    assert cfg["expert_cond"]["ver"] == K.KV_VER and cfg["expert_cond"]["layers"] == m.kv_layers
    noise = torch.randn(1, m.expert.cfg.horizon, m.expert.cfg.act_dim, generator=torch.Generator().manual_seed(3))
    m.shared = False
    before = m.predict(ss[0], enc, "cpu", noise=noise)
    m2 = K.load_heads_kv(str(tmp_path), bb, "cpu").eval()
    assert isinstance(m2, K.StageBKV) and m2.kv_layers == m.kv_layers
    m2.shared = False
    after = m2.predict(ss[0], enc, "cpu", noise=noise)
    assert (before == after).all()
    with pytest.raises(RuntimeError):
        M.load_heads(str(tmp_path), bb, "cpu")


def test_default_checkpoint_loads_unchanged_through_the_kv_loader(env, tmp_path):
    bb, enc, hd, ss, _ = env
    torch.manual_seed(0)
    m = M.new_model(bb, ss, hd, expert_kw=EK, aux_kw=AK).eval()
    m.save_heads(str(tmp_path), {})
    a = M.load_heads(str(tmp_path), bb, "cpu")
    b = K.load_heads_kv(str(tmp_path), bb, "cpu")
    assert type(b) is M.StageB and type(b.expert) is type(a.expert)
    sa, sb_ = a.state_dict(), b.state_dict()
    assert sa.keys() == sb_.keys() and all(torch.equal(sa[k], sb_[k]) for k in sa)


def test_kv_conversion_keeps_the_baseline_initialisation(env):
    bb, enc, hd, ss, _ = env
    torch.manual_seed(0)
    base = M.new_model(bb, ss, hd, expert_kw=EK, aux_kw=AK)
    m, _, _ = _kv_model(env, seed=0)
    sb_, sk = base.state_dict(), m.state_dict()
    assert all(torch.equal(sb_[k], sk[k]) for k in sb_)
    assert sorted(set(sk) - set(sb_)) and all(k.startswith("expert.kv.") for k in set(sk) - set(sb_))


def test_cli_without_the_option_is_stageb_train():
    for cmd in (["train", "--run", "a"], ["predict", "--ckpt", "c", "--out", "o"], ["evalck", "--ckpt", "c"]):
        a = K.build_parser().parse_args(cmd)
        b = T.build_parser().parse_args(cmd)
        assert a.expert_cond == "none" and {k: v for k, v in vars(a).items() if k != "expert_cond"} == vars(b)
    saved = (T.aux_model, T.load_heads)
    K.install(T, K.build_parser().parse_args(["train", "--run", "a"]))
    assert (T.aux_model, T.load_heads) == saved
