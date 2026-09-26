# E-SR0 조이스틱 준수 진단 — expert 청크는 조건으로 받은 결정을 따르는가 — 사전 등록 (2026-09-26T01:36:22Z, 본 실행 전)

작성 E-SR0 에이전트. 근거: 연구 문서 `docs/research/steering_representation_2026-09-25.md` §4 권고 0·§5.1(E-SR0 초안), E-MA2 결과 `docs/stage3/results/ma2.md`(`399d1cb`)·함정 P75, 정본 §58(융합 VLA: typed 결정 토큰 + expert 청크)·§67(C4: decide → chunk 두 호출, expert는 **확정 결정**을 조건으로 받는다)·§83(움직임 줄)·§84(결합 설계 승인, 보충 4 = E-MA2 NONE), 결합 설계 `docs/superpowers/specs/2026-09-26-astra-vla-coupling-design.md` §6(융합 경로 조이스틱 준수 = E-SR0)·§11(Astra `edit`은 조이스틱 결정의 기준 방향에 **편향으로** 더한다). 이 문서는 **본 실행 전에** 조건 집합·지표·판정 규칙·자체 검사 관문을 고정한다. 결과는 `docs/stage3/results/sr0.md`. 학습 없음(기존 체크포인트 추론만).

## 0. 성격, 이미 본 것, 자체 검사(user-log 87, CLAUDE.md)
- **진단 실험(학습 없음)**. 모델 자신의 추론 경로(`StageB.forward_shared` → 예측 결정·문맥 은닉 → `StageB.cond` + `stageb_expert.sample_actions` Euler 10, E-MA2 `ma2eval`·런타임과 같은 decide → chunk)에서 **expert에 주는 결정 토큰만** 바꾼다. 기준 파일(`stageb_*`·`prefix_share`·`se2e_*`·`r2_ma2`·`harvest/runtime`) 무수정 — 새 파일 `tools/sr0/*`와 시험뿐.
- **이 결과로 바뀌는 결정**: 조이스틱(typed 결정) → expert 조건이 약하면(WEAK) **결합(Astra–VLA, 설계 §11 편향이 조이스틱 결정을 통해 행동을 바꾼다는 전제) 전에 조건 강화부터** 한다 — 후속 학습 실험 E-SR1b(후보: 결정 조건 분류기 없는 안내(CFG) + 학습 때 결정 드롭아웃, 결정 드롭아웃 단독, FiLM·접두 같은 강한 조건, 청크와 결정을 잇는 보조 손실; 이 등록에서는 돌리지 않고 결과 문서에 문헌 근거 1–2개로 권고). 동시에 설계 §11 편향과 §6 결정 투영을 "결정 토큰 경유"가 아니라 "청크·손끝 기준 경유"로 적용해야 하는지가 이 결과로 갈린다. FOLLOWS면 조건 구조를 그대로 두고 결합으로 간다.
- **이미 본 것(등록 전)**: (1) E-MA2 결과 — C1 판에서 결정층은 돌린 명령 칸을 0.97로 고르지만 expert 청크는 90°에서 0.28·180°에서 0.09만 따름(C0 0.13·0.07). (2) E-MA3 기준 청크 평가 요약(`/data/harvest/logs/ma3/chunk_none_s1.jsonl` 끝 줄, 실행 스크립트를 읽다 봄): motion_s1 확정 결정 조건 `sample_mse_norm` 0.02960 대 예측 결정 조건 `chunk_mse_pred` 0.02970(+0.3 %). (3) 사전 실행(0.3절)의 관문 출력(재현 일치). 준수율 값은 사전 실행에서도 읽지 않았다(판정 스크립트 출력은 파일로만, rc만 확인). **문턱 0.6은 작업 지시(메인 세션)가 어느 실행보다 먼저 준 값**이고, 보조 문턱(z 0.6, 크기 순서 ρ 0.5, 그리퍼 0.1)은 사전 실행 전에 시험 파일(`tests/test_sr0_verdict.py`)에 적혔다.
- **이 표본으로 가를 수 있는가**: 주 지표는 반사실 방향 준수율 A_xy(스냅샷 × 강제 방향 쌍의 적중 비율). 스냅샷 군집 최악 분산(스냅샷별 비율 ∈ [0, 1], 분산 ≤ 0.25)으로 표준오차 ≤ √(0.25/n): S-E2E 1,799 → ≤ 0.012(두 시드 합동도 같은 스냅샷이라 이 이하), R2 1,200 → ≤ 0.014; 95 % 반폭 ≤ 0.023·0.028. 우연 수준(섞은 결정, 약 3/8 = 0.375)과 문턱 0.6의 간격 0.225는 표준오차의 16배 이상이다 → **0.6 판정은 참값이 0.6 ± 0.03 안에 있지 않는 한 가를 수 있다**(그 안이면 구간과 함께 규칙대로 보고). 300개 부분집합으로도 반폭 ≈ 0.058이라 극단 결과는 가를 수 있지만, 전체가 판마다 수 분이라 전체를 쓴다(재현 관문을 전체 기존 기록과 대조할 수 있다는 이점도 있음). 가를 수 없는 것: 체크포인트 학습 규모(2,000스텝)의 영향 — 이 진단은 "지금 레시피·규모의 expert"에 대한 것이며, 규모를 키우면 달라지는지는 판정 밖.
- **싼 사전 실행**(0.3절): 두 체크포인트 12스냅샷 + 재현 관문 + 판정 스크립트 끝까지.
- **도중 관문(멈추고 재설계 → 8절에 UTC와 함께 기록·커밋 → 재개)**: G0 데이터 — S-E2E 판마다 `n` 1,799·`skip` 0·`keys_sha` = `f03062db4b1d`(E-MA3 기준 평가 `val_keys_sha`와 같아야 함), R2 `n` 1,200·`skip` 0; G1 경로 재현(4절); G2 시간 — 평가 하나가 예상(S-E2E 약 10분, R2 약 5분)의 3배(30분·15분)를 넘으면 멈추고 원인 확인; G3 값 — NaN·무한대 0(판정 스크립트 입력 검사).
- 비용: 유료 API 0건. GPU 2·3만(파드 `juhyoung-native-7a2a`; GPU 0·1과 남의 프로세스는 건드리지 않음). 예상 ≈ 0.5 GPU-h 이하.

### 0.3 사전 실행 결과(등록 전, 파이프라인 확인 — 결과 아님)
- 2026-09-26 01:33:29–01:34:38 UTC, 개발 사본 `/data/harvest/tmp/sr0/repo`(HEAD `7c56331` 추출 + 새 파일), GPU 2, 드라이버 `run_sr0.sh … dry`: motion_s1 12스냅샷 rc 0(적재 포함 41 s), c0 12스냅샷(`--grip`) rc 0(27 s), 어휘 검사 통과(강제하는 값이 모두 체크포인트 어휘에 있음 — 없으면 id 0으로 조용히 바뀌므로 도구가 거부). 관문 G1: S-E2E 예측 결정 일치 36/36 = 1.0, 확정 결정 조건 평균 MSE가 E-MA3 기록 대비 +6.2 %(12개, 잡음 추출이 달라 생기는 차), R2 예측 결정 일치 60/60, `pred` 조건 청크 손끝 변위가 E-MA2 `eval_c0` `none` 기록과 중앙값 0.0005 mm·최대 0.0008 mm 차(같은 잡음 시드·순서 → 같은 경로 확인). 판정 스크립트(부트스트랩 100회) rc 0 — 출력 값은 읽지 않음. 로그 `/data/harvest/logs/sr0/dry/`.
- 시험: 로컬·파드 `tests/test_sr0_eval.py`·`test_sr0_verdict.py`·`test_sr0_gate.py` 22 통과.

## 1. 질문
융합 VLA의 expert(흐름 정합, KI stop)는 조건으로 받은 조이스틱 결정(`dir_xy`·`dir_z`·`mag_coarse`)을 따르는가 — 결정을 반사실 값으로 바꾸면 청크의 FK 손끝 변위가 그 방향·크기로 바뀌는가? 우연 수준(섞은 결정)과 참 결정 기준선은 얼마인가?

## 2. 체크포인트와 입력
| 판 | 체크포인트 | 데이터·평가 집합 | 비고 |
|---|---|---|---|
| S-E2E s1 | `/data/harvest/ckpt/se2e_confirm/motion_s1/last` | `se2e_c1` 검증 전체 1,799(`--val-per-kind 0`, 키 sha `f03062db4b1d`), 움직임 줄 `se2e-motion@v1` | 공개 AI Worker 실물, 10 Hz, H 5, 결정 = 휴리스틱(다음 0.3 s FK 변위 부호·크기), 내부용(§63 (6)) |
| S-E2E s2 | `…/motion_s2/last` | 같음 | 시드 2 |
| R2 C0 | `/data/harvest/ckpt/ma2/c0/last` | E-MA2 평가 집합 1,200(`/data/harvest/data/ma2/eval_set.json` sha `61b2bce64ee1`, R2_TRAIN eval 분할) | 30 Hz, H 15, 결정 = labels_v2(부분 목표 방향); 입력은 기본과 같음(`ma2_apply` given 0) |
- **R2 단계 B 기준 체크포인트**: `/data/harvest/ckpt/stageB`에는 스모크 판뿐이다. E-MA2 C0가 R2_TRAIN 전체로 2,000스텝 학습한 기본 입력 판이라 이것을 R2 기준으로 쓴다(따로 없음).
- 적재 = `stageb_train.load_backbone` + `stageb_model.load_heads` + `aux_model` + `temporal_model`(S-E2E `stageb_train predict`와 같은 옵션), R2 = `stageb_data.load_for_training("r2", eval rows)`에서 평가 id를 `r2_ma2.sample_id`로 고름(E-MA2 `ma2eval`과 같음).

## 3. 조건 집합(스냅샷마다 고정, 한 번에 한 질문만 바꿈)
- `true`: 확정 결정 = 스냅샷 라벨(학습 때 교사 강요와 같음). `pred`: 모델 argmax 결정(공유 접두 한 번).
- `xy:<d>`: `dir_xy`를 9개 보기(8방향 + `none_xy`) 각각으로, 나머지 질문은 라벨. `z:<d>`: `dir_z` ∈ {up, down, none_z}. `mag:<m>`: `mag_coarse` ∈ {tiny, small, medium, large, xlarge}(0.5/1/2/4/8 cm). `flip`: `dir_xy`·`dir_z` 부호 반대(none 유지).
- R2만 `pid:close`·`pid:open`: expert의 하위 단계 토큰(`phase_id`)을 close/open으로. **typed 결정 어휘에는 그리퍼 보기가 없다**(S-E2E 어휘 = `dir_xy`·`dir_z`·`mag_coarse`, 스킬 `teleop`·단계 `na` 하나라 그리퍼 사건을 나르는 이산 조건 자체가 없음). R2에서 그리퍼 사건을 나르는 이산 조건은 `phase_id`(close·open)이므로 "expert가 어떤 이산 토큰이든 따르는가"의 대조로 잰다(판정 밖).
- 한 스냅샷의 모든 조건은 같은 흐름 잡음(`seed * 1_000_003 + 스냅샷 순번`, seed 0 — `ma2eval`과 같음), 한 번의 묶음 expert 호출(B = 20 또는 22). 강제하는 값은 모두 체크포인트 어휘에 있어야 한다(없으면 도구가 멈춤).
- 기록: 조건마다 청크 손끝 변위 = FK(청크 마지막 목표 관절) − FK(첫 목표 관절)(활성 팔 URDF `ffw_bg2_rev4_follower.urdf`, `arm_base_link` 기준 — `ma2eval`과 같은 정의; S-E2E 라벨도 같은 좌표), 첫·마지막 목표의 그리퍼 열림(0–1), 기록 행동 대비 정규화 청크 MSE(유효 스텝). 기록 행동의 같은 변위(`disp_gt`)도.

## 4. 경로 재현 관문 G1(`tools/sr0/sr0_gate.py`, 본 결과를 읽기 전에 통과해야 함)
- S-E2E(판마다): 예측 결정이 E-MA3 기준 평가(`/data/harvest/logs/ma3/chunk_none_s{1,2}.jsonl` 항목)와 (키, 질문) 99 % 이상 같고, `true` 조건 평균 MSE가 그 기록의 `sample_mse_norm`과 ±10 % 안(잡음 추출 순서가 달라 완전 일치는 기대하지 않음).
- R2: 예측 결정이 E-MA2 `eval_c0.jsonl` `none` 기록과 99 % 이상 같고, `pred` 조건 청크 변위가 그 기록 `disp`와 중앙값 ≤ 1 mm(같은 잡음 시드·순서라 같아야 함).
- 실패하면 멈추고 원인(적재·순서·잡음)을 고친 뒤 8절에 기록·커밋하고 다시 돈다.

## 5. 지표와 판정 규칙 (고정, `tools/sr0/sr0_verdict.py`)
- **반사실 방향 준수율 A_xy(주 지표)**: 쌍 (스냅샷, d) — d ∈ 8방향, d ≠ 라벨 `dir_xy`(라벨이 `none_xy`면 8개 모두) — 중 [|청크 변위 xy| ≥ 0.1 mm **그리고** cos(변위 xy, d의 단위 벡터) > 0.5]인 비율(쌍 합산). 평균 코사인(변위 < 0.1 mm면 0)도 함께.
- **우연 수준(섞은 결정)**: 같은 쌍에서 `xy:d` 청크를 d 대신 8방향 라벨 전체에 대어 본 적중률의 평균 = 강제 라벨을 무작위로 섞었을 때의 기대 적중률(청크가 결정을 무시하면 A_xy ≈ 이 값; 변위가 한 방향이면 3/8).
- **수직 준수율 A_z**: d ∈ {up, down}, d ≠ 라벨 `dir_z`; 적중 = `z:d` 청크 z 변위 ≥ +0.1 mm(up)·≤ −0.1 mm(down). 우연 = 두 라벨 평균.
- **크기 순서**: 스냅샷마다 구간 순번(tiny→xlarge)과 `mag:<m>` 청크 |변위|의 Spearman ρ(평균 순위; 다섯 값이 같으면 제외), 평균 ρ. 우연 = 0(구간을 섞으면 기댓값 0). |xlarge|/|tiny| 중앙값도.
- **그리퍼(R2, 판정 밖)**: 차 = 열림(마지막 목표 | `pid:open`) − 열림(… | `pid:close`); 적중 = 차 ≥ 0.1, 역방향 = 차 ≤ −0.1, 우연 = (적중 + 역방향)/2.
- **참 결정 기준선(판정 밖)**: 라벨 `dir_xy` ≠ none인 스냅샷에서 `true` 청크가 라벨 방향과 맞는 비율, 기록 행동(`disp_gt`)이 라벨과 맞는 비율.
- **판정 밖 보고**: 판별(시드별) 값, 스냅샷 부트스트랩 10,000회(시드 0, S-E2E 두 시드는 같은 키로 짝) 95 % 구간(A_xy·우연·평균 코사인·A_z·평균 ρ), 라벨 크기 구간별·라벨 none 여부별·강제 방향별 A_xy, 강제 방향에 따른 변위 퍼짐(8방향 변위의 평균에서 떨어진 거리 평균, mm) 대 `true` 청크 크기(mm), MSE(`true`·`pred`·`flip`)와 상대 차(연구 문서 §5.1 예시의 "선택 무시"·"오류 전파" 분류용), 예측 = 라벨 비율.
- **판정**(CMP_EPS 1e-12; 데이터 두 개 = S-E2E(motion_s1 + motion_s2 쌍 합산)와 R2(C0)):
  1. 어느 한 데이터라도 **A_xy < 0.6** → **WEAK**: 조이스틱 → expert 조건이 너무 약하다. 결합(설계 §11 편향을 결정 경유로 쓰는 것) 전에 조건 강화 후속 실험 **E-SR1b**를 새로 사전 등록해 돌린다(0절 후보, 결과 문서에 권고 1–2개).
  2. 아니고, 어느 한 데이터라도 **A_z < 0.6 또는 평균 ρ < 0.5** → **PARTIAL**: 수평 방향은 따른다; 못 따르는 축(수직·크기)만 E-SR1b 대상으로 하고 결합은 진행.
  3. 그 밖 → **FOLLOWS**: 조건 구조 유지, 결합으로.
- 입력 검사(스크립트): 파일마다 `summary.n` = 기대 수(1,799·1,200) = 기록 수, `skip` 0, 키 중복 없음, 모든 조건 존재, 값 유한; S-E2E 두 시드의 키 순서 같음. 결과 뒤 고치지 않는다.
- **해석 한계**: 오프라인(폐루프 아님), 청크 하나(0.5 s)의 변위, 2,000스텝 규모 체크포인트, S-E2E 라벨은 휴리스틱(실물 공개 데이터 — 논문 근거 아님, §56), R2 라벨은 부분 목표 방향(실제 궤적과 `dir_xy` 0.74 일치 — E-MA2 등록 4절)이라 `true` 기준선 자체가 1보다 낮을 수 있다. 반사실 결정은 학습 분포 밖 조합(예: 목표 반대 방향)이라 "분포 밖이라 무시"와 "조건을 안 씀"을 이 설계로 완전히 가를 수는 없다 — 라벨 none 스냅샷(어느 방향도 모순이 아닌 경우)의 A_xy를 판정 밖으로 따로 보고해 참고한다.

## 6. 실행
- 파드 `juhyoung-native-7a2a`, 코드 `/data/harvest/code_sr0` = 이 등록 커밋의 `git -c core.autocrlf=false archive`(LF), `CODE_HASHES.txt`. 드라이버 `tools/sr0/run_sr0.sh <코드> A|B|gate|verdict`(사본 `/data/harvest/logs/sr0/run_sr0.sh`): **GPU 2** motion_s1 → c0, **GPU 3** motion_s2, 둘 다 끝나면 gate → verdict. `source /data/harvest/env.sh`, `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`, `nice`. 출력 `/data/harvest/logs/sr0/`(`sr0_*.jsonl`, `verdict.json`), 로컬 요약 `D:\tools\scratch_qdd\sr0`.

## 7. 코드
| 항목 | 값 |
|---|---|
| 이 등록과 함께 고정(LF sha256 앞 16) | `tools/sr0/sr0_eval.py` `b3e01612a9f7ef14`, `tools/sr0/sr0_gate.py` `0e592c85ad865e32`, `tools/sr0/sr0_verdict.py` `db74f1571b7f4cc9`, `tools/sr0/run_sr0.sh` `edcd9972c6f25612`, `tests/test_sr0_eval.py` `9e5e083b64edef59`, `tests/test_sr0_gate.py` `ae2b77a885fe9b01`, `tests/test_sr0_verdict.py` `28813634387e1a24` |

## 8. 하지 않는 것 / 변경 기록
- 하지 않음: 학습, CFG·드롭아웃 등 수정안 실행(E-SR1b는 따로 등록), 폐루프 평가, 기준 파일·런타임 변경, GPU 0·1, 유료 API.
- 변경 기록:
  - **변경 1 (2026-09-26T01:48:32Z, 판정 입력 검사 버그 — 결과 값을 읽기 전)**: 본 평가 세 판이 끝나고(G0 통과: `n` 1,799·1,799·1,200, `skip` 0, S-E2E `keys_sha` `f03062db4b1d`, R2 `61b2bce64ee1`) G1 관문도 통과한 뒤(S-E2E 예측 일치 1.0·1.0, MSE −1.9 %·−1.3 %; R2 예측 일치 1.0, 변위 차 중앙값 0.0005 mm) `sr0_verdict.py`가 `sr0_c0.jsonl: duplicate keys`로 멈췄다(rc 1, 출력 파일 없음 — 준수율 값은 계산·표시되지 않음). 원인: 스냅샷 동일성을 단계 B 키 `<섭동>_ep<시드>_k<k>`로 검사했는데, R2에서는 이 키가 변형·과제 폴더 사이에 겹친다(사전 실행 12개에서는 겹치지 않아 못 잡음). 고침: 동일성을 표본 id(`sr0_eval`이 쓰는 `id` — R2 = `r2_ma2.sample_id`, S-E2E = 키 그대로)로 바꿨다(5절 '키 중복 없음'·'두 시드의 키 순서 같음'은 'id'로 읽는다). 지표·문턱·규칙 무변경. 시험 `test_load_checks_count_duplicates_and_conditions`에 "키는 같고 id는 다른 두 표본은 받아들임"을 더함(고치기 전 실패 확인 → 고친 뒤 22 통과). 새 해시: `tools/sr0/sr0_verdict.py` `0948399fb1d17124`, `tests/test_sr0_verdict.py` `bd12a7b45e3d644a`. 평가 출력(`sr0_*.jsonl`)은 그대로 두고 판정만 이 커밋의 사본으로 다시 돈다.
