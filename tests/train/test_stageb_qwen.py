"""Stage-B on the real Qwen3-VL architecture (tiny random init, CPU) + the real processor / chat template.

Pod only (transformers + peft + the Qwen3-VL-4B processor files; no weights loaded). Checks: the §59 multi-image
layout (label text -> native image, head then active wrist, then state/question; 252 + 104 image tokens), KI
(zero LoRA gradient from the flow-matching loss, non-zero from aux and decision losses), and a LoRA-adapter +
heads save/load round trip with identical predictions.
"""
import os

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
pytest.importorskip("peft")

MODEL = os.environ.get("STAGEA_BASE", "/data/harvest/models/Qwen3-VL-4B-Instruct")
if not os.path.exists(os.path.join(MODEL, "preprocessor_config.json")):
    pytest.skip("Qwen3-VL processor files not present (pod only)", allow_module_level=True)

from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_model as M  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402

EK = {"width": 32, "depth": 2, "heads": 4}
AK = {"width": 32, "heads": 4, "queries": 2}


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    d = tmp_path_factory.mktemp("sb")
    ss = D.synthetic_rows(6, seed=0, img_dir=str(d / "img"))
    bb, proc, hd = T.load_backbone("tiny", MODEL, torch.device("cpu"))
    T.backbone_trainable(bb)
    m = M.new_model(bb, ss, hd, expert_kw=EK, aux_kw=AK)
    return m, M.HFEncoder(proc), ss, proc, d


def test_multi_image_layout_matches_d27(setup):
    m, enc, ss, proc, _ = setup
    x = enc.inputs(ss[0]["context"]["text"], ss[0]["context"]["images"], "cpu")
    text = proc.tokenizer.decode(x["input_ids"][0])
    i_sys = text.index("fast typed decision selector")
    i_head = text.index("head camera:")
    i_wr = text.index("right wrist camera (active arm):")
    i_state = text.index("t_state:")
    assert i_sys < i_head < i_wr < i_state
    assert text.count("<|vision_start|>") == 2
    pad = proc.tokenizer.convert_tokens_to_ids("<|image_pad|>")
    ids = x["input_ids"][0].tolist()
    vs = [k for k, t in enumerate(ids) if t == proc.tokenizer.convert_tokens_to_ids("<|vision_start|>")]
    n_head = sum(1 for t in ids[vs[0]:vs[1]] if t == pad)
    n_wrist = sum(1 for t in ids[vs[1]:] if t == pad)
    assert (n_head, n_wrist) == (252, 104)  # native 672x376 / 424x240, no tiling (§59)
    assert x["image_grid_thw"].shape[0] == 2


def test_ki_on_real_architecture(setup):
    m, enc, ss, _, _ = setup
    r = T.ki_check(m, enc, ss[:2], torch.device("cpu"))
    assert r["backbone_grad_norm_from_fm"] == 0.0
    assert r["backbone_grad_norm_from_aux"] > 0 and r["backbone_grad_norm_from_dec"] > 0
    assert r["expert_grad_norm_from_fm"] > 0


def test_adapter_and_heads_round_trip(setup):
    m, enc, ss, _, d = setup
    with torch.no_grad():  # make the LoRA non-trivial so a lost adapter would show
        for n, p in m.backbone.named_parameters():
            if "lora_B" in n:
                p.normal_(0, 0.05)
    m.eval()
    noise = torch.randn(1, 15, 8)
    p1 = m.predict(ss[0], enc, torch.device("cpu"), noise=noise)
    m.backbone.save_pretrained(str(d / "ck" / "adapter"))
    m.save_heads(str(d / "ck"))
    bb2, _, _ = T.load_backbone("tiny", MODEL, torch.device("cpu"), adapter=str(d / "ck" / "adapter"))
    m2 = M.load_heads(str(d / "ck"), bb2).eval()
    p2 = m2.predict(ss[0], enc, torch.device("cpu"), noise=noise)
    assert np.allclose(p1, p2, atol=1e-5)
    # a fresh backbone WITHOUT the adapter gives a different context -> different chunk
    bb3, _, _ = T.load_backbone("tiny", MODEL, torch.device("cpu"))
    p3 = M.load_heads(str(d / "ck"), bb3).eval().predict(ss[0], enc, torch.device("cpu"), noise=noise)
    assert not np.allclose(p1, p3, atol=1e-5)
