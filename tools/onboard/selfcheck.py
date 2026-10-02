"""(pure) Onboarding tool (A) self-checks: aggregates the outputs of the existing + small new scripts this chain
calls into PASS/FAIL with numbers (design doc docs/research/embodiment_onboarding_2026-10-03.md §4.1's 7 steps /
the task's 6 self-checks). No new measurement here -- every check just reads a JSON file another script already
wrote (build_curobo9.py's <robot>_build.json, width_table.py's verify output, ready_search.py's output,
verify_limits.py's stdout, spawn_smoke9.py's *_smoke.json).

usage: selfcheck.py <robot> <arm> --build B.json [--width W.json] [--ready R.json] [--limits-log L.log]
                    [--smoke S.json] [--width-tol-mm 5] [--out report.md]
"""
from __future__ import annotations

import argparse
import json
import re


def check_tcp(build: dict, arm: str, tol_mm: float = 1.0) -> dict:
    """1. TCP sim vs cuRobo < 1 mm -- build_curobo9.py's own FK(random q) -> IK(back to that TCP) round trip."""
    sm = build["arms"][arm].get("ik_smoke", {})
    v = sm.get("pos_err_mm_mean")
    ok = v is not None and v < tol_mm
    return {"name": "tcp_sim_vs_curobo", "ok": ok, "value_mm": v, "tol_mm": tol_mm,
           "detail": f"ik_smoke pos_err_mm_mean={v} over {sm.get('ik_success')}/{sm.get('n')} solved"}


def check_limits_log(log_text: str | None) -> dict:
    """2. joint limits: sim = URDF = yml -- parses verify_limits.py's one-line stdout
    ("... arm values outside sim limits N, inside-margin violations M, worst excess E mrad")."""
    if not log_text:
        return {"name": "joint_limits", "ok": None, "detail": "not run (pass --limits-log)"}
    m = re.search(r"outside sim limits (\d+), inside-margin violations (\d+), worst excess (-?[\d.]+) mrad", log_text)
    if not m:
        return {"name": "joint_limits", "ok": False, "detail": "verify_limits.py output not parseable"}
    out_lim, out_margin, worst = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return {"name": "joint_limits", "ok": out_lim == 0, "out_of_sim_limits": out_lim,
           "inside_margin_violations": out_margin, "worst_excess_mrad": worst,
           "detail": f"{out_lim} solved joints outside the sim/URDF limit (must be 0), "
                     f"{out_margin} inside the 0.03 rad margin band, worst {worst} mrad"}


def check_selfcollision(build: dict, arm: str) -> dict:
    """3. self-collision ignore pairs are sane -- every ignored touching-at-stow pair must be within one arm/hand
    (same left_/right_ side), not a spurious cross-body contact."""
    touch = build["arms"][arm].get("ignored_touching_at_stow", [])

    def side(n):
        return "left" if "left_" in n else ("right" if "right_" in n else None)
    bad = [p for p in touch if side(p[0]) and side(p[1]) and side(p[0]) != side(p[1])]
    return {"name": "self_collision_pairs", "ok": not bad, "n_pairs": len(touch), "cross_side_bad": bad,
           "detail": f"{len(touch)} ignored touching-at-stow pairs, {len(bad)} cross left/right (must be 0)"}


def check_width_table(width: dict | None, tol_mm: float = 5.0) -> dict:
    """4. width table monotonic AND matches the mesh gap -- width_table.py verify mode's independent FK
    re-measurement vs the claimed width_to_joint table (the G1 pad-tip lesson)."""
    if not width:
        return {"name": "width_table", "ok": None, "detail": "not run (pass --width)"}
    ok = bool(width.get("monotonic_ok")) and width.get("worst_abs_diff_mm", 1e9) <= tol_mm
    return {"name": "width_table", "ok": ok, "monotonic_ok": width.get("monotonic_ok"),
           "worst_abs_diff_mm": width.get("worst_abs_diff_mm"), "tol_mm": tol_mm,
           "detail": f"{width.get('monotonic_detail')}; claimed-vs-measured worst |diff| "
                     f"{width.get('worst_abs_diff_mm')} mm (tol {tol_mm} mm)"}


def check_ready_pose(ready: dict | None) -> dict:
    """5. ready pose clears a standard clutter set -- ready_search.py's chosen candidate (data-grounded clutter
    threshold = spec.clutter_height_p90(), the R1 Pro '9.4 cm' lesson)."""
    if not ready:
        return {"name": "ready_pose_clutter", "ok": None, "detail": "not run (pass --ready)"}
    ok = bool(ready.get("pass"))
    c = ready.get("chosen")
    return {"name": "ready_pose_clutter", "ok": ok,
           "height_above_surface_m": c.get("height_above_surface_m") if c else None,
           "clutter_threshold_m": ready.get("clutter_threshold_m"),
           "n_candidates_rejected": sum(1 for t in ready.get("trials", []) if not t.get("clears_clutter")),
           "detail": (f"chosen height {c['height_above_surface_m']} m above surface (threshold "
                      f"{ready.get('clutter_threshold_m')} m)" if c else
                      f"no candidate cleared clutter {ready.get('clutter_threshold_m')} m "
                      f"(trials: {[t.get('height_above_surface_m') for t in ready.get('trials', [])]})")}


def check_render_probe(smoke: dict | None) -> dict:
    """6. render probe: 1 frame per camera, target in view -- spawn_smoke9.py already renders cam_head +
    cam_wrist_<arm> to PNG and reports a non-degenerate pixel mean + the sim TCP-vs-cuRobo-target error (reused
    here as a second, independent cross-check of self-check 1, from inside the full articulated sim)."""
    if not smoke:
        return {"name": "render_probe", "ok": None, "detail": "not run (pass --smoke; needs a render-OK GPU, "
                                                               "coordinate with the L9 owner first)"}
    cam_keys = [k for k in smoke if k.endswith("_mean")]
    blank = [k for k in cam_keys if smoke[k] < 1.0 or smoke[k] > 254.0]
    tcp_ok = smoke.get("tcp_err_mm", 1e9) < 5.0
    ok = (not blank) and tcp_ok
    return {"name": "render_probe", "ok": ok, "cams": {k: smoke[k] for k in cam_keys}, "blank_cams": blank,
           "tcp_err_mm": smoke.get("tcp_err_mm"), "tcp_above_surface_m": smoke.get("tcp_above_surface_m"),
           "detail": f"{len(cam_keys)} camera(s) rendered, {len(blank)} blank/saturated; sim TCP err "
                     f"{smoke.get('tcp_err_mm')} mm"}


def run_all(robot: str, arm: str, build: dict, width: dict | None, ready: dict | None, limits_log: str | None,
           smoke: dict | None, width_tol_mm: float, tcp_tol_mm: float) -> dict:
    checks = [check_tcp(build, arm, tcp_tol_mm), check_limits_log(limits_log), check_selfcollision(build, arm),
             check_width_table(width, width_tol_mm), check_ready_pose(ready), check_render_probe(smoke)]
    return {"robot": robot, "arm": arm, "checks": checks,
           "overall_pass": all(c["ok"] for c in checks if c["ok"] is not None)}


def to_markdown(report: dict) -> str:
    lines = [f"### {report['robot']} / {report['arm']}", "", "| check | pass | detail |", "|---|---|---|"]
    for c in report["checks"]:
        mark = "PASS" if c["ok"] else ("FAIL" if c["ok"] is False else "skip")
        lines.append(f"| {c['name']} | {mark} | {c['detail']} |")
    lines.append(f"\n**overall: {'PASS' if report['overall_pass'] else 'FAIL'}**")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("robot")
    ap.add_argument("arm")
    ap.add_argument("--build", required=True)
    ap.add_argument("--width", default=None)
    ap.add_argument("--ready", default=None)
    ap.add_argument("--limits-log", default=None)
    ap.add_argument("--smoke", default=None)
    ap.add_argument("--width-tol-mm", type=float, default=5.0)
    ap.add_argument("--tcp-tol-mm", type=float, default=1.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    build = json.load(open(a.build))
    width = json.load(open(a.width)) if a.width else None
    ready = json.load(open(a.ready)) if a.ready else None
    smoke = json.load(open(a.smoke)) if a.smoke else None
    limits_log = open(a.limits_log).read() if a.limits_log else None

    report = run_all(a.robot, a.arm, build, width, ready, limits_log, smoke, a.width_tol_mm, a.tcp_tol_mm)
    print(json.dumps(report, indent=1, default=str))
    md = to_markdown(report)
    print(md)
    if a.out:
        open(a.out, "w").write(md + "\n")


if __name__ == "__main__":
    main()
