"""Stage L8-D episodes with frames/ (video seeds) for tools/astra_solo/make_videos.py and write an index of their
scene parameters. usage: python videos.py <collect root> <stage dir> <videos root> [<max per bucket>]
Episodes with a frames/ folder under <collect root>/<split>/<vdir>/<task>_s<seed>/ are linked as
<stage>/<split>__<vdir>/x/y/s<seed> (make_videos' glob), then make_videos runs per split__vdir into <videos root>
(H.264 of the head | right-wrist jpgs + the per-call model view). <videos root>/scenes.json maps each video to its
table height, task, variant and distractor count."""
import glob
import json
import os
import subprocess
import sys

root, stage, vroot = sys.argv[1:4]
cap = int(sys.argv[4]) if len(sys.argv) > 4 else 99
os.makedirs(stage, exist_ok=True)
runs, scenes = {}, []
for fr in sorted(glob.glob(os.path.join(root, "*", "*", "*", "frames"))):
    ep = os.path.dirname(fr)
    split, vdir = ep.split(os.sep)[-3], ep.split(os.sep)[-2]
    if not os.path.exists(os.path.join(ep, "result.json")):
        continue
    run = f"{split}__{vdir}"
    if len(runs.get(run, [])) >= cap:
        continue
    seed = os.path.basename(ep).rsplit("_s", 1)[1]
    dst = os.path.join(stage, run, "x", "y", f"s{seed}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        os.symlink(ep, dst)
    runs.setdefault(run, []).append(ep)
    sc = json.load(open(os.path.join(ep, "scene.json")))
    m = json.load(open(os.path.join(ep, "meta.json")))
    scenes.append({"run": run, "episode": ep, "seed": int(seed), "task": sc["task"], "variant": sc["variant"],
                   "table_z": sc["table_z"], "lift": sc.get("lift"), "n_distractors": sc["distractors"]["n"],
                   "distractors": sc["distractors"], "success": m["success"], "style": m["style"]})
here = os.path.dirname(os.path.abspath(__file__))
mk = os.path.join(here, "..", "astra_solo", "make_videos.py")
for run in sorted(runs):
    subprocess.run([sys.executable, mk, os.path.join(vroot, run), f"{run}={os.path.join(stage, run)}"], check=True)
os.makedirs(vroot, exist_ok=True)
json.dump(scenes, open(os.path.join(vroot, "scenes.json"), "w"), indent=1)
print(json.dumps({"runs": {k: len(v) for k, v in runs.items()}, "episodes": len(scenes)}))
