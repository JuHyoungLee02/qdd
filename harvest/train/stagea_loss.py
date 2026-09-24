"""Stage-A loss: NLL of the target option set under the option-set-renormalized probability (D26 §1.4).

The probability is the one Jev-L reads at inference (harvest/clients/jevl.py): option names are tokenized, put in
a trie (jevl.option_trie), and p(option) = product over its branching nodes of the softmax over that node's child
tokens (jevl.option_probs). Inference runs one pass per branching node on [prompt][prefix]; training gets the
same per-node logits from teacher-forced sequences [prompt][option ids] (causal LM: the logits after [prompt][pre]
do not depend on later tokens), choosing a few options whose paths cover every branching node (`cover`).
loss = -log sum_{o in target} p(o)  (a single target = plain renormalized NLL).
"""
from __future__ import annotations

try:
    import torch
except ImportError:  # the pure part (cover) is importable without torch
    torch = None


def cover(tok: dict, trie: dict) -> tuple[list[str], dict]:
    """Option names whose sequences reach every branching node, and node -> (sequence index, depth).
    Deepest nodes first; ties by option order, so the result is deterministic."""
    names: list[str] = []
    where: dict = {}
    for pre in sorted(trie, key=lambda p: (-len(p), p)):
        if pre in where:
            continue
        name = next(n for n, ids in tok.items() if tuple(ids[:len(pre)]) == pre and len(ids) >= len(pre))
        s = len(names)
        names.append(name)
        ids = tok[name]
        for d in range(len(ids) + 1):
            p = tuple(ids[:d])
            if p in trie and p not in where:
                where[p] = (s, d)
    return names, where


def option_logprobs(node_logits: dict, tok: dict, trie: dict, end: int) -> dict:
    """node_logits: prefix -> 1-D logits over the vocabulary at that node. {name: log p~(name)} (tensors)."""
    lse = {}
    for pre, kids in trie.items():
        v = node_logits[pre]
        idx = torch.tensor(sorted(kids), device=v.device)
        lse[pre] = torch.logsumexp(v.index_select(0, idx), 0)
    out = {}
    for name, ids in tok.items():
        terms = []
        for i in range(len(ids) + 1):
            pre = tuple(ids[:i])
            if pre in trie:
                nxt = ids[i] if i < len(ids) else end
                terms.append(node_logits[pre][nxt] - lse[pre])
        out[name] = torch.stack(terms).sum() if terms else torch.tensor(0.0)  # single option: p = 1
    return out


def batch_inputs(inputs: dict, suffixes: list, pad_id: int) -> tuple[dict, int]:
    """Repeat one processed prompt (batch 1) for every suffix and append the suffix ids (right-padded).
    Per-token tensors (input_ids, attention_mask, *token_type_ids) are extended (attention 1 on real suffix
    tokens, 0 on pads, other keys 0);
    everything else (pixel_values, image_grid_thw, ...) is repeated along dim 0. Returns (batch, logits_to_keep)."""
    ids = inputs["input_ids"]
    P, n = ids.shape[1], len(suffixes)
    m = max(len(s) for s in suffixes)
    out = {}
    for k, v in inputs.items():
        if k in ("input_ids", "attention_mask") or k.endswith("token_type_ids"):
            if v.shape != (1, P):
                raise ValueError(f"{k}: expected shape (1, {P}), got {tuple(v.shape)}")
            ext = torch.zeros(n, m, dtype=v.dtype, device=v.device)
            for j, s in enumerate(suffixes):
                if k == "input_ids":
                    ext[j, :len(s)] = torch.tensor(s, dtype=v.dtype)
                    ext[j, len(s):] = pad_id
                elif k == "attention_mask":
                    ext[j, :len(s)] = 1
            out[k] = torch.cat([v.expand(n, P), ext], 1)
        elif torch.is_tensor(v):
            out[k] = torch.cat([v] * n, 0)
        else:
            out[k] = v
    return out, m + 1


def item_logprobs(model, inputs: dict, tok: dict, trie: dict, end: int, pad_id: int) -> dict:
    """{option name: log p~} for one (prompt, question) item; inputs = processor output of the prompt (batch 1,
    generation prompt included). Logits are read in float32 (or the model dtype if wider)."""
    names, where = cover(tok, trie)
    batch, keep = batch_inputs(inputs, [tok[n] for n in names], pad_id)
    logits = model(**batch, logits_to_keep=keep).logits  # [n, keep, V]; index d <-> position P-1+d
    if logits.dtype in (torch.bfloat16, torch.float16):
        logits = logits.float()
    node_logits = {pre: logits[s, d] for pre, (s, d) in where.items()}
    return option_logprobs(node_logits, tok, trie, end)


def set_nll(logp: dict, target) -> "torch.Tensor":
    if not target:
        raise ValueError("empty target set")
    return -torch.logsumexp(torch.stack([logp[n] for n in target]), 0)
