"""E-OPEN8 (prereg §4): (a) held-out open accuracy of a served model, (b) frame-leak check over replies to OUR
runtime requests (teach_pt.evaluate replies.jsonl). Greedy, same content layout as the L8 loader (text, then
'Image k: <label>' + image). usage:
  python -m xemb.eval_open8 heldout HELDOUT_JSONL URL NAME OUT_JSON
  python -m xemb.eval_open8 leak REPLIES_JSONL OUT_JSON
"""
from __future__ import annotations

import base64
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import fmt as F

OUR_BOX = {"x": [0.25, 0.65], "y": [-0.50, 0.10], "z": [0.70, 1.30]}  # sim SAFE box, z covers table 0.78-0.92 + 0.40
LABELS = ("head camera", "right wrist camera")


def ask(url, name, prompt, images, max_tokens=800):
    content = [{"type": "text", "text": prompt}]
    for i, p in enumerate(images):
        b = base64.b64encode(open(p, "rb").read()).decode()
        content += [{"type": "text", "text": f"Image {i + 1}: {LABELS[min(i, 1)]}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}}]
    body = json.dumps({"model": name, "messages": [{"role": "user", "content": content}], "temperature": 0,
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def _json(t):
    try:
        return json.loads(t[t.find("{"): t.rfind("}") + 1])
    except Exception:
        return None


def score(row, reply):
    """-> dict(valid, err) per kind: points -> px error; trace -> mean px error over matched points;
    control -> target error (m, in that robot's base frame) and command-mode match; xyz / dir -> m or deg."""
    gt, pr = _json(row["answer"]), _json(reply or "")
    out = {"stream": row.get("stream"), "kind": row.get("xkind"), "valid": pr is not None}
    if pr is None:
        return out
    try:
        if "point" in gt:
            out["err_px"] = float(np.linalg.norm(np.subtract(pr["point"], gt["point"])))
        elif "trace" in gt:
            a, b = np.asarray(pr["trace"], float), np.asarray(gt["trace"], float)
            n = min(len(a), len(b))
            out["err_px"] = float(np.linalg.norm(a[:n] - b[:n], axis=1).mean())
            out["end_err_px"] = float(np.linalg.norm(a[-1] - b[-1]))
        elif "command" in gt:
            gc, pc = gt["command"], pr.get("command", {})
            out["mode_ok"] = gc.get("mode") == pc.get("mode")
            if gc.get("mode") == "eef" and pc.get("mode") == "eef":
                out["target_err_m"] = float(np.linalg.norm(np.subtract(pc["position_m"], gc["position_m"])))
                out["gripper_ok"] = gc.get("gripper") == pc.get("gripper")
        elif "xyz_cam" in gt:
            out["err_m"] = float(np.linalg.norm(np.subtract(pr["xyz_cam"], gt["xyz_cam"])))
        elif "dir_cam" in gt:
            a, b = np.asarray(pr["dir_cam"], float), np.asarray(gt["dir_cam"], float)
            out["err_deg"] = float(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))
        elif "points" in gt:
            a, b = np.asarray(pr["points"], float).reshape(-1, 2), np.asarray(gt["points"], float).reshape(-1, 2)
            out["err_px"] = float(np.linalg.norm(a[0] - b[0]))
        elif "answer" in gt:
            m = re.match(r"\(?([A-D])\)?", str(gt["answer"]).strip())
            p = re.match(r"\(?([A-D])\)?", str(pr.get("answer", "")).strip())
            out["choice_ok"] = bool(m and p and m.group(1) == p.group(1))
    except Exception:
        out["valid"] = False
    return out


def summarize(scores):
    by = {}
    for s in scores:
        by.setdefault(s["stream"], []).append(s)
    out = {}
    for k, v in by.items():
        d = {"n": len(v), "valid": round(float(np.mean([x["valid"] for x in v])), 3)}
        for key in ("err_px", "end_err_px", "target_err_m", "err_m", "err_deg"):
            xs = [x[key] for x in v if key in x]
            if xs:
                d[key + "_med"] = round(float(np.median(xs)), 4)
        for key in ("mode_ok", "gripper_ok", "choice_ok"):
            xs = [x[key] for x in v if key in x]
            if xs:
                d[key] = round(float(np.mean(xs)), 3)
        out[k] = d
    return out


def main(argv):
    if argv[1] == "heldout":
        rows = [json.loads(x) for x in open(argv[2], encoding="utf-8")]
        url, name, outp = argv[3], argv[4], argv[5]
        with ThreadPoolExecutor(8) as ex:
            replies = list(ex.map(lambda r: ask(url, name, r["prompt"], r["images"]), rows))
        scores = [score(r, rep) for r, rep in zip(rows, replies)]
        res = {"name": name, "summary": summarize(scores)}
        json.dump({**res, "replies": replies}, open(outp, "w"), indent=1)
        print(json.dumps(res, indent=1))
    elif argv[1] == "leak":
        n = bad = 0
        kinds = {}
        for line in open(argv[2], encoding="utf-8"):
            r = json.loads(line)
            txt = r.get("reply") or r.get("text") or r.get("content") or ""
            if not isinstance(txt, str):
                continue
            n += 1
            fl = F.leak_flags(txt, OUR_BOX)
            fl = [f for f in fl if f != "not_json"]
            if fl:
                bad += 1
                for f in fl:
                    kinds[f] = kinds.get(f, 0) + 1
        res = {"replies": n, "leak": bad, "rate": round(bad / max(1, n), 4), "by_flag": kinds}
        json.dump(res, open(argv[3], "w"), indent=1)
        print(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv)
