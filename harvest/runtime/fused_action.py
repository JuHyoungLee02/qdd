"""FusedModel action path (canon §58; R4 stage-B model, harvest/train/stageb_*.py).

The stage-B expert is conditioned on the COMMITTED decisions (cond["dec"]), so one fused step is two calls on the same
backbone: decide() = decision-token probabilities (vLLM, prefix + multimodal cache, lead mode; canon §59) -> M4
commit -> chunk(committed) = backbone context forward + expert flow sampling (HF torch; vLLM does not return hidden
states). GraphedSampler captures the Euler loop in a CUDA graph (R4: 10 steps eager 36-49 ms -> graph 23 ms, same
output) for B = 1 and a fixed padded context length (the key-padding mask keeps padding invisible).
chunk_value(): the expert's 30 Hz chunk (stageb_data.HZ, H = 15 = 0.5 s) read at the 100 Hz control tick (linear).
"""
from __future__ import annotations

import numpy as np


def chunk_value(chunk, chunk_dt: float, t0: float, now: float) -> np.ndarray:
    """Chunk row k is the target at t0 + k * chunk_dt; linear in between, held after the last row."""
    c = np.asarray(chunk, float)
    x = (now - t0) / chunk_dt
    if x <= 0:
        return c[0].copy()
    i = int(np.floor(x))
    if i >= len(c) - 1:
        return c[-1].copy()
    f = x - i
    return (1 - f) * c[i] + f * c[i + 1]


def pad_cond(cond: dict, T_max: int) -> dict:
    """Pad ctx [1,T,D] / ctx_mask [1,T] to T_max (mask 0 = padding, excluded by key_padding_mask)."""
    import torch
    ctx, m = cond["ctx"], cond["ctx_mask"]
    T = ctx.shape[1]
    if T > T_max:
        raise ValueError(f"context {T} tokens > T_max {T_max}")
    out = dict(cond)
    out["ctx"] = torch.cat([ctx, ctx.new_zeros(ctx.shape[0], T_max - T, ctx.shape[2])], 1)
    out["ctx_mask"] = torch.cat([m, m.new_zeros(m.shape[0], T_max - T)], 1)
    return out


class GraphedSampler:
    """sample_actions(expert, cond, steps, noise) with static shapes; CUDA graph replay on GPU, eager otherwise."""

    def __init__(self, expert, T_max: int, steps: int = 10, warmup: int = 3):
        import torch
        self.expert, self.T_max, self.steps, self.warmup = expert, T_max, steps, warmup
        self.dev = next(expert.parameters()).device
        self.graph, self.static = None, None
        self.use_graph = self.dev.type == "cuda"
        self.torch = torch

    def _capture(self, cond, noise):
        torch = self.torch
        from ..train.stageb_expert import sample_actions
        self.static = {k: (v.clone() if torch.is_tensor(v) else v) for k, v in cond.items()}
        self.static_noise = noise.clone()
        s = torch.cuda.Stream()
        s.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(s):
            for _ in range(self.warmup):
                sample_actions(self.expert, self.static, self.steps, self.static_noise)
        torch.cuda.current_stream().wait_stream(s)
        self.graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(self.graph):
            self.static_out = sample_actions(self.expert, self.static, self.steps, self.static_noise)

    def __call__(self, cond: dict, noise):
        from ..train.stageb_expert import sample_actions
        cond = pad_cond(cond, self.T_max)
        if not self.use_graph:
            return sample_actions(self.expert, cond, self.steps, noise)
        if self.graph is None:
            self._capture(cond, noise)
        for k, v in cond.items():
            if self.torch.is_tensor(v):
                self.static[k].copy_(v)
        self.static_noise.copy_(noise)
        self.graph.replay()
        return self.static_out.clone()
