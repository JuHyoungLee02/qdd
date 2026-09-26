"""E-PT closed-loop gate (prereg_pt.md §5.3): exit 0 when the DEV summary passes (valid >= 0.95 and approach xy
median <= 20 mm), else 1. usage: python gate.py <eval dir>/summary.json"""
import json
import sys

s = json.load(open(sys.argv[1]))["control_all"]
ok = s["valid_rate"] >= 0.95 and s["approach_xy_median_mm"] is not None and s["approach_xy_median_mm"] <= 20
print("GATE " + json.dumps({"pass": ok, "valid": s["valid_rate"], "approach_xy_median_mm": s["approach_xy_median_mm"]}))
sys.exit(0 if ok else 1)
