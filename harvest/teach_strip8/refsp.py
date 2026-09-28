"""RefSpatial (JingkunAn/RefSpatial, Apache-2.0, NeurIPS 2025) Simulator subset -> general pointing rows for D round 2
(prereg_dround2.md §1 c). Single-point turns only; the row copies the object-pointing pack's form (source / frame
tags, 0-1000 point answer) so it never shares the runtime answer form; kind 'aux' (prompt inline, one image)."""
from __future__ import annotations

import json
import re

_PT = re.compile(r"\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)")
_FMT = re.compile(r"\s*Your answer should be formatted.*$", re.S)
TAIL = ("Answer in 0-1000 normalised image coordinates (x to the right, y down). If it is not visible, answer "
        "{\"visible\": false}.\nReturn JSON only: {\"point\": [x, y]}.")


def rows_of(rec: dict, img_dir: str, W: int, H: int) -> list:
    v = rec.get("conversations") or []
    out = []
    for t in range(0, len(v) - 1, 2):
        q, a = v[t].get("value", ""), v[t + 1].get("value", "")
        pts = _PT.findall(a)
        if len(pts) != 1 or "normalized pixel" not in q and "Your answer should be formatted" not in q:
            continue
        x, y = (float(p) for p in pts[0])
        if not (0 <= x <= 1 and 0 <= y <= 1):
            continue
        q2 = _FMT.sub("", q).strip()
        prompt = ("source: refspatial/simulator\nframe: pixel\nCAMERAS\n"
                  f"- Image 1: {W}x{H} px; camera: unknown (no calibration).\n{q2}\n{TAIL}")
        out.append({"id": f"refsp_sim_{rec['id']}_{t}", "kind": "aux", "aux_kind": "refsp_point", "prompt": prompt,
                    "images": [f"{img_dir}/{rec['image'][0]}"],
                    "answer": json.dumps({"point": [int(round(x * 1000)), int(round(y * 1000))]})})
    return out
