"""Why stacking bases fail: per candidate (stable, name-checked, height 3-10 cm) its top surface and the base rule.
usage: python tools/l8x_assets/base_stats.py"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.teach_l8d import xnew as XN  # noqa: E402


def main():
    rows = XN.load_real_rows()
    for k, r in sorted(rows.items()):
        if r.get("split") != "train" or not r.get("task_target_ok") or not 0.03 <= r["height"] <= 0.10:
            continue
        t = r.get("top_surface")
        box = 4 * r["half_extents"][0] * r["half_extents"][1]
        print(f"{k[:40]:40s} {r['noun']:12s} h={r['height']:.3f} w={r['grasp_width']:.3f} L={r['length']:.3f} "
              f"top={None if not t else (round(t['area'] / box, 2), t['top_z'])}")


if __name__ == "__main__":
    main()
