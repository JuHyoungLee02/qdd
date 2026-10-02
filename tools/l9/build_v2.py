"""L9 v2 training-set build (harvest.l9.build9) with the 4-slot camera schema (views9) and the third-person switch
(user 10-02). Ego rows -> <out>/<name>.jsonl; with --third-person on, the third-person variants -> <name>_third_person.jsonl.
Checks: off-build 0 third-person rows; on-build third-person rows = third-person index entries of the episodes (one
view per row); every ego row parses to the 4 slots; 0 rows without the head image; image-count histogram.
usage: python tools/l9/build_v2.py <out dir> <name> <collect root>... [--third-person off|on] [--split l9train]
       [--eval] [--no-slots] [--seed 0] [--success-only] [--camera-line] [--both] [--spec L9v2-spec-final (family)]
       [--rationale off|on|both] [--no-ep-filter]
--no-ep-filter: skip build9.episode_filter (user 10-03 key-call occlusion drop + per-robot arm balance; default on
for training builds, off for --eval).
--both (with --third-person on): also <name>_tp_off.jsonl and <name>_tp_on.jsonl from the same build; the ego rows are
byte-identical (checked).
--rationale (owner 10-02 22:40, 8B check arm): on = every control row's answer gets the build-time "why"
(harvest.l9.rationale9); both = also <name>_rat_off.jsonl / <name>_rat_on.jsonl from the SAME rows (row ids
identical, only the reply text differs, checked like --both above); off (default) = unchanged (no production
change). The consistency gate (rationale word == command word) runs inside specgate9.gates() either way."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import build9 as B9  # noqa: E402
from harvest.l9 import tp9  # noqa: E402
from harvest.l9 import views9 as V  # noqa: E402
from harvest.l9 import specgate9 as SG  # noqa: E402
from harvest.l9 import rationale9 as RT  # noqa: E402


def main():
    a = sys.argv[1:]
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    out, name = a[0], a[1]
    roots = [x for i, x in enumerate(a[2:], 2) if not x.startswith("--") and not a[i - 1].startswith("--")]
    tp_on = arg("--third-person", "off") == "on"
    rat_mode = arg("--rationale", "off")
    slots = "--no-slots" not in a
    eps = []
    n_old_spec = 0
    train = "--eval" not in a
    from harvest.l9 import alloc9 as AL
    split_drop = {"holdout_def": 0, "non_train_split": 0, "robot_not_gated": 0}
    for r in roots:
        for m in sorted(glob.glob(os.path.join(r, "*", "*", "*", "meta.json"))):
            meta = json.load(open(m))
            if meta.get("grasp_v2") is None or ("--success-only" in a and not meta.get("success")):
                continue
            # one spec per training set (L9_PRINCIPLES §0), compared by FAMILY (specgate9.SPEC_FAMILY: the Franka r1
            # camera episodes belong to the frozen spec; the exact-string test dropped every one of them)
            if SG.spec_family(SG.spec_of(meta)) != SG.spec_family(arg("--spec", SG.SPEC)):
                n_old_spec += 1
                continue
            if train and meta.get("split", "train") != "train":  # owner 10-02: another split's episodes never train
                split_drop["non_train_split"] += 1
                continue
            if train and AL.is_holdout(meta.get("task_id")):  # E-TP1 leak: train episodes of a hold-out definition
                split_drop["holdout_def"] += 1  # (pilot rows, kept on disk; the hold-out build may take them)
                continue
            if train and not AL.robot_build_ready(meta.get("robot")):  # user 10-03 01h: robot-level all-task gate
                split_drop["robot_not_gated"] += 1  # (kept on disk; this robot's rows re-enter once it clears)
                continue
            eps.append(os.path.dirname(m))
    c = B9.build(eps, out, arg("--split", "l9train"), name, train="--eval" not in a, camera_line="--camera-line" in a,
                 seed=int(arg("--seed", "0")), slots=slots, third_person=tp_on, rationale=rat_mode != "off",
                 ep_filter=False if "--no-ep-filter" in a else None)  # user 10-03: key-call occlusion + arm balance
    ego = [json.loads(x) for x in open(c["path"])]
    bad = 0
    if slots:
        for x in ego:
            if x.get("image_views"):
                try:
                    V.parse_slots(open(x["prompt_path"], encoding="utf-8").read())
                except ValueError:
                    bad += 1
    n_idx = sum(len({(e["episode"], e["call"]) for e in tp9.index(r)}) for r in roots) if tp_on else 0
    vis_drop = {k: v for k, v in c.items() if k.startswith("vis_drop")}  # owner order 10-02: head / external / tp
    check = {"ego_third_person_rows": sum(1 for x in ego if x.get("third_person") or x.get("view") == "external"),
             "third_person_rows": c["third_person_rows"], "third_person_index_calls": n_idx,
             "slot_parse_errors": bad, "rows_without_head": c.get("rows_without_head"),
             "image_count_hist": c.get("image_count_hist"), "slot_combos": c.get("slot_combos"),
             "vis_gate": dict(vis_drop, states=c.get("states", 0),
                              drop_rate=round(c.get("vis_dropped_rows", 0) / c["states"], 4) if c.get("states") else None)}
    check["ok"] = (check["ego_third_person_rows"] == 0 and bad == 0 and not check["rows_without_head"]
                   and (c["third_person_rows"] == 0 if not tp_on else True))
    ctrl = [x for x in ego if x.get("kind", "control") == "control" and x.get("gen") == "l9"]
    texts = {x["prompt_path"]: open(x["prompt_path"], encoding="utf-8").read() for x in ctrl
             if x.get("prompt_path") and os.path.exists(x["prompt_path"])}
    ood_o, ood_r = set(), set()
    if train:
        from harvest.l9 import assets9 as A9
        from harvest.l9 import run9 as RN
        ood_o, ood_r = set(A9.catalog("ood_o")), set(RN.room_table("ood"))
    # hard gates: contradictions 0, one spec / overlay / template family / legend, schema, frame sentence (slot
    # builds), and for training sets the split gate (hold-out definitions, other splits, ood_o objects, ood rooms)
    g = SG.gates(ctrl, texts, train=train, frame_note=slots, ood_objects=ood_o, ood_rooms=ood_r, views=slots)
    if slots:  # r2-cams (user 10-03 02h): views per robot (each robot's own camera set, any number)
        from collections import Counter
        vb = {}
        for x in ctrl:
            vb.setdefault(x.get("robot"), Counter())["+".join(x.get("image_views") or [])] += 1
        check["views_by_robot"] = {k: dict(v) for k, v in vb.items()}
        check["episode_specs"] = dict(Counter(x.get("episode_spec") for x in ctrl))
    check.update(spec_gates=g, episodes_dropped_old_spec=n_old_spec, episodes_dropped_split=split_drop,
                 episode_filter=c.get("episode_filter"))  # per robot / arm: raw -> after key occlusion -> balanced
    check["ok"] = check["ok"] and g["ok"]
    if tp_on and "--both" in a:  # user 10-02: two sets from one build -- off = the ego rows, on = the same bytes + tp rows
        import hashlib
        ego_b = open(c["path"], "rb").read()
        tp_b = open(os.path.join(out, name + "_third_person.jsonl"), "rb").read()
        with open(os.path.join(out, name + "_tp_off.jsonl"), "wb") as f:
            f.write(ego_b)
        with open(os.path.join(out, name + "_tp_on.jsonl"), "wb") as f:
            f.write(ego_b + tp_b)
        off_b = open(os.path.join(out, name + "_tp_off.jsonl"), "rb").read()
        on_b = open(os.path.join(out, name + "_tp_on.jsonl"), "rb").read()
        check["sets"] = {"off_rows": off_b.count(b"\n"), "on_rows": on_b.count(b"\n"),
                         "ego_sha256": hashlib.sha256(off_b).hexdigest()[:16],
                         "ego_identical": on_b[:len(off_b)] == off_b}
        check["ok"] = check["ok"] and check["sets"]["ego_identical"]
    if rat_mode != "off":  # owner 10-02 22:40: 8B check arm (rationale on/off), build-time "why" (rationale9)
        anss = []
        for x in ctrl:
            try:
                anss.append(json.loads(x["answer"]))
            except (TypeError, ValueError):
                anss.append({})
        rats = [a.get("rationale") for a in anss]
        parsed = [RT.parse(r) if r else None for r in rats]
        n = len(ctrl)
        with_rat = sum(1 for r in rats if r)
        share = lambda f: round(sum(1 for p in parsed if p and f(p)) / n, 4) if n else 0.0  # noqa: E731
        check["rationale"] = {
            "rows": n, "with_rationale": with_rat, "share_with_rationale": round(with_rat / n, 4) if n else 0.0,
            "share_arm": share(lambda p: bool(p["arms"])), "share_approach": share(lambda p: p["approach"] is not None),
            "share_rot": share(lambda p: p["rot"] is not None), "share_handover": share(lambda p: p["handover"]),
            "share_axis": share(lambda p: p["axis"] is not None), "mismatches": g["rationale_mismatches"],
            "examples": [r for r in rats if r][:5]}
        check["ok"] = check["ok"] and check["rationale"]["mismatches"] == 0
        if rat_mode == "both":  # <name>_rat_off.jsonl / _rat_on.jsonl from the SAME rows (c["path"] = the on build)
            off_lines = [json.dumps(dict(x, answer=RT.strip(x["answer"]))) for x in ego]
            on_lines = [json.dumps(x) for x in ego]
            with open(os.path.join(out, name + "_rat_off.jsonl"), "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(ln + "\n" for ln in off_lines))
            with open(os.path.join(out, name + "_rat_on.jsonl"), "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(ln + "\n" for ln in on_lines))
            off_b = open(os.path.join(out, name + "_rat_off.jsonl"), "rb").read()
            on_b = open(os.path.join(out, name + "_rat_on.jsonl"), "rb").read()
            check["rationale"]["sets"] = {"off_rows": off_b.count(b"\n"), "on_rows": on_b.count(b"\n"),
                                          "rows_identical": off_b.count(b"\n") == on_b.count(b"\n")}
            check["ok"] = check["ok"] and check["rationale"]["sets"]["rows_identical"]
    json.dump(check, open(os.path.join(out, name + ".check.json"), "w"), indent=1)
    print(json.dumps(dict(check, episodes=len(eps), control_rows=c["control_rows"])))


if __name__ == "__main__":
    main()
