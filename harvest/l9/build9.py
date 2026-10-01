"""L9 episodes -> d-min training / evaluation rows (all robots, both arms, head-camera geometry; prereg_hcam8 §2-3,
NOW: the next main training uses L8 + all of L9). Same row format as the L8S build (teach_pt.min_format.row / _aux):
  control rows: the call's astra-solo@v2 request -> d-min text (+ the `hand` field, teach_pt.min_format), the verified
                point label, L8 repeats; rows without a verified label are dropped (train) or kept flagged (eval)
  aux rows:     the depth-verified pointing QA on the ring head image; object names are read back from the call's
                own request (OBJECTS block, the run-time names of that episode), geometry from the L9 catalog
  every row:    robot (profile), head_cam (meta), camera (the `camera:` line made from that call's cams.json),
                source; camera_line=True also writes it into the request (prereg change 1 position)
check_rows() verifies rows against their episodes (robot / camera / hand / images) for any mix of robots."""
from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np

from . import hcam9 as HC

OBJ_HEAD = "OBJECTS ("
CAM_ANCHOR = "CAMERAS (directions are unit vectors in the robot frame)\n"
ROBOT_WORDS = {"ffw_sg2": "AI Worker FFW-SG2", "franka_mast": "Franka Emika Panda"}
_READY = {}


def prepare(splits=("train", "ood_o")) -> int:
    """Register every L9 catalog object (targets / clutter as meshes, containers with their spawn scale and inner
    floor) and the L9 spot / surface / support ids, as the collection processes do (pure; idempotent)."""
    from . import assets9 as A9
    from .world9 import register_l9_ids, register_pool
    n = 0
    for s in splits:
        if s in _READY:
            continue
        register_l9_ids()
        try:
            cat = A9.catalog(s)
        except (KeyError, FileNotFoundError):
            cat = {}
        register_pool(cat)
        _READY[s] = len(cat)
        n += len(cat)
    return n


def object_names(text: str) -> list:
    """Names of the OBJECTS block lines of a request, in order ('- name: description (role)')."""
    if OBJ_HEAD not in text:
        return []
    block = text.split(OBJ_HEAD, 1)[1].split("\n", 1)[1].split("\n\n", 1)[0]
    out = []
    for ln in block.split("\n"):
        if ln.startswith("- "):
            out.append(ln[2:].split(": ", 1)[0].split(" (", 1)[0])
    return out


def register_call_names(r: dict, text: str) -> bool:
    """Set prompt names of this call's objects from its own request (keys: tgt, place, then the other present
    objects in the state's order = the request's order). False when the counts disagree (aux skipped)."""
    from ..astra_motion import prompts as P
    keys = [r["tgt"], r["place"]] + [k for k in (r.get("gt") or {}).get("others", {}) if k not in (r["tgt"], r["place"])]
    names = object_names(text)
    if len(names) != len(keys):
        return False
    for k, n in zip(keys, names):
        P.OBJ_NAME[k] = n
    return True


def add_camera_line(text: str, line: str) -> str:
    if CAM_ANCHOR not in text:
        raise ValueError("no CAMERAS header")
    if "\n- camera: head" in text:
        return text
    return text.replace(CAM_ANCHOR, CAM_ANCHOR + "- " + line + "\n", 1)


def camera_of(r: dict, robot: str) -> str:
    cam = json.load(open(r["cams_path"]))["head"]
    return HC.line(cam, f"l9/{robot}")


def episode_rows(ep_dir: str, out_dir: str, split: str, train: bool, rng, camera_line: bool = False) -> tuple:
    """-> (control rows, aux rows, counts) of one L9 episode."""
    from ..teach_l8.dataset import repeat_of
    from ..teach_pt import dataset as DS
    from ..teach_pt import min_format as MF
    meta = json.load(open(os.path.join(ep_dir, "meta.json")))
    robot = meta.get("robot") or "ffw_sg2"
    hc = meta.get("head_cam") or {"mode": "std"}
    ctrl, aux, c = [], [], Counter()
    for r in DS.load_rows(ep_dir, split):
        c["states"] += 1
        v2 = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
        named = register_call_names(r, v2)
        c["names_ok" if named else "names_mismatch"] += 1
        x = MF.row(r, out_dir, "d-min", "clean")
        if train and x["label_missing"]:
            c["label_missing_dropped"] += 1
            continue
        line = camera_of(r, robot)
        x.update(robot=robot, head_cam_mode=(hc.get("draw") or {}).get("mode", hc.get("mode", "std")), camera=line,
                 source=f"l9/{robot}", gen="l9")
        if camera_line:
            p = x["prompt_path"]
            dst = p[:-4] + "_cam.txt"
            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                f.write(add_camera_line(open(p, encoding="utf-8").read(), line))
            x.update(prompt_path=dst, camera_line=True)
        ctrl += [x] * (repeat_of(x) if train else 1)
        if train and named:
            a = MF._aux(x, "d-min", rng)
            if a is not None:
                aux.append(dict(a, robot=robot, source=f"l9/{robot}", gen="l9"))
    return ctrl, aux, c


def build(ep_dirs, out_dir: str, split: str, name: str, train: bool = True, camera_line: bool = False,
          seed: int = 0) -> dict:
    prepare(("train", "ood_o"))
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng([seed, 9, 29])
    ctrl, aux, c = [], [], Counter()
    for d in ep_dirs:
        a, b, k = episode_rows(d, out_dir, split, train, rng, camera_line)
        ctrl += a
        aux += b
        c.update(k)
    path = os.path.join(out_dir, name + ".jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for x in ctrl + aux:
            f.write(json.dumps(x) + "\n")
    counts = dict(c, episodes=len(ep_dirs), control_rows=len(ctrl), aux_rows=len(aux),
                  robots=dict(Counter(x["robot"] for x in ctrl)), head_cam=dict(Counter(x["head_cam_mode"] for x in ctrl)),
                  hands=dict(Counter(x.get("hand", "right") for x in ctrl)))
    json.dump(counts, open(os.path.join(out_dir, name + ".counts.json"), "w"), indent=1)
    return dict(counts, path=path)


def check_rows(rows, camera_line: bool = False, sample: int | None = None, seed: int = 0) -> dict:
    """Every L9 control row: robot = its episode meta's robot; the request names that robot (and not the other);
    `camera` = the line rebuilt from its call's cams.json; with camera_line the request carries exactly that line;
    the answer's hand = the episode arm; images exist. -> {"n", "errors": [...first 20], "by_robot"}."""
    rng = np.random.default_rng(seed)
    ctrl = [r for r in rows if r.get("kind") == "control" and r.get("gen") == "l9"]
    if sample and len(ctrl) > sample:
        ctrl = [ctrl[i] for i in sorted(rng.choice(len(ctrl), sample, replace=False))]
    errs, by = [], Counter()
    for r in ctrl:
        ep = os.path.dirname(os.path.dirname(r["call_dir"]))
        meta = json.load(open(os.path.join(ep, "meta.json")))
        robot = meta.get("robot") or "ffw_sg2"
        by[robot] += 1
        text = open(r["prompt_path"], encoding="utf-8").read()
        line = camera_of(r, robot)
        bad = []
        if r.get("robot") != robot:
            bad.append(f"robot {r.get('robot')} != meta {robot}")
        if ROBOT_WORDS[robot] not in text or any(w in text for k, w in ROBOT_WORDS.items() if k != robot):
            bad.append("request robot wording")
        if r.get("camera") != line:
            bad.append("camera field != cams.json line")
        if camera_line and ("- " + line) not in text:
            bad.append("camera line missing in the request")
        if not camera_line and "\n- camera: head" in text:
            bad.append("camera line present in a no-line build")
        hand = (json.loads(r["answer"]).get("command") or {}).get("hand") if not r.get("label_missing") else None
        if hand is not None and hand != meta.get("arm"):
            bad.append(f"hand {hand} != arm {meta.get('arm')}")
        for p in r["images"]:
            if not os.path.exists(p):
                bad.append(f"missing image {os.path.basename(p)}")
        if bad:
            errs.append({"id": r["id"], "errors": bad})
    return {"n": len(ctrl), "n_errors": len(errs), "errors": errs[:20], "by_robot": dict(by)}
