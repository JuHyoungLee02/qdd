"""Model clients of the Astra-solo arm: the probe's Astra client (Responses API streaming, PNG detail high, shared cost
ledger with a pre-call hard stop) extended to effort medium; the local VLM client is the probe's (vLLM chat).
model_id / name (prereg_open_vlm_solo.md): the same client with only the Responses-API model changed (an OpenAI proxy
of an open VLM, e.g. gpt-5.2-2025-12-11); the default stays gpt-6-astra."""
from __future__ import annotations

from ..astra_motion.cost import cost_usd
from ..astra_motion.models import ASTRA, MAX_IN_TOKENS, AstraModel, LocalVLM  # noqa: F401 - re-exported

MAX_OUT = {"low": 6000, "medium": 12000, "high": 20000}


class SoloAstra(AstraModel):
    def __init__(self, token, effort, ledger, transport=None, timeout_s=900.0, cache_key="astra_solo",
                 model_id=ASTRA, name="astra"):
        self.model_id = model_id
        super().__init__(token, "low", ledger, transport=transport, timeout_s=timeout_s, cache_key=cache_key)
        self.effort, self.name, self.max_out = effort, f"{name}-{effort}", MAX_OUT[effort]
        self.max_call_usd = cost_usd(self.model_id, {"input_tokens": MAX_IN_TOKENS, "output_tokens": self.max_out})
