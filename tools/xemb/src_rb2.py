"""ROBOTIS AI Worker open data RB2 (Task_0002_OrderPicking, FFW-BG2 rev4, real) -- a source WITHOUT camera calibration:
routes 1-4 and track T1 (self-calibration) on it.

Inputs (already on the pod from E-MAR-real, /data/harvest/data/marr_real): eps/RB2_epNNNNNN.npz = FK end-effector
positions ee_l / ee_r (URDF ffw_bg2_rev4_follower, arm_base_link frame, m) + gripper joints g_l / g_r (0 open ... ~1.1
closed, > 0.5 closed) at 10 Hz; frames/RB2/epNNNNNN/fKKKK.jpg = head ZED Mini left 672 x 376; points.shard*.jsonl =
Molmo2-ER "point to the {left|right} robot gripper" per frame and arm (route 2 detector, raw error 21-30 %).
Nothing here uses the nominal URDF camera: it is only compared at the end.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from . import fmt as F
from . import gates as Q
from . import geom as G
from . import selfcal as C
from . import steps as S
from . import track as TK

W, H = 672, 376
K_SPEC = np.array([[367.0, 0, 336.0], [0, 367.0, 188.0], [0, 0, 1]])  # ZED Mini VGA spec (canon §47)
BORDER = 12.0
GRIP_CLOSED = 0.5
T1_GATE_PX = 5.0  # projection QA / C' with camera only below this held-out reprojection (no-frame survey)
AGREE_PX = 20.0  # a pixel label needs the tracker and the pointing model to agree within this


RAW = "/data/harvest/data/se2e/raw/Task_0002_OrderPicking_lerobot"


def fk_rot(root_raw, ep, urdf):
    """End-effector rotations (arm_base_link) per frame from the raw joint states (same chain walk as
    harvest.train.se2e_data.fk_ee / tools/mar2 fk_pose) -> {arm: (p (N, 3), R (N, 3, 3))}."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    import pyarrow.parquet as pq
    from harvest.train import se2e_data as SD
    info = json.load(open(os.path.join(root_raw, "meta", "info.json")))
    c = ep // info["chunks_size"]
    t = pq.read_table(os.path.join(root_raw, info["data_path"].format(episode_chunk=c, episode_index=ep))).to_pydict()
    st = np.asarray(t["observation.state"], float)
    names = info["features"]["observation.state"]["names"]
    out = {}
    for a in ("left", "right"):
        chain = SD.load_arm_chain(urdf, a)
        q = st[:, SD.arm_index(names, a)[:7]]
        n = len(q)
        R = np.broadcast_to(np.eye(3), (n, 3, 3)).copy()
        p = np.zeros((n, 3))
        i = 0
        for typ, xyz, Ro, axis in chain:
            p = p + R @ xyz
            R = R @ Ro
            if typ in ("revolute", "continuous"):
                R = R @ SD._axis_rot(axis, q[:, i])
                i += 1
        out[a] = (p, R)
    return out


_TASKS = {}


def task_of(e) -> str:
    """Instruction of an RB2 episode from the raw LeRobot meta (meta/episodes.jsonl 'tasks')."""
    if not _TASKS:
        p = os.path.join(RAW, "meta", "episodes.jsonl")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                r = json.loads(line)
                _TASKS[int(r["episode_index"])] = (r.get("tasks") or [""])[0]
    return _TASKS.get(int(e["ep"]), "")


def load(root):
    eps = json.load(open(os.path.join(root, "episodes.json")))["episodes"]
    pts = {}
    for f in sorted(glob.glob(os.path.join(root, "points.shard*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            pts[(r["ep"], r["k"], r["arm"])] = r["point"]
    out = []
    for e in eps:
        p = os.path.join(root, "eps", f"RB2_ep{e['ep']:06d}.npz")
        if not os.path.exists(p):
            continue
        z = np.load(p)
        n = int(e.get("frames_decoded") or 0)
        if n < 10:
            continue
        rec = {"ep": e["ep"], "split": e["split"], "n": n, "ee": {"left": z["ee_l"][:n], "right": z["ee_r"][:n]},
               "g": {"left": z["g_l"][:n], "right": z["g_r"][:n]}, "uv": {}}
        for a in ("left", "right"):
            u = np.full((n, 2), np.nan)
            for k in range(n):
                q = pts.get((e["ep"], k, a))
                if q is not None and BORDER <= q[0] <= W - BORDER and BORDER <= q[1] <= H - BORDER:
                    u[k] = q
            rec["uv"][a] = u
        out.append(rec)
    return out


def nominal_E(urdf):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from harvest.train import se2e_trace as T
    R, t = T.head_camera(T.load_head_chain(urdf), T.RB1_HEAD)
    E = np.eye(4)
    E[:3, :3] = R.T
    E[:3, 3] = -R.T @ t
    return E


def _stack(eps, keep_jump=True):
    XL, XR, UL, UR, tag = [], [], [], [], []
    for e in eps:
        uL, uR = e["uv"]["left"].copy(), e["uv"]["right"].copy()
        if keep_jump:
            uL[~C.jump_filter(uL)] = np.nan
            uR[~C.jump_filter(uR)] = np.nan
        XL.append(e["ee"]["left"])
        XR.append(e["ee"]["right"])
        UL.append(uL)
        UR.append(uR)
        tag += [(e["ep"], k) for k in range(e["n"])]
    return np.concatenate(XL), np.concatenate(XR), np.concatenate(UL), np.concatenate(UR), tag


def calibrate(eps, K=K_SPEC):
    XL, XR, UL, UR, _ = _stack(eps)
    return C.selfcal_two_arm(XL, XR, UL, UR, K)


def heldout_resid(eps, K, E):
    """Residual of the self-calibrated projection on held-out episodes, using the same side/gate rule."""
    XL, XR, UL, UR, _ = _stack(eps)
    out = []
    for X, U, Xo in ((XL, UL, XR), (XR, UR, XL)):
        p, po = C.project_many(K, E, X), C.project_many(K, E, Xo)
        d, do = np.linalg.norm(U - p, axis=1), np.linalg.norm(U - po, axis=1)
        ok = np.isfinite(d) & ~(do + 10 < d)
        out += list(d[ok])
    d = np.asarray(out)
    return {"n": int(len(d)), "median_px": round(float(np.median(d)), 2), "p90_px": round(float(np.percentile(d, 90)), 2),
            "le_25px": round(float((d <= 25).mean()), 4)}


def convert(root, out, urdf="/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf", every=5,
            cache_dir="/data/harvest/out/xemb_proto/cache/rb2", t4_cam=None, t4_heldout=None):
    """t4_cam: npz (E, K) of the T4 silhouette-aligned camera; t4_heldout: its held-out boundary chamfer (px). When given
    and <= T1_GATE_PX, projection QA / C' with camera info use the T4 camera and the FK end-effector point."""
    import cv2
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    eps = load(root)
    rng = np.random.default_rng(0)
    order = rng.permutation(len(eps))
    test = {eps[i]["ep"] for i in order[: len(eps) // 5]}
    tr = [e for e in eps if e["ep"] not in test]
    te = [e for e in eps if e["ep"] in test]
    rep = {"episodes": len(eps), "train_eps": len(tr), "test_eps": len(te)}
    # ---- FK rotations from the raw joint states (for the detector aim-point offset)
    fkmax = 0.0
    for e in eps:
        fr = fk_rot(RAW, e["ep"], urdf)
        for a in ("left", "right"):
            p, R = fr[a]
            fkmax = max(fkmax, float(np.abs(p[: e["n"]] - e["ee"][a]).max()))
            e["R"] = e.get("R", {})
            e["R"][a] = R[: e["n"]]
    rep["fk_rot_pos_check_max_m"] = fkmax

    def stackR(es):
        pL, pR, RL, RR, uL, uR = [], [], [], [], [], []
        for e in es:
            for a, P, Rl, U in (("left", pL, RL, uL), ("right", pR, RR, uR)):
                u = e["uv"][a].copy()
                u[~C.jump_filter(u)] = np.nan
                P.append(e["ee"][a])
                Rl.append(e["R"][a])
                U.append(u)
        return [np.concatenate(v) for v in (pL, RL, pR, RR, uL, uR)]

    # ---- T1 (a): point model (no offset), focal scan -- the simple variant
    pL, RL, pR, RR, uL, uR = stackR(tr)
    fs = C.focal_search(pL, pR, uL, uR, K_SPEC, scales=np.linspace(0.8, 1.3, 26))
    rep["T1_point_model"] = {"fx_found": round(fs["fx"], 1), "resid_median_px": round(fs["fit"]["resid_median_px"], 2),
                             "inlier_frac": round(fs["fit"]["inlier_frac"], 3)}
    # ---- T1 (b): offset model (camera 6 + aim offset 3 per arm + focal 1), robust
    fit = C.selfcal_offset(pL, RL, pR, RR, uL, uR, K_SPEC, fit_fx=True)
    E, K = fit["E"], fit["K"]
    rep["T1"] = {"fx_found": round(float(K[0, 0]), 1), "fx_spec": 367.0,
                 "aim_offset_left_m": [round(float(v), 3) for v in fit["o_left"]],
                 "aim_offset_right_m": [round(float(v), 3) for v in fit["o_right"]],
                 "train": {"resid_median_px": round(fit["resid_median_px"], 2),
                           "resid_p90_px": round(fit["resid_p90_px"], 2), "inlier_frac": round(fit["inlier_frac"], 3),
                           "n": fit["n"]}}

    def held(es, fitx):
        pL, RL, pR, RR, uL, uR = stackR(es)
        d_all = []
        for p, R, u, po, Ro, arm, oth in ((pL, RL, uL, pR, RR, "left", "right"), (pR, RR, uR, pL, RL, "right", "left")):
            pn = C.project_offset(fitx, p, R, arm)
            pot = C.project_offset(fitx, po, Ro, oth)
            d, do = np.linalg.norm(u - pn, axis=1), np.linalg.norm(u - pot, axis=1)
            ok = np.isfinite(d) & ~(do + 10 < d)
            d_all += list(d[ok])
        d = np.asarray(d_all)
        return {"n": int(len(d)), "median_px": round(float(np.median(d)), 2),
                "p90_px": round(float(np.percentile(d, 90)), 2), "le_15px": round(float((d <= 15).mean()), 4),
                "le_25px": round(float((d <= 25).mean()), 4)}

    rep["T1"]["heldout"] = held(te, fit)
    # consistency: per-episode camera pose with the pooled K and aim offsets fixed
    per = []
    for e in eps:
        XLo = e["ee"]["left"] + np.einsum("nij,j->ni", e["R"]["left"], fit["o_left"])
        XRo = e["ee"]["right"] + np.einsum("nij,j->ni", e["R"]["right"], fit["o_right"])
        uL_, uR_ = e["uv"]["left"].copy(), e["uv"]["right"].copy()
        uL_[~C.jump_filter(uL_)] = np.nan
        uR_[~C.jump_filter(uR_)] = np.nan
        f = C.selfcal_two_arm(XLo, XRo, uL_, uR_, K)
        if f is not None and f["n"] >= 40:
            per.append(C.pose_error(f["E"], E) + (f["resid_median_px"],))
    per = np.asarray(per)
    rep["T1"]["per_episode_vs_pooled"] = {
        "n_eps": int(len(per)), "rot_deg_median": round(float(np.median(per[:, 0])), 2),
        "rot_deg_p90": round(float(np.percentile(per[:, 0], 90)), 2),
        "centre_cm_median": round(float(np.median(per[:, 1])) * 100, 2),
        "centre_cm_p90": round(float(np.percentile(per[:, 1], 90)) * 100, 2),
        "resid_median_px": round(float(np.median(per[:, 2])), 2)} if len(per) else None
    if urdf and os.path.exists(urdf):
        En = nominal_E(urdf)
        rot, dist = C.pose_error(E, En)
        rep["T1"]["vs_nominal_urdf_camera"] = {"rot_deg": round(rot, 2), "centre_cm": round(dist * 100, 2)}
        nom = {"E": En, "K": K_SPEC, "o_left": fit["o_left"], "o_right": fit["o_right"]}
        rep["T1"]["heldout_nominal_camera_same_offsets"] = held(te, nom)
    if t4_cam:
        z4 = np.load(t4_cam)
        E, K = z4["E"], z4["K"]
        fit = dict(fit, E=E, K=K, o_left=np.zeros(3), o_right=np.zeros(3))  # T4: camera from silhouettes, EE point
    T_base_cam = G.inv_T(E)
    fit_rb2 = fit
    # ---- samples
    rob_unknown = {"name": "ffw_bg2", "source": "robotis/ffw_bg2_rb2", "arm": "right",
                   "desc": "ROBOTIS AI Worker FFW-BG2 (real robot; positions from its URDF and joint encoders)",
                   "gripper": {"open_gap_m": 0.10}, "workspace": None,
                   "cameras": [{"name": "head camera", "W": W, "H": H, "K": None, "T_base_cam": None}]}
    allee = np.concatenate([np.r_[e["ee"]["left"], e["ee"]["right"]] for e in eps])
    lo, hi = np.percentile(allee, 1, 0), np.percentile(allee, 99, 0)
    rob_unknown["workspace"] = {"x": [lo[0], hi[0]], "y": [lo[1], hi[1]], "z": [lo[2], hi[2]]}
    rob_cal = dict(rob_unknown, cameras=[{"name": "head camera", "W": W, "H": H, "K": K.tolist(),
                                          "T_base_cam": T_base_cam.tolist()}])
    cnt = {k: 0 for k in ("ee_point_detected", "ee_trace_detected", "ee_point_projected", "ee_trace_projected",
                          "control_camera_unknown", "control_with_camera")}
    items = []
    fP = open(os.path.join(out, "records_P.jsonl"), "w")
    fC = open(os.path.join(out, "records_C.jsonl"), "w")
    # T1 gate (<= 5 px held-out): only then projection QA and C' with camera info; otherwise route 4 + pixel labels
    t1_pass = rep["T1"]["heldout"]["median_px"] <= T1_GATE_PX
    if t4_cam and t4_heldout is not None:
        t1_pass = float(t4_heldout) <= T1_GATE_PX
        rep["T4"] = {"camera": t4_cam, "heldout_boundary_chamfer_px": float(t4_heldout), "gate_pass": bool(t1_pass)}
    rep["T1"]["gate_px"] = T1_GATE_PX
    rep["T1"]["gate_pass"] = bool(t1_pass)
    cnt["pixel_agree_rate"] = [0, 0]
    for ei, e in enumerate(eps):
        fdir = os.path.join(root, "frames", "RB2", f"ep{e['ep']:06d}")
        cp = os.path.join(cache_dir, f"RB2_ep{e['ep']:06d}.npz") if cache_dir else None
        trk = TK.load(cp)["fused"] if cp and os.path.exists(cp) else {}
        for a in ("left", "right"):
            X, g = e["ee"][a], e["g"][a]
            uv_det = e["uv"][a].copy()
            uv_det[~C.jump_filter(uv_det)] = np.nan
            tk = trk.get(f"grip_{a}_point", np.full((e["n"], 2), np.nan))[: e["n"]]
            # route 2 + shared front-end: a pixel label where two independent detectors agree (tracker, pointing)
            agree = np.linalg.norm(tk - uv_det, axis=1) <= AGREE_PX
            inimg = (tk[:, 0] >= 12) & (tk[:, 0] <= W - 12) & (tk[:, 1] >= 12) & (tk[:, 1] <= H - 12)
            uv_proj = C.project_offset(fit_rb2, X, e["R"][a], a)
            closed = g > GRIP_CLOSED
            rel = [k for k in range(1, e["n"]) if closed[k - 1] and not closed[k]]
            robot_u, robot_c = dict(rob_unknown, arm=a), dict(rob_cal, arm=a)
            for k in range(0, e["n"], every):
                img = os.path.join(fdir, f"f{k:04d}.jpg")
                if not os.path.exists(img):  # some episodes were decoded only partly (marr_real "need")
                    continue
                nxt = next((r for r in rel if r > k), None)
                if np.isfinite(uv_det[k]).all():
                    cnt["pixel_agree_rate"][1] += 1
                    cnt["pixel_agree_rate"][0] += bool(agree[k])
                if agree[k] and inimg[k]:
                    fP.write(json.dumps(F.qa_point(robot_u, "ee_point_detected", tk[k], 0, img,
                                                   f"rb2_{e['ep']}_{k}_{a}_det")) + "\n")
                    cnt["ee_point_detected"] += 1
                    if nxt is not None:
                        idx = np.linspace(k, nxt, 5).round().astype(int)
                        tr_det = tk[idx]
                        if np.isfinite(tr_det).all() and inimg[idx].all():
                            fP.write(json.dumps(F.qa_trace(robot_u, tr_det, 0, img, f"rb2_{e['ep']}_{k}_{a}_trd",
                                                           arm=a)) + "\n")
                            cnt["ee_trace_detected"] += 1
                if t1_pass and np.isfinite(uv_proj[k]).all() and 0 <= uv_proj[k][0] < W and 0 <= uv_proj[k][1] < H:
                    fP.write(json.dumps(F.qa_point(robot_c, "ee_point", uv_proj[k], 0, img,
                                                   f"rb2_{e['ep']}_{k}_{a}_proj")) + "\n")
                    cnt["ee_point_projected"] += 1
                if ei < 12 and k % 20 == 0:
                    items.append({"img": img, "ee": uv_proj[k] if np.isfinite(uv_proj[k]).all() else None,
                                  "obj": tk[k] if np.isfinite(tk[k]).all() else None,
                                  "place": uv_det[k] if np.isfinite(uv_det[k]).all() else None,
                                  "label": f"rb2 ep{e['ep']} {a[0]} f{k} T1=red trk=green pt=yellow"})
            # route 4: C' from FK (targets in arm_base_link), camera unknown; with camera only if T1 passed
            if not rel and not closed.any():
                continue
            segs = S.segment(X, closed, None)
            hist = []
            for si, s in enumerate(segs):
                for k in S.sample_frames(s, 1):
                    img = os.path.join(fdir, f"f{k:04d}.jpg")
                    if not os.path.exists(img):
                        continue
                    for robot, key in ((robot_u, "control_camera_unknown"), (robot_c, "control_with_camera")):
                        if key == "control_with_camera" and not t1_pass:
                            continue
                        r = F.control_record(robot, s, k, X[k], 0.10 * max(0.0, 1 - g[k] / 1.1), task_of(e), "object",
                                             "target", hist, first=(si == 0), images=[img],
                                             rid=f"rb2_{e['ep']}_{a}_{k}_{s['step']}_{key[8:11]}")
                        fC.write(json.dumps(r) + "\n")
                        cnt[key] += 1
                if s["target"] is not None:
                    t = s["target"]
                    hist.append(f"{len(hist) + 1}: eef to ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}), gripper {s['gripper']}")
    fP.close()
    fC.close()
    rep["counts"] = cnt
    rep["K_used"] = K.tolist()
    rep["T_base_cam"] = T_base_cam.tolist()
    return rep, items
