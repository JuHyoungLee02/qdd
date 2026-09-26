"""Mock Astra for the coupling stream: answer() builds schema-valid answer dicts (tests, dry runs); no paid call."""
from __future__ import annotations

import json
import time


def answer(command: str = "continue", *, execution: str = "progressing", intent: str = "aligned",
           confidence: str = "high", evidence: str = "right wrist view: gripper above the mug",
           views=("cam_wrist_right",), claims=(), dp=(0.0, 0.0, 0.0), dr=(0.0, 0.0, 0.0), gripper: str = "keep",
           diff: str | None = None, info: str = "none", done=()) -> dict:
    d = {"assessment": {"task_progress": {"verified_completed": list(done), "currently_attempting": "pick the mug",
                                          "remaining": ["place the mug on the tray"]},
                        "execution": execution, "intent": intent, "confidence": confidence, "evidence": evidence,
                        "evidence_views": list(views), "claims": [{"kind": k, "view": v} for k, v in claims]},
         "info_request": info}
    if diff is not None:
        d["diff"] = diff
    if diff != "keep":
        d["command"] = command
        if command == "edit":
            d["edit"] = {"delta_position_m": list(dp), "delta_rotation_rad": list(dr), "gripper": gripper}
    return d


from ..clients.astra import AstraRecord  # noqa: E402  (keep answer() import-light for tests that only build dicts)


class ScriptedCoupleAstra:
    """Scripted stand-in with the AstraClient call() shape: `script` = a list of answers (dict or raw text; the last
    one repeats) or a callable(request dict) -> answer; a fixed synthetic latency (the runtime's DeliveryQueue delivers
    at send + latency); a fixed usage so the cost ledger can be exercised with a test price table."""
    model = "mock:astra-couple-scripted"

    def __init__(self, script, latency_s: float = 3.0, usage: dict | None = None):
        self.script, self.synthetic_latency = script, float(latency_s)
        self.usage = dict(usage or {})
        self.calls = []

    def call(self, inp, effort, max_output_tokens, meta) -> AstraRecord:
        from .prompt import request_from_input
        req = request_from_input(inp)
        self.calls.append({"req": req, "meta": dict(meta)})
        if callable(self.script):
            ans = self.script(req)
        else:
            ans = self.script[min(len(self.calls), len(self.script)) - 1]
        t = time.monotonic()
        return AstraRecord(t_send=t, t_first_token=t, t_done=t, http_status=200, usage=dict(self.usage),
                           output_text=ans if isinstance(ans, str) else json.dumps(ans), model_field=self.model,
                           effort=effort, meta=dict(meta))
