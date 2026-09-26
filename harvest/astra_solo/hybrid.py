"""Track H (hybrid RGB / depth) of the upper model — the user-approved design (user-log: "우리 H 설계 (추천)고";
docs/research/rgb_depth_hybrid_survey_2026-09-27.md §4; canon §98 supp 1, three tracks R / H / D):
- input: the R request (nd-xyz@v1 body: ring-only head image, no table height / grid) + a depth tag line, and, when
  depth is present, the head z-depth as an extra image: FIXED metric range 0.25-1.60 m -> 8-bit grey, near = bright
  (255 at 0.25 m, 1 at 1.60 m), invalid or out of range = 0 (black), half resolution (nearest, so holes stay holes);
- output (one answer): `move` = the PT fields (point_2d + height intent) AND the R field (position_m xyz), plus the
  v2 edit / gripper / stop; either field may be absent (depth-off answers may skip the point; depth-less open samples
  omit the xyz so its loss is masked);
- runtime selector: depth valid and the point (or lift) resolves -> the PT converter (the D code); otherwise the
  model's xyz (the R path); the branch and the fallback reason are logged (fallback_rate);
- training: per call, depth dropped with p = 0.5; of the kept, half with zed_mini stereo noise
  (teach_l8d.depth_noise) — deterministic from the row id."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from ..astra_motion.schema import SchemaError, extract_json
from . import nd_prompts as NP
from . import pt_schema as PS
from . import schema as V2
from .resolve import INTENTS

VERSION = "astra-solo-h@v1"
D_LO, D_HI = 0.25, 1.60
DEPTH_LABEL = "head depth (grey, 0.25-1.60 m, near = bright, black = no depth)"
TAG_ON = "depth: sensor (head, metric, gray 0.25-1.60 m, near=bright)"
TAG_OFF = "depth: none"
P_DROP, P_NOISY_OF_KEPT = 0.5, 0.5
MODES = ("move", "edit", "gripper", "stop")

ANSWER = NP.ANSWERS["nd-xyz@v1"].replace(
    '"command": {"mode": "eef"|"edit"|"gripper"|"stop", "position_m": [x, y, z] (eef only)',
    '"command": {"mode": "move"|"edit"|"gripper"|"stop", "point_2d": [x, y] (move: 0-1000 in image 1, on the object '
    'the gripper should go to), "height": "above"|"grasp"|"place"|"lift" (move), "position_m": [x, y, z] (move: the '
    'TCP target in metres)').replace("(eef / edit: after the move;", "(move / edit: after the move;")
assert ANSWER != NP.ANSWERS["nd-xyz@v1"] and "position_m" in ANSWER
HINT = ("\nMOVE: give both the point in image 1 with a height (the code turns it into the target with the head depth "
        "when depth is present) and your own TCP target position_m (used when there is no depth).")
PROMPT_ID = hashlib.sha256("\n".join((NP.STATIC, NP.V2.NOW, HINT, ANSWER, TAG_ON, TAG_OFF, DEPTH_LABEL, VERSION))
                           .encode()).hexdigest()[:12]


def encode_depth(depth: np.ndarray, lo: float = D_LO, hi: float = D_HI, scale: float = 0.5) -> np.ndarray:
    z = np.asarray(depth, float)
    ok = np.isfinite(z) & (z >= lo) & (z <= hi)
    g = np.where(ok, np.rint(1 + 254 * (hi - np.where(ok, z, hi)) / (hi - lo)), 0).astype(np.uint8)
    if scale != 1.0:
        H, W = g.shape
        rows = (np.arange(int(H * scale)) / scale).astype(int)
        cols = (np.arange(int(W * scale)) / scale).astype(int)
        g = g[rows][:, cols]
    return g


def depth_png(depth: np.ndarray) -> bytes:
    import io

    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(encode_depth(depth)).save(b, format="PNG")
    return b.getvalue()


def request(body: str, now: str, depth: bool) -> str:
    """The H request: the R (nd-xyz@v1) body and NOW block, the depth tag, the H answer form."""
    return body + now + "\n" + (TAG_ON if depth else TAG_OFF) + HINT + ANSWER


def _command(d, err):
    c = d.get("command")
    if not isinstance(c, dict):
        err.append("command: missing")
        return None
    mode = V2._enum(c, "mode", MODES, err, "command")
    if mode in ("edit", "gripper", "stop"):
        return V2._command(dict(d, command=dict(c, mode={"edit": "edit", "gripper": "gripper", "stop": "stop"}[mode])),
                           err)
    if mode != "move":
        return None
    out = {"mode": "move"}
    if c.get("gripper") is None:
        c = dict(c, gripper="keep")
        out["gripper_defaulted"] = True
    out["gripper"] = V2._enum(c, "gripper", V2.GRIPPER, err, "command")
    out["point_2d"] = PS._point(c, err) if c.get("point_2d") is not None else None
    out["height"] = V2._enum(c, "height", INTENTS, err, "command") if (c.get("height") is not None or
                                                                     out["point_2d"] is not None) else None
    out["position_m"] = V2._vec3(c, "position_m", err, "command") if c.get("position_m") is not None else None
    if out["position_m"] is None and out["point_2d"] is None and out["height"] != "lift":
        err.append("command: move needs point_2d + height or position_m")
    return out


def validate(text: str):
    err: list = []
    try:
        d = extract_json(text)
    except SchemaError as e:
        return None, [str(e)]
    out = {"assessment": V2._assessment(d, err), "command": _command(d, err), "reason": str(d.get("reason", ""))[:400]}
    return (out, []) if not err else (None, err)


def select(cmd: dict, resolver):
    """-> (goal [x, y, z] | None, branch "pt" | "xyz" | "none", info). resolver(cmd) -> (goal | None, info) is the
    PT converter bound to this call's valid depth; None = no valid depth."""
    info = {}
    wants_pt = cmd.get("point_2d") is not None or cmd.get("height") == "lift"
    if resolver is None:
        info["fallback"] = "no_depth"
    elif not wants_pt:
        info["fallback"] = "no_point"
    else:
        goal, rinfo = resolver(cmd)
        info["resolved"] = rinfo
        if goal is not None:
            return [float(v) for v in goal], "pt", info
        info["fallback"] = "unresolved"
    if cmd.get("position_m") is not None:
        return [float(v) for v in cmd["position_m"]], "xyz", info
    return None, "none", info


def describe(cmd: dict, res: dict | None) -> str:
    """History wording of a move (measured, no object ground truth): what was given and which branch ran."""
    parts = []
    if cmd.get("point_2d") is not None:
        parts.append(f"point ({cmd['point_2d'][0]:.0f}, {cmd['point_2d'][1]:.0f}) in image 1")
    if cmd.get("height"):
        parts.append(f"height {cmd['height']}")
    if cmd.get("position_m") is not None:
        p = cmd["position_m"]
        parts.append(f"position ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})")
    s = "move " + ", ".join(parts) + f", gripper {cmd['gripper']}"
    if res:
        g = res.get("goal")
        used = {"pt": "the point with the depth", "xyz": "your position", "none": "nothing"}[res.get("branch", "none")]
        s += f" [used {used}" + (f"; target ({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f})" if g else "") + "]"
    return s


def h_answer(xyz_answer: str, pt_answer: str | None, omit_xyz: bool = False) -> str:
    """Truth answer of H from the xyz (L8) and pt truth answers of the same state."""
    a = json.loads(xyz_answer)
    x = a["command"]
    p = json.loads(pt_answer)["command"] if pt_answer else None
    if p is not None and p.get("mode") in ("edit", "gripper", "stop"):
        cmd = dict(p)
    elif x.get("mode") == "eef":
        cmd = {"mode": "move"}
        if p is not None and p.get("mode") == "point":
            if p.get("point_2d") is not None:
                cmd["point_2d"] = p["point_2d"]
            cmd["height"] = p["height"]
        if not omit_xyz:
            cmd["position_m"] = x["position_m"]
        cmd["gripper"] = x.get("gripper", "keep")
    else:
        cmd = dict(x)
    return json.dumps(dict(a, command=cmd))


def train_depth_mode(row_id: str) -> str:
    """'off' (p 0.5) | 'noisy' (half of the kept) | 'clean' — deterministic from the row id."""
    u = int(hashlib.sha256(("h-depth:" + row_id).encode()).hexdigest()[:12], 16) / 16 ** 12
    return "off" if u < P_DROP else ("noisy" if u < P_DROP + (1 - P_DROP) * P_NOISY_OF_KEPT else "clean")
