"""M4 comparison conditions available in the runtime (M4 §5 table, minimal set C0-C6).

condition(name) -> (M4Params overrides, RuntimeConfig overrides). Same text state, skill, model, call rate (T_c)
everywhere; only the commit rule / feedback / overlap changes.
  C0  stop until the answer, then execute: one call in flight, the arm holds while it is out (baseline only)
  C1  single in flight + keep the last action (answers applied as they come = newest)
  C2  overlap + Slow Brain VLM Stream as pre-registered (E §4.12 D9, canon §20, M4 §5 C2; canon §74): T_c period,
      no in-flight cap (measured count reported), the newest valid answer by request time applied every tick (also
      when it arrives after its target step started), 5 s timeout -> default action; no agreement, no (b) feedback
  C3  overlap + (a) only: LA-2 / gamma + defer window, no (b) epoch invalidation
  C4  overlap + (b) only: newest answer + (b) categories / epoch invalidation
  C5  overlap + (a) + (b) (the M4 design; runtime default)
  C6  C5 with overlap off (one call in flight)
Not in the runtime (need their own code): C2' / C2'-S / C2-match (Slow Brain fusion; offline values in e05), C3' Beta
stop rule, C3'' option-order rotation, C5-A3 same-time batches, C-FIX, C5'.
"""
from __future__ import annotations

CONDITIONS = {
    "C0": ({"max_inflight": 1, "agree": "newest", "feedback_b": False}, {"stop_wait": True}),
    "C1": ({"max_inflight": 1, "agree": "newest", "feedback_b": False}, {}),
    "C2": ({"agree": "stream", "feedback_b": False, "stale_max": 5.0, "n_max_cap": False}, {}),
    "C3": ({"feedback_b": False}, {}),
    "C4": ({"agree": "newest"}, {}),
    "C5": ({}, {}),
    "C6": ({"max_inflight": 1}, {}),
}


def condition(name: str):
    if name not in CONDITIONS:
        raise ValueError(f"condition {name!r}: runtime has {sorted(CONDITIONS)} (see module doc for the others)")
    m4, rt = CONDITIONS[name]
    return dict(m4), dict(rt)
