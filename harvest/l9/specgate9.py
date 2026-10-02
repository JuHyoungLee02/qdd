"""L9 label spec version + build-time hard gates (pure; user 10-02 "vlm에 너무 혼란을 주지않아야해 꼭", L9_PRINCIPLES §0).

SPEC = the frozen label spec of new episodes (meta "spec_version"). Episodes written before the tag existed are
classified from their meta: L9 v2 with every pick under label_rule natural_v1 -> SPEC (the frozen spec's single-arm
part: arm = object side, natural_v1 grasp labels; format v3 / camera slots are build-time), v1 / other rules ->
"pre-final" (kept on disk, dropped from training builds).

Gates on a training set (each must hold, else the build is rejected):
  1. contradictions == 0: rows of the same situation (instruction, step, rounded TCP / target / place) must not
     disagree on arm, approach, rot or point (> 40 / 1000)
  2. one spec version
  3. one overlay convention, one prompt template family, one colour legend
  4. schema: every answer parses, command keys / types / ranges valid"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict

SPEC = "L9v2-spec-final"
APPROACH = ("top", "oblique", "front", "side")
ARMS = ("left", "right")
CMD_KEYS = {"mode", "position_m", "gripper", "quat_wxyz", "point_2d", "height", "approach", "rot", "arm", "hand",
            "delta_m", "role", "sync", "point_px", "wrist_bin", "skill", "point2", "axis", "pivot_2d", "turn", "amount",
            "handover_point", "handover_height", "giver", "receiver"}
MODES = {"point", "eef", "edit", "gripper", "stop", "lift", "push"}


def spec_of(meta: dict) -> str:
    if meta.get("spec_version"):
        return meta["spec_version"]
    g = meta.get("grasp_v2")
    if g is None:
        return "pre-final"
    rules = {p.get("label_rule") for p in g.get("picks") or [] if p.get("label_rule")}
    return SPEC if rules <= {"natural_v1"} else "pre-final"


def template_family(text: str) -> str:
    """Section headers of a request (capitalised lines ending in ':' or all-caps headings), hashed."""
    heads = [ln.strip() for ln in text.split("\n") if re.match(r"^[A-Z][A-Z0-9 /()_-]{3,}$", ln.strip())]
    return hashlib.sha256("|".join(heads).encode()).hexdigest()[:12]


def schema_errors(answer: str) -> list:
    errs = []
    try:
        a = json.loads(answer)
    except (TypeError, ValueError):
        return ["answer not json"]
    cmds = a.get("commands") or ([a.get("command")] if a.get("command") is not None else [])
    for c in cmds:
        if not isinstance(c, dict):
            errs.append("command not an object")
            continue
        extra = set(c) - CMD_KEYS
        if extra:
            errs.append(f"unknown command keys {sorted(extra)}")
        if c.get("mode") not in MODES:
            errs.append(f"mode {c.get('mode')!r}")
        if "arm" in c and c["arm"] not in ARMS:
            errs.append(f"arm {c['arm']!r}")
        if c.get("approach") is not None and c["approach"] not in APPROACH:
            errs.append(f"approach {c['approach']!r}")
        if c.get("rot") is not None and not (isinstance(c["rot"], int) and 0 <= c["rot"] <= 11):
            errs.append(f"rot {c['rot']!r}")
        for k in ("point_2d", "point2", "point_px", "pivot_2d", "handover_point"):
            p = c.get(k)
            if p is not None and not (isinstance(p, list) and len(p) == 2 and all(isinstance(v, int) and 0 <= v <= 1000
                                                                                     for v in p)):
                errs.append(f"{k} {p!r}")
    return errs


def situation_key(row: dict) -> tuple | None:
    gt = row.get("gt") or {}
    if not gt.get("tcp"):
        return None
    r3 = (lambda v: tuple(round(float(x), 2) for x in v) if v else None)  # noqa: E731  (1 cm)
    return (row.get("instruction") or row.get("task"), row.get("step"), r3(gt.get("tcp")), r3(gt.get("tgt")),
            r3(gt.get("place")))


def decision(answer: str) -> tuple:
    try:
        a = json.loads(answer)
    except (TypeError, ValueError):
        return ()
    cmds = a.get("commands") or ([a.get("command")] if a.get("command") is not None else [])
    out = []
    for c in cmds:
        c = c or {}
        out.append((c.get("arm"), c.get("approach"), c.get("rot"), tuple(c.get("point_2d") or ())))
    return tuple(out)


def contradictions(rows: list) -> int:
    seen = defaultdict(set)
    for r in rows:
        k = situation_key(r)
        if k is None or r.get("answer") is None:
            continue
        seen[k].add(decision(r["answer"]))
    n = 0
    for ds in seen.values():
        if len(ds) <= 1:
            continue
        base = next(iter(ds))
        for d in ds:
            if len(d) != len(base):
                n += 1
                continue
            for x, y in zip(d, base):
                if x[:3] != y[:3] or (x[3] and y[3] and max(abs(i - j) for i, j in zip(x[3], y[3])) > 40):
                    n += 1
                    break
    return n


def gates(rows: list, texts: dict) -> dict:
    """rows: control rows (with 'answer', 'spec_version', 'overlay', 'prompt_path'); texts: prompt_path -> text."""
    specs = {r.get("spec_version") for r in rows}
    overlays = {r.get("overlay", "mono") for r in rows}
    legends = {r.get("colour_legend", "none") for r in rows}
    fams = {template_family(texts[r["prompt_path"]]) for r in rows if r.get("prompt_path") in texts}
    schema = sum(1 for r in rows if r.get("answer") is not None and schema_errors(r["answer"]))
    out = {"contradictions": contradictions(rows), "spec_versions": sorted(map(str, specs)),
           "overlays": sorted(overlays), "colour_legends": sorted(legends), "template_families": len(fams),
           "schema_errors": schema}
    out["ok"] = (out["contradictions"] == 0 and len(specs) == 1 and len(overlays) == 1 and len(legends) == 1
                 and len(fams) <= 1 and schema == 0)
    return out
