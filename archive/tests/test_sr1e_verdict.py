"""E-SR1e verdict (docs/stage3/prereg_sr1e.md §4): per-arm E-SR1d rule + the arm choice of tools/sr1e/sr1e_verdict.py,
and the E-SR1e gate / generator hooks, on synthetic inputs."""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, *rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


T = _load("t_sr1d_verdict", "tests", "test_sr1d_verdict.py")
E = _load("sr1e_verdict", "tools", "sr1e", "sr1e_verdict.py")


def recs(follow, near_mse=0.02, n_far=6):
    far = [T.snap(i, "far", follow) for i in range(n_far)]
    return far + [T.snap(n_far + i, "near", False, near_mse, True) for i in range(4)]


def run(tmp, arms):
    c0 = [T.write(tmp, f"c0_{s}.jsonl", recs(False)) for s in (1, 2)]
    argv = ["--c0", *c0]
    for name, kw in arms:
        argv += ["--arm", name, *[T.write(tmp, f"{name}_{s}.jsonl", recs(**kw)) for s in (1, 2)]]
    out = os.path.join(tmp, "v.json")
    E.main(argv + ["--n", "10", "--boot", "50", "--out", out])
    return json.load(open(out))


def test_single_arm_follow_adopted(tmp_path):
    r = run(str(tmp_path), [("A", {"follow": True})])
    assert r["overall"]["verdict"] == "ADOPT_A" and r["per_arm"]["A"]["rule"]["grade"] == "FULL"


def test_no_arm_reaches(tmp_path):
    r = run(str(tmp_path), [("A", {"follow": False}), ("D", {"follow": False})])
    assert r["overall"]["verdict"] == "NOT_REACHED"


def test_near_bleed_only_is_none_adopted(tmp_path):
    r = run(str(tmp_path), [("A", {"follow": False}), ("D", {"follow": True, "near_mse": 0.03})])
    assert r["overall"]["verdict"] == "NONE_ADOPTED" and r["per_arm"]["D"]["rule"]["verdict"] == "NEAR_BLEED"


def test_simplest_adopt_kept_without_gain(tmp_path):
    r = run(str(tmp_path), [("A", {"follow": True}), ("D", {"follow": True})])
    assert r["overall"]["verdict"] == "ADOPT_A"


def test_complex_arm_only_adopted(tmp_path):
    r = run(str(tmp_path), [("A", {"follow": False}), ("D", {"follow": True})])
    assert r["overall"]["verdict"] == "ADOPT_D"


def test_cdg_smallest_passing_w(tmp_path):
    t = str(tmp_path)
    c0 = [T.write(t, f"c0_{s}.jsonl", recs(False)) for s in (1, 2)]
    base = [T.write(t, f"w1_{s}.jsonl", recs(False)) for s in (1, 2)]
    w15 = [T.write(t, f"w15_{s}.jsonl", recs(False)) for s in (1, 2)]
    w2 = [T.write(t, f"w2_{s}.jsonl", recs(True)) for s in (1, 2)]
    w3 = [T.write(t, f"w3_{s}.jsonl", recs(True), lat=80.0) for s in (1, 2)]
    out = os.path.join(t, "cdg.json")
    E.main(["--c0", *c0, "--cdg-base", *base, "--cdg", "1.5", *w15, "--cdg", "2", *w2, "--cdg", "3", *w3,
            "--n", "10", "--out", out])
    r = json.load(open(out))
    assert r["verdict"] == "CDG_ADOPT_w2"
    assert r["w"]["3"]["fails"] == ["iv_cdg"] and r["w"]["2"]["g2_pred_max_diff_m"] == 0.0


def test_gen_hooks_k_and_strata():
    X = _load("gen_branches_e", "tools", "sr1e", "gen_branches_e.py")
    G = X.patch(X.load_gen(), 7, ("far", "band"), "salt-x")
    assert G.K == 7 and G.SALT == "salt-x"
    assert G.eligible({"split": "train", "stratum": "band"}, "far")
    assert not G.eligible({"split": "val", "stratum": "far"}, "far")
    assert not G.eligible({"split": "train", "stratum": "near"}, "far")


def test_cfg_allows_steps_only(tmp_path):
    Gt = _load("sr1e_gate", "tools", "sr1e", "sr1e_gate.py")
    base = {"seed": 1, "batch": 8, "max_steps": 2000, "run": "m", "lr": 1e-4}
    ref = tmp_path / "ref.jsonl"
    ref.write_text(json.dumps({"event": "config", "args": base}) + "\n")
    ok = tmp_path / "ok.jsonl"
    ok.write_text(json.dumps({"event": "config", "args": {**base, "max_steps": 6000, "save_every": 2000, "run": "x",
                                                         "sr1d_frac": 0.75}}) + "\n")
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"event": "config", "args": {**base, "lr": 2e-4}}) + "\n")

    class A:
        pass
    a = A()
    a.log, a.ref = str(ok), str(ref)
    assert Gt.gate_cfg(a) == 0
    a.log = str(bad)
    assert Gt.gate_cfg(a) == 1
