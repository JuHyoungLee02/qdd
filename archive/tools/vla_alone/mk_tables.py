"""Markdown tables of the E-VLA-solo verdict.json (arm aggregates + per-variant success) for results/vla_solo.md.
  python tools/vla_alone/mk_tables.py verdict.json > tables.md"""
import json
import sys

v = json.load(open(sys.argv[1]))
NAME = {"A": "VLA C5 1.0x", "B": "VLA C3 1.0x", "C": "VLA C3 0.75x", "D": "VLA C3 0.5x", "E": "VLA C5 0.5x",
        "F": "scripted rule C5", "G": "no-op C5"}
cols = [("success", "성공"), ("min_d3_mm_median", "최소 3D 거리 중앙 mm"), ("min_xy_mm_median", "최소 xy 중앙 mm"),
        ("phase_rank_median", "도달 단계 중앙(0=approach)"), ("phase_max", "도달 단계 분포"),
        ("stuck_s_median", "멈춤 s 중앙"), ("hold_s_median", "hold s 중앙"), ("perm_hold", "영구 hold 편"),
        ("overshoot_mm_median", "지나침 mm 중앙"), ("t_end_s_median", "편 시간 s 중앙"),
        ("jump_ticks_median", "관절 계단 틱 중앙"), ("v_appr_mm_s_median", "approach 속도 mm/s 중앙")]
print("| 팔 | " + " | ".join(c[1] for c in cols) + " |")
print("|" + "---|" * (len(cols) + 1))
for k in sorted(v["agg"]):
    a = v["agg"][k]
    cells = []
    for key, _ in cols:
        x = a.get(key)
        cells.append(f"{x}/{a['n']}" if key in ("success", "perm_hold") else
                     (", ".join(f"{p} {n}" for p, n in x.items()) if isinstance(x, dict) else
                      ("—" if x is None else f"{x:.1f}" if isinstance(x, float) else str(x))))
    print(f"| {k} {NAME.get(k, '')} | " + " | ".join(cells) + " |")
print()
print("| 팔 | standard 성공 | dr 성공 |")
print("|---|---|---|")
for k in sorted(v["episodes"]):
    e = v["episodes"][k]
    s = sum(x["success"] for n, x in e.items() if n.startswith("standard/"))
    d = sum(x["success"] for n, x in e.items() if n.startswith("dr/"))
    print(f"| {k} | {s}/6 | {d}/6 |")
print()
print("판정:", json.dumps({k: v.get(k) for k in ("G_bench", "Q1", "Q1_task_arms", "Q1_progress", "Q2", "Q2_detail", "Q3",
                                               "n_ok")}, ensure_ascii=False))
