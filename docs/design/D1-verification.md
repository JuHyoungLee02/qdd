# D1. 독립 검증: M3·M4·M5·M7·M8·M9 설계 문서

- 작성: 2026-09-24 UTC, 독립 검증 에이전트. 대상: `docs/design/M3-action-representation.md`, `M4-overlap-commit.md`, `M5-smoothing.md`, `M7-progress.md`, `M8-astra-invocation.md`, `M9-recovery.md`. 기준: `docs/design/README.md`, `docs/plan.md` v4.3 §1.
- 방법: arXiv abs·HTML 본문(요청 간격 2초 이상), CVF Open Access 목록(CVPR 2026), OpenAI 개발자 문서 원문. arXiv 검색 API, Semantic Scholar API, GitHub API는 쓰지 않았다. 인용 수와 스타는 재지 않았다.
- 표기: **맞음** / **정정 필요** / **조건 보완**(수치는 맞지만 조건을 빠뜨렸거나 조건이 다름) / **학회 미확인**. 위치는 원문의 표 번호와 절 번호로 적는다.

---

## Part A. 원문 대조 (plan v4.3에 없던 새 출처)

### A.1 우선 항목

| # | 출처(문서) | 제목 / 첫 공개 / 학회 | 문서 주장 | 원문 | 판정 |
|---|---|---|---|---|---|
| 1 | **T2SGrid** 2603.06973 (M8) | "T2SGrid: Temporal-to-Spatial Gridification for Video Temporal Grounding" / v1 2026-03-07 / arXiv Comments 없음, **CVF Open Access CVPR 2026 목록에 논문·보충자료 PDF 있음** | 표 6: 1×1 53.5/32.9 → 3×3 63.7/41.1 → 4×3 64.5/41.2(최고), 4×4 mIoU 35.9, 토큰 약 5,790 | **Table 6 (Stage 1)**. 표기 `g{col}{row}_s{stride}`이므로 **g43 = 4열 × 3행(12프레임)**. 행 대응: g11_s1 = 53.5 / 32.9 (mToken 5,791) · g22_s4 = 56.5 / 34.2 · g23_s6 = 61.6 / 38.8 · g32_s6 = 61.8 / 39.0 · **g33_s9 = 63.7 / 41.1** · g34_s12 = 64.1 / 41.1 · **g43_s12 = 64.5 / 41.2** · **g44_s16 = 61.6 / 35.9** (R1@0.3 / mIoU). Stage 1 mToken 5,780~5,791. Stage 2 겹침: **g43_s7 = 70.2 / 44.3, mToken 7,910(+37%)**가 전체 최고 | **맞음 + 조건 보완 3개.** (1) 64.5/41.2는 **Stage 1(겹침 없음)의 최고**다. 전체 최고는 겹침 창 g43_s7(토큰 약 37% 더 씀). (2) "1×1 = 프레임 순차"의 행에는 **칸별 텍스트 타임스탬프(ComTextNum)가 이미 붙어 있다**. 타임스탬프가 없는 Qwen2-VL-7B는 R1@0.3 8.7 / mIoU 7.9(Table 1)이고, Table 4는 ComTextNum만으로 mIoU 7.9 → 32.9를 보고한다. 격자 효과(32.9 → 41.2)와 타임스탬프 효과(7.9 → 32.9)를 나눠 적어야 한다. (3) §4.1 "Training Detail"에 Qwen2-VL-7B **LoRA 3 에폭 학습**이 적혀 있고, Charades는 g43_s7로 "trained and evaluated"라고 쓰여 있다. **Table 6 절제가 학습 없는 설정인지는 원문에 명시가 없다**(학습 설정일 가능성이 높음). "학습 없는 모드 있음"은 그림 3 캡션 문장("can operate in a training-free manner")이 근거이고, 이 수치의 근거는 아니다. 추가 정정: "순차 입력은 무엇이 있는지에 주의가 간다"는 주의 지도 분석은 **§3.1 Attention Analysis**(그림 4)에 있다. §4가 아니다. **5×2(10칸)는 원문에서 시험하지 않았다**(가장 가까운 것은 6칸 g32/g23 61.8/61.6, 9칸 g33 63.7). 한 격자의 칸은 **연속 프레임(슬라이딩 창)**이다. 키프레임 선택(M8 §4.3)과는 다른 입력이다 |
| 2 | **BAGEN** 2606.00198 (M8) | "BAGEN: Are LLM Agents Budget-Aware?" / v1 2026-05-29 / Comments 없음(심사 전) | 5개 모델, 20쌍 모두 낙관 편향. 실패 궤적에서 예산 60% 소비 뒤에도 70% 이상 가능 예측, 경보는 마지막 20%. r=0.35. SFT+RL 뒤 포함률 47% | §1 요약 목록, §5.2(가설 2), **§5.4 + 그림 7**: "above 70% even after 60% of the budget… drops sharply only in the final 20%". r≈0.35 = 과제 성공 대 **구간 적중률**(§1 bullet). 47% = **Qwen2.5-7B** SFT+RL 뒤 구간 포함률(§5.1). 소속: Northwestern, All Hands AI, Stanford, UT Austin 등 | **맞음 + 조건 보완.** 예산은 **토큰·비용·시간·창고 점유**이고, 측정은 "남은 예산 구간 + 불가능 선언" 질의다. 47%는 **프런티어 모델 값이 아니라 학습한 7B 추정기** 값이다. 가설 3 결과("추정은 턴마다 갱신된다. 다만 방향은 모델마다 다르다")도 함께 적는 것이 공정하다 |
| 3 | **BATS** 2511.17006 (M8) | "Budget-Aware Tool Use Enables Effective Agent Scaling" / v1 2025-11-21 / **Accepted to COLM 2026** | Budget Tracker 플러그인으로 스케일링 개선, COLM 2026 | 초록 그대로 | **맞음.** 조건: 대상은 **웹 검색 에이전트의 도구 호출 예산**이다 |
| 4 | **Web-Shepherd** 2505.15277 (M7) | "Web-Shepherd: Advancing PRMs for Reinforcing Web Agents" / v1 2025-05-21 / **NeurIPS 2025 Spotlight** | §5 체크리스트 + Yes/In Progress/No. §6.1.2 "기준·우리 모델 모두 체크리스트로 크게 좋아짐"(Table 1). GPT-4o 대비 약 30점 | §5.1·§5.2, §6.1.2 원문 "both baseline and our models benefit significantly from the checklist"(Table 1), 초록 "about 30 points better accuracy compared to using GPT-4o on WebRewardBench" | **맞음.** 조건: 3라벨은 **라벨 토큰 확률(logit, verbalizer)**로 점수를 매긴다. "In Progress" 채택 근거는 부록 Table 7(MLLM 판정기)이다. Jev에 옮기면 확률 보정 전 규칙(plan §1)을 따라야 한다 |
| 5 | **FIPER** 2510.09459 (M4, M7) | "Failure Prediction at Runtime for Generative Robot Policies" / v1 2025-10-10 / Comments "**Accepted to NeurIPS 2025**" | 두 점수를 conformal 보정하고 창으로 모아 AND. M7: 부록 C.4 "CP 상수 = TNR↑ TPR↓, 시간 변동 = TPR↑ 오경보↑". M4: "한계 절: CP 임계는 예측보다 탐지 쪽" | 초록·A.4(AND, Proposition 4) 맞음. C.4.1 문장 일치. "CP-based thresholds detect rather than predict failures"는 **부록 C.4.2**에 있다. 한계 절(D)에는 "Time-varying thresholds can be restrictive"만 있다 | NeurIPS 2025 **맞음**. M4의 위치 표기는 **정정 필요**("한계 절" → C.4.2). **조건 보완**: FIPER의 최고 TWA는 **CP 보장이 없는 "time-varying threshold"**(시점별 경험 분위수)로 나왔다(C.4.2 "FIPER achieves the highest TWA values overall with our time-varying threshold"). 그러므로 "conformal 보정 = 보장된 임계"로 옮기면 원문의 최고 설정과 다르다. 참고: Rewind-IL Table I에서 RND/FIPER 대리 방법(결정적 ACT용으로 개조)은 균형 정확도 0.59였다 |
| 6 | **SAFE** 2506.09937 (M7) | "SAFE: Multitask Failure Detection for Vision-Language-Action Models" / v1 2025-06-11 / "NeurIPS 2025 camera ready" | §4.3 functional CP 시간 변동 띠, OpenVLA·π0·π0-FAST, 부록 F.2 온라인 CP | §4.3, §1("OpenVLA, π0, π0-FAST"), F.2 "Adaptive Thresholding by Online Conformal Prediction" | **맞음** |
| 7 | **RALCP** 2309.06706 (M4) | "Simultaneous Machine Translation with Large Language Models" / v1 2023-09-13 / Comments "**Accepted to ALTA 2024**" | γ=0.6 균형(§3.3, 부록 C.4 그림 6), Llama2-7b-chat, MuST-C 9쌍, **학회 미확인** | §3.3 투표 규칙, 부록 C.4: "better results tend to cluster around ≈0.6… too large → significant increase in latency", beam이 크면 지연 증가. **C.4 절제는 en-de·en-ro·en-ru 3쌍**, n=6·beam 10 고정 | **정정 필요**(학회 = **ALTA 2024**. 워크숍급이며 기간 밖 기초 문헌 표시는 유지). **조건 보완**: γ 절제는 9쌍이 아니라 **3쌍**이다. "γ 0.1~1.0 탐색"의 범위는 그림 안에 있어 본문 텍스트로는 확인하지 못했다. MLLP-VRAIN 2506.18828(IWSLT 2025 System Description) 표에 RALCP 0.5 있음: **맞음** |
| 8 | **CUNI IWSLT 2025** 2506.17077 (M4) | "Simultaneous Translation with Offline Speech and LLM Models in CUNI Submission to IWSLT 2025" / v1 2025-06-20 / "IWSLT 2025" | §2 원문 "LocalAgreement … best-performing policy that does not require attention weights" | 문장은 원문에 있다: "we can not apply the AlignAtt policy to EuroLLM, so we use it with the LocalAgreement simultaneous policy, which is the best-performing policy that does not require attention weights". 위치는 **§4 "Simultaneous Translation with EuroLLM"**이다. §2(Background)에는 LA 정의만 있다 | **정정 필요(위치 §2 → §4).** 조건: 이 논문 안에 LA 대 다른 정책의 비교표는 없다. 저자 주장이다(M4 §8의 "정성 문장만 근거"와 일치) |
| 9 | **FLy** 2511.22972 (M4) | "Training-Free Loosely Speculative Decoding: Accepting Semantically Correct Drafts Beyond Exact Match" / v1 2025-11-28 / "**Published as a conference paper at ICLR 2026**" | 엔트로피 게이트 + 유예 창, 99% 이상, 2.81×/5.07×, EAGLE-3 대비 1.62× | 초록 수치 일치, 본문 "Entropy-level gate", "Token-level deferred window" 절 일치 | **맞음.** 조건: 원문 유예 창에서 창 안의 두 번째 불일치는 **앞서 가수용한 토큰을 소급 거부**하는 신호다. M4의 "도전 선택이 다시 나오면 교체"는 우리 쪽 재해석이다(M4 표 #3 접목안 칸에 있으므로 문제없음) |
| 10 | **Rewind-IL** 2604.16683 (M4) | "Rewind-IL: Online Failure Detection and State Respawning for Imitation Learning" / v1 2026-04-17 / Comments 학회 없음 | TIDE, split CP α=0.001(§IV-B), 균형 정확도 0.95 대 FAIL-Detect 0.83, RND 0.59(Table I), 18.3→76.7%(Table II, 20회) | §IV-B "α=0.001 in all experiments", Table I 평균 행: FAIL-Detect 0.83, RND/FIPER 0.59, 군집 0.60, Mahalanobis 0.58, **TIDE 0.95**. Table II 섭동 평균 ACT 18.3 → +Rewind-IL 76.7, "20 rollouts each" | **맞음**(학회 미확인, LOW-MED 표기 유지). 조건: Table I·II는 **실물 양팔(AgileX Piper) ACT 6과제**다 |
| 11 | **2607.26627** (M4) | "Revisiting Lossy Verification in Speculative Decoding: Mechanisms, Trade-offs, and Failure Modes" / v1 2026-07-29 / Comments 없음 | 완화 수용이 분포를 바꿔 불안정, 절삭형은 진짜 절삭 샘플링보다 나쁠 수 있음 | 초록 일치 | **맞음**(학회 미확인). 덧붙일 것: 같은 초록에 "협력형 검증은 설계 원칙(overshoot 억제, supervision 품질)이 draft·target 선형 보간보다 중요하다"는 결론도 있다 |
| 12 | **AAC** 2604.04161 (M5) | "Adaptive Action Chunking at Inference-time for Vision-Language-Action Models" / v1 2026-04-05 / "accepted by CVPR 2026" + **CVF 목록 확인** | Table 1: RoboCasa 59.7 → 62.0, h=8 61.2, LIBERO 94.1 → 95.0, h=8 94.7, h=2 RoboCasa 47.0 | Table 1 값 전부 일치 | **맞음** |
| 13 | **UI-Zoomer** 2604.14113 (M3) | "UI-Zoomer: Uncertainty-Driven Adaptive Zoom-In for GUI Grounding" / v1 2026-04-15 / 학회 없음 | 불확실할 때만 줌(공간 합의 + 토큰 확신), 최대 +13.4 / +10.3 / +4.2 | 초록 일치 | **맞음, 학회 미확인.** 조건: 게이트의 "token-level generation confidence"는 생성 확률(logit)을 쓴다. Jev에서는 보기 확률로 바꿔야 한다 |
| 14 | **RIA** 2605.24004 (M3) | "Reason–Imagine–Act: Closed-Loop LLM Decision Making with World Models for Autonomous Driving" / v1 2026-05-19 / "**Accepted by ITSC 2026**" | CARLA 1,000회 80.05 / 51.10 / 0.20%, CARLA TM·MADA 대비 우세 | 초록 일치 | **맞음** |
| 15 | **Massive-option MCQA** 2604.14634 (M3) | "Pushing the Boundaries of Multiple Choice Evaluation to One Hundred Options" / v1 2026-04-16 / 학회 없음 | Full: Gemini-3-Pro 98.8 → 85.7, 2.5-Flash 97.3 → 71.7, EXAONE 81.2 → 14.0 / Easy: 99.98 → 98.98. Table 2, 30목표 × 1,000회. Full slope 약 −0.06~+0.03 | Table 2 Acc4 → Acc100: 0.9881 → 0.8574, 0.9730 → 0.7172, 0.8119 → 0.1401, Easy 0.9998 → 0.9898. K=1,000 시행. Full Slope100: −0.0008, −0.0084, +0.0317, −0.0488, **−0.0675** | 수치 **맞음**. **조건 보완**: "Full = 서로 **비슷한** 방해 보기"는 원문 정의가 아니다. 원문은 **Easy = 난도 1~2단계 문장에서 방해 보기 추출, Full = 1~4단계 전체**다(난도는 형태·통사 표면 특징 휴리스틱). 기울기 범위는 **−0.07~+0.03**으로 고친다(작은 정정) |
| 16 | **Tools shortlist** 2605.24660 (M3) | "How Many Tools Should an LLM Agent See? A Chance-Corrected Answer" / v1 2026-05-23 / "13 pages" | Sonnet 4.6, BFCL 370 도구, **짧은 적응 목록(평균 K≈7)**일 때 93.1% 대 5개 87.1%, 중간 난도 76.8 대 60.9%(Table 1, 120질의 × 3시드) | 초록 수치 일치. 그러나 Table 1 설명에 "RL agents are retrained for this setup… which produces **shorter lists (K̄=2.2) than the main-table agents (K̄=7.4)**". Choice Acc는 **정답 도구가 제시된 질의 안에서의** 선택 정확도다 | **정정 필요**: 93.1%는 평균 **K≈2.2** 목록일 때 값이다. K≈7(7.4)은 커버리지 표의 에이전트 값이다. **조건 보완**: 목록 길이는 **RL로 학습한 정책**이 정한다(M3 표의 "학습 없이 O"는 LLM 쪽만 해당) |
| 17 | **Show-Harness** 2609.10522 (M3, plan 기존 출처, 수치만 새로) | "Show-Harness: Just a VLM Agent Can Play Robots" / v1 2026-09-09 / 학회 없음 | 보폭 2 → 1cm로 ZS 60 → 82%(§5.3.1). 청킹 끔 96%, 항상 켬 74%(§5.4.3). 시행 수 확인 못 함 | §5.3.1 "reduce the interpreter step size from 2 cm to 1 cm… improves ZS from 60% to 82% and FT from 40% to 65%", 과제 = **블록 쌓기·페그 삽입**. §5.4.3은 Gemini-3.1 Pro 제로샷, Plate 5과제 leave-one-out. §5.1 "Unless noted otherwise, we run **10 trials per task**" | **맞음 + 보완**: 시행 수는 §5.1 기본값(과제당 10회)을 따르는 것으로 보인다. 즉 조건당 약 20회(2과제)이며, §5.3.1에 따로 적혀 있지는 않다. FT 40 → 65도 함께 적으면 좋다 |
| 18 | **OpenAI 이미지 토큰**(M8 §4.3) | developers.openai.com `api/docs/guides/images-vision` (2026-09-24 읽음) | 32px 패치 × 1.2, high 2,500패치, low 512×512, original 최대 30,000(초과 시 거부), auto = original. 640×480 격자 original = 개별 10장 high = 3,600 | 문서 원문 일치: gpt-6-astra 행 "low fits within 512×512 / high up to 2,500 patches and 65,535-px max / original preserves dimensions… >30,000 patches rejected / auto = original", 배수 1.2, 축소 공식(shrink_factor + floor 보정) | **맞음(핵심 결론).** 공식으로 다시 계산한 값은 아래 A.2 |

### A.2 M8 이미지 토큰 표 재계산 (공식 원문 공식, 이미지마다 올림)

| 묶음 | 문서 값 | 재계산 | 판정 |
|---|---|---|---|
| 640×480 1장 high | 300패치 → 360 | 20×15 = 300 → 360 | 맞음 |
| 640×480 1장 low | 192 → 230 | 512×384, 16×12 = 192 → ⌈230.4⌉ = **231** | 작은 정정 |
| 640×480 개별 10장 low | 2,304 | **2,310**(장마다 올림) | 작은 정정 |
| 640×480 **개별 10장 high / 격자 5×2 original** | 3,600 / 3,600 | 3,600 / 3,200×960 → 100×30 = 3,000 → 3,600 | **맞음(토큰 같음)** |
| 640×480 격자 5×2 high | 약 2,430 → 약 2,920, 칸 약 572×429 | 2880×864 → 90×27 = 2,430 → **2,916**, 칸 576×432 | 맞음 |
| 640×480 격자 4×3 high | 약 2,930, 칸 약 522×392 | 2104×1184 → 66×37 = 2,442 → **2,931**, 칸 약 526×395 | 맞음 |
| 1280×720 1장 high / low | 1,104 / 173 | 40×23 = 920 → 1,104 / 512×288 → 144 → 173 | 맞음 |
| 1280×720 격자 5×2 original | 10,800 | 6400×1440 → 200×45 = 9,000 → 10,800 | 맞음 |
| 1280×720 격자 5×2 high | 약 2,500 → 약 3,000, 칸 약 661×371 | 3271×736 → 103×23 = **2,369 → 2,843**, 칸 약 654×368 | 작은 정정 |
| 1280×720 격자 4×3 high | 약 2,920 | 2427×1024 → 76×32 = 2,432 → **2,919** | 맞음 |
| 격자 5×2 low | 96 / 77, 칸 102×77 | 512×153 → 80 → 96 / 512×115 → 64 → 77 | 맞음 |

### A.3 그 밖의 새 출처 (초록 확인)

| 출처 | 확인 | 판정 |
|---|---|---|
| ZoomClick 2512.05941 (M3) | 초록 "UI-Venus-72B 73.1% on ScreenSpot-Pro", Comments에 학회 없음 | 맞음, 학회 미확인 |
| Pace-and-Path 2605.11459 (M5) | 초록 "up to 28.8% (dynamic-only) and 25.9% (mixed) absolute" | 맞음. 혼합 환경 25.9%p는 문서에 빠져 있다 |
| 2608.02464 (M7·M9) | 초록: 0.71 @5% 오경보(AUROC 0.872), 결정적 검증 60%(96%) 오탐 0/63 대 감시기 54% / 17%, 0.527 → 0.885, 되돌림 재실행 45% 대 16%(p=0.0005) | 맞음(단독 저자·심사 전은 확인하지 않음, 학회 없음) |
| 2607.25152 (M7) | 초록: 54 사이클, 56% 변화 ≤ 0, 19% 하락, 산출물 안에서 검증 가능한 과제는 착시 0. "사전 등록 파일럿" Comments | 맞음 |
| MLLP-VRAIN 2506.18828 (M4) | "IWSLT 2025 System Description", RALCP 0.5 + wait-k | 맞음 |
| **이번에 원문을 보지 않은 새 출처** | AdaptiveSpec 2609.02897, EFR 2608.24015, ProTracer 2609.21369, VLA-Corrector 2607.01804, SV-VLA 2604.02965, AOSpec 2608.00881, SMC 2609.03236, Safe to Resume? 2608.29381, VRL-Bench 2609.12404, CorrectVLA 2608.29967, MoMaStage 2603.08383, FluxVLA 2609.17210, REAL-I 2609.13679, Robo-Dopamine 2.0 2608.15680, 2609.02057, ActProbe 2606.08508, AutoVLA, ZoomClick 본문, LiPo | **미검증**(시간 한도). 이 중 설계 기본값을 떠받치는 것은 FluxVLA(Ruckig 1.17ms, M5 L3 근거)뿐이다. 다음 검증 1순위 |

### A.4 이 밖에 원문과 다른 서술

- **M7 §2 표 FIPER 행** "학습 없이? 점수 학습은 필요": 맞다(RND-OE는 학습형). M4 표 "보정은 예(RND-OE는 학습)"도 같은 뜻이다.
- **M8 §8** "T2SGrid 표 3의 GPT-4o 행": 원문 **Table 1**에 "GPT-4o → +T2SGrid" 행이 있다. 본문 §4.2.1에 "GPT-4o… achieves further gains with T2SGrid"라고 적혀 있다. 즉 **독점 모델에도 적용한 결과가 있다**(수치는 HTML 표에서 추출하지 못함). M8 §6-4의 "격자 근거는 오픈 7B 모델" 위험 서술은 조금 약하게 고쳐야 한다.

---

## Part B. 모듈 사이 모순

| # | 모순 | 위치 | 심각도 |
|---|---|---|---|
| B1 | **호출 단위.** M3는 "한 요청 = 한 결정 스텝"이고, M4는 "한 호출 = H(=3)개 미래 스텝"이다. M4가 [결정 필요 ①]로 올렸지만 M3에는 반영이 없다. 또 M3 D-줌 (a)안("직전 스텝의 거친 구간으로 세밀 질문을 미리 만든다")은 H≥2일 때 두 번째 이후 스텝에서 성립하지 않는다 | M3 §4.1·§4.2 / M4 §4.1·§7-1 | 높음 |
| B2 | **예상 상태의 출처가 셋이다.** M3 `expected_after`(결정 전에 코드가 만든 술어), M4(b) "코드 전진 모델" 연속 잔차(+ M6에 `predict_after` 요구), M5 §6 "Ruckig 계획 궤적으로 계산해야 함". Ruckig는 기준을 늦게 따라가므로 M4 방식이면 스텝 끝마다 LAG가 나고 CUSUM이 DEVIATE로 올린다(가짜 epoch 교체) | M3 §4.5 / M4 §4.2 `on_step_executed` / M5 §6 | 높음 |
| B3 | **실패 판정자가 둘이다.** M7·M8·M9는 "실패 판정은 M7 한 곳, M9는 M7 FAIL로만 시작"이다. 그런데 M4 CONTRADICT는 직접 `flush queue; hold; request repair (M9) + M7`을 한다. M4 출력 3도 "repair 요청(M9로)"다 | M4 §1·§4.2 / M7 §1 / M9 §1 | 높음 |
| B4 | **M4 범주와 M7 채널이 이어지지 않는다.** M7 C_m4는 "'큼' 범주로 확정 3번 연속"인데 M4에는 "큼"이 없다(OK/LAG/DEVIATE/CONTRADICT). M4 TIDE `flip_score`(M4가 "(b)보다 먼저 오는 조기 경고"로 둔 신호)는 M7 입력 S4에 (a)로 적혀 있지만 채널이 없다. 결합 규칙도 둘이다: M4 "repair는 (b)+TIDE 둘 다 나쁠 때", M7 "소프트 채널 2개 AND" | M4 §3 #7·#8 / M7 §1 S4·§4.2 | 중간 |
| B5 | **고정·확정 구간 정의가 셋이다.** M4 FROZEN = `now + d̂_p95`, M5 L1 commit window = p_top ≥ 0.8이고 합의가 연속이면 3스텝(1초), 아니면 1스텝, M3 `DecisionStep.commit_window` 필드(누가 채우는지 없음) | M3 §4.5 / M4 §4.2 / M5 §4 L1 | 중간 |
| B6 | **교체(히스테리시스) 규칙이 둘이다.** M5 L1 "겹친 호출 2개가 연속으로 같은 새 보기(= W=2) 또는 (b) 실패" 대 M4 "W=1 기본(경계 직후 2), gate_hard, LA2/γ". 같은 규칙을 두 모듈이 다르게 정한다 | M4 §4.2·§4.4 / M5 §4 L1 | 중간 |
| B7 | **보정 전(E1 전) 확률 게이트 방침이 다르다.** M4는 θ를 "끔(E1 전)"으로 두는데, M5 τ_hi 0.8, M7 C_jev 0.8, M8 T3b 0.7, M9 L2 0.6(미달이면 안전 대기)은 E1 전부터 켠다. plan §1은 게이트 사용 자체를 허용하지만, 모듈마다 임계가 다르고 근거가 없다 | 각 문서 | 중간 |
| B8 | **Jev 요청 내용이 한 곳에 모여 있지 않다.** M4 호출 하나에 M3 결정 질문 × H, M7 S5 진행 범주, M7 이정표 체크리스트(Web-Shepherd), M8 T3b Noul이 함께 실린다. 입력이 길어지면 정확도가 떨어진다(plan §1). E0 지연 측정도 어떤 크기의 요청으로 잴지 정해지지 않았다 | M3 §4.1 / M7 §3 / M8 §4.1 / M4 §5 E0 | 중간 |
| B9 | **시간 파라미터가 서로 다르다.** 잡기·놓기 전환 보류 최대 **1.0초**(M7 허용 게이트) 대 **0.5초**(M9 t0). (b) 집계 창 w = 5 제어 주기(100Hz 기준 0.05초, M4) 대 critic 10Hz 틱(M7 H1 2틱 = 0.2초). `near/contact` 경계 5cm/1cm는 M3가 "M7 critic 정의와 공유"라고 했지만 M7에 dist_cat 정의가 없다. M5 L1 "3스텝 = 1초"는 D안(스텝 = T_c)에서만 맞는다. G/H안의 스텝은 시간 단위가 아니다 | M3 §7-3 / M4 §4.4 / M5 L1 / M7 §4.2 / M9 §4.1 | 낮음~중간 |
| B10 | **정지 경로가 여럿이다.** M4 CONTRADICT `hold`, M5 `NONE_ESCALATE` → 감속 정지 궤적, M9 L3 안전 대기, M8 T0. 사용자 원칙은 "초기 계획과 실패만 정지"다. M4·M5의 정지는 M7 FAIL을 거치지 않는다 | M4 §4.2 / M5 L2-4 / M9 §4.1 | 중간(Part C와 연결) |
| B11 | **실험이 서로를 고정값으로 삼는다.** E-M3-2는 M4 = C5로 고정하고, M4 실험은 "E2와 같은 과제", M3 안은 미정이다. E-M5-1은 M3(E-M3-2 결과)와 M4 C5로 고정한다. 순서가 정해지지 않았다 | M3 §5 / M4 §5 / M5 §5 | 낮음 |
| B12 | M3는 "코드 critic(M7)이 M3의 예상 결과 술어를 M4(b)에 재사용"이라고 쓰지만 M7 입력(S1~S6)에는 `expected_after`가 없다 | M3 §1 / M7 §1 | 낮음 |

### 제안: 하나로 맞춘 인터페이스 (짧게)

1. **호출 단위(B1, B8)**: `JevCall{call_id, t_state, epoch, decision_qs[ds_k … ds_k+H−1], monitor_qs[S5 진행, T3b]}`. H는 M4 변수로 두고 **H=1(M3 원안 + 호출 시각 앞당기기)**과 H=3을 E0 뒤에 비교한다. monitor_qs는 호출 N번에 한 번(예: 1초에 한 번)만 싣는다. E0은 이 전체 크기로 잰다. D-줌 세밀 질문은 첫 스텝(ds_k)에만 둔다.
2. **예상 상태 한 곳(B2, B12)**: M5가 `ref(t)`(Ruckig 계획 궤적, 코드)를 공개한다. M4(b)는 **연속 잔차 = 측정 − ref(t)**와 **범주 = `expected_after` 술어의 스텝 끝 성립 여부**를 따로 계산한다. LAG는 ref(t) 기준으로만 판정한다. M6 `predict_after`는 `expected_after`를 만드는 함수 하나로 합친다.
3. **신호와 판정의 분리(B3, B4, B10)**: M4는 **신호만 낸다**(`outcome ∈ {OK, LAG, DEVIATE, CONTRADICT}`, `flip_score`). 스스로 멈추거나 M9를 부르지 않는다. M4 안의 epoch 교체와 조기 Jev 호출은 유지한다. M7 매핑: CONTRADICT → 하드 채널 H4(즉시 FAIL), DEVIATE 3연속 → C_m4, `flip_score > FLIP_TH` → 새 소프트 채널 C_flip. FAIL만 M8 T_fail과 M9를 시작한다. 정지는 T0과 M9 L3에서만 한다.
4. **확정 규칙 한 곳(B5, B6)**: FROZEN 길이 = `max(d̂_p95, Ruckig 추종 지연)`. 교체 규칙은 M4 §4.2 하나만 두고, M5 L1은 "M4를 따름"으로 줄인다. AAC 확정 길이 게이트는 M4 변수(선택)로 옮긴다. `DecisionStep.commit_window`는 M4가 채운다.
5. **게이트 표 하나(B7, B9)**: 질문 유형별 확률 게이트(M5 0.8, M7 0.8, M8 0.7, M9 0.6)와 시간 값(보류 최대, 쿨다운 2초, STALE 1.5초, near/contact 5cm/1cm, critic 10Hz)을 공통 설정 한 파일로 모은다. E1 전에는 이 표의 값만 쓰고, E1 뒤에 질문 유형별로 보정한다.
6. **실험 순서(B11)**: E0 → E1 → E2(마차) → E-M4(M3 = D-줌과 G, 두 안) → E-M3-2(M4 = E-M4 승자) → E-M5-1. E-M7·E-M8b는 기록된 궤적으로 오프라인 병행한다.

---

## Part C. 사용자 의도 점검

| # | 위치 | 문제 | 판정 |
|---|---|---|---|
| C1 | M4 §5 E0 판정, 판정 기준 4 | "p95 < T_c/2이면 지연 흡수용 겹침은 불필요", "C6≈C5면 겹침은 불필요로 보고". [사용자] "1초에 여러 번 계단식으로 겹쳐 호출한다"는 설계 요구다. 결과가 나쁘면 기본안에서 빼는 쪽으로 읽힌다. **[결정 필요] 표시가 없다** | 보고만 한다면 괜찮다. 기본안 변경으로 이어질 경우 [결정 필요]를 붙여야 한다 |
| C2 | M4 §4.2 CONTRADICT `hold`, M5 L2 규칙 4 `NONE_ESCALATE` → 감속 정지 | M7 FAIL을 거치지 않는 정지다. [사용자] "그 이후는 웬만하면 멈추지 않는다. 실패로 생각해야 하는 경우만"과 부딪힌다. **[결정 필요] 없음** | 수정 필요(Part B 제안 3처럼 M7 경유로) |
| C3 | M5 대안(2순위) "L1+L3만" + 판정 4 "S3≈S4면 L2 없음을 기본으로(단순함 우선)" | [사용자] "아주 작은 움직임은 액션 스무딩 등 **VLA 방법**으로". L2(RTC식 블렌딩)가 빠지면 남는 L3 Ruckig은 고전 궤적 생성이다(FluxVLA가 VLA 배치에 썼다는 연결만 남음). 사용자 방향에서 멀어지는 기본값 변경인데 **[결정 필요]가 없다** | [결정 필요] 추가 권고 |
| C4 | M9 §1 [사용자] "논문은 무조건 1년 반 이내" | M9 설계의 재개 규칙 모양이 **기간 밖 행동 트리(PA-BT)**에 기대고, FLARE·REACH의 첫 공개일이 "2025~26", "—"로 비어 있다. README는 "아주 큰 주제의 기초 문헌"만 예외로 둔다. 사용자의 "무조건"과 충돌할 수 있다 | 기간 확인 + 기초 문헌 사용을 [결정 필요]로 |
| C5 | M8 E-M8a effort 축 {medium, high} | plan §1: "effort는 실험 축", low 기본안 금지. xhigh·max를 이유 없이 뺐다(지연 때문일 수 있다). 사용자 원칙("옳은 추론이면 더 빨리 성공")을 생각하면 높은 쪽을 빼는 것도 의도와 어긋날 수 있다 | 빼는 이유를 적거나 [결정 필요] |
| C6 | M3 §0 결론 "촘촘함을 크기 해상도가 아니라 결정 빈도·목표 해상도로" | [사용자] "촘촘하게 가도 된다"의 재해석이다. [제안] + [결정 필요](기본안, D255 강등)로 올렸고 D-줌도 함께 구현한다고 적었다 | **문제없음** |
| C7 | M8 T3a 대 T3b, 격자 기본값 / M9 L3 정지 / M5 micro-dwell / M7 AND 기본 | 모두 [결정 필요]로 올라가 있다 | **문제없음** |
| C8 | 과정 규칙(의도 아님) | README "arXiv 검색 API는 프롬프트에 명시된 에이전트 하나뿐". M4 §8은 검색 API를 12회 썼다. M4 에이전트가 그 지정 에이전트였는지 이 문서들로는 확인할 수 없다 | 메인 세션이 확인 |

---

## 확인 못 한 것

- A.3 "미검증" 목록의 원문(FluxVLA Table 11 1.17ms 우선).
- T2SGrid Table 6이 LoRA 학습 설정인지 학습 없는 설정인지(원문 명시 없음. 부록 PDF 미확인), Table 1의 GPT-4o + T2SGrid 수치(HTML 표 추출 실패).
- RALCP γ 탐색 범위(그림 6 안의 값), BAGEN·Show-Harness 소속(Show-Harness는 확인하지 않음).
- 모든 출처의 인용 수·스타(API 금지).
