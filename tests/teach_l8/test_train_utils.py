"""Pure parts of the SFT script: prompt masking, length-grouped micro-batches covering every row once, and the
message layout (control reads prompt.txt, aux carries its own question; answer only when training)."""
from harvest.teach_l8 import train as T


def test_mask_labels():
    assert T.mask_labels([5, 6, 7, 8], 2) == [-100, -100, 7, 8]


def test_micro_batches_cover_once_and_group_lengths():
    lengths = [100, 3000, 120, 2900, 110, 3100, 90, 2800]
    mbs = T.micro_batches(lengths, micro=2, window=8, seed=0)
    flat = sorted(i for mb in mbs for i in mb)
    assert flat == list(range(8))
    for mb in mbs:
        assert max(lengths[i] for i in mb) - min(lengths[i] for i in mb) < 500


def test_messages(tmp_path):
    p = tmp_path / "prompt.txt"
    p.write_text("REQ", encoding="utf-8")
    ctrl = {"kind": "control", "prompt_path": str(p), "images": ["a", "b"], "answer": "{}"}
    m = T.messages(ctrl, True)
    assert m[0]["content"][0]["text"] == "REQ" and m[1]["content"][0]["text"] == "{}"
    assert [c["type"] for c in m[0]["content"]] == ["text", "text", "image", "text", "image"]
    aux = {"kind": "aux", "prompt": "Q", "images": ["a"], "answer": '{"xy": [0, 0]}'}
    m2 = T.messages(aux, False)
    assert len(m2) == 1 and [c["type"] for c in m2[0]["content"]] == ["text", "text", "image"]
