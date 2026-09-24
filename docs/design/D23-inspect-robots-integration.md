# D23 Inspect Robots 코드 수준 통합 조사 (user-log 41)

저장 2026-09-24 08:04 UTC. 조사 에이전트 보고 전문. 메인이 받아 둔 코드(D:/tools/audit_d23/ir)에서 재확인: rollout.py:276-280 "The loop applies no wall-clock pacing of its own … declares the \"self_paced\" capability" / rollout.py:55-64 `derive_seed(eval_seed, scene_seed, epoch)` — scene.id 미사용(짝 장면 가능) / agent `_tools.py:632` "control needs finite low and high bounds" / isaacsim `embodiment.py:215` `Box(shape=(action_dim,), …)` low·high 없음 — 모두 일치.


## 작업 범위와 자료
- **소스:** 전체 클론 `D:\tools\audit_d23\ir`. HEAD `7e506e3`가 태그 **v0.59.0**(2026-09-22)과 같습니다. D22 얕은 클론과 내용도 같습니다.
  - 아래 경로는 이 폴더 기준입니다.
- **플러그인 판본(pyproject):** agent 0.27.0 / capx 0.3.1 / isaacsim 0.1.1 / ros 0.1.0 / xpolicylab 0.1.0.
- **스모크 시험(로컬):** `D:\tools\audit_d23\venv`에 코어만 설치했습니다. Isaac과 네트워크는 쓰지 않았습니다.
  - `smoke\smoke_async.py`: 비동기 정책 + 시계 3모드 + std/rnd 짝 장면 + 부가 로그. **3모드 모두 정상 종료(status=success)했습니다.**
  - `smoke\overhead.py`: 하네스 자체 오버헤드를 쟀습니다. **약 80 µs/step**(가드레일 + 행동 로그 포함, 이 노트북 기준)입니다.
- `D:\qdd`는 읽기만 했습니다.

---

## 1. 핵심 인터페이스 (코드 인용)

**관측·행동 타입** (`src/inspect_robots/types.py`)
- `Observation(images: Mapping[str, uint8 HWC], state: Mapping[str, float arr], instruction, image_times, state_time, extra)` (26–46).
  - 롤아웃이 `extra["env_step"]`, `extra["approvals"]`, `extra["operator_messages"]`를 넣습니다. 이 세 키는 예약돼 있습니다(32–38).
- `Action(data, meta)` (50–59). 행동의 의미는 행동 공간 쪽 `ActionSemantics`에 있습니다.
- `ActionChunk(actions, control_hz=None, inference_latency_s=None, meta)` (63–84).
  - 원문: "`control_hz` … advisory metadata … (the rollout enforces no rate)" (69–70).
- `StepResult(observation, reward, terminated, termination_reason, truncated, info)` (95–110).
  - 원문: "A simulator may expose privileged success via `info`" (102).

**Policy** (`policy.py`)
- Protocol은 `info: PolicyInfo`, `config: PolicyConfig`, `reset(scene)`, `act(observation) -> ActionChunk` 네 개뿐입니다(95–104).
- 선택 훅은 덕 타이핑으로 붙습니다: `bind(embodiment_info)`, `bind_task(envelope)`, `on_trial_start(scene_id, epoch, log_dir, run_id)`, `on_trial_end(record, log_dir, run_id)`, `transcript()`, `transcript_delta()` (61–92).
- `PolicyConfig(action_horizon=1, replan_interval=None, temperature=None)` (32–41). 로그에는 `asdict(policy.config)`로 들어갑니다(`eval.py:493`).
  - 따라서 **우리 설정 dataclass를 그대로 넣으면 EvalSpec에 기록됩니다.**

**Embodiment** (`embodiment.py`)
- 필수는 `reset(scene, *, seed) -> Observation`, `step(action) -> StepResult`, `close()` (136–150)입니다.
- 능력 플래그: `seedable/resettable/auto_reset/privileged_success/renderable/self_paced` (33–40).
- `EmbodimentInfo`에는 `control_hz`, `docs`(LLM 시스템 프롬프트에 그대로 들어감), `environment_id/revision`이 있습니다(44–69).

**Controller** (`controller.py`)
- `next_action(policy, observation, t, store) -> Action` (36–43).
- `DefaultController`: 버퍼가 비면 `policy.act()`를 호출하고 `replan_interval`개(없으면 청크 전체)를 쌓은 뒤 하나씩 꺼냅니다(46–67).
- `EnsemblingController`: 매 스텝 `act()`를 부르고 겹치는 청크를 섞습니다(117–190).
- **CLI에는 controller 선택지가 없습니다**(cli.py grep 0건). Python `eval(controller=...)`로만 바꿉니다(`eval.py:276`). 기본값은 `DefaultController(policy.config.replan_interval)`입니다(473).

**Task / Scene / Scorer**
- `Scene(id, instruction, target, init_seed, setup, metadata)` (`scene.py:33–41`).
- `Task(name, scenes, scorer, max_steps | max_seconds, epochs, metadata)` (`task.py:53–71`).
  - `max_seconds`는 `ceil(max_seconds × embodiment.control_hz)` 스텝으로 바뀝니다(131–161).
- `Scorer`: `name`, `__call__(record, target) -> Score` (`scorer.py:52–63`).
  - 기본 채점기: `success_at_end` (165–183), `episode_length`, `min_distance_to_goal`, `reached_goal_state`, `operator_scorer`.
  - 축약: `mean/median/max/min/mode/pass_at_<k>` (118–153).

**EvalLog** (`log.py`)
- `EvalSpec`: task/policy/embodiment/created/version/git_commit/policy_config/embodiment_info/seed/max_steps/max_seconds/environment_id/environment_revision/policy_checkpoint/grader/grader_config (43–90).
- `SceneResult`: reduced/epochs/instruction/scene_metadata/operator_judgements/judgement_sources/operator_notes/operator_messages/**trial_metadata**/termination_reasons/policy_transcripts (107–143).
- **스텝 궤적과 StepResult.info는 EvalLog에 남지 않습니다.**
  - 행동만 `actions/<run>/<trial>.jsonl`로 따로 저장됩니다(`eval.py:116–167`).
  - 카메라 프레임은 `--store-frames`일 때만 프레임당 `.npy` 파일로 저장됩니다(`frames.py` `FrameStore.put`).

**롤아웃 루프와 시간 소유** (`rollout.py:248–535`)
- 단일 스레드 동기 루프입니다: `policy.reset` → `embodiment.reset(scene, seed)` → `while t < max_steps:` → `controller.next_action` (383) → 차원·유한성 검사 → `approver.review` (444) → `embodiment.step` (470) → 기록.
- 원문: "The loop applies no wall-clock pacing of its own … An embodiment that needs real-time cadence paces itself inside `step()` and declares the `"self_paced"` capability" (276–280). 설계 R1 번복 경위는 `plans/0001-foundation-design.md:477–486`.
- **시간의 주인은 스텝 번호 t**입니다. 벽시계 박자는 몸체의 몫입니다.
  - 실례는 ROS 몸체입니다. `step()` 첫머리에서 `remaining = last_publish + 1/control_hz − now; sleep(remaining)`로 박자를 맞추고(`plugins/inspect-robots-ros/.../embodiment.py:418–431`), `capabilities = {SELF_PACED}`를 선언합니다(320).
- 정책 종료 요청은 `action.meta["request_stop"]`로 합니다(`rollout.py:440–441`, truncation으로 처리).
- 트라이얼은 순차로만 돕니다: `for scene … for epoch …` (`eval.py:547`). 병렬 실행은 없습니다.

**스레드 제약**
- 하네스는 정책 내부 스레드를 막지 않습니다. `act()`가 논블로킹이면 됩니다.
- Isaac Sim `SimulationApp`은 프로세스당 하나입니다(`isaacsim/.../embodiment.py:57–60`). step과 렌더는 롤아웃(메인) 스레드에서만 호출하고, 백그라운드 스레드는 HTTP(Jev/Astra)와 순수 파이썬 원장만 다뤄야 합니다([가정]: Kit 메인 스레드 규칙은 Isaac 쪽 제약).
- `TrialRecord.steps`가 매 스텝 관측(extra 포함)을 메모리에 쌓습니다(`rollout.py:486–495`). 깊이 배열은 callable로 넘겨야 합니다(capx README 같은 권고).

## 2. 우리 시스템을 Policy로 넣는 법

**가능합니다(스모크로 확인).**
- `act()`는 매 스텝 "현재 확정 행동 + 100 Hz 스킬 한 틱"을 즉시 반환합니다(ActionChunk 길이 1).
- Jev 약 3 Hz 겹침 호출과 Astra T_fail은 `ThreadPoolExecutor`에서 돌립니다.
- M4 원장·M7 critic은 `act()` 안에서 O(ms)로 갱신합니다.
- T0 계획(정지 허용)은 `reset()` 또는 첫 `act()`에서 블로킹해도 됩니다.
- Controller는 `DefaultController(replan_interval=1)`면 충분합니다.

**시계 모드 제안: 같은 정책 코드, 시계 주입만 다르게**

| 모드 | 방법 | 용도 | 스모크 결과 (시뮬 시각 기준 성공 시점) |
|---|---|---|---|
| **sync** | 호출마다 `act()`가 블로킹해 세계가 멈춤 | agent/capx와 같은 조건(공정 비교) | 0.14–0.35 s, 대기 0.3–1.1 s는 공짜 |
| **simlat**(권장, 시뮬 주 트랙) | 시뮬 시각 `t_s`에 보낸 응답을 `t_s + 실측 벽시계 지연`에 전달. 시뮬이 마감에 먼저 닿으면 그때만 블로킹 | 시뮬 속도와 무관하게 실시간 의미 보존, E-M4-lat 인공 지연 주입과 같은 틀 | 0.37–0.88 s |
| **wall** | 몸체가 SELF_PACED로 벽시계에 맞춤, 정책은 비블로킹 | 실물(E-real), 또는 시뮬 RTF ≥ 1일 때만 | 0.42–0.86 s, 블로킹 0 |

- 스모크에서 simlat ≈ wall이 나와 모델링이 맞다는 것을 확인했습니다(장난감 몸체 기준).
- 시뮬 시각은 몸체가 `extra["sim_time"]`로 주거나, `env_step / control_hz`로 계산합니다.
- **wall을 시뮬에 쓰면 위험합니다.** ZED_M 렌더 때문에 RTF < 1이면 LLM이 상대적으로 빨라 보이게 됩니다. RTF를 로그에 남겨야 합니다.

**공정성 문제**
- agent/capx는 동기입니다. agent README 원문: "the arm stands still while the model thinks" (`plugins/inspect-robots-agent/README.md:416`). 시뮬에서는 세계도 멈춥니다.
- 제안: **모든 조건을 sync-fair와 latency-faithful 두 트랙으로 돌리고 따로 보고합니다.**
  - 기준선용 latency-faithful은 우리 `LatencyChargingController`로 만듭니다(약 40줄).
  - 동작: `policy.act` 시간 L을 재고, 청크 앞에 "직전 명령 유지" 행동 `ceil(L×hz)`개를 붙입니다. 실물에서 LLM이 생각하는 동안 로봇이 멈춰 있는 상황과 같습니다(B6b-wall과 같은 모양).
  - `max_seconds` 과제는 sync에서 생각 시간이 공짜라는 점을 표에 적습니다.
- 어느 트랙을 주 표로 할지는 [결정 필요]입니다.

**2차(RoboDojo) 대비**
- xpolicylab 계획서 원문: "RoboDojo embeds the same protocol on its eval side" (`plans/0007-xpolicylab-policy-plugin.md:74`).
- 그러니 정책 핵심은 하네스 중립 모듈로 만들고, 얇은 어댑터 두 개(Inspect Robots `Policy`, XPolicyLab 서버)를 두기를 권합니다.

## 3. Embodiment: AI Worker SG2

**기본 isaacsim 플러그인은 그대로 쓸 수 없습니다(새로 써야 함).**
- 행동 Box에 low/high와 dim_labels가 없습니다(213–223). 그래서:
  - 적합성 검사 "bounds/dim_labels" 오류가 납니다(`docs/guide/adapters.md` 표).
  - agent는 `"absolute-target control needs finite low and high bounds"`로 bind에 실패합니다(`agent/_tools.py:626–632`).
  - capx도 유한 경계를 요구합니다.
- 상태 `joint_pos`가 (7,)이고 행동은 8-D입니다(`_default_state_fields` 133–145). agent가 요구하는 "exactly one state field with shape (8,)"(603–623)를 채우지 못합니다.
- `reset()`이 `scene`을 무시합니다. `env.reset(seed=seed)`만 호출합니다(297–301). 장면 변형을 적용할 곳이 없습니다.
- `num_envs=1`로 고정입니다(287). gripper가 `binary`이고, self_paced가 없고, extra에 깊이가 없습니다.
- 재사용할 부분: 지연 부팅 `AppLauncher`와 싱글턴 처리(244–269), `parse_env_cfg` + `gym.make(cfg=…)`(271–292), 텐서→numpy 헬퍼.

**판본**
- 코드가 `isaaclab.app`, `isaaclab_tasks`, `isaaclab_tasks.utils.parse_env_cfg`를 씁니다. Isaac Lab 2.x 이름 체계입니다.
- 플러그인은 isaac 판본을 고정하지도 않고, 시험 판본 기록도 없습니다. **Isaac Lab 2.3 / Sim 5.1에서의 실제 동작은 [미확인]입니다.**
- `Cyclo-*` gym id는 cyclo_lab 패키지를 import해야 등록됩니다. 모듈 이름은 [미확인]입니다.
- 코어는 Python ≥3.10에 numpy만 필요하므로 Isaac 5.1의 파이썬(3.11 [미확인])에 설치할 수 있습니다.

**우리 `aiworker` 몸체 요구 사항**
- **행동 공간:** `joint_pos` 8-D(팔 7 + RH-P12-RN). low/high, `dim_labels`(`…,"gripper"`), `max_step`, `gripper="continuous"`.
- **상태:** `joint_pos (8,)` 하나를 기준 필드로 둡니다(agent·capx 요구).
- **제어 주기:** 100 Hz 스킬을 쓰려면 cyclo_lab 기본 `sim.dt 0.01, decimation 5`(D21 §1, env step 20 Hz)를 **decimation 1**로 바꿔야 합니다. 카메라는 update_period 1/30 s로 두고, **새 프레임이 있는 스텝에만 images를 넣습니다.**
  - 이유: FrameStore가 스텝×카메라마다 `.npy`를 씁니다. 100 Hz × 2대 × 60 s면 에피소드당 수 GB입니다.
- **카메라:** ZED_M 좌·우 + 손목. `extra`에 `depth`/`intrinsics`/`extrinsics` callable(capx 형식), `sim_time`, 시뮬 전용 `oracle`(E0–E3)을 넣습니다.
- **성공 판정:** T1 술어가 1 s 연속 참이면 `terminated, "success"`.
- **eef 모드(선택):** `eef_abs_pose` + `rotation_repr="none"`(xyz + 그리퍼, 내부 DiffIK). agent가 `move_to`를 쓰게 됩니다(`_POSE_MODES`/`_SAFE_ROT`, `_tools.py:33–35`).
- **공유 규칙:** `docs` 문자열(관절 부호·그리퍼 극성), 적합성 테스트.

**ROS 2(실물 SG2)**
- ros 플러그인은 **rosbridge 웹소켓 + `joint_pos` 전용**입니다. `ros_version=2`, JointTrajectory 또는 Float64MultiArray를 지원합니다.
- 원문: "The stock ROS 2 `gripper_action_controller` is action-only and is not supported" (README).
- AI Worker의 그리퍼가 팔 JTC 안의 관절이면 `joints=`에 8번째로 넣어 그대로 쓸 수 있습니다. 그리퍼 컨트롤러 구성은 [미확인]입니다.
- Jazzy용 rosbridge 호환은 [미확인]입니다. 머리·리프트는 `reset_service`로 고정해야 합니다.
- 100 Hz를 JSON rosbridge + base64 JPEG로 보내는 것은 무리일 가능성이 큽니다. 권고: rosbridge로는 30–50 Hz 기준선만 돌리고, 우리 100 Hz 경로는 rclpy 네이티브 몸체를 따로 씁니다([가정]).

## 4. 장면·과제·채점

**짝 장면**
- `derive_seed(eval_seed, scene.init_seed, epoch)`는 **scene.id를 쓰지 않습니다**(`rollout.py:55–64`).
- 그래서 `std-L3`와 `rnd-L3`에 같은 `init_seed`를 주면 epoch마다 같은 트라이얼 시드를 받습니다. 스모크에서 확인했습니다(두 장면 모두 3720929858 / 2865746644).
- **변형 적용은 하네스에 없고 몸체 몫입니다.** 권고:
  - `Scene.metadata={"variant","layout_seed","appearance_set","distractors"}`를 `reset(scene, seed)`에서 해석합니다.
  - 배치는 `layout_seed`로 고정합니다(epoch 간 불변). trial seed는 잡음에만 씁니다.
  - `scene_metadata`는 로그에 복사됩니다(`log.py:117–119`).
  - `supported_setups`로 실현 가능성을 미리 검사할 수 있습니다(`compat.py:215–237`).

**채점**
- **시뮬:** 특권 판정을 `termination_reason="success"`나 `info`로 넘기고 `success_at_end` 또는 자작 scorer로 씁니다(`info`는 채점 시점 메모리에만 있습니다).
- **실물:** `operator_scorer`나 `--grader vlm`(+`observe_parked`)을 씁니다. 판정 경로는 `judgement_sources`에 남습니다.
  - Robocurve 편향 경고를 고려해 **조건을 모르는 채점자**를 둡니다.
  - 우리 센서 술어는 보조 기록으로 남깁니다.

**epoch와 축약**
- 축약기는 과제당 하나입니다(`Epochs.reducer`). `pass_at_k`는 epoch가 k 이상이어야 합니다(`scorer.py:127`).
- epoch별 값이 `SceneResult.epochs`에 남으므로 **RD·짝 부트스트랩·pass@k는 로그에서 오프라인으로 계산합니다.**

**병렬**
- 없습니다. Isaac은 프로세스당 싱글턴이므로 `@task(shard=k/n)`로 나눠 파드별로 돌리고 로그를 합칩니다. 합치는 기능은 없어 직접 써야 합니다.

## 5. 하네스 안 기준선과 필요한 준비

- **`agent` + Astra**
  - 충실판(Robocurve 보고서): `-P effort=medium -P max_llm_calls=20 -P max_speed_frac=0.25`, 224×224 프레임(몸체 카메라 해상도로 맞춤).
    - "25% speed cap" = `max_speed_frac` 대응은 [해석, 미확인].
  - 우리 공정 조건: effort low와 high, 호출 예산은 우리와 같게.
  - 모델 문자열·wire(`openai/…`, `responses`)는 [미확인]입니다.
  - 필요한 것: 경계와 라벨이 있는 우리 몸체. eef 비교까지 하려면 eef 모드도 필요합니다.
  - 주의: agent는 `obs.state`의 **모든 키**를 프롬프트에 씁니다(`policy.py:1201–1219`). 오라클 물체 자세를 state에 넣으면 agent도 봅니다. 정보 동등 스위치로 쓸 수 있습니다.
- **`capx`**
  - 요구: joint_pos, 유한 경계, `gripper` 라벨, 전체 차원 state 필드 하나, `control_hz`.
  - 서버 3개가 필요합니다: SAM3, Contact-GraspNet, Pyroki. Pyroki는 AI Worker URDF로 띄워야 하고 로봇 설명 등록 여부는 [미확인]입니다.
  - 깊이·행렬은 extra로 넘깁니다.
  - 생성 코드가 평가 프로세스 안에서 실행되므로 컨테이너로 격리해야 합니다(README Trust model).
- **`xpolicylab` π0.5**
  - `-P action_type=joint arms=1 arm_dim=7 ee_dim=1 cameras=… control_hz=…`로 8-D 행동이 됩니다(policy.py:168–170, gripper continuous).
  - **AI Worker 한 팔용 미세조정 체크포인트가 필요합니다**: cyclo_lab Mimic → LeRobot, standard + DR 데이터. XPolicyLab에서 우리 로봇 구성을 지원하는지는 [미확인]입니다.
  - B3c/B3c-V는 우리 Policy 플러그인으로 직접 붙입니다.

## 6. 로그 추가 방법

- **설정:** 우리 설정 dataclass를 `policy.config`로 둡니다 → `EvalSpec.policy_config`. 담을 것: `astra_prompt_id`, `question_id@vN` 목록, 모델 ID, effort, T_c, 시계 모드, M4 파라미터. 판본은 `environment_revision`·`policy_checkpoint`에 둡니다.
- **트라이얼별:** `on_trial_end`에서 부가 JSONL(M4 표·option_key·epoch·Astra 요청 해시·카나리 id)을 쓰고, 경로와 요약을 `record.metadata`에 넣습니다 → `SceneResult.trial_metadata`. 스모크에서 확인했습니다.
- **대화 기록:** `transcript()`는 최대 2 MB입니다(`rollout.py:50,117–141`).
- **스텝 단위 로그:** registry `sink`로 `LogSink.log_step/on_trial_end`를 받는 방법도 있습니다.

## 7. 단계별 계획 [가정: 공수]

| 단계 | 내용 | 공수 |
|---|---|---|
| **P0** | Isaac 5.1 파이썬에 코어 v0.59.0과 플러그인을 **git 태그로 고정** 설치. PyPI 판본 존재는 [미확인]. 할 일: `doctor`, cubepick + agent(Astra low), `plugins/inspect-robots-isaacsim/scripts/boot_proof.py`, Franka Lift, 우리 smoke_async를 RTX 노드에서 실행 | 0.5–1일 |
| **P1** | `aiworker` 몸체 작성(3절 요구 사항 + 시계 모드 + RTF 기록 + 적합성 테스트). 선결: SG2 한 팔 과제 등록 여부 [미확인] | 4–7일 |
| **P2** | `OursPolicy` 어댑터(스레드 풀, M4 원장, 스킬 100 Hz, M7, T_fail 비동기, sync/simlat/wall, E-M4-lat 지연 주입) + `LatencyChargingController` + 부가 로그 | 5–8일 |
| **P3** | 기준선: agent 충실판·공정판, capx 서버, xpolicylab π0.5 | 3–6일, π0.5 학습은 별도 |
| **P4** | 짝 파일럿: layout 0–4 × {std, rnd} × epoch 3 × {sync-fair, latency-faithful}. 오프라인 RD와 짝 부트스트랩 스크립트 | 3–5일 |

**위험**
- **API가 alpha입니다.** 원문: "breaking changes may occur on any minor release" (CHANGELOG). v0.59.0과 커밋 `7e506e3`을 고정하고 사본을 보관해야 합니다.
- **관리자 한 명 의존:** 기여 커밋 355/515가 한 사람입니다.
- **라이선스:** 하네스는 MIT입니다. cyclo_lab·XPolicyLab·CaP-X·SAM3 라이선스는 [미확인]입니다.
- **Isaac 호환·렌더링:** 2.3 호환 [미확인]. H200에는 RT 코어가 없어 렌더링 위험이 있습니다(D17과 같은 위험).
- **디스크·메모리:** 프레임 저장과 메모리 누적(3절)을 관리해야 합니다.
- **보안 기본값:** Python `eval()`의 기본 approver는 `AutoApprover`입니다(`eval.py:474`, capx README:163). 실물에서는 `ChainApprover(Clamp, DeltaLimit)`를 직접 연결해야 합니다.

**우리 문서에서 바꿀 것 (제안, D:\qdd는 수정하지 않음)**
- **EVAL:**
  - §2.6에 "1차 = Inspect Robots + AI Worker 시뮬" 행 추가.
  - §3.1에 B1a-IR(agent 충실판과 공정판), B5 capx판, B3b-IR(π0.5 AI Worker 재학습) 추가.
  - §3.2에 새 항목: **시계 트랙 두 개**(sync-fair / latency-faithful)와 RTF 보고.
  - §4.2 프로토콜을 AI Worker 짝 장면·layout 규칙으로 1차판 작성(RoboDojo는 2차).
  - §5에 S0' = P0/P1 추가.
- **E-first:**
  - §1.4 요구 조건 (4) "벽시계 동기 실시간"을 **"simlat(지연 충실 시뮬 시계), RTF ≥ 1일 때 wall 병기"**로 바꿉니다.
  - §4.3 "병렬: 환경 4개 동시"는 하네스가 순차이므로 **프로세스·파드 분할**로 바꿉니다.
  - §1.6 기록은 `trial_metadata`와 부가 JSONL 대응을 명시합니다.
  - E-M4-lat 지연 주입은 같은 시계 추상화로 구현한다고 적습니다.
  - 오라클 상태를 agent에 줄지(정보 동등)를 [결정 필요]로 올립니다.
- **00 §41:** "몸체 쪽 벽시계 박자"만으로는 시뮬 RTF < 1일 때 무너집니다. 이 점과 simlat 권고를 덧붙입니다.
