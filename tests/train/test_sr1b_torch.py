"""E-SR1b (prereg_sr1b): decision CFG sampling, training-time decision dropout and the CLI wrapper (torch needed:
pod / torch environments). The default path (options off) must be r2_ma2 / stageb_train unchanged."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from harvest.train import r2_ma2 as M  # noqa: E402
from harvest.train import sr1b as S  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402
from harvest.train.stageb_expert import ActionExpert, ExpertConfig, sample_actions  # noqa: E402

OPT = ("sr1b_drop", "sr1b_relabel", "sr1b_urdf")


def _expert_cond(B=3, seed=0):
    torch.manual_seed(seed)
    e = ActionExpert(ExpertConfig(ctx_dim=16, horizon=4, proprio_dim=5, n_questions=5, dec_vocab=20, width=32,
                                  depth=2, heads=4)).eval()
    g = torch.Generator().manual_seed(seed)
    cond = {"ctx": torch.randn(B, 6, 16, generator=g), "ctx_mask": torch.ones(B, 6, dtype=torch.long),
            "proprio": torch.randn(B, 5, generator=g), "skill": torch.tensor([1] * B), "phase": torch.tensor([2] * B),
            "dec": torch.randint(1, 20, (B, 5), generator=g)}
    noise = torch.randn(B, 4, 8, generator=g)
    return e, cond, noise


def test_null_cond_zeroes_only_the_slots():
    _, cond, _ = _expert_cond()
    d0 = cond["dec"].clone()
    n = S.null_cond(cond, (0, 1, 2))
    assert torch.equal(cond["dec"], d0)  # input unchanged
    assert (n["dec"][:, :3] == 0).all() and torch.equal(n["dec"][:, 3:], d0[:, 3:])
    assert n["ctx"] is cond["ctx"]


def test_cfg_w1_is_the_plain_path_and_w0_the_null_path():
    e, cond, noise = _expert_cond()
    assert torch.equal(S.sample_actions_cfg(e, cond, 1.0, 5, noise), sample_actions(e, cond, 5, noise))
    z0 = S.sample_actions_cfg(e, cond, 0.0, 5, noise)
    assert torch.allclose(z0, sample_actions(e, S.null_cond(cond, S.JOY_SLOTS), 5, noise), atol=1e-5)


def test_cfg_matches_the_guidance_formula():
    e, cond, noise = _expert_cond()
    w, steps = 3.0, 4
    nc = S.null_cond(cond, S.JOY_SLOTS)
    ec, en = e.encode(cond), e.encode(nc)
    x, dt = noise.clone(), -1.0 / steps
    for i in range(steps):
        t = torch.full((x.shape[0],), 1.0 + i * dt)
        vc, vn = e.velocity(ec, x, t), e.velocity(en, x, t)
        x = x + dt * (vn + w * (vc - vn))
    assert torch.allclose(S.sample_actions_cfg(e, cond, w, steps, noise), x, atol=1e-5)


class _Stub:
    def __init__(self):
        self.training = True

    def cond(self, samples, ctx, mask, device):
        return {"dec": torch.arange(1, 6).repeat(len(samples), 1), "ctx": ctx}


def test_dropout_only_in_training_and_only_the_joystick_slots():
    m = _Stub()
    S.with_dropout(m, 1.0, seed=0)
    c = m.cond([{}] * 4, "C", None, "cpu")
    assert (c["dec"][:, :3] == 0).all() and torch.equal(c["dec"][:, 3:], torch.tensor([[4, 5]] * 4))
    assert c["ctx"] == "C"
    m.training = False
    assert torch.equal(m.cond([{}] * 4, "C", None, "cpu")["dec"], torch.arange(1, 6).repeat(4, 1))
    m2 = _Stub()
    S.with_dropout(m2, 0.0, seed=0)
    assert "cond" not in vars(m2)  # p = 0: not installed


def test_dropout_rate():
    m = _Stub()
    S.with_dropout(m, 0.3, seed=0)
    z = torch.cat([(m.cond([{}] * 8, None, None, "cpu")["dec"][:, 0] == 0) for _ in range(3000)]).float()
    assert abs(float(z.mean()) - 0.3) < 0.01


def test_cli_without_the_options_is_r2_ma2():
    for cmd in (["train", "--run", "a"], ["predict", "--ckpt", "c", "--out", "o"], ["evalck", "--ckpt", "c"],
                ["train", "--run", "a", "--ma2", "c0", "--data", "r2"]):
        a = S.build_parser().parse_args(cmd)
        b = M.build_parser().parse_args(cmd)
        assert a.sr1b_drop == 0.0 and a.sr1b_relabel is False
        assert {k: v for k, v in vars(a).items() if k not in OPT} == vars(b)
    saved = (T._load_data, T.prompt_config, T.new_model)
    S.install(T, S.build_parser().parse_args(["train", "--run", "a", "--ma2", "c0", "--data", "r2"]))
    assert (T._load_data, T.prompt_config, T.new_model) == saved


def test_install_needs_r2_and_ma2_c0(monkeypatch):
    for n in ("_load_data", "prompt_config", "new_model"):
        monkeypatch.setattr(T, n, getattr(T, n))
    for cmd in (["train", "--run", "a", "--sr1b-drop", "0.3", "--data", "se2e", "--ma2", "c0"],
                ["train", "--run", "a", "--sr1b-drop", "0.3", "--data", "r2"],
                ["train", "--run", "a", "--sr1b-drop", "1.5", "--data", "r2", "--ma2", "c0"]):
        with pytest.raises(SystemExit):
            S.install(T, S.build_parser().parse_args(cmd))


def test_install_patches_loader_prompt_config_and_model(monkeypatch):
    ex = np.zeros((15, 8))
    ex[-1, :3] = [0.0, 0.01, 0.0]
    s = {"key": "P0_ep1_k3", "arm": "right", "action_exec": ex.tolist(),
         "committed": {"dir_xy": "minus_x", "dir_z": "none_z", "mag_coarse": "small"}, "items": []}

    def fake_load(args):
        return [s], 30, [s], []
    monkeypatch.setattr(T, "_load_data", fake_load)
    monkeypatch.setattr(T, "prompt_config", lambda *x, **k: {"camera": ["x"], "sha": "old"})
    monkeypatch.setattr(T, "new_model", lambda *x, **k: _Stub())
    a = S.build_parser().parse_args(["train", "--run", "a", "--data", "r2", "--ma2", "c0", "--sr1b-drop", "0.3",
                                     "--sr1b-relabel"])
    S.install(T, a, fk_by_arm={"right": lambda q: np.asarray(q, float)[..., :3]})
    ss, _, tr, va = T._load_data(a)
    assert ss[0]["committed"]["dir_xy"] == "plus_y" and tr[0] is ss[0] and va == []
    assert s["committed"]["dir_xy"] == "minus_x"
    cfg = T.prompt_config()
    assert cfg["sr1b_drop"] == 0.3 and cfg["sr1b_relabel"] is True and cfg["sha"] != "old"
    m = T.new_model()
    assert "cond" in vars(m)  # dropout installed on the new model
