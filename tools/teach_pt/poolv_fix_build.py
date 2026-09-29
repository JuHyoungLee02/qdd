"""E-POOLV8-FIX pool (docs/stage3/prereg_poolv_fix.md): corrected open pool.
  * RB2 / RB3 / MolmoBot RBY1: the original verified rows, minus only the object / place rows that failed the 4-way
    check (ee rows are all kept: the arm/hand ee rule wrongly dropped open-gripper fingertip centres, E-POOLV8);
    written to points/<src>_fix/records.jsonl from the original file and <src>_verified/rejected.jsonl.
  * BEHAVIOR, ManiSkill: unchanged; AgiBot: v3 final (agibot_v3_verified/final_all.jsonl) instead of agibot_p0.
  * then tools/final35/open_pool.main (G split + guard, repeat cap) with these sources.
usage: python poolv_fix_build.py <base d-min jsonl> <out jsonl> [p 0.75] [cap 1.5]"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "final35"))
import open_pool as OP  # noqa: E402

X = OP.X
ORIG = {"rb2": f"{X}/rb2/records_verified_v2.jsonl", "rb3": f"{X}/rb3/records_verified.jsonl",
        "molmobot_rby1": f"{X}/molmobot_rby1/records_verified.jsonl"}


def fix_source(src):
    rej = {}
    for x in open(f"{X}/{src}_verified/rejected.jsonl"):
        d = json.loads(x)
        rej[d["id"]] = d["reason"]
    drop = {i for i, w in rej.items() if w != "ee_off_arm"}
    os.makedirs(f"{X}/{src}_fix", exist_ok=True)
    n_in = n_out = 0
    with open(f"{X}/{src}_fix/records.jsonl", "w", encoding="utf-8", newline="\n") as fo:
        for line in open(ORIG[src], encoding="utf-8"):
            n_in += 1
            if json.loads(line)["id"] in drop:
                continue
            n_out += 1
            fo.write(line if line.endswith("\n") else line + "\n")
    print(json.dumps({"source": src, "orig": n_in, "dropped_obj_place": len(drop), "kept": n_out}))
    return f"{X}/{src}_fix/records.jsonl"


if __name__ == "__main__":
    a = sys.argv[1:]
    OP.SOURCES = {"rb2": fix_source("rb2"), "behavior": f"{X}/behavior/records_verified.jsonl",
                  "rb3": fix_source("rb3"), "molmobot_rby1": fix_source("molmobot_rby1"),
                  "maniskill": f"{X}/maniskill/records_verified.jsonl",
                  "agibot_v3": f"{X}/agibot_v3_verified/final_all.jsonl"}
    OP.main(a[0], a[1], float(a[2]) if len(a) > 2 else 0.75, float(a[3]) if len(a) > 3 else 1.5)
