"""Licence / attribution manifest of the b4 assets (user-log 173 / 175): every row of products.json, assets_ph.json,
the gsor_* rows of objects_real.json and the usable materials, with source, licence and authors, and the licence
texts' URLs. usage: python tools/l8x_assets/licenses_b4.py OUT.json"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import materials as M  # noqa: E402

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "harvest", "sim", "assets_x")
TEXTS = {"CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
         "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/ (Poly Haven: https://polyhaven.com/license)"}


def main(argv=None):
    out = {"licence_texts": TEXTS, "commercial_use": "all entries: CC BY 4.0 (attribution required) or CC0 1.0",
           "assets": {}}
    for f, kind in (("products.json", "product"), ("objects_real.json", "object")):
        for k, o in json.load(open(os.path.join(D, f)))["objects"].items():
            if kind == "object" and not k.startswith("gsor_"):
                continue
            out["assets"][k] = {"kind": kind, "source": o.get("source"), "source_name": o.get("source_name"),
                                "license": o.get("license"), "attribution": o.get("attribution")}
    for k, a in json.load(open(os.path.join(D, "assets_ph.json")))["assets"].items():
        out["assets"]["fixture_" + k] = {"kind": "fixture", "source": a["source"], "license": a["license"],
                                         "attribution": "Poly Haven: " + ", ".join(a.get("authors") or [])}
    for k, r in M.usable(json.load(open(os.path.join(D, "materials.json")))["materials"]).items():
        out["assets"]["material_" + k] = {"kind": "material_" + r["role"], "source": r["source"],
                                          "license": r["license"],
                                          "attribution": "Poly Haven: " + ", ".join(r["authors"])}
    json.dump(out, open((argv or sys.argv[1:])[0], "w", newline="\n"), indent=1)
    from collections import Counter
    print(len(out["assets"]), Counter(v["kind"] for v in out["assets"].values()))


if __name__ == "__main__":
    main()
