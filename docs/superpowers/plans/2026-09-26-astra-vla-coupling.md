# Astra–VLA 결합(직렬 흐름 + 두 층 M4) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 승인된 결합 설계(Astra low가 한 번에 하나씩 일반 조종 명령 continue/edit/stop + 진행 평가를 내고, 융합 VLA가 0.33 s마다 보정하며, 두 층의 답을 M4 규칙으로 합친다)를 런타임에 넣고, 모의 Astra만으로 전부 시험되게 하며, E-Couple·E-Astra-necessity(흐름 자리) 사전 등록 초안과 평가 배선까지 만든다.

**Architecture:** 새 패키지 `harvest/couple/`에 순수 모듈(스키마·게이트·비용 장부·직렬 흐름·Astra 층 히스테리시스·부드러운 편향·두 층 비가역 게이트·덧그림·재사용 캐시·로컬 VLM 어댑터)을 두고, `CoupleDriver` 하나가 이들을 묶어 `OursRuntime`(harvest/runtime/core.py)에 틱 단위로 끼운다. 런타임은 드라이버가 준 편향 한 걸음(6차원)과 속도 배율만 실행기에 적용하고, 비가역 전환(닫기·S1→S2·놓기)은 드라이버의 두 층 게이트에 묻는다. 움직임 줄(§83)은 직렬화 판본 `ser-A-min-3`으로 결정 상태에 들어간다.

**Tech Stack:** Python 3.13(로컬)·파드 Python, numpy, Pillow, httpx(MockTransport), pytest. Isaac는 카메라 자세 어댑터 한 곳(Task 8 Step 6)에서만.

**Spec:** `docs/superpowers/specs/2026-09-26-astra-vla-coupling-design.md`(개정 머리말, §11–§16이 앞 절보다 우선; §16 = 직렬 1개). 정본 `docs/design/00-interfaces.md` §82(J1–J6, 보충: 유료 한도), §82 보충 2(흐름은 effort low), §83(움직임 줄), §84 + 보충 1(falsify 먼저·재사용 한 번) + 보충 2(직렬 1개). 참고: `docs/research/molmoact_deepdive_2026-09-26.md`(덧그림 형식), `astra_role_2026-09-25.md`(§7 E-Astra-necessity), `steering_representation_2026-09-25.md`, GPT-as-Policy `D:\taskC_work\astra_refs\GPT-as-Policy\hybrid_rollout\robolab\robolab_server\{gate_assessment,action_edit_kinematics}.py`(게이트·edit 의미).

## Global Constraints

- 런타임 코드 구현은 **R7 E2E 준비 기준점(연속 무결 2회) 뒤**에 시작한다(정본 §84). 착수 조건 0-1 참고.
- Astra 흐름 호출은 **동시 1개**: 답(또는 시간 초과)이 오면 그때의 최신 관측으로 다음 요청, 간격 = 지연 L(정본 §84 보충 2, 설계 §16). 사건은 진행 중 요청을 버리지 않고 **다음 요청에 표시**한다.
- 흐름의 effort는 **low만**; high는 흐름에 절대 쓰지 않는다(정본 §82 보충 2).
- Astra 명령 = `continue` / `edit`(손끝 이동 **≤ 5 cm**·회전 **≤ 0.35 rad**·그리퍼 `keep|open|close`) / `stop`. 공간 목표(점·경로·물체 부위) 표현은 쓰지 않는다(설계 개정 머리말).
- `edit`은 `execution=failed` 또는 `intent=misaligned`일 때만; `uncertain`이거나 `confidence=low`이면 `continue`로 본다(설계 §11, GPT-as-Policy "Uncertainty alone … is not a takeover reason").
- 반영: **한 답 50 %, 연속 두 답이 같은 방향이면 100 %**, 방향이 뒤집히면 편향 0·확정 미룸, 유효 창(다음 답 예상 도착, 1–3 s) 동안 선형 경사, 새 답 없으면 감쇠(설계 §11). 편향 변화율 상한(튐 금지).
- 답 나이(도착 − 기준 시각) > **6 s(잠정, 탐침 뒤 고정)** → 그 `edit`은 버리고 평가만 쓴다(설계 §15).
- Astra 입력 = 카메라 **3대**(`cam_head`, `cam_wrist_left`, `cam_wrist_right`) + 이름표. "잡았다/놓았다/닿았다" 주장은 **활성 손목 시점 근거**가 있어야 유효, 어긋나면 손목 우선 + 고유감각(T1) 교차 확인(설계 §12).
- 비가역 동작(그리퍼 닫기·열기, 단계 S1→S2)은 **두 층이 일치할 때만** + **손목 시점 근거 또는 T1 고유감각 근거**(설계 §5, §12).
- 덧그림: 현재 손끝·최근 2–3 s 궤적·확정 다음 청크 방향·직전 Astra 편향 — **다음 청크 예정 화살표는 Astra 영상에만**, VLA 입력에는 넣지 않는다(설계 §13–§14, 정본 §84). 손목 영상엔 가장자리만.
- 유료 한도 **약 10만 원**(정본 §82 보충). 실험마다 예산 상한을 사전 등록에 먼저 적고, 누적 비용이 상한의 **80 %**에 닿으면 멈추고 보고(설계 §15). **유료 실행은 Claude 자체 검사 뒤**(user-log 87·저장소 CLAUDE.md: 사전 등록에 '바꾸는 결정·표본 충분성·무료 사전 실행' 자체 검사 절을 쓰고, 관문 결함이면 멈추고 재설계; 사용자 승인은 받지 않음 — 2026-09-25 18:00 UTC 메인 개정). 이 계획의 시험은 전부 모의 Astra(유료 호출 0).
- falsify 먼저: 저장된 복구안 재사용은 **같은 에피소드·같은 실패 서명(단계 + 대상 물체 + 실패 유형 + 검출 근거)에서 한 번까지**, 부분 일치는 재사용 금지, 재사용 사례도 J5·J6 입력으로 남기고 **모든 분기를 로그**(정본 §84 + 보충 1).
- 움직임 줄: `motion: arm=<still|slow|fast> gripper=<closing|still|opening>`, 인과 후방 차분, 경계 팔 **0.218/0.607 rad/s**·그리퍼 |열림 속도| **0.176 /s**(학습 분할 분위수), 줄 드롭아웃은 학습 때만(정본 §83). 새 직렬화 판본 → `question_id@vN`·보정 파일·카나리 기준 재생성(§77 규칙).
- 정지는 T0와 L3뿐(정본 §4): Astra `stop`은 물리 정지가 아니라 "과제 완료 주장"으로만 기록한다.
- 브랜치 `dev`만(main 금지). 로컬 쓰기는 D:만(C: 금지), 스크래치 `D:\tools\scratch_qdd\plan_coupling`. 파드는 `/data`만(`source /data/harvest/env.sh`). 스크립트·메시지 파일은 Write 도구로 만든다(Git Bash heredoc·`cat >`·`python -` 금지).
- git은 `git -c safe.directory=D:/qdd ...`. 커밋 메시지는 Write 도구로 `D:\tools\scratch_qdd\plan_coupling\msg_<task>.txt`에 쓰고 `git commit -F`로 넣는다; 메시지 끝 두 줄: `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01Cak1EG98gYtthtAuz7r8W8`.
- 비밀 값 출력·검색 금지. API 키는 파드 `/data/.openai_token`을 코드가 읽기만 한다.
- 다른 에이전트 소유물 수정 금지: E-MA1(학습·`prereg_ma1.md`), E-Astra-motion 탐침 코드 `harvest/astra_motion/`·`tests/astra_motion/`(미커밋). 탐침 **결과**만 입력으로 쓴다(아래 PROBE 표).
- 사용자 보고 시각은 KST, 저장소 기록 시각은 UTC. 문서 산문은 한국어, 코드·식별자는 영어.


## 메인 판정 (Rulings, 2026-09-25 18:00 UTC — 사용자가 판단을 메인에 위임: user-log 85 "옳은 방향으로 바꿔도돼", user-log 87)

- **R1 '두 층 일치'(설계 §5)의 뜻 = 관대한 기본값 채택**: 비가역 동작(닫기·S1→S2·놓기)은 (a) 신선한 Astra 답(도착 ≤ 3 s)이 반대(misaligned·failed·반대 그리퍼 명령)하지 않고 (b) T1 고유감각 전제(닫기 = 그리퍼 열림 + 접촉 근처, 들기·놓기 = 쥐고 있음)가 참이면 진행. 신선한 답이 없으면 VLA 단독(§5 '> 3 s 무답'). 엄격 모드(`irrev_need_aligned=True`)는 E-Couple 판정 밖 참고 팔로만 — 이유: L = 3–10 s에서 긍정 답을 기다리면 모든 파지가 수 초씩 멈춘다(Astra는 느리고 VLA는 실시간이라는 역할 분담, user-log 83). 비용: 틀리면 Astra가 막았어야 할 파지를 VLA가 진행 → E-Couple에서 '신선한 답이 반대였는데 진행된 비가역 동작 수'를 판정 밖 지표로 보고.
- **R2 유료 가드 = 사용자 승인 대신 자체 검사 참조**(Task 14 `--approval` 인자의 뜻을 바꿈, 이름은 유지).
- **R3 탐침 예산 15,000원**(재범위)로 누적 계산 갱신.
- 나머지 모호점 판정(2–12)은 에이전트 판정대로 채택.
- **실행 방식**: R7 E2E 준비 기준점 태그 뒤, **subagent-driven**(과제 16개가 인터페이스로 서로 물리고 런타임 안전에 닿아 과제마다 검토가 값어치 있음). Task 12(직렬화기 판 올림)는 E-MA1b가 끝난 뒤, Task 8은 탐침 코드 커밋 뒤.

## Review Focus

- 시간 초과로 버린 요청의 답이 늦게 도착하거나 순서가 바뀌어 도착해도 **제어에 쓰이지 않고 비용은 정확히 한 번** 청구되어야 한다 — Task 9 `test_late_answer_after_timeout_is_ignored_and_charged_once`.
- 카메라 프레임이나 카메라 모델(`cams`)이 없는 틱(렌더 간격, 가짜 세계)에서도 요청은 **텍스트만으로 나가고** 덧그림은 건너뛰며 멈추지 않아야 한다 — Task 8 `test_polylines_skip_cameras_without_model`, Task 9 `test_no_frames_no_cams_sends_text_only`.
- Astra 편향을 실행해도 M4 (b) 검사가 **가짜 DEVIATE/CONTRADICT를 내면 안 된다**(모듈형은 기준 자체를 옮기고, 융합형은 적용한 관절 편향이 `last_a`에 들어간다) — Task 10 `test_offset_does_not_create_false_b_deviations`.
- 병렬 Isaac 작업자(`closed --parallel`, 변형당 한 프로세스)가 **같은 비용 장부 파일**을 쓸 때 서로의 청구를 보고 80 % 정지가 지켜져야 한다 — Task 3 `test_two_ledgers_on_one_file_see_each_other`.
- 에피소드 재시작(`reset`) 때 진행 중이던 요청은 **다음 에피소드에 적용되지 않고** 예약 비용은 "unanswered"로 청구되어야 하며 편향·합의 상태가 새로 시작해야 한다 — Task 10 `test_reset_with_request_in_flight_charges_and_forgets_it`.

---

## 착수 조건 (Task 1 전에 확인, 코드 없음)

- [ ] **0-1. R7 기준점**: `docs/handoff.md` §2.8 마지막 줄이 "연속 무결 2회"(E2E 준비 완료)이고 그 태그가 있는지 확인한다: `git -c safe.directory=D:/qdd tag --list "stage3-*"`. 없으면 **멈추고** 조정자에게 보고한다(정본 §84: 런타임 구현은 그 뒤).
- [ ] **0-2. 탐침 결과**: `docs/stage3/results/astra_motion.md`가 있으면 아래 PROBE 표의 값을 읽어 Task 1의 `CoupleParams` 기본값과 `probe_ref`에 반영한다. 없으면 표의 기본값을 쓰고 `probe_ref="none"`으로 둔다(모든 실행 로그에 남는다).
- [ ] **0-3. 탐침 코드 커밋 여부**: `git -c safe.directory=D:/qdd ls-files harvest/astra_motion/world_isaac.py`. Task 8 Step 6(Isaac 카메라 자세 어댑터)은 이 파일이 커밋된 뒤에만 한다(그 함수 `camera_pose`를 재사용하고 다시 만들지 않는다). 나머지 Task는 무관.
- [ ] **0-4. E-MA1 일정**: Task 12(직렬화 판본 올림)는 `PROMPT_FILES`의 `serialize.py`·`deccall_snap.py`와 `PROMPT_FILES_B`의 `stageb_data.py` 바이트를 바꿔 **기존 체크포인트 전부를 런타임이 거부**하게 한다(§77과 같은 규칙). E-MA1 담당에게 학습·평가가 끝났는지 확인하고, 끝나지 않았으면 Task 12만 미룬다.

### PROBE 값 표 (E-Astra-motion 결과로 정하는 상수, 기본값은 탐침 사전 등록과 같게)

| `CoupleParams` 필드 | 기본값 | 무엇으로 정하나 (`docs/stage3/prereg_astra_motion.md`) |
|---|---|---|
| `request_mode` | `"F1"` | §7-1 판정(F1 뒤집힘율 ≤ 0.5 × F0 그리고 성공 ≥ F0 → F1) |
| `latency_init_s` | 3.0 | 직렬 호출 지연 p50 |
| `timeout_s` | 15.0 | 직렬 호출 지연 p95 × 1.5 |
| `stale_edit_s` | 6.0 | 답 나이 분포(설계 §15 잠정 6 s) |
| `same_dir_deg` / `flip_deg` | 35 / 90 | §4.2 부드러운 실행기와 같은 값 |
| `decay_s` / `v_max` / `a_max` | 0.5 / 0.08 / 0.32 | §4.2 부드러운 실행기와 같은 값 |
| `est_text_tokens`, `cost.TOK_HEAD`, `cost.TOK_WRIST` | 2500, 302, 134 | §8 토큰 추정 → 실측 입력 토큰 |
| `overlay` | True | §4.4 덧그림 절제(덧그림이 판정을 해치면 False) |

### 모호점 판정 (계획 작성 때 정함 — 조정자 확인 권장)

1. **"두 층 일치"(설계 §5)의 기본 해석**: 신선한 Astra 답(도착 뒤 ≤ `astra_fresh_s` = 3 s)이 있으면 그 답이 거부하지 않아야 한다(의도 misaligned·실행 failed·반대 그리퍼 명령이면 거부). 3 s 넘게 새 답이 없으면 §5 "Astra 확정이 오래되면 VLA로 흐름을 잇는다"를 따라 VLA 쪽만으로 진행한다. 엄격판(신선한 답이 `aligned`여야 함)은 `irrev_need_aligned=True`로 켤 수 있다. 직렬 L = 3–10 s에서 매 전환마다 긍정 답을 기다리면 파지가 수 초 멈추기 때문이다.
2. **T1 근거(설계 §12)**: 전환의 고유감각 전제로 정의한다 — 닫기 = 그리퍼 열림 + 접촉 근처 구역(`core.near_contact`), S1→S2 = 쥠, 놓기 = 쥠. 위치·접촉 적합성은 기존 코드 안전 술어(`skills.py`)가 그대로 맡는다.
3. **"더 보기" 동작 목록(설계 §11 "구현 계획에서 목록으로 고정")**: `info_request ∈ {none, slow_down}`만 허용(2 s 동안 속도 0.5배). 손목을 대상 쪽으로 기울이는 동작은 불확실할 때 움직이는 것이라 넣지 않는다(탐침도 넣지 않음).
4. **edit 좌표계**: GPT-as-Policy처럼 **로봇(시뮬 world) 좌표계**의 손끝 변위. Astra가 축을 알도록 덧그림에 손끝 x/y/z 축(빨강/초록/파랑 3 cm)을 추가한다(설계 §13 네 요소 + 축 한 가지).
5. **편향의 의미**: 편향은 "추가 이동 속도"로 들어가 누적 변위가 `가중치 × delta`가 된다. 모듈형은 스킬 기준점(`cmd_pos`)을 직접 옮기고, 융합형은 현재 청크의 관측 시각 뒤에 적용한 변위만 IK 차분으로 관절 편향에 더한다(청크는 관측에서 다시 예측되므로 이중 적용 방지). "감쇠" = 창이 끝났는데 남은 변위가 있으면 `decay_s` 동안 속도를 줄이고 나머지를 버린다.
6. **"불일치 사건"(설계 §5)**: 일반 조종에는 Astra 단계·대상이 없으므로 측정 가능한 두 조건으로 정의 — (i) VLA가 비가역 전환을 원하는데 Astra 층이 1 s 넘게 막음(`layer_mismatch`), (ii) VLA 확정 방향이 Astra 편향과 반대로 3스텝(1 s) 지속(`offset_contradicted`, 편향 남은 양 0.5배). **진전 없음** = 편향이 1 cm 넘게 나갔는데 2 s 동안 손끝이 그 방향으로 20 % 미만 이동(`no_progress`). 셋 다 다음 요청의 `events`에 붙는다(J2는 §82 구현 뒤).
7. **F1 keep의 확인**: keep은 대기 중 편집을 확인하지만, 그 keep 답의 평가가 개입 자격(failed/misaligned, 불확실 아님, 근거 있음)을 갖출 때만 100 %로 올린다. 확인 때 벡터는 처음 제안한 답의 것을 쓴다.
8. **stop**: 활성 손목 `placed`/`released` 주장이 있어야 유효, 연속 두 답(F1은 stop 뒤 keep)이면 "stop_confirmed" 사건으로 기록만 한다(물리 정지 없음).
9. **하트비트**: 결합 모드에서는 E-M8c 하트비트(K2)를 끄고, 기존 사건 호출 지점(M7 알람·T_fail·J5·CONTRADICT)은 흐름의 다음 요청 표시로 보낸다(설계 §16 "사건은 다음 요청에 표시").
10. **예산 정지 뒤 편**: 80 % 정지에 걸린 에피소드는 그 안에서 Astra 없이 VLA만 돈 것이므로 판정에서 빼고 수를 보고한다(`budget_excluded`).
11. **E-Astra-necessity 범위**: 이 계획은 흐름 자리(실행 중 일반 조종)만 다룬다. J1–J6 오프라인 슬롯 시험은 §82 구현(`harvest/astra/jobs.py`)과 함께 따로 등록한다. 흐름에는 트리거가 없으므로 U-rand는 빼고, 로컬 모델은 Astra 실측 지연 p50으로 호출 간격을 맞춘다(`min_interval_s`) — 호출 수 차이가 결과를 좌우하지 않게.
12. **움직임 줄 위치**: `last_step:` 줄 바로 앞(상태 끝에서 둘째 줄), 문맥 텍스트(`ctx_text`, 단계 B 문맥)는 상태 + 움직임 줄로 끝난다 — E-TC 학습(문맥 끝에 줄 추가)과 같은 모양. 기록이 없는 곳(모듈형 풀 라인, 아직 줄을 안 쓰는 R2 데이터)은 학습 때 쓰던 `motion: arm=unknown gripper=unknown`.

## 파일 구조

| 파일 | 책임 | Task |
|---|---|---|
| `harvest/couple/__init__.py` | 패키지 표지 | 1 |
| `harvest/couple/params.py` | `CoupleParams`: 결합의 모든 조정값(로그에 통째로 남김) | 1 |
| `harvest/couple/schema.py` | 응답 형식·어휘·`AstraAnswer`·`parse_answer` | 1 |
| `harvest/couple/prompt.py` | 프롬프트 판본(`astra-couple@v1`), `build_input`, `request_from_input` | 1 |
| `harvest/couple/mock.py` | 답 생성기 `answer()`(1), `ScriptedCoupleAstra`(4) | 1, 4 |
| `harvest/couple/gate.py` | 의미 게이트: 나이·불확실·개입 자격·근거·손목 규칙·T1 교차 | 2 |
| `harvest/couple/cost.py` | 가격표·실험 비용 장부(공유 파일, 예약, 80 % 정지) | 3 |
| `harvest/couple/stream.py` | `SerialStream`: 동시 1개·시간 초과·늦은 답·사건 표시·선택 쉬기 | 4 |
| `harvest/couple/layer.py` | `AstraLayer`: 연속 두 답 히스테리시스, 뒤집힘, F1 keep, stop | 5 |
| `harvest/couple/offset.py` | `OffsetApplier`: 경사·감쇠·속도·가속 상한·축소 | 6 |
| `harvest/couple/twolayer.py` | `TwoLayerGate`, `VlaFastCheck`, `NoProgress`, `committed_vector` | 7 |
| `harvest/couple/overlay.py` | 카메라 모델·투영·덧그림·MolmoAct식 0–255 폴리라인 | 8 |
| `harvest/couple/driver.py` | `CoupleDriver`: 틱마다 묶음, 요청 조립, 로그·요약 | 9 |
| `harvest/couple/geom.py` | 쿼터니언 보조(회전 벡터 → wxyz, 곱) | 10 |
| `harvest/runtime/core.py` | 결합 설정·배선·편향 실행·사건 전달·요약 | 10, 11, 12 |
| `harvest/runtime/skills.py` | `speed_scale`, `irrev_gate`, `nudge` | 10 |
| `harvest/runtime/ir_policy.py` | 관측에 `cams`, 사이드카에 `couple`·`recovery` 행 | 10, 11 |
| `harvest/runtime/aiworker.py` | 관측 `extra["cams"]`(탐침의 `camera_pose` 재사용) | 8 |
| `harvest/couple/recovery_cache.py` | falsify 먼저 재사용 캐시 | 11 |
| `harvest/runtime/motion.py` | 런타임 움직임 줄 추적기 | 12 |
| `harvest/serialize.py`, `harvest/deccall_snap.py`, `harvest/train/stageb_data.py`, `harvest/runtime/models.py`, `harvest/runtime/fused_model.py`, `harvest/train/stagea_train.py` | `ser-A-min-3`(움직임 줄) | 12 |
| `harvest/couple/local_vlm.py` | 로컬 VLM을 같은 `call()` 모양으로 | 13 |
| `harvest/eval/couple.py`, `harvest/eval/closed.py` | 결합 팔 배선, 유료 실행 가드, 집계, 예산 추정 CLI | 14 |
| `docs/stage3/prereg_couple.md` | E-Couple 사전 등록 초안 | 15 |
| `docs/stage3/prereg_astra_necessity_stream.md` | E-Astra-necessity 흐름 자리 초안 | 16 |
| `tests/couple/*.py`, `tests/runtime/test_couple_runtime.py`, `tests/runtime/test_motion_line.py`, `tests/eval/test_couple_eval.py` | 시험 | 각 Task |

시험 명령은 모두 저장소 루트 `D:\qdd`에서 `python -m pytest <path> -v`(pytest.ini가 basetemp를 D:로 둔다).

---

### Task 1: 조정값·응답 형식·프롬프트 판본

**Files:**
- Create: `harvest/couple/__init__.py`, `harvest/couple/params.py`, `harvest/couple/schema.py`, `harvest/couple/prompt.py`, `harvest/couple/mock.py`
- Test: `tests/couple/__init__.py`, `tests/couple/test_schema.py`

**Interfaces:**
- Consumes: 없음.
- Produces:
  - `CoupleParams` (frozen dataclass, 필드는 아래 코드 그대로), `CoupleParams.to_json() -> dict`
  - `schema`: 상수 `SCHEMA_ID, EXEC_STATUS, INTENT_STATUS, CONFIDENCE, COMMANDS, DIFFS, GRIPPER, INFO_REQUESTS, CLAIM_KINDS, EDIT_MAX_M, ROT_MAX_RAD`; `class SchemaError(ValueError)` (`.problems: list[str]`); `@dataclass Edit(dp, dr, gripper)` + `vec6() -> np.ndarray(6)`, `to_json()`; `@dataclass AstraAnswer(request_no, t_state, t_deliver, diff, command, edit, execution, intent, confidence, evidence, evidence_views, claims, task_progress, info_request="none", gate="raw", takeover_ok=False, progress_trusted=True, notes=[])` + `.age`; `parse_answer(text, mode, sent_cameras, request_no, t_state, t_deliver) -> AstraAnswer`
  - `prompt`: `REQ_OPEN, REQ_CLOSE, PROMPT_ID: dict[str, str]`(mode → 12 hex), `build_input(req: dict, images: dict[str, bytes], p: CoupleParams, task: str) -> list`, `request_from_input(inp: list) -> dict`
  - `mock.answer(command="continue", *, execution, intent, confidence, evidence, views, claims, dp, dr, gripper, diff, info, done) -> dict`

- [ ] **Step 1: 실패하는 시험 쓰기**

`tests/couple/__init__.py`는 빈 파일. `tests/couple/test_schema.py`:

```python
import json
import re

import numpy as np
import pytest

from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.prompt import PROMPT_ID, build_input, request_from_input
from harvest.couple.schema import COMMANDS, CONFIDENCE, EDIT_MAX_M, EXEC_STATUS, GRIPPER, INTENT_STATUS, ROT_MAX_RAD, \
    SchemaError, parse_answer

CAMS = ("cam_head", "cam_wrist_left", "cam_wrist_right")


def _parse(d, mode="F0", cams=CAMS, t_state=1.0, t_deliver=4.5):
    return parse_answer("model says: " + json.dumps(d) + " end", mode, cams, 7, t_state, t_deliver)


def test_f0_edit_parses_with_age_and_views():
    a = _parse(answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.03, 0.0)))
    assert a.command == "edit" and a.request_no == 7 and a.diff is None
    assert a.age == pytest.approx(3.5)
    np.testing.assert_allclose(a.edit.dp, [0.0, 0.03, 0.0])
    np.testing.assert_allclose(a.edit.vec6(), [0.0, 0.03, 0.0, 0.0, 0.0, 0.0])
    assert a.edit.gripper == "keep" and a.evidence_views == ("cam_wrist_right",) and a.gate == "raw"


def test_edit_over_5cm_or_035rad_is_refused():
    with pytest.raises(SchemaError, match="delta_position_m"):
        _parse(answer("edit", execution="failed", dp=(0.04, 0.04, 0.0)))
    with pytest.raises(SchemaError, match="delta_rotation_rad"):
        _parse(answer("edit", execution="failed", dp=(0.0, 0.0, 0.01), dr=(0.0, 0.0, 0.4)))
    assert EDIT_MAX_M == 0.05 and ROT_MAX_RAD == 0.35


def test_views_and_claims_must_be_cameras_that_were_sent():
    with pytest.raises(SchemaError, match="evidence_views"):
        _parse(answer(views=("cam_wrist_left",)), cams=("cam_head", "cam_wrist_right"))
    with pytest.raises(SchemaError, match="claims"):
        _parse(answer(claims=(("grasped", "cam_wrist_left"),)), cams=("cam_head", "cam_wrist_right"))
    with pytest.raises(SchemaError, match="claims"):
        _parse(answer(claims=(("holding_tight", "cam_wrist_right"),)))


def test_edit_block_only_with_command_edit():
    d = answer("continue")
    d["edit"] = {"delta_position_m": [0, 0, 0.01], "delta_rotation_rad": [0, 0, 0], "gripper": "keep"}
    with pytest.raises(SchemaError, match="only with command edit"):
        _parse(d)


def test_f1_keep_and_revise():
    a = _parse(answer(diff="keep"), mode="F1")
    assert a.diff == "keep" and a.command == "continue" and a.edit is None
    b = _parse(answer("edit", diff="revise", execution="failed", dp=(0.0, 0.0, 0.02)), mode="F1")
    assert b.diff == "revise" and b.command == "edit"
    with pytest.raises(SchemaError, match="diff"):
        _parse(answer("continue"), mode="F1")


def test_garbage_and_bad_enums_are_schema_errors():
    with pytest.raises(SchemaError, match="no JSON"):
        parse_answer("I would continue.", "F0", CAMS, 1, 0.0, 3.0)
    with pytest.raises(SchemaError, match="confidence"):
        _parse(answer(confidence="very"))
    with pytest.raises(SchemaError, match="info_request"):
        _parse(answer(info="tilt_wrist"))


def test_params_guard_effort_and_mode():
    CoupleParams()
    with pytest.raises(ValueError, match="low"):
        CoupleParams(effort="high")
    with pytest.raises(ValueError, match="request_mode"):
        CoupleParams(request_mode="F2")
    with pytest.raises(ValueError, match="single_weight"):
        CoupleParams(single_weight=1.5)
    assert CoupleParams().to_json()["cameras"] == list(CAMS)


def test_prompt_roundtrip_and_image_labels():
    req = {"request_no": 3, "events": ["m7_critic_alarm"], "flow_state": {"last_command": {"command": "continue"}}}
    imgs = {"cam_head": b"\xff\xd8head", "cam_wrist_right": b"\xff\xd8wrist"}
    inp = build_input(req, imgs, CoupleParams(), "Put the red mug on the blue tray.")
    assert request_from_input(inp) == req
    content = inp[0]["content"]
    assert [c["text"] for c in content[1:] if c["type"] == "input_text"] == ["cam_head:", "cam_wrist_right:"]
    assert sum(1 for c in content if c["type"] == "input_image") == 2
    assert "cam_wrist_right" in content[0]["text"] and "0.05" in content[0]["text"]
    assert all(re.fullmatch(r"[0-9a-f]{12}", v) for v in PROMPT_ID.values()) and PROMPT_ID["F0"] != PROMPT_ID["F1"]


def test_vocabulary_matches_the_probe_when_it_is_importable():
    S = pytest.importorskip("harvest.astra_motion.schema")
    assert set(S.GRIPPER) == set(GRIPPER) and tuple(S.EXEC_STATUS) == EXEC_STATUS
    assert tuple(S.INTENT_STATUS) == INTENT_STATUS and tuple(S.CONFIDENCE) == CONFIDENCE
    assert tuple(S.DECISIONS) == COMMANDS
    assert S.EDIT_MAX_CM / 100.0 == pytest.approx(EDIT_MAX_M) and S.ROT_MAX_RAD == pytest.approx(ROT_MAX_RAD)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/couple/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'harvest.couple'`

- [ ] **Step 3: 구현**

`harvest/couple/__init__.py`:

```python
"""Astra–VLA coupling (spec docs/superpowers/specs/2026-09-26-astra-vla-coupling-design.md §11-§16, canon §84)."""
```

`harvest/couple/params.py`:

```python
"""Tuning constants of the Astra–VLA coupling (spec 2026-09-26 §11-§16, canon §84 supplement 2). The whole dataclass
is logged with every run (RuntimeConfig.couple_params -> CoupleDriver.summary()["params"]). Values marked PROBE are
defaults until the E-Astra-motion result (docs/stage3/results/astra_motion.md) sets them; probe_ref names that result."""
from __future__ import annotations

from dataclasses import asdict, dataclass

REQUEST_MODES = ("F0", "F1")
CAMERAS = ("cam_head", "cam_wrist_left", "cam_wrist_right")


@dataclass(frozen=True)
class CoupleParams:
    probe_ref: str = "none"
    # stream: one request in flight (canon §84 supp 2); effort low only (canon §82 supp 2)
    request_mode: str = "F1"  # PROBE prereg §7-1
    effort: str = "low"
    max_output_tokens: int = 1200
    timeout_s: float = 15.0  # PROBE: 1.5 x serial latency p95
    min_interval_s: float = 0.0  # E-Astra-necessity: pace a local model to Astra's latency p50
    phase_pause_s: float | None = None  # optional cost fallback (canon §84 supp 2); None = off
    event_window_s: float = 3.0  # spec §15: no pause for 3 s after an event
    fail_slow_after: int = 3  # spec §7: 3 failed calls in a row -> slow down
    slow_factor: float = 0.5
    slow_down_s: float = 2.0  # info_request slow_down (plan ruling 3)
    # answers
    stale_edit_s: float = 6.0  # spec §15 provisional; PROBE answer-age distribution
    latency_init_s: float = 3.0  # predicted-state horizon before the first answer; PROBE latency p50
    single_weight: float = 0.5  # spec §11: one answer 50 %, two agreeing answers 100 %
    same_dir_deg: float = 35.0  # PROBE prereg §4.2
    flip_deg: float = 90.0  # PROBE prereg §4.2
    small_edit_m: float = 0.005
    small_rot_rad: float = 0.05
    # offset (spec §11; PROBE prereg §4.2 smooth executor limits)
    ramp_min_s: float = 1.0
    ramp_max_s: float = 3.0
    decay_s: float = 0.5
    v_max: float = 0.08
    a_max: float = 0.32
    w_max: float = 1.5
    alpha_max: float = 6.0  # [가정] rotation acceleration cap
    contra_steps: int = 3  # VLA fast check: committed direction opposite for 3 steps (1 s) -> shrink
    contra_factor: float = 0.5
    stag_s: float = 2.0  # no progress along an active offset over this window
    stag_frac: float = 0.2
    # two layers (spec §5, §12; plan rulings 1-2)
    astra_fresh_s: float = 3.0
    mismatch_s: float = 1.0
    irrev_need_aligned: bool = False
    predict_cap_m: float = 0.10
    # cameras, overlay (spec §12-§13)
    cameras: tuple = CAMERAS
    active_arm: str = "right"
    overlay: bool = True  # PROBE prereg §4.4 overlay ablation
    trace_s: float = 2.5
    est_text_tokens: int = 2500  # PROBE prereg §8

    def __post_init__(self):
        if self.request_mode not in REQUEST_MODES:
            raise ValueError(f"request_mode {self.request_mode!r}: one of {REQUEST_MODES}")
        if self.effort != "low":
            raise ValueError("the coupling stream runs effort low only (canon §82 supplement 2)")
        if not 0.0 <= self.single_weight <= 1.0:
            raise ValueError(f"single_weight {self.single_weight}: in [0, 1]")
        if self.phase_pause_s is not None and not self.phase_pause_s > 0:
            raise ValueError("phase_pause_s: None (off) or > 0")
        if self.active_arm not in ("right", "left"):
            raise ValueError(f"active_arm {self.active_arm!r}")
        if not set(self.cameras) <= set(CAMERAS):
            raise ValueError(f"cameras {self.cameras}: subset of {CAMERAS}")

    def to_json(self) -> dict:
        d = asdict(self)
        d["cameras"] = list(self.cameras)
        return d
```

`harvest/couple/schema.py`:

```python
"""Astra coupling answer schema (astra-couple@v1): general control only (spec revision, user-log 83) with the
GPT-as-Policy gate vocabulary (gate_assessment.py). parse_answer checks structure only and raises SchemaError with
every problem found; the meaning checks (age, uncertainty, takeover reason, wrist evidence) are gate.py."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field

import numpy as np

SCHEMA_ID = "astra-couple@v1"
EXEC_STATUS = ("not_started", "progressing", "failed", "uncertain", "recovered")
INTENT_STATUS = ("aligned", "misaligned", "uncertain")
CONFIDENCE = ("low", "medium", "high")
COMMANDS = ("continue", "edit", "stop")
DIFFS = ("keep", "revise")
GRIPPER = ("keep", "open", "close")
INFO_REQUESTS = ("none", "slow_down")
CLAIM_KINDS = ("grasp_ready", "grasped", "not_grasped", "released", "placed", "contact")
EDIT_MAX_M, ROT_MAX_RAD = 0.05, 0.35
TOL = 1e-9


class SchemaError(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


@dataclass
class Edit:
    dp: np.ndarray
    dr: np.ndarray
    gripper: str

    def vec6(self) -> np.ndarray:
        return np.r_[self.dp, self.dr].astype(float)

    def to_json(self) -> dict:
        return {"delta_position_m": [round(float(v), 4) for v in self.dp],
                "delta_rotation_rad": [round(float(v), 4) for v in self.dr], "gripper": self.gripper}


@dataclass
class AstraAnswer:
    request_no: int
    t_state: float
    t_deliver: float
    diff: str | None
    command: str
    edit: Edit | None
    execution: str
    intent: str
    confidence: str
    evidence: str
    evidence_views: tuple
    claims: tuple
    task_progress: dict
    info_request: str = "none"
    gate: str = "raw"
    takeover_ok: bool = False
    progress_trusted: bool = True
    notes: list = field(default_factory=list)

    @property
    def age(self) -> float:
        return self.t_deliver - self.t_state


def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise SchemaError(["no JSON object in the answer"])
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise SchemaError([f"JSON: {e.msg}"]) from None
    if not isinstance(d, dict):
        raise SchemaError(["the answer is not a JSON object"])
    return d


def _vec3(x, lim: float, name: str, err: list):
    ok = isinstance(x, list) and len(x) == 3 and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in x)
    if not ok:
        err.append(f"{name}: 3 finite numbers")
        return None
    v = np.asarray(x, float)
    if float(np.linalg.norm(v)) > lim + TOL:
        err.append(f"{name}: norm {float(np.linalg.norm(v)):.4f} > {lim}")
        return None
    return v


def _progress_ok(tp) -> bool:
    return (isinstance(tp, dict)
            and all(isinstance(tp.get(k), list) and all(isinstance(s, str) and s.strip() for s in tp[k])
                    for k in ("verified_completed", "remaining"))
            and isinstance(tp.get("currently_attempting"), str) and bool(tp["currently_attempting"].strip()))


def parse_answer(text: str, mode: str, sent_cameras, request_no: int, t_state: float,
                 t_deliver: float) -> AstraAnswer:
    d = extract_json(text)
    sent = tuple(sent_cameras)
    err = []
    a = d.get("assessment")
    if not isinstance(a, dict):
        raise SchemaError(["assessment: object required"])
    tp = a.get("task_progress")
    if not _progress_ok(tp):
        err.append("assessment.task_progress: verified_completed[], currently_attempting, remaining[]")
    for k, allowed in (("execution", EXEC_STATUS), ("intent", INTENT_STATUS), ("confidence", CONFIDENCE)):
        if a.get(k) not in allowed:
            err.append(f"assessment.{k}: one of {allowed}")
    ev = a.get("evidence", "")
    if not isinstance(ev, str):
        err.append("assessment.evidence: string")
        ev = ""
    views = a.get("evidence_views", [])
    if not (isinstance(views, list) and all(v in sent for v in views)):
        err.append(f"assessment.evidence_views: subset of the cameras sent {list(sent)}")
        views = []
    claims = []
    raw_claims = a.get("claims", [])
    for c in raw_claims if isinstance(raw_claims, list) else [None]:
        if not (isinstance(c, dict) and c.get("kind") in CLAIM_KINDS and c.get("view") in sent):
            err.append(f"assessment.claims: {{kind in {CLAIM_KINDS}, view in the cameras sent}}")
            break
        claims.append((c["kind"], c["view"]))
    diff = None
    if mode == "F1":
        diff = d.get("diff")
        if diff not in DIFFS:
            err.append(f"diff: one of {DIFFS}")
    cmd = "continue" if diff == "keep" else d.get("command")
    if cmd not in COMMANDS:
        err.append(f"command: one of {COMMANDS}")
    edit = None
    if cmd == "edit":
        e = d.get("edit")
        if not isinstance(e, dict):
            err.append("edit: object required with command edit")
        else:
            dp = _vec3(e.get("delta_position_m"), EDIT_MAX_M, "edit.delta_position_m", err)
            dr = _vec3(e.get("delta_rotation_rad", [0.0, 0.0, 0.0]), ROT_MAX_RAD, "edit.delta_rotation_rad", err)
            g = e.get("gripper", "keep")
            if g not in GRIPPER:
                err.append(f"edit.gripper: one of {GRIPPER}")
            elif dp is not None and dr is not None:
                edit = Edit(dp, dr, g)
    elif d.get("edit") not in (None, {}):
        err.append("edit: only with command edit")
    info = d.get("info_request", "none")
    if info not in INFO_REQUESTS:
        err.append(f"info_request: one of {INFO_REQUESTS}")
    if err:
        raise SchemaError(err)
    return AstraAnswer(request_no=request_no, t_state=float(t_state), t_deliver=float(t_deliver), diff=diff,
                       command=cmd, edit=edit, execution=a["execution"], intent=a["intent"],
                       confidence=a["confidence"], evidence=ev, evidence_views=tuple(views), claims=tuple(claims),
                       task_progress=tp, info_request=info)
```

`harvest/couple/prompt.py`:

```python
"""Astra coupling prompt astra-couple@v1: general control only (continue / edit / stop + assessment, GPT-as-Policy
gate wording), three labelled cameras with the wrist-evidence rule (spec §12), the code-drawn overlay legend
(spec §13, plan ruling 4: robot-frame axes at the tip). The static text comes first (prompt-cache friendly), the
request JSON (sorted keys) between REQ_OPEN / REQ_CLOSE, then the labelled images."""
from __future__ import annotations

import base64
import hashlib
import json

REQ_OPEN, REQ_CLOSE = "<request>", "</request>"
WRIST_OF = {"right": "cam_wrist_right", "left": "cam_wrist_left"}
TEMPLATE = (
    "You supervise a robot doing this task: {task}\n"
    "A fast policy (VLA) moves the {arm} gripper every 0.33 s and never waits for you. Your answer arrives seconds "
    "after these images were taken: judge the situation at predicted_ee_at_arrival.\n"
    "Cameras (each image is preceded by its name): cam_head = overview for layout, path and target choice; it is NOT "
    "enough on its own for contact, grasp or release (perspective makes fingers and objects overlap). cam_wrist_left "
    "/ cam_wrist_right = close-up of each gripper for contact, grasp, release and alignment. A claim that something "
    "is grasped, released, placed or touching is valid only with the active wrist camera ({wrist}) as evidence; if "
    "head and wrist disagree, trust the wrist.\n"
    "Overlay (drawn by code from the robot's own kinematics, never from object ground truth): white ring = gripper "
    "tip now; fading yellow line = the tip over the last {trace_s:g} s; cyan arrow = the motion the policy has "
    "committed for the next 0.5 s; magenta arrow = your previous correction still being applied; short red / green "
    "/ blue lines at the tip = robot frame x / y / z. On wrist images the overlay is only a small box in the "
    "top-right corner.\n"
    "Assess two things: (1) execution of the last seconds: not_started | progressing | failed | uncertain | "
    "recovered; (2) intent: does the policy's current motion pursue the right subgoal? aligned | misaligned | "
    "uncertain.\n"
    "Commands: continue = let the policy go on. edit = one short correction of the gripper tip in the robot frame: "
    "|delta_position_m| <= 0.05, |delta_rotation_rad| <= 0.35, gripper keep | open | close. An edit requires "
    "execution=failed or intent=misaligned; uncertainty alone or an imperfect pose is not a reason to take over. "
    "stop = the whole task is complete (needs a wrist claim placed or released). info_request slow_down asks the "
    "robot to move slower for 2 s when you need a clearer view; otherwise none.\n"
    "{mode_rules}\n"
    "{req_open}\n{request_json}\n{req_close}\n"
    "Answer with one JSON object only, in this form:\n{answer_form}")
MODE_RULES = {
    "F0": "Give the full command every time. A new edit is applied at half strength until your next answer repeats "
          "it.",
    "F1": "flow_state.last_command is the command being applied now. Answer diff=keep to confirm it, or "
          "diff=revise with a new command. A revised edit is applied at half strength until your next answer "
          "confirms it with keep."}
_ASSESS = ('"assessment": {"task_progress": {"verified_completed": ["..."], "currently_attempting": "...", '
           '"remaining": ["..."]}, "execution": "...", "intent": "...", "confidence": "low|medium|high", '
           '"evidence": "...", "evidence_views": ["cam_..."], "claims": [{"kind": '
           '"grasp_ready|grasped|not_grasped|released|placed|contact", "view": "cam_..."}]}')
_CMD = ('"command": "continue|edit|stop", "edit": {"delta_position_m": [dx, dy, dz], "delta_rotation_rad": '
        '[rx, ry, rz], "gripper": "keep|open|close"} (only with command edit, else null), '
        '"info_request": "none|slow_down"')
ANSWER_FORM = {"F0": "{" + _ASSESS + ", " + _CMD + "}",
               "F1": "{" + _ASSESS + ', "diff": "keep|revise", ' + _CMD + " (command only with diff revise)}"}
PROMPT_ID = {m: hashlib.sha256((TEMPLATE + MODE_RULES[m] + ANSWER_FORM[m]).encode()).hexdigest()[:12]
             for m in ("F0", "F1")}


def build_input(req: dict, images: dict, p, task: str) -> list:
    text = TEMPLATE.format(task=task, arm=p.active_arm, wrist=WRIST_OF[p.active_arm], trace_s=p.trace_s,
                           mode_rules=MODE_RULES[p.request_mode], req_open=REQ_OPEN,
                           request_json=json.dumps(req, sort_keys=True, ensure_ascii=False), req_close=REQ_CLOSE,
                           answer_form=ANSWER_FORM[p.request_mode])
    content = [{"type": "input_text", "text": text}]
    for cam in p.cameras:
        b = images.get(cam)
        if b is None:
            continue
        content.append({"type": "input_text", "text": f"{cam}:"})
        content.append({"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(b).decode()})
    return [{"role": "user", "content": content}]


def request_from_input(inp: list) -> dict:
    text = inp[-1]["content"][0]["text"]
    i = text.index(REQ_OPEN) + len(REQ_OPEN)
    return json.loads(text[i:text.index(REQ_CLOSE)])
```

`harvest/couple/mock.py`(이 Task에서는 답 생성기만; Task 4가 모의 클라이언트를 더한다):

```python
"""Mock Astra for the coupling stream: answer() builds schema-valid answer dicts (tests, dry runs); no paid call."""
from __future__ import annotations


def answer(command: str = "continue", *, execution: str = "progressing", intent: str = "aligned",
           confidence: str = "high", evidence: str = "right wrist view: gripper above the mug",
           views=("cam_wrist_right",), claims=(), dp=(0.0, 0.0, 0.0), dr=(0.0, 0.0, 0.0), gripper: str = "keep",
           diff: str | None = None, info: str = "none", done=()) -> dict:
    d = {"assessment": {"task_progress": {"verified_completed": list(done), "currently_attempting": "pick the mug",
                                          "remaining": ["place the mug on the tray"]},
                        "execution": execution, "intent": intent, "confidence": confidence, "evidence": evidence,
                        "evidence_views": list(views), "claims": [{"kind": k, "view": v} for k, v in claims]},
         "info_request": info}
    if diff is not None:
        d["diff"] = diff
    if diff != "keep":
        d["command"] = command
        if command == "edit":
            d["edit"] = {"delta_position_m": list(dp), "delta_rotation_rad": list(dr), "gripper": gripper}
    return d
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/couple/test_schema.py -v`
Expected: PASS(탐침 모듈이 없으면 마지막 시험은 SKIP).

- [ ] **Step 5: 커밋**

`msg_task1.txt`(Write 도구) 첫 줄 `couple: coupling params, answer schema, prompt astra-couple@v1 (plan 2026-09-26 Task 1)` + attribution 두 줄.

```bash
git -c safe.directory=D:/qdd add harvest/couple tests/couple
git -c safe.directory=D:/qdd commit -F D:/tools/scratch_qdd/plan_coupling/msg_task1.txt
```

---

### Task 2: 의미 게이트 (나이·불확실·개입 자격·근거·손목 규칙)

**Files:**
- Create: `harvest/couple/gate.py`
- Test: `tests/couple/test_gate.py`

**Interfaces:**
- Consumes: `AstraAnswer`, `parse_answer`(Task 1), `CoupleParams`, `mock.answer`.
- Produces: `gate_answer(a: AstraAnswer, p: CoupleParams, t1: dict) -> AstraAnswer` — `a.gate ∈ {"ok","stale","uncertain","no_takeover_reason","no_evidence","stop_without_wrist_claim"}`, `a.command`이 `continue`로 내려갈 수 있음(그때 `a.edit = None`), `a.takeover_ok`, `a.progress_trusted`, 걸러진 `a.claims`, `a.notes`. `ACTIVE_WRIST: dict`.

- [ ] **Step 1: 실패하는 시험**

`tests/couple/test_gate.py`:

```python
import json

from harvest.couple.gate import gate_answer
from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.schema import parse_answer

P = CoupleParams()


def _g(d, t1=None, age=2.0, mode="F0"):
    a = parse_answer(json.dumps(d), mode, P.cameras, 1, 10.0, 10.0 + age)
    return gate_answer(a, P, t1 or {})


def test_uncertain_or_low_confidence_edit_becomes_continue():
    a = _g(answer("edit", execution="uncertain", intent="misaligned", dp=(0, 0, 0.02)))
    assert (a.command, a.gate, a.edit) == ("continue", "uncertain", None)
    b = _g(answer("edit", execution="failed", confidence="low", dp=(0, 0, 0.02)))
    assert (b.command, b.gate) == ("continue", "uncertain")


def test_edit_needs_failed_or_misaligned():
    a = _g(answer("edit", execution="progressing", intent="aligned", dp=(0, 0, 0.02)))
    assert (a.command, a.gate) == ("continue", "no_takeover_reason")
    b = _g(answer("edit", execution="failed", dp=(0, 0, 0.02)))
    assert (b.command, b.gate, b.takeover_ok) == ("edit", "ok", True)


def test_stale_edit_keeps_only_the_assessment():
    a = _g(answer("edit", execution="failed", dp=(0, 0, 0.02)), age=6.5)
    assert (a.command, a.gate, a.edit) == ("continue", "stale", None) and a.execution == "failed"


def test_edit_without_evidence_is_dropped():
    a = _g(answer("edit", execution="failed", evidence="", dp=(0, 0, 0.02)))
    assert (a.command, a.gate) == ("continue", "no_evidence")
    b = _g(answer("edit", execution="failed", views=(), dp=(0, 0, 0.02)))
    assert b.gate == "no_evidence"


def test_claims_need_the_active_wrist_and_agree_with_t1():
    a = _g(answer(claims=(("grasped", "cam_head"), ("grasped", "cam_wrist_left"), ("grasped", "cam_wrist_right"))),
           t1={"holding_t": True})
    assert a.claims == (("grasped", "cam_wrist_right"),)
    assert "head_only_claim:grasped" in a.notes and "other_wrist_claim:grasped" in a.notes
    b = _g(answer(claims=(("grasped", "cam_wrist_right"),)), t1={"holding_t": False})
    assert b.claims == () and "claim_vs_t1:grasped" in b.notes
    c = _g(answer(claims=(("placed", "cam_wrist_right"),)), t1={"holding_t": True})
    assert c.claims == ()
    d = _g(answer(claims=(("grasped", "cam_wrist_right"),)), t1={"holding_t": None})
    assert d.claims == (("grasped", "cam_wrist_right"),)


def test_stop_needs_a_wrist_placed_or_released_claim():
    a = _g(answer("stop", execution="progressing"))
    assert (a.command, a.gate) == ("continue", "stop_without_wrist_claim")
    b = _g(answer("stop", claims=(("placed", "cam_wrist_right"),)), t1={"holding_t": False})
    assert (b.command, b.gate) == ("stop", "ok")


def test_progress_claims_without_wrist_view_are_not_trusted():
    a = _g(answer(done=("grasped the mug",), views=("cam_head",)))
    assert a.progress_trusted is False and "progress_claim_without_wrist" in a.notes
    b = _g(answer(done=("grasped the mug",)))
    assert b.progress_trusted is True


def test_keep_takeover_flag():
    a = _g(answer(diff="keep", execution="failed"), mode="F1")
    assert a.command == "continue" and a.takeover_ok is True and a.gate == "ok"
    b = _g(answer(diff="keep", execution="failed"), mode="F1", age=7.0)
    assert b.takeover_ok is False and "stale_keep" in b.notes
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/couple/test_gate.py -v` → FAIL(`No module named 'harvest.couple.gate'`).

- [ ] **Step 3: 구현** — `harvest/couple/gate.py`:

```python
"""Meaning checks of one Astra coupling answer (spec §11, §12, §15; GPT-as-Policy gate_assessment.validate_assessment):
  - claims: kept only from the ACTIVE wrist camera and when not contradicted by the T1 proprio holding value
    (wrist first + proprio cross-check, spec §12); head-only / other-wrist / contradicted claims are logged in notes;
  - task_progress with grasp / lift / place words is trusted only when the active wrist is among the evidence views;
  - edit / stop: stale (answer age > stale_edit_s, spec §15) -> continue (assessment kept); uncertain execution or
    intent or confidence low -> continue (spec §11); an edit needs execution failed or intent misaligned; edit and
    stop need evidence text + views; stop needs a wrist placed / released claim (plan ruling 8).
takeover_ok (used by the layer for F1 keep) = a takeover reason, not uncertain, evidence present, not stale."""
from __future__ import annotations

import re

ACTIVE_WRIST = {"right": "cam_wrist_right", "left": "cam_wrist_left"}
PROGRESS_WORDS = re.compile(r"grasp|hold|held|pick|lift|place|put|release|contact|touch", re.I)
_T1_CONTRA = {"grasped": True, "released": False, "placed": False, "not_grasped": False}  # claim valid if holding ==


def gate_answer(a, p, t1: dict):
    wrist = ACTIVE_WRIST[p.active_arm]
    keep = []
    for kind, view in a.claims:
        if not view.startswith("cam_wrist"):
            a.notes.append(f"head_only_claim:{kind}")
            continue
        if view != wrist:
            a.notes.append(f"other_wrist_claim:{kind}")
            continue
        h = t1.get("holding_t")
        if kind in _T1_CONTRA and h is not None and bool(h) != _T1_CONTRA[kind]:
            a.notes.append(f"claim_vs_t1:{kind}")
            continue
        keep.append((kind, view))
    a.claims = tuple(keep)
    done = " ".join(a.task_progress.get("verified_completed", []))
    a.progress_trusted = not (PROGRESS_WORDS.search(done) and wrist not in a.evidence_views)
    if not a.progress_trusted:
        a.notes.append("progress_claim_without_wrist")
    uncertain = a.execution == "uncertain" or a.intent == "uncertain" or a.confidence == "low"
    reason = a.execution == "failed" or a.intent == "misaligned"
    has_ev = bool(a.evidence.strip()) and bool(a.evidence_views)
    stale = a.age > p.stale_edit_s + 1e-9
    a.takeover_ok = reason and not uncertain and has_ev and not stale
    if a.diff == "keep" and stale:
        a.notes.append("stale_keep")
    gate = "ok"
    if a.command in ("edit", "stop"):
        if stale:
            gate = "stale"
        elif uncertain:
            gate = "uncertain"
        elif a.command == "edit" and not reason:
            gate = "no_takeover_reason"
        elif not has_ev:
            gate = "no_evidence"
        elif a.command == "stop" and not any(k in ("placed", "released") for k, _ in a.claims):
            gate = "stop_without_wrist_claim"
    if gate != "ok":
        a.command, a.edit = "continue", None
    a.gate = gate
    return a
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_gate.py -v` → PASS.
- [ ] **Step 5: 커밋** — `msg_task2.txt` 첫 줄 `couple: answer gate (age, uncertainty, takeover reason, wrist evidence) (Task 2)`; `git add harvest/couple/gate.py tests/couple/test_gate.py` 후 `commit -F`.

---

### Task 3: 가격표와 실험 비용 장부

**Files:**
- Create: `harvest/couple/cost.py`
- Test: `tests/couple/test_cost.py`

**Interfaces:**
- Produces: `TOK_HEAD=302, TOK_WRIST=134`; `estimate_input_tokens(text_tokens: int, cams) -> int`; `PriceTable(model, date, usd_per_mtok_input, usd_per_mtok_cached_input, usd_per_mtok_output, krw_per_usd, source)` + `load(path)`, `free()`, `is_free`, `krw(usage) -> float`, `krw_upper(est_in, max_out) -> float`; `CostLedger(path: str|None, budget_krw, prices, stop_frac=0.8, run_id="")` + `refresh()`, `can_send(est_krw) -> bool`, `reserve(key, est_krw)`, `charge(key, usage: dict|None, meta=None) -> float`, `finalize(prefix="")`, `stopped`, `limit`, `spent`, `reserved`, `state() -> dict`.
- 장부 행(JSONL): `{t_utc, run_id, model, price_date, budget_krw, key, kind: charge|no_usage|unanswered, cost_krw, usage, ...meta}`. `spent`는 파일을 다시 읽어서만 늘어난다(여러 프로세스 공유).

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_cost.py`:

```python
import json

import pytest

from harvest.couple.cost import CostLedger, PriceTable, estimate_input_tokens

TEST = PriceTable(model="test", date="2026-09-26", usd_per_mtok_input=2.0, usd_per_mtok_cached_input=0.5,
                  usd_per_mtok_output=8.0, krw_per_usd=1400.0, source="unit test (not a real price)")


def test_price_math_counts_cached_input_separately():
    u = {"input_tokens": 3000, "input_tokens_details": {"cached_tokens": 1000}, "output_tokens": 800}
    assert TEST.krw(u) == pytest.approx((2000 * 2.0 + 1000 * 0.5 + 800 * 8.0) / 1e6 * 1400.0)
    assert TEST.krw_upper(3000, 1200) == pytest.approx((3000 * 2.0 + 1200 * 8.0) / 1e6 * 1400.0)
    assert estimate_input_tokens(2500, ["cam_head", "cam_wrist_right", "cam_wrist_left"]) == 2500 + 302 + 2 * 134


def test_load_refuses_incomplete_tables(tmp_path):
    p = tmp_path / "prices.json"
    p.write_text(json.dumps({"model": "gpt-6-astra", "date": "2026-09-26", "usd_per_mtok_input": 1.0}))
    with pytest.raises(ValueError, match="lacks"):
        PriceTable.load(str(p))
    d = {f: 1.0 for f in ("usd_per_mtok_input", "usd_per_mtok_cached_input", "usd_per_mtok_output", "krw_per_usd")}
    p.write_text(json.dumps({**d, "model": "gpt-6-astra", "date": "26/09/2026", "source": "x"}))
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        PriceTable.load(str(p))
    p.write_text(json.dumps({**d, "model": "gpt-6-astra", "date": "2026-09-26", "source": "x"}))
    assert PriceTable.load(str(p)).usd_per_mtok_output == 1.0


def test_reservations_block_at_80_percent_and_charges_stop(tmp_path):
    L = CostLedger(str(tmp_path / "l.jsonl"), 100.0, TEST)
    L.reserve("e1:1", 50.0)
    assert L.can_send(30.0) and not L.can_send(31.0)
    L.charge("e1:1", None)  # no usage reported -> the reservation is charged
    assert L.spent == pytest.approx(50.0) and not L.stopped
    L.reserve("e1:2", 30.0)
    L.charge("e1:2", {"input_tokens": 0, "output_tokens": 3000})  # 33.6 KRW -> 83.6 >= 80
    assert L.stopped and not L.can_send(0.0)


def test_two_ledgers_on_one_file_see_each_other(tmp_path):
    f = str(tmp_path / "shared.jsonl")
    A, B = CostLedger(f, 100.0, TEST, run_id="standard"), CostLedger(f, 100.0, TEST, run_id="dr")
    A.reserve("a:1", 70.0)
    A.charge("a:1", None)
    assert B.can_send(10.0) and not B.can_send(10.1)
    B.reserve("b:1", 10.0)
    B.charge("b:1", None)
    assert A.can_send(0.0) is False and A.stopped


def test_finalize_charges_unanswered_reservations_by_prefix(tmp_path):
    L = CostLedger(str(tmp_path / "l.jsonl"), 100.0, TEST)
    L.reserve("e1:5", 4.0)
    L.reserve("e2:1", 3.0)
    L.finalize(prefix="e1:")
    assert L.spent == pytest.approx(4.0) and list(L.reserved) == ["e2:1"]
    rows = [json.loads(x) for x in open(tmp_path / "l.jsonl", encoding="utf-8")]
    assert rows[-1]["kind"] == "unanswered" and rows[-1]["key"] == "e1:5"


def test_free_prices_never_stop_and_priced_needs_a_budget():
    L = CostLedger(None, 0.0, PriceTable.free())
    L.reserve("k", L.prices.krw_upper(5000, 1200))
    assert L.can_send(1e9) and L.charge("k", {"input_tokens": 5000, "output_tokens": 900}) == 0.0
    with pytest.raises(ValueError, match="budget"):
        CostLedger(None, 0.0, TEST)
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_cost.py -v` → FAIL(모듈 없음).

- [ ] **Step 3: 구현** — `harvest/couple/cost.py`:

```python
"""Paid-call cost ledger of the coupling stream (canon §82 supplement: ~100,000 KRW in total; spec §15: a budget cap
per experiment, written in its pre-registration, stop and report at 80 %). Prices come from the run day's price table
(a JSON file, never a constant in code). The ledger is an append-only JSONL file shared by the Isaac workers of one
experiment: every process re-reads new rows before deciding to send (spent grows only from the file), so parallel
workers see each other's charges; an in-flight reservation is local to its process (overshoot <= one call per
worker, inside the 20 % margin). Requests are reserved at the upper bound (no cache credit, max output tokens);
an answer replaces its reservation by the billed usage, a missing usage or a never-answered request is charged at
the reservation."""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
from dataclasses import dataclass, fields

TOK_HEAD, TOK_WRIST = 302, 134  # PROBE prereg §8 (32 px patches x 1.2: head 672x376, wrist 424x240)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def estimate_input_tokens(text_tokens: int, cams) -> int:
    return int(text_tokens) + sum(TOK_HEAD if c == "cam_head" else TOK_WRIST for c in cams)


@dataclass(frozen=True)
class PriceTable:
    model: str
    date: str
    usd_per_mtok_input: float
    usd_per_mtok_cached_input: float
    usd_per_mtok_output: float
    krw_per_usd: float
    source: str

    @classmethod
    def load(cls, path: str) -> "PriceTable":
        d = json.load(open(path, encoding="utf-8"))
        miss = [f.name for f in fields(cls) if f.name not in d]
        if miss:
            raise ValueError(f"{path}: price table lacks {miss}")
        if not _DATE.match(str(d["date"])):
            raise ValueError(f"{path}: date {d['date']!r} is not YYYY-MM-DD")
        for k in ("usd_per_mtok_input", "usd_per_mtok_output", "krw_per_usd"):
            if not float(d[k]) > 0:
                raise ValueError(f"{path}: {k} must be > 0")
        if float(d["usd_per_mtok_cached_input"]) < 0:
            raise ValueError(f"{path}: usd_per_mtok_cached_input must be >= 0")
        return cls(model=str(d["model"]), date=str(d["date"]), usd_per_mtok_input=float(d["usd_per_mtok_input"]),
                   usd_per_mtok_cached_input=float(d["usd_per_mtok_cached_input"]),
                   usd_per_mtok_output=float(d["usd_per_mtok_output"]), krw_per_usd=float(d["krw_per_usd"]),
                   source=str(d["source"]))

    @classmethod
    def free(cls) -> "PriceTable":
        return cls("mock", "1970-01-01", 0.0, 0.0, 0.0, 1.0, "mock / local model: no charge")

    @property
    def is_free(self) -> bool:
        return self.usd_per_mtok_input == 0 and self.usd_per_mtok_output == 0 and self.usd_per_mtok_cached_input == 0

    def krw(self, usage: dict | None) -> float:
        u = usage or {}
        inp = int(u.get("input_tokens", 0) or 0)
        cached = int((u.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0)
        out = int(u.get("output_tokens", 0) or 0)
        usd = (max(inp - cached, 0) * self.usd_per_mtok_input + cached * self.usd_per_mtok_cached_input
               + out * self.usd_per_mtok_output) / 1e6
        return usd * self.krw_per_usd

    def krw_upper(self, est_in: int, max_out: int) -> float:
        return self.krw({"input_tokens": est_in, "output_tokens": max_out})


class CostLedger:
    def __init__(self, path: str | None, budget_krw: float, prices: PriceTable, stop_frac: float = 0.8,
                 run_id: str = ""):
        if not prices.is_free and not budget_krw > 0:
            raise ValueError("a priced ledger needs budget_krw > 0 (spec §15: the cap is pre-registered per experiment)")
        if not 0 < stop_frac <= 1:
            raise ValueError(f"stop_frac {stop_frac}: in (0, 1]")
        self.path, self.budget, self.prices = path, float(budget_krw), prices
        self.stop_frac, self.run_id = float(stop_frac), run_id
        self.spent, self._off, self.reserved = 0.0, 0, {}
        self.refresh()

    @property
    def limit(self) -> float:
        return self.stop_frac * self.budget

    @property
    def stopped(self) -> bool:
        return self.budget > 0 and self.spent >= self.limit - 1e-9

    def refresh(self) -> None:
        if not self.path or not os.path.exists(self.path):
            return
        with open(self.path, "rb") as f:
            f.seek(self._off)
            data = f.read()
        end = data.rfind(b"\n")
        if end < 0:
            return
        for line in data[:end + 1].splitlines():
            if line.strip():
                self.spent += float(json.loads(line)["cost_krw"])
        self._off += end + 1

    def can_send(self, est_krw: float) -> bool:
        self.refresh()
        if self.budget <= 0:  # free prices only (__init__ refuses a priced ledger without a budget)
            return True
        return not self.stopped and self.spent + sum(self.reserved.values()) + est_krw <= self.limit + 1e-9

    def reserve(self, key: str, est_krw: float) -> None:
        self.reserved[key] = float(est_krw)

    def charge(self, key: str, usage: dict | None, meta: dict | None = None) -> float:
        est = self.reserved.pop(key, 0.0)
        cost = self.prices.krw(usage) if usage else est
        self._append({**(meta or {}), "key": key, "kind": "charge" if usage else "no_usage", "cost_krw": cost,
                      "usage": usage or {}})
        return cost

    def finalize(self, prefix: str = "") -> None:
        for k in [k for k in self.reserved if k.startswith(prefix)]:
            self._append({"key": k, "kind": "unanswered", "cost_krw": self.reserved.pop(k), "usage": {}})

    def _append(self, row: dict) -> None:
        row = {"t_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "run_id": self.run_id,
               "model": self.prices.model, "price_date": self.prices.date, "budget_krw": self.budget, **row}
        if not self.path:
            self.spent += float(row["cost_krw"])
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        self.refresh()

    def state(self) -> dict:
        return {"spent_krw": round(self.spent, 3), "reserved_krw": round(sum(self.reserved.values()), 3),
                "budget_krw": self.budget, "limit_krw": round(self.limit, 3), "stopped": self.stopped,
                "price_date": self.prices.date, "price_model": self.prices.model}
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_cost.py -v` → PASS.
- [ ] **Step 5: 커밋** — `msg_task3.txt` 첫 줄 `couple: price table and shared experiment cost ledger with 80 % stop (Task 3)`.

---

### Task 4: 직렬 흐름(동시 1개)과 모의 Astra 클라이언트

**Files:**
- Create: `harvest/couple/stream.py`
- Modify: `harvest/couple/mock.py`(끝에 클래스 추가)
- Test: `tests/couple/test_stream.py`

**Interfaces:**
- Consumes: `CoupleParams`, `CostLedger`, `PriceTable`(Task 3), `prompt.request_from_input`(Task 1), `clients.astra.AstraRecord`.
- Produces: `SerialStream(p, ledger)` — `flag(name, now)`, `next_send(now, contact_window: bool, est_krw) -> tuple[bool, str]`(이유 `send|inflight|min_interval|pause|budget`), `sent(now) -> tuple[int, list[str]]`, `timed_out(now) -> int|None`, `is_late(no) -> bool`, `delivered(no, now, ok: bool, latency: float)`, `L_hat`, `slowed(now) -> bool`, `request_slow(now)`, 속성 `n_sent, fail_streak, max_inflight, max_outstanding, counts`. `ScriptedCoupleAstra(script, latency_s=3.0, usage=None)` — `.call(inp, effort, max_output_tokens, meta) -> AstraRecord`, `.calls: list[{"req","meta"}]`, `.synthetic_latency`, `.model`.

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_stream.py`:

```python
import json

import pytest

from harvest.couple.cost import CostLedger, PriceTable
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.params import CoupleParams
from harvest.couple.prompt import build_input
from harvest.couple.stream import SerialStream

TEST = PriceTable("test", "2026-09-26", 2.0, 0.5, 8.0, 1400.0, "unit test")


def _s(**kw):
    return SerialStream(CoupleParams(**kw), CostLedger(None, 0.0, PriceTable.free()))


def test_one_request_in_flight_and_next_goes_on_answer():
    s = _s()
    assert s.next_send(0.0, False, 0.0) == (True, "send")
    no, ev = s.sent(0.0)
    assert (no, ev) == (1, [])
    assert s.next_send(1.0, True, 0.0) == (False, "inflight")
    s.delivered(1, 3.2, True, 3.2)
    assert s.next_send(3.2, False, 0.0) == (True, "send") and s.L_hat == pytest.approx(3.2)
    assert s.max_inflight == 1 and s.max_outstanding == 1


def test_events_ride_on_the_next_request_only_once():
    s = _s()
    s.sent(0.0)
    s.flag("m7_critic_alarm", 0.5)
    s.flag("m7_critic_alarm", 0.6)
    s.flag("b_contradict", 0.7)
    s.delivered(1, 3.0, True, 3.0)
    assert s.sent(3.0) == (2, ["m7_critic_alarm", "b_contradict"])
    s.delivered(2, 6.0, True, 3.0)
    assert s.sent(6.0) == (3, [])


def test_timeout_frees_the_slot_late_answer_is_marked_and_failures_slow_down():
    s = _s(timeout_s=15.0)
    s.sent(0.0)
    assert s.timed_out(15.0) is None and s.timed_out(15.02) == 1
    assert s.next_send(15.02, False, 0.0) == (True, "send")
    s.sent(15.02)
    assert s.max_outstanding == 2 and s.is_late(1) and not s.is_late(2)
    for t in (30.1, 45.2):
        s.timed_out(t)
        s.sent(t)
    assert s.fail_streak == 3 and s.slowed(45.2)
    s.delivered(4, 47.0, True, 1.8)
    assert not s.slowed(47.0)
    s.request_slow(47.0)
    assert s.slowed(48.9) and not s.slowed(49.1)


def test_optional_phase_pause_and_min_interval():
    s = _s(phase_pause_s=3.0)
    s.sent(0.0)
    s.delivered(1, 1.0, True, 1.0)
    assert s.next_send(1.5, False, 0.0) == (False, "pause")
    assert s.next_send(1.5, True, 0.0) == (True, "send")
    s.flag("no_progress", 1.2)
    assert s.next_send(1.5, False, 0.0) == (True, "send")
    m = _s(min_interval_s=4.0)
    m.sent(0.0)
    m.delivered(1, 1.0, True, 1.0)
    assert m.next_send(3.9, False, 0.0) == (False, "min_interval") and m.next_send(4.0, False, 0.0)[0]


def test_budget_blocks_the_send():
    s = SerialStream(CoupleParams(), CostLedger(None, 1.0, TEST))
    assert s.next_send(0.0, False, 0.9) == (False, "budget")


def test_scripted_astra_answers_in_order_and_sees_the_request():
    ast = ScriptedCoupleAstra([answer("continue"), answer("edit", execution="failed", dp=(0, 0, 0.01))],
                              latency_s=2.0, usage={"input_tokens": 3000, "output_tokens": 900})
    p = CoupleParams(request_mode="F0")
    for n in (1, 2, 3):
        rec = ast.call(build_input({"request_no": n}, {}, p, "task"), "low", 1200, {"couple_no": n})
        assert rec.usage["output_tokens"] == 900 and rec.effort == "low"
    assert [c["req"]["request_no"] for c in ast.calls] == [1, 2, 3]
    assert json.loads(rec.output_text)["command"] == "edit" and ast.synthetic_latency == 2.0
    dyn = ScriptedCoupleAstra(lambda req: answer("stop" if req["request_no"] > 1 else "continue"))
    assert json.loads(dyn.call(build_input({"request_no": 2}, {}, p, "t"), "low", 10, {}).output_text)["command"] == "stop"
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_stream.py -v` → FAIL(모듈 없음).

- [ ] **Step 3: 구현** — `harvest/couple/stream.py`:

```python
"""Serial Astra stream (canon §84 supplement 2, spec §16): ONE request in flight; when its answer (or the timeout)
arrives the next request goes out with the latest observation, so the interval = the latency L. Events raised while a
request is out do not cancel it: they are attached to the next request (flag). Options: min_interval_s (E-Astra-
necessity pacing of a fast local model), phase_pause_s (cost fallback: outside contact windows and more than
event_window_s after an event, wait until last send + phase_pause_s). A timed-out request frees the slot; if its
answer still arrives it is 'late' (never applied, still charged). fail_slow_after failed calls in a row (timeout,
API error, schema error) slow the robot down (spec §7) until a valid answer."""
from __future__ import annotations

import math
import statistics
from collections import deque


class SerialStream:
    def __init__(self, p, ledger):
        self.p, self.ledger = p, ledger
        self.inflight = None  # (request no, t_send)
        self.n_sent, self.fail_streak = 0, 0
        self.dropped, self.outstanding = set(), set()
        self.last_send = None
        self.pending_events = []
        self.last_event_t = -math.inf
        self.slow_until = -math.inf
        self.lat = deque(maxlen=20)
        self.max_inflight, self.max_outstanding = 0, 0
        self.counts = {"sent": 0, "answered": 0, "failed": 0, "timeouts": 0, "late": 0}

    def flag(self, name: str, now: float) -> None:
        if name not in self.pending_events:
            self.pending_events.append(name)
        self.last_event_t = now

    def next_send(self, now: float, contact_window: bool, est_krw: float) -> tuple[bool, str]:
        if self.inflight is not None:
            return False, "inflight"
        if self.last_send is not None and now < self.last_send + self.p.min_interval_s - 1e-9:
            return False, "min_interval"
        pp = self.p.phase_pause_s
        if (pp is not None and self.last_send is not None and not contact_window
                and now - self.last_event_t > self.p.event_window_s + 1e-9 and now < self.last_send + pp - 1e-9):
            return False, "pause"
        if not self.ledger.can_send(est_krw):
            return False, "budget"
        return True, "send"

    def sent(self, now: float) -> tuple[int, list]:
        self.n_sent += 1
        no = self.n_sent
        self.inflight, self.last_send = (no, now), now
        self.outstanding.add(no)
        self.max_inflight = max(self.max_inflight, 1)
        self.max_outstanding = max(self.max_outstanding, len(self.outstanding))
        self.counts["sent"] += 1
        ev, self.pending_events = self.pending_events, []
        return no, ev

    def timed_out(self, now: float):
        if self.inflight is None or now - self.inflight[1] <= self.p.timeout_s + 1e-9:
            return None
        no = self.inflight[0]
        self.inflight = None
        self.dropped.add(no)
        self.fail_streak += 1
        self.counts["timeouts"] += 1
        return no

    def is_late(self, no: int) -> bool:
        if no not in self.dropped:
            return False
        self.outstanding.discard(no)
        self.counts["late"] += 1
        return True

    def delivered(self, no: int, now: float, ok: bool, latency: float) -> None:
        self.outstanding.discard(no)
        if self.inflight is not None and self.inflight[0] == no:
            self.inflight = None
        if ok:
            self.fail_streak = 0
            self.counts["answered"] += 1
            self.lat.append(float(latency))
        else:
            self.fail_streak += 1
            self.counts["failed"] += 1

    @property
    def L_hat(self) -> float:
        return float(statistics.median(self.lat)) if self.lat else float(self.p.latency_init_s)

    def slowed(self, now: float) -> bool:
        return self.fail_streak >= self.p.fail_slow_after or now < self.slow_until - 1e-9

    def request_slow(self, now: float) -> None:
        self.slow_until = max(self.slow_until, now + self.p.slow_down_s)
```

`harvest/couple/mock.py` 끝에 추가(맨 위 import에 `import json`, `import time` 추가):

```python
from ..clients.astra import AstraRecord  # noqa: E402  (keep answer() import-light for tests that only build dicts)


class ScriptedCoupleAstra:
    """Scripted stand-in with the AstraClient call() shape: `script` = a list of answers (dict or raw text; the last
    one repeats) or a callable(request dict) -> answer; a fixed synthetic latency (the runtime's DeliveryQueue delivers
    at send + latency); a fixed usage so the cost ledger can be exercised with a test price table."""
    model = "mock:astra-couple-scripted"

    def __init__(self, script, latency_s: float = 3.0, usage: dict | None = None):
        self.script, self.synthetic_latency = script, float(latency_s)
        self.usage = dict(usage or {})
        self.calls = []

    def call(self, inp, effort, max_output_tokens, meta) -> AstraRecord:
        from .prompt import request_from_input
        req = request_from_input(inp)
        self.calls.append({"req": req, "meta": dict(meta)})
        if callable(self.script):
            ans = self.script(req)
        else:
            ans = self.script[min(len(self.calls), len(self.script)) - 1]
        t = time.monotonic()
        return AstraRecord(t_send=t, t_first_token=t, t_done=t, http_status=200, usage=dict(self.usage),
                           output_text=ans if isinstance(ans, str) else json.dumps(ans), model_field=self.model,
                           effort=effort, meta=dict(meta))
```

(`mock.py` 첫 부분은 `from __future__ import annotations` 다음 줄에 `import json`과 `import time`을 둔다. `AstraRecord` import는 `clients.astra`가 `httpx`를 불러오므로 파일 끝 쪽에 둔다.)

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_stream.py tests/couple/test_schema.py -v` → PASS.
- [ ] **Step 5: 커밋** — `msg_task4.txt` 첫 줄 `couple: serial single-in-flight stream and scripted mock Astra (Task 4)`.

---

### Task 5: Astra 층 히스테리시스 (연속 두 답 합의)

**Files:**
- Create: `harvest/couple/layer.py`
- Test: `tests/couple/test_layer.py`

**Interfaces:**
- Consumes: `AstraAnswer`, `Edit`(Task 1), `gate_answer`(Task 2).
- Produces: `same_edit(a: Edit, b: Edit, p) -> bool`, `flipped(a, b, p) -> bool`; `@dataclass LayerResult(action, key=None, weight=0.0, edit=None)` — action `none|apply|confirm|flip|stop_claim|stop_confirmed`; `AstraLayer(p)` — `on_answer(a) -> LayerResult`, `flow_last() -> dict`, 속성 `progress`, `pending`, `confirmed`, `counts`.

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_layer.py`:

```python
import json

import pytest

from harvest.couple.gate import gate_answer
from harvest.couple.layer import AstraLayer
from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.schema import parse_answer

P0, P1 = CoupleParams(request_mode="F0"), CoupleParams(request_mode="F1")


def _a(d, no, p=P0, t1=None):
    return gate_answer(parse_answer(json.dumps(d), p.request_mode, p.cameras, no, 0.0, 2.0), p, t1 or {})


def _edit(dp, **kw):
    return answer("edit", execution="failed", dp=dp, **kw)


def test_single_then_confirmed_edit():
    L = AstraLayer(P0)
    r1 = L.on_answer(_a(_edit((0, 0, 0.02)), 1))
    assert (r1.action, r1.key, r1.weight) == ("apply", 1, 0.5)
    assert L.flow_last()["state"] == "unconfirmed"
    r2 = L.on_answer(_a(_edit((0, 0.004, 0.02)), 2))  # 11 deg apart: same
    assert (r2.action, r2.key, r2.weight) == ("confirm", 1, 1.0)
    assert L.flow_last()["state"] == "confirmed"


def test_different_direction_is_a_new_candidate_and_opposite_is_a_flip():
    L = AstraLayer(P0)
    L.on_answer(_a(_edit((0.02, 0, 0)), 1))
    r = L.on_answer(_a(_edit((0.02, 0.02, 0)), 2))  # 45 deg: not the same, not a flip
    assert (r.action, r.key, r.weight) == ("apply", 2, 0.5)
    f = L.on_answer(_a(_edit((-0.02, -0.02, 0)), 3))
    assert (f.action, f.key, f.weight) == ("flip", 3, 0.0)
    c = L.on_answer(_a(_edit((-0.02, -0.021, 0)), 4))
    assert (c.action, c.key, c.weight) == ("confirm", 3, 1.0)


def test_a_continue_between_two_edits_breaks_the_confirmation():
    L = AstraLayer(P0)
    L.on_answer(_a(_edit((0, 0, 0.02)), 1))
    assert L.on_answer(_a(answer("continue"), 2)).action == "none"
    assert L.on_answer(_a(_edit((0, 0, 0.02)), 3)).action == "apply"


def test_gripper_change_is_not_the_same_edit():
    L = AstraLayer(P0)
    L.on_answer(_a(_edit((0, 0, 0.02)), 1))
    assert L.on_answer(_a(_edit((0, 0, 0.02), gripper="open"), 2)).action == "apply"


def test_f1_keep_confirms_only_with_a_takeover_reason():
    L = AstraLayer(P1)
    L.on_answer(_a(answer("edit", diff="revise", execution="failed", dp=(0.01, 0, 0)), 1, P1))
    assert L.on_answer(_a(answer(diff="keep", execution="uncertain"), 2, P1)).action == "none"
    L.on_answer(_a(answer("edit", diff="revise", execution="failed", dp=(0.01, 0, 0)), 3, P1))
    r = L.on_answer(_a(answer(diff="keep", execution="failed"), 4, P1))
    assert (r.action, r.key, r.weight) == ("confirm", 3, 1.0)


def test_stop_needs_two_answers():
    L = AstraLayer(P0)
    s = answer("stop", claims=(("placed", "cam_wrist_right"),))
    assert L.on_answer(_a(s, 1, t1={"holding_t": False})).action == "stop_claim"
    assert L.on_answer(_a(s, 2, t1={"holding_t": False})).action == "stop_confirmed"
    assert L.counts["stop_confirmed"] == 1


def test_progress_only_from_trusted_answers():
    L = AstraLayer(P0)
    L.on_answer(_a(answer(done=("grasped the mug",)), 1))
    assert L.progress["verified_completed"] == ["grasped the mug"]
    L.on_answer(_a(answer(done=("placed the mug",), views=("cam_head",)), 2))
    assert L.progress["verified_completed"] == ["grasped the mug"]
    assert pytest.approx(P0.single_weight) == 0.5
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_layer.py -v` → FAIL.

- [ ] **Step 3: 구현** — `harvest/couple/layer.py`:

```python
"""Astra-layer agreement (spec §5 hysteresis, §11 weights): consecutive gated answers in request order.
  edit, no candidate            -> apply the new edit at single_weight (50 %), it becomes the candidate
  edit, same as the candidate   -> confirm: 100 % (the first proposal's vector, plan ruling 7)
  edit, > flip_deg from the applied one -> flip: the offset goes back to 0, the new edit becomes a candidate at 0 %
  continue (not keep)           -> the candidate expires (a one-answer spike is ignored for confirmation, logged)
  F1 keep                       -> confirms the candidate only when the keep answer has a takeover reason
  stop twice in a row (F1: stop then keep) -> stop_confirmed (a logged claim, never a physical stop, canon §4)."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import numpy as np


def _ang(a, b) -> float:
    c = float(np.dot(a, b)) / (float(np.linalg.norm(a)) * float(np.linalg.norm(b)))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def _same_part(x, y, small: float, deg: float) -> bool:
    sx, sy = float(np.linalg.norm(x)) < small, float(np.linalg.norm(y)) < small
    if sx or sy:
        return sx and sy
    return _ang(x, y) <= deg + 1e-9


def same_edit(a, b, p) -> bool:
    return (a.gripper == b.gripper and _same_part(a.dp, b.dp, p.small_edit_m, p.same_dir_deg)
            and _same_part(a.dr, b.dr, p.small_rot_rad, p.same_dir_deg))


def flipped(a, b, p) -> bool:
    return (float(np.linalg.norm(a.dp)) >= p.small_edit_m and float(np.linalg.norm(b.dp)) >= p.small_edit_m
            and _ang(a.dp, b.dp) > p.flip_deg + 1e-9)


@dataclass
class LayerResult:
    action: str
    key: int | None = None
    weight: float = 0.0
    edit: object = None


class AstraLayer:
    def __init__(self, p):
        self.p = p
        self.pending = None  # (key, Edit) applied at single weight, waiting for the next answer
        self.confirmed = None  # (key, Edit)
        self.stop_pending = False
        self.progress = None
        self.counts = Counter()

    def _res(self, action, key=None, weight=0.0, edit=None) -> LayerResult:
        self.counts[action] += 1
        return LayerResult(action, key, weight, edit)

    def _confirm(self) -> LayerResult:
        key, e = self.pending
        self.pending, self.confirmed = None, (key, e)
        return self._res("confirm", key, 1.0, e)

    def on_answer(self, a) -> LayerResult:
        self.counts["answers"] += 1
        if a.progress_trusted:
            self.progress = a.task_progress
        if a.diff == "keep":
            if self.stop_pending:
                self.stop_pending = False
                return self._res("stop_confirmed")
            if self.pending is not None and a.takeover_ok:
                return self._confirm()
            self.pending = None
            return self._res("none")
        if a.command == "stop":
            self.pending = None
            if self.stop_pending:
                self.stop_pending = False
                return self._res("stop_confirmed")
            self.stop_pending = True
            return self._res("stop_claim")
        self.stop_pending = False
        if a.command != "edit":
            self.pending, self.confirmed = None, None
            return self._res("none")
        if self.pending is not None and same_edit(self.pending[1], a.edit, self.p):
            return self._confirm()
        ref = self.pending or self.confirmed
        if ref is not None and flipped(ref[1], a.edit, self.p):
            self.pending, self.confirmed = (a.request_no, a.edit), None
            return self._res("flip", a.request_no, 0.0, a.edit)
        self.pending = (a.request_no, a.edit)
        return self._res("apply", a.request_no, self.p.single_weight, a.edit)

    def flow_last(self) -> dict:
        for state, cur in (("unconfirmed", self.pending), ("confirmed", self.confirmed)):
            if cur is not None:
                return {"command": "edit", "edit": cur[1].to_json(), "request_no": cur[0], "state": state}
        return {"command": "continue"}
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_layer.py -v` → PASS.
- [ ] **Step 5: 커밋** — `msg_task5.txt` 첫 줄 `couple: Astra-layer two-answer hysteresis, flip, F1 keep, stop claim (Task 5)`.

---

### Task 6: 부드러운 편향 적용기

**Files:**
- Create: `harvest/couple/offset.py`
- Test: `tests/couple/test_offset.py`

**Interfaces:**
- Consumes: `CoupleParams`.
- Produces: `OffsetApplier(p)` — `command(key, vec6, weight, now, window_s)`, `reset(now, reason)`, `scale_remaining(factor, now, reason)`, `step(now, dt) -> np.ndarray(6)`(이 틱의 변위: 위치 m 3 + 회전 벡터 rad 3), 속성 `active: bool`, `direction() -> np.ndarray|None`(위치 단위 벡터), `rem`, `v`, `applied`, `state_json() -> dict`, `stats() -> dict`, `log: list`.

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_offset.py`:

```python
import numpy as np
import pytest

from harvest.couple.offset import OffsetApplier
from harvest.couple.params import CoupleParams

DT = 0.01


def _run(ap, t0, t1, trace=None):
    t = t0
    while t < t1 - 1e-9:
        s = ap.step(t, DT)
        if trace is not None:
            trace.append((t, s.copy(), ap.v.copy()))
        t = round(t + DT, 6)
    return t


def _check_limits(ap, p):
    assert ap.v_seen <= p.v_max + 1e-9 and ap.a_seen <= p.a_max + 1e-6


def test_single_answer_ramps_to_half_of_the_edit_within_its_window():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.04, 0, 0, 0, 0, 0], 0.5, 0.0, 2.0)
    tr = []
    _run(ap, 0.0, 3.0, tr)
    np.testing.assert_allclose(ap.applied[:3], [0.02, 0, 0], atol=2e-5)
    assert sum(s[0] for t, s, _ in tr if t < 1.0) == pytest.approx(0.01, abs=1e-3)  # linear ramp
    _check_limits(ap, p)
    assert not ap.active


def test_confirmation_adds_the_other_half():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0, 0, 0.04, 0, 0, 0], 0.5, 0.0, 2.0)
    _run(ap, 0.0, 1.0)
    ap.command(1, [0, 0, 0.04, 0, 0, 0], 1.0, 1.0, 2.0)
    _run(ap, 1.0, 4.0)
    np.testing.assert_allclose(ap.applied[:3], [0, 0, 0.04], atol=5e-5)
    _check_limits(ap, p)


def test_window_is_clamped_to_1_3_s():
    ap = OffsetApplier(CoupleParams())
    ap.command(1, [0.01, 0, 0, 0, 0, 0], 1.0, 0.0, 0.2)
    assert ap.t_end == pytest.approx(1.0)
    ap.command(2, [0.01, 0, 0, 0, 0, 0], 1.0, 0.0, 9.0)
    assert ap.t_end == pytest.approx(3.0)


def test_reset_brakes_smoothly_without_a_jump():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.05, 0, 0, 0, 0, 0], 1.0, 0.0, 1.0)
    _run(ap, 0.0, 0.5)
    v0 = float(np.linalg.norm(ap.v[:3]))
    ap.reset(0.5, "flip")
    tr = []
    _run(ap, 0.5, 1.5, tr)
    speeds = [float(np.linalg.norm(v[:3])) for _, _, v in tr]
    assert v0 > 0.02 and speeds[-1] == 0.0
    assert all(b <= a + 1e-12 for a, b in zip(speeds, speeds[1:]))
    _check_limits(ap, p)


def test_rate_limit_leaves_a_rest_that_decays_and_is_dropped():
    p = CoupleParams(v_max=0.02)
    ap = OffsetApplier(p)
    ap.command(1, [0.05, 0, 0, 0, 0, 0], 1.0, 0.0, 1.0)
    _run(ap, 0.0, 3.0)
    assert ap.applied[0] < 0.05 - 0.02 and ap.dropped[0] > 0.0
    assert ap.v_seen <= 0.02 + 1e-9 and not ap.active


def test_scale_remaining_and_rotation():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.02, 0, 0, 0, 0, 0.2], 1.0, 0.0, 2.0)
    ap.scale_remaining(0.5, 0.0, "vla_contra")
    _run(ap, 0.0, 3.0)
    np.testing.assert_allclose(ap.applied, [0.01, 0, 0, 0, 0, 0.1], atol=5e-5)
    assert ap.stats()["scaled"] == 1 and ap.state_json()["weight"] == 1.0
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_offset.py -v` → FAIL.

- [ ] **Step 3: 구현** — `harvest/couple/offset.py`:

```python
"""Smooth application of Astra edits (spec §11, plan ruling 5): an edit enters as extra motion whose accumulated
displacement is weight x delta (6-D: tip translation m, rotation vector rad, robot frame). Inside the validity window
(= expected next answer, clamped to [ramp_min_s, ramp_max_s]) the remaining displacement is spread linearly over the
remaining window (GPT-as-Policy edit alpha = (i + 1) / steps), braking so that it lands (speed <= sqrt(2 a d)).
Limits: tip speed v_max / acceleration a_max, rotation w_max / alpha_max (no jumps). After the window with a rest
left (rate-limited), the speed decays to 0 over decay_s and the rest is dropped (logged). reset (a flipped answer)
empties the remaining displacement and brakes at a_max; scale_remaining (VLA fast check) shrinks it."""
from __future__ import annotations

import math

import numpy as np


def _r(x):
    return [round(float(v), 5) for v in x]


class OffsetApplier:
    def __init__(self, p):
        self.p = p
        self.key, self.w, self.vec = None, 0.0, np.zeros(6)
        self.rem, self.v, self.applied, self.dropped = np.zeros(6), np.zeros(6), np.zeros(6), np.zeros(6)
        self.t_end = -math.inf
        self._decay = {}
        self.v_seen, self.a_seen = 0.0, 0.0
        self.n = {"commands": 0, "resets": 0, "scaled": 0}
        self.log = []

    @property
    def active(self) -> bool:
        return bool(np.linalg.norm(self.rem) > 1e-9 or np.linalg.norm(self.v) > 1e-9)

    def direction(self):
        d = self.rem[:3] if np.linalg.norm(self.rem[:3]) > 1e-6 else self.v[:3]
        n = float(np.linalg.norm(d))
        return d / n if n > 1e-9 else None

    def command(self, key, vec6, weight: float, now: float, window_s: float) -> None:
        vec6 = np.asarray(vec6, float)
        if key == self.key:
            self.rem = self.rem + (weight - self.w) * self.vec
        else:
            self.key, self.vec, self.rem = key, vec6.copy(), weight * vec6
        self.w = float(weight)
        self.t_end = now + min(max(float(window_s), self.p.ramp_min_s), self.p.ramp_max_s)
        self._decay = {}
        self.n["commands"] += 1
        self.log.append({"t": round(now, 3), "event": "command", "key": key, "weight": self.w, "rem": _r(self.rem),
                         "t_end": round(self.t_end, 3)})

    def reset(self, now: float, reason: str) -> None:
        self.log.append({"t": round(now, 3), "event": "reset", "reason": reason, "dropped": _r(self.rem)})
        self.dropped += np.abs(self.rem)
        self.rem, self.key, self.w = np.zeros(6), None, 0.0
        self.n["resets"] += 1

    def scale_remaining(self, factor: float, now: float, reason: str) -> None:
        self.dropped += np.abs(self.rem) * (1.0 - factor)
        self.rem = self.rem * factor
        self.n["scaled"] += 1
        self.log.append({"t": round(now, 3), "event": "scale", "reason": reason, "factor": factor,
                         "rem": _r(self.rem)})

    def step(self, now: float, dt: float) -> np.ndarray:
        in_win = now < self.t_end - 1e-9
        out, v_new = np.zeros(6), self.v.copy()
        capped = False
        for i0, vmax, amax in ((0, self.p.v_max, self.p.a_max), (3, self.p.w_max, self.p.alpha_max)):
            sl = slice(i0, i0 + 3)
            rem, v = self.rem[sl].copy(), self.v[sl].copy()
            n = float(np.linalg.norm(rem))
            if in_win and n > 1e-12:
                speed = min(n / max(self.t_end - now, dt), vmax, math.sqrt(2.0 * amax * n))
                v_des, lim = rem / n * speed, amax * dt
            elif n > 1e-12:  # window over with a rest: decay over decay_s
                if i0 not in self._decay:
                    self._decay[i0] = max(float(np.linalg.norm(v)) / self.p.decay_s, 1e-6)
                v_des, lim = np.zeros(3), self._decay[i0] * dt
            else:  # nothing left (reset): brake at the acceleration cap
                v_des, lim = np.zeros(3), amax * dt
            dv = v_des - v
            nd = float(np.linalg.norm(dv))
            if nd > lim:
                dv = dv * (lim / nd)
            vn = v + dv
            d = vn * dt
            if n > 1e-12:
                u = rem / n
                along = float(d @ u)
                if along > n:  # landing: never pass the remaining displacement, stop there (no drift after)
                    d, vn, capped = d * (n / along), np.zeros(3), True
                rem = rem - d
                if float(rem @ u) <= 1e-12:
                    rem = np.zeros(3)
            out[sl], v_new[sl], self.rem[sl] = d, vn, rem
        if not capped:
            self.a_seen = max(self.a_seen, float(np.linalg.norm(v_new[:3] - self.v[:3])) / dt)
        self.v_seen = max(self.v_seen, float(np.linalg.norm(v_new[:3])))
        self.v = v_new
        self.applied += out
        if not in_win and np.linalg.norm(self.v) < 1e-9 and np.linalg.norm(self.rem) > 0:
            self.log.append({"t": round(now, 3), "event": "drop", "rest": _r(self.rem)})
            self.dropped += np.abs(self.rem)
            self.rem = np.zeros(6)
        if np.linalg.norm(self.v) < 1e-9:
            self.v = np.zeros(6)
        return out

    def state_json(self) -> dict:
        return {"key": self.key, "weight": self.w, "remaining_m": _r(self.rem[:3]), "remaining_rad": _r(self.rem[3:]),
                "velocity_mps": _r(self.v[:3])}

    def stats(self) -> dict:
        return {"applied_m": _r(self.applied[:3]), "applied_rad": _r(self.applied[3:]),
                "dropped_m": round(float(np.linalg.norm(self.dropped[:3])), 5), "v_max_seen": round(self.v_seen, 5),
                "a_max_seen": round(self.a_seen, 5), **self.n}
```

주의: 감쇠 구간(창 뒤)에서 속도가 1e-9보다 작아지면 속도를 0으로 두고 남은 것을 버린다. `test_reset_brakes_smoothly_without_a_jump`의 `speeds[-1] == 0.0`은 이 영점화에 기댄다. 착지 틱(남은 변위를 다 쓰는 틱)은 속도를 0으로 두므로 그 틱의 감속은 `a_seen`에서 뺀다(`capped`) — 착지 뒤 표류(과잉 이동)를 막는 쪽을 택했다.

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_offset.py -v` → PASS. 실패하면 `superpowers:systematic-debugging`으로 원인(착지 캡·감쇠 속도)을 먼저 찾는다 — 한계값을 늘려 맞추지 않는다.
- [ ] **Step 5: 커밋** — `msg_task6.txt` 첫 줄 `couple: smooth ramped offset with rate limits, decay, reset and shrink (Task 6)`.

---

### Task 7: 두 층 비가역 게이트, VLA 빠른 검증, 진전 없음

**Files:**
- Create: `harvest/couple/twolayer.py`
- Test: `tests/couple/test_twolayer.py`

**Interfaces:**
- Consumes: `AstraAnswer`(Task 1–2), `harvest.runtime.skills._XY_SIGN, _Z_SIGN`.
- Produces: `IRREV = ("close","stage","release")`, `SUPPORT`, `OPPOSE`; `t1_evidence(kind, t1, near) -> bool`; `TwoLayerGate(p)` — `allow(kind, now, last, last_t, t1, near) -> tuple[bool, str]`, `mismatch_due(kind, now) -> bool`, `log`, `counts`; `committed_vector(committed: dict) -> np.ndarray|None`; `VlaFastCheck(p)` — `on_step(vla_vec, offset_dir) -> bool`, `reset()`; `NoProgress(p)` — `update(now, tcp, applied_trans) -> bool`.

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_twolayer.py`:

```python
import json

import numpy as np

from harvest.couple.gate import gate_answer
from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.schema import parse_answer
from harvest.couple.twolayer import NoProgress, TwoLayerGate, VlaFastCheck, committed_vector

P = CoupleParams()
T1_CLOSE = {"gripper_open": True, "holding_t": False}


def _a(d, t1=None):
    return gate_answer(parse_answer(json.dumps(d), "F0", P.cameras, 1, 0.0, 2.0), P, t1 or {})


def test_fresh_misaligned_or_failed_or_opposite_gripper_vetoes():
    g = TwoLayerGate(P)
    assert g.allow("close", 10.0, _a(answer(intent="misaligned")), 9.0, T1_CLOSE, True) == (False, "astra_misaligned")
    assert g.allow("close", 10.0, _a(answer(execution="failed")), 9.0, T1_CLOSE, True) == (False, "astra_failed")
    op = _a(answer("edit", execution="failed", dp=(0, 0, 0.01), gripper="open"))
    assert g.allow("close", 10.0, op, 9.0, T1_CLOSE, True) == (False, "astra_gripper_opposes")
    low = _a(answer(intent="misaligned", confidence="low"))
    assert g.allow("close", 10.0, low, 9.0, T1_CLOSE, True) == (True, "t1_fresh")


def test_stale_astra_lets_the_vla_flow_with_t1_evidence():
    g = TwoLayerGate(P)
    old = _a(answer(intent="misaligned"))
    assert g.allow("close", 20.0, old, 16.9, T1_CLOSE, True) == (True, "t1_astra_stale")
    assert g.allow("close", 20.0, None, None, T1_CLOSE, False) == (False, "no_evidence")
    assert g.allow("stage", 20.0, None, None, {"holding_t": True}, False) == (True, "t1_astra_stale")
    assert g.allow("release", 20.0, None, None, {"holding_t": False}, True) == (False, "no_evidence")


def test_wrist_claim_is_evidence_without_t1():
    g = TwoLayerGate(P)
    a = _a(answer(claims=(("grasp_ready", "cam_wrist_right"),)))
    assert g.allow("close", 10.0, a, 9.5, {"gripper_open": True}, False) == (True, "wrist_fresh")


def test_strict_reading_needs_aligned():
    g = TwoLayerGate(CoupleParams(irrev_need_aligned=True))
    assert g.allow("close", 10.0, _a(answer(intent="uncertain")), 9.5, T1_CLOSE, True) == (False, "astra_not_aligned")


def test_mismatch_event_once_after_1_s_of_blocking():
    g = TwoLayerGate(P)
    bad = _a(answer(intent="misaligned"))
    g.allow("close", 10.0, bad, 9.9, T1_CLOSE, True)
    assert not g.mismatch_due("close", 10.5)
    g.allow("close", 11.0, bad, 10.9, T1_CLOSE, True)
    assert g.mismatch_due("close", 11.0) and not g.mismatch_due("close", 11.2)
    assert g.counts["deny:astra_misaligned"] == 1 and len(g.log) == 1


def test_committed_vector_and_fast_check():
    assert committed_vector({"dir_xy": "plus_x", "dir_z": "down"}).tolist() == [1, 0, -1]
    assert committed_vector({"dir_xy": "none_xy"}) is None
    f = VlaFastCheck(P)
    back = np.array([-1.0, 0.0, 0.0])
    fired = [f.on_step(back, np.array([1.0, 0, 0])) for _ in range(3)]
    assert fired == [False, False, True]
    assert f.on_step(np.array([1.0, 0, 0]), np.array([1.0, 0, 0])) is False


def test_no_progress_when_the_tip_does_not_follow_the_offset():
    n = NoProgress(P)
    fired = []
    for i in range(301):
        t = i * 0.01
        fired.append(n.update(t, np.zeros(3), np.array([0.0, 0.0, 0.01 * t])))
    assert any(fired)
    m = NoProgress(P)
    assert not any(m.update(i * 0.01, np.array([0, 0, 0.01 * i * 0.01]), np.array([0, 0, 0.01 * i * 0.01]))
                   for i in range(301))
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_twolayer.py -v` → FAIL.

- [ ] **Step 3: 구현** — `harvest/couple/twolayer.py`:

```python
"""Between the two layers (spec §5, §11, §12; plan rulings 1, 2, 6).
TwoLayerGate: an irreversible transition the VLA side wants (close = gripper close, stage = S1 -> S2, release =
gripper open at the place) is allowed only when
  (a) a fresh Astra answer (arrived <= astra_fresh_s ago) does not veto it (intent misaligned / execution failed with
      confidence not low, or an edit whose gripper opposes it; strict mode: intent must be aligned), and with no
      fresh answer the VLA carries the flow (spec §5 "> 3 s 무답"), and
  (b) there is evidence: a gated active-wrist claim of the transition (grasp_ready / grasped / placed) or the T1
      proprio premise (close: gripper open inside the near/contact zone; stage and release: holding).
A transition blocked for mismatch_s raises one layer_mismatch event. Only changes of the decision are logged.
VlaFastCheck: the VLA re-decides every 0.33 s; a committed direction opposite to the offset for contra_steps steps
shrinks the offset (spec §11). NoProgress: the offset moved > 1 cm over stag_s but the tip followed < stag_frac."""
from __future__ import annotations

from collections import Counter, deque

import numpy as np

from ..runtime.skills import _XY_SIGN, _Z_SIGN

IRREV = ("close", "stage", "release")
SUPPORT = {"close": "grasp_ready", "stage": "grasped", "release": "placed"}
OPPOSE = {"close": "open", "release": "close"}


def t1_evidence(kind: str, t1: dict, near: bool) -> bool:
    if kind == "close":
        return t1.get("gripper_open") is True and bool(near)
    return t1.get("holding_t") is True


class TwoLayerGate:
    def __init__(self, p):
        self.p = p
        self.blocked_since, self._state, self._flagged = {}, {}, set()
        self.log, self.counts = [], Counter()

    def _decide(self, kind, now, last, last_t, t1, near):
        fresh = last is not None and last_t is not None and now - last_t <= self.p.astra_fresh_s + 1e-9
        if fresh:
            if last.edit is not None and last.edit.gripper == OPPOSE.get(kind):
                return False, "astra_gripper_opposes"
            if last.intent == "misaligned" and last.confidence != "low":
                return False, "astra_misaligned"
            if last.execution == "failed" and last.confidence != "low":
                return False, "astra_failed"
            if self.p.irrev_need_aligned and last.intent != "aligned":
                return False, "astra_not_aligned"
        wrist = fresh and any(k == SUPPORT[kind] for k, _ in last.claims)
        if not (wrist or t1_evidence(kind, t1, near)):
            return False, "no_evidence"
        return True, ("wrist" if wrist else "t1") + ("_fresh" if fresh else "_astra_stale")

    def allow(self, kind, now, last, last_t, t1: dict, near: bool) -> tuple[bool, str]:
        if kind not in IRREV:
            raise ValueError(f"irreversible kind {kind!r}: one of {IRREV}")
        ok, why = self._decide(kind, now, last, last_t, t1, near)
        if self._state.get(kind) != (ok, why):
            self._state[kind] = (ok, why)
            self.counts[f"{'allow' if ok else 'deny'}:{why}"] += 1
            self.log.append({"t": round(now, 3), "kind": kind, "ok": ok, "why": why})
        if ok:
            self.blocked_since.pop(kind, None)
            self._flagged.discard(kind)
        else:
            self.blocked_since.setdefault(kind, now)
        return ok, why

    def mismatch_due(self, kind: str, now: float) -> bool:
        t0 = self.blocked_since.get(kind)
        if t0 is None or kind in self._flagged or now - t0 < self.p.mismatch_s - 1e-9:
            return False
        self._flagged.add(kind)
        return True


def committed_vector(committed: dict):
    xy, z = _XY_SIGN.get(committed.get("dir_xy")), _Z_SIGN.get(committed.get("dir_z"), 0)
    if xy is None:
        return None
    v = np.array([xy[0], xy[1], z], float)
    return v if np.any(v) else None


class VlaFastCheck:
    def __init__(self, p):
        self.p, self.n = p, 0

    def reset(self) -> None:
        self.n = 0

    def on_step(self, vla_vec, offset_dir) -> bool:
        if vla_vec is None or offset_dir is None:
            self.n = 0
            return False
        u = np.asarray(vla_vec, float) / float(np.linalg.norm(vla_vec))
        self.n = self.n + 1 if float(u @ np.asarray(offset_dir, float)) < 0 else 0
        if self.n >= self.p.contra_steps:
            self.n = 0
            return True
        return False


class NoProgress:
    def __init__(self, p):
        self.p, self.h = p, deque()

    def update(self, now: float, tcp, applied_trans) -> bool:
        self.h.append((now, np.asarray(tcp, float).copy(), np.asarray(applied_trans, float).copy()))
        while self.h and self.h[0][0] < now - self.p.stag_s - 1e-9:
            self.h.popleft()
        t0, p0, a0 = self.h[0]
        if now - t0 < self.p.stag_s - 0.02:
            return False
        cmd = self.h[-1][2] - a0
        n = float(np.linalg.norm(cmd))
        if n < 0.01:
            return False
        moved = float((self.h[-1][1] - p0) @ (cmd / n))
        if moved < self.p.stag_frac * n:
            self.h.clear()
            return True
        return False
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_twolayer.py -v` → PASS.
- [ ] **Step 5: 커밋** — `msg_task7.txt` 첫 줄 `couple: two-layer irreversible gate, VLA fast check, no-progress detector (Task 7)`.

---

### Task 8: 덧그림(Astra 영상 전용)과 카메라 모델

**Files:**
- Create: `harvest/couple/overlay.py`
- Modify: `harvest/runtime/aiworker.py`(`_obs` extra에 `cams`, 메서드 `camera_models`), `harvest/runtime/ir_policy.py`(`act`의 obs에 `cams`)
- Test: `tests/couple/test_overlay.py`

**Interfaces:**
- Produces: `CamModel(K, R, t, W, H)` + `from_dict(d)`(R = base_from_optical, t = 카메라 원점, world); `project(cam, p) -> (u, v, z)`; `uv255(cam, p) -> list[int]|None`; `EETrace(keep_s)` — `add(t, p)`, `window(now, span) -> list[tuple[float, np.ndarray]]`(오래된 것 → 새것); `draw_overlay(img, cam, *, tip, trace, next_vec=None, offset_vec=None, wrist=False) -> np.ndarray`; `polylines(cams: dict[str, CamModel], pts_newest_first: list, n=5) -> dict[str, list[list[int]]]`; 상수 `INSET=64`.
- 관측 규약: `obs["cams"]` = `{cam: {"K": 3x3, "R": 3x3, "t": 3, "W": int, "H": int}}` 또는 그것을 돌려주는 호출 가능 객체(요청을 보낼 때만 평가).

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_overlay.py`:

```python
import numpy as np

from harvest.couple.overlay import INSET, CamModel, EETrace, draw_overlay, polylines, project, uv255

R = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])  # optical x = -Y, y = -Z, z = +X (Isaac world)
CAM = CamModel.from_dict({"K": [[100, 0, 80], [0, 100, 60], [0, 0, 1]], "R": R.tolist(), "t": [0, 0, 0],
                          "W": 160, "H": 120})


def test_projection_center_and_right():
    u, v, z = project(CAM, [1.0, 0.0, 0.0])
    assert (round(u, 6), round(v, 6), round(z, 6)) == (80.0, 60.0, 1.0)
    u2, _, _ = project(CAM, [1.0, -0.1, 0.0])
    assert u2 > 80.0  # world -y is image right
    assert uv255(CAM, [1.0, 0.0, 0.0]) == [128, 128] and uv255(CAM, [-1.0, 0.0, 0.0]) is None


def test_head_overlay_draws_around_the_tip_only():
    img = np.zeros((120, 160, 3), np.uint8)
    tip = np.array([1.0, 0.0, 0.0])
    out = draw_overlay(img, CAM, tip=tip, trace=[tip + [0, 0.05, 0], tip], next_vec=np.array([0, -0.02, 0]),
                       offset_vec=np.array([0, 0, 0.02]), wrist=False)
    assert out.shape == img.shape and out[53:68, 72:89].any()  # ring / axes / arrows around the tip (80, 60)
    assert not out[:20, :20].any() and not out[100:, 140:].any()  # far corners untouched
    assert img.sum() == 0  # the input frame is not modified


def test_wrist_overlay_stays_inside_the_corner_box():
    img = np.zeros((120, 160, 3), np.uint8)
    out = draw_overlay(img, CAM, tip=np.array([1.0, 0, 0]), trace=[], next_vec=np.array([0, -0.02, 0]),
                       offset_vec=None, wrist=True)
    ys, xs = np.nonzero(out.sum(axis=2))
    assert len(xs) > 0 and xs.min() >= 160 - INSET - 3 and ys.max() <= INSET + 3


def test_polylines_skip_cameras_without_model():
    tr = EETrace(keep_s=5.0)
    for i in range(30):
        tr.add(i * 0.1, [1.0, -0.01 * i, 0.0])
    pts = [p for _, p in tr.window(2.9, 2.5)]
    out = polylines({"cam_head": CAM}, pts[::-1])
    assert list(out) == ["cam_head"] and 1 <= len(out["cam_head"]) <= 5
    assert out["cam_head"][0] == uv255(CAM, pts[-1])  # current point first (MolmoAct p1)
    assert polylines({}, pts[::-1]) == {} and polylines({"cam_head": CAM}, []) == {}
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_overlay.py -v` → FAIL.

- [ ] **Step 3: 구현** — `harvest/couple/overlay.py`:

```python
"""Code-drawn overlay for the Astra images only (spec §13-§14, canon §84: the next-chunk arrow never goes into the VLA
input). Projection from the robot's own kinematics (tip = kin.tcp_pose) and the camera models (live parent-link pose
x mount, the E-Astra-motion probe's camera_pose), never object ground truth. Head image: tip ring, fading trace
(MolmoAct / PEEK style), cyan committed-next-motion arrow, magenta remaining Astra correction, robot-frame axes at
the tip (plan ruling 4). Wrist images: only a corner box with the same arrows as directions (edges only, spec §13).
polylines(): MolmoAct trace format for the request JSON -- <= 5 points, current point first, 0-255 image ints."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

INSET = 64
AXES_M = 0.03
WHITE, YELLOW, CYAN, MAGENTA = (255, 255, 255), (255, 230, 0), (0, 255, 255), (255, 0, 255)
AXIS_COLORS = ((255, 40, 40), (40, 220, 40), (60, 120, 255))


@dataclass(frozen=True)
class CamModel:
    K: np.ndarray
    R: np.ndarray
    t: np.ndarray
    W: int
    H: int

    @classmethod
    def from_dict(cls, d: dict) -> "CamModel":
        return cls(np.asarray(d["K"], float), np.asarray(d["R"], float), np.asarray(d["t"], float), int(d["W"]),
                   int(d["H"]))


def project(cam: CamModel, p) -> tuple:
    pc = cam.R.T @ (np.asarray(p, float) - cam.t)
    z = float(pc[2])
    if z <= 1e-9:
        return math.nan, math.nan, z
    return float(cam.K[0, 0] * pc[0] / z + cam.K[0, 2]), float(cam.K[1, 1] * pc[1] / z + cam.K[1, 2]), z


def uv255(cam: CamModel, p):
    u, v, z = project(cam, p)
    if z <= 0 or not math.isfinite(u) or not (0 <= u < cam.W and 0 <= v < cam.H):
        return None
    return [int(round(255 * u / cam.W)), int(round(255 * v / cam.H))]


class EETrace:
    def __init__(self, keep_s: float = 4.0):
        self.keep_s, self.h = keep_s, deque()

    def add(self, t: float, p) -> None:
        self.h.append((float(t), np.asarray(p, float).copy()))
        while self.h and self.h[0][0] < t - self.keep_s - 1e-9:
            self.h.popleft()

    def window(self, now: float, span: float) -> list:
        return [(t, p) for t, p in self.h if t >= now - span - 1e-9]


def _px(cam, p):
    u, v, z = project(cam, p)
    return None if z <= 0 or not math.isfinite(u) else (u, v)


def _arrow(d, a, b, col, width=3):
    d.line([tuple(a), tuple(b)], fill=col + (255,), width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-1, 1):
        e = (b[0] - 8 * math.cos(ang + s * 0.45), b[1] - 8 * math.sin(ang + s * 0.45))
        d.line([tuple(b), e], fill=col + (255,), width=width)


def draw_overlay(img, cam: CamModel, *, tip, trace, next_vec=None, offset_vec=None, wrist: bool = False) -> np.ndarray:
    from PIL import Image, ImageDraw
    base = Image.fromarray(np.asarray(img, np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tip = np.asarray(tip, float)
    arrows = [(v, c) for v, c in ((next_vec, CYAN), (offset_vec, MAGENTA))
              if v is not None and float(np.linalg.norm(v)) > 1e-6]
    if wrist:
        W = base.size[0]
        x0, y0 = W - INSET - 2, 2
        d.rectangle([x0, y0, x0 + INSET, y0 + INSET], fill=(0, 0, 0, 150))
        c = np.array([x0 + INSET / 2, y0 + INSET / 2])
        for v, col in [(AXES_M * e, ac) for e, ac in zip(np.eye(3), AXIS_COLORS)] + arrows:
            dc = cam.R.T @ np.asarray(v, float)
            n = math.hypot(dc[0], dc[1])
            if n > 1e-9:
                _arrow(d, c, c + np.array([dc[0], dc[1]]) / n * (INSET / 2 - 5), col, width=2)
    else:
        pts = [q for q in (_px(cam, p) for p in trace) if q is not None]
        for i in range(1, len(pts)):
            d.line([pts[i - 1], pts[i]], fill=YELLOW + (int(60 + 160 * i / max(len(pts) - 1, 1)),), width=2)
        pt = _px(cam, tip)
        if pt is not None:
            for e, col in zip(np.eye(3), AXIS_COLORS):
                q = _px(cam, tip + AXES_M * e)
                if q is not None:
                    d.line([pt, q], fill=col + (230,), width=2)
            for v, col in arrows:
                q = _px(cam, tip + np.asarray(v, float))
                if q is not None:
                    _arrow(d, pt, q, col)
            d.ellipse([pt[0] - 6, pt[1] - 6, pt[0] + 6, pt[1] + 6], outline=WHITE + (255,), width=2)
    return np.asarray(Image.alpha_composite(base, layer).convert("RGB"))


def polylines(cams: dict, pts_newest_first: list, n: int = 5) -> dict:
    if not pts_newest_first:
        return {}
    k = len(pts_newest_first)
    idx = sorted({int(round(x)) for x in np.linspace(0, k - 1, min(n, k))})
    out = {}
    for c, cam in cams.items():
        uv = [q for q in (uv255(cam, pts_newest_first[i]) for i in idx) if q is not None]
        if uv:
            out[c] = uv
    return out
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_overlay.py -v` → PASS.

- [ ] **Step 5: 관측 규약 배선(로컬 시험 가능한 부분)** — `harvest/runtime/ir_policy.py`의 `act()` obs 딕셔너리 끝에 `"cams": x.get("cams")`를 더한다:

```python
        obs = {"sim_time": x["sim_time"], "joint_pos": observation.state["joint_pos"], "images": observation.images,
               "m1": x["m1"], "kin": x["kin"], "table_z": x["table_z"], "low": self.low, "high": self.high,
               "cams": x.get("cams")}
```

- [ ] **Step 6: Isaac 카메라 자세 어댑터(착수 조건 0-3 뒤에만)** — `harvest/runtime/aiworker.py` `AIWorkerEmbodiment`에 메서드를 더하고 `_obs`의 `extra`에 `"cams": self.camera_models`(호출 가능 객체 그대로, 요청 때만 평가)를 넣는다. 카메라 자세 계산은 탐침의 `camera_pose`를 **재사용**한다(Isaac 카메라 `pos_w`/`quat_w`가 물리를 따르지 않는 결함, 탐침 사전 등록 §0-2):

```python
    def camera_models(self) -> dict:
        """{cam: {K, R (base_from_optical), t, W, H}} now: live parent-link pose x mount (the E-Astra-motion probe's
        camera_pose; Isaac camera pos_w / quat_w do not follow physics). Evaluated only when an Astra request goes out."""
        from ..astra_motion.world_isaac import camera_pose
        from ..sim.scene import camera_table, load_realcam
        rc, rows = load_realcam(), {r["name"]: r for r in camera_table()}
        out = {}
        for n in self.cameras:
            R, t = camera_pose(self.env.robot, rc, n)
            out[n] = {"K": self.K[n].tolist(), "R": np.asarray(R).tolist(), "t": np.asarray(t).tolist(),
                      "W": int(rows[n]["width"]), "H": int(rows[n]["height"])}
        return out
```

`_obs`의 `extra`에 한 줄: `"cams": self.camera_models,`. 확인은 파드에서(유료 호출 없음): `source /data/harvest/env.sh`, Isaac 작업자로 DEV 시드 0 한 판을 `--couple serial --astra mock`으로 돌리고(Task 14 뒤) 사이드카 `couple` 행의 `overlay`가 세 카메라를 담는지, 블롭 JPEG 세 장에서 머리 영상 손끝 고리가 그리퍼 위에 있는지 **프레임으로 확인**한다.

- [ ] **Step 7: 커밋** — Step 1–5를 `msg_task8.txt` 첫 줄 `couple: Astra-only overlay, camera models, MolmoAct trace polylines (Task 8)`로 커밋하고, Step 6은 확인 뒤 `msg_task8b.txt` 첫 줄 `aiworker: live camera models for the coupling overlay (probe camera_pose) (Task 8)`로 따로 커밋한다.

---

### Task 9: CoupleDriver — 틱 단위 묶음, 요청 조립, 로그

**Files:**
- Create: `harvest/couple/driver.py`
- Test: `tests/couple/test_driver.py`

**Interfaces:**
- Consumes: Task 1–8 전부, `harvest.runtime.models.jpeg_bytes`, `harvest.runtime.reqhash.request_body`.
- Produces: `TickView(now, dt, tcp_p, phase, stage, near, committed, frames, cams=None, t1={}, motion=None)`, `TickOut(step6: np.ndarray, speed_scale: float)`, `CONTACT_PHASES`, `next_motion_vec(committed) -> np.ndarray|None`, `predict_ee(trace, horizon, cap, extra) -> np.ndarray`, `CoupleDriver(p, astra, ledger, submit, task, episode=1)` — `tick(v) -> TickOut`, `on_delivery(r, now, t1)`, `on_step(committed, outcome, now)`, `irrev_allowed(kind, now, t1, near) -> bool`, `flag(name, now)`, `summary() -> dict`, `close()`, 속성 `log`, `events`, `blobs`, `last`, `last_t`.
- `submit(now, fn, fixed_latency, meta)` 규약: 런타임이 `fn`을 작업 스레드에서 돌리고 결과 딕셔너리에 `meta`, `t_send`, `t_deliver`를 붙여 `on_delivery`로 돌려준다(`clock.DeliveryQueue`와 같음). `meta = {"kind": "couple", "no", "episode", "t_state", "cameras"}`.

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_driver.py`:

```python
import numpy as np
import pytest

from harvest.couple.cost import CostLedger, PriceTable
from harvest.couple.driver import CoupleDriver, TickView
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.params import CoupleParams

TEST = PriceTable("test", "2026-09-26", 2.0, 0.5, 8.0, 1400.0, "unit test")
FR = {c: np.full((12, 16, 3), 40, np.uint8) for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
CAMS = {c: {"K": [[20, 0, 8], [0, 20, 6], [0, 0, 1]], "R": [[0, 0, 1], [-1, 0, 0], [0, -1, 0]], "t": [0, 0, 0],
            "W": 16, "H": 12} for c in FR}


class MiniQueue:
    """The runtime DeliveryQueue contract, synchronously: fn runs at submit, delivered at send + latency."""

    def __init__(self):
        self.items = []

    def submit(self, now, fn, lat, meta):
        self.items.append((now + (lat or 0.0), fn(), meta, now))

    def due(self, now):
        out = [x for x in self.items if x[0] <= now + 1e-9]
        self.items = [x for x in self.items if x[0] > now + 1e-9]
        return [{**res, "meta": meta, "t_send": ts, "t_deliver": td} for td, res, meta, ts in out]


def _run(astra, seconds, p=None, ledger=None, frames=FR, cams=CAMS, t1=None, flag_at=None):
    p = p or CoupleParams(request_mode="F0")
    q = MiniQueue()
    ledger = ledger or CostLedger(None, 0.0, PriceTable.free())
    drv = CoupleDriver(p, astra, ledger, q.submit, "Put the red mug on the blue tray.")
    steps = []
    for i in range(int(round(seconds * 100))):
        now = round(i * 0.01, 6)
        for r in q.due(now):
            drv.on_delivery(r, now, t1 or {})
        if flag_at is not None and abs(now - flag_at) < 1e-9:
            drv.flag("m7_critic_alarm", now)
        out = drv.tick(TickView(now=now, dt=0.01, tcp_p=np.array([1.0, 0.0, 0.0]), phase="approach", stage="S1",
                                near=False, committed={"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"},
                                frames=frames, cams=cams, t1=t1 or {}))
        steps.append(out.step6)
    return drv, np.array(steps), q


def test_serial_cadence_one_in_flight():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    drv, steps, _ = _run(ast, 10.0)
    assert [r["t"] for r in drv.log if r["type"] == "send"] == [0.0, 3.0, 6.0, 9.0]
    s = drv.summary()
    assert s["max_inflight"] == 1 and s["answers"] == 3 and np.abs(steps).sum() == 0.0
    assert ast.calls[0]["req"]["cameras"] == ["cam_head", "cam_wrist_left", "cam_wrist_right"]
    assert set(ast.calls[0]["req"]["trace_uv"]) <= {"cam_head", "cam_wrist_left", "cam_wrist_right"}


def test_two_agreeing_edits_move_the_full_delta():
    ed = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.02))
    drv, steps, _ = _run(ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0), 13.0)
    assert steps[:, 2].sum() == pytest.approx(0.02, abs=2e-4)
    layers = [r["layer"] for r in drv.log if r["type"] == "answer"]
    assert layers[:2] == ["apply", "confirm"]


def test_stale_edit_is_not_applied():
    ed = answer("edit", execution="failed", dp=(0.0, 0.0, 0.02))
    drv, steps, _ = _run(ScriptedCoupleAstra([ed], latency_s=7.0), 15.0)
    assert np.abs(steps).sum() == 0.0 and {r["gate"] for r in drv.log if "gate" in r} == {"stale"}


def test_events_ride_on_the_next_request():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _run(ast, 7.0, flag_at=1.0)
    assert [c["req"]["events"] for c in ast.calls] == [[], ["m7_critic_alarm"], []]


def test_budget_stop_holds_further_sends(tmp_path):
    led = CostLedger(str(tmp_path / "l.jsonl"), 60.0, TEST)  # 80 % = 48 KRW; one call ~18 KRW at these test prices
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=1.0, usage={"input_tokens": 3000, "output_tokens": 900})
    drv, _, _ = _run(ast, 10.0, ledger=led)
    s = drv.summary()
    assert s["budget_excluded"] and 1 <= s["calls_sent"] < 10
    assert any(r["type"] == "hold_send" and r["why"] == "budget" for r in drv.log)


def test_late_answer_after_timeout_is_ignored_and_charged_once(tmp_path):
    led = CostLedger(str(tmp_path / "l.jsonl"), 1000.0, TEST)
    ed = answer("edit", execution="failed", dp=(0.0, 0.0, 0.02))
    ast = ScriptedCoupleAstra([ed], latency_s=20.0, usage={"input_tokens": 3000, "output_tokens": 900})
    drv, steps, _ = _run(ast, 21.0, p=CoupleParams(request_mode="F0", timeout_s=15.0), ledger=led)
    late = [r for r in drv.log if r.get("late")]
    assert len(late) == 1 and late[0]["no"] == 1 and np.abs(steps).sum() == 0.0
    rows = [r for r in open(tmp_path / "l.jsonl", encoding="utf-8")]
    assert len(rows) == 1  # request 1 charged once (at its late arrival); request 2 still reserved
    drv.close()
    assert len([r for r in open(tmp_path / "l.jsonl", encoding="utf-8")]) == 2


def test_no_frames_no_cams_sends_text_only():
    ast = ScriptedCoupleAstra([answer("continue", views=())], latency_s=3.0)
    drv, _, _ = _run(ast, 4.0, frames={}, cams=None)
    req = ast.calls[0]["req"]
    assert req["cameras"] == [] and req["trace_uv"] == {}
    assert drv.summary()["answers"] == 1 and drv.log[0]["overlay"] == []


def test_irrev_gate_and_mismatch_event():
    bad = answer("continue", intent="misaligned")
    drv, _, _ = _run(ScriptedCoupleAstra([bad], latency_s=1.0), 2.0)
    t1 = {"gripper_open": True}
    assert drv.irrev_allowed("close", 2.0, t1, True) is False
    drv.irrev_allowed("close", 3.05, t1, True)
    assert any(e["event"] == "layer_mismatch" for e in drv.events)
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_driver.py -v` → FAIL.

- [ ] **Step 3: 구현** — `harvest/couple/driver.py`:

```python
"""CoupleDriver: the Astra–VLA coupling inside OursRuntime (spec 2026-09-26 §11-§16, canon §84 supplement 2).
Per tick (tick): trace -> timeout -> maybe send (one in flight, budget, optional pause) -> offset step -> no-progress.
Deliveries (on_delivery, through the runtime DeliveryQueue, meta kind "couple"): charge -> late? -> parse -> gate ->
layer -> offset. Per decision step (on_step): VLA fast check against the offset. The runtime asks irrev_allowed()
before an irreversible transition and forwards its event calls with flag(). The request carries the flow state (F1),
the VLA's current committed decision and motion line, the predicted tip at arrival (spec §3), the MolmoAct trace
polylines and the pending events; images (three cameras, overlay drawn in the worker thread) are labelled by name."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from ..runtime.models import jpeg_bytes
from ..runtime.reqhash import request_body
from .cost import estimate_input_tokens
from .gate import gate_answer
from .layer import AstraLayer
from .offset import OffsetApplier
from .overlay import CamModel, EETrace, draw_overlay, polylines
from .prompt import PROMPT_ID, build_input
from .schema import SCHEMA_ID, SchemaError, parse_answer
from .stream import SerialStream
from .twolayer import NoProgress, TwoLayerGate, VlaFastCheck, committed_vector

CONTACT_PHASES = ("descend", "close", "place_descend", "open")
MAG_CENTER_M = {"tiny": 0.005, "small": 0.01, "medium": 0.02, "large": 0.04, "xlarge": 0.08}


def _r(x):
    return [round(float(v), 4) for v in x]


@dataclass
class TickView:
    now: float
    dt: float
    tcp_p: np.ndarray
    phase: str
    stage: str
    near: bool
    committed: dict
    frames: dict
    cams: object = None
    t1: dict = field(default_factory=dict)
    motion: str | None = None


@dataclass
class TickOut:
    step6: np.ndarray
    speed_scale: float


def next_motion_vec(committed: dict):
    v = committed_vector(committed)
    if v is None:
        return None
    return v / float(np.linalg.norm(v)) * MAG_CENTER_M.get(committed.get("mag_coarse"), 0.0)


def predict_ee(trace: list, horizon: float, cap: float, extra) -> np.ndarray:
    (t0, p0), (t1, p1) = trace[0], trace[-1]
    d = (p1 - p0) / (t1 - t0) * horizon if t1 > t0 else np.zeros(3)
    n = float(np.linalg.norm(d))
    if n > cap:
        d = d * (cap / n)
    return p1 + d + np.asarray(extra, float)


def gripper_word(phase: str, t1: dict) -> str:
    if phase == "close":
        return "closing"
    if phase == "open":
        return "opening"
    g = t1.get("gripper_open")
    return "open" if g is True else "closed" if g is False else "unknown"


class CoupleDriver:
    def __init__(self, p, astra, ledger, submit, task: str, episode: int = 1):
        self.p, self.astra, self.ledger, self.submit, self.task, self.episode = p, astra, ledger, submit, task, episode
        self.stream = SerialStream(p, ledger)
        self.layer, self.offset, self.gate = AstraLayer(p), OffsetApplier(p), TwoLayerGate(p)
        self.fast, self.stag = VlaFastCheck(p), NoProgress(p)
        self.trace = EETrace(keep_s=max(p.trace_s, 0.5) + 1.0)
        self.last, self.last_t = None, None
        self.log, self.events, self.blobs = [], [], {}
        self.est_text_tokens = p.est_text_tokens
        self.budget_hit, self.stop_confirmed_t, self._hold = False, None, None

    def key(self, no: int) -> str:
        return f"e{self.episode}:{no}"

    def flag(self, name: str, now: float) -> None:
        self.stream.flag(name, now)
        self.events.append({"t": round(now, 3), "event": name})

    # ------------------------------------------------------------------ per tick
    def tick(self, v: TickView) -> TickOut:
        self.trace.add(v.now, v.tcp_p)
        no = self.stream.timed_out(v.now)
        if no is not None:
            self.log.append({"type": "timeout", "no": no, "t": round(v.now, 3)})
        cams = [c for c in self.p.cameras if v.frames.get(c) is not None]
        est = self.ledger.prices.krw_upper(estimate_input_tokens(self.est_text_tokens, cams), self.p.max_output_tokens)
        ok, why = self.stream.next_send(v.now, bool(v.near or v.phase in CONTACT_PHASES), est)
        if ok:
            self._send(v, cams, est)
        elif why in ("budget", "pause") and why != self._hold:
            self.log.append({"type": "hold_send", "why": why, "t": round(v.now, 3), "ledger": self.ledger.state()})
        if why == "budget":
            self.budget_hit = True
        self._hold = None if ok else why
        step = self.offset.step(v.now, v.dt)
        if self.stag.update(v.now, v.tcp_p, self.offset.applied[:3]):
            self.flag("no_progress", v.now)
        return TickOut(step, self.p.slow_factor if self.stream.slowed(v.now) else 1.0)

    def request(self, v: TickView, no: int, events: list, cams: list) -> dict:
        nxt = next_motion_vec(v.committed)
        pred = predict_ee(self.trace.window(v.now, 0.5), self.stream.L_hat, self.p.predict_cap_m, self.offset.rem[:3])
        req = {"schema": SCHEMA_ID, "mode": self.p.request_mode, "request_no": no, "t_state": round(v.now, 3),
               "task": self.task, "active_arm": self.p.active_arm, "cameras": list(cams), "tip_now_m": _r(v.tcp_p),
               "vla_now": {"stage": v.stage, "phase": v.phase, "committed": dict(sorted(v.committed.items())),
                           "next_motion_m": None if nxt is None else _r(nxt), "motion": v.motion},
               "predicted_ee_at_arrival": {"pos_m": _r(pred), "horizon_s": round(self.stream.L_hat, 2),
                                           "gripper": gripper_word(v.phase, v.t1),
                                           "method": "0.5 s tip velocity x horizon (capped) + remaining correction"},
               "events": list(events)}
        if self.p.request_mode == "F1":
            req["flow_state"] = {"last_command": self.layer.flow_last(), "task_progress": self.layer.progress,
                                 "active_offset": self.offset.state_json()}
        return req

    def _send(self, v: TickView, cams: list, est: float) -> None:
        no, events = self.stream.sent(v.now)
        req = self.request(v, no, events, cams)
        frames = {c: np.asarray(v.frames[c]).copy() for c in cams}
        raw = (v.cams() if callable(v.cams) else v.cams) if (self.p.overlay and cams) else None
        models = {c: CamModel.from_dict(raw[c]) for c in cams if raw and c in raw}
        pts = [q for _, q in self.trace.window(v.now, self.p.trace_s)]
        req["trace_uv"] = polylines(models, pts[::-1])
        tip, nxt, off = np.asarray(v.tcp_p, float).copy(), next_motion_vec(v.committed), self.offset.rem[:3].copy()
        self.ledger.reserve(self.key(no), est)
        astra, p, task, ep = self.astra, self.p, self.task, self.episode
        pid = PROMPT_ID[p.request_mode]

        def run():  # worker thread: overlay, JPEG, request hash, the call
            images = {}
            for c, img in frames.items():
                if c in models:
                    img = draw_overlay(img, models[c], tip=tip, trace=pts, next_vec=nxt, offset_vec=off,
                                       wrist=c != "cam_head")
                images[c] = jpeg_bytes(img)
            inp = build_input(req, images, p, task)
            text_only = [{**m, "content": [x for x in m["content"] if x.get("type") != "input_image"]} for m in inp]
            h, ims, body = request_body({"api": "astra-couple", "model": getattr(astra, "model", ""),
                                         "effort": p.effort, "max_out": p.max_output_tokens, "prompt_id": pid,
                                         "input": text_only}, images)
            rec = astra.call(inp, p.effort, p.max_output_tokens, {"couple_no": no, "episode": ep, "prompt_id": pid})
            lat = getattr(astra, "synthetic_latency", None)
            return {"latency_s": lat if lat is not None else rec.t_done - rec.t_send, "rec": rec,
                    "req_hash": (h, ims), "req_body": body, "images_raw": images,
                    "text_chars": len(inp[0]["content"][0]["text"])}
        self.submit(v.now, run, getattr(astra, "synthetic_latency", None),
                    {"kind": "couple", "no": no, "episode": ep, "t_state": v.now, "cameras": list(cams)})
        self.log.append({"type": "send", "no": no, "t": round(v.now, 3), "events": list(events),
                         "cameras": list(cams), "est_krw": round(est, 4), "overlay": sorted(models)})

    # ------------------------------------------------------------------ deliveries
    def on_delivery(self, r: dict, now: float, t1: dict) -> None:
        m, rec = r["meta"], r["rec"]
        no = m["no"]
        cost = self.ledger.charge(self.key(no), rec.usage or None,
                                  {"no": no, "resp_model": rec.model_field, "error": rec.error})
        h, ims = r["req_hash"]
        self.blobs[h] = ("json", r["req_body"])
        for c, b in (r.get("images_raw") or {}).items():
            self.blobs[ims[c]] = ("jpg", b)
        if r.get("text_chars"):
            self.est_text_tokens = max(1, int(r["text_chars"]) // 4)
        row = {"type": "answer", "no": no, "t_state": round(m["t_state"], 3), "t_deliver": round(r["t_deliver"], 3),
               "latency_s": round(float(r["latency_s"]), 3), "cost_krw": round(cost, 4), "usage": rec.usage,
               "error": rec.error, "model": rec.model_field, "effort": rec.effort, "request_sha256": h,
               "image_sha256": ims, "output_text": rec.output_text, "prompt_id": PROMPT_ID[self.p.request_mode]}
        if self.stream.is_late(no):
            row["late"] = True
            self.log.append(row)
            return
        a, ok = None, rec.error is None
        if ok:
            try:
                a = parse_answer(rec.output_text, self.p.request_mode, m["cameras"], no, m["t_state"],
                                 r["t_deliver"])
            except SchemaError as e:
                ok, row["schema_error"] = False, e.problems
        self.stream.delivered(no, now, ok, float(r["latency_s"]))
        if not ok:
            self.log.append(row)
            return
        a = gate_answer(a, self.p, t1)
        res = self.layer.on_answer(a)
        if res.action in ("apply", "confirm"):
            self.offset.command(res.key, res.edit.vec6(), res.weight, now, self.stream.L_hat)
        elif res.action == "flip":
            self.offset.reset(now, "flip")
        elif res.action == "stop_confirmed":
            self.stop_confirmed_t = now
            self.flag("astra_stop_confirmed", now)
        if a.info_request == "slow_down":
            self.stream.request_slow(now)
        self.last, self.last_t = a, now
        row.update(gate=a.gate, notes=list(a.notes), diff=a.diff, command=a.command, execution=a.execution,
                   intent=a.intent, confidence=a.confidence, claims=[list(c) for c in a.claims],
                   takeover_ok=a.takeover_ok, layer=res.action, weight=res.weight, age_s=round(a.age, 3),
                   info_request=a.info_request)
        self.log.append(row)

    # ------------------------------------------------------------------ per decision step / gate
    def on_step(self, committed: dict, outcome: str, now: float) -> None:
        if not self.offset.active:
            self.fast.reset()
            return
        if self.fast.on_step(committed_vector(committed), self.offset.direction()):
            self.offset.scale_remaining(self.p.contra_factor, now, "vla_contra")
            self.flag("offset_contradicted", now)
        if outcome in ("DEVIATE", "CONTRADICT"):
            self.flag("offset_vs_b", now)

    def irrev_allowed(self, kind: str, now: float, t1: dict, near: bool) -> bool:
        ok, _ = self.gate.allow(kind, now, self.last, self.last_t, t1, near)
        if not ok and self.gate.mismatch_due(kind, now):
            self.flag("layer_mismatch", now)
        return ok

    # ------------------------------------------------------------------ summary
    def summary(self) -> dict:
        ans = [r for r in self.log if r["type"] == "answer" and not r.get("late")]
        good = [r for r in ans if "gate" in r]
        lat = [r["latency_s"] for r in ans if r.get("error") is None]

        def pct(xs, q):
            return round(float(np.percentile(xs, q)), 3) if xs else None
        return {"calls_sent": self.stream.n_sent, "answers": len(good),
                "schema_errors": sum(1 for r in ans if "schema_error" in r),
                "api_errors": sum(1 for r in ans if r.get("error")), "timeouts": self.stream.counts["timeouts"],
                "late": sum(1 for r in self.log if r.get("late")), "max_inflight": self.stream.max_inflight,
                "max_outstanding": self.stream.max_outstanding, "latency_s": {"p50": pct(lat, 50), "p95": pct(lat, 95)},
                "answer_age_s": {"p50": pct([r["age_s"] for r in good], 50)},
                "cost_krw": round(sum(r.get("cost_krw", 0.0) for r in self.log if r["type"] == "answer"), 4),
                "gates": dict(Counter(r["gate"] for r in good)), "layer": dict(self.layer.counts),
                "offset": self.offset.stats(), "irrev": dict(self.gate.counts),
                "events": dict(Counter(e["event"] for e in self.events)), "budget_excluded": self.budget_hit,
                "stop_confirmed_t": self.stop_confirmed_t, "prompt_id": PROMPT_ID[self.p.request_mode],
                "params": self.p.to_json(), "ledger": self.ledger.state()}

    def close(self) -> None:
        self.ledger.finalize(prefix=f"e{self.episode}:")
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple -v` → 전부 PASS.
- [ ] **Step 5: 커밋** — `msg_task9.txt` 첫 줄 `couple: CoupleDriver (serial stream, layer, offset, gate, overlay, ledger, logs) (Task 9)`.

---

### Task 10: 런타임 배선 (core·skills·ir_policy)

**Files:**
- Create: `harvest/couple/geom.py`
- Modify: `harvest/runtime/core.py`(RuntimeConfig, `__init__`, `reset`, `close`, `act`, `_deliver`, `_on_verify`, `_j5`, `_boundary`, `_execute`, `_play_chunk`, `summary`, 새 도우미 5개), `harvest/runtime/skills.py`(`speed_scale`, `irrev_gate`, `_gate`, `nudge`), `harvest/runtime/ir_policy.py`(사이드카 `couple` 행)
- Test: `tests/runtime/test_couple_runtime.py`, `tests/couple/test_geom.py`

**Interfaces:**
- Consumes: `CoupleDriver`, `TickView`, `CoupleParams`, `CostLedger`, `PriceTable`, `ScriptedCoupleAstra`, `answer`.
- Produces: `RuntimeConfig.couple: str = "off"`(`off|serial`), `couple_params: dict`, `couple_budget_krw: float`, `couple_ledger: str`, `couple_prices: str`, `couple_run_id: str`; `OursRuntime.driver`, `OursRuntime.couple_ledger`, `OursRuntime.episode`, `OursRuntime._event(now, name)`, `OursRuntime._t1()`; `summary()["couple"]`; 사이드카 행 `type="couple"`. `PickPlaceSkill.speed_scale`, `.irrev_gate: Callable[[str, float], bool] | None`, `.nudge(step6, table_z) -> (pos, quat)`. `geom.quat_from_rotvec(rv) -> wxyz`, `geom.quat_mul(a, b) -> wxyz`.

- [ ] **Step 1: 실패하는 시험**

`tests/couple/test_geom.py`:

```python
import numpy as np

from harvest.couple.geom import quat_from_rotvec, quat_mul


def test_rotvec_and_product():
    q = quat_from_rotvec([0, 0, np.pi / 2])
    np.testing.assert_allclose(q, [np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)], atol=1e-12)
    np.testing.assert_allclose(quat_from_rotvec([0, 0, 0]), [1, 0, 0, 0])
    np.testing.assert_allclose(quat_mul(q, q), [0, 0, 0, 1], atol=1e-12)
```

`tests/runtime/test_couple_runtime.py`:

```python
import json

import numpy as np
import pytest

from harvest.couple.cost import PriceTable
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockFusedModel, MockSelector

from .fakeworld import FakeWorld

FRAME = np.full((12, 16, 3), 60, np.uint8)
NO_FAST = {"contra_steps": 10 ** 6}  # the VLA fast check is Task 7's test; here the offset must run in full


def _run(backend, astra, seconds, params=None, **cfg_kw):
    """F0 answers (the scripted answers carry no diff); params = extra CoupleParams overrides."""
    model = MockFusedModel(latency_s=0.30) if backend == "fused" else MockSelector(latency_s=0.30)
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="mock", couple="serial",
                        couple_params={"request_mode": "F0", **(params or {})}, **cfg_kw)
    rt = OursRuntime(cfg, model, astra=astra)
    rt.reset()
    w = FakeWorld()
    hist = []
    for i in range(int(seconds * 100)):
        o = w.obs()
        if i % 10 == 0:
            o["images"] = {c: FRAME for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
        a, meta = rt.act(o)
        w.step(a)
        hist.append((w.t, meta["phase"], w.tcp.copy()))
    return rt, w, hist


def test_serial_continue_completes_pick_and_place_with_one_request_in_flight():
    rt, w, hist = _run("modular", ScriptedCoupleAstra([answer("continue")], latency_s=3.0), 40.0)
    phases = {p for _, p, _ in hist}
    assert {"close", "lift", "carry", "open", "retreat"} <= phases
    s = rt.summary()["couple"]
    assert s["max_inflight"] == 1 and 11 <= s["calls_sent"] <= 15 and s["answers"] >= 11
    assert rt.astra_log == []  # heartbeat off in couple mode
    rt.close()


def _bad_outcomes(rt):
    return sum(1 for e in rt.slots_log if e.get("prev_outcome") in ("DEVIATE", "CONTRADICT"))


def test_offset_does_not_create_false_b_deviations():
    base, _, _ = _run("modular", ScriptedCoupleAstra([answer("continue")], latency_s=3.0), 12.0,
                      params=NO_FAST)
    ed = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.03))
    rt, w, hist = _run("modular", ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0), 12.0,
                       params=NO_FAST)
    s = rt.summary()["couple"]
    assert s["offset"]["applied_m"][2] == pytest.approx(0.03, abs=2e-3)
    assert _bad_outcomes(rt) <= _bad_outcomes(base)  # the shifted reference is what (b) compares with
    jumps = [float(np.linalg.norm(b[2] - a[2])) for a, b in zip(hist, hist[1:])]
    assert max(jumps) <= 0.20 * 0.01 + 0.08 * 0.01 + 1e-9  # skill speed + offset speed per tick
    base.close()
    rt.close()


def test_fresh_misaligned_astra_blocks_the_grasp():
    veto = ScriptedCoupleAstra([answer("continue", intent="misaligned")], latency_s=2.5)
    rt, _, hist = _run("modular", veto, 25.0)
    assert "close" not in {p for _, p, _ in hist}
    s = rt.summary()["couple"]
    assert s["irrev"].get("deny:astra_misaligned", 0) >= 1 and s["events"].get("layer_mismatch", 0) >= 1
    rt.close()
    ok = ScriptedCoupleAstra([answer("continue")], latency_s=2.5)
    rt2, _, hist2 = _run("modular", ok, 25.0)
    assert "close" in {p for _, p, _ in hist2}
    rt2.close()


def test_fused_offset_reaches_the_arm_through_ik():
    ed = answer("edit", execution="failed", dp=(0.0, 0.02, 0.0))
    rt, w, hist = _run("fused", ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0), 12.0,
                       params=NO_FAST)
    assert rt.summary()["couple"]["offset"]["applied_m"][1] == pytest.approx(0.02, abs=2e-3)
    assert w.tcp[1] - hist[0][2][1] == pytest.approx(0.02, abs=5e-3)  # MockFused holds; the bias moves the tip
    rt.close()


def test_reset_with_request_in_flight_charges_and_forgets_it(tmp_path):
    f = tmp_path / "prices.json"
    f.write_text('{"model": "test", "date": "2026-09-26", "usd_per_mtok_input": 2.0, "usd_per_mtok_cached_input": 0.5,'
                 ' "usd_per_mtok_output": 8.0, "krw_per_usd": 1400.0, "source": "unit test"}')
    led = str(tmp_path / "ledger.jsonl")
    ast = ScriptedCoupleAstra([answer("edit", execution="failed", dp=(0.0, 0.0, 0.02))], latency_s=3.0,
                              usage={"input_tokens": 3000, "output_tokens": 900})
    rt, w, _ = _run("modular", ast, 1.0, couple_prices=str(f), couple_budget_krw=1000.0, couple_ledger=led)
    assert list(rt.couple_ledger.reserved) == ["e1:1"]
    rt.reset()
    assert rt.couple_ledger.reserved == {} and rt.episode == 2
    kinds = [json.loads(x)["kind"] for x in open(led, encoding="utf-8")]
    assert kinds == ["unanswered"]
    for _ in range(200):
        a, _ = rt.act(w.obs())
        w.step(a)
    s = rt.summary()["couple"]
    assert s["offset"]["applied_m"] == [0.0, 0.0, 0.0] and s["answers"] == 0
    rt.close()


def test_paid_couple_mode_needs_prices_budget_and_ledger():
    with pytest.raises(ValueError, match="couple_prices"):
        OursRuntime(RuntimeConfig(couple="serial", astra_mode="api"), MockSelector(), astra=ScriptedCoupleAstra([]))
    with pytest.raises(ValueError, match="off \\| serial"):
        OursRuntime(RuntimeConfig(couple="stagger"), MockSelector())
    assert PriceTable.free().is_free
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_geom.py tests/runtime/test_couple_runtime.py -v` → FAIL(`geom` 없음, `RuntimeConfig`에 `couple` 없음).

- [ ] **Step 3: `harvest/couple/geom.py`**

```python
"""Quaternion helpers (w, x, y, z) for the coupling offset (rotation-vector edits)."""
from __future__ import annotations

import math

import numpy as np


def quat_from_rotvec(rv) -> np.ndarray:
    rv = np.asarray(rv, float)
    a = float(np.linalg.norm(rv))
    if a < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return np.r_[math.cos(a / 2), math.sin(a / 2) * rv / a]


def quat_mul(a, b) -> np.ndarray:
    w1, x1, y1, z1 = (float(v) for v in a)
    w2, x2, y2, z2 = (float(v) for v in b)
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])
```

- [ ] **Step 4: `harvest/runtime/skills.py` 수정**

`PickPlaceSkill.__init__` 끝에 두 줄:

```python
        self.irrev_gate = None  # couple.driver irrev_allowed(kind, t): two-layer gate (spec §5); None = off
        self.speed_scale = 1.0  # couple slow down (spec §7, info_request slow_down)
```

`tick()`의 `if ph == "next":` 블록 세 조건에 게이트를 더한다(나머지는 그대로):

```python
            if (self.stage == "S1" and gs == "open" and M == "grasp" and reached and self.retries <= self.max_retries
                    and self._gate("close", t)):
                ...
            if (self.stage == "S1" and pred.get("holding(o3)") and pred.get("lifted(o3)")
                    and self.stage_gate == "self" and self._gate("stage", t)):
                ...
            elif (self.stage == "S2" and gs == "closed_holding" and M == "place"
                  and (pred.get("in_contact(o3,o5)") or reached) and self._gate("release", t)):
                ...
```

같은 `tick()`의 이동 한 걸음을 `step = min(V.get(self.phase, 0.06) * self.speed_scale * self.dt, n, self.cap_left)`로 바꾼다. 클래스에 메서드 둘:

```python
    def _gate(self, kind: str, t: float) -> bool:
        return self.irrev_gate is None or bool(self.irrev_gate(kind, t))

    def nudge(self, step6, table_z: float):
        """One tick of the Astra offset (couple.offset): the reference itself moves (the skill goes on from the shifted
        point and M4 (b) compares the measured TCP with it); rotation turns cmd_quat (the skill slerps it back)."""
        from ..couple.geom import quat_from_rotvec, quat_mul
        s = np.asarray(step6, float)
        p = self.cmd_pos + s[:3]
        self.cmd_pos = np.array([np.clip(p[0], *WS_X), np.clip(p[1], *WS_Y),
                                 np.clip(p[2], table_z + WS_Z[0], table_z + WS_Z[1])])
        if np.any(s[3:]):
            self.cmd_quat = quat_mul(quat_from_rotvec(s[3:]), self.cmd_quat)
        return self.cmd_pos.copy(), self.cmd_quat.copy()
```

`reset()`은 `speed_scale`을 되돌리지 않는다(런타임이 매 틱 넣는다).

- [ ] **Step 5: `harvest/runtime/core.py` 수정**

(a) `RuntimeConfig` 끝(`astra_canary_id` 다음)에:

```python
    # spec 2026-09-26 Astra–VLA coupling: "off" = no stream (E-M8c heartbeat cadences as before); "serial" = one
    # general-control Astra request in flight (canon §84 supp 2), two-layer M4, smooth offset; the heartbeat is off
    # and the event calls mark the next stream request (plan ruling 9)
    couple: str = "off"
    couple_params: dict = field(default_factory=dict)  # CoupleParams overrides (logged in summary couple.params)
    couple_budget_krw: float = 0.0  # the experiment cap from its pre-registration (spec §15)
    couple_ledger: str = ""  # JSONL cost ledger under /data, shared by the workers of one experiment
    couple_prices: str = ""  # the run day's price table (required with the paid API)
    couple_run_id: str = ""
```

(b) `__init__` 끝(`self.rules = ProprioRules()` 다음)에:

```python
        if cfg.couple not in ("off", "serial"):
            raise ValueError(f"couple {cfg.couple!r}: off | serial (spec 2026-09-26 §16)")
        self.couple_ledger, self.driver, self.episode = None, None, 0
        if cfg.couple == "serial":
            from ..couple.cost import CostLedger, PriceTable
            if cfg.astra_mode == "api" and not (cfg.couple_prices and cfg.couple_budget_krw > 0 and cfg.couple_ledger):
                raise ValueError("couple serial on the paid API needs couple_prices (the run day's price table), "
                                 "couple_budget_krw > 0 and couple_ledger (canon §82 supplement, spec §15)")
            prices = PriceTable.load(cfg.couple_prices) if cfg.couple_prices else PriceTable.free()
            self.couple_ledger = CostLedger(cfg.couple_ledger or None, cfg.couple_budget_krw, prices,
                                            run_id=cfg.couple_run_id)
```

(c) `reset()` 끝(`self._trace = deque(maxlen=40)` 다음)에:

```python
        if self.driver is not None:
            self.driver.close()  # the last episode's request in flight: charged as unanswered, never applied
        self.driver, self.couple_out, self._off_hist = None, None, []
        self._bias_q, self._chunk_played = np.zeros(7), False
        self.episode += 1
        if self.cfg.couple == "serial":
            from ..couple.driver import CoupleDriver
            from ..couple.params import CoupleParams
            if self.astra is None:
                raise ValueError("couple serial needs an Astra client (api, mock or local)")
            self.driver = CoupleDriver(CoupleParams(**self.cfg.couple_params), self.astra, self.couple_ledger,
                                       self._submit_couple, self.instruction, episode=self.episode)
            self.hb = HeartbeatScheduler(self.cfg.hb_N_s, self.cfg.hb_timeout_s, mode="K0")
            self.skill.irrev_gate = self._irrev_gate
```

(d) `close()` 첫 줄에 `if getattr(self, "driver", None) is not None: self.driver.close()`(두 줄로).

(e) 새 도우미(“helpers” 절에):

```python
    def _t1(self) -> dict:
        return values(self.meas_last) if self.meas_last is not None else {}

    def _submit_couple(self, now, fn, fixed_latency, meta):
        self.q.submit(now, self.pool.submit(fn), fixed_latency=fixed_latency, meta=meta)

    def _irrev_gate(self, kind: str, t: float) -> bool:
        return self.driver.irrev_allowed(kind, t, self._t1(), self.near_now)

    def _event(self, now: float, name: str) -> None:
        """An event call (canon §45): pulls the heartbeat forward (off in couple mode) and marks the next coupling
        request (spec §16: the request in flight is not cancelled)."""
        self.hb.advance(now)
        if self.driver is not None:
            self.driver.flag(name, now)

    def _couple_fused(self, a, now, kin, tcp_p):
        """Fused path: the offset moved since the current chunk's observation is added as a joint bias (IK difference
        at the measured tip; the chunk already contains earlier shifts, plan ruling 5). A held action (no chunk played
        this tick = last_a) already carries last tick's bias, so that bias is taken out first (no double count). A
        gripper transition in the chunk is held unless the two layers agree (spec §5)."""
        from ..couple.geom import quat_from_rotvec, quat_mul
        a = np.asarray(a, float).copy()
        if not self._chunk_played:
            a[:7] = a[:7] - self._bias_q
        st = self.couple_out.step6 if self.couple_out is not None else None
        if st is not None and np.any(st):
            self._off_hist.append((now, st.copy()))
        c = self.chunks.get(self.cur_k)
        t0 = c["t_state"] if c is not None else -math.inf
        self._off_hist = [(t, s) for t, s in self._off_hist if t > t0]
        self._bias_q = np.zeros(7)
        if self._off_hist:
            b = np.sum([s for _, s in self._off_hist], axis=0)
            p0, q0 = kin.tcp_pose()
            q_to = kin.ik(np.asarray(p0, float) + b[:3], quat_mul(quat_from_rotvec(b[3:]), q0), 0.2)
            q_at = kin.ik(np.asarray(p0, float), q0, 0.2)
            self._bias_q = (np.asarray(q_to, float) - np.asarray(q_at, float))[:7]
            a[:7] = a[:7] + self._bias_q
        w_prev = float(self.last_a[7]) if self.last_a is not None else float(a[7])
        t1 = self._t1()
        kind = ("close" if a[7] < w_prev - 0.005 and t1.get("gripper_open") else
                "release" if a[7] > w_prev + 0.005 and t1.get("holding_t") else None)
        if kind is not None and not self.driver.irrev_allowed(kind, now, t1, self.near_now):
            a[7] = w_prev
        return a
```

(f) 사건 호출 다섯 곳을 `_event`로 바꾼다: `_on_verify`의 `self.hb.advance(now)` → `self._event(now, "m7_critic_alarm")`; `_j5`의 → `self._event(now, "j5_escalate")`; `_boundary`의 M7 하드 채널 → `self._event(now, "m7_hard_t1")`, CONTRADICT → `self._event(now, "b_contradict")`; `_execute`의 `object_lost`/`grasp_miss` → `self._event(now, e["event"])`.

(g) `act()`: 하트비트 줄을 `kind = self.hb.next_kind(now) if self.astra is not None and self.driver is None else None`로. `if self.cfg.backend == "fused": self._maybe_request_chunk(now, obs)` 바로 앞에:

```python
        if self.driver is not None:
            from ..couple.driver import TickView
            self.couple_out = self.driver.tick(TickView(
                now=now, dt=self.dt, tcp_p=np.asarray(tcp_p, float), phase=self.skill.phase, stage=self.skill.stage,
                near=self.near_now, committed={q: c for q, c in self.skill.dec.items() if c is not None},
                frames=self.frames, cams=obs.get("cams"), t1=self._t1(), motion=None))
```

(h) `_deliver` 첫머리(`m = r["meta"]` 다음):

```python
        if m["kind"] == "couple":
            self.driver.on_delivery(r, now, self._t1())
            self.blobs.update(self.driver.blobs)
            self.driver.blobs.clear()
            return
```

(i) `_boundary`에서 `self.skill.begin_slot(k, dec)` 다음 줄:

```python
        if self.driver is not None:
            self.driver.on_step(dec, entry.get("prev_outcome", "OK"), now)
```

(j) `_execute`: `cmd = self.skill.tick(...)` 앞에 `if self.couple_out is not None: self.skill.speed_scale = self.couple_out.speed_scale`, 바로 뒤에:

```python
        if self.couple_out is not None and self.cfg.backend != "fused" and np.any(self.couple_out.step6):
            cmd.pos_w, cmd.quat_w = self.skill.nudge(self.couple_out.step6, tz)
```

융합 분기 `a = self._play_chunk(now, q_meas)` 다음 줄: `if self.driver is not None: a = self._couple_fused(a, now, kin, tcp_p)`(두 줄로).

(k) `_play_chunk`: 재생 줄을 속도 배율로 바꾸고, 재생했는지를 `self._chunk_played`에 남긴다(첫 줄에 `self._chunk_played = False`, 재생 분기 안에서 `True`):

```python
        self._chunk_played = False
        ...
        if c is not None and c["dec"] == dec and dec:
            self.chunk_stats["played"] += 1
            self._chunk_played = True
            scale = self.couple_out.speed_scale if self.couple_out is not None else 1.0
            return chunk_value(c["chunk"], c["dt"], c["t_state"], c["t_state"] + (now - c["t_state"]) * scale)
```

(l) `summary()` 딕셔너리에 `"couple": self.driver.summary() if self.driver is not None else None`.

- [ ] **Step 6: `harvest/runtime/ir_policy.py`** — `on_trial_end`의 행 목록 튜플에 `("couple", rt.driver.log if getattr(rt, "driver", None) is not None else [])`를 더한다.

- [ ] **Step 7: 통과 확인** — `python -m pytest tests/couple tests/runtime -v` → 전부 PASS(기존 `tests/runtime/*`도 그대로 통과해야 한다: `couple="off"`가 기본이고 사건 호출은 `_event` 안에서 같은 `hb.advance`를 부른다). 실패하면 `superpowers:systematic-debugging`.

- [ ] **Step 8: 전체 회귀** — `python -m pytest -q` → 실패 0(기존 skip 수 그대로).

- [ ] **Step 9: 커밋** — `msg_task10.txt` 첫 줄 `runtime: wire the Astra coupling (serial stream, offset, two-layer gate) into OursRuntime (Task 10)`; `git add harvest/couple/geom.py harvest/runtime/core.py harvest/runtime/skills.py harvest/runtime/ir_policy.py tests/couple/test_geom.py tests/runtime/test_couple_runtime.py`.

---

### Task 11: falsify 먼저 — 복구안 재사용 캐시

**Files:**
- Create: `harvest/couple/recovery_cache.py`
- Modify: `harvest/runtime/core.py`(`__init__`에 캐시, `_fail_event`, T_fail 대역 세 곳), `harvest/runtime/ir_policy.py`(사이드카 `recovery` 행)
- Test: `tests/couple/test_recovery_cache.py`

**Interfaces:**
- Produces: `FailSig(stage, target, mode, evidence)` + `to_json()`; `Lesson(sig, recovery, falsify, falsify_text, source, t)`; `check_falsify(checks)`; `falsified(checks, facts) -> "yes"|"no"|"unknown"`; `RecoveryCache()` — `remember(sig, recovery, falsify, falsify_text, source, now)`, `decide(episode, sig, facts, now) -> tuple[str, Lesson|None, str]`(결정 `reuse|call_j2`, 이유 `first_seen|partial_match|reuse_cap|reuse_failed|falsified|falsify_unknown|not_falsified`), `report(episode, sig, success, now)`, `audit: list`. 런타임 `OursRuntime.recovery`, `OursRuntime.recovery_apply(lesson) -> str`(기본 `"m9_not_built"`), `OursRuntime._fail_event(now, mode, evidence)`.
- 반증 조건 형식(J2 출력이 이 형식으로 들어온다고 정함): `[{"pred": <measure 값 이름: holding_t, gripper_open, lifted_holding, contact_tp, on_tp, lifted_t>, "value": true|false}]` — 하나라도 현재 측정값과 같으면 반증됨, 측정값이 없으면(`None`) "unknown" → J2.

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_recovery_cache.py`:

```python
import pytest

from harvest.couple.recovery_cache import FailSig, RecoveryCache, falsified

SIG = FailSig("S1", "o3", "grasp_miss", "t1_skill")
REC = {"lever": "dp.approach_dir", "value": "side_front"}
FALS = [{"pred": "holding_t", "value": True}]


def test_first_seen_then_one_reuse_per_episode():
    c = RecoveryCache()
    assert c.decide(1, SIG, {"holding_t": False}, 0.0)[:2] == ("call_j2", None)
    c.remember(SIG, REC, FALS, "if the mug ends up held the miss was timing, not approach", "j2:call7", 1.0)
    d, lesson, why = c.decide(1, SIG, {"holding_t": False}, 2.0)
    assert (d, why) == ("reuse", "not_falsified") and lesson.recovery == REC
    assert c.decide(1, SIG, {"holding_t": False}, 3.0)[::2] == ("call_j2", "reuse_cap")
    assert c.decide(2, SIG, {"holding_t": False}, 4.0)[0] == "reuse"


def test_partial_signature_never_reuses():
    c = RecoveryCache()
    c.remember(SIG, REC, FALS, "x", "j2:1", 0.0)
    other = FailSig("S1", "o3", "grasp_miss", "v1h_critic")
    assert c.decide(1, other, {"holding_t": False}, 1.0)[::2] == ("call_j2", "partial_match")


def test_falsified_or_unknown_goes_to_j2_and_failed_reuse_is_recorded():
    c = RecoveryCache()
    c.remember(SIG, REC, FALS, "x", "j2:1", 0.0)
    assert c.decide(1, SIG, {"holding_t": True}, 1.0)[::2] == ("call_j2", "falsified")
    assert c.decide(2, SIG, {}, 1.0)[::2] == ("call_j2", "falsify_unknown")
    assert c.decide(3, SIG, {"holding_t": False}, 2.0)[0] == "reuse"
    c.report(3, SIG, False, 5.0)
    assert c.decide(3, SIG, {"holding_t": False}, 6.0)[::2] == ("call_j2", "reuse_failed")
    kinds = [a["event"] for a in c.audit]
    assert kinds.count("decide") == 4 and "reuse_outcome" in kinds and "remember" in kinds


def test_falsify_format_is_checked():
    assert falsified([{"pred": "on_tp", "value": False}], {"on_tp": True}) == "no"
    with pytest.raises(ValueError, match="pred"):
        RecoveryCache().remember(SIG, REC, [{"value": True}], "x", "j2:1", 0.0)
```

`tests/runtime/test_recovery_hook.py`:

```python
from harvest.couple.recovery_cache import FailSig
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockSelector

from .fakeworld import FakeWorld

SIG = FailSig("S1", "o3", "grasp_miss", "t1_skill")
REC = {"lever": "dp.approach_dir", "value": "side_front"}
FALS = [{"pred": "holding_t", "value": True}]


def test_runtime_fail_event_reuses_without_calling_astra():
    rt = OursRuntime(RuntimeConfig(clock="simlat"), MockSelector())
    rt.reset()
    w = FakeWorld()
    rt.act(w.obs())
    rt.recovery.remember(SIG, REC, FALS, "x", "j2:test", 0.0)
    before = rt.hb.next_t
    rt._fail_event(0.5, "grasp_miss", "t1_skill")
    ev = [e for e in rt.events if e["event"] in ("fail_path", "recovery_reuse")]
    assert [e["event"] for e in ev] == ["fail_path", "recovery_reuse"] and ev[1]["applied"] == "m9_not_built"
    assert rt.hb.next_t == before  # no Astra call pulled forward
    rt._fail_event(0.6, "grasp_miss", "t1_skill")
    assert rt.events[-1]["decision"] == "call_j2" and rt.events[-1]["why"] == "reuse_cap"
    rt.close()
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_recovery_cache.py -v` → FAIL.

- [ ] **Step 3: 구현** — `harvest/couple/recovery_cache.py`:

```python
"""Falsify-first recovery reuse (canon §84 + supplement 1). A repeated diagnosis with the SAME failure signature
(stage + target object + failure type + detector evidence) first evaluates the stored lesson's falsify checks in code;
not falsified -> the stored recovery is reused without an Astra call, at most once per episode and signature; a
falsified / unevaluable lesson, a second repeat, a failed reuse, a partial signature match or a first-seen diagnosis
-> Astra J2. Every branch is appended to `audit` (J5 audit and J6 distillation input: Astra sees the reuses later).
Lessons are kept across episodes (runtime lifetime); the reuse cap is per episode."""
from __future__ import annotations

from dataclasses import asdict, astuple, dataclass

PREDS = ("holding_t", "gripper_open", "lifted_holding", "contact_tp", "on_tp", "lifted_t")


@dataclass(frozen=True)
class FailSig:
    stage: str
    target: str
    mode: str
    evidence: str

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class Lesson:
    sig: FailSig
    recovery: dict
    falsify: tuple
    falsify_text: str
    source: str
    t: float


def check_falsify(checks) -> tuple:
    out = []
    for c in checks:
        if not (isinstance(c, dict) and c.get("pred") in PREDS and isinstance(c.get("value"), bool)):
            raise ValueError(f"falsify check {c!r}: {{pred in {PREDS}, value: bool}}")
        out.append({"pred": c["pred"], "value": c["value"]})
    return tuple(out)


def falsified(checks, facts: dict) -> str:
    vals = [facts.get(c["pred"]) for c in checks]
    if any(v is not None and bool(v) == c["value"] for v, c in zip(vals, checks)):
        return "yes"
    return "unknown" if any(v is None for v in vals) else "no"


class RecoveryCache:
    def __init__(self):
        self.lessons, self.reuse, self.audit = {}, {}, []

    def remember(self, sig: FailSig, recovery: dict, falsify, falsify_text: str, source: str, now: float) -> None:
        self.lessons[sig] = Lesson(sig, dict(recovery), check_falsify(falsify), falsify_text, source, now)
        self.audit.append({"t": round(now, 3), "event": "remember", "sig": sig.to_json(), "source": source,
                           "recovery": dict(recovery), "falsify_text": falsify_text})

    def _log(self, now, episode, sig, decision, lesson, why):
        self.audit.append({"t": round(now, 3), "event": "decide", "episode": episode, "sig": sig.to_json(),
                           "decision": decision, "why": why, "source": lesson.source if lesson else None})
        return decision, lesson, why

    def decide(self, episode: int, sig: FailSig, facts: dict, now: float):
        e = self.lessons.get(sig)
        if e is None:
            partial = any(0 < sum(a == b for a, b in zip(astuple(s), astuple(sig))) < 4 for s in self.lessons)
            return self._log(now, episode, sig, "call_j2", None, "partial_match" if partial else "first_seen")
        st = self.reuse.get((episode, sig))
        if st is not None:
            return self._log(now, episode, sig, "call_j2", e, "reuse_failed" if st == "failed" else "reuse_cap")
        f = falsified(e.falsify, facts)
        if f != "no":
            return self._log(now, episode, sig, "call_j2", e, "falsified" if f == "yes" else "falsify_unknown")
        self.reuse[(episode, sig)] = "pending"
        return self._log(now, episode, sig, "reuse", e, "not_falsified")

    def report(self, episode: int, sig: FailSig, success: bool, now: float) -> None:
        if self.reuse.get((episode, sig)) == "pending":
            self.reuse[(episode, sig)] = "succeeded" if success else "failed"
            self.audit.append({"t": round(now, 3), "event": "reuse_outcome", "episode": episode,
                               "sig": sig.to_json(), "success": bool(success)})
```

`harvest/runtime/core.py`:
- `__init__` 끝에: `from ..couple.recovery_cache import RecoveryCache` 후 `self.recovery = RecoveryCache()`와 `self.recovery_apply = lambda lesson: "m9_not_built"  # M9 recovery not built (canon §67 SCOPED)`.
- 새 메서드:

```python
    def _fail_event(self, now: float, mode: str, evidence: str) -> None:
        """T_fail stand-in (M9 not built): falsify first (canon §84 + supplement 1) before the Astra call."""
        from ..couple.recovery_cache import FailSig
        sig = FailSig(stage=self.skill.stage, target=_PHASE_TARGET.get(self.skill.phase, "o5"), mode=mode,
                      evidence=evidence)
        dec, lesson, why = self.recovery.decide(self.episode, sig, self._t1(), now)
        self.events.append({"t": round(now, 4), "event": "fail_path", "sig": sig.to_json(), "decision": dec,
                            "why": why})
        if dec == "reuse":
            self.events.append({"t": round(now, 4), "event": "recovery_reuse", "recovery": lesson.recovery,
                                "source": lesson.source, "applied": self.recovery_apply(lesson)})
            return
        self._event(now, mode)
```

- T_fail 대역 세 곳을 `_fail_event`로: `_on_verify` 알람 → `self._fail_event(now, "m7_critic_alarm", "v1h_critic")`; `_boundary` 하드 채널 → `self._fail_event(now, "m7_hard_t1", "t1_hard")`; `_execute`의 `object_lost`/`grasp_miss` → `self._fail_event(now, e["event"], "t1_skill")`. (J5 승격·CONTRADICT는 실패 판정이 아니므로 `_event` 그대로.)
- `harvest/runtime/ir_policy.py` 행 목록에 `("recovery", [r for r in getattr(rt, "recovery", None).audit if r.get("episode") in (None, rt.episode)] if getattr(rt, "recovery", None) else [])`.

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_recovery_cache.py tests/runtime -v` → PASS.
- [ ] **Step 5: 커밋** — `msg_task11.txt` 첫 줄 `couple: falsify-first recovery reuse cache, one reuse per episode and signature (Task 11)`.

---

### Task 12: 움직임 줄(§83)과 직렬화 판본 `ser-A-min-3`

**전제**: 착수 조건 0-4(E-MA1 끝남). 이 Task의 커밋 뒤에는 **기존 체크포인트 전부가 런타임에서 거부**된다(§77과 같은 규칙) — 새 판으로 재학습한 체크포인트가 준비될 때까지 폐루프는 mock 모델로만 돈다. 이 사실을 커밋 메시지와 handoff에 적는다.

**Files:**
- Create: `harvest/runtime/motion.py`
- Modify: `harvest/serialize.py`, `harvest/deccall_snap.py`, `harvest/train/stageb_data.py:379`, `harvest/runtime/models.py`(`build_live_request`), `harvest/runtime/core.py`(RuntimeConfig, `reset`, `act`, `_decision_ctx`, `_maybe_request_chunk`, `TickView` motion), `harvest/runtime/fused_model.py`(`check_prompt`), `harvest/train/stagea_train.py`(`serializer_of` 문구), `harvest/eval/closed.py`(작업자에서 bins 전달)
- Modify tests: `tests/test_serialize.py:18`, `tests/test_deccall_snap.py:15`, `tests/train/test_r7c12_last_step.py:26,79,86,89`, `tests/eval/test_common.py:103`
- Test: `tests/runtime/test_motion_line.py`

**Interfaces:**
- Produces: `serialize.SERIALIZER_VERSION = "ser-A-min-3"`, `serialize.MOTION_UNKNOWN`, `serialize.with_motion_last_step(state, motion, last_step) -> str`; `deccall_snap.motion_of(line) -> str`; `models.build_live_request(..., motion=MOTION_UNKNOWN)`; `runtime.motion.MOTION_VER = "se2e-motion@v1"`, `bin_line(arm_speed, grip_rate, bins) -> str`, `MotionTracker(bins, window_s=0.1, grip_src="sim_width_m", keep_s=1.0)` — `add(t, q7, grip)`, `line() -> str`; `RuntimeConfig.motion_bins: dict|None = None`, `RuntimeConfig.motion_window_s: float = 0.1`.

- [ ] **Step 1: 실패하는 시험** — `tests/runtime/test_motion_line.py`:

```python
import numpy as np
import pytest

from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockFusedModel
from harvest.runtime.motion import MOTION_VER, MotionTracker, bin_line
from harvest.serialize import MOTION_UNKNOWN, SERIALIZER_VERSION, with_motion_last_step

from .fakeworld import FakeWorld

BINS = {"version": "se2e-motion@v1", "arm_speed": [0.218, 0.607], "grip_rate": 0.176}


def test_serializer_version_and_line_order():
    assert SERIALIZER_VERSION == "ser-A-min-3"
    s = with_motion_last_step("t_state: 1\nrobot: gripper=open", "motion: arm=slow gripper=still", "OK")
    assert s.split("\n")[-2:] == ["motion: arm=slow gripper=still", "last_step: OK"]
    with pytest.raises(ValueError, match="motion"):
        with_motion_last_step("x", "motion: arm=quick gripper=still", "OK")


def test_tracker_matches_the_training_rule():
    T = pytest.importorskip("harvest.train.se2e_temporal")
    assert T.MOTION_VER == MOTION_VER and T.MOTION_UNKNOWN == MOTION_UNKNOWN
    for qd, gr in (([0.1] * 7, 0.0), ([0.2, 0, 0, 0, 0, 0, 0], -0.05), ([0.5, 0.4, 0, 0, 0, 0, 0], 0.05)):
        row = {"motion_src": {"qd_bwd": qd, "grip_rate_bwd": gr}}
        m = MotionTracker(BINS, window_s=0.1)
        m.add(0.0, np.zeros(7), 0.05)
        m.add(0.1, np.asarray(qd) * 0.1, 0.05 + gr * 0.1)
        assert m.line() == T.motion_line(row, BINS)


def test_tracker_start_and_no_bins():
    m = MotionTracker(BINS, window_s=0.1)
    m.add(0.0, np.zeros(7), 0.1)
    assert m.line() == "motion: arm=still gripper=still"  # like training row k = 0 (zero backward difference)
    assert MotionTracker(None).line() == MOTION_UNKNOWN
    assert bin_line(0.7, -0.2, BINS) == "motion: arm=fast gripper=closing"
    with pytest.raises(ValueError, match="version"):
        MotionTracker({"version": "other", "arm_speed": [0, 1], "grip_rate": 1})


def test_fused_request_state_and_context_carry_the_motion_line():
    rt = OursRuntime(RuntimeConfig(backend="fused", clock="simlat", motion_bins=BINS), MockFusedModel(latency_s=0.3))
    rt.reset()
    w = FakeWorld()
    for _ in range(50):
        a, _ = rt.act(w.obs())
        w.step(a)
    ctx = rt._decision_ctx(rt.t_last, *rt._m1_last[:4], w.obs())
    lines = ctx["req"]["state"].split("\n")
    assert lines[-1].startswith("last_step: ") and lines[-2].startswith("motion: arm=")
    assert ctx["ctx_text"].split("\n")[-1] == lines[-2]
    rt.close()
```

`_decision_ctx(now, raw, present, pred, support, obs)` 인자 순서는 core.py 그대로다(`_m1_last = (raw, present, pred, support)`).

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/runtime/test_motion_line.py -v` → FAIL.

- [ ] **Step 3: `harvest/serialize.py`**

```python
SERIALIZER_VERSION = "ser-A-min-3"
# -2 (canon §77, R7 cycle 12 D3): every DecCall state ends with the M4 (b) category line of the last finished
# decision step, `last_step: <category>` ("none" = no step checked yet / no check in the data / withheld).
# -3 (canon §83, plan 2026-09-26 Task 12): the motion line `motion: arm=<..> gripper=<..>` (se2e-motion@v1 bins,
# causal backward differences; "unknown" where no history is recorded) sits right before the last_step line.
LAST_STEP_VALUES = ("none", "OK", "LAG", "DEVIATE", "CONTRADICT")
MOTION_UNKNOWN = "motion: arm=unknown gripper=unknown"
_MOTION_RE = re.compile(r"^motion: arm=(still|slow|fast|unknown) gripper=(closing|still|opening|unknown)$")


def with_motion_last_step(state: str, motion: str, last_step: str) -> str:
    if not _MOTION_RE.match(motion):
        raise ValueError(f"motion line {motion!r}: 'motion: arm=<still|slow|fast|unknown> "
                         f"gripper=<closing|still|opening|unknown>'")
    return with_last_step(f"{state}\n{motion}", last_step)
```

(`with_last_step`은 그대로 둔다; `import re`는 이미 있음.)

- [ ] **Step 4: `harvest/deccall_snap.py`** — import를 `from .serialize import MOTION_UNKNOWN, with_motion_last_step`로 바꾸고 함수 추가, `build_snapshot_request`의 마지막 줄 교체, 독스트링의 `ser-A-min-2`를 `ser-A-min-3`으로:

```python
def motion_of(line: dict) -> str:
    """The motion line of a snapshot line (canon §83): the runtime / datagen value, else the trained 'unknown'."""
    return line.get("motion") or MOTION_UNKNOWN
```

```python
    return build_request(with_motion_last_step(st, motion_of(line), last_step_of(line)), qs), oracle, shown
```

- [ ] **Step 5: `harvest/train/stageb_data.py:379`** — 단계 B 문맥도 움직임 줄로 끝나게(E-TC와 같은 모양; 항목은 `build_snapshot_request`가 줄을 붙이므로 `prompt_state` 자체는 바꾸지 않는다):

```python
        from ..deccall_snap import motion_of
        ctx = {"text": canonicalize(prompt_state(line, state) + "\n" + motion_of(line)),
               "images": images_of(line, arm, wrist, image_root)}
```

- [ ] **Step 6: `harvest/runtime/motion.py`**

```python
"""Runtime motion line (canon §83, se2e-motion@v1): `motion: arm=<still|slow|fast> gripper=<closing|still|opening>`
from CAUSAL backward differences of the robot state over the checkpoint's data step (window_s = 1 / its hz: S-E2E
10 Hz -> 0.1 s), binned exactly like harvest.train.se2e_temporal.motion_line with the checkpoint's train-split bins
(prompt_config["motion"]). No older sample yet -> zero difference (= training row k = 0: still / still). No bins
(a checkpoint trained without the line, mock models) -> the trained unknown value."""
from __future__ import annotations

from collections import deque

import numpy as np

from ..serialize import MOTION_UNKNOWN
from ..train.stageb_data import grip_rate01

MOTION_VER = "se2e-motion@v1"


def bin_line(arm_speed: float, grip_rate: float, bins: dict) -> str:
    lo, hi = bins["arm_speed"]
    arm = "still" if arm_speed < lo else "slow" if arm_speed < hi else "fast"
    t = bins["grip_rate"]
    grip = "opening" if grip_rate > t else "closing" if grip_rate < -t else "still"
    return f"motion: arm={arm} gripper={grip}"


class MotionTracker:
    def __init__(self, bins: dict | None, window_s: float = 0.1, grip_src: str = "sim_width_m", keep_s: float = 1.0):
        if bins is not None and bins.get("version") != MOTION_VER:
            raise ValueError(f"motion bins version {bins.get('version')!r} != {MOTION_VER}")
        self.bins, self.window, self.src, self.keep = bins, float(window_s), grip_src, float(keep_s)
        self.h = deque()

    def add(self, t: float, q7, grip: float) -> None:
        self.h.append((float(t), np.asarray(q7, float)[:7].copy(), float(grip)))
        while self.h and self.h[0][0] < t - self.keep - 1e-9:
            self.h.popleft()

    def line(self) -> str:
        if self.bins is None or not self.h:
            return MOTION_UNKNOWN
        t1, q1, g1 = self.h[-1]
        old = [x for x in self.h if x[0] <= t1 - self.window + 1e-9]
        if not old:
            return bin_line(0.0, 0.0, self.bins)
        t0, q0, g0 = old[-1]
        dt = t1 - t0
        arm = float(np.linalg.norm((q1 - q0) / dt))
        grip = float(grip_rate01((g1 - g0) / dt, self.src))
        return bin_line(arm, grip, self.bins)
```

- [ ] **Step 7: `harvest/runtime/models.py`** — `build_live_request` 서명에 `motion: str | None = None`을 더하고 몸체에서 `line`에 넣는다:

```python
    from ..serialize import LAST_STEP_VALUES, MOTION_UNKNOWN
    ...
    line = {"ds_id": f"ds{ds}", "phase": phase, "text_state": text_s0, "last_step": last_step,
            "motion": motion or MOTION_UNKNOWN,
            "state": {"present": list(present), "obs": {"raw": raw}}, "oracle": defaultdict(lambda: None)}
```

- [ ] **Step 8: `harvest/runtime/core.py`**
  - `RuntimeConfig`에: `motion_bins: dict | None = None  # checkpoint prompt_config["motion"] (canon §83); None = unknown line` 와 `motion_window_s: float = 0.1  # 1 / the checkpoint data rate`.
  - `reset()`에: `from .motion import MotionTracker` 후 `self.motion = MotionTracker(self.cfg.motion_bins, self.cfg.motion_window_s)`.
  - `act()`의 `self._jp_last, self._t_jp = jp.copy(), now` 다음 줄: `self.motion.add(now, jp[:7], jp[7])`.
  - `_decision_ctx`: `mline = self.motion.line()`를 두고 두 `build_live_request(...)` 호출에 `motion=mline`, `ctx["ctx_text"] = canonicalize(image_only_state(s0) + "\n" + mline)`, `ctx["motion"] = mline`.
  - `_maybe_request_chunk`의 `ctx_text`를 `canonicalize(image_only_state(self._s0(now, l1[2], l1[1], l1[3])) + "\n" + self.motion.line())`로.
  - Task 10의 `TickView(... motion=None)`를 `motion=self.motion.line()`로.

- [ ] **Step 9: `harvest/runtime/fused_model.py` `check_prompt`** — 움직임 줄로 학습한 체크포인트(`prompt_config_t`: `files_sha`에 `TEMPORAL_FILES` 포함)를 받아들이고, 채택 안 된 video2 배치는 거부:

```python
    from ..train.stageb_train import PROMPT_FILES_B, TEMPORAL_FILES
    files = PROMPT_FILES + PROMPT_FILES_B + (TEMPORAL_FILES if pc.get("motion") else ())
    now = {"camera_ok": cam in (pc.get("camera") or []), "state_ok": pc.get("state") == "IMG",
           "layout_ok": pc.get("layout", D.CAMERA_LAYOUT) == D.CAMERA_LAYOUT,
           "system_ok": pc.get("system_sha") == hashlib.sha256(SYSTEM.encode()).hexdigest()[:12],
           "serializer_ok": ser == SERIALIZER_VERSION,
           "files_ok": pc.get("files_sha") == file_sha(files), "sha": pc.get("sha"), "serializer": ser}
```

(기존 `from ..train.stageb_train import PROMPT_FILES_B` 줄을 위 import로 바꾼다.)

- [ ] **Step 10: `harvest/train/stagea_train.py` `serializer_of`** — 파일 해시가 다를 때 문구를 판본에 맞게:

```python
    return SERIALIZER_VERSION if same else f"older than {SERIALIZER_VERSION} (prompt-building files changed)"
```

- [ ] **Step 11: `harvest/eval/closed.py` 작업자** — `run_worker`에서 `cfg = RuntimeConfig(...)` 앞에:

```python
        mb, mw = None, 0.1
        if spec["selector"] == "stageb" and spec.get("model_path"):
            sb = json.load(open(os.path.join(spec["model_path"], "stageb.json"), encoding="utf-8"))
            mb, mw = (sb.get("prompt_config") or {}).get("motion"), 1.0 / float(sb.get("hz", 30))
```

그리고 `RuntimeConfig(...)` 인자에 `motion_bins=mb, motion_window_s=mw`.

- [ ] **Step 12: 기존 시험의 판본 기대값 갱신(이 줄들만)**
  - `tests/test_serialize.py:18` → `assert SERIALIZER_VERSION == "ser-A-min-3"  # -3: + motion line (canon §83)`
  - `tests/test_deccall_snap.py:15` → `assert req["state"] == "t_state: f1\nrobot: x\nmotion: arm=unknown gripper=unknown\nlast_step: none"`
  - `tests/train/test_r7c12_last_step.py:26`, `:79`, `:89` → `"ser-A-min-3"`; `:86` → `pytest.raises(ValueError, match="ser-A-min-3")`
  - `tests/eval/test_common.py:103` → `match="ser-A-min-3"`

- [ ] **Step 13: 통과 확인** — `python -m pytest tests/runtime/test_motion_line.py -v` → PASS; `python -m pytest -q` → 실패 0. 위 목록 밖의 실패가 나오면 **멈추고** `superpowers:systematic-debugging`으로 원인을 찾는다(기대값을 맞춰 고치지 않는다).

- [ ] **Step 14: `question_id@vN` 재생성(로컬, 유료 0)** — Write 도구로 `D:\tools\scratch_qdd\plan_coupling\qids.py`:

```python
import json

from harvest.runtime.run_r5 import question_ids

print(json.dumps({"HW/IMG": question_ids("HW", "IMG"), "H/S1-1mm": question_ids("H", "S1-1mm")}, indent=1))
```

Run(저장소 루트에서): `python D:/tools/scratch_qdd/plan_coupling/qids.py` → 새 해시가 `docs/stage3/qid_registry.json`에 새 vN으로 등록된다(판본 문자열이 해시 입력). 출력의 id가 이전과 모두 다른지 확인하고 레지스트리를 커밋에 넣는다.

- [ ] **Step 15: 정본 기록** — `docs/design/00-interfaces.md` §83 "런타임 적용" 줄 끝에 한 줄을 더한다(시각은 `date -u`):

```markdown
- (구현 기록, <UTC 시각>, 계획 `docs/superpowers/plans/2026-09-26-astra-vla-coupling.md` Task 12) 직렬화 판본 **`ser-A-min-3`**: 결정 상태 = … `motion: …` 줄 → `last_step: …` 줄(움직임 줄은 끝에서 둘째), 단계 B 문맥은 상태 + 움직임 줄로 끝남; 기록 없는 곳은 `motion: arm=unknown gripper=unknown`. 런타임 = `runtime/motion.py`(체크포인트 `prompt_config["motion"]` 구간·1/hz 창, 인과 후방 차분). `question_id@vN` 새 판(레지스트리 커밋), 기존 체크포인트는 모두 거부(§77 규칙) — 보정 파일(E1 `harvest.eval.calib`)과 카나리 기준(`harvest.eval.canary`, qid가 바뀌어 새 기준일)은 ser-A-min-3 체크포인트 학습 뒤 파드에서 다시 만든다. R2 데이터 생성기가 `line["motion"]`을 쓰기 전까지 R2 학습 항목의 줄은 unknown.
```

- [ ] **Step 16: 커밋** — `msg_task12.txt`:

```
serializer ser-A-min-3: motion line before last_step, runtime MotionTracker (canon §83) (Task 12)

Every checkpoint trained before this commit is refused by check_prompt (canon §77 rule);
question_id@vN regenerated; calibration files and canary baselines are rebuilt after the
ser-A-min-3 retrain.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Cak1EG98gYtthtAuz7r8W8
```

`git add` 대상: 위 Files 전부 + `docs/stage3/qid_registry.json` + `docs/design/00-interfaces.md` + `tests/runtime/test_motion_line.py`.

- [ ] **Step 17: 재생성 절차(파드, 새 체크포인트가 생긴 뒤 — 이 계획에서는 실행하지 않음, handoff에 적는다)**
  1. `source /data/harvest/env.sh`
  2. 카나리: `python -m harvest.eval.canary --model <ser-A-min-3 체크포인트> --set dev_v1 --repeats 2 --gpu 3` → qid가 바뀌었으므로 새 기준일이 자동으로 시작된다.
  3. 보정: `python -m harvest.eval.calib --model <체크포인트> --out /data/harvest/out/calib_serA3 --fit-data <DEV 풀> --fit-split dev --heldout <DEV 풀> --heldout-split dev` → `calibration.json`(새 qid에 묶임).
  4. 폐루프 스모크 `python -m harvest.eval.closed --model <체크포인트> --backend fused --out /data/harvest/out/serA3_smoke --seeds 0 --astra none` 한 판으로 `check_prompt` 통과와 결정 상태 끝 두 줄을 사이드카 요청 블롭에서 확인한다.

---

### Task 13: 로컬 VLM 어댑터 (E-Astra-necessity U-Q*)

**Files:**
- Create: `harvest/couple/local_vlm.py`
- Test: `tests/couple/test_local_vlm.py`

**Interfaces:**
- Consumes: `harvest.clients.astra.AstraRecord`, `_image_hashes`.
- Produces: `to_chat(inp) -> list`; `LocalVLMAstra(base_url, model, timeout_s=60.0, transport=None)` — `.model = "local:<model>"`, `.call(inp, effort, max_output_tokens, meta) -> AstraRecord`(usage는 `input_tokens`/`output_tokens`로 옮김, effort는 기록만), `.close()`.

- [ ] **Step 1: 실패하는 시험** — `tests/couple/test_local_vlm.py`:

```python
import json

import httpx

from harvest.couple.local_vlm import LocalVLMAstra, to_chat
from harvest.couple.params import CoupleParams
from harvest.couple.prompt import build_input

INP = build_input({"request_no": 1}, {"cam_head": b"\xff\xd8x"}, CoupleParams(), "task")


def test_responses_input_becomes_chat_messages():
    msgs = to_chat(INP)
    kinds = [c["type"] for c in msgs[0]["content"]]
    assert kinds == ["text", "text", "image_url"]
    assert msgs[0]["content"][2]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_call_maps_output_and_usage_without_guided_decoding():
    seen = {}

    def handler(req):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"model": "qwen3-vl-8b", "choices": [{"message": {"content": '{"a": 1}'}}],
                                         "usage": {"prompt_tokens": 1500, "completion_tokens": 300}})
    c = LocalVLMAstra("http://vllm:8000", "qwen3-vl-8b", transport=httpx.MockTransport(handler))
    rec = c.call(INP, "low", 800, {"couple_no": 1})
    assert rec.output_text == '{"a": 1}' and rec.usage == {"input_tokens": 1500, "output_tokens": 300}
    assert rec.error is None and rec.meta["effort_ignored"] is True and c.model == "local:qwen3-vl-8b"
    assert seen["max_tokens"] == 800 and seen["temperature"] == 0.0 and "guided_json" not in seen


def test_http_error_and_timeout_are_recorded():
    c = LocalVLMAstra("http://vllm:8000", "m", transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    assert c.call(INP, "low", 10, {}).error == "http_503"

    def boom(req):
        raise httpx.ReadTimeout("slow", request=req)
    t = LocalVLMAstra("http://vllm:8000", "m", transport=httpx.MockTransport(boom))
    assert t.call(INP, "low", 10, {}).error == "timeout"
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/couple/test_local_vlm.py -v` → FAIL.

- [ ] **Step 3: 구현** — `harvest/couple/local_vlm.py`:

```python
"""A local VLM in the Astra stream slot (E-Astra-necessity U-Q8 / U-Q4 / U-Q32, canon §82): OpenAI-compatible chat
on vLLM, the same call(inp, effort, max_output_tokens, meta) -> AstraRecord as clients.astra.AstraClient (effort is
recorded, not used). Same prompt bytes and images as Astra; no guided / JSON-schema decoding (canon §82 fairness:
Astra has none); temperature 0, seed 0."""
from __future__ import annotations

import time

import httpx

from ..clients.astra import AstraRecord, _image_hashes


def to_chat(inp: list) -> list:
    out = []
    for m in inp:
        parts = []
        for c in m["content"]:
            if c.get("type") == "input_text":
                parts.append({"type": "text", "text": c["text"]})
            elif c.get("type") == "input_image":
                parts.append({"type": "image_url", "image_url": {"url": c["image_url"]}})
        out.append({"role": m["role"], "content": parts})
    return out


class LocalVLMAstra:
    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0, transport=None):
        self.base, self.served = base_url.rstrip("/"), model
        self.model = f"local:{model}"
        self._c = httpx.Client(timeout=timeout_s, transport=transport)

    def call(self, inp: list, effort: str, max_output_tokens: int, meta: dict) -> AstraRecord:
        rec = AstraRecord(effort=effort, meta={**meta, "effort_ignored": True}, image_sha256s=_image_hashes(inp))
        body = {"model": self.served, "messages": to_chat(inp), "max_tokens": int(max_output_tokens),
                "temperature": 0.0, "seed": 0}
        rec.t_send = time.monotonic()
        try:
            r = self._c.post(f"{self.base}/v1/chat/completions", json=body)
            rec.http_status = r.status_code
            if r.status_code != 200:
                rec.error = f"http_{r.status_code}"
            else:
                d = r.json()
                rec.output_text = d["choices"][0]["message"]["content"] or ""
                u = d.get("usage") or {}
                rec.usage = {"input_tokens": int(u.get("prompt_tokens", 0)),
                             "output_tokens": int(u.get("completion_tokens", 0))}
                rec.model_field = d.get("model")
        except httpx.HTTPError as e:
            rec.error = "timeout" if isinstance(e, httpx.TimeoutException) else type(e).__name__
        rec.t_done = time.monotonic()
        rec.t_first_token = rec.t_done
        return rec

    def close(self) -> None:
        self._c.close()
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/couple/test_local_vlm.py -v` → PASS.
- [ ] **Step 5: 커밋** — `msg_task13.txt` 첫 줄 `couple: local VLM adapter for the stream slot (E-Astra-necessity) (Task 13)`.

---

### Task 14: 폐루프 평가 배선 — 결합 팔, 유료 실행 가드, 집계, 예산 추정

**Files:**
- Create: `harvest/eval/couple.py`
- Modify: `harvest/eval/closed.py`(`_args`, `run`, `run_worker`, `aggregate`, `_md`)
- Test: `tests/eval/test_couple_eval.py`

**Interfaces:**
- Consumes: `CoupleParams`, `PriceTable`, `LocalVLMAstra`, `ScriptedCoupleAstra`, `answer`, `analysis.stats.cluster_mean_ci`.
- Produces: `ARMS = ("off","serial","serial_pause")`, `parse_arms(s) -> list`, `arm_config(arm, phase_pause_s=3.0, min_interval_s=0.0) -> dict`(RuntimeConfig 덮어쓰기), `couple_label(label, arm, arms) -> str`, `check_paid(a)`, `stream_client(spec) -> (client, mode)`, `is_budget_excluded(trial) -> bool`, `couple_cell(summaries) -> dict|None`, `couple_diff(trials, n_boot) -> dict`, `estimate(prices, episodes, episode_s, latency_s, in_tokens, out_tokens, phase_pause_s=None, dense_frac=0.3) -> dict`, CLI `python -m harvest.eval.couple estimate ...`. `closed.aggregate` 결과에 `couple_diff`, `couple_budget_excluded`, 칸별 `couple`.

- [ ] **Step 1: 실패하는 시험** — `tests/eval/test_couple_eval.py`:

```python
import json
from types import SimpleNamespace

import pytest

from harvest.couple.cost import PriceTable
from harvest.eval import couple as CP
from harvest.eval.closed import aggregate

TEST = PriceTable("test", "2026-09-26", 2.0, 0.5, 8.0, 1400.0, "unit test")


def test_arms_labels_and_configs():
    assert CP.parse_arms("off,serial") == ["off", "serial"]
    with pytest.raises(SystemExit, match="couple"):
        CP.parse_arms("serial,stagger")
    assert CP.arm_config("off") == {"couple": "off"}
    assert CP.arm_config("serial_pause", 3.0) == {"couple": "serial", "couple_params": {"phase_pause_s": 3.0}}
    assert CP.arm_config("serial", min_interval_s=4.2) == {"couple": "serial", "couple_params": {"min_interval_s": 4.2}}
    assert CP.couple_label("C5", "serial", ["off"]) == "C5" and CP.couple_label("C5", "serial", ["off", "serial"]) == "C5|cp-serial"


def test_paid_runs_need_prices_budget_ledger_and_approval():
    base = dict(couple_prices="p.json", couple_budget_krw=25000.0, couple_ledger="/data/x.jsonl", approval="prereg_couple.md §0 self-check")
    CP.check_paid(SimpleNamespace(**base))
    for k, v in (("approval", ""), ("couple_prices", ""), ("couple_budget_krw", 0.0), ("couple_ledger", "")):
        with pytest.raises(SystemExit):
            CP.check_paid(SimpleNamespace(**{**base, k: v}))


def test_mock_stream_client_answers_in_both_modes():
    from harvest.couple.params import CoupleParams
    from harvest.couple.prompt import build_input
    from harvest.couple.schema import parse_answer
    c, mode = CP.stream_client({"astra": "mock", "couple_upper": "astra"})
    for m in ("F0", "F1"):
        rec = c.call(build_input({"request_no": 1, "mode": m}, {}, CoupleParams(request_mode=m), "t"), "low", 10, {})
        assert parse_answer(rec.output_text, m, (), 1, 0.0, 1.0).command == "continue"
    assert mode == "mock"


def test_estimate_serial_and_pause():
    e = CP.estimate(TEST, episodes=40, episode_s=60.0, latency_s=4.0, in_tokens=3500, out_tokens=1000)
    per = TEST.krw({"input_tokens": 3500, "output_tokens": 1000})
    assert e["calls"] == pytest.approx(600.0) and e["krw"] == pytest.approx(600 * per)
    p = CP.estimate(TEST, 40, 60.0, 4.0, 3500, 1000, phase_pause_s=8.0, dense_frac=0.3)
    assert p["calls"] == pytest.approx(40 * (0.3 * 60 / 4 + 0.7 * 60 / 8))


def _trial(cond, seed, ok, excluded=False, cost=10.0):
    c = {"calls_sent": 12, "latency_s": {"p50": 4.0, "p95": 6.0}, "answer_age_s": {"p50": 4.1}, "cost_krw": cost,
         "timeouts": 0, "schema_errors": 0, "gates": {"ok": 10}, "layer": {"apply": 1}, "irrev": {},
         "events": {}, "max_outstanding": 1, "budget_excluded": excluded}
    return {"variant": "standard", "condition": cond, "seed": seed, "epoch": 0, "success": ok, "sim_time": 30.0,
            "termination": "success" if ok else None, "summary": {"couple": c if "serial" in cond else None}}


def test_aggregate_excludes_budget_stopped_episodes_and_pairs_the_arms():
    trials = [_trial("C5|cp-off", s, s % 2 == 0) for s in range(6)]
    trials += [_trial("C5|cp-serial", s, True) for s in range(5)] + [_trial("C5|cp-serial", 5, False, excluded=True)]
    res = aggregate(trials, n_boot=200)
    assert res["couple_budget_excluded"] == 1
    d = res["couple_diff"]["C5|cp-serial - C5|cp-off/standard"]
    assert d["n_pairs"] == 5 and d["mean"] == pytest.approx(0.4)
    cell = res["cells"]["C5|cp-serial/standard"]["couple"]
    assert cell["episodes"] == 5 and cell["cost_krw_total"] == pytest.approx(50.0)


def test_estimate_cli(tmp_path, capsys):
    f = tmp_path / "prices.json"
    f.write_text(json.dumps({"model": "test", "date": "2026-09-26", "usd_per_mtok_input": 2.0,
                             "usd_per_mtok_cached_input": 0.5, "usd_per_mtok_output": 8.0, "krw_per_usd": 1400.0,
                             "source": "unit test"}))
    CP.main(["estimate", "--prices", str(f), "--episodes", "40", "--episode-s", "60", "--latency-s", "4",
             "--in-tokens", "3500", "--out-tokens", "1000"])
    out = json.loads(capsys.readouterr().out)
    assert out["calls"] == pytest.approx(600.0) and out["price_date"] == "2026-09-26"
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/eval/test_couple_eval.py -v` → FAIL.

- [ ] **Step 3: `harvest/eval/couple.py`**

```python
"""E-Couple / E-Astra-necessity (stream slot) evaluation pieces for harvest.eval.closed (spec §9, §15, §16; canon §82,
§84 supplement 2). Arms: off (no Astra at all when compared with a coupling arm = VLA alone), serial (one Astra
request in flight + two-layer M4), serial_pause (+ the optional phase pause, cost fallback). Paid runs need the run
day's price table, the pre-registered budget, a ledger path and a self-check reference — the prereg's self-check section (user-log 87; replaces user approval). Episodes
cut by the 80 % budget stop are excluded from the judgment and counted (plan ruling 10).

  python -m harvest.eval.couple estimate --prices P.json --episodes 40 --episode-s 60 --latency-s 4 \
      --in-tokens 3500 --out-tokens 1000 [--phase-pause 8 --dense-frac 0.3]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

ARMS = ("off", "serial", "serial_pause")


def parse_arms(s: str) -> list:
    arms = [x for x in (s or "off").split(",") if x]
    if not arms or len(set(arms)) != len(arms) or any(x not in ARMS for x in arms):
        raise SystemExit(f"--couple {s!r}: distinct values from {ARMS}")
    return arms


def arm_config(arm: str, phase_pause_s: float = 3.0, min_interval_s: float = 0.0) -> dict:
    if arm == "off":
        return {"couple": "off"}
    cp = {"min_interval_s": float(min_interval_s)} if min_interval_s else {}
    if arm == "serial_pause":
        cp["phase_pause_s"] = float(phase_pause_s)
    return {"couple": "serial", "couple_params": cp}


def couple_label(label: str, arm: str, arms: list) -> str:
    return label if list(arms) == ["off"] else f"{label}|cp-{arm}"


def check_paid(a) -> None:
    miss = [k for k, ok in (("--couple-prices", bool(a.couple_prices)), ("--couple-budget-krw", a.couple_budget_krw > 0),
                            ("--couple-ledger", bool(a.couple_ledger)), ("--approval", bool(a.approval))) if not ok]
    if miss:
        raise SystemExit(f"paid Astra coupling run refused: {miss} missing (user-log 87: self-check reference, the run day's "
                         f"prices, the pre-registered budget and a ledger)")


def stream_client(spec: dict):
    if spec.get("couple_upper") == "local":
        from ..couple.local_vlm import LocalVLMAstra
        return LocalVLMAstra(spec["couple_local_url"], spec["couple_local_model"]), "local"
    if spec["astra"] == "api":
        tok = "/data/.openai_token"
        if not os.path.exists(tok):
            raise SystemExit("--astra api but no /data/.openai_token")
        from ..clients.astra import AstraClient
        from ..runtime.astra_hb import MODEL
        return AstraClient(open(tok).read().strip(), MODEL, timeout_s=30.0), "api"
    from ..couple.mock import ScriptedCoupleAstra, answer
    # mock stream (pipeline smoke, no paid call): valid in both request modes (the request carries its mode)
    return ScriptedCoupleAstra(lambda req: answer("continue", views=(), diff="keep" if req.get("mode") == "F1" else None),
                               latency_s=3.0), "mock"


def is_budget_excluded(t: dict) -> bool:
    return bool((((t.get("summary") or {}).get("couple")) or {}).get("budget_excluded"))


def couple_cell(summaries: list):
    cs = [s.get("couple") for s in summaries if s.get("couple")]
    if not cs:
        return None

    def med(xs):
        xs = [x for x in xs if x is not None]
        return round(float(np.median(xs)), 4) if xs else None

    def tot(key):
        c = Counter()
        for x in cs:
            c.update(x.get(key) or {})
        return dict(c)
    return {"episodes": len(cs), "calls_per_episode": med([c["calls_sent"] for c in cs]),
            "latency_p50_s": med([c["latency_s"]["p50"] for c in cs]),
            "latency_p95_s": med([c["latency_s"]["p95"] for c in cs]),
            "answer_age_p50_s": med([c["answer_age_s"]["p50"] for c in cs]),
            "cost_krw_total": round(sum(c["cost_krw"] for c in cs), 3),
            "cost_krw_per_episode": med([c["cost_krw"] for c in cs]),
            "timeouts": sum(c["timeouts"] for c in cs), "schema_errors": sum(c["schema_errors"] for c in cs),
            "gates": tot("gates"), "layer": tot("layer"), "irrev": tot("irrev"), "events": tot("events"),
            "max_outstanding": max(c.get("max_outstanding", 1) for c in cs)}


def couple_diff(trials: list, n_boot: int) -> dict:
    """Paired success differences (same variant, seed, epoch) of each coupling arm against the off arm of the same
    base label; seed-cluster bootstrap (EVAL §4.2)."""
    from ..analysis.stats import cluster_mean_ci
    succ = {(t["condition"], t["variant"], t["seed"], t["epoch"]): int(bool(t["success"])) for t in trials}
    out = {}
    for c in sorted({t["condition"] for t in trials}):
        if "|cp-" not in c or c.endswith("|cp-off"):
            continue
        base = c.rsplit("|cp-", 1)[0] + "|cp-off"
        for v in sorted({t["variant"] for t in trials}):
            by = defaultdict(list)
            for (cc, vv, s, e), ok in succ.items():
                if cc == c and vv == v and (base, v, s, e) in succ:
                    by[s].append(ok - succ[(base, v, s, e)])
            if by:
                vals = [x for xs in by.values() for x in xs]
                lo, hi = cluster_mean_ci(by, n=n_boot, seed=0)
                out[f"{c} - {base}/{v}"] = {"mean": round(float(np.mean(vals)), 4), "ci": [round(lo, 4), round(hi, 4)],
                                            "n_pairs": len(vals), "n_seeds": len(by)}
    return out


def estimate(prices, episodes: int, episode_s: float, latency_s: float, in_tokens: int, out_tokens: int,
             phase_pause_s: float | None = None, dense_frac: float = 0.3) -> dict:
    if phase_pause_s is None:
        per_ep = episode_s / latency_s
    else:
        per_ep = dense_frac * episode_s / latency_s + (1 - dense_frac) * episode_s / max(latency_s, phase_pause_s)
    per_call = prices.krw({"input_tokens": in_tokens, "output_tokens": out_tokens})
    calls = episodes * per_ep
    return {"calls": round(calls, 3), "krw_per_call": round(per_call, 3), "krw": round(calls * per_call, 1),
            "price_date": prices.date, "price_model": prices.model,
            "assumptions": {"episodes": episodes, "episode_s": episode_s, "latency_s": latency_s,
                            "in_tokens": in_tokens, "out_tokens": out_tokens, "phase_pause_s": phase_pause_s,
                            "dense_frac": dense_frac}}


def main(argv=None):
    from ..couple.cost import PriceTable
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("estimate")
    e.add_argument("--prices", required=True)
    e.add_argument("--episodes", type=int, required=True)
    e.add_argument("--episode-s", type=float, required=True)
    e.add_argument("--latency-s", type=float, required=True)
    e.add_argument("--in-tokens", type=int, required=True)
    e.add_argument("--out-tokens", type=int, required=True)
    e.add_argument("--phase-pause", type=float, default=None)
    e.add_argument("--dense-frac", type=float, default=0.3)
    a = ap.parse_args(argv)
    r = estimate(PriceTable.load(a.prices), a.episodes, a.episode_s, a.latency_s, a.in_tokens, a.out_tokens,
                 a.phase_pause, a.dense_frac)
    print(json.dumps(r, indent=1))
    return r


if __name__ == "__main__":
    main(sys.argv[1:])
```

- [ ] **Step 4: `harvest/eval/closed.py` 수정**

(a) `_args`에:

```python
    ap.add_argument("--couple", default="off", help="coupling arms: comma list of off | serial | serial_pause "
                                                     "(spec 2026-09-26 §16, E-Couple)")
    ap.add_argument("--couple-phase-pause", type=float, default=3.0)
    ap.add_argument("--couple-upper", default="astra", choices=["astra", "local"],
                    help="stream model: Astra (--astra api|mock) or a local VLM (E-Astra-necessity U-Q*)")
    ap.add_argument("--couple-local-url", default="")
    ap.add_argument("--couple-local-model", default="")
    ap.add_argument("--couple-min-interval", type=float, default=0.0,
                    help="pace a local model to Astra's measured latency p50 (E-Astra-necessity)")
    ap.add_argument("--couple-prices", default="", help="the run day's price table JSON (paid runs)")
    ap.add_argument("--couple-budget-krw", type=float, default=0.0, help="the pre-registered experiment cap")
    ap.add_argument("--couple-ledger", default="", help="experiment cost ledger JSONL under /data")
    ap.add_argument("--approval", default="", help="self-check reference for paid calls: prereg self-check section (user-log 87), e.g. 'prereg_couple.md §0'")
```

(b) `run(a)`에서 `conds = ...` 다음:

```python
    from . import couple as CP
    arms = CP.parse_arms(a.couple)
    if any(x != "off" for x in arms) and a.astra == "api" and a.couple_upper == "astra":
        CP.check_paid(a)
```

`timeout` 식의 `len(conds)`를 `len(conds) * len(arms)`로. `spec` 딕셔너리에:

```python
                    "couple": arms, "couple_phase_pause": a.couple_phase_pause, "couple_upper": a.couple_upper,
                    "couple_local_url": a.couple_local_url, "couple_local_model": a.couple_local_model,
                    "couple_min_interval": a.couple_min_interval, "couple_prices": a.couple_prices,
                    "couple_budget_krw": a.couple_budget_krw,
                    "couple_ledger": os.path.abspath(a.couple_ledger) if a.couple_ledger else "",
                    "approval": a.approval,
```

`meta` 딕셔너리에 `"couple": {"arms": arms, "upper": a.couple_upper, "budget_krw": a.couple_budget_krw, "prices": a.couple_prices, "ledger": a.couple_ledger, "approval": a.approval, "phase_pause_s": a.couple_phase_pause, "min_interval_s": a.couple_min_interval}`.

(c) `run_worker`:
- 임베디먼트: `from ..sim.scene import KNOWN_CAMERAS`; `arms = spec.get("couple", ["off"])`; `emb = AIWorkerEmbodiment(variant=spec["variant"], cameras=KNOWN_CAMERAS if any(x != "off" for x in arms) else ("cam_head", "cam_wrist_right"))`.
- `for lab in run_labels(...)` 몸체 전체를 `for arm in arms:` 안으로 넣고(모델 생성부터 `rt.close()`까지), 첫 줄에서 라벨을 `label = CP.couple_label(lab[2], arm, arms)`로 정한다(`from . import couple as CP`는 함수 머리에서).
- Astra 선택 블록 뒤에:

```python
            if arm != "off":
                astra, amode = CP.stream_client(spec)
            elif len(arms) > 1:
                astra, amode = None, "none"  # E-Couple A0 = VLA alone: no Astra at all
```

- `RuntimeConfig(...)` 인자에 `**CP.arm_config(arm, spec.get("couple_phase_pause", 3.0), spec.get("couple_min_interval", 0.0)), couple_budget_krw=spec.get("couple_budget_krw", 0.0), couple_ledger=spec.get("couple_ledger", ""), couple_prices=spec.get("couple_prices", ""), couple_run_id=f"{os.path.basename(spec['out'])}/{spec['variant']}/{label}"`를 더한다(`**rto`와 겹치는 키는 없다).
- 행 기록의 `"condition": label`은 새 `label`을 쓴다.

(d) `aggregate` 머리에:

```python
    from .couple import couple_cell, couple_diff, is_budget_excluded
    n_excl = sum(1 for t in trials if is_budget_excluded(t))
    trials = [t for t in trials if not is_budget_excluded(t)]
```

칸 딕셔너리 끝에 `"couple": couple_cell(S)`, `return out` 앞에 `out["couple_diff"] = couple_diff(trials, n_boot)`와 `out["couple_budget_excluded"] = n_excl`.

(e) `_md`: `res["couple_diff"]`가 있으면 표 하나를 더한다:

```python
    if res.get("couple_diff"):
        lines += ["", f"## Coupling arms, paired success difference (budget-excluded episodes: "
                      f"{res.get('couple_budget_excluded', 0)})", "",
                  md_table(["pair", "diff [95% CI]", "n"], [[k.replace("|", "\\|"), ci_str(v), v["n_pairs"]]
                                                            for k, v in res["couple_diff"].items()])]
```

- [ ] **Step 5: 통과 확인** — `python -m pytest tests/eval -v` → PASS(기존 closed 시험 포함).
- [ ] **Step 6: 전체 회귀** — `python -m pytest -q` → 실패 0.
- [ ] **Step 7: 커밋** — `msg_task14.txt` 첫 줄 `eval: coupling arms in closed, paid-run guard, budget exclusion, paired arm diff, estimate CLI (Task 14)`.

---

### Task 15: E-Couple 사전 등록 초안

**Files:**
- Create: `docs/stage3/prereg_couple.md`
- Test: 추정 CLI 실행(가짜 가격표, 형식 확인만)

- [ ] **Step 1: 초안 작성** — `docs/stage3/prereg_couple.md` 전문(시각 칸은 작성 때 `date -u`로 채운다):

```markdown
# E-Couple — Astra 직렬 1개 + 두 층 M4 대 VLA 단독 (사전 등록 **초안**, 유료 호출 0)

- 작성: <UTC>, 계획 `docs/superpowers/plans/2026-09-26-astra-vla-coupling.md` Task 15. 상태: **초안 — 자체 검사 절(§0: 바꾸는 결정·표본 충분성·무료 Qwen 사전 실행 결과·관문별 재설계 조건) 작성·커밋 전 유료 실행 금지**(user-log 87). 결과를 본 뒤 문턱·조건·시드·예산을 바꾸지 않는다(바꾸려면 새 등록).
- 근거: 설계 §9·§15·§16, 정본 §84 보충 2(직렬 1개, E-Couple 조건 = {VLA 단독, Astra 직렬 1개 + 두 층 M4}).

## 1. 질문
Astra(low) 일반 조종 흐름을 한 번에 하나씩 부르고 두 층 M4로 합치면, 같은 융합 VLA 단독보다 폐루프 성공률이 오르는가? 새 환경 층(DR)에서 낙폭이 줄어드는가? 호출 수·지연·비용은 얼마인가?

## 2. 조건 (`harvest.eval.closed --couple ...`)
| id | 명령 | 내용 |
|---|---|---|
| A0 | `--couple off,serial`의 off 칸 | VLA 단독(Astra 없음, 하트비트 없음) |
| A1 | `--couple off,serial`의 serial 칸, `--astra api --couple-upper astra` | Astra low 직렬 1개 + 두 층 M4 + 부드러운 편향 + 3카메라·덧그림 |
| (선택) A2 | `serial_pause`, `--couple-phase-pause 8` | A1 + 단계 쉬기(비용이 넘칠 때만, 등록 때 넣을지 결정) |

같게 두는 것: 융합 체크포인트(ser-A-min-3 재학습판, 해시를 실행 전에 이 문서에 적음), M4 조건 C5, H = 3, clock simlat, 판 길이 60 s, `CoupleParams` = 탐침 결과로 고정한 값(표를 실행 전에 이 문서에 붙임, `probe_ref` 기록), 프롬프트 판본 `astra-couple@v1`(`PROMPT_ID` 기록).

## 3. 층·표본
- 층: `standard`, `dr`(새 물체 에셋은 준비되면 새 등록).
- 표본: DEV 레이아웃 시드 0–19 × epoch 1 × 층 2 = 조건당 40편, 조건끼리 시드·층 짝.
- 스모크(판정 제외): `--astra mock`으로 시드 0–2 한 번 — 사이드카 `couple` 행·블롭·요약이 채워지는지 확인.

## 4. 지표
- 주: 성공률, 짝 차 A1 − A0(같은 변형·시드·epoch), 레이아웃 시드 군집 부트스트랩 10,000회 95 % 구간(`closed.json` `couple_diff`).
- 보조(판정 밖, 모두 보고): RD(standard → dr), 성공까지 시간, 편당 호출 수, 지연 p50·p95, 답 나이 p50, 편당 비용·성공 1건당 비용, gate 분포(uncertain → continue 비율 포함), Astra 층 동작(apply/confirm/flip), 편향 적용량·최대 속도·가속, 비가역 거부 수·이유, 사건 수(layer_mismatch·offset_contradicted·no_progress), 시간 초과·늦은 답·스키마 오류, 예산 제외 편 수.

## 5. 판정 (결과 전 고정)
1. **채택**: 두 층(standard ∪ dr) 합산 성공률 짝 차 점추정 ≥ +10 pt 그리고 95 % 하한 > 0.
2. **새 환경 이득만**: 1이 아니고, 합산 하한 > −5 pt 이며 dr 층 짝 차 하한 > 0 → "DR에서만 이득"으로 보고(런타임 기본은 바꾸지 않음).
3. 그 밖: 결론 유보, 결과 보고. 표본을 늘리려면 새 등록.
4. 예산 80 % 정지 뒤의 편은 판정에서 빼고 수를 보고한다. Isaac·파드 오류 편은 같은 시드로 한 번 다시 돌린다(두 번 실패면 제외·보고).

## 6. 예산 (정본 §82 보충: 전체 약 10만 원)
- 식: 호출 수 = 편 수 × 60 s / L, 비용 = 호출 수 × 호출당 비용(실행일 가격표; `python -m harvest.eval.couple estimate --prices <그날 가격표> --episodes 40 --episode-s 60 --latency-s <탐침 L p50> --in-tokens <탐침 실측> --out-tokens <탐침 실측>`).
- 설계 추정(설계 §8·§15: 호출당 약 28원, L = 4 s): 40편 × 15회 = 600회 ≈ 16,800원.
- **상한 25,000원**(80 % = 20,000원에서 정지·보고). 누적: 탐침 하드 정지 15,000원(2026-09-25 18:00 UTC 재범위) + 이 실험 25,000원 + E-Astra-necessity 흐름 자리 20,000원 = 60,000원 ≤ 100,000원. 실측 단가(탐침: low 파지 질문 15.7원)가 나오면 판 수를 다시 계산한다.
- 실행 명령(승인 뒤, 파드): `python -m harvest.eval.closed --model <체크포인트> --backend fused --out /data/harvest/out/e_couple --split dev --seeds 0-19 --variants standard,dr --couple off,serial --astra api --couple-prices <가격표> --couple-budget-krw 25000 --couple-ledger /data/harvest/out/e_couple/ledger.jsonl --approval "<user-log 번호>" --parallel`

## 7. 산출물
`docs/stage3/results/e_couple.md`(표·그림·영상: 판마다 카메라 3대 영상 확인), `closed.json`, 장부 JSONL, 블롭.
```

- [ ] **Step 2: 추정 CLI로 형식 확인(가짜 가격, 결과 수치는 문서에 쓰지 않음)** — Write 도구로 `D:\tools\scratch_qdd\plan_coupling\prices_fake.json`에 `{"model": "fake", "date": "2026-09-26", "usd_per_mtok_input": 1.0, "usd_per_mtok_cached_input": 0.1, "usd_per_mtok_output": 4.0, "krw_per_usd": 1400.0, "source": "format check only"}`를 쓰고:

Run: `python -m harvest.eval.couple estimate --prices D:/tools/scratch_qdd/plan_coupling/prices_fake.json --episodes 40 --episode-s 60 --latency-s 4 --in-tokens 3500 --out-tokens 1000`
Expected: `"calls": 600.0`과 `price_date`가 있는 JSON.

- [ ] **Step 3: 커밋** — `msg_task15.txt` 첫 줄 `docs: E-Couple pre-registration draft (serial single call vs VLA alone), budget 25,000 KRW cap (Task 15)`.

---

### Task 16: E-Astra-necessity 흐름 자리 사전 등록 초안

**Files:**
- Create: `docs/stage3/prereg_astra_necessity_stream.md`

- [ ] **Step 1: 초안 작성** — 전문:

```markdown
# E-Astra-necessity — 흐름 자리(실행 중 일반 조종) (사전 등록 **초안**, 유료 호출 0)

- 작성: <UTC>, 계획 `docs/superpowers/plans/2026-09-26-astra-vla-coupling.md` Task 16. 상태: **초안 — 자체 검사 절(§0) 작성·커밋 전 유료 실행 금지**(user-log 87).
- 범위: 정본 §82 E-Astra-necessity 중 **결합 흐름 자리**만. J1–J6(과제 컴파일·진단·검사 술어·이름·감사·증류) 오프라인 슬롯 시험과 폐루프는 §82 구현(`harvest/astra/jobs.py`)과 함께 별도 등록한다(연구 문서 `astra_role_2026-09-25.md` §7).

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

## 3. 층·표본
S-ID = `standard`, S-random = `dr`; 층당 DEV 시드 0–19 × epoch 1. S-novel·S-long·S-fail은 에셋·과제 준비 뒤 새 등록.

## 4. 판정 (정본 §82·연구 §7.5 규칙, 결과 전 고정)
Δ = U-A-low − max(U-Q8, U-Q4[, U-Q32]) 성공률, 레이아웃 시드 군집 짝 부트스트랩 10,000회.
1. **Astra 필수(이 자리)**: S-random에서 Δ ≥ +10 pt 그리고 95 % 하한 > 0.
2. **강등**: S-random에서 Δ의 95 % 하한 > −5 pt 그리고 점추정 ≥ −3 pt, 그리고 로컬의 편당 비용·지연 p50이 더 작다 → 흐름 자리를 최고 로컬 모델로.
3. 그 밖: 결론 유보, Astra 유지, 보고.
4. 대조: S-ID에서 U-A-low − U-Q4의 95 % 구간이 ±5 pt 안이면 "분포 안에서는 위층 차이 없음" 확인. U-A-low − U-none은 E-Couple과 같은 식으로 보고.

## 5. 예산
- 유료는 U-A-low뿐. **E-Couple A1과 같은 날·같은 체크포인트·같은 `CoupleParams`·같은 시드면 그 결과를 재사용**하고(이 문서에 재사용을 명시), 이 등록의 추가 유료 호출은 0.
- 재사용이 불가능하면 상한 20,000원(80 % 정지), 누적 한도 계산은 E-Couple 등록 §6과 같음.

## 6. 산출물
`docs/stage3/results/e_astra_necessity_stream.md`, `closed.json`(조건별 칸·`couple_diff`), 장부.
```

- [ ] **Step 2: 형식 확인** — `python -c "import pathlib; t = pathlib.Path('docs/stage3/prereg_astra_necessity_stream.md').read_text(encoding='utf-8'); assert all(s in t for s in ('## 2.', '## 4.', 'min_interval', 'U-rand')); print('ok')"` → `ok`.
- [ ] **Step 3: 커밋** — `msg_task16.txt` 첫 줄 `docs: E-Astra-necessity stream-slot pre-registration draft (local VLM paced to Astra latency) (Task 16)`.

---

## 끝난 뒤 (모든 Task 뒤, 코드 없음)

- [ ] `python -m pytest -q` 전체 통과를 `superpowers:verification-before-completion`으로 확인하고 출력 끝 줄을 결과 보고에 붙인다.
- [ ] `docs/handoff.md`에 결합 구현 완료 줄(커밋 범위, ser-A-min-3로 기존 체크포인트 거부, 재생성 절차 Task 12 Step 17, 유료 실행은 두 초안 승인 뒤)을 더하고 dev에 푸시한다.
- [ ] 조정자에게: 두 사전 등록 초안의 승인 요청(예상 비용은 그날 가격표로 `harvest.eval.couple estimate` 재계산 값), 모호점 판정 1·2·5·11의 확인 요청.
