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
# L9 v2 output format (spec §12.8, research grasp_point_learning §11.7): grasp calls add approach + rot; the request
# gets a robot line and this block. Final wording after E-GP2 (main).
GRASP_BLOCK = ("GRASP (only when the gripper closes on an object): point at the visible part of the object where the "
               "fingers will close, and also give \"approach\": top | oblique | front | side (robot base frame: top = "
               "straight down, oblique = down at an angle, front = horizontally away from the robot, side = "
               "horizontally from the left or the right) and \"rot\": 0-11 = the direction of the line between the "
               "two finger pads as seen in image 1, in 15-degree steps (0 = image horizontal, increasing clockwise, "
               "0-165 degrees because both pads look alike).\n\n")
ROBOT_ANCHOR = CAM_ANCHOR


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


def robot_line(meta: dict) -> str:
    """'robot: <profile>, arm <arm> 7-DoF, parallel gripper max <cm> cm' from the episode meta (spec §12.8)."""
    gv = meta.get("grasp_v2") or {}
    g = gv.get("gripper") or {}
    w = g.get("max_open")
    w = f"{float(w) * 100:.1f}" if w else "?"
    return f"robot: {meta.get('robot') or 'ffw_sg2'}, arm {meta.get('arm', 'right')} 7-DoF, parallel gripper max {w} cm"


def add_grasp_format(text: str, rline: str) -> str:
    """The v2 request: the robot line above the CAMERAS block and the GRASP block before FRAME AND UNITS (or at the
    end of the static part)."""
    if "\n- robot: " not in text and ROBOT_ANCHOR in text:
        text = text.replace(ROBOT_ANCHOR, "ROBOT\n- " + rline + "\n\n" + ROBOT_ANCHOR, 1)
    if GRASP_BLOCK not in text:
        k = text.find("FRAME AND UNITS")
        text = text[:k] + GRASP_BLOCK + text[k:] if k >= 0 else text + "\n" + GRASP_BLOCK
    return text


def strip_grasp_fields(answer: str) -> str:
    d = json.loads(answer)
    c = d.get("command") or {}
    for k in ("approach", "rot"):
        c.pop(k, None)
    return json.dumps(d)


def camera_of(r: dict, robot: str) -> str:
    cam = json.load(open(r["cams_path"]))["head"]
    return HC.line(cam, f"l9/{robot}")


def external_rows(r: dict, x: dict, base_prompt: str, robot: str, out_dir: str) -> tuple:
    """Paired external-view control rows of one head row x (ext9): same state, same answer except point_2d = the
    head label's 3D point (head depth) projected into the external camera, kept only when the external depth shows
    it. Image 1 = the external image with the TCP ring, image 2 = the same wrist image; the request names the
    external camera (Image 1 line + `camera: external` line). -> (rows, Counter)."""
    from ..astra_motion.geometry import Cam
    from ..astra_solo import nd as ND
    from ..astra_solo.overlay import png_bytes
    from . import ext9 as E9
    from . import tp9
    c = Counter()
    cams = json.load(open(r["cams_path"]))
    ed_dir, ext_cams = tp9.external_cams(r["call_dir"])  # third-person tree (legacy: the ego call dir)
    cams.update(ext_cams)
    keys = sorted(ext_cams)
    c["third_person_views"] += len(keys)
    if not keys or x.get("label_missing"):
        return [], c
    head = cams["head"]
    cmd = json.loads(x["answer"]).get("command") or {}
    hd = np.load(r["depth_path"])["depth"] if cmd.get("point_2d") is not None else None
    text0 = open(base_prompt, encoding="utf-8").read()
    out = []
    for k in keys:
        ext = cams[k]
        ed = E9.load_depth(os.path.join(ed_dir, f"{k}_depth.npz"))
        pt, rot = None, None
        if cmd.get("rot") is not None:  # format v2: the closing-axis angle as seen by this camera (ext_save)
            rot = (ext.get("grasp_rot") or {}).get("rot_bin_img")
            if rot is None:
                c["external_no_rot"] += 1
                continue
        if cmd.get("point_2d") is not None:
            pt, info = E9.external_point(head, hd, cmd["point_2d"], ext, ed)
            if pt is None:
                c[f"external_{info['why']}"] += 1
                continue
        from PIL import Image
        rgb = np.asarray(Image.open(os.path.join(ed_dir, f"img1_{k}.png")).convert("RGB"))
        ring, drawn = ND.ring_overlay(rgb, Cam.from_json(ext), r["gt"]["tcp"])
        rid = f"{x['id']}_ext{k[len('external'):]}"
        ip = os.path.join(out_dir, "external_img", f"{rid}.png")
        os.makedirs(os.path.dirname(ip), exist_ok=True)
        with open(ip, "wb") as f:
            f.write(png_bytes(ring))
        line = E9.line(ext, f"l9/{robot}")
        pp = os.path.join(out_dir, "prompts_min", "d_ext", rid + ".txt")
        os.makedirs(os.path.dirname(pp), exist_ok=True)
        with open(pp, "w", encoding="utf-8", newline="\n") as f:
            f.write(add_camera_line(E9.external_text(text0, ext, "tcp" in drawn), line))
        out.append(dict(x, id=rid, view="external", external_cam=k, pair_of=x["id"], pair_id=ext.get("pair"),
                        camera=line, camera_line=True, prompt_path=pp, images=[ip] + list(x["images"][1:]),
                        answer=E9.external_answer(x["answer"], pt, rot),
                        depth_path=os.path.join(ed_dir, f"{k}_depth.npz")))
        c["external_rows"] += 1
    return out, c


def slot_rows(r: dict, x: dict, meta: dict, robot: str, seed: int, third_person: bool) -> tuple:
    """The 4-slot schema (views9) of one ego row x: (ego row, [third-person variant]) -- user 10-02."""
    from . import tp9
    from . import views9 as V
    arm = meta.get("arm") or "right"
    cams = json.load(open(r["cams_path"]))
    used = (x["images"][1], cams.get("wrist")) if len(x["images"]) > 1 and cams.get("wrist") else None
    op = os.path.join(r["call_dir"], "img3_wrist_other.png")
    other = (op, cams["wrist_other"]) if cams.get("wrist_other") and os.path.exists(op) else None
    text = open(x["prompt_path"], encoding="utf-8").read()
    src = f"l9/{robot}"

    def one(third, tag):
        res = V.canonical(text, x["answer"], arm, x["images"][0], used, other, third, V.row_rng(x["id"], seed),
                          source=src, anchor=CAM_ANCHOR)
        pp = x["prompt_path"][:-4] + f"_{tag}.txt"
        with open(pp, "w", encoding="utf-8", newline="\n") as f:
            f.write(res["text"])
        return dict(x, prompt_path=pp, images=res["images"], answer=res["answer"], image_views=res["image_views"],
                    slots=res["slots"], arm=arm)
    ego = one(None, "slots")
    tps = []
    if third_person and not x.get("label_missing"):
        d, ext = tp9.external_cams(r["call_dir"])
        for k in sorted(ext)[:1]:  # one third-person view per row
            ip = os.path.join(d, f"img1_{k}.png")
            if os.path.exists(ip):
                tps.append(dict(one((ip, ext[k]), "slots_tp"), id=x["id"] + "_tp", third_person=True,
                                third_person_cam=k))
    return ego, tps


def episode_rows(ep_dir: str, out_dir: str, split: str, train: bool, rng, camera_line: bool = False,
                 grasp_format: bool = True, external: bool = False, slots: bool = False,
                 third_person: bool = False, seed: int = 0) -> tuple:
    """-> (control rows, aux rows, counts) of one L9 episode. external=True adds the paired external-view rows of
    paired episodes (ext9; default off = the head-only build, unchanged)."""
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
        if meta.get("grasp_v2") is not None:  # spec §12.8 format v2 (grasp_format=False: the old point format)
            rl = robot_line(meta)
            x.update(robot_line=rl, gen_version="v2", label_origin=meta.get("label_origin", "l9v2"))
            p = x["prompt_path"]
            if grasp_format:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(add_grasp_format(open(p, encoding="utf-8").read(), rl))
            elif not x["label_missing"]:
                x["answer"] = strip_grasp_fields(x["answer"])
        ext_rows = []
        if external and meta.get("external_cams"):
            ext_rows, ce = external_rows(r, x, x["prompt_path"], robot, out_dir)
            c.update(ce)
        if camera_line:
            p = x["prompt_path"]
            dst = p[:-4] + "_cam.txt"
            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                f.write(add_camera_line(open(p, encoding="utf-8").read(), line))
            x.update(prompt_path=dst, camera_line=True)
        if slots:  # 4-slot camera schema (views9); third-person variants go to the third-person shard
            x, tp_rows = slot_rows(r, x, meta, robot, seed, third_person)
            ext_rows += tp_rows
            c["third_person_slot_rows"] += len(tp_rows)
        ctrl += [x] * (repeat_of(x) if train else 1)
        for e in ext_rows:  # right after their head row, same repeats
            ctrl += [e] * (repeat_of(x) if train else 1)
        if train and named:
            a = MF._aux(x, "d-min", rng)
            if a is not None:
                aux.append(dict(a, robot=robot, source=f"l9/{robot}", gen="l9"))
    return ctrl, aux, c


def build(ep_dirs, out_dir: str, split: str, name: str, train: bool = True, camera_line: bool = False,
          seed: int = 0, grasp_format: bool = True, external: bool = False, slots: bool = False,
          third_person: bool = False) -> dict:
    """external=True (--third-person on): + the paired external-view rows, written to their own shard
    <name>_third_person.jsonl (user 10-02: the ego shard <name>.jsonl never holds third-person rows; off = 0 of them)."""
    prepare(("train", "ood_o"))
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng([seed, 9, 29])
    ctrl, aux, c = [], [], Counter()
    for d in ep_dirs:
        a, b, k = episode_rows(d, out_dir, split, train, rng, camera_line, grasp_format, external, slots,
                               third_person, seed)
        ctrl += a
        aux += b
        c.update(k)
    is_tp = (lambda x: x.get("view") == "external" or bool(x.get("third_person")))  # noqa: E731
    tp = [x for x in ctrl if is_tp(x)]
    ctrl = [x for x in ctrl if not is_tp(x)]
    path = os.path.join(out_dir, name + ".jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for x in ctrl + aux:
            f.write(json.dumps(x) + "\n")
    if external or third_person:
        with open(os.path.join(out_dir, name + "_third_person.jsonl"), "w", encoding="utf-8", newline="\n") as f:
            for x in tp:
                f.write(json.dumps(x) + "\n")
    counts = dict(c, episodes=len(ep_dirs), control_rows=len(ctrl), aux_rows=len(aux),
                  robots=dict(Counter(x["robot"] for x in ctrl)), head_cam=dict(Counter(x["head_cam_mode"] for x in ctrl)),
                  hands=dict(Counter(x.get("hand", "right") for x in ctrl)))
    counts["third_person_rows"] = len(tp)
    if slots:
        counts["image_count_hist"] = dict(Counter(len(x["images"]) for x in ctrl + tp))
        counts["slot_combos"] = dict(Counter("+".join(x["image_views"]) for x in ctrl + tp))
        counts["rows_without_head"] = sum(1 for x in ctrl + tp if (x.get("image_views") or ["?"])[0] != "head")
    if external:
        counts["views"] = dict(Counter(x.get("view", "head") for x in ctrl + tp))
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
        ext = r.get("view") == "external"
        if ext:  # paired external row (ext9): its own camera's line, always in the request, no head wording
            from . import ext9 as E9
            line = E9.line(json.load(open(r["cams_path"]))[r["external_cam"]], f"l9/{robot}")
        else:
            line = camera_of(r, robot)
        bad = []
        if r.get("robot") != robot:
            bad.append(f"robot {r.get('robot')} != meta {robot}")
        if ROBOT_WORDS[robot] not in text or any(w in text for k, w in ROBOT_WORDS.items() if k != robot):
            bad.append("request robot wording")
        if r.get("camera") != line:
            bad.append("camera field != cams.json line")
        if (camera_line or ext) and ("- " + line) not in text:
            bad.append("camera line missing in the request")
        if not camera_line and "\n- camera: head" in text:
            bad.append("camera line present in a no-line build")
        if ext and ("head camera" in text or "- Image 1: external camera" not in text):
            bad.append("external row names the head camera")
        hand = (json.loads(r["answer"]).get("command") or {}).get("hand") if not r.get("label_missing") else None
        if hand is not None and hand != meta.get("arm"):
            bad.append(f"hand {hand} != arm {meta.get('arm')}")
        for p in r["images"]:
            if not os.path.exists(p):
                bad.append(f"missing image {os.path.basename(p)}")
        if bad:
            errs.append({"id": r["id"], "errors": bad})
    return {"n": len(ctrl), "n_errors": len(errs), "errors": errs[:20], "by_robot": dict(by)}
