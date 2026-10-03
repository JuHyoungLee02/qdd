"""Print the per-robot check fields of a gab_report.py --json output."""
import json
import sys

d = json.load(open(sys.argv[1]))
for robot, r in d["robots"].items():
    oks = {k: v for k, v in r.items() if k.endswith("_ok")}
    div = r.get("diversity_B_vs_A") or {}
    pa, pb = r["A"]["profile"], r["B"]["profile"]
    print(robot, oks, "lost", r["families_lost"])
    print("   fam A", pa["family_share"], "B", pb["family_share"])
    print("   iqr A", pa["iqr_table_z"], pa["iqr_x"], pa["iqr_y"], "B", pb["iqr_table_z"], pb["iqr_x"], pb["iqr_y"],
          "rot", pa["rot_bins"], pb["rot_bins"], "high", pa["high_share"], pb["high_share"], "left", pa["left_share"], pb["left_share"])
    print("   famrate A", r["A"]["family"], "\n   famrate B", r["B"]["family"])
    print("   dq_over", r["A"]["dq_over"], r["B"]["dq_over"], "spec B", r["B"]["spec"], "aba_n", r["A"]["aba_n"], r["B"]["aba_n"])
print(d["verdict"])
