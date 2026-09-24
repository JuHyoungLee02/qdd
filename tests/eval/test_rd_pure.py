"""R6 rd: paired standard -> variant accuracy drop with episode-cluster CIs (generalizes stagea_gen_report)."""
import pytest

from harvest.eval import rd


def _items(acc_by_seed, q="dir_z", kind="P0", n_k=4):
    """{(kind, seed, k, q): {cluster, correct, key, y}}: seed s is right for the first acc_by_seed[s] snapshots."""
    out = {}
    for s, n_ok in acc_by_seed.items():
        for k in range(n_k):
            out[(kind, s, k, q)] = {"cluster": (kind, s), "correct": int(k < n_ok), "key": "down", "y": "down"}
    return out


def test_offline_rd_paired_by_item():
    std = _items({0: 4, 1: 4, 2: 4})
    rnd = _items({0: 2, 1: 2, 2: 2})
    r = rd.offline_rd({"standard": std, "random": rnd}, n_boot=200)
    assert r["A"]["standard"]["pooled"]["mean"] == 1.0 and r["A"]["random"]["pooled"]["mean"] == 0.5
    d = r["RD"]["random"]["pooled"]
    assert d["drop"]["mean"] == 0.5 and d["relative"] == pytest.approx(0.5) and d["n_paired"] == 12
    assert r["RD"]["random"]["per_question"]["dir_z"]["drop"]["mean"] == 0.5


def test_unpaired_items_are_reported_not_paired():
    std = _items({0: 4, 1: 4})
    rnd = _items({0: 2, 5: 0})
    r = rd.offline_rd({"standard": std, "random": rnd}, n_boot=100)
    assert r["RD"]["random"]["pooled"]["n_paired"] == 4
    assert r["RD"]["random"]["pooled"]["unpaired"]["n"] == [8, 8]


def test_majority_baseline_uses_each_variants_own_labels():
    std = {("P0", 0, k, "dir_z"): {"cluster": ("P0", 0), "correct": 1, "key": "down", "y": "down" if k else "up"}
           for k in range(4)}
    m = rd.majority(std)
    assert m["labels"]["dir_z"] == "down" and m["pooled"]["mean"] == 0.75


def test_diff_of_diffs_between_two_models():
    A = {"standard": _items({0: 4, 1: 4}), "random": _items({0: 2, 1: 2})}   # drop 0.5
    B = {"standard": _items({0: 4, 1: 4}), "random": _items({0: 4, 1: 4})}   # drop 0
    d = rd.drd(A, B, "random", n_boot=100)
    assert d["mean"] == 0.5 and d["n"] == 8


def test_expand_dirs_uses_kind_subfolders(tmp_path):
    (tmp_path / "v" / "P0").mkdir(parents=True)
    (tmp_path / "v" / "P0" / "ep0.jsonl").write_text("")
    (tmp_path / "v" / "P2").mkdir()
    (tmp_path / "v" / "P2" / "ep0.jsonl").write_text("")
    (tmp_path / "w").mkdir()
    (tmp_path / "w" / "ep2000.jsonl").write_text("")
    got = rd.expand_dirs(str(tmp_path / "v"))
    assert [p.replace("\\", "/").split("/")[-1] for p in got] == ["P0", "P2"]
    assert rd.expand_dirs(str(tmp_path / "w")) == [str(tmp_path / "w")]
