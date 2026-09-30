"""E-DEP1 stage 1 rows (prereg_deploy1.md §1): mid-motion requests for the upper's d-min interface, from recorded JCR
episodes (harvest.jcr.record: raw head / right-wrist frames at decision ticks, 20 Hz privileged ticks, calls/ with
cams.json + head_depth.npz, result.json with every call's truth / resolve record and the history lines).
For each real call (the scene the upper was trained on: the robot at rest after arriving) and each delta:
  images  = the raw head / wrist frames of t_call - delta (the arm still moving toward the previous target); the head
            image gets the TCP ring (nd.ring_overlay), exactly as the d-min runtime draws it
  text    = the d-min request of the call (static + NOW + answer; min_format.d_text of the v2 request) with the TCP /
            pad gap / wrist-camera line of t_call - delta (the wrist camera rides with the gripper: top-down, fixed yaw
            -> its pose = call pose + TCP displacement) and the call's own history / call index / time used (the
            "as if arrived" format the upper was trained on; the adapter's "; JCR: ..." suffixes are removed)
  label   = the call's truth command (the noise-free PtTruth answer), scored by teach_pt.metrics.score on the call's
            head depth (objects before a grasp are static; the place does not move)
Rebuild check: the call's own pt request is rebuilt from the same inputs and must equal calls/cNNN/prompt.txt
byte for byte (history suffixes included) -- otherwise the episode is skipped and counted.
  python tools/deploy/mm_rows.py --data /data/harvest/out/jcr/d1 --out /data/harvest/out/deploy/mm1 [--n 400]"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DELTAS = (0.0, 0.5, 1.0, 2.0, 3.0)
IMG_TOL_S = 0.11
MAX_CALLS, T_MAX = 40, 180.0
JCR_SUFFIX = re.compile(r"; JCR: .*$")


NUM = re.compile(r"-?\d+\.\d+|-?\d+")


def same_text(a: str, b: str) -> bool:
    """Equal up to last-digit rounding of printed numbers (the record keeps TCP / camera poses rounded, the live
    request printed the unrounded values): the non-number text must be identical, every number within 1.5 units of
    its last printed digit."""
    if NUM.sub("#", a) != NUM.sub("#", b):
        return False
    for x, y in zip(NUM.findall(a), NUM.findall(b)):
        dec = len(x.split(".")[1]) if "." in x else 0
        if abs(float(x) - float(y)) > 1.5 * 10 ** (-dec) + 1e-12:
            return False
    return True


def nearest(ts, t, tol):
    i = int(np.argmin(np.abs(ts - t)))
    return i if abs(ts[i] - t) <= tol else None


def load_ep(d):
    res = json.load(open(os.path.join(d, "result.json")))
    ticks = [json.loads(x) for x in open(os.path.join(d, "ticks.jsonl"))]
    sp = os.path.join(d, "samples.jsonl")
    smp = [json.loads(x) for x in open(sp)] if os.path.exists(sp) else []
    cmds = [json.loads(x) for x in open(os.path.join(d, "cmds.jsonl"))]
    return res, ticks, smp, cmds


def build_episode(d, rng_pick=None):
    from harvest.astra_motion.geometry import Cam
    from harvest.astra_solo import nd as ND
    from harvest.astra_solo import prompts as V2P
    from harvest.astra_solo import pt_prompts as PT
    from harvest.astra_solo.overlay import head_overlay, png_bytes
    from harvest.sim.tasks import TASKS, close_width
    from harvest.teach_pt.min_format import d_text
    from PIL import Image
    res, ticks, smp, cmds = load_ep(d)
    spec = TASKS[res["task"]]
    tk_t = np.array([x["t"] for x in ticks])
    img_s = [s for s in smp if "img" in s]
    im_t = np.array([s["t"] for s in img_s]) if img_s else np.zeros(0)
    calls = [c for c in res["calls"] if c.get("valid") and c["attempt"] == 0]
    hist = res["history"]
    # absolute time origin: the cmds rows are the executed point / edit / gripper commands in call order
    t0s = [cm["t"] - c["t_sim"] for cm, c in zip(cmds, calls)]
    if not t0s or np.ptp(t0s) > 0.06:
        return [], {"skip": "t0"}
    t0 = float(np.median(t0s))
    w_close = close_width(spec.target)
    rows, info_ep = [], {"calls": 0, "rebuild_fail": 0}
    prev_t = None
    for j, c in enumerate(calls):
        cd = os.path.join(d, "calls", f"c{c['call']:03d}")
        cams = json.load(open(os.path.join(cd, "cams.json")))
        head, wrist0 = Cam.from_json(cams["head"]), Cam.from_json(cams["wrist"])
        tc = t0 + c["t_sim"]
        present = sorted(ticks[nearest(tk_t, tc, 0.06) or 0]["obj"].keys())
        info = {"instruction": spec.instruction, "tgt": spec.target, "place": spec.place, "present": present}
        tcp_c, gap_c = c["truth"]["tcp"], c["truth"]["grip_w"]
        table_z = float((c.get("resolved") or {}).get("plane") or 0.85)
        h_before = hist[:c["site"] - 1]
        info_ep["calls"] += 1
        # rebuild check (pt request, with the recorded history)
        try:
            k0 = nearest(im_t, tc, 0.25)
            ref = np.asarray(Image.open(os.path.join(d, "img", img_s[k0]["img"] + "_head_raw.jpg"))) if k0 is not None \
                else np.zeros((head.H, head.W, 3), np.uint8)
            _, drawn = head_overlay(ref, head, table_z, tcp_c)
            note = "" if "tcp" in drawn else "\nNOTE: the TCP is outside the head image this time: no ring and no drop line are drawn."
            if "tcp" in drawn and "drop" not in drawn:
                note = ("\nNOTE: the table point below the TCP is outside the head image this time: the drop line "
                        "leaves the image and its dot is not visible.")
            pt_text = PT.static(info, head, table_z, w_close) + PT.now(wrist0, tcp_c, gap_c, c["site"], MAX_CALLS,
                                                                       c["t_sim"], T_MAX, h_before) + PT.ANSWER + note
            if not same_text(open(os.path.join(cd, "prompt.txt"), encoding="utf-8").read(), pt_text):
                info_ep["rebuild_fail"] += 1
                info_ep.setdefault("fail", []).append([c["call"], "text"])
                prev_t = tc
                continue
        except Exception as ex:  # noqa: BLE001
            info_ep["rebuild_fail"] += 1
            info_ep.setdefault("fail", []).append([c["call"], repr(ex)[:120]])
            prev_t = tc
            continue
        parsed = json.loads(open(os.path.join(cd, "reply.txt"), encoding="utf-8").read())
        lab_cmd = parsed["command"]
        step = parsed.get("reason", "truth ?").split(" ", 1)[1]
        cm = next((x for x in cmds if abs(x["t"] - tc) < 0.06), {})  # none for a stop
        xyz = cm.get("goal_true") or tcp_c
        h_clean = [JCR_SUFFIX.sub("", x) for x in h_before]
        for dl in DELTAS:
            t = tc - dl
            if prev_t is not None and t < prev_t + 0.3:  # before the previous command was even issued
                continue
            ki = nearest(im_t, t, IMG_TOL_S if dl > 0 else 0.25)
            ti = nearest(tk_t, t, 0.06)
            if ki is None or ti is None:
                continue
            s = img_s[ki]
            tcp = np.asarray(ticks[ti]["tcp"], float)
            gap = float(ticks[ti]["grip_w"])
            wrist = Cam(wrist0.name, wrist0.W, wrist0.H, wrist0.fx, wrist0.fy, wrist0.cx, wrist0.cy, wrist0.R,
                        np.asarray(wrist0.t, float) + (tcp - np.asarray(tcp_c, float)))
            hr = np.asarray(Image.open(os.path.join(d, "img", s["img"] + "_head_raw.jpg")).convert("RGB"))
            wr = np.asarray(Image.open(os.path.join(d, "img", s["img"] + "_wrist_raw.jpg")).convert("RGB"))
            _, drawn = head_overlay(hr, head, table_z, tcp)
            note = "" if "tcp" in drawn else "\nNOTE: the TCP is outside the head image this time: no ring and no drop line are drawn."
            if "tcp" in drawn and "drop" not in drawn:
                note = ("\nNOTE: the table point below the TCP is outside the head image this time: the drop line "
                        "leaves the image and its dot is not visible.")
            v2 = V2P.static(info, head, table_z, w_close) + V2P.now(wrist, tcp, gap, c["site"], MAX_CALLS,
                                                                     c["t_sim"], T_MAX, h_clean) + V2P.ANSWER + note
            ring, _ = ND.ring_overlay(hr, head, tcp)
            rows.append({"ep": d, "call": c["call"], "site": c["site"], "delta": dl, "t_img": round(float(s["t"]), 3),
                         "t_call": round(tc, 3), "text": d_text(v2), "ring": png_bytes(ring), "wrist": png_bytes(wr),
                         "moving_mm": round(float(np.linalg.norm(tcp - np.asarray(tcp_c))) * 1e3, 1),
                         "answer": json.dumps({"command": lab_cmd}),
                         "xyz_answer": json.dumps({"command": {"mode": "eef", "position_m": list(map(float, xyz)),
                                                               "gripper": lab_cmd.get("gripper", "keep")}}),
                         "step": step, "cams_path": os.path.join(cd, "cams.json"),
                         "depth_path": os.path.join(cd, "head_depth.npz"),
                         "gt": {"tgt": c["truth"]["tgt_xyz"], "place": c["truth"]["place_xyz"], "tcp": tcp_c,
                                "grip_w": gap_c},
                         "ex_target": tcp_c,
                         "pt_state": {"holding": bool((c.get("resolved") or {}).get("holding", c["truth"]["holding"])),
                                      "grip_offset": (c.get("resolved") or {}).get("grip_offset"),
                                      "plane": table_z}})
        prev_t = tc
    return rows, info_ep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=400, help="call sites (each with up to len(DELTAS) rows)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    eps = sorted(os.path.dirname(p) for r in a.data for p in glob.glob(os.path.join(r, "*", "s*", "ep.json")))
    rng = np.random.default_rng(a.seed)
    rng.shuffle(eps)
    os.makedirs(os.path.join(a.out, "img"), exist_ok=True)
    out = open(os.path.join(a.out, "rows.jsonl"), "w")
    sites, stats = 0, {"episodes": 0, "calls": 0, "rebuild_fail": 0, "skip_t0": 0, "rows": 0}
    for d in eps:
        if sites >= a.n:
            break
        rows, inf = build_episode(d)
        if inf.get("skip"):
            stats["skip_t0"] += 1
            continue
        stats["episodes"] += 1
        stats["calls"] += inf["calls"]
        stats["rebuild_fail"] += inf["rebuild_fail"]
        for f in inf.get("fail", []):
            stats.setdefault("fail_examples", []).append([os.path.basename(d)] + f) if len(stats.get("fail_examples", [])) < 8 else None
        for r in rows:
            rid = f"{os.path.basename(os.path.dirname(r['ep']))}_{os.path.basename(r['ep'])}_c{r['call']:03d}_d{r['delta']}"
            ims = []
            for key in ("ring", "wrist"):
                p = os.path.join(a.out, "img", f"{rid}_{key}.png")
                with open(p, "wb") as f:
                    f.write(r.pop(key))
                ims.append(p)
            pp = os.path.join(a.out, "prompts", f"{rid}.txt")
            os.makedirs(os.path.dirname(pp), exist_ok=True)
            with open(pp, "w", encoding="utf-8") as f:
                f.write(r.pop("text"))
            r.update(id=rid, images=ims, prompt_path=pp, kind="control", arm="d-min", label_missing=False,
                     episode=f"{os.path.basename(os.path.dirname(r['ep']))}_{os.path.basename(r['ep'])}")  # teach_pt.evaluate row
            out.write(json.dumps(r) + "\n")
            stats["rows"] += 1
        sites += len({r["call"] for r in rows})
    out.close()
    stats["sites"] = sites
    json.dump(stats, open(os.path.join(a.out, "rows_stats.json"), "w"))
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
