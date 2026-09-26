"""Track T1 'create the frame': camera calibration from the data itself (no calibration shipped).

Inputs per frame: FK 3-D gripper position of each arm in the robot base frame (URDF + joint states) and a detected 2-D
gripper point per arm (pointing model or tracker, possibly wrong / on the other arm). Method:
  1. pool both arms' (3-D, 2-D) pairs, OpenCV EPnP inside RANSAC (reprojection threshold thr px) with the intrinsics
     from the camera model (e.g. ZED Mini VGA fx 367) -> camera pose;
  2. side re-assignment: a detection is kept for its named arm only if its reprojection distance to that arm is below
     the gate and clearly smaller than to the other arm (fixes the pointing model's other-arm errors, 17-20 % on RB2);
  3. Levenberg-Marquardt refinement on the kept pairs;
  optional: focal_search = 1-D scan of fx (= fy, principal point at the image centre) minimising the refined median
  residual -- the joint intrinsics solve when the camera model is unknown.
Earlier on the same data a free 3x4 DLT per episode failed (tools/marr, readiness 4.2: 12-71 % inliers at 15 px): the
DLT has 11 unknowns and absorbs the detector noise; PnP with known intrinsics has 6.
"""
from __future__ import annotations

import numpy as np

from . import geom as G


def _rt_to_E(rvec, tvec):
    import cv2
    E = np.eye(4)
    E[:3, :3] = cv2.Rodrigues(np.asarray(rvec, float))[0]
    E[:3, 3] = np.asarray(tvec, float).ravel()
    return E


def project_many(K, E, X):
    X = np.asarray(X, float)
    pc = X @ E[:3, :3].T + E[:3, 3]
    uv = (pc @ np.asarray(K, float).T)[:, :2] / pc[:, 2:3]
    uv[pc[:, 2] <= 0] = np.nan
    return uv


def pnp_ransac(X, uv, K, thr: float = 20.0, iters: int = 3000, seed: int = 0):
    import cv2
    X = np.ascontiguousarray(X, dtype=np.float64)
    uv = np.ascontiguousarray(uv, dtype=np.float64)
    if len(X) < 6:
        return None
    cv2.setRNGSeed(seed)
    ok, rvec, tvec, inl = cv2.solvePnPRansac(X, uv, np.asarray(K, float), None, iterationsCount=iters,
                                             reprojectionError=thr, confidence=0.999, flags=cv2.SOLVEPNP_EPNP)
    if not ok or inl is None or len(inl) < 6:
        return None
    m = np.zeros(len(X), bool)
    m[inl.ravel()] = True
    rvec, tvec = cv2.solvePnPRefineLM(X[m], uv[m], np.asarray(K, float), None, rvec, tvec)
    return _rt_to_E(rvec, tvec)


def refine(X, uv, K, E):
    import cv2
    rvec = cv2.Rodrigues(E[:3, :3])[0]
    rvec, tvec = cv2.solvePnPRefineLM(np.ascontiguousarray(X, np.float64), np.ascontiguousarray(uv, np.float64),
                                      np.asarray(K, float), None, rvec, E[:3, 3].reshape(3, 1).copy())
    return _rt_to_E(rvec, tvec)


def _valid(u):
    return np.isfinite(np.asarray(u, float)).all(1)


def selfcal_two_arm(XL, XR, uL, uR, K, thr: float = 20.0, gate: float = 25.0, margin: float = 10.0,
                    rounds: int = 3, seed: int = 0) -> dict | None:
    """-> {"E" (base -> cam), "keepL", "keepR", "resid_median_px", "resid_p90_px", "inlier_frac", "n"}"""
    XL, XR, uL, uR = (np.asarray(a, float) for a in (XL, XR, uL, uR))
    vL, vR = _valid(uL), _valid(uR)
    X = np.r_[XL[vL], XR[vR]]
    U = np.r_[uL[vL], uR[vR]]
    E = pnp_ransac(X, U, K, thr=thr, seed=seed)
    if E is None:
        return None
    keepL = keepR = None
    for _ in range(rounds):
        pL, pR = project_many(K, E, XL), project_many(K, E, XR)
        dLL = np.linalg.norm(uL - pL, axis=1)
        dLR = np.linalg.norm(uL - pR, axis=1)
        dRR = np.linalg.norm(uR - pR, axis=1)
        dRL = np.linalg.norm(uR - pL, axis=1)
        keepL = vL & (dLL < gate) & ~(dLR + margin < dLL)
        keepR = vR & (dRR < gate) & ~(dRL + margin < dRR)
        Xk, Uk = np.r_[XL[keepL], XR[keepR]], np.r_[uL[keepL], uR[keepR]]
        if len(Xk) < 6:
            return None
        E = refine(Xk, Uk, K, E)
    Xk, Uk = np.r_[XL[keepL], XR[keepR]], np.r_[uL[keepL], uR[keepR]]
    r = np.linalg.norm(project_many(K, E, Xk) - Uk, axis=1)
    return {"E": E, "keepL": keepL, "keepR": keepR, "resid_median_px": float(np.median(r)),
            "resid_p90_px": float(np.percentile(r, 90)), "inlier_frac": float(len(Xk) / max(1, vL.sum() + vR.sum())),
            "n": int(len(Xk))}


def focal_search(XL, XR, uL, uR, K, scales=np.linspace(0.7, 1.4, 29), **kw) -> dict:
    """Joint focal solve: fx = fy = s * K[0,0] for s in scales; score = inliers / (1 + median residual)."""
    best = None
    for s in scales:
        Ks = np.array(K, float).copy()
        Ks[0, 0] = Ks[1, 1] = K[0][0] * s
        f = selfcal_two_arm(XL, XR, uL, uR, Ks, **kw)
        if f is None:
            continue
        score = f["n"] / (1.0 + f["resid_median_px"])
        if best is None or score > best["score"]:
            best = {"fx": float(Ks[0, 0]), "score": float(score), "fit": f}
    return best


def _rodrigues(r):
    th = float(np.linalg.norm(r))
    if th < 1e-12:
        return np.eye(3)
    k = np.asarray(r, float) / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def _rvec(R):
    """Rotation vector of R (OpenCV Rodrigues: also correct near 180 deg, where the closed form divides by ~0 --
    the MolmoBot head camera sits ~130-180 deg from the base axes, hide-and-recover run 1)."""
    import cv2
    return cv2.Rodrigues(np.asarray(R, float))[0].ravel()


def _proj_param(theta, K0, pts, Rs, arm_idx, fit_fx):
    R = _rodrigues(theta[:3])
    t = theta[3:6]
    o = np.stack([theta[6:9], theta[9:12]])[arm_idx]  # (N, 3) offset per arm in the EE frame
    X = pts + np.einsum("nij,nj->ni", Rs, o)
    pc = X @ R.T + t
    f = K0[0, 0] * (np.exp(theta[12]) if fit_fx else 1.0)
    z = np.where(np.abs(pc[:, 2]) < 1e-6, 1e-6, pc[:, 2])
    return np.stack([f * pc[:, 0] / z + K0[0, 2], f * pc[:, 1] / z + K0[1, 2]], 1)


def selfcal_offset(pL, RL, pR, RR, uL, uR, K, fit_fx: bool = True, huber: float = 8.0, gate: float = 25.0,
                   margin: float = 10.0, rounds: int = 3, iters: int = 15) -> dict | None:
    """T1 with the detector's aim point unknown: the pointing model marks the gripper body, not the URDF end-effector
    point, so a constant 3-D offset per arm in the end-effector frame (o_L, o_R) is solved with the camera pose
    (6) and optionally the focal (1): u ~ pi(K(f), E (p + R o)). Init = selfcal_two_arm (o = 0); robust (Huber) Gauss-
    Newton with a numerical Jacobian; sides / gate re-assigned each round."""
    pL, pR, uL, uR = (np.asarray(a, float) for a in (pL, pR, uL, uR))
    RL, RR = np.asarray(RL, float), np.asarray(RR, float)
    init = selfcal_two_arm(pL, pR, uL, uR, K, gate=gate * 2, margin=margin)
    if init is None:
        return None
    E = init["E"]
    theta = np.r_[_rvec(E[:3, :3]), E[:3, 3], np.zeros(6), 0.0]
    K0 = np.asarray(K, float)
    vL, vR = _valid(uL), _valid(uR)
    nL = len(pL)
    pts_all = np.r_[pL, pR]
    Rs_all = np.r_[RL, RR]
    arm_all = np.r_[np.zeros(nL, int), np.ones(len(pR), int)]
    U_all = np.r_[uL, uR]
    keep = np.r_[init["keepL"], init["keepR"]]
    n_par = 13 if fit_fx else 12
    for _ in range(rounds):
        for _ in range(iters):
            idx = np.nonzero(keep)[0]
            if len(idx) < 12:
                return None
            res = (_proj_param(theta, K0, pts_all[idx], Rs_all[idx], arm_all[idx], fit_fx) - U_all[idx]).ravel()
            a = np.abs(res)
            w = np.where(a <= huber, 1.0, huber / np.maximum(a, 1e-9))
            J = np.zeros((len(res), n_par))
            for j in range(n_par):
                d = np.zeros_like(theta)
                d[j] = 1e-6 if j < 3 or j == 12 else 1e-5
                J[:, j] = ((_proj_param(theta + d, K0, pts_all[idx], Rs_all[idx], arm_all[idx], fit_fx)
                            - U_all[idx]).ravel() - res) / d[j]
            Jw = J * w[:, None]
            A = Jw.T @ J + 1e-3 * np.eye(n_par)
            step = np.linalg.solve(A, -Jw.T @ res)
            theta[:n_par] += step
            if np.linalg.norm(step) < 1e-7:
                break
        # re-assign sides and gate with the current model
        P_named = _proj_param(theta, K0, pts_all, Rs_all, arm_all, fit_fx)
        P_other = _proj_param(theta, K0, np.r_[pR, pL], np.r_[RR, RL], 1 - arm_all, fit_fx)
        d_n = np.linalg.norm(U_all - P_named, axis=1)
        d_o = np.linalg.norm(U_all - P_other, axis=1)
        keep = np.r_[vL, vR] & (d_n < gate) & ~(d_o + margin < d_n)
    idx = np.nonzero(keep)[0]
    if len(idx) < 12:
        return None
    r = np.linalg.norm(_proj_param(theta, K0, pts_all[idx], Rs_all[idx], arm_all[idx], fit_fx) - U_all[idx], axis=1)
    Eo = np.eye(4)
    Eo[:3, :3] = _rodrigues(theta[:3])
    Eo[:3, 3] = theta[3:6]
    Kf = K0.copy()
    Kf[0, 0] = Kf[1, 1] = K0[0, 0] * (np.exp(theta[12]) if fit_fx else 1.0)
    return {"E": Eo, "K": Kf, "o_left": theta[6:9].copy(), "o_right": theta[9:12].copy(), "keep": keep,
            "resid_median_px": float(np.median(r)), "resid_p90_px": float(np.percentile(r, 90)),
            "inlier_frac": float(len(idx) / max(1, vL.sum() + vR.sum())), "n": int(len(idx))}


def project_offset(fit, p, R, arm):
    o = fit["o_left"] if arm == "left" else fit["o_right"]
    X = np.asarray(p, float) + np.einsum("nij,j->ni", np.asarray(R, float), o)
    return project_many(fit["K"], fit["E"], X)


def pose_error(E1, E2):
    """-> (rotation angle deg, camera-centre distance m) between two base -> cam transforms."""
    dR = E1[:3, :3] @ E2[:3, :3].T
    ang = float(np.degrees(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1))))
    c1 = -E1[:3, :3].T @ E1[:3, 3]
    c2 = -E2[:3, :3].T @ E2[:3, 3]
    return ang, float(np.linalg.norm(c1 - c2))


def jump_filter(u, win: int = 2, max_px: float = 40.0) -> np.ndarray:
    """Tracker-style cleaning of a per-frame detection track: drop missing points and points farther than max_px from
    the median of their +-win neighbours (the MolmoAct pipeline has no such filter; readiness F3)."""
    u = np.asarray(u, float)
    ok = _valid(u)
    keep = ok.copy()
    for i in np.nonzero(ok)[0]:
        nb = [j for j in range(max(0, i - win), min(len(u), i + win + 1)) if j != i and ok[j]]
        if len(nb) >= 2:
            med = np.median(u[nb], 0)
            if np.linalg.norm(u[i] - med) > max_px:
                keep[i] = False
    return keep


def camera_T_base_cam(E):
    return G.inv_T(E)
