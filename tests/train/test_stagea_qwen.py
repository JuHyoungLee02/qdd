"""Stage-A pipeline on the real Qwen3-VL architecture (tiny random init, CPU) and the real processor/template.

Needs transformers + peft (venv_train) and the processor files of Qwen3-VL-4B-Instruct (no weights are loaded);
skipped elsewhere. Checks: (1) the chat template continues a branching-node prefix exactly as generation prompt +
prefix ids (what vLLM's continue_final_message request renders), for every real DecCall option set; (2) the
training log-probs through Scorer/item_logprobs equal an inference emulation that renders one prompt per trie node
(prefix text as assistant content, continue_final_message) and reads full-vocab logprobs of the children, fed to
jevl.option_probs; (3) tools/stagea_merge.py output reproduces base+adapter logits.
"""
import importlib.util
import math
import os

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
peft = pytest.importorskip("peft")

MODEL = os.environ.get("STAGEA_BASE", "/data/harvest/models/Qwen3-VL-4B-Instruct")
if not os.path.exists(os.path.join(MODEL, "preprocessor_config.json")):
    pytest.skip("Qwen3-VL processor files not present (pod only)", allow_module_level=True)

from harvest.clients.jevl import SYSTEM, option_probs, option_trie, question_text  # noqa: E402
from harvest.deccall_snap import build_snapshot_request  # noqa: E402
from harvest.train.stagea_loss import item_logprobs  # noqa: E402
from harvest.train.stagea_train import END_TOKEN, LORA_TARGET, Scorer  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _line(present=("o3", "o5", "o10")):
    return {"seed": 2000, "kind": "P0", "k": 3, "ds_id": "ds3", "phase": "approach", "text_state": "t_state: f1",
            "state": {"present": list(present)},
            "oracle": {"dir_xy": "plus_x", "dir_z": "down", "mag_coarse": "large", "target": "o3",
                       "phase_choice": "continue", "progress": "valid_progress"}}


@pytest.fixture(scope="module")
def proc():
    from transformers import AutoProcessor
    return AutoProcessor.from_pretrained(MODEL)


def tiny_model(seed=0, dtype=torch.float32):
    from transformers import AutoConfig, AutoModelForImageTextToText
    cfg = AutoConfig.from_pretrained(MODEL)
    t, v = cfg.text_config, cfg.vision_config
    t.hidden_size, t.num_hidden_layers, t.num_attention_heads, t.num_key_value_heads = 64, 2, 4, 2
    t.head_dim, t.intermediate_size = 16, 128
    rs = getattr(t, "rope_scaling", None) or getattr(t, "rope_parameters", None)
    if rs is not None:
        rs["mrope_section"] = [4, 2, 2]
    v.depth, v.hidden_size, v.num_heads, v.intermediate_size, v.out_hidden_size = 2, 32, 2, 64, 64
    v.deepstack_visual_indexes = [0]
    torch.manual_seed(seed)
    return AutoModelForImageTextToText.from_config(cfg, dtype=dtype).eval()


def _image(tmp_path):
    from PIL import Image
    import numpy as np
    p = tmp_path / "head.jpg"
    Image.fromarray((np.random.default_rng(0).random((376, 672, 3)) * 255).astype("uint8")).save(p, quality=90)
    return str(p)


def test_template_continuation_is_generation_prompt_plus_prefix_ids(proc):
    req, _, _ = build_snapshot_request(_line())
    tk = proc.tokenizer
    end = tk.encode(END_TOKEN, add_special_tokens=False)[0]
    for qid, q in req["questions"].items():
        base = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": [{"type": "image"}, {"type": "text",
                                                                 "text": question_text(req["state"], qid, q)}]}]
        gen = tk.encode(proc.apply_chat_template(base, tokenize=False, add_generation_prompt=True),
                        add_special_tokens=False)
        tok = {n: tk.encode(n, add_special_tokens=False) for n in q["criteria"]}
        for pre in option_trie(tok, end):
            if not pre:
                continue
            txt = proc.apply_chat_template(base + [{"role": "assistant", "content": tk.decode(list(pre))}],
                                           tokenize=False, continue_final_message=True)
            assert tk.encode(txt, add_special_tokens=False) == gen + list(pre), (qid, pre)


def test_tiny_qwen3vl_training_logprobs_equal_inference_emulation(proc, tmp_path):
    model = tiny_model()
    img = _image(tmp_path)
    sc = Scorer(proc, str(tmp_path))
    req, _, _ = build_snapshot_request(_line())
    from PIL import Image
    for qid, q in req["questions"].items():
        text = question_text(req["state"], qid, q)
        tok, trie = sc.trie(list(q["criteria"]))
        with torch.no_grad():
            lp = item_logprobs(model, sc.inputs(text, "head.jpg", "cpu"), tok, trie, sc.end, sc.pad)
            node_lp = {}
            for pre, kids in trie.items():  # jevl.py: one request per node, prefix as assistant text
                msgs = [{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": text}]}]
                if pre:
                    msgs.append({"role": "assistant", "content": proc.tokenizer.decode(list(pre))})
                    s = proc.apply_chat_template(msgs, tokenize=False, continue_final_message=True)
                else:
                    s = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                x = proc(text=[s], images=[Image.open(img).convert("RGB")], return_tensors="pt")
                full = torch.log_softmax(model(**x).logits[0, -1].float(), -1)
                node_lp[pre] = {c: float(full[c]) for c in kids}
        ref = option_probs(tok, trie, node_lp, sc.end)
        assert len(trie) >= 1
        for n in tok:
            assert math.isclose(math.exp(float(lp[n])), ref[n], rel_tol=1e-4, abs_tol=1e-6), (qid, n)


def test_lora_targets_only_llm_linear_layers():
    from peft import LoraConfig, get_peft_model
    m = get_peft_model(tiny_model(), LoraConfig(r=4, lora_alpha=8, target_modules=LORA_TARGET))
    wrapped = {n.rsplit(".lora_A", 1)[0] for n, _ in m.named_parameters() if ".lora_A" in n}
    assert wrapped and all("language_model.layers" in n for n in wrapped)
    kinds = {n.rsplit(".", 1)[-1] for n in wrapped}
    assert kinds == {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}
    assert len(wrapped) == 7 * 2
    assert not any(p.requires_grad for n, p in m.named_parameters() if "lora_" not in n)


def test_merge_tool_reproduces_adapter_logits(tmp_path):
    import shutil
    from peft import LoraConfig, get_peft_model
    base = tmp_path / "base"
    tiny_model().save_pretrained(base)
    for f in ("preprocessor_config.json", "tokenizer.json", "tokenizer_config.json", "chat_template.json"):
        if os.path.exists(os.path.join(MODEL, f)):
            shutil.copy2(os.path.join(MODEL, f), base / f)
    m = get_peft_model(tiny_model(), LoraConfig(r=4, lora_alpha=8, target_modules=LORA_TARGET))
    with torch.no_grad():
        for n, p in m.named_parameters():
            if "lora_B" in n:
                p.normal_(0, 0.5)  # non-zero adapter
    m.save_pretrained(tmp_path / "adapter")
    spec = importlib.util.spec_from_file_location("stagea_merge", os.path.join(ROOT, "tools", "stagea_merge.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    info = mod.merge(str(tmp_path / "adapter"), str(tmp_path / "merged"), base=str(base), dtype="float32",
                     check=True)
    assert info["check_argmax_equal"] and info["check_max_abs_logit_diff"] < 1e-4
    assert os.path.exists(tmp_path / "merged" / "chat_template.json") or not os.path.exists(
        os.path.join(MODEL, "chat_template.json"))
    ids = torch.randint(0, 1000, (1, 12))
    from transformers import AutoModelForImageTextToText
    with torch.no_grad():
        a = m(input_ids=ids).logits
        b = AutoModelForImageTextToText.from_pretrained(tmp_path / "merged", dtype=torch.float32)(input_ids=ids).logits
    assert float((a - b).abs().max()) < 1e-4


def test_train_cli_end_to_end_tiny_model(tmp_path, monkeypatch):
    """train (2 steps, CPU) -> best/last adapters + log -> load reproduces the logged val NLL of `best`."""
    import json
    import shutil

    from harvest.train import stagea_train as T

    from .test_stagea_data import _line, _rows
    base = tmp_path / "base"
    tiny_model().save_pretrained(base)
    for f in os.listdir(MODEL):
        if os.path.isfile(os.path.join(MODEL, f)) and not f.endswith(".safetensors") and f not in (
                "config.json", "model.safetensors.index.json"):
            shutil.copy2(os.path.join(MODEL, f), base / f)
    pool = tmp_path / "pool"
    (pool / "labels").mkdir(parents=True)
    for seed, split in ((2000, "fit"), (2007, "eval")):
        (pool / "img" / f"ep{seed}").mkdir(parents=True)
        _image(pool / "img" / f"ep{seed}")
        shutil.move(str(pool / "img" / f"ep{seed}" / "head.jpg"), str(pool / "img" / f"ep{seed}" / "k021_cam_head.jpg"))
        with open(pool / f"ep{seed}.jsonl", "w") as f:
            f.write(json.dumps(_line(seed=seed, split=split)) + "\n")
        with open(pool / "labels" / f"ep{seed}.jsonl", "w") as f:
            for r in _rows(seed=seed, split=split):
                f.write(json.dumps(r) + "\n")
        (pool / "labels" / f"ep{seed}.jsonl.done").write_text("{}")
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    T.main(["train", "--pool", str(pool), "--rule", "plan", "--run", "t", "--out-root", str(tmp_path / "ck"),
            "--model", str(base), "--state", "S0", "--target-source", "outcome", "--accum", "2", "--epochs", "1", "--eval-every", "1",
            "--lr", "1e-2"])
    run = tmp_path / "ck" / "t"
    log = [json.loads(x) for x in open(run / "log.jsonl")]
    cfg = json.load(open(run / "config.json"))
    assert cfg["n_train"] == 5 and cfg["n_val"] == 5 and cfg["total_steps"] == 3
    evals = [r for r in log if r["event"] == "eval"]
    assert [r["step"] for r in evals] == [0, 1, 2, 3] and log[-1]["event"] == "done"
    assert (run / "best" / "adapter_config.json").exists() and (run / "last" / "adapter_config.json").exists()
    best = min(r["nll"] for r in evals)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        T.main(["load", "--adapter", str(run / "best"), "--pool", str(pool), "--rule", "plan", "--model", str(base),
                "--state", "S0", "--target-source", "outcome"])
    got = json.loads(buf.getvalue().split("LOAD ", 1)[1])
    assert math.isclose(got["nll"], best, rel_tol=1e-5)
