"""Machine checks behind the static audit of the prompt health check (user-log 96): each check reads the live
production code / text and returns (flag, evidence). flag True = the defect is present now. No model calls.
usage: python tools/prompt_health/static_checks.py [--json out.json]"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _src(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _line(rel: str, pattern: str) -> str:
    for i, line in enumerate(_src(rel).splitlines(), 1):
        if re.search(pattern, line):
            return f"{rel}:{i}"
    return f"{rel}:?"


def check_couple() -> dict:
    from harvest.couple import prompt as CP
    from harvest.couple import schema as CS
    from harvest.couple.mock import answer
    from harvest.couple.params import CoupleParams
    out = {}
    t = CP.TEMPLATE
    out["C1_no_operational_definitions"] = (
        not re.search(r"(means|definition|defined as|=\s*both finger)", t, re.I),
        f"{_line('harvest/couple/prompt.py', 'A claim that something')}: claims grasped / released / placed / contact "
        "and execution / intent states are named but never defined (probe prompts.py:51 and :118 define 'held')")
    out["C2_no_axis_definition"] = (
        not re.search(r"x forward|away from the robot", t),
        f"{_line('harvest/couple/prompt.py', 'robot frame x')} and {_line('harvest/couple/prompt.py', 'in the robot frame')}: "
        "'robot frame' is used for edits but its axes are shown only by overlay colours (probe prompts.py:31 states them)")
    p_off = dataclasses.replace(CoupleParams(), overlay=False)
    text_off = CP.build_input({"a": 1}, {}, p_off, "T")[0]["content"][0]["text"]
    out["C3_overlay_legend_without_overlay"] = (
        "Overlay (drawn by code" in text_off,
        f"{_line('harvest/couple/prompt.py', 'Overlay .drawn by code')}: the legend (committed arrow, correction arrow, "
        "axes) is sent even with overlay off or when the arrows are not drawn (driver.py next_vec None / offset 0)")
    lim_prompt = re.search(r"\|delta_position_m\| <= ([0-9.]+)", t)
    out["C4_limit_without_margin"] = (
        lim_prompt is not None and abs(float(lim_prompt.group(1)) - CS.EDIT_MAX_M) < 1e-12,
        f"{_line('harvest/couple/prompt.py', 'delta_position_m. <= 0.05')} vs "
        f"{_line('harvest/couple/schema.py', '^EDIT_MAX_M')}: prompt limit = parser limit (P62: 5.1 cm answers were "
        "invalid in the probe)")
    keep_echo = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.02, 0.0), diff="keep")
    keep_echo["command"], keep_echo["edit"] = "edit", {"delta_position_m": [0.0, 0.02, 0.0],
                                                       "delta_rotation_rad": [0, 0, 0], "gripper": "keep"}
    try:
        CS.parse_answer(json.dumps(keep_echo), "F1", ("cam_head", "cam_wrist_right"), 1, 0.0, 1.0)
        rejected = False
    except CS.SchemaError:
        rejected = True
    out["C5_f1_keep_with_echoed_edit_rejected"] = (
        rejected, f"{_line('harvest/couple/schema.py', 'only with command edit')}: under F1 'diff=keep' plus the echoed "
                  "last edit is a schema error, though the F1 rule says 'keep to confirm it' (F0 is the default)")
    out["C6_prompt_id_scope"] = (
        True, f"{_line('harvest/couple/prompt.py', '^PROMPT_ID')}: the id hashes TEMPLATE + MODE_RULES + ANSWER_FORM only "
              "-- not the camera label strings, image encoding (JPEG q90) or the request field set; driver logs it per "
              "answer (driver.py:197)")
    out["C7_motion_field_always_null"] = (
        "motion=None" in _src("harvest/runtime/core.py"),
        f"{_line('harvest/runtime/core.py', 'motion=None')}: vla_now.motion is always null in the request")
    events = sorted(set(re.findall(r'_(?:fail_)?event\(now, "([a-z0-9_]+)"', _src("harvest/runtime/core.py")))
                    | set(re.findall(r'self\.flag\("([a-z_]+)"', _src("harvest/couple/driver.py"))))
    undefined = [e for e in events if e not in t]
    out["C8_event_names_undefined"] = (
        bool(undefined), f"events sent in request.events but not explained in the prompt: {undefined}")
    from harvest.couple.driver import MAG_CENTER_M
    out["C9_committed_arrow_length_semantics"] = (
        "next 0.5 s" in t and MAG_CENTER_M.get("xlarge", 0) >= 0.08,
        f"{_line('harvest/couple/driver.py', '^MAG_CENTER_M')}: arrow = decision token centre (xlarge 8 cm), prompt "
        f"says 'the motion the policy has committed for the next 0.5 s' ({_line('harvest/couple/prompt.py', 'next 0.5 s')}); "
        "R2 median 0.5 s chunk for xlarge is 38 mm and E-SR0 chunk adherence to the decision is low")
    out["C10_units_differ_from_probe"] = (
        "delta_position_m" in t and "delta_position_cm" in _src("harvest/astra_motion/prompts.py"),
        "production edits in metres (couple/prompt.py), probe calibration answers in centimetres (astra_motion/prompts.py:39)")
    out["C11_image_detail_differs_from_probe"] = (
        '"detail"' not in _src("harvest/couple/prompt.py") and '"detail": "high"' in _src("harvest/astra_motion/models.py"),
        f"{_line('harvest/couple/prompt.py', 'input_image')} (no detail, JPEG) vs "
        f"{_line('harvest/astra_motion/models.py', 'detail')} (detail high, PNG)")
    return out


def check_probe() -> dict:
    src = _src("harvest/astra_motion/grasp_probe.py")
    return {"P1_grasp_rows_log_prompt_version": (
        '"prompt_sha"' not in src,
        f"{_line('harvest/astra_motion/grasp_probe.py', 'prompt_sha|cost_usd.: round')}: grasp answer rows carry the prompt "
        "version (flag False after the 2026-09-26 fix)")}


def run() -> dict:
    return {**check_couple(), **check_probe()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = run()
    for k, (flag, ev) in res.items():
        print(f"{'DEFECT' if flag else 'ok    '} {k}: {ev}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({k: {"defect": bool(v[0]), "evidence": v[1]} for k, v in res.items()}, f, indent=1)


if __name__ == "__main__":
    main()
