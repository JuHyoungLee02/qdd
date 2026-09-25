"""E-MA3 OPT-IN: per-layer backbone KV conditioning of the action expert (docs/stage3/prereg_ma3.md; MolmoAct2 table
11 "per-layer KV", research molmoact_deepdive_2026-09-26 §3.3 / §5 rank 3). Nothing here is read by the default
training / runtime path; stageb_expert / stageb_model / prefix_share / stageb_data are not touched.

Baseline (`none`): every expert block cross-attends to ONE backbone layer's hidden states (the last), projected by
ctx_norm + ctx_proj. `kvcond@v1`: expert block i cross-attends to the key / value states of backbone layer
L_i = floor((i + 1) * n_layers / depth) - 1 (36 layers, depth 8 -> 3, 8, 12, 17, 21, 26, 30, 35; the last block reads
the last layer), K = k_norm(k_proj(x)) BEFORE the rotary embedding (position-free content; the expert has its own
positions) and V = v_proj(x), each [T, kv_heads * head_dim] (1024 for Qwen3-VL-4B), of the SAME context prompt tokens
the baseline uses (the context row of the shared prefix pass). Per block: LayerNorm + Linear(kv_dim -> width) for K
and for V, then the block's own cross-attention (queries from the action / condition tokens) with key = projected K,
value = projected V. KI stop (default and the only mode): K / V are detached, the flow loss never reaches the
backbone. The hidden-state ctx path (aux / verification heads, decisions) is unchanged; the expert's own
ctx_norm / ctx_proj become unused.

Capture: forward hooks on the chosen layers' self_attn.k_norm and self_attn.v_proj (LoRA-wrapped modules included),
active only inside StageBKV.forward_shared / contexts. Checkpoint: the KV projections live in expert.kv.* of
heads.pt and stageb.json gets "expert_cond" = {ver, layers, kv_dim}; stageb_model.load_heads refuses such a
checkpoint (strict state dict), load_heads_kv loads both kinds (a default checkpoint = load_heads unchanged).
The new modules are created AFTER the baseline heads (same initial baseline parameters and RNG stream).

CLI (stageb_train commands / options, plus --expert-cond kvcond@v1):
  python -m harvest.train.se2e_kvcond train|predict|evalck ... --expert-cond kvcond@v1
Without the option this is stageb_train.main unchanged (test).
"""
from __future__ import annotations

import json
import os

import torch
from torch import nn

from . import stageb_data as D
from .stageb_expert import ActionExpert, fm_loss, insulate, time_embedding  # noqa: F401  (fm_loss: tests)
from .stageb_model import StageB, build_heads

KV_VER = "kvcond@v1"
EXPERT_COND_CHOICES = ("none", KV_VER)


def kv_layers(n_layers: int, depth: int) -> list:
    return [((i + 1) * n_layers) // depth - 1 for i in range(depth)]


def check_layers(layers, n_layers: int) -> None:
    if any(x < 0 or x >= n_layers for x in layers) or len(set(layers)) != len(layers):
        raise ValueError(f"kv layers {layers}: need distinct layers in [0, {n_layers})")


def decoder_layers(backbone):
    """The LLM decoder layer list of a (peft-wrapped) Qwen3-VL."""
    for name, mod in backbone.named_modules():
        if name.endswith("language_model.layers") and isinstance(mod, nn.ModuleList):
            return mod
    raise ValueError("no language_model.layers in the backbone")


def text_config(backbone):
    m = backbone.get_base_model() if hasattr(backbone, "get_base_model") else backbone
    return m.config.text_config


# ------------------------------------------------------------------------------------------ expert
class KVProj(nn.Module):
    def __init__(self, kv_dim, w):
        super().__init__()
        self.nk, self.k = nn.LayerNorm(kv_dim), nn.Linear(kv_dim, w)
        self.nv, self.v = nn.LayerNorm(kv_dim), nn.Linear(kv_dim, w)

    def forward(self, k, v):
        return self.k(self.nk(k.float())), self.v(self.nv(v.float()))


class KVExpert(ActionExpert):
    """ActionExpert whose block i cross-attends to (projected K_i, projected V_i) instead of the shared ctx."""

    def encode(self, cond: dict) -> dict:
        enc = super().encode(cond)
        enc["kv"] = [p(k, v) for p, (k, v) in zip(self.kv, cond["kv"])]
        enc["ctx"] = None  # unused
        return enc

    def velocity(self, enc: dict, x_t: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        a = x_t.float()
        if self.cfg.residual:
            a = torch.cat([a, enc["script"].float()], -1)
        te = time_embedding(t, self.cfg.width)[:, None].expand(-1, a.shape[1], -1)
        tok = self.act_mlp(torch.cat([self.act_in(a), te], -1)) + self.pos[None, :a.shape[1]]
        n = enc["ctok"].shape[1]
        x = torch.cat([enc["ctok"], tok], 1)
        for b, (k, v) in zip(self.blocks, enc["kv"]):
            h = b.n1(x)
            x = x + b.sa(h, h, h, need_weights=False)[0]
            h = b.n2(x)
            x = x + b.ca(h, k, v, key_padding_mask=enc["pad"], need_weights=False)[0]
            x = x + b.mlp(b.n3(x))
        return self.out(self.out_norm(x[:, n:]))


def to_kv_expert(e: ActionExpert, kv_dim: int) -> KVExpert:
    """In place: class switch + the per-block KV projections (created now: after every baseline parameter)."""
    dev = next(e.parameters()).device
    e.__class__ = KVExpert
    e.kv_dim = kv_dim
    e.kv = nn.ModuleList(KVProj(kv_dim, e.cfg.width) for _ in range(e.cfg.depth)).to(dev)
    return e


# ------------------------------------------------------------------------------------------ capture
class _Capture:
    def __init__(self, backbone, layers, detach):
        self.layers, self.detach, self.k, self.v, self.h = layers, detach, {}, {}, []
        mods = decoder_layers(backbone)
        for i in layers:
            at = mods[i].self_attn
            self.h.append(at.k_norm.register_forward_hook(self._hook(self.k, i, flat=True)))
            self.h.append(at.v_proj.register_forward_hook(self._hook(self.v, i, flat=False)))

    def _hook(self, store, i, flat):
        def f(_m, _inp, out):
            o = out.detach() if self.detach else out
            store.setdefault(i, []).append(o.flatten(-2) if flat else o)
        return f

    def close(self):
        for h in self.h:
            h.remove()


class StageBKV(StageB):
    """StageB + per-layer KV conditioning of the expert (cond()['kv'] from the latest context forward)."""

    kv_layers: list = []

    def _gather(self, cap, ctx, mask, parts):
        """parts: per sample (capture call index, row in that call); the context row = the first T_i positions."""
        T = ctx.shape[1]
        kvs = []
        for i in self.kv_layers:
            ks, vs = [], []
            for (c, g), n in zip(parts, mask.sum(1).tolist()):
                k, v = cap.k[i][c][g, :n], cap.v[i][c][g, :n]
                ks.append(torch.nn.functional.pad(k, (0, 0, 0, T - n)))
                vs.append(torch.nn.functional.pad(v, (0, 0, 0, T - n)))
            kvs.append((torch.stack(ks), torch.stack(vs)))
        self._kv = (ctx, kvs)

    def forward_shared(self, samples, enc, device, grad=True):
        cap = _Capture(self.backbone, self.kv_layers, self.ki == "stop")
        try:
            ctx, mask, lps = super().forward_shared(samples, enc, device, grad)
        finally:
            cap.close()
        self._gather(cap, ctx, mask, [(0, g) for g in range(len(samples))])
        return ctx, mask, lps

    def contexts(self, samples, enc, device, grad=True):
        cap = _Capture(self.backbone, self.kv_layers, self.ki == "stop")
        try:
            ctx, mask = super().contexts(samples, enc, device, grad)
        finally:
            cap.close()
        self._gather(cap, ctx, mask, [(j, 0) for j in range(len(samples))])
        return ctx, mask

    def cond(self, samples, ctx, mask, device):
        c = super().cond(samples, ctx, mask, device)
        if getattr(self, "_kv", None) is None or self._kv[0] is not ctx:
            raise RuntimeError("kv conditioning: ctx is not the one of the latest context forward")
        c["kv"] = [(insulate(k, self.ki), insulate(v, self.ki)) for k, v in self._kv[1]]
        return c

    def head_config(self):
        return {**super().head_config(), "expert_cond": {"ver": KV_VER, "layers": list(self.kv_layers),
                                                         "kv_dim": self.expert.kv_dim}}


def as_kvcond(model: StageB, layers) -> StageBKV:
    if model.ki != "stop":
        raise ValueError("kvcond@v1: KI stop only")
    if not isinstance(model.expert, KVExpert):
        raise ValueError("expert without KV projections")
    model.__class__ = StageBKV
    model.kv_layers = list(layers)
    model._kv = None
    return model


def with_kvcond(model: StageB) -> StageBKV:
    """A NEW (untrained) baseline model -> kvcond@v1 (layers from the backbone depth, KV size from its config)."""
    tc = text_config(model.backbone)
    layers = kv_layers(tc.num_hidden_layers, model.expert.cfg.depth)
    check_layers(layers, tc.num_hidden_layers)
    to_kv_expert(model.expert, tc.num_key_value_heads * tc.head_dim)
    return as_kvcond(model, layers)


def load_heads_kv(out_dir, backbone, device="cpu") -> StageB:
    """stageb_model.load_heads for both checkpoint kinds (no 'expert_cond' -> load_heads itself)."""
    from .stageb_model import load_heads
    cfg = json.load(open(os.path.join(out_dir, "stageb.json")))
    ec = cfg.get("expert_cond")
    if ec is None:
        return load_heads(out_dir, backbone, device)
    if ec["ver"] != KV_VER:
        raise ValueError(f"expert_cond {ec['ver']!r} != {KV_VER}")
    e, a, v = build_heads(cfg)
    to_kv_expert(e, ec["kv_dim"])
    sd = torch.load(os.path.join(out_dir, "heads.pt"), map_location="cpu", weights_only=True)
    e.load_state_dict({k[7:]: x for k, x in sd.items() if k.startswith("expert.")})
    if a is not None:
        a.load_state_dict({k[4:]: x for k, x in sd.items() if k.startswith("aux.")})
    if v is not None:
        v.load_state_dict({k[7:]: x for k, x in sd.items() if k.startswith("verify.")})
    vocabs = {k: D.Vocab.from_json(x) for k, x in cfg["vocabs"].items()}
    m = StageB(backbone, e, a, D.ActionNorm.from_json(cfg["norm"]), vocabs, cfg["ki"], cfg["layer"], cfg["lam"],
               verify=v)
    return as_kvcond(m, ec["layers"]).to(device)


# ------------------------------------------------------------------------------------------ CLI wrapper
def build_parser():
    from . import stageb_train as TR
    ap = TR.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    for name in ("train", "predict", "evalck"):
        sub.choices[name].add_argument("--expert-cond", default="none", choices=EXPERT_COND_CHOICES,
                                       help="E-MA3 kvcond@v1: expert block i reads backbone layer L_i's K / V")
    return ap


def install(TR, a) -> None:
    """Patch stageb_train for a --expert-cond run: new models get the KV expert, checkpoints load with the kv loader."""
    if getattr(a, "expert_cond", "none") == "none":
        return
    aux0 = TR.aux_model

    def aux_model(args, model, new):
        model = aux0(args, model, new)
        if new:
            if getattr(args, "aux_extra", "none") != "none":
                raise SystemExit("--expert-cond with --aux-extra: not a prereg_ma3 cell")
            model = with_kvcond(model)
        elif not isinstance(model, StageBKV):
            raise SystemExit("--expert-cond: the checkpoint has no kv conditioning")
        return model
    TR.aux_model, TR.load_heads = aux_model, load_heads_kv


def main(argv=None):
    from . import stageb_train as TR
    a = build_parser().parse_args(argv)
    install(TR, a)
    {"smoke": TR.cmd_smoke, "train": TR.cmd_train, "evalck": TR.cmd_evalck, "predict": TR.cmd_predict}[a.cmd](a)


if __name__ == "__main__":
    main()
