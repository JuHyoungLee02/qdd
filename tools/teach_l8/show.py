"""Print one collected E-TEACH-L8 episode: per call the label step / status / executed kind / label command, then the
measured history and the monitor summary. usage: python show.py <episode dir> [...]"""
import json
import os
import sys

for d in sys.argv[1:]:
    print("==", d)
    meta = json.load(open(os.path.join(d, "meta.json")))
    print("meta", json.dumps(meta))
    for x in open(os.path.join(d, "labels.jsonl")):
        r = json.loads(x)
        cmd = json.loads(r["answer"])["command"] if r["answer"] else None
        print(f"  c{r['call']:03d} prev={r['prev_kind']:<12} step={r['step']:<13} status={r['status']!s:<11} "
              f"exec={r['exec_kind']:<12} drop={r['drop']} label={json.dumps(cmd)} tgt={r['gt']['tgt']}")
    res = json.load(open(os.path.join(d, "result.json")))
    for h in res["history"]:
        print("   H", h)
    print("  summary", {k: res.get(k) for k in ("success", "fail_stage", "tipped", "off_table", "knocked",
                                                "end_reason", "n_close")})
