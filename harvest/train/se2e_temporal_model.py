"""Torch side of the OPT-IN S-E2E temporal options (se2e_temporal; docs/stage3/prereg_se2e_temporal.md).

video2 ("D27v2-video2"): an image entry [label, now, prev] is encoded as ONE temporal patch holding [prev, now]
(Qwen3-VL temporal_patch_size 2; a still image fills both slots with itself). The pixel values equal the
Qwen3-VL video processor's output for the 2-frame clip [prev, now] bit for bit and the grid / LLM visual token
count equal the still image's (tests/train/test_se2e_temporal_qwen.py). The placeholder stays <|image_pad|>, so the
R3 shared-prefix forward (prefix_share.shared_forward, mrope index) is used unchanged; the per-frame timestamp text of
the video chat template is replaced by the entry label "(2 frames: t-0.3 s, t)". Entries [label, path] encode
exactly like HFEncoder / prefix_share.encode_group (the default path is not touched: stageb_model / prefix_share are
prompt-hash files, canon §71).
"""
from __future__ import annotations

import os

import torch

from . import prefix_share as P
from .stageb_model import HFEncoder, StageB


def _split(images):
    out = []
    for im in images or []:
        if isinstance(im, (list, tuple)):
            out.append((im[0], im[1], im[2] if len(im) > 2 else None))
        else:
            out.append((None, im, None))
    return out


class VideoEncoder(HFEncoder):
    """HFEncoder that also takes [label, now, prev] entries (2-frame clips)."""

    def _open(self, path):
        from PIL import Image
        return Image.open(os.path.join(self.root, path)).convert("RGB")

    def pixels(self, images) -> dict:
        ents = _split(images)
        if not ents:
            return {"pixel_values": None, "image_grid_thw": None}
        ip = self.p.image_processor
        x = ip(images=[self._open(n) for _, n, _ in ents], return_tensors="pt")
        pv, grid = x["pixel_values"], x["image_grid_thw"]
        if any(p is not None for _, _, p in ents):
            xp = ip(images=[self._open(p if p is not None else n) for _, n, p in ents], return_tensors="pt")
            if not torch.equal(xp["image_grid_thw"], grid):
                raise ValueError("past and current frames resize to different grids")
            T, ps = ip.temporal_patch_size, ip.patch_size
            N = pv.shape[0]
            pv = pv.clone().view(N, -1, T, ps * ps)
            pv[:, :, 0] = xp["pixel_values"].view(N, -1, T, ps * ps)[:, :, 0]  # slot 0 = the earlier frame
            pv = pv.view(N, -1)
        return {"pixel_values": pv, "image_grid_thw": grid}

    def render(self, text, images) -> str:
        content = []
        for label, _, _ in _split(images):
            if label:
                content.append({"type": "text", "text": label})
            content.append({"type": "image"})
        content.append({"type": "text", "text": text})
        msgs = [{"role": "system", "content": self.system}, {"role": "user", "content": content}]
        return self.p.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    def inputs(self, text, images, device):
        if isinstance(images, str):
            images = [images]
        ents = _split(images)
        prompt = self.render(text, images)
        x = self.p(text=[prompt], images=[self._open(n) for _, n, _ in ents] or None, return_tensors="pt")
        if any(p is not None for _, _, p in ents):
            px = self.pixels(images)
            if not torch.equal(px["image_grid_thw"], x["image_grid_thw"]):
                raise ValueError("grid mismatch")
            x["pixel_values"] = px["pixel_values"]
        return {k: v.to(device) for k, v in x.items()}


def encode_group_v(enc: VideoEncoder, texts, images) -> dict:
    """prefix_share.encode_group for VideoEncoder entries (same output for [label, path] entries)."""
    out = enc.pixels(images)
    counts = []
    if out["image_grid_thw"] is not None:
        merge = enc.p.image_processor.merge_size
        counts = [int(g.prod()) // merge ** 2 for g in out["image_grid_thw"]]
    img = P._image_id(enc)
    out["rows"] = [P.expand_image_tokens(enc.p.tokenizer(enc.render(t, images))["input_ids"], img, counts)
                   for t in texts]
    return out


def group_rows_v(enc, items, extra_texts=()):
    """prefix_share.group_rows with encode_group_v."""
    from .stagea_loss import cover
    ims = P._images(items[0]) if items else []
    texts = list(extra_texts) + [it["text"] for it in items]
    gr = encode_group_v(enc, texts, ims)
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


def samples_forward_v(model, enc, samples, device, layer=-1):
    """prefix_share.samples_forward with the VideoEncoder group encoder (one shared prefix pass per sample)."""
    groups, books = [], []
    for s in samples:
        its = s.get("items") or []
        ctx = s["context"]
        for it in its:
            if P._images(it) != list(ctx["images"] or []):
                raise ValueError(f"{s.get('key')}: item images differ from the context images")
        gr, book = group_rows_v(enc, [{**it, "images": ctx["images"]} for it in its], [ctx["text"]])
        if not its:
            gr = encode_group_v(enc, [ctx["text"]], ctx["images"])
            gr["rows"] = gr["rows"] + [gr["rows"][0]]
        groups.append(gr)
        books.append(book)
    req: dict = {}
    for g, book in enumerate(books):
        P._logits_req(g, book, req)
    logits, hid = P.shared_forward(model, groups, device, req, hidden_of=[(g, 0) for g in range(len(groups))],
                                   layer=layer, pad_id=enc.pad, enc=enc)
    return [hid[(g, 0)] for g in range(len(groups))], [P._lp_of(g, b, logits, enc.end) for g, b in enumerate(books)]


class StageBT(StageB):
    """StageB whose shared forward encodes 2-frame entries (use with VideoEncoder)."""

    def forward_shared(self, samples, enc, device, grad=True):
        with torch.set_grad_enabled(grad and torch.is_grad_enabled()):
            hs, lps = samples_forward_v(self.backbone, enc, samples, device, self.layer)
        T = max(h.shape[0] for h in hs)
        ctx = hs[0].new_zeros(len(hs), T, hs[0].shape[1])
        mask = torch.zeros(len(hs), T, dtype=torch.long, device=device)
        for i, h in enumerate(hs):
            ctx[i, :h.shape[0]] = h
            mask[i, :h.shape[0]] = 1
        return ctx, mask, lps


def as_temporal(model: StageB) -> StageB:
    model.__class__ = StageBT
    return model
