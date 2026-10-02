"""E-GP2 follow-up (main 10-03, L8-X collapse): the L8-X rows re-prompted in the L9 v2 request format (robot line +
GRASP block, harvest.l9.build9.add_grasp_format; images and labels unchanged) so an L9-trained model can be scored on
them in its own format. New prompt files only (the source files are never modified).
usage (pod python, PYTHONPATH = code dir): gp2_l8x_reprompt.py <src.jsonl> <out dir> <name>"""
import hashlib
import json
import os
import sys


def main():
    src, out, name = sys.argv[1:4]
    from harvest.l9 import build9 as B9
    pd = os.path.join(out, f"prompts_{name}")
    os.makedirs(pd, exist_ok=True)
    n, rows = 0, []
    for x in open(src, encoding="utf-8"):
        r = json.loads(x)
        if r.get("kind", "control") == "control" and r.get("prompt_path"):
            hand = (json.loads(r["answer"]).get("command") or {}).get("hand") or "right"
            rl = f"robot: ffw_sg2, arm {hand} 7-DoF, parallel gripper max 10.7 cm"
            t = B9.add_grasp_format(open(r["prompt_path"], encoding="utf-8").read(), rl)
            dst = os.path.join(pd, hashlib.sha1(r["prompt_path"].encode()).hexdigest()[:20] + ".txt")
            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                f.write(t)
            r = dict(r, prompt_path=dst)
            n += B9.GRASP_BLOCK in t and "- robot: " in t
        rows.append(r)
    p = os.path.join(out, f"{name}.jsonl")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(json.dumps({"rows": len(rows), "reprompted_with_robot_and_grasp": n, "out": p}))


if __name__ == "__main__":
    main()
