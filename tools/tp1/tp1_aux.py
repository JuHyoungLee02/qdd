"""E-TP1 arm 4 "on + perspective-aux" (prereg_tp1 change 3; docs/research/perspective_frames_2026-10-02.md §4 (2)):
auxiliary rows made at BUILD time from simulator ground truth, no re-render, on the existing ego (head) and third-person
images of the "on" set. Every directional word is in the ROBOT BASE FRAME (left = robot +y, right = -y, front = +x =
away from the robot, behind = -x); the labels come from robot-frame positions (labels gt) and the camera records
(cams.json head / tp9 external_cams; R columns = optical x, y, z in the robot frame, t = centre). One projection
function (project) for every label; no mirror-flip augmentation; no camera pose text in the aux prompts.
  P point_dir   "point to the table spot ~12 cm to the robot's <dir> of the <object>"  -> {"point_2d": [x, y]} 0-1000
  Q relation    "from the robot's view, is the <object> left / right / in front of / behind the gripper?" -> {"relation"}
  Y camera_yaw  "which way does this camera look relative to the robot's forward direction?" -> {"camera_facing"}
usage (pod python, PYTHONPATH = code dir):
  tp1_aux.py check <rows.jsonl>                          projection check: gt target vs the labels' head pixels
  tp1_aux.py train <train_on.jsonl> <out.jsonl> [--frac 0.15] [--seed 0]   on rows + aux rows (aux <= 15 % of rows)
  tp1_aux.py eval <ego eval.jsonl> <tp eval.jsonl> <out.jsonl> [--cap 2400]  stratified P/Q/Y hold-out items"""
import hashlib
import json
import math
import os
import sys
from collections import Counter

import numpy as np

DIRS = {"left": (0.0, 1.0), "right": (0.0, -1.0), "front": (1.0, 0.0), "behind": (-1.0, 0.0)}
OPP = {"left": "right", "right": "left", "front": "behind", "behind": "front"}
STEP_M = 0.12
HEAD = ("Image 1 is a camera view of the robot's workspace. Directions are in the robot's frame (the robot's own "
        "left and right; front = away from the robot, behind = toward the robot), not the camera image.\n")
P_ASK = ('Point to the table spot about 12 cm to the robot\'s {d} of the {name}.\n'
         'Return JSON only: {{"point_2d": [x, y]}} with x, y in 0-1000 of image 1.')
P_ASK_FB = ('Point to the table spot about 12 cm {d} the {name} (robot frame).\n'
            'Return JSON only: {{"point_2d": [x, y]}} with x, y in 0-1000 of image 1.')
Q_ASK = ('From the robot\'s point of view, is the {name} to the left of, to the right of, in front of, or behind the '
         'gripper?\nReturn JSON only: {{"relation": "left" | "right" | "front" | "behind"}}.')
Y_ASK = ('Relative to the direction the robot faces, which way does the camera of image 1 look?\n'
         'Return JSON only: {{"camera_facing": "same" | "left" | "right" | "toward"}} (same = the robot\'s forward '
         'direction, toward = facing the robot).')


def project(cam: dict, X) -> tuple:
    """(u, v) pixels and depth of a robot-frame point (grasp9.project convention)."""
    R, t = np.asarray(cam["R"], float), np.asarray(cam["t"], float)
    xc = (np.asarray(X, float) - t) @ R
    z = float(xc[2])
    if z <= 1e-6:
        return None, None, z
    return float(xc[0] / z * cam["fx"] + cam["cx"]), float(xc[1] / z * cam["fy"] + cam["cy"]), z


def n1000(cam, u, v):
    return [round(u / cam["W"] * 1000), round(v / cam["H"] * 1000)]


def inside(cam, u, v, m=0.03):
    return u is not None and m * cam["W"] <= u <= (1 - m) * cam["W"] and m * cam["H"] <= v <= (1 - m) * cam["H"]


def facing(cam):
    f = np.asarray(cam["R"], float)[:, 2]
    yaw = math.degrees(math.atan2(f[1], f[0]))
    if abs(yaw) <= 45:
        return "same", yaw
    if abs(yaw) >= 135:
        return "toward", yaw
    return ("left" if yaw > 0 else "right"), yaw


_META = {}


def meta_of(row):
    ep = os.path.dirname(os.path.dirname(row["call_dir"]))
    if ep not in _META:
        _META[ep] = json.load(open(os.path.join(ep, "meta.json")))
    return _META[ep]


def views_of(row):
    """[(view, image path, camera record)] of a control row: the head image (ego rows) or the third-person image."""
    from harvest.l9 import tp9
    out = []
    iv = row.get("image_views") or ["head"]
    if row.get("third_person"):
        k = row.get("third_person_cam")
        _, ext = tp9.external_cams(row["call_dir"])
        if k in ext and "third_person" in iv:
            out.append(("third_person", row["images"][iv.index("third_person")], ext[k]))
    else:
        cams = json.load(open(row["cams_path"]))
        out.append(("head", row["images"][0], cams["head"]))
    return out


def rng_of(key, seed=0):
    return np.random.default_rng(int(hashlib.sha256(f"tp1aux:{seed}:{key}".encode()).hexdigest()[:12], 16))


def make(row, kind, view, img, cam, rng):
    """-> aux dict (with a 'truth' block) or None."""
    gt = row.get("gt") or {}
    tgt = row.get("tgt")
    name = ((meta_of(row).get("objects") or {}).get(tgt) or {}).get("name")
    base = {"kind": "aux", "arm": "persp", "aux_kind": kind, "images": [img], "view": view, "gen": "l9",
            "robot": row.get("robot"), "head_cam_mode": row.get("head_cam_mode"), "src_id": row["id"]}
    if kind == "P":
        X = gt.get("tgt")
        if not (X and name):
            return None
        for d in rng.permutation(list(DIRS)):
            dx, dy = DIRS[d]
            z = float(row.get("table_z") or X[2])
            pt = [X[0] + STEP_M * dx, X[1] + STEP_M * dy, z]
            po = [X[0] - STEP_M * dx, X[1] - STEP_M * dy, z]
            u, v, _ = project(cam, pt)
            uo, vo, _ = project(cam, po)
            if inside(cam, u, v) and inside(cam, uo, vo):
                ask = P_ASK.format(d=d, name=name) if d in ("left", "right") else \
                    P_ASK_FB.format(d="in front of" if d == "front" else "behind", name=name)
                return dict(base, id=f"{row['id']}_persp_P", prompt=HEAD + ask,
                            answer=json.dumps({"point_2d": n1000(cam, u, v)}),
                            truth={"dir": d, "px": [u, v], "px_opp": [uo, vo], "W": cam["W"], "H": cam["H"]})
        return None
    if kind == "Q":
        A, B = gt.get("tgt"), gt.get("tcp")
        if not (A and B and name):
            return None
        dx, dy = A[0] - B[0], A[1] - B[1]
        if max(abs(dx), abs(dy)) < 0.05 or max(abs(dx), abs(dy)) < 1.5 * min(abs(dx), abs(dy)):
            return None
        rel = ("left" if dy > 0 else "right") if abs(dy) > abs(dx) else ("front" if dx > 0 else "behind")
        return dict(base, id=f"{row['id']}_persp_Q", prompt=HEAD + Q_ASK.format(name=name),
                    answer=json.dumps({"relation": rel}), truth={"relation": rel})
    if kind == "Y":
        f, yaw = facing(cam)
        return dict(base, id=f"{row['id']}_persp_Y", prompt=HEAD + Y_ASK, answer=json.dumps({"camera_facing": f}),
                    truth={"camera_facing": f, "yaw_deg": round(yaw, 1)})
    raise ValueError(kind)


def check(path, n=300):
    errs, k = [], 0
    for x in open(path, encoding="utf-8"):
        r = json.loads(x)
        if r.get("kind", "control") != "control" or r.get("third_person"):
            continue
        tgt, gt, px = r.get("tgt"), r.get("gt") or {}, r.get("pixels") or {}
        if not (tgt and gt.get("tgt") and px.get(tgt)):
            continue
        cam = json.load(open(r["cams_path"]))["head"]
        u, v, _ = project(cam, gt["tgt"])
        if u is None:
            continue
        q = n1000(cam, u, v)
        errs.append(math.hypot(q[0] - px[tgt][0], q[1] - px[tgt][1]))
        k += 1
        if k >= n:
            break
    e = np.array(errs)
    res = {"n": len(e), "median_n1000": round(float(np.median(e)), 2), "p95_n1000": round(float(np.percentile(e, 95)), 2)}
    tp_in, tp_n = 0, 0  # third-person cameras: the target must mostly project inside the image (same frame convention)
    for x in open(path.replace("train_off", "train_on"), encoding="utf-8"):
        r = json.loads(x)
        if not r.get("third_person") or not (r.get("gt") or {}).get("tgt"):
            continue
        for view, img, cam in views_of(r):
            u, v, _ = project(cam, r["gt"]["tgt"])
            tp_in += inside(cam, u, v, 0.0)
            tp_n += 1
        if tp_n >= n:
            break
    res.update(tp_n=tp_n, tp_inside=round(tp_in / max(tp_n, 1), 3))
    print(json.dumps(res))
    if not len(e) or res["median_n1000"] > 15 or (tp_n and res["tp_inside"] < 0.7):
        sys.exit(3)
    return res


def train(src, dst, frac=0.15, seed=0):
    raw = open(src, "rb").read()
    rows = [json.loads(x) for x in raw.decode().splitlines()]
    seen, ctrl = set(), []
    for r in rows:
        if r.get("kind", "control") == "control" and not r.get("label_missing") and r["id"] not in seen:
            seen.add(r["id"])
            ctrl.append(r)
    want = int(frac * len(rows))
    order = np.random.default_rng(seed).permutation(len(ctrl))
    kinds = ("P", "P", "P", "Q", "Q", "Q", "Y", "Y")  # about 3 : 3 : 2
    aux, c = [], Counter()
    for j, i in enumerate(order):
        if len(aux) >= want:
            break
        r = ctrl[i]
        rng = rng_of(r["id"], seed)
        for view, img, cam in views_of(r):
            kd = kinds[j % len(kinds)]
            a = make(r, kd, view, img, cam, rng)
            if a is not None:
                aux.append(a)
                c[(kd, view)] += 1
            else:
                c[("skip_" + kd, view)] += 1
    with open(dst, "wb") as f:
        f.write(raw)
        f.write("".join(json.dumps(a) + "\n" for a in aux).encode())
    share = len(aux) / (len(rows) + len(aux))
    res = {"on_rows": len(rows), "aux_rows": len(aux), "aux_share": round(share, 4),
           "by_kind_view": {f"{k[0]}/{k[1]}": v for k, v in sorted(c.items())},
           "relation_dist": dict(Counter(json.loads(a["answer"])["relation"] for a in aux if a["aux_kind"] == "Q")),
           "facing_dist": dict(Counter(json.loads(a["answer"])["camera_facing"] for a in aux if a["aux_kind"] == "Y"))}
    print(json.dumps(res))
    if share > 0.15:
        sys.exit(3)
    return res


def eval_items(ego_path, tp_path, dst, cap=2400, seed=0):
    items = []
    for path in (ego_path, tp_path):
        for x in open(path, encoding="utf-8"):
            r = json.loads(x)
            if r.get("kind", "control") != "control" or r.get("label_missing"):
                continue
            for view, img, cam in views_of(r):
                rng = rng_of(r["id"], seed + 7)
                stratum = "third_person" if view == "third_person" else (
                    "head_tilt" if r.get("head_cam_mode") == "rand" else "head_std")
                for kd in ("P", "Q", "Y"):
                    a = make(r, kd, view, img, cam, rng)
                    if a is not None:
                        items.append(dict(a, stratum=stratum))
    by = {}
    for a in items:
        by.setdefault((a["stratum"], a["aux_kind"]), []).append(a)
    per = max(1, cap // max(1, len(by)))
    out = []
    for k in sorted(by):
        v = sorted(by[k], key=lambda a: hashlib.sha256(a["id"].encode()).hexdigest())
        out += v[:per]
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        for a in out:
            f.write(json.dumps(a) + "\n")
    res = {"items": len(out), "available": len(items), "strata": {f"{k[0]}/{k[1]}": min(len(v), per) for k, v in sorted(by.items())}}
    print(json.dumps(res))
    return res


def main():
    a = sys.argv[1:]
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    if a[0] == "check":
        check(a[1])
    elif a[0] == "train":
        train(a[1], a[2], float(arg("--frac", "0.15")), int(arg("--seed", "0")))
    elif a[0] == "eval":
        eval_items(a[1], a[2], a[3], int(arg("--cap", "2400")))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
