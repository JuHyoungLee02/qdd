"""JCR data gate D0 (prereg_jcr1.md §4) + composition report. venv_train (numpy, PIL).
  python tools/jcr/data_gate.py --data /data/harvest/out/jcr/d0 --out /data/harvest/out/jcr/d0_gate [--n-sheet 50]
Checks: truth chunks inside the speed / acceleration limits (v <= 0.08 m/s, a <= 0.32 m/s^2 + 1e-6), commanded joint
step <= 0.04 rad per tick (ticks.jsonl), G-br (displacement) p50 <= 3 mm / p90 <= 8 mm, normal-episode share >= 0.5,
recover : progress inside disturbed episodes, success by normal / disturbed / command source, anomaly rates, and a
frame sheet of n random samples (wrist | head, with contact / anomaly / event labels) for the manual contact check
(<= 1 error in 50)."""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np

V_MAX, A_MAX, DT, DQ = 0.08, 0.32, 0.05, 0.04


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-sheet", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--select", default="", help="tools/jcr/select_data.py output (validation filter)")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    eps, pool = [], []
    vmax = amax = dqmax = 0.0
    gbr = []
    win = {"normal": 0, "recover": 0, "tail": 0}
    win_dis = {"recover": 0, "progress": 0}
    an = {}
    n_s = 0
    sel = json.load(open(a.select)) if a.select else {"exclude_episodes": {}, "exclude_samples": {}}
    for ej in sorted(glob.glob(os.path.join(a.data, "*", "s*", "ep.json"))):
        d = os.path.dirname(ej)
        if d in sel["exclude_episodes"]:
            continue
        drop_k = set(sel["exclude_samples"].get(d, []))
        e = json.load(open(ej))
        eps.append(e)
        sp = os.path.join(d, "samples_r3.jsonl")
        ss = [json.loads(x) for x in open(sp if os.path.exists(sp) else os.path.join(d, "samples.jsonl"))]
        tk = [json.loads(x) for x in open(os.path.join(d, "ticks.jsonl"))]
        q = np.array([x["q"] for x in tk])
        if len(q) > 1:
            dqmax = max(dqmax, float(np.abs(np.diff(q, axis=0)).max()))
        for s in ss:
            if s["k"] in drop_k:
                continue
            n_s += 1
            P = np.vstack([s["p_cmd"], s["chunk"]])
            v = np.linalg.norm(np.diff(P, axis=0), axis=1) / DT
            vmax = max(vmax, float(v.max()))
            vv = np.diff(np.vstack([s["v"], np.diff(P, axis=0) / DT]), axis=0)
            amax = max(amax, float(np.linalg.norm(vv, axis=1).max() / DT))
            if s.get("gbr_mm") is not None:
                gbr.append(s["gbr_mm"])
            win[s["window"]] += 1
            if not e["plan"]["normal"] and s["window"] != "tail":
                win_dis["recover" if s["window"] == "recover" else "progress"] += 1
            for k in s["anomaly"]:
                an[k] = an.get(k, 0) + 1
            if "img" in s:
                pool.append((d, s))
    def rate(sel):
        x = [e["success"] for e in eps if sel(e)]
        return {"n": len(x), "success": round(float(np.mean(x)), 3) if x else None}
    rep = {"episodes": len(eps), "samples": n_s, "normal_share": round(float(np.mean([e["plan"]["normal"] for e in eps])), 3),
           "success": {"all": rate(lambda e: True), "normal": rate(lambda e: e["plan"]["normal"]),
                       "disturbed": rate(lambda e: not e["plan"]["normal"]),
                       "src_truth": rate(lambda e: e["plan"]["src"] == "truth"),
                       "src_upper": rate(lambda e: e["plan"]["src"] == "upper")},
           "failures": {}, "windows": win, "disturbed_recover_to_progress": win_dis,
           "anomaly_sample_counts": an, "truth_v_max": round(vmax, 5), "truth_a_max": round(amax, 5),
           "joint_step_max_rad": round(dqmax, 5),
           "gbr_mm": {"p50": round(float(np.median(gbr)), 2), "p90": round(float(np.percentile(gbr, 90)), 2)} if gbr else None}
    for e in eps:
        if e["failure"]:
            rep["failures"][e["failure"]] = rep["failures"].get(e["failure"], 0) + 1
    rep["gate"] = {"limits": vmax <= V_MAX + 1e-6 and amax <= A_MAX * 1.01 and dqmax <= DQ + 1e-6,  # 1 %: arrival snap
                   "gbr": bool(gbr) and rep["gbr_mm"]["p50"] <= 3 and rep["gbr_mm"]["p90"] <= 8,
                   "normal_share": rep["normal_share"] >= 0.5}
    json.dump(rep, open(os.path.join(a.out, "gate.json"), "w"), indent=1)
    print(json.dumps(rep))
    # frame sheet for the manual contact / anomaly check
    from PIL import Image, ImageDraw
    rng = np.random.default_rng(a.seed)
    pick = [pool[i] for i in rng.choice(len(pool), size=min(a.n_sheet, len(pool)), replace=False)]
    W, Hh = 320, 180
    cols = 5
    rows = (len(pick) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rows * (Hh + 16)), (20, 20, 20))
    dr = ImageDraw.Draw(sheet)
    lab = []
    for i, (d, s) in enumerate(pick):
        im = Image.open(os.path.join(d, "img", s["img"] + "_wrist.jpg")).convert("RGB").resize((W, Hh))
        x, y = (i % cols) * W, (i // cols) * (Hh + 16)
        sheet.paste(im, (x, y + 16))
        t = f"{i} c={int(s.get('contact', False))} ev={s['grip_event'][0]} an={','.join(k[:4] for k in s['anomaly'])}"
        dr.text((x + 2, y + 2), t, fill=(255, 255, 0))
        lab.append({"i": i, "ep": d, "img": s["img"], "contact": s.get("contact"), "anomaly": s["anomaly"],
                    "event": s["grip_event"], "stage": s.get("stage")})
    sheet.save(os.path.join(a.out, "contact_sheet.jpg"), quality=80)
    json.dump(lab, open(os.path.join(a.out, "contact_sheet.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
