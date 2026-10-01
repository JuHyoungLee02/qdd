"""E-HCAM8 data builds (prereg_hcam8 §3; pod, venv python, PYTHONPATH = code dir).
  select  <collect root>... --out <episodes.json> --mode std|rand [--n 2000] [--match <episodes.json>]
          successful L9 AI Worker episodes (success, max_dq_rad <= 0.04, motion l9m-2, head camera mode),
          stratified by (definition, arm): equal share per stratum, seed order; --match takes exactly the strata
          counts of another selection (H1 matched to H0).
  rows    <episodes.json> <out dir> <tag> [--camera-line]
          symlinked stage -> harvest.teach_pt.min_format.build(split 'l9train', d-min) -> <out>/l9train_d-min.jsonl;
          --camera-line: every row's prompt gets the prereg change-1 `camera:` line (new prompt files).
  combine <base train jsonl> <l9 rows jsonl> <out train jsonl> [--camera-line-base] [--trim-to N]
          base (E-VIEW8 A0) + L9 rows; optional camera lines on the base rows (cams.json when the row has one,
          else 'camera: head, unknown'); prints rows, steps = round(1632 x rows / 78745), sha256."""
import glob
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

BASE_STEPS, BASE_ROWS = 1632, 78745
ANCHOR = "CAMERAS (directions are unit vectors in the robot frame)\n"


def _metas(roots):
    for root in roots:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            try:
                d = json.load(open(m))
            except (OSError, ValueError):
                continue
            if d.get("gen") == "l9":
                yield os.path.dirname(m), d


def eligible(d, mode):
    hc = d.get("head_cam") or {}
    m = (hc.get("draw") or {}).get("mode", "std")
    return (bool(d.get("success")) and (d.get("max_dq_rad") or 0) <= 0.04 and d.get("motion_version") == "l9m-2"
            and (d.get("robot") or "ffw_sg2") == "ffw_sg2" and m == mode and d.get("task_id") != "gate_move")


def select(roots, mode, n, match=None):
    by = defaultdict(list)
    for ep, d in _metas(roots):
        if eligible(d, mode):
            by[(d["task_id"], d["arm"])].append((int(d["seed"]), ep, d["env_family"]))
    for k in by:
        by[k].sort()
    if match:
        want = Counter((e["def"], e["arm"]) for e in match)
        short = {f"{k[0]}/{k[1]}": [len(by.get(k, [])), c] for k, c in want.items() if len(by.get(k, [])) < c}
        if short:
            return None, {"short_strata": short}
        take = {k: c for k, c in want.items()}
    else:
        keys = sorted(by)
        take, left = {k: 0 for k in keys}, n
        while left > 0:  # round robin: equal share, strata with fewer episodes give theirs to the others
            moved = False
            for k in keys:
                if left and take[k] < len(by[k]):
                    take[k] += 1
                    left -= 1
                    moved = True
            if not moved:
                break
    out = [{"dir": ep, "seed": s, "def": k[0], "arm": k[1], "family": f} for k, c in sorted(take.items())
           for s, ep, f in by[k][:c]]
    return out, {"n": len(out), "strata": len(take), "available": sum(len(v) for v in by.values())}


def stage(eps, d):
    os.makedirs(d, exist_ok=True)
    for e in eps:
        fam = os.path.join(d, e["family"])
        os.makedirs(fam, exist_ok=True)
        link = os.path.join(fam, os.path.basename(e["dir"]))
        if not os.path.islink(link):
            os.symlink(e["dir"], link)


def add_line(text, line):
    if ANCHOR not in text:
        raise ValueError("no CAMERAS header")
    return text.replace(ANCHOR, ANCHOR + "- " + line + "\n", 1) if ("- camera: head" not in text) else text


def cam_line(row):
    from harvest.l9.hcam9 import line
    p = row.get("cams_path")
    if p and os.path.exists(p):
        src = "l9/ffw_sg2" if str(row.get("id", "")).startswith("l9_") else "l8x/ffw_sg2"
        return line(json.load(open(p))["head"], src)
    return "camera: head, unknown; source: " + str(row.get("source") or row.get("dataset") or "open")


def relink_prompts(rows, out_dir, tag):
    """New prompt files with the camera line (the source prompt files are never modified)."""
    d = os.path.join(out_dir, f"prompts_{tag}")
    os.makedirs(d, exist_ok=True)
    out = []
    for r in rows:
        if r.get("kind") == "aux" or not r.get("prompt_path"):
            out.append(r)
            continue
        dst = os.path.join(d, hashlib.sha1(r["prompt_path"].encode()).hexdigest()[:20] + ".txt")
        if not os.path.exists(dst):
            txt = open(r["prompt_path"], encoding="utf-8").read()
            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                f.write(add_line(txt, cam_line(r)))
        out.append(dict(r, prompt_path=dst, camera_line=True))
    return out


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    a = sys.argv[1:]
    cmd = a[0]
    opt = {a[i]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith("--") and not a[i + 1].startswith("--")}
    pos = [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and not a[i - 1].startswith("--")]
    if cmd == "select":
        match = json.load(open(opt["--match"])) if "--match" in opt else None
        eps, info = select(pos, opt["--mode"], int(opt.get("--n", 2000)), match)
        if eps is None:
            print(json.dumps(info))
            sys.exit(2)
        json.dump(eps, open(opt["--out"], "w"))
        print(json.dumps(dict(info, out=opt["--out"])))
    elif cmd == "rows":
        from harvest.teach_pt import min_format as MF
        eps, out, tag = json.load(open(pos[0])), pos[1], pos[2]
        st = os.path.join(out, f"stage_{tag}")
        stage(eps, st)
        c = MF.build(st, out, "l9train", "d-min", "clean")
        p = os.path.join(out, "l9train_d-min.jsonl")
        final = os.path.join(out, f"l9_{tag}.jsonl")
        rows = [json.loads(x) for x in open(p, encoding="utf-8")]
        if "--camera-line" in a:
            rows = relink_prompts(rows, out, tag)
        with open(final, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        os.remove(p)
        print(json.dumps(dict(c, rows=len(rows), out=final, sha256=sha(final), episodes=len(eps))))
    elif cmd == "combine":
        base, l9, out = pos[0], pos[1], pos[2]
        b = [json.loads(x) for x in open(base, encoding="utf-8")]
        if "--camera-line-base" in a:
            b = relink_prompts(b, os.path.dirname(out), "base_" + os.path.basename(out).split(".")[0])
        rows = b + [json.loads(x) for x in open(l9, encoding="utf-8")]
        if "--trim-to" in opt:
            rows = rows[:int(opt["--trim-to"])]
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(json.dumps({"out": out, "rows": len(rows), "base_rows": len(b), "l9_rows": len(rows) - len(b),
                          "steps": round(BASE_STEPS * len(rows) / BASE_ROWS), "sha256": sha(out)}))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
