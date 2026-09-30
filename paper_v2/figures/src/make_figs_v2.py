"""PaceNotes v2 paper figures (2026-09-30): F1-F8.
Font setup = paper/figures/src/make_figs.py (Malgun Gothic, pdf.fonttype 42).
Content = D:/tools/scratch_qdd/board/NOW.md, PAPER_SKELETON.md, PLAN_coupling.md and docs/stage3 (no Astra, no teacher policy;
sim labels are "시뮬 참값(특권 정보로 계산)"; no third-person views). Orange text = tentative numbers.
Run (D drive caches):
  MPLCONFIGDIR=D:/tools/mplcache python paper_v2/figures/src/make_figs_v2.py [out_dir]
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
for f in ["C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"]:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": ["Malgun Gothic", "DejaVu Sans"],
    "font.size": 8, "axes.unicode_minus": False, "pdf.fonttype": 42,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
})

# role colours (fill, border): 4 roles only
UP = ("#FCE3CF", "#D9762B")    # upper VLM (orange)
VL = ("#D6E6F8", "#3F74B8")    # joystick VLA (blue)
CO = ("#EFEFEF", "#8A8A8A")    # code / robot (gray)
OF = ("#E9E2F5", "#7E5DB5")    # offline: data, training, evaluation (purple)
RED = "#C0392B"
TENT = "#E27000"
TXT = "#262626"
SUB = "#505050"
FULL_W = 6.875


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, col, title=None, sub=None, tfs=7.6, sfs=6.0, ls="-", lw=1.1, fc=None, tc=TXT, r=0.05):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc or col[0], ec=col[1],
                                lw=lw, ls=ls))
    if title and sub:
        ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center", fontsize=tfs, color=tc, fontweight="bold")
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=sfs, color=SUB, linespacing=1.2)
    elif title:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=tfs, color=tc, fontweight="bold",
                linespacing=1.2)


def txt(ax, x, y, s, fs=6.0, c=SUB, ha="center", va="center", bold=False, **kw):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=c, fontweight="bold" if bold else "normal", linespacing=1.2, **kw)


def arrow(ax, pts, c="#555555", lw=1.0, ls="-", hw=0.22, hl=0.45):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=c, lw=lw, ls=ls, solid_capstyle="butt")
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    ax.annotate("", xy=(x1, y1), xytext=(x0 + (x1 - x0) * 0.5, y0 + (y1 - y0) * 0.5),
                arrowprops=dict(arrowstyle=f"-|>,head_length={hl},head_width={hw}", color=c, lw=lw,
                                shrinkA=0, shrinkB=0))


def section(ax, x, y, w, h, label):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06", fc="none", ec="#B8B8B8",
                                lw=0.8, ls=(0, (4, 3))))
    txt(ax, x + 0.08, y + h - 0.07, label, fs=7.2, c="#4A4A4A", ha="left", va="top", bold=True)


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), dpi=250 if ext == "png" else None)
    plt.close(fig)
    print("saved", name)


def head_image(ax, x, y, w, h, ring=True, target=None):
    """flat head-camera thumbnail: table, two objects, gripper fingertip ring"""
    ax.add_patch(Rectangle((x, y), w, h, fc="#EEF3F8", ec="#9A9A9A", lw=0.8))
    ax.add_patch(Polygon([(x + w * 0.04, y + h * 0.05), (x + w * 0.96, y + h * 0.05), (x + w * 0.82, y + h * 0.55),
                          (x + w * 0.18, y + h * 0.55)], closed=True, fc="#D8C7AA", ec="none"))
    ax.add_patch(Rectangle((x + w * 0.30, y + h * 0.22), w * 0.12, h * 0.20, fc="#D0574B", ec="none"))  # mug
    ax.add_patch(Rectangle((x + w * 0.58, y + h * 0.18), w * 0.24, h * 0.07, fc="#4F7FC0", ec="none"))  # tray
    # gripper coming from right
    ax.plot([x + w * 0.98, x + w * 0.74], [y + h * 0.92, y + h * 0.62], color="#555", lw=2.2)
    if ring:
        ax.add_patch(Circle((x + w * 0.72, y + h * 0.60), h * 0.08, fc="none", ec="#1FA35B", lw=1.0))
    if target is not None:
        tx, ty = target
        ax.plot([x + w * tx], [y + h * ty], marker="x", color=RED, ms=6, mew=1.6)


def wrist_image(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, fc="#F3EEE6", ec="#9A9A9A", lw=0.8))
    ax.add_patch(Rectangle((x + w * 0.35, y + h * 0.15), w * 0.30, h * 0.45, fc="#D0574B", ec="none"))
    ax.plot([x + w * 0.10, x + w * 0.30], [y + h * 0.95, y + h * 0.70], color="#666", lw=2.0)
    ax.plot([x + w * 0.90, x + w * 0.70], [y + h * 0.95, y + h * 0.70], color="#666", lw=2.0)


# ============================================================ F1 overview
def f1_overview():
    W, H = FULL_W, 2.75
    fig, ax = canvas(W, H)
    # runtime row
    section(ax, 0.03, 1.42, W - 0.06, 1.30, "실행 층 (매 판)")
    y, h, w = 1.62, 0.66, 1.16
    xs = [0.22, 1.92, 3.62, 5.32]
    items = [(UP, "상위 VLM", "점 + 높이 의도"), (CO, "좌표 변환", "픽셀 → xyz"),
             (VL, "조이스틱 VLA", "범위 안 보정"), (CO, "로봇", "FFW-SG2")]
    for x, (col, t, s) in zip(xs, items):
        box(ax, x, y, w, h, col, t, s, tfs=8.0, sfs=6.6)
    for i in range(3):
        arrow(ax, [(xs[i] + w + 0.03, y + h / 2), (xs[i + 1] - 0.03, y + h / 2)])
    txt(ax, (xs[0] + w + xs[1]) / 2, y + h / 2 + 0.11, "명령", fs=5.8)
    txt(ax, (xs[1] + w + xs[2]) / 2, y + h / 2 + 0.11, "목표·범위", fs=5.8)
    txt(ax, (xs[2] + w + xs[3]) / 2, y + h / 2 + 0.11, "관절 청크", fs=5.8)
    # single thin dashed feedback line: robot/VLA -> upper
    fy = y + h + 0.12
    ax.plot([xs[3] + w / 2, xs[3] + w / 2, xs[0] + w / 2], [y + h, fy, fy], color=RED, lw=0.7, ls=(0, (3, 2)))
    arrow(ax, [(xs[0] + w / 2, fy), (xs[0] + w / 2, y + h + 0.01)], c=RED, lw=0.7, hw=0.18, hl=0.35)
    txt(ax, (xs[1] + xs[2] + w) / 2, fy + 0.09, "되돌림: 영상 · 진행 · 이상 신호", fs=5.8, c=RED)

    # offline row
    section(ax, 0.03, 0.05, W - 0.06, 1.25, "오프라인 층")
    y2 = 0.22
    xo = [0.22, 2.60, 4.98]
    wo = 1.66
    items2 = [("데이터", "L8S · 공개 점 · L9"), ("학습", "상위 LoRA · VLA 4단계"), ("평가", "오프라인 · 폐루프 · 2×2")]
    for x, (t, s) in zip(xo, items2):
        box(ax, x, y2, wo, h, OF, t, s, tfs=8.0, sfs=6.6)
    for i in range(2):
        arrow(ax, [(xo[i] + wo + 0.03, y2 + h / 2), (xo[i + 1] - 0.03, y2 + h / 2)], c=OF[1])
    # weights up from training to the two learned modules
    tx = xo[1] + wo / 2
    arrow(ax, [(tx - 0.25, y2 + h + 0.02), (tx - 0.25, 1.26), (xs[0] + w / 2 + 0.25, 1.26),
               (xs[0] + w / 2 + 0.25, y - 0.02)], c=OF[1], lw=0.7, hw=0.16, hl=0.32)
    arrow(ax, [(tx + 0.25, y2 + h + 0.02), (tx + 0.25, 1.20), (xs[2] + w / 2, 1.20), (xs[2] + w / 2, y - 0.02)],
          c=OF[1], lw=0.7, hw=0.16, hl=0.32)
    txt(ax, tx + 0.50, 1.02, "가중치", fs=5.8, c=OF[1], ha="left")
    save(fig, "f1_overview")


# ============================================================ F2 one upper-VLM call
def f2_upper_call():
    W, H = FULL_W, 2.95
    fig, ax = canvas(W, H)
    txt(ax, 0.05, H - 0.05, "입력", fs=7.6, c=TXT, ha="left", va="top", bold=True)
    # inputs column
    head_image(ax, 0.08, 1.62, 1.35, 0.90, ring=True)
    txt(ax, 0.755, 1.52, "머리 영상 (손끝 원 표시)", fs=5.8)
    wrist_image(ax, 0.08, 0.72, 0.95, 0.62)
    txt(ax, 0.555, 0.62, "쓰는 팔 손목 영상", fs=5.8)
    box(ax, 1.12, 0.92, 0.72, 0.42, CO, "로봇 상태", "관절·그리퍼", tfs=6.2, sfs=5.4)
    box(ax, 0.08, 0.08, 1.76, 0.40, CO, "직전 명령과 결과", "도달 오차·막힘 한 줄 이력", tfs=6.2, sfs=5.4)
    # model
    mx, my, mw, mh = 2.25, 0.85, 1.35, 1.10
    box(ax, mx, my, mw, mh, UP, "상위 VLM", "Qwen3.5-35B-A3B\nLoRA r16", tfs=8.2, sfs=6.0)
    for yy in (2.05, 1.03, 0.70, 0.28):
        arrow(ax, [(1.90, yy), (2.05, yy), (2.05, my + mh / 2), (mx - 0.02, my + mh / 2)], lw=0.8, hw=0.16, hl=0.3)
    txt(ax, mx + mw / 2, my - 0.14, "3인칭·어안 영상 없음, m 숫자 안 냄", fs=5.4)
    # outputs
    ox = 3.92
    txt(ax, ox, H - 0.05, "출력 (명령을 맨 앞에)", fs=7.6, c=TXT, ha="left", va="top", bold=True)
    outs = [("① 목표 점", "머리 영상 위 (u, v) ∈ 0–1000"), ("② 높이 의도", "위 · 잡기 · 놓기 · 들기"),
            ("③ 그리퍼 의도", "열기 · 닫기"), ("④ 진행 평가·검증", "됐다 / 진행 중 / 실패, 다음 단계")]
    oy = 2.35
    for i, (t, s) in enumerate(outs):
        yy = oy - i * 0.50
        col = UP if i < 3 else ("#F6DCE6", "#C2577F")
        box(ax, ox, yy, 1.30, 0.40, col, t, s, tfs=6.4, sfs=5.2)
    arrow(ax, [(mx + mw + 0.02, my + mh / 2), (ox - 0.04, my + mh / 2)], lw=0.9)
    # code: depth -> xyz
    cx = 5.50
    head_image(ax, cx, 1.62, 1.30, 0.86, ring=False, target=(0.36, 0.44))
    txt(ax, cx + 0.65, 2.58, "점이 가리키는 곳", fs=5.8, c=RED)
    box(ax, cx, 0.62, 1.30, 0.78, CO, "코드: 깊이 → xyz", "센서 깊이 + 카메라 정보\n탁자 평면·윗면 띠 중심\n+ 높이 의도 → 목표", tfs=6.4,
        sfs=5.2)
    arrow(ax, [(ox + 1.32, 2.55), (cx - 0.03, 2.05)], lw=0.8, hw=0.16, hl=0.3)
    arrow(ax, [(ox + 1.32, 2.05), (cx - 0.03, 1.10)], lw=0.8, hw=0.16, hl=0.3)
    arrow(ax, [(cx + 0.65, 0.60), (cx + 0.65, 0.32)], lw=0.9)
    txt(ax, cx + 0.65, 0.18, "목표 xyz + 그리퍼 → 실행기/VLA", fs=5.8, c=TXT)
    save(fig, "f2_upper_call")


# ============================================================ F3 joystick VLA
def f3_vla():
    W, H = FULL_W, 2.85
    fig, ax = canvas(W, H)
    # inputs
    box(ax, 0.05, 1.70, 1.55, 0.95, UP, "상위 명령", "목표 xyz·영상 점, 높이 의도\n그리퍼, 허용 범위 ±cm·±°\n시간 예산, 명령 나이",
        tfs=7.0, sfs=5.4)
    box(ax, 0.05, 0.75, 1.55, 0.75, CO, "관측", "머리 + 쓰는 팔 손목 영상\n관절 상태", tfs=7.0, sfs=5.4)
    # VLA
    box(ax, 2.00, 0.95, 1.30, 1.30, VL, "조이스틱 VLA", "스스로 계획 안 함\n잡는 시점·작은 회피\n밀린 물체 재정렬", tfs=7.6, sfs=5.5)
    arrow(ax, [(1.62, 2.17), (1.80, 2.17), (1.80, 1.75), (1.98, 1.75)], lw=0.8, hw=0.16, hl=0.3)
    arrow(ax, [(1.62, 1.12), (1.80, 1.12), (1.80, 1.45), (1.98, 1.45)], lw=0.8, hw=0.16, hl=0.3)
    # outputs: correction -> clip
    box(ax, 3.62, 1.55, 1.05, 0.62, VL, "보정 Δ", "기본 경로 기준", tfs=7.0, sfs=5.4)
    box(ax, 3.62, 0.72, 1.05, 0.62, CO, "범위로 자름", "clip(Δ, 허용 범위)", tfs=6.6, sfs=5.2)
    arrow(ax, [(3.32, 1.86), (3.60, 1.86)], lw=0.9)
    arrow(ax, [(4.145, 1.53), (4.145, 1.36)], lw=0.9)
    # anomaly scores up
    box(ax, 2.00, 2.42, 2.67, 0.36, ("#F6DCE6", "#C2577F"), "이상 점수 → 상위: 물체 변위 · 목표 불가 · 접촉 편차", tfs=6.0)
    arrow(ax, [(2.65, 2.27), (2.65, 2.40)], c="#C2577F", lw=0.8, hw=0.16, hl=0.3)
    # right panel: path picture
    px, py, pw, ph = 4.95, 0.30, 1.85, 2.30
    ax.add_patch(Rectangle((px, py), pw, ph, fc="white", ec="#C8C8C8", lw=0.6))
    sx, sy = px + 0.22, py + 0.35
    gx, gy = px + pw - 0.30, py + ph - 0.55
    import numpy as np
    t = np.linspace(0, 1, 60)
    bx = sx + (gx - sx) * t
    by = sy + (gy - sy) * (3 * t ** 2 - 2 * t ** 3)
    # envelope tube around nominal path
    dx = np.gradient(bx)
    dy = np.gradient(by)
    n = np.hypot(dx, dy)
    nx_, ny_ = -dy / n, dx / n
    wtube = 0.16
    upper = np.c_[bx + nx_ * wtube, by + ny_ * wtube]
    lower = np.c_[bx - nx_ * wtube, by - ny_ * wtube]
    ax.add_patch(Polygon(np.r_[upper, lower[::-1]], closed=True, fc="#FCE3CF", ec="#D9762B", lw=0.6, alpha=0.8))
    ax.plot(bx, by, color="#777", lw=1.0, ls=(0, (3, 2)))
    cxp = bx + nx_ * wtube * 0.75 * np.sin(np.pi * t) ** 2
    cyp = by + ny_ * wtube * 0.75 * np.sin(np.pi * t) ** 2
    ax.plot(cxp, cyp, color=VL[1], lw=1.4)
    ax.plot([sx], [sy], "o", color="#444", ms=3.5)
    ax.plot([gx], [gy], marker="x", color=RED, ms=6, mew=1.5)
    # obstacle nudged
    ax.add_patch(Circle((px + 0.80, py + 1.05), 0.10, fc="#BDBDBD", ec="none"))
    txt(ax, px + pw / 2, py + ph - 0.12, "허용 범위(주황) 안에서만", fs=5.8, c=TXT)
    txt(ax, gx - 0.45, gy + 0.10, "상위 목표", fs=5.4, c=RED)
    txt(ax, px + 1.30, py + 0.55, "기본 경로(점선)\n+ VLA 보정(파랑)", fs=5.4, c=VL[1])
    arrow(ax, [(4.69, 1.03), (4.93, 1.03)], lw=0.9)
    txt(ax, 3.3, 0.35, "0.4 s 관절 청크 → 로봇 (100 Hz 위치 명령, 관절 걸음 ≤ 0.04 rad)", fs=5.6, c=TXT)
    save(fig, "f3_vla")


# ============================================================ F4 coupling timeline
def _seg(ax, x0, x1, y, h, fc, ec="none", hatch=None, lw=0.6):
    ax.add_patch(Rectangle((x0, y), x1 - x0, h, fc=fc, ec=ec, lw=lw, hatch=hatch))


def f4_timeline():
    W, H = FULL_W, 3.55
    fig, ax = canvas(W, H)
    X0 = 1.10          # time origin (inch)
    S = 0.78           # inch per unit time
    L = 1.2            # planner latency (units, schematic)

    def X(t):
        return X0 + S * t

    # ---- (a) stage 1: robot waits
    txt(ax, 0.05, H - 0.05, "(a) 1단계: 로봇이 상위 답을 기다림", fs=7.4, c=TXT, ha="left", va="top", bold=True)
    ya_p, ya_r = 3.02, 2.66
    txt(ax, 1.02, ya_p + 0.10, "상위 VLM", fs=6.2, c=TXT, ha="right")
    txt(ax, 1.02, ya_r + 0.10, "로봇", fs=6.2, c=TXT, ha="right")
    t = 0.0
    for k in range(3):
        _seg(ax, X(t), X(t + L), ya_p, 0.20, UP[0], UP[1])
        txt(ax, X(t + L / 2), ya_p + 0.10, f"호출 {k + 1}", fs=5.4, c=TXT)
        _seg(ax, X(t), X(t + L), ya_r, 0.20, "white", "#9A9A9A", hatch="////")
        txt(ax, X(t + L / 2), ya_r + 0.10, "대기", fs=5.4, c="#444", bbox=dict(fc="white", ec="none", pad=2.5), zorder=6)
        _seg(ax, X(t + L), X(t + L + 1.2), ya_r, 0.20, "#DCEFD9", "#5E9E57")
        txt(ax, X(t + L + 0.6), ya_r + 0.10, "이동", fs=5.4, c=TXT)
        t += L + 1.2
    # ---- (b) coupled
    txt(ax, 0.05, 2.22, "(b) 결합: 기다림 없음", fs=7.4, c=TXT, ha="left", va="top", bold=True)
    yp, yr, yv = 1.58, 1.02, 0.62
    txt(ax, 1.02, yp + 0.10, "상위 VLM", fs=6.2, c=TXT, ha="right")
    txt(ax, 1.02, yr + 0.10, "실행(로봇)", fs=6.2, c=TXT, ha="right")
    txt(ax, 1.02, yv + 0.09, "VLA 틱", fs=6.2, c=TXT, ha="right")
    cf = 0.30          # command-first: command tokens available this long after call start
    calls = [(0.0, "1"), (2.0, "2"), (4.4, "3"), (5.2, "4")]
    # call 1
    _seg(ax, X(0), X(L), yp, 0.20, UP[0], UP[1])
    txt(ax, X(L / 2 + 0.15), yp + 0.10, "호출 1", fs=5.4, c=TXT)
    # command-first tick
    ax.plot([X(cf)] * 2, [yp - 0.02, yp + 0.24], color=UP[1], lw=1.4)
    txt(ax, X(cf), yp + 0.33, "명령 먼저", fs=5.4, c=UP[1])
    arrow(ax, [(X(cf), yp - 0.02), (X(cf), yr + 0.22)], c=UP[1], lw=0.8, hw=0.14, hl=0.28)
    # move 1 : cf -> 3.2 ; committed prefix during call 2 (2.0..3.2)
    m1a, m1b = cf, 3.2
    _seg(ax, X(m1a), X(m1b), yr, 0.20, "#DCEFD9", "#5E9E57")
    _seg(ax, X(2.0), X(m1b), yr, 0.20, "#8CC084", "#5E9E57")
    txt(ax, X((m1a + 2.0) / 2), yr + 0.10, "명령 1 실행", fs=5.4, c=TXT)
    txt(ax, X((2.0 + m1b) / 2), yr + 0.10, "확정 구간", fs=5.2, c="white", bold=True)
    # call 2: early re-query at remaining <= L
    _seg(ax, X(2.0), X(2.0 + L), yp, 0.20, UP[0], UP[1])
    txt(ax, X(2.0 + L / 2), yp + 0.10, "호출 2", fs=5.4, c=TXT)
    ax.annotate("", xy=(X(2.0), yp + 0.21), xytext=(X(2.0), yp + 0.44),
                arrowprops=dict(arrowstyle="-|>,head_length=0.35,head_width=0.16", color=RED, lw=0.8))
    txt(ax, X(2.0) - 0.05, yp + 0.52, "남은 시간 ≤ 지연 → 미리 부르기", fs=5.2, c=RED, ha="left")
    # pre-issued next command appended
    arrow(ax, [(X(2.0 + cf), yp - 0.02), (X(m1b), yr + 0.22)], c=UP[1], lw=0.8, hw=0.14, hl=0.28)
    txt(ax, X(m1b) + 0.06, yr + 0.36, "다음 명령 미리 발행", fs=5.2, c=UP[1], ha="left")
    # move 2 : 3.2 -> 5.6 (committed 4.4..)
    m2b = 5.2
    _seg(ax, X(m1b), X(m2b), yr, 0.20, "#DCEFD9", "#5E9E57")
    txt(ax, X((m1b + m2b) / 2), yr + 0.10, "명령 2 실행", fs=5.4, c=TXT)
    # call 3 pre-issue, then cancelled by anomaly at 5.2
    _seg(ax, X(4.0), X(4.0 + L), yp, 0.20, UP[0], UP[1])
    txt(ax, X(4.0 + L / 2 - 0.1), yp + 0.10, "호출 3", fs=5.4, c=TXT)
    ax.plot([X(5.2)], [yp + 0.10], marker="x", color=RED, ms=7, mew=1.8)
    txt(ax, X(5.2) + 0.08, yp + 0.34, "이상 신호 → 취소·재질의", fs=5.2, c=RED, ha="left")
    # call 4
    _seg(ax, X(5.2), X(5.2 + L), yp - 0.26, 0.20, UP[0], UP[1])
    txt(ax, X(5.2 + L / 2 + 0.1), yp - 0.16, "호출 4", fs=5.4, c=TXT)
    ax.plot([X(5.2 + cf)] * 2, [yp - 0.28, yp - 0.04], color=UP[1], lw=1.4)
    arrow(ax, [(X(5.2 + cf), yp - 0.28), (X(5.2 + cf), yr + 0.22)], c=UP[1], lw=0.8, hw=0.14, hl=0.28)
    _seg(ax, X(m2b), X(5.2 + cf), yr, 0.20, "#8CC084", "#5E9E57")
    _seg(ax, X(5.2 + cf), X(7.0), yr, 0.20, "#DCEFD9", "#5E9E57")
    txt(ax, X(6.3), yr + 0.10, "명령 4 실행", fs=5.4, c=TXT)
    # anomaly arrow from VLA row
    arrow(ax, [(X(5.2) - 0.02, yv + 0.20), (X(5.2) - 0.02, yr - 0.02)], c=RED, lw=0.7, hw=0.14, hl=0.28)
    # VLA ticks + correction band
    ax.add_patch(Rectangle((X(cf), yv), X(7.0) - X(cf), 0.18, fc=VL[0], ec="none"))
    for k in range(int((7.0 - cf) / 0.18) + 1):
        tt = cf + k * 0.18
        ax.plot([X(tt)] * 2, [yv, yv + 0.18], color=VL[1], lw=0.6)
    # time axis
    ax.plot([X(0), X(7.0)], [0.36, 0.36], color="#777", lw=0.7)
    ax.annotate("", xy=(X(7.1), 0.36), xytext=(X(6.9), 0.36),
                arrowprops=dict(arrowstyle="-|>,head_length=0.35,head_width=0.16", color="#777", lw=0.7))
    txt(ax, X(7.15), 0.36, "시간", fs=5.8, ha="left")
    # latency bracket
    ax.plot([X(2.0), X(2.0 + L)], [0.44, 0.44], color="#777", lw=0.6)
    for xx in (X(2.0), X(2.0 + L)):
        ax.plot([xx, xx], [0.40, 0.48], color="#777", lw=0.6)
    txt(ax, X(2.0 + L / 2), 0.25, "상위 지연 L", fs=5.4)
    # legend
    lx = 0.10
    _seg(ax, lx, lx + 0.22, 0.05, 0.12, "#8CC084", "#5E9E57")
    txt(ax, lx + 0.27, 0.11, "확정 구간(RTC식: 다음 명령이 이어 붙음)", fs=5.2, ha="left")
    _seg(ax, 3.00, 3.22, 0.05, 0.12, VL[0], VL[1])
    txt(ax, 3.27, 0.11, "VLA 보정(허용 범위 안)", fs=5.2, ha="left")
    txt(ax, 4.72, 0.11, "잡기·놓기 직전은 미리 내지 않음", fs=5.2, ha="left", c=RED)
    save(fig, "f4_timeline")


# ============================================================ F5 coupling training loop
def f5_training():
    W, H = FULL_W, 2.85
    fig, ax = canvas(W, H)
    # VLA stage 1, 2
    box(ax, 0.05, 1.75, 1.25, 0.78, VL, "VLA ① 단독", "참값 명령 + 교란 장면\n정답 = 시뮬 참값 보정", tfs=6.8, sfs=5.2)
    box(ax, 0.05, 0.70, 1.25, 0.78, VL, "VLA ② 상위 흉내", "측정한 상위 오차·지연\n명령 도중 교체 주입", tfs=6.8, sfs=5.2)
    arrow(ax, [(0.675, 1.73), (0.675, 1.50)], lw=0.9)
    # loop container
    section(ax, 1.55, 0.35, 3.30, 2.40, "번갈아 맞추기 (④)")
    box(ax, 1.68, 1.55, 1.30, 0.92, UP, "상위 갱신", "입력: 도착 0–3 s 전 장면\n+ 실행 중 명령 + 도착 예상 표시\n출력: 다음 명령 + 미리 내도 되나",
        tfs=6.8, sfs=5.0)
    box(ax, 3.42, 1.55, 1.30, 0.92, VL, "VLA ③ 갱신", "실제 상위 명령 위의\n기록에서 재학습\n(연결 지점 분포 맞춤)", tfs=6.8, sfs=5.0)
    box(ax, 1.68, 0.55, 1.30, 0.62, ("#FFF4E8", "#D9762B"), "보조 과제", "실제(VLA가 만든) 도착 위치 예측\n제어 출력에는 안 씀", tfs=6.2,
        sfs=4.9, ls=(0, (3, 2)))
    arrow(ax, [(2.33, 1.19), (2.33, 1.53)], c=UP[1], lw=0.7, hw=0.14, hl=0.28)
    # alternation arrows
    arrow(ax, [(3.00, 2.12), (3.40, 2.12)], lw=0.9)
    arrow(ax, [(3.40, 1.88), (3.00, 1.88)], lw=0.9)
    txt(ax, 3.20, 2.00, "번갈아", fs=5.0)
    box(ax, 3.42, 0.55, 1.30, 0.62, CO, "연결 손실 측정", "같은 시드 2×2 (그림 6)", tfs=6.4, sfs=5.0)
    arrow(ax, [(4.07, 1.53), (4.07, 1.19)], lw=0.9)
    arrow(ax, [(1.32, 1.09), (1.45, 1.09), (1.45, 2.00), (1.70, 2.00)], lw=0.9)
    # stop rule
    dx, dy = 5.55, 1.40
    ax.add_patch(Polygon([(dx, dy + 0.42), (dx + 0.55, dy), (dx, dy - 0.42), (dx - 0.55, dy)], closed=True,
                         fc="white", ec="#555", lw=0.9))
    txt(ax, dx, dy, "더 안\n줄어드나?", fs=5.8, c=TXT)
    arrow(ax, [(4.74, 0.86), (dx, 0.86), (dx, dy - 0.44)], lw=0.9)
    txt(ax, dx + 0.62, dy + 0.12, "예 → 멈춤", fs=5.8, c=TXT, ha="left")
    arrow(ax, [(dx, dy + 0.44), (dx, 2.62), (4.10, 2.62), (4.10, 2.49)], lw=0.8, hw=0.16, hl=0.3)
    txt(ax, dx + 0.06, 2.20, "아니오 → 한 바퀴 더", fs=5.4, ha="left")
    box(ax, 5.05, 0.10, 1.75, 0.55, ("#F7F7F7", "#8A8A8A"), "(선택) 엔드투엔드 미세 학습", "인터페이스·모듈 단독 평가 유지", tfs=6.0,
        sfs=4.9, ls=(0, (3, 2)))
    arrow(ax, [(dx + 0.56, dy), (6.55, dy), (6.55, 0.67)], c="#8A8A8A", lw=0.7, ls=(0, (3, 2)), hw=0.14, hl=0.28)
    txt(ax, 0.675, 0.45, "정답은 모두\n시뮬 참값(특권 정보로 계산)", fs=5.0)
    save(fig, "f5_training")


# ============================================================ F6 coupling loss 2x2 + attribution
def f6_coupling_loss():
    W, H = FULL_W, 2.70
    fig, ax = canvas(W, H)
    txt(ax, 0.05, H - 0.05, "(a) 같은 시드 2×2", fs=7.4, c=TXT, ha="left", va="top", bold=True)
    gx, gy, cw, ch = 1.00, 0.55, 1.10, 0.70
    txt(ax, gx + cw / 2, gy + 2 * ch + 0.22, "조이스틱 VLA", fs=6.4, c=VL[1], bold=True)
    txt(ax, gx + cw * 1.5 + 0.08, gy + 2 * ch + 0.22, "참값 실행기", fs=6.4, c=SUB, bold=True)
    txt(ax, gx - 0.08, gy + ch * 1.5 + 0.04, "상위 VLM", fs=6.4, c=UP[1], ha="right", bold=True)
    txt(ax, gx - 0.08, gy + ch * 0.5 + 0.04, "참값 명령", fs=6.4, c=SUB, ha="right", bold=True)
    cells = [(0, 1, ("#F6DCE6", "#C2577F"), "결합", "실제 성공률"), (1, 1, CO, "상한 B", "상위 + 참값 실행"),
             (0, 0, CO, "상한 A", "참값 명령 + VLA"), (1, 0, CO, "과제 상한", "참값 + 참값")]
    for i, j, col, t, s in cells:
        box(ax, gx + i * (cw + 0.08), gy + j * ch + 0.04, cw, ch - 0.08, col, t, s, tfs=7.0, sfs=5.4)
    txt(ax, gx + cw + 0.04, 0.28, "연결 손실 = min(상한 A, 상한 B) − 결합", fs=6.6, c=TXT, bold=True)
    txt(ax, gx + cw + 0.04, 0.08, "합격: ≤ 5 %p, 연결 탓 실패 ≤ 전체 실패의 10 %", fs=6.0, c=RED)
    # (b) attribution
    bx = 3.55
    txt(ax, bx, H - 0.05, "(b) 실패 편 원인 가르기 (반사실 재실행)", fs=7.4, c=TXT, ha="left", va="top", bold=True)
    box(ax, bx, 1.75, 0.95, 0.52, ("#F6DCE6", "#C2577F"), "결합 실패 편", "같은 시드", tfs=6.4, sfs=5.2)
    box(ax, bx + 1.20, 2.00, 1.55, 0.42, CO, "상위만 참값으로", "재실행 → 성공?", tfs=6.0, sfs=5.2)
    box(ax, bx + 1.20, 1.50, 1.55, 0.42, CO, "VLA만 참값으로", "재실행 → 성공?", tfs=6.0, sfs=5.2)
    arrow(ax, [(bx + 0.97, 2.10), (bx + 1.18, 2.21)], lw=0.8, hw=0.14, hl=0.28)
    arrow(ax, [(bx + 0.97, 1.92), (bx + 1.18, 1.71)], lw=0.8, hw=0.14, hl=0.28)
    # decision table
    rows = [("성공", "실패", "상위 탓", UP[1]), ("실패", "성공", "VLA 탓", VL[1]), ("성공", "성공", "연결 탓", "#C2577F"),
            ("실패", "실패", "둘 다 / 과제", SUB)]
    tx, ty = bx + 0.10, 1.15
    txt(ax, tx + 0.45, ty, "상위만 참값", fs=5.6, c=TXT, bold=True)
    txt(ax, tx + 1.35, ty, "VLA만 참값", fs=5.6, c=TXT, bold=True)
    txt(ax, tx + 2.40, ty, "판정", fs=5.6, c=TXT, bold=True)
    ax.plot([tx, tx + 3.05], [ty - 0.10, ty - 0.10], color="#AAA", lw=0.6)
    for k, (a, b, lab, c) in enumerate(rows):
        yy = ty - 0.25 - k * 0.21
        txt(ax, tx + 0.45, yy, a, fs=5.6)
        txt(ax, tx + 1.35, yy, b, fs=5.6)
        txt(ax, tx + 2.40, yy, lab, fs=5.8, c=c, bold=True)
    txt(ax, bx + 1.55, 0.02, "판정 규칙은 정의안(사전 등록 전)", fs=5.2, c=TENT, va="bottom")
    save(fig, "f6_coupling_loss")


# ============================================================ F7 data pipeline
def f7_data():
    W, H = FULL_W, 3.05
    fig, ax = canvas(W, H)
    section(ax, 0.03, 1.62, W - 0.06, 1.38, "지금: 본 35B 학습 데이터")
    box(ax, 0.20, 2.22, 1.45, 0.58, OF, "L8S 사실적 시뮬", "약 7,600편 · 편당 17.9행", tfs=6.6, sfs=5.2)
    box(ax, 0.20, 1.72, 1.45, 0.42, CO, "공개 로봇 데이터", "머리 시점만", tfs=6.2, sfs=5.0)
    box(ax, 1.90, 1.72, 1.35, 0.42, CO, "4중 검증", "투영·마스크·이름·관문", tfs=6.2, sfs=5.0)
    box(ax, 1.90, 2.22, 1.35, 0.58, OF, "시뮬 참값 라벨", "특권 정보로 계산\n139,603행", tfs=6.4, sfs=5.0)
    box(ax, 3.50, 1.72, 1.20, 0.42, OF, "공개 점 31,397행", "반복 ≤ 2배 → 62,794", tfs=6.0, sfs=5.0)
    box(ax, 5.05, 1.85, 1.70, 0.85, UP, "본 35B", "202,397행 · 3 에폭\n공개/시뮬 = min(0.75, 2×풀/시뮬)", tfs=7.2, sfs=5.2)
    arrow(ax, [(1.67, 2.51), (1.88, 2.51)], lw=0.8, hw=0.14, hl=0.28)
    arrow(ax, [(1.67, 1.93), (1.88, 1.93)], lw=0.8, hw=0.14, hl=0.28)
    arrow(ax, [(3.27, 1.93), (3.48, 1.93)], lw=0.8, hw=0.14, hl=0.28)
    arrow(ax, [(3.27, 2.51), (5.03, 2.51)], lw=0.8, hw=0.14, hl=0.28)
    arrow(ax, [(4.72, 1.93), (5.03, 1.93)], lw=0.8, hw=0.14, hl=0.28)
    txt(ax, 4.15, 2.62, "시뮬 약 69 %", fs=5.2)
    # L9 row
    section(ax, 0.03, 0.05, W - 0.06, 1.45, "다음: L9 생성기 (L8S의 5배, 구현 중)")
    lay = [("장면 층", "받침면 그래프\n환경 8계열"), ("과제 층", "기본 동작 조합\n과제 ≥ 75"),
           ("다양화 층", "방·재질·조명·목 자세\n모든 편 조합 다르게"), ("편 실행", "좌·우 팔, 사람 같은 동작\nL8S 형식 저장")]
    x = 0.20
    for i, (t, s) in enumerate(lay):
        box(ax, x, 0.62, 1.12, 0.62, OF, t, s, tfs=6.4, sfs=4.9)
        if i < 3:
            arrow(ax, [(x + 1.14, 0.93), (x + 1.30, 0.93)], lw=0.8, hw=0.14, hl=0.28)
        x += 1.32
    box(ax, 5.55, 0.62, 1.20, 0.62, UP, "다음 본 학습", "기본 모델부터\nL8S + L9 + 미리 내기 행", tfs=6.4, sfs=4.9)
    arrow(ax, [(x - 0.16, 0.93), (5.53, 0.93)], lw=0.8, hw=0.14, hl=0.28)
    box(ax, 1.52, 0.14, 3.80, 0.34, VL, "결합 학습용 로그: 매 순간 프레임 · 관절 · 명령 발행/도착 시각 → 미리 내기 행 · VLA 데이터", tfs=5.6)
    arrow(ax, [(4.51, 0.60), (4.51, 0.50)], lw=0.7, hw=0.12, hl=0.25)
    txt(ax, 0.62, 0.30, "비현실 모드는\n효과 검증 전 제외", fs=4.9, c=SUB)
    save(fig, "f7_data")


# ============================================================ F8 settled conclusions map
CONCL = [
    # (conclusion, evidence exp, key number, grade)  grade: "확정" or "방향"
    ("영샷 오픈 모델은 위치를 못 읽는다 → 시뮬 참값 학습이 전제", "E-TEACH-L8", "8B 접근 xy 125.5 → 2.6 mm, 폐루프 0/4 → 4/4", "확정"),
    ("거리 숫자 출력은 새 탁자 높이에서 무너진다 → 깊이 점", "E-PT", "새 높이 3.5–3.6 mm 대 xyz 31–71 mm, 폐루프 8/8", "확정"),
    ("손으로 준 탁자 높이는 참값일 때만 돕는다 → 입력에서 제거", "E-STRIP8b · E-PRIV8", "참값 입력 4.0 mm, 학습에서만 쓰기 10.9–20.5 mm", "확정"),
    ("출력 형식은 D가 하이브리드 H보다 낫다", "E-FINAL35", "새 물체 4.0 대 83.7 mm, 폐루프 6/8 대 4/8", "확정"),
    ("공개 점 데이터가 새 물체 일반화의 핵심", "E-FINAL35", "빼면 새 물체 85.3 mm, 짝 차 [−25.6, −8.0] mm", "확정"),
    ("실행기 규칙(깊이 기억·'위' 반복 전환)이 폐루프를 올린다", "boost1", "같은 8편 2/8 → 4/8, 퇴행 0", "확정"),
    ("사실적 L8S가 새 물체를 크게 개선", "E-C35", "새 물체 중앙 40.9 → 9.6 mm, 실패 60 → 36 %", "확정"),
    ("상위 결정이 VLA 실행을 조종하게 만들 수 있다", "E-SR1c · E-SR1e", "먼 구간 준수 0.34 → 0.991(시뮬)·0.899(실데이터)", "확정"),
    ("층 사이 부품이 새 실패를 만든다 → 연결 손실을 따로 잰다", "E-VLA-solo", "VLA 단독 0/12, 그중 8편 런타임 교착", "확정"),
    ("공개 비중을 0.59보다 올리면 L8-X가 나빠진다", "E-OPR3", "dev 실패 21.2 → 27.3 %, G 적중 0.64–0.65 같음", "방향"),
    ("L8S는 많을수록 낫고 50 % 뒤 포화에 가깝다", "E-L8SW", "새 물체 30.0 → 10.2 → 10.2 mm", "방향"),
]


def f8_conclusions():
    W = FULL_W
    rh = 0.285
    H = 0.45 + rh * len(CONCL) + 0.30
    fig, ax = canvas(W, H)
    cols = [0.08, 3.28, 4.26, 6.28]
    hy = H - 0.22
    for x, t in zip(cols, ["확정된 결론", "근거 실험", "핵심 수치 (초기값)", "등급"]):
        txt(ax, x, hy, t, fs=6.6, c=TXT, ha="left", bold=True)
    ax.plot([0.05, W - 0.05], [hy - 0.14, hy - 0.14], color="#888", lw=0.7)
    for k, (c, e, n, g) in enumerate(CONCL):
        y = hy - 0.14 - rh * (k + 0.5)
        if k % 2 == 0:
            ax.add_patch(Rectangle((0.05, y - rh / 2), W - 0.10, rh, fc="#F6F6F6", ec="none"))
        txt(ax, cols[0], y, c, fs=5.9, c=TXT, ha="left")
        txt(ax, cols[1], y, e, fs=5.7, c=SUB, ha="left")
        txt(ax, cols[2], y, n, fs=5.5, c=TENT, ha="left")
        col = ("#DCEFD9", "#3E8E3A") if g == "확정" else ("#FFF1C9", "#B98A12")
        ax.add_patch(FancyBboxPatch((cols[3], y - 0.085), 0.50, 0.17, boxstyle="round,pad=0,rounding_size=0.04",
                                    fc=col[0], ec=col[1], lw=0.7))
        txt(ax, cols[3] + 0.25, y, "확정" if g == "확정" else "방향 신호", fs=5.4, c=col[1], bold=True)
    yb = hy - 0.14 - rh * len(CONCL) - 0.14
    txt(ax, 0.08, yb, "확정 = 사전 등록 판정을 짝 비교로 통과(표본은 작음) · 방향 신호 = 시드 1개 경향. "
        "E-SR1c·E-SR1e는 오프라인 준수, E-VLA-solo는 옛 체크포인트 기준.", fs=5.2, c=SUB, ha="left")
    save(fig, "f8_conclusions")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    f1_overview()
    f2_upper_call()
    f3_vla()
    f4_timeline()
    f5_training()
    f6_coupling_loss()
    f7_data()
    f8_conclusions()
