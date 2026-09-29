"""E-M4b-meas analysis (numpy only): M4 (b) per-predicate metrics and the M7 critic evaluation, pre-registration
e_m4b_meas.md §0-§1. Reads the FI-DEV table, V1h logits, V1z/V1q yes-probabilities, V0 predicates; fits P on the
calibration seeds; writes one results JSON.

  python -m harvest.m4b.analyze --fi ROOT --pool DIR --v1h RUN/logits.jsonl --v1z F --v1q F --v0 F --out results.json
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

from ..analysis.stats import auroc, ece
from . import metrics as M
from . import prules as PR
from . import spec as FS

WORLD, ROBOT, PREDS = FS.WORLD, FS.ROBOT, FS.PREDS
ALPHA_SET, ALPHA_FWER, TAU, PERSIST = 0.1, 0.05, 2.0, 2
NEAR_CONTACT = ("descend", "close", "place_descend", "open")


# ------------------------------------------------------------------------------------------ critic score (pure)
def viol_prob(phase: str, p: dict, scope=None) -> float:
    """max over the phase's expected predicates (inside scope, measured) of P(value != expected)."""
    out = 0.0
    for name, want in FS.EXPECT.get(phase, ()):
        names = name if isinstance(name, tuple) else (name,)
        if scope is not None and not set(names) <= set(scope):
            continue
        vals = [p.get(x) for x in names]
        if any(v is None for v in vals):
            continue
        q = max(vals)  # P(at least one true) ~ max for an OR entry; the value itself for a single one
        out = max(out, 1.0 - q if want else q)
    return float(out)


def _sig(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, float)))


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


# ------------------------------------------------------------------------------------------ loading
def load_prob_sources(a, snaps):
    """{cond: {key: {pred: p or None}}} before calibration: raw probabilities (V1h: sigmoid(logit))."""
    src = {}
    if a.v1h and os.path.exists(a.v1h):
        d = {}
        for x in open(a.v1h):
            r = json.loads(x)
            d[r["key"]] = dict(zip(PREDS, r["logits"]))
        src["V1h_logit"] = d
    for name, f in (("V1z", a.v1z), ("V1q", a.v1q)):
        if f and os.path.exists(f):
            d = {}
            for x in open(f):
                r = json.loads(x)
                d[r["key"]] = {k: float(_logit(v)) for k, v in r["p_yes"].items()}
            src[name + "_logit"] = d
    d = {}
    for fv in (a.v0 or "").split(","):
        if fv and os.path.exists(fv):
            for x in open(fv):
                for r in json.loads(x)["rows"]:
                    d[r["key"]] = r["pred"]
    if d:
        src["V0"] = d
    return src


def temperatures(logit_src, snaps, cal_filter, preds):
    T = {}
    for p in preds:
        z, y = [], []
        for s in snaps:
            if not cal_filter(s) or s["key"] not in logit_src:
                continue
            v, t = logit_src[s["key"]].get(p), s["truth"].get(p)
            if v is None or t is None:
                continue
            z.append(v)
            y.append(int(t))
        T[p] = M.fit_temperature(z, y) if len(set(y)) == 2 else 1.0
    return T


def calibrated(logit_src, T):
    return {k: {p: (float(_sig(v / T[p])) if v is not None and p in T else None) for p, v in d.items()}
            for k, d in logit_src.items()}


def qhats(prob, snaps, cal_filter, preds):
    q = {}
    for p in preds:
        pp, yy = [], []
        for s in snaps:
            if not cal_filter(s) or s["key"] not in prob:
                continue
            v, t = prob[s["key"]].get(p), s["truth"].get(p)
            if v is None or t is None:
                continue
            pp.append(v)
            yy.append(int(t))
        q[p] = M.conformal_qhat(M.nonconf(pp, yy), ALPHA_SET) if pp else None
    return q


# ------------------------------------------------------------------------------------------ M4 (b)
def pred_table(prob, snaps, sel, preds, hard=None, q=None, eps_key="ep"):
    """Per predicate: n, pos, BA (+ per-episode counts for the bootstrap), AUROC, ECE, set metrics."""
    out, cnt = {}, {}
    for p in preds:
        rows = [(s, prob.get(s["key"], {}).get(p) if prob is not None else None,
                 None if hard is None else hard.get(s["key"], {}).get(p)) for s in snaps if sel(s)]
        rows = [(s, v, h) for s, v, h in rows if s["truth"].get(p) is not None and (v is not None or h is not None
                                                                                    or hard is not None)]
        if not rows:
            continue
        y = np.array([int(s["truth"][p]) for s, _, _ in rows])
        if hard is not None:  # binary source (V0 / P rule): unknown counts as wrong
            yh = np.array([(1 - yi) if h is None else int(h) for (s, v, h), yi in zip(rows, y)])
        else:
            yh = np.array([int(v >= 0.5) for s, v, _ in rows])
        per_ep = {}
        for (s, _, _), yi, hi in zip(rows, y, yh):
            per_ep.setdefault(s[eps_key], np.zeros(4))
            per_ep[s[eps_key]] += M.counts([yi], [hi])
        cnt[p] = per_ep
        r = {"n": int(len(y)), "pos": int(y.sum()), "neg": int(len(y) - y.sum()), "ba": M.balanced_accuracy(y, yh)}
        if hard is not None:
            r["unknown_rate"] = float(np.mean([h is None for _, _, h in rows]))
        pv = [v for _, v, _ in rows]
        if all(v is not None for v in pv) and hard is None:
            pv = np.array(pv, float)
            r["auroc"] = auroc(pv, y)
            conf = np.maximum(pv, 1 - pv)
            r["ece"] = ece(conf, (pv >= 0.5) == (y == 1))
            if q is not None and q.get(p) is not None:
                sets = [M.set_of(v, q[p]) for v in pv]
                r.update({"qhat": q[p], **M.set_metrics(y, sets)})
            r["_p"], r["_y"] = pv.tolist(), y.tolist()
        out[p] = r
    return out, cnt


def mean_ba_block(tab, cnt, preds, eps, min_n=20):
    use = [p for p in preds if p in tab and tab[p]["pos"] >= min_n and tab[p]["neg"] >= min_n]
    excl = [p for p in preds if p not in use]
    if not use:
        return {"use": [], "excluded": excl}
    C = np.stack([np.stack([cnt[p].get(e, np.zeros(4)) for p in use]) for e in eps])  # [E, P, 4]
    ba = float(np.nanmean([M.ba_from_counts(C[:, i].sum(0)) for i in range(len(use))]))
    lo, hi = M.boot_ba_ci(C, n=2000, seed=0)
    return {"use": use, "excluded": excl, "mean_ba": ba, "ci": [lo, hi], "_C": C}


def pooled_calib(tab, use):
    p = np.concatenate([tab[k]["_p"] for k in use if "_p" in tab[k]]) if use else np.array([])
    y = np.concatenate([tab[k]["_y"] for k in use if "_y" in tab[k]]) if use else np.array([])
    if not len(p):
        return {}
    conf = np.maximum(p, 1 - p)
    out = {"ece_pooled": ece(conf, (p >= 0.5) == (y == 1))}
    return out


def pooled_sets(prob, snaps, sel, use, q):
    y, sets = [], []
    for s in snaps:
        if not sel(s):
            continue
        for p in use:
            v, t = prob.get(s["key"], {}).get(p), s["truth"].get(p)
            if v is None or t is None or q.get(p) is None:
                continue
            y.append(int(t))
            sets.append(M.set_of(v, q[p]))
    return M.set_metrics(y, sets) if y else {}


# ------------------------------------------------------------------------------------------ critic
def ep_scores(ep, channels):
    """channels: [(name, prob dict, scope)] -> {name: persisted score array}."""
    out = {}
    for name, prob, scope in channels:
        v = [viol_prob(s["phase"], prob.get(s["key"], {}), scope) for s in ep["snaps"]]
        out[name] = M.persist(v, PERSIST)
    return out


def critic(eps, channels, cal_sel, eval_sel, alpha=ALPHA_FWER):
    names = [c[0] for c in channels]
    a_ch = alpha / len(names)
    nonfail = lambda e: e["cond"] not in FS.FAILURES and e["success"]  # noqa: E731
    cal = [e for e in eps if cal_sel(e) and nonfail(e)]
    thr = {n: M.fwer_threshold([ep_scores(e, channels)[n].max(initial=0.0) for e in cal], a_ch) for n in names}

    def first(e):
        sc = ep_scores(e, channels)
        ts = [s["t"] for s in e["snaps"]]
        al = [M.first_alarm(ts, sc[n], thr[n]) for n in names]
        al = [x for x in al if x is not None]
        return min(al) if al else None
    ev = [e for e in eps if eval_sel(e)]
    nf = [e for e in ev if nonfail(e)]
    fa = [e for e in nf if first(e) is not None]
    fails = [e for e in ev if e["cond"] in FS.FAILURES and e["onset"] is not None]
    unreal = [e["ep"] for e in ev if e["cond"] in FS.FAILURES and e["onset"] is None]
    det, lenient, early, delays, by = [], [], [], [], {}
    for e in fails:
        t = first(e)
        d = M.detected(t, e["onset"], TAU)
        sc = ep_scores(e, channels)
        ts = np.array([s["t"] for s in e["snaps"]])
        win = (ts >= e["onset"] - 1e-9) & (ts <= e["onset"] + TAU + 1e-9)
        len_ok = any((sc[n][win] > thr[n]).any() for n in names)
        det.append(d)
        lenient.append(len_ok)
        early.append(t is not None and t < e["onset"] - 1e-9)
        if d:
            delays.append(t - e["onset"])
        by.setdefault(e["cond"], []).append(d)
    harmless = [e for e in ev if e["cond"] in FS.HARMLESS]
    return {"thr": thr, "alpha_per_channel": a_ch, "n_cal_nonfail": len(cal), "n_eval_nonfail": len(nf),
            "fwer": len(fa) / max(len(nf), 1), "n_fail": len(fails), "unrealized": unreal,
            "recall": float(np.mean(det)) if det else None, "recall_lenient": float(np.mean(lenient)) if det else None,
            "early_alarm_rate": float(np.mean(early)) if det else None,
            "delay_median_s": float(np.median(delays)) if delays else None,
            "recall_by_type": {k: float(np.mean(v)) for k, v in by.items()},
            "n_by_type": {k: len(v) for k, v in by.items()},
            "harmless_first_intervention": float(np.mean([first(e) is not None for e in harmless])) if harmless else None,
            "false_alarm_eps": [e["ep"] for e in fa]}


def boot_recall_ci(det_by_ep, n=2000, seed=0):
    v = np.array(det_by_ep, float)
    if not len(v):
        return None
    rng = np.random.default_rng(seed)
    m = v[rng.integers(0, len(v), (n, len(v)))].mean(1)
    return [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))]


# ------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fi", default="/data/harvest/m4b/fidev")
    ap.add_argument("--pool", default="/data/harvest/data/pool")
    ap.add_argument("--v1h", default="/data/harvest/m4b/v1h/logits.jsonl")
    ap.add_argument("--v1z", default="/data/harvest/m4b/v1z.jsonl")
    ap.add_argument("--v1q", default="/data/harvest/m4b/v1q.jsonl")
    ap.add_argument("--v0", default="/data/harvest/m4b/v0.jsonl")
    ap.add_argument("--out", default="/data/harvest/m4b/results.json")
    a = ap.parse_args(argv)
    from .data import fi_episodes, pool_snaps
    eps = fi_episodes(a.fi, with_lines=False)
    fsn = [s for e in eps for s in e["snaps"]]
    psn = pool_snaps(a.pool) if a.pool else []
    snaps = fsn + psn
    src = load_prob_sources(a, snaps)
    res = {"data": {}, "m4b": {}, "critic": {}, "pc": {}}

    # ---- data summary
    ds = {}
    for e in eps:
        k = (e["split"], e["cond"])
        d = ds.setdefault(f"{k[0]}|{k[1]}", {"n": 0, "success": 0, "onset": 0, "snaps": 0})
        d["n"] += 1
        d["success"] += int(bool(e["success"]))
        d["onset"] += int(e["onset"] is not None)
        d["snaps"] += len(e["snaps"])
    res["data"]["episodes"] = ds
    res["data"]["pool_snaps"] = {sp: sum(s["split"] == sp for s in psn) for sp in ("pool_fit", "pool_eval")}
    # nominal / harmless truth violations (sanity of the expectation table)
    nv = {}
    for e in eps:
        if e["cond"] in FS.FAILURES:
            continue
        v = sum(bool(FS.violations(s["phase"], s["truth"])) for s in e["snaps"])
        nv[e["ep"]] = v
    res["data"]["nonfail_truth_violation_snaps"] = {k: v for k, v in nv.items() if v}

    is_cal = lambda s: s["split"] == "fi_cal"  # noqa: E731
    is_cal10 = lambda s: s["split"] == "fi_cal" and s["seed"] >= 10  # noqa: E731
    is_eval = lambda s: s["split"] == "fi_eval"  # noqa: E731
    is_peval = lambda s: s["split"] == "pool_eval"  # noqa: E731
    eval_eps = [e["ep"] for e in eps if e["split"] == "fi_eval"]
    pool_eps = sorted({s["ep"] for s in psn if s["split"] == "pool_eval"})

    probs, qs = {}, {}
    # V1h
    if "V1h_logit" in src:
        T = temperatures(src["V1h_logit"], snaps, is_cal, PREDS)
        probs["V1h"] = calibrated(src["V1h_logit"], T)
        qs["V1h"] = qhats(probs["V1h"], snaps, is_cal, PREDS)
        res["m4b"]["V1h_temperature"] = T
    for name in ("V1z", "V1q"):
        if name + "_logit" in src:
            T = temperatures(src[name + "_logit"], snaps, is_cal10, WORLD)
            probs[name] = calibrated(src[name + "_logit"], T)
            qs[name] = qhats(probs[name], snaps, is_cal10, WORLD)
            res["m4b"][name + "_temperature"] = T
            raw = {k: {p: float(_sig(v)) for p, v in d.items()} for k, d in src[name + "_logit"].items()}
            probs[name + "_raw"] = raw
    # P
    cal_s = [s for s in fsn if is_cal(s)]
    f = {k: np.array([s[k] for s in cal_s], float) for k in ("width", "grip_tau", "tcp_z", "tau_res")}
    tt = {p: np.array([bool(s["truth"][p]) for s in cal_s]) for p in ROBOT}
    par = PR.fit(f, tt)
    res["m4b"]["P_params"] = par
    fe = {k: np.array([s[k] for s in fsn], float) for k in ("width", "grip_tau", "tcp_z", "tau_res")}
    sc, hr = PR.scores(fe, par), PR.apply(fe, par)
    probs["P"] = {s["key"]: {p: float(sc[p][i]) for p in ROBOT} for i, s in enumerate(fsn)}
    hard_P = {s["key"]: {p: bool(hr[p][i]) for p in ROBOT} for i, s in enumerate(fsn)}
    hard_V0 = src.get("V0")

    # ---- M4 (b) tables on FI eval
    tabs = {}
    for name in ("V1h", "V1z", "V1q", "V1z_raw", "V1q_raw"):
        if name in probs:
            preds = PREDS if name == "V1h" else WORLD
            tabs[name] = pred_table(probs[name], snaps, is_eval, preds, q=qs.get(name.replace("_raw", ""))
                                    if not name.endswith("_raw") else None)
    tabs["P"] = pred_table(None, snaps, is_eval, ROBOT, hard=hard_P)
    if hard_V0:
        v0_sel = lambda s: is_eval(s) and s["key"] in hard_V0  # noqa: E731
        tabs["V0"] = pred_table(None, snaps, v0_sel, WORLD + ROBOT[:3], hard=hard_V0)
    blocks = {}
    for name, (tab, cnt) in tabs.items():
        preds = WORLD if name != "P" else ROBOT
        blk = mean_ba_block(tab, cnt, preds, eval_eps)
        blocks[name] = blk
        entry = {"per_pred": {p: {k: v for k, v in r.items() if not k.startswith("_")} for p, r in tab.items()},
                 "world_block" if name != "P" else "robot_block": {k: v for k, v in blk.items() if not k.startswith("_")}}
        if name in qs:
            entry["pooled"] = {**pooled_calib(tab, blk["use"]), **pooled_sets(probs[name], snaps, is_eval, blk["use"],
                                                                             qs[name])}
        res["m4b"][name] = entry
    # V1h robot-side block (for reference)
    if "V1h" in tabs:
        rb = mean_ba_block(tabs["V1h"][0], tabs["V1h"][1], ROBOT, eval_eps)
        res["m4b"]["V1h"]["robot_block"] = {k: v for k, v in rb.items() if not k.startswith("_")}
    # paired diffs (same predicate set = V1h's)
    if "V1h" in blocks and blocks["V1h"].get("use"):
        use = blocks["V1h"]["use"]
        CV = blocks["V1h"]["_C"]
        diffs = {"V1h-majority": [blocks["V1h"]["ci"][0] - 0.5, blocks["V1h"]["ci"][1] - 0.5]}
        for other in ("V0", "V1q", "V1z"):
            if other in tabs:
                cnt = tabs[other][1]
                CO = np.stack([np.stack([cnt.get(p, {}).get(e, np.zeros(4)) for p in use]) for e in eval_eps])
                diffs[f"V1h-{other}"] = list(M.boot_ba_diff_ci(CV, CO, n=2000, seed=0))
                diffs[f"{other}_mean_ba_same_set"] = float(np.nanmean([M.ba_from_counts(CO[:, i].sum(0))
                                                                         for i in range(len(use))]))
        res["m4b"]["paired"] = diffs
    # breakdowns for V1h: phase band, occluded frames
    if "V1h" in probs:
        br = {}
        for tag, sel in (("near_contact", lambda s: is_eval(s) and s["phase"] in NEAR_CONTACT),
                         ("far", lambda s: is_eval(s) and s["phase"] not in NEAR_CONTACT),
                         ("occluded_H2", lambda s: is_eval(s) and s.get("occluded")),
                         ("failure_eps", lambda s: is_eval(s) and s["cond"] in FS.FAILURES),
                         ("nonfail_eps", lambda s: is_eval(s) and s["cond"] not in FS.FAILURES)):
            t, _ = pred_table(probs["V1h"], snaps, sel, PREDS)
            br[tag] = {p: {"n": r["n"], "pos": r["pos"], "ba": r["ba"]} for p, r in t.items()}
        res["m4b"]["V1h_breakdown"] = br
        # pool eval (V1 family auxiliary)
        pe = {}
        for name in ("V1h", "V1z", "V1q"):
            if name in probs:
                t, c = pred_table(probs[name], snaps, is_peval, WORLD)
                b = mean_ba_block(t, c, WORLD, pool_eps)
                pe[name] = {"per_pred": {p: {"n": r["n"], "pos": r["pos"], "ba": r["ba"], "auroc": r.get("auroc")}
                                         for p, r in t.items()},
                            "block": {k: v for k, v in b.items() if not k.startswith("_")}}
        res["m4b"]["pool_eval"] = pe

    # ---- critic
    cal_e = lambda e: e["split"] == "fi_cal"  # noqa: E731
    cal10_e = lambda e: e["split"] == "fi_cal" and e["seed"] >= 10  # noqa: E731
    ev_e = lambda e: e["split"] == "fi_eval"  # noqa: E731
    Wc, Rc = set(WORLD), set(ROBOT)
    cfgs = {}
    if "V1h" in probs:
        cfgs["V1h"] = ([("v1h", probs["V1h"], None)], cal_e)
        cfgs["V1h_world"] = ([("v1h_w", probs["V1h"], Wc)], cal_e)
        cfgs["V1h+P"] = ([("p", probs["P"], Rc), ("v1h_w", probs["V1h"], Wc)], cal_e)
    cfgs["P"] = ([("p", probs["P"], Rc)], cal_e)
    for name in ("V1z", "V1q"):
        if name in probs:
            cfgs[f"{name}+P"] = ([("p", probs["P"], Rc), (name, probs[name], Wc)], cal10_e)
            cfgs[name] = ([(name, probs[name], Wc)], cal10_e)
    if hard_V0:
        v0p = {k: {p: (None if v is None else float(v)) for p, v in d.items()} for k, d in hard_V0.items()}
        v0p = {k: {p: (0.5 if v is None and p != "contact_stall" else v) for p, v in d.items()} for k, d in v0p.items()}
        cfgs["V0"] = ([("v0", v0p, None)], cal10_e)
        cfgs["V0+P"] = ([("p", probs["P"], Rc), ("v0_w", v0p, Wc)], cal10_e)
    for name, (chs, cs) in cfgs.items():
        res["critic"][name] = critic(eps, chs, cs, ev_e)
    # PC2 hard P rule on eval non-failure successes (binary, 2 ticks)
    hardp = {k: {p: float(v) for p, v in d.items()} for k, d in hard_P.items()}
    nf = [e for e in eps if ev_e(e) and e["cond"] not in FS.FAILURES and e["success"]]
    fa = [e["ep"] for e in nf if ep_scores(e, [("p", hardp, Rc)])["p"].max(initial=0) >= 1.0]
    fa_nom = [x for x in fa if "/nominal/" in x]
    per_pred = {}
    for p in ROBOT:
        fp = [e["ep"] for e in nf if ep_scores(e, [("p", hardp, {p})])["p"].max(initial=0) >= 1.0]
        per_pred[p] = {"fwer": len(fp) / max(len(nf), 1), "n_eps": len(fp),
                       "fwer_nominal": sum("/nominal/" in x for x in fp) / max(sum("/nominal/" in e["ep"] for e in nf), 1)}
    res["critic"]["P_hard_rule"] = {"fwer_nonfail": len(fa) / max(len(nf), 1), "n_nonfail": len(nf),
                                    "false_alarm_eps": fa,
                                    "fwer_nominal": len(fa_nom) / max(sum("/nominal/" in e["ep"] for e in nf), 1),
                                    "per_pred": per_pred}
    res["pc"] = verdicts(res)
    json.dump(res, open(a.out, "w"), indent=1, default=lambda o: None)
    print(json.dumps(res["pc"], indent=1))


def verdicts(res):
    pc = {}
    m = res["m4b"]
    v = m.get("V1h", {})
    wb, pooled = v.get("world_block", {}), v.get("pooled", {})
    pr = m.get("paired", {})
    if wb.get("use"):
        c1 = {"mean_ba": wb["mean_ba"], "ci_low": wb["ci"][0], "cond_ba_090": wb["ci"][0] >= 0.90,
              "v0_diff_ci": pr.get("V1h-V0"), "cond_v0": pr.get("V1h-V0") is not None and pr["V1h-V0"][0] >= 0.15,
              "maj_diff_ci": pr.get("V1h-majority"), "cond_maj": pr["V1h-majority"][0] >= 0.15,
              "ece_pooled": pooled.get("ece_pooled"), "cond_ece": (pooled.get("ece_pooled") or 1) <= 0.05,
              "coverage_pooled": pooled.get("coverage"),
              "cond_cov": pooled.get("coverage") is not None and 0.88 <= pooled["coverage"] <= 0.95}
        c1["pass"] = all(c1[k] for k in ("cond_ba_090", "cond_v0", "cond_maj", "cond_ece", "cond_cov"))
        q = m.get("V1q", {}).get("world_block", {})
        c1["v1q_mean_ba"] = q.get("mean_ba")
        c1["v1q_beats_by_003"] = q.get("mean_ba") is not None and q["mean_ba"] >= wb["mean_ba"] + 0.03
        pc["PC1"] = c1
    p = m.get("P", {}).get("per_pred", {})
    hard = res["critic"].get("P_hard_rule", {})
    # PC2 names three predicates (gripper_open, holding / empty grasp, lifted while holding); contact_stall is
    # reported with the same numbers but is not a PC2 predicate. FWER per predicate (its own hard rule, 2 ticks).
    pp = hard.get("per_pred", {})
    c2 = {k: {"ba": p.get(k, {}).get("ba"), "fwer": pp.get(k, {}).get("fwer"),
              "ba_ge_097": (p.get(k, {}).get("ba") or 0) >= 0.97,
              "fwer_le_001": pp.get(k, {}).get("fwer") is not None and pp[k]["fwer"] <= 0.01}
          for k in ("gripper_open", "holding_t", "lifted_holding", "contact_stall")}
    c2["fwer_all_robot_rules"] = hard.get("fwer_nonfail")
    c2["pc2_fwer_three"] = max((pp.get(k, {}).get("fwer") or 0) for k in ("gripper_open", "holding_t",
                                                                          "lifted_holding"))
    c2["T1_registered"] = [k for k in ("gripper_open", "holding_t", "lifted_holding")
                           if c2[k]["ba_ge_097"] and c2[k]["fwer_le_001"] and c2["pc2_fwer_three"] <= 0.01]
    pc["PC2"] = c2
    cr = res["critic"]
    if "V1h+P" in cr:
        r2 = cr["V1h+P"]["recall"] or 0
        r_h, r_p = cr["V1h"]["recall"] or 0, cr["P"]["recall"] or 0
        pc["PC3"] = {"recall_V1h+P": r2, "recall_V1h": r_h, "recall_P": r_p, "fwer_V1h+P": cr["V1h+P"]["fwer"],
                     "pass": r2 >= 0.80 and r2 >= r_h + 0.05 and r2 >= r_p + 0.05}
    pc["PC5"] = {"status": "not run (L skipped)"}
    return pc


if __name__ == "__main__":
    main()
