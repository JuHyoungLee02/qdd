# E-Astra-necessity — 흐름 자리(실행 중 일반 조종) (사전 등록 **초안**, 유료 호출 0)

- 작성: 2026-09-26 04:38 UTC, 계획 `docs/superpowers/plans/2026-09-26-astra-vla-coupling.md` Task 16. 상태: **초안 — §0 자체 검사 절 작성·커밋, 그리고 그 위에 사용자가 목적·호출 수·예상 비용을 보고 통제자 경유로 명시 승인해야만 유료 실행**(user-log 114 "돈드는건 내 허락맡고 하기", user-log 87의 자체 판단 규칙을 대체).
- 범위: 정본 §82 E-Astra-necessity 중 **결합 흐름 자리**만. J1–J6(과제 컴파일·진단·검사 술어·이름·감사·증류) 오프라인 슬롯 시험과 폐루프는 §82 구현(`harvest/astra/jobs.py`)과 함께 별도 등록한다(연구 문서 `astra_role_2026-09-25.md` §7).

## 0. 자체 검사 + 사용자 승인 (user-log 114, user-log 87 대체, [작성 전])

**[작성 전]** 실행 전(§0 작성·커밋 없이는 유료 실행 금지, 정본 §85):
- 이 결과로 바꾸는 설계 결정: [작성 전]
- 이 표본으로 그 결정을 가를 수 있는가(층·표본 크기가 §4 문턱을 통계적으로 가릴 힘이 있는가): [작성 전]
- 더 싼 사전 실행(무료 Qwen·작은 판) 결과: 이미 존재하는 무료 사전 실행 — **Qwen3-VL-8B 직렬 흐름 0/6 성공**(F0·F1 각 3편, `docs/stage3/results/astra_motion.md` §5), **Qwen3-VL-8B 동기 S 0/20 성공**(같은 문서 §7) — 둘 다 6/6·20/20 approach 단계 실패. 이 사전 실행이 U-Q8 조건의 전신이며, 본 등록 실행 전 이 결과가 §4 문턱 판정에 주는 함의를 [작성 전]에 적는다.

## 1. 질문
같은 흐름 자리(직렬 1개, 같은 프롬프트·영상·스키마·게이트·두 층 M4)에 Astra low 대신 로컬 VLM을 넣으면 결과가 의미 있게 나빠지는가? 나빠지지 않으면 이 자리는 로컬로 강등한다.

## 2. 조건 (위층 모델만 바꾼다)
| id | 위층 | 명령 |
|---|---|---|
| U-A-low | Astra, effort low | `--couple serial --astra api --couple-upper astra` |
| U-Q8 | Qwen3-VL-8B-Instruct(로컬 vLLM, GPU 2 또는 3 빈 곳) | `--couple serial --couple-upper local --couple-local-url <vLLM> --couple-local-model <이름> --couple-min-interval <U-A-low 지연 p50>` |
| U-Q4 | Qwen3-VL-4B-Instruct 영점(융합 VLA와 같은 백본) | U-Q8과 같게 |
| U-none | 위층 없음 = VLA 단독 | `--couple off` |
| [선택] U-Q32 | Qwen3-VL-32B-Instruct(`/data`에 내려받은 뒤) | U-Q8과 같게 |
- 빼는 것: U-A-high(흐름에 high 금지, 정본 §82 보충 2 — high 비교는 J1·J6 오프라인 등록에서), U-rand(흐름에는 트리거가 없음).
- 공정성: 같은 프롬프트 바이트(`PROMPT_ID`)·같은 JPEG, 로컬은 JSON 강제 디코딩 없음·temperature 0·seed 0, **호출 간격 맞춤** — 로컬은 `min_interval_s` = U-A-low 실측 지연 p50(먼저 U-A-low를 돌려 값을 얻고 이 문서에 적은 뒤 로컬을 돌린다).
- 조건 고정값(정본 §86, `harvest/couple/params.py`의 `CoupleParams` 그대로): `request_mode` F0, `stale_edit_s` 15.0, `timeout_s` 20.0. 위층만 바꾸고 나머지 `CoupleParams`는 손대지 않는다.
- `PROMPT_ID`는 각 조건 실행 전에 기록한다 — Task 8에서 프롬프트 범례·영상 덧그림을 고쳐(통제자 판정 O1b·O2b, 색·모양 구분) `PROMPT_ID`가 그 개정을 따라 바뀌었으므로(`harvest/couple/prompt.py`), 이 등록의 실행은 그 개정 뒤의 `PROMPT_ID`로 고정하고 문서에 값을 남긴다.

## 3. 층·표본
S-ID = `standard`, S-random = `dr`; 층당 DEV 시드 0–19 × epoch 1. S-novel·S-long·S-fail은 에셋·과제 준비 뒤 새 등록.

## 4. 판정 (정본 §82·연구 §7.5 규칙, 결과 전 고정)
Δ = U-A-low − max(U-Q8, U-Q4[, U-Q32]) 성공률, 레이아웃 시드 군집 짝 부트스트랩 10,000회.
1. **Astra 필수(이 자리)**: S-random에서 Δ ≥ +10 pt 그리고 95 % 하한 > 0.
2. **강등**: S-random에서 Δ의 95 % 하한 > −5 pt 그리고 점추정 ≥ −3 pt, 그리고 로컬의 편당 비용·지연 p50이 더 작다 → 흐름 자리를 최고 로컬 모델로.
3. 그 밖: 결론 유보, Astra 유지, 보고.
4. 대조: S-ID에서 U-A-low − U-Q4의 95 % 구간이 ±5 pt 안이면 "분포 안에서는 위층 차이 없음" 확인. U-A-low − U-none은 E-Couple과 같은 식으로 보고.
5. **판정 밖, 보고(추가) — 청크 수준 준수(couple adherence)**: `closed.json`의 `summary()["adherence"]`(`harvest/couple/driver.py`, 통제자 판정 C2/C3)로, 실행된 청크의 손끝 변위 대 Astra 편향(offset) 방향의 코사인 유사도 `cos_vs_offset`을 조건별로 집계하고 `cos > 0.5`를 따름(`follows_offset`)으로 판정한다. 정본 §84 보충 4는 결정 토큰이 청크를 조종한다고 가정하지 않는다고 못박았으므로(E-MA2 NONE: 결정 칸 준수 0.97이나 청크 준수 0.28/0.09) 준수율은 **반드시 청크 수준**(FK 변위)에서 재고, 결정 토큰 일치만으로 대신하지 않는다; §84 보충 5(E-SR0 WEAK)는 조이스틱 결정 조건화가 아직 약함을 보여 같은 경고가 이 조건(Astra `edit` 편향)에도 적용됨을 재확인한다. 이 항목은 판정(§4 1–4)을 바꾸지 않고 보고에만 쓴다.

## 5. 예산
- 유료는 U-A-low뿐. **E-Couple A1과 같은 날·같은 체크포인트·같은 `CoupleParams`·같은 시드면 그 결과를 재사용**하고(이 문서에 재사용을 명시), 이 등록의 추가 유료 호출은 0.
- 재사용이 불가능하면 상한 20,000원(80 % 정지), 누적 한도 계산은 E-Couple 등록 §6과 같음.
- 단가 참고(탐침 실측, 정본 §86 / `docs/stage3/results/astra_motion.md` §2): 흐름 호출(S2, F0) **약 49.7원/호출**, 지연 p50 약 9.3 s. 이 단가는 탐침 시점(gpt-6-astra, 입력 $10 / 캐시 $1 / 출력 $50 per 1M, 환율 1,450원/USD) 기준이며, **실행일에는 `python -m harvest.eval.couple estimate`(Task 14 추가)로 그날 가격표를 다시 읽어 예상 비용·상한을 재계산**한다 — 위 20,000원 상한은 탐침 단가 기준 참고값이고, 실제 실행 전 재계산 값으로 대체한다.

## 6. 산출물
`docs/stage3/results/e_astra_necessity_stream.md`, `closed.json`(조건별 칸·`couple_diff`·`adherence`), 장부.
