"""Prototype run (CPU only, free): convert the survey samples and write records, gates and overlay sheets.
usage: python -m xemb.run_proto SOURCE(molmobot|behavior|robotwin) SRC_ROOT OUT_DIR
pod: PYTHONPATH=<code dir> /data/harvest/venv_e3st/bin/python -m xemb.run_proto ..."""
from __future__ import annotations

import json
import os
import random
import sys

from . import sheet


def main(argv):
    src, root, out = argv[1], argv[2], argv[3]
    if src == "molmobot":
        from . import src_molmobot as M
        rep, items = M.convert(root, out)
    elif src == "refspatial":
        from . import src_refspatial as M
        R_ = "/data/harvest/data/upper_vlm_survey/raw/JingkunAn__RefSpatial/SubsetVisualization"
        rep = M.convert({"sim": f"{R_}/Simulator-00000-of-00001.parquet", "3d": f"{R_}/3D-00000-of-00001.parquet"}, out)
        items = []
    elif src == "rb2":
        from . import src_rb2 as M
        rep, items = M.convert(root, out)
    elif src == "mbfranka":
        from . import src_mbfranka as M
        rep, items = M.convert(root, out)
    elif src == "behavior":
        from . import src_behavior as M
        rep, items = M.convert(root, out)
    elif src == "robotwin":
        from . import src_robotwin as M
        rep, items = M.convert(root, out)
    else:
        raise SystemExit(f"unknown source {src}")
    random.Random(0).shuffle(items)
    fails = [it for it in items if it.get("fail")]
    rest = [it for it in items if not it.get("fail")]
    rep["sheets"] = sheet.sheets(rest[:36], os.path.join(out, "sheets", "sheet"))
    rep["sheets_fail"] = sheet.sheets(fails[:24], os.path.join(out, "sheets", "fail"))
    with open(os.path.join(out, "gates.json"), "w") as f:
        json.dump(rep, f, indent=1, default=float)
    print(json.dumps({k: v for k, v in rep.items() if k != "per_episode"}, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv)
