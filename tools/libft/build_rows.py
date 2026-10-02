"""E-LIBFT: training rows from the oracle episodes (prereg_libft.md §2): successful demos only, held-out check passed,
first-attempt calls (prompt.txt + img1_head_camera.png + img2_right_wrist_camera.png + reply.txt) -> main35 row format
(kind control, format pt, prompt_path, images, answer); label parse check with the runtime parser.
usage: build_rows.py <data root> <out.jsonl>"""
import collections
import glob
import json
import os
import sys

from harvest.astra_solo import pt_schema as PS

root, out = sys.argv[1], sys.argv[2]
n_rows, per_task, dropped = 0, collections.Counter(), collections.Counter()
with open(out, "w") as f:
    for rp in sorted(glob.glob(os.path.join(root, "*", "t*", "demo_*", "row.json"))):
        r = json.load(open(rp))
        key = f"{r['suite']}/t{r['task']:02d}"
        if not r["success"]:
            dropped[key] += 1
            continue
        if r.get("held_min_maxabs") is not None and r["held_min_maxabs"] <= 1e-4:
            dropped[key + ":heldout"] += 1
            continue
        d = os.path.dirname(rp)
        for cd in sorted(glob.glob(os.path.join(d, "calls", "c*"))):
            imgs = [os.path.join(cd, "img1_head_camera.png"), os.path.join(cd, "img2_right_wrist_camera.png")]
            if not all(os.path.exists(p) for p in imgs):
                continue  # repair attempts carry no images
            ans = open(os.path.join(cd, "reply.txt"), encoding="utf-8").read()
            parsed, err = PS.validate(ans)
            if parsed is None:
                dropped["bad_label"] += 1
                continue
            f.write(json.dumps({"id": f"libft_{r['suite']}_t{r['task']:02d}_{r['demo']}_{os.path.basename(cd)}",
                                "kind": "control", "format": "pt", "prompt_path": os.path.join(cd, "prompt.txt"),
                                "images": imgs, "answer": ans, "suite": r["suite"], "task": r["task"],
                                "demo": r["demo"]}) + "\n")
            n_rows += 1
            per_task[key] += 1
json.dump({"rows": n_rows, "per_task": per_task, "dropped": dropped}, open(out + ".counts.json", "w"), indent=1)
print(f"rows {n_rows} tasks {len(per_task)} dropped_demos {sum(v for k, v in dropped.items() if ':' not in k and k != 'bad_label')}")
