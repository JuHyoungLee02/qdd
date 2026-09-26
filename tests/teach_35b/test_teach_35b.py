"""E-TEACH-35B readiness code: LoRA target choice on Qwen3.5-35B-A3B module names, DDP sharding of micro-batches,
the chat-template prefix rule with thinking off, and the shard-level LoRA merge (keeps the base shard layout, so the
copied index points at shards that exist — P123)."""
import json
import re

import pytest

from harvest.teach_35b import merge as MG
from harvest.teach_35b import train as T

L = "model.language_model.layers"


@pytest.mark.parametrize("name", [
    f"{L}.3.self_attn.q_proj", f"{L}.3.self_attn.k_proj", f"{L}.3.self_attn.v_proj", f"{L}.39.self_attn.o_proj",
    f"{L}.0.linear_attn.in_proj_qkv", f"{L}.0.linear_attn.in_proj_z", f"{L}.0.linear_attn.out_proj",
    f"{L}.0.mlp.shared_expert.gate_proj", f"{L}.0.mlp.shared_expert.up_proj", f"{L}.12.mlp.shared_expert.down_proj"])
def test_lora_targets_hit(name):
    assert re.fullmatch(T.LORA_TARGET, name)


@pytest.mark.parametrize("name", [
    f"{L}.0.linear_attn.in_proj_a", f"{L}.0.linear_attn.in_proj_b", f"{L}.0.linear_attn.conv1d",
    f"{L}.0.mlp.gate", f"{L}.0.mlp.shared_expert_gate", f"{L}.0.mlp.experts", f"{L}.3.self_attn.q_norm",
    "model.visual.blocks.0.attn.qkv", "model.visual.merger.linear_fc1", "lm_head",
    "mtp.layers.0.self_attn.q_proj"])
def test_lora_targets_miss(name):
    assert not re.fullmatch(T.LORA_TARGET, name)


def test_shard_equal_and_disjoint():
    mbs = [[i] for i in range(11)]
    parts = [T.shard(mbs, r, 4) for r in range(4)]
    assert all(len(p) == 2 for p in parts)  # 11 // 4 = 2 each, the 3 left over are dropped (steps stay in sync)
    flat = [x[0] for p in parts for x in p]
    assert len(set(flat)) == len(flat) == 8
    assert T.shard(mbs, 0, 1) == mbs


def test_prefix_rule_thinking_off():
    pre = "<|im_start|>user\nQ<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    assert T.check_prefix(pre + "{}<|im_end|>\n", pre, "x") is None
    with pytest.raises(ValueError):
        T.check_prefix("<|im_start|>assistant\n{}", pre, "x")


def test_adapter_key_to_base():
    k = "base_model.model.model.language_model.layers.3.self_attn.q_proj.lora_A.weight"
    assert MG.base_key(k) == ("model.language_model.layers.3.self_attn.q_proj.weight", "A")
    assert MG.base_key(k.replace("lora_A", "lora_B")) == ("model.language_model.layers.3.self_attn.q_proj.weight", "B")
    assert MG.base_key("base_model.model.foo.bias") is None


def test_merge_shards(tmp_path):
    torch = pytest.importorskip("torch")
    st = pytest.importorskip("safetensors.torch")
    base, ad, out = tmp_path / "base", tmp_path / "ad", tmp_path / "out"
    base.mkdir(), ad.mkdir()
    w = torch.randn(6, 4, dtype=torch.bfloat16)
    other = torch.randn(3, dtype=torch.bfloat16)
    st.save_file({"model.language_model.layers.0.self_attn.q_proj.weight": w}, str(base / "m-1.safetensors"))
    st.save_file({"model.visual.x": other}, str(base / "m-2.safetensors"))
    idx = {"metadata": {}, "weight_map": {"model.language_model.layers.0.self_attn.q_proj.weight": "m-1.safetensors",
                                          "model.visual.x": "m-2.safetensors"}}
    (base / "model.safetensors.index.json").write_text(json.dumps(idx))
    (base / "config.json").write_text("{}")
    A, B = torch.randn(2, 4), torch.randn(6, 2)
    pre = "base_model.model.model.language_model.layers.0.self_attn.q_proj"
    st.save_file({pre + ".lora_A.weight": A, pre + ".lora_B.weight": B}, str(ad / "adapter_model.safetensors"))
    (ad / "adapter_config.json").write_text(json.dumps({"r": 2, "lora_alpha": 4, "use_rslora": False,
                                                         "use_dora": False}))
    rep = MG.merge(str(base), str(ad), str(out))
    assert rep["merged"] == 1 and rep["shards_written"] == 1 and rep["shards_linked"] == 1
    got = st.load_file(str(out / "m-1.safetensors"))["model.language_model.layers.0.self_attn.q_proj.weight"]
    want = (w.float() + 2.0 * (B @ A)).to(torch.bfloat16)
    assert torch.equal(got, want)
    assert torch.equal(st.load_file(str(out / "m-2.safetensors"))["model.visual.x"], other)
    assert (out / "config.json").exists() and (out / "model.safetensors.index.json").exists()
    MG.check_index(str(out))  # every shard the index names exists
