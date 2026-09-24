# R7 객관 검증 전 알려진 열린 문제 수정 (pre-R7 fixes)

- 계획: `docs/superpowers/plans/2026-09-25-e2e-ready.md`(R7 순회 전). 근거 정본: `00-interfaces.md` §45(E-M8c), §58–§65. 대상 열린 문제: `r4_stageB.md` §8, `r5_closed_loop.md` §6(7번), `r6_eval.md` §5(1·6·7번), `e_m4b_meas.md` §7·§11(측정원 반영).
- 실행: 2026-09-25(파드 `p-test2/juhyoung-native-7a2a`, 파드 시계는 하루 뒤진 2026-09-24 22:0x–22:5x UTC로 찍힘 — 이전 문서들과 같은 시계 차). 코드 파드 사본 `/data/harvest/code_pre_r7`(작업용), `code_pre_r7_run`·`code_pre_r7_run2`(긴 실행용 고정 사본, `tools/pre_r7/sync.sh DEST=...`). 산출물 `/data/harvest/out/pre_r7/`. **git 커밋 안 함.**
- GPU: Isaac = **GPU 1**(동시 ≤ 3 프로세스), 학습·융합 모델 서버 = **GPU 2**(렌더 없음), GPU 3 안 씀, **GPU 0은 건드리지 않음**(라벨러·데이터 생성 작업이 사용 중). 다른 에이전트 프로세스·파드는 건드리지 않았다.
- 시드: **DEV만**(0–9). CAL·TEST·TEST-P5는 만들지도 열지도 않았다(`splits.check_seeds`·`aiworker.check_layout_seed` 보호 그대로). 풀 `oracle` 필드는 정답으로 쓰지 않았다(작은 체크포인트의 결정 정답 = labels_v2, 확인 헤드 정답 = 특권 술어 `pool_truth`).
- **§56 규칙**: 아래 수치는 모두 "끝까지 도는지" 확인용 소규모 판이다. 성공률·지연·손실을 결과로 인용하지 않는다(작은 체크포인트는 20스텝·합성 행동).

## 요약

| # | 대상 | 결과 | 증거 |
|---|---|---|---|
| 1 | FusedModel 실체크포인트 어댑터 (R5 7 / R6 1) | **해결**: `runtime/fused_model.py` — 단계 B 체크포인트(LoRA + expert + aux + **확인 헤드**)를 모델 프로세스(GPU 2)가 올리고, `decide`(공유 접두 순전파 → 결정 토큰 확률 + 확인 헤드 로짓) · `chunk`(CUDA 그래프 expert)를 HTTP로 내준다. `python -m harvest.eval.closed --backend fused --model <ckpt>`로 DEV 한 판 끝까지 돈다 | 작은 체크포인트(GPU 2, 20스텝) → 벤치(결정 p50 104 ms, 확인 헤드 0.69 ms, 청크 그래프 30.0 ms, 그래프=eager 0.0, fp32 결정 확률 = 전체 행 경로 1.7e-5) → Isaac 폐루프 3판(호출 오류 0) |
| 2 | M4 `measure()` 출처 표 + M7 critic (§61·§64) | **해결**: `runtime/measure.py` + 런타임 연결. 세계 = V1h(온도 + conformal, 빈 집합·둘 다 = unknown, 소프트), 로봇 T1 = 고유 감각 코드(하드), critic 경보 = V1h 단독(지속 2), T1 하드 채널 별도. 옛 `holds()`(특권 술어) 경로를 실행기·(b)·Astra 요약에서 뺐다 | 단위 시험 12 + 런타임 시험 3, DEV 0–9 판에서 T1 거짓 CONTRADICT 0 |
| 3 | 모의 선택기 DEV 시드 1 집기 실패 (R6 6) | **해결(근본 원인)**: 그리퍼 적용 토크가 한 틱(10 ms) ~20 → 0.02 N·m로 떨어지는 순간 `holding` = 거짓 한 샘플에 스킬이 "놓침"으로 다시 열었다. 계획기에는 있던 쥠 디바운스(0.15 s)가 스킬 S에 없었다 → 추가 | 재현(40 s 실패, 놓침 3회) → 추적 로그 → 수정 뒤 시드 1 성공(16.25 s) → **DEV 0–9 P0 모의 10/10 성공** |
| 4 | E-M8c K1·K3·K4 훅 (R5 1 / R6 7) | **해결**: `runtime/astra_hb.py` 호출 주기 모드 K0–K4 + `closed --hb-mode/--hb-budget/--astra scripted` | 단위 시험 10(모의 Astra, 유료 호출 없음), Isaac 판 K0–K4, 실 API 저노력 1회(`run_instruction`, 첫 토큰 1.88 s) |

## 1. FusedModel 어댑터 (실 단계 B 체크포인트)

### 1.1 구조
- **체크포인트 형식**(`train/stageb_train.py` 산출): `adapter/`(PEFT LoRA) + `heads.pt`(`expert.*`, `aux.*`, **`verify.*` 새로 추가**) + `stageb.json`(구성·정규화·어휘·`prompt_config`, 새 `verify` 항목 = 헤드 구성 + 술어 목록).
- **확인 헤드(§61·§64 "단계 B 학습에 확인 헤드 손실 포함")**: `stageb_model.StageB.verify` = V1h 구조(`m4b.vhead.make_head`: 질의 4·폭 512·헤드 8)에 E-M4b 시험 술어 9개(`stageb_data.VERIFY_PREDS` = `m4b.spec.PREDS`) 로짓. 손실 = BCE(`verify.truth`, None 가림) × λ_ver(기본 0.1, `--lam-ver`). 보조 헤드처럼 **기울기가 백본으로 흐른다**(같은 백본이 세계를 보게). KI(expert → 백본 0)는 그대로(시험 갱신: 전체 손실의 백본 기울기 = 결정 + 0.5·보조 + 0.1·확인).
- **런타임 두 경로를 한 순전파로(R5 §5 "2순위")**: `decide` = R3 공유 접두 순전파(`prefix_share.samples_forward`) — 문맥 프롬프트(system → 머리 → 활성 손목 → IMG 상태, §59)와 결정 질문 5개가 접두 하나를 공유 → 보기 트라이 재정규화 확률(학습이 읽은 양) + 문맥 은닉 상태 → 확인 헤드 로짓. 문맥은 캐시한다. `chunk` = 가장 새 캐시 문맥(≤ 0.7 s, 아니면 문맥만 새로 순전파)에 확정 결정(보기 **이름** = 결정 토큰; M4는 보기 키로 확정하므로 키→이름 사상)·고유감각·스킬·단계를 조건으로 expert 10 스텝을 **CUDA 그래프로 재생**(`fused_action.GraphedSampler`).
- **프로세스**: Isaac 작업자는 GPU 1에서 렌더하므로 모델은 따로 모델 GPU(2 또는 3)의 프로세스(`python -m harvest.runtime.fused_model serve`, venv_train, 표준 라이브러리 HTTP 서버)에 둔다 — 모듈형 스택의 vLLM 서버와 같은 배치. 런타임 쪽은 `FusedClient`(같은 `decide`/`chunk` 인터페이스). `eval/common.Server`가 단계 B 체크포인트면 이 서버를 띄운다(`--gpu`, GPU 1은 거부 그대로).
- **입력 일치**: 런타임은 체크포인트의 `prompt_config`를 확인한다(카메라 배치 `D27v1:head camera:|right wrist camera (active arm):`, 상태 IMG, system 해시, 프롬프트 파일 해시; 어긋나면 거부). 융합 경로의 DecCall 상태 = `image_only_state(S0)`(좌표·술어 줄 없음, §58), 문맥 = 같은 문자열 `canonicalize` — 학습 `load_stageb`와 같은 함수. 프레임은 풀 이미지와 같은 JPEG q90.
- **고유감각 23-D ← aiworker 8-D**: q = joint_pos[:7], qd = 직전 제어 틱과의 차분, tau = 관측 없음 → **학습 평균(정규화 0, 평균 대치)**, grip = [패드 간격, 그 차분 속도]. 청크 메타에 기록.
- **GPU 줄 세우기**: 결정과 청크가 한 GPU를 번갈아 쓰므로 한 번에 한 작업. 첫 판에서 선착순이면 청크가 겹친 결정 뒤에서 p50 553 ms 기다렸다 → **기다리는 청크를 먼저**(청크는 스텝 시작 전에 도착해야 함) 규칙으로 바꿨다(시험 `test_gpu_gate_serves_a_waiting_chunk_before_waiting_decides`).
- `closed`의 오래된 거부("R5 open item 7")를 없앴다: `--backend fused --model <stage-B ckpt>`, `--verify-cal <파일>`. `run_r5`에도 `--selector stageb --url`.

### 1.2 작은 체크포인트 (GPU 2, `/data/harvest/out/pre_r7/fused/ckpt/tiny_pool_syn/last`)
- 데이터: 풀 스냅샷 3,361개(fit·eval 120편)에 대해 `harvest/train/stageb_poolrows.py`가 **합성 행동** 행을 만들었다(풀에 30 Hz 행동 흐름이 없음 → 스냅샷의 8-D 명령을 H = 15 스텝 유지; 고유감각은 풀 npz의 q·qd·`joint_effort_target`, 보조 기하는 `datagen.rows.aux_row`, 확인 헤드 정답은 특권 술어 `m4b.data.pool_truth`; `synthetic_actions: true` 표시, 풀 폴더 밖에 저장). 결정 정답 = labels_v2(풀 `oracle` 아님).
- 학습: Qwen3-VL-4B BF16 + LoRA r32 + expert 기본 크기(79.45 M) + 보조 + 확인 헤드, 학습 표본 200개(fit에서 무작위), 배치 2, **20스텝**, lr LoRA 1e-4 / 헤드 5e-4, λ = 결정 1·행동 1·보조 0.1·확인 0.1, KI stop, 12 s. prompt_config sha `f8cd5dbacf52`.
- 검증(val 4표본): 결정 NLL 4.89 → 0.83(정확도 0.4 → 0.8), fm 2.53 → 2.41, 보조 2.80 → 2.33; 학습 확인 손실 0.693 → 0.579. **파이프라인 확인일 뿐**(합성 행동이라 행동 품질은 의미 없음).

### 1.3 모델 프로세스 벤치 (GPU 2 H200, 풀 스냅샷 25개, `fused_model bench`)

| 측정 (BF16) | p50 | p95 |
|---|---|---|
| decide = 공유 접두 순전파(문맥 + 질문 5개, 이미지 2장, 문맥 485토큰) | 104 ms | 147 ms |
| 확인 헤드 추가분 | 0.69 ms | 0.79 ms |
| chunk expert 10 스텝, **CUDA 그래프** (조건 인코딩·잡음 포함) | 30.0 ms | 30.1 ms |
| chunk expert 10 스텝, eager | 36.9 ms | 42.8 ms |

- 그래프 대 eager 출력 최대 차 **0.0**.
- decide 확률 대 학습의 옛 전체 행 경로(`stagea_loss.item_logprobs`, 질문마다 따로 순전파) 최대 차: BF16 0.029, **FP32 1.7e-5**(`bench --dtype float32`) → 차이는 BF16 수치 잡음이고 경로는 같다. 단계 B 학습 자체가 이 공유 접두 경로(`forward_shared`)로 손실을 내므로 학습 = 추론 경로.

### 1.4 폐루프 한 판 (DEV 0, P0, standard, C5, Isaac GPU 1 + 모델 GPU 2, Astra 모의)
명령: `python -m harvest.eval.closed --backend fused --model /data/harvest/out/pre_r7/fused/ckpt/tiny_pool_syn/last --out ... --split dev --seeds 0 --max-seconds 20 --astra mock --isaac-gpu 1 --gpu 2`

| 판 | 코드 | 종료 | 결정 호출 / 청크 | 호출 오류 | 결정 지연 전체 p50 / p95 | 그중 GPU 대기 p50 / p95 | decide 계산 p50 / p95 | 확인 헤드 p50 | 청크 전체 p50 / p95 | 청크 대기 p50 | expert(그래프) p50 | 늦은 청크 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `closed_fused_dev0` | 선착순 GPU | 12.25 s `off_table` | 35 / 37 | 0 / 0 | 498 / 2,188 ms | 119 / 1,705 ms | 255 / 528 ms | 0.7 ms | 591 / 1,713 ms | 553 ms | 30.1 ms | — |
| `closed_fused_dev0_v2` | 청크 먼저 | 4.28 s `off_table` | 11 / 13 | 0 / 0 | 415 / 1,388 ms | 2.5 / 622 ms | 376 / 882 ms | 0.8 ms | 80 / 851 ms | 6.5 ms | 34.4 ms | 3/13 |
| `closed_fused_dev0_final` | 최종 코드(Isaac 3개 동시) | 8.48 s `off_table` | 20 / 26 | 0 / 0 | 497 / 2,870 ms | 5.3 / 1,980 ms | 365 / 1,455 ms | 0.7 ms | 332 / 1,710 ms | 230 ms | 30.2 ms | 17/26 |

- 인터페이스 확인: 결정 확률 → M4 표·확정, 확정 결정 → 청크 → 100 Hz 재생(청크 결정 = 실행 결정일 때만), 확인 헤드 로짓 → `measure()`·critic(판마다 `verify_outputs` = 결정 호출 수, `t2_checked` 11–30), 로그(§42 부가 JSONL `call.verify`·`call.critic`·`chunk.meta`·`measure`) 모두 돈다. 성공은 요구 사항이 아니다 — 20스텝 합성 행동 모델이 머그를 쳐서 탁상 밖으로 떨어뜨렸다(`off_table`).
- **지연 해석(판정 밖)**: 벤치(단독)의 decide 104 ms가 폐루프에서는 255–376 ms로 늘었다. decide 안의 이미지 전처리·토크나이즈는 CPU 일이고 같은 파드의 Isaac(CPU PhysX)·라벨러와 CPU를 나눈다(판 v2는 Isaac 3개가 동시에 돌 때). 이 상태로는 T_c = 0.33 s에 결정 3 Hz + 청크 3 Hz를 한 GPU 프로세스가 감당하기 빠듯하다 — §1.6 남은 문제.

### 1.5 최종 코드 판
- `closed_fused_dev0_final`(코드 사본 `code_pre_r7_run2`, 이 문서의 최종 코드): 끝까지 돎, 호출 오류 0, 확인 헤드 출력 20회 → 세계 쪽 검사 18회(만료 6), T1 CONTRADICT 0, (b) 결과 OK 17·LAG 1·DEVIATE 7(합성 행동 모델의 관절 추종 잔차), Astra K2 하트비트 1회. 다른 Isaac 판 2개와 동시에 돌아 CPU 경합이 가장 컸던 판이라 청크 대기가 다시 늘었다(p50 230 ms, 늦은 청크 17/26) — §1.6-1.

### 1.6 남은 문제 (FusedModel)
1. **동시 부하 지연**: 폐루프에서 decide 계산 p50 255–376 ms(단독 104 ms), 청크 일부가 스텝 시작 뒤 도착. 이미지 전처리를 요청 스레드로 빼거나(GPU 잠금 밖), 결정은 vLLM(R5 1순위)·청크는 HF로 나누거나, 실물 서버(RTX PRO 6000, §49)에서 같은 조건으로 다시 잰다. 지금 코드는 decide·chunk의 대기/계산/헤드 시간을 호출마다 기록한다.
2. **확인 헤드 보정 없음**: 작은 체크포인트의 확인 헤드는 온도·conformal·critic 문턱이 없다(`VerifyCal.default()`: T = 1, argmax 단일 집합, 문턱 없음 → critic 경보 없음, 로그에 `verify_calibrated: false`). 실제 단계 B 체크포인트가 나오면 FI-DEV 보정 시드 0–14로 맞춘 `verify-cal-v1` 파일을 `--verify-cal`로 준다(형식·불러오기·E-M4b 결과 가져오기 `VerifyCal.from_m4b_results`는 구현·시험됨; E-M4b의 V1h 값은 단계 A 동결 백본 헤드 것이라 이 체크포인트에 쓰면 안 된다).
3. **tau 평균 대치**: aiworker 관측에 관절 토크가 없다. 풀 행의 tau는 `joint_effort_target`(= 0)이라 학습 평균도 0. R2 행(측정 토크)으로 학습하면 런타임에도 토크를 넣어야 한다 — 몸체 `extra`에 `applied_torque`를 싣는 것이 다음 일.
4. 잔차 모드 체크포인트는 스크립트 청크가 런타임에 필요해서 거부한다(절대 모드만).

## 2. M4 `measure()` 출처 표 + M7 critic (§61·§64)

- `harvest/runtime/measure.py`(순수 numpy):
  - `SOURCE_TABLE`: `gripper_open`·`holding_t`·`lifted_holding` = (proprio, **T1**) / `on_tp`·`contact_tp`·`lifted_t`·`near_tp`·`above_tp`·`contact_stall` = (v1h, **T2**). `contact_stall`은 PC2 목록 밖이라 T2(§64).
  - `ProprioRules`: E-M4b 등록 문턱 그대로(`results.json m4b.P_params`: 열림 폭 ≥ 80.5 mm, 쥠 = 50.1 < 폭 < 80 mm ∧ |그리퍼 effort| ≥ 1.136, 쥔 채 들림 = 쥠 ∧ TCP z(탁상 기준, FK) ≥ 12.4 cm). `from_m4b_results`로 파일에서 다시 읽을 수 있다.
  - `VerifyCal`(verify-cal-v1): 술어별 온도·conformal q̂·critic 문턱·지속 2. `conformal_value`: {참}/{거짓}이면 값, **둘 다·빈 집합이면 `unknown`(§64 결정)**. 로봇 쪽 술어는 헤드에서 읽지 않는다(T1 = 코드).
  - `expected_check(phase, meas)`: 단계 기대표(`m4b.spec.EXPECT`)로 T1 거짓 → CONTRADICT(하드), T2 {거짓} → DEVIATE(소프트, C_m4), unknown → 판정 없음; OR 항목·범위 밖 술어 처리.
  - `Critic`: **V1h 단독** 9술어 위반 확률(= `m4b.analyze.viol_prob`), 지속 2 스냅샷 최소값 > 문턱이면 경보. `HardChannel`: T1 위반 2회 연속 → 하드 사건(경보 합산과 분리, PC3 결정).
- **런타임 연결(`core.py`)**:
  - 매 틱 T1 측정(패드 간격 = joint_pos[7], |그리퍼 effort|, TCP 높이 = FK − 탁상) + 가장 새 확인 헤드 출력(≤ 2 s)으로 `measure()`.
  - **옛 `holds()` 경로 교체**: 실행기(스킬 S)가 읽는 `gripper_open`·`holding(o3)`·`lifted(o3)`(= 쥔 채 들림 T1)·`in_contact(o3,o5)`·`on(o3,o5)`(V1h, 없으면 None → 스킬은 기하 `reached`로 대체)를 측정값으로 바꿨다. Astra 요약의 사실 줄도 측정값. 모듈형 스택의 DecCall 상태 문자열(M1 관측 = E0 오라클 조건)은 그대로.
  - (b)(2): 스텝이 한 단계 안에서 끝나면 스텝 끝에 T1 검사 → CONTRADICT, 그 스텝의 세계 쪽 검사는 **스텝 끝 뒤 첫 확인 헤드 출력**으로(D28 §3.1) → {거짓}이면 그 스텝에 DEVIATE(epoch+1, 조기 호출). 스텝 안에서 단계가 바뀐 스텝은 검사하지 않는다(전이는 실패가 아님, E-M4b §3의 1스냅샷 전이 위반과 같은 이유).
  - M7: critic 경보·T1 하드 사건 → 사건 기록 + Astra 호출 앞당김(FAIL → M8 T_fail 대신; M9 복구는 아직 없음, R5 열린 문제 2 그대로).
  - 요약 `measure`: t1_contradict·t2_deviate·t2_checked·t2_expired·critic_alarms·hard_events·verify_outputs·보정 여부.
- 시험: `tests/runtime/test_measure.py`(12: 출처 표, 등록 문턱, conformal unknown, 온도, 기대표 판정, T1만·T2만 범위, critic 지속, 문턱 없음, 하드 2틱, 보정 파일 왕복·E-M4b 가져오기, 기본값 표시), `tests/runtime/test_fused_model.py`의 런타임 시험 3(정직한 헤드 = DEVIATE·경보 0으로 과제 완주, 거짓 `lifted_t` 헤드 = 소프트 DEVIATE + critic 경보 + T1 CONTRADICT 0, 실행기가 오라클이 아니라 T1 규칙을 읽음). 가짜 세계는 쥔 동안 패드 간격을 머그 지름(64 mm)으로 보고하게 고쳤다(명령 폭 50 mm를 그대로 돌려주면 T1 쥠 규칙이 물리적으로 불가능한 값을 본다).
- DEV 0–9 모의 판(§3): T1 CONTRADICT 0, 하드 사건 0(명목에서 T1 거짓 경보 없음 — E-M4b PC2와 같은 모양).

## 3. 모의 선택기 DEV 시드 1 집기 실패 (R6 열린 문제 6) — 체계적 디버깅

1. **재현**(`mock_s1_repro`, 수정 전 코드, 40 s): 실패. 닫기 5.61 → 들기 6.21 → **7.21 `object_lost`** → 재접근 → 12.81 들기 → 13.39 놓침 → 16.44 → 17.09 놓침 → 재시도 한도(2) 초과로 descend에서 끝까지 멈춤(`max_steps`). 프레임 `pre_r7_s1_repro_frames.jpg`(머그가 계속 탁상에 남음).
2. **증거 수집 1**(`mock_s1_diag`/`mock_s0_diag`, 스텝 로그에 손가락 중점 g·머그 중심·폭 추가): 닫기 직전 TCP–머그 수평 오차 ≤ 1 mm(두 시드 모두 정렬 좋음). 닫는 순간 팔이 +x 11–25 mm, +z 15–23 mm 밀린다(두 시드 공통, 계획기 기록 `grasp_rel_mm` −10.9 mm와 같은 크기). 시드 0은 이 밀림이 DEVIATE(> 40 mm)가 되어 기준을 다시 세웠고, 시드 1은 LAG 구간(21.7 mm)이라 명령이 옛 점에 남았다.
3. **가설 1(기각)**: "닫기 뒤 옛 명령점으로 당기는 힘이 쥔 머그를 끌어낸다" → 쥠 확정 때 기준을 측정 TCP로 다시 세우는 수정(시험 포함)을 넣고 시드 1을 돌렸으나(`mock_s1_fix1`) **여전히 7.02 s에 놓침** → 원인이 아님. 수정과 시험을 되돌렸다(덧대지 않음).
4. **증거 수집 2**(`mock_s1_trace`, 놓침 사건에 직전 0.4 s의 그리퍼 신호 추적 첨부 — 영구 진단으로 남김): 놓침 순간 폭 75.7 mm·손가락 접촉 **켜짐** 그대로인데 **그리퍼 적용 토크만 한 틱에 20.8 → 0.015 N·m**(두 번째 놓침: 21.1 → 0.75)로 떨어졌다. `holding` = 접촉 ∧ 폭 < 80 mm ∧ effort ≥ 1.0(또는 T1 1.136) 이 한 샘플만 거짓 → 스킬이 즉시 "빈 집기"로 보고 그리퍼를 열어 머그를 떨어뜨렸다.
5. **근본 원인**: 스킬 S는 100 Hz 한 샘플의 `holding` 거짓에 바로 반응한다. 같은 판정을 쓰는 오라클 계획기는 `HOLD_DEBOUNCE = 3 제어 스텝(20 Hz) = 0.15 s`(데이터 생성기도 30 Hz 5틱)로 디바운스한다 — 스킬로 옮길 때 빠졌다. 시드 1은 폭이 넓게 잡혀(75–80 mm) 적용 토크가 순간적으로 0 근처로 튀는 판이다.
6. **수정**(`skills.py`, 계획기와 같은 규칙): `holding`이 마지막으로 참이었던 뒤 0.15 s 안의 거짓은 쥠으로 본다(`HOLD_DEBOUNCE_S = 0.15`). 시험 `test_one_tick_holding_dropout_is_not_an_object_loss`(한 틱 끊김은 놓침 아님, 0.2 s 끊김은 여전히 놓침) — 수정 전 실패 확인 후 통과. 시험 시드로 문턱을 맞추지 않았다(계획기 값 그대로).
7. **검증**: 시드 1 `mock_s1_fix2` **성공 16.25 s**(놓침 0, 프레임 `pre_r7_s1_fixed_frames.jpg`: 운반 중 머그 들림, 열기·후퇴에서 머그가 파란 트레이 위). **DEV 0–9 P0 모의 선택기 `closed` 한 명령: 10/10 성공**(`closed_mock_dev0_9`, 성공 시각 13.9–16.6 s, 중앙 15.4 s, 재시도 0, 호출 461·오류 0, RTF 중앙 0.86). 최종 코드로 다시 돈 판은 §8.

## 4. E-M8c 훅 K1·K3·K4 (§45)

- `runtime/astra_hb.py` `HeartbeatScheduler(mode=K0..K4)` — 모든 모드에서 Astra 호출은 한 번에 하나(Gemini "cancellation loop" 경고), 15 s 무응답이면 기록 후 재송신:
  - **K0**: 사건 호출만(T_fail = 놓침/빈 집기, J5 상위 호출, M7 critic 경보·T1 하드 사건, (b) CONTRADICT가 다음 호출을 앞당김). 주기·경계 없음.
  - **K1 (단계 경계 확인)**: K0 + T_sub — 계약 단계가 끝나면(스킬 S1 → S2, done; 놓쳐서 S1로 돌아가는 것은 T_fail이지 경계가 아님) "다음 단계 계약이 지금 장면에도 맞나"를 비동기로 묻는다(`TSUB_TEMPLATE`, ack/patch/replace). 다음 단계는 기다리지 않는다. 호출 중이면 대기열에 두었다가 응답 뒤 보낸다.
  - **K2**: K1 + 직전 응답 N s 뒤 하트비트(§45 결정, 런타임 기본; `--hb-n` 격자 = K2-N).
  - **K3 (Gemini 하트비트 원문 충실판)**: 기회적 1 Hz — 다음 송신 = max(직전 송신 + 1 s, 직전 응답 도착), 즉 **앞 턴이 끝나기를 기다림**. 프롬프트(`GEMINI_TEMPLATE`)는 최신 프레임 + 짧은 지시로 명시적 결정 `ack`(진행 중) / `run_instruction`(단계 완료 → 다음 단계) / `reset`(목표 달성). 이 모드에서는 **단계 전환을 Astra가 정한다**(스킬의 S1→S2·done 자체 전환 끔, `stage_gate = astra`) — 단, 코드 안전 술어가 참일 때만 적용(S1→S2 = 쥠 ∧ 쥔 채 들림, reset = S2·그리퍼 열림·후퇴 중), 아니면 `rejected` 기록.
  - **K4 (호출 수 맞춘 사건 전용 대조)**: K1의 촉발만, 에피소드당 호출 예산 `--hb-budget`(맞출 K2-N 칸의 평균 호출 수를 넣는다).
- `closed`: `--hb-mode K0,..,K4`(목록이면 격자, 라벨 `C5|K3`, K2일 때만 N 격자), `--hb-budget`(K4 필수, K4에만 적용), `--astra scripted`(키 없이 K3를 돌리는 텍스트 요약 성공 판정 모의 `ScriptedAstra`). `run_r5`도 같은 인자. 로그: Astra 행에 `kind`(hb/sub)·`cadence`·`prompt_id`·`applied`, 요약에 `hb_mode`·`astra_budget`·`astra_by_kind`, 사건 `t_sub`·`astra_gemini`.
- 시험(모의 Astra, **유료 호출 없음**): `tests/runtime/test_astra_cadence.py`(10: 스케줄러 K0–K4, 프롬프트·파싱, 가짜 세계 K1 경계 호출·K0/K2·K3 1 Hz + run_instruction 안전 적용·K4 예산), `tests/eval/test_closed_pure.py`(+2: 라벨 격자, 플래그 검사). 기존 `test_astra_hb.py` 5개 그대로 통과.
- Isaac 판(`closed_cadence_dev0`, DEV 0, 모의 선택기, `--astra scripted`): 첫 판에서 **`--hb-budget`이 K4 밖 모드에도 걸리는 배선 오류**를 찾았다(K3가 2회 호출 뒤 멈춰 단계 전환을 못 받고 `max_steps`) → K4에만 적용하도록 고침 → 다시 돈 판은 §8.
- **실 API 저노력 1회**(`tools/pre_r7/astra_k3_smoke.py`, 키는 파드 `/data/.openai_token`을 프로세스가 직접 읽음, 복사·출력 없음): K3 프롬프트 + 풀 머리 프레임(ep2000 k12, 들기 중) → `{"decision":"run_instruction","note":"The red mug is grasped and lifted. Move it over the blue tray."}`, HTTP 200, 첫 토큰 1.88 s, 전체 2.57 s, 입력 495 + 출력 29 토큰(`/data/harvest/out/pre_r7/astra_k3_smoke.json`). 한 번뿐이라 지연은 결과가 아니다.

## 5. 시험

- 로컬 `cd D:/qdd && python -m pytest -q`: **768 passed, 11 skipped**(torch 없는 기본 파이썬; pytest 임시 폴더 = `pytest.ini`의 `D:/tools/scratch_qdd/pytest_tmp`). 새·바뀐 시험: `tests/runtime/test_measure.py`(새 12), `test_fused_model.py`(새 7), `test_astra_cadence.py`(새 10), `test_skills.py`(+1 디바운스), `tests/eval/test_closed_pure.py`(+2), `tests/train/test_stageb_poolrows.py`(새 1), `tests/train/test_stageb_torch.py`(확인 헤드 기울기·저장/재적재 + 술어 목록 일치 1), `tests/runtime/fakeworld.py`(쥔 동안 패드 간격 64 mm).
- 로컬 CPU torch 경로(`D:\tools\pylib_train`)로 `tests/train/test_stageb_torch.py`·`test_stageb_data.py` 통과. `tests/train` 전체를 로컬 torch로 돌리면 파이썬이 비정상 종료했다(로컬 메모리 부족으로 보임, 확인 못 함) → 같은 모음을 파드에서 돌렸다.
- 파드(`venv_train`, CPU, IR PYTHONPATH): `tests/train tests/runtime tests/eval tests/m4b` **271 passed, 2 skipped**(최종 코드, 실제 Qwen3-VL 구조 시험 포함).

## 6. 남은 문제 (R7에 넘김)
1. FusedModel 폐루프 동시 부하 지연(§1.6-1), 확인 헤드 보정 파일 없음(§1.6-2), 토크 입력(§1.6-3). 실제 단계 B 학습(R2 행, 30 Hz 행동)은 이 작업 범위 밖.
2. M7 FAIL → M9 복구·M8 T_fail 일시정지(복구 끝 + 2 s)는 여전히 없다: critic 경보·하드 사건은 기록 + Astra 앞당김만 한다. T2 연속 2회 {거짓} → CONTRADICT-soft(D28)도 넣지 않았다(단일 DEVIATE).
3. 모듈형 스택(Jev-L·모의)에는 확인 헤드 출력이 없어 세계 쪽이 항상 `unknown`이다 — 단계 A 병합 모델 + E-M4b V1h 헤드(`/data/harvest/m4b/v1h/head_fold*.pt`)를 모듈형 경로의 측정원으로 붙이는 일은 하지 않았다(vLLM은 은닉 상태를 내주지 않음).
4. K3 `run_instruction`의 안전 술어는 이 과제(머그 → 트레이)의 S1/S2에 맞춘 것이다. 계약 편집(patch/replace의 A5′·M2 R3)은 여전히 epoch만 올린다(R5 열린 문제 1의 나머지).
5. `closed`를 동시에 여러 개 돌릴 때 Isaac 인스턴스 이름이 같으면(`r6_standard`) 캐시 폴더를 나눠 쓴다 → `--inst-prefix` 추가(이번 동시 판들은 서로 다른 접두로 돌렸다; 첫 동시 판 두 개는 같은 이름이었으나 둘 다 정상 종료).
6. 모의 판은 오라클 M1 좌표(E0 조건)를 쓰므로 DEV 0–9 10/10은 실행기·런타임 배관 확인이지 결정층 성능이 아니다(§56).

## 7. 파일

- 새: `harvest/runtime/measure.py`, `harvest/runtime/fused_model.py`, `harvest/train/stageb_poolrows.py`, `tests/runtime/test_measure.py`, `tests/runtime/test_fused_model.py`, `tests/runtime/test_astra_cadence.py`, `tests/train/test_stageb_poolrows.py`, `tools/pre_r7/{sync.sh,run_episode.sh,astra_k3_smoke.py,sheet.py}`, 이 문서, 프레임 `pre_r7_s1_repro_frames.jpg`·`pre_r7_s1_fixed_frames.jpg`.
- 수정: `harvest/runtime/{core,skills,astra_hb,models,ir_policy,run_r5}.py`, `harvest/eval/{closed,common}.py`, `harvest/train/{stageb_data,stageb_model,stageb_train}.py`, `tests/runtime/{test_skills,fakeworld}.py`, `tests/train/test_stageb_torch.py`, `tests/eval/test_closed_pure.py`.
- 파드 산출(전부 `/data/harvest` 아래): `out/pre_r7/`(판 폴더, 합성 행 `fused/pool_syn.stageb.jsonl`, 체크포인트 `fused/ckpt/tiny_pool_syn/last`, 벤치 `fused/bench.json`·`bench_fp32.json`, Astra 1회 기록), 코드 사본 `code_pre_r7`·`code_pre_r7_run`·`code_pre_r7_run2`, 임시 `tmp/fused_frames/<pid>`(호출마다 지움)·`tmp/pre_r7_pytest`, Isaac 캐시 `ir/kitcache/cyclo-{pr7a,pr7b,r6_standard,pr7final_standard,pr7fused_standard}`.
- **`/data` 밖에 쓴 것**: 파드 쪽 없음. 로컬은 D:만(저장소 파일 + 임시 `D:\tools\scratch_qdd\pre_r7`, pytest `D:\tools\scratch_qdd\pytest_tmp`). 유료 API = Astra low 1회(524 토큰).

## 8. 최종 코드 판 (실행 기록)

코드 사본 `/data/harvest/code_pre_r7_run2`(CODE_VERSION: 로컬 HEAD 7db76eeb + dirty 25, code_sha `5d35a99d556d91a8`). 모두 DEV P0 standard C5, Isaac GPU 1.

| 판 | 명령 요지 | 결과 |
|---|---|---|
| `closed_mock_dev0_9_final` | `closed --model mock --seeds 0-9 --max-seconds 40 --astra mock --inst-prefix pr7final` | **10/10 성공**, 성공 시각 13.94–16.63 s(중앙 15.42), 재시도 0, 결정 호출 461·오류 0, Astra 20회(K2 하트비트 + T_sub), M4 epoch 중앙 3.5, RTF 중앙 0.86, T1 CONTRADICT·하드 사건 0. 수정 직후 판(`closed_mock_dev0_9`, 오라클 대신 측정 술어·디바운스 포함, K 훅 전)과 시드별 성공 시각이 같다(실행기 결정성) |
| `closed_cadence_dev0_v2` | `closed --model mock --seeds 0 --hb-mode K0,K1,K2,K3,K4 --hb-budget 2 --astra scripted --max-seconds 30` | 5칸 모두 성공(16.1–17.5 s). Astra 호출: K0 0 / K1 1(`sub`) / K2 3(`hb` 2 + `sub` 1) / **K3 17(1 Hz, 최소 간격 1.01 s, 7.06 s에 `run_instruction` → 안전 술어 참 → 적용, S1→S2)** / K4 1(예산 2 안). 모든 모드에서 동시 호출 1개. K3 `reset`은 후퇴 중 환경 성공 종료가 먼저 와서 나오지 않았다 |
| `closed_fused_dev0_final` | `closed --backend fused --model .../tiny_pool_syn/last --seeds 0 --max-seconds 20 --gpu 2 --inst-prefix pr7fused` | §1.5 |

판 폴더: `/data/harvest/out/pre_r7/<판>/`(closed.json·closed.md·IR 로그·부가 JSONL·프레임), 디버깅 판 `mock_s1_{repro,diag,fix1,trace,fix2}`, `mock_s0_diag`, 앞선 판 `closed_mock_dev0_9`, `closed_fused_dev0{,_v2}`, `closed_cadence_dev0`(예산 배선 오류 판).
