# 05. 비용 장부 — 유료 API·GPU 시간

- 한도: 유료 API **약 10만 원**(user-log 76, 정본 §82 보충). 실행 판단은 Claude 자체 검사(user-log 87, 정본 §85): 단계마다 결정·표본 충분성·무료 사전 실행, 실험별 상한, **80 %에서 멈추고 보고**, 공유 장부 파일 합산(P23).
- 가격(탐침 등록 시점, developers.openai.com): gpt-6-astra 입력 $10 / 캐시 $1 / 출력 $50 per 1M 토큰, 환율 가정 1,450원/USD.

## 유료 API (Astra 등)
| 실험 | 호출 | 비용 | 측정 | 출처 |
|---|---|---|---|---|
| Astra 모델 ID 스모크 | 1 (low) | 무시할 수준 `[금액 미기록]` | 첫 토큰 2.975 s, 완료 3.288 s | [R/astra_model_id](../stage3/results/astra_model_id.md) |
| Sol·Luna 사전 시험 | 10 | `[금액 미기록]` | Luna 중앙 1.17 s | [R/sol_luna_probe](../stage3/results/sol_luna_probe.md) |
| pre-R7 K 모드 실 API | 1 (low) | `[금액 미기록]` | 첫 토큰 1.88 s | [R/pre_r7_fixes](../stage3/results/pre_r7_fixes.md) |
| R5 폐루프 Astra | 9(SFT 판 2 + 영점 판 7) | `[금액 미기록]` | — | [R/r5_closed_loop](../stage3/results/r5_closed_loop.md) |
| E-Astra-motion 옛 설계 G1(분석 제외) | 13 (low) | **204원** | 호출당 **15.7원**, 입력 507/657/811 토큰(이미지 1/2/3장), 출력 73(추론 약 19), 지연 p50 **4.2 s** | user-log 87, `P/prereg_astra_motion.md` 수정 2 |
| E-Astra-motion 본 단계(G1 v2 160 · S2 F0·F1 각 3편 · 표적 G2 8) | — | 합계 약 7천 원 `[미검증 — 결과 문서 커밋 뒤 확정]` | 결과 문서 작성 중 | 상한 15,000원(수정 2) |
| **누적(확정분)** | | **204원 + 미확정 약 7천 원** | | |

### 예정 예산 (계획 [Task 14–16](../superpowers/plans/2026-09-26-astra-vla-coupling.md))
| 실험 | 상한 | 비고 |
|---|---|---|
| E-Couple | 25,000원 | 직렬 1개 흐름 + 두 층 M4 대 VLA 단독; 실측 단가로 판 수 다시 계산 |
| E-Astra-necessity(흐름 자리) | 20,000원 | 로컬 소형 VLM 대조, low·high 병기 |
| 합계(탐침 15,000 포함) | 60,000원 ≤ 100,000원 | |

## GPU 시간 (H200, 시각 차로 계산한 추정 ≈)
| 실험 | GPU | 추정 | 출처 |
|---|---|---|---|
| S-E2E 본 학습 2판 | 2·3 | ≈ 3.8 GPU-h(09:40–11:34 × 2) | [R/se2e_train](../stage3/results/se2e_train.md) |
| S-E2E 진단·규모 곡선 | 2·3 | `[미기록]` | [R/se2e_diag](../stage3/results/se2e_diag.md) |
| E-TC 4칸 | 2·3 | ≈ 2.5 GPU-h(칸당 2,119–2,450 s) | [R/se2e_temporal](../stage3/results/se2e_temporal.md) 5절 |
| 움직임 줄 확인 4판 | 2·3 | ≈ 2.9 GPU-h(15:53–17:21 × 2) | [R/se2e_motion_confirm](../stage3/results/se2e_motion_confirm.md) |
| E-MA1 G0 | 2 | 약 1.5분 | [R/ma1](../stage3/results/ma1.md) |
| E-MA1b 2판 | 2 | ≈ 1.3 GPU-h 계획 `[진행 중]` | [P/prereg_ma1b](../stage3/prereg_ma1b.md) |
| R2_TRAIN 생성 | 0·1(렌더) | `[진행 중]` | — |
| R7 순회 | 1(Isaac 한 프로세스) | 회차당 폐루프 한 판 | `R/r7_cycle*.md` |
