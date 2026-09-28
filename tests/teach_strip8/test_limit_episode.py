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


def test_parse_and_resolver_v2_episode():
    from harvest.astra_solo import resolve as RS
    from harvest.teach_strip8.run_limits import parse
    assert parse("none") == (None, False, "v1") and parse("none:v2") == (None, False, "v2")
    assert parse("hole:0.3:r") == (("hole", 0.3), True, "v1") and parse("light:dim_warm") == (("light", "dim_warm"), False, "v1")
    rp0 = RS.resolve_point
    r = run(resolver="v2")
    assert RS.resolve_point is rp0  # restored after the episode
    assert r["limits"]["resolver"] == "v2"
    assert any((c.get("resolved") or {}).get("method", "").startswith("v2") for c in r["calls"])


def test_v2g_uses_v2_only_before_the_grasp():
    from harvest.teach_strip8.run_limits import parse
    assert parse("none:v2g") == (None, False, "v2g")
    r = run(resolver="v2g")
    m = [((c.get("resolved") or {}).get("method"), (c.get("resolved") or {}).get("holding")) for c in r["calls"]
         if (c.get("resolved") or {}).get("kind") == "object"]
    assert any(meth and meth.startswith("v2") and not h for meth, h in m)
    assert all(not (meth or "").startswith("v2") for meth, h in m if h)


def test_hole_rescue_logged():
    on = run(corrupt=("hole", 0.6), rescue=True)
    assert on["limits"]["rescues"], "the rescue path must be used with 60 % holes"
    assert on["success"], (on["end_reason"], on["history"][-3:])
