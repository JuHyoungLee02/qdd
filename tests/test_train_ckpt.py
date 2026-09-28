"""Full-state checkpoints (harvest.teach_l8.ckpt): a run stopped at a checkpoint and resumed must end with exactly the
same trainable weights as the run that never stopped (toy model with dropout, AdamW, cosine LR, grad accumulation,
micro-batch order from the seed — the same loop shape as the trainers); a resume with another layout is refused."""
import math

import pytest

torch = pytest.importorskip("torch")

from harvest.teach_l8 import ckpt  # noqa: E402

LAYOUT = {"world": 1, "micro": 2, "accum": 2, "seed": 0, "epochs": 2, "max_steps": 0, "rows": 24}


def _model():
    torch.manual_seed(123)
    return torch.nn.Sequential(torch.nn.Linear(4, 16), torch.nn.Dropout(0.3), torch.nn.Linear(16, 1))


def _run(out, stop_after=None, resume=False, save_every=3):
    torch.manual_seed(0)
    m = _model()
    x = torch.randn(24, 4, generator=torch.Generator().manual_seed(1))
    y = torch.randn(24, 1, generator=torch.Generator().manual_seed(2))
    opt = torch.optim.AdamW(m.parameters(), lr=1e-2)
    per_epoch, total = 24 // 2 // 2, 2 * 24 // 2 // 2
    lr_at = lambda s: 1e-2 * 0.5 * (1 + math.cos(math.pi * s / total))  # noqa: E731
    step, ep0, k0 = 0, 0, 0
    if resume:
        pos = ckpt.load(out, m, opt, LAYOUT)
        step, ep0, k0 = pos["step"], pos["epoch"], pos["next_k"]
    m.train()
    for ep in range(ep0, 2):
        order = torch.randperm(24, generator=torch.Generator().manual_seed(LAYOUT["seed"] + ep)).view(-1, 2)
        start = k0 if ep == ep0 else 0
        for k in range(start, len(order)):
            idx = order[k]
            (torch.nn.functional.mse_loss(m(x[idx]), y[idx]) / 2).backward()
            if (k + 1) % 2 == 0:
                for g in opt.param_groups:
                    g["lr"] = lr_at(step)
                opt.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                if step % save_every == 0:
                    ckpt.save(out, m, opt, {"step": step, "epoch": ep, "next_k": k + 1}, LAYOUT)
                    if stop_after is not None and step == stop_after:
                        return None
    assert step == total and per_epoch * 2 == total
    return {n: p.detach().clone() for n, p in m.named_parameters()}


def test_resume_matches_straight_run(tmp_path):
    straight = _run(str(tmp_path / "a"))
    assert _run(str(tmp_path / "b"), stop_after=3) is None       # stops inside epoch 1 (6 steps per epoch)
    resumed = _run(str(tmp_path / "b"), resume=True)
    assert set(straight) == set(resumed)
    for n in straight:
        assert torch.equal(straight[n], resumed[n]), n
    assert _run(str(tmp_path / "c"), stop_after=6) is None       # stops exactly at the epoch boundary
    again = _run(str(tmp_path / "c"), resume=True)
    assert all(torch.equal(straight[n], again[n]) for n in straight)


def test_resume_without_rng_restore_differs(tmp_path, monkeypatch):
    """Guard that the check is sensitive: dropping the RNG restore changes the result (dropout stream)."""
    straight = _run(str(tmp_path / "a"))
    _run(str(tmp_path / "b"), stop_after=3)
    monkeypatch.setattr(ckpt, "set_rng_state", lambda s: None)
    torch.manual_seed(999)
    resumed = _run(str(tmp_path / "b"), resume=True)
    assert any(not torch.equal(straight[n], resumed[n]) for n in straight)


def test_layout_change_refused(tmp_path):
    _run(str(tmp_path / "b"), stop_after=3)
    m = _model()
    opt = torch.optim.AdamW(m.parameters(), lr=1e-2)
    with pytest.raises(ValueError, match="layout"):
        ckpt.load(str(tmp_path / "b"), m, opt, dict(LAYOUT, world=2))
