"""PaceNotes figures (2026-09-27 figure pass): Fig. 1 overview, joystick-VLA model, evidence plot, eval protocol.
Reuses the style helpers of make_figs.py (pastel rounded boxes, thin gray elbow arrows).
Numbers come only from docs/stage3/results (teach_l8.md, open_vlm_solo.md, astra_solo_pilot.md) and canon §90/§91/§96.
Run (D drive only for caches):
  MPLCONFIGDIR=D:/tools/mplcache <python with matplotlib> paper/figures/src/make_figs_pn.py
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_figs as mf  # noqa: E402  (style, helpers, fonts)
from make_figs import (plt, FancyBboxPatch, Rectangle, Circle, Polygon, PAL, ARROW, TXT, FULL_W, COL_W,
                       canvas, rbox, pill, arr, icon_robot, icon_scene, save, TENT)

UP = PAL["astra"]     # upper planner (co-driver): orange
VL = PAL["jev"]       # VLA (driver): blue
EX = PAL["skill"]     # action expert / execution: green
VER = PAL["crit"]     # verification: rose
DAT = PAL["mem"]      # data: purple


def note(ax, x, y, w, h, text, fs=6.3, ec=None, fc="white", tc=TXT, bold=False):
    ec = ec or UP[1]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.04", fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", linespacing=1.15)


def check(ax, x, y, s=0.05, c="#2E7D32"):
    ax.plot([x - s, x - s * 0.3, x + s], [y, y - s * 0.7, y + s * 0.9], color=c, lw=1.6, solid_capstyle="round")


# ================================================================ Fig. 1 PaceNotes overview
def fig_overview():
    W = FULL_W
    H = 4.55
    fig, ax = canvas(W, H)

    # ---------------- (a) roles
    top = H - 0.05
    ax.text(0.04, top, "(a) 역할: 코드라이버와 드라이버", fontsize=8, va="top", color=TXT, fontweight="bold")
    # upper planner panel
    px, py, pw, ph = 0.05, 2.30, 2.55, 1.95
    ax.add_patch(FancyBboxPatch((px, py), pw, ph, boxstyle="round,pad=0,rounding_size=0.06", fc=UP[0], ec=UP[1], lw=1.3))
    ax.text(px + 0.10, py + ph - 0.10, "상위 계획기 = 코드라이버", fontsize=8.2, va="top", color=TXT, fontweight="bold")
    ax.text(px + 0.10, py + ph - 0.33, "Astra (지금) → 학습한 8B·35B (목표)", fontsize=6.0, va="top", color="#6A4A2A")
    ax.text(px + 0.10, py + ph - 0.55, "구간 의도를 먼저 선언", fontsize=6.4, va="top", color="#333")
    ny = py + 0.80
    notes = ["지금: 접근\n머그로", "지금: 잡기\n할 일: 쥐기", "지금: 나르기\n다음: 놓기"]
    nx = px + 0.12
    for i, t in enumerate(notes):
        note(ax, nx + i * 0.80, ny, 0.70, 0.40, t, fs=5.9)
        if i < 2:
            arr(ax, [(nx + i * 0.80 + 0.70, ny + 0.20), (nx + (i + 1) * 0.80, ny + 0.20)], lw=0.8)
    # verify badge
    ax.add_patch(FancyBboxPatch((px + 0.12, py + 0.15), pw - 0.24, 0.55, boxstyle="round,pad=0,rounding_size=0.04",
                                fc=VER[0], ec=VER[1], lw=1.0))
    ax.text(px + 0.22, py + 0.52, "결과를 검증하고 다음 노트", fontsize=6.4, va="center", color=TXT, fontweight="bold")
    ax.text(px + 0.22, py + 0.30, "잡음 확인 (근거: T1 고유 감각 · V1h 확인 헤드)", fontsize=5.8, va="center", color="#444")
    check(ax, px + pw - 0.30, py + 0.42)

    # VLA panel
    vx, vy, vw, vh = 4.25, 2.30, 2.58, 1.95
    ax.add_patch(FancyBboxPatch((vx, vy), vw, vh, boxstyle="round,pad=0,rounding_size=0.06", fc=VL[0], ec=VL[1], lw=1.3))
    ax.text(vx + 0.10, vy + vh - 0.10, "VLA = 드라이버", fontsize=8.2, va="top", color=TXT, fontweight="bold")
    ax.text(vx + 0.10, vy + vh - 0.33, "조이스틱 VLA (Qwen3-VL-4B)", fontsize=6.0, va="top", color="#2F4F7A")
    note(ax, vx + 0.12, vy + 1.03, vw - 0.24, 0.40,
         "0.33 s마다 닫힌 보기 선택\n방향 · 크기 · 대상 · 단계 · 그리퍼", fs=6.0, ec=VL[1])
    note(ax, vx + 0.12, vy + 0.58, vw - 0.24, 0.34, "쥐기·놓기 시점은 VLA가 정함 (T1 관문 허가)", fs=6.0, ec=VL[1])
    rbox(ax, vx + 0.12, vy + 0.12, 1.55, 0.36, "skill", "행동 전문가 → 0.5 s 관절 청크", fs=6.0)
    icon_robot(ax, vx + 2.20, vy + 0.10, s=0.62)

    # middle: messages + reconciliation
    mx0, mx1 = px + pw + 0.05, vx - 0.05
    arr(ax, [(mx0, 3.85), (mx1, 3.85)], color=UP[1], lw=1.1)
    ax.text((mx0 + mx1) / 2, 3.90, "구간 의도 (now · do · next)\n+ 말단 수정", ha="center", va="bottom", fontsize=6.0, color=UP[1])
    arr(ax, [(mx1, 2.62), (mx0, 2.62)], color=VER[1], lw=1.1)
    ax.text((mx0 + mx1) / 2, 2.57, "실제 움직임 · 결과", ha="center", va="top", fontsize=6.0, color=VER[1])
    ax.add_patch(FancyBboxPatch((mx0 + 0.08, 2.95), mx1 - mx0 - 0.16, 0.66, boxstyle="round,pad=0,rounding_size=0.04",
                                fc="white", ec="#6F6F6F", lw=0.9))
    ax.text((mx0 + mx1) / 2, 3.46, "도착 시 대조", ha="center", va="center", fontsize=6.5, color=TXT, fontweight="bold")
    ax.text((mx0 + mx1) / 2, 3.16, "이미 됨 · 아직 유효\n상황 바뀜 · 충돌", ha="center", va="center", fontsize=5.7,
            color="#444", linespacing=1.15)

    # ---------------- (b) timeline
    ty0 = 1.05
    ax.text(0.04, 2.18, "(b) 한 편의 시간 축 (예시)", fontsize=8, va="top", color=TXT, fontweight="bold")
    x0, x1, T = 1.30, 6.80, 24.0
    X = lambda t: x0 + t * (x1 - x0) / T
    lanes = [("상위 계획기", 1.78), ("VLA (0.33 s)", 1.50), ("거리 권한 a", 1.22)]
    for name, yy in lanes:
        ax.text(x0 - 0.08, yy, name, ha="right", va="center", fontsize=6.2, color="#333")
        ax.plot([x0, x1], [yy, yy], color="#E6E6E6", lw=0.8, zorder=0)
    # upper calls (L ~ 9 s): answers carry the next intent
    calls = [(0.0, 3.0, "첫 계획: 접근"), (3.0, 12.0, "요청 1 → \"이번엔 잡기\""), (12.0, 21.0, "요청 2 → 검증 + \"나르기\"")]
    for a, b, t in calls:
        pill(ax, X(a), 1.71, (b - a) * (x1 - x0) / T - 0.02, 0.14, "astra", t, fs=5.6)
    # arrivals: reconciliation marker
    for tt in [12.0, 21.0]:
        ax.plot([X(tt), X(tt)], [1.30, 1.70], color="#6F6F6F", lw=0.7, ls=(0, (2, 1.5)))
        ax.text(X(tt) + 0.03, 1.66, "대조", fontsize=5.2, color="#555", va="top")
    # VLA ticks
    t = 3.0
    while t < T - 0.1:
        ax.plot([X(t), X(t)], [1.45, 1.55], color=VL[1], lw=0.5)
        t += 0.66
    # grasp timing chosen by VLA
    ax.add_patch(Circle((X(14.5), 1.50), 0.055, fc=VL[1], ec="white", lw=0.6, zorder=5))
    ax.text(X(14.5), 1.38, "VLA가 쥐는 시점", ha="center", va="top", fontsize=5.4, color=VL[1])
    # verification on the next answer
    check(ax, X(21.0) + 0.14, 1.89, s=0.035)
    ax.text(X(21.0) + 0.22, 1.90, "잡음 검증", fontsize=5.4, color=VER[1], va="center")
    # authority a(t): far = 1, near the mug = 0, after lift = 1
    segs = [(0.0, 11.0, 1.0), (11.0, 11.8, 0.5), (11.8, 16.5, 0.0), (16.5, 17.2, 0.5), (17.2, 24.0, 1.0)]
    for a, b, v in segs:
        ax.add_patch(Rectangle((X(a), 1.15), (b - a) * (x1 - x0) / T, 0.14 * v + 0.004,
                               fc=UP[0] if v > 0 else "white", ec=UP[1] if v > 0 else "none", lw=0.5))
    ax.text(X(5.5), 1.12, "a = 1 먼 구간: 상위 수정 반영", ha="center", va="top", fontsize=5.4, color=UP[1])
    ax.text(X(14.2), 1.12, "a = 0 접촉 근처: VLA만", ha="center", va="top", fontsize=5.4, color=VL[1])
    for tk in [0, 6, 12, 18, 24]:
        ax.text(X(tk), 0.93, f"{tk} s", ha="center", va="center", fontsize=5.4, color="#777")

    # ---------------- (c) training band
    ax.text(0.04, 0.84, "(c) 학습", fontsize=8, va="top", color=TXT, fontweight="bold")
    bw, bh, by = 2.16, 0.60, 0.05
    bx = [0.05, 2.36, 4.67]
    rbox(ax, bx[0], by, bw, bh, "astra", "상위 계획기 증류", fs=6.6, bold=True,
         sub="Astra·시뮬 참값 선생 → 학생이 간 상태에 라벨\n8B 대리 → 35B (DAgger식, LoRA)", sfs=5.5)
    rbox(ax, bx[1], by, bw, bh, "jev", "VLA 끝-끝 학습", fs=6.6, bold=True,
         sub="조이스틱 역할: 결정 + 행동 전문가(KI)\n먼 구간 반사실 분기, 의도 교란", sfs=5.5)
    rbox(ax, bx[2], by, bw, bh, "mem", "다양화 데이터", fs=6.6, bold=True,
         sub="다양화 시뮬 + 좌표계 없는 공개 데이터\n점 추적 → 픽셀 경로 · 자기 보정", sfs=5.5)
    save(fig, "overview")


# ================================================================ model (joystick VLA) -- column width
def fig_model():
    W, H = COL_W, 2.95
    fig, ax = canvas(W, H)
    # upper planner (top)
    rbox(ax, 0.05, 2.45, 3.15, 0.42, "astra", "상위 계획기", fs=7.0, bold=True,
         sub="구간 의도(now · do · next)를 선언, 결과를 검증", sfs=5.6)
    # inputs
    icon_scene(ax, 0.05, 1.55, 0.50, 0.36, "std")
    ax.text(0.30, 1.51, "머리", ha="center", va="top", fontsize=5.6, color="#444")
    icon_scene(ax, 0.05, 1.00, 0.50, 0.36, "rnd")
    ax.text(0.30, 0.96, "활성 손목", ha="center", va="top", fontsize=5.6, color="#444")
    note(ax, 0.02, 0.28, 0.58, 0.50, "과제 문장\n구간 의도 줄\n그리퍼 · 움직임", fs=5.4, ec="#9A9A9A")
    # backbone
    bx, bw = 0.78, 1.50
    ax.add_patch(FancyBboxPatch((bx, 0.28), bw, 1.98, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=VL[0], ec=VL[1], lw=1.2))
    ax.text(bx + bw / 2, 2.17, "조이스틱 VLA", ha="center", va="top", fontsize=7.0, fontweight="bold", color=TXT)
    ax.text(bx + bw / 2, 1.97, "Qwen3-VL-4B (영상 탑 동결, LoRA)", ha="center", va="top", fontsize=5.3, color="#2F4F7A")
    note(ax, bx + 0.08, 1.24, bw - 0.16, 0.50, "decide: typed 결정\n방향·크기·대상·단계·그리퍼", fs=5.5, ec=VL[1])
    note(ax, bx + 0.08, 0.80, bw - 0.16, 0.34, "확인 헤드 V1h (세계 쪽 술어)", fs=5.5, ec=VER[1])
    rbox(ax, bx + 0.08, 0.36, bw - 0.16, 0.34, "skill", "행동 전문가 (sg[h])", fs=5.6)
    for yy in [1.73, 1.18, 0.53]:
        arr(ax, [(0.60, yy), (bx, yy)], lw=0.8)
    # intent from upper
    arr(ax, [(0.9, 2.45), (0.9, 2.26)], color=UP[1], lw=0.9)
    # right column: M4, chunk, robot, verification back
    rbox(ax, 2.45, 1.30, 0.75, 0.42, "rule", "M4 확정", fs=6.2, sub="합의 + 측정", sfs=5.2)
    arr(ax, [(bx + bw, 1.49), (2.45, 1.49)], lw=0.8)
    arr(ax, [(2.62, 1.30), (2.62, 0.75), (2.10, 0.75), (2.10, 0.70)], lw=0.8)
    ax.text(2.70, 1.02, "확정 결정", ha="left", va="center", fontsize=5.2, color="#555")
    arr(ax, [(bx + bw, 0.53), (2.42, 0.53)], lw=0.8)
    ax.text(2.46, 0.53, "0.5 s 청크\n→ 안전 투영", ha="left", va="center", fontsize=5.3, color="#444")
    icon_robot(ax, 2.95, 0.02, s=0.36)
    # verification back up
    arr(ax, [(3.12, 1.72), (3.12, 2.45)], color=VER[1], lw=0.9)
    ax.text(3.08, 2.08, "검증\n(T1·V1h)", ha="right", va="center", fontsize=5.2, color=VER[1])
    save(fig, "model")


# ================================================================ evidence: closed-loop approach error per episode
def fig_evidence():
    W, H = COL_W, 2.15
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0.16, 0.24, 0.80, 0.66])
    # per-episode median commanded approach-target xy error (mm), same astra-solo@v2 interface, DEV seeds 0-1 x std/dr
    data = [
        ("Qwen3-VL-8B\n영샷", [389.5, 487.2, 149.3, 145.4], "0/4", "#9A9A9A"),   # teach_l8.md §3
        ("gpt-5.2 대리\n영샷", [206.7, 202.0, 103.6, 167.4], "0/4", "#9A9A9A"),  # open_vlm_solo.md §2
        ("Astra low\n(프런티어)", [2.6, 48.9, 21.0, 7.2], "4/4", UP[1]),          # astra_solo_pilot.md §3 (pilot)
        ("Qwen3-VL-8B\n시뮬 참값 LoRA", [19.0, 18.2, 8.4, 7.7], "4/4", VL[1]),    # teach_l8.md §3
    ]
    rng = np.random.default_rng(0)
    for i, (name, vals, succ, c) in enumerate(data):
        xs = i + rng.uniform(-0.12, 0.12, len(vals))
        ax.scatter(xs, vals, s=14, color=c, zorder=3, edgecolors="white", linewidths=0.4)
        med = float(np.median(vals))
        ax.plot([i - 0.25, i + 0.25], [med, med], color=c, lw=1.6, zorder=2)
        ax.text(i, 900, f"성공 {succ}", ha="center", va="center", fontsize=6.2, color=c, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylim(1.5, 1500)
    ax.axhline(20, color="#BBBBBB", lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.text(3.45, 22, "20 mm", fontsize=5.4, color="#888", va="bottom", ha="right")
    ax.set_xticks(range(len(data)))
    ax.set_xticklabels([d[0] for d in data], fontsize=5.6)
    ax.set_xlim(-0.5, len(data) - 0.5)
    ax.set_ylabel("접근 목표 xy 오차 (mm, 로그)", fontsize=6.0)
    ax.tick_params(axis="y", labelsize=5.6)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    save(fig, "evidence")


# ================================================================ eval protocol (paired RD)
def fig_eval():
    W, H = COL_W, 1.95
    fig, ax = canvas(W, H)
    icon_scene(ax, 0.04, 1.08, 0.56, 0.42, "std")
    icon_scene(ax, 0.04, 0.40, 0.56, 0.42, "rnd")
    ax.text(0.32, 1.54, "standard", ha="center", va="bottom", fontsize=6.2, color="#444")
    ax.text(0.32, 0.36, "random", ha="center", va="top", fontsize=6.2, color="#444")
    ax.text(0.32, 0.96, "같은 layout 짝", ha="center", va="center", fontsize=6.0, color="#555")
    ax.add_patch(FancyBboxPatch((0.80, 0.22), 1.55, 1.50, boxstyle="round,pad=0,rounding_size=0.05",
                                fc="none", ec="#BDBDBD", lw=0.9, ls=(0, (3, 2))))
    ax.text(1.575, 1.66, "바꾸는 축", ha="center", va="top", fontsize=6.4, color="#333", fontweight="bold")
    rbox(ax, 0.88, 1.12, 1.39, 0.36, "astra", "상위: Astra · 8B · 35B · 끔", fs=6.0)
    rbox(ax, 0.88, 0.70, 1.39, 0.36, "jev", "구성: VLA · 상위 · 상위+VLA", fs=6.0)
    rbox(ax, 0.88, 0.28, 1.39, 0.36, "gray", "기준선: π0.5 · 코드 정책 · 규칙", fs=5.8)
    arr(ax, [(0.60, 1.29), (0.70, 1.29), (0.70, 0.97), (0.80, 0.97)])
    arr(ax, [(0.60, 0.61), (0.70, 0.61), (0.70, 0.97)], head=False)
    rbox(ax, 2.52, 0.62, 0.70, 0.70, "rule", "RD", fs=9, sub="1 − 성공(rnd)\n÷ 성공(std)", sfs=6.0)
    arr(ax, [(2.35, 0.97), (2.52, 0.97)])
    ax.text(W / 2, 0.08, "시계 두 가지: 지연 충실 · 동기 공정(생각 시간 공짜)", ha="center", va="center",
            fontsize=6.0, color="#333")
    save(fig, "eval_protocol")


if __name__ == "__main__":
    fig_overview()
    fig_model()
    fig_evidence()
    fig_eval()
    print("ok")
