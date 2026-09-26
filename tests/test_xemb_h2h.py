from collections import Counter

from tools.xemb.prep_h2h import alloc, generic_name, strat_take


def test_generic_name_rows_are_dropped():
    assert generic_name({"answer": "{\"currently_attempting\": \"lower to the object and close on it\"}"})
    assert not generic_name({"answer": "{\"currently_attempting\": \"lower to the red mug and close on it\"}"})


def test_alloc_fills_shortfall_to_exact_n():
    q = alloc([1000, 1000, 100], [0.45, 0.35, 0.20], 2000)
    assert q[2] == 100 and sum(q) == 2000 and q[0] <= 1000 and q[1] <= 1000
    assert alloc([5000, 5000, 5000], [0.5, 0.15, 0.35], 2000) == [1000, 300, 700]


def test_strat_take_proportional_and_exact():
    rows = [{"step": "a", "i": i} for i in range(600)] + [{"step": "b", "i": i} for i in range(300)] + \
        [{"step": "c", "i": i} for i in range(100)]
    got = strat_take(rows, 101)
    assert len(got) == 101
    c = Counter(r["step"] for r in got)
    assert c["a"] in (60, 61) and c["b"] in (30, 31) and c["c"] in (10, 11)


def test_strat_take_same_seed_same_rows():
    rows = [{"step": s, "i": i} for i, s in enumerate("abc" * 50)]
    assert strat_take(rows, 40) == strat_take(rows, 40)
