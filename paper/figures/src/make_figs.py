"""Harvest paper figures (style: CVPR/VLA papers such as OpenVLA, pi0 -- pastel rounded boxes,
thin gray elbow arrows, numbered circles, minimal text, dashed system container, flat icons).
Content comes only from docs/design (SUMMARY v3.4, 00-interfaces §7, §26, §27).
Run:  PYTHONPATH=D:/tools/pylib python paper/figures/src/make_figs.py
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
    ax.text(x, y - 0.015 * s, "API", ha="center", va="center", fontsize=5.5 * s, color=ec, zorder=5, fontweight="bold")


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
def fig_overview():
    W, H = FULL_W, 2.9
    fig, ax = canvas(W, H)
    container(ax, 1.05, 0.08, 5.02, 2.76, "Harvest")

    # inputs (left)
    rbox(ax, 0.02, 1.95, 0.92, 0.5, "gray", "“{과제}”", fs=9)
    ax.text(0.48, 1.84, "사용자 명령", ha="center", va="top", fontsize=6.8, color="#444")
    icon_scene(ax, 0.1, 0.62, 0.76, 0.56, "std")
    ax.text(0.48, 0.55, "카메라 관측", ha="center", va="top", fontsize=6.8, color="#444")

    # slow layer
    rbox(ax, 1.55, 1.95, 1.55, 0.62, "astra", "Astra", fs=11, sub="느린 계획기 · effort 기본 low", sfs=6.3)
    icon_cloud(ax, 1.78, 2.40, s=0.9)
    num(ax, 1.55, 2.57, 1)
    icon_doc(ax, 3.35, 1.98, 0.36, 0.48)
    ax.text(3.53, 2.50, "세션 계약", ha="center", va="bottom", fontsize=6.8, color="#444")
    rbox(ax, 4.05, 1.98, 1.25, 0.5, "mem", "경험", fs=9.5, sub="검증된 교훈·규칙만", sfs=6.1)
    num(ax, 4.05, 2.48, 6)

    # fast layer
    rbox(ax, 1.20, 0.55, 1.0, 0.72, "perc", "텍스트 상태", fs=8.5, sub="술어 등록부\n물체 ID 술어 표", sfs=6.0)
    num(ax, 1.20, 1.27, 2)
    rbox(ax, 2.45, 0.55, 1.20, 0.72, "jev", "Jev", fs=11, sub="typed 객관식 · 약 3 Hz", sfs=6.3)
    for k in range(3):
        pill(ax, 2.60 + k * 0.32, 1.10, 0.26, 0.11, "jev")
    num(ax, 2.45, 1.27, 3)
    rbox(ax, 3.90, 0.55, 1.05, 0.72, "jev", "확정 규칙", fs=9, sub="(a) 합의 + (b) 예상 대 측정", sfs=5.7)
    num(ax, 3.90, 1.27, 4)
    rbox(ax, 5.15, 0.55, 0.78, 0.72, "skill", "스킬", fs=9.5, sub="100 Hz", sfs=6.3)
    rbox(ax, 5.15, 1.45, 0.78, 0.36, "crit", "코드 critic", fs=7.2)
    num(ax, 5.15, 1.81, 5)

    # output
    icon_robot(ax, 6.40, 0.62, s=1.1)
    ax.text(6.47, 0.52, "로봇", ha="center", va="top", fontsize=6.8, color="#444")

    # arrows
    arr(ax, [(0.94, 2.2), (1.55, 2.2)])
    arr(ax, [(0.86, 0.9), (1.20, 0.9)])
    arr(ax, [(3.10, 2.22), (3.35, 2.22)])
    arr(ax, [(3.53, 1.98), (3.53, 1.62), (3.05, 1.62), (3.05, 1.27)])
    ax.text(3.10, 1.44, "현재 단계 조각", fontsize=6.0, color="#555", va="center", ha="left")
    arr(ax, [(4.05, 2.23), (3.71, 2.23)])
    arr(ax, [(2.20, 0.91), (2.45, 0.91)])
    arr(ax, [(3.65, 0.91), (3.90, 0.91)])
    arr(ax, [(4.95, 0.91), (5.15, 0.91)])
    arr(ax, [(5.93, 0.91), (6.28, 0.91)])
    arr(ax, [(5.54, 1.27), (5.54, 1.45)])
    # failure -> Astra (async)
    arr(ax, [(5.54, 1.81), (5.54, 1.92), (2.60, 1.92), (2.60, 1.95)], color=PAL["crit"][1], lw=1.2, ls=(0, (3, 2)))
    ax.text(4.55, 1.87, "실패 → Astra 비동기 호출", fontsize=6.2, color=PAL["crit"][1],
            ha="center", va="top")
    icon_grid(ax, 1.62, 1.50, 0.55, 0.22)
    ax.text(1.895, 1.46, "연속 프레임 (10장 격자)", fontsize=5.6, color="#555", ha="center", va="top")
    arr(ax, [(1.895, 1.72), (1.895, 1.95)])
    save(fig, "overview")


# ================================================================ Fig 2: M4
def fig_m4():
    W, H = FULL_W, 2.55
    fig, ax = canvas(W, H)
    # (left) staggered calls on a time axis
    x0, y0, sx = 0.35, 0.55, 1.05  # 1 s = 1.05 in
    ax.plot([x0, x0 + 2.0 * sx], [y0 - 0.12, y0 - 0.12], color="#777", lw=0.9)
    for t in [0, 0.5, 1.0, 1.5]:
        ax.plot([x0 + t * sx] * 2, [y0 - 0.15, y0 - 0.09], color="#777", lw=0.9)
        ax.text(x0 + t * sx, y0 - 0.2, f"{t:g}", ha="center", va="top", fontsize=6, color="#555")
    ax.text(x0 + 1.0 * sx, y0 - 0.36, "시간 (s)", ha="center", va="top", fontsize=6.3, color="#555")
    lat = 0.45
    for i in range(5):
        t0 = i * 0.33
        pill(ax, x0 + t0 * sx, y0 + i * 0.28, lat * sx, 0.19, "jev", f"호출 {i+1}", fs=6.2)
    ax.annotate("", xy=(x0 + 0.33 * sx, y0 - 0.03), xytext=(x0, y0 - 0.03),
                arrowprops=dict(arrowstyle="<->", lw=0.8, color="#555"))
    ax.text(x0 + 0.38 * sx, y0 - 0.03, "0.33 s", ha="left", va="center", fontsize=6.0, color="#444")
    ax.text(x0, H - 0.12, "(a) 1초에 약 3번 겹쳐 호출", fontsize=8, va="top", color=TXT, fontweight="bold")

    # (middle) vote table: future steps x calls, regions
    tx, ty, cw, chh = 2.95, 0.55, 0.30, 0.26
    votes = [["A", "A", "A", "B", "B", "B", "C", "C"],
             ["A", "A", "A", "B", "B", "C", "C", "C"],
             ["",  "A", "A", "B", "B", "B", "C", "D"],
             ["",  "",  "A", "B", "B", "B", "C", "C"]]
    reg = ["fix"] * 2 + ["mid"] * 4 + ["tail"] * 2
    fcol = {"fix": "#E4E4E4", "mid": PAL["jev"][0], "tail": "#FFFFFF"}
    for i, row in enumerate(votes):
        for j, v in enumerate(row):
            ax.add_patch(Rectangle((tx + j * cw, ty + (3 - i) * chh), cw, chh, fc=fcol[reg[j]], ec="#B5B5B5", lw=0.6))
            if v:
                ax.text(tx + j * cw + cw / 2, ty + (3 - i) * chh + chh / 2, v, ha="center", va="center", fontsize=7)
        ax.text(tx - 0.06, ty + (3 - i) * chh + chh / 2, f"호출 {i+1}", ha="right", va="center", fontsize=6.0, color="#444")
    for j in range(8):
        ax.text(tx + j * cw + cw / 2, ty - 0.07, f"t+{j}", ha="center", va="top", fontsize=5.8, color="#555")
    top = ty + 4 * chh + 0.05
    for lab, a, b in [("고정", 0, 2), ("중간", 2, 6), ("끝", 6, 8)]:
        ax.plot([tx + a * cw + 0.03, tx + b * cw - 0.03], [top, top], color="#777", lw=0.9)
        ax.text(tx + (a + b) / 2 * cw, top + 0.04, lab, ha="center", va="bottom", fontsize=6.6, color="#333")
    ax.text(tx - 0.35, H - 0.12, "(b) 미래 스텝별 표 (보기 id 기준)", fontsize=8, va="top", color=TXT, fontweight="bold")
    ax.text(tx + 4 * cw, ty - 0.30, "고정: Jev p95 지연 길이 · 중간: 바꾸려면 합의 · 끝: 최신 표 가확정",
            ha="center", va="top", fontsize=5.8, color="#555")

    # (right) decision
    dx = 5.55
    ax.text(dx - 0.15, H - 0.12, "(c) 확정", fontsize=8, va="top", color=TXT, fontweight="bold")
    rbox(ax, dx, 1.62, 1.25, 0.36, "jev", "합의 (a)", fs=7.6)
    rbox(ax, dx, 1.14, 1.25, 0.36, "skill", "예상 대 측정 (b)", fs=7.6)
    rbox(ax, dx, 0.60, 0.58, 0.36, "skill", "유지", fs=7.6)
    rbox(ax, dx + 0.67, 0.60, 0.58, 0.36, "crit", "교체·수리", fs=7.3)
    arr(ax, [(dx + 0.62, 1.62), (dx + 0.62, 1.50)])
    arr(ax, [(dx + 0.30, 1.14), (dx + 0.30, 0.96)])
    arr(ax, [(dx + 0.95, 1.14), (dx + 0.95, 0.96)], color=PAL["crit"][1])
    ax.text(dx + 0.25, 1.06, "맞음", fontsize=5.8, ha="right", va="center", color="#444")
    ax.text(dx + 1.00, 1.06, "어긋남", fontsize=5.8, ha="left", va="center", color=PAL["crit"][1])
    ax.text(dx + 0.96, 0.53, "전제 epoch 무효화", fontsize=5.6, ha="center", va="top", color=PAL["crit"][1])
    arr(ax, [(tx + 8 * cw + 0.05, ty + 2 * chh), (dx - 0.12, ty + 2 * chh), (dx - 0.12, 1.80), (dx, 1.80)])
    save(fig, "m4_commit")


# ================================================================ Fig 3: failure timeline
def fig_recovery():
    W, H = COL_W, 2.0
    fig, ax = canvas(W, H)
    lanes = [("Astra", 1.55), ("L1 스킬 재시도", 1.17), ("L2 Jev 복구 선택", 0.79), ("L3 안전 대기", 0.41)]
    lx = 0.86
    for name, yy in lanes:
        ax.text(lx - 0.07, yy + 0.09, name, ha="right", va="center", fontsize=6.4, color="#333")
        ax.plot([lx, W - 0.05], [yy + 0.09, yy + 0.09], color="#E3E3E3", lw=0.8, zorder=0)
    t0, t1 = lx + 0.05, lx + 1.60
    ax.plot([t0, t0], [0.25, 1.85], color=PAL["crit"][1], lw=1.2, ls=(0, (3, 2)))
    ax.text(t0, 1.88, "실패 판정", ha="center", va="bottom", fontsize=6.4, color=PAL["crit"][1])
    pill(ax, t0, 1.55, t1 - t0, 0.18, "astra", "비동기 호출 · low 약 3 s", fs=5.9)
    ax.annotate("", xy=(W - 0.08, 1.64), xytext=(t1, 1.64), arrowprops=dict(arrowstyle="-|>", lw=0.8,
                color=PAL["astra"][1], ls=(0, (2, 2))))
    ax.text(W - 0.08, 1.76, "high 약 73 s", ha="right", va="bottom", fontsize=5.8, color=PAL["astra"][1])
    pill(ax, t0 + 0.03, 1.17, 0.55, 0.18, "skill", "인자 바꿔 1회", fs=5.6)
    pill(ax, t0 + 0.58, 0.79, 0.72, 0.18, "jev", "코드 제안 중 고름", fs=5.6)
    ax.add_patch(FancyBboxPatch((t0 + 1.02, 0.41), 0.55, 0.18, boxstyle="round,pad=0,rounding_size=0.09",
                                fc="#F4F4F4", ec="#9A9A9A", lw=0.9, ls=(0, (2, 2))))
    ax.text(t0 + 1.295, 0.50, "필요할 때만", ha="center", va="center", fontsize=5.6, color="#555")
    ax.plot([t1, t1], [0.25, 1.85], color=PAL["astra"][1], lw=0.9)
    ax.text(t1 + 0.05, 1.08, "새 계획 도착 →\n조건이 참인\n가장 늦은\n체크포인트\n에서 재개",
            fontsize=5.7, color="#333", va="center", ha="left", linespacing=1.25)
    ax.text(W / 2 + 0.3, 0.12, "시간 (개념도, 길이는 비례 아님)", ha="center", va="center", fontsize=5.8, color="#777")
    save(fig, "failure_timeline")


# ================================================================ Fig 4: evaluation protocol
def fig_eval():
    W, H = COL_W, 1.75
    fig, ax = canvas(W, H)
    icon_scene(ax, 0.05, 0.98, 0.55, 0.42, "std")
    icon_scene(ax, 0.05, 0.32, 0.55, 0.42, "rnd")
    ax.text(0.325, 1.44, "standard", ha="center", va="bottom", fontsize=6.2, color="#444")
    ax.text(0.325, 0.28, "random", ha="center", va="top", fontsize=6.2, color="#444")
    rbox(ax, 0.82, 0.55, 0.62, 0.62, "perc", "같은\n인식 앞단", fs=7.0)
    rbox(ax, 1.70, 1.02, 0.80, 0.46, "gray", "학습 정책", fs=7.2, sub="VLA 포함", sfs=5.8)
    rbox(ax, 1.70, 0.25, 0.80, 0.46, "jev", "LLM 결정 층", fs=7.2, sub="Astra + Jev", sfs=5.8)
    rbox(ax, 2.72, 0.55, 0.48, 0.62, "skill", "같은\n실행기", fs=6.8)
    arr(ax, [(0.60, 1.19), (0.70, 1.19), (0.70, 0.86), (0.82, 0.86)])
    arr(ax, [(0.60, 0.53), (0.70, 0.53), (0.70, 0.86), (0.82, 0.86)], head=False)
    arr(ax, [(1.44, 0.86), (1.57, 0.86), (1.57, 1.25), (1.70, 1.25)])
    arr(ax, [(1.57, 0.86), (1.57, 0.48), (1.70, 0.48)])
    arr(ax, [(2.50, 1.25), (2.61, 1.25), (2.61, 0.86), (2.72, 0.86)])
    arr(ax, [(2.50, 0.48), (2.61, 0.48), (2.61, 0.86)], head=False)
    ax.text(2.10, 0.86, "결정 층만 교체", ha="center", va="center", fontsize=5.9, color="#555")
    ax.text(W / 2, 0.06, "지표: standard → random 짝지은 상대 하락", ha="center", va="center", fontsize=6.3, color="#333")
    save(fig, "eval_protocol")


# ================================================================ Fig 5: preliminary drop (OpenVLA bar style)
def fig_prelim():
    names = ["GPT-6 Astra", "π$_{0.5}$", "Spatial Forcing", "X-VLA"]
    std = [35.32, 20.92, 21.25, 17.92]
    rnd = [31.40, 5.82, 6.98, 3.04]
    drop = ["−11.1%", "−72.2%", "−67.2%", "−83.0%"]
    fig, ax = plt.subplots(figsize=(COL_W, 1.85))
    x = np.arange(4); w = 0.36
    ax.bar(x - w / 2, std, w, color="#A7C4E5", label="standard", zorder=3)
    ax.bar(x + w / 2, rnd, w, color="#E8A07A", label="random", zorder=3)
    for xi, s, r, d in zip(x, std, rnd, drop):
        ax.text(xi - w / 2, s + 0.6, f"{s:.2f}", ha="center", va="bottom", fontsize=5.8, color="#333")
        ax.text(xi + w / 2, r + 0.6, f"{r:.2f}", ha="center", va="bottom", fontsize=5.8, color="#333")
        ax.text(xi, max(s, r) + 4.6, d, ha="center", va="bottom", fontsize=6.6,
                color="#2F5E9E" if xi == 0 else "#B04A2A", fontweight="bold")
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
    fig_overview(); fig_m4(); fig_recovery(); fig_eval(); fig_prelim()
    print("ok")
