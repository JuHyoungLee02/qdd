"""Measure each robot's arm tracking overshoot for the L9 common executor (audit row 7, robot9.TRACK_OVERSHOOT).

The commanded joint path is resampled to <= cap rad per control step; the simulated arm lags and then catches up with
larger steps. overshoot = meta max_dq_rad / cap (the cap in effect for the run). Per robot over the successful v2
episodes (motion_version l9v2-*): quantiles, the share over the 0.04 gate and the cap that keeps the chosen quantile
under the gate (0.04 / overshoot, 1 mrad steps, <= the default cap).

  python -m tools.l9.track_lag --cap 0.034 /data/harvest/l9v2/pilot1 /data/harvest/l9v2/pilotR ... [--q 0.95]

Pure (json + numpy); reads only meta.json files."""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

GATE = 0.04


def scan(roots, motion_prefix: str = "l9v2", success_only: bool = True) -> dict:
    """robot -> list of max_dq_rad over the episodes under roots."""
    out: dict = {}
    for root in roots:
        for d, _, files in os.walk(root):
            if "meta.json" not in files:
                continue
            try:
                m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not str(m.get("motion_version") or "").startswith(motion_prefix):
                continue
            if success_only and not m.get("success"):
                continue
            v = m.get("max_dq_rad")
            if v is None:
                continue
            out.setdefault(str(m.get("robot") or "ffw_sg2"), []).append(float(v))
    return out


def summarize(dq, cap: float, q: float = 0.95, default_cap: float = 0.034) -> dict:
    a = np.asarray(dq, float)
    r = a / cap
    ov = float(np.quantile(r, q)) if len(r) else 0.0
    sug = default_cap if ov <= 1.0 else min(default_cap, math.floor(GATE / ov * 1000.0 + 1e-9) / 1000.0)
    return {"n": int(len(a)), "over_gate": int((a > GATE).sum()), "p50": round(float(np.median(r)), 3) if len(r) else None,
            "q": q, "overshoot": round(ov, 3), "max": round(float(r.max()), 3) if len(r) else None,
            "suggested_cap": sug}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--cap", type=float, default=0.034, help="the command cap in effect for these runs")
    ap.add_argument("--q", type=float, default=0.95)
    ap.add_argument("--all", action="store_true", help="failed episodes too")
    a = ap.parse_args(argv)
    res = {k: summarize(v, a.cap, a.q) for k, v in sorted(scan(a.roots, success_only=not a.all).items())}
    print(json.dumps({"cap": a.cap, "robots": res}, indent=1))


if __name__ == "__main__":
    main()
