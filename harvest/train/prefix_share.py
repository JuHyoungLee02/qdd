"""Shared-prefix batched forward for stage A / stage B training (R3 throughput, canon §59 layout).

Old path: every (snapshot, question) item is its own forward of [system][images][state][question][option ids]
(one row per trie-covering option, stagea_loss.item_logprobs), so a snapshot with 5 questions encodes its images
and its state 5 times (+1 for the stage-B context prompt).
Shared path, per micro-batch of snapshots ("groups"): ONE forward. Each group's rows (every question's option
rows, + the stage-B context prompt) are packed into one sequence as a token trie: the shared prefix (system +
images + state, the longest common token prefix; images must lie inside it) once, then every distinct
continuation once (a question's option rows share its tail; options share first tokens). A 4-D boolean
attention mask lets each token attend to its trie ancestors only = exactly the tokens before it in its own row
("tree attention", the prefix-sharing form of the KV-cache reuse), and its position ids are those of the full
row (mrope of the prefix from the model's get_rope_index, text positions = prefix end + depth). So each token's
hidden state equals the full-row forward's (tests/train/test_r3_*.py: rel 1e-4 fp32, gradients included), the
images and state are encoded once per snapshot, and groups are batched with right padding.
Logits are computed only at the positions the option tries need.
"""
from __future__ import annotations

import json
import os

try:
    import torch
except ImportError:  # pure helpers stay importable without torch
    torch = None


# ------------------------------------------------------------------------------------------ pure helpers
def lcp_len(seqs) -> int:
    n = min(len(s) for s in seqs)
    first = seqs[0]
    for i in range(n):
        if any(s[i] != first[i] for s in seqs[1:]):
            return i
    return n


def shared_len(rows, image_ids=frozenset(), cap=None) -> int:
    """Shared prefix length of one group: common prefix, but every row keeps >= 1 own token and at most `cap`
    (= shortest prompt - 1: the logits after the last prompt token must come from pass 2); every image token
    must lie inside it (images are encoded once, in pass 1)."""
    L = min(lcp_len(rows), min(len(r) for r in rows) - 1)
    if cap is not None:
        L = min(L, cap)
    for r in rows:
        if any(t in image_ids for t in r[L:]):
            raise ValueError("an image token lies outside the shared prefix (images must precede the row text)")
    return L


def expand_image_tokens(ids, image_id, counts) -> list:
    """Repeat the k-th image placeholder token counts[k] times (what the Qwen3-VL processor does in text)."""
    out, k = [], 0
    for t in ids:
        if t == image_id:
            if k >= len(counts):
                raise ValueError("more image tokens than images")
            out += [t] * counts[k]
            k += 1
        else:
            out.append(t)
    if k != len(counts):
        raise ValueError(f"{k} image tokens for {len(counts)} images")
    return out


def _images(it):
    return it.get("images") or ([it["image"]] if it.get("image") else [])


def group_items(items) -> list:
    """Items sharing snapshot key and images, in first-appearance order (each group = one shared prefix)."""
    groups: dict = {}
    for it in items:
        groups.setdefault((it["key"], json.dumps(_images(it))), []).append(it)
    return list(groups.values())


def snapshot_order(items, rng) -> list:
    """Item indices: snapshots shuffled, each snapshot's items contiguous (so a step's items share prefixes)."""
    by: dict = {}
    for i, it in enumerate(items):
        by.setdefault(it["key"], []).append(i)
    keys = list(by)
    rng.shuffle(keys)
    return [i for k in keys for i in by[k]]


# ------------------------------------------------------------------------------------------ encoding
def _render(enc, text, images):
    content = []
    for im in images or []:
        label, _ = im if isinstance(im, (list, tuple)) else (None, im)
        if label:
            content.append({"type": "text", "text": label})
        content.append({"type": "image"})
    content.append({"type": "text", "text": text})
    msgs = [{"role": "system", "content": enc.system}, {"role": "user", "content": content}]
    return enc.p.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def _image_id(enc):
    return enc.p.tokenizer.convert_tokens_to_ids("<|image_pad|>")


def mm_types(ids, enc) -> list:
    img, vid = _image_id(enc), enc.p.tokenizer.convert_tokens_to_ids("<|video_pad|>")
    return [1 if t == img else 2 if t == vid else 0 for t in ids]


def encode_group(enc, texts, images) -> dict:
    """Prompt token ids of several texts that share one image list, with the images processed once.
    Equal to the processor's per-prompt output (test_group_ids_equal_processor)."""
    from PIL import Image
    paths = [im[1] if isinstance(im, (list, tuple)) else im for im in images or []]
    out = {"pixel_values": None, "image_grid_thw": None}
    counts = []
    if paths:
        ims = [Image.open(os.path.join(enc.root, p)).convert("RGB") for p in paths]
        x = enc.p.image_processor(images=ims, return_tensors="pt")
        out["pixel_values"], out["image_grid_thw"] = x["pixel_values"], x["image_grid_thw"]
        merge = enc.p.image_processor.merge_size
        counts = [int(g.prod()) // merge ** 2 for g in x["image_grid_thw"]]
    img = _image_id(enc)
    out["rows"] = [expand_image_tokens(enc.p.tokenizer(_render(enc, t, images))["input_ids"], img, counts)
                   for t in texts]
    return out


# ------------------------------------------------------------------------------------------ forward
def _parts(model):
    m = model.get_base_model() if hasattr(model, "get_base_model") else model
    return m.model, m.lm_head


def pack_rows(rows, L):
    """Token trie of one group's rows: the first L tokens (shared by every row) form a chain, the rest is merged
    wherever rows share a prefix (question tails of the same question, option first tokens). Returns (node token
    ids, parent index per node, depth per node, per row the node index of each of its positions)."""
    ids, parent, depth = list(rows[0][:L]), list(range(-1, L - 1)), list(range(L))
    child: dict = {}
    where = []
    for r in rows:
        if list(r[:L]) != ids[:L]:
            raise ValueError("row does not start with the shared prefix")
        path, cur = list(range(L)), L - 1
        for t in r[L:]:
            key = (cur, t)
            if key not in child:
                child[key] = len(ids)
                ids.append(t)
                parent.append(cur)
                depth.append(depth[cur] + 1 if cur >= 0 else 0)
            cur = child[key]
            path.append(cur)
        where.append(path)
    return ids, parent, depth, where


def shared_forward(model, groups, device, logits_at: dict, hidden_of=(), layer=-1, pad_id=0, enc=None):
    """groups: [{"rows": [ids...], "pixel_values", "image_grid_thw"}]; logits_at: {(g, j): [positions]} (absolute
    positions of row j of group g); hidden_of: [(g, j)] rows whose hidden states (layer `layer`, every position)
    are returned. Returns ({(g, j): logits [n_pos, V] float32}, {(g, j): hidden [len, D]}).
    ONE forward: each group's rows packed as a token trie (tree attention: a token attends to its ancestors =
    exactly the tokens before it in its own row), batched over groups; mrope positions of the shared prefix from
    the model's get_rope_index, text positions after it = prefix end + depth."""
    inner, head = _parts(model)
    img_ids = {_image_id(enc)} if enc is not None else set()
    G = len(groups)
    Ls = [shared_len(gr["rows"], img_ids, gr.get("cap")) for gr in groups]
    packs = [pack_rows(gr["rows"], L) for gr, L in zip(groups, Ls)]
    Lmax, T = max(Ls), max(len(p[0]) for p in packs)
    ids1 = torch.full((G, Lmax), pad_id, dtype=torch.long)
    m1 = torch.zeros(G, Lmax, dtype=torch.long)
    for g, gr in enumerate(groups):
        ids1[g, :Ls[g]] = torch.tensor(gr["rows"][0][:Ls[g]])
        m1[g, :Ls[g]] = 1
    types = torch.tensor([mm_types(r, enc) for r in ids1.tolist()]) if enc is not None else torch.zeros_like(ids1)
    thw = [gr["image_grid_thw"] for gr in groups if gr.get("image_grid_thw") is not None]
    thw = torch.cat(thw).to(device) if thw else None
    pos1, _ = inner.get_rope_index(input_ids=ids1.to(device), mm_token_type_ids=types.to(device),
                                   image_grid_thw=thw, attention_mask=m1.to(device))
    ids = torch.full((G, T), pad_id, dtype=torch.long)
    mask = torch.zeros(G, 1, T, T, dtype=torch.bool)
    pos = torch.zeros(3, G, T, dtype=torch.long)
    idx = torch.arange(T)
    mask[:, 0, idx, idx] = True  # padding nodes see themselves only (no fully masked row)
    for g, (nid, par, dep, _) in enumerate(packs):
        n, L = len(nid), Ls[g]
        ids[g, :n] = torch.tensor(nid)
        M = mask[g, 0]
        for i in range(n):
            if par[i] >= 0:
                M[i] = M[par[i]]
            M[i, i] = True
        pos[:, g, :L] = pos1[:, g, :L].cpu()
        nxt = int(pos1[:, g, :L].max()) + 1 if L else 0
        pos[:, g, L:n] = nxt + torch.tensor(dep[L:]) - L
    pv = [gr["pixel_values"] for gr in groups if gr.get("pixel_values") is not None]
    kw = {"pixel_values": torch.cat(pv).to(device, dtype=next(inner.visual.parameters()).dtype),
          "image_grid_thw": thw} if pv else {}
    o = inner(input_ids=ids.to(device), attention_mask=mask.to(device), position_ids=pos.to(device),
              use_cache=False, output_hidden_states=bool(hidden_of), **kw)
    out_l, out_h = {}, {}
    sel_g, sel_n, spans = [], [], []
    for (g, j), ps in logits_at.items():
        spans.append(((g, j), len(sel_g), len(ps)))
        sel_g += [g] * len(ps)
        sel_n += [packs[g][3][j][p] for p in ps]
    if sel_g:
        h = o.last_hidden_state[torch.tensor(sel_g, device=device), torch.tensor(sel_n, device=device)]
        lg = head(h)
        if lg.dtype in (torch.bfloat16, torch.float16):
            lg = lg.float()
        for rc, a, n in spans:
            out_l[rc] = lg[a:a + n]
    for g, j in hidden_of:
        out_h[(g, j)] = o.hidden_states[layer][g, torch.tensor(packs[g][3][j], device=device)]
    return out_l, out_h


def group_rows(enc, items, extra_texts=()):
    """One group (items of one snapshot, same images): prompt rows [extra texts..., then per item its cover rows].
    Returns (group dict, per-item [(row index, depth offset)...] bookkeeping)."""
    from .stagea_loss import cover
    ims = _images(items[0]) if items else []
    texts = list(extra_texts) + [it["text"] for it in items]
    gr = encode_group(enc, texts, ims)
    prompts = gr["rows"]
    rows = prompts[:len(extra_texts)]
    book = []
    for i, it in enumerate(items):
        p = prompts[len(extra_texts) + i]
        tok, trie = enc.trie(it["names"])
        names, where = cover(tok, trie)
        base = len(rows)
        rows += [p + list(tok[n]) for n in names]
        book.append((tok, trie, where, base, len(p), names))
    gr["rows"] = rows
    gr["cap"] = min(len(p) for p in prompts) - 1
    return gr, book


def _logits_req(g, book, out):
    for tok, trie, where, base, P, names in book:
        for s, n in enumerate(names):
            out[(g, base + s)] = [P - 1 + d for d in range(len(tok[n]) + 1)]


def _lp_of(g, book, logits, end):
    from .stagea_loss import option_logprobs
    res = []
    for tok, trie, where, base, P, names in book:
        node = {pre: logits[(g, base + s)][d] for pre, (s, d) in where.items()}
        res.append(option_logprobs(node, tok, trie, end))
    return res


def items_logprobs(model, enc, items, device) -> list:
    """{option name: log p~} per item (same order), all items in one shared-prefix batch."""
    groups, books, order = [], [], []
    for grp in group_items(items):
        gr, book = group_rows(enc, grp)
        groups.append(gr)
        books.append(book)
        order += [id(it) for it in grp]
    req: dict = {}
    for g, book in enumerate(books):
        _logits_req(g, book, req)
    logits, _ = shared_forward(model, groups, device, req, pad_id=enc.pad, enc=enc)
    got = {}
    for g, (book, grp) in enumerate(zip(books, group_items(items))):
        for it, lp in zip(grp, _lp_of(g, book, logits, enc.end)):
            got[id(it)] = lp
    return [got[id(it)] for it in items]


def samples_forward(model, enc, samples, device, layer=-1):
    """Stage B: per sample one group = [context prompt] + its decision items. Returns ([hidden [T_i, D]],
    [[item lp dicts]]); the context and all questions of a sample share one prefix pass."""
    groups, books = [], []
    for s in samples:
        its = s.get("items") or []
        ctx = s["context"]
        for it in its:
            if _images(it) != list(ctx["images"] or []):
                raise ValueError(f"{s.get('key')}: item images differ from the context images")
        gr, book = group_rows(enc, [{**it, "images": ctx["images"]} for it in its], [ctx["text"]])
        if not its:
            gr = encode_group(enc, [ctx["text"]], ctx["images"])
            gr["rows"] = gr["rows"] + [gr["rows"][0]]  # a twin row keeps shared_len < len (no questions)
        groups.append(gr)
        books.append(book)
    req: dict = {}
    for g, book in enumerate(books):
        _logits_req(g, book, req)
    logits, hid = shared_forward(model, groups, device, req, hidden_of=[(g, 0) for g in range(len(groups))],
                                 layer=layer, pad_id=enc.pad, enc=enc)
    return [hid[(g, 0)] for g in range(len(groups))], [_lp_of(g, b, logits, enc.end) for g, b in enumerate(books)]
