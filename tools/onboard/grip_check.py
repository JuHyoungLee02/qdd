"""(pure) Onboarding self-checks for the generic grip layer (harvest/l9/hand9.py), one per item of the user order
10-03 03시 "집게·손 공통 층":
  grip1_gap_table    -- the measured free-gap table exists, closed -> open strictly increasing, monotonic along the
                        closing path, closed <= 5 mm, max >= 3 cm; reports the old table's error (pad-tip lesson)
  grip2_open_empty   -- pre-open / empty verdict from the measured gap: the closed row reads EMPTY, every object
                        width the table can take reads CONTACT on its own row, pre-open w + 2 cm round-trips
  grip3_any_finger   -- holding reads ALL fingers: every finger joint of the robot is in the table (max effort over
                        all of them), every opposition side has a contact-sensed body, the one generic holding
                        function fires on the last finger / last joint alone
  grip4_frame        -- the derived grasp frame (fingertip convergence, closing axis, palm normal; hand_sweep.py)
                        agrees with frame G, and the GraspGen-X registration of this gripper exists
  grip6_torso        -- (optional, episode data) torso / lift joints fixed during each episode, inside their range
                        and varied between episodes
usage: grip_check.py <profile> <arm> [--ggx-dir D] [--torso T.json] [--out report.md]
       (profile = ffw_sg2 | franka_mast | r1pro | g1 | a new robot's profile; laptop or pod)"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from harvest.l9 import hand9 as H  # noqa: E402


def robot_fingers(profile: str, arm: str) -> tuple:
    """(finger joints, finger contact bodies) the sim uses for this profile / arm."""
    from harvest.l9 import robot9 as R9
    if profile in R9.V2_PROFILES:
        return tuple(R9.V2[profile]["arms"][arm]["fingers"]), tuple(R9.v2_contact_bodies(profile, arm))
    if profile == "franka_mast":
        return tuple(R9.FINGERS), tuple(R9.FINGER_BODIES)
    from harvest.sim import scene as S
    return tuple(S.GRIP_ALL[arm]), tuple(S.FINGER_BODIES[arm])


def check_gap_table(t) -> dict:
    if t is None:
        return {"name": "grip1_gap_table", "ok": False, "detail": "no gap9 table (run tools/onboard/hand_sweep.py)"}
    m = t.meta
    inc = bool((np.diff(t.gap) > 0).all())
    ok = inc and bool(m.get("path_monotonic", True)) and 0.0 <= t.closed_gap <= 0.005 and t.max_gap >= 0.03
    old = m.get("worst_claimed_diff_mm")
    return {"name": "grip1_gap_table", "ok": ok, "max_gap_mm": round(t.max_gap * 1e3, 1),
            "closed_gap_mm": round(t.closed_gap * 1e3, 1), "old_max_mm": None if m.get("old_max_opening_m") is None
            else round(m["old_max_opening_m"] * 1e3, 1), "old_table_worst_diff_mm": old,
            "detail": f"{len(t.gap)} rows, closed {t.closed_gap * 1e3:.1f} mm, max {t.max_gap * 1e3:.1f} mm (old "
                      f"table max {m.get('old_max_opening_m')}), old width table worst |claimed - measured| {old} mm"}


def check_open_empty(t) -> dict:
    if t is None:
        return {"name": "grip2_open_empty", "ok": False, "detail": "no gap9 table"}
    bad = []
    if H.close_verdict(t.gap_of_q(t.Q[0]), 0.03, t.closed_gap) != "EMPTY":
        bad.append("closed row not EMPTY")
    for i in range(1, len(t.gap)):
        if t.gap[i] <= t.closed_gap + H.EMPTY_TOL + 0.002:
            continue
        q = t.Q[i]
        v = H.close_verdict(t.gap_of_q(q), float(t.gap_tcp[i]), t.closed_gap, gap_tcp=t.tcp_gap_of_q(q))
        if v != "CONTACT":
            bad.append(f"row {i} ({t.gap[i] * 1e3:.0f} mm) -> {v}")
    rt = []
    for w in np.linspace(0.005, t.max_gap - H.PRE_CLEAR, 8):
        g = t.gap_of_q(t.joints_for_gap(w + H.PRE_CLEAR))
        rt.append(abs(g - (w + H.PRE_CLEAR)))
    if max(rt) > 0.001:
        bad.append(f"pre-open round trip off by {max(rt) * 1e3:.2f} mm")
    return {"name": "grip2_open_empty", "ok": not bad, "issues": bad[:5],
            "detail": f"closed row EMPTY, {len(t.gap) - 1} open rows CONTACT on their own TCP-plane width, pre-open "
                      f"(w + {H.PRE_CLEAR * 100:.0f} cm) round trip max {max(rt) * 1e3:.2f} mm"
                      + (f"; FAIL: {bad[:3]}" if bad else "")}


def check_any_finger(t, profile: str, arm: str) -> dict:
    if t is None:
        return {"name": "grip3_any_finger", "ok": False, "detail": "no gap9 table"}
    joints, bodies = robot_fingers(profile, arm)
    missing = [j for j in joints if j not in t.joints]
    sides = {H.side_of(b, t) for b in bodies}
    n = len(joints)
    f, e = np.zeros(len(bodies)), np.zeros(n)
    f[-1], e[-1] = 3.0, 1.5
    fires = H.holding(f, e) and not H.holding(np.zeros(len(bodies)), e)
    ok = not missing and {0, 1} <= sides and fires
    return {"name": "grip3_any_finger", "ok": ok, "n_joints": n, "n_contact_bodies": len(bodies),
            "missing_joints": missing, "sides_sensed": sorted(s for s in sides if s is not None),
            "detail": f"{n} finger joints (effort = max over all; missing from table {missing}), {len(bodies)} "
                      f"contact bodies covering sides {sorted(s for s in sides if s is not None)} (need [0, 1]), "
                      f"holding fires on the last finger + last joint alone: {fires}"}


def check_frame(t, ggx_dir: str | None) -> dict:
    if t is None:
        return {"name": "grip4_frame", "ok": False, "detail": "no gap9 table"}
    fc = dict(t.meta.get("frame_check") or {})
    reg = H.GGX_GRIPPER.get(t.name)
    have = None
    if ggx_dir:
        have = any(os.path.exists(os.path.join(ggx_dir, f"{reg}{s}.json")) for s in ("", "_sweep"))
    ok = bool(fc.get("ok")) and (have is not False)
    return {"name": "grip4_frame", "ok": ok, "frame": fc, "ggx_gripper": reg, "ggx_registered": have,
            "detail": f"closing {fc.get('closing_err_deg')} deg, approach {fc.get('approach_err_deg')} deg, tcp lateral "
                      f"{fc.get('tcp_lateral_mm')} mm, TCP plane on pads {fc.get('tcp_plane_on_pads')}; GraspGen-X "
                      f"gripper '{reg}' registered: {have}"}


def check_torso(eps: list | None, ranges: dict | None) -> dict:
    if not eps:
        return {"name": "grip6_torso", "ok": None, "detail": "not run (pass --torso episodes.json)"}
    r = H.torso_check(eps, ranges, min_spread=0.0)
    return {"name": "grip6_torso", "ok": r["ok"], **r,
            "detail": f"{r['n_episodes']} episodes, moved during an episode {len(r['moved'])}, outside range "
                      f"{len(r['outside'])}, spread between episodes {r['spread']}"}


def run(profile: str, arm: str, ggx_dir: str | None = None, torso: dict | None = None) -> dict:
    t = H.table_for(profile, arm)
    checks = [check_gap_table(t), check_open_empty(t), check_any_finger(t, profile, arm), check_frame(t, ggx_dir),
              check_torso((torso or {}).get("episodes"), (torso or {}).get("ranges"))]
    return {"profile": profile, "arm": arm, "gripper": H.GRIPPER_JSON.get((profile, arm)), "checks": checks,
            "overall_pass": all(c["ok"] for c in checks if c["ok"] is not None)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("arm")
    ap.add_argument("--ggx-dir", default=None)
    ap.add_argument("--torso", default=None, help='{"episodes": [{joint: [q...]}], "ranges": {joint: [lo, hi]}}')
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = run(a.profile, a.arm, a.ggx_dir, json.load(open(a.torso)) if a.torso else None)
    lines = [f"### grip layer: {a.profile} / {a.arm} ({r['gripper']})", "", "| check | pass | detail |", "|---|---|---|"]
    for c in r["checks"]:
        lines.append(f"| {c['name']} | {'PASS' if c['ok'] else ('skip' if c['ok'] is None else 'FAIL')} | {c['detail']} |")
    lines.append(f"\n**overall: {'PASS' if r['overall_pass'] else 'FAIL'}**")
    print("\n".join(lines))
    if a.out:
        open(a.out, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
