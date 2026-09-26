"""E-ACC arms (docs/stage3/prereg_eacc.md §3): an arm name = base [+ modifiers joined by '_'].
  base  v1    production astra-couple@v1 F0 (harvest/couple/prompt.build_input), production overlay (committed arrow =
              decision-token centre, F3), three cameras, JPEG q90, no detail field
        v2    tools/eacc/prompt_v2 without the camera pose line; committed arrow = executed chunk motion (0.5 s);
              since_last_request context on
        v2cp  v2 + camera pose lines and tip height above the table (F5)
  mods  med   effort medium (else low)          r1 / r2  repeat index (ask-twice; the same input again)
        2cam  head + active (right) wrist only  noov     no overlay (v2 legend says so)
        noctx no since_last_request (v2)        dlow / dhigh  image detail field low / high (token probe)
Pure: builds the model input of one snapshot for one arm; no model calls."""
from __future__ import annotations

import os

import numpy as np

try:
    from . import bench as B
    from . import prompt_v2 as P2
except ImportError:  # run as a script from tools/eacc
    import bench as B  # type: ignore
    import prompt_v2 as P2  # type: ignore

BASES = ("v1", "v2", "v2cp")
MODS = ("med", "r1", "r2", "2cam", "noov", "noctx", "dlow", "dhigh", "ax", "gc", "gc2")
CAMS3 = ("cam_head", "cam_wrist_left", "cam_wrist_right")
CAMS2 = ("cam_head", "cam_wrist_right")


def parse_arm(name: str) -> dict:
    parts = name.split("_")
    base, mods = parts[0], parts[1:]
    if base not in BASES or any(m not in MODS for m in mods) or len(set(mods)) != len(mods):
        raise ValueError(f"arm {name!r}: base in {BASES}, modifiers in {MODS}")
    if base == "v1" and set(mods) & {"2cam", "noov", "noctx", "dlow", "dhigh", "ax", "gc", "gc2"}:
        raise ValueError(f"arm {name!r}: v1 is production only (effort / repeat modifiers)")
    return {"name": name, "base": base, "effort": "medium" if "med" in mods else "low",
            "rep": 2 if "r2" in mods else 1 if "r1" in mods else 0,
            "cams": CAMS2 if "2cam" in mods else CAMS3, "overlay": "noov" not in mods,
            "context": base != "v1" and "noctx" not in mods, "campose": base == "v2cp",
            "detail": "low" if "dlow" in mods else "high" if "dhigh" in mods else None,
            "axis": "ax" in mods and "noov" not in mods, "goalcheck": "gc2" if "gc2" in mods else ("gc" in mods)}


AXIS_LONG_M = 0.10
AXIS_COLORS = ((255, 40, 40), (40, 220, 40), (60, 120, 255))  # = couple.overlay.AXIS_COLORS (r / g / b = x / y / z)


def draw_axisguide(img, cam, tip) -> tuple:
    """AxisGuide-style (RSS 2026, arXiv 2606.06761) robot-frame basis axes drawn at the projected tip of this view:
    10 cm arrows along +x / +y / +z, each labelled '+x' / '+y' / '+z' (outlined), from robot kinematics and the
    camera model only. Returns (image, drawn?) -- nothing is drawn when the tip is outside the image."""
    from PIL import Image, ImageDraw

    from harvest.couple.overlay import _arrow, _px
    pt = _px(cam, tip)
    if pt is None or not (0 <= pt[0] < cam.W and 0 <= pt[1] < cam.H):
        return img, False
    base = Image.fromarray(np.asarray(img, np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=16)
    except (TypeError, OSError):  # older Pillow: bitmap default font
        font = None
    for e, col, lab in zip(np.eye(3), AXIS_COLORS, ("+x", "+y", "+z")):
        q = _px(cam, np.asarray(tip, float) + AXIS_LONG_M * e)
        if q is None:
            continue
        _arrow(d, pt, q, col, width=3, head_size=9)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            d.text((q[0] + 4 + dx, q[1] - 9 + dy), lab, fill=(0, 0, 0, 255), font=font)
        d.text((q[0] + 4, q[1] - 9), lab, fill=col + (255,), font=font)
    return np.asarray(Image.alpha_composite(base, layer).convert("RGB")), True


def _png(path: str) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB"))


def images(snap_dir: str, meta: dict, arm: dict) -> tuple:
    """({cam: JPEG bytes}, drawn legend dict or None, CamModel dict). Overlay = production couple.overlay.draw_overlay
    (tip ring, 2.5 s trace, committed arrow, axes; wrist corner boxes); v1 draws the decision-token centre, v2 the
    executed 0.5 s chunk motion."""
    from harvest.couple.overlay import CamModel, _px, draw_overlay
    from harvest.runtime.models import jpeg_bytes
    vv = B.vla_view(meta)
    nxt = vv["token_vec"] if arm["base"] == "v1" else vv["exec_vec"]
    if nxt is not None and float(np.linalg.norm(nxt)) < 1e-6:
        nxt = None
    models = {c: CamModel.from_dict(d) for c, d in B.cam_models(meta).items()}
    tip = np.asarray(meta["tip"], float)
    trace = B.trace_points(meta)
    out, drawn, ax_on = {}, None, set()
    for c in arm["cams"]:
        img = _png(os.path.join(snap_dir, f"{c}.png"))
        if arm["overlay"]:
            img = draw_overlay(img, models[c], tip=tip, trace=trace, next_vec=nxt, offset_vec=None,
                               wrist=c != "cam_head")
            if arm.get("axis") and c == "cam_head":  # head only: at the wrist the tip sits at the image edge and 10 cm arrows cover the view
                img, ok = draw_axisguide(img, models[c], tip)
                if ok:
                    ax_on.add(c)
        out[c] = jpeg_bytes(img)
    if arm["overlay"]:
        head = set()
        pt = _px(models["cam_head"], tip)
        m = models["cam_head"]
        if pt is not None and 0 <= pt[0] < m.W and 0 <= pt[1] < m.H:
            head |= {"ring", "axes"} | ({"next"} if nxt is not None else set())
        if sum(_px(m, p) is not None for p in trace) >= 2:
            head.add("trace")
        drawn = {"head": head, "wrist": {"next"} if nxt is not None else set(), "axisguide": sorted(ax_on)}
    return out, drawn, models, nxt


def build(snap_dir: str, meta: dict, arm: dict) -> tuple:
    """(model input, request dict, prompt id, prompt text)."""
    from harvest.couple import prompt as CP
    from harvest.couple.overlay import polylines
    from harvest.couple.params import CoupleParams
    imgs, drawn, models, nxt = images(snap_dir, meta, arm)
    cams = [c for c in arm["cams"] if c in imgs]
    req = B.request(meta, cams, version="v1" if arm["base"] == "v1" else "v2", next_vec=nxt, context=arm["context"])
    pts = B.trace_points(meta)[::-1]
    req["trace_uv"] = polylines({c: models[c] for c in cams}, pts) if arm["overlay"] else {}
    if arm["base"] == "v1":
        p = CoupleParams()
        inp = CP.build_input(req, imgs, p, meta["instruction"])
        pid = CP.PROMPT_ID["F0"]
    else:
        cp = ""
        if arm["campose"]:
            cp = P2.campose_text({c: meta["cams"][c] for c in cams}, cams,
                                 float(meta["tip"][2]) - float(meta["table_z"]))
        inp = P2.build_v2(req, imgs, cams, meta["instruction"], horizon_s=B.L_ARR, drawn=drawn, campose=cp,
                          detail=arm["detail"], goalcheck=arm.get("goalcheck", False))
        pid = (P2.PROMPT_ID + (f"+ax{P2.AXISGUIDE_ID}" if (drawn or {}).get("axisguide") else "")
               + (f"+gc2{P2.GOALCHECK2_ID}" if arm.get("goalcheck") == "gc2" else
                  f"+gc{P2.GOALCHECK_ID}" if arm.get("goalcheck") else ""))
    return inp, req, pid, inp[0]["content"][0]["text"]
