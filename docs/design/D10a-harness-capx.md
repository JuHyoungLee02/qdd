# D10a 원문 정독: Harness VLA · CaP-X

작성: 2026-09-24 00:47 UTC. 정독 에이전트 보고 전문을 메인 세션이 저장했다(대화 기록에서 추출, 줄이지 않음). 메인 세션 원문 재확인(curl): Harness VLA HTML v4 "The planner waits for these files before selecting the next primitive" / "limited by an open feedback loop between the high-level planner and low-level VLA" / "the planner cannot invent new primitives at deployment time" / "never replay literal coordinates" / Table 3 CC 82.4 / RoboCasa 57.1 대 30.0 = 27.1. CaP-X HTML "9 verified, task-agnostic primitives" / Table 5 3M 68.29 대 3M+debug 65.43 / "hybrid CaP-VLA policies" / M2 저하 "cross-modal alignment gap". RPent README "Codex / GPT-6 Astra / low / reasoning: 92.63% Overall (741/800)".


작업 규칙: WebSearch·GitHub API 없음, curl만 썼고 요청 간격은 2초 이상. 조사일 2026-09-24.

**읽은 것**
- Harness VLA: arXiv HTML v4 전문(2026-09-02 개정, v1은 2026-07-09) + 부록 A~F.
- RPent 저장소 README.
- RPent 문서(readthedocs) 10쪽: leaderboard/performance, time-token-costs, development/memory, usage/configure_primitives, configure_planner, flash, flywheel, libero, development/interfaces, add_primitive.
- RPent 코드: `robots/libero/toolkit.py`, `robots/libero/tools.py`, `robots/libero/prompt_bundle.py`, `robots/libero/prompts/evaluate.py`, `rpent/memory/manager.py`.
- HF 데이터셋 `RLinf/RPent-memory`의 `libero/MEMORY.md`와 전역 leaf 2개.
- CaP-X: arXiv HTML v2 전문(2026-07-02 개정, v1은 2026-03-23) + 부록 A~K.
- capgym/cap-x 저장소: README, `docs/configuration.md`, `scripts/skill_library_compilation/README.md`, `compile_skill_library.py`, `capx/envs/launch.py`, `capx/envs/trial.py`(VDM 프롬프트), `env_configs/cube_stack/franka_robosuite_cube_stack_multiturn_vdm.yaml`.

---

## 1. Harness VLA (2607.08448) + RPent

### 1.1 원문 사실

**서지**
- 저자: Yixian Zhang, Huanming Zhang 외 16명. 교신 저자 Wenbo Ding, Chao Yu.
- 소속: Tsinghua 1순위, Striding AI, Purdue, CASIA, Infinigence AI, HKUST, Zhongguancun Academy.
- 학회 표기 없음. 코드: github.com/RLinf/RPent. 웹: harnessvla.github.io.
- 초록 수치가 판본마다 다르다. arXiv abs 페이지 초록은 "38.6 and 25.4 percentage points", HTML v4 본문·초록은 "38.6 and 27.1". RoboTwin C2R은 둘 다 58.4%.

**프리미티브 어휘와 인터페이스(§2.3 Table 1, 부록 B Table 8)**
- 분석형(analytic) 6개:
  - `move_to`: Composite. 세계 좌표 데카르트 목표로 이동, 환경 내장 solver 사용.
  - `move_pose`: Composite. pitch 등 자세 변수를 함께 바꿈.
  - `rotate_wrist`: Atomic. yaw set-point.
  - `rotate_pitch`: Atomic. pitch set-point.
  - `set_gripper`: Atomic. 열림/닫힘 set-point를 고정 스텝 수 동안.
  - `release`: Atomic. release post-condition까지 연다.
- VLA 1개: `vla_act`. "Execute a frozen VLA in short bursts".
- RoboCasa365 전용 2개: `navigate_to`(Composite), `move_base`(Atomic, 개루프 속도 set-point).
- RoboTwin은 새 이름 없이 `arm` 인자로 왼팔/오른팔/양팔 바인딩.
- `reset`은 탐색 단계 전용이고 프리미티브로 세지 않는다.
- 규칙 문장: "the primitive vocabulary is fixed before evaluation; the planner cannot invent new primitives at deployment time."
- 각 호출은 JSON 하나이고, "executes inside the environment until an internal post-condition is reached, and then returns control together with a refreshed observation". 플래너는 토크·관절 목표·액션 청크를 직접 내지 않는다.
- JSON 계약(§2.3): `{"action": "vla_act", "prompt": <str>, "max_chunks": <int>, "stop": <predicate>}`.
- 부록 B 예시:
  - `move_to`: `"xyz":[-0.101,0.202,1.05], "arm":"auto", "gripper":"open", "tol":0.012, "max_steps":80`
  - `navigate_to`: `"xy":[1.20,-0.35], "tol":0.05`
  - `move_base`: `"forward":0.10, "lateral":0.00, "turn":-0.15, "steps":12`
  - `vla_act`: `"prompt":"grasp the black bowl", "arm":"auto", "max_chunks":30, "stop":"object_lifted"`
- "The exact numerical tolerances and stop predicates are benchmark-specific."

**stop 술어(부록 B)**
- 원문: "The planner configures a stop predicate τ, which may correspond to a lift-and-grasp condition, a contact-state condition, a benchmark predicate, or a chunk budget."
- 프리미티브 post-condition은 제어를 돌려줄 때만 쓰고, 과제 성공 판정은 벤치마크 술어로만 한다(부록 C 서두).

**실제 공개 코드 LIBERO 도구(`robots/libero/tools.py` TOOLS_SPEC)** — 논문 어휘와 이름이 다르다.
- `vla_act`는 `pi0_pick`과 `pi0_doubled` 두 개로 나뉘어 있다.
- `pi0_pick(prompt, max_chunks=24, lift_thresh=0.05 m, gripper_closed_thresh=0.06, gripper_open_thresh=0.0, descent_thresh=0.10 m)`:
  - 성공 = EEF가 descent_thresh만큼 내려갔다가, 최저점 뒤 lift_thresh만큼 올라가고, 손가락 간격이 [open_thresh, closed_thresh) 안에 있을 때.
  - LIBERO `terminated`가 뜨거나 max_chunks를 다 쓰면 조기 종료.
  - 반환 필드: success, chunks_used, peak_lift_m, min/final_gripper_opening, diagnostics.
  - 설명문: "Use it for the grasp; YOU then do every move_to and release. Use modest max_chunks and verify the grasp from EEF lift, gripper closure, and available images."
- `pi0_doubled(prompt, max_chunks=20)`:
  - 비집기 접촉용(스토브·손잡이·버튼·짧은 밀기).
  - success는 공식 종료 신호만 따른다. 설명문: "success=false does not necessarily mean the contact interaction failed."
- `move_to`:
  - 기본값: tol 0.012 m, step_clip 0.025 m, max_steps 80, action_scale 0.05, yaw_step_clip 0.10 rad.
  - 설명문에 "NEVER command a single move_to with |Δxy| > 0.30 — OSC flips IK"가 들어 있다.
- `release`: max_steps 20. `set_gripper`: steps 5.
- 읽기 전용 도구: `back_project`, `segment`(SAM3), `view_env_state`, `view_camera_meta`, `finish`. 이 도구들은 환경을 진행시키지 않는다.
- 문서 원문: "Physical action tools advance the environment and record new state and images."
- `reset`은 exploration 모드에서만 등록된다(toolkit.py).

**루프: staging → attempt → observe → retry(§2.1, Key Finding 2, 부록 A)**
- 매 턴 플래너 Π가 관측, 과제 문장, Task Specific Memory와 Global Memory 문맥을 받아 프리미티브 호출 하나를 낸다. 실행 종료 뒤 새 관측이 오고, 목표 술어가 참이 되거나 스텝 예산이 끝날 때까지 반복한다.
- Key Finding 2: 분석형 프리미티브로 접촉 전 자세를 잡는다(staging) → VLA 호출 → 접촉 결과 관찰 → 계속할지, 다시 자세를 잡을지(re-stage) 결정.
  - "staging restores a VLA-compatible local state"
  - "retry localizes contact failures"
- Fig. 4: 에피소드당 VLA 호출 상한별 누적 성공 곡선. 처음 몇 번에 빠르게 오르고 포화한다. 곡선 점별 값은 본문에 없고 그림만 있다.
- Fig. 6: 성공 롤아웃의 마지막 완료 술어가 분석형 뒤에서 켜졌는지 VLA 뒤에서 켜졌는지 비율. 역시 수치 표 없음.
- 부록 A(동기 대기): "synchronous file-mediated Read-Eval-Print Loop… emits one primitive invocation c_t by writing a JSON object to command.json. The worker consumes this file, executes the selected primitive…, and writes the next indexed observation… **The planner waits for these files before selecting the next primitive.** Thus, each physical action is followed by observation and diagnosis before the rollout continues."
- Table 7 파일:
  - `command.json`
  - `state_NN.json`: 과제 문장, 고유감각, 벤치 성공 신호
  - RGB-D / world-map 파일
  - `log_NN.json`: 받아들인 명령, 상태, 스텝 수, 실패 정보
  - `done_NN.flag`: 동기화 신호
  - Task Specific Memory trace(JSONL)와 summary(JSON)
  - Global Memory
- 부록 E.6 프롬프트 골격 3번: "Write one JSON command… Wait for the driver result. Read state_NN.json, log_NN.json, images… Then decide the next command."
- 플래너가 생각하는 동안 시뮬이 멈춘다는 명시 문장은 없다. 다만 환경은 물리 행동 도구로만 진행되므로 사실상 정지형이다([해석]).
- 부록 A 하단: 매 프리미티브 뒤 플래너가 결과를 **progress / recoverable failure / unrecoverable failure** 셋 중 하나로 분류한다.

**두 단계 수명(§2.2)**
- 탐색 부트스트래핑:
  - 참조 인스턴스 1개(seed 0)에서 reset 허용, "generous wall-clock budget".
  - 바꿔 보는 것: "staging orders, pre-contact poses, invocation timings for vla_act, and early-return termination thresholds".
- 배포 평가:
  - reset 금지, "operational step budget is significantly shortened".
  - Task Specific Memory의 JSONL을 불러와 현재 RGB-D로 다시 grounding하고, Global Memory를 참고해 "executes the trajectory deterministically".

**Task Specific Memory(부록 A, E.3)**
- 절차 JSONL trace와 의미 JSON summary 두 파일.
- summary 예: `{"task", "success", "trace_file", "strategy":"use VLA for grasping, then analytic transport and release", "avoid":["do not reuse reference xyz values", "verify placement with the benchmark success signal"]}`
- trace 예: `{"action":"vla_act","prompt":"grasp the black bowl","max_chunks":2}`, `{"action":"move_to","xyz":[0.12,-0.08,0.92],"gripper":null}`, `{"action":"release"}`
- §2.2는 좌표를 "symbolic perception queries"로 바꿔 저장한다고 적었다. 부록 A는 좌표를 "reference-scene bindings"로 보고 배포 때 다시 grounding한다고 적었다.
- E.3 규칙: "Reuse the Task Specific Memory procedural structure, but never replay literal coordinates."

**Global Memory(부록 A, E.4)**
- 과제와 무관한 운용 지식 = **success rules + failure models**.
- 예시 원문:
  - Success rule: "Use VLA primitives for contact-rich phases such as irregular grasping or fixture interaction. After a stable grasp, prefer analytic motion for long transport and precise placement."
  - Failure model: "If the gripper closes but the object does not move with the end effector, treat the attempt as an empty grasp. Re-localize the object and re-stage before retrying."
  - Failure model: "Do not terminate from visual proximity alone. Check the benchmark success signal and the latest execution record."
- E.4 점검 목록: (1) VLA·분석형 성공 규칙, (2) 반복·수리 전 알려진 실패 모델, (3) 빈 집기, 엉뚱한 물체, 거짓 시각 성공, 불안정한 staging.

**메모리를 만드는 방식**(부록 A "Iterative memory construction")
- 상호작용 중에 만든다.
- 성공 롤아웃 → Task Specific Memory.
- 회복 가능한 실패 → trace에 남기고 summary에 설명.
- 실패 시도 → 부정 증거로 남기고 failure model 후보로 Global Memory에 기여.
- "A later attempt can replace the procedural trace if it yields a shorter or more reliable solution."

**메모리 코드·데이터 형식(RPent, 원문=코드)**
- 디렉터리(`development/memory`): `MEMORY.md`, `global/`, `suite/`, `task_only/{<cell>.json, <cell>_recipe.jsonl, <task_key>.md}`.
- 평가 모드는 읽기만 하고, 탐색 모드는 생성·갱신한다. 탐색 모드는 LIBERO만 지원.
- HF `RLinf/RPent-memory`에서 동기화한다. 기여는 이슈를 열면 유지보수자가 심사해 게시한다.
- `manager.py`:
  - SCOPES = {global, suite}
  - KINDS = {primitive, perception, strategy, failure, infra}
  - CONFIDENCE = {single-shot, probable, verified}
  - 전역 leaf 필수 필드: `title`, `applies_when`, `kind`, `confidence`, `evidence.cells`(비어 있지 않은 목록).
  - suite leaf 필수 필드: `suite`, `regime`, `task_id`, `task_language`.
  - 병합(`_merge_evidence`): cells 합집합, attempts 합산. **confidence = cells ≥ 3이고 과제 ≥ 2면 verified, cells ≥ 2면 probable, 그 밖은 single-shot.**
  - 본문이 다르면 새 초안을 `_internal/conflicts/`에 보관하고 기존 본문은 유지한다.
  - task audit/recipe 쌍은 solved일 때만 `task_only/`로 복사한다.
  - 효용 카운터·삭제 규칙은 없다.
- HF `libero/MEMORY.md` 색인: Global 61개, Suite 75개.
- leaf 예(`global/can-pick-visual-confirmation.md`):
  - frontmatter: id, scope, kind: perception, title, applies_when, symptom 목록, evidence{cells:[object_swap_t0_s0], attempts:[1]}, confidence: single-shot, related.
  - 본문: 한 줄 교훈, **Why**, **How to apply**, **Falsify**(반증 조건), **Related**.
  - 교훈 내용: `pi0_pick.success`가 false여도 영상상 들고 있으면 `set_gripper +1 steps 5` 뒤 운반을 계속한다.
- 다른 leaf(`avoid-full-task-prompt-after-miss`): 집기에 실패하면 전체 과제 문장이 아니라 "pick up the <object>"만 주고, 사전 위치 1~3 cm 이동 또는 max_chunks 12~16 중 한 레버만 바꾼다.

**꺼내는 방식(evaluate.py 프롬프트)**
- 검색은 코드가 아니라 **플래너 에이전트 스스로** 한다.
- 원문: "READ MEMORY FIRST… `MEMORY.md`… SEARCH the library yourself… `list_dir`… `grep -rl "<keyword>"`… choose the one whose objects, spatial relation and step order actually match YOUR scene, deciding from the file body". 읽은 파일 이름을 `strategy_notes`에 기록하게 한다(감사 가능성).
- 같은 평가 프롬프트에 seed-0 탐색에서 얻은 과제별 수치 레버가 긴 절 "PROVEN LEVERS & LESSONS — libero_10_task seed-0 sweep solved 9/10"로 하드코딩돼 있다. 예:
  - 머그·그릇은 테두리 잡기 `eef_y = object_y + 0.045`
  - t4는 `max_chunks<=8`, 집기 전용 프롬프트
  - `|y|>0.27`은 z≥0.56 도달 불가
  - GRIPPER SIGN +1=닫힘

**플래너 모델·설정**
- 논문에는 "Harness VLA (Codex)"와 "Harness VLA (CC)" 두 행뿐이다. 모델 판본과 effort는 **논문에 없다**.
- RPent 리더보드: Codex 행 = "Codex / GPT-5.5 / xhigh / reasoning", CC 행 = "Claude Code / Opus-4.7 / max.reasoning".
- 같은 사이트 비용 표는 xhigh 행을 "GPT-5.6 Sol Codex · xhigh"로 적어 이름이 어긋난다.
- 플래너 CLI 기본값(`configure_planner`):
  - `--max-turns` 100. "A single LIBERO task rarely needs more than ~30 turns".
  - `--planner-timeout-s` 1200 s(codex/claude_code).
  - api 플래너 `--max-tokens` 8192.
  - claude_code 달러 상한 기본 10.
  - Codex는 `--reasoning-effort` 옵션이 있고, `CODEX_SERVICE_TIER=fast`는 effort를 바꾸지 않는다.
- 재현 명령(libero 문서, gpt-5.5 xhigh, reproduce/libero 브랜치): `--max-turns 100 --planner-timeout-s 5000 --max-episode-steps 10000 --libero-type pro`. 이 판의 기록: libero_10_task 70%(70/100), libero_10_swap 55%(55/100).

**Astra low 92.63% (741/800) 항목** — README와 리더보드에만 있고 논문에는 없다.
- README: "Codex / GPT-6 Astra / low / reasoning: 92.63% Overall (741/800) across all eight LIBERO-PRO suites".
- 칸별 값: Spatial Task 100%, Spatial Swap 98%, Object Task 100%, Object Swap 99%, Goal Task 88%, Goal Swap 99%, Long Task 85%, Long Swap 72%.
- 리더보드 주석 원문: "GPT-6 Astra (memory-enabled configuration): Long Task/Swap and the other six suites use separate memory-file snapshots frozen after their respective exploration phases, with no updates during evaluation. Overall combines two non-overlapping batches: Long 157/200 plus the other suites 584/600, giving 741/800 (92.63%); the 800 episodes do not share a single memory snapshot."
- 축: T(instruction-redirection, 문서의 "Task")와 S(position-swap) × Spatial/Object/Goal/Long = 8칸. lan/object/env 섭동은 포함되지 않는다.
- 같은 리더보드의 "RPent / GPT-6 Motor Only (Codex · low · reasoning)": Long Task만 38.0%. 설명: "directly outputs end-effector pose increments and gripper commands through execute_action, without invoking VLA / primitives or loading memory".
- 시간·토큰(time-token-costs, LIBERO-PRO):

| 구성 | 에피소드당 평균 시간 | 총 출력 토큰 |
|---|---|---|
| GPT-6 Astra low | 412.14 s | 3,364,938 |
| GPT-5.6 Sol xhigh | 529.23 s | 3,635,426 |
| GPT-5.6 Sol no-reasoning | 344.17 s | 2,569,676 |
| Flash(Molmo2-8B) | 60.19 s | 0 |
| Qwen3.6 27B no-reasoning | 626.3 s | 3,270,754 |

- 리더보드의 다른 Astra 값:
  - RoboCasa365 Target50: GPT-6 Astra low 59.20%(Atomic-Seen 87.78 / Composite-Seen 43.75 / Composite-Unseen 42.50), 1,168.95 s/에피소드.
  - RoboTwin: Astra 성공률 행 없음. 시간만 1,078.8 s. 성공률 표에는 GPT-5.5 xhigh 62.4%(논문 Codex 58.0%와 다름), Opus-4.7 58.4%.
- Flash Mode(`usage/flash`): LLM 없이 기록된 계획을 재생하고, SAM3·Molmo2-8B 앵커로 좌표만 다시 잡는다.
  - LIBERO-PRO 800칸: Flash 581(72.63%), "Codex without reasoning" 500(62.50%), "Codex with high reasoning" 628(78.50%). 이 쪽에 Codex 모델명은 없다.
  - 계획 78개 / 과제 80개. goal_swap_t0과 10_swap_t9는 계획이 없어 0/10으로 셌다.

**결과 표(조건 포함)**
- **LIBERO 표준(Table 2)**
  - 조건: 4개 묶음 × 10과제 × 평가 seed 10(s1–s10) = 400. seed 0은 메모리 구축 전용.
  - Harness VLA(CC): Spatial 97.0 / Object 100.0 / Goal 94.0 / LIBERO-10 93.0 / Overall 96.0(384/400).
  - π_RLinf(pi05_libero130_fullshot SFT, 동결): 99.0 / 96.0 / 97.0 / 89.0 / 95.3.
  - AtomVLA 97.0, π0 94.2, NORA 79.5, OpenVLA 76.5.
- **LIBERO-Pro(Table 3)**
  - 조건: 8칸 × 10과제 × 10 seed = 800.

| 방법 | Spat-T | Spat-S | Obj-T | Obj-S | Goal-T | Goal-S | L10-T | L10-S | Overall |
|---|---|---|---|---|---|---|---|---|---|
| Harness VLA(CC) | 94 | 80 | 88 | 90 | 87 | 87 | 71 | 62 | 82.4 |
| Harness VLA(Codex) | 81 | 69 | 94 | 91 | 75 | 66 | 52 | 49 | 72.1 |
| π_RLinf | 42 | 59 | 71 | 78 | 45 | 42 | 49 | 14 | 50.0 |
| RATS(6칸만) | 31 | 29 | 63 | 61 | 36 | 43 | / | / | 43.8 |
| Cap-X(6칸만) | 14 | 12 | 18 | 22 | 17 | 26 | / | / | 18.2 |
| π0.5 | 1 | 20 | 1 | 17 | 2 | 38 | 1 | 8 | 11.0 |

  - AtomVLA 6.3, X-VLA 3.8, MolmoAct 1.5, π0 0.3, OpenVLA 0.0, NORA 0.0.
  - "+38.6pp" = CC 82.4 대 RATS 43.8(RATS는 보고된 6칸 평균).
- **RoboCasa365 Target50(Table 4)**
  - 조건: Atomic-Seen 18과제 × 10 seed = 180, Composite-Seen 16 × 5 = 80, Composite-Unseen 16 × 5 = 80, 합계 340. 참조 seed 1개로 부트스트랩.

| 방법 | Atomic-Seen | Composite-Seen | Composite-Unseen | Overall |
|---|---|---|---|---|
| RLDX-1(우리 프로토콜) | 60.0 | 21.3 | 5.0 | 30.0 |
| WorldDreamer | 66.3 | 26.7 | 9.0 | 35.3 |
| π0.5 | 39.6 | 7.1 | 1.2 | 16.9 |
| π0 | 34.6 | 6.1 | 1.1 | 14.8 |
| Harness(Codex) | 92.0 | 61.0 | 13.8 | 57.1 |
| Harness(CC) | 79.4 | 47.5 | 15.0 | 48.6 |

  - +27.1pp = Codex 57.1 대 RLDX-1 30.0.
- **RoboTwin C2R(Table 6)**
  - 조건: 50과제 × randomized seed 5 = 250. trace는 demo_clean의 전문가 검증 seed 1개에서 얻고, demo_randomized에서 평가. 탐색·미세조정 없음.
  - GR00T-N1.7 20.7, π0.5 47.9, StarVLA 10.6, LingBot-VLA(자체 post-train 뒤 동결) 50.4, Harness(Codex) 58.0, Harness(CC) 58.4.
- **Zero-shot LIBERO-Pro Goal(Table 5)**
  - 조건: Task Specific Memory도, 해당 Global Memory도 쓰지 않음. 과제당 10 seed. CaP-X와 과제별 비교.
  - Pos(S): Cap-X 평균 25.6(과제 0~9: 0, 4, 0, 36, 22, 60, 4, 2, 62, 66) / Harness(CC) 31.0(0, 10, 0, 20, 90, 0, 10, 80, 100, 0).
  - Task(T): Cap-X 16.8(0, 0, 10, 38, 12, 4, 34, 12, 40, 18) / Harness(CC) 79.0(10, 100, 90, 100, 20, 80, 90, 100, 100, 100).
  - 저자 해석: 메모리가 없으면 Goal-T는 zero-shot 79.0 대 few-shot 87.0으로 대부분 유지되고, Goal-S는 31.0 대 87.0으로 크게 떨어진다.
- **프리미티브 사용 통계(부록 F Table 18·19, CC)**

| 프리미티브 | LIBERO | RoboTwin | RoboCasa365 |
|---|---|---|---|
| move_to | 6263 (61.8%) | 685 (40.9%) | 3004 (38.7%) |
| move_pose | 203 (2.0%) | – | – |
| navigate_to | – | – | 701 (9.0%) |
| rotate_wrist | 44 (0.4%) | 1 (0.1%) | – |
| rotate_pitch | 58 (0.6%) | – | 66 (0.8%) |
| set_gripper | 1137 (11.2%) | 71 (4.2%) | 371 (4.8%) |
| release | 831 (8.2%) | 124 (7.4%) | 76 (1.0%) |
| move_base | – | – | 808 (10.4%) |
| vla_act | 1598 (15.8%) | 794 (47.4%) | 2746 (35.3%) |
| 합계 | 10134 | 1675 | 7772 |
| 분석형 합 | 84.2% | 52.6% | 64.7% |

**절제(ablation)**
- 모듈별(메모리 끔, staging 끔 등) 절제 표는 없다.
- 있는 것: (a) Table 5 zero-shot(메모리 없음) 대 few-shot, (b) Fig. 4 VLA 호출 상한 곡선(수치 없음), (c) 동결 VLA 단독 대비(π_RLinf 50.0 → 82.4).

**저자 한계(§5 원문)**
- "Our current framework is limited by an **open feedback loop between the high-level planner and low-level VLA**."
- 환경 보상·사람 선호로 함께 미세조정하지 않았다(GRPO 등은 향후 과제).
- 세밀한 이미지 캡션이 없어 복잡하고 긴 과제의 구조 추론이 제한된다.
- 향후: ASPIRE식 자동 스킬 발견과 결합.

### 1.2 우리 해석

**M6(스킬 카드·결정 지점·생성 스킬 (b))**
- **스킬 카드 필드 보강** [접목]: RPent 도구 명세는 사실상 MCP 스키마(name, description, input_schema)이고, 반환 dict에 `success`와 원자료 진단값(`peak_lift_m`, `min_gripper_opening`, `chunks_used`, `terminated`)을 함께 둔다. M6 스킬 출력(출구 술어 + 오류 코드)에 **원자료 진단 필드**를 필수로 추가할 것을 제안한다.
  - 근거 1: RPent 전역 메모리가 "`pi0_pick.success`=false여도 영상상 들고 있으면 계속"을 교훈으로 가질 만큼 스킬 불리언 하나는 틀린다.
  - 근거 2: 이것은 M7 "코드 술어가 정답, 스킬 자기 보고는 보조" 규칙의 원문 사례다.
- **stop 술어·예산을 인자로**: 원문 `vla_act{prompt, max_chunks, stop}`와 코드 `pi0_pick(lift_thresh 0.05, descent_thresh 0.10, gripper_closed_thresh 0.06, max_chunks 24)`. M6 §3 표의 "모든 스킬 단계에 stop·budget 인자"는 원문과 맞는다.
  - 다른 점: RPent는 **연속 수치 임계값을 플래너가 자유롭게** 준다. 우리는 이를 enum(보기 ID)으로 바꾼다. 예: `dp.chunk_budget ∈ {short(≤8), mid(12–16), long(24)}` — 값은 RPent 교훈의 수치에서 가져온 [가정].
- **typed 결정 지점 후보 목록**(원문 탐색 레버에서 도출): §2.2 원문 "staging orders, pre-contact poses, invocation timings for vla_act, and early-return termination thresholds" + 메모리 교훈의 레버. 후보:
  - `dp.stage_pose`(사전 자세: default_home / over_target / offset_rim)
  - `dp.invoke_now`(지금 스킬 호출 / 한 번 더 staging)
  - `dp.chunk_budget`
  - `dp.retry_prompt`(grasp-only / full-task — 교훈 "missed pick 뒤 full task 문장 금지")
  - `dp.grasp_verify`(스킬 불리언 / 영상 증거)
  - 모두 [접목]이다. Harness 원문은 typed 보기 없이 자유 JSON 인자를 쓴다.
- **"cannot invent"**: M6 §4.1 "Astra는 계약에 있는 스킬·보기·결정 지점 id만"의 원문 근거가 맞다(§2.3 원문 문장 확인).
- **생성 스킬 (b)와의 관계**: Harness VLA는 (b)의 반대편이다. 코드를 생성하지 않고 고정 어휘만 쓴다(§4 "our agentic planner does not synthesize executable code or new control programs"). 따라서 M6 §4.4 표의 (a)/(a') 행 근거로 쓰는 것이 맞고 (b) 근거로는 쓰지 않는다. 저자도 향후 과제로 ASPIRE식 "propose, validate, and admit a new reusable skill"을 적었다 → (b) + 검증 게이트(M6 §4.5)가 이 빈칸에 들어간다.

**M9(복구)**
- 원문 루프 = 동기 staging → attempt → observe → re-stage + re-invoke. 매 프리미티브 뒤 결과를 {progress, recoverable failure, unrecoverable failure}로 분류(부록 A). 이 3분류는 M7 판정(정상/WARN·FAIL/복구 불가 → L3)과 대응시킬 수 있다.
- M9 L1 "같은 스킬을 파라미터 바꿔 1회 재시도"의 원문 사례:
  - 전역 교훈: 빈 집기 → 재위치 파악·re-stage, full prompt 금지, max_chunks 12~16, 사전 위치 1~3 cm.
  - 평가 프롬프트: "if lift isn't reached within 8 chunks, RE-ISSUE pi0_pick rather than raising max_chunks".
- 원문은 이 선택을 LLM 플래너가 동기로 한다(로봇은 파일을 기다림). 우리는 코드 후보 + Jev `dp.critic_accept`로 멈추지 않고 한다.
- Fig. 7 사례: `move_to` 중 VLA가 실제로 잡지 못했음을 알아채고 돌아가 재시도. 운반 중 빈 집기 감지 = M9 "잡기 하위 단계로 되돌림" 구조의 또 다른 선행(Show-Harness 폭 규칙과 같은 계열).
- "Do not terminate from visual proximity alone. Check the benchmark success signal" → M7 완료 판정은 코드 T1 술어 기준이라는 규칙과 같다.

**M10(경험)**
- 가져올 형식 [접목]: 전역 leaf의 `applies_when`, `symptom` 목록, `evidence.cells`, `confidence`(cells ≥ 3이고 과제 ≥ 2면 verified, cells ≥ 2면 probable, 그 밖은 single-shot), **`Falsify`**(반증 조건).
  - `Falsify`는 M10 교훈 항목에 없는 필드다. 이력 기반 삭제(최소 n회 꺼낸 뒤 β 이하)와 별도로, "이 조건이 관측되면 폐기"를 교훈 작성 시점에 적게 하는 장치로 추가를 제안한다.
  - `confidence` 규칙은 M10의 (a)등급 센서 라벨 게이트와 결합한다. 예: Astra 주입은 probable 이상만.
- 다른 점:
  1. RPent 검색은 **플래너가 index·grep으로 스스로** 한다. 우리는 코드가 키 정확 일치로 0~2개를 고른다.
  2. RPent에는 효용 카운터·삭제가 없다. 병합은 증거 합산만 하고, 본문이 충돌하면 보관함에 넣는다.
  3. RPent 평가 프롬프트에는 seed-0 과제별 수치가 하드코딩돼 있다. 이는 M10의 "원시 궤적·좌표 주입 금지, 추상 교훈만"보다 훨씬 강한 과제 특화 주입이다.
- 경험 효과의 크기(원문 수치):
  - LIBERO-Pro Goal-S: 메모리 없음 31.0 대 메모리 87.0. Goal-T: 79.0 대 87.0(CC).
  - Flash(LLM 없이 기록 재생 + 앵커 재위치) 72.63% 대 Codex high 78.50% / no-reasoning 62.50%.
  - 해석: LIBERO-Pro T/S 성능의 상당 부분이 **과제별 기록 구조**에서 온다. E-M10에서 "과제별 trace 주입" 조건을 따로 두면 메모리 효과의 상한을 볼 수 있다([제안]).

**EVAL 기준 방법(범주 5·6) 원문 충실판**
- **B6c 원문판(LIBERO-PRO, 공개 수치 재현)**:
  - `rpent --robot libero --planner codex --model <GPT-6 Astra> --reasoning-effort low --libero-type pro --memory-profile hf`
  - π_RLinf = `RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT`, SAM3. 평가는 단일 시도(reset 없음), seed 1~10, 8칸 × 10과제.
  - 메모리는 HF 스냅샷 두 묶음(Long / 나머지 6칸). **max-turns·timeout 등 Astra 실행 설정은 리더보드에 없다** → 기본값(100턴, 1200 s)을 쓰고 표에 적는다.
  - 판본 점검: 칸 일부(예: Long-S, Goal-T)를 재실행.
  - EVAL §2.3 "어느 섭동 축인지 확인 필요" → **해소**: T(instruction) + S(swap) 8칸, env·lan·object 축 없음.
- **B6c-0(zero-shot 판)**: Table 5 조건(메모리 없음). 우리 시스템이 탐색 예산 없이 돌면 이쪽이 공정 비교다. 원문도 이 조건을 따로 냈다.
- **"Harness VLA에서 VLA를 우리 스킬로 바꾼" 조건**:
  - 이름: B6c-S 또는 B5d [우리 계획].
  - 구성: RPent의 고정 어휘 루프(동기 JSON REPL, `--max-turns` 100)를 그대로 두고, `vla_act` 자리에 우리 스킬(pick/place, 원문과 같은 stop·budget 인자)을 `add_primitive` 인터페이스로 등록한다. 분석형 프리미티브는 우리 `ee` 경계로 맞춘다. Global/Task 메모리는 우리 standard 장면 탐색으로 만든다(random 장면에서 만들지 않음).
  - 이 조건은 "결정 층 = 동기 LLM 플래너 + 자유 JSON" 대 "우리 = 비동기 Jev typed 결정 + 실패 시 Astra"를 **같은 스킬·같은 인식 위에서** 비교하게 해 준다.
  - RoboDojo는 RPent Feature Matrix에서 체크 표시 없이 "RoboDojo"만 적혀 있다. 이식은 우리가 해야 한다([가정]: 미구현).
  - 벽시계 트랙용 **B6c-S-wall**: 플래너가 생각하는 동안에도 시뮬이 진행하고 직전 명령을 유지한다. 원문은 에피소드당 412 s(Astra low, LIBERO-PRO) 동안 정지형이다.
- 정보 동등(EVAL §3.2 3번)과 충돌하는 점: RPent 평가 프롬프트의 "PROVEN LEVERS"는 seed-0 탐색 결과를 담은 과제별 정보다. 우리 시스템에 같은 정보를 주지 않으면 "입력 정보 다름" 각주가 필요하다.

**차별 문장 초안**
- "Harness VLA는 프리미티브 하나가 끝날 때마다 플래너가 결과 파일을 기다렸다가 다음 JSON 호출을 고르는 동기 REPL이며(부록 A 'The planner waits for these files before selecting the next primitive'), 저자 스스로 플래너와 하위 VLA 사이가 열린 고리라고 적었다(§5). VLA 실행 중에는 플래너가 정한 stop 술어와 청크 예산만 작동한다. 우리는 스킬 안 단계 경계마다 typed 결정 지점을 두고 Jev가 로봇을 멈추지 않은 채 겹쳐 답하며, Astra는 실패 신호가 날 때만 비동기로 부른다."
- "Harness VLA의 전역 메모리는 성공 규칙·실패 모델을 사람이 읽는 문서로 쌓고 플래너가 스스로 찾아 읽는다. 증거 셀 수로 신뢰도만 올리고 효용 추적·삭제는 없다(RPent `manager.py`). 우리는 센서 술어로 확정한 경험만 (스킬, 결정 지점) 키 정확 일치로 0~2개 주입하고, 재생·새 seed 비열화 게이트와 이력 기반 삭제를 둔다."
- 주의: "Astra를 쓰는 기존 연구"에 RPent Astra low 92.63%를 넣을 때는 반드시 "논문이 아니라 저장소 리더보드 값, 메모리 스냅샷 두 묶음, 에피소드당 평균 412 s 정지형"을 함께 적는다.

---

## 2. CaP-X (2603.22435) + capgym/cap-x

### 2.1 원문 사실

**서지**
- 저자: Letian(Max) Fu 외. NVIDIA, UC Berkeley, Stanford, CMU. 공동 지도 Ken Goldberg, Jim Fan.
- arXiv v2 본문에 "Keywords: Machine Learning, ICML", Impact Statements, 부록 K("clarifications… requested by reviewers during the discussion period")가 있다. 게재 학회 문구 자체는 본문에서 확인하지 못했다(M6 표 HIGH(ICML 2026)는 v3 조사값).

**구성(§1~2)**
- CaP-Gym: Gymnasium + REPL. 턴 = "the agent receives observations, generates a Python program, and the environment executes it to completion". 프로그램 하나가 여러 프리미티브를 부르고, 각 프리미티브는 시뮬/제어기를 여러 스텝 돌린다.
- 과제 수: 논문은 187(Robosuite 7 + LIBERO-PRO 130 + BEHAVIOR 50), README는 "39 tasks across Robosuite, LIBERO-PRO, and BEHAVIOR". 서로 다르다.
- 인식 프리미티브: SAM3(언어 분할), Molmo 2(포인팅), OpenCV, Open3D. 제어 프리미티브: IK/모션 플래너(PyRoki). stateless 서비스.

**API 추상화 단계(§3.1~3.2, Table 1, 부록 G)**
- **S1**: High-level + **Privileged**(참값 마스크·자세). 계획 상한 측정용.
- **S2**: High-level + Non-privileged(실제 인식, RGB-D). "the default setting for most prior work".
- **S3**: Low-level(`solve_ik()`, `sam3_text_prompt()` 등 각 패키지 API 그대로) + docstring **사용 예시 포함**.
- **S4**: S3과 같은 프리미티브에서 예시를 제거(시그니처·docstring만).
- **M1**: 다회. 매 턴 stdout·stderr 반환. 에이전트가 print를 넣어 상태를 스스로 들여다본다. M2~M4는 모두 이 트레이스를 유지.
- **M2**: 현재 RGB를 문맥에 넣음.
- **M3**: VDM(텍스트 시각 차분) + High-level.
- **M4**: VDM + Low-level + S3 사용 예시.
- 부록 G의 Low-level 목록(Robosuite Franka): `get_observation`, `segment_sam3_point_prompt`, `segment_sam3_text_prompt`, `point_prompt_molmo`, `get_oriented_bounding_box_from_3d_points`, `plan_grasp`(Contact-GraspNet 얇은 래퍼, 좌표 변환·TCP 오프셋은 호출자 책임), `solve_ik`, `move_to_joints`, `open_gripper`, `close_gripper`, 양팔용 `*_arm0/arm1`, `move_to_joints_both`.
- High-level 예(부록 E 코드): `get_object_pose(name, return_bbox_extent)`, `sample_grasp_pose(name)`, `goto_pose(pos, quat, z_approach)`.
- 실물 AgiBot G1 도구(부록 B.2): 위 목록 + `goto_pose`(사전 집기 오프셋·최대 힘 렌치), `query_vlm`(Gemini-3-Pro 전문가 VLM), `go_forward`(1 m), `turn_left/right_45_degrees`, `goto_planar_position`, `forward_kinematics`, 시각화 도구, `say_something`.
  - 원문: "3D rigid body transformation helpers… when not provided… almost always written by the models who make mistakes".
- 프로토콜: Zero-Shot Pass@1. 시도 안에서 다회 상호작용은 허용하지만 "the environment is never reset during the trial". 과제·tier당 100회. 모델 12개: Gemini-3-Pro, GPT o1, o4-mini, 5.1, 5.2, Claude Haiku 4.5, Opus 4.5, GPT-OSS-20B/120B, Qwen3 235B, Qwen-2.5-Coder-7B-Instruct, Kimi K2 Instruct, DeepSeek-V3.1-Terminus.
- 핵심 7과제: Cube Lift, Cube Stack, Spill Wipe, Peg Insertion, Cube Re-stack, Two-Arm Lift, Two-Arm Handover.

**높은 단계 프리미티브를 빼면(Takeaway 2, Fig. 3·4)**
- "monotonic increase in task success as primitive abstraction increases" — S4 → S1로 갈수록 성공률이 오른다. 반대로 사람이 설계한 추상을 빼면 떨어진다.
- 단계별 수치는 그림에만 있고 본문 표에는 없다.
- S3/S4 저하는 "only in part" 코드 정확성(컴파일 성공률, Fig. 4) 때문이다.
- 대가: 높은 단계 API는 "generality ceiling"을 두고 저수준 추론 실패를 가린다. 저수준은 계층적 인식 폴백 같은 표현이 가능하다(F.2.2).
- 저자 권고: "generalist embodied coding agents be evaluated primarily on primitive-level performance".
- 사람 전문가 기준(부록 K.1): 저자 7명(로봇 프로그래밍 2년 이상)이 tier마다 같은 API로 스크립트를 쓰고 반복 수정해 **단일 턴 평균 88.5%**.
  - 노력: 단순 집기·놓기는 1일 미만, Peg Insertion·Two-Arm Handover는 과제당 2~3주.

**다회 되먹임(Takeaway 3, Fig. 5·6)**
- M1(stdout/stderr)은 거의 모든 모델에서 향상.
- **M2(원시 RGB 삽입)는 M1보다 오히려 저하**. 가설은 "cross-modal alignment gap".
- M3(VDM)은 M1·M2보다 모든 과제에서 향상.
- M4(저수준 + 다회 + VDM)는 S2(높은 단계 단일 턴)를 넘고 M3와 동등(Gemini-3-Pro, Fig. 6). 수치는 그림만.

**VDM(§3.2 M3, 부록 K.3, 코드 `capx/envs/trial.py`)**
- 논문 VLM = Gemini-3-Pro(K.3: 가장 강한 VLM으로 상한을 보려는 선택. MMMU-Pro 81%, Video-MMMU 87.6%). 코드 기본값 `visual_differencing_model="google/gemini-3.1-pro-preview"`.
- 첫 턴 출력(코드 원문): 시스템 "describes the initial state of the environment with the goal of the task in mind… objective information and no assumptions. Do *NOT* write any code." + 과제 문장 + 주 카메라(+ 선택적으로 손목) 이미지.
- 이후 턴(코드 원문): "Describe the difference between the current state of the environment and the previous state… with the goal of the task in mind **and whether the task has been completed**…". 입력은 직전·현재 주 카메라(+ 손목) 두 장.
- 영상판 옵션 `use_video_differencing`도 있다(턴 실행 영상을 VDM에 전달).
- 쓰임: VDM 텍스트가 코딩 에이전트 관측 문맥에 들어가고, 에이전트가 **REGENERATE + 코드** 또는 **FINISH**를 낸다(yaml `multi_turn_prompt`).
- K.3: "model-agnostic by design". 백본 절제는 하지 않았다.

**스킬 합성 라이브러리(§4 항목 2, 부록 H.1, `compile_skill_library.py`)**
- 원문 절차: "collect all successful S3-tier rollouts pooled across all 12 models and 7 Robosuite tasks… extract function definitions via regular-expression matching, and prompt Gemini-3-Pro to identify frequently recurring, task-agnostic logic. This yields a compact library of **9 verified, task-agnostic primitives**." 단일 패스이고, 원리상 반복 갱신이 가능하다고 적었다. 시도 사이에 유지된다(persist across trials).
- 9개(H.1): `rotation_matrix_to_quaternion`, `decompose_transform`, `depth_to_point_cloud`, `mask_to_world_points`, `pixel_to_world_point`, `transform_points`, `interpolate_segment`, `normalize_vector`, `select_top_down_grasp`. 대부분 **좌표·기하 유틸리티**이고, 조작 스킬은 `select_top_down_grasp` 하나 정도다.
- 코드의 필터:
  - `min_occurrences=2`
  - 3줄 미만 제외
  - 이름이 과제 특화 패턴(`cube`, `stack`, `lift`, `wipe`, `spill`, `place_.*_on`, `pick_.*_up`, `grab_the`, `move_to_goal`)이면 제외
  - `_reduced_api` 실험만 대상
- 그 뒤 LLM(`google/gemini-3.1-pro-preview`) 큐레이션 프롬프트: "Identify the MOST USEFUL and REUSABLE… Exclude task-specific or overly narrow functions… Note any functions that appear frequently". 산출물은 `outputs/skill_library.txt`.
- **컴파일 스크립트 안에 자동 테스트·실행 검증 단계는 없다.** 논문의 "verified"가 무엇을 뜻하는지(성공 롤아웃 출처라는 뜻인지, 사람 확인인지)는 원문에서 확인하지 못했다.
- 저장 형식은 파이썬 함수 정의(docstring·타입 힌트). 사전·사후조건 필드는 없다.

**병렬 추론(§4 항목 3, 부록 H.2~H.5)**
- 턴마다 후보 9개를 만든다.
  - 단일 모델: Gemini-3-Pro를 온도 0.1~0.9로 9회.
  - 다중 모델: Gemini-3-Pro, Claude-Opus-4.5, GPT-5.2 각 3회(온도 0.1 / 0.5 / 0.9).
- 중앙 에이전트가 합성한다(규칙: "assume no candidate is fully correct", "Prefer explicit checks").
- 다회 턴에서는 REGENERATE/FINISH 투표 수를 합성 프롬프트에 넣는다.
- H.5: 앙상블은 평균 턴 수를 줄인다. 선제적 폴백이 늘고 사후 수리가 줄었다.
- **H.4 Table 5**(디버깅·검증 강화 프롬프트):

| 조건 | Cube Lift | Cube Stack | Spill Wipe | Peg Insert | Cube Restack | Two Arm Lift | Two Arm Handover | 평균 |
|---|---|---|---|---|---|---|---|---|
| 3M | 97 | 98 | 100 | 0 | 89 | 74 | 20 | 68.29 |
| 3M + debug | 94 | 100 | 98 | 0 | 88 | 66 | 12 | 65.43 |

  - "did not empirically improve success rate".

**CaP-Agent0 결과**
- Fig. 8(수치는 그림만): M4 + SL + 1M/3M 절제에서 단일 턴 저수준보다 크게 향상. 7과제 중 4과제에서 사람 단일 턴 코드와 같거나 높다.
- **LIBERO-PRO(Table 2, 부록 J Table 6~8)**
  - 조건: 30과제(object·goal·spatial × 10), Pos(swap)와 Task(instruction) 두 섭동, **과제당 50회**. libero-10 없음.
  - 평균(분율):

| 방법 | object Pos | object Task | goal Pos | goal Task | spatial Pos | spatial Task |
|---|---|---|---|---|---|---|
| CaP-Agent0 | 0.22(표 J 0.218) | 0.18(0.182) | 0.26(0.256) | 0.17(0.168) | 0.12(0.118) | 0.14 |
| π0.5 | 0.17 | 0.01 | 0.38 | 0.00 | 0.20 | 0.01 |
| π0 | 0 | 0 | 0 | 0 | 0 | 0 |
| OpenVLA | 0 | 0 | 0 | 0 | 0 | 0 |

  - "12~26%"의 출처가 이 표다. Harness VLA Table 3의 Cap-X 행(Spat-T 14, Spat-S 12, Obj-T 18, Obj-S 22, Goal-T 17, Goal-S 26, overall 18.2)은 이 값을 옮긴 것이다(50회 기준 보고치이고 Harness의 10 seed 프로토콜과 다르다).
  - 이 실행의 CaP-Agent0 구성(단일/다중 모델, 모델 판본)은 원문에서 찾지 못했다.
  - 저자 실패 분석(부록 J): SAM3가 "alphabet soup can"을 "tomato sauce can"으로 분할한다. 카메라가 위에서 내려다보지 않아 비스듬한 집기 + **충돌 무시 모션 플래닝**으로 다른 물체를 쓰러뜨린다.
- **BEHAVIOR(Table 3, 과제당 25회, R1Pro)**

| 과제 | 항법: Human | 항법: S3 | 항법: CaP-Agent0 | 과제: Human | 과제: S3 | 과제: CaP-Agent0 |
|---|---|---|---|---|---|---|
| Pick up Radio | 88% | 72% | 80% | 36% | 24% | 56% |
| Pick up Soda Can | 80% | 52% | 84% | 72% | 32% | 72% |

- 실물: Franka Panda, AgiBot G1에서 zero-shot 시연(바늘 찾기, 기계적 탐색, 수식 블록, 사람 되먹임, 쌓기, 엘리베이터). 성공률 표는 없다.
- **시간(부록 K.2, Gemini-3-Pro, cube stack, N=20)**

| tier | LLM 코드 생성 | 시도 전체 |
|---|---|---|
| S1 | 6.8 s | 12.9 s |
| S2 | 9.6 s | 20.0 s |
| S3 | 23.8 s | 28.4 s |
| M1 | 20.1 s | 60.8 s |
| M3 | 15.8 s | 113.6 s |

  - 로보수트 과제 한 시도 약 2분(K.1).

**CaP-RL(§5, Table 4)**
- 설정: Qwen2.5-Coder-7B-Instruct에 GRPO. **S1(특권 상태) API로 학습**(인식 잡음으로 인한 보상 모호성을 피하려고), 과제당 50 iteration, S2에서 평가.

| 방법 | 시뮬 Cube Lift | 시뮬 Cube Stack | 시뮬 Spill Wipe | 실물 Cube Lift | 실물 Cube Stack |
|---|---|---|---|---|---|
| 사람 전문가 | 93 | 73 | 100 | 92 | 84 |
| 기본 모델 | 25 | 4 | 30 | 24 | 12 |
| CaP-RL | 80 | 44 | 93 | 84 | 76 |

- 시뮬 N=100, 실물 Franka N=25.

**공개 코드 기본값(`launch.py`, `docs/configuration.md`)**
- `model="google/gemini-3.1-pro-preview"`, `temperature=1.0`, `max_tokens=20480`, `reasoning_effort="medium"`(선택지 minimal / low / medium / high).
- 플래그: `use_img_differencing`, `use_video_differencing`, `use_wrist_camera`, `use_parallel_ensemble`, `use_multimodel`, `use_oracle_code`(사람 참조 해답).
- LLM은 OpenRouter 프록시를 거친다(`127.0.0.1:8110`). LIBERO는 별도 venv(py3.12, robosuite 1.4.0 충돌).

**한계(부록 A Future Works)**
- 원문: "brittle for contact-rich behaviors that require tight visual servoing and continuous feedback (e.g., insertion or pouring). One promising direction is **hybrid CaP-VLA policies**, in which a coding agent manages high-level task logic and recovery while deferring low-level execution to VLA policies."
- 이 외: 충돌 회피 최적화 제어 프리미티브 필요(현재는 IK 해를 관절 공간에서 보간), 능동·상호작용 인식 확장. Peg Insertion은 3M에서 0%(H.4).

### 2.2 우리 해석

**M6**
- **추상 수준 = 우리 스킬 계약의 위치**: CaP-X의 가장 강한 결과는 "사람이 만든 높은 단계 API일수록 성공률↑, 빼면↓(단조)"와 "저수준은 다회 + VDM으로 높은 단계 다회(M3)와 동등까지"다.
  - (b) 생성 스킬이 **무엇 위에서 생성하는가**가 핵심 변수라는 뜻이다. E-M6-3에 "생성 기반 API 단계"를 축으로 추가할 것을 제안한다: 우리 스킬 다발 위(높은 단계, S2/M3 대응) 대 M1 술어 + IK만(저수준, S3/M4 대응).
  - 원문 권고("primitive-level performance로 평가")와 우리 설계("접촉 구간은 스킬")가 방향이 달라, 이 비교가 필요하다.
- **생성 스킬 라이브러리 추출 절차 [원문 → 접목]**:
  - 원문 = 성공 롤아웃 코드 → 정규식으로 함수 추출 → 2회 이상 등장 + 이름 필터 → LLM 큐레이션. 결과는 기하 유틸 9개이고 사전·사후조건이 없으며 자동 검증 단계도 없다.
  - 우리 (b): 같은 추출 파이프라인을 쓰되, 산출 함수에 계약(entry/exit/effect)과 typed hole(`jev_choice(dp_id, Enum)`)을 붙이고 M6 §4.5 사후 검사 게이트를 통과한 것만 등록한다.
  - "verified"의 뜻이 원문에서 불분명하므로, 우리는 검증을 **실행 기반**(재생 + 새 seed 비열화, M10 게이트와 같은 장치)으로 정의한다.
- **typed 결정 지점**: CaP-X는 자유 코드이고, 결정은 REGENERATE/FINISH 이진뿐이다(다회 턴). 우리 typed 결정 지점과 가장 대비되는 설계다. CaP-X의 "FINISH 판정"은 우리 M7 완료 판정(코드 T1 술어)과 대응한다. VDM의 "whether the task has been completed"는 LLM 판정이므로 원문 자체가 거짓 완료 위험을 H.4에서 실패 사례로 지목했다.

**M9**
- CaP-X 복구 = 다음 턴에 전체 프로그램 재생성(REGENERATE). 부분 재개 지점 개념이 없다. F.2.1 사례는 "목표 조건(z_object > z_table) 미충족을 다음 턴에 확인하고 복구 분기를 합성"이다. M9 체크포인트 재개(가장 늦은 재개 가능 k)와 다른 거친 단위다.
- H.4 반대 증거: 검증·디버깅을 강하게 시키는 프롬프트가 68.29 → 65.43으로 오히려 약간 나빴다. M9의 "반성 유지"(D3 잠정)에 반대 증거로 추가한다. 조건은 7과제 × 100회, 3M 앙상블.
- M2(원시 이미지) < M1 < M3(텍스트 차분): Astra 재계획 호출 입력 설계(M8)에 "이미지 그대로 대 텍스트 차분 요약"을 비교 조건으로 넣을 근거다. 단 Astra는 이미지 직접 입력이 강점이라 결과가 다를 수 있다([가정]).

**M10**
- 원문 "persistent across trials"는 스킬 코드 라이브러리뿐이다. 실패 교훈 저장은 없다. M10의 교훈 저장소·규칙표는 CaP-X와 겹치지 않는다. SkillsBench 경고(자기 생성 스킬 −8.1~−11.5pp)와 CaP-X의 SL 향상(Fig. 8, 수치는 그림)은 조건이 다르다. CaP-X는 여러 모델·과제의 **성공** 롤아웃에서 추출하고, SkillsBench는 사전 생성 팩만 쓴다. M6 §6에 함께 적는다.

**EVAL 범주 5 원문 충실판**
- **B5a(LIBERO-PRO, 공개 코드)**:
  - `capx/envs/launch.py --config-path env_configs/libero/...` + `use_img_differencing` + `use_parallel_ensemble` + `use_multimodel`.
  - 3M = Gemini-3-Pro, Claude-Opus-4.5, GPT-5.2 각 3회, 온도 0.1/0.5/0.9. VDM = Gemini-3-Pro. 스킬 라이브러리 9개. 과제당 50회. object·goal·spatial × Pos/Task 30과제.
  - 원문 LIBERO-PRO 실행 구성이 명시되지 않았으므로 "CaP-Agent0 전체 구성 = 우리 가정"으로 표기한다.
  - 공개 수치(0.12~0.26)와 대조해 판본 변동을 점검한다. 모델 판본은 코드 기본값(gemini-3.1-pro-preview)과 논문(Gemini-3-Pro)이 다르다.
- **B5b(RoboDojo 재구현, "CaP-X식")**:
  - Astra가 우리 스킬 API 위에서 파이썬을 생성한다. 턴마다 stdout/stderr + VDM 텍스트(Astra가 VDM 역할도 할지, 별도 VLM을 쓸지는 [결정 필요]) → REGENERATE/FINISH.
  - 두 판: **B5b-H**(우리 스킬 = 높은 단계, M3 대응) / **B5b-L**(술어 등록부 + IK·그리퍼만, M4 대응).
  - 스킬 라이브러리는 standard 장면 성공 롤아웃에서 원문 스크립트 규칙(min_occurrences 2, 이름 필터)으로 만든다.
  - 앙상블 9후보는 Astra 호출 수를 9배로 늘리므로, 호출 예산 맞춤(EVAL §3.2 4번)을 위해 앙상블 끔/켬을 따로 보고한다.
  - reset 없는 Pass@1. Astra effort는 공정 조건대로 high. 원문 코드 기본값은 medium이므로 재현용 행을 따로 둔다.
- 정지형 여부: CaP-X도 턴마다 코드 생성(6.8~23.8 s) 동안 로봇이 멈춘다(K.2의 "Avg Trial Time"에 포함). 벽시계 트랙에서는 B5b-wall(생성 중 직전 명령 유지)을 따로 둘 수 있다.

**차별 문장 초안**
- "CaP-X의 한 턴은 생성한 프로그램 한 편을 끝까지 실행한 뒤, stdout/stderr와 VLM 시각 차분 텍스트를 보고 프로그램 전체를 다시 생성할지(REGENERATE) 끝낼지(FINISH)를 정한다(§2, §3.2). 성공 롤아웃에서 뽑은 스킬 라이브러리는 사전·사후조건이 없는 기하 유틸리티 9개다(부록 H.1). 우리는 생성 스킬에 진입·출구·효과 계약과 typed 결정 지점을 붙여 실행 중 결정 지점 단위로 고르고, 실패하면 전체 재생성이 아니라 사전조건이 참인 가장 늦은 체크포인트에서 재개한다."
- "CaP-X는 접촉이 많은 과제(삽입·붓기)에서 코드 제어가 약하다고 적고 코딩 에이전트 + VLA 혼합을 향후 과제로 남겼다(부록 A). Harness VLA가 그 혼합을 동기 루프로 구현했다. 우리는 같은 분업을 비동기 typed 결정으로 한다."

---

## 3. 현재 문서와의 불일치·정정 제안

1. **EVAL §2.3**: "RPent Astra low 92.63% (741/800) — 어느 섭동 축인지는 문서 확인 필요" → 해소.
   - 축: Task(T) + Swap(S) × Spatial/Object/Goal/Long 8칸, seed 1~10.
   - 메모리: 스냅샷 두 묶음(Long 157/200 + 나머지 584/600).
   - 출처: 논문이 아니라 RPent 리더보드.
2. **EVAL B6c**: "RPent Astra를 LIBERO-PRO에서(공개 수치 + 코드)" → 논문 본문 플래너는 Codex(리더보드상 GPT-5.5 xhigh)와 Claude Code(Opus-4.7 max)다. Astra는 저장소 리더보드 행으로만 있다. B6c 표기에 "논문 밖 리더보드 값"을 적는다.
3. **M6 §2.1 Harness VLA 행**: "`vla_act{prompt, max_chunks, stop 술어}`"는 논문과 맞다. 공개 LIBERO 코드는 `pi0_pick`/`pi0_doubled`이고 stop은 수치 임계 인자(lift/descent/gripper thresh)라는 점을 덧붙인다.
4. **M6 §2.1 CaP-X 행**: "성공 롤아웃에서 스킬 9개 추출"은 맞다. "9개는 대부분 기하 유틸리티, 자동 검증 단계 없음(스크립트 기준)"을 추가한다.
5. **초록 수치**: Harness VLA RoboCasa365 +27.1pp(HTML v4 본문) 대 +25.4pp(abs 페이지 초록). 인용할 때는 본문 Table 4 기준 57.1 − 30.0 = 27.1을 쓰고 불일치를 병기한다.
6. **M9 §6 "반성 유지" 반대 증거**에 CaP-X H.4(검증 강화 프롬프트 68.29 → 65.43)를 추가한다.

## 4. 확인 못 한 것
- Harness VLA:
  - Fig. 4(VLA 호출 상한 곡선)와 Fig. 6(완료 귀속 비율)의 점별 값.
  - 평가 단계 "significantly shortened" 스텝 예산의 수치.
  - 플래너가 생각하는 동안 시뮬이 멈춘다는 명시 문장(구조상 정지형으로 추론).
  - 논문 본문의 모델 판본과 effort(논문에 없음. 리더보드에서만 확인).
- RPent:
  - Astra low 실행의 max-turns·timeout·max-episode-steps.
  - 리더보드 이름 불일치(GPT-5.5 xhigh 대 GPT-5.6 Sol xhigh).
  - RoboTwin 성공률 불일치(리더보드 Codex 62.4 대 논문 58.0).
  - Flash 문서 "Codex with high reasoning 78.50%"의 모델명.
- CaP-X:
  - Fig. 1·3·5·6·8(tier별·모델별 성공률)의 수치.
  - LIBERO-PRO 실행 구성(단일/다중 모델, VDM 사용 여부).
  - "9 verified"의 검증 뜻.
  - 다회 턴 최대 턴 수.
  - README 39과제 대 논문 187과제 차이의 이유.
  - 게재 학회 문구(ICML은 템플릿 흔적만 확인).
