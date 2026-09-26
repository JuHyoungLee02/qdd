# E-Couple 무료 사전 실행(셰이크다운) — 결합 폐루프 배관 점검, P3 판정 없음 (사전 등록)

- 작성: 2026-09-26 06:05 UTC. 근거: 정본 §92 보충 1 전제 표 **P3**(결합이 폐루프에서 VLA 단독보다 낫다)로 가는 임계 경로를 줄이기 위해, 직렬화기 판 올림(결합 계획 Task 12)과 재학습이 끝나기 **전에** 이미 커밋된 결합 배선(Task 1–11, 13–16)을 폐루프에서 끝까지 돌려 **통합 버그를 먼저 찾고 배관 수치를 잰다**. E-Couple 사전 등록 초안(`prereg_couple.md`, 2a99db6) §0의 "무료 Qwen3-VL 흐름 사전 실행" 칸이 바로 이것이다.
- **성격(§56)**: 셰이크다운. **P3에 대한 판정·결론을 내지 않는다.** 행동 지표(성공·성공 시각·저크)는 서술로만 보고하고, 어떤 설계 결정도 이 수치로 바꾸지 않는다. 유료 호출 0회(Astra 대신 로컬 Qwen3-VL-8B).

## 0. 자체 검사 (user-log 87, CLAUDE.md)

- **이 결과로 바꾸는 결정**: 본 E-Couple(`prereg_couple.md`)을 Task 12·재학습 직후 **바로** 돌려도 되는가 — 실행 전에 고쳐야 할 결함 목록(심각도·재현·담당)과 `prereg_couple.md` §0의 사전 실행 칸 내용. 행동 수치는 결정에 쓰지 않는다(아래 표본·대역 한계).
- **이 표본으로 그 결정을 가를 수 있는가**: 배관 결함은 한 번 나오면 결함이다(빈도 추정이 목적이 아님). 흐름 호출 약 6–7회/편 × 결합 12편 ≈ 70–80회면 호출당 3 % 빈도 결함을 약 88 % 확률로 한 번 이상 본다(1 − 0.97^70). 시간 초과·늦은 답 경로는 드물어 자연 발생을 기다리지 않고 **고정 결함 주입**(아래 2절)으로 반드시 지나가게 한다. 성공률 차는 12쌍이라 가를 힘이 없고 Qwen ≠ Astra이므로 판정하지 않는다.
- **더 싼 사전 실행**: 이 실행 자체가 E-Couple의 무료 사전 실행이다. 그 앞 단계로 G0 스모크(1쌍, 20 s)를 둔다. 도구 단위 시험 `tools/couple_dry/test_couple_dry.py`(5개)는 등록 전 로컬 통과.
- **관문·재설계(정본 §85)**: G0 실패(작업자 충돌·결합 행 없음·흐름 답 0개) → 멈추고 원인 추적. 원인이 `harvest/`(결합 통제자 소유 파일)이면 **고치지 않고** 재현과 함께 main에 보고하고, 우회가 `tools/couple_dry/` 안에서만 가능할 때만 우회해 변경 기록을 이 문서에 커밋한 뒤 재개한다. 본 실행 중 Isaac·파드 오류 편은 같은 시드로 한 번 다시(두 번 실패면 제외·보고). 무효 답(스키마 오류) 비율 > 10 %는 **멈춤 조건이 아니라 측정 항목**으로 둔다 — 대역 Qwen의 성질이고 판정이 없어 낭비가 생기지 않으며, 그 비율 자체가 Astra 실행 전 프롬프트·파서 점검 근거이기 때문이다(이 예외를 결과 전에 등록한다). 시간 2배 초과(GPU 1 3 h 초과) → 남은 편 중단·보고.
- **비용**: 유료 0원(`--astra none`, `--couple-upper local`; `dry_closed.py`가 다른 조합을 거부). GPU: 메인 파드 **GPU 1만** 약 1.5 GPU-h 예상(Isaac 렌더 + 융합 VLA 서버 + Qwen vLLM). 다른 GPU·프로세스는 건드리지 않는다(GPU 0 MolmoAct, 2 E-NOV0, 3 prompt-health vLLM, x2 GPU 0·1 E-SR1d).

## 1. 고정 코드·모델

- 코드: **이 등록 커밋**의 고정 사본(`git -c core.autocrlf=false archive`, LF) → 파드 `/data/harvest/code_couple_dry_<등록 커밋 짧은 해시>`, `CODE_VERSION` JSON(P73). 결합 배선 기준 = 553a8ad(정본 §92 보충 1); 그 뒤 커밋 32065de(E-SR1d)는 `harvest/train/sr1d*`·`tools/sr1d` 등 새 파일만 더해 `harvest/runtime/`·`harvest/couple/`·`harvest/eval/`·직렬화기는 553a8ad와 같다(`git diff --stat 553a8ad 32065de`로 확인). 결합 통제자가 작업 중인 **미커밋** 편집(`harvest/runtime/*`·직렬화기·`harvest/couple/*`, Task 12)은 포함하지 않는다.
- VLA: E-SR1c 채택 체크포인트 `/data/harvest/ckpt/sr1c/c1/last`(R2, 먼 구간 분기 레시피, 정본 §84 보충 8). 553a8ad의 프롬프트 파일 해시 11개가 체크포인트 `prompt_config.files_sha`와 모두 같음을 등록 전 확인(엄격 `check_prompt` 통과 예상). Task 12 판 올림 뒤에는 이 체크포인트가 거부되는 것이 정상이다.
- Astra 대역: 로컬 **Qwen3-VL-8B-Instruct**(vLLM, GPU 1, `--gpu-memory-utilization 0.22`, 온도 0·seed 0), 결합 코드의 로컬 VLM 어댑터(`harvest/couple/local_vlm.py`, Task 13) 그대로. 프롬프트 `astra-couple@v1` F0, 카메라 3대 + 덧그림.
- `CoupleParams` = 553a8ad 기본값(탐침 확정값: F0, `stale_edit_s` 15, `timeout_s` 20, `latency_init_s` 9.3, 편향 `v_max` 0.08 m/s·`a_max` 0.32 m/s², 두 층 관문 T1 근거만).

## 2. 조건·표본

| 팔 | 명령(`tools/couple_dry/run_dry.sh main`) | 내용 |
|---|---|---|
| A0 | `--couple off,serial`의 off | 융합 VLA 단독(Astra·하트비트 없음) |
| A1-dry | 같은 명령의 serial, `--couple-upper local --astra none` | Qwen3-VL-8B 직렬 1개 + 두 층 M4 + 부드러운 편향 + 3카메라·덧그림 |

- 표본: DEV 레이아웃 시드 **0–5 × 변형 {standard, dr} = 12 단위 × 팔 2 = 24편**, 판 60 s, C5, H = 3, clock simlat, epoch 1. 팔끼리 시드·변형 짝. 변형은 차례로(병렬 아님, P58·P86 CPU 부하 교란 회피).
- **시험 전용 고리 3개**(`tools/couple_dry/dry_closed.py`, `harvest/` 무수정 — 작업자 프로세스 안에서만 감쌈):
  1. **지연 맞춤**: Qwen 답을 Astra 지연처럼 붙잡는다 — 로그정규 중앙 9.3 s(정본 §86 F0 벽시계 p50), σ 0.25(p95 약 14 s), (편, 요청 번호)로 결정적. Qwen 실제 지연은 따로 기록. 이유: 답 나이·도착 시점 예상 상태·늦은 답 폐기(15 s)·`L_hat`이 Astra 조건에서 돌게 하려는 것.
  2. **결함 주입**: 결합 팔의 **짝수 번째 편**(시드 1·3·5)에서 요청 3번을 25 s 붙잡는다(> `timeout_s` 20 s) → 시간 초과 → 자리 비움 → 다음 요청 → 늦은 답 도착 경로를 반드시 지난다.
  3. **관측만**: 틱마다 TCP·단계·근접·특권 권한 대리값 a_priv(`sr1c_authority.authority`, 손가락 중점 → 단계 대상 거리; **적용하지 않음**)·결합 편향 스텝·편향 속도·남은 양·속도 배율; 영상 프레임(머리 + 오른손목, 시뮬 3 Hz, 두 팔 같은 비용).
- 스모크 G0(판정 제외): 시드 0, standard, 두 팔, 20 s(`run_dry.sh smoke`).

## 3. 지표 (모두 서술 보고, 판정 없음)

**배관**(결합 팔; `tools/couple_dry/analyze.py`):
1. 충돌: 작업자 Traceback 수, `eval_runs` 상태·오류, 기대 편 수 대비 실제.
2. 시간 초과·늦은 답 수(기대 = 주입 결함 중 실제로 요청 3번까지 간 편 수).
3. **동시 1개 불변식**: (a) 부가 로그만으로 — 요청 k+1은 요청 k의 답(오류·스키마 오류 포함) 또는 시간 초과 뒤에만 나감(위반 수, 기대 0); (b) 클라이언트 층 실제 동시 호출 수(기대: 1, 주입 시간 초과 직후에만 2); (c) 흐름 자체 계수 `max_inflight`·`max_outstanding`.
4. **늦은 답 폐기**: 게이트 `stale` 수, 답 나이 분포(15 s 초과 수).
5. **도착 시 대조 판정 수(정본 §91)**: 553a8ad에 구현 없음(결합 계획 Task 19 미커밋) → "측정 불가·미구현"으로 적는다.
6. **권한 a 궤적(§84 보충 8)**: 553a8ad에 런타임 적용 없음(Task 17 미커밋) → 대리값 a_priv 궤적(틱 비율 a = 0·중간·1)과 **a_priv = 0에서 실제로 적용된 편향 이동량**(Task 17이 들어가면 0이어야 할 양)을 잰다.
7. **편향 크기·속도 상한**: 요약 `v_max_seen` ≤ 0.08·`a_max_seen` ≤ 0.32(기대: 지킴), 틱 궤적의 편향 속도 최댓값, 편향 누적 경로 길이·남은 양 최댓값, 명령·리셋·축소 수.
8. **T1 관문 결정**: `irrev` 허용/거부 사유별 수, `layer_mismatch` 사건 수.
9. 답 형식: 스키마 오류 수와 문제 종류, 게이트 분포, 명령 분포, 층 동작(apply/confirm/flip).
10. **장부**: 행 수·합계(기대 **0원**, 가격 모델 `mock`), 종류(charge/unanswered).
11. 지연: 붙잡은 지연 p50·p95, Qwen 실제 지연 p50·p95, 청크 수준 준수(`adherence`).

**행동**(두 팔, 서술만): 성공 수, 성공 시각 중앙, 저크 RMS 중앙(탐침과 같은 식 `harvest/astra_motion/harness.motion_stats`, 틱 TCP 경로), 최대 속도, RTF, 마지막 단계 분포.

**프레임 확인**(책 규칙): 결합 팔 몇 편의 영상과 흐름 모델이 실제로 받은 요청 영상(덧그림 포함, 블롭)을 시트로 만들어 눈으로 확인하고 결과 문서에 적는다.

## 4. 산출물
`docs/stage3/results/couple_dry.md`(배관 표·버그 목록(심각도·재현·담당)·본 E-Couple 전에 고칠 것), 파드 `/data/harvest/out/couple_dry/{smoke,main}/`(closed.json·부가 로그·`dry_*.jsonl`·장부·`dry_analysis.json`·`sheets/` 영상), 로그 `/data/harvest/logs/couple_dry/`.

## 변경 기록
- (없음)
