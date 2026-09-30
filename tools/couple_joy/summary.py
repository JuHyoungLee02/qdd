"""E-CJ1 summary and verdict (docs/stage3/prereg_cj1.md §5; fixed at registration). venv_train, no Isaac.
  python tools/couple_joy/summary.py [--root /data/harvest/out/couple/cj1] [--n-boot 10000]
Reads <root>/res/{ox,ov}/<variant>/s<seed>/cj.json (+ vla_steps.jsonl) and <root>/res/v0/<variant>/s<seed>/closed.json,
writes <root>/summary.json + summary.md. Units = (variant, seed) pairs present in every compared arm."""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, HERE)


def load(root: str) -> dict:
    out = {"ox": {}, "ov": {}, "v0": {}}
    for arm in ("ox", "ov"):
        for p in glob.glob(os.path.join(root, "res", arm, "*", "s*", "cj.json")):
            r = json.load(open(p))
            r["_dir"] = os.path.dirname(p)
            out[arm][(r["variant"], int(r["seed"]))] = r
    for p in glob.glob(os.path.join(root, "res", "v0", "*", "s*", "closed.json")):
        d = json.load(open(p))
        for t in d.get("trials", []):
            out["v0"][(t["variant"], int(t["seed"]))] = {"success": bool(t["success"]),
                                                          "termination": t.get("termination"), "_dir": os.path.dirname(p)}
    return out


def adherence(ep_dir: str) -> tuple[int, int]:
    """(hits, n): steps whose commanded dir_xy is not none_xy and whose TCP moved >= 2 mm in xy until the next step;
    hit = the xy move within 45 deg of the commanded direction (E-SR0 direction vectors, train.sr1c_branch._SGN)."""
    from harvest.train.sr1c_branch import _SGN
    p = os.path.join(ep_dir, "vla_steps.jsonl")
    if not os.path.exists(p):
        return 0, 0
    R = [json.loads(x) for x in open(p)]
    hit = n = 0
    for a, b in zip(R, R[1:]):
        want = a["dec"]["dir_xy"]
        d = (np.asarray(b["tcp"], float) - np.asarray(a["tcp"], float))[:2]
        if want == "none_xy" or a.get("error") or np.linalg.norm(d) < 0.002:
            continue
        u = np.asarray(_SGN[want], float)
        n += 1
        hit += int(float(d @ u) / (np.linalg.norm(d) * np.linalg.norm(u)) >= np.cos(np.pi / 4))
    return hit, n


def paired(a: dict, b: dict, n_boot: int, seed: int = 0):
    keys = sorted(set(a) & set(b))
    if not keys:
        return None
    x = np.array([float(a[k]["success"]) - float(b[k]["success"]) for k in keys])
    rng = np.random.default_rng(seed)
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n_boot)]
    return {"n": len(keys), "diff": float(x.mean()), "ci95": [float(np.percentile(bs, 2.5)),
                                                              float(np.percentile(bs, 97.5))]}


def verdict(S: dict, n_boot: int) -> dict:
    ox, ov, v0 = S["ox"], S["ov"], S["v0"]
    k = lambda d: sum(r["success"] for r in d.values())  # noqa: E731
    res = {"n": {a: len(S[a]) for a in S}, "success": {a: k(S[a]) for a in S}}
    res["G0"] = "PASS" if k(ox) >= 30 else "FAIL"
    q2 = paired(ox, ov, n_boot)
    res["Q2_ox_minus_ov"] = q2
    if res["G0"] == "FAIL" or q2 is None:
        res["Q2"] = "WITHHELD"
    elif k(ov) <= 4:
        res["Q2"] = "VLA_FLOOR"
    elif q2["diff"] <= 0.05 and k(ov) >= 30:
        res["Q2"] = "EXEC_OK"
    else:
        res["Q2"] = "EXEC_LOSS"
    q3 = paired(ov, v0, n_boot)
    res["Q3_ov_minus_v0"] = q3
    if res["G0"] == "FAIL" or q3 is None:
        res["Q3"] = "WITHHELD"
    elif q3["diff"] >= 0.10 and q3["ci95"][0] > 0:
        res["Q3"] = "JOY_BETTER"
    elif q3["diff"] <= -0.10 and q3["ci95"][1] < 0:
        res["Q3"] = "JOY_WORSE"
    else:
        res["Q3"] = "NO_DIFF"
    # OV breakdown (reported, not judged)
    h = n = 0
    fb, stages, ends, lat = 0, {}, {}, []
    for r in ov.values():
        a, b = adherence(r["_dir"])
        h, n = h + a, n + b
        fb += (r.get("events") or {}).get("grip_fallback", 0)
        stages[r.get("fail_stage") or "none"] = stages.get(r.get("fail_stage") or "none", 0) + 1
        ends[r.get("end_reason")] = ends.get(r.get("end_reason"), 0) + 1
        if r.get("exec") and r["exec"].get("lat_p50_s") is not None:
            lat.append(r["exec"]["lat_p50_s"])
    res["ov"] = {"joystick_adherence": None if n == 0 else round(h / n, 4), "adherence_n": n, "grip_fallback": fb,
                 "fail_stage": stages, "end_reason": ends,
                 "lat_p50_median_s": None if not lat else float(np.median(lat))}
    res["ox_fail_stage"] = {}
    for r in ox.values():
        s = r.get("fail_stage") or "none"
        res["ox_fail_stage"][s] = res["ox_fail_stage"].get(s, 0) + 1
    res["v0_termination"] = {}
    for r in v0.values():
        s = str(r.get("termination"))
        res["v0_termination"][s] = res["v0_termination"].get(s, 0) + 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data/harvest/out/couple/cj1")
    ap.add_argument("--n-boot", type=int, default=10000)
    a = ap.parse_args()
    S = load(a.root)
    res = verdict(S, a.n_boot)
    json.dump(res, open(os.path.join(a.root, "summary.json"), "w"), indent=1)
    lines = ["# E-CJ1 summary (tools/couple_joy/summary.py)", "",
             f"- n: {res['n']}  success: {res['success']}",
             f"- G0 {res['G0']} | Q2 {res['Q2']} {res['Q2_ox_minus_ov']} | Q3 {res['Q3']} {res['Q3_ov_minus_v0']}",
             f"- OV: {res['ov']}", f"- OX fail stage: {res['ox_fail_stage']}",
             f"- V0 termination: {res['v0_termination']}"]
    open(os.path.join(a.root, "summary.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
