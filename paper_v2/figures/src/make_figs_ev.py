"""paper_v2 evidence plot and evaluation protocol (copy of paper/figures/src/make_figs_pn.py, v2 content).
Style helpers come from paper/figures/src/make_figs.py; output goes to paper_v2/figures.
Evidence numbers = paper_v2/sec/9_evidence.tex.
Run (D drive only for caches):
  MPLCONFIGDIR=D:/tools/mplcache python paper_v2/figures/src/make_figs_ev.py [evidence eval]
"""
import os
import sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "paper", "figures", "src"))
import make_figs as mf  # noqa: E402  (style, helpers, fonts)
mf.OUT = os.path.dirname(_HERE)  # write into paper_v2/figures
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
    """dashed rounded box = stage-2 part (measured after the upper-only stage)"""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06", fc=fc, ec=ec, lw=lw,
                                ls=(0, (4, 2.5))))


def fig_overview():
    W = FULL_W
    H = 5.0
    fig, ax = canvas(W, H)

    # ---------------- (a) roles
    ax.text(0.04, H - 0.05, "(a) 명령은 코드라이버, 좁은 보정은 드라이버: 검증은 1단계 상위 단독부터", fontsize=8, va="top",
            color=TXT, fontweight="bold")
    py, ph = 2.75, 1.95
    # upper planner panel (stage 1, solid)
    px, pw = 0.05, 2.40
    ax.add_patch(FancyBboxPatch((px, py), pw, ph, boxstyle="round,pad=0,rounding_size=0.06", fc=UP[0], ec=UP[1], lw=1.3))
    ax.text(px + 0.10, py + ph - 0.10, "상위 계획기 = 코드라이버", fontsize=8.0, va="top", color=TXT, fontweight="bold")
    ax.text(px + 0.10, py + ph - 0.33, "본 35B: Qwen3.5-35B-A3B LoRA (학습한 상위)", fontsize=5.9, va="top", color="#6A4A2A")
    ax.text(px + 0.10, py + ph - 0.55, "명령 권한 전부: 구간 의도·목표·검증", fontsize=6.2, va="top", color="#333")
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

    # VLA panel (stage 2, dashed = measured after stage 1; the VLA is always-on in the target structure)
    vx, vw = 4.18, 2.65
    dbox(ax, vx, py, vw, ph, "#EEF4FB", VL[1])
    ax.text(vx + 0.10, py + ph - 0.10, "2단계: VLA = 좁은 조이스틱 드라이버", fontsize=7.6, va="top", color="#2F4F7A",
            fontweight="bold")
    ax.text(vx + 0.10, py + ph - 0.33, "상위가 허용한 범위 안에서만, 상위는 그사이 다음 명령", fontsize=5.8, va="top", color="#2F4F7A")
    note(ax, vx + 0.10, py + 1.06, vw - 0.20, 0.36, "맡는 일: 허용 범위 안 보정 · 쥐는 시점\n작은 회피 · 부딪힌 뒤 재정렬 + 이상 신호", fs=5.4,
         ec="#6F6F6F")
    note(ax, vx + 0.10, py + 0.62, vw - 0.20, 0.36, "상위: 사건 기반 조기 재질의 + 청크 겹침\n도착 전에 다음 명령 선발행 (안전 표지)", fs=5.4,
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
    ax.text(X(12.0), y1 - 0.10, "빗금 = 상위가 생각하는 동안 로봇 대기   초록 = 실행기 운동   (상위 단독 검증)",
            ha="center", va="top", fontsize=5.2, color="#555")
    # stage 2 lanes (dashed group)
    dy = 0.14
    dbox(ax, 0.05, 1.02, 6.78, 1.05, "none", "#7A96C0", lw=0.9)
    ax.text(0.12, 2.03, "2단계: 로봇은 기다리지 않고, VLA는 허용 범위 안에서만 보정", fontsize=5.8, va="top", color="#2F4F7A", fontweight="bold")
    lanes = [("상위 계획기", 1.78 + dy - 0.06), ("VLA (0.33 s)", 1.50 + dy - 0.06), ("VLA 보정 폭", 1.22 + dy - 0.06)]
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
    # the VLA correction stays inside the envelope set by the planner (illustrative, not measured)
    w = 0.5 + 0.35 * _np.sin(tt * 1.7) * _np.exp(-((tt - 14.5) / 4.0) ** 2) + 0.12 * _np.sin(tt * 0.9)
    w = _np.where(tt < 3.0, 0.5, w)
    ax.plot([X(3.0), X(T)], [ya - 0.07 + 0.15, ya - 0.07 + 0.15], color=UP[1], lw=0.7, ls=(0, (3, 2)))
    ax.plot([X(3.0), X(T)], [ya - 0.07, ya - 0.07], color=UP[1], lw=0.7, ls=(0, (3, 2)))
    ax.plot([X(v) for v in tt], ya - 0.07 + 0.15 * w, color=VL[1], lw=0.8)
    ax.text(X(6.0), ya - 0.10, "점선 = 상위가 정한 허용 범위", ha="center", va="top", fontsize=5.2, color=UP[1])
    ax.text(X(15.0), ya - 0.10, "VLA 보정은 이 안에서만 (명령 권한은 상위)", ha="center", va="top", fontsize=5.2, color=VL[1])
    for tk in [0, 6, 12, 18, 24]:
        ax.text(X(tk), 0.93, f"{tk} s", ha="center", va="center", fontsize=5.2, color="#777")

    # ---------------- (c) training band
    ax.text(0.04, 0.84, "(c) 학습", fontsize=8, va="top", color=TXT, fontweight="bold")
    bw, bh, by = 2.16, 0.60, 0.05
    bx = [0.05, 2.36, 4.67]
    rbox(ax, bx[0], by, bw, bh, "astra", "상위 계획기 학습 (주 기여)", fs=6.4, bold=True,
         sub="시뮬 참값 라벨 + 공개 점 라벨\n35B-A3B LoRA, 줄기 D", sfs=5.2)
    rbox(ax, bx[1], by, bw, bh, "mem", "다양화 데이터", fs=6.4, bold=True,
         sub="L8S 13.96만 행 (본 35B) → L9 (5배, 다음)\n공개 점 6.28만 행 (머리 시점, 반복 ≤2배)", sfs=5.2)
    dbox(ax, bx[2], by, bw, bh, "#EEF4FB", VL[1])
    ax.text(bx[2] + bw / 2, by + bh * 0.66, "VLA 단계별 학습 (본 35B 평가 뒤)", ha="center", va="center", fontsize=6.4,
            color=TXT, fontweight="bold")
    ax.text(bx[2] + bw / 2, by + bh * 0.28, "혼자 → 상위 오차·지연 주입\n→ 실제 명령 → 상위와 번갈아", ha="center",
            va="center", fontsize=5.4, color="#555", linespacing=1.25)
    save(fig, "overview")


# ================================================================ model (joystick VLA) -- column width
def fig_model():
    W, H = COL_W, 2.95
    fig, ax = canvas(W, H)
    # upper planner (top)
    rbox(ax, 0.05, 2.45, 3.15, 0.42, "astra", "상위 계획기 (원래 형식)", fs=7.0, bold=True,
         sub="점 + 높이 의도 → xyz(깊이), 명령 권한 전부", sfs=5.6)
    # inputs
    icon_scene(ax, 0.05, 1.55, 0.50, 0.36, "std")
    ax.text(0.30, 1.51, "머리", ha="center", va="top", fontsize=5.6, color="#444")
    icon_scene(ax, 0.05, 1.00, 0.50, 0.36, "rnd")
    ax.text(0.30, 0.96, "활성 손목", ha="center", va="top", fontsize=5.6, color="#444")
    note(ax, 0.02, 0.28, 0.58, 0.50, "구간 의도\n그리퍼 상태\n허용 범위", fs=5.4, ec="#9A9A9A")
    # backbone
    bx, bw = 0.78, 1.50
    ax.add_patch(FancyBboxPatch((bx, 0.28), bw, 1.98, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=VL[0], ec=VL[1], lw=1.2))
    ax.text(bx + bw / 2, 2.17, "좁은 조이스틱 VLA", ha="center", va="top", fontsize=7.0, fontweight="bold", color=TXT)
    ax.text(bx + bw / 2, 1.97, "Qwen3-VL-4B (영상 탑 동결, LoRA)", ha="center", va="top", fontsize=5.3, color="#2F4F7A")
    note(ax, bx + 0.08, 1.24, bw - 0.16, 0.50, "decide: 보정 방향·크기\n+ 쥐기 시점", fs=5.5, ec=VL[1])
    note(ax, bx + 0.08, 0.80, bw - 0.16, 0.34, "이상 신호 (이동·놓침·막힘)", fs=5.5, ec=VER[1])
    rbox(ax, bx + 0.08, 0.36, bw - 0.16, 0.34, "skill", "행동 전문가 (sg[h])", fs=5.6)
    for yy in [1.73, 1.18, 0.53]:
        arr(ax, [(0.60, yy), (bx, yy)], lw=0.8)
    # upper target -> code conversion + blend (not a model)
    note(ax, 2.30, 1.86, 0.66, 0.40, "코드: 목표→\n허용 범위\n(자르기)", fs=4.8, ec="#6F6F6F")
    arr(ax, [(2.63, 2.45), (2.63, 2.26)], color=UP[1], lw=0.9)
    arr(ax, [(2.62, 1.86), (2.62, 1.72)], color="#6F6F6F", lw=0.8)
    # right column: gate (T1 / V1h), chunk, robot, verification back
    rbox(ax, 2.45, 1.30, 0.75, 0.42, "rule", "관문", fs=6.2, sub="T1 허가", sfs=5.2)
    arr(ax, [(bx + bw, 1.49), (2.45, 1.49)], lw=0.8)
    arr(ax, [(2.62, 1.30), (2.62, 0.75), (2.10, 0.75), (2.10, 0.70)], lw=0.8)
    ax.text(2.70, 1.02, "허가된 결정", ha="left", va="center", fontsize=5.2, color="#555")
    arr(ax, [(bx + bw, 0.53), (2.42, 0.53)], lw=0.8)
    ax.text(2.46, 0.53, "0.4 s 청크\n→ 안전 투영", ha="left", va="center", fontsize=5.3, color="#444")
    icon_robot(ax, 2.95, 0.02, s=0.36)
    # verification back up
    arr(ax, [(3.12, 1.72), (3.12, 2.45)], color=VER[1], lw=0.9)
    ax.text(3.17, 2.06, "검증 (T1)", ha="left", va="center", fontsize=4.8, color=VER[1], rotation=90)
    save(fig, "model")


# ================================================================ evidence: current key evidence (all tentative)
def _ev_axis(ax, title):
    ax.set_title(title, fontsize=6.6, color=TXT, fontweight="bold", loc="left", pad=3)
    ax.tick_params(axis="both", labelsize=5.4, length=2, pad=1.5)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color("#9A9A9A")
        ax.spines[s].set_linewidth(0.6)


def fig_evidence():
    """Numbers = paper_v2/sec/9_evidence.tex (E-C35, E-L8SW, E-OPR3, main35 C35 -> ep0.25/0.5/1); 50 % L8SW point and the
    E-OPR3 per-ratio rates come from the verdict files (/data/harvest/out/l8sw/verdict.json,
    /data/harvest/out/opr2/verdict_stage3.json) and are also written in the text."""
    W, H = FULL_W, 2.05
    fig = plt.figure(figsize=(W, H))
    GR, OR = "#8C8C8C", TENT
    top, bot, hh = 0.83, 0.20, 0.63

    # (a) E-C35 vs f35_d: dumbbell, percent
    ax = fig.add_axes([0.085, bot, 0.175, hh])
    rows = [("새 물체 실패", 60.0, 36.0, False), ("L8-X dev 실패", 16.8, 27.5, False),
            ("OOD-H 실패", 17.3, 22.8, False), ("G Franka 적중*", 87.0, 45.0, True)]
    for i, (name, a, b, rep) in enumerate(rows):
        y = len(rows) - 1 - i
        c = "#B0B0B0" if rep else "#6F6F6F"
        ax.annotate("", xy=(b, y), xytext=(a, y),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=0.8, mutation_scale=6, shrinkA=2, shrinkB=2))
        ax.scatter([a], [y], s=12, color=GR, zorder=3, edgecolors="white", linewidths=0.4)
        ax.scatter([b], [y], s=12, color=OR, zorder=3, edgecolors="white", linewidths=0.4)
        lo, hi = (a, b) if a < b else (b, a)
        ax.text(lo - 3, y, f"{lo:g}", ha="right", va="center", fontsize=5.0, color=GR if lo == a else OR)
        ax.text(hi + 3, y, f"{hi:g}", ha="left", va="center", fontsize=5.0, color=GR if hi == a else OR)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=5.3)
    ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.set_xlim(0, 100)
    ax.set_xlabel("%", fontsize=5.4, labelpad=1)
    _ev_axis(ax, "(a) E-C35: f35_d → 확인판")
    fig.text(0.085 - 0.075, 0.045, "새 물체 중앙 40.9 → 9.6 mm · 회색 f35_d, 주황 확인판 · *3인칭, 보고만",
             fontsize=4.9, color="#555", ha="left")

    # (b) E-L8SW: L8S share 25/50/100 %
    ax = fig.add_axes([0.335, bot, 0.18, hh])
    xs = [25, 50, 100]
    newo = [30.0, 10.2, 10.2]
    held = [8.2, 6.6, 5.2]
    ax.plot(xs, newo, color=OR, lw=1.1, marker="o", ms=3)
    ax.plot(xs, held, color=VL[1], lw=1.1, marker="s", ms=2.8)
    for x, v, dx, dy, ha in zip(xs, newo, [0, 4, 0], [1.6, 1.2, 1.6], ["center", "left", "center"]):
        ax.text(x + dx, v + dy, f"{v:.1f}", ha=ha, va="bottom", fontsize=5.0, color=OR)
    ax.text(25, held[0] - 1.3, f"{held[0]:g}", ha="center", va="top", fontsize=5.0, color=VL[1])
    ax.text(100, held[-1] - 1.3, f"{held[-1]:g}", ha="center", va="top", fontsize=5.0, color=VL[1])
    ax.text(62, 22.5, "새 물체", fontsize=5.3, color=OR, ha="center")
    ax.text(62, 1.2, "L8S 보류", fontsize=5.3, color=VL[1], ha="center")
    ax.set_xticks(xs)
    ax.set_xticklabels(["25", "50", "100"])
    ax.set_xlim(15, 110)
    ax.set_ylim(0, 36)
    ax.set_xlabel("L8S 양 (%)", fontsize=5.4, labelpad=1)
    ax.set_ylabel("접근 3D 중앙 (mm)", fontsize=5.4, labelpad=1)
    _ev_axis(ax, "(b) E-L8SW: L8S가 많을수록")
    fig.text(0.335, 0.045, "OOD-H 실패 29 → 24 % · 50 % 뒤 이득 작음", fontsize=4.9, color="#555", ha="left")

    # (c) E-OPR3: open/sim ratio
    ax = fig.add_axes([0.585, bot, 0.165, hh])
    xr = [0, 1, 2, 3]
    dev = [21.2, 21.4, 24.4, 27.3]
    hl = [13.9, 16.2, 19.4, 29.6]
    ax.plot(xr, dev, color=OR, lw=1.1, marker="o", ms=3)
    ax.plot(xr, hl, color=VL[1], lw=1.1, marker="^", ms=3, ls=(0, (3, 1.5)))
    ax.text(3.12, dev[-1] - 1.2, f"{dev[-1]:g}", fontsize=5.0, color=OR, va="center")
    ax.text(3.12, hl[-1] + 0.8, f"{hl[-1]:g}", fontsize=5.0, color=VL[1], va="center")
    ax.text(-0.12, dev[0] + 1.2, f"{dev[0]:g}", fontsize=5.0, color=OR, va="bottom", ha="center")
    ax.text(-0.12, hl[0] - 1.2, f"{hl[0]:g}", fontsize=5.0, color=VL[1], va="top", ha="center")
    ax.text(1.4, 29.5, "dev 실패", fontsize=5.3, color=OR, ha="center")
    ax.text(1.8, 12.0, "OOD-HL 실패", fontsize=5.3, color=VL[1], ha="center")
    ax.set_xticks(xr)
    ax.set_xticklabels(["0.59", "1.0", "1.5", "3.0"])
    ax.set_xlim(-0.5, 3.6)
    ax.set_ylim(8, 34)
    ax.set_xlabel("공개/시뮬 비율", fontsize=5.4, labelpad=1)
    ax.set_ylabel("L8-X 실패 (%)", fontsize=5.4, labelpad=1)
    _ev_axis(ax, "(c) E-OPR3: 공개 비중↑")
    fig.text(0.585, 0.045, "G 적중 0.64--0.65로 같음 → 상한 0.75".replace("--", "–"), fontsize=4.9, color="#555",
             ha="left")

    # (d) main35 early checkpoints vs E-C35, f35_d reference dashed
    ax = fig.add_axes([0.815, bot, 0.17, hh])
    xc = [0, 1, 2, 3]
    dv = [27.5, 23.7, 21.4, 18.9]
    oh = [22.8, 25.0, 18.6, 17.3]
    ax.axhline(16.8, color=OR, lw=0.7, ls=(0, (2, 2)), alpha=0.7)
    ax.axhline(17.3, color=VL[1], lw=0.7, ls=(0, (2, 2)), alpha=0.7)
    ax.text(-0.3, 16.2, "f35_d: dev 16.8 · OOD-H 17.3", fontsize=4.6, color="#777", va="top", ha="left")
    ax.plot(xc, dv, color=OR, lw=1.1, marker="o", ms=3)
    ax.plot(xc, oh, color=VL[1], lw=1.1, marker="^", ms=3, ls=(0, (3, 1.5)))
    for (x, v), (dx, dy, va) in zip(zip(xc, dv), [(0, 0.8, "bottom"), (0, -0.9, "top"), (0, 0.8, "bottom"), (0, 0.8, "bottom")]):
        ax.text(x + dx, v + dy, f"{v:.1f}", ha="center", va=va, fontsize=5.0, color=OR)
    for (x, v), (dx, dy, ha, va) in zip(zip(xc, oh), [(0, -0.9, "center", "top"), (0, 0.8, "center", "bottom"),
                                                     (-0.12, 0, "right", "center"), (0.14, -0.9, "center", "top")]):
        ax.text(x + dx, v + dy, f"{v:.1f}", ha=ha, va=va, fontsize=5.0, color=VL[1])
    ax.text(0.5, 30.0, "dev 실패", fontsize=5.3, color=OR, ha="center")
    ax.text(1.0, 27.4, "OOD-H 실패", fontsize=5.3, color=VL[1], ha="center")
    ax.set_xticks(xc)
    ax.set_xticklabels(["확인판", "0.25", "0.5", "1 에폭"])
    ax.set_xlim(-0.35, 3.35)
    ax.set_ylim(12, 32)
    ax.set_yticks([15, 20, 25, 30])
    ax.set_ylabel("실패 (%)", fontsize=5.4, labelpad=1)
    _ev_axis(ax, "(d) 본 35B: 학습 진행")
    fig.text(0.815, 0.045, "1 에폭 새 물체 9.5 mm (f35_d 40.9)", fontsize=4.9, color="#555", ha="left")
    save(fig, "evidence")


# ================================================================ eval protocol (current: offline sets, closed loop, coupling 2x2)
def chip(ax, x, y, w, h, text, kind="gray", fs=5.4, tc=TXT, bold=False):
    fc, ec = PAL[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.035", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, linespacing=1.15,
            fontweight="bold" if bold else "normal")


def panel(ax, x, y, w, h, title, ec="#BDBDBD"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc="none", ec=ec, lw=0.9,
                                ls=(0, (3, 2))))
    ax.text(x + 0.08, y + h - 0.07, title, ha="left", va="top", fontsize=7.0, color=TXT, fontweight="bold")


def fig_eval():
    W, H = FULL_W, 2.30
    fig, ax = canvas(W, H)
    py, ph = 0.05, 2.20

    # (a) offline point evaluation
    x0, w0 = 0.04, 2.30
    panel(ax, x0, py, w0, ph, "(a) 오프라인 점 평가 (체크포인트마다)")
    ax.text(x0 + 0.10, 1.93, "L8-X 보호 분할 7세트", fontsize=5.6, color="#444", va="center")
    sets = ["dev", "OOD-H", "OOD-O", "OOD-D", "OOD-S", "OOD-T", "OOD-HL"]
    cw, gap = 0.29, 0.024
    for i, s in enumerate(sets):
        chip(ax, x0 + 0.10 + i * (cw + gap), 1.66, cw, 0.17, s, "jev", fs=4.9)
    chip(ax, x0 + 0.10, 1.34, 1.02, 0.22, "새 물체 OOD-O58", "astra", fs=5.4, bold=True)
    chip(ax, x0 + 1.18, 1.34, 1.02, 0.22, "L8S 보류 검증\n(최적 에폭 선택)", "skill", fs=5.0, bold=True)
    chip(ax, x0 + 0.10, 0.98, 2.10, 0.26, "G 1,577행: 학습에서 뺀 공개 과제·기체 + 가리키기 벤치\nMolmoBot Franka = 3인칭 → 보고만, 판정 제외",
         "mem", fs=4.9)
    ax.add_patch(FancyBboxPatch((x0 + 0.10, 0.14), 2.10, 0.74, boxstyle="round,pad=0,rounding_size=0.04",
                                fc=PAL["rule"][0], ec=PAL["rule"][1], lw=0.9))
    ax.text(x0 + 1.15, 0.78, "판정 ni_judge (실행 전 고정)", ha="center", va="center", fontsize=5.8, color=TXT,
            fontweight="bold")
    ax.text(x0 + 1.15, 0.44, "접근 3D 오차의 중앙값 + 20 mm 초과 실패율\n비열등 여유 = 같은 모델 시드 쌍(A/A)의 흔들림\n"
            "짝 부트스트랩 95 % 구간, 기준 f35_d", ha="center", va="center", fontsize=4.9, color="#444",
            linespacing=1.3)

    # (b) closed loop E-M35CL (report only)
    x1, w1 = 2.42, 1.86
    panel(ax, x1, py, w1, ph, "(b) 폐루프 E-M35CL (보고만)")
    ax.text(x1 + 0.10, 1.93, "같은 편을 체크포인트마다 (f35_d → 0.5 → … → 3)", fontsize=5.0, color="#444", va="center")
    conds = ["기본", "어두운\n조명", "머리\n+10°", "머리\n+15°"]
    rows = ["OOD-O58", "L8S 보류"]
    gx, gy, cwid, chh = x1 + 0.52, 1.10, 0.32, 0.22
    for j, c in enumerate(conds):
        ax.text(gx + j * (cwid + 0.02) + cwid / 2, gy + 2 * (chh + 0.04) + 0.02, c, ha="center", va="bottom",
                fontsize=4.6, color="#444")
    for i, r in enumerate(rows):
        yy = gy + (1 - i) * (chh + 0.04)
        ax.text(gx - 0.05, yy + chh / 2, r, ha="right", va="center", fontsize=4.9, color="#444")
        for j in range(len(conds)):
            chip(ax, gx + j * (cwid + 0.02), yy, cwid, chh, "", "astra" if i == 0 else "skill")
            ax.text(gx + j * (cwid + 0.02) + cwid / 2, yy + chh / 2, "▶", ha="center", va="center", fontsize=5.0,
                    color="#777")
    ax.text(x1 + w1 / 2, 0.86, "OOD-O58 + L8S 보류 약 160편 × 4조건\n모든 편 영상 저장", ha="center", va="center", fontsize=5.0,
            color="#444")
    note(ax, x1 + 0.10, 0.14, w1 - 0.20, 0.56, "판정 규칙 없음\n약 15 %p 이상 차이만 읽는다\n(새 물체 개선이 폐루프에서도 유지되는가)",
         fs=4.9, ec=PAL["rule"][1])

    # (c) coupling 2x2 + H-J
    x2, w2 = 4.36, 2.48
    panel(ax, x2, py, w2, ph, "(c) 결합 평가: 같은 시드의 2×2 (2단계)")
    cx, cy, cw2, ch2 = x2 + 0.72, 1.12, 0.82, 0.30
    ax.text(cx + cw2 / 2, cy + 2 * ch2 + 0.08, "조이스틱 JCR", ha="center", va="bottom", fontsize=5.0, color=VL[1],
            fontweight="bold")
    ax.text(cx + cw2 * 1.5 + 0.04, cy + 2 * ch2 + 0.08, "참값 실행기", ha="center", va="bottom", fontsize=5.0,
            color="#555", fontweight="bold")
    ax.text(cx - 0.05, cy + ch2 * 1.5 + 0.02, "상위(본 35B)", ha="right", va="center", fontsize=5.0, color=UP[1],
            fontweight="bold")
    ax.text(cx - 0.05, cy + ch2 * 0.5, "참값 명령", ha="right", va="center", fontsize=5.0, color="#555",
            fontweight="bold")
    cells = [(0, 1, "결합 (실제)", "crit"), (1, 1, "상한 B", "gray"), (0, 0, "상한 A", "gray"),
             (1, 0, "과제 상한", "gray")]
    for cc, rr, t, k in cells:
        chip(ax, cx + cc * (cw2 + 0.04), cy + rr * (ch2 + 0.04), cw2, ch2, t, k, fs=5.4,
             bold=(k == "crit"))
    ax.text(x2 + w2 / 2, 0.93, "연결 손실 = min(상한 A, 상한 B) − 결합  ≤ 5 %p", ha="center", va="center",
            fontsize=5.5, color=TXT, fontweight="bold")
    ax.text(x2 + w2 / 2, 0.73, "실패 탓 가르기: 한쪽만 참값으로 바꾼 반사실 재생\n→ 상위 / JCR / 연결(인터페이스) 탓, 연결 탓 ≤ 실패의 10 %",
            ha="center", va="center", fontsize=4.9, color="#444", linespacing=1.3)
    note(ax, x2 + 0.10, 0.22, w2 - 0.20, 0.34, "H-J: 같은 JCR를 단독(스스로 계획) 대 상위 아래 조이스틱으로\n같은 장면에서 비교 → 짐을 덜어 준 쪽이 나아야 채택",
         fs=4.9, ec=VL[1])
    ax.text(x2 + w2 / 2, 0.13, "참값 = 시뮬 특권 정보로 계산한 명령·실행", ha="center", va="center", fontsize=4.6,
            color="#777")
    save(fig, "eval_protocol")


if __name__ == "__main__":
    # overview/model are drawn by fig_overview/fig_model; pass names to redraw only some figures
    names = sys.argv[1:] or ["evidence", "eval"]
    for n in names:
        {"evidence": fig_evidence, "eval": fig_eval}[n]()
    print("ok")
