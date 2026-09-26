"""Markdown tables for docs/stage3/results/prompt_health.md from analyze.py's JSON (so numbers are not copied by
hand). usage: python tools/prompt_health/report_tables.py res.json > tables.md"""
from __future__ import annotations

import json
import sys


def kn(v) -> str:
    return "—" if not v or v.get("n") in (None, 0) else f"{v['k']}/{v['n']}"


def _hot(out: dict, base: str, field: str) -> str:
    """Temperature 0.7 samples: summed flips against the temperature-0 base over all reps."""
    k = n = 0
    for c, s in out.items():
        if c.startswith(f"{base}@t0.7"):
            f = (s["flip_vs_base"] or {}).get(field) or {}
            k, n = k + f.get("k", 0), n + f.get("n", 0)
    return f"{k}/{n}" if n else "—"


def grasp(res: dict) -> str:
    L = ["| 모델 | 조건 | 파싱 실패 | 판정 뒤집힘(기준 대비) | 거짓 '잡음'(안 쥠) | 놓친 '잡음'(쥠) | uncertain |",
         "|---|---|---|---|---|---|---|"]
    for key, out in res.items():
        if not key.startswith("grasp|"):
            continue
        for c, s in out.items():
            if "@t0.7" in c:
                continue
            t = s["truth"]
            fl = (s["flip_vs_base"] or {}).get("grasp_state")
            L.append(f"| {key.split('|')[1]} | {c} | {kn(s['parse_fail'])} | {kn(fl)} | {kn(t['false_grasped'])} | "
                     f"{kn(t['missed_grasped'])} | {t['uncertain']} |")
        if any("@t0.7" in c for c in out):
            L.append(f"| {key.split('|')[1]} | base@t0.7 × 3 | — | {_hot(out, 'base', 'grasp_state')} | — | — | — |")
    return "\n".join(L)


def couple(res: dict) -> str:
    L = ["| 시험 · 모델 | 조건 | 파싱 실패 | 뒤집힘 execution / intent / command / 잡기 주장 | 명령 정답(오라클) | "
         "거짓 '잡음' 주장(안 쥠) | 없는 화살표 인용 | edit 수(게이트 전) |", "|---|---|---|---|---|---|---|---|"]
    for key, out in res.items():
        if not key.startswith("couple"):
            continue
        for c, s in out.items():
            if "@t0.7" in c:
                continue
            t = s["truth"]
            fl = s["flip_vs_base"]
            ftxt = "—" if fl is None else " / ".join(kn(fl[f]) for f in ("execution", "intent", "command", "claim_raw"))
            L.append(f"| {key.replace('|', ' · ')} | {c} | {kn(s['parse_fail'])} | {ftxt} | {kn(t['cmd_acc_raw'])} | "
                     f"{kn(t['false_claim_raw'])} | {kn(t['cites_absent_arrow'])} | {t['edit_raw']} |")
        if any("@t0.7" in c for c in out):
            hot = " / ".join(_hot(out, "base", f) for f in ("execution", "intent", "command", "claim_raw"))
            L.append(f"| {key.replace('|', ' · ')} | base@t0.7 × 3 | — | {hot} | — | — | — | — |")
    return "\n".join(L)


def frame(res: dict) -> str:
    L = ["| 모델 | 조건 | 파싱 실패 | xy 방향 정답(< 60°) | xy 오차 중앙(°) | x 부호 일치 | y 부호 일치 | 5 cm 초과 | "
         "기준 대비 방향 뒤집힘(> 90°) |", "|---|---|---|---|---|---|---|---|---|"]
    for key, out in res.items():
        if not key.startswith("frame|"):
            continue
        for c, s in out.items():
            if "@t0.7" in c:
                continue
            t = s["truth"]
            fl = (s["flip_vs_base"] or {}).get("dir_flip_gt90_vs_base")
            L.append(f"| {key.split('|')[1]} | {c} | {kn(s['parse_fail'])} | {kn(t['xy_ok_lt60'])} | "
                     f"{t['xy_err_deg_median']} | {kn(t['x_sign_agree'])} | {kn(t['y_sign_agree'])} | {t['over_limit']} | "
                     f"{kn(fl)} |")
    return "\n".join(L)


def main():
    res = json.load(open(sys.argv[1], encoding="utf-8"))
    sys.stdout.reconfigure(encoding="utf-8")
    print("### 잡기 질문(G 집합 40장)\n" + grasp(res) + "\n")
    print("### 결합 프롬프트 astra-couple@v1(G 집합 40장 · R 집합 60장)\n" + couple(res) + "\n")
    print("### 방향 질문(R 집합 approach 60장; Astra는 앞 30장)\n" + frame(res))


if __name__ == "__main__":
    main()
