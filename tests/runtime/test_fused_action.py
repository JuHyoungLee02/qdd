"""FusedModel action path: chunk read-out at 100 Hz and the CUDA-graphed expert sampler."""
import numpy as np
import pytest

from harvest.runtime.fused_action import chunk_value


def test_chunk_value_linear_and_held():
    c = np.array([[0.0] * 8, [3.0] * 8, [6.0] * 8])
    dt = 1 / 30
    assert chunk_value(c, dt, 1.0, 0.9)[0] == 0.0
    assert chunk_value(c, dt, 1.0, 1.0 + dt / 2)[0] == pytest.approx(1.5)
    assert chunk_value(c, dt, 1.0, 5.0)[0] == 6.0


def _expert(torch):
    from harvest.train.stageb_expert import ActionExpert, ExpertConfig
    torch.manual_seed(0)
    return ActionExpert(ExpertConfig(ctx_dim=32, proprio_dim=23, width=32, depth=2, heads=4)).eval()


def _cond(torch, T, dev="cpu"):
    g = torch.Generator().manual_seed(1)
    return {"ctx": torch.randn(1, T, 32, generator=g).to(dev), "ctx_mask": torch.ones(1, T, dtype=torch.long).to(dev),
            "proprio": torch.randn(1, 23, generator=g).to(dev), "skill": torch.tensor([1]).to(dev),
            "phase": torch.tensor([2]).to(dev), "dec": torch.tensor([[1, 2, 3, 4, 5]]).to(dev)}


def test_padding_is_invisible_to_the_expert():
    torch = pytest.importorskip("torch")
    from harvest.runtime.fused_action import GraphedSampler
    from harvest.train.stageb_expert import sample_actions
    ex = _expert(torch)
    cond = _cond(torch, 17)
    noise = torch.randn(1, 15, 8, generator=torch.Generator().manual_seed(2))
    ref = sample_actions(ex, cond, 10, noise)
    got = GraphedSampler(ex, T_max=64)(cond, noise)  # CPU: eager on the padded context
    assert torch.allclose(ref, got, atol=1e-5)


def test_cuda_graph_matches_eager():
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("no CUDA")
    from harvest.runtime.fused_action import GraphedSampler
    from harvest.train.stageb_expert import sample_actions
    ex = _expert(torch).cuda()
    gs = GraphedSampler(ex, T_max=64)
    for T, seed in ((17, 2), (40, 3)):  # replay with different context lengths and noise
        cond = _cond(torch, T, "cuda")
        noise = torch.randn(1, 15, 8, generator=torch.Generator().manual_seed(seed)).cuda()
        ref = sample_actions(ex, cond, 10, noise)
        assert torch.allclose(ref, gs(cond, noise), atol=1e-4)
    assert gs.graph is not None
