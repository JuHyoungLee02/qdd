"""Harvest paper figures (style: CVPR/VLA papers such as OpenVLA, pi0 -- pastel rounded boxes,
thin gray elbow arrows, numbered circles, minimal text, dashed system container, flat icons).
Content comes only from docs/design (00-interfaces §7, §26, §27, §45, §51-§59) and docs/stage3/results (measured values).
2026-09-25: redrawn for the fused decision-token VLA (§58); orange = tentative values, as in the paper.
Run:  MPLCONFIGDIR=D:/tools/mplcache PYTHONPATH=D:/tools/pylib python paper/figures/src/make_figs.py
      (D drive only: never let matplotlib write its cache to C:)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, Ellipse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
for f in ["C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"]:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": ["Malgun Gothic", "DejaVu Sans"],
    "font.size": 8, "axes.unicode_minus": False, "pdf.fonttype": 42,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})

# pastel fill / border pairs (OpenVLA-like)
PAL = {
    "astra": ("#FCE3CF", "#E08A3C"),   # slow planner (orange)
    "jev":   ("#D6E6F8", "#4A7FC1"),   # fast typed decisions (blue)
    "skill": ("#DCEFD9", "#5E9E57"),   # execution (green)
    "crit":  ("#F6DCE6", "#C2577F"),   # critic / failure (rose)
    "perc":  ("#FFF1C9", "#D2A52C"),   # perception (yellow)
    "mem":   ("#E9E2F5", "#8A6BBE"),   # memory (purple)
    "gray":  ("#F1F1F1", "#9A9A9A"),
}
ARROW = "#555555"
TXT = "#262626"
FULL_W, COL_W = 6.875, 3.25


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


def rbox(ax, x, y, w, h, kind="gray", text=None, fs=9, sub=None, sfs=6.5, r=0.06, lw=1.2, bold=False, tc=TXT):
    fc, ec = PAL[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))
    if text and sub:
        ax.text(x + w / 2, y + h * 0.62, text, ha="center", va="center", fontsize=fs, color=tc,
                fontweight="bold" if bold else "normal")
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=sfs, color="#555555", linespacing=1.25)
    elif text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
                fontweight="bold" if bold else "normal", linespacing=1.2)


def pill(ax, x, y, w, h, kind="jev", text=None, fs=6.5):
    fc, ec = PAL[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={h/2}", fc=fc, ec=ec, lw=1.0))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=TXT)


def container(ax, x, y, w, h, label=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                fc="none", ec="#BDBDBD", lw=1.1, ls=(0, (4, 3))))
    if label:
        ax.text(x + 0.10, y + h - 0.08, label, ha="left", va="top", fontsize=13, color="#4A4A4A", fontweight="bold")


def num(ax, x, y, n, r=0.085):
    ax.add_patch(Circle((x, y), r, fc="white", ec="#555555", lw=0.9, zorder=5))
    ax.text(x, y - 0.005, str(n), ha="center", va="center", fontsize=7, color="#333", zorder=6)


def arr(ax, pts, color=ARROW, lw=1.0, ls="-", head=True):
    """elbow polyline arrow through pts [(x,y),...]"""
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] + (xs[-1],), ys[:-1] + (ys[-1],), color=color, lw=lw, ls=ls, solid_capstyle="butt",
            solid_joinstyle="miter")
    if head:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ax.annotate("", xy=(x1, y1), xytext=(x0 + (x1 - x0) * 0.6, y0 + (y1 - y0) * 0.6),
                    arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=color, lw=lw,
                                    shrinkA=0, shrinkB=0))


# ---------- flat icons ----------
def icon_robot(ax, x, y, s=1.0, c="#3E3E3E"):
    """simple arm: base, two links, gripper"""
    ax.add_patch(Rectangle((x - 0.16 * s, y), 0.32 * s, 0.07 * s, fc=c, ec="none"))
    pts = [(x, y + 0.07 * s), (x - 0.06 * s, y + 0.42 * s), (x + 0.26 * s, y + 0.58 * s)]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=c, lw=4.2 * s, solid_capstyle="round")
    for p in pts:
        ax.add_patch(Circle(p, 0.035 * s, fc="white", ec=c, lw=1.0, zorder=4))
    gx, gy = x + 0.26 * s, y + 0.58 * s
    ax.plot([gx, gx + 0.09 * s], [gy, gy + 0.05 * s], color=c, lw=2 * s)
    ax.plot([gx + 0.09 * s, gx + 0.15 * s], [gy + 0.05 * s, gy + 0.10 * s], color=c, lw=1.6 * s)
    ax.plot([gx + 0.09 * s, gx + 0.16 * s], [gy + 0.05 * s, gy - 0.01 * s], color=c, lw=1.6 * s)


def icon_cloud(ax, x, y, s=1.0, fc="#FFFFFF", ec="#E08A3C"):
    for dx, dy, r in [(-0.10, 0, 0.08), (0.0, 0.05, 0.10), (0.11, 0.0, 0.08)]:
        ax.add_patch(Circle((x + dx * s, y + dy * s), r * s, fc=fc, ec=ec, lw=1.0))
    ax.add_patch(Rectangle((x - 0.10 * s, y - 0.08 * s), 0.21 * s, 0.08 * s, fc=fc, ec="none", zorder=3))
    ax.plot([x - 0.18 * s, x + 0.19 * s], [y - 0.08 * s, y - 0.08 * s], color=ec, lw=1.0, zorder=4)
    ax.text(x, y - 0.015 * s, "API", ha="center", va="center", fontsize=6.3, color=ec, zorder=5, fontweight="bold")


def icon_grid(ax, x, y, w, h, nx=5, ny=2, c="#9A9A9A"):
    """multi-frame grid (user example: 10 frames in one image)"""
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=c, lw=0.9))
    cw, ch = w / nx, h / ny
    rng = np.random.default_rng(3)
    for i in range(nx):
        for j in range(ny):
            ax.add_patch(Rectangle((x + i * cw + cw * 0.08, y + j * ch + ch * 0.1), cw * 0.84, ch * 0.8,
                                   fc="#E7EEF6", ec="none"))
            ax.add_patch(Rectangle((x + i * cw + cw * (0.3 + 0.05 * i), y + j * ch + ch * 0.18),
                                   cw * 0.22, ch * 0.28, fc="#E8A36B", ec="none"))


def icon_doc(ax, x, y, w, h, ec="#E08A3C"):
    ax.add_patch(Polygon([(x, y), (x + w, y), (x + w, y + h * 0.78), (x + w * 0.78, y + h), (x, y + h)],
                         closed=True, fc="white", ec=ec, lw=1.0))
    for k in range(4):
        ax.plot([x + w * 0.15, x + w * (0.8 if k % 2 else 0.6)], [y + h * (0.72 - 0.17 * k)] * 2, color=ec, lw=0.8)


def icon_scene(ax, x, y, w, h, variant="std"):
    """flat tabletop thumbnail; random variant changes background, layout, distractor"""
    bg = "#EEF3F8" if variant == "std" else "#F4E9DD"
    table = "#C9B79C" if variant == "std" else "#9FB7A5"
    ax.add_patch(Rectangle((x, y), w, h, fc=bg, ec="#B0B0B0", lw=0.8))
    ax.add_patch(Polygon([(x + w * 0.05, y + h * 0.08), (x + w * 0.95, y + h * 0.08),
                          (x + w * 0.80, y + h * 0.48), (x + w * 0.20, y + h * 0.48)], closed=True, fc=table, ec="none"))
    if variant == "std":
        ax.add_patch(Rectangle((x + w * 0.32, y + h * 0.22), w * 0.12, h * 0.18, fc="#D9534F", ec="none"))
        ax.add_patch(Ellipse((x + w * 0.64, y + h * 0.26), w * 0.22, h * 0.08, fc="#5B8FD1", ec="none"))
    else:
        ax.add_patch(Rectangle((x + w * 0.56, y + h * 0.20), w * 0.12, h * 0.18, fc="#D9534F", ec="none"))
        ax.add_patch(Ellipse((x + w * 0.34, y + h * 0.30), w * 0.22, h * 0.08, fc="#5B8FD1", ec="none"))
        ax.add_patch(Circle((x + w * 0.76, y + h * 0.30), w * 0.05, fc="#F2C94C", ec="none"))
        ax.add_patch(Rectangle((x + w * 0.7, y + h * 0.62), w * 0.2, h * 0.25, fc="#FFFFFF", ec="#B0B0B0", lw=0.5))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=220)
    plt.close(fig)


# ================================================================ Fig 1: overview (teaser)
PAL["rule"] = ("#ECECEC", "#6F6F6F")    # M4 commit rule (code) -- neutral, not a failure color
PAL["fix"] = ("#F3E6DA", "#9C6B45")     # replace / repair (not failure)


def tag(ax, x, y, s):
    """module tag on a box corner (replaces bare numbers; paper uses M-numbers)"""
    w = 0.075 * len(s) + 0.06
    ax.add_patch(FancyBboxPatch((x - w / 2, y - 0.07), w, 0.14, boxstyle="round,pad=0,rounding_size=0.07",
                                fc="white", ec="#555555", lw=0.8, zorder=5))
    ax.text(x, y - 0.003, s, ha="center", va="center", fontsize=6.3, color="#333", zorder=6)


def wbox(ax, x, y, w, h, ec, text, fs=7.0, sub=None, sfs=6.0, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc=fc, ec=ec, lw=1.0))
    if sub:
        ax.text(x + w / 2, y + h * 0.66, text, ha="center", va="center", fontsize=fs, color=TXT)
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=sfs, color="#555555")
    else:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=TXT)


def overview_strip(ax, W, Hs):
    """(b) three time scales on one clock; the robot never stops after T0."""
    ax.text(0.04, Hs - 0.04, "(b) 세 시간 척도와 비정지 실행", fontsize=8, va="top", color=TXT, fontweight="bold")
    x0, x1, T = 1.55, 6.70, 12.0
    sx = (x1 - x0) / T
    X = lambda t: x0 + t * sx
    lanes = [("Astra (초 단위, 비동기)", 0.90), ("decide: 결정 토큰 (0.33 s 겹침)", 0.64),
             ("chunk: 행동 (0.5 s 청크, 100 Hz)", 0.38)]
    for name, yy in lanes:
        ax.text(x0 - 0.08, yy, name, ha="right", va="center", fontsize=6.4, color="#333")
        ax.plot([x0, x1], [yy, yy], color="#E6E6E6", lw=0.8, zorder=0)
    # Astra lane
    pill(ax, X(0), 0.82, 3.0 * sx, 0.16, "astra", "T0 첫 계획", fs=6.0)
    pill(ax, X(8.0), 0.82, 3.0 * sx, 0.16, "astra", "하트비트 (5 s 뒤)", fs=6.0)
    ax.annotate("", xy=(X(8.0), 1.02), xytext=(X(3.0), 1.02),
                arrowprops=dict(arrowstyle="<->", lw=0.8, color=PAL["astra"][1]))
    ax.text(X(5.5), 1.04, "N = 5 s (잠정)", ha="center", va="bottom", fontsize=6.0, color=PAL["astra"][1])
    ax.text(X(5.5), 0.90, "단계 경계·실패 때도 기다리지 않고 호출", ha="center", va="center", fontsize=6.0,
            color="#555", bbox=dict(fc="white", ec="none", pad=1.0), zorder=4)
    # decision lane: staggered calls every 0.33 s, each ~0.28 s long
    k = 0
    t = 3.0
    while t + 0.28 <= T:
        yy = 0.59 if k % 2 == 0 else 0.66
        ax.add_patch(FancyBboxPatch((X(t), yy), 0.28 * sx, 0.06, boxstyle="round,pad=0,rounding_size=0.02",
                                    fc=PAL["jev"][0], ec=PAL["jev"][1], lw=0.6))
        t += 0.33
        k += 1
    # action lane
    ax.add_patch(Rectangle((X(0), 0.32), 3.0 * sx, 0.12, fc="#F2F2F2", ec="#9A9A9A", lw=0.7, hatch="////"))
    ax.text(X(1.5), 0.28, "정지 (T0만 허용)", ha="center", va="top", fontsize=6.0, color="#666")
    ax.add_patch(Rectangle((X(3.0), 0.32), (T - 3.0) * sx, 0.12, fc=PAL["skill"][0], ec=PAL["skill"][1], lw=0.9))
    tt = 3.5
    while tt < T:
        ax.plot([X(tt), X(tt)], [0.32, 0.44], color="white", lw=0.8)
        tt += 0.5
    ax.text(X(7.5), 0.28, "로봇은 계속 움직인다 (보류 = 직전 확정 행동 유지 + 감속)", ha="center", va="top",
            fontsize=6.0, color=PAL["skill"][1])
    # time axis
    for tk in [0, 3, 6, 9, 12]:
        ax.text(X(tk), 0.02, f"{tk} s", ha="center", va="bottom", fontsize=6.0, color="#666")


def fig_overview():
    W, Hm, Hs = FULL_W, 3.10, 1.24
    H = Hm + Hs
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, Hs / H, 1, Hm / H])
    ax.set_xlim(0, W); ax.set_ylim(0, Hm); ax.axis("off")
    axs = fig.add_axes([0, 0, 1, Hs / H])
    axs.set_xlim(0, W); axs.set_ylim(0, Hs); axs.axis("off")
    overview_strip(axs, W, Hs)
    ax.text(0.04, Hm - 0.02, "(a) 구성", fontsize=8, va="top", color=TXT, fontweight="bold")
    container(ax, 1.10, 0.06, 5.72, 2.98, "Harvest")

    # inputs
    rbox(ax, 0.02, 2.30, 0.95, 0.45, "gray", "“{과제}”", fs=9)
    ax.text(0.495, 2.24, "사용자 명령", ha="center", va="top", fontsize=6.8, color="#444")
    icon_scene(ax, 0.08, 1.30, 0.80, 0.48, "std")
    ax.text(0.48, 1.25, "머리 카메라", ha="center", va="top", fontsize=6.6, color="#444")
    icon_scene(ax, 0.08, 0.58, 0.80, 0.40, "rnd")
    ax.text(0.48, 0.53, "활성 손목 카메라", ha="center", va="top", fontsize=6.6, color="#444")

    # slow layer: Astra + contract
    icon_cloud(ax, 1.82, 2.43, s=0.85)
    rbox(ax, 2.10, 2.25, 1.40, 0.58, "astra", "Astra", fs=11, sub="느린 API 계획기 · effort low", sfs=6.2)
    icon_doc(ax, 3.75, 2.30, 0.34, 0.46)
    ax.text(4.16, 2.53, "세션 계약", ha="left", va="center", fontsize=6.8, color="#444")
    arr(ax, [(0.97, 2.52), (1.62, 2.52)])
    arr(ax, [(3.50, 2.53), (3.75, 2.53)])

    # fused VLA: one backbone forward per step; decide (tokens + verification head) -> M4 -> chunk (expert)
    ax.add_patch(FancyBboxPatch((1.45, 0.74), 2.55, 1.18, boxstyle="round,pad=0,rounding_size=0.07",
                                fc=PAL["jev"][0], ec=PAL["jev"][1], lw=1.3))
    ax.text(2.725, 1.81, "융합 VLA (Qwen3-VL-4B)", ha="center", va="center", fontsize=9.5, color=TXT,
            fontweight="bold")
    wbox(ax, 1.60, 1.47, 2.25, 0.22, PAL["jev"][1], "decide · 결정 토큰  p(o) : 방향 · cm 구간 · 대상 · 단계", fs=6.2)
    wbox(ax, 1.60, 1.20, 2.25, 0.22, PAL["perc"][1], "decide · 확인 헤드 V1h : 세계 쪽 술어", fs=6.2)
    wbox(ax, 1.60, 0.93, 2.25, 0.22, PAL["skill"][1], "chunk · action expert : 확정 결정 조건 0.5 s 청크", fs=6.2)
    ax.text(2.725, 0.83, "백본 순전파는 스텝당 1회 (+ 보조 기하 헤드, 학습 신호)", ha="center", va="center",
            fontsize=5.8, color="#555")
    arr(ax, [(0.88, 1.54), (1.45, 1.54)])
    arr(ax, [(0.88, 0.80), (1.20, 0.80), (1.20, 1.10), (1.45, 1.10)])
    # contract -> VLA
    arr(ax, [(3.92, 2.30), (3.92, 2.08), (3.45, 2.08), (3.45, 1.92)])
    ax.text(3.40, 2.13, "현재 단계 요약", fontsize=6.0, color="#555", ha="right", va="bottom")
    # heartbeat VLA side -> Astra
    arr(ax, [(2.40, 1.92), (2.40, 2.25)], color=PAL["astra"][1], lw=1.1, ls=(0, (3, 2)))
    ax.text(2.35, 2.07, "하트비트(잠정 5 s) · 단계 경계", fontsize=6.0, color=PAL["astra"][1], ha="right",
            va="center")

    # M4 + projection
    rbox(ax, 4.20, 1.34, 0.95, 0.46, "rule", "M4 확정", fs=8.5, sub="(a) 합의 + (b) 측정", sfs=6.0)
    rbox(ax, 4.20, 0.60, 0.95, 0.40, "fix", "안전 투영", fs=8.0, sub="방향·구간 제한, 저크", sfs=5.8)
    arr(ax, [(3.85, 1.58), (4.20, 1.58)])                                   # decision tokens -> M4
    arr(ax, [(3.85, 1.31), (4.05, 1.31), (4.05, 1.43), (4.20, 1.43)], color=PAL["perc"][1])  # V1h -> M4 (b)
    arr(ax, [(4.45, 1.34), (4.45, 1.09), (3.85, 1.09)])                     # committed decision -> chunk
    ax.text(4.49, 1.20, "확정 → chunk", fontsize=5.8, color="#555", ha="left", va="center")
    arr(ax, [(3.85, 0.99), (4.02, 0.99), (4.02, 0.80), (4.20, 0.80)])        # chunk -> projection

    # robot
    icon_robot(ax, 5.70, 0.62, s=1.0)
    ax.text(5.77, 0.55, "로봇 (100 Hz)", ha="center", va="top", fontsize=6.6, color="#444")
    arr(ax, [(5.15, 0.80), (5.52, 0.80)])
    # measurement back to M4 (b) and to critic
    ax.plot([6.25, 6.25], [0.95, 1.98], color="#777", lw=0.9, ls=(0, (2, 2)))
    arr(ax, [(6.25, 1.55), (5.15, 1.55)], color="#777", lw=0.9, ls=(0, (2, 2)))
    ax.text(5.70, 1.60, "고유 감각 T1", fontsize=6.0, color="#555", ha="center", va="bottom")
    rbox(ax, 5.40, 1.96, 1.05, 0.34, "crit", "critic (실패 판정)", fs=6.6, sub="하드 T1 · 경보 V1h", sfs=5.6)
    # failure -> Astra
    arr(ax, [(5.95, 2.30), (5.95, 2.92), (2.80, 2.92), (2.80, 2.83)], color=PAL["crit"][1], lw=1.2,
        ls=(0, (3, 2)))
    ax.text(4.60, 2.87, "실패 → Astra 비동기 호출(연속 프레임) + 아래 층 복구", fontsize=6.0,
            color=PAL["crit"][1], ha="center", va="top")

    # modular baseline / teacher inset
    ax.add_patch(FancyBboxPatch((1.30, 0.12), 2.85, 0.52, boxstyle="round,pad=0,rounding_size=0.05",
                                fc="#FAFAFA", ec="#9A9A9A", lw=0.9, ls=(0, (3, 2))))
    ax.text(1.36, 0.585, "모듈형 기준선 · 교사", fontsize=6.2, color="#444", ha="left", va="top")
    wbox(ax, 1.38, 0.17, 0.78, 0.24, PAL["perc"][1], "명시적 인식", fs=6.2, fc=PAL["perc"][0])
    wbox(ax, 2.33, 0.17, 0.78, 0.24, PAL["jev"][1], "typed 결정", fs=6.2, fc=PAL["jev"][0])
    wbox(ax, 3.28, 0.17, 0.80, 0.24, PAL["skill"][1], "스크립트 스킬 S", fs=6.2, fc=PAL["skill"][0])
    arr(ax, [(2.16, 0.29), (2.33, 0.29)])
    arr(ax, [(3.11, 0.29), (3.28, 0.29)])
    arr(ax, [(3.68, 0.41), (3.68, 0.74)], color="#8A8A8A", lw=0.9, ls=(0, (1, 1.5)))
    ax.text(3.62, 0.53, "교사 데이터", fontsize=6.0, color="#666", ha="right", va="center")
    save(fig, "overview")


def fig_model():
    """one backbone forward per decision step; call 1 = decide (tokens + verification head, same forward),
    call 2 = chunk (expert on cached context, conditioned on the decision M4 committed) -- canon §61, §64, §67 C4."""
    W, H = COL_W, 2.30
    fig, ax = canvas(W, H)
    icon_scene(ax, 0.04, 1.70, 0.56, 0.40, "std")
    ax.text(0.32, 1.66, "머리 (252 토큰)", ha="center", va="top", fontsize=6.0, color="#444")
    icon_scene(ax, 0.04, 1.02, 0.56, 0.34, "rnd")
    ax.text(0.32, 0.98, "활성 손목 (104)", ha="center", va="top", fontsize=6.0, color="#444")
    wbox(ax, 0.04, 0.30, 0.56, 0.40, "#9A9A9A", "텍스트", fs=6.4, sub="과제·단계\n그리퍼", sfs=6.0,
         fc=PAL["gray"][0])
    rbox(ax, 0.78, 0.10, 0.74, 2.02, "jev", "Qwen3-VL-4B", fs=7.2, sub="LoRA r32\n비전 동결", sfs=6.0)
    arr(ax, [(0.60, 1.90), (0.78, 1.90)])
    arr(ax, [(0.60, 1.19), (0.78, 1.19)])
    arr(ax, [(0.60, 0.50), (0.78, 0.50)])
    hx, hw, hh = 1.80, 1.08, 0.40
    rows = {"dec": 1.70, "ver": 1.20, "aux": 0.70, "act": 0.12}
    rbox(ax, hx, rows["dec"], hw, hh, "jev", "결정 토큰", fs=6.8, sub="트라이 재정규화 → M4", sfs=5.6)
    rbox(ax, hx, rows["ver"], hw, hh, "crit", "확인 헤드 V1h", fs=6.8, sub="세계 술어 → M4 (b)·critic", sfs=5.6)
    rbox(ax, hx, rows["aux"], hw, hh, "perc", "보조 기하 헤드", fs=6.8, sub="상대 위치 (학습 신호)", sfs=5.6)
    rbox(ax, hx, rows["act"], hw, hh, "skill", "action expert", fs=6.8, sub="flow matching · 0.5 s", sfs=5.6)
    for k in ("dec", "ver"):
        arr(ax, [(1.52, rows[k] + hh / 2), (hx, rows[k] + hh / 2)])
    arr(ax, [(hx, rows["aux"] + hh / 2), (1.52, rows["aux"] + hh / 2)], color=PAL["perc"][1])
    ax.text(1.66, rows["aux"] + hh / 2 + 0.03, "∇", ha="center", va="bottom", fontsize=6.4, color=PAL["perc"][1])
    # expert reads cached context through stop-gradient (KI)
    ye = rows["act"] + hh / 2
    arr(ax, [(1.52, ye), (hx, ye)])
    ax.plot([1.64, 1.64], [ye - 0.06, ye + 0.06], color=PAL["crit"][1], lw=1.4)
    ax.plot([1.67, 1.67], [ye - 0.06, ye + 0.06], color=PAL["crit"][1], lw=1.4)
    ax.text(1.655, ye + 0.08, "sg", ha="center", va="bottom", fontsize=6.0, color=PAL["crit"][1])
    # committed decision from M4 into the expert (call 2)
    xr = hx + hw
    arr(ax, [(xr, rows["dec"] + hh / 2), (3.14, rows["dec"] + hh / 2), (3.14, ye), (xr, ye)], color="#6F6F6F")
    ax.text(3.19, (rows["dec"] + ye) / 2 + 0.25, "M4\n확정\n결정", ha="left", va="center", fontsize=5.6,
            color="#555", linespacing=1.1)
    # call brackets
    ax.plot([1.74, 1.74], [rows["ver"], rows["dec"] + hh], color="#4A7FC1", lw=0.8)
    ax.text(1.72, rows["dec"] + hh + 0.02, "호출 1 decide", ha="left", va="bottom", fontsize=5.6, color="#4A7FC1")
    ax.text(hx + hw / 2, rows["act"] + hh + 0.02, "호출 2 chunk", ha="center", va="bottom", fontsize=5.6,
            color=PAL["skill"][1])
    save(fig, "model")


def fig_latency():
    items = [  # label, lo, hi, kind
        ("제어 주기 (100 Hz)", 0.01, 0.01, "design"),
        ("chunk: expert 1회 (CUDA 그래프)", 0.023, 0.023, "tent"),
        ("문맥 순전파 + expert 1회 (HF)", 0.12, 0.12, "tent"),
        ("모듈형 결정 p95 (vLLM lead)", 0.18, 0.28, "tent"),
        ("융합 decide (폐루프, CPU 경합)", 0.255, 0.376, "tent"),
        ("결정 호출 간격 $T_c$", 0.33, 0.33, "design"),
        ("행동 청크 길이", 0.5, 0.5, "design"),
        ("모듈형 결정 p95 (캐시 끔)", 0.63, 0.63, "tent"),
        ("Astra low 첫 토큰 (1회)", 2.975, 2.975, "tent"),
        ("Astra 하트비트 실효 주기", 8.0, 9.0, "tent"),
        ("Astra high 첫 토큰 (공개 측정)", 73.0, 73.0, "public"),
    ]
    col = {"design": "#3A3A3A", "tent": "#E27000", "public": "#A8A8A8"}
    fig, ax = plt.subplots(figsize=(COL_W, 2.6))
    base = 0.005
    for i, (lab, lo, hi, k) in enumerate(items):
        y = len(items) - 1 - i
        ax.barh(y, lo - base, left=base, height=0.55, color=col[k], zorder=3)
        if hi > lo:
            ax.barh(y, hi - lo, left=lo, height=0.55, color=col[k], alpha=0.45, zorder=3)
        txt = (f"{lo:g}–{hi:g} s" if hi > lo else f"{lo:g} s")
        ax.text(hi * 1.18, y, txt, va="center", ha="left", fontsize=6.0, color="#333")
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([it[0] for it in items][::-1], fontsize=6.2)
    ax.set_xscale("log")
    ax.set_xlim(base, 600)
    ax.set_xticks([0.01, 0.1, 1, 10, 100])
    ax.set_xticklabels(["0.01", "0.1", "1", "10", "100"], fontsize=6.2)
    ax.set_xlabel("시간 (s, 로그 축)", fontsize=6.4)
    ax.axvline(0.33, color="#3A3A3A", lw=0.8, ls=(0, (3, 2)), zorder=2)
    ax.xaxis.grid(True, color="#E4E4E4", lw=0.6, zorder=0)
    ax.tick_params(length=0)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=col["design"], label="설계값"), Patch(color=col["tent"], label="임시(실측·가정)"),
                       Patch(color=col["public"], label="공개 측정")],
              fontsize=6.0, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 1.02))
    save(fig, "latency_budget")


# ================================================================ Fig 2: M4
def fig_m4():
    W, H = FULL_W, 2.55
    fig, ax = canvas(W, H)
    # (a) staggered calls on a time axis (bar length is illustrative; latency is measured in E0)
    x0, y0, sx = 0.35, 0.60, 1.05
    ax.plot([x0, x0 + 1.95 * sx], [y0 - 0.12, y0 - 0.12], color="#777", lw=0.9)
    for t in [0, 0.5, 1.0, 1.5]:
        ax.plot([x0 + t * sx] * 2, [y0 - 0.15, y0 - 0.09], color="#777", lw=0.9)
        ax.text(x0 + t * sx, y0 - 0.2, f"{t:g}", ha="center", va="top", fontsize=6, color="#555")
    ax.text(x0 + 0.95 * sx, y0 - 0.36, "시간 (s)", ha="center", va="top", fontsize=6.3, color="#555")
    for i in range(4):
        pill(ax, x0 + i * 0.33 * sx, y0 + i * 0.30, 0.45 * sx, 0.20, "jev", f"호출 {i+1}", fs=6.2)
    ax.annotate("", xy=(x0 + 0.33 * sx, y0 + 1.30), xytext=(x0, y0 + 1.30),
                arrowprops=dict(arrowstyle="<->", lw=0.8, color="#555"))
    ax.text(x0 + 0.38 * sx, y0 + 1.30, "간격 0.33 s", ha="left", va="center", fontsize=6.0, color="#444")
    ax.text(x0, H - 0.12, "(a) 1초에 약 3번 겹쳐 호출", fontsize=8, va="top", color=TXT, fontweight="bold")

    # (b) ledger: call i answers H=3 future steps (t+i-1 .. t+i+1); staircase
    tx, ty, cw, chh = 2.95, 0.60, 0.33, 0.27
    nsteps, ncalls, Hs = 6, 4, 3
    votes = {0: "AAA", 1: "AAB", 2: "ABB", 3: "BBC"}
    zone = ["fix", "fix", "mid", "mid", "mid", "tail"]
    fcol = {"fix": "#E4E4E4", "mid": PAL["jev"][0], "tail": "#FFFFFF"}
    for j in range(nsteps):
        for i in range(ncalls):
            yy = ty + (ncalls - 1 - i) * chh
            filled = i <= j <= i + Hs - 1
            ax.add_patch(Rectangle((tx + j * cw, yy), cw, chh, fc=fcol[zone[j]] if filled else "white",
                                   ec="#C4C4C4", lw=0.6))
            if filled:
                ax.text(tx + j * cw + cw / 2, yy + chh / 2, votes[i][j - i], ha="center", va="center", fontsize=7)
    for i in range(ncalls):
        ax.text(tx - 0.06, ty + (ncalls - 1 - i) * chh + chh / 2, f"호출 {i+1}", ha="right", va="center",
                fontsize=6.0, color="#444")
    for j in range(nsteps):
        ax.text(tx + j * cw + cw / 2, ty - 0.07, f"s{j+1}", ha="center", va="top", fontsize=6.0, color="#555")
    top = ty + ncalls * chh + 0.05
    for lab, a, b in [("고정", 0, 2), ("중간", 2, 5), ("끝", 5, 6)]:
        ax.plot([tx + a * cw + 0.03, tx + b * cw - 0.03], [top, top], color="#777", lw=0.9)
        ax.text(tx + (a + b) / 2 * cw, top + 0.04, lab, ha="center", va="bottom", fontsize=6.6, color="#333")
    ax.text(tx - 0.40, H - 0.12, "(b) 미래 스텝별 표 (option_key 기준, H=3)", fontsize=8, va="top", color=TXT,
            fontweight="bold")
    ax.text(tx + 3 * cw, ty - 0.24, "고정: 송신 뒤 d_p95 안 · 중간: 바꾸려면 합의(2/3, W=1) · 끝: 가장 새 표만",
            ha="center", va="top", fontsize=6.0, color="#555")
    ax.text(tx + 3 * cw, ty - 0.40, "H=1: 같은 스텝을 lead_max(1.0 s) 전부터 T_c마다 앞당겨 물어 2–3표",
            ha="center", va="top", fontsize=6.0, color="#555")

    # (c) decision (matches tab:m4rule)
    dx = 5.25
    ax.text(dx - 0.10, H - 0.12, "(c) 결정", fontsize=8, va="top", color=TXT, fontweight="bold")
    rbox(ax, dx, 1.72, 1.55, 0.30, "jev", "(a) 호출 사이 합의", fs=7.2)
    rbox(ax, dx, 1.28, 1.55, 0.30, "skill", "(b) 실행 뒤 예상 대 측정", fs=7.2)
    arr(ax, [(dx + 0.78, 1.72), (dx + 0.78, 1.58)])
    outs = [("OK + 합의", "확정", "skill"), ("LAG + 합의", "늦춰 확정", "gray"), ("DEVIATE", "교체", "fix"),
            ("CONTRADICT", "수리", "fix")]
    for k, (cond, act, kind) in enumerate(outs):
        yy = 1.06 - k * 0.22
        ax.text(dx + 0.02, yy + 0.09, cond, fontsize=6.0, color="#444", ha="left", va="center")
        rbox(ax, dx + 0.92, yy, 0.63, 0.19, kind, act, fs=6.8)
    ax.text(dx + 0.78, 0.32, "교체·수리: 전제 판본 +1,\n그 전제의 미확정 표 폐기", fontsize=6.0,
            color=PAL["fix"][1], ha="center", va="top", linespacing=1.2)
    ax.text(dx + 0.78, 0.02, "(b) 범주 → 다음 decide 입력 한 줄", fontsize=6.0,
            color="#E27000", ha="center", va="bottom")
    arr(ax, [(tx + nsteps * cw + 0.05, ty + 2 * chh), (dx - 0.12, ty + 2 * chh), (dx - 0.12, 1.87), (dx, 1.87)])
    save(fig, "m4_commit")


# ================================================================ Fig 3: failure timeline
def fig_recovery():
    W, H = COL_W, 2.0
    fig, ax = canvas(W, H)
    lanes = [("Astra (M8)", 1.55), ("L1 스킬 재시도", 1.17), ("L2 결정 토큰", 0.79), ("L3 안전 대기", 0.41)]
    lx = 0.86
    for name, yy in lanes:
        ax.text(lx - 0.07, yy + 0.09, name, ha="right", va="center", fontsize=6.3, color="#333")
        ax.plot([lx, W - 0.05], [yy + 0.09, yy + 0.09], color="#E3E3E3", lw=0.8, zorder=0)
    t0, t1 = lx + 0.05, lx + 1.70
    ax.plot([t0, t0], [0.25, 1.85], color=PAL["crit"][1], lw=1.2, ls=(0, (3, 2)))
    ax.text(t0, 1.88, "실패 판정 (M7)", ha="center", va="bottom", fontsize=6.3, color=PAL["crit"][1])
    pill(ax, t0, 1.55, 1.30, 0.18, "astra", "비동기 호출 (첫 토큰 low 약 3 s)", fs=6.0)
    ax.annotate("", xy=(t1, 1.64), xytext=(t0 + 1.30, 1.64), arrowprops=dict(arrowstyle="-", lw=0.9,
                color=PAL["astra"][1], ls=(0, (2, 2))))
    ax.text(t1 - 0.04, 1.78, "high: 첫 토큰 약 73 s", ha="right", va="bottom", fontsize=6.0, color=PAL["astra"][1])
    pill(ax, t0 + 0.03, 1.17, 0.62, 0.18, "skill", "인자 바꿔 1회", fs=6.0)
    pill(ax, t0 + 0.62, 0.79, 0.72, 0.18, "jev", "코드 제안 중 고름", fs=6.0)
    ax.add_patch(FancyBboxPatch((t0 + 1.06, 0.41), 0.50, 0.18, boxstyle="round,pad=0,rounding_size=0.09",
                                fc="#F4F4F4", ec="#9A9A9A", lw=0.9, ls=(0, (2, 2))))
    ax.text(t0 + 1.31, 0.50, "필요할 때만", ha="center", va="center", fontsize=6.0, color="#555")
    ax.plot([t1, t1], [0.25, 1.85], color=PAL["astra"][1], lw=0.9)
    ax.text(t1 + 0.05, 1.08, "새 계획 도착 →\n조건이 참인\n가장 늦은\n체크포인트\n에서 재개",
            fontsize=6.0, color="#333", va="center", ha="left", linespacing=1.25)
    ax.text(W / 2 + 0.3, 0.12, "시간 (개념도, 길이는 비례 아님)", ha="center", va="center", fontsize=6.0, color="#777")
    save(fig, "failure_timeline")


# ================================================================ Fig 4: evaluation protocol
def fig_eval():
    W, H = COL_W, 1.95
    fig, ax = canvas(W, H)
    icon_scene(ax, 0.04, 1.08, 0.56, 0.42, "std")
    icon_scene(ax, 0.04, 0.40, 0.56, 0.42, "rnd")
    ax.text(0.32, 1.54, "standard", ha="center", va="bottom", fontsize=6.2, color="#444")
    ax.text(0.32, 0.36, "random", ha="center", va="top", fontsize=6.2, color="#444")
    ax.text(0.32, 0.96, "같은 layout 짝", ha="center", va="center", fontsize=6.0, color="#555")
    # systems column
    ax.add_patch(FancyBboxPatch((0.80, 0.22), 1.55, 1.50, boxstyle="round,pad=0,rounding_size=0.05",
                                fc="none", ec="#BDBDBD", lw=0.9, ls=(0, (3, 2))))
    ax.text(1.575, 1.66, "바꾸는 축", ha="center", va="top", fontsize=6.4, color="#333", fontweight="bold")
    rbox(ax, 0.88, 1.12, 1.39, 0.36, "astra", "위층: Astra 켬 / 끔", fs=6.4)
    rbox(ax, 0.88, 0.70, 1.39, 0.36, "jev", "아래층: C · A · A+RL · B", fs=6.4)
    rbox(ax, 0.88, 0.28, 1.39, 0.36, "gray", "기준선: π0.5 · Astra만 · 룰 등", fs=6.2)
    arr(ax, [(0.60, 1.29), (0.70, 1.29), (0.70, 0.97), (0.80, 0.97)])
    arr(ax, [(0.60, 0.61), (0.70, 0.61), (0.70, 0.97)], head=False)
    # metric
    rbox(ax, 2.52, 0.62, 0.70, 0.70, "rule", "RD", fs=9, sub="1 − 성공(rnd)\n÷ 성공(std)", sfs=6.0)
    arr(ax, [(2.35, 0.97), (2.52, 0.97)])
    ax.text(W / 2, 0.08, "시계 두 가지: 지연 충실(simlat) · 동기 공정(생각 시간 공짜)", ha="center", va="center",
            fontsize=6.0, color="#333")
    save(fig, "eval_protocol")


# ================================================================ Fig: training stages C -> A -> B
TENT = "#E27000"


def fig_training():
    W, H = FULL_W, 1.95
    fig, ax = canvas(W, H)
    cols = [
        ("C  영점", "gray", [("데이터", "없음 (학습 안 함)", False),
                             ("정답", "---", False),
                             ("손실", "---", False),
                             ("실행", "스크립트 스킬 S", False),
                             ("역할", "기준선 행 · LLM 일반화 축의 출발점", False)]),
        ("A  결정층 학습", "jev", [("데이터", "시뮬 풀: standard + DR", False),
                                   ("정답", "labels_v2(관측 정의) + 결과 기반", False),
                                   ("손실", "보기 NLL(SFT) → 기대 보상 + KL(RL)", False),
                                   ("실행", "스크립트 스킬 S", False),
                                   ("역할", "결정 토큰만 학습 · M4 입력 확률", False)]),
        ("B  융합 VLA (주 시스템)", "skill", [("데이터", "시뮬 R2 + ROBOTIS 공개 ~9 GB", True),
                                            ("정답", "+ S 행동(교사) · 특권 기하", False),
                                            ("손실", "결정 NLL + flow matching(sg) + 보조", False),
                                            ("실행", "action expert + 안전 투영", False),
                                            ("역할", "런타임 모델 하나", False)]),
    ]
    bw, gap, x = 2.05, 0.30, 0.04
    top, bh = 1.62, 1.30
    for i, (title, kind, rows) in enumerate(cols):
        fc, ec = PAL[kind]
        ax.add_patch(FancyBboxPatch((x, top - bh), bw, bh, boxstyle="round,pad=0,rounding_size=0.06",
                                    fc="white", ec=ec, lw=1.2))
        ax.add_patch(FancyBboxPatch((x, top - 0.24), bw, 0.24, boxstyle="round,pad=0,rounding_size=0.06",
                                    fc=fc, ec=ec, lw=1.2))
        ax.text(x + bw / 2, top - 0.12, title, ha="center", va="center", fontsize=7.6, color=TXT, fontweight="bold")
        for j, (k, v, tent) in enumerate(rows):
            yy = top - 0.38 - j * 0.20
            ax.text(x + 0.08, yy, k, ha="left", va="center", fontsize=6.2, color="#666")
            ax.text(x + 0.46, yy, v, ha="left", va="center", fontsize=6.2, color=TENT if tent else TXT)
        if i < 2:
            arr(ax, [(x + bw + 0.03, top - bh / 2), (x + bw + gap - 0.03, top - bh / 2)], lw=1.3)
        x += bw + gap
    ax.text(W / 2, 0.18, "모델이 바뀔 때마다: 질문별 온도(보정 시드 절반) → conformal 문턱(나머지 절반)"
            "   ·   random 장면은 시험 전용 (학습·조정에 쓰지 않음)", ha="center", va="center", fontsize=6.3,
            color="#444")
    ax.text(W / 2, 1.82, "같은 Qwen3-VL-4B 백본 · LoRA · 같은 결정 질문과 보기", ha="center", va="center", fontsize=6.6,
            color="#333")
    save(fig, "training")


# ================================================================ Fig 5: preliminary drop (OpenVLA bar style)
def fig_prelim():
    names = ["GPT-6 Astra", "π$_{0.5}$", "Spatial Forcing", "X-VLA"]
    std = [35.32, 20.92, 21.25, 17.92]
    rnd = [31.40, 5.82, 6.98, 3.04]
    drop = ["−11.1%", "−72.2%", "−67.2%", "−83.0%"]
    fig, ax = plt.subplots(figsize=(COL_W, 1.85))
    x = np.arange(4); w = 0.36
    ax.bar(x - w / 2, std, w, color="#C9C9C9", label="standard", zorder=3)
    ax.bar(x + w / 2, rnd, w, color="#6E6E6E", label="random", zorder=3)
    for xi, s, r, d in zip(x, std, rnd, drop):
        ax.text(xi - w / 2, s + 0.6, f"{s:.2f}", ha="center", va="bottom", fontsize=6.0, color="#333")
        ax.text(xi + w / 2, r + 0.6, f"{r:.2f}", ha="center", va="bottom", fontsize=6.0, color="#333")
        ax.text(xi, max(s, r) + 4.6, d, ha="center", va="bottom", fontsize=6.6, color="#222",
                fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=6.6)
    ax.set_ylabel("RoboDojo Gen 점수", fontsize=6.6)
    ax.set_ylim(0, 46); ax.set_yticks([0, 10, 20, 30, 40])
    ax.yaxis.grid(True, color="#E2E2E2", lw=0.6, zorder=0)
    ax.tick_params(labelsize=6.2, length=0)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999")
    ax.legend(fontsize=6.2, frameon=False, loc="upper right", ncol=2, bbox_to_anchor=(1.0, 1.08))
    save(fig, "prelim_drop")


if __name__ == "__main__":
    fig_overview(); fig_model(); fig_training(); fig_m4(); fig_recovery(); fig_eval(); fig_latency(); fig_prelim()
    print("ok")
