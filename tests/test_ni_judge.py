"""ni_judge (user-log 186): no-goal replies count as failures, A/A margins, a clearly worse arm fails, a copy passes."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "teach_pt"))
import ni_judge as NJ  # noqa: E402


def _arm(root, name, errs):
    for xs in NJ.XSETS:
        d = root / name / f"x_{xs}_d-min_clean"
        d.mkdir(parents=True)
        with open(d / "scores.jsonl", "w") as f:
            for i, e in enumerate(errs):
                f.write(json.dumps({"id": f"s{i}", "approach_row": True, "approach_3d_mm": e}) + "\n")
            f.write(json.dumps({"id": "carry", "approach_row": False, "approach_3d_mm": None}) + "\n")
    return str(root / name)


def test_stats_and_judge(tmp_path):
    NJ.N_BOOT = 500
    rng = np.random.default_rng(0)
    base = list(np.round(rng.gamma(2, 3, 300), 1))
    e0 = _arm(tmp_path, "a0", base)
    e1 = _arm(tmp_path, "a1", [x + (1 if i % 3 == 0 else 0) for i, x in enumerate(base)])
    assert NJ.stats([1, 2, float("inf")]) == (2.0, 1 / 3)
    m = NJ.aa(str(tmp_path / "m.json"), [e0, e1])
    assert m["sets"]["dev"]["median_margin_mm"] >= 0
    bad = _arm(tmp_path, "bad", [x + 30 if i % 2 else None for i, x in enumerate(base)])
    r = NJ.judge(str(tmp_path / "m.json"), str(tmp_path / "j.json"), [bad], [e0])
    assert not r["noninferior_all"] and len(r["worse_sets"]) == 7
    r = NJ.judge(str(tmp_path / "m.json"), str(tmp_path / "j2.json"), [e0], [e0])
    assert r["noninferior_all"]
