"""LimitEpisode wiring on the fake world: every head observation is corrupted, the truth still succeeds under light
changes, and with object depth holes the rescue path is used (logged) and the truth succeeds with rescue on."""
from harvest.astra_solo.pt_truth import PtTruth
from harvest.teach_strip8 import boost as B

from astra_solo.test_pt_episode import PadWorld


def run(**kw):
    w = PadWorld()
    m = PtTruth(w)
    ep = B.LimitEpisode(w, m, 3, "mug_tray", None, mem_points=True, fix_loop=True, stop_calls=16, **kw)
    m.ep = ep
    return ep.run()


def test_light_corruption_applied():
    r = run(corrupt=("light", "dim_warm"))
    assert r["limits"]["n_corrupted_obs"] >= r["n_calls"] and r["success"], r["end_reason"]


def test_hole_rescue_logged():
    on = run(corrupt=("hole", 0.6), rescue=True)
    assert on["limits"]["rescues"], "the rescue path must be used with 60 % holes"
    assert on["success"], (on["end_reason"], on["history"][-3:])
