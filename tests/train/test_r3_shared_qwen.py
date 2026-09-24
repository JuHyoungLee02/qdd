"""R3: shared-prefix batched training path == the per-question path == Jev-L inference, on the real Qwen3-VL
architecture (tiny random init, CPU, fp32) with the real processor / chat template. Pod only.

Checks: (1) the group encoder's token ids / pixel values equal the processor's per-prompt output; (2) stage-A
option log-probs of several snapshots x questions (head + wrist, §59 layout, and the legacy head-only prompt) from
ONE prefix pass per snapshot + one batched suffix pass equal the old per-item path (rel 1e-4), and so do the LoRA
gradients of the summed NLL; (3) the shared-path probabilities equal an emulation of jevl.JevLClient._body_mm
(one rendered request per trie node, continue_final_message, full-vocab logprobs -> jevl.option_probs);
(4) stage B: shared context hidden states + decision loss + total loss + gradients equal the old path.
"""
import math
import os
from collections import defaultdict

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
pytest.importorskip("peft")

MODEL = os.environ.get("STAGEA_BASE", "/data/harvest/models/Qwen3-VL-4B-Instruct")
if not os.path.exists(os.path.join(MODEL, "preprocessor_config.json")):
    pytest.skip("Qwen3-VL processor files not present (pod only)", allow_module_level=True)

from harvest.clients.jevl import SYSTEM, option_probs, question_text  # noqa: E402
from harvest.deccall_snap import build_snapshot_request  # noqa: E402
from harvest.train import prefix_share as P  # noqa: E402
from harvest.train.stagea_loss import item_logprobs, set_nll  # noqa: E402
from harvest.train.stageb_model import HFEncoder, item_images  # noqa: E402

REL = 1e-4


def _line(k, present=("o3", "o5", "o10")):
    return {"seed": 2000, "kind": "P0", "k": k, "ds_id": "ds3", "phase": "approach",
            "text_state": "t_state: f1\nrobot: gripper=open" + " x" * (3 * k), "state": {"present": list(present)},
            "oracle": defaultdict(lambda: None)}


def _img(path, w, h, seed):
    from PIL import Image
    Image.fromarray((np.random.default_rng(seed).random((h, w, 3)) * 255).astype("uint8")).save(path, quality=90)
    return str(path)


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    from peft import LoraConfig, get_peft_model
    from transformers import AutoProcessor

    from harvest.train.stagea_train import LORA_TARGET
    from .test_stagea_qwen import tiny_model
    d = tmp_path_factory.mktemp("r3")
    proc = AutoProcessor.from_pretrained(MODEL)
    m = get_peft_model(tiny_model(), LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, target_modules=LORA_TARGET))
    with torch.no_grad():
        for n, p in m.named_parameters():
            if "lora_B" in n:
                p.normal_(0, 0.3)
    m.eval()
    items = []
    for k in range(3):  # 3 snapshots, different state lengths and images
        head = _img(d / f"h{k}.jpg", 672, 376, k)
        wrist = _img(d / f"w{k}.jpg", 424, 240, 10 + k)
        req, _, _ = build_snapshot_request({**_line(k)})
        for j, (qid, q) in enumerate(req["questions"].items()):
            if j >= 3 + k:
                break
            items.append({"key": f"s{k}", "qid": qid, "text": question_text(req["state"], qid, q),
                          "names": list(q["criteria"]), "target": [list(q["criteria"])[0]],
                          "images": [["head camera:", head], ["right wrist camera (active arm):", wrist]],
                          "image": head})
    return m, HFEncoder(proc), proc, items


def _old(m, enc, it, images):
    tok, trie = enc.trie(it["names"])
    return item_logprobs(m, enc.inputs(it["text"], images, "cpu"), tok, trie, enc.end, enc.pad)


def _close(a, b):
    return math.isclose(float(a), float(b), rel_tol=REL, abs_tol=1e-6)


def test_group_ids_equal_processor(env):
    m, enc, proc, items = env
    its = [it for it in items if it["key"] == "s1"]
    g = P.encode_group(enc, [it["text"] for it in its], its[0]["images"])
    for it, ids in zip(its, g["rows"]):
        x = enc.inputs(it["text"], it["images"], "cpu")
        assert ids == x["input_ids"][0].tolist()
        assert torch.equal(g["pixel_values"], x["pixel_values"])
        assert torch.equal(g["image_grid_thw"], x["image_grid_thw"])
        if "mm_token_type_ids" in x:
            assert P.mm_types(ids, enc) == x["mm_token_type_ids"][0].tolist()


@pytest.mark.parametrize("layout", ["HW", "H"])
def test_shared_logprobs_equal_per_item_path(env, layout):
    m, enc, _, items = env
    its = [dict(it) for it in items]
    if layout == "H":
        for it in its:
            it.pop("images")
    with torch.no_grad():
        new = P.items_logprobs(m, enc, its, "cpu")
        for it, lp in zip(its, new):
            old = _old(m, enc, it, item_images(it))
            assert set(lp) == set(old)
            for n in old:
                assert _close(lp[n], old[n]), (layout, it["qid"], n, float(lp[n]), float(old[n]))
            # a snapshot with one question: its option rows share more than the prompt (e.g. plus_x / plus_y)
            (one,) = P.items_logprobs(m, enc, [it], "cpu")
            for n in old:
                assert _close(one[n], old[n]), ("single", layout, it["qid"], n)


def test_shared_grads_equal_per_item_path(env):
    m, enc, _, items = env
    ps = [p for p in m.parameters() if p.requires_grad]
    m.zero_grad(set_to_none=True)
    sum(set_nll(_old(m, enc, it, it["images"]), it["target"]) for it in items).backward()
    g_old = [p.grad.clone() for p in ps]
    m.zero_grad(set_to_none=True)
    lps = P.items_logprobs(m, enc, items, "cpu")
    sum(set_nll(lp, it["target"]) for lp, it in zip(lps, items)).backward()
    num = sum(float(((p.grad - g) ** 2).sum()) for p, g in zip(ps, g_old)) ** 0.5
    den = sum(float((g ** 2).sum()) for g in g_old) ** 0.5
    m.zero_grad(set_to_none=True)
    assert den > 0 and num / den < REL, (num, den)


def test_shared_grads_with_gradient_checkpointing(env):
    """The packed forward has no KV cache, so gradient checkpointing gives the same gradients."""
    m, enc, _, items = env
    ps = [p for p in m.parameters() if p.requires_grad]

    def grads():
        m.zero_grad(set_to_none=True)
        lps = P.items_logprobs(m, enc, items, "cpu")
        sum(set_nll(lp, it["target"]) for lp, it in zip(lps, items)).backward()
        return [p.grad.clone() for p in ps]
    g0 = grads()
    m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    m.train()
    try:
        g1 = grads()
    finally:
        m.gradient_checkpointing_disable()
        m.eval()
        m.zero_grad(set_to_none=True)
    num = sum(float(((a - b) ** 2).sum()) for a, b in zip(g0, g1)) ** 0.5
    den = sum(float((a ** 2).sum()) for a in g0) ** 0.5
    assert den > 0 and num / den < REL


def test_shared_probs_equal_jevl_mm_inference_emulation(env):
    """jevl.JevLClient._body_mm layout HW: system -> [label, image]* -> question text; one request per node."""
    from PIL import Image
    m, enc, proc, items = env
    with torch.no_grad():
        lps = P.items_logprobs(m, enc, items, "cpu")
        for it, lp in zip(items, lps):
            tok, trie = enc.trie(it["names"])
            user = []
            for label, _ in it["images"]:
                user += [{"type": "text", "text": label}, {"type": "image"}]
            user.append({"type": "text", "text": it["text"]})
            ims = [Image.open(p).convert("RGB") for _, p in it["images"]]
            node_lp = {}
            for pre, kids in trie.items():
                msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
                if pre:
                    msgs.append({"role": "assistant", "content": proc.tokenizer.decode(list(pre))})
                    s = proc.apply_chat_template(msgs, tokenize=False, continue_final_message=True)
                else:
                    s = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                x = proc(text=[s], images=ims, return_tensors="pt")
                full = torch.log_softmax(m(**x).logits[0, -1].float(), -1)
                node_lp[pre] = {c: float(full[c]) for c in kids}
            ref = option_probs(tok, trie, node_lp, enc.end)
            for n in tok:
                assert math.isclose(math.exp(float(lp[n])), ref[n], rel_tol=REL, abs_tol=1e-6), (it["qid"], n)


# ------------------------------------------------------------------------------------------ stage B
@pytest.fixture(scope="module")
def sb(tmp_path_factory):
    from harvest.train import stageb_data as D
    from harvest.train import stageb_model as M
    from harvest.train import stageb_train as T
    d = tmp_path_factory.mktemp("r3b")
    ss = D.synthetic_rows(4, seed=1, img_dir=str(d / "img"))
    bb, proc, hd = T.load_backbone("tiny", MODEL, torch.device("cpu"), lora={"r": 4, "alpha": 8, "dropout": 0.0})
    with torch.no_grad():
        for n, p in bb.named_parameters():
            if "lora_B" in n:
                p.normal_(0, 0.3)
    m = M.new_model(bb, ss, hd, expert_kw={"width": 32, "depth": 2, "heads": 4},
                    aux_kw={"width": 32, "heads": 4, "queries": 2}).eval()
    return m, M.HFEncoder(proc), ss


def test_stageb_shared_context_and_losses_equal_old(sb):
    m, enc, ss = sb
    batch = ss[:3]
    assert all(s["items"] for s in batch)
    g = torch.Generator().manual_seed(0)
    t = torch.rand(len(batch), generator=g)
    a, _, _ = m.targets(batch, "cpu")
    noise = torch.randn(a.shape, generator=g)
    with torch.no_grad():
        m.shared = False
        c0, k0 = m.contexts(batch, enc, "cpu", grad=False)
        m.shared = True
        c1, k1, _ = m.forward_shared(batch, enc, "cpu", grad=False)
    assert torch.equal(k0, k1)
    assert float((c0 - c1).abs().max()) <= REL * float(c0.abs().max())
    res = {}
    ps = [p for p in m.parameters() if p.requires_grad]
    for shared in (False, True):
        m.shared = shared
        m.zero_grad(set_to_none=True)
        tot, logs = m.losses(batch, enc, "cpu", fm_t=t, fm_noise=noise)
        tot.backward()
        res[shared] = (logs, [None if p.grad is None else p.grad.clone() for p in ps])
    m.zero_grad(set_to_none=True)
    (l0, g0), (l1, g1) = res[False], res[True]
    for k in ("fm", "aux", "dec", "total"):
        assert _close(l0[k], l1[k]), (k, l0[k], l1[k])
    num = sum(float(((x - y) ** 2).sum()) for x, y in zip(g0, g1) if x is not None)
    den = sum(float((x ** 2).sum()) for x in g0 if x is not None)
    assert den > 0 and (num / den) ** 0.5 < REL
