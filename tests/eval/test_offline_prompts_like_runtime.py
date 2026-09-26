"""ser-A-min-3 fix round 1 items 2 / 4: offline prompts are the runtime's prompts.
- The fused canary (FusedAsker, stage-B checkpoint behind /decide) and the fused bench send what the fused runtime
  sends: the fused DecCall (FUSED_QUESTIONS, PH-A1 wording, gripper question) and ctx_text = IMG state + segment line +
  motion line (models.fused_ctx_text) -- the unknown segment (no Astra plan) and the snapshot's motion line.
- E0.5 / E1 / calibration / the modular canary (eval.common.build_request) show the unknown segment line like the
  modular runtime (never the skill's own phase), not the training rule's segment."""
import asyncio
import json
import os
from collections import defaultdict

import httpx

from harvest.serialize import SEGMENT_UNKNOWN

from .conftest import make_line


def test_fused_canary_asks_the_runtime_decall(tmp_path):
    from harvest.eval.canary import FusedAsker
    from harvest.runtime.models import FUSED_QUESTIONS, build_live_request, fused_ctx_text
    ln = make_line(0, "P0", 3)
    for cam in ("cam_head", "cam_wrist_right"):
        os.makedirs(os.path.dirname(tmp_path / ln["images"][cam]), exist_ok=True)
        open(tmp_path / ln["images"][cam], "wb").write(b"\xff\xd8jpg")
    sent = {}

    def handler(req):
        d = json.loads(req.content)
        sent.update(d)
        probs = {qid: {q["criteria"] and list(q["criteria"])[0]: 1.0} for qid, q in d["req"]["questions"].items()}
        return httpx.Response(200, json={"probs": probs})
    ask = FusedAsker("http://x", transport=httpx.MockTransport(handler))
    r = asyncio.run(ask.ask(ln, str(tmp_path)))
    want, shown = build_live_request(int(ln["ds_id"][2:]), ln["phase"], ln["text_state"], ln["state"]["present"],
                                     ln["state"]["obs"]["raw"], state="IMG", last_step=ln.get("last_step", "none"),
                                     questions=FUSED_QUESTIONS)
    assert sent["req"] == want  # fused wording + gripper question, unknown segment
    assert sent["ctx_text"] == fused_ctx_text(ln["text_state"])
    assert set(r["answers"]) == set(FUSED_QUESTIONS) and r["error"] is None
    assert ask.questions == FUSED_QUESTIONS
    asyncio.run(ask.close())


def test_modular_eval_requests_show_the_unknown_segment():
    from harvest.eval.common import build_request
    from harvest.deccall_snap import build_snapshot_request
    ln = make_line(0, "P0", 3)
    req, _ = build_request(ln)
    assert req["state"].split("\n")[-3] == SEGMENT_UNKNOWN  # like the modular runtime (no Astra plan)
    train, _, _ = build_snapshot_request({**ln, "oracle": defaultdict(lambda: None)})  # training items keep the rule's segment (+ the dropout share)
    assert train["state"].split("\n")[-3] == "segment: now=approach do=close next=carry"
    plan = "segment: now=carry do=open next=retreat"
    req, _ = build_request({**ln, "segment": plan})  # a recorded runtime plan is kept
    assert req["state"].split("\n")[-3] == plan
