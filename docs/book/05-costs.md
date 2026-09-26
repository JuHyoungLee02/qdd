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
| 프롬프트 검진 Astra 표본(Q1 방향 60 + Q2 잡기 60, low) | 120 | **2,093.9원** | 호출당 16.45원(방향, 영상 2장 JPEG)·18.45원(잡기, 3장 PNG detail high), 무효 0 | [R/prompt_health](../stage3/results/prompt_health.md) 5절, 장부 `H/logs/prompt_health/astra_ledger.jsonl`(상한 3,000원) |
| E-Astra-solo P1 폐루프 low 4편 + P2 medium 짝 재질문 12 | 44 + 12 | **3,080.9원**(P1 2,366.1 + P2 714.8) | low **53.8원/호출**(입력 2,339·출력 274·추론 118), 지연 p50 6.8 s·p95 16.5 s, **원/성공 591.5원**; medium 59.6원/호출(추론 약 200), 지연 p50 10.0 s | [R/astra_solo_pilot](../stage3/results/astra_solo_pilot.md) 8절, 장부 `H/logs/astra_solo/ledger.jsonl` 56행(상한 5,000원) |
| E-ACC P1(on 10장 × v1·v2·v2cp, low; 크레딧 소진으로 중단) | 30(+ 빈 답 37, 진단 1) | **1,352.7원** | 원/호출 v1 35.3·v2 47.8·v2cp 52.2, 지연 p50 4.3·5.6·6.1 s; 빈 답 37은 과금 없음(장부 no_usage 예약액 5,043원은 미과금) | [R/eacc](../stage3/results/eacc.md) 7절, 장부 `H/logs/eacc/astra_ledger.jsonl` charge 30행(상한 8,000원) |
| E-ACC P1 재개(off 20장 × v1·v2·v2_ax, low) | 60 | **2,760.7원** | 원/호출 v1 36.4·v2 49.1·v2_ax 51.3, 지연 p50 4.3·5.4·5.3 s, 무효 0, 캐시 적중 0(`prompt_cache_key` 넣음) | [R/eacc](../stage3/results/eacc.md) 7절, 장부 `H/logs/eacc/astra_ledger_r2.jsonl`(첫 행 = 이월 1,352.7원; E-ACC 합계 4,113.4원, 상한 8,000원) |
| E-ACC 2단계(off_a·off_c 13 × v2_med + 13·on 5 × v2_gc) | 31 | **1,793.7원** | 원/호출 medium 58.4·목표 확인 57.5, 지연 p50 8.0·8.0 s, p95 17.6·11.4 s, 무효 0 | [R/eacc](../stage3/results/eacc.md) 6·7절, 장부 `H/logs/eacc/astra_ledger_r2.jsonl`(E-ACC 합계 5,907.1원, 상한 8,000원) |
| E-ACC B′(off_a·off_c 13 + on 5 × v2_gc2, low) | 18 | **985.1원** | 원/호출 54.7, 지연 p50 6.4 s·p95 11.9 s, 무효 0 | [R/eacc](../stage3/results/eacc.md) 6.3·7절, 장부 `H/logs/eacc/astra_ledger_r2.jsonl`(E-ACC 합계 6,892.2원, 상한 8,000원, B′만 정지 95 %) |
| **누적(확정분)** | | **19,000.4원** = E-Astra-motion 6,933.4원(장부 `H/logs/astra_motion/cost.jsonl` 256행 합; 상한 15,000원) + 프롬프트 검진 2,093.9원(장부 `H/logs/prompt_health/astra_ledger.jsonl` 120행; 상한 3,000원) + E-Astra-solo 3,080.9원(장부 `H/logs/astra_solo/ledger.jsonl` 56행; 상한 5,000원) + E-ACC 6,892.2원(장부 `H/logs/eacc/astra_ledger.jsonl` charge 30행 + `astra_ledger_r2.jsonl` 109행; 상한 8,000원) + 이전 `[금액 미기록]` 분 | | |

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
| E-MA2 3판(C0·C1·C2) + 평가·지연 | 2·3 | ≈ 2.6 GPU-h(사전 실행 23:18–23:26; GPU 2 23:33–01:08, GPU 3 23:33–00:29; 학습 40.6·41.8·41.1분) | [R/ma2](../stage3/results/ma2.md) 5절 |
| E-SR0 진단(학습 없음, 3판 추론) | 2·3 | ≈ 0.3 GPU-h(사전 실행 01:33–01:35; GPU 2 01:37–01:47, GPU 3 01:37–01:43) | [R/sr0](../stage3/results/sr0.md) 7절 |
| E-SR1b(학습 8판 + 평가 9판·지연) | x2 0·1 + 메인 2·3 | ≈ 7.9 GPU-h(x2 3.72 + 메인 4.21; 사전 실행 02:20–02:29; 본 02:31–04:43; 학습 루프 37.6–39.0분) | [R/sr1b](../stage3/results/sr1b.md) 7절 |
| E-SR1c(분기 생성 CPU + Isaac G-br + 학습 2판·평가 4판) | 메인 1(학습·평가) + 0(Isaac CPU PhysX, 렌더 없음) | ≈ 2.5 GPU-h(GPU 1 ≈ 2.2: 사전 실행 02:50–02:57, 본 03:09–05:23; GPU 0 ≈ 0.3) | [R/sr1c](../stage3/results/sr1c.md) 7절 |
| E-SR1d(층·분기 CPU + 학습 2판·평가 4판, 시뮬 없음) | x2 0·1 | ≈ 2.2 GPU-h(사전 실행 GPU 0 ≈ 0.1: 05:52–05:57; 본 두 레인 06:00–07:02; 학습 루프 47.5·47.8분) | [R/sr1d](../stage3/results/sr1d.md) 6절 |
| E-NOV0(학습 없음, 특징 추출 27,107스냅샷 + 지연·재집계) | 2 | ≈ 1.0 GPU-h(사전 실행 05:15–05:35 ≈ 0.33 h; 본 05:37–06:15 ≈ 0.62 h; 재집계 06:17 ≈ 0.02 h; 판정은 CPU) | [R/nov0](../stage3/results/nov0.md) 7절 |
| E-CONF(학습 없음, 확신도 추출 34,630스냅샷 + S-E2E 묶음 1 재추출 3,598) | 2 | ≈ 1.5 GPU-h(사전 실행 06:55–07:17 ≈ 0.23 h; 본 07:19–08:21 ≈ 1.03 h; 재추출 09:41–09:56 ≈ 0.24 h; 판정·재집계 CPU) | [R/conf](../stage3/results/conf.md) 8절 |
| 프롬프트 검진(vLLM Qwen3-VL 8B·4B, 추론만) | 3 | ≈ 0.8 GPU-h(05:24–06:10, 두 서버 한 GPU) | [R/prompt_health](../stage3/results/prompt_health.md) 10절 |
| E-Astra-solo(Isaac + Qwen vLLM 사전 실행, 유료 폐루프) | 3 | ≈ 1.5 GPU-h(프로세스 합: vLLM 06:37–07:07 ≈ 0.48 h + Isaac 약 1.06 h, 06:34–07:31 한 장 공유) | [R/astra_solo_pilot](../stage3/results/astra_solo_pilot.md) 8절 |
| E-Couple 무료 사전 실행(Isaac + 융합 VLA + Qwen3-VL-8B vLLM, 한 GPU) | 메인 1 | ≈ 1.3 GPU-h(Qwen 서버 06:07–07:23; 스모크 06:08–06:12, 본 06:14–07:22), 유료 0원 | [R/couple_dry](../stage3/results/couple_dry.md) 5절 |
| MAR-real 준비(Molmo2-ER 포인팅 10,834회, 추론만) + MAR2D 시뮬 파일럿(중단) | 메인 0(포인팅·Isaac) + x2 1(Isaac 렌더 시험) | ≈ 0.56 GPU-h(포인팅 0.37: 일괄 시험 05:38–05:46 + 본 05:46–06:01; Isaac 약 0.19: 메인 0 05:22–05:30·x2 1 05:22–05:27) | [molmoact_real_readiness](../stage3/molmoact_real_readiness.md) 7절 |
| R2_TRAIN 생성 | 0·1(렌더) + 2(로더 확인) | ≈ 21.3 GPU-h(21.34; GPU 0·1 각 11:16–21:56 ≈ 10.7 h 점유, 동시 Isaac 최대 5 = 누적 52.8 프로세스-시간, 사용률 20–50 % `[미검증]` — 저장된 로그에 없음) [→ 정정 2026-09-25 23:58 UTC, R7 35회차 N178·N179] + GPU 2 약 0.2 h(로더 확인 2회); 첫 파일럿(6b013ac, 폐기) GPU 1 약 0.7 h 별도 | [R/r2_train_gen](../stage3/results/r2_train_gen.md) 8절 |
| R7 순회 | 1(Isaac 한 프로세스) | 회차당 폐루프 한 판 | `R/r7_cycle*.md` |
| E-MAR-real 요인 A(궤적 보조 학습·평가) | 메인 0 + x2 0·1 | ≈ 3.6 GPU-h(메인 GPU 0 1.55 h + x2 GPU 0·1 2.05 h) | [R/marr](../stage3/results/marr.md) |
| E-OpenVLM-proxy gpt-5.2 low 4편 + gpt-5-mini 7호출(중단) | 79 + 7 | **1,322.4원**(gpt-5.2 1,299.1 + mini 23.3; 상한 3,000원, 누적 확정분 합계에는 이 줄을 더한다) | gpt-5.2 **16.4원/호출**(입력 2,639·출력 471·추론 289 중앙), 지연 p50 7.2 s·p95 11.5 s, 성공 0; GPU ≈ 0.42 GPU-h(Isaac GPU 1) | [R/open_vlm_solo](../stage3/results/open_vlm_solo.md), 장부 `H/logs/open_vlm_proxy/ledger.jsonl` 86행 |
| E-TEACH-L8(참값 라벨 수집 340편 + 8B LoRA 학습 + 오프라인 평가 + 폐루프 8편) | 메인 0·1 + x2 0·1 | ≈ 6.7 GPU-h 점유(학습 1.39 = x2 0 12:50–14:14; 수집 1.55 + 파일럿 0.28; 폐루프 Isaac 0.6; 미세조정 vLLM 0.5; 영샷 vLLM 2.27 중 실사용 약 0.4) — 대기 뺀 실사용 ≈ 4.8 GPU-h, **유료 0원** | [R/teach_l8](../stage3/results/teach_l8.md) 6절 |
| E-TEACH-35B 준비(35B 내려받기·영샷 서빙 지연·학습 스모크 50걸음 × 2·병합-서빙 왕복) | 메인 1(Isaac 공유) + x3 0 + x2 0(시작 실패) | ≈ 1.3 GPU-h(메인 1 ≈ 1.1: 서빙 16:22–16:48, 스모크 16:48–17:10, fla 스모크 17:15–17:29; x3 0 17:15–17:22 ≈ 0.12; x2 0 ≈ 0.05), **유료 0원** | [R/teach_35b_ready](../stage3/results/teach_35b_ready.md) 6절 |
| E-SR1e(진단 + 학습 4판 + 평가 6판 + L1 8판 + 판정 밖 6판, 시뮬 없음) | 메인 2·3 | ≈ 13.2 GPU-h(GPU 2 학습 09:59–14:16 4.27 h + 평가 14:58–17:57 2.98 h, GPU 3 학습 09:59–14:58 4.97 h, 진단·사전 실행 ≈ 1.0 h; 다른 에이전트와 GPU 공유), 유료 0원 | [R/sr1e](../stage3/results/sr1e.md) 7절 |
