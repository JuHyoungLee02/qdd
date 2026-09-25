"""E0.5 offline replay (E §2A, canon §28 J3, §59) -- one command.

  python -m harvest.eval.e05 --model <merged dir | adapter dir | zero-shot> --out DIR --data DIR[,DIR] --split pool|dev \
      [--episodes N] [--variants A0,A1,A2,A3,A4] [--same-k 3] [--blocks 2] [--floor-n 0] [--d-p95 0.307] \
      [--truth labels_v2 | outcome:<rule>] [--gpu 3 | --url URL --served-name NAME]

Data = episode folders of continuous 0.33 s snapshots (POOL `data/pool`, DEV `data/jsel_dev/P0` ...; ep<seed>.jsonl +
ep<seed>.meta.json + img/). Per snapshot the model (vLLM, call mode lead, §59) is asked the 5 DecCall decision
questions (S1 1 mm state, §54) as follows:
  A0 x K concurrently (same-time repeat, K = --same-k; the first answer is the snapshot's vote),
  A1..A4 once each (option-name variants, canon §27, options.variant),
  then --blocks time blocks, each asking the floor subset twice in sequence (test-retest floor (ii), per layer x
  block, canon §28); the first block's first answer vs the vote = the one-shot retest (judgment 5).
Replay: decision step k starts at t_k; its votes are the 3 newest snapshots with t <= t_k - d_p95 (§2A.3). Rules
newest (C2) / LA-2 gamma 0.67 / C2'' (age-decayed mode) / C2' (Slow Brain Probability Fusion, S1 = the labels_v2 code
rule on the step's S1 text, Sim = code expected displacement, M4 §5) / C2'-S (Score Fusion) / S1 alone, scored against
labels_v2 of the step snapshot (or the outcome labels' best set under a pre-registered rule). Then judge_e05
(judgments 1-4, 6, 9, 10) plus 5, 7, 8 computed here. Episode-cluster bootstrap CIs.
Output: <out>/e05.json, <out>/e05.md, raw answers <out>/calls.jsonl (resumable).
"""
from __future__ import annotations

import math
import time
from collections import Counter

import numpy as np

from ..analysis.replay import c2pp, judge_e05, la2, newest  # noqa: F401  (judge_e05 re-exported for main)
from ..analysis.stats import N_BOOT, above, at_least, cluster_diff_ci, cluster_mean_ci, holm_ci
from ..runtime.m4 import GAMMA, share_at_least

T_C = 0.33
NE = "NONE_ESCALATE"
# Slow Brain Probability / Score Fusion (M4 §5 C2', C2'-S; original real-robot values, Table 6)
LAMBDA_P, LAMBDA_S, TAU_S, T_VLM, TIMEOUT_S = 3.0, 1.0, 5.0, 1.0, 5.0
_XYV = {"plus_x": (1, 0), "minus_x": (-1, 0), "plus_y": (0, 1), "minus_y": (0, -1), "plus_x_plus_y": (1, 1),
        "plus_x_minus_y": (1, -1), "minus_x_plus_y": (-1, 1), "minus_x_minus_y": (-1, -1), "none_xy": (0, 0)}
_ZV = {"up": 1.0, "down": -1.0, "none_z": 0.0}
_MAGV = {"tiny": 0.005, "small": 0.01, "medium": 0.02, "large": 0.04, "xlarge": 0.08}


# ------------------------------------------------------------------------------------------ replay geometry
def vote_steps(t_of: dict, d_p95: float, n_votes: int = 3):
    """t_of: {k: t} of one episode's continuous snapshots. -> [(k_step, [(k_vote, t_vote - t_step)] newest first)]
    for every step whose n_votes newest snapshots with t <= t_step - d_p95 exist. On the 0.33 s grid these are the
    request times of the runtime's H = 1 early asks (runtime.m4.early_ask_steps) for lead_max in
    [d_p95 + 2 T_c, d_p95 + 3 T_c), e.g. the default 1.0 s at d_p95 0.307 (canon §75; test_r7c10_prereg)."""
    ks = sorted(t_of)
    out = []
    for k in ks:
        cut = t_of[k] - d_p95 + 1e-9
        prior = [j for j in ks if t_of[j] <= cut]
        if len(prior) < n_votes:
            continue
        vs = sorted(prior, reverse=True)[:n_votes]
        out.append((k, [(j, round(t_of[j] - t_of[k], 6)) for j in vs]))
    return out


def apply_rules(votes) -> dict:
    """votes: [{"t_req", "key"}]. newest / LA-2 (with whether consensus was reached) / C2''."""
    k, n = Counter(v["key"] for v in votes).most_common(1)[0]
    confirmed = n >= 2 and share_at_least(n, len(votes), GAMMA)  # γ 0.67 = 2/3 exactly (canon §74)
    return {"newest": newest(votes), "la2": la2(votes), "la2_confirmed": bool(confirmed), "c2pp": c2pp(votes)}


def same_time_flip(keys) -> bool:
    m = Counter(keys).most_common(1)[0][0]
    return any(k != m for k in keys)


def successive_flips(seq) -> list:
    return [int(a != b) for a, b in zip(seq, seq[1:])]


def c_flip_tv(cur, prev) -> float:
    """(i) total-variation distance between this step's vote distribution and the previous step's (00 §12)."""
    a, b = Counter(cur), Counter(prev)
    return 0.5 * sum(abs(a[k] / len(cur) - b[k] / len(prev)) for k in set(a) | set(b))


def c_flip_one(votes_newest_first) -> float:
    """(ii) one-answer-vs-one-answer flip share over time-adjacent vote pairs of the step."""
    f = successive_flips(list(votes_newest_first))
    return float(np.mean(f)) if f else 0.0


# ------------------------------------------------------------------------------------------ C2' / C2'-S
def _vec(q: str, key: str):
    if q == "dir_xy" and key in _XYV:
        x, y = _XYV[key]
        n = math.hypot(x, y)
        return np.array([x / n, y / n]) if n else np.zeros(2)
    if q == "dir_z" and key in _ZV:
        return np.array([_ZV[key]])
    if q == "mag_coarse" and key in _MAGV:
        return np.array([_MAGV[key]])
    return None


def sim_scores(q: str, opts, vlm_key: str) -> dict:
    """Sim(option, late vote): geometric questions -||e_i - e_vlm|| / d_scale with d_scale = mean pairwise distance of
    the question's geometric options [가정, M4 §5 "보기 간 평균 거리"]; non-geometric options (target, phase,
    NONE_ESCALATE) 1 if the same id else 0 (M4 §5 our extension); a geometric option vs NONE_ESCALATE = -max
    distance / d_scale."""
    vecs = {o: _vec(q, o) for o in opts}
    geo = [v for v in vecs.values() if v is not None]
    if len(geo) < 2:
        return {o: 1.0 if o == vlm_key else 0.0 for o in opts}
    d = [float(np.linalg.norm(a - b)) for i, a in enumerate(geo) for b in geo[i + 1:]]
    scale, dmax = float(np.mean(d)) or 1.0, max(d)
    ev = vecs.get(vlm_key)
    out = {}
    for o, v in vecs.items():
        if o == vlm_key:
            out[o] = 0.0
        elif v is None or ev is None:
            out[o] = -dmax / scale
        else:
            out[o] = -float(np.linalg.norm(v - ev)) / scale
    return out


def _softmax(x: dict, T: float = 1.0) -> dict:
    m = max(x.values())
    e = {k: math.exp((v - m) / T) for k, v in x.items()}
    s = sum(e.values())
    return {k: v / s for k, v in e.items()}


def s1_logits(opts, s1_key) -> dict:
    """S1 = the fast layer's code-rule score: 1 for the rule's option, 0 otherwise [가정: one-hot rule score]."""
    return {o: 1.0 if o == s1_key else 0.0 for o in opts}


def c2prime_probs(q: str, opts, s1_key, vlm_key, dt: float) -> dict:
    """C2' (Slow Brain Probability Fusion, streaming): p = (1-a) softmax(S1) + a softmax(Sim / T_vlm),
    a = l/(l+1) exp(-dt/tau), a = 0 past the 5 s timeout."""
    a = 0.0 if dt > TIMEOUT_S else LAMBDA_P / (LAMBDA_P + 1) * math.exp(-dt / TAU_S)
    p1, p2 = _softmax(s1_logits(opts, s1_key)), _softmax(sim_scores(q, opts, vlm_key), T_VLM)
    return {o: (1 - a) * p1[o] + a * p2[o] for o in opts}


def c2prime_score_choice(q: str, opts, s1_key, vlm_key, dt: float) -> str:
    """C2'-S (Score Fusion, lambda 1): argmax S1 + lambda exp(-dt/tau) Sim (first option wins ties)."""
    w = 0.0 if dt > TIMEOUT_S else LAMBDA_S * math.exp(-dt / TAU_S)
    s1, sim = s1_logits(opts, s1_key), sim_scores(q, opts, vlm_key)
    return max(opts, key=lambda o: s1[o] + w * sim[o])


def argmax_first(p: dict, opts) -> str:
    return max(opts, key=lambda o: p[o])


# ------------------------------------------------------------------------------------------ variants / windows
def name_meaning(a0_opts) -> dict:
    """{A0 shown name: option_key} -- the original meaning of a name (A3 name-following)."""
    return {o.name: o.key for o in a0_opts}


def in_perturb_window(t_step: float, events_t, win: float = 1.0) -> bool:
    """Step starting in (t_event, t_event + win] [가정: window 1 s after the perturbation]."""
    return any(te < t_step <= te + win + 1e-9 for te in events_t)


# ------------------------------------------------------------------------------------------ statistics helpers
def mean_ci(by_cluster: dict, n: int = N_BOOT) -> dict:
    vals = [x for v in by_cluster.values() for x in v]
    if not vals:
        return {"mean": None, "ci": [None, None], "n": 0}
    lo, hi = cluster_mean_ci(by_cluster, n=n)
    return {"mean": round(float(np.mean(vals)), 4), "ci": [round(lo, 4), round(hi, 4)], "n": len(vals)}


def diff_ci(a: dict, b: dict, n: int = N_BOOT) -> dict:
    va = [x for v in a.values() for x in v]
    vb = [x for v in b.values() for x in v]
    if not va or not vb:
        return {"mean": None, "ci": [None, None], "n": [len(va), len(vb)]}
    lo, hi = cluster_diff_ci(a, b, n=n)
    return {"mean": round(float(np.mean(va) - np.mean(vb)), 4), "ci": [round(lo, 4), round(hi, 4)],
            "n": [len(va), len(vb)]}


def _mean_x(by_cluster: dict):
    """Unrounded mean (judgment input; mean_ci's 4 dp are for display, canon §74)."""
    vals = [x for v in by_cluster.values() for x in v]
    return float(np.mean(vals)) if vals else None


def _lo_x(by_cluster: dict, n: int):
    """Unrounded 95 % lower bound (the same draws as mean_ci)."""
    return cluster_mean_ci(by_cluster, n=n)[0] if any(by_cluster.values()) else None


def _diff_lo_x(a: dict, b: dict, n: int):
    """Unrounded 95 % lower bound of mean(a) - mean(b) (the same draws as diff_ci)."""
    return cluster_diff_ci(a, b, n=n)[0] if any(a.values()) and any(b.values()) else None


def block_diff_lo(blocks, n: int = N_BOOT) -> float:
    """Judgment 10: blocks = [ {cluster: [flip 0/1]} per time block ]. For every block pair the CI of the floor
    difference at level 1 - 0.05/m; returns the largest signed lower bound max(lo, -hi). > 0 exactly when Holm
    rejects at least one pair (Holm's first step is this level), so it is the judgment-10 decision; which pairs
    differ is block_diff_holm (canon §72)."""
    pairs = [(i, j) for i in range(len(blocks)) for j in range(i + 1, len(blocks))]
    if not pairs:
        return float("nan")
    level = 1 - 0.05 / len(pairs)
    best = -float("inf")
    for i, j in pairs:
        lo, hi = cluster_diff_ci(blocks[j], blocks[i], n=n, level=level)
        best = max(best, lo, -hi)
    return float(best)


def gain_holm(gain_la2: dict, gain_c2pp: dict, n: int = N_BOOT, alpha: float = 0.05) -> dict:
    """Judgment 2 ("LA-2 또는 C2''" +2 pp, lower > 0; E §2A.6-2) with E §1.7 "한 판정에 여러 조건을 걸면 Holm": Holm
    step-down (stats.holm_ci) over the two paired gains vs newest (per-step differences, episode-cluster bootstrap,
    same draws at every level). {"la2" | "c2pp": {reject, lo, hi, level}} (canon §73). Directional ("하한 > 0"): a
    gain significantly below 0 is no rejection and does not release the other's level (canon §74)."""
    by = {"la2": gain_la2, "c2pp": gain_c2pp}
    r = holm_ci(lambda k, level: cluster_mean_ci(by[k], n=n, level=level), list(by), alpha, direction="greater")
    return {k: {"reject": bool(v["reject"]), "lo": float(v["lo"]), "hi": float(v["hi"]),  # unrounded: judge input
                "level": round(v["level"], 6)} for k, v in r.items()}


def block_diff_holm(blocks, n: int = N_BOOT, alpha: float = 0.05) -> dict:
    """Judgment 10 per block pair (E §2A.6-10 "블록 여러 개면 Holm"): Holm step-down (stats.holm_ci) over the
    pairwise floor differences, paired cluster bootstrap (cluster_diff_ci, same draws at every level)."""
    pairs = {f"{i}-{j}": (i, j) for i in range(len(blocks)) for j in range(i + 1, len(blocks))}
    r = holm_ci(lambda k, level: cluster_diff_ci(blocks[pairs[k][1]], blocks[pairs[k][0]], n=n, level=level),
                list(pairs), alpha)
    r = {k: {"reject": v["reject"], "lo": round(v["lo"], 4), "hi": round(v["hi"], 4), "level": round(v["level"], 6)}
         for k, v in r.items()}
    return {"pairs": r, "any": any(v["reject"] for v in r.values()), "alpha": alpha}


# ------------------------------------------------------------------------------------------ analysis
RULES = ("newest", "la2", "c2pp", "c2prime", "c2prime_s", "s1")
_STREAMS = ("succ", "pert", "la2_unconf", "gain_la2", "gain_c2pp", "c2p_minus_newest", "c2p_minus_la2")


def _layer(n_opts: int) -> str:
    from ..options import layer
    return layer(n_opts, "choice")


def _dd():
    from collections import defaultdict
    return defaultdict(list)


def _acc():
    d = {s: _dd() for s in _STREAMS}
    d["rules"] = {r: _dd() for r in RULES}
    return d


def _merge(dicts):
    m = _dd()
    for d in dicts:
        for c, v in d.items():
            m[c].extend(v)
    return m


def _q(xs, q):
    return round(float(np.quantile(xs, q)), 4) if xs else None


def analyze(eps, ans, truth, questions, d_p95: float, n_boot: int = N_BOOT, win: float = 1.0) -> dict:
    """eps: [{cluster, kind, seed, success, events_t, t: {k: t}}]; ans: {(kind, seed, k): {vote: {q: key},
    same: [{q: key}] (K same-time answers, first = vote), var: {A1..A4: {q: {key, name}}}, rt: {block: [{q: key},
    {q: key}]}, s1: {q: key} (code rule), opts: {q: [A0 option keys in shown order]}, names: {q: {key: A0 name}}}};
    truth: {(kind, seed, k): {q: set of correct keys}}. Returns the metrics, the judge_e05 input and the judgments."""
    from ..analysis.stats import auroc
    per_q = {q: _acc() for q in questions}
    pooled = _acc()
    step_rows = []  # (tv, one, in perturb window, success trajectory)
    for ep in eps:
        c, kind, seed = ep["cluster"], ep["kind"], ep["seed"]
        ks = sorted(k for k in ep["t"] if (kind, seed, k) in ans)
        succ_traj = kind == "P0" and ep["success"]
        for q in questions:  # successive-snapshot flips (H05-a, judgment 1-4)
            seq = [(k, ans[(kind, seed, k)]["vote"].get(q)) for k in ks]
            for (_, a0), (k1, a1) in zip(seq, seq[1:]):
                if a0 is None or a1 is None:
                    continue
                f = int(a0 != a1)
                if succ_traj:
                    tgt = "succ"
                elif kind != "P0" and in_perturb_window(ep["t"][k1], ep["events_t"], win):
                    tgt = "pert"
                else:
                    continue
                per_q[q][tgt][c].append(f)
                pooled[tgt][c].append(f)
        prev = None
        for k, vs in vote_steps({k: ep["t"][k] for k in ks}, d_p95):
            key = (kind, seed, k)
            tv, one, nq, cur = 0.0, 0.0, 0, {}
            for q in questions:
                keys = [ans[(kind, seed, kv)]["vote"].get(q) for kv, _ in vs]
                if any(x is None for x in keys):
                    continue
                cur[q] = keys
                if prev is not None and q in prev:
                    tv += c_flip_tv(keys, prev[q])
                    one += c_flip_one(keys)
                    nq += 1
                t = truth.get(key, {}).get(q)
                if t is None or key not in ans:
                    continue
                r = apply_rules([{"t_req": rel, "key": x} for (_, rel), x in zip(vs, keys)])
                opts, s1, dt = ans[key]["opts"][q], ans[key]["s1"].get(q), -vs[0][1]
                r["c2prime"] = argmax_first(c2prime_probs(q, opts, s1, r["newest"], dt), opts)
                r["c2prime_s"] = c2prime_score_choice(q, opts, s1, r["newest"], dt)
                r["s1"] = s1
                ok = {rn: int(r[rn] in t) for rn in RULES}
                for tgt in (per_q[q], pooled):
                    for rn in RULES:
                        tgt["rules"][rn][c].append(ok[rn])
                    tgt["la2_unconf"][c].append(int(not r["la2_confirmed"]))
                    tgt["gain_la2"][c].append(ok["la2"] - ok["newest"])
                    tgt["gain_c2pp"][c].append(ok["c2pp"] - ok["newest"])
                    tgt["c2p_minus_newest"][c].append(ok["c2prime"] - ok["newest"])
                    tgt["c2p_minus_la2"][c].append(ok["c2prime"] - ok["la2"])
            if nq:
                pw = kind != "P0" and in_perturb_window(ep["t"][k], ep["events_t"], win)
                step_rows.append((tv / nq, one / nq, pw, succ_traj))
            prev = cur
    # same-time K, retest, floors (layer x block), option-name variants per layer
    same, retest, floor, lay = _dd(), _dd(), {}, {}
    for key, a in ans.items():
        c = (key[0], key[1])
        for q in questions:
            v = a["vote"].get(q)
            if v is None:
                continue
            opts = a["opts"][q]
            L = _layer(len(opts))
            d = lay.setdefault(L, {n: _dd() for n in ("a0", "a1", "a2", "a3", "a4", "subst", "follow", "a4flip",
                                                      "a1_minus_a0", "first_pick", "first_true")})
            st = [x.get(q) for x in a.get("same", []) if x.get(q) is not None]
            if len(st) >= 2:
                same[c].append(int(same_time_flip(st)))
            rt = a.get("rt") or {}
            if rt:
                b0 = rt[min(rt)]
                if b0 and b0[0].get(q) is not None:
                    retest[c].append(int(b0[0][q] != v))
                for b, pair in rt.items():
                    if len(pair) >= 2 and pair[0].get(q) is not None and pair[1].get(q) is not None:
                        floor.setdefault(L, {}).setdefault(b, _dd())[c].append(int(pair[0][q] != pair[1][q]))
            t = truth.get(key, {}).get(q)
            d["first_pick"][c].append(int(v == opts[0]))
            if t is not None:
                d["first_true"][c].append(int(opts[0] in t))
                d["a0"][c].append(int(v in t))
            for vn in ("A1", "A2", "A3", "A4"):
                x = (a.get("var") or {}).get(vn, {}).get(q)
                if x is None or x.get("key") is None:
                    continue
                if t is not None:
                    d[vn.lower()][c].append(int(x["key"] in t))
                    if vn == "A1":
                        d["a1_minus_a0"][c].append(int(x["key"] in t) - int(v in t))
                if vn == "A1":
                    d["subst"][c].append(int(x["key"] != v))
                elif vn == "A3":
                    meaning = {nm: kk for kk, nm in a["names"][q].items()}
                    d["follow"][c].append(int(meaning.get(x.get("name")) == v))
                elif vn == "A4":
                    d["a4flip"][c].append(int(x["key"] != v))
    out = {"n_episodes": len(eps), "n_snapshots": len(ans), "n_steps": len(step_rows), "d_p95": d_p95,
           "perturb_window_s": win}
    out["flip"] = {"pooled": {"success": mean_ci(pooled["succ"], n_boot),
                              "perturb_window": mean_ci(pooled["pert"], n_boot)},
                   "per_question": {q: {"success": mean_ci(per_q[q]["succ"], n_boot),
                                        "perturb_window": mean_ci(per_q[q]["pert"], n_boot)} for q in questions}}

    def rules_block(src):
        r = {rn: mean_ci(src["rules"][rn], n_boot) for rn in RULES}
        r.update(la2_unconfirmed=mean_ci(src["la2_unconf"], n_boot),
                 la2_minus_newest=mean_ci(src["gain_la2"], n_boot),
                 c2pp_minus_newest=mean_ci(src["gain_c2pp"], n_boot),
                 c2prime_minus_newest=mean_ci(src["c2p_minus_newest"], n_boot),
                 c2prime_minus_la2=mean_ci(src["c2p_minus_la2"], n_boot))
        return r
    out["rules"] = {"pooled": rules_block(pooled), "per_question": {q: rules_block(per_q[q]) for q in questions}}
    out["same_time_flip"] = mean_ci(same, n_boot)
    out["retest_flip"] = mean_ci(retest, n_boot)
    blocks = sorted({b for L in floor.values() for b in L})
    fb = {b: _merge([floor[L][b] for L in floor if b in floor[L]]) for b in blocks}
    out["floor"] = {"pooled": mean_ci(_merge(list(fb.values())), n_boot),
                    "per_block": {str(b): mean_ci(fb[b], n_boot) for b in blocks},
                    "per_layer_block": {L: {str(b): mean_ci(v, n_boot) for b, v in floor[L].items()} for L in floor}}
    pw = [r for r in step_rows if r[2]]
    sw = [r for r in step_rows if r[3]]
    au = {}
    if pw and sw:
        lab = [1] * len(pw) + [0] * len(sw)
        au = {"tv_distance": auroc([r[0] for r in pw + sw], lab), "one_flip": auroc([r[1] for r in pw + sw], lab)}
    out["c_flip"] = {"auroc": au, "n_perturb_steps": len(pw), "n_success_steps": len(sw),
                     "flip_th_candidates": {f"q{1 - al:.2f}": {"tv_distance": _q([r[0] for r in sw], 1 - al),
                                                               "one_flip": _q([r[1] for r in sw], 1 - al)}
                                            for al in (0.05, 0.1)}}
    layers = {}
    for L, d in lay.items():
        fl = _merge(list(floor.get(L, {}).values()))
        layers[L] = {n: mean_ci(v, n_boot) for n, v in d.items()}
        layers[L]["floor"] = mean_ci(fl, n_boot)
        layers[L]["a0_minus_a1"] = mean_ci({c: [-x for x in v] for c, v in d["a1_minus_a0"].items()}, n_boot)
        layers[L]["follow_minus_floor"] = diff_ci(d["follow"], fl, n_boot)
        layers[L]["subst_minus_floor"] = diff_ci(d["subst"], fl, n_boot)
    out["layers"] = layers
    pr = out["rules"]["pooled"]
    # judgment inputs = the unrounded statistics (the rounded ones above are for display; canon §74)
    j = {"flip_rate_success": _mean_x(pooled["succ"]),
         "gain_la2": _mean_x(pooled["gain_la2"]), "gain_c2pp": _mean_x(pooled["gain_c2pp"]),
         "same_time_flip": _mean_x(same)}
    if pooled["gain_la2"] and pooled["gain_c2pp"]:  # judgment 2 decides on the Holm step-down (E §1.7, canon §73)
        j["gain_holm"] = gain_holm(pooled["gain_la2"], pooled["gain_c2pp"], n=n_boot)
    if au and None not in au.values() and out["flip"]["pooled"]["perturb_window"]["mean"] is not None:
        j["perturb_flip"], j["auroc"] = _mean_x(pooled["pert"]), au
    lj = {}
    for L, d in lay.items():
        if L not in layers:
            continue
        fl = _merge(list(floor.get(L, {}).values()))
        vals = (_lo_x(d["a1_minus_a0"], n_boot), _diff_lo_x(d["follow"], fl, n_boot),
                _lo_x({c: [-x for x in v] for c, v in d["a1_minus_a0"].items()}, n_boot), _mean_x(d["a4flip"]))
        if None not in vals:
            lj[L] = {"a1_minus_a0_lo": vals[0], "a3_follow_minus_floor_lo": vals[1], "a0_minus_a1_lo": vals[2],
                     "a4_flip": vals[3]}
    if lj:
        j["layers"] = lj
    if len(fb) >= 2:
        j["block_diff_lo"] = block_diff_lo([fb[b] for b in blocks], n=n_boot)
        out["floor"]["block_pairs_holm"] = block_diff_holm([fb[b] for b in blocks], n=n_boot)
    j = {k: v for k, v in j.items() if v is not None}
    out["judge_input"] = j
    needed = ("flip_rate_success", "gain_la2", "gain_c2pp", "gain_holm")
    jd = judge_e05(j) if all(k in j for k in needed) else {"claim": "insufficient_data"}
    fs, rf = j.get("flip_rate_success"), out["retest_flip"]["mean"]
    jd["j5_flip_minus_retest"] = None if fs is None or rf is None else round(fs - rf, 4)
    c2 = pr["c2prime_minus_la2"]
    c2m, c2lo = _mean_x(pooled["c2p_minus_la2"]), _lo_x(pooled["c2p_minus_la2"], n_boot)
    jd["j7_c2prime_strong_baseline"] = bool(c2m is not None and at_least(c2m, 0.02) and above(c2lo, 0))
    jd["j7_values"] = {"c2prime_minus_newest": pr["c2prime_minus_newest"], "c2prime_minus_la2": c2,
                       "s1_alone": pr["s1"]}
    j8 = {}
    for L, d in lay.items():
        if L in layers:
            lo8 = _diff_lo_x(d["subst"], _merge(list(floor.get(L, {}).values())), n_boot)
            j8[L] = bool(lo8 is not None and above(lo8, 0))
    jd["j8_subst_above_floor"] = j8
    if "gain_holm" in j:
        jd["j2_gain_holm"] = {"tests": j["gain_holm"], "alpha": 0.05,
                              "rule": "judgment 2 = flip >= 5% and some rule with gain >= 0.02 rejected by Holm "
                                      "with lower > 0 (E §1.7, §2A.6-2)"}
    if "block_pairs_holm" in out["floor"]:
        jd["j10_block_pairs_holm"] = out["floor"]["block_pairs_holm"]
    out["judgments"] = jd
    return out


# ------------------------------------------------------------------------------------------ command
def _args(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="python -m harvest.eval.e05", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="merged dir | adapter dir | zero-shot | mock")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", required=True, help="comma-separated episode folders")
    ap.add_argument("--split", required=True, help="dev | pool | cal | test | test_p5 (protected: env guard)")
    ap.add_argument("--episodes", type=int, default=0, help="first N episodes per folder (0 = all)")
    ap.add_argument("--seeds", default="", help="comma list / a-b ranges to keep")
    ap.add_argument("--variants", default="A0,A1,A2,A3,A4")
    ap.add_argument("--same-k", type=int, default=3)
    ap.add_argument("--blocks", type=int, default=2, help="time blocks of the test-retest floor (ii)")
    ap.add_argument("--floor-n", type=int, default=0, help="snapshots in the floor subset (0 = all)")
    ap.add_argument("--d-p95", type=float, default=0.307, help="E0 / stage-A p95 (M4Params.d_p95_init)")
    ap.add_argument("--truth", default="labels_v2", help="labels_v2 | outcome:<rule>")
    ap.add_argument("--outcome-dirs", default="", help="label row folders for --truth outcome:<rule>")
    ap.add_argument("--layout", default="auto", help="auto (training layout) | H | HW")
    ap.add_argument("--mode", default="lead")
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--gpu", default="3")
    ap.add_argument("--gpu-util", type=float, default=0.30)
    ap.add_argument("--url", default="")
    ap.add_argument("--served-name", default="")
    ap.add_argument("--perturb-window", type=float, default=1.0)
    ap.add_argument("--n-boot", type=int, default=N_BOOT, help="bootstrap draws (E §1.7: 10,000)")
    return ap.parse_args(argv)


def parse_seeds(s: str):
    if not s:
        return None
    out = set()
    for part in s.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


async def _collect(asker, eps, a, out_dir):
    """All calls (resumable via calls.jsonl): phase 1 = per snapshot A0 x K concurrently + A1..A4; phase 2 = time
    blocks of the floor subset, two sequential repeats each."""
    import asyncio
    import json
    import os
    import random
    from .common import run_pool
    path = os.path.join(out_dir, "calls.jsonl")
    done = {}
    if os.path.exists(path):
        for x in open(path, encoding="utf-8"):
            r = json.loads(x)
            done[(r["dir"], r["seed"], r["k"], r["tag"])] = r
    f = open(path, "a", encoding="utf-8")

    def rec(ep, ln, tag, res, block=None):
        r = {"dir": ep["dir"], "seed": ep["seed"], "kind": ep["kind"], "k": ln["k"], "tag": tag, "block": block,
             "utc_s": round(time.time(), 3), **res}
        done[(ep["dir"], ep["seed"], ln["k"], tag)] = r
        f.write(json.dumps(r) + "\n")

    snaps = [(ep, ln) for ep in eps for ln in ep["lines"]]
    variants = [v for v in a.variants.split(",") if v and v != "A0"]

    def phase1(ep, ln):
        async def go():
            tags = [f"A0#{i}" for i in range(a.same_k)]
            todo = [t for t in tags if (ep["dir"], ep["seed"], ln["k"], t) not in done]
            if todo:  # same-time repeat: the K calls of one snapshot are sent concurrently
                res = await asyncio.gather(*(asker.ask(ln, ep["dir"], "A0") for _ in todo))
                for t, r in zip(todo, res):
                    rec(ep, ln, t, r)
            for v in variants:
                if (ep["dir"], ep["seed"], ln["k"], v) not in done:
                    rec(ep, ln, v, await asker.ask(ln, ep["dir"], v))
        return go
    await run_pool([phase1(ep, ln) for ep, ln in snaps], a.conc)
    floor = list(snaps)
    if a.floor_n and a.floor_n < len(floor):
        floor = random.Random(0).sample(floor, a.floor_n)
    for b in range(a.blocks):
        def rt(ep, ln, b=b):
            async def go():
                for j in range(2):  # the two repeats of one block are sequential (not same-time)
                    t = f"rt{b}#{j}"
                    if (ep["dir"], ep["seed"], ln["k"], t) not in done:
                        rec(ep, ln, t, await asker.ask(ln, ep["dir"], "A0"), block=b)
            return go
        await run_pool([rt(ep, ln) for ep, ln in floor], a.conc)
    f.close()
    return done


def _assemble(eps, done):
    """calls -> the analyze() inputs."""
    from .common import build_request, s1_rule
    E, A = [], {}
    for ep in eps:
        meta = ep["meta"]
        E.append({"cluster": (ep["kind"], ep["seed"]), "kind": ep["kind"], "seed": ep["seed"],
                  "success": bool(meta.get("success", True)),
                  "events_t": [float(e["t"]) for e in meta.get("events", []) if "t" in e],
                  "t": {ln["k"]: float(ln["t"]) for ln in ep["lines"]}})
        for ln in ep["lines"]:
            g = lambda t: done.get((ep["dir"], ep["seed"], ln["k"], t))  # noqa: E731
            first = g("A0#0")
            if first is None:
                continue
            req, _ = build_request(ln, "A0")
            same = [x["answers"] for x in (g(f"A0#{i}") for i in range(8)) if x is not None]
            var = {v: g(v)["answers"] for v in ("A1", "A2", "A3", "A4") if g(v) is not None}
            rt = {}
            for b in range(16):
                pair = [g(f"rt{b}#{j}") for j in range(2)]
                if pair[0] is not None:
                    rt[b] = [{q: x["key"] for q, x in p["answers"].items()} for p in pair if p is not None]
            A[(ep["kind"], ep["seed"], ln["k"])] = {
                "vote": {q: x["key"] for q, x in first["answers"].items()},
                "same": [{q: x["key"] for q, x in s.items()} for s in same], "var": var, "rt": rt,
                "s1": s1_rule(req["state"]), "opts": first["opts"], "names": first["names"]}
    return E, A


def _markdown(res, meta) -> str:
    from .common import ci_str, md_table
    r = res
    pr = r["rules"]["pooled"]
    lines = [f"# E0.5 offline replay — {meta['model']['spec']}", "",
             f"- utc {meta['utc']}, git {meta['git']}, code_sha {meta['code_sha']}, model fingerprint "
             f"{meta['model'].get('fingerprint')}, prompt_config {meta['prompt_config']['sha']} "
             f"(layout {meta['layout']}, mode {meta['mode']}), split {meta['split']}, truth {meta['truth']}",
             f"- episodes {r['n_episodes']}, snapshots {r['n_snapshots']}, steps {r['n_steps']}, d_p95 used "
             f"{r['d_p95']} s (--d-p95), A0 call p50/p95 under load {meta['lat']['p50']}/{meta['lat']['p95']} s, "
             f"call errors {meta['errors']}, runtime {meta['runtime_s']}", "", "## Flip / floors", "",
             md_table(["metric", "mean [95% CI]", "n"], [
                 ["successive flip, success traj.", ci_str(r["flip"]["pooled"]["success"]),
                  r["flip"]["pooled"]["success"]["n"]],
                 ["successive flip, perturb window", ci_str(r["flip"]["pooled"]["perturb_window"]),
                  r["flip"]["pooled"]["perturb_window"]["n"]],
                 ["same-time flip (K)", ci_str(r["same_time_flip"]), r["same_time_flip"]["n"]],
                 ["retest flip (1x)", ci_str(r["retest_flip"]), r["retest_flip"]["n"]],
                 ["test-retest floor (ii)", ci_str(r["floor"]["pooled"]), r["floor"]["pooled"]["n"]]]),
             "", "## Rules (correctness vs truth)", "",
             md_table(["rule", "acc [95% CI]", "n"], [[k, ci_str(pr[k]), pr[k]["n"]] for k in RULES] +
                      [[k, ci_str(pr[k]), pr[k]["n"]] for k in ("la2_minus_newest", "c2pp_minus_newest",
                                                                 "c2prime_minus_newest", "c2prime_minus_la2",
                                                                 "la2_unconfirmed")]),
             "", "## Option-name layers", "",
             md_table(["layer", "A0", "A1", "A2", "A3", "A4", "subst flip", "A3 follow", "A4 flip", "floor",
                       "first pick / first true"],
                      [[L, ci_str(x["a0"]), ci_str(x["a1"]), ci_str(x["a2"]), ci_str(x["a3"]), ci_str(x["a4"]),
                        ci_str(x["subst"]), ci_str(x["follow"]), ci_str(x["a4flip"]), ci_str(x["floor"]),
                        f"{x['first_pick']['mean']} / {x['first_true']['mean']}"] for L, x in r["layers"].items()]),
             "", "## C_flip", "", f"AUROC {r['c_flip']['auroc']} (perturb steps {r['c_flip']['n_perturb_steps']}, "
             f"success steps {r['c_flip']['n_success_steps']}); FLIP_TH candidates {r['c_flip']['flip_th_candidates']}",
             "", "## Judgments (E §2A.6)", "", "```", __import__("json").dumps(r["judgments"], indent=1, default=str),
             "```"]
    return "\n".join(lines)


def main(argv=None):
    import asyncio
    import os
    from . import common as C
    from .splits import check_split
    a = _args(argv)
    check_split(a.split)
    t0 = time.monotonic()
    info = C.resolve_model(a.model)
    os.makedirs(a.out, exist_ok=True)
    info = C.ensure_merged(info, a.out)
    dirs = [d for d in a.data.split(",") if d]
    eps = C.load_episodes(dirs, a.split, a.episodes, parse_seeds(a.seeds))
    truth = C.load_truth(eps, a.truth, [d for d in a.outcome_dirs.split(",") if d])
    pc = C.training_prompt_config(info["path"]) if info["kind"] != "mock" else None
    layout = C.default_layout(pc) if a.layout == "auto" else a.layout
    with C.Server(info, a.gpu, a.out, a.url, a.served_name, a.gpu_util) as srv:
        asker = C.MockAsker() if info["kind"] == "mock" else C.Asker(srv.url, srv.name, layout, a.mode)
        t1 = time.monotonic()
        done = asyncio.run(_run(asker, eps, a))
        t_calls = time.monotonic() - t1
    E, A = _assemble(eps, done)
    res = analyze(E, A, truth, C.QUESTIONS, a.d_p95, a.n_boot, a.perturb_window)
    lat = [r["lat"] for r in done.values() if r["tag"] == "A0#0" and r.get("lat") is not None]
    p95 = round(float(np.quantile(lat, 0.95)), 4) if lat else None
    by_dir = {}
    for ep in eps:
        by_dir.setdefault(os.path.basename(ep["dir"].rstrip("/\\")), []).append(ep["seed"])
    meta = C.run_meta("e05", info, {
        "split": a.split, "data": dirs, "seeds": by_dir, "truth": a.truth, "layout": layout, "mode": a.mode,
        "episode_data_split": dict(Counter(str(ep["lines"][0].get("split")) for ep in eps if ep["lines"])),
        "prompt_config": C.prompt_config_eval(layout), "variants": a.variants, "same_k": a.same_k,
        "blocks": a.blocks, "floor_n": a.floor_n, "n_calls": len(done),
        "bootstrap": C.bootstrap_meta(a.n_boot, "episode (kind, seed); paired differences share the episode id"),
        "errors": sum(1 for r in done.values() if r.get("error")),
        "lat": {"p50": round(float(np.median(lat)), 4) if lat else None, "p95": p95,
                "note": f"A0 call latency under this run's load (conc {a.conc} snapshots x K {a.same_k} concurrent); "
                        "not an E0 latency -- the §2A.8 d_p95 re-run rule uses E0's final p95 (--d-p95)"},
        "runtime_s": {"total": round(time.monotonic() - t0, 1), "calls": round(t_calls, 1),
                      "vllm_ready": round(getattr(srv, "t_ready", 0.0), 1)},
        "note": "labels_v2 truth is defined by the same S1 code rule as C2' S1 (S1-alone accuracy is circular under "
                "labels_v2); POOL fit episodes are stage-A SFT training data (§56: pipeline check, not a result)"})
    C.write_outputs(a.out, "e05", {"meta": meta, "result": res}, _markdown(res, meta))
    print("E05_DONE " + __import__("json").dumps({"out": a.out, "claim": res["judgments"].get("claim"),
                                                  "runtime_s": meta["runtime_s"]}), flush=True)
    return res


async def _run(asker, eps, a):
    try:
        return await _collect(asker, eps, a, a.out)
    finally:
        await asker.close()


if __name__ == "__main__":
    main()
