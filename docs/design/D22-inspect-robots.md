# D22 Robocurve Inspect Robots 평가 하네스 조사 (user-log 40)

저장 2026-09-24 07:46 UTC. 조사 에이전트 보고 전문. 메인 재확인: README "If you know Inspect AI, this is that for robotics." / plans/0001 "no wall-clock pacing of its own"(동기 루프) / MIT / GitHub API 600★·생성 2026-06-26 / Astra 보고서 "medium thinking effort, 20-LLM-call budget, 25% speed cap"·"Grading was operator-judged with the model known, so scores are open to unconscious bias." — 일치. 19/20 수치는 JS 렌더라 메인이 원문에서 읽지 못함 [미확인].

## 결론
사용자가 말한 "인스펙트 로봇스"는 **Robocurve의 Inspect Robots**(https://github.com/robocurve/inspect-robots)로 확정했습니다. 이름이 비슷한 저장소는 모두 이 저장소의 포크입니다(kiwicampus, breken-ai, jav359003 등 설명문이 같음). arXiv를 이 이름·StationeryBench·RoboHarm·robocurve로 검색했지만 나온 것이 없습니다.

한 줄 평가: **LLM(Astra 포함)과 VLA를 로봇 과제에서 돌리는 평가 하네스이고, 우리 기여(빠른 typed 결정, M4 확정 규칙, 실패가 불러내는 비동기 Astra)와는 겹치지 않습니다.** 논문 주 평가(RoboDojo)의 틀로는 맞지 않습니다. 쓸 만한 곳은 관련 연구 인용과 E-real의 범주 1 기준선 후보 정도입니다.

## 1. 정체
- **저장소:** robocurve/inspect-robots, MIT.
  - 생성 2026-06-26, 마지막 push 2026-09-23.
  - **600★ / 67 포크**, 열린 이슈 65개.
  - 커밋 515개, 릴리스 v0.59.0(2026-09-22)까지 매주 나옴.
  - 기여 커밋은 한 사람(jeqcho)이 355/515로 대부분을 냄.
- **소유 조직:** Robocurve.
  - 조직 설명: "We measure and report frontier robotics capabilities to the public."
  - 2026-06-25에 만들어짐. YC 지원, 시드 $10M(2026-09-14 발표, https://robocurve.org/blog/seed-raise/).
- **UK AISI Inspect와의 관계:** 코드를 파생한 것은 아니고 구조만 본뜬 것입니다. README: "If you know [Inspect AI](https://inspect.aisi.org.uk/), this is that for robotics." 대응 관계는 Model→Policy+Embodiment, Sample→Scene, Solver→Controller, eval()→EvalLog입니다.
- **딸린 저장소(모두 별 적음):**
  - worldevals 8★ (벤치 목록)
  - stationerybench 5★
  - roboharm 6★
  - clapboardbench 3★
- **논문:** 없음. CITATION.cff는 `@software` 형식입니다.
- **HF 좋아요:** 해당 없음.
- **언론 보도:** RuntimeWire(https://runtimewire.com/article/robocurve-unveils-inspect-robots-free-framework-to-benchmark-ai-driven-robots), The Information, NBC(RoboHarm 관련, robocurve.org 링크 기준).

## 2. 무엇을 하나
**설계 원칙.** README 원문 인용: "Define a robotics benchmark once, then run any policy (LLM agent, VLA) against any compatible embodiment (a real arm or humanoid, or a simulator) with auditable logs (grader scores, LLM transcript, full config) and first-class Rerun visualization."
- 실물 우선. 원문: "human-in-the-loop reset, no privileged success oracle, wall-clock control rate"
- 코어는 NumPy만 의존합니다.

**정책 쪽(플러그인).**
- **`agent`: LLM을 도구 호출로 연결.**
  - 제공자: `anthropic/*`, `openai/*`, `google/*`, xai, groq, mistral, deepseek, Tinker, OpenRouter.
  - 연결 방식: chat / responses / messages / gemini-live / interactions.
  - 도구: `move_joints` / `move_to`(절대 자세), `move_by`(변위), `take_pic`, `done` / `give_up`(hindsight 인자 필수).
  - 이동 호출마다 `note`가 필수이고, 원문대로 "one approver-checked motion chunk per call"입니다.
  - 안전 장치: 기본 속도 `max_speed_frac=0.1`, 호출당 재생 상한 10 s, 그리고 `pre_check` 콜백(충돌 검사 등이 거부 사유를 LLM에게 돌려줌).
- **`capx`:** CaP-X식 코드 생성 정책. SAM3, Contact-GraspNet, Pyroki IK 서버를 따로 띄워야 합니다.
- **`xpolicylab`:** XPolicyLab 웹소켓 프로토콜로 VLA 40종 이상(π0/π0.5, GR00T, OpenVLA-OFT 등)을 연결합니다.
- **기타:** `voice`(운영자 음성 피드백), `prior_learnings`(실패 로그 요약을 다음 실행에 주입).

**몸체 쪽(embodiment).**
- 실물: YAM 양팔, Franka, AgiBot A2, Unitree G1, SO-100/101, WidowX, 그리고 **ROS 1/2 아무 팔(rosbridge, joint_pos)**.
- 시뮬: **Isaac Lab**(기본은 Franka 7자유도 joint_pos, 생성자 훅으로 매핑)과 CubePick 모의 세계.
- **RoboDojo, LIBERO, ManiSkill 몸체는 없습니다.**
  - ManiSkill은 문서에 플러그인 예시로만 나옵니다.
  - xpolicylab 계획서 원문: "RoboDojo embeds the same protocol on its eval side". 즉 Inspect Robots와 RoboDojo는 둘 다 환경 쪽 클라이언트라서 그대로 이어 붙일 수 없습니다.

**루프 구조: 동기(blocking)입니다.** foundation 설계 문서의 의사코드는 `chunk = controller.infer(policy, obs)`로 추론한 뒤 청크를 실행합니다. 원문: "The rollout applies **no wall-clock pacing of its own**; an embodiment that needs real-time cadence paces itself inside `step()`" (plans/0001-foundation-design.md). 시뮬에서는 LLM이 생각하는 동안 세계가 멈춥니다. agent README도 "step-count constructs, not wall-clock guarantees"라고 적습니다. 비동기 상위 호출은 지원하지 않습니다.

**채점과 재현성.**
- 채점기: `success_at_end`, `episode_length`, 거리 기반, `operator_scorer`(사람 판정), VLM 채점기, epochs와 `pass_at_k` 축약.
- 채점기는 기록된 궤적만 읽으므로 로그에서 다시 채점할 수 있습니다.
- `EvalLog`: 불변, 스키마 판본 있음, 설정·git 리비전·패키지 판본을 기록합니다.
- 시드: `seed=None`이어도 뽑은 시드를 기록합니다.
- Rerun `.rrd` 기록, HTML 보고서, 에피소드 transcript를 남깁니다.

**Astra 지원.** 명시된 예시는 없지만 `openai/*` 제공자와 responses 연결로 돌리고 있습니다. Robocurve가 직접 GPT-6 Astra 보고서를 냈습니다.

## 3. Astra 관련 결과 (Robocurve 블로그, 원문 인용)
**GPT-6 Astra 보고서 (https://openai.robocurve.org/gpt-6-astra/)**
- 설정 원문: YAM 양팔, `move_to` EEF, 카메라 3대 + 고유수용, "medium thinking effort, 20-LLM-call budget, 25% speed cap".
- 결과 (각 20회):

| 과제 | Astra | Fable 5.1 | Fable 5 |
|---|---|---|---|
| Bowl | 19/20 | 8/20 | 1/20 |
| Puzzle | 2/20 | 2/20 | 0/20 |

- 비용·시간: Bowl에서 Astra $0.94 / 2.5분, Fable 5.1 $2.12 / 6.8분.
- 단서 원문:
  - "Grading was operator-judged with the model known, so scores are open to unconscious bias."
  - "Astra's trials were run two days after the Fable trials, and not interleaved with them."
  - "the bowl comparison is not [on the same rig]"

**StationeryBench (https://openai.robocurve.org/stationerybench/)**
- 원문: "Astra completed 7 of 100 trials and MolmoAct2 completed none. Mean progress scores were 46 and 12 out of 100."
- 설정: Astra는 "medium effort, 20-LLM-call budget, 25% speed cap, 900-step cap, eef_pos interface", 입력 프레임 224×224. 채점은 사람이 마일스톤 4개(25점씩)로 매겼습니다.
- 단서: 위와 같은 사람 채점 편향 문장, 그리고 "In 47 of 100 MolmoAct2 trials, the arms never left the start pose".

**RoboHarm (robocurve.org 요약문)**
- 원문: "Across 300 trials on five harmful instructions, GPT-6 Astra attempted harm 1.2× as often as Fable 5.1 and succeeded 7.3× as often as MolmoAct2."

## 4. 신뢰도 등급
- **도구(소프트웨어)로서는 MED.**
  - 강점: 600★ / 3개월, YC 지원 조직, MIT, CI 커버리지 100%, 릴리스가 잦음.
  - 약점: 논문 없음, 실사용자 대부분이 제작사 자신, API가 alpha 단계("pin a version").
- **근거(수치) 출처로서는 LOW.**
  - 동료 심사가 없고, 과제당 n=20입니다.
  - 모델을 알고 사람이 채점했고, 조건을 섞어 돌리지 않았고, 장비가 다릅니다.
  - user-log 14 기준에 따라 Astra 실물 성능의 근거로 본문에 쓰지 않는 것이 맞습니다.

## 5. 우리 설계와의 관계 (SUMMARY §0, 00-interfaces §24·§31–§39, EVAL §3.1·§3.2 기준)
**선행 겹침: 없음.**
- 이 하네스의 LLM 정책은 "관측 → LLM 한 번 → 동작 청크 하나"를 반복하는 동기 루프입니다.
- 없는 것: 빠른 typed 선택기(Jev), 겹침 호출 합의·확정(M4), 실패 판정이 불러내는 비동기 Astra(M8), 같은 인식 비교.
- 부분 유사점(인용 한 줄로 충분):
  - `hindsight` / `prior_learnings`: 텍스트 교훈을 다음 실행에 주입합니다. M10과 비슷하지만 센서 술어 검증은 없습니다.
  - `pre_check`: 동작을 거부하고 사유를 LLM에 돌려줍니다. 코드 검사를 LLM 피드백으로 쓴다는 점이 비슷합니다.
- 결론: 00 §24의 C1·C2 판단을 바꿀 필요는 없습니다.

**기준선 후보.**
- `agent` + Astra는 사실상 **범주 1 "Astra만"**(B1a의 실물판: 이미지 직접, 절대 EEF 도구 호출, 동기)에 해당합니다.
  - E-real(AI Worker FFW-SG2, ROS 2 Jazzy)에서는 `ros` 몸체로 붙일 수 있을 가능성이 있습니다.
  - 다만 ROS 몸체는 joint_pos만 지원합니다. 그래서 `move_to`가 아니라 `move_joints`가 되어 StationeryBench 구성(eef_pos)과 같지 않습니다.
  - 머리·리프트 축, rosbridge 호환은 [미확인]입니다.
  - 충실판 구성으로 적을 값: medium, 20호출 예산, 25% 속도 상한, 카메라 3대 224×224. 행동 공간은 "우리 가정"으로 표기합니다.
- `capx`는 범주 5 B5a와 같은 계열입니다. 하지만 SAM3·Contact-GraspNet·Pyroki 서버가 필요해 부담이 크고, 이미 B5a는 CaP-X 공개 코드로 계획돼 있어 중복입니다.

**도구로서.**
- **RoboDojo 주 평가: 부적합.**
  1. RoboDojo 몸체가 없습니다(직접 작성해야 함).
  2. 시뮬이 LLM을 기다리는 동기 루프라서 B6b-wall이나 우리 비동기 Astra의 벽시계 조건을 표현할 수 없습니다.
  3. RoboDojo는 이미 자체 평가 루프와 공개 칸별 자료(N1)를 쓰므로 틀을 바꾸면 공개 수치와 같은 기준이 깨집니다.
- **우리 시스템을 Policy로 감싸기: 어색함.** 우리 스택은 자체 100 Hz 제어와 비동기 스레드를 갖고 있어서, 하네스가 `step()` 루프를 소유하는 구조와 충돌합니다.
- **E-real의 기록·재현성 도구: 선택적으로 가치 있음.** `EvalLog` 스키마, Rerun 기록, 운영자 판정 채점기, 시드 기록, HTML 보고서가 해당됩니다. 의존성을 넣기보다 로그 필드 설계(설정·git 리비전·판본·transcript·사람 판정 출처)를 참고하는 정도를 권합니다.

## 6. 권고
1. **관련 연구로 한 줄 인용(software):** "LLM/VLA 공용 로봇 평가 하네스, 동기 도구 호출 루프". 우리와의 차이는 비정지 실행 + 실패 기반 비동기 Astra + typed 빠른 결정입니다.
2. **Astra 실물 수치(19/20, 7/100)는 근거로 쓰지 않습니다.** LOW 등급이고 사람 채점 편향이 있습니다. 동기 부여 각주 이상은 권하지 않습니다.
3. **주 평가(RoboDojo)에는 쓰지 않습니다.** 이유는 5절의 1~3입니다.
4. **선택 사항(사용자 결정):** E-real에 범주 1 기준선 "B1a-real = Inspect Robots `agent` + Astra"를 넣을지 정해야 합니다. 넣으려면 rosbridge·AI Worker 관절 매핑을 먼저 짧게 점검해야 합니다.
5. **CaP-X 플러그인은 무시합니다.** B5a 계획과 중복입니다.

## 확인 경로
- 소스를 `D:\tools\audit_d22\ir`에 얕은 클론으로 받았습니다(git이 소유권 경고를 냈지만 파일은 전부 받아짐). 읽은 파일:
  - README.md
  - plugins/inspect-robots-agent/README.md
  - plugins/inspect-robots-isaacsim/README.md
  - plans/0001-foundation-design.md
  - plans/0007-xpolicylab-policy-plugin.md
  - docs/guide/scoring.md
  - docs/guide/policies-and-embodiments.md
- 수치 출처: GitHub API(별·날짜·릴리스·기여자), robocurve.org 번들 JS(보고서 요약문), 위 두 블로그 보고서.
- D:\qdd는 읽기만 했습니다.

Sources:
- [robocurve/inspect-robots](https://github.com/robocurve/inspect-robots)
- [robocurve.org](https://robocurve.org)
- [GPT-6 Astra 보고서](https://openai.robocurve.org/gpt-6-astra/)
- [StationeryBench 보고서](https://openai.robocurve.org/stationerybench/)
- [YC Launch](https://www.ycombinator.com/launches/TGj-robocurve-real-world-evaluations-of-physical-ai)
- [RuntimeWire 기사](https://runtimewire.com/article/robocurve-unveils-inspect-robots-free-framework-to-benchmark-ai-driven-robots)
- [robocurve/roboharm](https://github.com/robocurve/roboharm)
