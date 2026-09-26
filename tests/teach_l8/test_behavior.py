"""Behavior policy of the collection (DART-style state mix): with p = 0 it executes the truth label; each perturbation
kind gives a valid runtime command of the registered shape; carry perturbations never drop the object from height."""
import json

import numpy as np

from harvest.astra_solo import schema as SC
from harvest.teach_l8 import behavior as B
from teach_l8.test_labels import GZ, INFO, MUG, TZ, W_OPEN, st
from harvest.teach_l8 import labels as L


def _valid(cmd):
    parsed, err = SC.validate(json.dumps({"assessment": {"task_progress": {"verified_completed": [],
                                                                           "currently_attempting": "x",
                                                                           "remaining": []},
                                                         "execution_status": "progressing", "evidence": "",
                                                         "evidence_view": "both", "confidence": "high"},
                                          "command": cmd}))
    assert not err, err
    return parsed["command"]


def ctx(s):
    step, cmd = L.plan(s, INFO, TZ, W_OPEN)
    return B.Ctx(state=s, info=INFO, table_z=TZ, step=step, label_cmd=cmd)


def test_zero_rate_is_clean():
    rng = np.random.default_rng(0)
    c = ctx(st([0.34, -0.25, TZ + 0.25]))
    for _ in range(20):
        cmd, kind = B.choose(rng, c, p=0.0)
        assert kind == "clean" and cmd == c.label_cmd


def test_every_approach_kind_is_valid_and_shaped():
    rng = np.random.default_rng(1)
    c = ctx(st([0.42, -0.20, GZ + 0.10]))
    for kind in B.APPROACH_KINDS:
        for _ in range(30):
            cmd = _valid(B.perturb(rng, kind, c))
            if kind == "wrong_offset":
                d = np.linalg.norm(np.asarray(cmd["position_m"][:2]) - MUG[:2])
                assert 0.069 <= d <= 0.101
            if kind == "empty_close":
                d = np.linalg.norm(np.asarray(cmd["position_m"][:2]) - MUG[:2])
                assert cmd["gripper"] == "close" and 0.019 <= d <= 0.051
            if kind == "clip":
                p = cmd["position_m"]
                assert not (0.25 <= p[0] <= 0.65 and -0.50 <= p[1] <= 0.10)
            if kind == "early_close":
                assert cmd == {"mode": "gripper", "gripper": "close"}


def test_carry_kinds_keep_the_object():
    rng = np.random.default_rng(2)
    c = ctx(st([0.42, -0.20, TZ + 0.22], grip=0.05, hold=True))
    for kind in B.CARRY_KINDS:
        if kind == "slip":
            continue
        for _ in range(30):
            cmd = _valid(B.perturb(rng, kind, c))
            assert cmd["gripper"] == "keep" and cmd["position_m"][2] >= TZ + 0.15


def test_slip_only_when_low():
    high = ctx(st([0.42, -0.20, TZ + 0.22], grip=0.05, hold=True))
    low = ctx(st([0.42, -0.20, GZ + 0.005], grip=0.05, hold=True))
    assert "slip" not in B.allowed(high) and "slip" in B.allowed(low)
    assert B.perturb(np.random.default_rng(0), "slip", low) == {"mode": "gripper", "gripper": "open"}


def test_no_perturbation_on_done_or_reopen():
    assert B.allowed(ctx(st([0.44, -0.38, TZ + 0.2], on=True))) == ()
    assert B.allowed(ctx(st([0.46, -0.20, GZ], grip=0.03))) == ()


def test_wrong_object_uses_a_distractor_when_present():
    s = st([0.34, -0.25, TZ + 0.25])
    s["obj"]["o8"] = np.array([0.55, 0.0, TZ + 0.05])
    info = dict(INFO, present=["o3", "o5", "o8"])
    step, cmd = L.plan(s, info, TZ, W_OPEN)
    c = B.Ctx(state=s, info=info, table_z=TZ, step=step, label_cmd=cmd)
    got = [tuple(np.round(B.perturb(np.random.default_rng(k), "wrong_object", c)["position_m"][:2], 3))
           for k in range(20)]
    assert (0.55, 0.0) in got
