from harvest.canary import canary_compare, plan_signature

PLAN = {"stages": [{"skill": "pick", "obj": "o3"}, {"skill": "place", "obj": "o3", "target": "o5"}],
        "decision_points": ["dp1"], "roles": {"o3": "target", "o5": "goal"}, "note": "x"}


def test_signature_ignores_wording_changes():
    assert plan_signature(PLAN) == plan_signature(dict(PLAN, note="different words"))


def test_signature_changes_with_roles_or_skills():
    assert plan_signature(PLAN) != plan_signature(dict(PLAN, roles={"o3": "target", "o5": "obstacle"}))
    swapped = dict(PLAN, stages=[{"skill": "push", "obj": "o3"}, PLAN["stages"][1]])
    assert plan_signature(PLAN) != plan_signature(swapped)


def test_drift_flag():
    base = {"q1": ["a"] * 10, "q2": ["b"] * 10}
    assert canary_compare(base, {"q1": ["a"] * 10, "q2": ["b"] * 10}, floor=0.05)["drift_suspect"] is False
    assert canary_compare(base, {"q1": ["c"] * 10, "q2": ["c"] * 10}, floor=0.05)["drift_suspect"] is True


def test_drift_not_flagged_within_floor():
    base = {"q1": ["a"] * 10}
    today = {"q1": ["a"] * 9 + ["b"]}
    assert canary_compare(base, today, floor=0.10)["drift_suspect"] is False
