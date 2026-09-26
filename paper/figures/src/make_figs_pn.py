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


# ================================================================ Fig. 1 PaceNotes overview (staged: co-driver first)
def dbox(ax, x, y, w, h, fc, ec, lw=1.2):
    """dashed rounded box = planned / conditional part"""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06", fc=fc, ec=ec, lw=lw,
                                ls=(0, (4, 2.5))))


def fig_overview():
    W = FULL_W
    H = 5.0
    fig, ax = canvas(W, H)

    # ---------------- (a) roles
    ax.text(0.04, H - 0.05, "(a) 코드라이버 먼저: 1단계는 상위 + 실행기, VLA는 한계가 확인될 때만", fontsize=8, va="top",
            color=TXT, fontweight="bold")
    py, ph = 2.75, 1.95
    # upper planner panel (stage 1, solid)
    px, pw = 0.05, 2.40
    ax.add_patch(FancyBboxPatch((px, py), pw, ph, boxstyle="round,pad=0,rounding_size=0.06", fc=UP[0], ec=UP[1], lw=1.3))
    ax.text(px + 0.10, py + ph - 0.10, "상위 계획기 = 코드라이버", fontsize=8.0, va="top", color=TXT, fontweight="bold")
    ax.text(px + 0.10, py + ph - 0.33, "Astra (지금) → 학습한 8B·35B (목표)", fontsize=5.9, va="top", color="#6A4A2A")
    ax.text(px + 0.10, py + ph - 0.55, "구간 의도를 선언하고 움직임까지 지시", fontsize=6.2, va="top", color="#333")
    ny = py + 0.80
    notes = ["지금: 접근\n머그로", "지금: 잡기\n할 일: 쥐기", "지금: 나르기\n다음: 놓기"]
    nx = px + 0.10
    for i, t in enumerate(notes):
        note(ax, nx + i * 0.76, ny, 0.66, 0.40, t, fs=5.7)
        if i < 2:
            arr(ax, [(nx + i * 0.76 + 0.66, ny + 0.20), (nx + (i + 1) * 0.76, ny + 0.20)], lw=0.8)
    ax.add_patch(FancyBboxPatch((px + 0.10, py + 0.15), pw - 0.20, 0.55, boxstyle="round,pad=0,rounding_size=0.04",
                                fc=VER[0], ec=VER[1], lw=1.0))
    ax.text(px + 0.20, py + 0.52, "결과를 검증하고 다음 노트", fontsize=6.3, va="center", color=TXT, fontweight="bold")
    ax.text(px + 0.20, py + 0.30, "잡음 확인 (근거: T1 고유 감각)", fontsize=5.8, va="center", color="#444")
    check(ax, px + pw - 0.28, py + 0.42)

    # executor (stage 1, solid green)
    ex0, ew = 2.62, 1.40
    ax.add_patch(FancyBboxPatch((ex0, py + 0.55), ew, 1.10, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=EX[0], ec=EX[1], lw=1.2))
    ax.text(ex0 + ew / 2, py + 1.50, "결정적 실행기", ha="center", va="center", fontsize=7.0, color=TXT, fontweight="bold")
    ax.text(ex0 + ew / 2, py + 1.10, "명령을 최소 저크\n직선 운동으로 수행\n끝나면 새 영상으로\n다시 묻는다",
            ha="center", va="center", fontsize=5.6, color="#333", linespacing=1.2)
    icon_robot(ax, ex0 + ew / 2 - 0.08, py + 0.05, s=0.55)
    arr(ax, [(px + pw, py + 1.45), (ex0, py + 1.45)], color=UP[1], lw=1.0)
    ax.text((px + pw + ex0) / 2, py + 1.50, "명령", ha="center", va="bottom", fontsize=5.4, color=UP[1])
    arr(ax, [(ex0, py + 0.75), (px + pw, py + 0.75)], color=VER[1], lw=1.0)
    ax.text((px + pw + ex0) / 2, py + 0.70, "측정", ha="center", va="top", fontsize=5.4, color=VER[1])

    # VLA panel (stage 2, dashed = conditional)
    vx, vw = 4.18, 2.65
    dbox(ax, vx, py, vw, ph, "#EEF4FB", VL[1])
    ax.text(vx + 0.10, py + ph - 0.10, "2단계(조건부): VLA = 드라이버", fontsize=7.6, va="top", color="#2F4F7A",
            fontweight="bold")
    ax.text(vx + 0.10, py + ph - 0.33, "기다림 실패·벽시계 등 한계가 측정될 때만", fontsize=5.8, va="top", color="#2F4F7A")
    note(ax, vx + 0.10, py + 1.06, vw - 0.20, 0.36, "코드: 상위 목표 → 매 0.33 s VLA 결정 칸으로 변환", fs=5.6,
         ec="#6F6F6F")
    note(ax, vx + 0.10, py + 0.62, vw - 0.20, 0.36, "VLA 자기 결정과 늘 연속 혼합 (답 나이·확신·가시성)\n쥐는 시점은 VLA, 상위가 검증", fs=5.4,
         ec=VL[1])
    note(ax, vx + 0.10, py + 0.16, vw - 0.20, 0.36, "행동 전문가 → 0.4 s 관절 청크", fs=5.8, ec=EX[1], fc=EX[0])
    arr(ax, [(ex0 + ew, py + 1.30), (vx, py + 1.30)], color="#7A96C0", lw=0.9, ls=(0, (3, 2)))
    ax.text((ex0 + ew + vx) / 2, py + 1.35, "대체", ha="center", va="bottom", fontsize=5.2, color="#7A96C0")

    # ---------------- (b) timeline
    ax.text(0.04, 2.66, "(b) 한 편의 시간 축 (예시)", fontsize=8, va="top", color=TXT, fontweight="bold")
    x0, x1, T = 1.40, 6.80, 24.0
    X = lambda t: x0 + t * (x1 - x0) / T
    sx = (x1 - x0) / T
    # stage 1 lane: think (robot waits) / executor motion
    y1 = 2.28
    ax.text(x0 - 0.08, y1, "1단계: 상위 + 실행기", ha="right", va="center", fontsize=6.0, color="#333")
    cyc = [(0.0, 1.2, "t"), (1.2, 4.6, "m"), (4.6, 5.8, "t"), (5.8, 8.4, "m"), (8.4, 9.6, "t"), (9.6, 11.4, "m"),
           (11.4, 12.6, "t"), (12.6, 15.8, "m"), (15.8, 17.0, "t"), (17.0, 20.6, "m"), (20.6, 21.8, "t"),
           (21.8, 24.0, "m")]
    for a, b, k in cyc:
        if k == "t":
            ax.add_patch(Rectangle((X(a), y1 - 0.06), (b - a) * sx, 0.12, fc="#F2F2F2", ec="#9A9A9A", lw=0.5,
                                   hatch="////"))
        else:
            ax.add_patch(Rectangle((X(a), y1 - 0.06), (b - a) * sx, 0.12, fc=EX[0], ec=EX[1], lw=0.6))
    ax.text(X(12.0), y1 - 0.10, "빗금 = 상위가 생각하는 동안 로봇 대기   초록 = 실행기 운동   (대기가 한계 후보)",
            ha="center", va="top", fontsize=5.2, color="#555")
    # stage 2 lanes (dashed group)
    dy = 0.14
    dbox(ax, 0.05, 1.02, 6.78, 1.05, "none", "#7A96C0", lw=0.9)
    ax.text(0.12, 2.03, "2단계(조건부)", fontsize=5.8, va="top", color="#2F4F7A", fontweight="bold")
    lanes = [("상위 계획기", 1.78 + dy - 0.06), ("VLA (0.33 s)", 1.50 + dy - 0.06), ("상위 목표 가중", 1.22 + dy - 0.06)]
    for name, yy in lanes:
        ax.text(x0 - 0.08, yy, name, ha="right", va="center", fontsize=6.0, color="#333")
        ax.plot([x0, x1], [yy, yy], color="#E6E6E6", lw=0.8, zorder=0)
    yu, yv, ya = lanes[0][1], lanes[1][1], lanes[2][1]
    calls = [(0.0, 3.0, "목표: 머그 위"), (3.0, 12.0, "요청 1 → 목표: 머그 + \"잡기\""), (12.0, 21.0, "요청 2 → 검증 + 목표: 쟁반")]
    for a, b, t in calls:
        pill(ax, X(a), yu - 0.07, (b - a) * sx - 0.02, 0.14, "astra", t, fs=5.4)
    t = 3.0
    while t < T - 0.1:
        ax.plot([X(t), X(t)], [yv - 0.05, yv + 0.05], color=VL[1], lw=0.5)
        t += 0.66
    ax.add_patch(Circle((X(14.5), yv), 0.05, fc=VL[1], ec="white", lw=0.6, zorder=5))
    ax.text(X(14.5), yv - 0.09, "VLA가 쥐는 시점", ha="center", va="top", fontsize=5.2, color=VL[1])
    check(ax, X(21.0) + 0.14, yu + 0.11, s=0.03)
    ax.text(X(21.0) + 0.21, yu + 0.12, "잡음 검증", fontsize=5.2, color=VER[1], va="center")
    # continuous blend weight of the upper-derived decision: high after a fresh answer, decays with answer age,
    # lower while the VLA itself sees the target up close (illustrative, not measured)
    import numpy as _np
    tt = _np.linspace(0.0, 24.0, 400)
    last = _np.where(tt < 3.0, 0.0, _np.where(tt < 12.0, 3.0, _np.where(tt < 21.0, 12.0, 21.0)))
    w = 0.85 * _np.exp(-(tt - last) / 9.0)
    w = w * (1.0 - 0.55 * _np.exp(-((tt - 14.5) / 2.2) ** 2))
    ax.fill_between([X(v) for v in tt], ya - 0.07, ya - 0.07 + 0.15 * w, color=UP[0], lw=0)
    ax.plot([X(v) for v in tt], ya - 0.07 + 0.15 * w, color=UP[1], lw=0.8)
    ax.text(X(6.0), ya - 0.10, "새 답 직후 크고 답 나이에 따라 줄어듦", ha="center", va="top", fontsize=5.2, color=UP[1])
    ax.text(X(15.0), ya - 0.10, "VLA가 목표를 가까이 볼 때 VLA 쪽으로 (스위치 아님)", ha="center", va="top", fontsize=5.2, color=VL[1])
    for tk in [0, 6, 12, 18, 24]:
        ax.text(X(tk), 0.93, f"{tk} s", ha="center", va="center", fontsize=5.2, color="#777")

    # ---------------- (c) training band
    ax.text(0.04, 0.84, "(c) 학습", fontsize=8, va="top", color=TXT, fontweight="bold")
    bw, bh, by = 2.16, 0.60, 0.05
    bx = [0.05, 2.36, 4.67]
    rbox(ax, bx[0], by, bw, bh, "astra", "상위 계획기 증류 (주 기여)", fs=6.4, bold=True,
         sub="Astra·시뮬 참값 선생 → 학생이 간 상태에 라벨\n8B 대리 → 35B, m 좌표 없는 출력, 손으로 준 정보 제거", sfs=5.2)
    rbox(ax, bx[1], by, bw, bh, "mem", "다양화 데이터", fs=6.4, bold=True,
         sub="다양화 시뮬 + 좌표계 없는 공개 데이터\n점 추적 → 픽셀 경로 · 자기 보정", sfs=5.4)
    dbox(ax, bx[2], by, bw, bh, "#EEF4FB", VL[1])
    ax.text(bx[2] + bw / 2, by + bh * 0.66, "VLA 끝-끝 학습 (조건부)", ha="center", va="center", fontsize=6.4,
            color=TXT, fontweight="bold")
    ax.text(bx[2] + bw / 2, by + bh * 0.28, "결정 + 행동 전문가(KI)\n먼 구간 반사실 분기, 의도 교란", ha="center",
            va="center", fontsize=5.4, color="#555", linespacing=1.25)
    save(fig, "overview")


# ================================================================ model (joystick VLA) -- column width
def fig_model():
    W, H = COL_W, 2.95
    fig, ax = canvas(W, H)
    # upper planner (top)
    rbox(ax, 0.05, 2.45, 3.15, 0.42, "astra", "상위 계획기 (원래 형식)", fs=7.0, bold=True,
         sub="손끝 목표 xyz + 그리퍼 의도, 결과를 검증", sfs=5.6)
    # inputs
    icon_scene(ax, 0.05, 1.55, 0.50, 0.36, "std")
    ax.text(0.30, 1.51, "머리", ha="center", va="top", fontsize=5.6, color="#444")
    icon_scene(ax, 0.05, 1.00, 0.50, 0.36, "rnd")
    ax.text(0.30, 0.96, "활성 손목", ha="center", va="top", fontsize=5.6, color="#444")
    note(ax, 0.02, 0.28, 0.58, 0.50, "과제 문장\n그리퍼 상태\n움직임 줄", fs=5.4, ec="#9A9A9A")
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
    # upper target -> code conversion + blend (not a model)
    note(ax, 2.30, 1.86, 0.66, 0.40, "코드: 목표→결정\n변환 + 늘 섞기", fs=4.8, ec="#6F6F6F")
    arr(ax, [(2.63, 2.45), (2.63, 2.26)], color=UP[1], lw=0.9)
    arr(ax, [(2.62, 1.86), (2.62, 1.72)], color="#6F6F6F", lw=0.8)
    # right column: M4, chunk, robot, verification back
    rbox(ax, 2.45, 1.30, 0.75, 0.42, "rule", "M4 확정", fs=6.2, sub="합의 + 측정", sfs=5.2)
    arr(ax, [(bx + bw, 1.49), (2.45, 1.49)], lw=0.8)
    arr(ax, [(2.62, 1.30), (2.62, 0.75), (2.10, 0.75), (2.10, 0.70)], lw=0.8)
    ax.text(2.70, 1.02, "확정 결정", ha="left", va="center", fontsize=5.2, color="#555")
    arr(ax, [(bx + bw, 0.53), (2.42, 0.53)], lw=0.8)
    ax.text(2.46, 0.53, "0.4 s 청크\n→ 안전 투영", ha="left", va="center", fontsize=5.3, color="#444")
    icon_robot(ax, 2.95, 0.02, s=0.36)
    # verification back up
    arr(ax, [(3.12, 1.72), (3.12, 2.45)], color=VER[1], lw=0.9)
    ax.text(3.17, 2.06, "검증 (T1·V1h)", ha="left", va="center", fontsize=4.8, color=VER[1], rotation=90)
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
