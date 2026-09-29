import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "stagea_gen_report", os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "stagea_gen_report.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def _it(correct, kind="P0", seed=0, y="a", key=None):
    return {"cluster": (kind, seed), "q": "dir_xy", "y": y, "key": key if key is not None else (y if correct else "b"),
            "correct": correct, "p": 0.9, "p_ne": 0.0, "error": None}


def test_paired_keys_only_common_snapshots():
    A = {("P0_s0_k1", "dir_xy"): _it(True), ("P0_s0_k2", "dir_xy"): _it(True)}
    B = {("P0_s0_k2", "dir_xy"): _it(False), ("P0_s0_k3", "dir_xy"): _it(False)}
    assert G.common(A, B) == [("P0_s0_k2", "dir_xy")]


def test_paired_diff_and_diff_of_diffs():
    ks = [(f"P0_s{s}_k1", "dir_xy") for s in range(4)]
    Sstd = {k: _it(True, seed=i) for i, k in enumerate(ks)}
    Svar = {k: _it(i % 2 == 0, seed=i) for i, k in enumerate(ks)}  # SFT drops on half
    Zstd = {k: _it(True, seed=i) for i, k in enumerate(ks)}
    Zvar = {k: _it(True, seed=i) for i, k in enumerate(ks)}  # zero-shot no drop
    rd = G.paired_diff(Sstd, Svar, ks)
    assert rd["mean"] == 0.5 and rd["n"] == 4
    dd = G.diff_of_diffs(Sstd, Svar, Zstd, Zvar, ks)
    assert dd["mean"] == 0.5


def test_majority_correct_uses_that_variants_labels():
    I = {("P0_s0_k1", "dir_xy"): _it(True, y="a"), ("P0_s1_k1", "dir_xy"): _it(True, seed=1, y="a"),
         ("P0_s2_k1", "dir_xy"): _it(False, seed=2, y="c")}
    maj = G.majority(I, list(I))
    assert maj == {"dir_xy": "a"}
    m = G.majority_items(I, maj)
    assert [m[k]["correct"] for k in sorted(I)] == [True, True, False]


def test_pair_meta_counts_phase_and_label_agreement():
    std = {"P0_s0_k1": {"phase": "approach", "labels": {"dir_xy": "a"}},
           "P0_s0_k2": {"phase": "lift", "labels": {"dir_xy": "a"}}}
    var = {"P0_s0_k1": {"phase": "approach", "labels": {"dir_xy": "b"}},
           "P0_s0_k2": {"phase": "carry", "labels": {"dir_xy": "a"}},
           "P0_s0_k9": {"phase": "carry", "labels": {"dir_xy": "a"}}}
    m = G.pair_meta(std, var, ("dir_xy",))
    assert m["n_std"] == 2 and m["n_var"] == 3 and m["n_paired"] == 2
    assert m["same_phase"] == 0.5 and m["same_label"] == {"dir_xy": 0.5}
