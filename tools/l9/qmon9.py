"""L9v2-general production quality monitor (owner order 2026-10-03): ONE round per invocation, no Claude in the
loop -- qmon.sh (same dir) calls this every 2 h on the collection pod. Scans the given collect roots
(root/<split>/<family>/<episode>/meta.json), caches cheap per-episode metrics (--cache, keyed by episode dir) so a
round only reads episodes it has not cached yet, then checks the production of the last --hours ("recent") and the
whole cache ("cumulative") against 10 health checks + successes/h, and OVERWRITES --status (one line) / appends
--events (same line) -- nothing else.

Checks (each PASS/WARN with its value; thresholds from the owner order):
  1 visibility drops   per robot, recent: share of control rows (labels.jsonl "drop" is None) the build-time
                        visibility gate would drop (visgate9 via build9._vis_gate, reusing a row's own "occ" when
                        present). WARN > 3% for any robot.
  2 left/right         per dual-arm robot (ffw_sg2, r1pro, g1), recent successes: left share in 40-60%.
  3 robot mix          recent new successes, share per robot vs --quotas, renormalised over the robots alloc9.
                        ROBOT_GATE_CLEARED today; WARN > 10 pp off target for any of them.
  4 approach families   cumulative successes (robot_gate9.profile): top family share <= 50%, all 12 rot bins used.
  5 high/shelf share    cumulative successes: place_height band "high" share >= 10%.
  6 spread              IQR of table_z / grasp x / grasp y, recent batch vs the cumulative reference (same --spec):
                        >= 0.8x; report-only (never WARN) until the cumulative population has >= 500 successes.
  7 duplicate layouts   cumulative successes (diversity9's (robot, task) layout+pose combo): WARN if any > 1.
  8 spec_version        every recent (new) episode's specgate9.spec_of(meta) == --spec; WARN otherwise.
  9 label contradictions up to --sample-n new control rows (episode_rows, built into a throwaway --tmp subdir that
                        is removed whole at the end of the round) via specgate9.contradictions; WARN > 4% (the
                        spec's own "> 40/1000" gate).
  10 ABA oscillation    place_oscillation fix canary (docs/research/place_oscillation_2026-10-03.md §1 definition,
                        applied to the GT label column): share of recent episodes with >=1 carry-phase call
                        (step in carry_up/carry_over/lower_open) whose step sequence round-trips
                        (h[k]==h[k-2]!=h[k-1]) that show >=1 such round-trip. Baseline measured in the doc is
                        0.17% (41/23,973) before the (a)/(d) fix (L9V2_PLACE_TOL/HYST); WARN > 1%. This is a GT
                        quality canary, not a trained-policy eval -- the doc's own ABA definition, applied upstream.
  + successes/h for context only (never WARN): tools/l9/rate9.py's log parser when --logs has matching logs,
    else the same cache's recent successes / --hours.

Cheap / incremental / CPU-only: harvest.l9.build9.prepare() loads the (pure, no-Isaac) L9 catalog once; after that
each NEW episode costs a few small json / npz reads (no image decode, no Isaac). The cache is rewritten in full
each round (bounded size, no unbounded jsonl growth) but only episodes missing from it are re-read from disk.

usage: PYTHONPATH=<deployed harvest code dir> venv/bin/python qmon9.py <collect root>... [--cache F] [--status F]
       [--events F] [--tmp DIR] [--spec L9v2-spec-final] [--hours 2] [--sample-n 200] [--logs DIR]
       [--quotas ffw_sg2:3800,franka_mast:4000,r1pro:3700,g1:3400] [--now EPOCH]
Sibling imports (robot_gate9, diversity9, rate9) resolve from this file's own directory -- deploy all four files
together under /data/harvest/out/l9/."""
from __future__ import annotations

import glob
import json
import os
import random
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np

KST = timezone(timedelta(hours=9))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling tools/l9 scripts (diversity9, robot_gate9, rate9)
import diversity9 as DV  # noqa: E402
import rate9 as R9  # noqa: E402
import robot_gate9 as RG  # noqa: E402

from harvest.l9 import build9 as B9  # noqa: E402
from harvest.l9 import specgate9 as SG  # noqa: E402
from harvest.l9 import alloc9 as AL  # noqa: E402

TWO_ARMED = RG.TWO_ARMED
QUOTA_DEFAULT = "ffw_sg2:3800,franka_mast:4000,r1pro:3700,g1:3400"


def _label_rows(ep_dir: str) -> list:
    """Raw labels.jsonl rows of one episode with drop is None (= reach a build), + call_dir/cams_path/depth_path.
    No seed-range check (teach_pt.dataset._check is for train/eval set membership, not quality monitoring) -- this
    reads episodes of any seed range, pilot or general production alike."""
    p = os.path.join(ep_dir, "labels.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if x.get("drop") is not None:
            continue
        c = os.path.join(ep_dir, "calls", f"c{int(x['call']):03d}")
        out.append(dict(x, call_dir=c, cams_path=os.path.join(c, "cams.json"),
                        depth_path=os.path.join(c, "head_depth.npz")))
    return out


def _vis_counts(ep_dir: str) -> tuple:
    """(control rows checked, of those dropped by the build-time visibility gate) of one episode."""
    total = dropped = 0
    for r in _label_rows(ep_dir):
        total += 1
        try:
            cam = json.load(open(r["cams_path"]))["head"]
            depth = np.load(r["depth_path"])["depth"]
            ok, _ = B9._vis_gate(cam, depth, r, use_occ=True)
        except Exception:
            continue  # unreadable call (e.g. still being written) -- not counted either way
        if not ok:
            dropped += 1
    return total, dropped


CARRY_STEPS = ("carry_up", "carry_over", "lower_open")  # = harvest.teach_l8.labels.CARRY_STEPS


def aba_oscillations(ep_dir: str) -> tuple:
    """(carry-phase calls, ABA round-trips) in one episode's labels.jsonl GT step column -- the place_oscillation
    doc's own ABA definition (h[k]==h[k-2]!=h[k-1]), applied to the GT "step" field rather than a policy's
    point-interface height: a canary on the label generator itself (qmon9 check 10), not a trained-policy metric."""
    steps = [r.get("step") for r in _label_rows(ep_dir) if r.get("step") in CARRY_STEPS]
    aba = sum(1 for k in range(2, len(steps)) if steps[k] == steps[k - 2] != steps[k - 1])
    return len(steps), aba


def episode_record(ep_dir: str):
    """Cache record of one episode, or None when meta.json can't be read."""
    mp = os.path.join(ep_dir, "meta.json")
    try:
        meta = json.load(open(mp))
        mtime = os.path.getmtime(mp)
    except (OSError, ValueError):
        return None
    base = meta.get("base") if isinstance(meta.get("base"), dict) else {}
    bx, by = ((base.get("pos") or [0.0, 0.0])[:2]) if base else (0.0, 0.0)
    picks = []
    for p in (meta.get("grasp_v2") or {}).get("picks") or []:
        g = p.get("grasp_world")
        picks.append({"family": p.get("family"), "rot": p.get("rot_bin_img"),
                      "gx": (float(g[0][3]) - float(bx)) if g else None,
                      "gy": (float(g[1][3]) - float(by)) if g else None})
    bands = [b for b in ((s.get("place_height") or {}).get("band") for s in meta.get("step_info") or []) if b]
    success = bool(meta.get("success"))
    combo = None
    if success and (meta.get("max_dq_rad") or 0) <= 0.04:
        r = DV.episode_combo(ep_dir, meta)
        if r is not None:
            combo = json.dumps([r[0], r[1], r[3]], default=str)
    vt, vd = _vis_counts(ep_dir)
    carry_calls, carry_aba = aba_oscillations(ep_dir)
    return {"ep_dir": ep_dir, "mtime": mtime, "robot": meta.get("robot") or "ffw_sg2", "task_id": meta.get("task_id"),
            "success": success, "arm": meta.get("arm"), "spec": SG.spec_of(meta),
            "has_grasp_v2": meta.get("grasp_v2") is not None, "table_z": meta.get("table_z"), "picks": picks,
            "bands": bands, "vis_total": vt, "vis_dropped": vd, "combo": combo,
            "carry_calls": carry_calls, "carry_aba": carry_aba}


def load_cache(path: str) -> dict:
    out = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            out[r["ep_dir"]] = r
    return out


def save_cache(path: str, cache: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for k in sorted(cache):
            f.write(json.dumps(cache[k]) + "\n")
    os.replace(tmp, path)


def scan(roots: list, cache: dict, cache_path: str | None = None, checkpoint_every: int = 500) -> int:
    """Updates cache in place with every episode under roots not already keyed -- the incremental step. On a
    production root this can be tens of thousands of episodes on the very first (cold-cache) round, so with
    cache_path given it checkpoints to disk every checkpoint_every new episodes -- an interrupted first round loses
    at most one checkpoint's worth of work, not the whole scan, on the next invocation."""
    added = 0
    for root in roots:
        for m in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")):
            d = os.path.dirname(m)
            if d in cache:
                continue
            r = episode_record(d)
            if r is not None:
                cache[d] = r
                added += 1
                if cache_path and added % checkpoint_every == 0:
                    save_cache(cache_path, cache)
    return added


def meta_like(rec: dict) -> dict:
    """Reconstructs just enough of a meta.json dict from a cache record for robot_gate9.profile() (base already
    folded into picks' gx/gy at cache time, so base is zero here)."""
    picks = [{"family": p["family"], "rot_bin_img": p["rot"],
             "grasp_world": [[0, 0, 0, p["gx"]], [0, 0, 0, p["gy"]], [0, 0, 0, 0]] if p["gx"] is not None else None}
            for p in rec["picks"]]
    return {"task_id": rec["task_id"], "arm": rec["arm"], "table_z": rec["table_z"], "base": {"pos": [0.0, 0.0]},
            "grasp_v2": {"picks": picks}, "step_info": [{"place_height": {"band": b}} for b in rec["bands"]]}


def quotas_of(s: str) -> dict:
    out = {}
    for kv in s.split(","):
        if not kv:
            continue
        k, v = kv.split(":")
        out[k.strip()] = float(v)
    return out


def succ_per_hour(logs_dir, hours: float, now: float, recent: list) -> float:
    """tools/l9/rate9.py's log parser when --logs has recent *.log files, else the recent-window cache count."""
    t_min = now - hours * 3600
    n = 0
    try:
        paths = [p for p in glob.glob(os.path.join(logs_dir or "", "*.log")) if os.path.getmtime(p) >= t_min - 7200]
    except OSError:
        paths = []
    if paths:
        for p in paths:
            try:
                jobs = R9.jobs_of(p)
            except Exception:
                continue
            for j in jobs:
                boot = 60.0
                t = j["start"] + boot
                for kind, wall, robot, ok, tt in j["rows"]:
                    t = float(tt) if tt else t + wall
                    if kind == "EP" and t_min <= t <= now and ok:
                        n += 1
        return round(n / hours, 1)
    return round(sum(1 for r in recent if r["success"]) / hours, 1)


def run(roots: list, cache_path: str, status_path: str, events_path: str, tmp_root: str, spec_expected: str,
        hours: float, sample_n: int, quotas: dict, logs_dir: str, now: float | None = None) -> str:
    now = now if now is not None else time.time()
    B9.prepare(("train", "ood_o"))
    cache = load_cache(cache_path)
    scan(roots, cache, cache_path)
    save_cache(cache_path, cache)
    all_recs = list(cache.values())
    recent = [r for r in all_recs if r["mtime"] >= now - hours * 3600]
    warn = []

    def W(cond, text):
        if cond:
            warn.append(text)

    # 1: visibility drops per robot, recent
    vt, vd = Counter(), Counter()
    for r in recent:
        vt[r["robot"]] += r["vis_total"]
        vd[r["robot"]] += r["vis_dropped"]
    for robot in sorted(vt):
        if vt[robot] <= 0:
            continue
        share = vd[robot] / vt[robot]
        W(share > 0.03, f"vis_drop[{robot}]={share:.1%}")

    # 2: left/right share of recent successes, two-armed robots
    arm_c = defaultdict(Counter)
    for r in recent:
        if r["success"] and r["robot"] in TWO_ARMED:
            arm_c[r["robot"]][r["arm"] or "?"] += 1
    for robot, c in arm_c.items():
        n = sum(c.values())
        if n == 0:
            continue
        left = c.get("left", 0) / n
        W(not (0.40 <= left <= 0.60), f"left_share[{robot}]={left:.2f}")

    # 3: robot mix vs quota, recent new successes, only robots currently cleared for production
    cleared = {r for r in quotas if AL.robot_build_ready(r)}
    q_sum = sum(quotas[r] for r in cleared) or 1.0
    succ_c = Counter(r["robot"] for r in recent if r["success"])
    s_sum = sum(succ_c[r] for r in cleared)
    if s_sum > 0:
        for robot in sorted(cleared):
            tgt = quotas[robot] / q_sum
            got = succ_c.get(robot, 0) / s_sum
            W(abs(got - tgt) > 0.10, f"mix[{robot}]={got:.1%}(target {tgt:.1%})")

    # 4/5: approach families / rot bins / high share, cumulative successes
    cum_succ_metas = [meta_like(r) for r in all_recs if r["success"]]
    prof_cum = RG.profile(cum_succ_metas)
    top = max(prof_cum["family_share"].values()) if prof_cum["family_share"] else 0.0
    W(top > 0.50, f"approach_top={top:.2f}")
    W(prof_cum["rot_bins"] < 12, f"rot_bins={prof_cum['rot_bins']}/12")
    W(prof_cum["high_share"] < 0.10, f"high_share={prof_cum['high_share']:.2f}")

    # 6: spread, recent batch vs cumulative reference, same --spec, report-only under 500 cumulative successes
    spec_fam = SG.spec_family(spec_expected)
    same_spec = lambda r: SG.spec_family(r["spec"]) == spec_fam  # noqa: E731
    cum_spec_succ = [r for r in all_recs if r["success"] and same_spec(r)]
    rec_spec_succ = [r for r in recent if r["success"] and same_spec(r)]
    ref = RG.profile([meta_like(r) for r in cum_spec_succ])
    p = RG.profile([meta_like(r) for r in rec_spec_succ])
    spread_report = {}
    for k in ("iqr_table_z", "iqr_x", "iqr_y"):
        if p[k] is None or ref[k] in (None, 0):
            continue
        ok = p[k] >= 0.8 * ref[k]
        spread_report[k] = (p[k], ref[k], ok)
        if not ok and len(cum_spec_succ) >= 500:
            warn.append(f"spread[{k}]={p[k]:.3f}(ref {ref[k]:.3f})")

    # 7: duplicate layouts, cumulative successes
    combo_c = Counter(r["combo"] for r in all_recs if r["combo"])
    dups = sum(c - 1 for c in combo_c.values() if c > 1)
    W(dups > 0, f"dup_layouts={dups}")

    # 8: spec_version of every recent (new) episode
    bad_spec = sum(1 for r in recent if r["spec"] != spec_expected)
    W(bad_spec > 0, f"spec_mismatch={bad_spec}/{len(recent)}(expect {spec_expected})")

    # 9: label-contradiction spot check on sampled new control rows, built into a throwaway temp dir
    cand = [r["ep_dir"] for r in recent if r["has_grasp_v2"]]
    random.Random(0).shuffle(cand)
    round_tmp = os.path.join(tmp_root, f"r{int(now)}")
    n_sampled, n_contra = 0, 0
    try:
        os.makedirs(round_tmp, exist_ok=True)
        rng = np.random.default_rng(0)
        ctrl = []
        for ep in cand:
            try:
                c, _, _ = B9.episode_rows(ep, round_tmp, "l9train", True, rng)
            except Exception:
                continue
            ctrl += c
            if len(ctrl) >= sample_n:
                break
        if ctrl:
            sample = ctrl if len(ctrl) <= sample_n else random.Random(1).sample(ctrl, sample_n)
            n_sampled = len(sample)
            n_contra = SG.contradictions(sample)
            W(n_contra / max(1, n_sampled) > 0.04, f"contradictions={n_contra}/{n_sampled}")
    finally:
        shutil.rmtree(round_tmp, ignore_errors=True)

    # 10: ABA (above<->lift) GT-label canary, recent episodes with >=1 carry-phase call
    carry_eps = [r for r in recent if r.get("carry_calls", 0) >= 1]
    aba_eps = sum(1 for r in carry_eps if r.get("carry_aba", 0) > 0)
    aba_rate = aba_eps / len(carry_eps) if carry_eps else 0.0
    if carry_eps:
        W(aba_rate > 0.01, f"aba_rate={aba_rate:.1%}({aba_eps}/{len(carry_eps)})")

    sph = succ_per_hour(logs_dir, hours, now, recent)
    utc = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    kst = datetime.fromtimestamp(now, tz=KST).strftime("%Y-%m-%d %H:%M:%S KST")
    verdict = "WARN" if warn else "PASS"
    body = "; ".join(warn) if warn else "-"
    line = f"{utc} {kst} {verdict} {body} | succ/h {sph}"
    with open(status_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    with open(events_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    return line


def main():
    a = sys.argv[1:]
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    flags = {"--cache", "--status", "--events", "--tmp", "--spec", "--hours", "--sample-n", "--logs", "--quotas", "--now"}
    roots = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in flags)]
    base = arg("--cache", None)
    out_dir = os.path.dirname(os.path.abspath(base)) if base else os.getcwd()
    line = run(roots, arg("--cache", os.path.join(out_dir, "qmon_cache.jsonl")),
              arg("--status", os.path.join(out_dir, "qmon_status.txt")),
              arg("--events", os.path.join(out_dir, "events_qmon.log")),
              arg("--tmp", os.path.join(out_dir, "qmon_tmp")), arg("--spec", "L9v2-spec-final"),
              float(arg("--hours", "2")), int(arg("--sample-n", "200")), quotas_of(arg("--quotas", QUOTA_DEFAULT)),
              arg("--logs", "/data/harvest/logs/l9"), float(arg("--now")) if "--now" in a else None)
    print(line)


if __name__ == "__main__":
    main()
