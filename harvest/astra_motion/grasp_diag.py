"""Free diagnosis of the grasp-question over-claim with the local VLM (no paid calls): the same snapshots under prompt /
packaging variants, to separate a packaging or prompt bug from a genuine model tendency (main session instruction,
2026-09-25). Variants on the all-three-cameras condition (overlay on):
  base     the frozen question (prompts.GRASP_Q)
  define   + an explicit definition of 'held' (fingers closed on the object; open fingers around it are not a grasp)
  gray     the idle left-wrist image replaced by a flat gray image (labelled as not informative)
  order    right wrist first, then head, then left wrist
  python -m harvest.astra_motion.grasp_diag --snaps DIR --out JSONL --qwen-url URL
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import numpy as np

from . import prompts as PR
from . import schema as SC
from .grasp_probe import images
from .overlay import png_bytes

DEFINE = ("DEFINITION: 'held' means the two finger pads are CLOSED on the object (little or no gap between each pad "
          "and the object) so that it would move with the gripper. Open fingers with the object between them, fingers "
          "closed next to or in front of the object, or an object merely overlapping the fingers in a view are NOT "
          "held. Judge the finger opening from the right wrist view.\n")


def variant(sd, meta, v):
    ims = images(sd, meta, "all3", True)
    text = PR.GRASP_Q.format(views=PR.GRASP_VIEWS["all3"], tgt_name=PR.OBJ_NAME[meta["gt"]["tgt"]])
    if v == "define":
        text = text.replace("QUESTION:", DEFINE + "QUESTION:")
    elif v == "gray":
        g = np.full((240, 424, 3), 128, np.uint8)
        ims[1] = ("left wrist camera (idle arm, not informative for the right gripper: blanked)", png_bytes(g))
    elif v == "order":
        ims = [ims[2], ims[0], ims[1]]
        text = text.replace(PR.GRASP_VIEWS["all3"], "Image 1: RIGHT wrist camera. Image 2: head camera. Image 3: LEFT "
                                                     "wrist camera (idle left arm).")
    return text, ims


def main(argv=None):
    from .models import LocalVLM
    ap = argparse.ArgumentParser()
    ap.add_argument("--snaps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--qwen-url", default="http://127.0.0.1:8341")
    ap.add_argument("--variants", default="base,define,gray,order")
    a = ap.parse_args(argv)
    m = LocalVLM(a.qwen_url, "Qwen3-VL-8B-Instruct", "qwen8b")
    for ep in sorted(os.listdir(a.snaps)):
        for st in ("pre", "closed", "grasped", "miss"):
            sd = os.path.join(a.snaps, ep, st)
            if not os.path.isdir(sd):
                continue
            meta = json.load(open(os.path.join(sd, "meta.json")))
            for v in a.variants.split(","):
                text, ims = variant(sd, meta, v)
                rep = m.ask(text, ims, {"kind": "grasp_diag"})
                p, err = SC.validate("G", rep.text) if rep.text else (None, [str(rep.error)])
                row = {"snap": f"{ep}/{st}", "state": st, "gt_holding": meta["gt"]["holding"], "variant": v,
                       "answer": (p or {}).get("grasp_state"), "view": (p or {}).get("evidence_view"),
                       "evidence": (p or {}).get("evidence"), "valid": p is not None,
                       "prompt_id": PR.PROMPT_ID, "prompt_sha": hashlib.sha256(text.encode()).hexdigest()[:12]}
                with open(a.out, "a") as f:
                    f.write(json.dumps(row) + "\n")
    rows = [json.loads(x) for x in open(a.out)]
    for v in a.variants.split(","):
        R = [r for r in rows if r["variant"] == v]
        neg, pos = [r for r in R if not r["gt_holding"]], [r for r in R if r["gt_holding"]]
        print("DIAG " + json.dumps({"variant": v, "false_grasped": f"{sum(r['answer'] == 'grasped' for r in neg)}/"
                                                                  f"{len(neg)}",
                                    "missed": f"{sum(r['answer'] != 'grasped' for r in pos)}/{len(pos)}",
                                    "pre_false": f"{sum(r['answer'] == 'grasped' for r in neg if r['state'] == 'pre')}/"
                                                 f"{sum(r['state'] == 'pre' for r in neg)}"}), flush=True)


if __name__ == "__main__":
    main()
