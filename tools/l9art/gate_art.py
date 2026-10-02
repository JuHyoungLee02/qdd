"""Pilot gate summary over a harvest.l9art.run_art collect root (pure: reads meta.json / labels.jsonl / skipped.json
only, no sim). Per (def, robot): episode / skip counts, success rate (Wilson 95%), end_reason + fail_counts totals,
max_dq_rad health, label presence (point_2d / point2), grasp-draw diversity (approach families, rot bins, draw
u/pitch/yaw spread) and a PASS/FAIL verdict.

CLI: python tools/l9art/gate_art.py --root <collect_dir> [--split train] [--min-succ 0.70] [--out gate_art.json]
     [--sheet]  (--sheet also writes one contact-sheet PNG per definition under <out dir>/gate_sheets/, from each
     episode's review.jpg when present, else its first call's head-ring image; <= 12 episodes per sheet)."""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

MIN_SUCC = 0.40  # user 10-02 18h: per-skill gate success >= 40 % + quality gates
MAX_DQ = 0.04
MAX_DQ_OK_SHARE = 0.99
LABEL_MIN = 0.95
MIN_APPROACH_FAMILIES = 2
GRASP_SKILLS = ("pull_axis", "pick")  # knobs: axis-aligned pinch is the natural grasp -> rot-bin diversity instead
MIN_ROT_BINS_ROTATE = 3  # stages that grasp a part -> need approach-family diversity


# ---------------------------------------------------------------- loading
def episode_dirs(root: str, split: str | None = None) -> list:
    pat = os.path.join(root, split or "*", "*", "*", "meta.json")
    return sorted(os.path.dirname(p) for p in glob.glob(pat))


def skipped_files(root: str, split: str | None = None) -> list:
    pat = os.path.join(root, split or "*", "*", "*", "skipped.json")
    return sorted(glob.glob(pat))


def load_episode(ep_dir: str) -> tuple:
    meta = json.load(open(os.path.join(ep_dir, "meta.json")))
    lp = os.path.join(ep_dir, "labels.jsonl")
    labels = [json.loads(ln) for ln in open(lp, encoding="utf-8") if ln.strip()] if os.path.exists(lp) else []
    return meta, labels


def collect(root: str, split: str | None = None) -> dict:
    """-> {(def, robot): {"episodes": [(ep_dir, meta, labels)], "n_skipped": int, "skip_reasons": Counter}}"""
    groups = defaultdict(lambda: {"episodes": [], "n_skipped": 0, "skip_reasons": Counter()})
    for d in episode_dirs(root, split):
        meta, labels = load_episode(d)
        key = (meta.get("task_id"), meta.get("robot") or "ffw_sg2")
        groups[key]["episodes"].append((d, meta, labels))
    for p in skipped_files(root, split):
        sk = json.load(open(p))
        row = sk.get("row") or {}
        key = (row.get("def"), row.get("robot") or "ffw_sg2")
        g = groups[key]
        g["n_skipped"] += 1
        g["skip_reasons"][str(sk.get("reason"))[:80]] += 1
    return groups


# ---------------------------------------------------------------- stats
def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return 0.0, 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(p, 4), round(max(0.0, (centre - half) / denom), 4), round(min(1.0, (centre + half) / denom), 4)


def _group_stats(eps: list) -> dict:
    n = len(eps)
    succ = sum(1 for _, m, _ in eps if m.get("success"))
    usable = sum(1 for _, m, _ in eps if m.get("success") and float(m.get("max_dq_rad") or 0.0) <= MAX_DQ)
    p, lo, hi = wilson(succ, n)
    pu, ulo, uhi = wilson(usable, n)
    end_reason = Counter(m.get("end_reason") for _, m, _ in eps)
    fail_counts = Counter()
    for _, m, _ in eps:
        fail_counts.update(m.get("fail_counts") or {})
    dq = [float(m["max_dq_rad"]) for _, m, _ in eps if m.get("max_dq_rad") is not None]
    dq_over = sum(1 for v in dq if v > MAX_DQ)
    dq_ok_share = round(1.0 - dq_over / len(dq), 4) if dq else 1.0
    n_point, n_point_ok, n_move, n_move_ok = 0, 0, 0, 0
    approach_ct, rot_ct = Counter(), Counter()
    draw_u, draw_pitch, draw_yaw = [], [], []
    skills_v3 = set()
    for _, m, labels in eps:
        skills_v3.update(m.get("skills_v3") or [])
        dw = m.get("draw") or {}
        if "u" in dw:
            draw_u.append(float(dw["u"]))
        if "pitch" in dw:
            draw_pitch.append(float(dw["pitch"]))
        if "yaw" in dw:
            draw_yaw.append(float(dw["yaw"]))
        for r in labels:
            cmd = r.get("command") or {}
            if cmd.get("mode") != "point" or cmd.get("height") == "lift":  # lift has no point by design
                continue
            n_point += 1
            n_point_ok += cmd.get("point_2d") is not None
            if r.get("sub") == "move":
                n_move += 1
                n_move_ok += cmd.get("point2") is not None
            if cmd.get("approach"):
                approach_ct[cmd["approach"]] += 1
            if cmd.get("rot") is not None:
                rot_ct[int(cmd["rot"])] += 1
    n_req = n_point + n_move
    label_presence = round((n_point_ok + n_move_ok) / n_req, 4) if n_req else 1.0

    def spread(vals):
        return None if not vals else {"min": round(min(vals), 4), "max": round(max(vals), 4),
                                       "mean": round(sum(vals) / len(vals), 4), "n": len(vals)}

    needs_approach_diversity = bool(skills_v3 & set(GRASP_SKILLS))
    return {"n_episodes": n, "n_success": succ, "success_rate": p, "success_ci95": [lo, hi],
            "n_usable": usable, "usable_rate": pu, "usable_ci95": [ulo, uhi],
            "needs_rot_diversity": "rotate" in skills_v3,
            "end_reason": dict(end_reason), "fail_counts": dict(fail_counts),
            "max_dq_rad": {"max": round(max(dq), 4) if dq else None, "n_over_0.04": dq_over,
                           "ok_share": dq_ok_share, "n": len(dq)},
            "label_presence": {"point_2d_share": round(n_point_ok / n_point, 4) if n_point else 1.0,
                               "point2_share": round(n_move_ok / n_move, 4) if n_move else 1.0,
                               "overall": label_presence},
            "diversity": {"approach_families": dict(approach_ct), "n_approach_families": len(approach_ct),
                         "rot_bins_used": sorted(rot_ct), "draw_u": spread(draw_u), "draw_pitch": spread(draw_pitch),
                         "draw_yaw": spread(draw_yaw), "needs_approach_diversity": needs_approach_diversity}}


def verdict_of(stats: dict, min_succ: float) -> dict:
    fails = []
    if stats["n_episodes"] == 0:
        fails.append("no_episodes")
    else:
        if stats["usable_rate"] < min_succ:  # usable = success and measured joint step <= 0.04 (build keeps only these)
            fails.append(f"usable_rate {stats['usable_rate']} < {min_succ}")
        if stats.get("needs_rot_diversity") and len(stats["diversity"]["rot_bins_used"]) < MIN_ROT_BINS_ROTATE:
            fails.append(f"rot_bins {len(stats['diversity']['rot_bins_used'])} < {MIN_ROT_BINS_ROTATE}")
        if stats["label_presence"]["overall"] < LABEL_MIN:
            fails.append(f"label_presence {stats['label_presence']['overall']} < {LABEL_MIN}")
        if stats["diversity"]["needs_approach_diversity"] and stats["diversity"]["n_approach_families"] < MIN_APPROACH_FAMILIES:
            fails.append(f"approach_families {stats['diversity']['n_approach_families']} < {MIN_APPROACH_FAMILIES}")
    return {"pass": not fails, "reasons": fails}


def summarize(groups: dict, min_succ: float = MIN_SUCC) -> dict:
    out = {}
    for (did, robot), g in sorted(groups.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        stats = _group_stats(g["episodes"])
        stats.update(n_skipped=g["n_skipped"],
                     top_skip_reasons=dict(g["skip_reasons"].most_common(5)))
        stats["verdict"] = verdict_of(stats, min_succ)
        out[f"{did}|{robot}"] = dict(stats, task_id=did, robot=robot)
    return out


# ---------------------------------------------------------------- markdown
def to_markdown(res: dict) -> str:
    rows = ["| def | robot | n | skipped | success | usable | ci95 (usable) | dq_ok_share | label | families | verdict |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, s in res.items():
        lo, hi = s["usable_ci95"]
        rows.append(f"| {s['task_id']} | {s['robot']} | {s['n_episodes']} | {s['n_skipped']} | "
                    f"{s['success_rate']} | {s['usable_rate']} | [{lo}, {hi}] | {s['max_dq_rad']['ok_share']} | "
                    f"{s['label_presence']['overall']} | {s['diversity']['n_approach_families']} | "
                    f"{'PASS' if s['verdict']['pass'] else 'FAIL: ' + '; '.join(s['verdict']['reasons'])} |")
    return "\n".join(rows) + "\n"


# ---------------------------------------------------------------- contact sheets
def make_sheet(eps: list, out_path: str, max_n: int = 12) -> str | None:
    from PIL import Image, ImageDraw
    eps = eps[:max_n]
    if not eps:
        return None
    tiles = []
    for ep_dir, meta, _ in eps:
        rj = os.path.join(ep_dir, "review.jpg")
        c0 = os.path.join(ep_dir, "calls", "c001", "img1_head_ring.png")
        src = rj if os.path.exists(rj) else (c0 if os.path.exists(c0) else None)
        im = Image.open(src).convert("RGB") if src else Image.new("RGB", (336, 188), (40, 40, 40))
        im = im.resize((336, 220))
        d = ImageDraw.Draw(im)
        label = f"s{meta.get('seed')} {'OK' if meta.get('success') else 'FAIL'} {meta.get('end_reason')}"
        d.rectangle([0, 0, 336, 16], fill=(0, 0, 0))
        d.text((2, 2), label, fill=(255, 255, 255))
        tiles.append(im)
    cols = min(4, len(tiles))
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (336 * cols, 220 * rows), (0, 0, 0))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * 336, (i // cols) * 220))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path, quality=85)
    return out_path


def make_sheets(groups: dict, out_dir: str, max_n: int = 12) -> list:
    paths = []
    for (did, robot), g in sorted(groups.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        if not g["episodes"]:
            continue
        p = make_sheet(g["episodes"], os.path.join(out_dir, f"{did}_{robot}.jpg"), max_n)
        if p:
            paths.append(p)
    return paths


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--split", default=None)
    ap.add_argument("--min-succ", type=float, default=MIN_SUCC)
    ap.add_argument("--out", default=None)
    ap.add_argument("--sheet", action="store_true")
    a = ap.parse_args(argv)
    groups = collect(a.root, a.split)
    res = summarize(groups, a.min_succ)
    out_json = a.out or os.path.join(a.root, "gate_art.json")
    json.dump(res, open(out_json, "w"), indent=1, default=str)
    md = to_markdown(res)
    md_path = os.path.splitext(out_json)[0] + ".md"
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(md)
    if a.sheet:
        paths = make_sheets(groups, os.path.join(os.path.dirname(out_json), "gate_sheets"))
        print(json.dumps({"sheets": paths}))


if __name__ == "__main__":
    main()
