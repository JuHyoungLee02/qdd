"""R7 cycle 9 N1 (canon §74): Holm step-down in the pre-registered direction. Judgment 2 ("LA-2 또는 C2''가 newest보다
+2%p 이상(하한 > 0)", E §2A.6-2) and the canary ("불일치가 바닥보다 유의하게 크면(하한 > 0, Holm)", E §1.8) are
directional: a hypothesis significant in the opposite direction is not a rejection and does not release the next
step's level. Judgment 10 ("시간 블록 사이 차이가 유의하면", E §2A.6-10; pair order is arbitrary) stays two-sided."""
import pytest

from harvest.analysis.stats import holm_ci


def _ci(table):
    """table: {name: [(level, (lo, hi)), ...]} -> the interval of the smallest listed level >= the asked one."""
    def ci_at(k, level):
        for L, iv in sorted(table[k]):
            if L >= level - 1e-12:
                return iv
        raise AssertionError(level)
    return ci_at


# neg: significantly negative at every level; pos: lower > 0 at 95 % only (not at 97.5 %)
_T = {"neg": [(0.95, (-0.3, -0.2)), (0.975, (-0.31, -0.19))],
      "pos": [(0.95, (0.01, 0.2)), (0.975, (-0.01, 0.21))]}


def test_two_sided_holm_counts_the_negative_rejection():
    r = holm_ci(_ci(_T), ["neg", "pos"])
    assert r["neg"]["reject"] and r["pos"]["reject"] and r["pos"]["level"] == pytest.approx(0.95)


def test_directional_holm_ignores_the_opposite_direction():
    r = holm_ci(_ci(_T), ["neg", "pos"], direction="greater")
    assert not r["neg"]["reject"] and not r["pos"]["reject"]
    assert r["pos"]["level"] == pytest.approx(0.975) and r["pos"]["lo"] == -0.01


def test_direction_is_validated():
    with pytest.raises(ValueError):
        holm_ci(_ci(_T), ["neg", "pos"], direction="less")


def test_judgment2_negative_c2pp_does_not_release_la2():
    """Reviewer hand_checks.py A3: C2'' gain significantly NEGATIVE; two-sided Holm then tested LA-2 at 95 % -> keep_a."""
    from harvest.analysis.replay import judge_e05
    from harvest.eval import e05

    from .test_r7c8_prereg import _LA2
    la2 = {("P0", s): v for s, v in enumerate(_LA2)}
    c2n = {c: [-1] * 5 + [0] * 5 for c in la2}
    h = e05.gain_holm(la2, c2n)
    assert not h["c2pp"]["reject"] and not h["la2"]["reject"] and h["la2"]["level"] == pytest.approx(0.975)
    g = sum(x for v in _LA2 for x in v) / sum(len(v) for v in _LA2)
    assert judge_e05({"flip_rate_success": 0.2, "gain_la2": g, "gain_c2pp": -0.5, "gain_holm": h})["claim"] != "keep_a"


def test_canary_below_floor_questions_do_not_release_level():
    """Reviewer C4: 4 questions with 0 mismatch (significantly BELOW the floor 0.5) and dir_xy with lower > 0 at 95 %
    but not at 99 % (step 1 of 5 questions): two-sided Holm reached dir_xy at 95 % -> drift; directional -> none."""
    from harvest.canary import canary_compare
    shares = (0, 2, 3, 4, 4, 4, 4, 4)
    base, today = {}, {}
    for s in range(8):
        k = f"P0_ep{s}_k3"
        base[f"{k}|dir_xy"], today[f"{k}|dir_xy"] = ["a"] * 4, ["b"] * shares[s] + ["a"] * (4 - shares[s])
        for q in ("dir_z", "mag_coarse", "target", "phase"):
            base[f"{k}|{q}"], today[f"{k}|{q}"] = ["a"] * 4, ["a"] * 4
    r = canary_compare(base, today, floor=0.5, n_boot=2000)
    assert not r["drift_suspect"]
    assert not any(v["reject"] for v in r["per_question"].values())
    assert r["per_question"]["dir_xy"]["level"] == pytest.approx(0.99)
    one = canary_compare({k: v for k, v in base.items() if k.endswith("dir_xy")},
                         {k: v for k, v in today.items() if k.endswith("dir_xy")}, floor=0.5, n_boot=2000)
    assert one["drift_suspect"]  # alone (m = 1, 95 %) it is significant


def test_judgment10_stays_two_sided():
    from harvest.eval import e05
    lo_blk = {i: [0] * 10 for i in range(20)}
    hi_blk = {i: [1] * 5 + [0] * 5 for i in range(20)}
    r = e05.block_diff_holm([hi_blk, lo_blk], n=500)  # block 1 - block 0 is negative: still a block effect
    assert r["any"] and r["pairs"]["0-1"]["reject"] and r["pairs"]["0-1"]["hi"] < 0
