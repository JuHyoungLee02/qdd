"""OXE ManiSkill (maniskill_dataset_converted_externally_to_rlds 0.1.0, gs://gresearch/robotics, public) -> D / H depth
rows (xemb.dh). The only OXE depth dataset in the user-log 156 list whose features state BOTH the depth unit
(uint16 / 2**10 = m) and the calibration (main_camera_intrinsic_cv, main_camera_extrinsic_cv = world -> camera in
OpenCV axes, base_pose / tcp_pose / target_object_or_part_initial_pose in the world frame, [x, y, z, qw, qx, qy, qz]).
Reads RLDS TFRecord shards without TensorFlow (minimal tf.train.Example wire-format parser).
Gates per state (before the first close, object at its initial pose):
  target  the initial object pose when given (clutter tasks), else the TCP at the first close (grasp point)
  G-unit  depth at the projected target vs the target depth: |dz| <= 5 cm (the surface is in front)
  G-conv  converter (point + depth -> base xyz) within dh.CONV_TOL_M of the object centre
usage (pod): python -m xemb.src_maniskill SHARD_GLOB OUT_DIR [MAX_EPISODES]"""
from __future__ import annotations

import glob
import json
import os
import re
import struct
import sys

import numpy as np

from . import dh as DH
from . import geom as G


def _varint(b, i):
    s = r = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        if c < 0x80:
            return r, i
        s += 7


def _fields(b):
    i, n = 0, len(b)
    while i < n:
        key, i = _varint(b, i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 1:
            v, i = b[i:i + 8], i + 8
        elif wt == 2:
            L, i = _varint(b, i)
            v, i = b[i:i + L], i + L
        elif wt == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"wire type {wt}")
        yield f, wt, v


def parse_example(buf):
    out = {}
    for f, _, feats in _fields(buf):
        if f != 1:
            continue
        for f2, _, entry in _fields(feats):
            if f2 != 1:
                continue
            key, val = None, None
            for f3, _, v in _fields(entry):
                if f3 == 1:
                    key = v.decode()
                elif f3 == 2:
                    val = v
            for kind, _, lst in _fields(val or b""):
                if kind == 1:
                    out[key] = [v for ff, _, v in _fields(lst) if ff == 1]
                elif kind == 2:
                    fl = []
                    for ff, wt, v in _fields(lst):
                        fl += list(struct.unpack(f"<{len(v) // 4}f", v)) if wt == 2 else [struct.unpack("<f", v)[0]]
                    out[key] = np.array(fl, np.float32)
                elif kind == 3:
                    iv = []
                    for ff, wt, v in _fields(lst):
                        if wt == 2:
                            j = 0
                            while j < len(v):
                                x, j = _varint(v, j)
                                iv.append(x)
                        else:
                            iv.append(v)
                    out[key] = np.array(iv, np.int64)
    return out


def records(path):
    with open(path, "rb") as f:
        while True:
            h = f.read(12)
            if len(h) < 12:
                return
            n = struct.unpack("<Q", h[:8])[0]
            data = f.read(n)
            f.read(4)
            yield data


def pose_T(p):
    """[x, y, z, qw, qx, qy, qz] -> 4x4"""
    return G.pose_to_T(p[:3], G.quat_xyzw_to_mat([p[4], p[5], p[6], p[3]]))


_NAME = re.compile(r"(?:pick up|pick|grasp|lift|move|push|insert|stack|place|put)\s+(?:the |a |an )?([a-z0-9 _-]+?)"
                   r"(?:\s+(?:onto|on|into|in|to|from|and|with)\b|$)", re.I)


def name_of(instr):
    m = _NAME.search((instr or "").strip().rstrip("."))
    n = m.group(1).strip() if m else None
    return None if (n is None or "designated" in n) else n  # clutter: the target is not named


def convert(shard_glob, out, max_eps=400, per_ep=3):
    import cv2
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    robot = {"name": "panda_maniskill", "source": "oxe/maniskill_panda"}
    fd, fh = open(os.path.join(out, "records_D.jsonl"), "w"), open(os.path.join(out, "records_H.jsonl"), "w")
    st = {"episodes": 0, "named": 0, "states": 0, "g_unit": [], "g_conv": [], "rows": 0, "instr": {}}
    for sh in sorted(glob.glob(shard_glob)):
        for buf in records(sh):
            if st["episodes"] >= max_eps:
                break
            ex = parse_example(buf)
            st["episodes"] += 1
            ins = ex.get("steps/language_instruction", [b""])[0].decode(errors="ignore")
            st["instr"][ins] = st["instr"].get(ins, 0) + 1
            nm = name_of(ins)
            if not nm:
                continue
            st["named"] += 1
            T = len(ex["steps/observation/image"])
            Kall = ex["steps/observation/main_camera_intrinsic_cv"].reshape(T, 3, 3)
            Eall = ex["steps/observation/main_camera_extrinsic_cv"].reshape(T, 4, 4)
            base = ex["steps/observation/base_pose"].reshape(T, 7)
            obj = ex["steps/observation/target_object_or_part_initial_pose"].reshape(T, 7)
            valid = ex["steps/observation/target_object_or_part_initial_pose_valid"].reshape(T, 7)
            grip = ex["steps/observation/state"].reshape(T, 18)[:, 7:9].sum(1)
            closed = np.nonzero(grip < 0.9 * grip[0])[0]
            t_end = int(closed[0]) if len(closed) else T
            if t_end < 1 or t_end >= T:
                continue
            # target: the object's initial pose when the task gives it (clutter tasks only); otherwise the TCP at the
            # first close = the grasp point (single-object tasks leave the pose invalid)
            tcp = ex["steps/observation/tcp_pose"].reshape(T, 7)
            xw_fixed = obj[0, :3].astype(float) if valid[0, :3].all() else tcp[t_end, :3].astype(float)
            st["target_from_tcp"] = st.get("target_from_tcp", 0) + (not valid[0, :3].all())
            for t in sorted({int(x) for x in np.linspace(0, max(0, t_end - 8), per_ep)}):
                st["states"] += 1
                K, E = Kall[t].astype(float), Eall[t].astype(float)
                Twb = pose_T(base[t])
                Tbc = G.inv_T(Twb) @ G.inv_T(E)
                xw = xw_fixed
                uv, z = G.project(K, E, xw)
                dep = cv2.imdecode(np.frombuffer(ex["steps/observation/depth"][t], np.uint8), cv2.IMREAD_UNCHANGED)
                if dep is None or z <= 0:
                    continue
                dep = dep.reshape(dep.shape[0], dep.shape[1]).astype(float) / 1024.0
                Hh, Ww = dep.shape
                if not (0 <= uv[0] < Ww and 0 <= uv[1] < Hh):
                    continue
                dz = float(dep[int(uv[1]), int(uv[0])] - z)
                st["g_unit"].append(dz)
                xb = DH.converter(K, Tbc, dep, uv)
                if xb is None:
                    continue
                gt_b = G.apply_T(G.inv_T(Twb), xw)
                e = float(np.linalg.norm(xb - gt_b))
                st["g_conv"].append(e)
                if abs(dz) > 0.05 or e > DH.CONV_TOL_M:
                    continue
                rgb = cv2.imdecode(np.frombuffer(ex["steps/observation/image"][t], np.uint8), cv2.IMREAD_COLOR)
                rid = f"msk_{os.path.basename(sh)[-14:-9]}_{st['episodes']}_{t}"
                pi, pd = (os.path.join(out, "frames", f"{rid}_{k}") for k in ("rgb.jpg", "depth.png"))
                cv2.imwrite(pi, rgb)
                cv2.imwrite(pd, DH.encode_depth(dep))
                d, h = DH.rows(robot, Ww, Hh, K, Tbc, uv, gt_b, nm, [pi, pd], rid)
                fd.write(json.dumps(d) + "\n")
                fh.write(json.dumps(h) + "\n")
                st["rows"] += 1
    fd.close()
    fh.close()
    gu, gc = np.abs(np.array(st.pop("g_unit"))), np.array(st.pop("g_conv"))
    st["g_unit_absdz_cm"] = {"median": round(float(np.median(gu)) * 100, 2), "p90": round(float(np.percentile(gu, 90)) * 100, 2),
                             "le5cm": round(float((gu <= 0.05).mean()), 3)} if len(gu) else None
    st["g_conv_cm"] = {"median": round(float(np.median(gc)) * 100, 2), "p90": round(float(np.percentile(gc, 90)) * 100, 2),
                       "le5cm": round(float((gc <= DH.CONV_TOL_M).mean()), 3)} if len(gc) else None
    st["instr"] = dict(sorted(st["instr"].items(), key=lambda kv: -kv[1])[:15])
    json.dump(st, open(os.path.join(out, "report.json"), "w"), indent=1)
    return st


if __name__ == "__main__":
    print(json.dumps(convert(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:4])), indent=1))
