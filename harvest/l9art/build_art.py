"""L9art episodes -> training / evaluation rows, same row schema as the L9 build (harvest.l9.build9): each call of
labels.jsonl becomes one control row {id, kind:"control", prompt_path, images [ring head, wrist], answer, label_missing,
robot, camera, source, gen, gen_version, skill, split, episode, success}. No depth / aux rows (format v3 has none yet);
harvest.l9 is read-only (only hcam9.line is reused for the camera field, exactly as harvest.l9.build9.camera_of does).

Train builds (train=True): episodes with meta.success != True are dropped whole, and any remaining row whose label is
missing is dropped too. Eval builds (train=False) keep every call of every episode, flags included, for scoring."""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter

from ..l9 import hcam9 as HC

ROW_ID_PREFIX = "l9art"


def row_id(ep_name: str, call: int) -> str:
    return f"{ROW_ID_PREFIX}_{ep_name}_c{call:03d}"


def label_missing_of(r: dict) -> bool:
    """True when the labels.jsonl row's command is a point command missing its target pixel, or (sub == "move",
    where every stage kind always sets point2) missing the end pixel."""
    cmd = r.get("command") or {}
    if cmd.get("mode") != "point" or cmd.get("height") == "lift":  # lift: no point by design
        return False
    if cmd.get("point_2d") is None or (r.get("occ") is True and r.get("sub") in ("start", "above")):  # target hidden
        # before the hand reaches it (depth check); near / holding it the own fingers hide it by nature: kept
        return True
    return r.get("sub") == "move" and cmd.get("point2") is None


OLD_P2 = ("- point2 = [x, y] in image 1 (0-1000): where the pointed contact (handle, pushed spot, the knob's white mark, the "
          "pushed object's centre) should END. Give it only with the move along the joint / the push / the turn; the code "
          "snaps it onto the part's joint (axis, distance and angle come from point and point2).")
OLD_FMT = '''"point2": [x, y] (moves along a joint / pushes / turns only), "height"'''


def upgrade_prompt(text: str) -> str:
    """Requests stored before art2 (no joint-axis fields) -> the art2 wording (prompts_art), so all rows share it."""
    from . import prompts_art as PA
    new_p2 = PA.ART_BLOCK.split("- point2 = ", 1)[1].split("\n- press:", 1)[0]
    text = text.replace(OLD_P2, "- point2 = " + new_p2)
    fmt = PA.ANSWER.split('"point2": ', 1)[1].split(', "height"', 1)[0]
    return text.replace(OLD_FMT, '"point2": ' + fmt + ', "height"')


class _Cam:
    def __init__(self, d):
        import numpy as np
        self.W, self.H, self.fx, self.fy, self.cx, self.cy = (d[k] for k in ("W", "H", "fx", "fy", "cx", "cy"))
        self.R, self.t = np.asarray(d["R"], float), np.asarray(d["t"], float)


def backfill_axis(r: dict, meta: dict, cams: dict):
    """Older rows (before art2): add axis / pivot_2d / turn / amount to a joint move's command from the episode's
    fixture (spec re-made from family + seed, fx2) and that call's head camera. -> (answer, ok)."""
    import numpy as np
    from . import fixtures as FX
    from . import skills as SK
    cmd = r.get("command") or {}
    if r.get("sub") != "move" or cmd.get("skill") not in ("pull_axis", "push_axis", "rotate") or "axis" in cmd:
        return r["answer"], True
    fx = meta.get("fixture") or {}
    if not fx or fx.get("version", "l9art-fx2") != "l9art-fx2":
        return r["answer"], False
    spec = FX.sample(fx["family"], int(fx["seed"]))
    st = (meta.get("prog") or {}).get("stages", [])[int(r.get("stage") or 0)]
    T = np.asarray(fx["pose"]["T"], float)
    extra = SK.axis_fields(_Cam(cams["head"]), spec, st["link"], T, r.get("joints") or {}, float(st["goal"]))
    a = json.loads(r["answer"])
    a["command"].update(extra)
    return json.dumps(a), extra.get("axis") == "linear" or extra.get("pivot_2d") is not None


def _copy_prompt(src: str, dst: str) -> None:
    text = upgrade_prompt(open(src, encoding="utf-8").read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def episode_rows(ep_dir: str, out_dir: str, split: str, train: bool) -> tuple:
    """-> (control rows, counts) of one l9art episode folder. Episodes without meta.json / labels.jsonl (fully
    skipped rows) contribute nothing."""
    c = Counter()
    meta_path = os.path.join(ep_dir, "meta.json")
    labels_path = os.path.join(ep_dir, "labels.jsonl")
    if not (os.path.exists(meta_path) and os.path.exists(labels_path)):
        c["episode_skipped"] += 1
        return [], c
    meta = json.load(open(meta_path))
    robot = meta.get("robot") or "ffw_sg2"
    success = bool(meta.get("success"))
    ep_name = os.path.basename(ep_dir)
    if train and not success:
        c["episode_failed_dropped"] += 1
        return [], c
    if train and float(meta.get("max_dq_rad") or 0.0) > 0.04:  # measured joint jump (contact): not a training episode
        c["episode_jump_dropped"] += 1
        return [], c
    out = []
    for line in open(labels_path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        c["states"] += 1
        call = int(r["call"])
        call_dir = os.path.join(ep_dir, "calls", f"c{call:03d}")
        missing = label_missing_of(r)
        if train and missing:
            c["label_missing_dropped"] += 1
            continue
        cams = json.load(open(os.path.join(call_dir, "cams.json")))
        answer, ok_axis = backfill_axis(r, meta, cams)
        if not ok_axis:
            missing = True
            if train:
                c["axis_missing_dropped"] += 1
                continue
        camera = HC.line(cams["head"], f"l9art/{robot}")
        rid = row_id(ep_name, call)
        dst_prompt = os.path.join(out_dir, "prompts_art", rid + ".txt")
        _copy_prompt(os.path.join(call_dir, "prompt_v3.txt"), dst_prompt)
        images = [os.path.join(call_dir, "img1_head_ring.png"), os.path.join(call_dir, "img2_right_wrist_camera.png")]
        from ..l9.views9 import native_slots  # r2-cams: no wrist image for a robot without native wrist cameras (G1)
        if not {"wrist_left", "wrist_right"} & set(native_slots(robot)) or not os.path.exists(images[1]):
            images = images[:1]
        out.append({"id": rid, "kind": "control", "prompt_path": dst_prompt, "images": images,
                    "answer": answer, "label_missing": missing, "robot": robot, "camera": camera,
                    "source": f"l9art/{robot}", "gen": "l9art", "gen_version": "v3", "skill": r.get("skill"),
                    "split": split, "episode": ep_name, "success": success})
        c["rows"] += 1
    return out, c


def build(ep_dirs, out_dir: str, split: str, name: str, train: bool = True) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rows, c = [], Counter()
    for d in ep_dirs:
        a, k = episode_rows(d, out_dir, split, train)
        rows += a
        c.update(k)
    path = os.path.join(out_dir, name + ".jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for x in rows:
            f.write(json.dumps(x) + "\n")
    counts = dict(c, episodes=len(ep_dirs), control_rows=len(rows),
                  robots=dict(Counter(x["robot"] for x in rows)),
                  skills=dict(Counter(x["skill"] for x in rows)),
                  label_missing=sum(1 for x in rows if x["label_missing"]))
    json.dump(counts, open(os.path.join(out_dir, name + ".counts.json"), "w"), indent=1)
    return dict(counts, path=path)


def check_rows(rows) -> dict:
    """Every control row of this build: prompt / images exist, the answer parses as JSON, and (when its command is a
    point command) command.command.skill is one of harvest.l9art.tasks.SKILLS. -> {"n", "n_errors", "errors"}."""
    from . import tasks as TK
    errs = []
    for r in rows:
        bad = []
        for p in [r["prompt_path"]] + list(r["images"]):
            if not os.path.exists(p):
                bad.append(f"missing {os.path.basename(p)}")
        try:
            d = json.loads(r["answer"])
        except (TypeError, json.JSONDecodeError):
            bad.append("answer not JSON")
        else:
            cmd = d.get("command") or {}
            if cmd.get("mode") == "point" and cmd.get("skill") not in TK.SKILLS:
                bad.append(f"bad skill {cmd.get('skill')!r}")
        if bad:
            errs.append({"id": r["id"], "errors": bad})
    return {"n": len(rows), "n_errors": len(errs), "errors": errs[:20]}


def find_episode_dirs(root: str, split: str) -> list:
    return sorted(os.path.dirname(p) for p in glob.glob(os.path.join(root, split, "**", "meta.json"), recursive=True))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="collect root (holds <split>/<def>/<def>_s<seed>_<arm>/...)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--name", default="train_art")
    ap.add_argument("--eval", action="store_true", help="keep every row (flagged), instead of the train filter")
    a = ap.parse_args(argv)
    ep_dirs = find_episode_dirs(a.root, a.split)
    res = build(ep_dirs, a.out, a.split, a.name, train=not a.eval)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
