"""E-FUT1 data-gate diagnosis: why does the rebuild check (recorded request vs rebuilt request) fail?
For every call of every d1 episode: rebuild the pt request exactly as fut_rows.build_episode does and, on a mismatch,
record the first differing line (number-normalised), its NOW / history / static section, and episode facts
(variant, disturbance, swap / pre commands, repair attempts, call index).
  python tools/fut1/diag_rebuild.py --data /data/harvest/out/jcr/d1 --out /data/harvest/out/fut1/diag [--workers 8]"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy"))

from mm_rows import MAX_CALLS, NUM, T_MAX, load_ep, nearest, same_text  # noqa: E402


FIXED = os.environ.get("FUT1_PRESENT_AT_RESET") == "1"  # change 1: object list = the reset-time list


def norm(x):
    return NUM.sub("#", x)


def first_diff(a: str, b: str):
    la, lb = a.splitlines(), b.splitlines()
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<none>"
        y = lb[i] if i < len(lb) else "<none>"
        if not same_text(x, y):
            return i, x, y
    return None, "", ""


def ep_diag(d):
    from harvest.astra_motion.geometry import Cam
    from harvest.astra_solo import pt_prompts as PT
    from harvest.astra_solo.overlay import head_overlay
    from harvest.sim.tasks import TASKS, close_width
    from PIL import Image
    out = []
    try:
        res, ticks, smp, cmds = load_ep(d)
    except Exception as ex:  # noqa: BLE001
        return [{"ep": d, "kind": "load", "err": repr(ex)[:200]}]
    epj = json.load(open(os.path.join(d, "ep.json")))
    spec = TASKS[res["task"]]
    tk_t = np.array([x["t"] for x in ticks])
    img_s = [s for s in smp if "img" in s]
    im_t = np.array([s["t"] for s in img_s]) if img_s else np.zeros(0)
    calls = [c for c in res["calls"] if c.get("valid") and c["attempt"] == 0]
    all_calls = res["calls"]
    hist = res["history"]
    t0s = [cm["t"] - c["t_sim"] for cm, c in zip(cmds, calls)]
    t0 = float(np.median(t0s)) if t0s else 0.0
    w_close = close_width(spec.target)
    info = {"instruction": spec.instruction, "tgt": spec.target, "place": spec.place}
    facts = {"variant": os.path.basename(os.path.dirname(d)), "n_dist": len(epj.get("disturb_events") or []),
             "n_swap": sum(c.get("swap_t") is not None for c in cmds), "n_pre": sum(bool(c.get("pre")) for c in cmds),
             "n_calls_all": len(all_calls), "n_calls_valid0": len(calls), "n_cmds": len(cmds),
             "n_hist": len(hist), "end": res.get("end_reason"), "t0_ptp": float(np.ptp(t0s)) if t0s else None}
    for j, c in enumerate(calls):
        cd = os.path.join(d, "calls", f"c{c['call']:03d}")
        rec = {"ep": os.path.basename(os.path.dirname(d)) + "_" + os.path.basename(d), "call": c["call"],
               "site": c["site"], "j": j, **facts}
        try:
            cams = json.load(open(os.path.join(cd, "cams.json")))
            head, wrist0 = Cam.from_json(cams["head"]), Cam.from_json(cams["wrist"])
            tc = t0 + c["t_sim"]
            info["present"] = list(ticks[0 if FIXED else (nearest(tk_t, tc, 0.06) or 0)]["obj"].keys())
            tcp_c, gap_c = c["truth"]["tcp"], c["truth"]["grip_w"]
            table_z = float((c.get("resolved") or {}).get("plane") or 0.85)
            h_before = hist[:c["site"] - 1]
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
            rec_text = open(os.path.join(cd, "prompt.txt"), encoding="utf-8").read()
            if same_text(rec_text, pt_text):
                rec["ok"] = True
            else:
                i, x, y = first_diff(rec_text, pt_text)
                rec.update(ok=False, kind="text", line=i, rec_line=x[:300], built_line=y[:300],
                           rec_norm=norm(x)[:120], built_norm=norm(y)[:120], k0_dt=None if k0 is None else round(float(im_t[k0] - tc), 3))
        except Exception as ex:  # noqa: BLE001
            rec.update(ok=False, kind="exception", err=repr(ex)[:200])
        out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    eps = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(a.data, "*", "s*", "ep.json")))
    from multiprocessing import Pool
    with Pool(a.workers) as pool:
        recs = [r for rs in pool.imap(ep_diag, eps, chunksize=4) for r in rs]
    with open(os.path.join(a.out, "rebuild.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in recs)
    bad = [r for r in recs if not r.get("ok")]
    summ = {"calls": len(recs), "fail": len(bad), "fail_rate": round(len(bad) / max(1, len(recs)), 4),
            "by_kind": Counter(r.get("kind") for r in bad),
            "by_line_pattern": Counter(f"{r.get('rec_norm', '')[:60]} || {r.get('built_norm', '')[:60]}" for r in bad).most_common(15),
            "by_variant": Counter(r["variant"] for r in bad), "by_variant_all": Counter(r["variant"] for r in recs),
            "fail_eps": len({r["ep"] for r in bad}), "eps": len({r["ep"] for r in recs}),
            "fail_with_swap": sum(r["n_swap"] > 0 for r in bad), "all_with_swap": sum(r["n_swap"] > 0 for r in recs),
            "fail_with_dist": sum(r["n_dist"] > 0 for r in bad), "all_with_dist": sum(r["n_dist"] > 0 for r in recs),
            "fail_with_pre": sum(r["n_pre"] > 0 for r in bad), "all_with_pre": sum(r["n_pre"] > 0 for r in recs),
            "fail_calls_ne_cmds": sum(r["n_calls_valid0"] != r["n_cmds"] for r in bad),
            "all_calls_ne_cmds": sum(r["n_calls_valid0"] != r["n_cmds"] for r in recs),
            "exceptions": Counter(r.get("err", "")[:80] for r in bad if r.get("kind") == "exception").most_common(5),
            "examples": [{k: r.get(k) for k in ("ep", "call", "site", "line", "rec_line", "built_line")} for r in bad[:6]]}
    json.dump(summ, open(os.path.join(a.out, "rebuild_summary.json"), "w"), indent=1, default=str)
    print(json.dumps(summ, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
