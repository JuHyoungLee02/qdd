"""Torch part of the stage-A loss tests (CPU, mocked causal LM): training log-prob == jevl.py inference log-prob."""
import math
import random
from types import SimpleNamespace

import pytest

from harvest.clients.jevl import option_probs, option_trie
from harvest.train import stagea_loss as SL

from .test_stagea_loss import END, TOK, _rand_tok

torch = pytest.importorskip("torch")


class CausalMock(torch.nn.Module):
    """Stand-in LM: logits at position t depend only on tokens <= t (cumulative-sum state)."""

    def __init__(self, vocab=48, hidden=16, seed=0):
        super().__init__()
        g = torch.Generator().manual_seed(seed)
        self.emb = torch.nn.Parameter(torch.randn(vocab, hidden, generator=g, dtype=torch.float64))
        self.head = torch.nn.Parameter(torch.randn(hidden, vocab, generator=g, dtype=torch.float64) * 3)
        self.calls = []

    def forward(self, input_ids, attention_mask=None, logits_to_keep=0, pixel_values=None, **kw):
        self.calls.append({"input_ids": input_ids, "attention_mask": attention_mask, "pixel_values": pixel_values,
                           **kw})
        h = torch.tanh(torch.cumsum(self.emb[input_ids], dim=1))
        logits = h @ self.head
        if logits_to_keep:
            logits = logits[:, -logits_to_keep:]
        return SimpleNamespace(logits=logits)


def _inference_probs(model, prompt, tok, trie):
    """jevl.py path: one pass per branching node on prompt + prefix, raw full-vocab logprobs of the children."""
    node_lp = {}
    for pre, kids in trie.items():
        ids = torch.tensor([prompt + list(pre)])
        lp = torch.log_softmax(model(ids).logits[0, -1], -1)
        node_lp[pre] = {c: float(lp[c]) for c in kids}
    return option_probs(tok, trie, node_lp, END)


def _inputs(prompt):
    return {"input_ids": torch.tensor([prompt]), "attention_mask": torch.ones(1, len(prompt), dtype=torch.long),
            "pixel_values": torch.randn(6, 4, dtype=torch.float64), "image_grid_thw": torch.tensor([[1, 2, 3]])}


@pytest.mark.parametrize("seed", range(5))
def test_training_logprobs_equal_jevl_inference_logprobs(seed):
    rng = random.Random(seed)
    model = CausalMock(seed=seed)
    for tok in [TOK] + [_rand_tok(rng, rng.randint(2, 10), vocab=rng.choice([8, 40])) for _ in range(20)]:
        trie = option_trie(tok, END)
        prompt = [rng.randrange(4, 48) for _ in range(rng.randint(3, 12))]
        p_inf = _inference_probs(model, prompt, tok, trie)
        lp = SL.item_logprobs(model, _inputs(prompt), tok, trie, END, pad_id=0)
        assert list(lp) == list(tok)
        for n in tok:
            assert math.isclose(float(lp[n].exp()), p_inf[n], rel_tol=1e-9, abs_tol=1e-12), (n, tok)
            assert math.isclose(float(lp[n]), math.log(p_inf[n]), rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(sum(float(v.exp()) for v in lp.values()), 1.0, rel_tol=1e-9)


def test_option_logprobs_from_node_logits_match_option_probs():
    trie = option_trie(TOK, END)
    g = torch.Generator().manual_seed(1)
    logits = {pre: torch.randn(48, generator=g, dtype=torch.float64) * 4 for pre in trie}
    lp = SL.option_logprobs(logits, TOK, trie, END)
    node_lp = {pre: {c: float(torch.log_softmax(v, -1)[c]) for c in trie[pre]} for pre, v in logits.items()}
    ref = option_probs(TOK, trie, node_lp, END)
    for n in TOK:
        assert math.isclose(float(lp[n].exp()), ref[n], rel_tol=1e-12)


def test_batch_extends_token_tensors_and_repeats_image_tensors():
    inp = _inputs([7, 8, 9])
    inp["mm_token_type_ids"] = torch.tensor([[0, 1, 0]])
    b, keep = SL.batch_inputs(inp, [[5, 6], [9]], pad_id=0)
    assert b["input_ids"].tolist() == [[7, 8, 9, 5, 6], [7, 8, 9, 9, 0]]
    assert b["attention_mask"].tolist() == [[1, 1, 1, 1, 1], [1, 1, 1, 1, 0]]
    assert b["mm_token_type_ids"].tolist() == [[0, 1, 0, 0, 0], [0, 1, 0, 0, 0]]
    assert b["pixel_values"].shape == (12, 4) and b["image_grid_thw"].tolist() == [[1, 2, 3], [1, 2, 3]]
    assert keep == 3


def test_set_nll_single_and_multi_target():
    lp = {"a": torch.log(torch.tensor(0.5, dtype=torch.float64)),
          "b": torch.log(torch.tensor(0.3, dtype=torch.float64)),
          "c": torch.log(torch.tensor(0.2, dtype=torch.float64))}
    assert math.isclose(float(SL.set_nll(lp, ["b"])), -math.log(0.3), rel_tol=1e-12)
    assert math.isclose(float(SL.set_nll(lp, ["a", "c"])), -math.log(0.7), rel_tol=1e-12)
    with pytest.raises(ValueError):
        SL.set_nll(lp, [])


def test_loss_gradient_flows_and_decreases_with_sgd():
    model = CausalMock(seed=3)
    trie = option_trie(TOK, END)
    prompt = [4, 20, 30, 40]
    opt = torch.optim.SGD(model.parameters(), lr=0.05)
    losses = []
    for _ in range(30):
        loss = SL.set_nll(SL.item_logprobs(model, _inputs(prompt), TOK, trie, END, pad_id=0), ["plus_x_plus_y"])
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(float(loss))
    assert losses[-1] < losses[0] * 0.5
