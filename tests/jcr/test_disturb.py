from harvest.jcr import disturb as D


def test_reproducible():
    assert D.plan_episode(12345) == D.plan_episode(12345)


def test_at_least_half_normal_and_normal_has_no_events_or_swaps():
    plans = [D.plan_episode(s) for s in range(10000, 12000)]
    share = sum(p["normal"] for p in plans) / len(plans)
    assert 0.47 <= share <= 0.53
    assert all(not p["events"] and p["p_swap"] == 0 for p in plans if p["normal"])
    assert all(1 <= len(p["events"]) <= 2 for p in plans if not p["normal"])


def test_scale_shrinks_physical_sizes():
    a, b = D.plan_episode(10001, 1.0), D.plan_episode(10001, 0.5)
    for ea, eb in zip(a["events"], b["events"]):
        if ea["kind"] == "push":
            assert abs(eb["dxy"][0] - 0.5 * ea["dxy"][0]) < 1e-12
