"""E-SR1e training option (harvest/train/sr1e.py): the chunked branch loss equals the one-pass loss when one piece
covers the batch, and is the valid-weighted mean of the piece losses otherwise; options off -> E-SR1d parser."""
import pytest

torch = pytest.importorskip("torch")

from harvest.train import sr1c, sr1e  # noqa: E402


class _Exp(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.w = torch.nn.Parameter(torch.tensor(0.5))

    def forward(self, cond, x, t):
        return self.w * x + cond["b"][:, None, None]


class _M:
    def __init__(self):
        self.expert = _Exp()

    def forward_shared(self, bs, enc, device, grad=False):
        return torch.tensor([[float(s["v"])] for s in bs]), None, None

    def targets(self, bs, device):
        a = torch.stack([torch.full((5, 8), float(s["v"])) for s in bs])
        valid = torch.tensor([s["valid"] for s in bs], dtype=torch.float32)
        return a, valid, 0.0

    def cond(self, bs, ctx, mask, device):
        return {"b": ctx[:, 0] * 0.1}


def _bs(n, short=()):
    return [{"v": i / 10, "valid": [1, 1, 1, 0, 0] if i in short else [1] * 5} for i in range(n)]


def test_one_piece_equals_default():
    m, bs = _M(), _bs(8)
    torch.manual_seed(3)
    a = sr1c.fm_branch_default(m, bs, None, "cpu")
    torch.manual_seed(3)
    b = sr1e.fm_branch_chunked(m, bs, None, "cpu", size=8)
    assert torch.allclose(a, b)


def test_pieces_are_valid_weighted():
    m, bs = _M(), _bs(24, short=(1, 9))
    torch.manual_seed(5)
    got = sr1e.fm_branch_chunked(m, bs, None, "cpu", size=8)
    torch.manual_seed(5)
    parts = [sr1c.fm_branch_default(m, bs[i:i + 8], None, "cpu") for i in range(0, 24, 8)]
    w = [sum(sum(s["valid"]) for s in bs[i:i + 8]) for i in range(0, 24, 8)]
    want = sum(p * x for p, x in zip(parts, w)) / sum(w)
    assert torch.allclose(got, want)
    got.backward()
    assert m.expert.w.grad is not None


def test_parser_default_off():
    ap = sr1e.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    p = sub.choices["train"]
    assert p.get_default("sr1e_branch_chunk") == 0 and p.get_default("sr1d_frac") == 0.0
