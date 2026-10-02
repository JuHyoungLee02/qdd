"""E-TP1 data (prereg_tp1.md): third-person rows off vs on, L9 v2 only, the build_v2.py path (harvest.l9.build9 with the
4-slot camera schema and third_person=True, spec gate L9v2-spec-final) run in parallel parts.
  off = the ego rows; on = the same ego bytes + the third-person rows of the same episodes (build_v2 --both rule).
  training episodes = collect/train, hold-out = collect/holdout (the L9 owner's held-out definitions, alloc9.holdout_defs),
  both: success, max_dq_rad <= 0.04, robot in {ffw_sg2, franka_mast}, spec_of(meta) == L9v2-spec-final.
usage (pod python, PYTHONPATH = code dir):
  tp1_build.py select <eps.json> <collect root>...
  tp1_build.py rows <eps.json> <out dir> <train|eval> --part k/n
  tp1_build.py merge <out dir> <n train parts> <n eval parts>"""
import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter

ROBOTS = ("ffw_sg2", "franka_mast")
EVAL_CAP = 10  # change 2


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def gp2_holdout(task_id: str) -> bool:  # the E-GP2 definition hash (sha256("gp2:<task_id>") % 5 == 0)
    return int(hashlib.sha256(f"gp2:{task_id}".encode()).hexdigest()[:8], 16) % 5 == 0


def select(out, roots):
    """change 1: held-out DEFINITIONS = the definitions of collect/holdout episodes + the E-GP2 hash definitions; every
    eligible episode of those definitions (either folder) is evaluated, none is trained on."""
    from harvest.l9 import alloc9 as AL
    from harvest.l9 import specgate9 as SG
    ho_defs = set(AL.HOLDOUT_FROZEN)  # change 3: the owner's frozen hold-out definitions as well
    for root in roots:
        for m in glob.glob(os.path.join(root, "holdout", "*", "*", "meta.json")):
            try:
                ho_defs.add(json.load(open(m))["task_id"])
            except (OSError, ValueError, KeyError):
                pass
    eps, c = {"train": [], "eval": []}, Counter()
    for root in roots:
        for split in ("train", "holdout"):
            for m in sorted(glob.glob(os.path.join(root, split, "*", "*", "meta.json"))):
                try:
                    d = json.load(open(m))
                except (OSError, ValueError):
                    c["unreadable"] += 1
                    continue
                if d.get("gen") != "l9" or d.get("grasp_v2") is None:
                    continue
                key = "eval" if (d.get("task_id") in ho_defs or gp2_holdout(d.get("task_id", ""))) else "train"
                c[f"{key}_v2"] += 1
                if not d.get("success"):
                    continue
                if SG.spec_of(d) != SG.SPEC:
                    c[f"{key}_old_spec"] += 1
                    continue
                if (d.get("max_dq_rad") or 0) > 0.04 or (d.get("robot") or "ffw_sg2") not in ROBOTS \
                        or d.get("task_id") == "gate_move":
                    c[f"{key}_excluded"] += 1
                    continue
                eps[key].append({"dir": os.path.dirname(m), "def": d["task_id"], "robot": d.get("robot") or "ffw_sg2",
                                 "seed": d.get("seed")})
    # change 2: at most EVAL_CAP episodes per held-out definition (seed order) -- evaluation time per model
    by = {}
    for e in sorted(eps["eval"], key=lambda e: (e["def"], int(e.get("seed") or 0), e["dir"])):
        by.setdefault(e["def"], []).append(e)
    c["eval_before_cap"] = len(eps["eval"])
    eps["eval"] = [e for k in sorted(by) for e in by[k][:EVAL_CAP]]
    dt, de = {e["def"] for e in eps["train"]}, {e["def"] for e in eps["eval"]}
    info = dict(c, train=len(eps["train"]), eval=len(eps["eval"]), train_defs=len(dt), eval_defs=len(de),
                shared_defs=len(dt & de), holdout_folder_defs=len(ho_defs), robots={s: dict(Counter(e["robot"] for e in eps[s])) for s in eps})
    assert not (dt & de), "a held-out definition in training"
    json.dump(dict(eps, info=info), open(out, "w"), indent=0)
    print(json.dumps(info))


def rows(eps_path, out, split, part):
    from harvest.l9 import build9 as B9
    eps = json.load(open(eps_path))[split]
    k, n = (int(v) for v in part.split("/"))
    eps = eps[k::n]
    tr = split == "train"
    c = B9.build([e["dir"] for e in eps], out, "l9train", f"l9tp_{split}.part{k:02d}", train=tr, camera_line=False,
                 seed=0, slots=True, third_person=True)  # seed 0 = build_v2 (slot draws keyed by row id + seed)
    # change 3: the hold-out build also makes its third-person rows (directional third-person eval subset)
    print(json.dumps({x: v for x, v in c.items() if x != "path"}))


DIR_WORDS = re.compile(r"\b(left|right|front|behind)\b", re.I)


def instruction_of(row):
    ep = os.path.dirname(os.path.dirname(row["call_dir"]))
    return json.load(open(os.path.join(ep, "meta.json"))).get("instruction") or ""


def merge(out, nt, ne):
    from harvest.l9 import assets9 as A9
    from harvest.l9 import run9 as RN
    from harvest.l9 import specgate9 as SG
    from harvest.l9 import views9 as V

    def cat(names):
        b = b""
        for p in names:
            b += open(p, "rb").read()
        return b
    ego = cat([os.path.join(out, f"l9tp_train.part{k:02d}.jsonl") for k in range(nt)])
    tp = cat([os.path.join(out, f"l9tp_train.part{k:02d}_third_person.jsonl") for k in range(nt)])
    ev = cat([os.path.join(out, f"l9tp_eval.part{k:02d}.jsonl") for k in range(ne)])
    evtp = [json.loads(x) for k in range(ne)
            for x in open(os.path.join(out, f"l9tp_eval.part{k:02d}_third_person.jsonl"), encoding="utf-8")]
    evdir = [x for x in evtp if x.get("kind", "control") == "control" and not x.get("label_missing")
             and DIR_WORDS.search(instruction_of(x))]  # change 3: directional third-person hold-out subset
    files = {"train_off.jsonl": ego, "train_on.jsonl": ego + tp, "l9_eval_off.jsonl": ev, "l9_eval_on.jsonl": ev,
             "l9_eval_onaux.jsonl": ev, "l9_eval_tpdir.jsonl": "".join(json.dumps(x) + "\n" for x in evdir).encode(),
             "l9_eval_tp_all.jsonl": "".join(json.dumps(x) + "\n" for x in evtp).encode()}
    for name, b in files.items():
        with open(os.path.join(out, name), "wb") as f:
            f.write(b)
    rows_e = [json.loads(x) for x in ego.decode().splitlines()]
    rows_t = [json.loads(x) for x in tp.decode().splitlines()]
    rows_v = [json.loads(x) for x in ev.decode().splitlines()]
    ctrl = [x for x in rows_e + rows_t if x.get("kind", "control") == "control" and x.get("gen") == "l9"]
    texts = {x["prompt_path"]: open(x["prompt_path"], encoding="utf-8").read() for x in ctrl if x.get("prompt_path")}
    bad = 0
    for x in ctrl:
        if x.get("image_views"):
            try:
                V.parse_slots(texts[x["prompt_path"]])
            except ValueError:
                bad += 1
    ood_o, ood_r = set(A9.catalog("ood_o")), set(RN.room_table("ood"))
    g = SG.gates(ctrl, texts, train=True, frame_note=True, ood_objects=ood_o, ood_rooms=ood_r)
    vctrl = [x for x in rows_v + evtp if x.get("kind", "control") == "control"]
    vtexts = {x["prompt_path"]: open(x["prompt_path"], encoding="utf-8").read() for x in vctrl if x.get("prompt_path")}
    gv = SG.gates(vctrl, vtexts, frame_note=True)
    chk = {"off_rows": len(rows_e), "on_rows": len(rows_e) + len(rows_t), "third_person_rows": len(rows_t),
           "ego_third_person_rows": sum(1 for x in rows_e if x.get("third_person") or x.get("view") == "external"),
           "tp_rows_not_third_person": sum(1 for x in rows_t if not (x.get("third_person") or x.get("view") == "external")),
           "ego_identical": files["train_on.jsonl"][:len(ego)] == ego, "slot_parse_errors": bad,
           "rows_without_head": sum(1 for x in ctrl if (x.get("image_views") or ["head"])[0] != "head"),
           "eval_rows": len(rows_v), "eval_control": sum(1 for x in rows_v if x.get("kind", "control") == "control"),
           "eval_third_person_rows": sum(1 for x in rows_v if x.get("third_person") or x.get("view") == "external"),
           "eval_tp_rows": len(evtp), "eval_tpdir_rows": len(evdir),
           "frame_note_missing": sum(1 for t in list(texts.values()) + list(vtexts.values()) if V.FRAME_NOTE not in t),
           "spec_gates_ok": g.get("ok"), "eval_spec_gates_ok": gv.get("ok"),
           "image_count_hist": dict(Counter(len(x["images"]) for x in rows_e + rows_t)),
           "sha256": {k: sha(os.path.join(out, k)) for k in files}}
    chk["ok"] = (chk["ego_third_person_rows"] == 0 and chk["tp_rows_not_third_person"] == 0 and chk["ego_identical"]
                 and bad == 0 and chk["rows_without_head"] == 0 and chk["eval_third_person_rows"] == 0
                 and chk["frame_note_missing"] == 0 and bool(g.get("ok")) and bool(gv.get("ok")))
    json.dump(dict(chk, spec_gates=g, eval_spec_gates=gv), open(os.path.join(out, "check.json"), "w"), indent=1)
    print(json.dumps(chk))
    if not chk["ok"]:
        sys.exit(3)


def main():
    a = sys.argv[1:]
    if a[0] == "select":
        select(a[1], a[2:])
    elif a[0] == "rows":
        rows(a[1], a[2], a[3], a[a.index("--part") + 1])
    elif a[0] == "merge":
        merge(a[1], int(a[2]), int(a[3]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
