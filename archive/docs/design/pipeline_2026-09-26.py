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
    "astra": ("#fde7d9", "#d9622b"),
    "recon": ("#fff4c9", "#b58a00"),
    "vla": ("#dcebfb", "#2266b8"),
    "expert": ("#d9f2e4", "#1e8a4c"),
    "gate": ("#f6dcdc", "#b3261e"),
    "robot": ("#ececec", "#555555"),
    "train": ("#efe4fa", "#6b3fa0"),
    "log": ("#e6f4f4", "#227777"),
}


def box(x, y, w, h, kind, title, lines, tsize=15, lsize=11.5):
    fc, ec = C[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18",
                                fc=fc, ec=ec, lw=2.2))
    ax.text(x + 0.18, y + h - 0.2, title, fontsize=tsize, fontweight="bold", color=ec, va="top", ha="left")
    ax.text(x + 0.18, y + h - 0.75, "\n".join(lines), fontsize=lsize, va="top", ha="left", color="#222222",
            linespacing=1.45)


def arrow(x1, y1, x2, y2, text="", color="#333333", ls="-", tx=0.0, ty=0.0, tsize=11, rad=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0, ls=ls, mutation_scale=18,
                                connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((x1 + x2) / 2 + tx, (y1 + y2) / 2 + ty, text, fontsize=tsize, color=color, ha="center",
                va="center", bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))


ax.text(0.3, H - 0.35, "Harvest 파이프라인 (확정안, 2026-09-26)", fontsize=24, fontweight="bold", va="top")
ax.text(0.3, H - 1.05, "Astra = 느린 큰 조종·구간 계획 · VLA = 세부 조종 스틱(실시간) · 행동 전문가 = 실행 · 관문 = 안전 · 기록 = 추가 학습",
        fontsize=13.5, va="top", color="#444444")

# runtime frame
ax.add_patch(FancyBboxPatch((0.2, 0.3), 15.9, H - 1.9, boxstyle="round,pad=0.02,rounding_size=0.2",
                            fc="none", ec="#999999", lw=1.4, ls="--"))
ax.text(0.45, H - 1.85, "실행(런타임)", fontsize=15, color="#777777", va="top", fontweight="bold")
ax.add_patch(FancyBboxPatch((16.4, 0.3), 7.4, H - 1.9, boxstyle="round,pad=0.02,rounding_size=0.2",
                            fc="none", ec="#999999", lw=1.4, ls="--"))
ax.text(16.65, H - 1.85, "학습(오프라인)", fontsize=15, color="#777777", va="top", fontweight="bold")

# Astra
box(0.6, 9.3, 7.2, 3.95, "astra", "① Astra (low) — 직렬 흐름, 한 번에 하나",
    ["입력: 카메라 3대(머리·양 손목) + 손끝 덧그림",
     "       + 로봇 상태 + 직전 답·그 뒤 VLA 실행 요약(§91)",
     "출력: 평가(진행·실행·의도·확신)",
     "       + 명령: 계속 / 수정(≤5 cm) / 정지",
     "       + 구간 계획: 지금 구간·할 일·다음 구간(§90)",
     "답 간격 약 9–10 s · 호출당 약 50원 · 로봇은 안 기다림",
     "시작 J1 과제 컴파일 · 실패 J2 진단(falsify 먼저)"])

# Reconciliation
box(8.3, 9.3, 7.4, 3.95, "recon", "② 도착 시 대조 + 합의 + 권한 a",
    ["도착한 답(9–10 s 전 판단) vs 그사이 VLA 실제 움직임",
     "  → 이미 됨 / 아직 유효 / 상황 바뀜 / 충돌 (§91)",
     "두 답 합의: 1답 50 % → 2답 100 %, 구간 계획 변경도 합의",
     "권한 a(물체 거리): 먼 구간 a=1 → 조종 반영",
     "                    접촉 근처 a=0 → 외부 명령 차단",
     "부드러운 반영: 선형 증가·감쇠·속도 상한(§11)",
     "15 s 넘은 답의 수정은 버림 · 판단만 참고"])

# VLA
box(0.6, 4.55, 7.2, 4.15, "vla", "③ VLA 결정 = 세부 조종 스틱 (0.33 s마다)",
    ["Qwen3-VL-4B (영상 탑 SigLIP2-L 고정, LoRA)",
     "입력: 머리 + 활성 손목 영상, 상태 글,",
     "       움직임 줄(§83), 구간 의도 줄(§90, Astra에서)",
     "출력(typed 선택): 방향 xy·z · 크기 · 대상 · 단계",
     "                  · 그리퍼 쥐기/놓기/유지(§87)",
     "→ 구간 안에서 '언제 잡을지'를 상황 보고 스스로 결정",
     "먼 구간: 조이스틱 편향 반영(준수 0.991, E-SR1c)"])

# Expert
box(8.3, 4.55, 7.4, 4.15, "expert", "④ 행동 전문가 — 흐름 정합 청크",
    ["결정 토큰 + 백본 문맥 → 0.5 s 관절 청크",
     "먼 구간 분기 데이터 50 %로 결정을 따르게 학습",
     "  (먼 구간 준수 0.344 → 0.991, 근접 능력 유지)",
     "Astra 수정은 청크·손끝 좌표에 편향으로 (× a)",
     "청크 이어 붙이기: 앞부분 고정·뒷부분 교체(RTC식)",
     "결정 지연 p95 약 85–96 ms · 청크 p95 약 33 ms"])

# Gates
box(0.6, 0.6, 7.2, 3.35, "gate", "⑤ 안전 관문 (되돌릴 수 없는 동작)",
    ["쥐기 · 들기 · 놓기 = VLA 의도 + 허가 필요",
     "허가: T1 고유감각 전제(그리퍼 폭·접촉 근처)",
     "       + V1h 확인 헤드(세계 쪽)",
     "Astra의 '잡았다' 영상 판단은 참고만(§86)",
     "신선한 Astra 답이 반대하면 보류"])

# Robot
box(8.3, 0.6, 3.6, 3.35, "robot", "⑥ 로봇 실행",
    ["AI Worker 양팔", "청크 실행(30 Hz)", "상태·영상 기록"])

# Log
box(12.1, 0.6, 3.6, 3.35, "log", "⑦ 기록",
    ["호출·답·대조 판정", "편향·관문·결과", "비용 장부(상한 80 % 정지)"])

# Training side
box(16.7, 9.0, 6.8, 4.25, "train", "본 학습 — 가정한 정답",
    ["실데이터 S-E2E(ROBOTIS) + 시뮬 R2(연구·검증)",
     "라벨: 규칙 라벨·단계 전이·그리퍼 사건",
     "레시피: 움직임 줄 + 먼 구간 분기 50 %",
     "        + 그리퍼 선택지 + 구간 의도 줄",
     "        (직렬화기 판 올림 한 번에)",
     "기각: 3D 궤적 보조·카메라 3대·층별 KV",
     "      ·드롭아웃+CFG·SigLIP 별도 추가"])

box(16.7, 4.0, 6.8, 4.5, "train", "추가 학습 — 실데이터만(§89)",
    ["Astra 교사(§88): 실물 기록에 Astra 판단·수정",
     "   → 대조·결과로 거른 라벨로 DAgger식 학습",
     "MolmoAct 이식: 실영상 포인팅(Molmo2-ER) 궤적 라벨",
     "   → 궤적 보조·이력 덧그림 (E-MAR-real)",
     "선행: Astra 명령 정확도(E-ACC)·라벨 품질 관문",
     "목표: Astra 없이도(덜 불러도) 맞게 움직이기"])

box(16.7, 0.6, 6.8, 2.9, "train", "검증 순서",
    ["E-SR1d(실데이터 분기) → 직렬화기 판 올림",
     "→ E-Couple(폐루프: VLA 단독 대 결합)",
     "→ E-Astra-necessity(low·high·로컬 VLM)",
     "→ E-AT(Astra 교사) · E-MAR-real"])

# arrows runtime
arrow(7.8, 11.3, 8.3, 11.3, "답", color=C["astra"][1], ty=0.3)
arrow(11.9, 9.3, 7.0, 8.7, "구간 의도 · 편향(× a)", color=C["recon"][1], tx=0.2, ty=0.25)
arrow(7.8, 6.6, 8.3, 6.6, "결정 토큰", color=C["vla"][1], ty=0.3)
arrow(12.0, 4.55, 10.1, 3.95, "청크", color=C["expert"][1], tx=0.35, ty=0.1)
arrow(4.2, 4.55, 4.2, 3.95, "그리퍼 의도", color=C["gate"][1], tx=1.1)
arrow(7.8, 2.3, 8.3, 2.3, "허가", color=C["gate"][1], ty=0.3)
arrow(11.9, 2.3, 12.1, 2.3, "", color="#555555")
# feedback: robot state -> astra & vla
arrow(8.05, 3.95, 8.05, 9.3, "", color="#777777", ls="--")
ax.text(8.05, 4.25, "영상·상태\n→ ①·③", fontsize=10.5, color="#555555", ha="center", va="bottom",
        bbox=dict(fc="white", ec="none", alpha=0.9, pad=1.0))
arrow(15.7, 3.3, 15.2, 9.3, "대조용: VLA 실제 움직임", color=C["log"][1], ls="--", tx=0.2, ty=0.0)
# logs -> training
arrow(15.7, 1.2, 16.7, 5.0, "추가 학습 데이터", color=C["log"][1], ls="--", tx=0.1, ty=-0.35)
# training -> runtime model
arrow(16.7, 10.5, 15.7, 7.4, "체크포인트", color=C["train"][1], ls="--", tx=-0.2, ty=0.3)

out = "D:/qdd/docs/design/pipeline_2026-09-26.png"
fig.savefig(out, bbox_inches="tight", facecolor="white")
print(out)
