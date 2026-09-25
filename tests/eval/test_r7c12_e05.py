"""R7 cycle 12 D1 / D2: E0.5 §2A.5 metrics -- FLIP_TH candidates at the pre-registered alpha 0.01 (q0.99; E :253,
:487; M4 :285, :287), same-time flip split by success vs perturbed trajectories (E :253, §2A.4), and the A0-relative
flip of every variant A1-A4 (canon §27 :243). Canon §77."""
from harvest.eval import e05

from .test_e05_pure import NAMES, Q, _synth


def _mixed():
    """P0 success episodes with a constant same-time triple and P1 episodes whose K=3 same-time answers disagree on
    dir_z at every step; A2 always answers another dir_z key than A0, A3 never."""
    e0, a0, t0 = _synth(n_ep=4, kind="P0")
    e1, a1, t1 = _synth(n_ep=4, kind="P1")
    for key, a in a1.items():
        a["same"] = [dict(a["vote"]), {**a["vote"], "dir_z": "up"}, dict(a["vote"])]
    for a in list(a0.values()) + list(a1.values()):
        v = {q: {"key": a["vote"][q], "name": NAMES[q][a["vote"][q]]} for q in Q}
        a2 = {**v, "dir_z": {"key": "up", "name": "up"}}
        a["var"] = {"A1": v, "A2": a2, "A3": v, "A4": v}
    return e0 + e1, {**a0, **a1}, {**t0, **t1}


def test_flip_th_candidates_include_the_prereg_alpha_001():
    eps, ans, truth = _mixed()
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=100)
    c = r["c_flip"]["flip_th_candidates"]
    assert "q0.99" in c and set(c["q0.99"]) == {"tv_distance", "one_flip"}
    assert set(c) == {"q0.99", "q0.999", "q0.95"}  # M4 §4.4 alpha range {0.001, 0.01, 0.05}; 0.1 is outside it
    assert r["c_flip"]["flip_th_initial"] == {"alpha": 0.01, "key": "q0.99", **c["q0.99"]}


def test_same_time_flip_reported_for_success_and_perturbed_trajectories_separately():
    eps, ans, truth = _mixed()
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=100)
    st = r["same_time_flip_by_trajectory"]
    assert st["success"]["mean"] == 0.0
    assert st["perturbed"]["mean"] == 0.5  # dir_z disagrees at every perturbed step, target never
    assert r["same_time_flip"]["mean"] == 0.25  # pooled value unchanged in meaning


def test_a0_relative_flip_for_every_variant():
    eps, ans, truth = _mixed()
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=100)
    L = r["layers"]["L3_6"]
    assert L["a2flip"]["mean"] == 0.5 and L["a3flip"]["mean"] == 0.0
    assert L["a1flip"]["mean"] == 0.0 and L["a4flip"]["mean"] == 0.0
    assert L["a1flip"] == L["subst"]  # A1 flip = the substitution flip
