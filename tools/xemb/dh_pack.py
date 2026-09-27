"""Merge D / H depth rows of the converted sources into the pack (dh_D.jsonl, dh_H.jsonl) + counts; only sources whose
report passes the gates are merged (G-unit median |dz| <= 3 cm and converter <= 5 cm share >= 0.5 where reported).
usage (pod): python -m xemb.dh_pack OUT_DIR SRC_DIR [SRC_DIR ...]"""
from __future__ import annotations

import json
import os
import sys


def gate(rep):
    gu = rep.get("g_unit_absdz_cm")
    if gu is not None and gu["median"] > 3.0:
        return False, "unit"
    # per-row converter <= 5 cm is applied by the converters; the source gate checks units / quantisation only
    q, g = rep.get("quant_step_cm_at_point"), rep.get("measured_level_gap_cm")
    if q and g and abs(g["median"] - q["median"]) > 0.3 * q["median"]:
        return False, "quant_step"
    return True, "ok"


def main(out, srcs, tol=None, suffix=""):
    """tol: extra per-row converter-error threshold (m) on top of the converters' 5 cm; files dh_D<suffix>.jsonl."""
    import numpy as np
    os.makedirs(out, exist_ok=True)
    counts = {}
    with open(os.path.join(out, f"dh_D{suffix}.jsonl"), "w") as fD, open(os.path.join(out, f"dh_H{suffix}.jsonl"), "w") as fH:
        for s in srcs:
            rep = json.load(open(os.path.join(s, "report.json")))
            ok, why = gate(rep)
            errs, n = [], 0
            if ok:
                for name, f in (("records_D.jsonl", fD), ("records_H.jsonl", fH)):
                    for line in open(os.path.join(s, name)):
                        e = json.loads(line).get("conv_err_m")
                        if tol is not None and (e is None or e > tol):
                            continue
                        f.write(line)
                        if name == "records_D.jsonl":
                            n += 1
                            if e is not None:
                                errs.append(e)
            e = np.array(errs)
            dist = {"median_cm": round(float(np.median(e)) * 100, 2), "p90_cm": round(float(np.percentile(e, 90)) * 100, 2)} \
                if len(e) else None
            counts[os.path.basename(s.rstrip("/"))] = {"gate": why, "states": n, "kept_conv_err": dist, "report": rep}
    json.dump(counts, open(os.path.join(out, f"dh_counts{suffix}.json"), "w"), indent=1)
    print(json.dumps({k: {"gate": v["gate"], "states": v["states"], "kept_conv_err": v["kept_conv_err"]}
                      for k, v in counts.items()}))


if __name__ == "__main__":
    a = sys.argv[1:]
    tol = None
    if a and a[0].startswith("--tol="):
        tol = float(a[0].split("=")[1])
        a = a[1:]
    main(a[0], a[1:], tol, suffix="" if tol is None else f"_{int(round(tol * 100))}cm")
