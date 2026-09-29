"""E-CONF held-out view builder (docs/stage3/prereg_conf.md §3): never-trained R2_TRAIN episodes -> stage-B views."""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = _load("conf_build", ("tools", "conf", "conf_build.py"))


def _w(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for x in lines:
            f.write(json.dumps(x) + "\n")


def _tree(root):
    for v in ("standard", "dr"):
        fo = os.path.join(root, v, "bottle_tray", "P0")
        os.makedirs(os.path.join(fo, "img"), exist_ok=True)
        for s in (10000, 10001, 10002):
            valid = (s == 10000) or (v == "dr" and s == 10002)
            json.dump({"seed": s, "split": "eval" if s % 20 == 0 else "fit", "valid_for_training": valid},
                      open(os.path.join(fo, f"ep{s}.meta.json"), "w"))
            ks = list(range(0, 31))  # frames 0..30, K = 30 (no row at k = 30)
            _w(os.path.join(fo, f"ep{s}.jsonl"), [{"seed": s, "kind": "P0", "k": k, "decision": k % 10 == 0} for k in ks])
            _w(os.path.join(fo, "rows", f"ep{s}.stageb.jsonl"),
               [{"seed": s, "kind": "P0", "k": k, "decision": k % 10 == 0} for k in ks[:-1]])
            _w(os.path.join(fo, "rows", f"ep{s}.labels_v2.jsonl"),
               [{"seed": s, "kind": "P0", "k": k} for k in ks if k % 10 == 0])


def _link(src, dst):
    open(dst, "w").write(src)


def test_build_keeps_only_never_trained_episodes(tmp_path):
    src, dst = str(tmp_path / "src"), str(tmp_path / "dst")
    _tree(src)
    info = B.build(src, dst, cap=10, seed=0, link=_link)
    assert info["selected"] == [["dr", "bottle_tray", "P0", 10001], ["standard", "bottle_tray", "P0", 10001],
                                ["standard", "bottle_tray", "P0", 10002]]
    assert info["mismatch"] == 0
    V = os.path.join(dst, "view", "standard", "bottle_tray", "P0")
    assert sorted(os.listdir(V)) == ["ep10001.jsonl", "ep10002.jsonl", "img"]
    lines = [json.loads(x) for x in open(os.path.join(V, "ep10001.jsonl"))]
    assert [x["k"] for x in lines] == [0, 10, 20, 30]
    rows = [json.loads(x) for x in open(V + ".stageb.jsonl")]
    assert sorted({(r["seed"], r["k"]) for r in rows}) == [(10001, 0), (10001, 10), (10001, 20),
                                                           (10002, 0), (10002, 10), (10002, 20)]
    labs = [json.loads(x) for x in open(V + ".labels_v2.jsonl")]
    assert len(labs) == 8
    assert open(os.path.join(V, "img")).read() == os.path.join(src, "standard", "bottle_tray", "P0", "img")


def test_build_layout_unseen_flags(tmp_path):
    src, dst = str(tmp_path / "src"), str(tmp_path / "dst")
    _tree(src)
    info = B.build(src, dst, cap=10, seed=0, link=_link)
    # seed 10001 is invalid in both variants -> unseen layout; standard 10002 has a valid dr twin -> seen
    assert info["layout_unseen"] == [["dr", "bottle_tray", "P0", 10001], ["standard", "bottle_tray", "P0", 10001]]
    assert json.load(open(os.path.join(dst, "heldout.json")))["n_episodes"] == 3
