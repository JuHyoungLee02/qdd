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

# Episode-level filters (user 10-03), applied by build() before any row is made, for every build (current and
# L9v2-general) and whatever head camera the episode drew (each call's own live "occ" in labels.jsonl).
# (1) key-call occlusion: an episode whose KEY call (approach = above_target, grasp = descend_close, place =
#     lower_open) has its pointed-at object (target while approaching / grasping, else the place) >= OCC_MAX hidden
#     in the head image is dropped WHOLE -- otherwise the VLM learns to move without seeing the key step. Same
#     measure / threshold as the per-call gate (visgate9.OCC_MAX on labels.jsonl "occ", teach_l8d.collect._occ).
#     Robots: KEY_OCC_ROBOTS (user order names the Franka; the rule itself is robot-agnostic).
# (2) arm balance: per robot with both arms present, the majority arm is thinned to the minority arm's count
#     (definitions where that arm leads most first, so per-definition balance improves too); the shortfall is what
#     the auto top-up must add on the minority arm (capfilter9 --arm-need).
KEY_STEPS = {"above_target": "approach", "descend_close": "grasp", "lower_open": "place"}
KEY_OCC_ROBOTS = ("franka_mast",)


def key_occlusion(ep_dir: str, occ_max: float | None = None) -> dict | None:
    """First key call of the episode whose pointed-at object is >= occ_max occluded in the head image, as
    {"call", "step", "key", "occ"}; None = the episode keeps (key calls without a measured occ are not judged)."""
    from . import visgate9 as VG
    occ_max = VG.OCC_MAX if occ_max is None else float(occ_max)
    p = os.path.join(ep_dir, "labels.jsonl")
    if not os.path.exists(p):
        return None
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        if r.get("step") in KEY_STEPS and r.get("occ") is not None and float(r["occ"]) >= occ_max:
            return {"call": r.get("call"), "step": r["step"], "key": KEY_STEPS[r["step"]], "occ": float(r["occ"])}
    return None


def episode_filter(ep_dirs, key_occ_robots=KEY_OCC_ROBOTS, arm_balance: bool = True) -> tuple:
    """-> (kept episode dirs, report). report["robots"][robot] = {"raw": {arm: n}, "after_occ": {...},
    "after_balance": {...}, "need": {arm: shortfall}}, report["key_occ"] = {robot: {key: n}}."""
    import hashlib
    metas = []
    for d in ep_dirs:
        m = json.load(open(os.path.join(d, "meta.json")))
        metas.append((d, m.get("robot") or "ffw_sg2", m.get("arm") or "right", m.get("task_id")))
    rep = {"robots": {}, "key_occ": {}}
    kept = []
    for d, rb, arm, td in metas:
        st = rep["robots"].setdefault(rb, {"raw": Counter(), "after_occ": Counter()})
        st["raw"][arm] += 1
        if rb in key_occ_robots:
            k = key_occlusion(d)
            if k is not None:
                rep["key_occ"].setdefault(rb, Counter())[k["key"]] += 1
                continue
        st["after_occ"][arm] += 1
        kept.append((d, rb, arm, td))
    drop = set()
    for rb, st in rep["robots"].items():
        n = st["after_occ"]
        need = Counter()
        if arm_balance and n["left"] > 0 and n["right"] > 0 and n["left"] != n["right"]:
            maj, mnr = ("left", "right") if n["left"] > n["right"] else ("right", "left")
            surplus = n[maj] - n[mnr]
            need[mnr] = surplus
            by_def = {}
            for d, r_, a_, td in kept:
                if r_ == rb:
                    by_def.setdefault((a_, td), []).append(d)
            for v in by_def.values():  # deterministic thinning order (path hash), stable across builds
                v.sort(key=lambda p: hashlib.sha1(p.encode()).hexdigest())
            for _ in range(surplus):
                tds = {td for (a_, td) in by_def if a_ == maj and by_def[(a_, td)]}
                td = max(sorted(tds, key=str), key=lambda t: len(by_def[(maj, t)]) - len(by_def.get((mnr, t), [])))
                drop.add(by_def[(maj, td)].pop())
        st["after_balance"] = Counter(a_ for d, r_, a_, td in kept if r_ == rb and d not in drop)
        st["need"] = need
    rep["robots"] = {rb: {k: dict(v) for k, v in st.items()} for rb, st in rep["robots"].items()}
    rep["key_occ"] = {rb: dict(v) for rb, v in rep["key_occ"].items()}
    return [d for d, r_, a_, td in kept if d not in drop], rep


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


def _vis_point(r: dict) -> tuple:
    """(role, OBJ_GEOM record, centre) of the ONE object this call's step actually points at -- owner order 10-03,
    same convention as teach_l8d.collect._occ: "approach" (not yet holding the target) -> tgt; every other phase
    (carrying / lowering / releasing -- the target is in hand) -> place. The held object is never checked (it is
    not what the row's command points at)."""
    from ..sim.scene import OBJ_GEOM
    role = "tgt" if r.get("phase") == "approach" else "place"
    key = r[role]
    return role, OBJ_GEOM.get(key) or {}, r["gt"][role]


def _vis_gate(cam_json: dict, depth, r: dict, use_occ: bool = False) -> tuple:
    """(ok, reason) of one rendered view (its cams.json camera entry + depth array) for this call's ONE pointed-at
    object (_vis_point; owner order 10-02/10-03: the VLM must never be asked to point at something it cannot see,
    and only the row's own point is checked). reason = "<role>:<why>" ("tgt:out_of_frame" / "too_small" /
    "occluded") when dropped, else None. use_occ=True (the head view only): reuse labels.jsonl's own "occ" (live
    env, the real container yaw -- collect.py's _occ) instead of the build-time depth / footprint_r approximation,
    when present."""
    from ..astra_motion.geometry import Cam
    from . import visgate9 as VG
    role, geom, centre = _vis_point(r)
    occ = r.get("occ") if use_occ else None
    point = (role, geom, centre) if occ is None else (role, geom, centre, float(occ))
    ok, reason, role = VG.row_visible(Cam.from_json(cam_json), depth, [point])
    return ok, (None if ok else f"{role}:{reason}")


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
        ok, reason = _vis_gate(ext, ed, r)
        if not ok:
            c[f"vis_drop_ext_{reason}"] += 1
            continue
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


def extra_views(r: dict) -> list:
    """r2-cams: the call's further native cameras, cams.json "extra_views" = {view name (views9.EXTRA_VIEWS): camera
    record + "img" (file name in the call dir)}, in views9.EXTRA_VIEWS order, only those whose image exists ->
    [(name, image path, record)]. No entry (every episode so far) -> []."""
    from . import views9 as V
    ex = json.load(open(r["cams_path"])).get("extra_views") or {}
    out = []
    for name in V.EXTRA_VIEWS:
        rec = ex.get(name)
        if rec and rec.get("img") and os.path.exists(os.path.join(r["call_dir"], rec["img"])):
            out.append((name, os.path.join(r["call_dir"], rec["img"]), {k: v for k, v in rec.items() if k != "img"}))
    return out


def slot_rows(r: dict, x: dict, meta: dict, robot: str, seed: int, third_person: bool) -> tuple:
    """The 4-slot schema (views9) of one ego row x: (ego row, [third-person variant], visibility-drop Counter) --
    user 10-02 (4 slots); the third-person variant is gated by _vis_gate (owner order 10-02)."""
    from . import tp9
    from . import views9 as V
    arm = meta.get("arm") or "right"
    cams = json.load(open(r["cams_path"]))
    used = (x["images"][1], cams.get("wrist")) if len(x["images"]) > 1 and cams.get("wrist") else None
    op = os.path.join(r["call_dir"], "img3_wrist_other.png")
    other = (op, cams["wrist_other"]) if cams.get("wrist_other") and os.path.exists(op) else None
    text = open(x["prompt_path"], encoding="utf-8").read()
    src = f"l9/{robot}"
    extras = extra_views(r)
    from .specgate9 import SPEC_CAMS

    def one(third, tag):
        res = V.canonical(text, x["answer"], arm, x["images"][0], used, other, third, V.row_rng(x["id"], seed),
                          source=src, anchor=CAM_ANCHOR, robot=robot, extras=extras)
        pp = x["prompt_path"][:-4] + f"_{tag}.txt"
        with open(pp, "w", encoding="utf-8", newline="\n") as f:
            f.write(res["text"])
        return dict(x, prompt_path=pp, images=res["images"], answer=res["answer"], image_views=res["image_views"],
                    slots=res["slots"], arm=arm, spec_version=SPEC_CAMS,
                    episode_spec=x.get("episode_spec", x.get("spec_version")))
    ego = one(None, "slots")
    tps = []
    cv = Counter()
    if third_person and not x.get("label_missing"):
        from . import ext9 as E9
        d, ext = tp9.external_cams(r["call_dir"])
        for k in sorted(ext)[:1]:  # one third-person view per row
            ip = os.path.join(d, f"img1_{k}.png")
            dp = os.path.join(d, f"{k}_depth.npz")
            if os.path.exists(ip) and os.path.exists(dp):
                ok, reason = _vis_gate(ext[k], E9.load_depth(dp), r)
                if not ok:
                    cv[f"vis_drop_tp_{reason}"] += 1
                    continue
                tps.append(dict(one((ip, ext[k]), "slots_tp"), id=x["id"] + "_tp", third_person=True,
                                third_person_cam=k))
    return ego, tps, cv


def episode_rows(ep_dir: str, out_dir: str, split: str, train: bool, rng, camera_line: bool = False,
                 grasp_format: bool = True, external: bool = False, slots: bool = False,
                 third_person: bool = False, seed: int = 0, rationale: bool = False) -> tuple:
    """-> (control rows, aux rows, counts) of one L9 episode. external=True adds the paired external-view rows of
    paired episodes (ext9; default off = the head-only build, unchanged). rationale=True: each control row's answer
    (ego + any third-person slot variant) gets the build-time "why" (rationale9.build) inserted before "reason";
    default False = byte-identical to the no-rationale build (owner 10-02 22:40, no production change)."""
    from ..teach_l8.dataset import repeat_of
    from ..teach_pt import dataset as DS
    from ..teach_pt import min_format as MF
    meta = json.load(open(os.path.join(ep_dir, "meta.json")))
    robot = meta.get("robot") or "ffw_sg2"
    hc = meta.get("head_cam") or {"mode": "std"}
    ctrl, aux, c = [], [], Counter()
    for r in DS.load_rows(ep_dir, split):
        c["states"] += 1
        head_ok, head_reason = _vis_gate(json.load(open(r["cams_path"]))["head"], np.load(r["depth_path"])["depth"], r,
                                         use_occ=True)
        if not head_ok:  # owner order 2026-10-02/10-03: never a row whose pointed-at object the head image can't show
            c["vis_dropped_rows"] += 1
            c[f"vis_drop_head_{head_reason}"] += 1
            continue
        v2 = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
        named = register_call_names(r, v2)
        c["names_ok" if named else "names_mismatch"] += 1
        x = MF.row(r, out_dir, "d-min", "clean")
        if train and x["label_missing"]:
            c["label_missing_dropped"] += 1
            continue
        line = camera_of(r, robot)
        from .specgate9 import spec_of
        x.update(robot=robot, head_cam_mode=(hc.get("draw") or {}).get("mode", hc.get("mode", "std")), camera=line,
                 source=f"l9/{robot}", gen="l9", spec_version=spec_of(meta), overlay="mono", colour_legend="none",
                 instruction=meta.get("instruction"), gt=r.get("gt"), step=r.get("step"),
                 task_def=meta.get("task_id"), ep_split=meta.get("split", "train"),
                 objects=sorted(meta.get("objects") or {}), room=meta.get("room") if isinstance(meta.get("room"), str) else None)
        if meta.get("grasp_v2") is not None:  # spec §12.8 format v2 (grasp_format=False: the old point format)
            rl = robot_line(meta)
            x.update(robot_line=rl, gen_version="v2", label_origin=meta.get("label_origin", "l9v2"))
            p = x["prompt_path"]
            if grasp_format:
                t = open(p, encoding="utf-8").read()  # read before opening for write (that truncated the request
                with open(p, "w", encoding="utf-8", newline="\n") as f:  # to the GRASP block alone, 10-02)
                    f.write(add_grasp_format(t, rl))
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
        tp_rows = []
        if slots:  # 4-slot camera schema (views9); third-person variants go to the third-person shard
            x, tp_rows, cv = slot_rows(r, x, meta, robot, seed, third_person)
            ext_rows += tp_rows
            c["third_person_slot_rows"] += len(tp_rows)
            c.update(cv)
        if rationale:
            from . import rationale9 as RT
            text = RT.for_answer(meta, r, x["answer"])
            if text:
                x["answer"] = RT.inject(x["answer"], text)
                for tp in tp_rows:
                    tp["answer"] = RT.inject(tp["answer"], text)
                c["rationale_rows"] += 1
            else:
                c["rationale_missing"] += 1
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
          third_person: bool = False, rationale: bool = False, ep_filter: bool | None = None) -> dict:
    """external=True (--third-person on): + the paired external-view rows, written to their own shard
    <name>_third_person.jsonl (user 10-02: the ego shard <name>.jsonl never holds third-person rows; off = 0 of them).
    rationale=True: see episode_rows (default False = unchanged output, owner 10-02 22:40).
    ep_filter (default = train): episode_filter() first -- key-call occlusion + arm balance (user 10-03)."""
    prepare(("train", "ood_o"))
    os.makedirs(out_dir, exist_ok=True)
    ep_rep = None
    if train if ep_filter is None else ep_filter:
        ep_dirs, ep_rep = episode_filter(ep_dirs)
    rng = np.random.default_rng([seed, 9, 29])
    ctrl, aux, c = [], [], Counter()
    for d in ep_dirs:
        a, b, k = episode_rows(d, out_dir, split, train, rng, camera_line, grasp_format, external, slots,
                               third_person, seed, rationale)
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
    if ep_rep is not None:
        counts["episode_filter"] = ep_rep
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
