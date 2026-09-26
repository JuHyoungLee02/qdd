# E-Couple — Astra 직렬 1개 + 두 층 M4 대 VLA 단독 (사전 등록 **초안**, 유료 호출 0)

- 작성: 2026-09-26 05:20 UTC, 계획 `docs/superpowers/plans/2026-09-26-astra-vla-coupling.md` Task 15. 상태: **초안 — §0 자체 검사 절(바꾸는 결정·표본 충분성·무료 Qwen 사전 실행 결과·관문별 재설계 조건) 작성·커밋, 그리고 그 위에 사용자가 목적·호출 수·예상 비용을 보고 통제자 경유로 명시 승인해야만 유료 실행**(user-log 114 "돈드는건 내 허락맡고 하기", user-log 87의 자체 판단 규칙을 대체). 결과를 본 뒤 문턱·조건·시드·예산을 바꾸지 않는다(바꾸려면 새 등록).
- 근거: 설계 §9·§15·§16, 정본 §84 보충 2(직렬 1개, E-Couple 조건 = {VLA 단독, Astra 직렬 1개 + 두 층 M4}).

## 0. 자체 검사 + 사용자 승인 (user-log 114, user-log 87 대체, [작성 전])

**[작성 전]** 실행 전(§0 작성·커밋 없이는 유료 실행 금지, 정본 §85):
- 이 결과로 바꾸는 설계 결정: [작성 전]
- 이 표본으로 그 결정을 가를 수 있는가(층·표본 크기가 §5 문턱을 통계적으로 가릴 힘이 있는가): [작성 전]
- 더 싼 사전 실행(무료 모델·작은 판) 결과: [작성 전] — 계획된 값싼 사전 실행은 (1) `--astra mock`(`ScriptedCoupleAstra`)으로 시드 0–2 파이프라인 스모크(§3에 이미 기재 — 사이드카 `couple` 행·블롭·요약이 채워지는지만 확인, 유료 0), (2) 무료 Qwen3-VL 흐름 사전 실행(예: `--couple-upper local`, GPU 빈 곳, 시드 몇 개) — Astra 대신 로컬 VLM으로 A1 배선 전체(직렬 흐름 → 편향 → 두 층 관문 → 청크 준수 로그)가 끝까지 도는지 유료 호출 없이 먼저 확인한다. 이 항목에는 사전 실행이 끝난 뒤 그 결과가 §5 판정에 주는 함의를 적는다.
- 관문·재설계 규칙(정본 §85, user-log 87 (2)): 실행 중 단계 관문마다 결함(버그·무효 답 > 10 %·교란·비용이나 시간 2배 초과·관문 실패)이 보이면 그 자리에서 멈추고 재설계한다 — 재설계는 이 사전 등록 문서를 고쳐 **커밋한 뒤에만** 재개한다(틀린 설계로 계속 쓰지 않는다). 끝에는 검증 명령으로 결과를 확인한 뒤 보고한다.
- **유료 실행 승인(user-log 114, user-log 87 대체)**: 위 자체 검사 절을 커밋한 뒤, 이 목적·호출 수·예상 비용을 통제자 경유로 사용자에게 제안하고 **사용자가 명시로 승인**해야만 유료 실행을 시작한다("유익성 판단은 Claude가 하고 사용자 승인은 받지 않는다"는 user-log 87 문구는 더는 유효하지 않다). 승인 근거는 `--approval`에 남긴다.

## 1. 질문
Astra(low) 일반 조종 흐름을 한 번에 하나씩 부르고 두 층 M4로 합치면, 같은 융합 VLA 단독보다 폐루프 성공률이 오르는가? 새 환경 층(DR)에서 낙폭이 줄어드는가? 호출 수·지연·비용은 얼마인가?

## 2. 조건 (`harvest.eval.closed --couple ...`)
| id | 명령 | 내용 |
|---|---|---|
| A0 | `--couple off,serial`의 off 칸 | VLA 단독(Astra 없음, 하트비트 없음) |
| A1 | `--couple off,serial`의 serial 칸, `--astra api --couple-upper astra` | Astra low 직렬 1개 + 두 층 M4 + 부드러운 편향 + 3카메라·덧그림 |
| (선택) A2 | `serial_pause`, `--couple-phase-pause 8` | A1 + 단계 쉬기(비용이 넘칠 때만, 등록 때 넣을지 결정) |

같게 두는 것: 융합 체크포인트(**`ser-A-min-3` 직렬화 판 재학습판** — 움직임 줄 정본 §83 + 그리퍼 판단 질문 §87, 계획 Task 12; 체크포인트 해시는 실행 전에 이 문서에 적는다), M4 조건 C5, H = 3, clock simlat, 판 길이 60 s, `CoupleParams` = **탐침 결과로 고정한 값**(정본 §86: `request_mode` F0, `stale_edit_s` 15.0 s, `timeout_s` 20.0 s, `latency_init_s` 9.3 s, `probe_ref` = `docs/stage3/results/astra_motion.md` — 실행 전 이 표를 문서에 붙이고 `probe_ref`를 기록), 프롬프트 판본 `astra-couple@v1`(`PROMPT_ID`는 실행 전에 기록 — Task 8에서 범례·덧그림을 고쳐 `PROMPT_ID`가 그 개정을 따라 바뀌었으므로, 실행은 그 개정 뒤의 값으로 고정한다).

## 3. 층·표본
- 층: `standard`, `dr`(새 물체 에셋은 준비되면 새 등록).
- 표본: DEV 레이아웃 시드 0–19 × epoch 1 × 층 2 = 조건당 40편, 조건끼리 시드·층 짝.
- 스모크(판정 제외): `--astra mock`으로 시드 0–2 한 번 — 사이드카 `couple` 행·블롭·요약이 채워지는지 확인.

## 4. 지표
- 주: 성공률, 짝 차 A1 − A0(같은 변형·시드·epoch), 레이아웃 시드 군집 부트스트랩 10,000회 95 % 구간(`closed.json` `couple_diff`).
- 보조(판정 밖, 모두 보고): RD(standard → dr), 성공까지 시간, 편당 호출 수, 지연 p50·p95, 답 나이 p50, 편당 비용·성공 1건당 비용, gate 분포(uncertain → continue 비율 포함), Astra 층 동작(apply/confirm/flip), 편향 적용량·최대 속도·가속, 시간 초과·늦은 답·스키마 오류, 예산 제외 편 수.
- **청크 수준 준수(couple adherence, 판정 밖·보고)**: `closed.json`의 `summary()["adherence"]`(`harvest/couple/driver.py`, 통제자 판정 C2/C4)로 두 갈래를 조건별로 집계한다 — 실행된 청크의 손끝 변위 대 **Astra 편향(offset) 방향**의 코사인 `cos_vs_offset`/`follows_offset`, 그리고 실행된 청크 대 **VLA 확정 결정**의 코사인 `cos_chunk_vs_decision`/`follows_decision`, 둘 다 문턱 `cos > 0.5`(`p.adhere_cos`). 정본 §84 보충 4·5(E-MA2 NONE, E-SR0 WEAK)가 못박은 대로 **결정 토큰이 청크를 조종한다고 가정하지 않는다** — 두 준수율 모두 청크 FK 변위에서 재고, 결정 칸 일치만으로 대신하지 않는다.
- **비가역 전이 거부 수(판정 밖·보고, 계획 주 판정 R1의 비용 항목)**: `summary()["irrev"]`(`harvest/couple/twolayer.py`의 `Counter`, 키 `"allow:<이유>"`/`"deny:<이유>"`)를 조건별로 집계해 허용/거부 수를 보고한다. **주의**: 두 층 관문의 근거는 T1 고유감각 전제뿐이고(정본 §86, 계획 주 판정 R1) `_decide`가 신선한(≤ `astra_fresh_s`) Astra 답의 거부(`astra_gripper_opposes`/`astra_misaligned`/`astra_failed`)를 T1 증거 확인보다 **먼저** 보고 즉시 `False`를 반환하므로, 설계상 신선한 Astra 거부는 항상 전이를 막는다 — "신선한 Astra 답이 거부했는데도 진행된 비가역 전이" 수는 이 게이트 구현에서는 **정의상 0**이다. 그래도 `deny:astra_*` 대 `deny:no_evidence` 대 `allow:t1_fresh`/`allow:t1_astra_stale` 분포와, `layer_mismatch` 사건 수(거부가 `mismatch_s` 넘게 이어진 횟수)는 조건별로 보고한다(계획 R1이 묻는 "거부 비용"의 실측치).

## 5. 판정 (결과 전 고정)
1. **채택**: 두 층(standard ∪ dr) 합산 성공률 짝 차 점추정 ≥ +10 pt 그리고 95 % 하한 > 0.
2. **새 환경 이득만**: 1이 아니고, 합산 하한 > −5 pt 이며 dr 층 짝 차 하한 > 0 → "DR에서만 이득"으로 보고(런타임 기본은 바꾸지 않음).
3. 그 밖: 결론 유보, 결과 보고. 표본을 늘리려면 새 등록.
4. 예산 80 % 정지 뒤의 편은 판정에서 빼고 수를 보고한다. Isaac·파드 오류 편은 같은 시드로 한 번 다시 돌린다(두 번 실패면 제외·보고).

## 6. 예산 (정본 §82 보충: 전체 약 10만 원)
- 식: **호출 수 = 편 수 × 판 길이 / L**, 비용 = 호출 수 × 호출당 비용(실행일 가격표; `python -m harvest.eval.couple estimate --prices <그날 가격표> --episodes 40 --episode-s 60 --latency-s <탐침 L p50> --in-tokens <탐침 실측> --out-tokens <탐침 실측>`).
- **탐침 실측값으로 지금 추정**(정본 §86 보충 2, `docs/stage3/results/astra_motion.md` §2/§5: 직렬 F0 호출당 **약 49.7원**, 지연(벽시계) p50 **약 9.3 s**; 참고로 로봇 1분당 약 350–500원): 편 수 40 × 판 길이 60 s / L 9.3 s = **약 258회**(40 × 60 / 9.3 = 258.06), 비용 = 258회 × 49.7원 ≈ **12,826원**(약 12,800원) — 이 값은 실행 전 추정일 뿐이며, **실행일에는 위 CLI로 그날 가격표를 다시 읽어 재계산한다**(설계 §8·§15의 옛 사전 추정 28원/호출·L = 4 s는 탐침 전 값이라 더는 쓰지 않는다).
- **상한 25,000원**(80 % = 20,000원에서 정지·보고).
- **누적**(정본 §82 보충 "약 10만 원" 한도, E-Astra-necessity §5가 참조하는 계산과 같음): **탐침 실제 지출 6,933원**(하드 정지 상한 15,000원이 아니라 실측 지출 — `docs/stage3/results/astra_motion.md` §2, `docs/book/05-costs.md` 누적행) **+ 이 실험 상한 25,000원 + E-Astra-necessity 흐름 자리 상한 20,000원 = 51,933원 ≤ 100,000원**. 실측 단가(탐침: low 파지 질문 15.7원, 흐름 질문 49.7원)가 이미 나와 있으므로 실행 전 위 CLI 재계산 값이 이 문단의 12,826원 추정을 대체한다.
- 실행 명령(§0 자체 검사 커밋 + 사용자 명시 승인 뒤, user-log 114, 파드): `python -m harvest.eval.closed --model <체크포인트> --backend fused --out /data/harvest/out/e_couple --split dev --seeds 0-19 --variants standard,dr --couple off,serial --astra api --couple-prices <가격표> --couple-budget-krw 25000 --couple-ledger /data/harvest/out/e_couple/ledger.jsonl --approval "user approval: user-log 114, prereg_couple.md §0" --parallel`

## 7. 산출물
`docs/stage3/results/e_couple.md`(표·그림·영상: 판마다 카메라 3대 영상 확인), `closed.json`, 장부 JSONL, 블롭.
