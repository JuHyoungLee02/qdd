# R5 폐루프 런타임 (Inspect Robots `aiworker` P1 + `OursPolicy` P2)

- 계획: `docs/superpowers/plans/2026-09-25-e2e-ready.md` 관문 R5. 근거 정본: 00-interfaces §41–§42, §45, §46, §53–§59, M4 §4, M6, D23, `p0_inspect_robots.md`.
- 실행: 2026-09-25 (파드 `p-test2/juhyoung-native-7a2a`, 파드 시계 KST 03:20–04:20 무렵). Inspect Robots v0.59.0 / `7e506e3` (`/data/harvest/ir/src`), Isaac = `ir_run.sh IR_ROOT=cyclo`, **Isaac GPU 1**(프로세스 ≤ 2), **vLLM GPU 3**(비었을 때만), GPU 0·2 안 씀. 시드 = DEV 0만, P0, standard. git 커밋 안 함.
- 코드 파드 사본: `/data/harvest/code_r5cl/`(공용 `/data/harvest/code`는 다른 작업이 쓰므로 건드리지 않음). 산출물: `/data/harvest/out/r5/<태그>/`.

## 1. 결론

| 판 | 결정층 | 결과 | 시뮬 시각 | 결정 호출 | 결정/시뮬 s | 지연 p50 / p95 / 최대 | 확정 비율 | Astra |
|---|---|---|---|---|---|---|---|---|
| `sft_h2` | **단계 A SFT 병합**(`sftA_pool_v1/merged`), 배치 H(학습 형식) | **성공**(종료 사유 `success`) | 16.8 s | 51, 오류 0 | 3.04 | 0.198 / 0.293 / 0.322 s | 0.80 | API 2회(patch 1, ack 1) |
| `zs_hw` | 영점 Qwen3-VL-4B, 배치 HW(§59) | 실패(60 s 시간 초과, 접근 단계에서 정지) | 60.0 s | 182, 오류 0 | 3.03 | 0.150 / 0.314 / 1.98 s | 0.97 | API 7회(전부 ack) |
| `mock_det1`·`mock_det2` | 결정적 모의 선택기(labels_v2 S1 코드 규칙, 지연 0.30 s 고정) | 성공 ×2 | 16.45 s | 55 | 3.0 | 0.30(고정) | 0.76 | 모의(ack) |
| `fused_mock2` | FusedModel 모의(결정 = 특권 코드 규칙, 청크 = 정지 유지) | 인터페이스·로그 확인용 6 s | 6.0 s | 18 + 청크 18 | 3.0 | 0.30 / 청크 0.12(고정) | 0.88 | 모의 |

- **R5 통과 조건 충족**: DEV 한 판이 Inspect Robots `eval()` 안에서 끝까지 돈다(모의·SFT 모두 성공, 영점은 끝까지 돌고 실패), 로그 스키마(§42) 확인, **결정성**: 같은 모의 판 두 번의 행동 1,646개가 비트 단위로 같다(최대 차 0.0) — RTF가 0.36 대 0.64로 달랐는데도 같다(simlat 전달이 벽시계 속도와 무관함을 뜻함).
- 영점 실패는 §53 판정과 같은 모양이다: 182회 모두 `dir_xy = plus_x_plus_y`, `dir_z = down`, `mag = medium`(머그는 −y 쪽) → 스킬 S의 부호 투영이 y축을 막아 팔이 머그 위에 선다. 런타임 결함이 아니라 결정 품질 문제다(호출 오류 0, 확정 0.97).
- **§56 규칙**: 위 수치는 파이프라인 확인용 1판 결과다. 성공률·지연을 논문 결과로 쓰지 않는다. 입력 좌표는 시뮬 참값(M1 = 오라클, E0 오라클 조건).
- RTF: 카메라 2대(머리 672×376 + 우손목 424×240, 33 Hz 렌더) + 100 Hz 제어 + CPU PhysX에서 0.36–0.64(GPU 1을 다른 작업과 공유). §42대로 시뮬은 simlat, wall 모드 안 씀.

## 2. 만든 것

### 2.1 `aiworker` 몸체 (P1) — `harvest/runtime/aiworker.py`
- v2 장면(`sim/scene.py make_env`, CPU PhysX, variant standard/random/dr)을 감싼다. 장면 코드는 두 인자만 추가(`decimation`, `render_interval`, 기본값은 기존 20 Hz 그대로).
- 행동: `joint_pos` 8-D(우팔 7관절 목표 rad + 그리퍼 패드 간격 목표 m), **유한 경계**(소프트 관절 한계, 0–0.107 m), `dim_labels`, `max_step`, `gripper="continuous"`. 몸체가 매 행동을 경계로 자른다. `check_embodiment()` 적합(P0의 부적합 3건 bounds·dim_labels·state_alignment 해소).
- 상태: `joint_pos (8,)` 하나(측정 관절 + 측정 패드 간격). 제어 100 Hz(`sim.dt 0.01`, decimation 1). 카메라는 렌더가 일어난 스텝(3 물리 스텝마다 = 33 Hz)에만 `images`에 넣는다.
- `extra`: `sim_time`, `m1`(시뮬 오라클 관측, 표 좌표계 — 우리 정책만 읽음, 기준선 agent는 state만 보므로 §42 정보 동등 유지), `kin`(시뮬 운동학 서비스: 계획기의 TCP 자세와 DLS IK + 중력 처짐 보정; 실물에서는 URDF IK로 대체), `depth`·`intrinsics`는 **callable**, `table_z`, `rtf`.
- 성공 술어: `planner.success_from_history`(on(o3,o5) ∧ ¬holding ∧ upright 1 s 연속) → `terminated, "success"`; 머그 바닥 아래 → `"off_table"`. `self_paced` 기본 끔(simlat). DEV 시드(0–29)만 허용.

### 2.2 `OursPolicy` (P2) — `harvest/runtime/core.py`(하네스 중립) + `ir_policy.py`(얇은 어댑터)
- `act()` 비블로킹, 청크 길이 1(`DefaultController(replan_interval=1)`), `policy.config = RuntimeConfig`(→ `EvalSpec.policy_config`).
- 한 틱 순서: M1 관측 → 호출 예약 → 시계에 따른 응답 전달(표 → M4 원장, 앞쪽부터 확정) → 결정 스텝 경계((b) 확인, M4 신호, 새 스텝 결정) → 실행기.
- **(a) 결정 호출**(`models.py`): T_c = 0.33 s 계단식, 동시 in-flight ≤ N_max = ⌈d̂/T_c⌉+1, 조기 호출은 주기 슬롯 하나를 당겨 씀(호출 예산 고정, M4 §4.3). 한 호출의 답은 `t_start ≥ t_send + d̂`인 첫 스텝부터 H = 3개 스텝의 표가 된다(표마다 t_state가 달라 J3 합의 표 조건 충족).
  - `JevLSelector`: Jev-L DecCall(`clients/jevl.py`에 `acall_mm` 추가 — §59 다중 이미지 배치 H/HW, 호출 방식 **lead**: 트라이 첫 시퀀스를 먼저 보내 캐시를 채운 뒤 나머지 병렬). 입력 = 라이브 상태로 만든 풀 형식 줄 → `deccall_snap.build_snapshot_request` + E3-lite S1 1 mm(§54), 질문 5개(dir_xy·dir_z·mag_coarse·target·phase). 프레임은 JPEG q90(풀 학습 이미지와 같은 부호화). vLLM은 접두 캐시 + 멀티모달 캐시 켬(`tools/r5/serve.sh`).
  - `MockSelector`: labels_v2 S1 코드 규칙 + 고정 지연(결정적).
- **(b) M4 겹침 확정**(`m4.py`, M4 §4.1–§4.2, §4.6 충실 최소판): 슬롯 = (스텝, 질문), option_key로 셈. premise epoch 낮은 표 폐기, STALE_MAX 1.5 s 폐기, 이미 시작한 스텝(FROZEN)·확정 스텝은 불변(log_only), 도전 선택은 유예 창 W(비가역 보기 W+1)를 지나야 교체, (b) ≠ OK가 현 선택 뒤에 오면 즉시 교체(gate_hard), 앞쪽부터만 확정(LA-2 또는 3표 이상 γ ≥ 0.67), 순서형 mag는 τ = 1 칸 허용([정정 R7 8회차, 정본 §73: 접촉 근처(목표 ≤ 5 cm 또는 접촉)는 τ = 0 — `core.near_contact`를 `on_vote`·`try_commit_prefix`에 넘김]), flip_score(TV 거리) 기록(FLIP_TH는 E0.5 전 끔), 확정 못 한 채 시작한 스텝은 가확정 실행 후 "unconfirmed-executed"로 셈. (b) 결과: OK/LAG/DEVIATE/CONTRADICT, DEVIATE·CONTRADICT → epoch+1 + 미래 미확정 슬롯 재개방 + 조기 호출, CONTRADICT는 직전 확정 행동 유지(정지 아님). 확률 게이트·J5는 E1 전이라 끔(§6).
- **(c) Astra 하트비트**(`astra_hb.py`, §45): 직전 응답 도착 N = 5 s 뒤 최신 머리캠 + 원장 요약으로 닫힌 선택 ack/patch/replace, in-flight 1개, 15 s 무응답이면 기록 후 재송신, 사건은 앞당김·T_fail은 멈춤(훅). `gpt-6-astra`, effort low. **키는 파드 `/data/.openai_token`이 있어 API로 돌렸다**(키를 복사하지 않고 프로세스가 직접 읽음). 없으면 모의(ack). ack는 epoch 불변, patch/replace는 epoch+1(계약 편집·A5′ 검사는 미구현, 기록만).
- **(d) 실행기 = 스크립트 스킬 S + 잔차 R 훅**(`skills.py`): 스킬이 매 틱 새 측정으로 자기 소단계 목표(labels_v2 기하)를 계산하고, 그 스텝의 확정 결정을 **구간 제한 투영**(§35)으로 지킨다 — 축마다 결정 부호와 같은 방향만, "none" 축은 1 cm 데드밴드 안만, mag 구간 위 경계로 스텝당 이동 상한, target이 소단계 물체와 다르면 정지 유지, phase `hold` → 유지, `next` + 코드 안전 술어 → 닫기/열기(비가역)·S1→S2. 결정 없음/NE → 직전 명령 유지(정지 아님). 잔차 R 훅은 근접·접촉 구간에서만 ±0.02 rad로 잘라 더함(지금은 0).
- **simlat 시계**(`clock.py`, §42): 시뮬 시각 t_s에 보낸 호출은 t_s + 실측 지연에 전달. 시뮬이 벽시계보다 앞설 때만 막음(모의는 고정 마감에서 막음 → 결정성). sync·wall 모드도 같은 코드.
- **FusedModel**(§58, 사용자 방향 조정 반영): 같은 M4 규칙을 공유. 결정 호출 `decide()` 뒤, **R4 stage-B expert가 확정 결정(`cond["dec"]`)을 입력으로 받으므로** 행동 청크는 스텝 k+1 시작 `chunk_lead` = 0.15 s 전에 그때의 확정 결정으로 `chunk(ctx, committed)`를 따로 부른다. 청크는 그 결정이 실제 실행 결정과 같을 때만 재생(30 Hz 청크를 100 Hz로 선형 보간), 아니면 유지. (b)는 실행한 청크 목표 대 측정 관절(0.05 / 0.15 rad). 입력 = 이미지(머리 + 활성 손목) + 과제 문장 + 계약 요약 + 고유감각(S1 좌표 없음). 지금은 모의 모델만(결정은 특권 코드 규칙이라 로그에 `privileged_decisions` 표시).
- **expert CUDA 그래프**(`fused_action.py GraphedSampler`, R4 요청): B = 1, 문맥을 고정 길이로 채우고 key-padding 마스크로 가림, 10 스텝 Euler 루프를 캡처·재생. 시험: 채움이 결과를 바꾸지 않음(CPU), GPU 3에서 그래프 재생 = eager(문맥 길이 17·40, 오차 ≤ 1e-4).
- `LatencyChargingController`(§42, 동기 기준선용): 스텁 + TODO 시험(건너뜀).

### 2.3 로그 (§42)
- `EvalSpec.policy_config`: backend, selector, model_id, model_path, layout(H/HW), call_mode(lead), clock(simlat), T_c, control_hz, M4 파라미터 전부, `question_ids`(5개 `question_id@vN`, 카메라 배치를 legend에 넣음 — §59), astra_model/effort/prompt_id(`86ea9d346eaf`)/mode, 하트비트 N·timeout, state_repr, residual_hook. `environment_id`/`environment_revision`(장면 코드 해시 `harvest-sim-…`), `policy_checkpoint`.
- `SceneResult.trial_metadata`: 부가 JSONL 경로, 표본 프레임 폴더, 요약(결정/초, 지연 분포, 확정 비율, 막힘 시간, Astra 집계, RTF). 부가 JSONL 행 종류: `call`(t_state·t_deliver·지연·표 대상 슬롯·보낸 epoch·질문별 option_key·p·표 처리 결과), `step`(스텝별 질문 결정·상태, 이전 스텝 (b) 결과·잔차 mm, TCP·명령), `astra`(결정·메모·지연·첫 토큰·사용량), `event`(스킬 단계 전환·재기준), `m4`(epoch 변경 사유), `chunk`(fused). 행동은 하네스가 `actions/<run>/<trial>.jsonl`에 따로 저장.

## 3. 시험 (TDD, 로컬 `cd D:/qdd && python -m pytest -q` 통과, 파드 사본에서도 통과)
- `tests/runtime/test_m4.py`(15): 목표 슬롯·H, 첫 표 가확정·LA2 확정, 앞쪽만 확정, 유예 창 W, 비가역 W+1, premise epoch·STALE 폐기, FROZEN log_only, γ 확정, 순서형 τ, DEVIATE/CONTRADICT 신호, gate_hard, 실행 계정(확정/가확정/빈), d̂·N_max, flip_score.
- `test_clock.py`(7): simlat 전달 시각, 고정 마감 막음, 시뮬이 앞설 때만 막음, sync·wall, 전달 순서.
- `test_skills.py`(10): 부호·데드밴드 투영, 속도, hold/결정 없음/target 불일치 정지, mag 상한, 닫기 = next + 도달, 헛잡기 → CONTRADICT, 단계 전환, (b) 문턱, 잡기 깊이 바닥, DEVIATE 뒤 재기준, R 훅 제한.
- `test_models.py`(4), `test_astra_hb.py`(5), `test_fused_action.py`(3, CUDA 1개는 파드 GPU 3), `test_latency_ctrl.py`(스텁 1 + TODO 1).
- `test_core_fakeworld.py`(4): Isaac 없는 운동학 가짜 세계에서 런타임 전체(모의 선택기 → simlat → M4 → S)로 집기–놓기 완주, 결정성, fused 인터페이스·청크 시각, fused (b).
- `test_ir_adapter.py`(3): 행동 경계 자르기, `aiworker` 정보 적합성(`check_embodiment`), **가짜 세계를 IR `eval()`에 넣어 `OursPolicy` 로그 스키마 확인**(inspect_robots 필요: 파드 PYTHONPATH, 로컬은 `INSPECT_ROBOTS_SRC`).
- `tests/test_jevl_client.py`에 다중 이미지 `acall_mm` 시험 1개 추가(배치 H = 단계 A 학습 프롬프트와 바이트까지 같음, HW 표지 순서, lead).

## 4. 판 기록과 발견 (시간순, 고친 것 포함)

| 판 | 코드 상태 | 결과 | 발견·조치 |
|---|---|---|---|
| `smoke_mock8`(8 s) | 첫판 | 끝까지 돔, RTF 0.55 | 종료 뒤 `SimulationApp` 닫기에서 프로세스가 멈춤 → 결과 쓴 뒤 `os._exit(0)`. 손가락 중점 목표로 내려가 그리퍼 몸체가 테두리에 걸림(잔차 8 mm) → 들기 중 놓침 |
| `mock_full1`(60 s) | 스킬 목표를 TCP(패드 중심)로 | 실패(내려가기에서 교착) | TCP는 계획기 잡기 높이에 도달했는데 결정(손가락 중점 기준)은 계속 `down small` → `next`가 안 나옴. 풀 확인: 계획기가 닫을 때 손가락 중점은 목표 위 7.8 mm(데드밴드 안) |
| `mock_full2` | 손가락 중점 기하 + **잡기 깊이 바닥**(TCP ≥ 계획기 잡기 높이 − 3 mm, 바닥 도달 = 도달) | **성공 15.5 s** | — |
| `zs_hw` | 위와 같음 | 실패(영점 결정 품질) | §1 |
| `sft_h` | 위와 같음 | 실패(들기에서 활성 잠김) | 닫기 때 팔이 약 40 mm 밀림 → 명령 기준이 제자리 → 매 스텝 DEVIATE → epoch+1 → 모든 표가 premise epoch로 폐기 → 결정 없음 → 정지 → 다시 DEVIATE(epoch 66). **Astra 하트비트가 "Repeated deviations during lift"로 patch를 냈다**(감시가 실제로 작동). 조치: DEVIATE/CONTRADICT 뒤 스킬 기준 ref(t)를 측정 TCP에서 다시 세움(M5 재계획, 00 §3) |
| `sft_h2` | 재기준 추가 | **성공 16.8 s** | epoch 6(DEVIATE 5 + Astra patch 1), 호출 오류 0 |
| `mock_det1/2` | 최종 | 성공 ×2, 행동 비트 동일 | 결정성 |
| `fused_mock` → `fused_mock2` | fused (b)를 관절 공간으로 | 인터페이스 확인 | 첫판은 실행하지 않는 스킬 명령을 (b) 기준으로 써서 가짜 DEVIATE → 실행 청크 목표 기준으로 고침(epoch 0, 청크 재생 501/600 틱) |
| (Jev-L 탐침) | — | 풀 DEV 프레임 24개, N = 1 | HW p50 0.124 s, H p50 0.118 s(참고, 판정 밖) |

- 영점 판은 재기준 수정 전 코드로 돌았으나 DEVIATE가 0회라 수정의 영향이 없다.
- 프레임 확인: `docs/stage3/results/r5_sft_frames.jpg`(SFT 성공 판의 닫기·운반·열기·후퇴, 위 = 머리캠, 아래 = 우손목캠). 닫기에서 머그를 잡고, 운반 중 들려 있고, 열기·후퇴에서 머그가 파란 트레이 위에 서 있다. 영점 판은 프레임을 보지 않았고, 스텝 로그상 TCP가 탁자 위 약 18 cm(머그 옆 y 쪽)에서 끝까지 멈춰 있다.

## 5. 지연 예산 — FusedModel 결정·행동 경로 합치기 (R4 요청)

**정한 것 [Claude]**: vLLM OpenAI 서버는 로그 확률 경로에서 은닉 상태를 내주지 않는다. 그리고 R4 expert는 **확정 결정**을 조건으로 받으므로, 결정과 행동은 한 호출이 될 수 없고 스텝마다 두 단계다. 1순위(지금 구현) = **결정은 vLLM(lead, 접두·멀티모달 캐시), 행동은 같은 병합 가중치를 올린 HF 행동 서버(문맥 순전파 + CUDA 그래프 expert)**. 2순위(측정 대상) = HF 한 프로세스에서 결정 로그 확률(R3 접두 공유)과 문맥 은닉 상태를 한 번에 얻어 캐시하고, 확정 뒤에는 expert(23 ms)만 돌리기 — 결정 지연이 vLLM lead보다 나쁘지 않으면 이쪽이 더 "하나로 융합"(§58)에 맞다. (**정정(정본 §67 C4, R7 4회차 M2)**: 실제 구현은 2순위 — decide도 HF 백본의 공유 접두 순전파 한 번으로 결정 확률·문맥 은닉·확인 헤드를 함께 얻고, 확정 뒤 chunk는 캐시된 문맥 + CUDA 그래프 expert. vLLM은 모듈형 기준선 Jev-L에만 쓴다. `harvest/runtime/fused_model.py`)

| 구간 (스텝 T_c = 0.33 s) | 값 | 출처 |
|---|---|---|
| 결정 호출(머리 + 활성 손목, lead) p95 | 설계 0.28 s | §59(D27 최악 판) |
| 〃 이번 폐루프 실측(동시 in-flight ≤ 2) | SFT·H p95 0.29 s(`sft_h2`) / 0.40 s(`sft_h`, 60 s 판) · 영점·HW p95 0.31 s | 이 문서 §1 |
| M4 표 처리·확정(act 안) | O(ms) | 설계 |
| 행동 청크: HF 문맥 순전파(4B) | 약 97 ms(= 120 − 23) | R4 실측(H200, HF) |
| 행동 청크: expert 10 스텝 | eager 36–49 ms → **CUDA 그래프 23 ms** | R4 실측, 우리 GraphedSampler로 동등 확인 |
| 행동 청크 합(1순위) | 약 120 ms < `chunk_lead` 0.15 s | 스텝 시작 전 도착(가짜 세계 시험으로 확인) — 1순위 설계값(76줄 정정: 실제 구현은 2순위) |
| 2순위의 확정 뒤 행동 | 약 23 ms | 문맥 캐시 재사용 가정 [미측정] → 실측(pre-R7, 실제 구현 = 2순위): 청크 expert CUDA 그래프 30.0 ms(단독 벤치), 폐루프 동시 부하에서 청크 전체 p50 80–591 ms(`pre_r7_fixes.md` §1.3–§1.4) |
| 청크 길이 | 15 × 1/30 s = 0.5 s ≥ lead 0.15 + T_c 0.33 | stageb_data |

- 결정 호출은 겹쳐 돌아 T_c를 넘어도 되지만(d̂가 목표 슬롯을 밀어냄), 행동 경로는 스텝마다 순차라 `chunk_lead` 안에 끝나야 한다. 같은 GPU에서 vLLM과 HF 행동 서버가 경쟁하므로 **실물 서버(RTX PRO 6000) 조건에서 두 경로 동시 부하 지연**을 다시 재야 한다(사용자 지시 user-log 62: 폐루프 검증은 실물 서버 조건 가정, 같은 vLLM 설정·캐시·lead). 이번 판은 H200 GPU 3이다. → **정정(sweep6, R7 5회차 N3)**: 괄호 안 '같은 vLLM 설정·캐시·lead'는 user-log 62 원문('프로600에서 하는걸 가정해서 여기서 다할거고')에 없는 Claude의 풀이다(모듈형 Jev-L에만 맞음). 'vLLM과 HF 행동 서버가 경쟁'은 1순위 설계 기준이다 — 실제 구현(2순위, 76줄 정정)은 한 HF 모델 프로세스가 decide·chunk로 GPU를 번갈아 쓴다(`pre_r7_fixes.md` §1.1 GPU 줄 세우기, 동시 부하 지연은 §1.6-1 → 정본 §67 C8 SCOPED).

## 6. 남은 문제 (열린 것)
1. **계약 편집 없음**: Astra patch/replace는 epoch만 올린다(A5′ 검사·M2 R3 경계 교체·`detect_phrase`(§46) 반영 미구현). T0 첫 계획 호출도 없음(고정 계약 c1). T_sub(단계 경계 질의)·사건 앞당김은 훅만 있다. → **갱신**: T_sub(K1)·사건 앞당김·K3/K4는 pre-R7(519de26, `pre_r7_fixes.md` §4)에서 구현. A5′ 검사·M2 R3 합치기는 E2E-ready 범위 밖(정본 §67 C8 SCOPED). T0 첫 계획 호출·`detect_phrase` 반영은 여전히 없다(`r7_sweep6.md` §3).
2. **M7 없음**: FAIL 판정·M9 복구 대신 스킬 안의 단순 재시도(헛잡기·놓침 → 다시 열고 접근, 최대 2회). 진행 질문(progress)은 호출에서 뺐다(학습 안 된 질문). → **갱신**: M4 `measure()`·M7 critic(V1h 단독 경보 + T1 하드 채널)은 pre-R7(519de26, `pre_r7_fixes.md` §2)에서 구현. FAIL → M9 복구는 E2E-ready 범위 밖(정본 §67 C8 SCOPED).
3. **M4 미구현 부분**: C3′ Beta 정지 규칙, 누적 예상 상태 합의(agree_mode), align_tol, CUSUM, θ·J5 게이트(E1 전이라 끔), LAG 시 재배치. (b) 문턱(OK 15 mm / LAG 40 mm, fused 0.05/0.15 rad)은 [가정]이고 추종 지연을 모델링한 ref(t)가 아니라 명령 자체와 비교한다 → 빠른 운반 중 DEVIATE가 가끔 난다(`sft_h2` 5회). M5 ref(t)(Ruckig) 연결 필요. → **갱신**: J5 게이트는 R6에서 런타임에 들어갔다(`core.py` `_j5`, 보정 파일 + `--j5-alpha`일 때만, `r6_eval.md` §4). θ 게이트는 오프라인 판정(`calibration.py`)만 있다. 나머지(C3′·agree_mode·align_tol·CUSUM·ref(t))는 여전히 열림(`m4.py` 머리 설명).
4. **라벨 기하 대 계획기 기하 차이**: 결정 정답(labels_v2)은 손가락 링크 중점, 계획기 잡기 높이는 패드 중심 기준 → 잡기 깊이 바닥(−3 mm)으로 맞췄다. 데드밴드 경계(약 1 cm)에 붙어 있어 취약하다. 단계 B 데이터 정의 때 기준점을 하나로 정해야 한다.
5. **H 표 공유**: 한 호출의 답을 H = 3 스텝의 표로 쓴다(M4 §4.1의 "앞선 스텝 예상 상태를 앞에 적기"는 안 함). 질문 문구의 ds 번호는 첫 목표 스텝.
6. **SFT 판의 입력 형식**: SFT 모델은 머리캠만(H)으로 학습돼 H로 돌렸다. §59 기본(HW)은 영점 판에만 썼다 — 두 판의 입력이 다르다. 단계 A′(R3)가 HW로 학습되면 HW로 다시 돌린다.
7. **FusedModel 실물 모델 없음**: `StageBFused`(vLLM decide + HF chunk; (**정정(정본 §67 C4, R7 4회차 M2)**: 실제 구현은 2순위 — decide도 HF 백본의 공유 접두 순전파 한 번으로 결정 확률·문맥 은닉·확인 헤드를 함께 얻고, 확정 뒤 chunk는 캐시된 문맥 + CUDA 그래프 expert. vLLM은 모듈형 기준선 Jev-L에만 쓴다. `harvest/runtime/fused_model.py`))는 R4 체크포인트가 나오면 붙인다(계약·스케줄·로그·CUDA 그래프 샘플러는 준비됨). stage-B 고유감각은 23-D로 우리 8-D `joint_pos`와 다르다 — 어댑터 필요. → **해결(pre-R7 519de26, `pre_r7_fixes.md` §1, R7 5회차 P2)**: 실체크포인트 어댑터 = `harvest/runtime/fused_model.py`(LoRA + expert + 보조 + 확인 헤드를 올린 HF 서버 + `FusedClient`), 고유감각 23-D ← aiworker 8-D 사상(§1.1; tau는 학습 평균 대치 — 정본 §67 C8 SCOPED), `closed --backend fused --model <ckpt>`(`harvest/eval/closed.py` 머리 설명 'Backends' 줄, `info["kind"] == "stageb"` 분기). '실물 모델 없음'은 R5 당시 기록이다.
8. **DEV P0만**: P1/P2는 `perturb.apply_pending`이 계획기 단계를 요구해 몸체에서 막았다(NotImplementedError). random/dr 변형은 몸체가 받지만 이번에 돌리지 않았다.
9. **LatencyChargingController**는 스텁(P3에서 구현).
10. **종료 멈춤**: 평가 뒤 `SimulationApp.close()`가 멈춰 결과 저장 뒤 강제 종료한다(스모크 1판은 수동 정리: 내 프로세스만).
11. 한 판씩이라 성공률·지연 분포는 결과가 아니다(§56). 지연 최대 1.98 s(영점 첫 호출 부근)는 토크나이즈·캐시 예열로 보임 [미확인].

## 7. 재현
```bash
bash tools/r5/sync.sh                                   # 로컬 → /data/harvest/code_r5cl
# vLLM (GPU 3, 비었을 때만): 접두 + 멀티모달 캐시, 이미지 2장
/data/harvest/code_r5cl/tools/r5/serve.sh /data/harvest/ckpt/stageA/sftA_pool_v1/merged sftA-r5 8142 0.40
# 한 판 (Isaac GPU 1, 결과 /data/harvest/out/r5/<tag>)
/data/harvest/code_r5cl/tools/r5/run_episode.sh sft_h2 1800 --backend modular --selector jevl \
  --url http://127.0.0.1:8142 --model sftA-r5 --model-path /data/harvest/ckpt/stageA/sftA_pool_v1/merged \
  --layout H --mode lead --astra auto --max-seconds 60
run_episode.sh mock_det1 1800 --backend modular --selector mock --astra mock        # 결정적 모의
run_episode.sh fused_mock2 1200 --backend fused --selector mock_fused --astra mock --max-seconds 6
```

> 정정(2026-09-25 00:08 UTC, R7 1회차 D2): 위 '로그 스키마(§42) 확인'은 요청 해시·카나리 id가 빠진 상태였다. `harvest/runtime/reqhash.py`·`harvest/eval/canary.py` 추가로 결정·청크·Astra 행에 요청 sha256·이미지 해시·카나리 id가 기록된다(`r7_fixes.md` 사이클 1 수정).
