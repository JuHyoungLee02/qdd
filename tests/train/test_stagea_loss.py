import math
import random
from types import SimpleNamespace

import pytest

from harvest.clients.jevl import option_probs, option_trie
from harvest.train import stagea_loss as SL

END = 3
TOK = {"plus_x": [5, 6], "plus_x_plus_y": [5, 6, 7, 8], "plus_y": [5, 8], "minus_x": [9, 6], "none_xy": [10],
       "NONE_ESCALATE": [11, 12, 13]}


def test_cover_reaches_every_branching_node_with_few_sequences():
    trie = option_trie(TOK, END)
    names, where = SL.cover(TOK, trie)
    assert set(where) == set(trie)
    for pre, (s, d) in where.items():
        assert tuple(TOK[names[s]][:d]) == pre and d == len(pre)
    assert names == ["plus_x"]  # (5,6) is the only deep branching node; its path also covers () and (5,)


def test_cover_distinct_first_tokens_is_one_sequence():
    tok = {"up": [1], "down": [2], "none_z": [4, 5], "NONE_ESCALATE": [6, 7]}
    names, where = SL.cover(tok, option_trie(tok, END))
    assert len(names) == 1 and where == {(): (0, 0)}


def _rand_tok(rng, n, vocab=40):
    tok = {}
    while len(tok) < n:
        ids = [rng.randrange(4, vocab) for _ in range(rng.randint(1, 4))]
        if tuple(ids) not in {tuple(v) for v in tok.values()}:
            tok[f"n{len(tok)}"] = ids
    return tok


def test_cover_random_tries():
    rng = random.Random(0)
    for _ in range(200):
        tok = _rand_tok(rng, rng.randint(2, 10), vocab=rng.choice([8, 40]))
        trie = option_trie(tok, END)
        names, where = SL.cover(tok, trie)
        assert set(where) == set(trie)
        for pre, (s, d) in where.items():
            assert tuple(tok[names[s]][:d]) == pre
