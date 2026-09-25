"""E0.5 comparison rules and pre-registered judgments (E §2A.3, §2A.6).

Votes: [{"t_req": request time relative to the decision boundary (s, negative), "key": option_key}].
"""
from collections import Counter

from ..runtime.m4 import GAMMA, share_at_least
from .stats import above, at_least, below


def newest(votes):
    """C2 (Slow Brain VLM Stream): newest valid vote by request time."""
    return max(votes, key=lambda v: v["t_req"])["key"]


def la2(votes, gamma=GAMMA):
    """C3 consensus: modal key if ≥2 agree and share ≥ γ (γ=0.67 = 2/3 exactly, the runtime ledger's
    m4.share_at_least, canon §74); else first vote."""
    k, n = Counter(v["key"] for v in votes).most_common(1)[0]
    if n >= 2 and share_at_least(n, len(votes), gamma):
        return k
    return min(votes, key=lambda v: v["t_req"])["key"]


def c2pp(votes, half_life=0.33):
    """C2'' (our variant): age-decayed weighted mode."""
    w = Counter()
    for v in votes:
        w[v["key"]] += 0.5 ** (-v["t_req"] / half_life)
    return w.most_common(1)[0][0]


def judge_e05(r):
    """r["gain_holm"] = {"la2" | "c2pp": {"reject", "lo", ...}}: judgment 2's two conditions under Holm (E §1.7 "한
    판정에 여러 조건을 걸면 Holm", e05.gain_holm; canon §73). Judgments 1 and 3 read the point gains. Inputs are the
    unrounded statistics; every threshold is compared as worded (≥ / < / >) with stats.CMP_EPS (canon §74)."""
    out = {}
    flip = r["flip_rate_success"]
    gain = {"la2": r["gain_la2"], "c2pp": r["gain_c2pp"]}
    h = r["gain_holm"]
    sig_gain = any(at_least(g, 0.02) and h[k]["reject"] and above(h[k]["lo"], 0) for k, g in gain.items())
    small_gain = all(below(g, 0.02) for g in gain.values())
    if below(flip, 0.05) and small_gain:
        out["claim"] = "narrow_to_b"  # judgment 1
    elif at_least(flip, 0.05) and sig_gain:
        out["claim"] = "keep_a"  # judgment 2
    elif at_least(flip, 0.05) and small_gain:
        out["claim"] = "a_as_stabilizer"  # judgment 3
    else:
        out["claim"] = "undecided"  # not covered by judgments 1-3; reported as-is, no new rule
    if "perturb_flip" in r:  # judgment 4
        au = r["auroc"]
        best = max(au, key=au.get)
        out["c_flip_keep"] = at_least(r["perturb_flip"], 2 * flip) and at_least(au[best], 0.7)
        others = [v for k, v in au.items() if k != best]
        out["c_flip_default"] = best if others and at_least(au[best] - max(others), 0.03) else "tv_distance"
    if "same_time_flip" in r:  # judgment 6
        out["c5a3_caveat"] = below(r["same_time_flip"], 0.01)
    if "layers" in r:  # judgment 9
        out["name_rule"] = {}
        for layer, d in r["layers"].items():
            if at_least(d["a1_minus_a0_lo"], -0.02) and above(d["a3_follow_minus_floor_lo"], 0):
                out["name_rule"][layer] = "neutral"
            elif above(d["a0_minus_a1_lo"], 0):
                out["name_rule"][layer] = "keep"
            else:
                out["name_rule"][layer] = "undecided"
        out["c3pp_required"] = any(at_least(d["a4_flip"], 0.05) for d in r["layers"].values())
    if "block_diff_lo" in r:  # judgment 10
        out["time_block_effect"] = above(r["block_diff_lo"], 0)
    return out
