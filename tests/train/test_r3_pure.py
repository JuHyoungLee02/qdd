"""R3 pure parts (no torch): shared-prefix helpers, snapshot-grouped batching, stage-A multi-image items (§59)."""
import json
import os

from harvest.train import prefix_share as P
from harvest.train import stagea_data as D

from .test_stagea_data import _line, _rows


def test_lcp_len():
    assert P.lcp_len([[1, 2, 3, 4], [1, 2, 5], [1, 2, 3]]) == 2
    assert P.lcp_len([[7, 8]]) == 2
    assert P.lcp_len([[1], [2]]) == 0


def test_shared_len_leaves_one_token_and_keeps_images():
    # rows share [1, 9, 9, 2]; the shortest row has 5 tokens -> at most 4 shared; image token 9 inside
    assert P.shared_len([[1, 9, 9, 2, 3, 4], [1, 9, 9, 2, 5]], image_ids={9}) == 4
    assert P.shared_len([[1, 9, 9, 2], [1, 9, 9, 2, 5]], image_ids={9}) == 3  # identical row: keep 1 token
    assert P.shared_len([[1, 9, 2, 7, 3], [1, 9, 2, 7, 4]], image_ids={9}, cap=2) == 2  # prompt [1,9,2]: logits at 2
    import pytest
    with pytest.raises(ValueError):
        P.shared_len([[1, 9, 2], [1, 3, 9]], image_ids={9})  # an image token outside the shared prefix


def test_pack_rows_is_a_token_trie_after_the_shared_prefix():
    rows = [[1, 2, 3, 4, 5], [1, 2, 3, 4, 6], [1, 2, 7]]
    ids, par, dep, where = P.pack_rows(rows, 2)
    assert ids == [1, 2, 3, 4, 5, 6, 7] and par == [-1, 0, 1, 2, 3, 3, 1] and dep == [0, 1, 2, 3, 4, 4, 2]
    assert where == [[0, 1, 2, 3, 4], [0, 1, 2, 3, 5], [0, 1, 6]]
    for r, w in zip(rows, where):  # every row is recovered exactly, each token's parent = previous position
        assert [ids[n] for n in w] == r and all(par[w[i]] == w[i - 1] for i in range(1, len(w)))


def test_expand_image_tokens():
    assert P.expand_image_tokens([5, 9, 6, 9, 7], 9, [3, 2]) == [5, 9, 9, 9, 6, 9, 9, 7]
    import pytest
    with pytest.raises(ValueError):
        P.expand_image_tokens([5, 9, 6], 9, [3, 2])


def test_group_items_by_snapshot_and_images_keeps_order():
    its = [{"key": "a", "images": [["h", "1"]], "q": 0}, {"key": "b", "images": [["h", "2"]], "q": 1},
           {"key": "a", "images": [["h", "1"]], "q": 2}, {"key": "a", "image": "x", "q": 3}]
    g = P.group_items(its)
    assert [[it["q"] for it in grp] for grp in g] == [[0, 2], [1], [3]]


def test_snapshot_order_is_a_permutation_grouped_by_snapshot():
    import random
    its = [{"key": f"s{i // 5}", "question": i % 5} for i in range(50)]
    order = P.snapshot_order(its, random.Random(0))
    assert sorted(order) == list(range(50))
    keys = [its[i]["key"] for i in order]
    runs = [k for i, k in enumerate(keys) if i == 0 or keys[i - 1] != k]
    assert len(runs) == 10  # each snapshot contiguous
    assert P.snapshot_order(its, random.Random(0)) == order


def _pool(tmp_path, wrist=True):
    ln = _line()
    if wrist:
        ln["images"]["cam_wrist_right"] = "img/ep2000/k021_cam_wrist_right.jpg"
    (tmp_path / "labels").mkdir()
    (tmp_path / "ep2000.jsonl").write_text(json.dumps(ln) + "\n")
    with open(tmp_path / "labels" / "ep2000.jsonl", "w") as f:
        for r in _rows():
            f.write(json.dumps(r) + "\n")
    (tmp_path / "labels" / "ep2000.jsonl.done").write_text("{}")


def test_load_pool_hw_cameras_follow_d27_layout(tmp_path):
    _pool(tmp_path)
    items = D.load_pool(str(tmp_path), "plan", state="S0", cameras="HW")
    assert items
    for it in items:
        assert it["images"] == [["head camera:", os.path.join(str(tmp_path), "img/ep2000/k021_cam_head.jpg")],
                                ["right wrist camera (active arm):",
                                 os.path.join(str(tmp_path), "img/ep2000/k021_cam_wrist_right.jpg")]]
    assert D.camera_of(items[0]) == "D27v1:head camera:|right wrist camera (active arm):"


def test_load_pool_h_cameras_is_the_legacy_single_image_prompt(tmp_path):
    _pool(tmp_path)
    items = D.load_pool(str(tmp_path), "plan", state="S0", cameras="H")
    assert all("images" not in it and it["image"].endswith("k021_cam_head.jpg") for it in items)
    assert D.camera_of(items[0]) == "H:cam_head"


def test_load_pool_hw_requires_the_wrist_image(tmp_path):
    import pytest
    _pool(tmp_path, wrist=False)
    with pytest.raises(KeyError):
        D.load_pool(str(tmp_path), "plan", state="S0", cameras="HW")
