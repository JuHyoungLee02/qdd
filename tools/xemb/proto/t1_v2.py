"""T1 on RB2 with the E-MAR-real filter-v2 kept pointings (labels/logs/marr_real/filter_decisions.json) as the 2-D
correspondences, vs raw pointing, same split and solver as t1_compare. usage: t1_v2.py OUT_JSON"""
import json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
import numpy as np
from xemb import selfcal as C
from xemb import src_rb2 as R

from harvest.train import se2e_molmo as MM
from harvest.train import se2e_trace as TT
CAM = TT.head_camera(TT.load_head_chain("/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"), TT.RB1_HEAD)
root = "/data/harvest/data/marr_real"
urdf = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
eps = R.load(root)
n_dec = {"keep": 0, "drop": 0, "missing": 0}
for e in eps:
    fr = R.fk_rot(R.RAW, e["ep"], urdf)
    e["R"] = {a: fr[a][1][: e["n"]] for a in ("left", "right")}
    e["v2"] = {}
    nom = {a: TT.project(CAM, e["ee"][a])[0] for a in ("left", "right")}
    pts = {a: [None if not np.isfinite(p).all() else (float(p[0]), float(p[1])) for p in e["uv"][a]] for a in ("left", "right")}
    kl, wl, kr, wr, info = MM.filter_nominal(pts["left"], pts["right"], nom["left"], nom["right"])
    keep = {"left": kl, "right": kr}
    for a in ("left", "right"):
        u = e["uv"][a].copy()
        for k in range(e["n"]):
            d = [keep[a][k]]
            if not d[0]:
                n_dec["drop"] += 1
                u[k] = np.nan
            else:
                n_dec["keep"] += 1
        e["v2"][a] = u
rng = np.random.default_rng(0)
order = rng.permutation(len(eps))
test = {eps[i]["ep"] for i in order[: len(eps) // 5]}


def stack(es, src):
    out = {k: [] for k in ("pL", "RL", "pR", "RR", "uL", "uR")}
    for e in es:
        for a, P, Rk, U in (("left", "pL", "RL", "uL"), ("right", "pR", "RR", "uR")):
            u = (e["v2"][a] if src == "v2" else e["uv"][a]).copy()
            if src == "raw":
                u[~C.jump_filter(u)] = np.nan
            out[P].append(e["ee"][a]); out[Rk].append(e["R"][a]); out[U].append(u)
    return [np.concatenate(out[k]) for k in ("pL", "RL", "pR", "RR", "uL", "uR")]


def held(fit, es, src):
    pL, RL, pR, RR, uL, uR = stack(es, src)
    d_all = []
    for p, Rr, u, arm in ((pL, RL, uL, "left"), (pR, RR, uR, "right")):
        d = np.linalg.norm(u - C.project_offset(fit, p, Rr, arm), axis=1)
        d_all += list(d[np.isfinite(d)])
    d = np.asarray(d_all)
    return {"n": int(len(d)), "median_px": round(float(np.median(d)), 2), "p90_px": round(float(np.percentile(d, 90)), 2),
            "le_5px": round(float((d <= 5).mean()), 4), "le_15px": round(float((d <= 15).mean()), 4)}


tr = [e for e in eps if e["ep"] not in test]
te = [e for e in eps if e["ep"] in test]
res = {"decisions_used": n_dec}
for src in ("v2", "raw"):
    f = C.selfcal_offset(*stack(tr, src), R.K_SPEC, fit_fx=True)
    res[src] = {"fx": round(float(f["K"][0, 0]), 1), "train_resid_median_px": round(f["resid_median_px"], 2),
                "inlier_frac": round(f["inlier_frac"], 3), "offset_left": f["o_left"].round(3).tolist(),
                "offset_right": f["o_right"].round(3).tolist(), "heldout_same_src_all_points": held(f, te, src),
                "vs_nominal": dict(zip(("rot_deg", "centre_m"), C.pose_error(f["E"], R.nominal_E(urdf))))}
    np.savez(outp := sys.argv[1].replace(".json", f"_{src}.npz"), E=f["E"], K=f["K"], o_left=f["o_left"], o_right=f["o_right"])
json.dump(res, open(sys.argv[1], "w"), indent=1)
print(json.dumps(res, indent=1))
