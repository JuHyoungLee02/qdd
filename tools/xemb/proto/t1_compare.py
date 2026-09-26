"""T1 on RB2 with the shared tracking front-end vs per-frame pointing (CPU). usage: t1_compare.py CACHE_DIR OUT_JSON"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import numpy as np
from xemb import selfcal as C
from xemb import src_rb2 as R
from xemb import track as TK

cache, outp = sys.argv[1], sys.argv[2]
root = "/data/harvest/data/marr_real"
urdf = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
eps = [e for e in R.load(root) if os.path.exists(os.path.join(cache, f"RB2_ep{e['ep']:06d}.npz"))]
for e in eps:
    fr = R.fk_rot(R.RAW, e["ep"], urdf)
    e["R"] = {a: fr[a][1][: e["n"]] for a in ("left", "right")}
    c = TK.load(os.path.join(cache, f"RB2_ep{e['ep']:06d}.npz"))
    e["trk"] = {a: c["fused"].get(f"grip_{a}_point", np.full((e["n"], 2), np.nan))[: e["n"]] for a in ("left", "right")}
    for a in ("left", "right"):  # tracks leaving the image are not points on the gripper
        t = e["trk"][a]
        bad = ~((t[:, 0] >= 12) & (t[:, 0] <= 660) & (t[:, 1] >= 12) & (t[:, 1] <= 364))
        t[bad] = np.nan
rng = np.random.default_rng(0)
order = rng.permutation(len(eps))
test = {eps[i]["ep"] for i in order[: len(eps) // 5]}


def stack(es, src):
    out = {k: [] for k in ("pL", "RL", "pR", "RR", "uL", "uR")}
    for e in es:
        for a, P, Rk, U in (("left", "pL", "RL", "uL"), ("right", "pR", "RR", "uR")):
            u = (e["uv"][a] if src == "point" else e["trk"][a]).copy()
            if src == "point":
                u[~C.jump_filter(u)] = np.nan
            out[P].append(e["ee"][a])
            out[Rk].append(e["R"][a])
            out[U].append(u)
    return [np.concatenate(out[k]) for k in ("pL", "RL", "pR", "RR", "uL", "uR")]


def held(fit, es, src):
    pL, RL, pR, RR, uL, uR = stack(es, src)
    d_all = []
    for p, Rr, u, po, Ro, arm, oth in ((pL, RL, uL, pR, RR, "left", "right"), (pR, RR, uR, pL, RL, "right", "left")):
        pn, pot = C.project_offset(fit, p, Rr, arm), C.project_offset(fit, po, Ro, oth)
        d, do = np.linalg.norm(u - pn, axis=1), np.linalg.norm(u - pot, axis=1)
        ok = np.isfinite(d) & ~(do + 10 < d)
        d_all += list(d[ok])
    d = np.asarray(d_all)
    return {"n": int(len(d)), "median_px": round(float(np.median(d)), 2), "p90_px": round(float(np.percentile(d, 90)), 2),
            "le_15px": round(float((d <= 15).mean()), 4)}


res = {"episodes": len(eps), "test_eps": len(test)}
tr = [e for e in eps if e["ep"] not in test]
te = [e for e in eps if e["ep"] in test]
fits = {}
for src in ("point", "track"):
    f = C.selfcal_offset(*stack(tr, src), R.K_SPEC, fit_fx=True)
    fits[src] = f
    per = []
    for e in eps:
        pL, RL, pR, RR, uL, uR = stack([e], src)
        XLo = pL + np.einsum("nij,j->ni", RL, f["o_left"])
        XRo = pR + np.einsum("nij,j->ni", RR, f["o_right"])
        g = C.selfcal_two_arm(XLo, XRo, uL, uR, f["K"])
        if g is not None and g["n"] >= 40:
            per.append(C.pose_error(g["E"], f["E"]))
    per = np.asarray(per)
    res[src] = {"fx": round(float(f["K"][0, 0]), 1), "train_resid_median_px": round(f["resid_median_px"], 2),
                "train_inlier_frac": round(f["inlier_frac"], 3), "n": f["n"],
                "heldout_vs_point": held(f, te, "point"), "heldout_vs_track": held(f, te, "track"),
                "per_episode_rot_deg_median": round(float(np.median(per[:, 0])), 2) if len(per) else None,
                "per_episode_centre_cm_median": round(float(np.median(per[:, 1]) * 100), 2) if len(per) else None,
                "per_episode_n": int(len(per))}
rot, dist = C.pose_error(fits["point"]["E"], fits["track"]["E"])
res["point_vs_track_camera"] = {"rot_deg": round(rot, 2), "centre_cm": round(dist * 100, 2)}
En = R.nominal_E(urdf)
for src in ("point", "track"):
    r_, d_ = C.pose_error(fits[src]["E"], En)
    res[src]["vs_nominal"] = {"rot_deg": round(r_, 2), "centre_cm": round(d_ * 100, 2)}
json.dump(res, open(outp, "w"), indent=1)
np.savez(outp.replace(".json", "_fit.npz"), **{f"{s}_{k}": fits[s][k] for s in fits for k in ("E", "K", "o_left", "o_right")})
print(json.dumps(res, indent=1))
