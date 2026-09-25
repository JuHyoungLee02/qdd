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
| E-Astra-motion G1 v2 (정지 영상 40장 × 4조건, low) | 160 | **2,682원** | 호출당 **16.8원**, 입력 약 588/738/892(영상 1/2/3장) [→ 정정 2026-09-25 20:37 UTC, R7 27회차 E-D1/N70: 507/657/811은 옛 설계 G1 값], 출력 약 75(추론 약 22), 지연 p50 **3.5 s** | [R/astra_motion](../stage3/results/astra_motion.md) 2절 |
| E-Astra-motion S2 직렬 흐름 (F0·F1 각 3편, low) | 72(끝난 뒤 도착 6 포함) [→ 정정 2026-09-25 20:37 UTC, R7 27회차 E-D1/N70] | **3,824원** | 호출당 **49.7원(F0)·58.0원(F1)**, 입력 2,207/2,486, 출력 244/302, 지연 p50 **9.3 s(F0)·10.3 s(F1)**, 첫 토큰 약 6 s, 로봇 1분당 350–500원, 캐시 적중 0 | 같은 문서 5절 |
| E-Astra-motion G2 표적 (8장, high) | 8 | **224원** | 호출당 **27.9원**, 추론 64–289토큰, 지연 p50 5.7 s | 같은 문서 4절 |
| E-Astra-motion API 설정 시험 | 3 (HTTP 400) | 0원 | temperature·top_p·seed 모두 거부 | 사전 등록 수정 1 |
| **누적(확정분)** | | **6,933.4원**(E-Astra-motion 전체, 장부 `H/logs/astra_motion/cost.jsonl` 256행 합; 상한 15,000원) + 이전 `[금액 미기록]` 분 | | |

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
| E-MA1b 2판 + 기준 재예측·보기 확인 | 2 | ≈ 1.9 GPU-h(17:54–19:46; 학습 41.0·37.1분, 예측·확인 약 0.6 h) | [R/ma1b](../stage3/results/ma1b.md) 5절 |
| E-CAM3 2판 + 기준 재예측·지연 | 2 | ≈ 1.7 GPU-h(사전 실행 20:22–20:25 + 20:34–22:15; 학습 41.0·40.6분) | [R/cam3](../stage3/results/cam3.md) 5절 |
| E-MA3 2판 + 기준 청크 평가·지연 | 3 | ≈ 1.7 GPU-h(사전 실행 20:22–20:25 + 20:34–22:13; 학습 37.9·38.2분) | [R/ma3](../stage3/results/ma3.md) 5절 |
| R2_TRAIN 생성 | 0·1(렌더) + 2(로더 확인) | ≈ 21.3 GPU-h(21.34; GPU 0·1 각 11:16–21:56 ≈ 10.7 h 점유, 동시 Isaac 최대 5 = 누적 52.8 프로세스-시간, 사용률 20–50 % `[미검증]` — 저장된 로그에 없음) [→ 정정 2026-09-25 23:58 UTC, R7 35회차 N178·N179] + GPU 2 약 0.2 h(로더 확인 2회); 첫 파일럿(6b013ac, 폐기) GPU 1 약 0.7 h 별도 | [R/r2_train_gen](../stage3/results/r2_train_gen.md) 8절 |
| R7 순회 | 1(Isaac 한 프로세스) | 회차당 폐루프 한 판 | `R/r7_cycle*.md` |
