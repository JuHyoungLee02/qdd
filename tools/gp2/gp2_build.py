"""E-GP2 early pilot data (prereg_gp2.md): L9 v2 successes -> d-min rows (harvest.l9.build9, ego only), held-out split by
task definition, and the two rotation-label arms that differ ONLY in the grasp rows' "rot" value and the GRASP block
wording of the request:
  a = rot_bin_img  (closing axis projected into the head image, 15 deg bins; the build9 default)
  b = rot_bin_base (the same pick's angle in the robot base frame, grasp9.rot_base)
usage (pod venv_train python, PYTHONPATH = code dir):
  gp2_build.py select <eps.json> <collect root>...           eligible episodes + split (sha256 of task_id)
  gp2_build.py rows <eps.json> <out dir> <train|eval> [--part k/n]
  gp2_build.py arms <out dir> <train|eval> <n parts>          merge parts -> l9_<split>_a.jsonl / _b.jsonl (+ truth)"""
import hashlib
import json
import os
import sys
from collections import Counter

ROBOTS = ("ffw_sg2", "franka_mast")  # build9.ROBOT_WORDS: the two robots the d-min request wording supports
HOLDOUT_MOD = 5  # task definitions with sha256("gp2:<task_id>") % 5 == 0 are held out (about 20 %)
ROT_BASE_TEXT = ("\"rot\": 0-11 = the direction of the line between the two finger pads in the robot base frame, in "
                 "15-degree steps (top approach: its yaw seen from above, 0 = the robot's forward x axis, increasing "
                 "towards the robot's left; other approaches: its angle about the approach direction, 0 = horizontal, "
                 "6 = vertical; 0-165 degrees because both pads look alike).\n\n")


def holdout(task_id: str) -> bool:
    return int(hashlib.sha256(f"gp2:{task_id}".encode()).hexdigest()[:8], 16) % HOLDOUT_MOD == 0


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def select(out, roots):
    import glob
    eps, c = {"train": [], "eval": []}, Counter()
    for root in roots:
        for m in sorted(glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)):
            try:
                d = json.load(open(m))
            except (OSError, ValueError):
                c["unreadable"] += 1
                continue
            if d.get("gen") != "l9" or d.get("grasp_v2") is None:
                continue
            c["v2_episodes"] += 1
            if not d.get("success"):
                continue
            c["success"] += 1
            if (d.get("max_dq_rad") or 0) > 0.04 or (d.get("robot") or "ffw_sg2") not in ROBOTS \
                    or d.get("task_id") == "gate_move":
                c["excluded_dq_robot_gate"] += 1
                continue
            s = "eval" if holdout(d["task_id"]) else "train"
            eps[s].append({"dir": os.path.dirname(m), "def": d["task_id"], "robot": d.get("robot") or "ffw_sg2",
                           "arm": d.get("arm"), "seed": d.get("seed")})
    seen = set()
    for s in ("train", "eval"):  # one episode folder name once (build9 row ids use the folder name)
        keep = []
        for e in eps[s]:
            k = os.path.basename(e["dir"])
            if k in seen:
                c["duplicate_name"] += 1
                continue
            seen.add(k)
            keep.append(e)
        eps[s] = keep
    info = dict(c, train=len(eps["train"]), eval=len(eps["eval"]),
                train_defs=len({e["def"] for e in eps["train"]}), eval_defs=len({e["def"] for e in eps["eval"]}),
                robots={s: dict(Counter(e["robot"] for e in eps[s])) for s in eps})
    assert not ({e["def"] for e in eps["train"]} & {e["def"] for e in eps["eval"]})
    json.dump(dict(eps, info=info), open(out, "w"), indent=0)
    print(json.dumps(info))


def rows(eps_path, out, split, part):
    from harvest.l9 import build9 as B9
    eps = json.load(open(eps_path))[split]
    name = f"l9_{split}"
    if part:
        k, n = (int(v) for v in part.split("/"))
        eps, name = eps[k::n], f"l9_{split}.part{k:02d}"
    c = B9.build([e["dir"] for e in eps], out, "l9" + split, name, train=(split == "train"), camera_line=False,
                 seed=0, grasp_format=True, external=False, slots=False, third_person=False)
    print(json.dumps({k: v for k, v in c.items() if k != "path"}))


def pick_for(row, picks):
    """The pick of this grasp row: same object, family and image bin as the label; None when absent or when the
    candidates disagree on the base bin (ambiguous)."""
    cmd = json.loads(row["answer"]).get("command") or {}
    if not isinstance(cmd.get("rot"), int):  # rot null (no image bin recorded for that pick): no label to compare
        return None
    cand = [p for p in picks if p.get("obj") == row.get("tgt") and p.get("family") == cmd.get("approach")
            and p.get("rot_bin_img") == cmd.get("rot") and p.get("rot_bin_base") is not None]
    if not cand or len({p["rot_bin_base"] for p in cand}) > 1:
        return None
    return cand[-1]


def arms(out, split, n):
    from harvest.l9 import build9 as B9
    allr = []
    for k in range(n):
        allr += [json.loads(x) for x in open(os.path.join(out, f"l9_{split}.part{k:02d}.jsonl"), encoding="utf-8")]
    metas, c = {}, Counter()
    pdir = os.path.join(out, "prompts_gp2b")
    os.makedirs(pdir, exist_ok=True)
    rot_img_txt = B9.GRASP_BLOCK[B9.GRASP_BLOCK.index("\"rot\": 0-11"):]
    block_b = B9.GRASP_BLOCK.replace(rot_img_txt, ROT_BASE_TEXT)
    ra, rb, truth = [], [], []
    for r in allr:
        if r.get("kind") != "control":
            ra.append(r)
            rb.append(r)
            continue
        cmd = {} if r.get("label_missing") else (json.loads(r["answer"]).get("command") or {})
        rr = r
        if "rot" in cmd:
            ep = os.path.dirname(os.path.dirname(r["call_dir"]))
            if ep not in metas:
                metas[ep] = json.load(open(os.path.join(ep, "meta.json")))
            p = pick_for(r, metas[ep]["grasp_v2"].get("picks") or [])
            if p is None:
                c["grasp_rows_unmatched_dropped"] += 1
                continue
            c["grasp_rows"] += 1
            d = json.loads(r["answer"])
            d["command"]["rot"] = int(p["rot_bin_base"])
            rr = dict(r, answer=json.dumps(d))
            truth.append({"id": r["id"], "episode": r["episode"], "step": r["step"], "robot": r.get("robot"),
                          "def": metas[ep].get("task_id"), "family": p["family"],
                          "rot_bin_img": p["rot_bin_img"], "rot_deg_img": p.get("rot_deg_img"),
                          "rot_bin_base": p["rot_bin_base"], "rot_deg_base": p.get("rot_deg_base"),
                          "instructed": bool(p.get("instructed_approach")), "point": cmd.get("point_2d")})
        t = open(r["prompt_path"], encoding="utf-8").read()
        if B9.GRASP_BLOCK in t:
            dst = os.path.join(pdir, hashlib.sha1(r["prompt_path"].encode()).hexdigest()[:20] + ".txt")
            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                f.write(t.replace(B9.GRASP_BLOCK, block_b))
            rr = dict(rr, prompt_path=dst)
            c["prompts_rewritten"] += 1
        ra.append(r)
        rb.append(rr)
    # the two arms: same ids in the same order; answers differ only in command.rot; prompts only in the GRASP block
    assert [x["id"] for x in ra] == [x["id"] for x in rb]
    for x, y in zip(ra, rb):
        if x.get("kind") == "control" and not x.get("label_missing"):
            dx, dy = json.loads(x["answer"]), json.loads(y["answer"])
            dx["command"].pop("rot", None)
            dy["command"].pop("rot", None)
            assert dx == dy, x["id"]
    res = {}
    for arm, rs in (("a", ra), ("b", rb)):
        p = os.path.join(out, f"l9_{split}_{arm}.jsonl")
        ctrl = [x for x in rs if x.get("kind") == "control"]
        aux = [x for x in rs if x.get("kind") != "control"]
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            for x in ctrl + aux:
                f.write(json.dumps(x) + "\n")
        res[arm] = {"path": p, "rows": len(rs), "control": len(ctrl), "aux": len(aux), "sha256": sha(p)}
    with open(os.path.join(out, f"truth_{split}.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for t in truth:
            f.write(json.dumps(t) + "\n")
    chk = B9.check_rows([x for x in ra if x.get("kind") == "control"], sample=3000)
    res.update(counts=dict(c), check_n=chk["n"], check_errors=chk["n_errors"],
               families=dict(Counter(t["family"] for t in truth)),
               steps=dict(Counter(t["step"] for t in truth)), robots=dict(Counter(t["robot"] for t in truth)))
    json.dump(res, open(os.path.join(out, f"arms_{split}.json"), "w"), indent=1)
    print(json.dumps(res))
    if chk["n_errors"]:
        sys.exit(3)


def main():
    a = sys.argv[1:]
    if a[0] == "select":
        select(a[1], a[2:])
    elif a[0] == "rows":
        part = a[a.index("--part") + 1] if "--part" in a else None
        rows(a[1], a[2], a[3], part)
    elif a[0] == "arms":
        arms(a[1], a[2], int(a[3]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
