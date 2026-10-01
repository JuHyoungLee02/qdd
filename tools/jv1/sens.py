"""E-JV1 destination sensitivity (docs/stage3/prereg_jv1.md §5, the prereg_jcr1 change-3 metric in a kinematic
closed loop with the MODEL in JCR's place). For N held-out d1 decisions (fixed stride, non-stop, |goal - tcp| > 2 cm):
roll the commanded TCP for 2 s (10 decisions x 4 ticks, model re-asked every 0.2 s with the updated commanded TCP /
velocity / command age, same images -- a kinematic approximation), executed through the same rule as the closed loop
(envelope B priority blend with the upper's destination, truth.blend_rows), once with the recorded command and once
with the command moved 5 cm horizontally (fixed random direction per decision). Sensitivity = projection of the end
point shift on the move direction / 5 cm (1 = follows the upper's destination fully, 0 = ignores it).
Arm C (no server) = the truth waypoint through the text quantisation.
  python tools/jv1/sens.py --url http://IP:PORT|truth --data d1 --select ... --n 100 --out sens_A.json"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from harvest.jcr import truth as T  # noqa: E402
from harvest.jv1.realtime import quantize  # noqa: E402

_spec = importlib.util.spec_from_file_location("jcr_train", os.path.join(ROOT, "tools", "jcr", "train.py"))
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)
KEYS = ("k", "t", "tcp", "p_cmd", "v", "goal_cmd", "r_goal", "allow", "kappa", "height", "cmd_age", "q", "grip_w",
        "effort")
MOVE_M = 0.05


def rollout(act, s0, goal, imgs, n_dec=10):
    s = {k: s0[k] for k in KEYS if k in s0}
    s.update(goal_cmd=list(map(float, goal)), allow=None)  # no gripper action during the probe
    p, v = np.asarray(s["p_cmd"], float), np.asarray(s["v"], float)
    for d in range(n_dec):
        s.update(p_cmd=p.tolist(), tcp=p.tolist(), v=v.tolist(), cmd_age=float(s0.get("cmd_age", 0.0)) + 0.2 * d)
        o = act(s, imgs)
        P = p[None] + np.asarray(o["delta"], float)
        P = T.blend_rows(p, v, P, goal, T.MODE_PRIO["B"], float(s.get("kappa", 0.9)), s["cmd_age"])
        p_new = P[3]
        v = (P[3] - P[2]) / T.DT
        p = p_new
    return p


def main(argv=None):
    from PIL import Image
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="model server URL, or 'truth' (arm C)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--select", default="")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    _, va = J.load_data([a.data], "B", a.select)
    cand = [s for s in va if not s.get("stop") and
            np.linalg.norm(np.asarray(s["goal_cmd"]) - np.asarray(s["tcp"])) > 0.02]
    cand = cand[::max(1, len(cand) // a.n)][:a.n]
    if a.url == "truth":
        def act(s, imgs, gt=None):
            c = quantize(act.gt)
            return {"delta": (T.smooth_chunk(s["p_cmd"], s["v"], c)[0] - np.asarray(s["p_cmd"])).tolist()}
    else:
        from harvest.jcr.serve import Client
        cl = Client(a.url)

        def act(s, imgs):
            return cl.act(s, imgs[0], imgs[1])
    rng = np.random.default_rng(0)
    sens = []
    for s in cand:
        imgs = [np.asarray(Image.open(p).convert("RGB")) for _, p in s["_imgs"]]
        act.gt = np.asarray(s["goal_true"], float)
        ang = rng.uniform(0, 2 * np.pi)
        u = np.array([np.cos(ang), np.sin(ang), 0.0])
        g0 = np.asarray(s["goal_cmd"], float)
        e0 = rollout(act, s, g0, imgs)
        e1 = rollout(act, s, g0 + MOVE_M * u, imgs)
        sens.append(float(np.dot(e1 - e0, u)) / MOVE_M)
    res = {"url": a.url, "n": len(sens), "sens_mean": float(np.mean(sens)), "sens_p50": float(np.median(sens)),
           "sens_p10": float(np.percentile(sens, 10)), "move_m": MOVE_M, "rule": "B", "prio": T.MODE_PRIO["B"]}
    json.dump(res, open(a.out, "w"), indent=1)
    print("SENS " + json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
