"""Calibrated C' records -> D / H rows (user-log 158: ready-to-run D / H converters for every calibrated candidate).
A C' row carries the step target (answer command.position_m, robot base frame) and, in its prompt, the head camera
(fx fy cx cy, position, axes). D label = the target projected into the head image + the height intent of the step:
  descend_close -> grasp (the object)   lower_open -> place (the place)
  (above_target / carry_over key poses are in the air above the object: their projection misses it -> not used)
Camera: the EXACT camera when given (T4 npz for RB2 / RB3), else parsed from the prompt (2-decimal pose -> the
projection gate measures that rounding on the sources where both exist). H rows only where a metric depth map exists
for the image (RB2 stereo frames that passed the 2 cm arm gate): depth image + position_m.
Gates: point inside the image (12 px border), in front of the camera; for exact-camera sources the camera itself passed
the T4 <= 5 px held-out gate; parsed-camera projection vs exact <= 5 px measured on RB2 (report 'proj_parsed_vs_exact').
usage (pod): python -m xemb.cp_to_dh RECORDS_C OUT_DIR NAME [--cam NPZ] [--depth DIR] [--n N]"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

from . import dh as DH

INTENT = {"descend_close": ("grasp", 0), "lower_open": ("place", 1)}  # contact steps only: the TCP key pose of
# above_target / carry_over is in the air, so its projection is not on the object (eye check)
_CAM = re.compile(r"(\d+)x(\d+) px, fx ([\d.]+) fy ([\d.]+) cx ([\d.]+) cy ([\d.]+); at \(([-\d., ]+)\) m, looking along "
                  r"\(([-+\d., ]+)\); image right = \(([-+\d., ]+)\), image down = \(([-+\d., ]+)\)")
_NAMES = [re.compile(p) for p in (r"move the TCP (?:about 10 cm )?above the (.+)$", r"lower to the (.+?) and close on it",
                                  r"carry the (.+?) above the (.+)$", r"lower the (.+?) onto the (.+?) and release it")]


def parse_cam(prompt):
    m = _CAM.search(prompt)
    if not m:
        return None
    v = lambda s: np.array([float(x) for x in s.split(",")])
    W, H = int(m.group(1)), int(m.group(2))
    K = np.array([[float(m.group(3)), 0, float(m.group(5))], [0, float(m.group(4)), float(m.group(6))], [0, 0, 1]])
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = v(m.group(9)), v(m.group(10)), v(m.group(8)), v(m.group(7))
    return W, H, K, T


def names_of(doing):
    for p in _NAMES:
        m = p.search(doing)
        if m:
            g = m.groups()
            return g[0], (g[1] if len(g) > 1 else g[0])
    return None


def project(K, T_base_cam, x):
    pc = np.linalg.inv(T_base_cam) @ np.r_[x, 1.0]
    if pc[2] <= 0.05:
        return None
    return np.array([K[0, 0] * pc[0] / pc[2] + K[0, 2], K[1, 1] * pc[1] / pc[2] + K[1, 2]])


def convert(rec_path, out, source_name, cam=None, depth_dir=None, n=None):
    import cv2
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    exact = None
    if cam:
        z = np.load(cam)
        E = z["E_head"] if "E_head" in z.files else z["E"]
        exact = (z["K"].astype(float), np.linalg.inv(E.astype(float)))
    st = {"rows_in": 0, "step_ok": 0, "named": 0, "in_image": 0, "D": 0, "H": 0, "proj_parsed_vs_exact_px": []}
    fD, fH = open(os.path.join(out, "records_D.jsonl"), "w"), open(os.path.join(out, "records_H.jsonl"), "w")
    for line in open(rec_path):
        if n is not None and st["D"] >= n:
            break
        r = json.loads(line)
        st["rows_in"] += 1
        if r.get("step") not in INTENT or "camera: unknown" in r["prompt"]:
            continue
        a = json.loads(r["answer"])
        tgt = (a.get("command") or {}).get("position_m")
        if tgt is None:
            continue
        st["step_ok"] += 1
        intent, which = INTENT[r["step"]]
        nm = names_of(a["assessment"]["task_progress"]["currently_attempting"])
        if nm is None or nm[which] in ("object", "target", "item", "place"):
            continue
        st["named"] += 1
        pc = parse_cam(r["prompt"])
        if pc is None:
            continue
        W, H, K, T = pc
        uv_p = project(K, T, np.array(tgt))
        if exact is not None:
            K, T = exact
        uv = project(K, T, np.array(tgt))
        if uv is None or not (12 <= uv[0] <= W - 12 and 12 <= uv[1] <= H - 12):
            continue
        if exact is not None and uv_p is not None:
            st["proj_parsed_vs_exact_px"].append(float(np.linalg.norm(uv_p - uv)))
        st["in_image"] += 1
        img = r["images"][0]
        if not os.path.isabs(img):  # converter records keep paths relative to the xemb_proto root
            img = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(rec_path))), img)
        images = [img]
        if depth_dir:
            m = re.search(r"ep(\d+)/f(\d+)\.jpg$", img)
            dp = m and os.path.join(depth_dir, f"ep{int(m.group(1)):06d}_f{int(m.group(2)):04d}.npz")
            if dp and os.path.exists(dp):
                pd = os.path.join(out, "frames", f"{r['id']}_depth.png")
                if not os.path.exists(pd):
                    cv2.imwrite(pd, DH.encode_depth(np.load(dp)["depth"].astype(float)))
                images.append(pd)
        robot = {"name": r["frame"].replace("base_", ""), "source": r["source"]}
        d, h = DH.rows(robot, W, H, K, T, uv, tgt, nm[which], images, f"{source_name}_{r['id']}", intent)
        fD.write(json.dumps(d) + "\n")
        st["D"] += 1
        if h is not None:
            fH.write(json.dumps(h) + "\n")
            st["H"] += 1
    fD.close()
    fH.close()
    e = np.array(st.pop("proj_parsed_vs_exact_px"))
    st["proj_parsed_vs_exact_px"] = {"median": round(float(np.median(e)), 2), "p90": round(float(np.percentile(e, 90)), 2),
                                     "le5": round(float((e <= 5).mean()), 3)} if len(e) else None
    json.dump(st, open(os.path.join(out, "report.json"), "w"), indent=1)
    return st


if __name__ == "__main__":
    a = sys.argv[1:]
    kw = {}
    for flag, key, typ in (("--cam", "cam", str), ("--depth", "depth_dir", str), ("--n", "n", int)):
        if flag in a:
            i = a.index(flag)
            kw[key] = typ(a[i + 1])
            del a[i:i + 2]
    print(json.dumps(convert(a[0], a[1], a[2], **kw), indent=1))
