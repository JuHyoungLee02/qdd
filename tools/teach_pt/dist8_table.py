"""Print a compact table of an E-DIST8 comparison file (one JSON per line from dist8_compare.py), skipping empty pairs.
usage: python dist8_table.py <cmp jsonl>"""
import json
import sys

for line in open(sys.argv[1]):
    d = json.loads(line)
    if not d.get("n_pairs"):
        continue
    ni = "" if d.get("noninferior") is None else f" noninferior={d['noninferior']}(m {d['margin_mm']})"
    print(f"{d['name']:32s} n={d['n_pairs']:4d} X={d['x_median']:6.1f} Y={d['y_median']:6.1f} "
          f"CI={d['diff_ci95']} {d['verdict']}{ni} gz15 X={d['x_grasp_absz_le15']} Y={d['y_grasp_absz_le15']}")
