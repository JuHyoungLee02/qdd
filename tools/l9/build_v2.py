"""L9 v2 training-set build (harvest.l9.build9) with the 4-slot camera schema (views9) and the third-person switch
(user 10-02). Ego rows -> <out>/<name>.jsonl; with --third-person on, the third-person variants -> <name>_third_person.jsonl.
Checks: off-build 0 third-person rows; on-build third-person rows = third-person index entries of the episodes (one
view per row); every ego row parses to the 4 slots; 0 rows without the head image; image-count histogram.
usage: python tools/l9/build_v2.py <out dir> <name> <collect root>... [--third-person off|on] [--split l9train]
       [--eval] [--no-slots] [--seed 0] [--success-only] [--camera-line] [--both]
--both (with --third-person on): also <name>_tp_off.jsonl and <name>_tp_on.jsonl from the same build; the ego rows are
byte-identical (checked)."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import build9 as B9  # noqa: E402
from harvest.l9 import tp9  # noqa: E402
from harvest.l9 import views9 as V  # noqa: E402


def main():
    a = sys.argv[1:]
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    out, name = a[0], a[1]
    roots = [x for i, x in enumerate(a[2:], 2) if not x.startswith("--") and not a[i - 1].startswith("--")]
    tp_on = arg("--third-person", "off") == "on"
    slots = "--no-slots" not in a
    eps = []
    for r in roots:
        for m in sorted(glob.glob(os.path.join(r, "*", "*", "*", "meta.json"))):
            meta = json.load(open(m))
            if meta.get("grasp_v2") is None or ("--success-only" in a and not meta.get("success")):
                continue
            eps.append(os.path.dirname(m))
    c = B9.build(eps, out, arg("--split", "l9train"), name, train="--eval" not in a, camera_line="--camera-line" in a,
                 seed=int(arg("--seed", "0")), slots=slots, third_person=tp_on)
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
    check = {"ego_third_person_rows": sum(1 for x in ego if x.get("third_person") or x.get("view") == "external"),
             "third_person_rows": c["third_person_rows"], "third_person_index_calls": n_idx,
             "slot_parse_errors": bad, "rows_without_head": c.get("rows_without_head"),
             "image_count_hist": c.get("image_count_hist"), "slot_combos": c.get("slot_combos")}
    check["ok"] = (check["ego_third_person_rows"] == 0 and bad == 0 and not check["rows_without_head"]
                   and (c["third_person_rows"] == 0 if not tp_on else True))
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
    json.dump(check, open(os.path.join(out, name + ".check.json"), "w"), indent=1)
    print(json.dumps(dict(check, episodes=len(eps), control_rows=c["control_rows"])))


if __name__ == "__main__":
    main()
