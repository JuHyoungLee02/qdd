import numpy as np

from harvest.predicates import Gripper, Obj, PredicateState

I = np.array([1.0, 0, 0, 0])
G_OPEN = Gripper(width_m=0.10, effort=0.0, pos=np.array([0, 0, 0.5]))


def obj(i, x, y, z, h=0.05):
    return Obj(i, np.array([x, y, z]), I.copy(), np.array([h, h, h]))


def run(ps, o3, o5, contacts=frozenset(), grip=G_OPEN, support=None):
    return ps.update({"o3": o3, "o5": o5}, grip, set(contacts), support or {"o3": "table", "o5": "table"})


def test_near_hysteresis_holds_between_bands():
    ps = PredicateState()
    o5 = obj("o5", 0, 0, 0)
    assert run(ps, obj("o3", 0.070, 0, 0), o5)["near(o3,o5)"] is False
    assert run(ps, obj("o3", 0.055, 0, 0), o5)["near(o3,o5)"] is False  # in band, stays
    assert run(ps, obj("o3", 0.049, 0, 0), o5)["near(o3,o5)"] is True  # enters < 5 cm
    assert run(ps, obj("o3", 0.058, 0, 0), o5)["near(o3,o5)"] is True  # in band, stays
    assert run(ps, obj("o3", 0.061, 0, 0), o5)["near(o3,o5)"] is False  # exits > 6 cm


def test_on_requires_contact_and_support_above():
    ps = PredicateState()
    o5 = obj("o5", 0, 0, 0.02, h=0.02)
    o3 = obj("o3", 0, 0, 0.02 + 0.02 + 0.05)
    r = run(ps, o3, o5, contacts={frozenset({"o3", "o5"})}, support={"o3": "o5", "o5": "table"})
    assert r["on(o3,o5)"] is True
    r = run(ps, o3, o5, contacts=set(), support={"o3": "o5", "o5": "table"})
    assert r["on(o3,o5)"] is False


def test_upright_uses_tilt_max():
    ps = PredicateState()
    ang = np.deg2rad(40)
    tilted = Obj("o3", np.zeros(3), np.array([np.cos(ang / 2), np.sin(ang / 2), 0, 0]), np.full(3, 0.05))
    assert run(ps, tilted, obj("o5", 1, 1, 0))["upright(o3)"] is False
    assert run(ps, obj("o3", 0, 0, 0), obj("o5", 1, 1, 0))["upright(o3)"] is True


def test_holding_needs_closed_width_and_effort_and_contact():
    ps = PredicateState()
    g = Gripper(width_m=0.04, effort=5.0, pos=np.array([0, 0, 0.1]))
    r = run(ps, obj("o3", 0, 0, 0.1), obj("o5", 1, 1, 0), contacts={frozenset({"gripper", "o3"})}, grip=g)
    assert r["holding(o3)"] is True
    r = run(ps, obj("o3", 0, 0, 0.1), obj("o5", 1, 1, 0), contacts=set(), grip=g)
    assert r["holding(o3)"] is False


def test_unknown_propagates():
    ps = PredicateState()
    o3 = obj("o3", 0, 0, 0)
    o3.occluded = True
    assert run(ps, o3, obj("o5", 0.01, 0, 0))["near(o3,o5)"] is None
