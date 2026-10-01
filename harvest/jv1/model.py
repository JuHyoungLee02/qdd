"""E-JV1 arm B model (docs/stage3/prereg_jv1.md §2): the same backbone as JCR (Qwen3-VL-4B, LoRA r32 on the language
layers, vision frozen) with NO action expert -- it answers in text (harvest.jv1.text): the head-image waypoint +
height, the gripper event, contact and anomaly bits. Loss = next-token cross entropy on the answer tokens only.
Inference: greedy decoding; contact / anomaly probabilities = p('1') / (p('0') + p('1')) at their answer positions;
the waypoint goes through the rule controller (text.rows) so predict() returns JCR's output format (delta rows, event
probs, contact p, anomaly p) and plugs into the unchanged JCR executor / offline evaluation."""
from __future__ import annotations

import json
import os

import numpy as np
import torch
import torch.nn.functional as F

from ..jcr import features as FT
from ..jcr import truth as T
from . import text as X

SYSTEM = ("You are the joystick reflex of a robot arm. Read the head and wrist images, the command and the state, "
          "and answer with the waypoint, event, contact and anomaly fields only.")
END = "<|im_end|>"
LABELS = (("head camera", 0), ("right wrist camera", 1))


class JV1:
    def __init__(self, backbone, proc, label: str = "P"):
        self.backbone, self.proc, self.label = backbone, proc, label
        tk = proc.tokenizer
        self.tok = tk
        self.end = tk.encode(END, add_special_tokens=False)[0]
        self.id0, self.id1 = tk.encode("0", add_special_tokens=False)[0], tk.encode("1", add_special_tokens=False)[0]

    # ------------------------------------------------------------------ inputs
    def _prompt(self, s) -> str:
        content = []
        for lab, _ in LABELS:
            content += [{"type": "text", "text": lab}, {"type": "image"}]
        content.append({"type": "text", "text": X.prompt(s)})
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
        return self.proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    def _inputs(self, items, device, answers=None):
        """items: [(image paths [head, wrist], sample)]; left padding (answers end-aligned)."""
        from PIL import Image
        texts, imgs = [], []
        for k, (paths, s) in enumerate(items):
            p = self._prompt(s)
            texts.append(p + (answers[k] + END if answers is not None else ""))
            imgs += [Image.open(q).convert("RGB") for q in paths]
        self.tok.padding_side = "left"
        x = self.proc(text=texts, images=imgs, return_tensors="pt", padding=True)
        return {k: v.to(device) for k, v in x.items()}

    # ------------------------------------------------------------------ training
    def losses(self, items, device):
        """items: [(image paths, sample with the training label)] -> mean CE over answer tokens."""
        ans = [X.answer(s, self.label) for _, s in items]
        x = self._inputs(items, device, ans)
        n_ans = [len(self.tok.encode(a + END, add_special_tokens=False)) for a in ans]
        M = max(n_ans)
        out = self.backbone(**x, logits_to_keep=M + 1)
        lg = out.logits[:, :-1].float()
        tgt = x["input_ids"][:, -M:].clone()
        for i, n in enumerate(n_ans):
            tgt[i, :M - n] = -100
        loss = F.cross_entropy(lg.reshape(-1, lg.shape[-1]), tgt.reshape(-1), ignore_index=-100)
        return loss

    # ------------------------------------------------------------------ inference
    @torch.no_grad()
    def generate(self, paths, samples, device, max_new: int = 28):
        x = self._inputs([(paths, s) for s in samples], device)
        g = self.backbone.generate(**x, max_new_tokens=max_new, do_sample=False, output_scores=True,
                                   return_dict_in_generate=True, eos_token_id=self.end, pad_token_id=self.tok.pad_token_id)
        L = x["input_ids"].shape[1]
        seqs = g.sequences[:, L:]
        out = []
        for i in range(seqs.shape[0]):
            ids = seqs[i].tolist()
            field, probs = 0, {4: [], 5: []}
            text = ""
            for j, t in enumerate(ids):
                if t == self.end or t == self.tok.pad_token_id:
                    break
                s = self.tok.decode([t])
                text += s
                if s.startswith(" ") and j > 0:
                    field += 1
                if s.strip() in ("0", "1") and field in probs:
                    sc = torch.softmax(g.scores[j][i].float(), -1)
                    p0, p1 = float(sc[self.id0]), float(sc[self.id1])
                    probs[field].append(p1 / max(p0 + p1, 1e-9))
            out.append((text.strip(), probs))
        return out

    def predict(self, enc, image_set, samples, device, steps=None, seed=0):
        """JCR-compatible output (enc / steps / seed unused: greedy text). image_set: [[label, path], ...]."""
        paths = [p for _, p in image_set]
        res = []
        for (text, probs), s in zip(self.generate(paths, samples, device), samples):
            pr = X.parse(text)
            ev = np.zeros(FT.N_EVENT)
            if pr is None:
                ev[FT.EV_KEEP] = 1.0
                res.append({"delta": np.zeros((T.H, 3)).tolist(), "event_p": ev.tolist(), "contact_p": 0.0,
                            "anomaly_p": [0.0] * (len(T.ANOMALIES) + 1), "text": text, "parse_ok": False})
                continue
            ev[pr["event"]] = 1.0
            stop = pr["event"] == FT.EV_STOP
            c = X.from_pt(*pr["pt"])
            P = X.rows(s, s["p_cmd"] if stop else c, stop=stop)
            cp = probs[4][0] if probs[4] else float(pr["contact"])
            an = probs[5] if len(probs[5]) == len(T.ANOMALIES) else [float(b) for b in pr["anom"]]
            res.append({"delta": (P - np.asarray(s["p_cmd"], float)).tolist(), "event_p": ev.tolist(),
                        "contact_p": cp, "anomaly_p": list(an) + [max(an)], "c_hat": c.tolist(), "text": text,
                        "parse_ok": True})
        return res

    def eval(self):
        self.backbone.eval()
        return self

    def save(self, d, extra=None):
        os.makedirs(d, exist_ok=True)
        self.backbone.save_pretrained(os.path.join(d, "adapter"))
        with open(os.path.join(d, "jv1.json"), "w") as f:
            json.dump({"label": self.label, "system": SYSTEM, "head": X.HEAD, "table_z": X.TABLE_Z, **(extra or {})}, f)


def load(d, model_dir, device, dtype=torch.bfloat16):
    from ..train.stageb_train import load_backbone
    cfg = json.load(open(os.path.join(d, "jv1.json")))
    bb, proc, _ = load_backbone("qwen", model_dir, device, adapter=os.path.join(d, "adapter"), dtype=dtype)
    bb.eval()
    return JV1(bb, proc, cfg["label"]), None
