"""Pre-R7 fix 4: ONE real low-effort Astra call with the K3 (Gemini-faithful) heartbeat prompt + one pool head frame.
The key is read in-process from /data/.openai_token (never copied or printed). Writes the record (no key) to --out.

  python tools/pre_r7/astra_k3_smoke.py --out /data/harvest/out/pre_r7/astra_k3_smoke.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.clients.astra import AstraClient  # noqa: E402
from harvest.runtime.astra_hb import EFFORT, MAX_OUT, MODEL, heartbeat_input, parse_decision, prompt_for  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--frame", default="/data/harvest/data/pool/img/ep2000/k012_cam_head.jpg")
    a = ap.parse_args()
    tok = "/data/.openai_token"
    if not os.path.exists(tok):
        raise SystemExit("no /data/.openai_token: skip the real-call smoke")
    template, allowed, pid = prompt_for("K3", "hb")
    summary = ("t=4.0s stage=S1 phase=lift gripper_open=False\nfacts={'holding(o3)': True, "
               "'lifted_holding(o3)': True, 'on(o3,o5)': None, 'lifted(o3)': None}\n"
               "current step decisions={}\nlast step checks=['OK', 'OK']\npremise_epoch=0 grasp_retries=0")
    inp = heartbeat_input(summary, open(a.frame, "rb").read(), template=template)
    rec = AstraClient(open(tok).read().strip(), MODEL, timeout_s=60.0).call(inp, EFFORT, MAX_OUT,
                                                                            {"smoke": "pre_r7_k3", "prompt_id": pid})
    dec, note = parse_decision(rec.output_text, allowed)
    out = {"model": MODEL, "effort": EFFORT, "prompt_id": pid, "http": rec.http_status, "error": rec.error,
           "decision": dec, "note": note, "output_text": rec.output_text, "usage": rec.usage,
           "first_token_s": None if not rec.t_first_token else round(rec.t_first_token - rec.t_send, 3),
           "total_s": None if not rec.t_done else round(rec.t_done - rec.t_send, 3), "model_field": rec.model_field,
           "frame": a.frame}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
