"""G split (user-log 166): a general, outside-L8 evaluation bundle frozen BEFORE any training on converted public data.
  * AgiBot / BEHAVIOR / MolmoBot: ~10 % of groups by hash -- group = task (AgiBot), episode (BEHAVIOR, one scene per
    episode), house scene (MolmoBot RBY1 / Franka). Rule: sha256("g166|<family>|<group>") % 100 < 10.
  * RB2 real: the T4 held-out episodes (src_rb2 split: seed-0 permutation, first 20 %) are in G as well, plus the same
    hash rule on episodes.
  * public pointing benchmarks (licence checked): Where2Place (wentao-yuan/where2place, Apache-2.0, not gated),
    RefSpatial-Bench (BAAI/RefSpatial-Bench, Apache-2.0, not gated) -- evaluation only, never trained on.
Format of G rows: object name + point (pointlab rows); scoring = pixel error and 'point inside the object mask'.
guard(rows) raises if any row belongs to G -- every training build must call it (packs, prep_h2h, dist8 mixes).
usage: python -m xemb.gsplit check TRAIN_JSONL [...]     (exit 1 when a G row is found)"""
from __future__ import annotations

import hashlib
import json
import re
import sys

PCT = 10
BENCHMARKS = {"where2place": {"repo": "wentao-yuan/where2place", "license": "Apache-2.0", "gated": False},
              "refspatial_bench": {"repo": "BAAI/RefSpatial-Bench", "license": "Apache-2.0", "gated": False}}
# RB2 T4 held-out episodes are recomputed from the src_rb2 rule (seed-0 permutation of the converted episodes)
RB2_TEST_FILE = "/data/harvest/out/xemb_proto/points/rb2_test_episodes.json"

_RULES = [
    ("molmobot", re.compile(r"house_(\d+)")),
    ("behavior", re.compile(r"b1k(?:dh)?_(\d{8})")),
    ("agibot", re.compile(r"agb_t(\d+)_")),
    ("rb2", re.compile(r"rb2_(\d+)_")),
]
_rb2_test = None


def group_of(row: dict):
    """(family, group) of a row by its id / source, or None when the row is not in a G family."""
    rid, src = str(row.get("id", "")), str(row.get("source", ""))
    for fam, rx in _RULES:
        if fam == "rb2" and "rb2" not in src and not rid.startswith("rb2"):
            continue
        if fam == "molmobot" and "molmobot" not in src and "mb_" not in rid and "mf_" not in rid:
            continue
        m = rx.search(rid)
        if m:
            return fam, m.group(1)
    return None


def in_g(row: dict) -> bool:
    global _rb2_test
    g = group_of(row)
    if g is None:
        return False
    fam, grp = g
    if fam == "rb2":
        if _rb2_test is None:
            try:
                _rb2_test = set(json.load(open(RB2_TEST_FILE)))
            except OSError:
                _rb2_test = set()
        if int(grp) in _rb2_test:
            return True
    h = int(hashlib.sha256(f"g166|{fam}|{grp}".encode()).hexdigest()[:8], 16)
    return h % 100 < PCT


def guard(rows, where: str = "") -> None:
    bad = [r.get("id") for r in rows if in_g(r)]
    if bad:
        raise RuntimeError(f"G-split rows in a training build {where}: {len(bad)} (e.g. {bad[:3]})")


def split(rows):
    tr, g = [], []
    for r in rows:
        (g if in_g(r) else tr).append(r)
    return tr, g


if __name__ == "__main__" and sys.argv[1] == "check":
    n = 0
    for p in sys.argv[2:]:
        rows = [json.loads(x) for x in open(p, encoding="utf-8")]
        bad = [r.get("id") for r in rows if in_g(r)]
        print(p, "rows", len(rows), "G rows", len(bad))
        n += len(bad)
    sys.exit(1 if n else 0)
