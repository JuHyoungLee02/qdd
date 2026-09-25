"""Stage-B fused model: one Qwen3-VL backbone (LoRA, as stage A) + action expert + auxiliary geometry head.

Losses per batch of stage-B samples (stageb_data):
  L = lam_dec * L_dec + lam_act * L_fm + lam_aux * L_aux (+ lam_vqa * L_vqa, off by default)
  L_dec : stage-A decision loss unchanged (stagea_loss.item_logprobs + set_nll: option-set renormalized NLL on the
          same prompts / option tries the inference reads) -> backbone (LoRA)
  L_fm  : flow matching of the action chunk; the expert reads the backbone hidden states of the context prompt
          through `insulate` (KI stop-gradient by default) -> expert only
  L_aux : privileged-geometry regression / predicates from the same hidden states WITHOUT insulation -> backbone +
          aux head (geometry must be learned from the images, §58)
  L_vqa : optional general-VQA retention (answer-token NLL), batches from a caller-supplied source.
The encoder turns (text, images) into backbone inputs: HFEncoder = Qwen3-VL processor + chat template (system =
jevl.SYSTEM, user = [image]*n + text, generation prompt), i.e. stage A's prompt with n images (§57).
"""
from __future__ import annotations

import json
import os

import numpy as np
import torch
from torch import nn

from . import stageb_data as D
from .stageb_expert import (ActionExpert, AuxConfig, AuxGeomHead, ExpertConfig, aux_loss, fm_loss, insulate,
                            sample_actions)
from .stagea_loss import batch_inputs, item_logprobs, set_nll

END_TOKEN = "<|im_end|>"


class HFEncoder:
    def __init__(self, processor, image_root: str = ""):
        from ..clients.jevl import SYSTEM
        self.p, self.root, self.system = processor, image_root, SYSTEM
        tk = processor.tokenizer
        e = tk.encode(END_TOKEN, add_special_tokens=False)
        if len(e) != 1:
            raise ValueError(f"end token {END_TOKEN!r} is not one token: {e}")
        self.end, self.pad = e[0], tk.pad_token_id if tk.pad_token_id is not None else e[0]
        self._tries = {}

    def trie(self, names):
        from ..clients.jevl import option_trie
        key = tuple(names)
        if key not in self._tries:
            tok = {n: self.p.tokenizer.encode(n, add_special_tokens=False) for n in names}
            self._tries[key] = (tok, option_trie(tok, self.end))
        return self._tries[key]

    def ids(self, text):
        return self.p.tokenizer.encode(text, add_special_tokens=False)

    def inputs(self, text, images, device):
        """images: [[label, path], ...] (§59: label text then the native-resolution image, in order) or plain
        paths (no label, stage-A single-image form)."""
        from PIL import Image
        if isinstance(images, str):
            images = [images]
        content, imgs = [], []
        for im in images or []:
            label, path = im if isinstance(im, (list, tuple)) else (None, im)
            if label:
                content.append({"type": "text", "text": label})
            content.append({"type": "image"})
            imgs.append(Image.open(os.path.join(self.root, path)).convert("RGB"))
        content.append({"type": "text", "text": text})
        msgs = [{"role": "system", "content": self.system}, {"role": "user", "content": content}]
        prompt = self.p.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        x = self.p(text=[prompt], images=imgs or None, return_tensors="pt")
        return {k: v.to(device) for k, v in x.items()}

    def logprobs(self, model, item, device):
        """Old per-item path: {option name: log p~} of one item (its own full forward)."""
        tok, trie = self.trie(item["names"])
        return item_logprobs(model, self.inputs(item["text"], item_images(item), device), tok, trie, self.end,
                             self.pad)


def item_images(it):
    return it.get("images") or ([it["image"]] if it.get("image") else [])


class StageB(nn.Module):
    def __init__(self, backbone, expert: ActionExpert, aux: AuxGeomHead | None, norm: D.ActionNorm, vocabs: dict,
                 ki: str = "stop", layer: int = -1, lam=None, verify: AuxGeomHead | None = None):
        super().__init__()
        self.backbone, self.expert, self.aux, self.verify = backbone, expert, aux, verify
        self.norm, self.vocabs, self.ki, self.layer = norm, vocabs, ki, layer
        self.lam = {"dec": 1.0, "act": 1.0, "aux": 0.1, "vqa": 0.0, "ver": 0.1, **(lam or {})}
        insulate(torch.zeros(1), ki)  # validate
        self.shared = True  # R3: context + questions of a sample share one prefix pass (prefix_share)
        self.last_fw = None  # (ctx, mask, per-sample item log-probs) of the last shared losses() call

    # ---------------------------------------------------------------------------------- backbone features
    def context(self, inputs, grad: bool = True):
        """Hidden states [T, D] of one context prompt (layer self.layer)."""
        with torch.set_grad_enabled(grad and torch.is_grad_enabled()):
            out = self.backbone(**inputs, output_hidden_states=True, logits_to_keep=1)
        return out.hidden_states[self.layer][0]

    def contexts(self, samples, enc, device, grad=True):
        hs = [self.context(enc.inputs(s["context"]["text"], s["context"]["images"], device), grad) for s in samples]
        T = max(h.shape[0] for h in hs)
        ctx = hs[0].new_zeros(len(hs), T, hs[0].shape[1])
        mask = torch.zeros(len(hs), T, dtype=torch.long, device=device)
        for i, h in enumerate(hs):
            ctx[i, :h.shape[0]] = h
            mask[i, :h.shape[0]] = 1
        return ctx, mask

    def forward_shared(self, samples, enc, device, grad=True):
        """R3 path: (ctx [B, T, D], mask [B, T], [[item lp dicts] per sample]) from one prefix pass per sample
        (system + images + state) and one batched pass of the context tail and every question's option rows."""
        from .prefix_share import samples_forward
        with torch.set_grad_enabled(grad and torch.is_grad_enabled()):
            hs, lps = samples_forward(self.backbone, enc, samples, device, self.layer)
        T = max(h.shape[0] for h in hs)
        ctx = hs[0].new_zeros(len(hs), T, hs[0].shape[1])
        mask = torch.zeros(len(hs), T, dtype=torch.long, device=device)
        for i, h in enumerate(hs):
            ctx[i, :h.shape[0]] = h
            mask[i, :h.shape[0]] = 1
        return ctx, mask, lps

    # ---------------------------------------------------------------------------------- conditions / targets
    def proprio_input(self, s) -> np.ndarray:
        """Expert proprio input of one sample: per-arm normalized values with masked keys zeroed (§63 (1), (3)) +
        one mask channel per key (experts built with proprio_dim = D.PROPRIO_IN_DIM; pre-§63 experts: values only)."""
        arm = s.get("arm", "right")
        x = self.norm.proprio(s["proprio"], arm, s.get("proprio_mask"))
        if self.expert.cfg.proprio_dim == D.PROPRIO_IN_DIM:
            x = np.concatenate([x, D.proprio_mask_vec(s.get("proprio_mask"))])
        return x.astype(np.float32)

    def cond(self, samples, ctx, mask, device):
        n, v = self.norm, self.vocabs
        c = {"ctx": insulate(ctx, self.ki), "ctx_mask": mask,
             "proprio": torch.tensor(np.stack([self.proprio_input(s) for s in samples]), device=device),
             "skill": torch.tensor([v["skill"].get(s["skill_id"]) for s in samples], device=device),
             "phase": torch.tensor([v["phase"].get(s["phase_id"]) for s in samples], device=device),
             "dec": torch.tensor([D.dec_ids(s["committed"], v["dec"]) for s in samples], device=device)}
        if self.expert.cfg.residual:
            c["script"] = torch.tensor(np.stack([n.cond_script(s["action_script"], s.get("arm", "right"))
                                                 for s in samples]), device=device)
        return c

    def targets(self, samples, device):
        zs, sat = zip(*[self.norm.target(s["action_exec"], s["action_script"], s.get("arm", "right"))
                        for s in samples])
        a = torch.tensor(np.stack(zs), device=device)
        valid = torch.tensor(np.asarray([s["valid"] for s in samples], np.float32), device=device)
        return a, valid, float(np.mean(sat))

    # ---------------------------------------------------------------------------------- losses
    def decision_loss(self, samples, enc, device):
        vals = []
        for s in samples:
            for it in s["items"]:
                tok, trie = enc.trie(it["names"])
                lp = item_logprobs(self.backbone, enc.inputs(it["text"], item_images(it), device), tok, trie,
                                   enc.end, enc.pad)
                vals.append(set_nll(lp, it["target"]))
        return torch.stack(vals).mean() if vals else None

    def vqa_loss(self, vqa, enc, device):
        vals = []
        for x in vqa:
            ids = enc.ids(x["answer"]) + [enc.end]
            batch, keep = batch_inputs(enc.inputs(x["text"], x.get("images"), device), [ids], enc.pad)
            lg = self.backbone(**batch, logits_to_keep=keep).logits[0].float()
            lp = torch.log_softmax(lg[:len(ids)], -1)
            vals.append(-lp[torch.arange(len(ids)), torch.tensor(ids, device=lg.device)].mean())
        return torch.stack(vals).mean()

    def verify_loss(self, samples, ctx, mask, device):
        """§61 / §64 verification head: BCE on the E-M4b-meas test predicates (verify.truth), None masked; the
        gradient reaches the backbone like the aux head (the same backbone must see the world)."""
        import torch.nn.functional as F
        y, m = (torch.tensor(np.stack(x), device=device) for x in zip(*[D.verify_vecs(s.get("verify")) for s in samples]))
        _, lg = self.verify(ctx, mask)
        return (F.binary_cross_entropy_with_logits(lg, y, reduction="none") * m).sum() / m.sum().clamp_min(1.0)

    def verify_logits(self, ctx, mask) -> torch.Tensor:
        """[B, len(D.VERIFY_PREDS)] raw logits (runtime: temperature + conformal in runtime.measure)."""
        return self.verify(ctx, mask)[1]

    def losses(self, samples, enc, device, vqa=None, fm_t=None, fm_noise=None):
        need_grad_ctx = (self.aux is not None and self.lam["aux"] > 0 or self.ki != "stop"
                         or self.verify is not None and self.lam.get("ver", 0) > 0)
        lps = None
        if self.shared and hasattr(enc, "p"):  # the shared path needs the HF processor (mock encoders: old path)
            dec = self.lam["dec"] > 0 and any(s["items"] for s in samples)
            ctx, mask, lps = self.forward_shared(samples, enc, device, grad=need_grad_ctx or dec)
            self.last_fw = (ctx, mask, lps)
        else:
            ctx, mask = self.contexts(samples, enc, device, grad=need_grad_ctx)
        a, valid, sat = self.targets(samples, device)
        cond = self.cond(samples, ctx, mask, device)
        l_fm = fm_loss(self.expert, cond, a, valid, t=fm_t, noise=fm_noise)
        total = self.lam["act"] * l_fm
        logs = {"fm": float(l_fm.detach()), "res_sat": sat}
        if self.aux is not None and self.lam["aux"] > 0:
            r, rm, c, cm = (torch.tensor(np.stack(x), device=device) for x in
                            zip(*[D.aux_vecs(s["aux"]) for s in samples]))
            l_aux, lg = aux_loss(self.aux, ctx, mask, r, rm, c, cm)
            total = total + self.lam["aux"] * l_aux
            logs.update(aux=float(l_aux.detach()), **lg)
        if self.verify is not None and self.lam.get("ver", 0) > 0 and any(s.get("verify") for s in samples):
            l_ver = self.verify_loss(samples, ctx, mask, device)
            total = total + self.lam["ver"] * l_ver
            logs["ver"] = float(l_ver.detach())
        if self.lam["dec"] > 0:
            if lps is None:
                l_dec = self.decision_loss(samples, enc, device)
            else:
                vals = [set_nll(lp, it["target"]) for s, lp_s in zip(samples, lps) for it, lp in zip(s["items"], lp_s)]
                l_dec = torch.stack(vals).mean() if vals else None
            if l_dec is not None:
                total = total + self.lam["dec"] * l_dec
                logs["dec"] = float(l_dec.detach())
        if vqa and self.lam["vqa"] > 0:
            l_vqa = self.vqa_loss(vqa, enc, device)
            total = total + self.lam["vqa"] * l_vqa
            logs["vqa"] = float(l_vqa.detach())
        logs["total"] = float(total.detach())
        return total, logs

    # ---------------------------------------------------------------------------------- inference
    @torch.no_grad()
    def predict(self, sample, enc, device, steps=10, noise=None):
        """Executable chunk [H, 8] for one sample (context forward + `steps` Euler steps)."""
        ctx, mask = self.contexts([sample], enc, device, grad=False)
        z = sample_actions(self.expert, self.cond([sample], ctx, mask, device), steps, noise)[0].cpu().numpy()
        return self.norm.action(z, sample["action_script"], sample.get("arm", "right"))

    # ---------------------------------------------------------------------------------- save / load heads
    def head_config(self):
        return {"expert": self.expert.cfg.to_json(), "aux": None if self.aux is None else self.aux.cfg.to_json(),
                "verify": None if self.verify is None else {**self.verify.cfg.to_json(),
                                                            "preds": list(D.VERIFY_PREDS)},
                "norm": self.norm.to_json(), "vocabs": {k: v.to_json() for k, v in self.vocabs.items()},
                "ki": self.ki, "layer": self.layer, "lam": self.lam}

    def save_heads(self, out_dir, extra=None):
        os.makedirs(out_dir, exist_ok=True)
        sd = {f"expert.{k}": v.detach().cpu().contiguous() for k, v in self.expert.state_dict().items()}
        if self.aux is not None:
            sd.update({f"aux.{k}": v.detach().cpu().contiguous() for k, v in self.aux.state_dict().items()})
        if self.verify is not None:
            sd.update({f"verify.{k}": v.detach().cpu().contiguous() for k, v in self.verify.state_dict().items()})
        torch.save(sd, os.path.join(out_dir, "heads.pt"))
        json.dump({**self.head_config(), **(extra or {})}, open(os.path.join(out_dir, "stageb.json"), "w"), indent=1)


def build_heads(cfg_json: dict, device=None):
    e = ActionExpert(ExpertConfig(**cfg_json["expert"]))
    a = None if cfg_json.get("aux") is None else AuxGeomHead(AuxConfig(**cfg_json["aux"]))
    vc = cfg_json.get("verify")
    if vc is not None and list(vc.get("preds", D.VERIFY_PREDS)) != list(D.VERIFY_PREDS):
        raise ValueError(f"verify head predicates {vc.get('preds')} != {D.VERIFY_PREDS}")
    v = None if vc is None else AuxGeomHead(AuxConfig(**{k: x for k, x in vc.items() if k != "preds"}))
    if device is not None:
        e.to(device)
        a is not None and a.to(device)
        v is not None and v.to(device)
    return e, a, v


def load_heads(out_dir, backbone, device="cpu") -> StageB:
    cfg = json.load(open(os.path.join(out_dir, "stageb.json")))
    e, a, v = build_heads(cfg)
    sd = torch.load(os.path.join(out_dir, "heads.pt"), map_location="cpu", weights_only=True)
    e.load_state_dict({k[7:]: x for k, x in sd.items() if k.startswith("expert.")})
    if a is not None:
        a.load_state_dict({k[4:]: x for k, x in sd.items() if k.startswith("aux.")})
    if v is not None:
        v.load_state_dict({k[7:]: x for k, x in sd.items() if k.startswith("verify.")})
    vocabs = {k: D.Vocab.from_json(x) for k, x in cfg["vocabs"].items()}
    m = StageB(backbone, e, a, D.ActionNorm.from_json(cfg["norm"]), vocabs, cfg["ki"], cfg["layer"], cfg["lam"],
               verify=v)
    return m.to(device)


def new_verify_head(ctx_dim, aux_kw=None) -> AuxGeomHead:
    """V1h architecture (m4b.vhead.make_head: queries 4, width 512, heads 8) with the 9 test-predicate logits."""
    kw = {"width": 512, "queries": 4, "heads": 8, **{k: x for k, x in (aux_kw or {}).items()
                                                      if k in ("width", "queries", "heads")}}
    return AuxGeomHead(AuxConfig(ctx_dim=ctx_dim, n_reg=0, n_cls=len(D.VERIFY_PREDS), **kw))


def new_model(backbone, samples, ctx_dim, mode="absolute", ki="stop", layer=-1, expert_kw=None, aux_kw=None,
              lam=None, xi=None, use_aux=True, use_verify=True) -> StageB:
    """Heads sized from the training samples (vocabularies, normalization statistics)."""
    rows = [{"action_exec": s["action_exec"], "valid": s["valid"], "proprio": s["proprio"],
             "arm": s.get("arm", "right"), "proprio_mask": s.get("proprio_mask")} for s in samples]
    norm = D.ActionNorm.fit(rows, mode, xi)  # per-arm statistics, masked proprio left out (§63 (1), (3))
    vocabs = D.build_vocabs(samples)
    H = samples[0]["H"]
    ecfg = ExpertConfig(ctx_dim=ctx_dim, horizon=H, proprio_dim=D.PROPRIO_IN_DIM, n_questions=len(D.QUESTIONS),
                        dec_vocab=len(vocabs["dec"]) + 8, skill_vocab=len(vocabs["skill"]) + 4,
                        phase_vocab=len(vocabs["phase"]) + 4, residual=mode == "residual", **(expert_kw or {}))
    acfg = AuxConfig(ctx_dim=ctx_dim, n_reg=len(D.AUX_REG), n_cls=len(D.AUX_CLS), **(aux_kw or {}))
    return StageB(backbone, ActionExpert(ecfg), AuxGeomHead(acfg) if use_aux else None, norm, vocabs, ki, layer, lam,
                  verify=new_verify_head(ctx_dim, aux_kw) if use_verify else None)
