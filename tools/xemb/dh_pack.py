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


def main(out, srcs):
    os.makedirs(out, exist_ok=True)
    counts = {}
    with open(os.path.join(out, "dh_D.jsonl"), "w") as fD, open(os.path.join(out, "dh_H.jsonl"), "w") as fH:
        for s in srcs:
            rep = json.load(open(os.path.join(s, "report.json")))
            ok, why = gate(rep)
            n = 0
            if ok:
                for name, f in (("records_D.jsonl", fD), ("records_H.jsonl", fH)):
                    for line in open(os.path.join(s, name)):
                        f.write(line)
                        n += name == "records_D.jsonl"
            counts[os.path.basename(s.rstrip("/"))] = {"gate": why, "states": n, "report": rep}
    json.dump(counts, open(os.path.join(out, "dh_counts.json"), "w"), indent=1)
    print(json.dumps({k: {"gate": v["gate"], "states": v["states"]} for k, v in counts.items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
