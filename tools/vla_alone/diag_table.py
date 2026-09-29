"""Per-episode table (markdown) of tools/vla_alone/diag_couple_dry.py output.
  python tools/vla_alone/diag_table.py diag.json > table.md"""
import json
import sys

d = json.load(open(sys.argv[1]))["episodes"]
cols = ("final_phase", "phase_s", "hold_share", "first_hold_t", "longest_hold_s", "t1_false", "w_start_mm",
        "w_min_approach_mm", "w_first_hold_mm", "first_w_below_open_t", "d_xy_start_mm", "d_xy_min_mm", "t_d_xy_min",
        "z_above_mug_at_min_mm", "d_xy_first_hold_mm", "overshoot_max_mm", "overshoot_at_first_hold_mm", "d_xy_end_mm",
        "z_above_mug_end_mm", "cmd_gap_mm_median", "exec_dir_vs_oracle", "answer_dir_vs_oracle", "moved_vs_exec_dir",
        "chunk", "mug_moved_mm", "answer_dir_hist")
print("| ep | " + " | ".join(cols) + " |")
print("|" + "---|" * (len(cols) + 1))
for k, e in d.items():
    print(f"| {k} | " + " | ".join(json.dumps(e.get(c)).replace("|", "/") for c in cols) + " |")
