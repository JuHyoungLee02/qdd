"""Harvest pipeline (current, 2026-09-30). Replaces archive/docs/design/pipeline_2026-09-26 (Astra-centric, obsolete).
Source of truth: D:/tools/scratch_qdd/board/NOW.md (sec. 1, 1-1, 5) and board/PLAN_coupling.md.
No Astra and no teacher policy: labels and oracle parts are sim ground truth computed from privileged information.
Run: MPLCONFIGDIR=D:/tools/mplcache python docs/design/pipeline_2026-09-30.py  (writes the .png next to this file)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

FONT = "C:/Windows/Fonts/malgun.ttf"
FONTB = "C:/Windows/Fonts/malgunbd.ttf"
fm.fontManager.addfont(FONT)
if os.path.exists(FONTB):
    fm.fontManager.addfont(FONTB)
plt.rcParams["font.family"] = fm.FontProperties(fname=FONT).get_name()

W, H = 24, 15.5
fig, ax = plt.subplots(figsize=(W, H), dpi=110)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

C = {
    "upper": ("#fde7d9", "#d9622b"),
    "code": ("#ececec", "#555555"),
    "vla": ("#dcebfb", "#2266b8"),
    "exec": ("#d9f2e4", "#1e8a4c"),
    "lat": ("#fff4c9", "#b58a00"),
    "robot": ("#ececec", "#555555"),
    "data": ("#efe4fa", "#6b3fa0"),
    "train": ("#e6f4f4", "#227777"),
    "eval": ("#f6dcdc", "#b3261e"),
}


def box(x, y, w, h, kind, title, lines, tsize=15, lsize=11.5, ls="-"):
    fc, ec = C[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18",
                                fc=fc, ec=ec, lw=2.2, ls=ls))
    ax.text(x + 0.18, y + h - 0.2, title, fontsize=tsize, fontweight="bold", color=ec, va="top", ha="left")
    ax.text(x + 0.18, y + h - 0.75, "\n".join(lines), fontsize=lsize, va="top", ha="left", color="#222222",
            linespacing=1.45)


def arrow(x1, y1, x2, y2, text="", color="#333333", ls="-", tx=0.0, ty=0.0, tsize=11, rad=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0, ls=ls, mutation_scale=18,
                                connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((x1 + x2) / 2 + tx, (y1 + y2) / 2 + ty, text, fontsize=tsize, color=color, ha="center",
                va="center", bbox=dict(fc="white", ec="none", alpha=0.9, pad=1.5))


def frame(x, y, w, h, label):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.2",
                                fc="none", ec="#999999", lw=1.4, ls="--"))
    ax.text(x + 0.25, y + h - 0.12, label, fontsize=15, color="#777777", va="top", fontweight="bold")


ax.text(0.3, H - 0.3, "Harvest 파이프라인 (현재, 2026-09-30)", fontsize=24, fontweight="bold", va="top")
ax.text(0.3, H - 1.0, "핵심 가설 H-J: 계획·판단·명령은 전부 상위 LLM이 맡고 VLA에는 상위 명령 기준의 미세 조종(조이스틱)만 준다"
        " → 짐을 덜어 준 VLA가 같은 크기의 단독 VLA보다 낫고, 두 층의 연결 손실은 작다",
        fontsize=13.5, va="top", color="#444444")

# ---------------------------------------------------------------- runtime
frame(0.2, 0.3, 15.9, H - 1.9, "실행(런타임)")

box(0.6, 10.0, 3.4, 2.7, "robot", "입력", [
    "머리 영상 (ZED, 머리 45°)",
    "쓰는 팔 손목 영상 (D405)",
    "고유 감각: 관절·그리퍼 폭·전류",
    "센서 깊이 (측정값)",
], tsize=14, lsize=11)

box(4.6, 9.4, 6.4, 3.3, "upper", "상위 계획기 = 본 35B (명령 권한 전부)", [
    "Qwen3.5-35B-A3B LoRA (지금 학습 중)",
    "구간 의도 · 명령 · 결과 검증(확정 근거 T1)",
    "방식 D: 머리 영상 위 점 + 높이 의도",
    "   (위 / 잡기 / 놓기 / 들기), m 숫자는 안 냄",
    "그리퍼 의도 + VLA 허용 범위(±cm·±°)",
], tsize=14.5, lsize=11.5)

box(11.6, 9.9, 4.2, 2.3, "code", "공용 코드: 픽셀 → xyz", [
    "센서 깊이 + 카메라 자기 정보",
    "탁자 평면·윗면 띠 중심",
    "상위와 VLA가 같은 코드 하나를 씀",
], tsize=13.5, lsize=11)

box(0.6, 5.3, 5.6, 3.1, "exec", "1단계: 결정적 실행기", [
    "명령을 최소 저크 직선 운동으로 수행",
    "쥐기 전 깊이 기억 · 'above' 반복 전환",
    "도달 오차·막힘 측정 → 새 영상으로 다시 묻기",
    "로봇은 상위 답을 기다림 (상위 단독 검증)",
], tsize=14, lsize=11)

box(6.7, 4.6, 5.3, 3.8, "vla", "2단계: 좁은 조이스틱 VLA", [
    "상위가 허용한 범위 안에서만 보정",
    "· 잡는 시점 · 작은 회피",
    "· 밀린 물체 재정렬",
    "+ 이상 신호 (이동 · 놓침 · 막힘)",
    "입력 목표 = 상위 명령, 스스로 계획 안 함",
    "행동 전문가 → 0.4 s 관절 청크",
], tsize=14, lsize=11, ls="--")

box(12.4, 4.6, 3.4, 4.3, "lat", "지연 줄이기", [
    "사건 기준 조기 재질의",
    "  (이상 신호·도착 임박)",
    "RTC식 겹치기: 생각하는",
    "  동안 앞 구간 계속 실행",
    "도착 전 다음 명령 선발행",
    "  + 취소 규칙(새 답이",
    "  반대하면 취소)",
], tsize=14, lsize=11)

box(3.6, 0.8, 8.8, 2.6, "robot", "로봇: ROBOTIS AI Worker FFW-SG2", [
    "7자유도 팔 ×2 + 평행 그리퍼, 머리 2자유도, 리프트 · 100 Hz 위치 명령",
    "안전: 관절 걸음 ≤ 0.04 rad (튐 금지)",
], tsize=14, lsize=11.5)

arrow(4.0, 11.3, 4.6, 11.3, "영상", tsize=10.5)
arrow(11.0, 11.0, 11.6, 11.0, "점 + 의도", color="#d9622b", tsize=10.5, ty=0.35)
arrow(13.7, 9.9, 3.4, 8.4, "목표 xyz", color="#555555", tsize=10.5, rad=0.0, tx=-2.0, ty=-0.25)
arrow(13.7, 9.9, 8.0, 8.4, "허용 범위 안 목표", color="#2266b8", tsize=10.5, tx=-1.3, ty=-0.35)
arrow(3.4, 5.3, 6.0, 3.4, "관절 명령", color="#1e8a4c", tsize=10.5, tx=-0.6)
arrow(9.35, 4.6, 8.6, 3.4, "보정된 청크", color="#2266b8", tsize=10.5, tx=0.9)
arrow(12.4, 6.3, 12.0, 6.3, "", color="#b58a00")
arrow(11.2, 8.4, 10.6, 9.4, "", color="#b3261e", ls="--")
ax.text(11.1, 9.05, "이상 신호", fontsize=10.5, color="#b3261e", ha="left", va="center")
ax.text(0.7, 4.5, "실선 = 1단계(지금, 상위 단독)\n점선 = 2단계(본 35B 평가 뒤)", fontsize=11, color="#666666", va="top")

# ---------------------------------------------------------------- right column: data / training / evaluation
frame(16.4, 0.3, 7.4, H - 1.9, "데이터 · 학습 · 평가")

box(16.7, 9.55, 6.8, 3.55, "data", "데이터", [
    "L8S 사실적 시뮬 139,603행 (고리 포함, 서랍 b3d 제외)",
    "공개 점 풀 62,794행: 머리 시점만, 반복 ≤ 2배",
    "   (3인칭·어안 금지, 정확도 위험 데이터 금지)",
    "다음 L9: L8S의 5배(양·과제·다양성), 왼팔 포함,",
    "   환경 8계열 모두 다르게, 사람 같은 동작",
], tsize=14, lsize=11)

box(16.7, 4.65, 6.8, 4.6, "train", "학습", [
    "본 35B: 202,397행, 3 에폭 (0.25 에폭마다 저장)",
    "다음 본 학습: 기본 모델부터 L8S + L9",
    "   + 도착 전 선발행 행 (+ 도착 자기예측 보조)",
    "VLA 4단계: 단독 → 상위 오차 흉내",
    "   → 실제 상위와 → 번갈아",
    "정답 = 시뮬 참값(특권 정보로 계산한 보정·명령)",
], tsize=14, lsize=11)
ax.add_patch(FancyBboxPatch((16.95, 4.8), 6.3, 0.62, boxstyle="round,pad=0.02,rounding_size=0.12",
                            fc="white", ec="#227777", lw=1.6, ls="--"))
ax.text(20.1, 5.11, "(선택) 전체 엔드투엔드 미세 학습, 같은 인터페이스 유지", fontsize=11, color="#227777",
        ha="center", va="center")

box(16.7, 0.55, 6.8, 3.8, "eval", "평가", [
    "오프라인 점: L8-X 7세트 · 새 물체 OOD-O58",
    "   · L8S 보류(최적 에폭) · G (Franka는 보고만)",
    "폐루프 E-M35CL (보고만): 조명·머리 각 교란, 영상",
    "결합 2×2: {상위, 참값 명령} × {VLA, 참값 실행기}",
    "   연결 손실 ≤ 5 %p, 연결 탓 실패 ≤ 10 %",
    "H-J: 같은 VLA 단독 대 상위 아래 조이스틱",
], tsize=14, lsize=11)

arrow(20.1, 9.55, 20.1, 9.25, "", color="#6b3fa0")
arrow(20.1, 4.65, 20.1, 4.35, "", color="#227777")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_2026-09-30.png")
fig.savefig(out, bbox_inches="tight")
print(out)
