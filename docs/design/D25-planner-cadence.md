# D25. 상위 계획기(Astra) 호출 주기 — Gemini Robotics는 어떻게 했나

작성: 2026-09-24, 조사 에이전트. 커밋하지 않음(메인 세션이 검토 후 반영).

사용자 질문(user-log 원문 그대로): "근데 처음 계획 세우고 실패할 때만 불러온다는 것 자체도 약간 좀 이상한데 어느 정도 주기로 하든지 뭔가가 있어야 될것 같은데 제미나이 3.0에서 어떤 식으로 했는지 한번 찾아봐봐 상위 계획기를 어떤 식으로 사용했는지 VLA 할때"

## 0. 조사 방법과 한계

- 이 세션의 WebSearch 한도(200회)는 시작 시점에 이미 다 쓴 상태였다. 그래서 **검색 없이 1차 원문 URL을 직접 내려받아** 읽었다(curl → `D:\tools\scratch_qdd\d25\`). 인용 수는 Semantic Scholar API로 쟀다(2026-09-24).
- 직접 읽은 1차 원문:
  - Google 공식 문서: ai.google.dev `robotics-overview`, `robotics-orchestration`, `robotics-streaming`, `robotics-video-progress`(2026-09 갱신판).
  - 공식 저장소 `google-gemini/robotics-samples` 코드: `live-api/agent/` 아래 `session_manager.py`, `server.py`, `tool/tools.py`, `core/tool_call_handler.py`, `embodiment/robot_client.py`, `camera_poller.py`, `prompt/data/spot_di.md`.
  - DeepMind 블로그: Gemini Robotics 2(2026-07-30), Gemini Robotics ER 2(blog.google, 2026-07-30), ER 1.6(2026-04-14), Gemini Robotics 1.5(2025-09-25), On-Device(2025-06), ER 1.5 개발자 블로그. 모델 카드 ER 2. 안전 보고서 `Gemini-Robotics-2-Safety.pdf`.
  - arXiv HTML: Gemini Robotics 1.5(2510.03342), Gemini Robotics(2503.20020), π0.5(2504.16054), Hi Robot(2502.19417), GR00T N1(2503.14734), RoboBrain 2.0(2507.02029), Agentic Robot(2505.23450), OneTwoVLA(2505.11917), A3(2605.11567). Figure Helix 블로그.
  - 이미 정독한 문서 재사용: Slow Brain·GPT-as-Policy(`D9`), Harness VLA(`D10a`), CheckVLA·Critic in the Loop(`D10b`), JEV-Star·REFLEX(`D12`), 나머지 트리거 비교 문헌(M8 §2).
- 못 한 것: 새 키워드 검색(한도 소진, Semantic Scholar 검색도 429로 대부분 실패). 그래서 "2025–26에 계획기 재질의 주기를 수치로 비교한 새 논문"은 M8 §2에 이미 있는 것 + OneTwoVLA·Agentic Robot만 다룬다. **부재 주장이 아니다.**
- GR00T N1.5·N1.6, RoboDawn의 System 2 주기는 이번에 원문을 새로 열지 않았다(§8).

## 1. "제미나이 3.0"이 로봇에서 무엇을 가리키나

- 2026-09 기준 "Gemini 3.0 로보틱스"라는 제품 이름은 없다. 가장 가까운 것은 아래 둘이다.
  - **Gemini Robotics ER 2**(2026-07-30): 모델 카드 원문 "Gemini Robotics ER (Embodied Reasoning) 2 is based on Gemini 3.5 Flash." 즉 Gemini 3 세대 위의 로봇용 상위 모델이다. 같은 날 VLA인 **Gemini Robotics 2**와 **On-Device 2**가 함께 나왔다.
  - **Gemini Robotics-ER 1.6**(2026-04-14): 블로그가 "Gemini 3.0 Flash"를 비교 대상으로 둔다("significant improvement over both Gemini Robotics-ER 1.5 and Gemini 3.0 Flash"). ER 1.6은 2026년 8월 말 종료 예정이다(API 문서).
- 따라서 이 문서는 "제미나이 3.0 = Gemini 3 세대 기반의 Gemini Robotics 2 계열(ER 2 + GR 2)"로 읽고, 그 앞 세대(GR 1.5 / ER 1.5)도 함께 본다. 사용자가 다른 것을 뜻했다면 알려 주면 다시 찾는다.

## 2. Gemini Robotics 계열 원문: 상위 모델이 VLA를 언제, 어떻게 부르나

### 2.1 Gemini Robotics 1.5 / ER 1.5 (2510.03342, 2025-10-02) — HIGH (DeepMind, 인용 89)

[원문]
- 구조: "The full agentic system consists of an orchestrator and an action model that are implemented by the VLM and the VLA, respectively". 오케스트레이터(ER 1.5)는 "breaks complex tasks into simpler steps that can be executed by the VLA, and it performs success detection to decide when to switch to the next step."
- 아래로 내려보내는 것: **자연어 지시**. "It is made available to the orchestrator as a specialized tool and receives instructions via open-vocabulary natural language."
- 두 층의 시간 척도: 오케스트레이터가 "pack the rain jacket into the luggage" 같은 지시를 보내면, VLA가 그것을 다시 "shorter segments that correspond to a few seconds of robot movement each"로 쪼갠다(Thinking VLA). 즉 **몇 초 단위의 재분해는 VLA 쪽**이 한다.
- Thinking VLA는 하위 과제 완료를 스스로 알아채고 다음 목표로 넘어가며("removing the need for an explicit success detector"), 물병을 놓치면 "the next thinking trace immediately becomes 'pick up the water bottle with the left hand'"로 복구한다.
- 상위 모델의 실시간 한계: ER의 성공 감지를 5 Hz로 돌리고 지연을 흉내 낸 실험에서 "models often require long inference time making real-time usage challenging, since stale success predictions quickly become irrelevant during dynamic robot interactions."
- 실패 분해(표 1, 장기 과제): 계획 실패 Gemini 2.5 Flash 25.5% 대 ER 1.5 9%, 성공 감지 실패 6% 대 4%, VLA 실행 실패 13% 대 9%, 합계 44.5% 대 22%(M8·SUMMARY에 이미 정정 반영된 값).
- **보고서에 없는 것**: 오케스트레이터를 몇 Hz로 부르는지, 로봇이 오케스트레이터를 기다리는지. 보고서가 적은 호출 시점은 "하위 과제 성공 감지로 다음 단계 전환"뿐이다.

### 2.2 Gemini Robotics 2 / ER 2 (2026-07-30) — 공식 블로그·문서·코드 (HIGH: 제조사 1차 자료, 단 독립 검증 없음)

[원문, blog.google ER 2]
- "Think of Gemini Robotics ER 2 as a high-level brain for robots. … It then hands off motor execution to any given lower level vision-language-action (VLA) model."
- "The design of Gemini Robotics ER 2 allows the robot to 'think' about what comes next **while simultaneously performing its actions**."
- "Gemini Robotics ER 2 commands action models and robotics APIs to complete multi-step tasks **without the jarring 'stop-and-think' pauses**."
- "By watching continuous video feeds, robots can now track their own progress, adapt if something goes wrong, and know exactly when to move on to the next step." 진행 분류(5구간) 정확도 57.4%(블로그 수치, 표 없음).

[원문, DeepMind GR2 블로그] ER 2가 "observes the room, reasons about the steps needed to complete the task, coordinates with the VLA to carry out the actions, and tracks progress until the task is done … self-correct if a step fails". 과제는 "lasting several minutes and involving hundreds of decisions".

[원문, 안전 보고서] "During physical execution, the Agent **continuously monitors** dynamic safety-relevant states, such as actuator health or human proximity." 사람이 다가오면 ER 2가 "orchestrates the VLA to settle down in-hand objects and move the robot to a safe pose, before autonomously resuming the nominal task"(실험실 사람 감지 99%, 안전 자세 전환 96%).

**핵심: 주기는 공식 문서와 코드에 있다.**

[원문, ai.google.dev `robotics-streaming` "Proactive spatial-temporal reasoning"]
- "The Live API streams video in, but video frames alone do not trigger a new reasoning turn."
- "To enable proactive reasoning, implement a **heartbeat**: periodically send the latest camera frame followed by a short text prompt that forces the model to inspect the scene and make an explicit decision. Video input is rate-limited to one frame per second."
- "It opportunistically targets a **1 Hz cadence** (matching the video input rate limit) while **waiting for each turn to complete** … to avoid interrupting in-flight reasoning".
- 하트비트 문장(원문 그대로): "[HEARTBEAT] If no task is active, call 'ack' and wait for user input. If a task is active: observe the scene. If the current step is progressing correctly, call 'ack'. If the current step is complete, call 'run_instruction' with the next step. If the overall goal is achieved, call 'reset' and inform the user."
- 주의 문구: "Sending a new prompt while the model is generating acts as an interruption (barge-in), which cancels in-flight reasoning and tool calls. If you fire heartbeats on a blind timer without waiting for the previous turn to complete, you may trap the model in a cancellation loop".
- 도구 규칙: "Physical actions must use `"behavior": "BLOCKING"` so the model waits for the robot to finish before choosing the next step."

[원문, 공식 저장소 `google-gemini/robotics-samples`(116★, 2025-10 생성) — 코드 사실은 MED~HIGH, 성능 주장은 없음]
- `run_instruction` 도구 설명: "When you call this tool, the robot will start executing the instruction. **The robot continues executing until you call `run_instruction` again** with a new instruction. Observe the scene visually to determine if the current step is complete." 로봇 클라이언트 구현은 "(fire-and-forget)" — 지시를 보내고 바로 돌아온다. 즉 **VLA는 계속 돌고, ER은 하트비트마다 지켜보다가 다음 지시로 갈아 끼운다.** 로봇이 ER을 기다리지 않는다.
- `ack` 도구: "acknowledge the regular heartbeat and indicate that no new intervention is needed. This is the default action".
- 하트비트 두 방식(`session_manager.py`, `server.py` 기본값):
  - 기본 = **사건 구동 하트비트**(`use_event_driven_heartbeat=True`): 앞 턴이 끝나면(도구 호출이 없던 턴) 곧바로 다음 하트비트를 보낸다. 직전 하트비트 뒤 0.5 s 안에는 보내지 않는다. 10 s 동안 모델 응답이 없으면 "safety_timeout" 복구 하트비트. 즉 실효 주기 ≈ **모델 응답 시간**(요청 1개만 진행).
  - 옛 방식 = 고정 간격 `heartbeat_interval_seconds=2.0`, 턴 완료를 기다리고 최소 지연을 둠.
  - 블로킹 도구(pick, place, navigate 등)가 실행 중이면 하트비트를 보내지 않는다: "Suppressing %s heartbeat while blocking tool executes".
- 카메라: 여러 카메라를 한 장으로 이어 붙여(`cell_size=384`) 1 Hz로 넣고, 최근 10장을 버퍼에 둔다. 카메라가 흔들리면 pick/place를 거부하는 안정도 검사가 있다.
- 로봇용 시스템 문장(`spot_di.md`): "You are operating in a closed-loop control system. You will be prompted at a regular frequency to make a decision. At each prompt, evaluate the current state and decide to either take an action or call the `ack` tool if no intervention is needed."

[원문, `robotics-orchestration`, 스트리밍 아닌 표준 ER 2] 다른 방식도 있다. 도구 호출 → 결과 반환 → 다음 도구 호출을 반복하는 **순차 에이전트 루프**(max_steps 15, thinking_level "low"). 이 방식은 모델이 생각하는 동안 로봇이 다음 명령을 기다린다. ER 2 블로그가 "stop-and-think 없이"라고 강조한 것은 이 방식 대신 스트리밍 + 하트비트를 쓰라는 뜻으로 읽힌다(우리 해석).

[원문, API 문서 한계 절] "For thinking level use medium for a good balance between latency and performance."

### 2.3 Gemini Robotics(1.0, 2503.20020) / On-Device

- [원문] GR 1.0 VLA는 클라우드 백본(질의→응답 "under 160ms") + 로봇 쪽 디코더, "end-to-end latency … approximately 250ms", 청크로 "effective control frequency is 50Hz". 상위 오케스트레이터의 호출 주기는 다루지 않는다. (2025-03-25, 기간 안. 인용 수는 Semantic Scholar 0으로 나오지만 색인 오류로 보인다. 신뢰도는 DeepMind 1차 보고서로 HIGH)
- [원문] On-Device(2025-06)·On-Device 2(2026-07): "operates independent of a data network, it's helpful for latency sensitive applications". VLA 단독이고 상위 계획 주기에 대한 서술은 없다.

### 2.4 Gemini 방식 한 줄 요약

| 질문 | Gemini Robotics 2 / ER 2의 답(원문 근거) |
|---|---|
| 상위 모델을 언제 부르나 | **주기 하트비트(목표 1 Hz, 앞 턴이 끝난 뒤에만)** + 하위 과제 완료 확인 + 사용자 입력·안전 사건. 실패 때만 부르지 않는다 |
| 하트비트에서 무엇을 묻나 | 닫힌 선택: `ack`(계속) / `run_instruction`(다음 단계) / `reset`(끝) / `stop`(안전) |
| 아래로 무엇을 넘기나 | 자연어 원자 지시 한 개(`run_instruction`), 또는 점·경로 같은 공간 출력(ER의 pointing 형식) |
| 로봇이 기다리나 | 아니다. VLA는 새 지시가 올 때까지 계속 실행(fire-and-forget). 블로킹 도구는 **모델**이 결과를 기다리고, 그동안 하트비트를 멈춘다 |
| 고속 재분해는 | Thinking VLA가 "몇 초 단위" 하위 조각으로 스스로 쪼갠다(GR 1.5) |
| 성공 감지 | 상위 모델(ER)이 영상으로 한다. 단 GR 1.5는 "stale success predictions"가 실시간 사용을 어렵게 한다고 적었다 |

## 3. 비교 대상 원문 (호출 주기만)

신뢰도: HIGH = 주요 학회 또는 인용 100 이상 또는 제조사 1차 자료, MED = 인용 20~100 또는 학회 미확인이지만 주요 연구실, LOW = 인용 10 미만·심사 전. 권고는 HIGH·MED에만 기댄다.

| 이름 | 날짜 | 상위 호출 주기 [원문] | 아래로 넘기는 것 | 로봇이 기다리나 | 신뢰도 |
|---|---|---|---|---|---|
| **Gemini Robotics 2 / ER 2** | 2026-07 | 하트비트 목표 1 Hz(턴 완료 뒤), 코드 기본은 사건 구동(턴 끝나면 바로, ≥0.5 s, 10 s 안전 타임아웃) | 자연어 지시, 도구 호출 | 아니오 | HIGH(제조사 문서·코드) |
| Gemini Robotics 1.5 | 2025-10 | 하위 과제 성공 감지 때 다음 단계로("decide when to switch to the next step"). 주기 미기재 | 자연어 지시 | 미기재 | HIGH(인용 89) |
| **π0.5** (2504.16054) | 2025-04 | "during each step of inference, the model first predicts the semantic subtask" + "the high-level inference process still runs at a lower frequency than low-level action inference" | 하위 과제 텍스트(같은 모델 안) | 아니오(한 모델) | HIGH(인용 1,899) |
| **Hi Robot** (2502.19417, ICML 2025) | 2025-02 | "we rerun high-level inference … either when **one second** has elapsed, or when a new interaction with the user takes place"; 사용자 개입은 "triggered immediately". 저자: 완료 감지 기반 전략도 가능하나 단순 주기가 "work well" | 저수준 언어 명령 | 아니오 | HIGH, **기간 밖 기초 문헌**(인용 254) |
| Figure Helix | 2025-02 | S2 "operating at 7-9 Hz", "asynchronous background process", S1 200 Hz가 "most recent S2 latent" 사용 | 잠재 벡터 | 아니오 | MED(제조사 블로그), **기간 밖** |
| GR00T N1 (2503.14734) | 2025-03-18 | "System 2 … runs at 10Hz on an NVIDIA L40", System 1 120 Hz | 내부 토큰 | 아니오 | HIGH(인용 1,346), **기간 밖**(5일 차) |
| **OneTwoVLA** (2505.11917) | 2025-05 | 모델이 스스로 추론 시점을 고름 "at key steps — like completing a subtask, detecting an error, or requiring human input". 183 s 과제에서 추론 5회·합 16 s(8.7%) | 추론 텍스트 → 같은 모델 행동 | **예**: 긴 추론(>100 토큰)이면 "the robot needs to pause for a few seconds" | MED(인용 123, 학회 미확인) |
| Agentic Robot (2505.23450) | 2025-05 | 계획기는 하위 목표 분해, 검증기(VLM) **0.5 Hz**(20프레임마다), 실행기 10 Hz. "only 1.2% drop from 10-frame intervals while reducing computational load by 48%" | 하위 목표 텍스트 | 아니오(비동기 FSM) | MED-LOW(인용 39, 심사 전) |
| RoboBrain 2.0 (2507.02029) | 2025-07 | 호출 주기 서술 없음 | — | — | MED(인용 100) |
| Harness VLA (2607.08448) | 2026-07 | 매 프리미티브 뒤 계획기가 결과 분류, "The planner waits for these files before selecting the next primitive" | 프리미티브 + 인자 | 예(동기) | MED(인용 23) |
| GPT-as-Policy (Galbot 보고서) | 2026-09 | **매 청크 경계** Astra(xhigh) 게이트, 개입은 failed·misaligned일 때만, 에피소드당 약 75회 | 편집·EEF 목표 | 예(시뮬 정지) | LOW-MED(심사·arXiv 없음) |
| Slow Brain (2606.20458) | 2026-06 | 고정 1 Hz 스트리밍, 여러 요청 동시 진행, 가장 새 응답 하나 융합. 실물 중앙 지연 약 2.7 s | 후보 번호 | 아니오 | LOW-MED(인용 0, Amazon FAR) |
| JEV-Star (2609.27331) | 2026-09 | "The planner is checked on a nominal 60-game-second interval and at relevant events"; 실패·지연 시 "previous valid plan available" | 계획 | 아니오 | LOW(인용 0) — 계층 선행이라 **반드시 인용**(00 §24) |
| CheckVLA (2607.26789) | 2026-07 | 호출 수 맞춘 비교: 주기 10.1회 대 검증 트리거 10.2회, 27.6 → 31.5% | 같은 VLA 재호출 | 아니오 | LOW-MED(인용 2) |
| Critic in the Loop (2603.05185) | 2026-03 | 완료·이상·정체(약 9 s)일 때만 상위 호출, 동기 | 하위 과제 | 예 | LOW-MED(인용 4) |
| A3 (2605.11567) | 2026-05 | VLA 청크를 몇 개 확정할지(실행 지평) — 상위 계획 주기가 아니라 **하위 재추론 주기** 문헌 | — | — | LOW(인용 1) |
| Learning When to Plan (2509.03581) | 2025-09 | 계획 빈도 스윕에서 **중간 빈도가 최고**, 항상 계획은 더 나쁨. "필요할 때만" 프롬프트로는 적응이 안 됨 | — | — | MED(인용 19) |
| AgileThinker (2511.04898, ICLR 2026) | 2025-11 | 빠른 반응 + 느린 계획 동시, 느린 쪽을 기다리지 않음 | — | 아니오 | HIGH |

## 4. 종합: 흔한 설계 5가지와 비용

| 설계 | 대표 | 좋은 점 | 비용·위험 |
|---|---|---|---|
| (a) 고정 주기 | Hi Robot 1 s, Helix 7–9 Hz, GR00T 10 Hz, Slow Brain 1 Hz, Gemini 하트비트 1 Hz | 실패 판정기가 못 잡는 조용한 어긋남(잘못된 단계, 새 물체, 사람)을 잡는다. 구현이 단순 | 호출 수·비용. 너무 잦으면 계획이 흔들림(Learning When to Plan, Critic in the Loop Dual-System 진동). 응답보다 빠른 타이머는 취소 고리(Gemini 주의 문구) |
| (b) 하위 과제 경계 | GR 1.5 오케스트레이터, Harness VLA, Agentic Robot 계획기 | 싸고 자연스럽다. 계획이 바뀌어야 할 시점과 잘 맞는다 | 단계 **안**에서 생긴 문제는 다음 경계까지 모른다 |
| (c) 사건·실패 | 우리 T_fail, Critic in the Loop, CheckVLA 트리거 | 필요할 때만 부른다. 호출 수 맞춘 비교에서 주기보다 낫다는 결과(CheckVLA, LOW-MED) | 감시기가 못 잡는 실패에는 무력. 감시기의 오경보가 곧 호출 비용 |
| (d) 비동기 배경 재계획 | Gemini 하트비트(fire-and-forget VLA), Helix, Slow Brain, AgileThinker | 로봇이 멈추지 않는다 | 늦게 온 답을 어떻게 섞을지 규칙 필요(낡음, 순서 역전) — 우리 M2 R5·M4 epoch가 이 자리 |
| (e) 확신·자체 판단 | OneTwoVLA(스스로 [BOR]), REFLEX(낮은 확신), 우리 J5·T3b | 필요한 순간에 부른다 | 대부분 학습이 필요(OneTwoVLA). 프롬프트만으로는 잘 안 됨(Learning When to Plan). 모델은 실패를 늦게 인정(BAGEN) |

- **실제 배포형 시스템은 섞는다.** Gemini ER 2는 (a)+(b)+(c)+(d)를 한 루프에 담았다: 하트비트(a)가 오면 모델이 "지금 단계 진행 중이면 ack, 끝났으면 다음 지시"를 고르므로(b), 사람·안전 사건은 도구로 바로 처리(c), 그동안 VLA는 계속 돈다(d). Hi Robot도 (a) 1 s + (c) 사용자 개입이다.
- 주기 값의 공통 모양: **주기 ≈ 상위 모델 1회 응답 시간 수준**. Gemini는 "앞 턴이 끝난 뒤에만 다음 하트비트, 목표 1 Hz"이고 코드 기본은 "턴이 끝나면 바로"다. Slow Brain은 1 Hz에 응답 2.7 s라 여러 요청을 겹쳐 보냈다. Hi Robot 1 s, Agentic Robot 검증 2 s(10프레임 대비 −1.2%, 계산 −48%).
- 수치로 잰 주기 효과(신뢰도 낮은 것 포함, 권고 근거는 MED 이상만): 중간 빈도 최고(Learning When to Plan, MED), 검증 간격 2 s가 1 s 대비 거의 같음(Agentic Robot, MED-LOW), 호출 수 맞추면 사건 트리거가 주기보다 +3.9%p(CheckVLA, LOW-MED — 참고만).
- 우리 쪽 함정 하나: GR 1.5 원문대로 **느린 상위 모델은 빠른 성공 감지에 맞지 않는다**("stale success predictions quickly become irrelevant"). Astra 첫 토큰 약 3 s(low)면 단계 완료 판정은 지금처럼 M7 코드(빠름)가 하고, Astra 주기 확인은 "계획이 아직 맞나"를 보는 쪽이 맞다.

## 5. 우리 설계와의 대응

| Gemini Robotics 2 | 우리(정본 §44 이후) | 비고 |
|---|---|---|
| ER 2(오케스트레이터, 하트비트 목표 1 Hz) | **Astra**(GPT-6 Astra, effort low, 첫 토큰 2.975 s·완료 3.288 s — 출력 10토큰 스모크 1회, `stage3/results/astra_model_id.md`) | Astra는 ER 2보다 여러 배 느리다 → 같은 1 Hz는 못 한다 |
| Thinking VLA(몇 초 단위 하위 조각 재분해) | **Jev-L 3 Hz typed 선택기**(`dp.next_skill` 등) + M4 겹침 합의 | "매 스텝 하위 과제 재추론"(π0.5)에 해당하는 빠른 층은 이미 있다 |
| GR 2 VLA(모터) | 스크립트 스킬 S + 잔차 R | |
| `run_instruction` fire-and-forget, 다음 지시 올 때까지 계속 | 활성 계약으로 계속, 새 계약은 M2 R3 경계에서 교체 | 같은 모양 |
| `ack` / `run_instruction` / `reset` / `stop` | `ack` / `patch` / `replace` / (안전은 M7·M9) | 닫힌 선택지 |
| 사건 구동 하트비트(턴 완료 뒤, 진행 요청 1개) | M8 §4.2 "진행 중 비실패 요청 1개" | 이미 같은 제약 |

→ **지금 설계(T0 + 실패·사건 트리거)에 빠진 것은 Gemini의 (a) 주기 하트비트와 (b) 단계 경계 확인이다.** 사용자 직감("어느 정도 주기로 하든지 뭔가가 있어야")이 Gemini·Hi Robot·π0.5 모두와 맞는다. M8의 T1(주기)·T2(정해 둔 순간)는 비교 조건으로만 있었고, [결정 필요] D33(JEV-Star식 주기 + 사건)도 아직 넣지 않은 상태였다.

## 6. 권고안 [우리 접목안, 정본 반영은 메인 세션·사용자 결정]

> **[→ 정본 §82 갱신 2026-09-25 15:27 UTC]** 이 절(6.1–6.3과 표)의 T_hb 5 s 하트비트·T_sub 단계 경계 기본값은 §82(2026-09-25, user-log 74·76)로 대체됐다: 닫힌 감시는 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사. 아래 표 칸 밖의 §82 표시는 렌더에서 빠지므로 이 줄이 절 전체에 적용된다.

사용자 원칙은 그대로 둔다: T0만 정지 허용, 실패하면 항상 Astra(T_fail), 그 밖에는 멈추지 않는다, effort 기본 low.

### 6.1 호출 규칙 "H-cadence" (Gemini ER 2 하트비트의 Astra판)

| id | 언제 | 무엇을 묻나 | 진행 중 요청 | 근거 |
|---|---|---|---|---|
| T0 | 과제 시작 | 첫 계약(A5′ 검사·수리) | 기다림(정지 허용) | 기존 |
| **T_hb 하트비트** (새 기본) | 직전 Astra 응답(어떤 트리거든)이 도착한 뒤 **N초가 지나면** 다음 확인. 기본 **N = 5 s** [가정, §6.3 실험으로 결정]. 응답이 N보다 늦으면 도착 즉시 다음 확인(= Gemini 사건 구동). 응답이 **15 s** 넘게 안 오면 안전 타임아웃 기록 후 새 하트비트 1회(Gemini 10 s 안전 타임아웃을 Astra 지연에 맞게 늘림 [가정]) | 닫힌 선택 `ack` / `patch` / `replace`. 입력 = 활성 계약 요약 + `based_on` 이후 변한 사실 + 현재 단계·경과(BATS식 명시) + 머리캠 격자(작게) | 비실패 1개(기존 M8 §4.2 그대로). **타이머로 겹쳐 보내지 않는다**(Gemini 취소 고리 주의) | Gemini 하트비트, Hi Robot 1 s, JEV-Star 주기+사건 | [→ 정본 §82(2026-09-25, user-log 74·76): 5 s 하트비트·단계 경계 확인·Astra 성공 판정은 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사로 대체 — 이 줄은 §82 이전 설계]
| **T_sub 단계 경계** (새 기본) | M7이 단계 k `exit` 참을 확정한 순간 | "다음 단계 k+1 계약이 지금 장면에서도 맞나" (`ack`/`patch`/`replace`). **다음 단계는 기다리지 않고 바로 시작**, 답은 R3 경계에서 적용 | 진행 중 하트비트가 있으면 새로 보내지 않고 그 요청이 경계 정보를 싣게 함(합치기). 하트비트 타이머는 경계 호출로 초기화 | GR 1.5 "success detection to decide when to switch", OneTwoVLA "completing a subtask" | [→ 정본 §82(2026-09-25, user-log 74·76): 5 s 하트비트·단계 경계 확인·Astra 성공 판정은 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사로 대체 — 이 줄은 §82 이전 설계]
| T_fail | M7 FAIL | 진단·복구(연속 프레임 격자) | 진행 중 하트비트가 있어도 **새로 보냄**(기존), 하트비트는 복구 완료 + cooldown 2 s까지 **멈춤** | 기존 원칙, Gemini "블로킹 도구 실행 중 하트비트 억제" |
| 사건 | `C_assume`(가정 거짓, 계약 거부), T3a 마감, T_stag 정체, **T_j5**(J5 보류 2번 연속), 사용자 새 지시 | 사건 문맥 붙인 확인 | 하트비트 자리를 **앞당겨** 쓴다(다음 하트비트 대신 지금 보냄). 사용자 지시는 즉시(Hi Robot "triggered immediately") | M2 R4, M8 T3a·T_stag, 정본 §31 J5, Hi Robot |

- 확신 기반(J5 반복)은 E1 뒤에 켠다(정본 §6·§31 그대로). 켜기 전에는 하트비트가 그 몫을 느리게나마 대신한다.
- effort: 하트비트·단계 경계는 **low 고정**, `ack`가 대부분이므로 최대 출력 토큰을 작게(예: `ack`면 짧은 JSON) 두고, `patch`/`replace`일 때만 계약 필드를 쓴다. T_fail은 기존대로(low, 비교는 low·high).

### 6.2 결과를 합치는 규칙 (M2·M4와의 연결, 새 규칙 없음)

1. 모든 응답은 `based_on_t_state`를 가진다. **M2 R5**: 기준 시각이 더 새 것만 받는다. 하트비트 답이 T_fail 답보다 늦게 와도, T_fail 요청보다 먼저 찍힌 관측에 기댄 답이면 적용하지 않고 기록만 한다.
2. `ack` → 아무것도 바꾸지 않는다. 계약 버전·**M4 `premise_epoch` 그대로**(하트비트가 epoch를 흔들지 않게 하는 것이 핵심 — 흔들면 M4 합의 표가 계속 비워진다).
3. `patch` / `replace` → **A5′** 코드 검사 1–7 → 통과하면 **M2 R3 시점**(결정 스텝 경계, 비가역 phase면 그 phase 끝)에 교체 + `premise_epoch` +1. 불통과면 이전 유효 계약 유지(R7) + 백그라운드 수리(최대 2회). **A4′** 강제 replace 규칙 그대로.
4. 흔들림 억제(Critic in the Loop Dual-System 진동 대비): 같은 단계에서 하트비트 `patch`가 **서로를 되돌리는 변경**(A→B→A)을 30 s 안에 2번 내면 그 단계 동안 하트비트 `patch`를 기록만 하고 적용하지 않는다 [가정]. 실패·사건 호출의 답에는 이 억제를 걸지 않는다.
5. 비용 상한: 에피소드당 비실패 Astra 호출 상한 `B_hb`(시작값 = 과제 예상 시간 / N × 1.2) [가정]. 넘으면 하트비트만 끄고 단계 경계·사건·실패 호출은 유지(BATS식 예산을 코드가 셈).

### 6.3 기본 N = 5 s를 고른 이유와 한계

- Gemini ER 2: 하트비트 목표 1 Hz, 앞 턴이 끝나야 다음 → 주기 ≈ max(1 s, 응답 시간). Hi Robot 1 s. 둘 다 상위 모델 응답이 1 s 안팎인 조건이다.
- Astra low: 첫 토큰 약 3.0 s, 10토큰 출력 완료 3.3 s(1회 측정). `ack` 위주의 짧은 출력이면 1회 응답이 약 3.5~4 s일 것으로 본다(추정, 계약 크기 출력이면 더 길다 — 미측정).
- 진행 중 요청 1개 규칙에서 "응답 도착 뒤 N초" 규칙이면 실효 주기 = 응답 시간 + N ≈ 8~9 s(N=5). "응답 도착 즉시"(N=0, Gemini 코드 기본과 같은 모양)면 약 4 s. **5 s는 Gemini·Hi Robot의 "응답 시간 수준" 원칙을 지키면서 호출 수를 절반쯤으로 줄인 출발값**이다. 3분 과제면 비실패 하트비트 약 20~40회, 호출당 입력 약 3,600(격자) + 2,000(텍스트) 토큰.
- 근거가 설계 원칙(HIGH, 제조사 문서·ICML)이지 우리 조건의 측정이 아니다. **N은 아래 실험으로 정한다.**

### 6.4 실험 E-M8c 호출 주기 (사전 등록, E-M8a의 변형)

- 목적: (i) 하트비트가 필요한가, (ii) 필요하면 N을 몇으로 할까.
- 조건(모두 T0 + T_fail + 기존 사건 트리거 포함, 사용자 원칙 불변):
  - **K0** 현행: 하트비트·단계 경계 없음(= E-M8a의 사건 조합).
  - **K1** + T_sub(단계 경계만).
  - **K2-N** + T_sub + T_hb, N ∈ {0(도착 즉시, Gemini 코드 기본형), 5, 10, 20} s. [→ 정본 §82(2026-09-25, user-log 74·76): 5 s 하트비트·단계 경계 확인·Astra 성공 판정은 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사로 대체 — 이 줄은 §82 이전 설계]
  - **K3 Gemini 원문 충실판**: 하트비트 문장을 §2.2 원문 그대로(ack / 다음 단계 / reset), 단계 경계 없음, N = 0, 진행 요청 1개.
  - **K4 호출 수 맞춤 대조**: K2-5와 에피소드당 비실패 호출 수를 ±10%로 맞춘 사건 전용 판(CheckVLA 관행, 문턱은 개발 분할에서만 조정).
- 섭동(E-M8a와 같음) + **감시기 밖 실패** 2종을 반드시 넣는다: M7이 FAIL을 내지 않지만 계획이 틀린 경우(다른 물체를 잡음, 목표 물체가 옮겨짐, 새 장애물). 하트비트의 존재 이유가 이것이므로, 이 칸이 없으면 실험이 하트비트 가치를 못 잰다.
- 지표: 성공률, 완료 시간, **정지 시간**(T0 + M9 L3 밖 정지는 구현 결함), 감시기 밖 실패의 **발견 지연**(섭동 시각 → 첫 `patch`/`replace` 적용), 비실패 호출 수·토큰·비용, `premise_epoch` 증가 횟수, 되돌림 patch 비율(흔들림), rescue/harm(CheckVLA 정의).
- 판정 기준(실행 전 고정):
  1. K2-N 중 어느 것이 K1보다 성공률 +3%p 이상이고 부트스트랩 95% 구간 하한 > 0이면 "하트비트 필요". 아니면 기본 = K1(단계 경계 + 사건), 하트비트는 끔.
  2. 하트비트가 필요하면 **최고 성공률 조건 대비 −2%p 안에 드는 N 중 가장 큰 N**을 기본으로 한다(같은 성능이면 싼 쪽).
  3. K2-N이 K4(호출 수 맞춘 사건 전용)보다 −2%p 안이면 "주기의 이득은 호출 수 몫"으로 보고하고, 감시기 밖 실패 발견 지연으로 둘을 가른다.
  4. 되돌림 patch 비율이 N = 0에서 N = 20보다 유의하게 크면(짝 부트스트랩 하한 > 0) 흔들림 억제(§6.2-4) 문턱을 올리는 것을 [결정 필요]로 올린다.
  5. 정지 시간은 모든 조건에서 T0 + L3만 허용.
- 반복·검정력: 정본 §28 그대로(Astra 조건 비교는 2%p 검출 약 9회 기준 반복, 단일 실행 결론 금지, 매일 카나리). 시드 3개 이상. N·문턱은 개발 분할에서만 조정.
- 순서: E0(Astra 실제 입력 지연 p50/p95 측정) 뒤. E0에서 `ack` 응답 p95가 N보다 크면 N 후보를 {0, p95, 2×p95, 4×p95}로 바꾼다(이 규칙도 사전 등록).

## 7. 반대 증거와 위험

1. 자주 부르면 나빠질 수 있다(Learning When to Plan: 항상 계획 < 중간 빈도, MED; Critic in the Loop Dual-System 진동, LOW-MED). → `ack` 기본, epoch 불변, 되돌림 억제.
2. 호출 수를 맞추면 사건 트리거가 주기보다 낫다는 결과가 있다(CheckVLA, LOW-MED). → K4 대조로 직접 잰다.
3. Gemini의 1 Hz는 ER 2(Flash 기반) + 스트리밍 엔드포인트 조건이다. Astra에 그대로 옮길 수 없고, "stop-and-think 없음"은 제조사 주장이며 독립 측정이 없다.
4. 느린 상위 모델의 판단은 금방 낡는다(GR 1.5 원문). Astra 하트비트를 단계 완료 판정에 쓰면 안 된다 → 완료 판정은 M7 코드 유지.
5. 비용: 하트비트는 에피소드당 Astra 호출을 수십 회 늘린다. 공급자 비용 기준 반대 이론(2602.09902)은 M8 §6-7에 이미 기록.
6. 새로움: 주기 + 사건 계층은 JEV-Star·Gemini ER 2가 이미 했다. 우리 차이 문장은 00 §24대로 "실패 판정이 불러내는 호출 + 겹침 합의·실행 뒤 확인(M4)"에 두고, 하트비트는 선행을 따른 것으로 적는다.

## 8. 확인 못 한 것

- Gemini ER 2 스트리밍의 실제 응답 지연 수치, 하트비트 주기별 성능 비교(문서·블로그에 없음).
- GR 1.5 보고서의 오케스트레이터 호출 주기와 로봇 대기 여부(보고서에 없음).
- GR00T N1.5·N1.6의 System 2 주기, RoboDawn의 상위 호출 주기(이번에 원문을 열지 않음).
- Hi Robot·Helix·GR00T N1은 기간 밖(2025-03-23 이전) 기초 문헌이다.
- 2025–26에 "주기 대 사건 대 비동기"를 수치로 비교한 새 논문 검색(검색 한도 소진). M8 §2 목록 밖의 결과는 찾지 못했을 수 있다.
- Astra 계약 크기 출력의 완료 시간(E0에서 잴 것).

## 출처

- Gemini Robotics ER 개요: https://ai.google.dev/gemini-api/docs/robotics-overview
- 작업 오케스트레이션: https://ai.google.dev/gemini-api/docs/robotics-orchestration
- 스트리밍·하트비트: https://ai.google.dev/gemini-api/docs/robotics-streaming
- 영상 진행: https://ai.google.dev/gemini-api/docs/robotics-video-progress
- 공식 예제 코드: https://github.com/google-gemini/robotics-samples/tree/main/live-api
- ER 2 모델 카드: https://deepmind.google/models/model-cards/gemini-robotics-er-2/
- ER 2 블로그: https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-robotics-er-2/
- Gemini Robotics 2 블로그: https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/
- Gemini Robotics 2 안전 보고서: https://storage.googleapis.com/deepmind-media/gemini-robotics/Gemini-Robotics-2-Safety.pdf
- ER 1.6 블로그: https://deepmind.google/blog/gemini-robotics-er-1-6/
- Gemini Robotics 1.5 블로그: https://deepmind.google/discover/blog/gemini-robotics-15-brings-ai-agents-into-the-physical-world/
- ER 1.5 개발자 블로그: https://developers.googleblog.com/en/building-the-next-generation-of-physical-agents-with-gemini-robotics-er-1-5/
- On-Device 블로그: https://deepmind.google/discover/blog/gemini-robotics-on-device-brings-ai-to-local-robotic-devices/
- Gemini Robotics 1.5: https://arxiv.org/abs/2510.03342 · Gemini Robotics: https://arxiv.org/abs/2503.20020
- π0.5: https://arxiv.org/abs/2504.16054 · Hi Robot: https://arxiv.org/abs/2502.19417 · GR00T N1: https://arxiv.org/abs/2503.14734 · Helix: https://www.figure.ai/news/helix
- OneTwoVLA: https://arxiv.org/abs/2505.11917 · Agentic Robot: https://arxiv.org/abs/2505.23450 · RoboBrain 2.0: https://arxiv.org/abs/2507.02029 · A3: https://arxiv.org/abs/2605.11567
- 이미 정독한 문헌은 `D9`, `D10a`, `D10b`, `D12`, `M8 §2`의 출처를 따른다.
