"""General spatial QA (S9 RefSpatial, JingkunAn/RefSpatial, Apache-2.0, NeurIPS 2025): single turns of the released
multi-turn conversations -> our records with a separate instruction ('frame: pixel' for point answers,
'frame: none' for choice answers), so they never share the runtime answer form. Point answers ([(x, y)] in 0..1)
become pixels of the stored image. The 8-bit per-image min-max depth PNG is not used (not metric)."""
from __future__ import annotations

import io
import json
import os
import re

_PT = re.compile(r"\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)")


def points(ans):
    return [(float(a), float(b)) for a, b in _PT.findall(ans or "")]


def convert(files, out, max_rows=2000, seed=0):
    import numpy as np
    import pyarrow.parquet as pq
    from PIL import Image
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    rng = np.random.default_rng(seed)
    recs = []
    for src, path in files.items():
        for ri, r in enumerate(pq.read_table(path).to_pylist()):
            img_b = (r.get("image_0") or {}).get("bytes")
            if not img_b:
                continue
            im = Image.open(io.BytesIO(img_b)).convert("RGB")
            W, H = im.size
            img = os.path.join(out, "frames", f"refsp_{src}_{ri}.jpg")
            im.save(img, quality=90)
            v = r["conversations"]["value"]
            turns = list(range(0, len(v) - 1, 2))
            for t in rng.permutation(turns)[:3]:
                q, a = v[t], v[t + 1]
                pts = points(a)
                base = f"source: refspatial/{src}\n"
                if pts and "normalized pixel" in q:
                    q2 = re.sub(r"Your answer should be formatted.*$", "", q, flags=re.S).strip()
                    prompt = (base + f"frame: pixel\nCAMERAS\n- Image 1: {W}x{H} px; camera: unknown (no calibration).\n"
                              + q2 + "\nReturn JSON only: {\"points\": [[u, v], ...]} in pixels.")
                    ans = {"points": [[int(round(x * (W - 1))), int(round(y * (H - 1)))] for x, y in pts]}
                    kind = "refsp_point"
                    frame = "pixel"
                else:
                    prompt = base + "frame: none\n" + q + "\nReturn JSON only: {\"answer\": string}."
                    ans = {"answer": a}
                    kind = "refsp_text"
                    frame = "none"
                recs.append({"id": f"refsp_{src}_{ri}_{t}", "kind": "qa_xemb", "qa_kind": kind, "source": f"refspatial/{src}",
                             "frame": frame, "prompt": prompt, "images": [img], "answer": json.dumps(ans)})
                if len(recs) >= max_rows:
                    break
    with open(os.path.join(out, "records_P.jsonl"), "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    return {"n_P": len(recs), "by_kind": {k: sum(r["qa_kind"] == k for r in recs) for k in {r["qa_kind"] for r in recs}}}
