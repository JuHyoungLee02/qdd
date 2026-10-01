"""E-FUT1 rows (docs/stage3/prereg_fut1.md §3): 'answer for the moment of arrival' rows for the upper (d-min interface)
from the recorded JCR d1 episodes (harvest.jcr.record: raw head / right-wrist frames about every 0.2 s, 20 Hz
privileged ticks, calls/ with cams.json + head_depth.npz + the recorded request, cmds.jsonl with the executed goals).

A call site = a real call of the recorded episode (the robot at rest after the previous command; the label = the
simulator-truth command of that call, reply.txt). For a lead time delta > 0 the request is built from the scene at
t_call - delta, while the previous command (the in-flight one) is still moving. Only what the current scene and the
in-flight command determine is a target (user 10-01 via main: "그 순간 등장하는 미래예측은 좀 어렵긴하겠고"):
a delta > 0 row exists only when
  - the in-flight command is a gripper-keep move (point / edit), not pre-issued, not swapped mid-way (the overlap
    runtime only asks early during such moves, prereg_deploy1 change 1);
  - no scripted disturbance falls in [t - delta, t_call], no object other than a held one moves > 10 mm and the
    holding state does not change in that window (new events stay with the JCR anomaly signal + re-asking);
  - t - delta is at least 0.3 s after the in-flight command was issued.
History for delta > 0: the in-flight command's line in the trained 'as if arrived' form of the overlap runtime
(harvest.deploy.runner._provisional: '-> reached the target (error 0 mm); TCP now (goal), pad gap <now>'), goal = the
executed goal of the in-flight command (cmds.jsonl goal_cmd). The adapter's '; JCR: ...' suffixes are removed.
Input variants (the answer is the same for all):
  cur   TCP / pad gap / wrist-camera line and the head ring at t - delta (what the E-DEP1 stage-2 runner sends now)
  roll  the robot state rolled forward to the expected arrival (VLASH): TCP line, ring and wrist pose at the
        in-flight goal; the images stay those of t - delta
  rt    roll + one NOW line with the expected remaining move time (TIC-VLA-style latency metadata)
delta = 0: the recorded static request (all variants identical; the rebuild check of E-DEP1 stage 1 must pass).
Labels: the full d-min answer (assessment / command / reason) templated like the L8S labels
(harvest.teach_l8.labels: texts, status, evidence) from the call's truth step and command; evidence = the TCP / pad
gap the request shows. Aux 'arrival' rows (arm F4): head ring image of t - delta + the in-flight command -> the
point of the TCP where the arm actually stopped (simulator truth at t_call) and its z.
Split: held-out = the 61 E-DEP1 stage-1 episodes + sha256('fut1|<variant>_<seed>') % 10 == 0; train = the rest.
  python tools/fut1/fut_rows.py --data /data/harvest/out/jcr/d1 --mm1 /data/harvest/out/deploy/mm1/rows.jsonl \
     --replay /data/harvest/out/main35/data/train_main35.jsonl --out /data/harvest/out/fut1/data"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy"))

from mm_rows import IMG_TOL_S, JCR_SUFFIX, MAX_CALLS, T_MAX, load_ep, nearest, same_text  # noqa: E402

TRAIN_DELTAS = (0.0, 0.5, 1.0, 1.5, 2.0)
EVAL_DELTAS = (0.0, 0.5, 1.0, 2.0, 3.0)
ALL_DELTAS = tuple(sorted(set(TRAIN_DELTAS) | set(EVAL_DELTAS)))
VARIANTS = ("cur", "roll", "rt")
OBJ_MOVE_M = 0.010
ISSUE_GAP_S = 0.3
ARMS = ("F0", "F1", "F2", "F3", "F4")
ARM_VARIANT = {"F0": "cur", "F1": "cur", "F2": "roll", "F3": "rt", "F4": "roll"}
CMD_KEYS = ("mode", "point_2d", "height", "delta_m", "gripper")
RT_LINE = ("- The previous command is still executing: the arm reaches this TCP in about {s:.1f} s (the images show "
           "the scene now). Answer for the moment it arrives.")
AUX_PROMPT = ("Image 1 is the robot's head camera (the white ring is the gripper's TCP now).\n"
              "The arm is still executing this command: {desc}.\n"
              "Point to where the TCP will actually stop when this move ends, and give its height.\n"
              'Return JSON only: {{"point_2d": [x, y], "z_m": z}} with x, y on a 0-1000 scale of image 1 (x from the '
              "left edge, y from the top edge) and z in metres in the robot frame.")


def h01(s: str) -> float:
    return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16) / 16 ** 12


def ep_name(d: str) -> str:
    return f"{os.path.basename(os.path.dirname(d))}_{os.path.basename(d)}"


def held_out(name: str, mm1_eps: set) -> bool:
    return name in mm1_eps or int(hashlib.sha256(f"fut1|{name}".encode()).hexdigest(), 16) % 10 == 0


def order_cmd(c: dict) -> dict:
    return {k: c[k] for k in CMD_KEYS if k in c} if c.get("mode") != "stop" else {"mode": "stop"}


def answer_text(step: str, cmd: dict, info: dict, tcp, gap: float, first: bool, last_line: str, prev_failed: bool):
    from harvest.astra_motion.prompts import OBJ_NAME
    from harvest.teach_l8 import labels as LB
    tn, pn = OBJ_NAME.get(info["tgt"], info["tgt"]), OBJ_NAME.get(info["place"], info["place"])
    try:
        doing, remaining, done = LB._texts(step, tn, pn)
    except KeyError:
        return None
    st = {"tcp": list(map(float, tcp)), "grip_w": float(gap)}
    ans = {"assessment": {"task_progress": {"verified_completed": done, "currently_attempting": doing,
                                            "remaining": remaining},
                          "execution_status": LB.status_of(step, first, last_line, prev_failed),
                          "evidence": LB.evidence_of(step, st, tn, last_line), "evidence_view": "both",
                          "confidence": "high"},
           "command": order_cmd(cmd), "reason": f"Next: {doing}."}
    return json.dumps(ans)


def provisional(line: str, goal, gap: float) -> str:
    """runner._provisional: the in-flight command's line as if it had reached its goal."""
    desc = line.split(" -> ", 1)[0]
    g = goal
    return (f"{desc} -> reached the target (error 0 mm); TCP now ({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f}), "
            f"pad gap {gap * 100:.1f} cm")


def window_ok(ticks, tk_t, t_a, t_b, dist, held_obj) -> bool:
    for e in dist:
        if t_a - 0.05 <= float(e.get("t", -1e9)) <= t_b + 0.05:
            return False
    ia, ib = nearest(tk_t, t_a, 0.06), nearest(tk_t, t_b, 0.06)
    if ia is None or ib is None:
        return False
    A, B = ticks[ia], ticks[ib]
    if bool(A.get("holding")) != bool(B.get("holding")) or set(A["obj"]) != set(B["obj"]):
        return False  # grasp state changed or an object appeared (obstacle disturbance) inside the window
    for k, p in A["obj"].items():
        if k == held_obj and A.get("holding"):
            continue
        q = B["obj"].get(k)
        if q is None or float(np.linalg.norm(np.subtract(p, q))) > OBJ_MOVE_M:
            return False
    return True


def build_episode(d: str, out_img: str, want_variants=VARIANTS, deltas=ALL_DELTAS):
    """-> (sites, info). site = {id, episode, call, step, answer_cmd, rows: {delta: {variant: row}}, aux: {delta: row}}"""
    from harvest.astra_motion.geometry import Cam, project
    from harvest.astra_solo import nd as ND
    from harvest.astra_solo import prompts as V2P
    from harvest.astra_solo import pt_prompts as PT
    from harvest.astra_solo.overlay import head_overlay, png_bytes
    from harvest.sim.tasks import TASKS, close_width
    from harvest.teach_pt.min_format import d_text
    from PIL import Image
    res, ticks, smp, cmds = load_ep(d)
    epj = json.load(open(os.path.join(d, "ep.json")))
    dist = list(epj.get("disturb_events") or [])
    spec = TASKS[res["task"]]
    tk_t = np.array([x["t"] for x in ticks])
    img_s = [s for s in smp if "img" in s]
    im_t = np.array([s["t"] for s in img_s]) if img_s else np.zeros(0)
    calls = [c for c in res["calls"] if c.get("valid") and c["attempt"] == 0]
    hist = res["history"]
    t0s = [cm["t"] - c["t_sim"] for cm, c in zip(cmds, calls)]
    info_ep = {"calls": len(calls), "rebuild_fail": 0, "no_step": 0, "sites": 0}
    if not t0s or np.ptp(t0s) > 0.06:
        return [], {"skip": "t0"}
    t0 = float(np.median(t0s))
    w_close = close_width(spec.target)
    name = ep_name(d)
    info = {"instruction": spec.instruction, "tgt": spec.target, "place": spec.place}
    sites, prev = [], None  # prev = (t_issue, cmds row) of the previous call
    prev_step = None

    def note_of(drawn):
        if "tcp" not in drawn:
            return "\nNOTE: the TCP is outside the head image this time: no ring and no drop line are drawn."
        if "drop" not in drawn:
            return ("\nNOTE: the table point below the TCP is outside the head image this time: the drop line "
                    "leaves the image and its dot is not visible.")
        return ""

    for j, c in enumerate(calls):
        cd = os.path.join(d, "calls", f"c{c['call']:03d}")
        cams = json.load(open(os.path.join(cd, "cams.json")))
        head, wrist0 = Cam.from_json(cams["head"]), Cam.from_json(cams["wrist"])
        tc = t0 + c["t_sim"]
        # the runtime request lists the objects present at reset (env.present); an 'obstacle' disturbance appends
        # o10 to the ticks later but never to the request (diag_rebuild: 1,479/1,479 rebuild failures, change 1)
        info["present"] = list(ticks[0]["obj"].keys())
        tcp_c, gap_c = c["truth"]["tcp"], c["truth"]["grip_w"]
        table_z = float((c.get("resolved") or {}).get("plane") or 0.85)
        h_before = hist[:c["site"] - 1]
        cm_row = next((x for x in cmds if abs(x["t"] - tc) < 0.06), None)
        cur_prev, prev = prev, (tc, cm_row)
        # rebuild check of the recorded request (as E-DEP1 stage 1)
        try:
            k0 = nearest(im_t, tc, 0.25)
            ref = np.asarray(Image.open(os.path.join(d, "img", img_s[k0]["img"] + "_head_raw.jpg"))) if k0 is not None \
                else np.zeros((head.H, head.W, 3), np.uint8)
            _, drawn = head_overlay(ref, head, table_z, tcp_c)
            pt_text = PT.static(info, head, table_z, w_close) + PT.now(wrist0, tcp_c, gap_c, c["site"], MAX_CALLS,
                                                                       c["t_sim"], T_MAX, h_before) + PT.ANSWER + note_of(drawn)
            if not same_text(open(os.path.join(cd, "prompt.txt"), encoding="utf-8").read(), pt_text):
                info_ep["rebuild_fail"] += 1
                continue
        except Exception:  # noqa: BLE001
            info_ep["rebuild_fail"] += 1
            continue
        parsed = json.loads(open(os.path.join(cd, "reply.txt"), encoding="utf-8").read())
        lab_cmd = parsed["command"]
        step = parsed.get("reason", "truth ?").split(" ", 1)[1]
        h_clean = [JCR_SUFFIX.sub("", x) for x in h_before]
        first = c["site"] == 1
        last_line = h_clean[-1] if h_clean else ""
        prev_failed = prev_step == "reopen" or (len(h_clean) > 1 and "BLOCKED" in h_clean[-2])
        prev_step = step
        # the in-flight command (the previous call's executed command)
        fl = cur_prev[1] if cur_prev else None
        inflight_ok = bool(fl and h_clean and fl.get("cmd", {}).get("gripper") == "keep"
                           and fl.get("cmd", {}).get("mode") in ("point", "edit") and not fl.get("pre")
                           and fl.get("swap_t") is None and fl.get("goal_cmd") is not None)
        site = {"id": f"{name}_c{c['call']:03d}", "episode": name, "call": c["call"], "site": c["site"], "step": step,
                "command": lab_cmd, "rows": {}, "aux": {}, "inflight_keep": inflight_ok}
        for dl in deltas:
            t = tc - dl
            if dl > 0:
                if not inflight_ok or t < cur_prev[0] + ISSUE_GAP_S:
                    continue
                if not window_ok(ticks, tk_t, t, tc, dist, spec.target):
                    continue
            ki = nearest(im_t, t, IMG_TOL_S if dl > 0 else 0.25)
            ti = nearest(tk_t, t, 0.06)
            if ki is None or ti is None:
                continue
            s = img_s[ki]
            tcp_now = np.asarray(ticks[ti]["tcp"], float)
            gap_now = float(ticks[ti]["grip_w"])
            hr = np.asarray(Image.open(os.path.join(d, "img", s["img"] + "_head_raw.jpg")).convert("RGB"))
            wr_p = os.path.join(out_img, f"{site['id']}_d{dl}_wrist.png")
            if dl == 0:
                states = {"cur": (np.asarray(tcp_c, float), float(gap_c))}
                hist_d = h_clean
            else:
                goal = np.asarray(fl["goal_cmd"], float)
                states = {"cur": (tcp_now, gap_now), "roll": (goal, gap_now)}
                hist_d = h_clean[:-1] + [provisional(h_clean[-1], goal, gap_now)]
            rows = {}
            for v in want_variants:
                key = "cur" if (dl == 0 or v == "cur") else "roll"
                tcp_v, gap_v = states[key]
                wrist = Cam(wrist0.name, wrist0.W, wrist0.H, wrist0.fx, wrist0.fy, wrist0.cx, wrist0.cy, wrist0.R,
                            np.asarray(wrist0.t, float) + (tcp_v - np.asarray(tcp_c, float)))
                _, drawn = head_overlay(hr, head, table_z, tcp_v)
                v2 = V2P.static(info, head, table_z, w_close) + V2P.now(wrist, tcp_v, gap_v, c["site"], MAX_CALLS,
                                                                         c["t_sim"], T_MAX, hist_d) + V2P.ANSWER + note_of(drawn)
                text = d_text(v2)
                if v == "rt" and dl > 0:
                    lines = text.split("\n")
                    k = next(i for i, x in enumerate(lines) if x.startswith("- TCP at ("))
                    lines.insert(k + 1, RT_LINE.format(s=dl))
                    text = "\n".join(lines)
                ring_p = os.path.join(out_img, f"{site['id']}_d{dl}_ring_{key}.png")
                if not os.path.exists(ring_p):
                    ring, _ = ND.ring_overlay(hr, head, tcp_v)
                    with open(ring_p, "wb") as f:
                        f.write(png_bytes(ring))
                ans = answer_text(step, lab_cmd, info, tcp_v, gap_v, first, hist_d[-1] if hist_d else "", prev_failed)
                if ans is None:
                    info_ep["no_step"] += 1
                    break
                rows[v] = {"text": text, "images": [ring_p, wr_p], "answer": ans,
                           "moving_mm": round(float(np.linalg.norm(tcp_now - np.asarray(tcp_c))) * 1e3, 1)}
            if not rows or len(rows) < len(want_variants):
                continue
            if not os.path.exists(wr_p):
                wr = np.asarray(Image.open(os.path.join(d, "img", s["img"] + "_wrist_raw.jpg")).convert("RGB"))
                with open(wr_p, "wb") as f:
                    f.write(png_bytes(wr))
            site["rows"][dl] = rows
            if dl > 0:  # aux 'actual arrival' row
                u, vv, z = project(head, tcp_c)
                if z > 0 and 0 <= u < head.W and 0 <= vv < head.H:
                    desc = h_clean[-1].split(" -> ", 1)[0].split(": ", 1)[-1]
                    site["aux"][dl] = {"prompt": AUX_PROMPT.format(desc=desc),
                                       "images": [os.path.join(out_img, f"{site['id']}_d{dl}_ring_cur.png")],
                                       "answer": json.dumps({"point_2d": [int(round(u / head.W * 1000)),
                                                                          int(round(vv / head.H * 1000))],
                                                             "z_m": round(float(tcp_c[2]), 3)})}
        xyz = (cm_row or {}).get("goal_true") or tcp_c
        site.update(xyz_answer=json.dumps({"command": {"mode": "eef", "position_m": list(map(float, xyz)),
                                                       "gripper": lab_cmd.get("gripper", "keep")}}),
                    t_call=round(tc, 3), cams_path=os.path.join(cd, "cams.json"),
                    depth_path=os.path.join(cd, "head_depth.npz"),
                    gt={"tgt": c["truth"]["tgt_xyz"], "place": c["truth"]["place_xyz"], "tcp": tcp_c, "grip_w": gap_c},
                    pt_state={"holding": bool((c.get("resolved") or {}).get("holding", c["truth"]["holding"])),
                              "grip_offset": (c.get("resolved") or {}).get("grip_offset"), "plane": table_z})
        if site["rows"].get(0.0):
            sites.append(site)
            info_ep["sites"] += 1
    return sites, info_ep


def _build(arg):
    d, img_dir = arg
    try:
        sites, inf = build_episode(d, img_dir)
    except Exception as ex:  # noqa: BLE001
        return d, [], {"skip": repr(ex)[:200]}
    return d, sites, inf


def control_row(site: dict, dl: float, v: str, prompts_dir: str, tag: str) -> dict:
    r = site["rows"][dl][v]
    rid = f"{site['id']}_d{dl}_{v}"
    pp = os.path.join(prompts_dir, f"{rid}.txt")
    if not os.path.exists(pp):
        with open(pp, "w", encoding="utf-8") as f:
            f.write(r["text"])
    return {"id": f"{rid}_{tag}" if tag else rid, "kind": "control", "arm": "d-min", "format": "pt",
            "prompt_path": pp, "images": r["images"], "answer": r["answer"], "label_missing": False,
            "episode": site["episode"], "call": site["call"], "site": site["site"], "delta": dl, "variant": v,
            "step": site["step"], "moving_mm": r["moving_mm"], "cams_path": site["cams_path"],
            "depth_path": site["depth_path"], "gt": site["gt"], "ex_target": site["gt"]["tcp"],
            "pt_state": site["pt_state"], "xyz_answer": site["xyz_answer"], "prev_kind": "fut1", "src": "d1"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", required=True)
    ap.add_argument("--mm1", required=True, help="E-DEP1 stage-1 rows (their episodes are held out)")
    ap.add_argument("--replay", required=True, help="main35 train rows (the replay part, same for every arm)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-d1", type=int, default=4000, help="d1 rows per arm")
    ap.add_argument("--n-replay", type=int, default=4000)
    ap.add_argument("--aux-frac", type=float, default=0.25, help="F4: share of its d1 rows that are aux rows")
    ap.add_argument("--eval-sites", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit-eps", type=int, default=0, help="smoke")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    from harvest.astra_solo.pt_schema import validate
    img_dir, pr_dir = os.path.join(a.out, "img"), os.path.join(a.out, "prompts")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(pr_dir, exist_ok=True)
    mm1_eps = {json.loads(x)["episode"] for x in open(a.mm1)}
    eps = sorted(os.path.dirname(p) for r in a.data for p in glob.glob(os.path.join(r, "*", "s*", "ep.json")))
    if a.limit_eps:
        eps = eps[:a.limit_eps]
    stats = {"episodes": 0, "skip_t0": 0, "rebuild_fail": 0, "no_step": 0, "label_invalid": 0,
             "sites_train": 0, "sites_eval": 0, "held_out_eps": 0}
    tr_sites, ev_sites = [], []
    from multiprocessing import Pool
    with Pool(a.workers) as pool:
        built = list(pool.imap(_build, [(d, img_dir) for d in eps], chunksize=4))
    for d, sites, inf in built:
        if inf.get("skip"):
            stats["skip_t0" if inf["skip"] == "t0" else "skip_error"] = stats.get("skip_t0" if inf["skip"] == "t0" else "skip_error", 0) + 1
            continue
        stats["episodes"] += 1
        stats["calls"] = stats.get("calls", 0) + inf["calls"]
        stats["rebuild_fail"] += inf["rebuild_fail"]
        stats["no_step"] += inf["no_step"]
        ok = []
        for s in sites:
            if validate(s["rows"][0.0]["cur"]["answer"], allow_eef=True)[0] is None:
                stats["label_invalid"] += 1
                continue
            ok.append(s)
        ho = held_out(ep_name(d), mm1_eps)
        stats["held_out_eps"] += ho
        (ev_sites if ho else tr_sites).extend(ok)
    stats["sites_train"], stats["sites_eval"] = len(tr_sites), len(ev_sites)
    rng = np.random.default_rng(a.seed)
    # ---- eval files (one per variant; the same sites and deltas)
    ev_sites.sort(key=lambda s: h01("fut1ev|" + s["id"]))
    ev_sites = ev_sites[:a.eval_sites]
    for v in VARIANTS:
        with open(os.path.join(a.out, f"eval_{v}.jsonl"), "w") as f:
            for s in ev_sites:
                for dl in EVAL_DELTAS:
                    if dl in s["rows"]:
                        f.write(json.dumps(control_row(s, dl, v, pr_dir, "")) + "\n")
    ev_aux = [dict(id=f"{s['id']}_d{dl}_aux", kind="aux", aux_kind="fut1_arrival", episode=s["episode"], delta=dl,
                   **s["aux"][dl]) for s in ev_sites for dl in EVAL_DELTAS if dl in s["aux"]]
    with open(os.path.join(a.out, "eval_aux.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in ev_aux)
    # ---- train: the same sites for every arm; one delta per site (F1-F4), delta 0 for F0
    rng.shuffle(tr_sites)
    sel = tr_sites[:a.n_d1]
    draw = []
    for s in sel:
        ds = [dl for dl in TRAIN_DELTAS if dl in s["rows"]]
        draw.append(float(rng.choice(ds)))
    replay = []
    with open(a.replay) as f:
        allr = f.readlines()
    for i in sorted(rng.choice(len(allr), size=min(a.n_replay, len(allr)), replace=False).tolist()):
        replay.append(json.loads(allr[i]))
    n_aux = int(round(a.aux_frac * len(sel)))
    aux_pool = [(i, dl) for i, (s, dl) in enumerate(zip(sel, draw)) if dl > 0 and dl in s["aux"]]
    aux_pick = aux_pool[-n_aux:] if n_aux else []
    aux_idx = {i for i, _ in aux_pick}
    arm_stats = {}
    for arm in ARMS:
        v = ARM_VARIANT[arm]
        rows = list(replay)
        for i, (s, dl) in enumerate(zip(sel, draw)):
            if arm == "F0":
                rows.append(control_row(s, 0.0, "cur", pr_dir, "tr"))
            elif arm == "F4" and i in aux_idx:
                rows.append(dict(id=f"{s['id']}_d{dl}_aux_tr", kind="aux", arm="d-min", format="pt",
                                 aux_kind="fut1_arrival", episode=s["episode"], **s["aux"][dl]))
            else:
                rows.append(control_row(s, dl, v, pr_dir, "tr"))
        order = np.random.default_rng(a.seed + 1).permutation(len(rows))  # same order for every arm
        with open(os.path.join(a.out, f"train_{arm}.jsonl"), "w") as f:
            for k in order:
                f.write(json.dumps(rows[k]) + "\n")
        dd = [r.get("delta", 0.0) for r in rows if r.get("src") == "d1"]
        arm_stats[arm] = {"rows": len(rows), "replay": len(replay), "d1_control": len(dd),
                          "aux": sum(r.get("aux_kind") == "fut1_arrival" for r in rows),
                          "delta_hist": {str(x): dd.count(x) for x in TRAIN_DELTAS}}
    stats["arms"] = arm_stats
    stats["eval_sites"] = len(ev_sites)
    stats["eval_rows_per_variant"] = sum(len([dl for dl in EVAL_DELTAS if dl in s["rows"]]) for s in ev_sites)
    stats["eval_delta_hist"] = {str(dl): sum(dl in s["rows"] for s in ev_sites) for dl in EVAL_DELTAS}
    stats["eval_aux"] = len(ev_aux)
    f1 = arm_stats["F1"]["delta_hist"]
    gate = {"rebuild_fail_rate": round(stats["rebuild_fail"] / max(1, stats.get("calls", 0)), 4),
            "label_invalid": stats["label_invalid"],
            "train_delta_pos_share": round(1 - f1["0.0"] / max(1, sum(f1.values())), 4),
            "eval_sites": len(ev_sites), "eval_d1": stats["eval_delta_hist"]["1.0"], "eval_d2": stats["eval_delta_hist"]["2.0"]}
    gate["pass"] = bool(gate["rebuild_fail_rate"] <= 0.05 and gate["label_invalid"] == 0
                        and gate["train_delta_pos_share"] >= 0.30 and gate["eval_sites"] >= 400
                        and gate["eval_d1"] >= 150 and gate["eval_d2"] >= 150)
    stats["gate"] = gate
    json.dump(stats, open(os.path.join(a.out, "rows_stats.json"), "w"), indent=1)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
